#!/usr/bin/env python3
"""Exclusive, reversible stock-norns smoke runner; credentials stay external."""
import argparse,ctypes,hashlib,json,re,socket,struct,subprocess,sys,tarfile,tempfile,time
from pathlib import Path
REPO=Path(__file__).resolve().parents[2];ROOT='/home/we/.cache/mosaic-real-norns'
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def osc_string(value):
 data=value.encode()+b'\0';return data+b'\0'*((-len(data))%4)
def osc_packet(path,*values):return osc_string(path)+osc_string(','+'i'*len(values))+struct.pack('!'+('i'*len(values)),*values)
class OSC:
 def __init__(self,host,port):self.address=(host,port)
 def send(self,kind,n,value):
  if kind not in ('key','enc'):raise ValueError('Stock OSC supports only key and enc actions')
  packet=osc_packet('/remote/'+kind,int(n),int(value))
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as out:out.sendto(packet,self.address)
  return {'type':kind,'n':int(n),'value':int(value),'host_monotonic_ns':time.monotonic_ns(),'packet_hex':packet.hex()}
class SSHOSC(OSC):
 def __init__(self,ssh,port):self.ssh=ssh;self.port=port
 def send(self,kind,n,value):
  if kind not in ('key','enc'):raise ValueError('Stock OSC supports only key and enc actions')
  packet=osc_packet('/remote/'+kind,int(n),int(value));lower=time.monotonic_ns();self.ssh.run("python3 - <<'PY'\nimport socket\np=bytes.fromhex('"+packet.hex()+"')\ns=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)\ns.sendto(p,('127.0.0.1',"+str(self.port)+"))\ns.close()\nPY\n");upper=time.monotonic_ns()
  return {'type':kind,'n':int(n),'value':int(value),'host_monotonic_ns':lower,'host_completion_ns':upper,'packet_hex':packet.hex(),'transport':'ssh-loopback-udp'}
class SSH:
 def __init__(self,host,options=()):self.host=host;self.options=list(options)
 def run(self,script):return subprocess.run(['ssh',*self.options,self.host,'bash','-s'],input=script,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
 def rsync(self,source,dest):
  import shlex;shell=' '.join(shlex.quote(x) for x in ['ssh',*self.options]);subprocess.run(['rsync','-a','--delete','-e',shell,str(source)+'/',self.host+':'+dest+'/'],check=True)
 def fetch(self,remote,local):local.parent.mkdir(parents=True,exist_ok=True);local.write_bytes(subprocess.check_output(['ssh',*self.options,self.host,'cat',remote]))
 def push(self,local,remote):subprocess.run(['ssh',*self.options,self.host,'tee',remote],input=Path(local).read_bytes(),stdout=subprocess.DEVNULL,check=True)
class Maiden:
 """Persistent nanomsg BUS client for official Maiden's matron socket."""
 def __init__(self,url,library='libnanomsg.so.5',timeout_ms=120000):
  self.url=url;self.library=library;self.timeout_ms=timeout_ms;self.nn=None;self.fd=None;self.endpoint=None
 def _connect(self):
  if self.fd is not None:return
  nn=ctypes.CDLL(self.library);nn.nn_socket.argtypes=[ctypes.c_int,ctypes.c_int];nn.nn_connect.argtypes=[ctypes.c_int,ctypes.c_char_p];nn.nn_setsockopt.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t];nn.nn_send.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int];nn.nn_recv.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int];nn.nn_close.argtypes=[ctypes.c_int]
  fd=nn.nn_socket(1,112)
  if fd<0:raise RuntimeError('nn_socket failed')
  timeout=ctypes.c_int(self.timeout_ms)
  if nn.nn_setsockopt(fd,0,5,ctypes.byref(timeout),ctypes.sizeof(timeout))<0:nn.nn_close(fd);raise RuntimeError('nn_setsockopt RCVTIMEO failed')
  if nn.nn_setsockopt(fd,0,4,ctypes.byref(timeout),ctypes.sizeof(timeout))<0:nn.nn_close(fd);raise RuntimeError('nn_setsockopt SNDTIMEO failed')
  endpoint=nn.nn_connect(fd,self.url.encode())
  if endpoint<0:nn.nn_close(fd);raise RuntimeError('nn_connect failed')
  self.nn=nn;self.fd=fd;self.endpoint=endpoint;time.sleep(.25)
 def _send(self,payload):
  self._connect();buf=ctypes.create_string_buffer(payload)
  if self.nn.nn_send(self.fd,buf,len(payload),0)!=len(payload):raise RuntimeError('nn_send failed')
 def eval(self,code):
  marker='__MOSAIC_HW_'+hashlib.sha256((code+str(time.monotonic_ns())).encode()).hexdigest()[:16]+'__';payload=(code.rstrip()+"; print('"+marker+"')\n").encode()+b'\0';self._send(payload);output=[]
  while True:
   received=ctypes.create_string_buffer(65536);size=self.nn.nn_recv(self.fd,received,len(received),0)
   if size<0:raise TimeoutError('Maiden marker not observed')
   chunk=received.raw[:size].decode(errors='replace');output.append(chunk)
   if 'stack traceback:' in chunk:raise RuntimeError('Maiden Lua error: '+''.join(output)[-2000:])
   if marker in chunk:return ''.join(output)
 def send(self,code):self._send((code.rstrip()+'\n').encode()+b'\0');time.sleep(.25)
 def load(self,path):
  self.send("norns.script.load("+repr(path)+")");time.sleep(8);ready=self.eval("print('__MOSAIC_ACTIVE__'..(norns.state.script or ''))")
  if path not in ready:raise RuntimeError('norns did not activate '+path+': '+ready[-1000:])
  return ready
 def close(self):
  if self.fd is None:return
  try:
   shutdown=getattr(self.nn,'nn_shutdown',None)
   if shutdown is not None:shutdown(self.fd,self.endpoint)
  finally:self.nn.nn_close(self.fd);self.fd=None;self.endpoint=None
class WebSocketMaiden:
 """Persistent official Maiden WebSocket text client."""
 def __init__(self,url,wheel=None,timeout_ms=120000,connector=None):
  self.url=url;self.wheel=wheel;self.timeout=timeout_ms/1000;self.connector=connector;self.ws=None
 def _connect(self):
  if self.ws is not None:return
  if self.connector is None:
   if self.wheel:sys.path.insert(0,str(self.wheel))
   from websockets.sync.client import connect
   self.connector=connect
  self.ws=self.connector(self.url,subprotocols=['bus.sp.nanomsg.org'],open_timeout=self.timeout,close_timeout=1)
 def eval(self,code):
  self._connect();marker='__MOSAIC_HW_'+hashlib.sha256((code+str(time.monotonic_ns())).encode()).hexdigest()[:16]+'__';self.ws.send(code.rstrip()+"; print('"+marker+"')\n");output=[]
  while True:
   chunk=self.ws.recv(timeout=self.timeout)
   if isinstance(chunk,bytes):raise RuntimeError('Maiden returned binary data instead of text')
   output.append(chunk)
   if 'stack traceback:' in chunk:raise RuntimeError('Maiden Lua error: '+''.join(output)[-2000:])
   if marker in chunk:return ''.join(output)
 def send(self,code):self._connect();self.ws.send(code.rstrip()+'\n')
 def load(self,path):
  self.send("norns.script.load("+repr(path)+")");time.sleep(8);ready=self.eval("print('__MOSAIC_ACTIVE__'..(norns.state.script or ''))")
  if path not in ready:raise RuntimeError('norns did not activate '+path+': '+ready[-1000:])
  return ready
 def close(self):
  if self.ws is not None:self.ws.close();self.ws=None
class MaidenInput:
 def __init__(self,maiden):self.maiden=maiden
 def send(self,kind,n,value):
  if kind not in ('key','enc'):raise ValueError('Norns script callbacks support only key and enc actions')
  lower=time.monotonic_ns();self.maiden.eval(f'{kind}({int(n)},{int(value)})');upper=time.monotonic_ns()
  return {'type':kind,'n':int(n),'value':int(value),'host_monotonic_ns':lower,'host_completion_ns':upper,'transport':'maiden-script-hardware-callback'}
class OutputTrace:
 """Pass-through observation at stock norns MIDI and grid driver boundaries."""
 def __init__(self,maiden):self.maiden=maiden;self.installed=False
 def install(self):
  code="if _MOSAIC_HW_ORIG_MIDI or _MOSAIC_HW_ORIG_GRID_LED then error('hardware trace already installed') end; _MOSAIC_HW_ORIG_MIDI=_norns.midi_send; _MOSAIC_HW_ORIG_GRID_LED=_norns.grid_set_led; _MOSAIC_HW_ORIG_GRID_ALL=_norns.grid_all_led; _MOSAIC_HW_ORIG_GRID_REFRESH=_norns.monome_refresh; _MOSAIC_HW_MIDI={}; _MOSAIC_HW_MIDI_REALTIME=0; _MOSAIC_HW_GRID={writes=0,refreshes=0,all=0,levels={}}; _norns.midi_send=function(dev,payload) local bytes={} if type(payload)=='table' then for i=1,#payload do bytes[i]=payload[i] end end if #bytes>1 then table.insert(_MOSAIC_HW_MIDI,{when=util.time(),device=tostring(dev),payload_type=type(payload),bytes=bytes}) else _MOSAIC_HW_MIDI_REALTIME=_MOSAIC_HW_MIDI_REALTIME+1 end return _MOSAIC_HW_ORIG_MIDI(dev,payload) end; _norns.grid_set_led=function(dev,x,y,value) _MOSAIC_HW_GRID.writes=_MOSAIC_HW_GRID.writes+1; _MOSAIC_HW_GRID.levels[x..','..y]=value; return _MOSAIC_HW_ORIG_GRID_LED(dev,x,y,value) end; _norns.grid_all_led=function(dev,value) _MOSAIC_HW_GRID.writes=_MOSAIC_HW_GRID.writes+1; _MOSAIC_HW_GRID.all=value; _MOSAIC_HW_GRID.levels={}; return _MOSAIC_HW_ORIG_GRID_ALL(dev,value) end; _norns.monome_refresh=function(dev) _MOSAIC_HW_GRID.refreshes=_MOSAIC_HW_GRID.refreshes+1; return _MOSAIC_HW_ORIG_GRID_REFRESH(dev) end"
  self.maiden.eval(code);self.installed=True
 def reset_midi(self):self.maiden.eval('_MOSAIC_HW_MIDI={}; _MOSAIC_HW_MIDI_REALTIME=0')
 def snapshot(self):
  code="print('__GRID_COUNTS__'.._MOSAIC_HW_GRID.writes..','.._MOSAIC_HW_GRID.refreshes); for y=1,8 do local row={} for x=1,16 do local value=_MOSAIC_HW_GRID.levels[x..','..y] if value==nil then value=_MOSAIC_HW_GRID.all end row[x]=value end print('__GRID_ROW__'..y..'|'..table.concat(row,',')) end; for i,e in ipairs(_MOSAIC_HW_MIDI) do print(string.format('__MIDI__%d|%.9f|%s|%s|%s',i,e.when,e.device,e.payload_type,table.concat(e.bytes,','))) end"
  output=self.maiden.eval(code);counts=re.search(r'__GRID_COUNTS__(\d+),(\d+)',output)
  if not counts:raise RuntimeError('Hardware grid trace missing')
  rows={int(y):[int(v) for v in values.split(',')] for y,values in re.findall(r'__GRID_ROW__(\d+)\|([-0-9,]+)',output)}
  if set(rows)!=set(range(1,9)) or any(len(row)!=16 for row in rows.values()):raise RuntimeError('Hardware grid trace incomplete: '+repr(output[-4000:]))
  midi=[]
  for index,when,device,payload_type,values in re.findall(r'__MIDI__(\d+)\|([0-9.]+)\|([^|]*)\|([^|]*)\|([0-9,]*)',output):
   midi.append({'index':int(index),'monotonic_seconds':float(when),'device':device,'payload_type':payload_type,'bytes':[int(v) for v in values.split(',') if v]})
  raw_grid=sum((rows[y] for y in range(1,9)),[]);physical_grid=[value&15 for value in raw_grid]
  return {'grid':physical_grid,'raw_grid':raw_grid,'grid_writes':int(counts.group(1)),'grid_refreshes':int(counts.group(2)),'midi':midi}
 def remove(self):
  if not self.installed:return
  code="if _MOSAIC_HW_ORIG_MIDI then _norns.midi_send=_MOSAIC_HW_ORIG_MIDI end; if _MOSAIC_HW_ORIG_GRID_LED then _norns.grid_set_led=_MOSAIC_HW_ORIG_GRID_LED end; if _MOSAIC_HW_ORIG_GRID_ALL then _norns.grid_all_led=_MOSAIC_HW_ORIG_GRID_ALL end; if _MOSAIC_HW_ORIG_GRID_REFRESH then _norns.monome_refresh=_MOSAIC_HW_ORIG_GRID_REFRESH end; _MOSAIC_HW_ORIG_MIDI=nil; _MOSAIC_HW_ORIG_GRID_LED=nil; _MOSAIC_HW_ORIG_GRID_ALL=nil; _MOSAIC_HW_ORIG_GRID_REFRESH=nil; print('__TRACE_REMOVED__'..debug.getinfo(_norns.midi_send).what)"
  try:
   output=self.maiden.eval(code)
   if '__TRACE_REMOVED__C' not in output:raise RuntimeError('Stock MIDI binding was not restored')
  finally:self.installed=False
def export_head(repo):
 temporary=tempfile.TemporaryDirectory();root=Path(temporary.name);archive=root/'head.tar';tree=root/'tree';tree.mkdir();subprocess.run(['git','archive','--format=tar','-o',str(archive),'HEAD'],cwd=repo,check=True)
 with tarfile.open(archive) as rows:rows.extractall(tree)
 sub=repo/'lib/nb'
 if subprocess.run(['git','rev-parse','--verify','HEAD:lib/nb'],cwd=repo,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).returncode==0:
  commit=subprocess.check_output(['git','rev-parse','HEAD:lib/nb'],cwd=repo,text=True).strip()
  if not (sub/'.git').exists() or subprocess.run(['git','cat-file','-e',commit+'^{commit}'],cwd=sub,stderr=subprocess.DEVNULL).returncode:
   raise RuntimeError('Initialize exact lib/nb gitlink before deployment: git submodule update --init lib/nb')
  subarchive=root/'nb.tar';subprocess.run(['git','archive','--format=tar','-o',str(subarchive),commit],cwd=sub,check=True);(tree/'lib/nb').mkdir(parents=True,exist_ok=True)
  with tarfile.open(subarchive) as rows:rows.extractall(tree/'lib/nb')
 manifest=[]
 for p in sorted(tree.rglob('*')):
  if p.is_file():manifest.append((hashlib.sha256(p.read_bytes()).hexdigest(),p.relative_to(tree).as_posix()))
 (root/'source.sha256').write_text(''.join(h+'  '+name+'\n' for h,name in manifest));return temporary,tree,root/'source.sha256',manifest
class Runner:
 def __init__(self,ssh,maiden,osc,out,run_id):self.ssh=ssh;self.maiden=maiden;self.osc=osc;self.out=out;self.run_id=run_id
 @property
 def remote(self):return ROOT+'/'+self.run_id
 def probe(self):
  r=self.ssh.run("""set -eu
echo '--- uname'; uname -a
echo '--- failed'; systemctl --failed --no-legend || true
echo '--- units'; systemctl list-units --type=service --all --no-legend | grep -E 'matron|crone|supercollider|norns|maiden' || true
echo '--- alsa'; if command -v aconnect >/dev/null; then aconnect -l; else echo 'UNAVAILABLE: aconnect'; fi
""");(self.out/'probe.log').write_text(r.stdout);return {'alsa_available':'UNAVAILABLE: aconnect' not in r.stdout,'grid_input':'synthetic-lua-only-or-physical','grid_led_readback':'physical-not-available'}
 def backup(self):
  r=self.remote;self.ssh.run(f"""set -eu; umask 077; mkdir -p {ROOT}; test ! -e {ROOT}/active || {{ echo 'recovery required'; exit 73; }}; mkdir {r}; echo {self.run_id} > {r}/run-id; echo {self.run_id} > {ROOT}/active.tmp; mv {ROOT}/active.tmp {ROOT}/active
+if test -e /home/we/dust/code/mosaic; then cp -a /home/we/dust/code/mosaic {r}/code-mosaic; touch {r}/had-code; fi
+if test -e /home/we/dust/data/mosaic; then cp -a /home/we/dust/data/mosaic {r}/data-mosaic; touch {r}/had-data; fi
+if test -e /home/we/dust/data/system.state; then cp -a /home/we/dust/data/system.state {r}/system.state; touch {r}/had-state; fi
+""".replace('\n+','\n'))
 def deploy(self,repo):
  self.backup();self.maiden.eval('norns.script.clear()');self.ssh.run('rm -rf /home/we/dust/data/mosaic; mkdir -p /home/we/dust/data/mosaic');temp,tree,manifest,rows=export_head(repo);self._export=temp;staging='/home/we/dust/code/.mosaic-'+self.run_id+'.staging';self.ssh.run(f'rm -rf {staging}; mkdir -p {staging}');self.ssh.rsync(tree,staging);self.ssh.push(manifest,self.remote+'/source.sha256');self.ssh.run(f"set -eu; cd {staging}; sha256sum -c {self.remote}/source.sha256; rm -rf /home/we/dust/code/mosaic; mv {staging} /home/we/dust/code/mosaic");(self.out/'source.sha256').write_text(manifest.read_text());(self.out/'load.log').write_text(self.maiden.load('/home/we/dust/code/mosaic/mosaic.lua'));return rows
 def resume(self):
  r=self.remote;result=self.ssh.run(f"""set -eu
+test "$(cat {ROOT}/active)" = {self.run_id}
+test "$(cat {r}/run-id)" = {self.run_id}
+test -f {r}/source.sha256
+cd /home/we/dust/code/mosaic
+sha256sum -c {r}/source.sha256
+""".replace('\n+','\n'));(self.out/'resume-verify.log').write_text(result.stdout);self.ssh.fetch(r+'/source.sha256',self.out/'source.sha256');active=self.maiden.eval("print('__MOSAIC_ACTIVE__'..(norns.state.script or ''))")
  if '/home/we/dust/code/mosaic/mosaic.lua' not in active:active=self.maiden.load('/home/we/dust/code/mosaic/mosaic.lua')
  (self.out/'load.log').write_text(active);return sum(1 for line in (self.out/'source.sha256').read_text().splitlines() if line.strip())
 def action(self,kind,n,value):
  if not isinstance(self.osc,SSHOSC):return self.osc.send(kind,n,value)
  # Stock ws-wrapper temporarily drops output for newly connected BUS peers
  # while a prior Maiden peer is retiring. Keep this outside musical timing.
  self.maiden.close();time.sleep(5);result=self.osc.send(kind,n,value);time.sleep(5);return result
 def channel_subpage(self):
  output=self.maiden.eval("print('__MOSAIC_SUBPAGE__'..channel_edit_page_ui.get_selected_page())");match=re.search(r'__MOSAIC_SUBPAGE__(\d+)',output)
  if not match:raise RuntimeError('Could not observe Mosaic channel subpage')
  return int(match.group(1))
 def seed_config(self,source):
  source=Path(source).resolve()
  if not source.is_dir():raise ValueError('Missing hardware config source: '+str(source))
  self.ssh.run('rm -rf /home/we/dust/data/mosaic/config; mkdir -p /home/we/dust/data/mosaic/config')
  self.ssh.rsync(source,'/home/we/dust/data/mosaic/config')
  self.maiden.send('norns.script.clear()');time.sleep(2);self.maiden.load('/home/we/dust/code/mosaic/mosaic.lua')
 def device_map_index(self,device_id,channel=1):
  if not re.fullmatch(r'[A-Za-z0-9 _./-]+',device_id):raise ValueError('Unsafe device map ID')
  output=self.maiden.eval("for i,d in ipairs(device_map.get_available_devices_for_channel("+str(int(channel))+")) do if d.id=="+repr(device_id)+" then print('__MOSAIC_DEVICE_MAP_INDEX__'..i) end end")
  match=re.search(r'__MOSAIC_DEVICE_MAP_INDEX__(\d+)',output)
  if not match:raise RuntimeError('Required device map is unavailable: '+device_id)
  return int(match.group(1))
 def grid_device(self,requested=0):
  if requested>0:return requested
  output=self.maiden.eval("for k in pairs(grid.devices) do print('__MOSAIC_GRID_ID__'..k) end");ids=[int(x) for x in re.findall(r'__MOSAIC_GRID_ID__(\d+)',output)]
  if not ids:raise RuntimeError('No connected grid in grid.devices')
  return ids[0]
 def synthetic_grid(self,device,x,y,state):return self.maiden.eval(f'_norns.grid.key({int(device)},{int(x)},{int(y)},{int(state)})')
 def screenshot(self,label):
  rel='hardware-'+self.run_id+'/'+label;self.maiden.eval("os.execute('mkdir -p '..norns.state.data..'hardware-"+self.run_id+"'); screen.export_screenshot("+repr(rel)+")");local=self.out/(label+'.png');self.ssh.fetch('/home/we/dust/data/mosaic/'+rel+'.png',local);raw=local.read_bytes()
  if raw[:8]!=b'\x89PNG\r\n\x1a\n' or len(raw)<24 or struct.unpack('!II',raw[16:24])!=(640,384):raise AssertionError('Expected 640x384 PNG screenshot')
  return {'path':local.name,'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'width':640,'height':384}
 def logs(self):
  r=self.ssh.run("systemctl --failed --no-legend || true\nfor u in $(systemctl list-units --type=service --all --no-legend | awk '/matron|crone|supercollider|norns|maiden/{print $1}'); do echo --- $u; journalctl -u $u -n 200 --no-pager || true; done\n");(self.out/'runtime.log').write_text(r.stdout)
 def reload_saved(self):
  output=self.maiden.eval("local f=io.open('/home/we/dust/data/system.state'); if f then f:close(); dofile('/home/we/dust/data/system.state'); print('__MOSAIC_SAVED__'..(norns.state.script or '')) else print('__MOSAIC_SAVED__') end");match=re.search(r'__MOSAIC_SAVED__(/[^\r\n]*)',output)
  if match and match.group(1):self.maiden.load(match.group(1))
 def restore(self):
  try:self.maiden.eval('norns.script.clear()')
  except Exception as e:(self.out/'restore-warning.txt').write_text(str(e))
  r=self.remote;self.ssh.run(f"""set -eu; test "$(cat {ROOT}/active)" = {self.run_id}; test "$(cat {r}/run-id)" = {self.run_id}; rm -rf /home/we/dust/code/mosaic /home/we/dust/data/mosaic; if test -e {r}/had-code; then mv {r}/code-mosaic /home/we/dust/code/mosaic; fi; if test -e {r}/had-data; then mv {r}/data-mosaic /home/we/dust/data/mosaic; fi; if test -e {r}/had-state; then mv {r}/system.state /home/we/dust/data/system.state; else rm -f /home/we/dust/data/system.state; fi; rm -f {ROOT}/active; rm -rf {r}""");self.reload_saved()
 def finalize(self):
  self.maiden.eval('norns.script.clear()');r=self.remote
  self.ssh.run(f"""set -eu; test "$(cat {ROOT}/active)" = {self.run_id}; test "$(cat {r}/run-id)" = {self.run_id}; rm -rf /home/we/dust/data/mosaic; if test -e {r}/had-data; then mv {r}/data-mosaic /home/we/dust/data/mosaic; fi; if test -e {r}/had-state; then cp -a {r}/system.state /home/we/dust/data/system.state; else rm -f /home/we/dust/data/system.state; fi; rm -f {ROOT}/active; rm -rf {r}""")
  receipt={'run_id':self.run_id,'kept_deployment':True,'restored_user_data_and_state':True,'filesystem_finalized':True,'reload_complete':False};write(self.out/'finalized.json',receipt)
  self.reload_saved();receipt['reload_complete']=True;write(self.out/'finalized.json',receipt)
def run_m_pat_001(r,grid_device,device_map_id):
 """Real-norns form of the registered four-note user workflow."""
 trace=OutputTrace(r.maiden);actions=[]
 tempo_output=r.maiden.eval("print('__MOSAIC_TEMPO__'..clock.get_tempo())");tempo_match=re.search(r'__MOSAIC_TEMPO__([0-9.]+)',tempo_output)
 if not tempo_match:raise RuntimeError('Could not observe norns clock tempo')
 tempo_bpm=float(tempo_match.group(1));expected_step_seconds=15/tempo_bpm
 def grid(x,y,state):
  r.synthetic_grid(grid_device,x,y,state);actions.append({'type':'grid','x':x,'y':y,'state':state,'transport':'norns-grid-key-callback'})
 def tap(x,y):grid(x,y,1);grid(x,y,0);time.sleep(.06)
 def hold_tap(first,last):
  grid(first[0],first[1],1)
  try:tap(last[0],last[1])
  finally:grid(first[0],first[1],0)
 def action(kind,n,value):actions.append(r.action(kind,n,value));time.sleep(.05)
 def wait_grid(x,y,expected,timeout=3):
  deadline=time.monotonic()+timeout;actual=None
  while time.monotonic()<deadline:
   actual=trace.snapshot()['grid'][(y-1)*16+(x-1)]
   if actual==expected:return
   time.sleep(.08)
  raise AssertionError({'grid_cell':[x,y],'expected':expected,'actual':actual})
 def play_phrase(expected):
  trace.reset_midi();tap(1,8);deadline=time.monotonic()+6;snapshot=None
  while time.monotonic()<deadline:
   snapshot=trace.snapshot();notes=[e for e in snapshot['midi'] if len(e['bytes'])>=3 and 144<=e['bytes'][0]<=159 and e['bytes'][2]>0]
   if len(notes)>=13:break
   time.sleep(.08)
  else:raise AssertionError('Timed out waiting for three complete four-note phrases')
  tap(1,8);time.sleep(.3);snapshot=trace.snapshot();notes=[e for e in snapshot['midi'] if len(e['bytes'])>=3 and 144<=e['bytes'][0]<=159 and e['bytes'][2]>0]
  actual=[e['bytes'] for e in notes];wanted=[expected[i%len(expected)] for i in range(len(actual))]
  assert len(actual)>=13 and actual==wanted,{'expected':wanted,'actual':actual}
  intervals=[notes[i+1]['monotonic_seconds']-notes[i]['monotonic_seconds'] for i in range(12)]
  assert all(abs(value-expected_step_seconds)<=.02 for value in intervals),{'tempo_bpm':tempo_bpm,'expected_seconds':expected_step_seconds,'actual_seconds':intervals}
  ons={};offs={}
  for event in snapshot['midi']:
   b=event['bytes']
   if len(b)<3:continue
   key=(b[0]&15,b[1])
   if 144<=b[0]<=159 and b[2]>0:ons[key]=ons.get(key,0)+1
   elif 128<=b[0]<=143 or (144<=b[0]<=159 and b[2]==0):offs[key]=offs.get(key,0)+1
  assert all(offs.get(key,0)>=count for key,count in ons.items()),{'note_ons':ons,'note_offs':offs}
  return {'expected_cycle':expected,'captured_note_ons':actual,'tempo_bpm':tempo_bpm,'expected_step_seconds':expected_step_seconds,'first_twelve_intervals_seconds':intervals,'trace':snapshot}
 trace.install()
 try:
  r.maiden.eval("params:set('new',1); fn.dirty_screen(true); fn.dirty_grid(true)");time.sleep(.5)
  tap(4,8);tap(3,8)
  subpage=r.channel_subpage()
  while subpage<5:action('enc',1,1);subpage=r.channel_subpage()
  while subpage>5:action('enc',1,-1);subpage=r.channel_subpage()
  assert subpage==5,'Encoder navigation did not select Device Config'
  for _ in range(r.device_map_index(device_map_id)-1):action('enc',3,1)
  action('key',3,1);action('key',3,0)
  tap(5,8)
  for x in range(1,5):tap(x,4)
  tap(5,8)
  for x,y in ((1,7),(2,6),(3,5),(4,4)):tap(x,y)
  tap(5,8)
  for x,y in ((1,1),(2,2),(3,3),(4,4)):tap(x,y)
  tap(3,8);tap(1,2);hold_tap((1,4),(4,4))
  authored=r.screenshot('m-pat-001-authored');wait_grid(1,2,15)
  first=play_phrase([[144,60,127],[144,62,117],[144,64,107],[144,65,97]])
  tap(5,8);tap(5,8);tap(4,3);edited=trace.snapshot()
  assert edited['grid'][(3-1)*16+(4-1)]==12,'Edited note LED at grid 4,3 was not level 12'
  second=play_phrase([[144,60,127],[144,62,117],[144,64,107],[144,67,97]])
  levels=set();deadline=time.monotonic()+3
  while time.monotonic()<deadline and not {2,4}.issubset(levels):
   levels.add(trace.snapshot()['grid'][0]);time.sleep(.08)
  assert {2,4}.issubset(levels),{'selected_pattern_blink_levels':sorted(levels)}
  finished=r.screenshot('m-pat-001-finished')
  return {'case':'M-PAT-001','actions':actions,'screens':[authored,finished],'screen_changed':authored['sha256']!=finished['sha256'],'configured_grid_observed':True,'edited_grid_observed':True,'selected_pattern_blink_levels':[2,4],'tempo_bpm':tempo_bpm,'expected_step_seconds':expected_step_seconds,'phrases':[first,second],'physical_grid_driver_commands_observed':True,'physical_grid_led_photons_observed':False,'midi_driver_boundary_observed':True}
 finally:trace.remove()

def main(argv=None):
 p=argparse.ArgumentParser()
 p.add_argument('command',choices=['probe','workflow','resume','case','restore','finalize'])
 p.add_argument('--host',required=True);p.add_argument('--ssh-option',action='append',default=[])
 p.add_argument('--maiden-url',required=True);p.add_argument('--nanomsg-library',default='libnanomsg.so.5')
 p.add_argument('--websocket-wheel',help='path to a pinned websockets wheel; selects official Maiden WebSocket framing')
 p.add_argument('--maiden-timeout',type=float,default=120);p.add_argument('--osc-host',required=True);p.add_argument('--osc-port',type=int,default=10111)
 p.add_argument('--osc-via-ssh',action='store_true',help='send stock remote OSC from norns loopback over the existing SSH transport')
 p.add_argument('--maiden-input',action='store_true',help='invoke the script hardware callbacks after stock norns encoder processing')
 p.add_argument('--source',default=str(REPO));p.add_argument('--artifacts',required=True);p.add_argument('--run-id',required=True)
 p.add_argument('--synthetic-grid',action='store_true');p.add_argument('--grid-device-id',type=int,default=0,help='stock grid.devices ID; 0 auto-discovers the first connected grid')
 p.add_argument('--case',dest='case_id',choices=['M-PAT-001']);p.add_argument('--config-source');p.add_argument('--device-map-id',default='emu-test')
 a=p.parse_args(argv)
 if not a.run_id.replace('-','').isalnum():p.error('unsafe run ID')
 if a.osc_via_ssh and a.maiden_input:p.error('choose only one alternate input transport')
 if a.command=='case' and (not a.case_id or not a.maiden_input or not a.synthetic_grid):p.error('case requires --case, --maiden-input and --synthetic-grid')
 out=Path(a.artifacts).resolve();out.mkdir(parents=True,exist_ok=False)
 ssh=SSH(a.host,a.ssh_option)
 maiden=WebSocketMaiden(a.maiden_url,a.websocket_wheel,int(a.maiden_timeout*1000)) if a.websocket_wheel else Maiden(a.maiden_url,a.nanomsg_library,int(a.maiden_timeout*1000))
 osc=MaidenInput(maiden) if a.maiden_input else SSHOSC(ssh,a.osc_port) if a.osc_via_ssh else OSC(a.osc_host,a.osc_port)
 r=Runner(ssh,maiden,osc,out,a.run_id);failure=None
 try:
  caps=r.probe()
  if a.command in ('workflow','resume','case'):
   source_files=len(r.deploy(Path(a.source).resolve())) if a.command=='workflow' else r.resume()
   if a.command=='case':
    if a.config_source:r.seed_config(a.config_source)
    evidence=run_m_pat_001(r,r.grid_device(a.grid_device_id),a.device_map_id);r.logs()
    evidence.update({'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.source,text=True).strip(),'source_files':source_files,'resumed_after_interruption':True,'capabilities':caps,'campaign_complete':False})
    write(out/'evidence.json',evidence)
   else:
    grid_device=None;synthetic=None
    if a.synthetic_grid:grid_device=r.grid_device(a.grid_device_id);r.synthetic_grid(grid_device,3,8,1);r.synthetic_grid(grid_device,3,8,0);time.sleep(.1)
    channel_subpage=r.channel_subpage();encoder_delta=1 if channel_subpage==1 else -1;before=r.screenshot('before-controls');actions=[r.action('enc',1,encoder_delta)];time.sleep(.5);after_encoder=r.screenshot('after-encoder');assert before['sha256']!=after_encoder['sha256'],'Encoder one did not change the visible channel subpage';actions.extend([r.action('key',2,1),r.action('key',2,0)])
    if a.synthetic_grid:synthetic=r.synthetic_grid(grid_device,5,8,1)+r.synthetic_grid(grid_device,5,8,0)
    time.sleep(.25);after=r.screenshot('after-controls');assert before['sha256']!=after['sha256'],'Controls produced no changed screen';r.logs();write(out/'evidence.json',{'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.source,text=True).strip(),'source_files':source_files,'resumed_after_interruption':a.command=='resume','capabilities':caps,'actions':actions,'screens':[before,after_encoder,after],'screen_changed':True,'synthetic_grid':bool(a.synthetic_grid),'synthetic_grid_device':grid_device,'physical_grid_input_skipped':True,'grid_led_readback_skipped':True,'campaign_complete':False})
  elif a.command=='restore':r.restore()
  elif a.command=='finalize':r.finalize()
  else:write(out/'capabilities.json',caps)
 except Exception as e:failure=type(e).__name__+': '+str(e);raise
 finally:maiden.close();write(out/'run.json',{'run_id':a.run_id,'command':a.command,'case':a.case_id,'failure':failure})
 return 0
if __name__=='__main__':sys.exit(main())

#!/usr/bin/env python3
"""Exclusive, reversible stock-norns smoke runner; credentials stay external."""
import argparse,ctypes,hashlib,json,re,socket,struct,subprocess,sys,tarfile,tempfile,time
from pathlib import Path
from hardware_driver import hardware_applicability,run_hardware_case
from hardware_performance import CASES as HARDWARE_PERFORMANCE_CASES,run_hardware_performance
REPO=Path(__file__).resolve().parents[2];ROOT='/home/we/.cache/mosaic-real-norns'
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def maiden_timeout(output):return TimeoutError('Maiden marker not observed; output tail: '+''.join(output)[-2000:])
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
  """Copy a local tree into an existing empty remote directory (tar stream; never deletes)."""
  import io,shlex;buffer=io.BytesIO()
  with tarfile.open(fileobj=buffer,mode='w') as archive:archive.add(str(source),arcname='.')
  subprocess.run(['ssh',*self.options,self.host,'set -eu; test -d '+shlex.quote(dest)+'; test -z "$(ls -A '+shlex.quote(dest)+')"; tar -C '+shlex.quote(dest)+' -xf -'],input=buffer.getvalue(),stdout=subprocess.DEVNULL,check=True)
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
 def eval(self,code,allow_lua_error=False):
  marker='__MOSAIC_HW_'+hashlib.sha256((code+str(time.monotonic_ns())).encode()).hexdigest()[:16]+'__';payload=(code.rstrip()+"; print('"+marker+"')\n").encode()+b'\0';self._send(payload);output=[]
  while True:
   received=ctypes.create_string_buffer(65536);size=self.nn.nn_recv(self.fd,received,len(received),0)
   if size<0:raise maiden_timeout(output)
   chunk=received.raw[:size].decode(errors='replace');output.append(chunk)
   if 'stack traceback:' in chunk and not allow_lua_error:raise RuntimeError('Maiden Lua error: '+''.join(output)[-2000:])
   if marker in chunk:return ''.join(output)
 def send(self,code):self._send((code.rstrip()+'\n').encode()+b'\0');time.sleep(.25)
 def load(self,path,allow_lua_error=False):
  self.send("norns.script.load("+repr(path)+")");time.sleep(8);ready=self.eval("print('__MOSAIC_ACTIVE__'..(norns.state.script or ''))",allow_lua_error=allow_lua_error)
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
 def eval(self,code,allow_lua_error=False):
  self._connect();marker='__MOSAIC_HW_'+hashlib.sha256((code+str(time.monotonic_ns())).encode()).hexdigest()[:16]+'__';self.ws.send(code.rstrip()+"; print('"+marker+"')\n");output=[]
  while True:
   try:chunk=self.ws.recv(timeout=self.timeout)
   except TimeoutError:raise maiden_timeout(output)
   if isinstance(chunk,bytes):raise RuntimeError('Maiden returned binary data instead of text')
   output.append(chunk)
   if 'stack traceback:' in chunk and not allow_lua_error:raise RuntimeError('Maiden Lua error: '+''.join(output)[-2000:])
   if marker in chunk:return ''.join(output)
 def send(self,code):self._connect();self.ws.send(code.rstrip()+'\n')
 def load(self,path,allow_lua_error=False):
  self.send("norns.script.load("+repr(path)+")");time.sleep(8);ready=self.eval("print('__MOSAIC_ACTIVE__'..(norns.state.script or ''))",allow_lua_error=allow_lua_error)
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
 def install(self,allow_lua_error=False):
  code="if _MOSAIC_HW_ORIG_MIDI or _MOSAIC_HW_ORIG_GRID_LED then error('hardware trace already installed') end; do local original_midi=_norns.midi_send; local original_grid_led=_norns.grid_set_led; local original_grid_all=_norns.grid_all_led; local original_grid_refresh=_norns.monome_refresh; local midi_state={}; local function midi_port(dev) local found=0 for i,v in ipairs(midi.vports or {}) do if v.device and v.device.dev==dev then if found~=0 then return 0 end found=i end end return found end; local realtime_state={count=0}; local grid_state={writes=0,refreshes=0,all=0,levels={}}; _MOSAIC_HW_ORIG_MIDI=original_midi; _MOSAIC_HW_ORIG_GRID_LED=original_grid_led; _MOSAIC_HW_ORIG_GRID_ALL=original_grid_all; _MOSAIC_HW_ORIG_GRID_REFRESH=original_grid_refresh; _MOSAIC_HW_MIDI=midi_state; _MOSAIC_HW_MIDI_REALTIME=realtime_state; _MOSAIC_HW_GRID=grid_state; _norns.midi_send=function(dev,payload,...) local bytes={} if type(payload)=='table' then for i=1,#payload do bytes[i]=payload[i] end end if #bytes>1 then table.insert(midi_state,{when=util.time(),port=midi_port(dev),device=tostring(dev),payload_type=type(payload),bytes=bytes}) else realtime_state.count=realtime_state.count+1 end return original_midi(dev,payload,...) end; _norns.grid_set_led=function(dev,x,y,value,rel,...) grid_state.writes=grid_state.writes+1; local key=x..','..y; if rel then local prev=grid_state.levels[key]; if prev==nil then prev=grid_state.all end; grid_state.levels[key]=math.max(0,math.min(15,prev+value)) else grid_state.levels[key]=value end; return original_grid_led(dev,x,y,value,rel,...) end; _norns.grid_all_led=function(dev,value,rel,...) grid_state.writes=grid_state.writes+1; if rel then for k,v in pairs(grid_state.levels) do grid_state.levels[k]=math.max(0,math.min(15,v+value)) end; grid_state.all=math.max(0,math.min(15,grid_state.all+value)) else grid_state.all=value; grid_state.levels={} end; return original_grid_all(dev,value,rel,...) end; _norns.monome_refresh=function(dev,...) grid_state.refreshes=grid_state.refreshes+1; return original_grid_refresh(dev,...) end end"
  self.installed=True
  try:return self.maiden.eval(code,allow_lua_error=allow_lua_error)
  except BaseException as install_error:
   try:self.remove(allow_lua_error=True)
   except Exception as cleanup_error:raise RuntimeError('Hardware trace installation failed and cleanup could not be confirmed: '+str(cleanup_error)) from install_error
   raise
 def reset_midi(self,allow_lua_error=False):return self.maiden.eval('for i=#_MOSAIC_HW_MIDI,1,-1 do _MOSAIC_HW_MIDI[i]=nil end; _MOSAIC_HW_MIDI_REALTIME.count=0',allow_lua_error=allow_lua_error)
 def reset(self,allow_lua_error=False):return self.maiden.eval('for i=#_MOSAIC_HW_MIDI,1,-1 do _MOSAIC_HW_MIDI[i]=nil end; _MOSAIC_HW_MIDI_REALTIME.count=0; _MOSAIC_HW_GRID.writes=0; _MOSAIC_HW_GRID.refreshes=0; _MOSAIC_HW_GRID.all=0; _MOSAIC_HW_GRID.levels={}',allow_lua_error=allow_lua_error)
 def snapshot(self,allow_lua_error=False,return_output=False):
  code="print('__GRID_COUNTS__'.._MOSAIC_HW_GRID.writes..','.._MOSAIC_HW_GRID.refreshes); for y=1,8 do local row={} for x=1,16 do local value=_MOSAIC_HW_GRID.levels[x..','..y] if value==nil then value=_MOSAIC_HW_GRID.all end row[x]=value end print('__GRID_ROW__'..y..'|'..table.concat(row,',')) end; for i,e in ipairs(_MOSAIC_HW_MIDI) do print(string.format('__MIDI__%d|%.9f|%d|%s|%s|%s',i,e.when,e.port,e.device,e.payload_type,table.concat(e.bytes,','))) end"
  output=self.maiden.eval(code,allow_lua_error=allow_lua_error);counts=re.search(r'__GRID_COUNTS__(\d+),(\d+)',output)
  if not counts:raise RuntimeError('Hardware grid trace missing')
  rows={int(y):[int(v) for v in values.split(',')] for y,values in re.findall(r'__GRID_ROW__(\d+)\|([-0-9,]+)',output)}
  if set(rows)!=set(range(1,9)) or any(len(row)!=16 for row in rows.values()):raise RuntimeError('Hardware grid trace incomplete: '+repr(output[-4000:]))
  midi=[]
  for index,when,port,device,payload_type,values in re.findall(r'__MIDI__(\d+)\|([0-9.]+)\|(\d+)\|([^|]*)\|([^|]*)\|([0-9,]*)',output):
   midi.append({'index':int(index),'monotonic_seconds':float(when),'port':int(port),'device':device,'payload_type':payload_type,'bytes':[int(v) for v in values.split(',') if v]})
  raw_grid=sum((rows[y] for y in range(1,9)),[]);physical_grid=[value&15 for value in raw_grid]
  result={'grid':physical_grid,'raw_grid':raw_grid,'grid_writes':int(counts.group(1)),'grid_refreshes':int(counts.group(2)),'midi':midi}
  return (result,output) if return_output else result
 def remove(self,allow_lua_error=False):
  if not self.installed:return ''
  code="if _MOSAIC_HW_ORIG_MIDI then _norns.midi_send=_MOSAIC_HW_ORIG_MIDI end; if _MOSAIC_HW_ORIG_GRID_LED then _norns.grid_set_led=_MOSAIC_HW_ORIG_GRID_LED end; if _MOSAIC_HW_ORIG_GRID_ALL then _norns.grid_all_led=_MOSAIC_HW_ORIG_GRID_ALL end; if _MOSAIC_HW_ORIG_GRID_REFRESH then _norns.monome_refresh=_MOSAIC_HW_ORIG_GRID_REFRESH end; _MOSAIC_HW_ORIG_MIDI=nil; _MOSAIC_HW_ORIG_GRID_LED=nil; _MOSAIC_HW_ORIG_GRID_ALL=nil; _MOSAIC_HW_ORIG_GRID_REFRESH=nil; print('__TRACE_REMOVED__'..debug.getinfo(_norns.midi_send).what)"
  output=self.maiden.eval(code,allow_lua_error=allow_lua_error)
  if '__TRACE_REMOVED__C' not in output:raise RuntimeError('Stock MIDI binding was not restored')
  self.installed=False
  return output
class ExpectedClockErrorMaiden:
 """Record stock queued-resume Lua errors instead of aborting; any other Lua error still raises."""
 def __init__(self,maiden,runner,label):self.maiden=maiden;self.runner=runner;self.label=label
 def eval(self,code,allow_lua_error=False):return self.runner.validate_clock_output(self.maiden.eval(code,allow_lua_error=True),self.label)
 def send(self,code):return self.maiden.send(code)
 def load(self,path,allow_lua_error=False):return self.runner.validate_clock_output(self.maiden.load(path,allow_lua_error=True),self.label+'-load')
 def close(self):return self.maiden.close()
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
 def __init__(self,ssh,maiden,osc,out,run_id):self.ssh=ssh;self.maiden=maiden;self.osc=osc;self.out=out;self.run_id=run_id;self.clock_error_drains=[]
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
+if test -e /home/we/dust/code/mosaic; then (cd /home/we/dust/code/mosaic && find . -type f -print0 | sort -z | xargs -0 sha256sum) > {r}/installed-before.sha256; touch {r}/had-code; fi
+if test -e /home/we/dust/data/mosaic; then mv /home/we/dust/data/mosaic {r}/data-mosaic; touch {r}/had-data; fi
+if test -e /home/we/dust/data/system.state; then cp -a /home/we/dust/data/system.state {r}/system.state; touch {r}/had-state; fi
+""".replace('\n+','\n'))
 def deploy(self,repo):
  self.maiden.eval('norns.script.clear()');self.backup();self.ssh.run('set -eu; test ! -e /home/we/dust/data/mosaic; mkdir -p /home/we/dust/data/mosaic');temp,tree,manifest,rows=export_head(repo);self._export=temp;staging='/home/we/dust/code/.mosaic-'+self.run_id+'.staging';self.ssh.run(f'set -eu; test ! -e {staging}; mkdir -p {staging}');self.ssh.rsync(tree,staging);self.ssh.push(manifest,self.remote+'/source.sha256');self.ssh.run(f"set -eu; cd {staging}; sha256sum --quiet -c {self.remote}/source.sha256; if test -e /home/we/dust/code/mosaic; then mv /home/we/dust/code/mosaic {self.remote}/code-mosaic; fi; mv {staging} /home/we/dust/code/mosaic; cd /home/we/dust/code/mosaic; find . -type f -print0 | sort -z | xargs -0 sha256sum > {self.remote}/installed-after.sha256");self.ssh.fetch(self.remote+'/installed-after.sha256',self.out/'installed-after.sha256')
  if self.ssh.run(f'test -e {self.remote}/installed-before.sha256 && cat {self.remote}/installed-before.sha256 || true').stdout:self.ssh.fetch(self.remote+'/installed-before.sha256',self.out/'installed-before.sha256')
  (self.out/'source.sha256').write_text(manifest.read_text());(self.out/'load.log').write_text(self.maiden.load('/home/we/dust/code/mosaic/mosaic.lua',allow_lua_error=True));return rows
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
  self.ssh.run('set -eu; test ! -e /home/we/dust/data/mosaic/config; mkdir -p /home/we/dust/data/mosaic/config')
  self.ssh.rsync(source,'/home/we/dust/data/mosaic/config')
  self.maiden.send('norns.script.clear()');time.sleep(2);self.maiden.load('/home/we/dust/code/mosaic/mosaic.lua',allow_lua_error=True)
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
 def remote_sha256(self,path):
  result=self.ssh.run('sha256sum -- '+path);match=re.search(r'\b([0-9a-f]{64})\b',result.stdout)
  if not match:raise RuntimeError('Could not hash remote file: '+path)
  return match.group(1)
 def install_clock_file(self,source,label,path='/home/we/norns/lua/core/clock.lua'):
  if path!='/home/we/norns/lua/core/clock.lua':raise ValueError('Unexpected stock clock path')
  source=Path(source);wanted=hashlib.sha256(source.read_bytes()).hexdigest();staging=self.remote+'-'+label+'.clock.lua'
  self.ssh.run('mkdir -p '+ROOT);self.ssh.push(source,staging);self.ssh.run('set -eu\nchmod --reference='+path+' '+staging+'\nmv '+staging+' '+path)
  actual=self.remote_sha256(path)
  if actual!=wanted:raise RuntimeError('Remote clock hash mismatch after '+label)
  return actual
 def clock_cancel_probe(self,label):
  trace=OutputTrace(self.maiden);failure=None;snapshot=None;expected_errors=0
  def drain(output,phase):
   nonlocal expected_errors
   self.validate_clock_output(output,phase);expected_errors+=output.count('stack traceback:');return output
  try:
   try:drain(trace.install(allow_lua_error=True),'install-'+label+'-trace')
   except Exception as error:failure=type(error).__name__+': '+str(error)
   if failure is None:
    try:drain(trace.reset_midi(allow_lua_error=True),'reset-'+label+'-trace')
    except Exception as error:failure=type(error).__name__+': '+str(error)
   if failure is None:
    code="local probe_midi=midi.connect(1); for i=1,24 do local id=clock.run(function() clock.sleep(0.001); error('cancelled native clock resumed') end); local finish=util.time()+0.008; while util.time()<finish do end; clock.cancel(id) end; local ok=pcall(clock.resume,99999999); assert(not ok,'unknown clock identity was silently ignored'); clock.run(function() clock.sleep(0.05); probe_midi:cc(78,1,1) end); probe_midi:cc(77,1,1)"
    try:drain(self.maiden.eval(code,allow_lua_error=True),'exercise-'+label);time.sleep(.2);drain(self.maiden.eval("print('__CLOCK_CANCEL_SETTLED__')",allow_lua_error=True),'settle-'+label)
    except Exception as error:failure=type(error).__name__+': '+str(error)
   if failure is None:
    try:snapshot,output=trace.snapshot(allow_lua_error=True,return_output=True);drain(output,'snapshot-'+label+'-trace')
    except Exception as error:failure=type(error).__name__+': '+str(error)
  finally:
   try:drain(trace.remove(allow_lua_error=True),'remove-'+label+'-trace')
   except Exception as error:failure=failure or type(error).__name__+': '+str(error)
  if expected_errors:failure=failure or 'Expected stock queued-resume Lua errors observed: '+str(expected_errors)
  messages=[event['bytes'] for event in (snapshot or {}).get('midi',[])]
  return {'label':label,'passed':failure is None and expected_errors==0 and [176,77,1] in messages and [176,78,1] in messages,'failure':failure,'expected_queued_resume_errors':expected_errors,'midi':messages}
 def validate_clock_output(self,output,label):
  count=output.count('stack traceback:')
  for match in re.finditer(r'stack traceback:',output):
   prefix=output[max(0,match.start()-1000):match.start()]
   if "bad argument #1 to 'resume' (thread expected" not in prefix:
    raise RuntimeError('Unexpected Lua error while '+label+': '+output[-2000:])
  if count:self.clock_error_drains.append({'phase':label,'expected_queued_resume_errors':count})
  return output
 def clock_control_eval(self,code,label):
  return self.validate_clock_output(self.maiden.eval(code,allow_lua_error=True),label)
 def clock_control_load(self,path,label):
  return self.validate_clock_output(self.maiden.load(path,allow_lua_error=True),label)
 def clock_cancel_comparison(self,candidate,path='/home/we/norns/lua/core/clock.lua'):
  candidate=Path(candidate).resolve()
  if not candidate.is_file():raise ValueError('Missing clock candidate: '+str(candidate))
  stock=self.out/'stock-clock.lua';stock_hash=self.remote_sha256(path);self.ssh.fetch(path,stock)
  if hashlib.sha256(stock.read_bytes()).hexdigest()!=stock_hash:raise RuntimeError('Fetched stock clock hash mismatch')
  active_output=self.maiden.eval("print('__MOSAIC_ACTIVE__'..(norns.state.script or ''))");match=re.search(r'__MOSAIC_ACTIVE__([^\r\n]*)',active_output);active=match.group(1) if match else ''
  phases=[];restored_hash=None;self.clock_error_drains=[]
  try:
   self.clock_control_eval('norns.script.clear()','clear-before-stock-baseline');self.clock_control_eval('clock=dofile('+repr(path)+')','load-stock-baseline');phases.append(self.clock_cancel_probe('stock-baseline'))
   candidate_hash=self.install_clock_file(candidate,'candidate',path);self.clock_control_eval('clock=dofile('+repr(path)+')','load-temporary-candidate');phases.append(self.clock_cancel_probe('temporary-candidate'))
  finally:
   try:
    restored_hash=self.install_clock_file(stock,'stock-restore',path);self.clock_control_eval('clock=dofile('+repr(path)+')','reload-restored-stock')
    if active:self.clock_control_load(active,'reload-prior-active-script')
   finally:self.ssh.run('rm -f '+self.remote+'-candidate.clock.lua '+self.remote+'-stock-restore.clock.lua')
  return {'schema_version':1,'kind':'stock-clock-cancel-queued-resume','clock_path':path,'stock_sha256':stock_hash,'candidate_sha256':candidate_hash if 'candidate_hash' in locals() else None,'restored_sha256':restored_hash,'stock_restored':restored_hash==stock_hash,'phases':phases,'expected_error_drains':self.clock_error_drains,'no_reboot_or_jack_restart':True,'active_script':active,'active_script_reloaded':bool(active)}
 def logs(self):
  r=self.ssh.run("systemctl --failed --no-legend || true\nfor u in $(systemctl list-units --type=service --all --no-legend | awk '/matron|crone|supercollider|norns|maiden/{print $1}'); do echo --- $u; journalctl -u $u -n 200 --no-pager || true; done\n");(self.out/'runtime.log').write_text(r.stdout)
 def reload_saved(self):
  output=self.maiden.eval("local f=io.open('/home/we/dust/data/system.state'); if f then f:close(); dofile('/home/we/dust/data/system.state'); print('__MOSAIC_SAVED__'..(norns.state.script or '')) else print('__MOSAIC_SAVED__') end");match=re.search(r'__MOSAIC_SAVED__(/[^\r\n]*)',output)
  if match and match.group(1):self.maiden.load(match.group(1))
 def restore(self):
  try:self.maiden.eval('norns.script.clear()')
  except Exception as e:(self.out/'restore-warning.txt').write_text(str(e))
  r=self.remote;self.ssh.run(f"""set -eu; test "$(cat {ROOT}/active)" = {self.run_id}; test "$(cat {r}/run-id)" = {self.run_id}; K={ROOT}/kept-{self.run_id}; mkdir $K; if test -e /home/we/dust/data/mosaic; then mv /home/we/dust/data/mosaic $K/test-data; fi; if test -e {r}/code-mosaic; then mv /home/we/dust/code/mosaic $K/tested-code; mv {r}/code-mosaic /home/we/dust/code/mosaic; fi; if test -e {r}/had-data; then mv {r}/data-mosaic /home/we/dust/data/mosaic; fi; if test -e {r}/had-state; then mv {r}/system.state /home/we/dust/data/system.state; fi; rm -f {ROOT}/active; mv {r} $K/recovery""");self.reload_saved()
 def finalize(self):
  self.maiden.eval('norns.script.clear()');r=self.remote
  self.ssh.run(f"""set -eu; test "$(cat {ROOT}/active)" = {self.run_id}; test "$(cat {r}/run-id)" = {self.run_id}; K={ROOT}/kept-{self.run_id}; mkdir $K; if test -e /home/we/dust/data/mosaic; then mv /home/we/dust/data/mosaic $K/test-data; fi; if test -e {r}/had-data; then mv {r}/data-mosaic /home/we/dust/data/mosaic; fi; if test -e {r}/had-state; then cp -a {r}/system.state /home/we/dust/data/system.state; fi; rm -f {ROOT}/active; mv {r} $K/recovery""")
  receipt={'run_id':self.run_id,'kept_deployment':True,'restored_user_data_and_state':True,'filesystem_finalized':True,'reload_complete':False};write(self.out/'finalized.json',receipt)
  self.reload_saved();receipt['reload_complete']=True;write(self.out/'finalized.json',receipt)
def run_m_pat_001(r,grid_device,device_map_id):
 """Compatibility entry point; the recipe remains registered only in cases.py."""
 return run_hardware_case(r,'M-PAT-001',grid_device,device_map_id,OutputTrace(r.maiden))
def main(argv=None):
 p=argparse.ArgumentParser()
 p.add_argument('command',choices=['applicability','probe','workflow','resume','case','performance','clock-cancel','restore','finalize'])
 p.add_argument('--host');p.add_argument('--ssh-option',action='append',default=[])
 p.add_argument('--maiden-url');p.add_argument('--nanomsg-library',default='libnanomsg.so.5')
 p.add_argument('--websocket-wheel',help='path to a pinned websockets wheel; selects official Maiden WebSocket framing')
 p.add_argument('--maiden-timeout',type=float,default=120);p.add_argument('--osc-host');p.add_argument('--osc-port',type=int,default=10111)
 p.add_argument('--osc-via-ssh',action='store_true',help='send stock remote OSC from norns loopback over the existing SSH transport')
 p.add_argument('--maiden-input',action='store_true',help='invoke the script hardware callbacks after stock norns encoder processing')
 p.add_argument('--source',default=str(REPO));p.add_argument('--artifacts');p.add_argument('--run-id')
 p.add_argument('--synthetic-grid',action='store_true');p.add_argument('--grid-device-id',type=int,default=0,help='stock grid.devices ID; 0 auto-discovers the first connected grid')
 p.add_argument('--case',dest='case_id',choices=['M-PAT-001']);p.add_argument('--config-source');p.add_argument('--device-map-id',default='emu-test')
 p.add_argument('--performance-case',choices=sorted(HARDWARE_PERFORMANCE_CASES))
 p.add_argument('--stock-clock-errors',choices=['fail','record'],default='fail',help='record: count stock queued-resume errors (clock.lua thread expected) instead of aborting')
 p.add_argument('--tempo',type=float,help='set params clock_tempo for the run; system.state restoration returns the prior value')
 p.add_argument('--lua-timing-trace',action='store_true',help='diagnostic: record Lua redraw, display update, grid redraw, scheduler and clock resume calls over 1 ms');p.add_argument('--no-resource-sampler',action='store_true',help='diagnostic: omit the on-device resource sampler');p.add_argument('--native-screen-trace',action='store_true',help='diagnostic: with --lua-timing-trace, total native screen text and font-size time per redraw');p.add_argument('--redraw-count-trace',action='store_true',help='diagnostic: with --lua-timing-trace, count Lua VM instructions (per 100) in every redraw');p.add_argument('--thread-sampler',help='path to a per-thread schedstat sampler (monome-emulator scripts/calibration/thread_sampler.py)')
 p.add_argument('--measured-windows',type=int,default=1,help='play/stop windows measured on one built project')
 p.add_argument('--clock-cancel-candidate',help='complete temporary replacement for /home/we/norns/lua/core/clock.lua')
 a=p.parse_args(argv)
 if a.command=='applicability':
  from cases import CASES
  print(json.dumps(hardware_applicability(CASES),indent=2));return 0
 required=('host','maiden_url','artifacts','run_id') if a.command=='clock-cancel' else ('host','maiden_url','osc_host','artifacts','run_id')
 missing=[name for name in required if not getattr(a,name)]
 if missing:p.error('required for hardware commands: '+', '.join('--'+name.replace('_','-') for name in missing))
 if not a.run_id.replace('-','').isalnum():p.error('unsafe run ID')
 if a.osc_via_ssh and a.maiden_input:p.error('choose only one alternate input transport')
 if a.command=='case' and (not a.case_id or not a.maiden_input or not a.synthetic_grid):p.error('case requires --case, --maiden-input and --synthetic-grid')
 if a.command=='performance' and (not a.performance_case or not a.config_source or not a.maiden_input or not a.synthetic_grid):p.error('performance requires --performance-case, --config-source, --maiden-input and --synthetic-grid')
 if a.command=='clock-cancel' and not a.clock_cancel_candidate:p.error('clock-cancel requires --clock-cancel-candidate')
 out=Path(a.artifacts).resolve();out.mkdir(parents=True,exist_ok=False)
 ssh=SSH(a.host,a.ssh_option)
 maiden=WebSocketMaiden(a.maiden_url,a.websocket_wheel,int(a.maiden_timeout*1000)) if a.websocket_wheel else Maiden(a.maiden_url,a.nanomsg_library,int(a.maiden_timeout*1000))
 osc=MaidenInput(maiden) if a.maiden_input else SSHOSC(ssh,a.osc_port) if a.osc_via_ssh else OSC(a.osc_host,a.osc_port)
 r=Runner(ssh,maiden,osc,out,a.run_id);failure=None
 try:
  caps=r.probe()
  if a.command=='clock-cancel':
   evidence=r.clock_cancel_comparison(a.clock_cancel_candidate);evidence['capabilities']=caps;write(out/'clock-cancel.json',evidence)
   if not evidence['stock_restored'] or not evidence['phases'][-1]['passed']:raise AssertionError('Clock candidate failed or stock clock was not restored')
  elif a.command in ('workflow','resume','case','performance'):
   source_files=len(r.deploy(Path(a.source).resolve())) if a.command in ('workflow','performance') else r.resume()
   if a.command in ('case','performance'):
    if a.stock_clock_errors=='record':r.maiden=ExpectedClockErrorMaiden(r.maiden,r,a.command)
    if a.config_source:r.seed_config(a.config_source)
    if a.tempo:
     before=r.maiden.eval("print('__TEMPO_BEFORE__'..clock.get_tempo())");r.maiden.eval('params:set("clock_tempo",%r)'%float(a.tempo));time.sleep(.5)
     after=r.maiden.eval("print('__TEMPO_AFTER__'..clock.get_tempo())");write(out/'tempo.json',{'requested':a.tempo,'before':re.findall(r'__TEMPO_BEFORE__([0-9.]+)',before),'after':re.findall(r'__TEMPO_AFTER__([0-9.]+)',after)})
    evidence=run_hardware_case(r,a.case_id,r.grid_device(a.grid_device_id),a.device_map_id,OutputTrace(r.maiden)) if a.command=='case' else run_hardware_performance(r,a.performance_case,r.grid_device(a.grid_device_id),a.device_map_id,a.source,thread_sampler=a.thread_sampler,windows=a.measured_windows,timing_trace=a.lua_timing_trace,resource_sampler=not a.no_resource_sampler,native_screen_trace=a.native_screen_trace,redraw_count_trace=a.redraw_count_trace)
    r.logs()
    evidence['clock_error_drains']=r.clock_error_drains;evidence['stock_clock_errors_mode']=a.stock_clock_errors
    evidence.update({'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.source,text=True).strip(),'source_files':source_files,'resumed_after_interruption':True,'capabilities':caps,'campaign_complete':False})
    write(out/'performance.json' if a.command=='performance' else out/'evidence.json',evidence)
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
 finally:maiden.close();write(out/'run.json',{'run_id':a.run_id,'command':a.command,'case':a.case_id,'performance_case':a.performance_case,'failure':failure})
 return 0
if __name__=='__main__':sys.exit(main())

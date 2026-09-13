#!/usr/bin/env python3
"""Exclusive, reversible stock-norns smoke runner; credentials stay external."""
import argparse,ctypes,hashlib,json,socket,struct,subprocess,sys,tarfile,tempfile,time
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
class SSH:
 def __init__(self,host,options=()):self.host=host;self.options=list(options)
 def run(self,script):return subprocess.run(['ssh',*self.options,self.host,'bash','-s'],input=script,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
 def rsync(self,source,dest):
  import shlex;shell=' '.join(shlex.quote(x) for x in ['ssh',*self.options]);subprocess.run(['rsync','-a','--delete','-e',shell,str(source)+'/',self.host+':'+dest+'/'],check=True)
 def fetch(self,remote,local):local.parent.mkdir(parents=True,exist_ok=True);local.write_bytes(subprocess.check_output(['ssh',*self.options,self.host,'cat',remote]))
 def push(self,local,remote):subprocess.run(['ssh',*self.options,self.host,'tee',remote],input=Path(local).read_bytes(),stdout=subprocess.DEVNULL,check=True)
class Maiden:
 """Scriptable nanomsg BUS client for official Maiden's matron socket."""
 def __init__(self,url,library='libnanomsg.so.5',timeout_ms=120000):self.url=url;self.library=library;self.timeout_ms=timeout_ms
 def eval(self,code):
  nn=ctypes.CDLL(self.library);nn.nn_socket.argtypes=[ctypes.c_int,ctypes.c_int];nn.nn_connect.argtypes=[ctypes.c_int,ctypes.c_char_p];nn.nn_setsockopt.argtypes=[ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t];nn.nn_send.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int];nn.nn_recv.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int];nn.nn_close.argtypes=[ctypes.c_int]
  fd=nn.nn_socket(1,112)
  if fd<0:raise RuntimeError('nn_socket failed')
  try:
   timeout=ctypes.c_int(self.timeout_ms)
   if nn.nn_setsockopt(fd,0,5,ctypes.byref(timeout),ctypes.sizeof(timeout))<0:raise RuntimeError('nn_setsockopt RCVTIMEO failed')
   if nn.nn_setsockopt(fd,0,4,ctypes.byref(timeout),ctypes.sizeof(timeout))<0:raise RuntimeError('nn_setsockopt SNDTIMEO failed')
   if nn.nn_connect(fd,self.url.encode())<0:raise RuntimeError('nn_connect failed')
   time.sleep(.25)
   marker='__MOSAIC_HW_'+hashlib.sha256((code+str(time.monotonic_ns())).encode()).hexdigest()[:16]+'__';payload=(code.rstrip()+"; print('"+marker+"')\n").encode();buf=ctypes.create_string_buffer(payload)
   if nn.nn_send(fd,buf,len(payload)+1,0)!=len(payload)+1:raise RuntimeError('nn_send failed')
   output=[]
   while True:
    received=ctypes.create_string_buffer(65536);size=nn.nn_recv(fd,received,len(received),0)
    if size<0:raise TimeoutError('Maiden marker not observed')
    chunk=received.raw[:size].decode(errors='replace');output.append(chunk)
    if marker in chunk:return ''.join(output)
  finally:nn.nn_close(fd)
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
  self.backup();self.maiden.eval('norns.script.clear()');self.ssh.run('rm -rf /home/we/dust/data/mosaic; mkdir -p /home/we/dust/data/mosaic');temp,tree,manifest,rows=export_head(repo);self._export=temp;staging='/home/we/dust/code/.mosaic-'+self.run_id+'.staging';self.ssh.run(f'rm -rf {staging}; mkdir -p {staging}');self.ssh.rsync(tree,staging);self.ssh.push(manifest,self.remote+'/source.sha256');self.ssh.run(f"set -eu; cd {staging}; sha256sum -c {self.remote}/source.sha256; rm -rf /home/we/dust/code/mosaic; mv {staging} /home/we/dust/code/mosaic");(self.out/'source.sha256').write_text(manifest.read_text());(self.out/'load.log').write_text(self.maiden.eval("norns.script.load('/home/we/dust/code/mosaic/mosaic.lua')"));return rows
 def action(self,kind,n,value):return self.osc.send(kind,n,value)
 def synthetic_grid(self,device,x,y,state):return self.maiden.eval(f'_norns.grid.key({int(device)},{int(x)-1},{int(y)-1},{int(state)})')
 def screenshot(self,label):
  rel='hardware-'+self.run_id+'/'+label;self.maiden.eval("os.execute('mkdir -p '..norns.state.data..'hardware-"+self.run_id+"'); screen.export_screenshot("+repr(rel)+")");local=self.out/(label+'.png');self.ssh.fetch('/home/we/dust/data/mosaic/'+rel+'.png',local);raw=local.read_bytes()
  if raw[:8]!=b'\x89PNG\r\n\x1a\n' or len(raw)<24 or struct.unpack('!II',raw[16:24])!=(640,384):raise AssertionError('Expected 640x384 PNG screenshot')
  return {'path':local.name,'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw),'width':640,'height':384}
 def logs(self):
  r=self.ssh.run("systemctl --failed --no-legend || true\nfor u in $(systemctl list-units --type=service --all --no-legend | awk '/matron|crone|supercollider|norns|maiden/{print $1}'); do echo --- $u; journalctl -u $u -n 200 --no-pager || true; done\n");(self.out/'runtime.log').write_text(r.stdout)
 def restore(self):
  try:self.maiden.eval('norns.script.clear()')
  except Exception as e:(self.out/'restore-warning.txt').write_text(str(e))
  r=self.remote;self.ssh.run(f"""set -eu; test "$(cat {ROOT}/active)" = {self.run_id}; test "$(cat {r}/run-id)" = {self.run_id}; rm -rf /home/we/dust/code/mosaic /home/we/dust/data/mosaic; if test -e {r}/had-code; then mv {r}/code-mosaic /home/we/dust/code/mosaic; fi; if test -e {r}/had-data; then mv {r}/data-mosaic /home/we/dust/data/mosaic; fi; if test -e {r}/had-state; then mv {r}/system.state /home/we/dust/data/system.state; else rm -f /home/we/dust/data/system.state; fi; rm -f {ROOT}/active; rm -rf {r}""");self.maiden.eval("local f=io.open('/home/we/dust/data/system.state'); if f then f:close(); dofile('/home/we/dust/data/system.state'); if norns.state.script ~= '' then norns.script.load(norns.state.script) end end")
 def finalize(self):
  self.maiden.eval('norns.script.clear()');r=self.remote
  self.ssh.run(f"""set -eu; test "$(cat {ROOT}/active)" = {self.run_id}; test "$(cat {r}/run-id)" = {self.run_id}; rm -rf /home/we/dust/data/mosaic; if test -e {r}/had-data; then mv {r}/data-mosaic /home/we/dust/data/mosaic; fi; if test -e {r}/had-state; then cp -a {r}/system.state /home/we/dust/data/system.state; else rm -f /home/we/dust/data/system.state; fi; rm -f {ROOT}/active; rm -rf {r}""")
  self.maiden.eval("local f=io.open('/home/we/dust/data/system.state'); if f then f:close(); dofile('/home/we/dust/data/system.state'); if norns.state.script ~= '' then norns.script.load(norns.state.script) end end");write(self.out/'finalized.json',{'run_id':self.run_id,'kept_deployment':True,'restored_user_data_and_state':True})
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('command',choices=['probe','workflow','restore','finalize']);p.add_argument('--host',required=True);p.add_argument('--ssh-option',action='append',default=[]);p.add_argument('--maiden-url',required=True);p.add_argument('--nanomsg-library',default='libnanomsg.so.5');p.add_argument('--maiden-timeout',type=float,default=120);p.add_argument('--osc-host',required=True);p.add_argument('--osc-port',type=int,default=10111);p.add_argument('--source',default=str(REPO));p.add_argument('--artifacts',required=True);p.add_argument('--run-id',required=True);p.add_argument('--synthetic-grid',action='store_true');p.add_argument('--grid-device-id',type=int,default=1);a=p.parse_args(argv)
 if not a.run_id.replace('-','').isalnum():p.error('unsafe run ID')
 out=Path(a.artifacts).resolve();out.mkdir(parents=True,exist_ok=False);r=Runner(SSH(a.host,a.ssh_option),Maiden(a.maiden_url,a.nanomsg_library,int(a.maiden_timeout*1000)),OSC(a.osc_host,a.osc_port),out,a.run_id);failure=None
 try:
  caps=r.probe()
  if a.command=='workflow':
   rows=r.deploy(Path(a.source).resolve());before=r.screenshot('before-controls');actions=[r.action('enc',1,1),r.action('key',2,1),r.action('key',2,0)];synthetic=None
   if a.synthetic_grid:synthetic=r.synthetic_grid(a.grid_device_id,3,8,1)+r.synthetic_grid(a.grid_device_id,3,8,0)
   time.sleep(.25);after=r.screenshot('after-controls');assert before['sha256']!=after['sha256'],'Controls produced no changed screen';r.logs();write(out/'evidence.json',{'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.source,text=True).strip(),'source_files':len(rows),'capabilities':caps,'actions':actions,'screens':[before,after],'screen_changed':True,'synthetic_grid':bool(a.synthetic_grid),'physical_grid_input_skipped':True,'grid_led_readback_skipped':True,'campaign_complete':False})
  elif a.command=='restore':r.restore()
  elif a.command=='finalize':r.finalize()
  else:write(out/'capabilities.json',caps)
 except Exception as e:failure=type(e).__name__+': '+str(e);raise
 finally:write(out/'run.json',{'run_id':a.run_id,'command':a.command,'failure':failure})
 return 0
if __name__=='__main__':sys.exit(main())

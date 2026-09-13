#!/usr/bin/env python3
"""Exclusive, reversible stock-norns smoke runner; credentials stay external."""
import argparse,hashlib,json,shlex,subprocess,sys,time
from pathlib import Path
REPO=Path(__file__).resolve().parents[2];ROOT='/home/we/.cache/mosaic-real-norns'
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
class SSH:
 def __init__(self,host,options=()):self.host=host;self.options=list(options)
 def run(self,script):return subprocess.run(['ssh',*self.options,self.host,'bash','-s'],input=script,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
 def rsync(self,source,dest):
  shell=' '.join(shlex.quote(x) for x in ['ssh',*self.options]);subprocess.run(['rsync','-a','--delete','--exclude=.git','--exclude=__pycache__','-e',shell,str(source)+'/',self.host+':'+dest+'/'],check=True)
 def fetch(self,remote,local):local.parent.mkdir(parents=True,exist_ok=True);subprocess.run(['scp',*self.options,self.host+':'+remote,str(local)],check=True)
class Maiden:
 """Use official maiden-repl; caller supplies its executable and WebSocket URL."""
 def __init__(self,command,url,crone_url,timeout=15):self.command=command;self.url=url;self.crone_url=crone_url;self.timeout=timeout
 def eval(self,code):
  marker='__MOSAIC_HW_DONE__';payload=code.rstrip()+"; print('"+marker+"')\n"
  result=subprocess.run([self.command,self.url,self.crone_url],input=payload,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=self.timeout)
  if result.returncode or marker not in result.stdout:raise RuntimeError('Maiden evaluation failed: '+result.stdout[-1000:])
  return result.stdout
class Runner:
 def __init__(self,ssh,maiden,out,run_id):self.ssh=ssh;self.maiden=maiden;self.out=out;self.run_id=run_id
 @property
 def remote(self):return ROOT+'/'+self.run_id
 def probe(self):
  r=self.ssh.run("""set -eu
echo '--- uname'; uname -a
echo '--- failed'; systemctl --failed --no-legend || true
echo '--- units'; systemctl list-units --type=service --all --no-legend | grep -E 'matron|crone|supercollider|norns|maiden' || true
echo '--- alsa'; if command -v aconnect >/dev/null; then aconnect -l; else echo 'UNAVAILABLE: aconnect'; fi
echo '--- osc'; command -v oscsend || true
""");(self.out/'probe.log').write_text(r.stdout)
  return {'alsa_available':'UNAVAILABLE: aconnect' not in r.stdout,'oscsend_available':'/oscsend' in r.stdout,'grid_input':'unsupported-without-automated-physical-device-boundary','grid_led_observation':'unsupported-without-automated-physical-device-boundary'}
 def backup(self):
  root=shlex.quote(self.remote);active=shlex.quote(ROOT+'/active');run=shlex.quote(self.run_id)
  self.ssh.run(f"""set -eu; umask 077; mkdir -p {ROOT}
test ! -e {active} || {{ echo 'recovery required: active marker exists'; exit 73; }}
mkdir {root}; printf '%s\n' {run} > {root}/run-id
if test -e /home/we/dust/code/mosaic; then mv /home/we/dust/code/mosaic {root}/code-mosaic; touch {root}/had-code; fi
if test -e /home/we/dust/data/mosaic; then mv /home/we/dust/data/mosaic {root}/data-mosaic; touch {root}/had-data; fi
if test -e /home/we/dust/data/system.state; then mv /home/we/dust/data/system.state {root}/system.state; touch {root}/had-state; fi
printf '%s\n' {run} > {active}.tmp; mv {active}.tmp {active}; mkdir -p /home/we/dust/code/.mosaic-{self.run_id}.staging /home/we/dust/data/mosaic
""")
 def deploy(self,source):
  self.maiden.eval('norns.script.clear()');self.backup();staging='/home/we/dust/code/.mosaic-'+self.run_id+'.staging';self.ssh.rsync(source,staging);self.ssh.run(f"set -eu; test \"$(cat {ROOT}/active)\" = {shlex.quote(self.run_id)}; mv {staging} /home/we/dust/code/mosaic");(self.out/'load.log').write_text(self.maiden.eval("norns.script.load('/home/we/dust/code/mosaic/mosaic.lua')"))
 def action(self,kind,n,value):
  if kind not in ('key','enc'):raise ValueError('Stock runner supports only key and enc actions')
  r=self.ssh.run(f"set -eu; command -v oscsend >/dev/null; oscsend 127.0.0.1 10111 /remote/{kind} ii {int(n)} {int(value)}")
  return {'type':kind,'n':int(n),'value':int(value),'host_monotonic_ns':time.monotonic_ns(),'output':r.stdout}
 def screenshot(self,label):
  if not label.replace('-','').isalnum():raise ValueError('Invalid screenshot label')
  rel='hardware-'+self.run_id+'/'+label;self.maiden.eval("os.execute('mkdir -p '..norns.state.data..'hardware-"+self.run_id+"'); screen.export_screenshot("+repr(rel)+")");local=self.out/(label+'.png');self.ssh.fetch('/home/we/dust/data/mosaic/'+rel+'.png',local);return {'path':local.name,'sha256':hashlib.sha256(local.read_bytes()).hexdigest(),'size':local.stat().st_size}
 def logs(self):
  r=self.ssh.run("""set -eu
systemctl --failed --no-legend || true
for u in $(systemctl list-units --type=service --all --no-legend | awk '/matron|crone|supercollider|norns|maiden/{print $1}'); do echo "--- $u"; journalctl -u "$u" -n 200 --no-pager || true; done
""");(self.out/'runtime.log').write_text(r.stdout)
 def restore(self):
  try:self.maiden.eval('norns.script.clear()')
  except Exception as e:(self.out/'restore-warning.txt').write_text(str(e)+'\n')
  root=shlex.quote(self.remote);active=shlex.quote(ROOT+'/active');run=shlex.quote(self.run_id)
  self.ssh.run(f"""set -eu
test -f {active}; test \"$(cat {active})\" = {run}; test \"$(cat {root}/run-id)\" = {run}
rm -rf /home/we/dust/code/mosaic /home/we/dust/data/mosaic
if test -e {root}/had-code; then mv {root}/code-mosaic /home/we/dust/code/mosaic; fi
if test -e {root}/had-data; then mv {root}/data-mosaic /home/we/dust/data/mosaic; fi
if test -e {root}/had-state; then mv {root}/system.state /home/we/dust/data/system.state; else rm -f /home/we/dust/data/system.state; fi
rm -f {active}; rmdir {root}
""")
  self.maiden.eval("local f=io.open('/home/we/dust/data/system.state'); if f then f:close(); dofile('/home/we/dust/data/system.state'); if norns.state.script ~= '' then norns.script.load(norns.state.script) end end")
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('command',choices=['probe','workflow','restore']);p.add_argument('--host',required=True);p.add_argument('--ssh-option',action='append',default=[]);p.add_argument('--maiden-command',default='maiden-repl');p.add_argument('--maiden-url',required=True);p.add_argument('--crone-url',required=True);p.add_argument('--source',default=str(REPO));p.add_argument('--artifacts',required=True);p.add_argument('--run-id',required=True);a=p.parse_args(argv)
 if not a.run_id.replace('-','').isalnum():p.error('unsafe run ID')
 out=Path(a.artifacts).resolve();out.mkdir(parents=True,exist_ok=False);r=Runner(SSH(a.host,a.ssh_option),Maiden(a.maiden_command,a.maiden_url,a.crone_url),out,a.run_id);failure=None
 try:
  caps=r.probe()
  if a.command=='workflow':r.deploy(Path(a.source).resolve());actions=[r.action('enc',1,1),r.action('key',2,1),r.action('key',2,0)];time.sleep(.25);screen=r.screenshot('after-controls');r.logs();write(out/'evidence.json',{'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=a.source,text=True).strip(),'capabilities':caps,'actions':actions,'screen':screen,'grid_cases_skipped':True,'campaign_complete':False})
  elif a.command=='restore':r.restore()
  else:write(out/'capabilities.json',caps)
 except Exception as e:failure=type(e).__name__+': '+str(e);raise
 finally:write(out/'run.json',{'run_id':a.run_id,'command':a.command,'failure':failure})
 return 0
if __name__=='__main__':sys.exit(main())

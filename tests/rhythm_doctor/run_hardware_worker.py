"""Run the owned capture stack on physical Norns with exact deployment cleanup."""
import argparse, hashlib, json, pathlib, shlex, subprocess, tempfile, time, uuid

ROOT=pathlib.Path(__file__).resolve().parents[2]
FILES=("tools/rhythm_doctor/rd_capture.c","tools/rhythm_doctor/rd_capture_worker.c",
       "tests/rhythm_doctor/test_capture_injector.c","tests/rhythm_doctor/test_capture_stack.lua",
       "lib/rhythm_doctor/state_machine.lua","lib/rhythm_doctor/bank.lua",
       "lib/rhythm_doctor/capture_controller.lua","lib/rhythm_doctor/native_transport.lua")

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--host',required=True);parser.add_argument('--control-path',required=True);parser.add_argument('--output',type=pathlib.Path,required=True);args=parser.parse_args()
    if args.output.exists():parser.error('output exists; evidence is immutable')
    run='mosaic-rd-worker-'+uuid.uuid4().hex;remote='/tmp/'+run
    ssh=['ssh','-S',args.control_path,'-o','BatchMode=yes','-o','ConnectTimeout=5',args.host]
    def call(command,timeout=30):return subprocess.run(ssh+[command],text=True,capture_output=True,timeout=timeout)
    def checked(command,timeout=30):
        result=call(command,timeout)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        return result.stdout
    def launch(argv, stdout_path, stderr_path):
        code=("import subprocess;out=open("+repr(stdout_path)+",'w');err=open("+repr(stderr_path)+",'w');"
              "p=subprocess.Popen("+repr(argv)+",stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);print(p.pid)")
        return int(checked('python3 -c '+shlex.quote(code)).strip())
    checked('test ! -e /home/we/.cache/mosaic-real-norns/active')
    before=checked("jack_lsp -c | grep -v 'mosaic-rd-capture\|rd-capture-injector' || true")
    directories=(remote,remote+'/tools',remote+'/tools/rhythm_doctor',remote+'/tests',remote+'/tests/rhythm_doctor',remote+'/lib',remote+'/lib/rhythm_doctor')
    checked('mkdir '+ ' '.join(shlex.quote(x) for x in directories))
    hashes={};worker_pid=injector_pid=None;socket_path=None;result=None;cleanup=[]
    try:
        with tempfile.TemporaryDirectory(prefix=run) as frozen:
            for relative in FILES:
                local=pathlib.Path(frozen)/pathlib.Path(relative).name;local.write_bytes((ROOT/relative).read_bytes());hashes[relative]=hashlib.sha256(local.read_bytes()).hexdigest()
                subprocess.run(['scp','-o','ControlPath='+args.control_path,str(local),args.host+':'+remote+'/'+relative],check=True,capture_output=True,timeout=30)
            for relative,digest in hashes.items():
                actual=checked('sha256sum '+shlex.quote(remote+'/'+relative)).split()[0]
                if actual!=digest:raise RuntimeError('deployed source mismatch: '+relative)
        checked('cd '+shlex.quote(remote)+' && gcc -std=c11 -O2 -Wall -Wextra -Werror tools/rhythm_doctor/rd_capture_worker.c -o rd-worker -ljack && gcc -std=c11 -O2 -Wall -Wextra -Werror tests/rhythm_doctor/test_capture_injector.c -o rd-injector -ljack',60)
        injector_pid=launch([remote+'/rd-injector'],remote+'/injector.log',remote+'/injector.log');time.sleep(.2)
        worker_pid=launch([remote+'/rd-worker',remote+'/owned-XXXXXX','rd-capture-injector:left','rd-capture-injector:right'],remote+'/worker.socket',remote+'/worker.log')
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            socket_path=checked('test -s '+shlex.quote(remote+'/worker.socket')+' && head -1 '+shlex.quote(remote+'/worker.socket')+' || true').strip()
            if socket_path:break
            time.sleep(.05)
        if not socket_path:raise RuntimeError('worker socket was not published')
        result=call('cd '+shlex.quote(remote)+' && luajit tests/rhythm_doctor/test_capture_stack.lua '+shlex.quote(socket_path),15)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and call('kill -0 '+str(worker_pid)).returncode==0:time.sleep(.05)
        after=checked("jack_lsp -c | grep -v 'mosaic-rd-capture\|rd-capture-injector' || true")
        cleanup.append({'worker_exited_after_peer_close':call('kill -0 '+str(worker_pid)).returncode!=0,'unrelated_routes_restored':after==before})
    finally:
        for pid in (worker_pid,injector_pid):
            if pid:call('kill '+str(pid)+' 2>/dev/null || true')
        # Exact known files only; the worker owns and removes its mkdtemp directory.
        for relative in FILES:call('rm -f '+shlex.quote(remote+'/'+relative))
        for name in ('rd-worker','rd-injector','injector.log','worker.socket','worker.log'):call('rm -f '+shlex.quote(remote+'/'+name))
        for directory in reversed(directories):call('rmdir '+shlex.quote(directory)+' 2>/dev/null || true')
    passed=bool(result and result.returncode==0 and cleanup and all(cleanup[0].values()) and call('test ! -e '+shlex.quote(remote)).returncode==0)
    report={'run_id':run,'profile':'physical-norns-native-worker','source_sha256':hashes,'result':{'exit_code':result.returncode if result else None,'stdout':result.stdout if result else '', 'stderr':result.stderr if result else ''},'cleanup':cleanup,'passed':passed,'scope':'actual Norns JACK input worker plus LuaJIT controller transport; injected PCM, not physical ADC or transcription','full_feature_acceptance':False}
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2));return int(not passed)
if __name__=='__main__':raise SystemExit(main())

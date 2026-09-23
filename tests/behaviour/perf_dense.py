"""PERF-002 dense sequencing: actual Mosaic in the constrained norns-class container.

    MONOME_EMULATOR=/path/to/monome-emulator python3 tests/behaviour/perf_dense.py \\
        --image monome-emulator:perf-recorder-02 --output ../mosaic-behaviour-runs/perf-dense-<name>

For each channel count, a fresh container (0.5 CPU quota, 768 MiB, cpuset 0)
loads this worktree as code/mosaic. The project is built through the real UI
over the container's HTTP API: pattern 1 has all 16 steps active; each active
channel N plays it on MIDI channel N. After a recorded settle, Play runs for a
fixed time. The oracle is the complete native MIDI export: every step emits
one Note On (note 60, velocity 100) per active channel, in time, and every note
is released. Resource figures are measurements for the refactor, not gates
that this runner may relax (PERFORMANCE.md; user direction D23).
"""
import argparse,base64,hashlib,json,os,subprocess,sys,tempfile,time,urllib.error,urllib.request,uuid
from pathlib import Path
BEHAVIOUR=Path(__file__).resolve().parent;REPO=BEHAVIOUR.parents[1]
EMULATOR=Path(os.environ['MONOME_EMULATOR']).resolve()
sys.path.insert(0,str(EMULATOR/'src'));sys.path.insert(0,str(BEHAVIOUR))
from automation.performance import performance_metrics,throttling_deltas,bracketing_samples
import driver
from perf_provenance import git_identity,installation_identity
from dense_workload import build_project,validate_events
from contract.performance_visuals import render_observation
from ui_map import PERFORMANCE_RENDER_PRESSURE_SCHEDULE, performance_gesture_recipe

STEP=1/6  # default 90 BPM, sixteenth steps

def docker(*args,timeout=60,check=True):
    result=subprocess.run(['docker',*args],capture_output=True,text=True,timeout=timeout)
    if check and result.returncode:raise RuntimeError('docker %s: %s'%(args[0],result.stderr[-800:]))
    return result

class Http:
    """The subset of the emulator Session client the Driver uses, over HTTP."""
    def __init__(self,port,token,session_id):self.port,self.token,self.id,self.sequence=port,token,session_id,0
    def request(self,path,payload=None,timeout=10):
        data=json.dumps(payload).encode() if payload is not None else None
        call=urllib.request.Request('http://127.0.0.1:%d%s'%(self.port,path),data=data,
            headers={'Authorization':'Bearer '+self.token,'Content-Type':'application/json'})
        with urllib.request.urlopen(call,timeout=timeout) as response:return json.load(response)
    def action(self,value):
        self.sequence+=1
        return self.request('/action',dict(schema_version=1,session_id=self.id,action_id=uuid.uuid4().hex,sequence=self.sequence,action=value))
    def observe(self):
        return self.observe_path('/snapshot')
    def display(self):
        return self.observe_path('/display')
    def observe_path(self,path):
        value=self.request(path)
        if value['errors']:raise RuntimeError('runtime errors: %s'%value['errors'])
        return value

class ContainerDriver(driver.Driver):
    def __init__(self,out,http):
        self.out=out;self.runtime=http;self.clock_mode='real-time';self.logical_ns=0
        self.recipe=[];self.observations=[];self.results=[];self.profile='base-midi';self.launch_options={}
        from ui import Ui
        self.ui=Ui(self)
        self.action_acks=[]
    def action(self,**value):
        ack=super().action(**value)
        self.action_acks.append(dict(recipe_index=len(self.recipe)-1,ack=ack))
        return ack
    def finish(self):
        driver.write(self.out/'recipe.json',self.recipe);driver.write(self.out/'results.json',self.results)
        driver.write(self.out/'action-acks.json',self.action_acks)

def workload_id(workload,pressure=False):
    base={'dense':'PERF-002','slides':'PERF-003'}[workload]
    return base+'+PERF-005-partial' if pressure else base

# Safe, non-musical controls reused from existing page/viewer/playhead cases.
RENDER_PRESSURE_SCHEDULE=PERFORMANCE_RENDER_PRESSURE_SCHEDULE
def run_render_pressure(d,http,seconds,observe_each=True,display_only=False):
    observe=http.display if display_only else http.observe
    assert seconds==8,'Render-pressure recipe requires exactly 8 seconds'
    started_ns=time.monotonic_ns();deadline_ns=started_ns+8_000_000_000;rows=[]
    expected=[x for x in RENDER_PRESSURE_SCHEDULE if started_ns+round(x[0]*1e9)<deadline_ns]
    for offset,label,gesture in expected:
        target_ns=started_ns+round(offset*1e9);remaining_ns=target_ns-time.monotonic_ns()
        if remaining_ns>0:time.sleep(remaining_ns/1e9)
        if time.monotonic_ns()>=deadline_ns:break
        before_start=time.monotonic_ns();before=render_observation(observe()) if observe_each else None;before_end=time.monotonic_ns()
        if time.monotonic_ns()>=deadline_ns:break
        ack_start=len(d.action_acks);dispatch_start=time.monotonic_ns()
        d.ui.performance_gesture(*gesture)
        dispatch_end=time.monotonic_ns();observed_start=time.monotonic_ns()
        after=render_observation(observe()) if observe_each else None;observed_end=time.monotonic_ns()
        rows.append(dict(offset_seconds=offset,label=label,gesture=performance_gesture_recipe(gesture),
          target_dispatch_ns=target_ns,dispatch_started_ns=dispatch_start,dispatch_ended_ns=dispatch_end,
          dispatch_lateness_ns=dispatch_start-target_ns,acknowledgement_indexes=list(range(ack_start,len(d.action_acks))),
          before_observe_ns=[before_start,before_end] if observe_each else None,after_observe_ns=[observed_start,observed_end] if observe_each else None,
          post_dispatch_observation_delay_ns=[observed_start-dispatch_end,observed_end-dispatch_end] if observe_each else None,
          before=before,after=after,frame_changed=(after['frame_sha256']!=before['frame_sha256']) if observe_each else None,
          grid_changed=(after['grid_sha256']!=before['grid_sha256']) if observe_each else None,
          attribution='Changes may include the live playhead and are not attributed to this gesture.'))
    remaining_ns=deadline_ns-time.monotonic_ns()
    if remaining_ns>0:time.sleep(remaining_ns/1e9)
    ended_ns=time.monotonic_ns()
    return dict(observation_mode=("display" if display_only else "snapshot") if observe_each else "none",observe_each_gesture=observe_each,schedule=[(offset,label,performance_gesture_recipe(gesture)) for offset,label,gesture in RENDER_PRESSURE_SCHEDULE],window_seconds=8,started_ns=started_ns,ended_ns=ended_ns,
      actual_window_ns=ended_ns-started_ns,expected_gestures=len(expected),dispatched_gestures=len(rows),
      complete=len(rows)==len(expected),observations=rows,
      acknowledged_actions=sum(len(x['acknowledgement_indexes']) for x in rows),
      limitation='Partial rendering-pressure evidence: changes are not gesture-attributable; no native per-render/dirty-frame counters, maximum render cadence, full-grid change workload or tooltip pressure.')
def run_one(image,out,channels,repeat,seconds,workload='dense',render_pressure=False,observe_each=True,display_only=False,cpus=.5):
    out.mkdir(parents=True);data=Path(tempfile.mkdtemp(prefix='perf-dense-data-'))
    name='mosaic-perf-'+uuid.uuid4().hex[:10];started=False;d=None
    code=Path(tempfile.mkdtemp(prefix='perf-dense-code-'))
    result=dict(schema_version=1,workload=workload_id(workload,render_pressure),channels=channels,repeat=repeat,seconds=seconds,image=image,render_pressure=render_pressure,passed=False)
    result['host_loadavg_before']=os.getloadavg() # shared host: record contention, never correct for it
    try:
        docker('run','-d','--name',name,'--cpus',str(cpus),'--memory','768m','--memory-swap','768m','--cpuset-cpus','0',
               '--shm-size','256m','-p','127.0.0.1::8765','--mount','type=bind,source=%s,target=/data'%data,
               '--mount','type=bind,source=%s,target=/code/mosaic,readonly'%REPO,
               image,'--script','/code/mosaic/mosaic.lua','--code-root','/code');started=True
        ready=None;deadline=time.monotonic()+120
        while not ready and time.monotonic()<deadline:
            for line in docker('logs',name,check=False).stdout.splitlines():
                try:value=json.loads(line)
                except ValueError:continue
                if value.get('status')=='ready':ready=value
            if not ready:time.sleep(.5)
        if not ready:raise RuntimeError('container did not become ready')
        port=int(docker('port',name,'8765/tcp').stdout.strip().rsplit(':',1)[1])
        http=Http(port,ready['token'],ready['session_id'])
        d=ContainerDriver(out,http)
        build_project(d,channels,workload)
        d.finish()
        driver.write(out/'setup-snapshot.json',http.observe())
        recording=http.request('/performance/start',dict(period_ms=10,maximum_seconds=int(seconds+15)))
        time.sleep(1.0)                            # recorded settle: build work leaves the quota window
        d.ui.control_edge('play_stop',True);d.ui.control_edge('play_stop',False)
        pressure=run_render_pressure(d,http,seconds,observe_each,display_only) if render_pressure else None
        if not render_pressure:time.sleep(seconds)
        d.ui.control_edge('play_stop',True);d.ui.control_edge('play_stop',False)
        time.sleep(1.0)
        final_snapshot=http.observe();driver.write(out/'final-snapshot.json',final_snapshot)
        state=final_snapshot['state'];assert not state['midi_capture']['outstanding'],state['midi_capture']['outstanding']
        result['render_pressure_observations']=pressure
        if render_pressure:assert pressure['complete'],('Missed render-pressure gestures',pressure['dispatched_gestures'],pressure['expected_gestures'])
        http.request('/performance/stop',{})
        samples=[];cursor=0
        while True:
            page=http.request('/performance/read',dict(after=cursor,limit=1000));samples+=page['samples'];cursor=page['cursor']
            if not page['has_more']:break
        driver.write(out/'samples.json',dict(recording=recording,samples=samples))
        found=docker('exec',name,'find','/opt/emulator/.runtime/sessions/'+ready['session_id'],'-name','native-events.jsonl').stdout.split()
        docker('cp',name+':'+found[0],str(out/'native-events.jsonl'))
        emitted=[e for e in (json.loads(l) for l in (out/'native-events.jsonl').read_text().splitlines()) if 'index' in e and 'bytes' in e]
        validated=validate_events(emitted,channels,workload);ons=validated['ons'];offs=validated['offs'];steps=validated['steps'];slide_cycles=validated['slide_cycles']
        origin=steps[0][0]['monotonic_ns']
        errors=[e['monotonic_ns']-(origin+round(k*STEP*1e9)) for k,group in enumerate(steps) for e in group]
        service=[group[-1]['monotonic_ns']-group[0]['monotonic_ns'] for group in steps]
        metrics=performance_metrics(samples,errors,service,len(emitted),round(STEP*1e9))
        window=throttling_deltas(bracketing_samples(samples,origin,steps[-1][-1]['monotonic_ns']))
        expected_steps=int(seconds/STEP)
        result['host_loadavg_after']=os.getloadavg()
        result.update(slide_cycles_checked=slide_cycles,render_pressure_observations=pressure,passed=bool(metrics['passed']),session_id=ready['session_id'],limits=recording['limits'],steps=len(steps),
            note_ons=len(ons),messages=len(emitted),metrics=metrics,throttling_workload=window,final_phase_error_ns=errors[-1])
        assert abs(len(steps)-expected_steps)<=2,('Step count',len(steps),expected_steps)
    except Exception as error:
        result['passed']=False
        result['error']=repr(error)[:2000]
        if isinstance(error,urllib.error.HTTPError):
            result['http_error_body']=error.read().decode('utf-8',errors='replace')[:4000]
    finally:
        if d is not None:d.finish()
        if started:
            (out/'container.log').write_text(docker('logs',name,check=False).stdout)
            docker('stop','--time','40',name,timeout=60,check=False);docker('rm',name,check=False)
        driver.write(out/'result.json',result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--workload',choices=('dense','slides'),default='dense')
    parser.add_argument('--render-pressure',action='store_true',help='Drive fixed non-musical UI gestures during timed playback')
    observations=parser.add_mutually_exclusive_group()
    observations.add_argument('--display-observations',action='store_true',help='Read exported frame/grid only during pressure; requires a runtime with GET /display')
    observations.add_argument('--no-render-observations',action='store_true',help='Diagnostic: keep pressure gestures but omit per-gesture snapshots to measure observer cost')
    parser.add_argument('--image',default='monome-emulator:perf-recorder-02');parser.add_argument('--output',required=True)
    parser.add_argument('--channels',default='1,4,8,16');parser.add_argument('--cpus',type=float,default=.5);parser.add_argument('--repeats',type=int,default=3);parser.add_argument('--seconds',type=float,default=8)
    parser.add_argument('--installation-manifest',help='Optional native installation.json to verify and bind to this report')
    args=parser.parse_args()
    if (args.no_render_observations or args.display_observations) and not args.render_pressure:parser.error('Observation mode requires --render-pressure')
    if args.render_pressure and args.seconds!=8:parser.error('--render-pressure requires --seconds 8')
    if args.cpus<=0:parser.error('--cpus must be positive')
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=False)
    source_git=git_identity(REPO);emulator_git=git_identity(EMULATOR)
    dirty=subprocess.check_output(['git','diff','HEAD'],cwd=REPO)
    manifest=args.installation_manifest
    if manifest is None:
        candidate=EMULATOR/'.runtime/performance-profile/installation.json'
        manifest=str(candidate) if candidate.is_file() else None
    install=installation_identity(manifest) if manifest else None
    image_id=docker('image','inspect',args.image,'--format','{{.Id}}').stdout.strip()
    rows=[run_one(args.image,root/('channels-%s-%d'%(n,r)),int(n),r,args.seconds,args.workload,args.render_pressure,not args.no_render_observations,args.display_observations,args.cpus) for n in args.channels.split(',') for r in range(1,args.repeats+1)]
    source_after=git_identity(REPO);emulator_after=git_identity(EMULATOR)
    install_after=installation_identity(manifest) if manifest else None
    stable=(source_git==source_after and emulator_git==emulator_after and install==install_after)
    report=dict(schema_version=2,workload=workload_id(args.workload,args.render_pressure),mosaic_revision=source_git['revision'],dirty_patch_sha256=hashlib.sha256(dirty).hexdigest() if dirty else None,
                emulator=str(EMULATOR),image=args.image,image_id=image_id,argv=sys.argv[1:],passed=all(r['passed'] for r in rows),runs=rows)
    report.update(source_git=source_git,source_git_after=source_after,emulator_git=emulator_git,
                  emulator_git_after=emulator_after,native_installation=install,
                  native_installation_after=install_after,provenance_stable=stable)
    if not stable:
        report['passed']=False
        report['provenance_error']='Mosaic, emulator, or native installation identity changed during the run'
    driver.write(root/'result.json',report);print(root/'result.json')
    return 0 if report['passed'] else 1

if __name__=='__main__':sys.exit(main())

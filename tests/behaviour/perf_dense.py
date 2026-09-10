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
import argparse,hashlib,json,os,subprocess,sys,tempfile,time,urllib.request,uuid
from pathlib import Path
BEHAVIOUR=Path(__file__).resolve().parent;REPO=BEHAVIOUR.parents[1]
EMULATOR=Path(os.environ['MONOME_EMULATOR']).resolve()
sys.path.insert(0,str(EMULATOR/'src'));sys.path.insert(0,str(BEHAVIOUR))
from automation.performance import performance_metrics,throttling_deltas,bracketing_samples
import driver

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
        value=self.request('/snapshot')
        if value['errors']:raise RuntimeError('runtime errors: %s'%value['errors'])
        return value

class ContainerDriver(driver.Driver):
    def __init__(self,out,http):
        self.out=out;self.runtime=http;self.clock_mode='real-time';self.logical_ns=0
        self.recipe=[];self.observations=[];self.results=[];self.profile='base-midi';self.launch_options={}
    def finish(self):
        driver.write(self.out/'recipe.json',self.recipe);driver.write(self.out/'results.json',self.results)

def build_project(d,channels,workload='dense'):
    d.tap(5,8);d.tap(1,1)                          # trig editor, pattern 1
    for x in range(1,17):d.tap(x,4)                # all 16 steps active
    d.tap(3,8);d.enc(1,4)                          # channel page, Device Config
    for channel in range(1,channels+1):
        d.tap(channel,1)
        d.enc(3,1);d.enc(2,1)                      # first device, then its MIDI channel
        if channel>1:d.enc(3,channel-1)
        d.key(3);d.tap(1,2);d.hold_tap((1,4),(16,4))
        if workload=='slides':
            # PERF-003: CC 1 locked 0 on step 1 and 127 on step 9, global slide on.
            from cases import assign_trig_parameter
            d.enc(1,-3);assign_trig_parameter(d,'CC 1')
            for step,value in ((1,0),(9,127)):
                d.action(type='grid',x=step,y=4,state=1)
                try:d.elapse(.05);d.action(type='enc',n=3,delta=-126);d.elapse(.15);d.enc(3,value+1)
                finally:d.action(type='grid',x=step,y=4,state=0)
                d.elapse(.1)
            d.key(3);d.enc(1,3)
    d.tap(1,1)

def check_slides(emitted,ons,channels):
    """Each channel's CC 1: 0 with step 1, a rising ramp, 127 with step 9, every cycle."""
    checked=0
    for channel in range(channels):
        cc=[e for e in emitted if e['bytes'][:2]==[176+channel,1]]
        notes=[e for e in ons if e['bytes'][0]==144+channel]
        for cycle in range(len(notes)//16):
            first,ninth=notes[16*cycle],notes[16*cycle+8]
            ramp=[e['bytes'][2] for e in cc if first['index']-channels*2<e['index']<ninth['index']]
            assert ramp and ramp[0]==0 and ramp[-1]==127 and ramp==sorted(ramp) and len(set(ramp))>=4,(channel+1,cycle,ramp)
            checked+=1
    assert checked>=channels,('No complete slide cycle',checked)
    return checked

def run_one(image,out,channels,repeat,seconds,workload='dense'):
    out.mkdir(parents=True);data=Path(tempfile.mkdtemp(prefix='perf-dense-data-'))
    name='mosaic-perf-'+uuid.uuid4().hex[:10];started=False
    code=Path(tempfile.mkdtemp(prefix='perf-dense-code-'))
    result=dict(schema_version=1,workload={'dense':'PERF-002','slides':'PERF-003'}[workload],channels=channels,repeat=repeat,seconds=seconds,image=image,passed=False)
    result['host_loadavg_before']=os.getloadavg() # shared host: record contention, never correct for it
    try:
        docker('run','-d','--name',name,'--cpus','0.5','--memory','768m','--memory-swap','768m','--cpuset-cpus','0',
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
        recording=http.request('/performance/start',dict(period_ms=10,maximum_seconds=int(seconds+15)))
        time.sleep(1.0)                            # recorded settle: build work leaves the quota window
        http.action(dict(type='grid',x=1,y=8,state=1));http.action(dict(type='grid',x=1,y=8,state=0))
        time.sleep(seconds)
        http.action(dict(type='grid',x=1,y=8,state=1));http.action(dict(type='grid',x=1,y=8,state=0))
        time.sleep(1.0)
        state=http.observe()['state'];assert not state['midi_capture']['outstanding'],state['midi_capture']['outstanding']
        http.request('/performance/stop',{})
        samples=[];cursor=0
        while True:
            page=http.request('/performance/read',dict(after=cursor,limit=1000));samples+=page['samples'];cursor=page['cursor']
            if not page['has_more']:break
        found=docker('exec',name,'find','/opt/emulator/.runtime/sessions/'+ready['session_id'],'-name','native-events.jsonl').stdout.split()
        docker('cp',name+':'+found[0],str(out/'native-events.jsonl'))
        emitted=[e for e in (json.loads(l) for l in (out/'native-events.jsonl').read_text().splitlines()) if 'index' in e and 'bytes' in e]
        assert [e['index'] for e in emitted]==list(range(1,len(emitted)+1)),'Non-contiguous native export'
        ons=[e for e in emitted if e['bytes'][0]&240==144 and e['bytes'][2]>0]
        offs=[e for e in emitted if e['bytes'][0]&240==128 or (e['bytes'][0]&240==144 and e['bytes'][2]==0)]
        # Oracle: step k has one Note On per channel 1..N, note 60 velocity 100.
        assert ons and len(ons)%channels==0,('Incomplete step',len(ons))
        steps=[ons[i:i+channels] for i in range(0,len(ons),channels)]
        for index,group in enumerate(steps):
            assert sorted(e['bytes'][0] for e in group)==[144+c for c in range(channels)],('Channels at step',index,[e['bytes'] for e in group])
            assert all(e['bytes'][1:]==[60,100] and e['port']==1 for e in group),('Bytes at step',index,[e['bytes'] for e in group])
        assert len(offs)==len(ons),('Unbalanced releases',len(ons),len(offs))
        slide_cycles=check_slides(emitted,ons,channels) if workload=='slides' else None
        origin=steps[0][0]['monotonic_ns']
        errors=[e['monotonic_ns']-(origin+round(k*STEP*1e9)) for k,group in enumerate(steps) for e in group]
        service=[group[-1]['monotonic_ns']-group[0]['monotonic_ns'] for group in steps]
        metrics=performance_metrics(samples,errors,service,len(emitted),round(STEP*1e9))
        window=throttling_deltas(bracketing_samples(samples,origin,steps[-1][-1]['monotonic_ns']))
        expected_steps=int(seconds/STEP)
        assert abs(len(steps)-expected_steps)<=2,('Step count',len(steps),expected_steps)
        driver.write(out/'samples.json',dict(recording=recording,samples=samples))
        result['host_loadavg_after']=os.getloadavg()
        result.update(slide_cycles_checked=slide_cycles,passed=bool(metrics['passed']),session_id=ready['session_id'],limits=recording['limits'],steps=len(steps),
            note_ons=len(ons),messages=len(emitted),metrics=metrics,throttling_workload=window,final_phase_error_ns=errors[-1])
        d.finish()
    except Exception as error:
        result['error']=repr(error)[:2000]
    finally:
        if started:
            (out/'container.log').write_text(docker('logs',name,check=False).stdout)
            docker('stop','--time','40',name,timeout=60,check=False);docker('rm',name,check=False)
        driver.write(out/'result.json',result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--workload',choices=('dense','slides'),default='dense')
    parser.add_argument('--image',default='monome-emulator:perf-recorder-02');parser.add_argument('--output',required=True)
    parser.add_argument('--channels',default='1,4,8,16');parser.add_argument('--repeats',type=int,default=3);parser.add_argument('--seconds',type=float,default=8)
    args=parser.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=False)
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    dirty=subprocess.check_output(['git','diff','HEAD'],cwd=REPO)
    image_id=docker('image','inspect',args.image,'--format','{{.Id}}').stdout.strip()
    rows=[run_one(args.image,root/('channels-%s-%d'%(n,r)),int(n),r,args.seconds,args.workload) for n in args.channels.split(',') for r in range(1,args.repeats+1)]
    report=dict(schema_version=1,workload={'dense':'PERF-002','slides':'PERF-003'}[args.workload],mosaic_revision=revision,dirty_patch_sha256=hashlib.sha256(dirty).hexdigest() if dirty else None,
                emulator=str(EMULATOR),image=args.image,image_id=image_id,argv=sys.argv[1:],passed=all(r['passed'] for r in rows),runs=rows)
    driver.write(root/'result.json',report);print(root/'result.json')
    return 0 if report['passed'] else 1

if __name__=='__main__':sys.exit(main())

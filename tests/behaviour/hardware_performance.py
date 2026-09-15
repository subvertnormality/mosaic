"""Physical-norns calibration adapter for the shared PERF-002/003 workload."""
import hashlib,json,subprocess,threading,time
from pathlib import Path

from dense_workload import build_project,validate_events
from hardware_driver import HardwareDriver

CASES={
    'PERF-002-HW-1':{'workload':'dense','channels':1,'seconds':8},
    'PERF-002-HW-4':{'workload':'dense','channels':4,'seconds':8},
    'PERF-002-HW-8':{'workload':'dense','channels':8,'seconds':8},
    'PERF-002-HW-16':{'workload':'dense','channels':16,'seconds':8},
    'PERF-003-HW-1':{'workload':'slides','channels':1,'seconds':8},
    'PERF-003-HW-8':{'workload':'slides','channels':8,'seconds':8},
    'PERF-003-HW-16':{'workload':'slides','channels':16,'seconds':8},
    'PERF-009-HW-4':{'workload':'locks','channels':4,'seconds':8},
    'PERF-009-HW-8':{'workload':'locks','channels':8,'seconds':8},
    'PERF-009-HW-16':{'workload':'locks','channels':16,'seconds':8},
}
from heldout_workloads import HELDOUT_CASES,LUA_LOAD_SOURCE,recovery_oracle,run_window
CASES.update(HELDOUT_CASES)
TIMING_THRESHOLDS={'p99_ns':10_000_000,'maximum_ns':50_000_000,'final_phase_ns':20_000_000,'service_p99_deadline_fraction':.5,'service_maximum_deadline_fraction':1.0}

def percentile(values,percent):
    ordered=sorted(values);return ordered[(percent*len(ordered)+99)//100-1]

def source_identity(source):
    source=Path(source).resolve();revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip();dirty=subprocess.check_output(['git','diff','HEAD'],cwd=source)
    return {'mosaic_revision':revision,'dirty_patch_sha256':hashlib.sha256(dirty).hexdigest() if dirty else None}

class OnDeviceResourceSampler:
    """Sample matron and device state through the runner's existing SSH transport."""
    def __init__(self,ssh,seconds,period=.25):self.ssh=ssh;self.seconds=float(seconds);self.period=float(period);self.result=None;self.error=None;self.thread=None
    def start(self):
        if self.thread:raise RuntimeError('resource sampler already started')
        self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()
    def _run(self):
        script="""python3 - <<'PY'
import glob,hashlib,json,os,platform,subprocess,time
duration=%r
period=%r
def matron():
 for path in glob.glob('/proc/[0-9]*/comm'):
  try:
   if open(path).read().strip()=='matron':return int(path.split('/')[2])
  except (IOError,OSError):pass
 raise RuntimeError('matron process not found')
pid=matron();ticks=os.sysconf('SC_CLK_TCK');page=os.sysconf('SC_PAGE_SIZE')
stat=open('/proc/%%d/stat'%%pid).read();end=stat.rfind(')');fields=stat[end+2:].split();start_ticks=int(fields[19])
try:boot_id=open('/proc/sys/kernel/random/boot_id').read().strip()
except IOError:boot_id=None
try:norns_revision=subprocess.check_output(['git','-C','/home/we/norns','rev-parse','HEAD'],stderr=subprocess.DEVNULL).decode().strip()
except (OSError,subprocess.CalledProcessError):norns_revision=None
try:clock_sha256=hashlib.sha256(open('/home/we/norns/lua/core/clock.lua','rb').read()).hexdigest()
except IOError:clock_sha256=None
try:matron_executable=os.readlink('/proc/%%d/exe'%%pid)
except OSError:matron_executable=None
print(json.dumps({'kind':'identity','uname':platform.uname()._asdict(),'boot_id':boot_id,'norns_revision':norns_revision,'clock_lua_sha256':clock_sha256,'matron_pid':pid,'matron_start_ticks':start_ticks,'matron_executable':matron_executable,'clock_ticks_per_second':ticks,'page_size':page}))
deadline=time.monotonic()+duration
while True:
 now=time.monotonic_ns()
 try:
  stat=open('/proc/%%d/stat'%%pid).read();end=stat.rfind(')');f=stat[end+2:].split();cpu_ticks=int(f[11])+int(f[12]);rss_pages=int(f[21])
 except (IOError,OSError):raise RuntimeError('matron identity disappeared')
 thermal=[]
 for path in glob.glob('/sys/class/thermal/thermal_zone*/temp'):
  try:thermal.append(int(open(path).read().strip()))
  except (IOError,OSError,ValueError):pass
 throttle=None
 try:
  raw=subprocess.check_output(['vcgencmd','get_throttled'],stderr=subprocess.DEVNULL).decode().strip();throttle=int(raw.rsplit('=',1)[1],16)
 except (IOError,OSError,ValueError,subprocess.CalledProcessError):pass
 print(json.dumps({'kind':'sample','monotonic_ns':now,'matron_cpu_ticks':cpu_ticks,'matron_rss_bytes':rss_pages*page,'load':list(os.getloadavg()),'thermal_millicelsius_max':max(thermal) if thermal else None,'throttled_flags':throttle}),flush=True)
 if time.monotonic()>=deadline:break
 time.sleep(period)
PY
"""%(self.seconds,self.period)
        try:
            rows=[json.loads(line) for line in self.ssh.run(script).stdout.splitlines() if line.strip()];self.result={'identity':next(row for row in rows if row['kind']=='identity'),'samples':[row for row in rows if row['kind']=='sample']}
        except Exception as error:self.error=error
    def stop(self):
        if not self.thread:raise RuntimeError('resource sampler not started')
        self.thread.join(self.seconds+30)
        if self.thread.is_alive():raise TimeoutError('on-device resource sampler did not finish')
        if self.error:raise self.error
        if not self.result or len(self.result['samples'])<2:raise RuntimeError('on-device resource sampler returned insufficient samples')
        return self.result

def resource_metrics(recording):
    samples=recording['samples'];identity=recording['identity'];first,last=samples[0],samples[-1];elapsed=last['monotonic_ns']-first['monotonic_ns'];cpu_ticks=last['matron_cpu_ticks']-first['matron_cpu_ticks']
    flags=[row['throttled_flags'] for row in samples if row['throttled_flags'] is not None]
    return {'sample_count':len(samples),'matron_cpu_ticks_delta':cpu_ticks,'matron_cpu_percent':100*cpu_ticks/identity['clock_ticks_per_second']/(elapsed/1e9),'matron_peak_rss_bytes':max(row['matron_rss_bytes'] for row in samples),'load_peak_1m':max(row['load'][0] for row in samples),'thermal_millicelsius_peak':max([row['thermal_millicelsius_max'] for row in samples if row['thermal_millicelsius_max'] is not None] or [None]),'throttling_available':bool(flags),'throttled_flags_or':__import__('functools').reduce(lambda a,b:a|b,flags,0) if flags else None,'threshold_status':'calibration-only'}

def dense_oracle(events,channels,seconds,step_seconds,workload):
    validated=validate_events(events,channels,workload);ons=validated['ons'];offs=validated['offs'];captured_steps=validated['steps']
    measurement_end_ns=captured_steps[0][0]['monotonic_ns']+round(seconds*1e9)
    steps=[group for group in captured_steps if group[0]['monotonic_ns']<measurement_end_ns]
    expected_steps=int(seconds/step_seconds);assert abs(len(steps)-expected_steps)<=2,('Step count',len(steps),expected_steps,len(captured_steps))
    slide_cycles=validated['slide_cycles'];lock_values_checked=validated['lock_values_checked'];origin=steps[0][0]['monotonic_ns'];step_ns=round(step_seconds*1e9)
    errors=[e['monotonic_ns']-(origin+k*step_ns) for k,group in enumerate(steps) for e in group];absolute=[abs(x) for x in errors];service=[group[-1]['monotonic_ns']-group[0]['monotonic_ns'] for group in steps]
    timing={name:percentile(absolute,p) for name,p in (('p50_ns',50),('p95_ns',95),('p99_ns',99),('maximum_ns',100))};service_metrics={name:percentile(service,p) for name,p in (('p50_ns',50),('p95_ns',95),('p99_ns',99),('maximum_ns',100))}
    service_metrics.update(p99_deadline_fraction=service_metrics['p99_ns']/step_ns,maximum_deadline_fraction=service_metrics['maximum_ns']/step_ns)
    intervals=[steps[i+1][0]['monotonic_ns']-steps[i][0]['monotonic_ns'] for i in range(len(steps)-1)];gates={'event_timing':timing['p99_ns']<=TIMING_THRESHOLDS['p99_ns'] and timing['maximum_ns']<=TIMING_THRESHOLDS['maximum_ns'] and abs(errors[-1])<=TIMING_THRESHOLDS['final_phase_ns'],'sustained_service':service_metrics['p99_deadline_fraction']<=TIMING_THRESHOLDS['service_p99_deadline_fraction'],'hard_service':service_metrics['maximum_deadline_fraction']<=TIMING_THRESHOLDS['service_maximum_deadline_fraction']}
    return {'passed':all(gates.values()),'steps':len(steps),'captured_steps':len(captured_steps),'note_ons':len(ons),'note_offs':len(offs),'messages':len(events),'slide_cycles_checked':slide_cycles,'lock_values_checked':lock_values_checked,'timing':timing,'final_phase_error_ns':errors[-1],'service':service_metrics,'interval_jitter_ns':[value-step_ns for value in intervals],'skipped_deadlines':sum(value>step_ns*1.5 for value in intervals),'gates':gates,'thresholds':TIMING_THRESHOLDS}

def parameter_position(runner,label):
    """1-based position of a parameter in the selected channel's device parameter list (read-only query)."""
    import re
    output=runner.maiden.eval("local c=program.get_selected_channel(); for i,p in ipairs(device_map.get_params(program.get().devices[c.number].device_map)) do if p.name=="+repr(label)+" then print('__MOSAIC_PARAM_POSITION__'..i..'/'..#device_map.get_params(program.get().devices[c.number].device_map)) end end")
    match=re.search(r'__MOSAIC_PARAM_POSITION__(\d+)/(\d+)',output)
    if not match:raise RuntimeError('Parameter unavailable in selected device list: '+label)
    return int(match.group(1)),int(match.group(2))

def select_fixture_parameter(driver,label):
    """Select a fixture parameter with front-panel gestures; its list position is resolved first."""
    if label not in ('CC 1','CC 2','CC 3','CC 4'):raise ValueError('Hardware fixture selector only supports CC 1-4')
    position,count=parameter_position(driver.runner,label)
    driver.key(2);driver.enc(3,-(count+2));driver.enc(3,position-1);driver.key(3);driver.key(2)

class ThreadSampler:
    """Run an external per-thread schedstat sampler on the device for one window."""
    def __init__(self,ssh,path,seconds,period=.5):self.ssh=ssh;self.path=Path(path);self.seconds=seconds;self.period=period;self.stdout=None;self.error=None;self.thread=None
    def start(self):
        code=self.path.read_bytes().decode()
        script="python3 - --seconds %s --period %s --system-every 4 <<'CALIBRATION_SAMPLER'\n%s\nCALIBRATION_SAMPLER\n"%(self.seconds,self.period,code)
        def run():
            try:self.stdout=self.ssh.run(script).stdout
            except Exception as error:self.error=error
        self.thread=threading.Thread(target=run,daemon=True);self.thread.start()
    def stop(self):
        self.thread.join(self.seconds+60)
        if self.error:raise self.error
        return self.stdout

class TimingTrace:
    """Diagnostic: record Lua-thread calls longer than 1 ms (redraws, display update, grid redraw, scheduler, clock resumes).

    Wrappers allocate only when a call exceeds the threshold, so observation adds little load.
    Timestamps use util.time(), the same clock as the MIDI trace.
    """
    INSTALL=("if _MOSAIC_TT then error('timing trace already installed') end; do local T={events={},n=0,limit=4000,orig={}}; local now=util.time; "
             "local function wrap(tbl,key,kind) local orig=tbl and tbl[key]; if type(orig)~='function' then return end; T.orig[#T.orig+1]={tbl,key,orig}; "
             "tbl[key]=function(...) local s=now(); orig(...); local d=now()-s; if d>0.001 and T.n<T.limit then local a=...; T.n=T.n+1; T.events[T.n]={kind,s,d,type(a)=='number' and a or 0,collectgarbage('count')} end end end; "
             "wrap(_G,'redraw','redraw'); wrap(_norns,'screen_update','screen_update'); wrap(m_grid,'grid_redraw','grid_redraw'); wrap(scheduler,'update','scheduler'); wrap(clock,'resume','clock_resume'); "
             "if _MOSAIC_TT_NATIVE then T.native={text=0,font_size=0,calls=0}; local function total(key,field) local orig=_norns[key]; if type(orig)~='function' then return end; T.orig[#T.orig+1]={_norns,key,orig}; "
             "_norns[key]=function(...) local s=now(); orig(...); local n=T.native; n[field]=n[field]+now()-s; n.calls=n.calls+1 end end; total('screen_text','text'); total('screen_font_size','font_size'); "
             "local draw=_G.redraw; _G.redraw=function(...) local n=T.native; local t0,f0,c0=n.text,n.font_size,n.calls; local s=now(); draw(...); local d=now()-s; "
             "if d>0.001 and T.n<T.limit then T.n=T.n+1; T.events[T.n]={'redraw_native',s,n.text-t0,math.floor((n.font_size-f0)*1e6),n.calls-c0} end end; T.orig[#T.orig+1]={_G,'redraw',draw} end; "
             "if _MOSAIC_TT_COUNT then local draw=_G.redraw; _G.redraw=function(...) local c=0; local cpu=os.clock(); local s=now(); debug.sethook(function() c=c+1 end,'',100); draw(...); debug.sethook(); local d=now()-s; "
             "if T.n<T.limit then T.n=T.n+1; T.events[T.n]={'redraw_count',s,d,c,math.floor((os.clock()-cpu)*1e6)} end end; T.orig[#T.orig+1]={_G,'redraw',draw} end; "
             "_MOSAIC_TT=T; print('__TT_INSTALLED__'..#T.orig) end")
    REMOVE=("if _MOSAIC_TT then for i=#_MOSAIC_TT.orig,1,-1 do local o=_MOSAIC_TT.orig[i]; o[1][o[2]]=o[3] end; _MOSAIC_TT=nil end; print('__TT_REMOVED__')")
    def __init__(self,maiden,native=False,count=False):self.maiden=maiden;self.installed=False;self.native=native;self.count=count
    def install(self):
        import re
        output=self.maiden.eval(('_MOSAIC_TT_NATIVE=true; ' if self.native else '_MOSAIC_TT_NATIVE=nil; ')+('_MOSAIC_TT_COUNT=true; ' if self.count else '_MOSAIC_TT_COUNT=nil; ')+self.INSTALL,allow_lua_error=True);match=re.search(r'__TT_INSTALLED__(\d+)',output)
        if not match:raise RuntimeError('Timing trace not installed: '+output[-1000:])
        self.installed=True;return int(match.group(1))
    def reset(self):return self.maiden.eval('if _MOSAIC_TT then _MOSAIC_TT.events={}; _MOSAIC_TT.n=0 end',allow_lua_error=True)
    def snapshot(self):
        import re
        output=self.maiden.eval("for i=1,_MOSAIC_TT.n do local e=_MOSAIC_TT.events[i]; print(string.format('__TT__%s|%.6f|%.6f|%d|%.0f',e[1],e[2],e[3],e[4],e[5])) end",allow_lua_error=True)
        return [{'kind':k,'start_seconds':float(a),'duration_ms':float(d)*1000,'argument':int(x),'lua_kb':float(kb)} for k,a,d,x,kb in re.findall(r'__TT__(\w+)\|([0-9.]+)\|([0-9.]+)\|(-?\d+)\|([0-9.]+)',output)]
    def remove(self):
        if self.installed:self.maiden.eval(self.REMOVE,allow_lua_error=True);self.installed=False

class NoResourceSampler:
    """Diagnostic: run without the on-device resource sampler."""
    thread=None
    def start(self):pass
    def stop(self):return None

class HardwareLane:
    """Timed held-out stimuli through the same public controls as the emulator lane."""
    def __init__(self,runner,driver):self.runner=runner;self.driver=driver
    def gesture(self,kind,a,b):
        if kind=='grid':
            self.driver.action(type='grid',x=a,y=b,state=1);self.driver.action(type='grid',x=a,y=b,state=0)
        else:self.driver.action(type='enc',n=a,delta=b)
    def lua_load(self,iterations):
        maiden=getattr(self.runner.maiden,'maiden',self.runner.maiden)
        code='load(%s)(%d)'%(json.dumps(LUA_LOAD_SOURCE),int(iterations))
        maiden._send((code+'\n').encode()+b'\0')

def functional_preflight(runner,driver,trace,spec):
    """Short unmeasured playback proving every channel sounds (and slides) before timing windows."""
    trace.reset();driver.tap(1,8);driver.elapse(2.0);driver.tap(1,8);driver.elapse(.4);state=driver.snapshot()
    channels=sorted({e['bytes'][0]&15 for e in state['midi'] if len(e['bytes'])==3 and e['bytes'][0]&240==144 and e['bytes'][2]>0 and e['port']==1})
    cc1=sorted({e['bytes'][0]&15 for e in state['midi'] if len(e['bytes'])==3 and e['bytes'][0]&240==176 and e['bytes'][1]==1 and e['port']==1})
    expected=list(range(spec['channels']))
    cc4=sorted({e['bytes'][0]&15 for e in state['midi'] if len(e['bytes'])==3 and e['bytes'][0]&240==176 and e['bytes'][1]==4 and e['port']==1})
    value={'note_channels':channels,'cc1_channels':cc1,'cc4_channels':cc4,'messages':len(state['midi']),'passed':channels==expected and (spec['workload'] not in ('slides','locks') or cc1==expected) and (spec['workload']!='locks' or cc4==expected)}
    if not value['passed']:
        dump=runner.maiden.eval("for ch=1,16 do local d=program.get().devices[ch]; print('__MOSAIC_CHANNEL__'..ch..'|'..tostring(d and d.device_map)..'|'..tostring(d and d.midi_channel)..'|'..tostring(d and d.midi_device)) end")
        (runner.out/'preflight-failure.json').write_text(json.dumps({**value,'channel_dump':dump[-6000:],'midi_head':state['midi'][:80]},indent=2)+'\n')
        raise AssertionError(('Functional preflight failed',value))
    return value

def run_hardware_performance(runner,case_id,grid_device,device_map_id,source,trace=None,sampler=None,thread_sampler=None,windows=1,timing_trace=False,resource_sampler=True,native_screen_trace=False,redraw_count_trace=False):
    if case_id not in CASES:raise ValueError('Unknown hardware performance case: '+case_id)
    spec=CASES[case_id];trace=trace or __import__('real_norns').OutputTrace(runner.maiden);driver=HardwareDriver(runner,grid_device,device_map_id,trace,capture_screens=False,artifact_prefix=case_id.lower());recording=None;results=[]
    try:
        build_project(driver,spec['channels'],spec['workload'],select_fixture_parameter,lambda d,channel:d.enc(3,runner.device_map_index(device_map_id,channel)-1))
        if spec.get('fingerprint'):__import__('perf_overload').configure_fingerprint(driver)
        driver.tap(5,8);driver.tap(1,1);driver.led_values([(x,4) for x in range(1,17)],[15]*16)
        preflight=functional_preflight(runner,driver,trace,spec)
        timings=TimingTrace(runner.maiden,native=native_screen_trace,count=redraw_count_trace) if timing_trace else None
        if timings:timings.install()
        for window in range(1,windows+1):
            recording=None;suffix='' if windows==1 else '-window-%d'%window
            trace.reset();sampler=(OnDeviceResourceSampler(runner.ssh,spec['seconds']+1.5) if resource_sampler else NoResourceSampler()) if windows>1 or sampler is None else sampler;threads=ThreadSampler(runner.ssh,thread_sampler,spec['seconds']+3) if thread_sampler else None
            if threads:threads.start()
            sampler.start();time.sleep(.25)
            started_ns=time.monotonic_ns();driver.tap(1,8)
            stimulus=run_window(HardwareLane(runner,driver),spec) if (spec.get('render') or spec.get('loads')) else None
            if stimulus is None:driver.elapse(spec['seconds'])
            driver.tap(1,8);driver.elapse(.3 if not spec.get('loads') else 1.5);state=driver.snapshot();ended_ns=time.monotonic_ns();recording=sampler.stop()
            if timings:state['lua_timings']=timings.snapshot();timings.reset()
            (runner.out/('performance-raw%s.json'%suffix)).write_text(json.dumps(state,indent=2)+'\n')
            if threads:(runner.out/('thread-samples%s.jsonl'%suffix)).write_text(threads.stop())
            recovery=None
            try:
                if spec.get('oracle')=='recovery':
                    recovery=recovery_oracle(state['midi'],spec['channels'],driver.expected_step_seconds,spec['loads'][0][0])
                    oracle={'timing':{'p99_ns':recovery['recovered_p99_ns'],'maximum_ns':recovery['recovered_max_ns']},'final_phase_error_ns':recovery['final_phase_error_ns'],
                            'service':{'p99_ns':0},'skipped_deadlines':0,'gates':dict(recovery['gates']),'passed':recovery['passed'],'note_ons':recovery['groups']*spec['channels'],
                            'messages':len(state['midi']),'steps':recovery['groups'],'slide_cycles_checked':None}
                else:oracle=dense_oracle(state['midi'],spec['channels'],spec['seconds'],driver.expected_step_seconds,spec['workload'])
                if stimulus is not None:
                    oracle['gates']['stimulus_complete']=stimulus['complete'];oracle['passed']=oracle['passed'] and stimulus['complete']
                failure=None
            except AssertionError as error:
                if windows==1:raise
                oracle=None;failure=repr(error)[:2000]
            results.append({'window':window,'stimulus':stimulus,'recovery':recovery,'host_window_ns':ended_ns-started_ns,'grid_writes':state['grid_writes'],'grid_refreshes':state['grid_refreshes'],'oracle':oracle,'oracle_failure':failure,'resources':resource_metrics(recording) if recording else None,'resource_samples':recording['samples'] if recording else None,'runtime_identity':recording['identity'] if recording else None,'lua_timings_recorded':len(state.get('lua_timings',[])) if timing_trace else None,'passed':bool(oracle and oracle['passed'])})
            if window<windows:driver.elapse(2.0)
        first=results[0]
        (runner.out/'preflight.json').write_text(json.dumps(preflight,indent=2)+'\n')
        value={'schema_version':1,'case':case_id,'workload':spec['workload'],'channels':spec['channels'],'requested_window_seconds':spec['seconds'],'host_window_ns':first['host_window_ns'],'tempo_bpm':driver.tempo_bpm,'trace_boundary':{'reset_before_sampler_and_play':True,'midi_driver_boundary':'stock _norns.midi_send pass-through','grid_writes':first['grid_writes'],'grid_refreshes':first['grid_refreshes']},'oracle':first['oracle'],'resources':first['resources'],'resource_samples':first['resource_samples'],'runtime_identity':first['runtime_identity'],'source_identity':source_identity(source),'passed':all(r['passed'] for r in results),'limitations':['Resource figures are physical-device calibration measurements, not emulator-equivalence gates.','Grid activity is observed at the driver boundary; frame revision diagnostics are emulator-only.']}
        if windows>1:value['windows']=results
        return value
    finally:
        if sampler and sampler.thread and recording is None:
            try:sampler.stop()
            except Exception:pass
        if timing_trace and 'timings' in locals() and timings:
            try:timings.remove()
            except Exception:pass
        driver.finish()

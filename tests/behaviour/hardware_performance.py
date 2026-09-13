"""Physical-norns calibration adapter for the shared PERF-002/003 workload."""
import hashlib,json,subprocess,threading,time
from pathlib import Path

from dense_workload import build_project,validate_events
from hardware_driver import HardwareDriver

CASES={
    'PERF-002-HW-1':{'workload':'dense','channels':1,'seconds':8},
    'PERF-002-HW-16':{'workload':'dense','channels':16,'seconds':8},
    'PERF-003-HW-16':{'workload':'slides','channels':16,'seconds':8},
}
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
    slide_cycles=validated['slide_cycles'];origin=steps[0][0]['monotonic_ns'];step_ns=round(step_seconds*1e9)
    errors=[e['monotonic_ns']-(origin+k*step_ns) for k,group in enumerate(steps) for e in group];absolute=[abs(x) for x in errors];service=[group[-1]['monotonic_ns']-group[0]['monotonic_ns'] for group in steps]
    timing={name:percentile(absolute,p) for name,p in (('p50_ns',50),('p95_ns',95),('p99_ns',99),('maximum_ns',100))};service_metrics={name:percentile(service,p) for name,p in (('p50_ns',50),('p95_ns',95),('p99_ns',99),('maximum_ns',100))}
    service_metrics.update(p99_deadline_fraction=service_metrics['p99_ns']/step_ns,maximum_deadline_fraction=service_metrics['maximum_ns']/step_ns)
    intervals=[steps[i+1][0]['monotonic_ns']-steps[i][0]['monotonic_ns'] for i in range(len(steps)-1)];gates={'event_timing':timing['p99_ns']<=TIMING_THRESHOLDS['p99_ns'] and timing['maximum_ns']<=TIMING_THRESHOLDS['maximum_ns'] and abs(errors[-1])<=TIMING_THRESHOLDS['final_phase_ns'],'sustained_service':service_metrics['p99_deadline_fraction']<=TIMING_THRESHOLDS['service_p99_deadline_fraction'],'hard_service':service_metrics['maximum_deadline_fraction']<=TIMING_THRESHOLDS['service_maximum_deadline_fraction']}
    return {'passed':all(gates.values()),'steps':len(steps),'captured_steps':len(captured_steps),'note_ons':len(ons),'note_offs':len(offs),'messages':len(events),'slide_cycles_checked':slide_cycles,'timing':timing,'final_phase_error_ns':errors[-1],'service':service_metrics,'interval_jitter_ns':[value-step_ns for value in intervals],'skipped_deadlines':sum(value>step_ns*1.5 for value in intervals),'gates':gates,'thresholds':TIMING_THRESHOLDS}

def select_fixture_parameter(driver,label):
    """Select the first opt-in fixture parameter using only front-panel gestures."""
    if label!='CC 1':raise ValueError('Hardware fixture selector only supports CC 1')
    driver.key(2);driver.enc(3,-50);driver.key(3);driver.key(2)

def run_hardware_performance(runner,case_id,grid_device,device_map_id,source,trace=None,sampler=None):
    if case_id not in CASES:raise ValueError('Unknown hardware performance case: '+case_id)
    spec=CASES[case_id];trace=trace or __import__('real_norns').OutputTrace(runner.maiden);driver=HardwareDriver(runner,grid_device,device_map_id,trace,capture_screens=False,artifact_prefix=case_id.lower());recording=None
    try:
        build_project(driver,spec['channels'],spec['workload'],select_fixture_parameter,lambda d,channel:d.enc(3,runner.device_map_index(device_map_id,channel)-1));driver.tap(5,8);driver.tap(1,1);driver.led_values([(x,4) for x in range(1,17)],[15]*16);trace.reset();sampler=sampler or OnDeviceResourceSampler(runner.ssh,spec['seconds']+1.5);sampler.start();time.sleep(.25)
        started_ns=time.monotonic_ns();driver.tap(1,8);driver.elapse(spec['seconds']);driver.tap(1,8);driver.elapse(.3);state=driver.snapshot();ended_ns=time.monotonic_ns();recording=sampler.stop()
        (runner.out/'performance-raw.json').write_text(json.dumps(state,indent=2)+'\n')
        oracle=dense_oracle(state['midi'],spec['channels'],spec['seconds'],driver.expected_step_seconds,spec['workload'])
        return {'schema_version':1,'case':case_id,'workload':spec['workload'],'channels':spec['channels'],'requested_window_seconds':spec['seconds'],'host_window_ns':ended_ns-started_ns,'tempo_bpm':driver.tempo_bpm,'trace_boundary':{'reset_before_sampler_and_play':True,'midi_driver_boundary':'stock _norns.midi_send pass-through','grid_writes':state['grid_writes'],'grid_refreshes':state['grid_refreshes']},'oracle':oracle,'resources':resource_metrics(recording),'resource_samples':recording['samples'],'runtime_identity':recording['identity'],'source_identity':source_identity(source),'passed':oracle['passed'],'limitations':['Resource figures are physical-device calibration measurements, not emulator-equivalence gates.','Grid activity is observed at the driver boundary; frame revision diagnostics are emulator-only.']}
    finally:
        if sampler and sampler.thread and recording is None:
            try:sampler.stop()
            except Exception:pass
        driver.finish()

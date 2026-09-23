"""Physical-norns calibration adapter for the shared PERF-002/003 workload."""
import hashlib,json,subprocess,threading,time
from pathlib import Path

from dense_workload import EXTREME_STEP_STRIDE,build_project,validate_events
from hardware_driver import HardwareDriver

CASES={
    'PERF-002-HW-1':{'workload':'dense','channels':1,'seconds':8},
    'PERF-002-HW-4':{'workload':'dense','channels':4,'seconds':8},
    'PERF-002-HW-8':{'workload':'dense','channels':8,'seconds':8},
    # The gated 16-channel cases play at 130 bpm, a representative working tempo
    # (user, 2026-09-17); the smaller ones calibrate the emulator lane at 90.
    'PERF-002-HW-16':{'workload':'dense','channels':16,'seconds':8,'tempo_bpm':130},
    'PERF-003-HW-1':{'workload':'slides','channels':1,'seconds':8},
    'PERF-003-HW-8':{'workload':'slides','channels':8,'seconds':8},
    'PERF-003-HW-16':{'workload':'slides','channels':16,'seconds':8,'tempo_bpm':130},
    'PERF-009-HW-4':{'workload':'locks','channels':4,'seconds':8},
    'PERF-009-HW-8':{'workload':'locks','channels':8,'seconds':8},
    'PERF-009-HW-16':{'workload':'locks','channels':16,'seconds':8,'tempo_bpm':130},
    # Chords, locks and a slide on every channel, every other step: a stress probe at
    # any tempo, and a gated case at 200 bpm, where one DIN port runs at capacity.
    'PERF-EXT-HW-16':{'workload':'extreme','channels':16,'seconds':8,'step_stride':EXTREME_STEP_STRIDE},
    'PERF-010-HW-16':{'workload':'extreme','channels':16,'seconds':8,'step_stride':EXTREME_STEP_STRIDE,'tempo_bpm':200},
}
from heldout_workloads import HELDOUT_CASES,LUA_LOAD_SOURCE,recovery_oracle,run_window
CASES.update(HELDOUT_CASES)
TIMING_THRESHOLDS={'p99_ns':10_000_000,'maximum_ns':50_000_000,'final_phase_ns':20_000_000,'service_p99_deadline_fraction':.5,'service_maximum_deadline_fraction':1.0,'step_jitter_p95_ns':5_000_000,'step_jitter_maximum_ns':10_000_000}
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

def dense_oracle(events,channels,seconds,step_seconds,workload,thresholds=None,step_stride=1,lead_ms=0):
    thresholds=thresholds or TIMING_THRESHOLDS
    # A workload that sounds every Nth step is timed against a grid N steps wide.
    step_seconds=step_seconds*step_stride
    validated=validate_events(events,channels,workload,lead_ms);ons=validated['ons'];offs=validated['offs'];captured_steps=validated['steps']
    measurement_end_ns=captured_steps[0][0]['monotonic_ns']+round(seconds*1e9)
    steps=[group for group in captured_steps if group[0]['monotonic_ns']<measurement_end_ns]
    expected_steps=int(seconds/step_seconds);assert abs(len(steps)-expected_steps)<=2,('Step count',len(steps),expected_steps,len(captured_steps))
    slide_cycles=validated['slide_cycles'];lock_values_checked=validated['lock_values_checked'];origin=steps[0][0]['monotonic_ns'];step_ns=round(step_seconds*1e9)
    errors=[e['monotonic_ns']-(origin+k*step_ns) for k,group in enumerate(steps) for e in group];absolute=[abs(x) for x in errors];service=[group[-1]['monotonic_ns']-group[0]['monotonic_ns'] for group in steps]
    timing={name:percentile(absolute,p) for name,p in (('p50_ns',50),('p95_ns',95),('p99_ns',99),('maximum_ns',100))}
    # A device stall now and then delays one whole step: every note of it lands
    # late together, and on its own that step decides the window's p99. Gate
    # event timing on the p99 of every other step, so one stall per window is
    # tolerated while lateness spread across steps still fails. The stalled
    # step stays bounded by the maximum and step jitter gates, and is reported.
    step_worst=[max(abs(e['monotonic_ns']-(origin+k*step_ns)) for e in group) for k,group in enumerate(steps)]
    stalled=max(range(len(steps)),key=lambda k:step_worst[k])
    others=[abs(e['monotonic_ns']-(origin+k*step_ns)) for k,group in enumerate(steps) if k!=stalled for e in group]
    stall_tolerance={'excluded_step':stalled,'excluded_step_maximum_ns':step_worst[stalled],'p99_ns':percentile(others,99) if others else timing['p99_ns']}
    service_metrics={name:percentile(service,p) for name,p in (('p50_ns',50),('p95_ns',95),('p99_ns',99),('maximum_ns',100))}
    service_metrics.update(p99_deadline_fraction=service_metrics['p99_ns']/step_ns,maximum_deadline_fraction=service_metrics['maximum_ns']/step_ns)
    intervals=[steps[i+1][0]['monotonic_ns']-steps[i][0]['monotonic_ns'] for i in range(len(steps)-1)];jitter=[abs(value-step_ns) for value in intervals]
    # Where a step starts is the tempo the player hears; how far its own notes
    # spread is a separate, ordered offset. Gate them separately.
    step_jitter={name:percentile(jitter,p) for name,p in (('p50_ns',50),('p95_ns',95),('p99_ns',99),('maximum_ns',100))} if jitter else {'p50_ns':0,'p95_ns':0,'p99_ns':0,'maximum_ns':0}
    gates={'event_timing':stall_tolerance['p99_ns']<=thresholds['p99_ns'] and timing['maximum_ns']<=thresholds['maximum_ns'] and abs(errors[-1])<=thresholds['final_phase_ns'],'sustained_service':service_metrics['p99_deadline_fraction']<=thresholds['service_p99_deadline_fraction'],'hard_service':service_metrics['maximum_deadline_fraction']<=thresholds['service_maximum_deadline_fraction'],'step_jitter':step_jitter['p95_ns']<=thresholds['step_jitter_p95_ns'] and step_jitter['maximum_ns']<=thresholds['step_jitter_maximum_ns']}
    return {'passed':all(gates.values()),'steps':len(steps),'captured_steps':len(captured_steps),'note_ons':len(ons),'note_offs':len(offs),'messages':len(events),'slide_cycles_checked':slide_cycles,'lock_values_checked':lock_values_checked,'timing':timing,'timing_one_stall_tolerated':stall_tolerance,'final_phase_error_ns':errors[-1],'service':service_metrics,'interval_jitter_ns':[value-step_ns for value in intervals],'step_jitter':step_jitter,'skipped_deadlines':sum(value>step_ns*1.5 for value in intervals),'gates':gates,'thresholds':thresholds}

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
    driver.ui.press_key(2);driver.ui.turn(3,-(count+2));driver.ui.turn(3,position-1);driver.ui.press_key(3);driver.ui.press_key(2)

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
             "wrap(_G,'redraw','redraw'); wrap(_norns,'screen_update','screen_update'); wrap(m_grid,'grid_redraw','grid_redraw'); wrap(scheduler,'update','scheduler'); wrap(clock,'resume','clock_resume'); wrap(_norns,'midi_send','midi_send'); "
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
        self.driver.ui.performance_gesture(kind,a,b)
    def lua_load(self,iterations):
        maiden=getattr(self.runner.maiden,'maiden',self.runner.maiden)
        code='load(%s)(%d)'%(json.dumps(LUA_LOAD_SOURCE),int(iterations))
        maiden._send((code+'\n').encode()+b'\0')

TRANSPORT_STATE_LUA="do local keys={} for _,k in ipairs(m_grid.get_pressed_keys()) do keys[#keys+1]=k[1]..','..k[2] end print('__TRANSPORT__'..tostring(m_clock.is_playing())..'|'..table.concat(keys,';')) end"

def transport_state(runner):
    """Read-only, between windows: whether the transport plays, and which grid keys Mosaic holds pressed."""
    import re
    match=re.search(r'__TRANSPORT__(true|false)\|([0-9,;]*)',runner.maiden.eval(TRANSPORT_STATE_LUA,allow_lua_error=True))
    if not match:raise RuntimeError('Transport state unavailable')
    return match.group(1)=='true',[tuple(int(v) for v in key.split(',')) for key in match.group(2).split(';') if key]

def ready_to_play(runner,driver,log):
    """Before a window: the transport must be stopped with no grid key held.

    The play button toggles, and a key Mosaic still holds turns the next tap
    into a two-key press, so either would invert or swallow the window's play.
    Release held keys and stop a running transport here, outside the window."""
    playing,held=transport_state(runner)
    for x,y in held:driver.ui.control_edge('cell',False,(x,y));driver.elapse(.05)
    if playing:driver.ui.stop();driver.elapse(.3)
    playing_after,held_after=transport_state(runner)
    log.append({'held_keys_released':held,'was_playing':playing,'playing_after':playing_after,'held_after':held_after})
    if playing_after or held_after:raise AssertionError(('Transport not ready for a window',log[-1]))

def stopped_after_window(runner,log):
    """After a window's stop tap: a transport still playing means its taps were swallowed or inverted."""
    playing,held=transport_state(runner)
    log.append({'stopped_after_window':not playing,'held_keys':held})
    return not playing

def functional_preflight(runner,driver,trace,spec):
    """Short unmeasured playback proving every channel sounds (and slides) before timing windows."""
    ready_to_play(runner,driver,[]);trace.reset();driver.ui.play();driver.elapse(2.0);driver.ui.stop();driver.elapse(.4);state=driver.snapshot()
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

CHANNEL_STATE_LUA=("do local d=program.get(); local sp=d.selected_song_pattern; print('__STATE__selected_channel='..tostring(d.selected_channel)..' page='..tostring(d.selected_page)..' song_pattern='..tostring(sp)..' record='..tostring(params:get('record'))) "
    "for c=1,2 do local ch=program.get_channel(sp,c); local wp=ch.working_pattern or {}; local notes={} local trigs={} for s=1,16 do notes[s]=tostring((wp.note_values or {})[s]) trigs[s]=tostring((wp.trig_values or {})[s]) end "
    "local ids={} for i=1,10 do local p=ch.trig_lock_params[i] ids[i]=p and tostring(p.id or p.param_id) or '-' end "
    "local locks=0 for _,slots in pairs(ch.step_trig_lock_banks or {}) do for _ in pairs(slots) do locks=locks+1 end end "
    "print('__STATE__ch'..c..' octave='..tostring(ch.octave)..' transpose='..tostring(select(2,pcall(step.calculate_step_transpose,c)))..' mute='..tostring(ch.mute)..' step='..tostring(program.get_current_step_for_channel(c))..' notes='..table.concat(notes,',')..' trigs='..table.concat(trigs,',')..' lock_params='..table.concat(ids,',')..' step_lock_entries='..locks..' fixed='..tostring(params:get('midi_device_params_channel_'..c..'_2'))..' qfixed='..tostring(params:get('midi_device_params_channel_'..c..'_3'))) "
    "local dev=d.devices[c] or {}; local stock={} for _,k in ipairs({'fixed_note','quantised_fixed_note','bipolar_random_note','twos_random_note','random_velocity','chord_arp','mute_root_note','chord_strum_pattern','trig_probability'}) do local ok,v=pcall(step.process_stock_params,c,1,k) stock[#stock+1]=k..'='..tostring(ok and v or ('err:'..tostring(v))) end "
    "local okz,qz=pcall(include,'mosaic/lib/quantiser'); local okq,q=false,'quantiser unavailable' if okz and qz then okq,q=pcall(qz.process,0,0,0,ch.step_scale_number) end "
    "print('__STATE__ch'..c..' pipeline step_scale_number='..tostring(ch.step_scale_number)..' quantised_c0='..tostring(okq and q or ('err:'..tostring(q)))..' device_map='..tostring(dev.device_map)..' midi_channel='..tostring(dev.midi_channel)..' midi_device='..tostring(dev.midi_device)..' chord_masks='..tostring(ch.chord_one_mask)..','..tostring(ch.chord_two_mask)..','..tostring(ch.chord_three_mask)..','..tostring(ch.chord_four_mask)..' step_chord_masks_1='..tostring(ch.step_chord_masks and ch.step_chord_masks[1] ~= nil)..' '..table.concat(stock,' ')) end end")

def channel_state_dump(runner):
    """Read-only: the selected channel, page and channels 1-2 settings that shape their notes and locks."""
    import re
    output=runner.maiden.eval(CHANNEL_STATE_LUA,allow_lua_error=True)
    return re.findall(r'__STATE__([^\n]*)',output)

def _lead_identity(lead_ms, timing_contract, seed, probe_mode):
    if type(lead_ms) is not int or not 0 <= lead_ms <= 50:
        raise ValueError('midi_lock_lead_time must be an integer in 0..50')
    # 'legacy-delay-v1' delays notes, clock and transport behind the locks.
    # 'pulse-advance' delays nothing and sends the locks early instead. They are
    # different contracts, not settings of one, and each result says which it is.
    if timing_contract not in ('legacy-delay-v1', 'pulse-advance'):
        raise ValueError('Unsupported timing_contract: %r' % (timing_contract,))
    if type(seed) is not int or not 0 <= seed <= 2**31-1:
        raise ValueError('seed must be a nonnegative 31-bit integer')
    if probe_mode not in ('off', 'pulse-v1', 'pulse-core-v1'):
        raise ValueError('Unsupported probe_mode')
    return dict(midi_lock_lead_time=lead_ms, timing_contract=timing_contract, seed=seed, probe_mode=probe_mode)


def set_lock_lead(driver, lead_ms, timing_contract='legacy-delay-v1'):
    """Set through stock Norns params (same public API as the tempo control).

    The contract is selected and read back the same way, so a run cannot silently
    measure a different contract from the one its manifest claims.
    """
    import re
    _lead_identity(lead_ms, timing_contract, 0, 'off')
    output = driver.runner.maiden.eval("params:set('midi_lock_lead_time',%d); print('__MOSAIC_LOCK_LEAD__'..params:get('midi_lock_lead_time'))" % lead_ms)
    found = re.search(r'__MOSAIC_LOCK_LEAD__([0-9.]+)', output)
    if not found or float(found.group(1)) != lead_ms:
        raise AssertionError('Lock lead readback mismatch: requested %s, observed %s' % (lead_ms, found.group(1) if found else 'missing'))
    reply = driver.runner.maiden.eval(
        "m_clock.set_lock_contract('%s'); print('__MOSAIC_LOCK_CONTRACT__'..m_clock.get_lock_contract())" % timing_contract)
    seen = re.search(r'__MOSAIC_LOCK_CONTRACT__(\S+)', reply)
    if not seen or seen.group(1) != timing_contract:
        raise AssertionError('Lock contract readback mismatch: requested %s, observed %s'
                             % (timing_contract, seen.group(1) if seen else 'missing'))
    return lead_ms


def write_fixture_manifest(directory,case_id,spec,source,*,lead_ms=0,timing_contract='legacy-delay-v1',seed=0,probe_mode='off'):
    """Record what a saved project fixture holds and which build produced it."""
    import hashlib,subprocess
    directory=Path(directory)
    files={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in ('autosave.ptn','autosave.pset')}
    revision=subprocess.run(['git','rev-parse','HEAD'],cwd=source,capture_output=True,text=True).stdout.strip()
    manifest={'case':case_id,'workload':spec['workload'],'channels':spec['channels']}
    manifest.update(_lead_identity(lead_ms, timing_contract, seed, probe_mode), fixture_id=case_id)
    if spec.get('step_stride',1)!=1:manifest['step_stride']=spec['step_stride']
    manifest.update(built_from_revision=revision,files=files,lane='cm3plus-norns')
    (directory/'fixture.json').write_text(json.dumps(manifest,indent=2)+'\n')


def prepare_fixture(source_dir, destination_dir, *, lead_ms=0, seed=0, probe_mode='off',
                    timing_contract='legacy-delay-v1'):
    """Create an explicitly identified variant, never relabel historical evidence."""
    import re
    source, destination = Path(source_dir).resolve(), Path(destination_dir).resolve()
    identity = _lead_identity(lead_ms, timing_contract, seed, probe_mode)
    if destination == source or source in destination.parents:
        raise ValueError('Destination must be outside source fixture')
    if destination.exists():
        raise FileExistsError('Fixture destination already exists: '+str(destination))
    original = json.loads((source/'fixture.json').read_text())
    content = {}
    for name in ('autosave.ptn', 'autosave.pset'):
        if not (source/name).is_file():
            raise ValueError('Missing fixture file: '+name)
        content[name] = (source/name).read_bytes()
        if hashlib.sha256(content[name]).hexdigest() != original.get('files', {}).get(name):
            raise ValueError('Fixture hash mismatch: '+name)
    text = content['autosave.pset'].decode('utf-8')
    lines = [line for line in text.splitlines() if not re.match(r'^\s*"midi_lock_lead_time"\s*:', line)]
    content['autosave.pset'] = ('\n'.join(lines)+'\n"midi_lock_lead_time": '+str(lead_ms)+'\n').encode('utf-8')
    manifest = {key:value for key,value in original.items() if key != 'migrated_from'}
    manifest.update(identity, fixture_id=original.get('case'), migrated_from=original,
                    files={name:hashlib.sha256(value).hexdigest() for name,value in content.items()})
    destination.mkdir(parents=True, exist_ok=False)
    for name, value in content.items():
        (destination/name).write_bytes(value)
    (destination/'fixture.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def check_project_fixture(directory,case_id):
    """A fixture must hold the project this case plays, exactly as it was saved.

    Several cases play the same project (every dense case with four channels, for
    instance), so a fixture is matched on workload and channel count rather than
    on the case that happened to build it."""
    directory=Path(directory);spec=CASES[case_id];manifest_path=directory/'fixture.json'
    if not manifest_path.is_file():raise ValueError('Project fixture has no fixture.json: '+str(directory))
    manifest=json.loads(manifest_path.read_text())
    for field in ('midi_lock_lead_time', 'timing_contract', 'seed', 'probe_mode'):
        if field not in manifest:
            raise ValueError('Project fixture missing '+field+': '+str(directory))
    _lead_identity(manifest['midi_lock_lead_time'], manifest['timing_contract'], manifest['seed'], manifest['probe_mode'])
    if (manifest.get('workload'),manifest.get('channels'))!=(spec['workload'],spec['channels']):
        raise ValueError('Project fixture %s holds %s/%s, but %s plays %s/%s'%(directory,manifest.get('workload'),manifest.get('channels'),case_id,spec['workload'],spec['channels']))
    if manifest.get('step_stride',1)!=spec.get('step_stride',1):
        raise ValueError('Project fixture %s has a trig every %s steps, but %s plays one every %s'%(directory,manifest.get('step_stride',1),case_id,spec.get('step_stride',1)))
    files=manifest.get('files') or {}
    for name in ('autosave.ptn','autosave.pset'):
        if name not in files:raise ValueError('Project fixture manifest does not record '+name+': '+str(directory))
        if not (directory/name).is_file() or hashlib.sha256((directory/name).read_bytes()).hexdigest()!=files[name]:
            raise ValueError('Project fixture file does not match its manifest: '+str(directory/name))
    return manifest

def case_tempo(case_id,requested=None):
    """The tempo a case runs at: its own when it fixes one, which a different request may not override."""
    fixed=CASES.get(case_id,{}).get('tempo_bpm')
    if fixed is None:return requested
    if requested is not None and float(requested)!=float(fixed):
        raise ValueError('%s runs at %s bpm, not %s'%(case_id,fixed,requested))
    return fixed

def project_fixture_name(case_id):
    """The fixture directory name for the project a case plays."""
    spec=CASES[case_id];return '%s-%d'%(spec['workload'],spec['channels'])

def run_hardware_performance(runner,case_id,grid_device,device_map_id,source,trace=None,sampler=None,thread_sampler=None,windows=1,timing_trace=False,resource_sampler=True,native_screen_trace=False,redraw_count_trace=False,project_fixture=None,save_project_fixture=None,lead_ms=None,probe_mode='off',seed=0,measured_steps=None,probe_schedule=None,seed_schedule=None,timing_contract='legacy-delay-v1'):
    if case_id not in CASES:raise ValueError('Unknown hardware performance case: '+case_id)
    if type(windows) is not int or windows < 1:raise ValueError('windows must be positive')
    if measured_steps is not None and (type(measured_steps) is not int or measured_steps < 1):raise ValueError('measured_steps must be positive')
    if probe_schedule is not None:
        if type(probe_schedule) is not list or len(probe_schedule) != windows or any(mode not in ('off','pulse-v1','pulse-core-v1') for mode in probe_schedule):
            raise ValueError('probe_schedule must be a list of valid modes matching windows')
        probe_schedule=list(probe_schedule)
    if seed_schedule is not None:
        if type(seed_schedule) is not list or len(seed_schedule) != windows or any(type(value) is not int or not 0 <= value <= 2**31-1 for value in seed_schedule):
            raise ValueError('seed_schedule must be a list of 31-bit seeds matching windows')
        seed_schedule=list(seed_schedule)
    spec=dict(CASES[case_id]);trace=trace or __import__('real_norns').OutputTrace(runner.maiden);driver=HardwareDriver(runner,grid_device,device_map_id,trace,capture_screens=False,artifact_prefix=case_id.lower());recording=None;results=[]
    if measured_steps is not None:spec['seconds']=measured_steps*driver.expected_step_seconds*spec.get('step_stride',1)
    try:
        # A loaded project fixture already holds the workload; build it through the
        # UI only when there is none, and keep that build as a fixture if asked.
        fixture_manifest=check_project_fixture(project_fixture,case_id) if project_fixture is not None else {}
        if lead_ms is None:lead_ms=fixture_manifest['midi_lock_lead_time'] if fixture_manifest else 0
        identity=_lead_identity(lead_ms, timing_contract, seed, probe_mode)
        identity.update(fixture_id=case_id, workload=spec['workload'], fixture_files=fixture_manifest.get('files'), clock_source='internal', port=1,
                        capture_backend='stock-norns-output-trace', requested_window_seconds=spec['seconds'])
        if measured_steps is not None:identity['measured_steps']=measured_steps
        if probe_schedule is not None:identity['probe_schedule']=probe_schedule
        if seed_schedule is not None:identity['seed_schedule']=seed_schedule
        if spec.get('tempo_bpm') is not None and abs(driver.tempo_bpm-spec['tempo_bpm'])>.01:
            raise AssertionError('%s runs at %s bpm but the norns clock is at %s'%(case_id,spec['tempo_bpm'],driver.tempo_bpm))
        if project_fixture is None:
            build_project(driver,spec['channels'],spec['workload'],select_fixture_parameter,lambda d,channel:d.ui.set_value(runner.device_map_index(device_map_id,channel)-1))
        set_lock_lead(driver, lead_ms)
        if seed_schedule is None:runner.maiden.eval('math.randomseed(%d)' % seed)
        if project_fixture is None:
            if save_project_fixture:
                runner.fetch_project(save_project_fixture)
                write_fixture_manifest(save_project_fixture,case_id,spec,source,lead_ms=lead_ms,seed=seed,probe_mode=probe_mode,timing_contract=timing_contract)
        if spec.get('fingerprint'):__import__('perf_overload').configure_fingerprint(driver)
        driver.ui.pattern_editor();driver.ui.tap_control('pattern_select',1);driver.ui.expect_steps({x:'selected' for x in range(1,17,spec.get('step_stride',1))})
        preflight=functional_preflight(runner,driver,trace,spec)
        timings=TimingTrace(runner.maiden,native=native_screen_trace,count=redraw_count_trace) if timing_trace else None
        if timings:timings.install()
        from pulse_probe import PulseProbe, summarize_snapshot
        pulse_probe=None
        transport_log=[]
        for window in range(1,windows+1):
            recording=None;suffix='' if windows==1 else '-window-%d'%window
            pulse_probe=None;probe_cleaned=False
            window_mode=probe_schedule[window-1] if probe_schedule is not None else probe_mode
            window_seed=seed_schedule[window-1] if seed_schedule is not None else seed
            window_identity=dict(identity,probe_mode=window_mode,seed=window_seed)
            pulse_probe=PulseProbe(runner.maiden,mode=window_mode) if window_mode!='off' else None
            if pulse_probe:
                window_identity.update(probe_schema_version=1,probe_capacity=pulse_probe.capacity,
                                       probe_kinds=[1,4,5] if window_mode=='pulse-core-v1' else [1,2,3,4,5,6])
                if probe_schedule is None:identity.update(window_identity)
                pulse_probe.install()
            ready_to_play(runner,driver,transport_log)
            observed_lead=set_lock_lead(driver, lead_ms, timing_contract)
            if seed_schedule is not None:runner.maiden.eval('math.randomseed(%d)' % window_seed)
            if pulse_probe:pulse_probe.reset()
            trace.reset();sampler=(OnDeviceResourceSampler(runner.ssh,spec['seconds']+1.5) if resource_sampler else NoResourceSampler()) if windows>1 or sampler is None else sampler;threads=ThreadSampler(runner.ssh,thread_sampler,spec['seconds']+3) if thread_sampler else None
            if threads:threads.start()
            sampler.start();time.sleep(.25)
            started_ns=time.monotonic_ns();play_tap=driver.ui.play()
            stimulus=run_window(HardwareLane(runner,driver),spec) if (spec.get('render') or spec.get('loads')) else None
            if stimulus is None:driver.elapse(spec['seconds'])
            stop_tap=driver.ui.stop();driver.elapse(.3 if not spec.get('loads') else 1.5);state=driver.snapshot();ended_ns=time.monotonic_ns();recording=sampler.stop()
            if timings:state['lua_timings']=timings.snapshot();timings.reset()
            state['run_identity']=dict(window_identity, observed_lead_ms=observed_lead, window=window)
            (runner.out/('performance-raw%s.json'%suffix)).write_text(json.dumps(state,indent=2)+'\n')
            if pulse_probe:
                try:
                    state['pulse_probe']=pulse_probe.snapshot()
                    state['pulse_probe_summary']=summarize_snapshot(state['pulse_probe'])
                    (runner.out/('performance-raw%s.json'%suffix)).write_text(json.dumps(state,indent=2)+'\n')
                finally:
                    try:
                        pulse_probe.remove();probe_cleaned=True
                    finally:(runner.out/('pulse-probe-replies%s.json'%suffix)).write_text(json.dumps(pulse_probe.raw_replies,indent=2)+'\n')
            if threads:(runner.out/('thread-samples%s.jsonl'%suffix)).write_text(threads.stop())
            recovery=None
            window_stopped=stopped_after_window(runner,transport_log)
            try:
                if not window_stopped:raise AssertionError(('Transport still playing after the window stop tap: its play and stop taps were swallowed or inverted',transport_log[-2:]))
                if spec.get('oracle')=='recovery':
                    recovery=recovery_oracle(state['midi'],spec['channels'],driver.expected_step_seconds,spec['loads'][0][0])
                    oracle={'timing':{'p99_ns':recovery['recovered_p99_ns'],'maximum_ns':recovery['recovered_max_ns']},'final_phase_error_ns':recovery['final_phase_error_ns'],
                            'service':{'p99_ns':0},'skipped_deadlines':0,'gates':dict(recovery['gates']),'passed':recovery['passed'],'note_ons':recovery['groups']*spec['channels'],
                            'messages':len(state['midi']),'steps':recovery['groups'],'slide_cycles_checked':None}
                else:oracle=dense_oracle(state['midi'],spec['channels'],spec['seconds'],driver.expected_step_seconds,spec['workload'],step_stride=spec.get('step_stride',1),lead_ms=lead_ms)
                if stimulus is not None:
                    oracle['gates']['stimulus_complete']=stimulus['complete'];oracle['passed']=oracle['passed'] and stimulus['complete']
                if pulse_probe:
                    oracle['probe_diagnostics']=state['pulse_probe_summary']
                    oracle['gates']['probe_complete']=True
                failure=None
            except AssertionError as error:
                # Keep what the device held when a window's output was wrong, so an
                # intermittent state change can be traced (see INCIDENTS.md 22:24).
                try:(runner.out/('oracle-failure%s.json'%suffix)).write_text(json.dumps({'failure':repr(error)[:2000],'midi_input':state.get('midi_input'),'channel_state':channel_state_dump(runner),'transport':transport_log[-2:]},indent=2)+'\n')
                except Exception as dump_error:(runner.out/('oracle-failure%s.json'%suffix)).write_text(json.dumps({'failure':repr(error)[:2000],'dump_error':repr(dump_error)})+'\n')
                if windows==1:raise
                oracle=None;failure=repr(error)[:2000]
            results.append({'window':window,'seed':window_seed,'probe_mode':window_mode,'run_identity':state['run_identity'],'transport_taps':{'play':play_tap,'stop':stop_tap},'stimulus':stimulus,'recovery':recovery,'host_window_ns':ended_ns-started_ns,'grid_writes':state['grid_writes'],'grid_refreshes':state['grid_refreshes'],'oracle':oracle,'oracle_failure':failure,'resources':resource_metrics(recording) if recording else None,'resource_samples':recording['samples'] if recording else None,'runtime_identity':recording['identity'] if recording else None,'lua_timings_recorded':len(state.get('lua_timings',[])) if timing_trace else None,'passed':bool(oracle and oracle['passed'])})
            if window<windows:driver.elapse(2.0)
        first=results[0]
        (runner.out/'preflight.json').write_text(json.dumps(preflight,indent=2)+'\n')
        value={'schema_version':1,'case':case_id,'workload':spec['workload'],'channels':spec['channels'],'requested_window_seconds':spec['seconds'],'host_window_ns':first['host_window_ns'],'tempo_bpm':driver.tempo_bpm,'trace_boundary':{'reset_before_sampler_and_play':True,'midi_driver_boundary':'stock _norns.midi_send pass-through','grid_writes':first['grid_writes'],'grid_refreshes':first['grid_refreshes']},'oracle':first['oracle'],'resources':first['resources'],'resource_samples':first['resource_samples'],'runtime_identity':first['runtime_identity'],'source_identity':source_identity(source),'passed':all(r['passed'] for r in results),'limitations':['Resource figures are physical-device calibration measurements, not emulator-equivalence gates.','Grid activity is observed at the driver boundary; frame revision diagnostics are emulator-only.']}
        value['transport_checks']=transport_log
        value['run_identity']=identity
        value['source_identity'].update(identity)
        # The current trace measures Lua driver dispatch, not receiver capture.
        value['qualification_eligible']=False
        value['limitations'].append('Diagnostic only: receiver-capture calibration, absolute input anchoring and the foundation acceptance campaign remain required.')
        if windows>1:value['windows']=results
        return value
    finally:
        try:
            if 'pulse_probe' in locals() and pulse_probe and not probe_cleaned:
                try:pulse_probe.remove()
                finally:(runner.out/('pulse-probe-replies%s.json'%suffix)).write_text(json.dumps(pulse_probe.raw_replies,indent=2)+'\n')
        finally:
            if sampler and sampler.thread and recording is None:
                try:sampler.stop()
                except Exception:pass
            if timing_trace and 'timings' in locals() and timings:
                try:timings.remove()
                except Exception:pass
            driver.finish()

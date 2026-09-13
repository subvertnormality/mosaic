"""Stock-norns adapter for a deliberately small registered-recipe suite."""
import re,time

HARDWARE_PERFORMANCE_RECIPES={
    'perf_dense.py':{
        'status':'implemented-unverified','hardware_verified':False,'adaptation':'hardware-calibration','cases':['PERF-002-HW-1','PERF-002-HW-16','PERF-003-HW-16'],
        'comparable_metrics':['MIDI event completeness and order','per-step channel grouping','balanced releases','onset lateness/jitter/drift','intra-step service span','grid driver activity'],
        'available_boundaries':['HardwareDriver controls','OutputTrace MIDI timestamps','OutputTrace grid writes','screen screenshots'],
        'capability_gaps':['frame revision counters for render pressure','cross-device resource thresholds require repeated physical calibration'],
    },
    'perf_input.py':{
        'status':'deferred','adaptation':'blocked-on-input-boundary',
        'comparable_metrics':['MIDI event completeness and order','output lateness/jitter/drift','input action latency','grid and screen activity'],
        'available_boundaries':['HardwareDriver controls','OutputTrace MIDI timestamps','grid driver trace','screen screenshots'],
        'capability_gaps':['scheduled external-MIDI ingress','accepted/delivered input ledger with device timestamps','comparable action acknowledgement timestamps','512-event boundary transport'],
    },
    'perf_overload.py':{
        'status':'deferred','adaptation':'blocked-on-load-and-resource-boundaries',
        'comparable_metrics':['complete ordered MIDI groups','balanced release ownership','post-load lateness/jitter/drift/skips','one-bar recovery','grid and screen recovery','overload threshold'],
        'available_boundaries':['HardwareDriver controls','OutputTrace MIDI timestamps','grid driver trace','screen screenshots'],
        'capability_gaps':['bounded repeatable on-device load generator','CPU/throttling/resource samples bracketing the load','frame/grid revision counters','device-specific threshold calibration'],
    },
    'perf_storage.py':{
        'status':'excluded','adaptation':'not-sequencer-timing',
        'reason':'The current recipe defines no storage-speed threshold or sequencer timing correlation; include only if a measured storage stall affects musical output.',
    },
}

HARDWARE_QUALIFICATION_TARGETS={
    'representative-smoke':{'status':'implemented','cases':['M-PAT-001']},
    'performance-load':{'status':'partial-unverified','implemented_cases':['PERF-002-HW-1','PERF-002-HW-16','PERF-003-HW-16'],'hardware_verified':False,'recipes':HARDWARE_PERFORMANCE_RECIPES},
    'musical-timing-drift':{'status':'deferred','cases':['M-TIM-001','M-TIM-002','M-SYNC-022']},
    'midi-master-slave-sync':{'status':'deferred','cases':['M-TIM-003','M-TIM-004']+['M-SYNC-%03d'%n for n in range(1,23)]},
    'stock-clock-cancel-queued-resume':{'status':'implemented','mode':'clock-cancel','fixture':'dedicated stock-runtime baseline/candidate/restoration comparison'},
}
HARDWARE_DRIVER_CAPABILITIES={
    'driver':'real-norns','clock_modes':['real-time'],
    'implemented_semantics':['action:key','action:enc','action:grid','elapse','snapshot:grid','snapshot:midi','wait','tap','key','enc','hold_tap','led_values','configure:base-midi','playback:base-midi','finish'],
    'unsupported_semantics':{
        'screen_header':'No machine-readable stock-norns text/frame oracle is installed.',
        'controlled_time':'Physical norns runs use wall time.',
        'fault_injection':'Emulator lifecycle, transport, stall and drop actions are unavailable on stock norns.',
        'external_midi_input':'This first adapter increment drives only norns controls and synthetic grid callbacks.',
        'non_base_midi_profiles':'Audio, Crow, n.b. and modulation output oracles are deferred.',
    },
    'observation_boundaries':['stock _norns.midi_send pass-through trace','stock grid LED driver pass-through trace','screen screenshots'],
    'qualification_targets':HARDWARE_QUALIFICATION_TARGETS,
    'broad_functional_suite':'emulator-coverage',
}

def hardware_applicability(cases):
    """Return fail-closed machine-readable applicability for every recipe."""
    rows=[]
    targeted={}
    for target,value in HARDWARE_QUALIFICATION_TARGETS.items():
        for case_id in value.get('cases',[]):targeted.setdefault(case_id,[]).append(target)
    for case_id,spec in cases.items():
        if case_id=='M-PAT-001':status='implemented';category='representative-smoke';reason='Registered recipe runs through HardwareDriver'
        elif spec.get('controlled_only'):status='unsupported';category='controlled-only';reason=spec['controlled_only']
        elif spec.get('emulator_only_fault'):status='unsupported';category='emulator-only-fault';reason=spec['emulator_only_fault']
        elif case_id in targeted:status='deferred';category='targeted-hardware-qualification';reason='Adapter/oracle work remains for '+', '.join(targeted[case_id])
        else:status='deferred';category='broad-functional-emulator-coverage';reason='Not selected for the focused hardware qualification suite'
        row={'case':case_id,'status':status,'category':category,'applicable':status=='implemented','reason':reason}
        if case_id in targeted:row['qualification_targets']=targeted[case_id]
        rows.append(row)
    return {'schema_version':1,'capabilities':HARDWARE_DRIVER_CAPABILITIES,'performance_recipes':HARDWARE_PERFORMANCE_RECIPES,'cases':rows}

class HardwareDriver:
    """Public behavior-driver surface backed by Runner and OutputTrace."""
    def __init__(self,runner,grid_device,device_map_id,trace,capture_screens=True,artifact_prefix='m-pat-001'):
        self.runner=runner;self.grid_device=grid_device;self.device_map_id=device_map_id;self.trace=trace
        self.clock_mode='real-time';self.logical_ns=0;self.recipe=[];self.observations=[];self.results=[];self.screens=[];self.finished=False;self.capture_screens=capture_screens;self.artifact_prefix=artifact_prefix
        output=runner.maiden.eval("print('__MOSAIC_TEMPO__'..clock.get_tempo())");match=re.search(r'__MOSAIC_TEMPO__([0-9.]+)',output)
        if not match:raise RuntimeError('Could not observe norns clock tempo')
        self.tempo_bpm=float(match.group(1));self.expected_step_seconds=15/self.tempo_bpm;self.trace.install()
    def action(self,**value):
        kind=value.get('type')
        if kind=='grid':
            self.runner.synthetic_grid(self.grid_device,value['x'],value['y'],value['state']);row={**value,'transport':'norns-grid-key-callback'}
        elif kind in ('key','enc'):
            field='state' if kind=='key' else 'delta';row=self.runner.action(kind,value['n'],value[field])
        else:raise NotImplementedError('HardwareDriver action unsupported: '+str(kind))
        self.recipe.append(row);return row
    def elapse(self,seconds):time.sleep(seconds)
    def snapshot(self):
        raw=self.trace.snapshot();midi=[];outstanding={}
        for event in raw['midi']:
            match=re.search(r'(\d+)$',event['device'])
            if not match:raise RuntimeError('Cannot map traced MIDI device to behavior port: '+event['device'])
            row={**event,'port':int(match.group(1)),'monotonic_ns':round(event['monotonic_seconds']*1e9)};midi.append(row)
            b=row['bytes']
            if len(b)<3:continue
            key=(row['port'],b[0]&15,b[1])
            if 144<=b[0]<=159 and b[2]>0:outstanding[key]=outstanding.get(key,0)+1
            elif 128<=b[0]<=143 or (144<=b[0]<=159 and b[2]==0):outstanding[key]=max(0,outstanding.get(key,0)-1)
        state={**raw,'midi':midi,'midi_count':len(midi),'midi_capture':{'outstanding':[list(key)+[count] for key,count in outstanding.items() if count]},'diagnostics':{'monotonic_ns':time.monotonic_ns()}}
        self.observations.append({'state':state,'source':'stock-norns-output-trace'});return state
    def wait(self,predicate,timeout=3):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            state=self.snapshot()
            if predicate(state):return state
            time.sleep(.08)
        raise AssertionError('Required observable output did not arrive')
    def tap(self,x,y):
        self.action(type='grid',x=x,y=y,state=1);self.action(type='grid',x=x,y=y,state=0);self.elapse(.06)
    def key(self,n):
        self.action(type='key',n=n,state=1);self.action(type='key',n=n,state=0);self.elapse(.06)
    def enc(self,n,steps):
        for _ in range(abs(steps)):
            self.action(type='enc',n=n,delta=1 if steps>0 else -1);self.elapse(.05)
        self.elapse(.15)
    def hold_tap(self,first,last):
        self.action(type='grid',x=first[0],y=first[1],state=1)
        try:self.tap(*last)
        finally:self.action(type='grid',x=first[0],y=first[1],state=0)
    def led_values(self,cells,expected):
        indexes=[(y-1)*16+x-1 for x,y in cells]
        state=self.wait(lambda s:[s['grid'][i] for i in indexes]==expected)
        self.results.append({'kind':'grid','cells':cells,'expected':expected,'actual':[state['grid'][i] for i in indexes]})
    def screen_header(self,text,selected=None):raise NotImplementedError(HARDWARE_DRIVER_CAPABILITIES['unsupported_semantics']['screen_header'])
    def configure(self):
        self.runner.maiden.eval("params:set('new',1); fn.dirty_screen(true); fn.dirty_grid(true)");self.elapse(.5)
        self.tap(4,8);self.tap(3,8);subpage=self.runner.channel_subpage()
        while subpage<5:self.enc(1,1);subpage=self.runner.channel_subpage()
        while subpage>5:self.enc(1,-1);subpage=self.runner.channel_subpage()
        for _ in range(self.runner.device_map_index(self.device_map_id)-1):self.enc(3,1)
        self.key(3);self.tap(5,8)
        for x in range(1,5):self.tap(x,4)
        self.tap(5,8)
        for x,y in ((1,7),(2,6),(3,5),(4,4)):self.tap(x,y)
        self.tap(5,8)
        for x,y in ((1,1),(2,2),(3,3),(4,4)):self.tap(x,y)
        self.tap(3,8);self.tap(1,2);self.hold_tap((1,4),(4,4));self.led_values([(1,2)],[15])
        if self.capture_screens:self.screens.append(self.runner.screenshot(self.artifact_prefix+'-authored'))
    def playback(self,expected,cycles=3,timeout=5,settle_seconds=0):
        assert expected and cycles>=2 and settle_seconds>=0
        self.trace.reset_midi();self.tap(1,8)
        if settle_seconds:self.elapse(settle_seconds)
        target=len(expected)*cycles+1
        state=self.wait(lambda s:len([e for e in s['midi'] if len(e['bytes'])>=3 and 144<=e['bytes'][0]<=159 and e['bytes'][2]>0])>=target,timeout)
        self.tap(1,8);self.elapse(.3);state=self.snapshot();notes=[e for e in state['midi'] if len(e['bytes'])>=3 and 144<=e['bytes'][0]<=159 and e['bytes'][2]>0]
        actual=[(e['port'],e['bytes']) for e in notes];wanted=[expected[i%len(expected)] for i in range(len(actual))]
        assert len(actual)>=target and actual==wanted,{'expected':wanted,'actual':actual}
        intervals=[notes[i+1]['monotonic_seconds']-notes[i]['monotonic_seconds'] for i in range(target-1)]
        assert all(abs(value-self.expected_step_seconds)<=.02 for value in intervals),{'tempo_bpm':self.tempo_bpm,'expected_seconds':self.expected_step_seconds,'actual_seconds':intervals}
        ons={};offs={}
        for event in state['midi']:
            b=event['bytes']
            if len(b)<3:continue
            key=(b[0]&15,b[1])
            if 144<=b[0]<=159 and b[2]>0:ons[key]=ons.get(key,0)+1
            elif 128<=b[0]<=143 or (144<=b[0]<=159 and b[2]==0):offs[key]=offs.get(key,0)+1
        assert all(offs.get(key,0)>=count for key,count in ons.items()),{'note_ons':ons,'note_offs':offs}
        result={'kind':'midi','expected':wanted,'actual':actual,'complete_cycles':cycles,'tempo_bpm':self.tempo_bpm,'expected_step_seconds':self.expected_step_seconds,'intervals_seconds':intervals,'trace':state}
        self.results.append(result);return notes
    def finish(self):
        if self.finished:return
        try:
            if self.capture_screens:self.screens.append(self.runner.screenshot(self.artifact_prefix+'-finished'))
        finally:self.trace.remove();self.finished=True

def run_hardware_case(runner,case_id,grid_device,device_map_id,trace):
    from cases import CASES
    report=hardware_applicability(CASES);row=next(item for item in report['cases'] if item['case']==case_id)
    if not row['applicable']:raise ValueError('Hardware case is not implemented: '+case_id+' ('+row['category']+')')
    driver=HardwareDriver(runner,grid_device,device_map_id,trace)
    try:CASES[case_id]['run'](driver)
    finally:driver.finish()
    midi=[x for x in driver.results if x['kind']=='midi'];blink=next(x for x in driver.results if x['kind']=='selected-pattern-blink-cycle')
    phrases=[{'expected_cycle':[value[1] for value in item['expected'][:4]],'captured_note_ons':[value[1] for value in item['actual']],
              'tempo_bpm':item['tempo_bpm'],'expected_step_seconds':item['expected_step_seconds'],
              'first_twelve_intervals_seconds':item['intervals_seconds'],'trace':item['trace']} for item in midi]
    return {'case':case_id,'actions':driver.recipe,'screens':driver.screens,'screen_changed':len(driver.screens)>1 and driver.screens[0]['sha256']!=driver.screens[-1]['sha256'],'configured_grid_observed':True,'edited_grid_observed':True,'selected_pattern_blink_levels':sorted(blink['levels']),'tempo_bpm':driver.tempo_bpm,'expected_step_seconds':driver.expected_step_seconds,'phrases':phrases,'physical_grid_driver_commands_observed':True,'physical_grid_led_photons_observed':False,'midi_driver_boundary_observed':True,'hardware_applicability':row,'hardware_capabilities':HARDWARE_DRIVER_CAPABILITIES}

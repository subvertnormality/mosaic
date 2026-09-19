import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from hardware_performance import CASES,OnDeviceResourceSampler,dense_oracle,resource_metrics,run_hardware_performance,select_fixture_parameter,write_fixture_manifest
import hardware_performance

def dense_events(channels,steps=32,step_ns=250_000_000):
    rows=[];index=0
    for step in range(steps):
        for channel in range(channels):index+=1;rows.append({'index':index,'monotonic_ns':1_000_000_000+step*step_ns+channel*1000,'port':1,'bytes':[144+channel,60,100]})
        for channel in range(channels):index+=1;rows.append({'index':index,'monotonic_ns':1_100_000_000+step*step_ns+channel*1000,'port':1,'bytes':[128+channel,60,0]})
    return rows

_transport_patch=None
def setUpModule():
    # Fake runners have no Maiden; their transport is always ready and stops when asked.
    global _transport_patch
    _transport_patch=patch('hardware_performance.transport_state',return_value=(False,[]));_transport_patch.start()
def tearDownModule():
    _transport_patch.stop()

class TransportChecks(unittest.TestCase):
    def test_a_window_starts_only_stopped_with_no_key_held(self):
        actions=[];taps=[]
        driver=type('D',(),{'action':lambda self,**k:actions.append(k),'elapse':lambda self,s:None,'tap':lambda self,x,y:taps.append((x,y))})()
        states=iter([(True,[(3,5)]),(False,[])])
        with patch('hardware_performance.transport_state',side_effect=lambda runner:next(states)):
            log=[];hardware_performance.ready_to_play(object(),driver,log)
        self.assertEqual(actions,[{'type':'grid','x':3,'y':5,'state':0}]);self.assertEqual(taps,[(1,8)])
        self.assertEqual(log[0]['held_keys_released'],[(3,5)]);self.assertTrue(log[0]['was_playing'])
        with patch('hardware_performance.transport_state',return_value=(True,[])):
            with self.assertRaisesRegex(AssertionError,'Transport not ready'):hardware_performance.ready_to_play(object(),driver,[])
    def test_a_transport_still_playing_after_the_window_is_reported(self):
        with patch('hardware_performance.transport_state',return_value=(True,[(1,8)])):
            log=[];self.assertFalse(hardware_performance.stopped_after_window(object(),log))
        self.assertEqual(log,[{'stopped_after_window':False,'held_keys':[(1,8)]}])

def saved_fixture(workload,channels):
    import hashlib
    directory=Path(tempfile.mkdtemp())
    (directory/'autosave.ptn').write_text('ptn');(directory/'autosave.pset').write_text('pset')
    files={name:hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in ('autosave.ptn','autosave.pset')}
    (directory/'fixture.json').write_text(json.dumps({'case':'built','workload':workload,'channels':channels,'files':files,
        'midi_lock_lead_time':0,'timing_contract':'legacy-delay-v1','seed':0,'probe_mode':'off'}))
    return directory

class FakeSSH:
    def run(self,script):
        identity={'kind':'identity','clock_ticks_per_second':100,'matron_pid':12,'matron_start_ticks':3}
        samples=[{'kind':'sample','monotonic_ns':1_000_000_000,'matron_cpu_ticks':20,'matron_rss_bytes':1000,'load':[.1,.2,.3],'thermal_millicelsius_max':40000,'throttled_flags':0},{'kind':'sample','monotonic_ns':2_000_000_000,'matron_cpu_ticks':70,'matron_rss_bytes':1200,'load':[.4,.2,.3],'thermal_millicelsius_max':42000,'throttled_flags':2}]
        return type('R',(),{'stdout':'\n'.join(json.dumps(x) for x in [identity]+samples)})()

class FakeSampler:
    def __init__(self):self.thread=True;self.started=0;self.stopped=0
    def start(self):self.started+=1
    def stop(self):
        self.stopped+=1
        return {'identity':{'clock_ticks_per_second':100,'matron_pid':12,'matron_start_ticks':3},'samples':[{'monotonic_ns':1_000_000_000,'matron_cpu_ticks':20,'matron_rss_bytes':1000,'load':[.1,.2,.3],'thermal_millicelsius_max':40000,'throttled_flags':0},{'monotonic_ns':2_000_000_000,'matron_cpu_ticks':70,'matron_rss_bytes':1200,'load':[.4,.2,.3],'thermal_millicelsius_max':42000,'throttled_flags':2}]}

class FakeTrace:
    def __init__(self):self.resets=0
    def reset(self):self.resets+=1

def preflight_reply(source, lead=0, contract='legacy-delay-v1'):
    """Answer the two preflight reads the way the device would."""
    if '__MOSAIC_LOCK_LEAD__' in source: return '__MOSAIC_LOCK_LEAD__%s' % lead
    if '__MOSAIC_LOCK_CONTRACT__' in source: return '__MOSAIC_LOCK_CONTRACT__%s' % contract
    return ''

class FakeMaiden:
    def eval(self,source):
        return preflight_reply(source)

class FakeDriver:
    def __init__(self,*args,**kwargs):
        self.expected_step_seconds=.25;self.tempo_bpm=60;self.finished=0
        self.runner=type('R',(),{'maiden':type('M',(),{'eval':lambda self,source:preflight_reply(source)})()})()
    def tap(self,*args):pass
    def key(self,*args):pass
    def enc(self,*args):pass
    def elapse(self,*args):pass
    def led_values(self,*args):pass
    def snapshot(self):return {'midi':dense_events(1),'grid_writes':4,'grid_refreshes':2}
    def finish(self):self.finished+=1

class Tests(unittest.TestCase):
    def test_fixture_manifest_carries_explicit_lead_probe_and_timing_identity(self):
        source=Path(tempfile.mkdtemp());fixture=Path(tempfile.mkdtemp())
        (fixture/'autosave.ptn').write_text('ptn');(fixture/'autosave.pset').write_text('pset')
        write_fixture_manifest(fixture,'PERF-002-HW-1',CASES['PERF-002-HW-1'],source,lead_ms=25,timing_contract='legacy-delay-v1',seed=871,probe_mode='pulse-v1')
        manifest=json.loads((fixture/'fixture.json').read_text())
        self.assertEqual(manifest['midi_lock_lead_time'],25)
        self.assertEqual(manifest['timing_contract'],'legacy-delay-v1')
        self.assertEqual(manifest['seed'],871)
        self.assertEqual(manifest['probe_mode'],'pulse-v1')

    def test_loaded_fixture_rejects_missing_lead_identity_instead_of_defaulting_to_zero(self):
        fixture=saved_fixture('dense',1)
        manifest=json.loads((fixture/'fixture.json').read_text());del manifest['midi_lock_lead_time'];(fixture/'fixture.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'midi_lock_lead_time'):
            hardware_performance.check_project_fixture(fixture,'PERF-002-HW-1')

    def test_preflight_sets_and_reads_back_the_requested_public_lock_lead(self):
        calls=[]
        maiden=type('M',(),{'eval':lambda self,source:calls.append(source) or preflight_reply(source,25)})()
        driver=type('D',(),{'runner':type('R',(),{'maiden':maiden})()})()
        self.assertEqual(hardware_performance.set_lock_lead(driver,25),25)
        self.assertEqual(len(calls),2)
        self.assertIn("params:set('midi_lock_lead_time',25)",calls[0])
        self.assertIn("params:get('midi_lock_lead_time')",calls[0])

    def test_preflight_rejects_a_lock_lead_readback_mismatch_before_play(self):
        maiden=type('M',(),{'eval':lambda self,source:preflight_reply(source,24)})()
        driver=type('D',(),{'runner':type('R',(),{'maiden':maiden})()})()
        with self.assertRaisesRegex(AssertionError,'requested 25.*observed 24'):
            hardware_performance.set_lock_lead(driver,25)

    def test_preflight_sets_and_reads_back_the_requested_timing_contract(self):
        calls=[]
        maiden=type('M',(),{'eval':lambda self,source:calls.append(source) or preflight_reply(source,25,'pulse-advance')})()
        driver=type('D',(),{'runner':type('R',(),{'maiden':maiden})()})()
        self.assertEqual(hardware_performance.set_lock_lead(driver,25,'pulse-advance'),25)
        self.assertIn("m_clock.set_lock_contract('pulse-advance')",calls[1])
        self.assertIn('m_clock.get_lock_contract()',calls[1])

    def test_preflight_rejects_a_timing_contract_readback_mismatch_before_play(self):
        # A run must never measure a different contract from the one it claims.
        maiden=type('M',(),{'eval':lambda self,source:preflight_reply(source,25,'legacy-delay-v1')})()
        driver=type('D',(),{'runner':type('R',(),{'maiden':maiden})()})()
        with self.assertRaisesRegex(AssertionError,'requested pulse-advance.*observed legacy-delay-v1'):
            hardware_performance.set_lock_lead(driver,25,'pulse-advance')

    def test_timing_contract_identity_accepts_both_contracts_and_rejects_anything_else(self):
        for contract in ('legacy-delay-v1','pulse-advance'):
            self.assertEqual(hardware_performance._lead_identity(25,contract,0,'off')['timing_contract'],contract)
        for bad in ('lookahead','pulse_advance','',None):
            with self.assertRaises(ValueError):
                hardware_performance._lead_identity(25,bad,0,'off')

    def test_hardware_slide_parameter_selection_is_front_panel_only(self):
        calls=[];maiden=type('M',(),{'eval':lambda self,code:calls.append(('query',code)) or '__MOSAIC_PARAM_POSITION__3/9'})()
        driver=type('D',(),{'runner':type('R',(),{'maiden':maiden})(),'key':lambda self,n:calls.append(('key',n)),'enc':lambda self,n,v:calls.append(('enc',n,v))})()
        select_fixture_parameter(driver,'CC 1');self.assertEqual(calls[0][0],'query');self.assertIn("p.name=='CC 1'",calls[0][1]);self.assertEqual(calls[1:],[('key',2),('enc',3,-11),('enc',3,2),('key',3),('key',2)])
        with self.assertRaises(ValueError):select_fixture_parameter(driver,'not-fixture-parameter')
        with self.assertRaises(ValueError):select_fixture_parameter(driver,'CC 5')
        calls.clear();select_fixture_parameter(driver,'CC 4');self.assertIn("p.name=='CC 4'",calls[0][1])
    def test_timing_trace_wrappers_pass_arguments_through_exactly(self):
        import shutil,subprocess
        from hardware_performance import TimingTrace
        lua=shutil.which('lua5.3')
        if not lua:self.skipTest('lua5.3 unavailable')
        check=("util={time=os.clock}; _norns={screen_update=function(...) if select('#',...)~=0 then error('requires 0 arguments') end end}; "
               "local seen; clock={resume=function(...) seen={select('#',...),...} end}; m_grid={grid_redraw=function(...) assert(select('#',...)==0) end}; "
               "scheduler={update=function(...) assert(select('#',...)==0) end}; function redraw(...) assert(select('#',...)==0) end; "
               "assert(load(io.read('a')))(); _norns.screen_update(); m_grid.grid_redraw(); redraw(); scheduler.update(); clock.resume(7,1.5); "
               "assert(seen[1]==2 and seen[2]==7 and seen[3]==1.5); assert(load("+repr(TimingTrace.REMOVE)+"))(); assert(_MOSAIC_TT==nil); print('ok')")
        result=subprocess.run([lua,'-e',check],input=TimingTrace.INSTALL,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('ok',result.stdout)
    def test_lock_oracle_checks_every_parameter_value_per_step(self):
        from dense_workload import LOCK_PARAMETERS,lock_values
        def lock_events(channels,steps=20,corrupt=None):
            rows=[];index=0
            for channel in range(channels):
                for parameter in LOCK_PARAMETERS:index+=1;rows.append({'index':index,'monotonic_ns':900_000_000+index,'port':1,'bytes':[176+channel,parameter,lock_values(parameter)[5]]})
            for step in range(steps):
                for channel in range(channels):
                    for parameter in LOCK_PARAMETERS:
                        value=lock_values(parameter)[step%16]
                        if corrupt==(step,channel,parameter):value=value+1
                        index+=1;rows.append({'index':index,'monotonic_ns':1_000_000_000+step*250_000_000+index,'port':1,'bytes':[176+channel,parameter,value]})
                    index+=1;rows.append({'index':index,'monotonic_ns':1_000_000_000+step*250_000_000+index,'port':1,'bytes':[144+channel,60,100]})
                for channel in range(channels):index+=1;rows.append({'index':index,'monotonic_ns':1_100_000_000+step*250_000_000+index,'port':1,'bytes':[128+channel,60,0]})
            return rows
        value=dense_oracle(lock_events(2),2,4,.25,'locks')
        self.assertEqual(value['lock_values_checked'],2*4*20);self.assertIsNone(value['slide_cycles_checked'])
        self.assertIsNone(dense_oracle(dense_events(2,4),2,1,.25,'dense')['lock_values_checked'])
        with self.assertRaises(AssertionError):dense_oracle(lock_events(2,corrupt=(8,1,3)),2,4,.25,'locks')
        with self.assertRaisesRegex(AssertionError,'Lock cycle incomplete'):dense_oracle(lock_events(1,steps=8),1,2,.25,'locks')
    def test_a_workload_sounding_every_other_step_is_timed_on_a_grid_twice_as_wide(self):
        events=dense_events(2,steps=16,step_ns=500_000_000)
        value=dense_oracle(events,2,8,.25,'extreme',step_stride=2)
        self.assertEqual(value['steps'],16);self.assertTrue(value['gates']['event_timing'])
        self.assertEqual(value['step_jitter']['maximum_ns'],0)
        with self.assertRaisesRegex(AssertionError,'Step count'):dense_oracle(events,2,8,.25,'extreme')
        self.assertEqual(CASES['PERF-EXT-HW-16']['step_stride'],2)
    def test_one_stalled_step_per_window_is_tolerated_but_two_are_not(self):
        def stalled(steps_late):
            events=dense_events(2,steps=32)
            for event in events:
                step=(event['monotonic_ns']-1_000_000_000)//250_000_000
                if step in steps_late:event['monotonic_ns']+=15_000_000
            return events
        clean=dense_oracle(dense_events(2,steps=32),2,8,.25,'dense')
        one=dense_oracle(stalled({10}),2,8,.25,'dense')
        self.assertGreater(one['timing']['p99_ns'],10_000_000)
        self.assertEqual(one['timing_one_stall_tolerated']['excluded_step'],10)
        self.assertEqual(one['timing_one_stall_tolerated']['excluded_step_maximum_ns'],15_000_000+1000)
        self.assertTrue(one['gates']['event_timing'])
        two=dense_oracle(stalled({10,20}),2,8,.25,'dense')
        self.assertFalse(two['gates']['event_timing'],'Two stalled steps in one window must fail')
        self.assertTrue(clean['gates']['event_timing'])
    def test_dense_oracle_reuses_complete_order_timing_release_and_skip_gates(self):
        value=dense_oracle(dense_events(2,4),2,1,.25,'dense')
        self.assertTrue(value['passed']);self.assertEqual((value['steps'],value['note_ons'],value['note_offs']),(4,8,8));self.assertEqual(value['skipped_deadlines'],0);self.assertEqual(value['timing']['maximum_ns'],1000)
        broken=dense_events(2,4);broken[1]['bytes'][0]=144
        with self.assertRaisesRegex(AssertionError,'Channels at step'):dense_oracle(broken,2,1,.25,'dense')
        tailed=dense_oracle(dense_events(1,6),1,1,.25,'dense');self.assertEqual((tailed['steps'],tailed['captured_steps'],tailed['note_ons']),(4,6,6))
    def test_resource_sampler_and_metrics_report_matron_load_thermal_and_throttle(self):
        sampler=OnDeviceResourceSampler(FakeSSH(),.01,.01);sampler.start();recording=sampler.stop();metrics=resource_metrics(recording)
        self.assertEqual(metrics['sample_count'],2);self.assertEqual(metrics['matron_peak_rss_bytes'],1200);self.assertEqual(metrics['thermal_millicelsius_peak'],42000);self.assertEqual(metrics['throttled_flags_or'],2);self.assertEqual(metrics['threshold_status'],'calibration-only')
    def test_gated_cases_fix_their_tempo_and_calibration_cases_take_the_requested_one(self):
        self.assertEqual({case:CASES[case]['tempo_bpm'] for case in ('PERF-002-HW-16','PERF-003-HW-16','PERF-009-HW-16','PERF-010-HW-16')},
                         {'PERF-002-HW-16':130,'PERF-003-HW-16':130,'PERF-009-HW-16':130,'PERF-010-HW-16':200})
        self.assertEqual((CASES['PERF-010-HW-16']['workload'],CASES['PERF-010-HW-16']['step_stride']),('extreme',2))
        self.assertEqual(hardware_performance.case_tempo('PERF-010-HW-16'),200)
        self.assertEqual(hardware_performance.case_tempo('PERF-002-HW-16',130.0),130)
        with self.assertRaisesRegex(ValueError,'PERF-009-HW-16 runs at 130 bpm, not 90'):hardware_performance.case_tempo('PERF-009-HW-16',90)
        self.assertEqual(hardware_performance.case_tempo('PERF-002-HW-4',90),90);self.assertIsNone(hardware_performance.case_tempo('PERF-002-HW-1'))
        self.assertEqual(hardware_performance.project_fixture_name('PERF-010-HW-16'),'extreme-16')
    def test_a_fixed_tempo_case_refuses_a_norns_clock_at_another_tempo(self):
        runner=type('R',(),{'maiden':FakeMaiden(),'ssh':object(),'out':Path(tempfile.mkdtemp())})()
        with patch('hardware_performance.HardwareDriver',FakeDriver),patch('hardware_performance.build_project'),patch('hardware_performance.time.sleep'):
            with self.assertRaisesRegex(AssertionError,'PERF-002-HW-16 runs at 130 bpm but the norns clock is at 60'):
                run_hardware_performance(runner,'PERF-002-HW-16',2,'map',runner.out,FakeTrace(),FakeSampler())
    def test_three_calibration_cases_and_trace_start_boundary(self):
        self.assertEqual(set(CASES),{'PERF-002-HW-1','PERF-002-HW-4','PERF-002-HW-8','PERF-002-HW-16','PERF-003-HW-1','PERF-003-HW-8','PERF-003-HW-16','PERF-005-HW-1','PERF-005-HW-4','PERF-008L-HW-4','MIX-HW-8','PERF-009-HW-4','PERF-009-HW-8','PERF-009-HW-16','PERF-EXT-HW-16','PERF-010-HW-16'})
        trace=FakeTrace();sampler=FakeSampler();source=Path(tempfile.mkdtemp());runner=type('R',(),{'maiden':FakeMaiden(),'ssh':object(),'out':source})()
        with patch('hardware_performance.HardwareDriver',FakeDriver),patch('hardware_performance.build_project') as build,patch('hardware_performance.source_identity',return_value={'mosaic_revision':'abc','dirty_patch_sha256':None}),patch('hardware_performance.time.sleep'):
            value=run_hardware_performance(runner,'PERF-002-HW-1',2,'map',source,trace,sampler)
        build.assert_called_once();self.assertEqual(build.call_args.args[1:3],(1,'dense'));self.assertIs(build.call_args.args[3],select_fixture_parameter);self.assertEqual(trace.resets,2);self.assertEqual((sampler.started,sampler.stopped),(1,1));self.assertTrue(value['passed']);self.assertTrue(value['trace_boundary']['reset_before_sampler_and_play']);self.assertEqual(value['source_identity']['mosaic_revision'],'abc')
    def test_raw_performance_evidence_survives_oracle_failure(self):
        trace=FakeTrace();sampler=FakeSampler();source=Path(tempfile.mkdtemp());runner=type('R',(),{'maiden':FakeMaiden(),'ssh':object(),'out':source})()
        with patch('hardware_performance.HardwareDriver',FakeDriver),patch('hardware_performance.build_project'),patch('hardware_performance.dense_oracle',side_effect=AssertionError('timing oracle failed')),patch('hardware_performance.time.sleep'):
            with self.assertRaisesRegex(AssertionError,'timing oracle failed'):run_hardware_performance(runner,'PERF-002-HW-1',2,'map',source,trace,sampler)
        raw=json.loads((source/'performance-raw.json').read_text());self.assertEqual(len(raw['midi']),64);self.assertEqual((sampler.started,sampler.stopped),(1,1))

    def test_a_loaded_project_fixture_skips_the_ui_build(self):
        trace=FakeTrace();sampler=FakeSampler();source=Path(tempfile.mkdtemp());runner=type('R',(),{'maiden':FakeMaiden(),'ssh':object(),'out':source})()
        fixture=saved_fixture('dense',1)
        with patch('hardware_performance.HardwareDriver',FakeDriver),patch('hardware_performance.build_project') as build,patch('hardware_performance.source_identity',return_value={'mosaic_revision':'abc','dirty_patch_sha256':None}),patch('hardware_performance.time.sleep'):
            run_hardware_performance(runner,'PERF-002-HW-1',2,'map',source,trace,sampler,project_fixture=fixture)
        build.assert_not_called()
    def test_a_fixture_is_matched_on_the_project_a_case_plays(self):
        fixture=saved_fixture('dense',4)
        for case_id in ('PERF-002-HW-4','PERF-005-HW-4','PERF-008L-HW-4'):
            self.assertEqual(hardware_performance.check_project_fixture(fixture,case_id)['channels'],4)
            self.assertEqual(hardware_performance.project_fixture_name(case_id),'dense-4')
        self.assertEqual(hardware_performance.project_fixture_name('MIX-HW-8'),'slides-8')
        with self.assertRaisesRegex(ValueError,'holds dense/4'):hardware_performance.check_project_fixture(fixture,'PERF-002-HW-8')
        with self.assertRaisesRegex(ValueError,'holds dense/4'):hardware_performance.check_project_fixture(fixture,'PERF-009-HW-4')
    def test_a_fixture_saved_with_another_trig_spacing_is_refused(self):
        fixture=saved_fixture('extreme',16)
        with self.assertRaisesRegex(ValueError,'trig every 1 steps'):hardware_performance.check_project_fixture(fixture,'PERF-EXT-HW-16')
    def test_a_fixture_whose_files_changed_since_saving_is_refused(self):
        fixture=saved_fixture('locks',8);(fixture/'autosave.ptn').write_text('edited')
        with self.assertRaisesRegex(ValueError,'does not match its manifest'):hardware_performance.check_project_fixture(fixture,'PERF-009-HW-8')
        missing=Path(tempfile.mkdtemp())
        with self.assertRaisesRegex(ValueError,'no fixture.json'):hardware_performance.check_project_fixture(missing,'PERF-009-HW-8')
    def test_every_checked_in_fixture_matches_its_manifest(self):
        root=Path(__file__).resolve().parent/'fixtures'/'performance'/'cm3plus';cases={}
        for case_id in CASES:cases.setdefault(hardware_performance.project_fixture_name(case_id),case_id)
        for directory in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []:
            self.assertIn(directory.name,cases,'Fixture for a project no case plays: '+directory.name)
            # These are historical source artifacts. Their hashes must remain
            # valid, but they deliberately lack a lead identity and may never
            # be silently reinterpreted as a lead-zero fixture.
            manifest=json.loads((directory/'fixture.json').read_text())
            self.assertEqual(set(manifest['files']), {'autosave.ptn', 'autosave.pset'})
            for name, expected_hash in manifest['files'].items():
                self.assertEqual(hashlib.sha256((directory/name).read_bytes()).hexdigest(), expected_hash,
                                 'Historical fixture hash changed: '+str(directory/name))
            with self.assertRaisesRegex(ValueError,'missing midi_lock_lead_time'):
                hardware_performance.check_project_fixture(directory,cases[directory.name])
    def test_saving_a_project_fixture_builds_then_fetches_and_records_it(self):
        trace=FakeTrace();sampler=FakeSampler();source=Path(tempfile.mkdtemp());saved=Path(tempfile.mkdtemp())/'fixture'
        fetched=[]
        def fetch(destination):
            destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
            (destination/'autosave.ptn').write_text('ptn');(destination/'autosave.pset').write_text('pset');fetched.append(destination)
        runner=type('R',(),{'maiden':FakeMaiden(),'ssh':object(),'out':source,'fetch_project':staticmethod(fetch)})()
        with patch('hardware_performance.HardwareDriver',FakeDriver),patch('hardware_performance.build_project') as build,patch('hardware_performance.source_identity',return_value={'mosaic_revision':'abc','dirty_patch_sha256':None}),patch('hardware_performance.time.sleep'):
            run_hardware_performance(runner,'PERF-002-HW-1',2,'map',source,trace,sampler,save_project_fixture=saved)
        build.assert_called_once();self.assertEqual(fetched,[saved])
        manifest=json.loads((saved/'fixture.json').read_text())
        self.assertEqual((manifest['case'],manifest['workload'],manifest['channels']),('PERF-002-HW-1','dense',1))
        self.assertEqual(set(manifest['files']),{'autosave.ptn','autosave.pset'})

if __name__=='__main__':unittest.main()


class StepJitterGate(unittest.TestCase):
    """Where a step starts is the tempo a player hears; how far its own notes
    spread is a separate, ordered offset. They are gated separately."""

    def test_the_shared_thresholds_carry_a_step_jitter_gate(self):
        shared = hardware_performance.TIMING_THRESHOLDS
        self.assertEqual(shared['step_jitter_p95_ns'], 5_000_000)
        self.assertEqual(shared['step_jitter_maximum_ns'], 10_000_000)

    def test_every_case_shares_one_event_timing_threshold(self):
        self.assertEqual(shared_p99 := hardware_performance.TIMING_THRESHOLDS['p99_ns'], 10_000_000)
        self.assertFalse(hasattr(hardware_performance, 'CASE_TIMING_THRESHOLDS'),
                         'A per-case relaxation would need its own hardware measurement')

import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

from hardware_performance import CASES,OnDeviceResourceSampler,dense_oracle,resource_metrics,run_hardware_performance,select_fixture_parameter
import hardware_performance

def dense_events(channels,steps=32,step_ns=250_000_000):
    rows=[];index=0
    for step in range(steps):
        for channel in range(channels):index+=1;rows.append({'index':index,'monotonic_ns':1_000_000_000+step*step_ns+channel*1000,'port':1,'bytes':[144+channel,60,100]})
        for channel in range(channels):index+=1;rows.append({'index':index,'monotonic_ns':1_100_000_000+step*step_ns+channel*1000,'port':1,'bytes':[128+channel,60,0]})
    return rows

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

class FakeDriver:
    def __init__(self,*args,**kwargs):self.expected_step_seconds=.25;self.tempo_bpm=60;self.finished=0
    def tap(self,*args):pass
    def key(self,*args):pass
    def enc(self,*args):pass
    def elapse(self,*args):pass
    def led_values(self,*args):pass
    def snapshot(self):return {'midi':dense_events(1),'grid_writes':4,'grid_refreshes':2}
    def finish(self):self.finished+=1

class Tests(unittest.TestCase):
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
    def test_dense_oracle_reuses_complete_order_timing_release_and_skip_gates(self):
        value=dense_oracle(dense_events(2,4),2,1,.25,'dense')
        self.assertTrue(value['passed']);self.assertEqual((value['steps'],value['note_ons'],value['note_offs']),(4,8,8));self.assertEqual(value['skipped_deadlines'],0);self.assertEqual(value['timing']['maximum_ns'],1000)
        broken=dense_events(2,4);broken[1]['bytes'][0]=144
        with self.assertRaisesRegex(AssertionError,'Channels at step'):dense_oracle(broken,2,1,.25,'dense')
        tailed=dense_oracle(dense_events(1,6),1,1,.25,'dense');self.assertEqual((tailed['steps'],tailed['captured_steps'],tailed['note_ons']),(4,6,6))
    def test_resource_sampler_and_metrics_report_matron_load_thermal_and_throttle(self):
        sampler=OnDeviceResourceSampler(FakeSSH(),.01,.01);sampler.start();recording=sampler.stop();metrics=resource_metrics(recording)
        self.assertEqual(metrics['sample_count'],2);self.assertEqual(metrics['matron_peak_rss_bytes'],1200);self.assertEqual(metrics['thermal_millicelsius_peak'],42000);self.assertEqual(metrics['throttled_flags_or'],2);self.assertEqual(metrics['threshold_status'],'calibration-only')
    def test_three_calibration_cases_and_trace_start_boundary(self):
        self.assertEqual(set(CASES),{'PERF-002-HW-1','PERF-002-HW-4','PERF-002-HW-8','PERF-002-HW-16','PERF-003-HW-1','PERF-003-HW-8','PERF-003-HW-16','PERF-005-HW-1','PERF-005-HW-4','PERF-008L-HW-4','MIX-HW-8','PERF-009-HW-4','PERF-009-HW-8','PERF-009-HW-16'})
        trace=FakeTrace();sampler=FakeSampler();source=Path(tempfile.mkdtemp());runner=type('R',(),{'maiden':object(),'ssh':object(),'out':source})()
        with patch('hardware_performance.HardwareDriver',FakeDriver),patch('hardware_performance.build_project') as build,patch('hardware_performance.source_identity',return_value={'mosaic_revision':'abc','dirty_patch_sha256':None}),patch('hardware_performance.time.sleep'):
            value=run_hardware_performance(runner,'PERF-002-HW-1',2,'map',source,trace,sampler)
        build.assert_called_once();self.assertEqual(build.call_args.args[1:3],(1,'dense'));self.assertIs(build.call_args.args[3],select_fixture_parameter);self.assertEqual(trace.resets,2);self.assertEqual((sampler.started,sampler.stopped),(1,1));self.assertTrue(value['passed']);self.assertTrue(value['trace_boundary']['reset_before_sampler_and_play']);self.assertEqual(value['source_identity']['mosaic_revision'],'abc')
    def test_raw_performance_evidence_survives_oracle_failure(self):
        trace=FakeTrace();sampler=FakeSampler();source=Path(tempfile.mkdtemp());runner=type('R',(),{'maiden':object(),'ssh':object(),'out':source})()
        with patch('hardware_performance.HardwareDriver',FakeDriver),patch('hardware_performance.build_project'),patch('hardware_performance.dense_oracle',side_effect=AssertionError('timing oracle failed')),patch('hardware_performance.time.sleep'):
            with self.assertRaisesRegex(AssertionError,'timing oracle failed'):run_hardware_performance(runner,'PERF-002-HW-1',2,'map',source,trace,sampler)
        raw=json.loads((source/'performance-raw.json').read_text());self.assertEqual(len(raw['midi']),64);self.assertEqual((sampler.started,sampler.stopped),(1,1))

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

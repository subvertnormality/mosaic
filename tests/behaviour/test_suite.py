"""The regression runner must fail closed and compare by item, not by count."""
import contextlib,io,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import suite

def report(cases,layers=None,passed=True):
    return dict(passed=passed,complete_regression_run=False,
                cases=[dict(case=c,lane=l,passed=p) for c,l,p in cases],layers=layers or {})

class CompareTests(unittest.TestCase):
    def compare(self,base,new):
        with tempfile.TemporaryDirectory() as tmp:
            paths=[Path(tmp)/'b.json',Path(tmp)/'n.json']
            for path,value in zip(paths,(base,new)):path.write_text(json.dumps(value))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code=suite.compare(SimpleNamespace(baseline=str(paths[0]),candidate=str(paths[1])))
            return code,json.loads(out.getvalue())

    def test_pass_to_fail_and_missing_items_are_regressions(self):
        base=report([('A','real-time',True),('B','real-time',True),('C','real-time',False)],
                    layers={'lua_units':dict(name='lua-units',passed=True)})
        new=report([('A','real-time',False),('C','real-time',True),('D','real-time',True)],
                   layers={'lua_units':dict(name='lua-units',passed=True)},passed=False)
        code,result=self.compare(base,new)
        self.assertEqual(code,1)
        self.assertEqual(result['regressions'],['case/A/real-time','case/B/real-time'])
        self.assertEqual(result['fixed'],['case/C/real-time'])
        self.assertEqual(result['added'],['case/D/real-time'])

    def test_identical_passing_reports_compare_clean(self):
        value=report([('A','controlled-experimental',True)],layers={'python':[dict(name='test_x',passed=True)]})
        code,result=self.compare(value,value)
        self.assertEqual((code,result['regressions'],result['fixed'],result['added']),(0,[],[],[]))

    def test_a_layer_regression_fails_even_with_all_cases_green(self):
        base=report([('A','real-time',True)],layers={'python':[dict(name='test_x',passed=True)]})
        new=report([('A','real-time',True)],layers={'python':[dict(name='test_x',passed=None)]})
        code,result=self.compare(base,new)
        self.assertEqual((code,result['regressions']),(1,['layer/python/test_x']))

class FailureClassTests(unittest.TestCase):
    def test_native_startup_is_not_a_case_result(self):
        crone='ContractError: crone exited -6; /x/crone.log; cleanup also failed'
        timeout='ContractError: sclang did not reach AudioContext: initPolls; inspect /x'
        self.assertEqual([suite.failure_class(dict(failure=f)) for f in (crone,timeout)],['native-startup']*2)
        for failure in ("AssertionError: ('Onset phase', 0, 19255089)",None,'ContractError: midi_drop'):
            self.assertEqual(suite.failure_class(dict(failure=failure)),'case')

class StartGateTests(unittest.TestCase):
    def test_launches_are_spaced_by_the_interval(self):
        import threading,time
        gate=suite.StartGate(.2);times=[]
        def launch():gate.wait();times.append(time.monotonic())
        threads=[threading.Thread(target=launch) for _ in range(3)]
        for t in threads:t.start()
        for t in threads:t.join()
        times.sort()
        self.assertTrue(all(b-a>=.19 for a,b in zip(times,times[1:])),times)

class CollectionTests(unittest.TestCase):
    def test_every_existing_test_file_is_classified(self):
        lua,python=suite.collect(set(suite.case_registry()))
        self.assertIn('pentatonic_options',{Path(p).stem for p in suite.BEHAVIOUR.glob('*.py')})
        self.assertEqual(set(python),{p.stem for p in suite.BEHAVIOUR.glob('test_*.py')})
        self.assertEqual(set(lua),{p.name for p in suite.BEHAVIOUR.glob('*.lua')})

    def test_unclassified_or_stale_declarations_fail(self):
        cases=set(suite.case_registry())
        with patch.object(suite,'PYTHON_UNITTEST',suite.PYTHON_UNITTEST-{'test_midi_window'}):
            with self.assertRaisesRegex(SystemExit,'test_midi_window'):suite.collect(cases)
        with patch.object(suite,'LUA_ARGUMENT',dict(suite.LUA_ARGUMENT,**{'gone.lua':'norns-root'})):
            with self.assertRaisesRegex(SystemExit,'gone.lua'):suite.collect(cases)
        with self.assertRaisesRegex(SystemExit,'M-MOD-001'):suite.collect(cases-{'M-MOD-001'})

class TreeIdentityTests(unittest.TestCase):
    def test_runner_is_excluded_from_the_tested_tree(self):
        state=suite.source_state(exclude_runner=True)
        self.assertNotIn(suite.RUNNER,state['files'])
        self.assertIn('lib/step.lua',state['files'])
        self.assertTrue(suite.same_tested_tree(state))
        changed=dict(state,files=dict(state['files'],**{'lib/step.lua':'0'*64}))
        self.assertFalse(suite.same_tested_tree(changed))

class SchedulingTests(unittest.TestCase):
    def test_session_budget_fits_the_jack_server_cap(self):
        self.assertEqual(suite.session_budget({'real-time':3,'controlled-experimental':5},0),{'real-time':3,'controlled-experimental':5})
        self.assertEqual(suite.session_budget({'real-time':3,'controlled-experimental':5},2),{'real-time':3,'controlled-experimental':3})
        self.assertEqual(suite.session_budget({'real-time':6,'controlled-experimental':6},0,cap=8),{'real-time':4,'controlled-experimental':4})
        self.assertEqual(suite.session_budget({'real-time':0},7),{'real-time':1})
        with self.assertRaises(SystemExit):suite.session_budget({'real-time':1,'controlled-experimental':1},7)
        self.assertEqual(suite.JACK_SERVER_CAP,8)

    def test_longest_first_puts_unknown_then_longest_cases_first(self):
        jobs=[('A','real-time','base-midi'),('B','real-time','base-midi'),('C','real-time','base-midi'),('D','real-time','base-midi')]
        durations={('A','real-time'):10,('B','real-time'):600,('D','real-time'):10}
        self.assertEqual([j[0] for j in suite.longest_first(jobs,durations)],['C','B','A','D'])

    def test_recorded_durations_reads_case_seconds(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'suite.json'
            path.write_text(json.dumps(dict(cases=[dict(case='A',lane='real-time',seconds=12.5),dict(case='B',lane='real-time')])))
            self.assertEqual(suite.recorded_durations(str(path)),{('A','real-time'):12.5})
        self.assertEqual(suite.recorded_durations(None),{})

    def test_lanes_run_concurrently_within_each_lane_budget(self):
        import threading,time
        active={'a':0,'b':0};peak={'a':0,'b':0};both=[False];lock=threading.Lock();seen=[]
        def run_one(job):
            lane=job[1]
            with lock:
                active[lane]+=1;peak[lane]=max(peak[lane],active[lane])
                if active['a'] and active['b']:both[0]=True
            time.sleep(.05)
            with lock:active[lane]-=1
            return dict(case=job[0])
        jobs={'a':[(str(i),'a','p') for i in range(6)],'b':[(str(i),'b','p') for i in range(6)]}
        suite.execute_lanes(jobs,{'a':2,'b':3},run_one,lambda lane,done,total,row:seen.append((lane,row['case'])))
        self.assertTrue(both[0]);self.assertEqual(peak,{'a':2,'b':3});self.assertEqual(len(seen),12)
        both[0]=False;peak.update(a=0,b=0)
        suite.execute_lanes(jobs,{'a':2,'b':3},run_one,lambda *a:None,concurrent_lanes=False)
        self.assertFalse(both[0]);self.assertEqual(peak,{'a':2,'b':3})

if __name__=='__main__':unittest.main()

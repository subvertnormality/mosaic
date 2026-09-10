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

if __name__=='__main__':unittest.main()

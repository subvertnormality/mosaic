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

    def test_real_time_subset_skips_are_listed_not_counted_as_regressions(self):
        base=report([('A','real-time',True),('B','real-time',True),('C','real-time',True)])
        new=report([('A','real-time',True)])
        new['not_run']=[dict(case='B',lane='real-time',profile='base-midi',reason='real-time subset: not timing-selected; run in the controlled lane only'),
                        dict(case='C',lane='real-time',profile='base-midi',reason='profile not requested')]
        code,result=self.compare(base,new)
        self.assertEqual(result['regressions'],['case/C/real-time'])
        self.assertEqual(result['not_run_by_subset'],['case/B/real-time'])
        self.assertEqual(code,1)

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

    def test_persisted_digest_lua_contract_receives_norns_root_and_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(suite, 'run_command') as run:
                suite.lua_layer(['persisted_digest.lua'], Path(tmp), Path(tmp))
        command = run.call_args.args[1]
        self.assertEqual(command[2:], [tmp,
                          str(suite.BEHAVIOUR/'fixtures/persisted/current/data/autosave.ptn')])

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

class RuntimeIdentityTests(unittest.TestCase):
    def test_runtime_sources_are_recaptured_as_exact_start_identities(self):
        emulator=Path('/emulator').resolve();norns=Path('/norns').resolve()
        expected=dict(emulator={'revision':'e','tree_sha256':'et'},
                      norns_source={'path':str(norns),'revision':'n','lua_tree_sha256':'nt'})
        with patch.object(suite,'source_state',return_value=expected['emulator']) as source_state, \
             patch.object(suite,'git',return_value='n\n') as git, \
             patch.object(suite,'tree_digest',return_value='nt') as tree_digest:
            actual=suite.runtime_source_state(emulator,norns)
        self.assertEqual(actual,expected)
        source_state.assert_called_once_with(emulator)
        git.assert_called_once_with('rev-parse','HEAD',cwd=norns)
        tree_digest.assert_called_once_with(norns/'lua')

    def test_runtime_stability_detects_either_emulator_or_norns_change(self):
        started=dict(emulator={'revision':'e','tree_sha256':'et'},
                     norns_source={'path':'/norns','revision':'n','lua_tree_sha256':'nt'})
        self.assertTrue(suite.same_runtime_sources(started,started))
        changed_emulator=dict(started,emulator={'revision':'e','tree_sha256':'changed'})
        self.assertFalse(suite.same_runtime_sources(started,changed_emulator))
        changed_norns=dict(started,norns_source={'path':'/norns','revision':'n','lua_tree_sha256':'changed'})
        self.assertFalse(suite.same_runtime_sources(started,changed_norns))

    def test_suite_run_fails_source_stability_when_a_runtime_changes(self):
        mosaic=dict(files={'mosaic.lua':'m'},runner_sha256='runner')
        runtime_before=dict(emulator={'revision':'e','tree_sha256':'et'},
                            norns_source={'path':'/norns','revision':'n','lua_tree_sha256':'nt'})
        runtime_after=dict(runtime_before,
                           norns_source={'path':'/norns','revision':'n','lua_tree_sha256':'changed'})
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'suite-output'
            args=SimpleNamespace(output=str(output),emulator='/emulator',output_mod_root=None,
                norns_source='/norns',experimental_install=None,lanes=['controlled-experimental'],
                profiles={'base-midi'},case_pattern=None,skip_fast_layers=True,real_time_subset=False,
                real_time_history=None,durations_from=None,real_time_workers=1,controlled_workers=1,
                start_interval=0,sequential_lanes=True)
            with patch.object(suite,'case_registry',return_value={'A':['REQ']}), \
                 patch.object(suite,'collect',return_value=([],[])), \
                 patch.object(suite,'source_state',side_effect=[mosaic,mosaic]), \
                 patch.object(suite,'runtime_source_state',side_effect=[runtime_before,runtime_after]), \
                 patch.object(suite,'controlled_only_cases',return_value={}), \
                 patch.object(suite,'real_time_only_cases',return_value={}), \
                 patch.object(suite,'active_jack_servers',return_value=0), \
                 patch.object(suite,'execute_lanes'):
                suite.run(args)
            report=json.loads((output/'suite.json').read_text())
        self.assertFalse(report['summary']['runtime_sources_stable'])
        self.assertFalse(report['summary']['sources_stable'])

class SchedulingTests(unittest.TestCase):
    def test_controlled_only_cases_are_not_applicable_in_real_time(self):
        jobs,not_run=suite.plan_jobs(['A','B'],['real-time','controlled-experimental'],{'base-midi'},{'B':'needs logical time'})
        self.assertEqual(jobs,[('A','real-time','base-midi'),('A','controlled-experimental','base-midi'),('B','controlled-experimental','base-midi')])
        self.assertEqual(not_run,[dict(case='B',lane='real-time',profile='base-midi',reason='controlled only: needs logical time',applicable=False)])

    def test_controlled_only_declarations_match_the_clock_mode_guards(self):
        self.assertEqual(sorted(suite.controlled_only_cases()),
                         ['M-ARP-005','M-ARP-012','M-ARP-013','M-SPREAD-023','M-SPREAD-026','M-SPREAD-027'])

    def test_real_time_only_cases_are_not_applicable_in_controlled_time(self):
        jobs,not_run=suite.plan_jobs(['A','B'],['real-time','controlled-experimental'],{'base-midi'}, {},
                                     real_time_only={'B':'requires a wall-clock native fault'})
        self.assertEqual(jobs,[('A','real-time','base-midi'),('B','real-time','base-midi'),('A','controlled-experimental','base-midi')])
        self.assertEqual(not_run,[dict(case='B',lane='controlled-experimental',profile='base-midi',
                                      reason='real-time only: requires a wall-clock native fault',applicable=False)])
        self.assertFalse(not_run[0].get('applicable',True))

    def test_real_time_only_declarations_match_the_clock_mode_guards(self):
        self.assertEqual(sorted(suite.real_time_only_cases()),['M-SYNC-023','M-TIM-005'])

    def test_real_time_subset_selects_timing_requirements_profiles_and_history(self):
        registry={'T':['CH-SWING'],'P':['CLOCK-PHRASE-001'],'R':['REC-LIVE'],'N':['NAV-PAGES'],'A':['NAV-PAGES'],'H':['CH-RANGE']}
        chosen=suite.real_time_subset(registry,{'A':'crow-jf'},{'H'})
        self.assertEqual(chosen,{'T','P','R','A','H'})
        self.assertEqual(suite.real_time_subset(registry,{},set()),{'T','P','R'})

    def test_real_time_subset_names_live_requirements(self):
        requirements={r for case in suite.case_registry().values() for r in case}
        self.assertEqual(sorted(suite.REAL_TIME_REQUIREMENTS-requirements),[])
        self.assertEqual([p for p in suite.REAL_TIME_PREFIXES if not any(r.startswith(p) for r in requirements)],[])

    def test_real_time_history_reads_failed_real_time_first_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'suite.json'
            path.write_text(json.dumps(dict(cases=[
                dict(case='A',lane='real-time',passed=False),
                dict(case='B',lane='real-time',passed=True,first_attempt=dict(passed=False)),
                dict(case='C',lane='controlled-experimental',passed=False),
                dict(case='D',lane='real-time',passed=True)])))
            self.assertEqual(suite.real_time_history(str(path)),{'A','B'})
        self.assertEqual(suite.real_time_history(None),set())

    def test_real_time_subset_records_skipped_runs_as_required_not_run(self):
        jobs,not_run=suite.plan_jobs(['A','B'],['real-time','controlled-experimental'],{'base-midi'},{},real_time_subset={'A'})
        self.assertEqual(jobs,[('A','real-time','base-midi'),('A','controlled-experimental','base-midi'),('B','controlled-experimental','base-midi')])
        self.assertEqual(not_run,[dict(case='B',lane='real-time',profile='base-midi',
                                      reason='real-time subset: not timing-selected; run in the controlled lane only')])
        self.assertTrue(not_run[0].get('applicable',True))
        jobs,not_run=suite.plan_jobs(['A','B'],['real-time'],{'base-midi'},{},real_time_subset=None)
        self.assertEqual((len(jobs),not_run),(2,[]))

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

    def test_mod_patches_are_forwarded_only_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest=Path(tmp)/'manifest.json'
            manifest.write_text(json.dumps(dict(passed=True)))
            result=SimpleNamespace(returncode=0,stdout=json.dumps(dict(case='M-MOD-001',manifest=str(manifest)))+chr(10),stderr='')
            base=dict(experimental_install=None,mod_code_root={'midi-modulation':'/mods'},case_timeout=1)
            for enabled,profile in ((False,'midi-modulation'),(True,'midi-modulation'),(True,'base-midi'),(True,'nb-audio'),(True,'crow-jf')):
                base['mod_code_root'][profile]='/mods'
                args=SimpleNamespace(mod_patches=enabled,**base)
                with patch.object(suite.subprocess,'run',return_value=result) as launched:
                    row=suite.run_case('M-MOD-001','real-time',profile,args,Path(tmp),{})
                self.assertTrue(row['passed'])
                command=launched.call_args.args[0]
                self.assertEqual('--mod-patches' in command,enabled and profile=='midi-modulation')

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

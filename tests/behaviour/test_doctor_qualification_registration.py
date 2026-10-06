"""Registration-only guards; public ADC/native acceptance remains separate."""
import ast,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests/behaviour'))
spec=importlib.util.spec_from_file_location('doctor_registration_runner',ROOT/'tools/doctor_options_capture.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
from contract import rhythm_doctor_start_beat as procedure
from contract import rhythm_doctor_options as option_recipe

STAGED_DOCTOR_OPTION_REGISTRATIONS = {'MA-DOCTOR-SETUP-OPTIONS-001'}

class DoctorQualificationRegistrationTests(unittest.TestCase):
    def test_stable_id_and_manual_citation_are_not_global_case_registration(self):
        self.assertEqual(getattr(procedure,'CASE_ID',None),'MA-DOCTOR-MANUAL-START-BEAT-001')
        self.assertEqual(procedure.CITATION,'manual:rhythm-doctor')
        import cases
        self.assertNotIn('MA-DOCTOR-MANUAL-START-BEAT-001',cases.CASES)

    def test_manifest_is_bound_to_actual_adc_role_and_exact_checkpoints(self):
        self.assertTrue(hasattr(runner,'qualification_registration'),'Runner lacks immutable qualification registration')
        record=runner.qualification_registration('manual_right','real-time')
        self.assertEqual(record['specialized_qualifications'],[{'id':'MA-DOCTOR-MANUAL-START-BEAT-001','citation':'manual:rhythm-doctor'}])
        manifest=json.loads((ROOT/record['qualification_manifest']['source_path']).read_text())
        entry=manifest['qualifications'][0]
        self.assertFalse(entry['global_inventory_member']);self.assertTrue(entry['required_for_manual_build'])
        self.assertEqual(entry['runner']['role'],'manual_right')
        self.assertEqual(entry['checkpoint_ids'],['start-beat-original1','start-beat-next2','start-beat-next-ready','start-beat-restore1','start-beat-restored-ready'])
        self.assertFalse(entry['controlled_time']['applicable'])
        self.assertFalse(entry['ui_only_witness']['backend_regression'])
        self.assertEqual(record['qualification_manifest']['file'],'qualification-registration.json')

    def test_setup_options_is_registered_expected_but_not_claimed_as_run(self):
        manifest=json.loads((ROOT/'tools/doctor-qualification-inventory.json').read_text())
        entries=manifest['qualifications']
        self.assertEqual(len(entries),2)
        setup=next(entry for entry in entries if entry['id']=='MA-DOCTOR-SETUP-OPTIONS-001')
        self.assertIn(setup['id'],STAGED_DOCTOR_OPTION_REGISTRATIONS)
        self.assertEqual(setup['citation'],'manual:rhythm-doctor')
        self.assertEqual(setup['feature_id'],'rhythm-doctor')
        self.assertTrue(setup['required_for_manual_build'])
        self.assertFalse(setup['global_inventory_member'])
        self.assertTrue(setup['registration_only'])
        self.assertTrue(setup['native_run_required'])
        self.assertFalse(any(key in setup for key in ('passed','report','report_sha256','qualified_at')))
        self.assertEqual(setup['runner']['path'],'tools/doctor_options_capture.py')
        self.assertEqual(setup['runner']['roles'],[
            {'role':'setup_real','clock_mode':'real-time','installation_profile':'audio'},
            {'role':'setup_controlled','clock_mode':'controlled-experimental','installation_profile':'controlled'}])
        self.assertEqual(setup['procedure'],{'path':'tests/behaviour/contract/rhythm_doctor_options.py','callable':'setup_options'})
        self.assertEqual(setup['result_ids'],['setup-complete'])
        self.assertTrue(setup['controlled_time']['applicable'])
        self.assertEqual(runner.CASES['setup_options'],option_recipe.setup_options)
        for role,clock in [('setup_real','real-time'),('setup_controlled','controlled-experimental')]:
            record=runner.qualification_registration('setup_options',clock)
            self.assertEqual(record['specialized_qualifications'],[
                {'id':'MA-DOCTOR-SETUP-OPTIONS-001','citation':'manual:rhythm-doctor'}])
        cases=__import__('cases')
        self.assertNotIn('MA-DOCTOR-SETUP-OPTIONS-001',cases.CASES)
        self.assertIsNotNone(cases.CASES.get('M-DOCTOR-SETUP-001'),
            'M-DOCTOR-SETUP-001 missing from global CASES registry')
        global_case=cases.CASES['M-DOCTOR-SETUP-001']
        self.assertEqual(global_case['case_id'],'M-DOCTOR-SETUP-001')
        self.assertEqual(global_case['citation'],'manual:rhythm-doctor')
        self.assertEqual(global_case['run'],cases.run_doctor_setup_options)
        self.assertNotEqual(global_case['case_id'],setup['id'])
        import types
        for context in ('M-DOCTOR-SETUP-001','MA-DOCTOR-SETUP-OPTIONS-001'):
            with self.subTest(context=context):
                driver=types.SimpleNamespace(results=[],doctor_options_case_id=context)
                option_recipe._record(driver,'identity-probe')
                self.assertEqual(driver.results,[dict(kind='doctor-options',check='identity-probe',
                    contract='README.md#rhythm-doctor',citation='manual:rhythm-doctor',case_id=context)])
        import manual_build
        self.assertEqual(manual_build.DOCTOR_OPTION_STAGES['doctor-options-setup-real'],
            ('setup_options','real-time','doctor-options-setup-real'))
        self.assertEqual(manual_build.DOCTOR_OPTION_STAGES['doctor-options-setup-controlled'],
            ('setup_options','controlled-experimental','doctor-options-setup-controlled'))

    def test_unrelated_role_does_not_claim_start_beat_acceptance(self):
        self.assertTrue(hasattr(runner,'qualification_registration'),'Runner lacks immutable qualification registration')
        record=runner.qualification_registration('ready_options','controlled-experimental')
        self.assertEqual(record['specialized_qualifications'],[])
        self.assertTrue(record['qualification_manifest']['sha256'])

    def test_controlled_lane_reason_distinguishes_setup_ready_and_actual_audio(self):
        tree=ast.parse((ROOT/'tools/doctor_options_capture.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        report=next(n.value for n in ast.walk(function) if isinstance(n,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id=='report' for t in n.targets))
        expression=next(k.value for k in report.keywords if k.arg=='controlled_time')
        code=compile(ast.Expression(expression),'<controlled applicability metadata>','eval')
        for role,applicable,words in [('setup_options',True,('setup','draft')),
            ('ready_options',True,('persisted','bank','refusal')),
            ('manual_right',False,('adc','retained','reanalysis','real-time'))]:
            with self.subTest(role=role):
                result=eval(code,{'case':role,'audio_case':not applicable})
                self.assertEqual(result['applicable'],applicable)
                for word in words:self.assertIn(word,result['reason'].lower())

    def test_unknown_membership_and_invalid_full_lane_fail(self):
        self.assertTrue(hasattr(runner,'qualification_registration'),'Runner lacks immutable qualification registration')
        with self.assertRaisesRegex(ValueError,'real-time'):
            runner.qualification_registration('manual_right','controlled-experimental')
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'wrong.json'
            source.write_text(json.dumps({'schema_version':1,'qualifications':[]}))
            with self.assertRaisesRegex(ValueError,'registration'):
                runner.qualification_registration('manual_right','real-time',source)
            current=json.loads(runner.QUALIFICATION_MANIFEST.read_text())
            current['qualifications'][0]['checkpoint_ids']=['unregistered-checkpoint']
            source.write_text(json.dumps(current))
            with self.assertRaisesRegex(ValueError,'registration'):
                runner.qualification_registration('manual_right','real-time',source)
            current=json.loads(runner.QUALIFICATION_MANIFEST.read_text())
            current['qualifications'].append(dict(current['qualifications'][1]))
            source.write_text(json.dumps(current))
            with self.assertRaisesRegex(ValueError,'registration'):
                runner.qualification_registration('setup_options','controlled-experimental',source)

if __name__=='__main__':unittest.main()

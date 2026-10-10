"""Controlled-local manual generation claims remain distinct from REAL qualification."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import manual_publication_verify as audit

def fixture(directory):
 root=Path(directory);manual=root/'manual';(manual/'generated').mkdir(parents=True)
 plan=manual/'scene-plans-core.yaml';plan.write_text('scenes:\n- id: one\n  behaviour_case: M-ONE\n')
 build=root/'build';archive=build/'authoring-before/manual';archive.mkdir(parents=True);(archive/plan.name).write_bytes(plan.read_bytes())
 source={'manual/scene-plans-core.yaml':audit.digest(plan)}
 context=dict(schema_version=1,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',clock_mode='controlled-experimental',complete_regression_run=False,selected_plans=[plan.name],required_plans=[plan.name],selected_scene_ids=['one'],required_scene_ids=['one'],source_files_before=source)
 (build/'generation-context.json').write_text(json.dumps(context))
 native=build/'reference-scenes.json';native.write_text(json.dumps(dict(validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',clock_mode='controlled-experimental',complete_regression_run=False,selected_scene_ids=['one'],scenes=[dict(id='one')])))
 name='reference-controlled-scene-plans-core-base-midi';log=build/(name+'.log');log.write_text('native capture passed')
 row=dict(name=name,passed=True,returncode=0,log_sha256=audit.digest(log),native_report=dict(path=str(native),sha256=audit.digest(native)))
 (build/(name+'.json')).write_text(json.dumps(row))
 return root,manual,build,source,row

class ControlledGenerationPhaseIntegrity(unittest.TestCase):
 def test_prefinal_feature_bind_audits_raw_receipts_without_compiled_book(self):
  with tempfile.TemporaryDirectory() as directory:
   root,manual,build,source,row=fixture(directory)
   (manual/'generated/book.json').write_text('{"stale":true}')
   with patch.object(audit,'ROOT',root),patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_reference',return_value=1),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True,complete_regression_run=False)),patch.object(audit,'compile_book',side_effect=AssertionError('book compilation is a later build stage')):
    result=audit.audit_controlled_manual_generation(build,require_manual_generation_complete=False)
   self.assertTrue(result['passed']);self.assertFalse(result['manual_generation_complete']);self.assertFalse(result['complete_regression_run'])

 def test_final_completion_requires_pending_ci_scope_and_exact_current_book(self):
  with tempfile.TemporaryDirectory() as directory:
   root,manual,build,source,row=fixture(directory)
   manifest=dict(schema_version=1,passed=True,build_complete=False,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',clock_mode='controlled-experimental',manual_generation_complete=True,complete_regression_run=False,controlled_time_admitted=False,renderer_validated=True,selected_plans=['scene-plans-core.yaml'],required_plans=['scene-plans-core.yaml'],selected_scene_ids=['one'],required_scene_ids=['one'],source_files_before=source,source_files_after=source,stages=[row])
   (build/'manifest.json').write_text(json.dumps(manifest))
   actual=dict(project={},features=[],scenes={'one':dict(id='one')});(manual/'generated/book.json').write_text(json.dumps(actual))
   with patch.object(audit,'ROOT',root),patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_reference',return_value=1),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True,complete_regression_run=False)),patch.object(audit,'compile_book',return_value=actual),patch.object(audit,'load',return_value={}),patch.object(audit,'capture_catalogue',return_value={'one':dict(id='one')}),patch.object(audit,'check_compiled_scene_contract'):
    result=audit.audit_controlled_manual_generation(build)
   self.assertTrue(result['manual_generation_complete']);self.assertEqual(result['realtime_qualification'],'pending-ci')
   manifest['complete_regression_run']=True;(build/'manifest.json').write_text(json.dumps(manifest))
   with patch.object(audit,'ROOT',root),patch.object(audit,'MANUAL',manual):
    with self.assertRaisesRegex(ValueError,'scope'):
     audit.audit_controlled_manual_generation(build)

if __name__=='__main__':unittest.main()

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
 # This synthetic inventory fixture needs only a legacy-source pointer; loading
 # the real manual here repeatedly parses every authored lesson unnecessarily.
 book_source={'legacy_source':'legacy.md'}
 inventory_sources={'manual/'+book_source['legacy_source'],'cheat_sheet.html','tests/behaviour/manual-inventory.json'}
 for relative in inventory_sources:
  path=root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('fixture source: '+relative)
 inventory={relative:audit.digest(root/relative) for relative in inventory_sources}
 (manual/'inventory.json').write_text(json.dumps(dict(source_files=inventory)))
 context=dict(schema_version=1,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',clock_mode='controlled-experimental',complete_regression_run=False,selected_plans=[plan.name],required_plans=[plan.name],selected_scene_ids=['one'],required_scene_ids=['one'],source_files_before=source)
 (build/'generation-context.json').write_text(json.dumps(context))
 native=build/'reference-scenes.json';native.write_text(json.dumps(dict(validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',clock_mode='controlled-experimental',complete_regression_run=False,selected_scene_ids=['one'],scenes=[dict(id='one')])))
 name='reference-controlled-scene-plans-core-base-midi';log=build/(name+'.log');log.write_text('native capture passed')
 row=dict(name=name,passed=True,returncode=0,log_sha256=audit.digest(log),native_report=dict(path=str(native),sha256=audit.digest(native)))
 (build/(name+'.json')).write_text(json.dumps(row))
 return root,manual,build,source,row,book_source

class ControlledGenerationPhaseIntegrity(unittest.TestCase):
 def test_final_packaging_reuses_the_sealed_fresh_midi_receipt(self):
  # Regression for manual CI run 38205559039: generation passed with fresh
  # MIDI, but the final packaging audit discarded its receipt and rejected
  # the Panic lesson's deliberately truncated reader MIDI preview.
  with tempfile.TemporaryDirectory() as directory:
   root,manual,build,source,row,book_source=fixture(directory)
   fresh=build/'fresh-target-midi-manifest.json';fresh.write_text('{"kind":"fresh-native-target-midi-v1"}')
   receipt=dict(path=str(fresh.resolve()),sha256=audit.digest(fresh))
   producer=dict(name='fresh-target-midi-producer',passed=True,returncode=0,fresh_target_midi_manifest=receipt)
   (build/'fresh-target-midi-producer.json').write_text(json.dumps(producer))
   projection=dict(passed=True,reader_index_sha256='3'*64)
   admission=dict(fresh_target_midi_manifest_sha256=receipt['sha256'],fresh_target_midi_qualification='fresh-candidate-pending-ci',fresh_target_midi_producer_sha256='2'*64)
   projection_row=dict(name='reader-projection',passed=True,returncode=0,reader_projection=projection)
   manifest=dict(schema_version=1,passed=True,build_complete=False,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',clock_mode='controlled-experimental',manual_generation_complete=True,complete_regression_run=False,controlled_time_admitted=False,renderer_validated=True,selected_plans=['scene-plans-core.yaml'],required_plans=['scene-plans-core.yaml'],selected_scene_ids=['one'],required_scene_ids=['one'],source_files_before=source,source_files_after=source,stages=[row,producer,projection_row])
   actual=dict(project={},features=[],scenes={'one':dict(id='one')});(manual/'generated/book.json').write_text(json.dumps(actual))
   expected=dict(fresh_target_midi_manifest=fresh.resolve(),fresh_target_midi_sha256=receipt['sha256'],fresh_build_root=build.resolve())
   def verify_fresh(retained=None,**kwargs):
    if retained is not None or kwargs!=expected:
     raise ValueError('target MIDI missing, truncated, or lacks its typed source receipt')
    return dict(projection,**admission)
   def final_audit(changed):
    (build/'manifest.json').write_text(json.dumps(changed))
    with patch.object(audit,'ROOT',root),patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_reference',return_value=1),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True,complete_regression_run=False)),patch.object(audit,'compile_book',return_value=actual),patch.object(audit,'load',return_value=book_source),patch.object(audit,'capture_catalogue',return_value={'one':dict(id='one')}),patch.object(audit,'check_compiled_scene_contract'),patch.object(audit,'audit_reader_projection',side_effect=verify_fresh):
     return audit.audit_controlled_manual_generation(build)
   result=final_audit(manifest)
   self.assertTrue(result['manual_generation_complete']);self.assertEqual(result['reader_projection'],projection)
   self.assertEqual(result['fresh_target_midi_admission'],admission)
   missing=dict(manifest,stages=[row,projection_row])
   with self.assertRaisesRegex(ValueError,'Fresh target MIDI producer receipt'):final_audit(missing)
   conflicted=dict(manifest,retained_midi_admission={'relative_path':'retained.json','sha256':'1'*64})
   with self.assertRaisesRegex(ValueError,'retained and fresh'):final_audit(conflicted)
   (build/'fresh-target-midi-producer.json').write_text(json.dumps(dict(producer,passed=False)))
   with self.assertRaisesRegex(ValueError,'Fresh target MIDI producer receipt'):final_audit(manifest)

 def test_prefinal_feature_bind_audits_raw_receipts_without_compiled_book(self):
  with tempfile.TemporaryDirectory() as directory:
   root,manual,build,source,row,book_source=fixture(directory)
   (manual/'generated/book.json').write_text('{"stale":true}')
   with patch.object(audit,'ROOT',root),patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_reference',return_value=1),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True,complete_regression_run=False)),patch.object(audit,'compile_book',side_effect=AssertionError('book compilation is a later build stage')):
    result=audit.audit_controlled_manual_generation(build,require_manual_generation_complete=False)
   self.assertTrue(result['passed']);self.assertFalse(result['manual_generation_complete']);self.assertFalse(result['complete_regression_run'])

 def test_final_completion_requires_pending_ci_scope_and_exact_current_book(self):
  with tempfile.TemporaryDirectory() as directory:
   root,manual,build,source,row,book_source=fixture(directory)
   projection=dict(passed=True,fixture=True);projection_row=dict(name='reader-projection',passed=True,returncode=0,reader_projection=projection)
   manifest=dict(schema_version=1,passed=True,build_complete=False,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',clock_mode='controlled-experimental',manual_generation_complete=True,complete_regression_run=False,controlled_time_admitted=False,renderer_validated=True,selected_plans=['scene-plans-core.yaml'],required_plans=['scene-plans-core.yaml'],selected_scene_ids=['one'],required_scene_ids=['one'],source_files_before=source,source_files_after=source,stages=[row,projection_row],retained_midi_admission={'relative_path':'retained-midi.json','sha256':'4'*64})
   (build/'manifest.json').write_text(json.dumps(manifest))
   actual=dict(project={},features=[],scenes={'one':dict(id='one')});(manual/'generated/book.json').write_text(json.dumps(actual))
   with patch.object(audit,'ROOT',root),patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_reference',return_value=1),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True,complete_regression_run=False)),patch.object(audit,'compile_book',return_value=actual),patch.object(audit,'load',return_value=book_source),patch.object(audit,'capture_catalogue',return_value={'one':dict(id='one')}),patch.object(audit,'check_compiled_scene_contract'),patch.object(audit,'audit_reader_projection',return_value=projection) as reader:
    result=audit.audit_controlled_manual_generation(build)
   self.assertTrue(result['manual_generation_complete']);self.assertEqual(result['realtime_qualification'],'pending-ci');self.assertEqual(result['inventory_sources'],dict(passed=True,sources=3))
   # Reader projection (reader-shell install, 2026-10-06): the final audit re-derives it from source-bound files and
   # binds the manifest's stage receipt to it; a missing, failed or differing receipt is rejected.
   reader.assert_called_once_with(manifest['retained_midi_admission']);self.assertEqual(result['reader_projection'],projection)
   def audited(stages,projection_now=projection):
    changed=dict(manifest,stages=stages);(build/'manifest.json').write_text(json.dumps(changed))
    with patch.object(audit,'ROOT',root),patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_reference',return_value=1),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True,complete_regression_run=False)),patch.object(audit,'compile_book',return_value=actual),patch.object(audit,'load',return_value=book_source),patch.object(audit,'capture_catalogue',return_value={'one':dict(id='one')}),patch.object(audit,'check_compiled_scene_contract'),patch.object(audit,'audit_reader_projection',return_value=projection_now):
     return audit.audit_controlled_manual_generation(build)
   with self.assertRaisesRegex(ValueError,'Reader projection stage receipt'):audited([row])
   with self.assertRaisesRegex(ValueError,'Reader projection stage receipt'):audited([row,dict(projection_row,passed=False)])
   with self.assertRaisesRegex(ValueError,'stage inventory differs'):audited([row,projection_row,projection_row])
   with self.assertRaisesRegex(ValueError,'differs from current'):audited([row,projection_row],dict(passed=True,fixture='changed'))
   (build/'manifest.json').write_text(json.dumps(manifest))
   manifest['complete_regression_run']=True;(build/'manifest.json').write_text(json.dumps(manifest))
   with patch.object(audit,'ROOT',root),patch.object(audit,'MANUAL',manual):
    with self.assertRaisesRegex(ValueError,'scope'):
     audit.audit_controlled_manual_generation(build)

if __name__=='__main__':unittest.main()

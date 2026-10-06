"""Publication integrity characterisation outside instrument behaviour."""
import copy,importlib.util,unittest,sys,tempfile,json
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('manual_publication_verify',ROOT/'tools/manual_publication_verify.py')
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
class PublicationIntegrity(unittest.TestCase):
 def test_editorial_overlay_keeps_exact_performance_contract(self):
  baseline=dict(schema_version=1,feature=dict(id='masks',title='Masks',summary='old'),scenes=[dict(id='note',steps=[dict(inputs=[dict(type='key',n=3)],expect=dict(midi=[60]))])],audio=dict(bpm=90,tracks=[]))
  revised=copy.deepcopy(baseline);revised['feature']['summary']='New literal description';revised['audio']['description']='Four bars'
  revised['scenes'][0]['title']='Set a note mask';revised['scenes'][0]['steps'][0]['caption']='Press K3'
  audit.check_editorial_overlay(baseline,revised)
  revised['audio']['bpm']=91
  with self.assertRaisesRegex(ValueError,'performance contract'):audit.check_editorial_overlay(baseline,revised)
  revised['audio']['bpm']=90
  audit.check_editorial_overlay(baseline,revised)
  revised['scenes'][0]['steps'][0]['expect']['midi']=[61]
  with self.assertRaisesRegex(ValueError,'performance contract'):audit.check_editorial_overlay(baseline,revised)
 def test_feature_identity_cannot_be_overlaid(self):
  original=dict(feature=dict(id='masks'),scenes=[],audio={});revised=copy.deepcopy(original);revised['feature']['id']='song'
  with self.assertRaisesRegex(ValueError,'feature identity'):audit.check_editorial_overlay(original,revised)
 def test_exact_assertion_index_hash_and_trace_required(self):
  row=dict(kind='midi',passed=True,notes=[60]);inputs=[dict(type='key',n=3)]
  binding=dict(assertion_index=0,assertion=row,assertion_sha256=audit.canonical_hash(row),trace_sha256=audit.canonical_hash(inputs))
  step=dict(inputs=inputs,expect=dict(assertion=dict(kind='midi',passed=True)),output=dict(binding=binding))
  audit.check_assertion(step,[row])
  bad=copy.deepcopy(step);bad['output']['binding']['assertion_index']=1
  with self.assertRaisesRegex(ValueError,'assertion index'):audit.check_assertion(bad,[row])
  bad=copy.deepcopy(step);bad['inputs'][0]['n']=2
  with self.assertRaisesRegex(ValueError,'trace'):audit.check_assertion(bad,[row])
  bad=copy.deepcopy(step);bad['output']['binding']['assertion']['notes']=[61]
  with self.assertRaisesRegex(ValueError,'assertion'):audit.check_assertion(bad,[row])
 def test_failed_semantic_checkpoint_rejected(self):
  row=dict(kind='midi',passed=False);binding=dict(assertion_index=0,assertion=row,assertion_sha256=audit.canonical_hash(row),trace_sha256=audit.canonical_hash([]))
  with self.assertRaisesRegex(ValueError,'failed'):audit.check_assertion(dict(inputs=[],expect=dict(assertion={}),output=dict(binding=binding)),[row])
class GenericPublicationIntegrity(unittest.TestCase):
 def test_generic_scene_requires_exact_semantics_and_citation(self):
  source=dict(id='first',behaviour_case='M-PAT-001',setup=dict(fixture='empty'),steps=[dict(id='note',inputs=[],expect=dict(midi_phrase=[60]),citation='manual:masks')])
  captured=copy.deepcopy(source);captured['evidence']={};captured['steps'][0]['output']={}
  audit.check_generic_scene_contract(captured,source)
  captured['steps'][0]['expect']['midi_phrase']=[61]
  with self.assertRaisesRegex(ValueError,'scene contract'):audit.check_generic_scene_contract(captured,source)
 def test_generic_publication_cannot_skip_baseline_case(self):
  with self.assertRaisesRegex(ValueError,'baseline cases'):
   audit.check_generic_scope(dict(passed=True,complete_regression_run=False,scene_build_complete=True,behaviour_cases=[]),[dict(behaviour_case='M-PAT-001')])
 def test_unknown_scene_dataset_is_fail_closed(self):
  with self.assertRaisesRegex(ValueError,'Unrecognised scene publication'):
   audit.scene_format(dict(scenes=[dict(id='unknown')]))
  self.assertEqual(audit.scene_format(dict(scenes=[],validation={},feature={})), 'generic')
  self.assertEqual(audit.scene_format(dict(scenes=[],source={},clock_mode='real-time')), 'reference')
class FreshPilotPublication(unittest.TestCase):
 def test_current_source_native_publication_needs_no_git_commit_or_overlay(self):
  import yaml
  with tempfile.TemporaryDirectory() as directory:
   manual=Path(directory);(manual/'features').mkdir();(manual/'generated').mkdir()
   source=dict(feature=dict(id='masks'),scenes=[],audio={})
   (manual/'features/masks.yaml').write_text(yaml.safe_dump(source))
   data=dict(feature=source['feature'],source_sha256=audit.source_hash(source),scenes=[],validation=dict(run_id='fresh'))
   target=manual/'generated/pilot.json';target.write_text(json.dumps(data,indent=2)+'\n');original=target.read_bytes()
   with patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_fresh_pilot',return_value=dict(frames=1)) as verify,patch.object(audit,'refresh_compression_receipt',return_value={}) as receipt,patch.object(audit.subprocess,'check_output',side_effect=AssertionError('Fresh publication must not require Git')):
    result=audit.refresh_pilot_editorial()
   verify.assert_called_once_with(data,source,check_receipt=False)
   receipt.assert_called_once()
   self.assertEqual(target.read_bytes(),original);self.assertFalse(result['overlay_required'])
 def test_native_verification_failure_prevents_receipt_refresh(self):
  import yaml
  with tempfile.TemporaryDirectory() as directory:
   manual=Path(directory);(manual/'features').mkdir();(manual/'generated').mkdir()
   source=dict(feature=dict(id='masks'),scenes=[],audio={});(manual/'features/masks.yaml').write_text(yaml.safe_dump(source))
   (manual/'generated/pilot.json').write_text(json.dumps(dict(source_sha256=audit.source_hash(source))))
   with patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_fresh_pilot',side_effect=ValueError('Native assertion failed')),patch.object(audit,'refresh_compression_receipt') as receipt:
    with self.assertRaisesRegex(ValueError,'Native assertion'):audit.refresh_pilot_editorial()
   receipt.assert_not_called()
class CompressionReceiptIntegrity(unittest.TestCase):
 def test_different_decoded_signal_cannot_replace_prior_receipt(self):
  with tempfile.TemporaryDirectory() as directory:
   manual=Path(directory);(manual/'evidence').mkdir();(manual/'audio').mkdir()
   receipt=manual/'evidence/audio-files.json';receipt.write_text('{"prior":"hash"}');before=receipt.read_bytes()
   native=manual/'native-run';wav=native/'native/audio-captures/job/output.wav';wav.parent.mkdir(parents=True);wav.write_bytes(b'Preserved native PCM')
   (manual/'audio/example.ogg').write_bytes(b'Unrelated encoded audio')
   document=dict(source_sha256='fresh',audio=dict(files=['audio/example.ogg'],bars=1,bpm=120,evidence=dict(path=str(native),job=dict(job_id='job'),wav_sha256=audit.digest(wav))))
   with patch.object(audit,'MANUAL',manual),patch.object(audit.subprocess,'run'),patch.object(audit.subprocess,'check_output',side_effect=[b'unrelated decoded PCM',b'expected decoded PCM']):
    with self.assertRaisesRegex(ValueError,'encoding contract'):audit.refresh_compression_receipt(document,'ffmpeg')
   self.assertEqual(receipt.read_bytes(),before)
class DeferredCaptureIntegrity(unittest.TestCase):
 def fixture(self):
  expected=dict(field=dict(layout='detail',label='Cutoff',value='64'))
  ui=dict(kind='selected-field',layout='detail',label='Cutoff',value='64',matched=True)
  oracle=dict(kind='cc',passed=True,value=64)
  binding=dict(kind='documentation-frame',name='manual/CC/step',passed=True,semantic_assertions=1,assertion_index=2,assertion=oracle,capture_stage='before-finish',pre_finish_expect=expected,pre_finish_assertion_indices=[0])
  return dict(output=dict(binding=binding)),[ui,binding,oracle],dict(capture_stage='before-finish',pre_finish_expect=expected)
 def test_earlier_image_cannot_be_accepted_as_after_assertion_capture(self):
  step,results,plan=self.fixture();step['output']['binding'].pop('capture_stage')
  with self.assertRaisesRegex(ValueError,'precedes'):audit.check_capture_stage(step,results,plan)
 def test_explicit_before_finish_flag_requires_pinned_authorization_and_ui_evidence(self):
  step,results,plan=self.fixture();audit.check_capture_stage(step,results,plan)
  with self.assertRaisesRegex(ValueError,'authorised'):audit.check_capture_stage(step,results,{})
  bad=copy.deepcopy(step);bad['output']['binding']['pre_finish_assertion_indices']=[2];bad_results=copy.deepcopy(results);bad_results[1]=bad['output']['binding']
  with self.assertRaisesRegex(ValueError,'pre-finish'):audit.check_capture_stage(bad,bad_results,plan)
  bad=copy.deepcopy(plan);bad['pre_finish_expect']['field']['value']='65'
  with self.assertRaisesRegex(ValueError,'pre-finish'):audit.check_capture_stage(step,results,bad)
class NativeSessionTraceIntegrity(unittest.TestCase):
 def test_exact_native_grid_coordinates_and_controlled_time(self):
  recipe=[dict(type='grid',x=2,y=4,state=1),dict(type='advance',nanoseconds=1500000000),dict(type='grid',x=2,y=4,state=0)]
  events=[dict(kind='input',type=3,args=[1,3,1]),dict(kind='input',type=8,args=[1,500000000]),dict(kind='input',type=3,args=[1,3,0])]
  audit.check_native_input_trace(recipe,events)
  events[1]['args'][1]=500000001
  with self.assertRaisesRegex(ValueError,'full-session inputs'):audit.check_native_input_trace(recipe,events)
 def test_native_selected_label_and_value_oracles_are_exact(self):
  expected=dict(menu_label=dict(label='CC1'),menu_value=dict(value='63'))
  self.assertEqual(audit.pre_finish_rows(expected),[dict(kind='selected-menu-label',text='CC1'),dict(kind='selected-menu-value',text='63')])
  with self.assertRaisesRegex(ValueError,'unsupported'):audit.pre_finish_rows(dict(arbitrary_screenshot=True))
class CompiledCaptionIntegrity(unittest.TestCase):
 def test_compiled_caption_receipt_preserves_entire_native_contract(self):
  raw=dict(id='scene',title='Scene',steps=[dict(id='step',caption='Old',title='Control',inputs=[dict(type='enc',n=3,delta=2)],expect=dict(value=63),output=dict(grid=[0],binding=dict(sha256='native')),citation='manual:parameters')],evidence=dict(results_sha256='immutable'))
  compiled=copy.deepcopy(raw);compiled['steps'][0]['caption']='Set CC 1 to 63'
  with self.assertRaisesRegex(ValueError,'receipt'):audit.check_compiled_scene_contract(raw,compiled)
  compiled['steps'][0]['caption_overlay']=dict(original_caption_sha256=audit.text_digest('Old'),caption_sha256=audit.text_digest('Set CC 1 to 63'),contract_sha256=audit.scene_contract_digest(raw))
  audit.check_compiled_scene_contract(raw,compiled)
  compiled['steps'][0]['inputs'][0]['delta']=3
  with self.assertRaisesRegex(ValueError,'native contract'):audit.check_compiled_scene_contract(raw,compiled)
 def test_fresh_desired_caption_needs_no_historic_overlay(self):
  raw=dict(id='fresh',steps=[dict(id='step',caption='Set CC 1 to 63',title='Control',inputs=[])])
  audit.check_compiled_scene_contract(raw,copy.deepcopy(raw))
  changed=copy.deepcopy(raw);changed['steps'][0]['title']='Different control'
  with self.assertRaisesRegex(ValueError,'native contract'):audit.check_compiled_scene_contract(raw,changed)
class NestedParticipantIntegrity(unittest.TestCase):
 def test_child_native_clock_and_source_identity_must_match_declared_context(self):
  identity=dict(session_id='child',runtime_identity=dict(lock='pinned'),application_identity=dict(files=[dict(path='mosaic/mosaic.lua',sha256='lua')]))
  context=dict(session_ordinal=1,clock_mode='controlled-experimental',profile='base-midi',app_root='/capture/application',session_id='child',runtime_identity_sha256=audit.canonical_hash(identity['runtime_identity']),application_identity_sha256=audit.canonical_hash({'mosaic/mosaic.lua':'lua'}),finished=True,held_inputs=[],cleanup_verified=True)
  config=dict(clock_mode='controlled-experimental')
  audit.check_participant_context(context,identity,config,'controlled-experimental','base-midi',1,'/capture/application')
  with self.assertRaisesRegex(ValueError,'native clock'):audit.check_participant_context(context,identity,dict(clock_mode='real-time'),'controlled-experimental','base-midi',1,'/capture/application')
  wrong=copy.deepcopy(context);wrong['runtime_identity_sha256']='foreign-runtime'
  with self.assertRaisesRegex(ValueError,'runtime identity'):audit.check_participant_context(wrong,identity,config,'controlled-experimental','base-midi',1,'/capture/application')
 def test_child_cannot_use_parent_assertion_or_frame_namespace(self):
  scene=dict(session_ordinal=1,steps=[dict(output=dict(binding=dict(session_ordinal=0)))])
  with self.assertRaisesRegex(ValueError,'participant namespace'):audit.check_participant_binding(scene,1)
  scene['steps'][0]['output']['binding']['session_ordinal']=1;audit.check_participant_binding(scene,1)
class ExactPublicationSubset(unittest.TestCase):
 def test_subset_can_select_complete_scenes_without_changing_any_evidence(self):
  original=dict(source=dict(plans='pinned'),clock_mode='real-time',evidence='/native/run',complete_regression_run=False,selected_scene_ids=['a','b'],scenes=[dict(id='a',steps=[dict(inputs=[dict(type='enc',delta=2)])]),dict(id='b',steps=[])])
  subset=copy.deepcopy(original);subset['scenes']=subset['scenes'][:1];subset['selected_scene_ids']=['a'];subset['publication_subset']=dict(original_report='receipt',original_report_sha256='sha',scope='One exact completed scene')
  audit.check_reference_publication(subset,original)
  altered=copy.deepcopy(subset);altered['scenes'][0]['steps'][0]['inputs'][0]['delta']=3
  with self.assertRaisesRegex(ValueError,'exact scene subset'):audit.check_reference_publication(altered,original)
  altered=copy.deepcopy(subset);altered['clock_mode']='controlled-experimental'
  with self.assertRaisesRegex(ValueError,'campaign metadata'):audit.check_reference_publication(altered,original)
 def test_subset_cannot_convert_failed_or_empty_report_into_success(self):
  original=dict(passed=False,scenes=[],source={},clock_mode='real-time',complete_regression_run=False)
  subset=dict(original,publication_subset=dict(scope='recovery'))
  with self.assertRaisesRegex(ValueError,'Failed or empty'):audit.check_reference_publication(subset,original)
class ExternalModulePinIntegrity(unittest.TestCase):
 def test_module_whitelist_requires_exact_origin_and_revision(self):
  pins={'toolkit':dict(url='https://example/toolkit.git',commit='pinned')}
  audit.check_module_pin('toolkit',pins,'https://example/toolkit.git','pinned')
  for name,url,revision in [('unknown','https://example/toolkit.git','pinned'),('toolkit','https://wrong/repo.git','pinned'),('toolkit','https://example/toolkit.git','other')]:
   with self.assertRaisesRegex(ValueError,'module pin'):audit.check_module_pin(name,pins,url,revision)
class ScopedRecoveryIntegrity(unittest.TestCase):
 def test_only_exact_completed_cases_can_be_recovered_with_missing_start_fields_explicit(self):
  completed=[dict(id='completed',steps=[dict(inputs=[dict(type='enc',delta=2)])])]
  failure=dict(passed=False,scenes=['failed'],clock_mode='real-time',case_sources={'case.py':'case-sha'},capture_sources={'capture.py':'capture-sha'},plans_sha256='plan')
  report=dict(clock_mode='real-time',complete_regression_run=False,source=dict(case_sources=failure['case_sources'],capture_sources=failure['capture_sources'],plans_sha256='plan',fixture_sources=None),scenes=copy.deepcopy(completed),selected_scene_ids=['completed'],publication_recovery=dict(source_start_identity_complete=False,missing_start_identity_fields=['fixture_sources']))
  with self.assertRaisesRegex(ValueError,'complete start'):audit.check_recovery_publication(report,failure,completed)
 def test_exact_selector_alternatives_do_not_authorise_arbitrary_shortened_interval_lists(self):
  authored=dict(assertion=dict(kind='intervals',values=[1,1,1,1,1,1]),assertion_alternatives=[dict(kind='intervals',values=[1,1,1,1,1,1,1])])
  audit.check_authored_assertion(dict(expect=dict(assertion=authored['assertion'])),authored)
  audit.check_authored_assertion(dict(expect=dict(assertion=authored['assertion_alternatives'][0])),authored)
  with self.assertRaisesRegex(ValueError,'pinned selector'):audit.check_authored_assertion(dict(expect=dict(assertion=dict(kind='intervals',values=[1,1,1,1,1]))),authored)
class StartSourceReceiptIntegrity(unittest.TestCase):
 def test_final_source_must_reuse_every_start_map_and_selection(self):
  maps={field:{'pinned.py':'sha'} for field in ('plan_files','case_sources','capture_sources','fixture_sources')}
  receipt=dict(maps,schema_version=1,plans_sha256='plans',adapter_sha256='adapter',clock_mode='real-time',selected_scene_ids=['one'],extra_case_files=[])
  document=dict(source=dict(maps,plans_sha256='plans',adapter_sha256='adapter'),clock_mode='real-time',selected_scene_ids=['one'])
  audit.check_start_source_receipt(document,receipt)
  altered=copy.deepcopy(document);altered['source']['fixture_sources']['pinned.py']='after-start'
  with self.assertRaisesRegex(ValueError,'start source'):audit.check_start_source_receipt(altered,receipt)
  altered=copy.deepcopy(document);altered['selected_scene_ids']=['other']
  with self.assertRaisesRegex(ValueError,'start selection'):audit.check_start_source_receipt(altered,receipt)
 def test_extra_helpers_must_be_pinned_inside_tools(self):
  receipt=dict(schema_version=1,plans_sha256='plans',adapter_sha256='adapter',clock_mode='real-time',selected_scene_ids=['one'],extra_case_files=['tools/extra.py'],plan_files={},case_sources={},capture_sources={},fixture_sources={})
  document=dict(source={key:value for key,value in receipt.items() if key not in ('schema_version','clock_mode','selected_scene_ids','extra_case_files')},clock_mode='real-time',selected_scene_ids=['one'])
  with self.assertRaisesRegex(ValueError,'extra-case'):audit.check_start_source_receipt(document,receipt)
class ReasonMidiIntegrity(unittest.TestCase):
 def test_native_pulses_pitch_velocity_and_absent_step_are_independent(self):
  expected=[[0,60,127],[24,62,117],[48,64,107],[72,65,97],[144,60,70],[192,60,127]]
  row=dict(expected=expected,absent_pulse=96,channel=1,tolerance_seconds=2e-9,midi_start_index=0)
  events=[dict(kind=11,index=i+1,port=1,logical_ns=1000000000+round(p/144*1e9),decoded=[dict(type='note_on',channel=1,data=[pitch,velocity])]) for i,(p,pitch,velocity) in enumerate(expected)]
  audit.check_reason_midi(row,events,'controlled-experimental')
  wrong=copy.deepcopy(events);wrong[4]['decoded'][0]['data'][1]=71
  with self.assertRaisesRegex(ValueError,'Reason MIDI'):audit.check_reason_midi(row,wrong,'controlled-experimental')
  wrong=copy.deepcopy(events);wrong[4]['logical_ns']=1000000000+round(96/144*1e9)
  with self.assertRaisesRegex(ValueError,'Reason MIDI'):audit.check_reason_midi(row,wrong,'controlled-experimental')
  altered=dict(row,tolerance_seconds=.02)
  with self.assertRaisesRegex(ValueError,'lane tolerance'):audit.check_reason_midi(altered,events,'controlled-experimental')
class ExplicitPublicationKind(unittest.TestCase):
 def test_audio_route_and_doctor_cannot_fall_through_as_ordinary_reference(self):
  for kind in ('audio-route-projection','doctor-native-audio'):
   self.assertEqual(audit.scene_format(dict(publication_kind=kind,scenes=[dict(id='native')],source={},clock_mode='real-time')),kind)
class CompleteStartRecoveryIntegrity(unittest.TestCase):
 def test_recovery_reuses_complete_original_start_identity_without_missing_field_exemptions(self):
  source=dict(plans_sha256='p',plan_files={},case_sources={},capture_sources={},fixture_sources={},adapter_sha256='a',start_source_identity_path='receipt',start_source_identity_sha256='sha')
  failure=dict(passed=False,scenes=['failed'],clock_mode='real-time',source=source)
  scene=dict(id='done',steps=[])
  document=dict(source=copy.deepcopy(source),clock_mode='real-time',complete_regression_run=False,selected_scene_ids=['done'],scenes=[scene],publication_recovery=dict(source_start_identity_complete=True,missing_start_identity_fields=[]))
  audit.check_recovery_publication(document,failure,[scene])
  document['source']['fixture_sources']['invented']='sha'
  with self.assertRaisesRegex(ValueError,'complete start'):audit.check_recovery_publication(document,failure,[scene])
 def test_yaml_numeric_selector_keys_match_exact_json_serialization(self):
  audit.check_authored_assertion(dict(expect=dict(assertion=dict(phrases={'1':[[144,60,127]]}))),dict(assertion=dict(phrases={1:[[144,60,127]]})))
class CompleteRecoveryInventoryIntegrity(unittest.TestCase):
 def test_complete_recovery_cannot_omit_a_passing_scene_from_full_report(self):
  with tempfile.TemporaryDirectory() as directory:
   run=Path(directory);source=dict(plans_sha256='plans',adapter_sha256='adapter',plan_files={},case_sources={},capture_sources={},fixture_sources={})
   receipt=dict(source,schema_version=1,clock_mode='real-time',selected_scene_ids=['done','also-done','failed'],extra_case_files=[])
   failure=dict(passed=False,scenes=['failed'],source=source)
   failure_path=run/'failure.json';failure_path.write_text(json.dumps(failure))
   recovery=dict(failed_campaign=str(run),failure_sha256=audit.digest(failure_path),source_start_identity_complete=True,missing_start_identity_fields=[])
   document=dict(source=source,clock_mode='real-time',selected_scene_ids=['done','also-done'],publication_recovery=recovery,evidence=str(run))
   full=run/'reference-scenes.json';full.write_text(json.dumps(document));audit.check_start_source_receipt(document,receipt)
   changed=copy.deepcopy(document);changed['selected_scene_ids']=['done'];full.write_text(json.dumps(changed))
   with self.assertRaisesRegex(ValueError,'selected or omitted inventory'):audit.check_start_source_receipt(changed,receipt)
class VerticalListCheckpointIntegrity(unittest.TestCase):
 def test_unknown_or_changed_literal_vertical_checkpoint_is_not_accepted(self):
  with self.assertRaisesRegex(ValueError,'Unsupported vertical'):audit.vertical_checkpoint_contract(dict(kind='vertical-list-ui',checkpoint='arbitrary',passed=True))
  with self.assertRaisesRegex(ValueError,'literal vertical'):audit.vertical_checkpoint_contract(dict(kind='vertical-list-ui',checkpoint='inherit-sentinel',label='Swing type',value='Shuffle',passed=True))
  actual=audit.vertical_checkpoint_contract(dict(kind='vertical-list-ui',checkpoint='clock-neighbors',rows=['Rate','Feel source','Swing type'],passed=True))
  self.assertEqual(actual['field'],dict(layout='vertical_list',label='Rate',value='/1'))
 def test_large_scroll_checkpoint_requires_actual_public_encoder_delta(self):
  row=dict(kind='vertical-list-ui',checkpoint='scroll-end',label='Shuffle amount',value='0',passed=True)
  with self.assertRaisesRegex(ValueError,'encoder'):audit.check_vertical_public_inputs(row,[dict(type='enc',n=2,delta=1)])
  audit.check_vertical_public_inputs(row,[dict(type='enc',n=2,delta=126)])
class DoctorPublicationIntegrity(unittest.TestCase):
 def test_failed_or_diagnostic_doctor_report_cannot_be_published(self):
  for report in [dict(publication_kind='doctor-native-audio',passed=False),dict(publication_kind='doctor-native-audio',passed=True,diagnostic_only=True)]:
   with self.assertRaisesRegex(ValueError,'Doctor acceptance'):audit.check_doctor_scope(report)
 def test_setup_preview_and_commit_leds_are_native_acceptance(self):
  setup=[0]*128;preview=[0]*128;preview[48]=12;preview[50]=15;commit=[0]*128;commit[48]=commit[50]=15
  steps=[dict(id='setup',expect=dict(empty_grid=True),output=dict(grid=setup)),dict(id='preview',expect=dict(grid='preview',levels=[12,15],minimum_trigs=2,grid_steps=[1,3]),output=dict(grid=preview)),dict(id='paint',expect=dict(grid='commit',level=15,grid_steps=[1,3]),output=dict(grid=commit))]
  audit.check_doctor_grids(steps)
  changed=copy.deepcopy(steps);changed[0]['output']['grid'][48]=15
  with self.assertRaisesRegex(ValueError,'setup'):audit.check_doctor_grids(changed)
  changed=copy.deepcopy(steps);changed[2]['output']['grid'][50]=12
  with self.assertRaisesRegex(ValueError,'committed'):audit.check_doctor_grids(changed)
class ContinuingCourseIntegrity(unittest.TestCase):
 def test_complete_two_cycle_native_phrase_rejects_extra_attack_and_missing_release(self):
  literal=[dict(port=1,status=144,note=60,velocity=80,step=0,length=.5)]
  row=dict(bpm=90,cycle_steps=4,cycles=2,expected=literal,midi_start_index=0,midi_end_index=4,next_cycle_index=5,timing_tolerance_seconds=2e-9)
  events=[]
  for index,(step,status) in enumerate([(0,144),(.5,128),(4,144),(4.5,128),(8,144)],1):events.append(dict(kind=11,index=index,port=1,bytes=[status,60,80],logical_ns=1000000000+round(step/6*1e9)))
  audit.check_course_midi(row,events,'controlled-experimental')
  with self.assertRaisesRegex(ValueError,'packet inventory'):audit.check_course_midi(row,events[:1]+events[2:],'controlled-experimental')
  changed=copy.deepcopy(events);changed[1]['bytes']=[144,60,80]
  with self.assertRaisesRegex(ValueError,'packet inventory'):audit.check_course_midi(row,changed,'controlled-experimental')
  changed=copy.deepcopy(events);changed[3]['logical_ns']+=10000000
  with self.assertRaisesRegex(ValueError,'gate'):audit.check_course_midi(row,changed,'controlled-experimental')
 def test_song_indicators_and_exact_native_phrase_cannot_be_faked_by_passed_true(self):
  row=dict(kind='manual-song-indicators',stage='playing',levels=[7,15,2],midi_start_index=0,phrase=[[144,60,127],[144,62,117],[144,64,107],[144,65,97]],tolerance_seconds=2e-9)
  events=[dict(kind=11,index=i+1,port=1,bytes=note,logical_ns=1000000000+round(i/6*1e9)) for i,note in enumerate(row['phrase'])]
  state=dict(grid=[7,15,2]+[0]*125);audit.check_song_indicators(row,state,events,'controlled-experimental')
  state['grid'][1]=7
  with self.assertRaisesRegex(ValueError,'Song native LED'):audit.check_song_indicators(row,state,events,'controlled-experimental')
class UnsupportedNewSemanticIntegrity(unittest.TestCase):
 def test_new_manual_semantic_kind_cannot_pass_without_its_independent_checker(self):
  for kind in ('manual-made-up','manual-motion-unverified','manual-doctor-semantic'):
   with self.assertRaisesRegex(ValueError,'Unsupported new'):audit.check_custom_kind(kind)
  audit.check_custom_kind('manual-course-midi')
  audit.check_custom_kind('manual-reason-dashboard')
class MotionSampleIntegrity(unittest.TestCase):
 def fixture(self):
  row,observations,events=MiniReadabilityPublicationIntegrity().fixture()
  import base64,hashlib
  spec=next(item for item in json.loads((audit.ROOT/'tests/behaviour/contract/mini_header_atlas_v2.json').read_text())['screens'] if item['id']=='C04')
  samples=copy.deepcopy(row['samples'])
  for item in samples:
   obs=observations[item['observation_index']];state=obs['state'];pixels=base64.b64decode(state['frame']['pixels_base64']);x,y=spec['origin']
   mark=bytes(pixels[(yy*128+xx)*4+k] for yy in range(8) for xx in range(96,128) for k in range(3))
   item.update(grid_sha256=audit.canonical_hash(state['grid']),logical_ns=state['clock']['logical_ns'],mark_sha256=hashlib.sha256(mark).hexdigest())
  motion=dict(enabled=True,samples=samples,decorative_mark_changed=True,public_mini_header_assertion=row)
  return motion,observations,events,[row,motion]
 def test_full_authored_motion_requires_original_native_mini_proof(self):
  row,obs,events,results=self.fixture()
  audit.check_motion_samples(row,obs,'controlled-experimental',events,results,1)
  for field in ('public_mini_header_assertion','mark_sha256','phase_check','grid_sha256','logical_ns'):
   bad=copy.deepcopy(row)
   if field=='public_mini_header_assertion':bad.pop(field)
   else:bad['samples'][0][field]='fabricated'
   with self.subTest(field=field),self.assertRaises(ValueError):audit.check_motion_samples(bad,obs,'controlled-experimental',events,results,1)
  with self.assertRaises(ValueError):audit.check_motion_samples(row,obs,'controlled-experimental',events,[row],0)
  for field in ('grid','midi_count'):
   badobs=copy.deepcopy(obs)
   if field=='grid':badobs[-1]['state']['grid'][0]=15
   else:badobs[-1]['state']['midi_count']=1
   with self.subTest(native=field),self.assertRaises(ValueError):audit.check_motion_samples(row,badobs,'controlled-experimental',events,results,1)
  with self.assertRaises(ValueError):audit.check_motion_samples(row,obs,'controlled-experimental',[],results,1)
  bad=copy.deepcopy(row);bad['public_mini_header_assertion']['all_distinct_poses_required']=False
  with self.assertRaises(ValueError):audit.check_motion_samples(bad,obs,'controlled-experimental',events,[bad['public_mini_header_assertion'],bad],1)
 def test_old_tiny_crop_without_native_phase_is_refused(self):
  with self.assertRaises(ValueError):audit.check_motion_samples(dict(enabled=False,samples=[],decorative_mark_changed=False),[],'controlled-experimental',[],[],0)
class MotionResponseAndMusicIntegrity(unittest.TestCase):
 def test_response_bound_comes_from_native_observations_not_declared_timeout(self):
  observations=[dict(monotonic_ns=t,state=dict(clock=dict(mode='controlled-experimental',logical_ns=t))) for t in (0,50000000,100000000,150000000)]
  recipe=[];events=[];actions=[];receipts=[]
  for stage,delta,before,after,seq,time in [('edit',-2,0,1,1,1000000),('restore',2,2,3,4,101000000)]:
   start=len(recipe);triple=[dict(type='enc',n=3,delta=delta),dict(type='key',n=3,state=1),dict(type='key',n=3,state=0)];recipe.extend(triple)
   native=dict(sequence=seq+10,monotonic_ns=time)
   receipts.append(dict(stage=stage,before_observation_index=before,response_observation_index=after,recipe_start_index=start,recipe_end_index=len(recipe),input_sequence=seq,native=native))
   for offset,action in enumerate(triple):
    ack_native=dict(sequence=seq+10+offset,monotonic_ns=time+offset)
    actions.append(dict(request=dict(sequence=seq+offset,action=action),ack=dict(status='applied',native=ack_native)))
    events.append(dict(kind='input',sequence=seq+10+offset,type=2 if offset==0 else 1,args=[3,delta if offset==0 else action['state']],monotonic_ns=time+offset))
  for action in actions:
   n=action['ack']['native'];events.extend([dict(kind=4,id=n['sequence'],monotonic_ns=n['monotonic_ns']),dict(kind='input_timing',sequence=n['sequence'],submission_start_ns=n['monotonic_ns'],submitted_ns=n['monotonic_ns'],native_ack_ns=n['monotonic_ns'],monotonic_ns=n['monotonic_ns'])])
  row=dict(public_feedback_bound_seconds=.25,response_receipts=receipts)
  audit.check_motion_feedback(row,observations,recipe,events,actions)
  wrong=copy.deepcopy(observations);wrong[1]['state']['clock']['logical_ns']=300000000
  with self.assertRaisesRegex(ValueError,'quarter-second'):audit.check_motion_feedback(row,wrong,recipe,events,actions)
  wrong=copy.deepcopy(recipe);wrong[1]['state']=0
  with self.assertRaisesRegex(ValueError,'exact public'):audit.check_motion_feedback(row,observations,wrong,events,actions)
  with self.assertRaisesRegex(ValueError,'native input edge'):audit.check_motion_feedback(row,observations,recipe,events[:1]+events[2:],actions)
 def test_motion_gate_and_stopped_led_are_native_observations(self):
  row=dict(pitches=[60,62,64,65],velocities=[127,117,107,97],onset_spacing_seconds=1/6,tolerance_seconds=2e-9,stopped=True,midi_start_index=0)
  events=[]
  for i in range(9):
   note=row['pitches'][i%4];velocity=row['velocities'][i%4]
   events.append(dict(kind=11,index=len(events)+1,port=1,bytes=[144,note,velocity],logical_ns=1000000000+round(i/6*1e9)))
   if i<8:events.append(dict(kind=11,index=len(events)+1,port=1,bytes=[128,note,velocity],logical_ns=1000000000+round((i+1)/6*1e9)))
  state=dict(grid=[0]*128,midi_count=17,midi_capture=dict(outstanding=[]));state['grid'][112]=2
  audit.check_motion_music(row,state,events,'controlled-experimental')
  changed=copy.deepcopy(events);changed[1]['logical_ns']+=10000000
  with self.assertRaisesRegex(ValueError,'gate'):audit.check_motion_music(row,state,changed,'controlled-experimental')
  state['grid'][112]=15
  with self.assertRaisesRegex(ValueError,'not stopped'):audit.check_motion_music(row,state,events,'controlled-experimental')
class MissingSpecializedScenesIntegrity(unittest.TestCase):
 def test_explicit_native_publication_kind_cannot_be_silently_ignored_when_scenes_are_missing(self):
  for scenes in (None,[]):
   doc=dict(publication_kind='doctor-native-audio',passed=True)
   if scenes is not None:doc['scenes']=scenes
   with self.assertRaisesRegex(ValueError,'Incomplete specialized'):audit.scene_format(doc)
class DoctorCanonicalSourceIntegrity(unittest.TestCase):
 def test_owned_relative_and_absolute_source_paths_resolve_to_same_canonical_authoring(self):
  self.assertEqual(audit.doctor_authoring_path('manual/doctor-scene.yaml'),audit.MANUAL/'doctor-scene.yaml')
  self.assertEqual(audit.doctor_authoring_path(str(audit.MANUAL/'doctor-auto-probe.yaml')),audit.MANUAL/'doctor-auto-probe.yaml')
  with self.assertRaisesRegex(ValueError,'owned Doctor'):audit.doctor_authoring_path('../doctor-scene.yaml')
class DoctorIdentityNamespaceIntegrity(unittest.TestCase):
 def test_driver_receipt_matches_native_application_namespace_exactly(self):
  application=dict(code_root='/frozen/code',digest='app',files=[dict(path='mosaic/mosaic.lua',sha256='lua')])
  native=dict(session_id='native',application_identity=application,runtime_identity=dict(digest='runtime'))
  audit.check_doctor_identity(application,native)
  with self.assertRaisesRegex(ValueError,'application source identity'):audit.check_doctor_identity(dict(application,digest='changed'),native)
class DoctorCollectionIntegrity(unittest.TestCase):
 def test_collection_requires_both_owned_modes_and_exact_native_scene_objects(self):
  scope=dict(publication_kind='doctor-native-audio',passed=True,clock_mode='real-time',complete_regression_run=False,hardware_timing_equivalent=False,controlled_time=dict(applicable=False,reason='Real audio required'))
  application=dict(files=[dict(path='mosaic/mosaic.lua',sha256='unchanged')])
  reports=[dict(scope,source=dict(yaml_path='manual/'+name),source_identity=copy.deepcopy(application),scenes=[dict(id=scene,steps=[dict(inputs=[dict(type='key',n=3,state=1)])])]) for name,scene in [('doctor-scene.yaml','manual'),('doctor-auto-probe.yaml','auto')]]
  collection=dict(scope,schema_version=1,evidence=dict(runs=[dict(report='manual'),dict(report='auto')]),scenes=[report['scenes'][0] for report in reports])
  audit.check_doctor_collection(collection,reports)
  with self.assertRaisesRegex(ValueError,'both Manual and Auto'):audit.check_doctor_collection(dict(collection,scenes=reports[0]['scenes']),reports[:1])
  changed=copy.deepcopy(collection);changed['scenes'][1]['steps'][0]['inputs'][0]['n']=2
  with self.assertRaisesRegex(ValueError,'exact native scenes'):audit.check_doctor_collection(changed,reports)
  changed=copy.deepcopy(reports);changed[1]['source_identity']['files'][0]['sha256']='other'
  with self.assertRaisesRegex(ValueError,'Mosaic source identities'):audit.check_doctor_collection(collection,changed)
class RawPublicationPipelineIntegrity(unittest.TestCase):
 def test_raw_audit_dispatches_all_native_families_without_compiling(self):
  from contextlib import ExitStack
  import types
  with tempfile.TemporaryDirectory() as directory:
   manual=Path(directory);generated=manual/'generated';generated.mkdir()
   docs={'reference.json':dict(scenes=[{}],source={},clock_mode='real-time'),'generic.json':dict(scenes=[{}],feature={},validation={}),'routes.json':dict(publication_kind='audio-route-projection',scenes=[{}]),'doctor.json':dict(publication_kind='doctor-native-audio',scenes=[{}])}
   for name,doc in docs.items():(generated/name).write_text(json.dumps(doc))
   # A stale book is deliberately irrelevant to raw evidence acceptance.
   (generated/'book.json').write_text('{}')
   with ExitStack() as stack:
    stack.enter_context(patch.object(audit,'MANUAL',manual))
    stack.enter_context(patch.object(audit,'audit_audio_session_integrity',return_value={}))
    stack.enter_context(patch.object(audit,'compile_book',side_effect=AssertionError('Raw evidence must not compile')))
    checks={name:stack.enter_context(patch.object(audit,name,return_value=value)) for name,value in [('audit_pilot',{'frames':1}),('audit_reference',2),('audit_generic',{'frames':3}),('audit_doctor',{'frames':4})]}
    routes=stack.enter_context(patch.dict(sys.modules,{'manual_player_routes':types.SimpleNamespace(audit=lambda path:dict(frames=5)),'manual_audio':types.SimpleNamespace(audit_publication=lambda:dict(passed=True))}))
    report=audit.audit_raw_publications()
   self.assertTrue(report['passed']);self.assertFalse(report['complete_regression_run']);self.assertFalse(report['hardware_timing_verified'])
   self.assertEqual([r['frames'] for r in report['references']],[2]);self.assertEqual([r['frames'] for r in report['generic']],[3]);self.assertEqual([r['frames'] for r in report['specialized']],[4,5])
   for check in checks.values():check.assert_called_once()
 def test_raw_audit_keeps_native_failure_and_unknown_dataset_fail_closed(self):
  import types
  with tempfile.TemporaryDirectory() as directory:
   manual=Path(directory);generated=manual/'generated';generated.mkdir();target=generated/'reference.json'
   target.write_text(json.dumps(dict(scenes=[{}],source={},clock_mode='real-time')))
   with patch.object(audit,'audit_audio_session_integrity',return_value={}),patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_pilot',return_value={}),patch.object(audit,'audit_reference',side_effect=ValueError('Stale native Mosaic source')),patch.dict(sys.modules,{'manual_audio':types.SimpleNamespace(audit_publication=lambda:dict(passed=True))}):
    with self.assertRaisesRegex(ValueError,'Stale native Mosaic source'):audit.audit_raw_publications()
    target.write_text(json.dumps(dict(scenes=[dict(id='unsupported')])))
    with self.assertRaisesRegex(ValueError,'Unrecognised scene publication'):audit.audit_raw_publications()
 def test_full_audit_still_rejects_stale_book_before_accepting_raw_evidence(self):
  with tempfile.TemporaryDirectory() as directory:
   manual=Path(directory);(manual/'generated').mkdir();(manual/'generated/book.json').write_text('{}')
   with patch.object(audit,'MANUAL',manual),patch.object(audit,'load',return_value={}),patch.object(audit,'compile_book',return_value=dict(features={})),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True)) as raw:
    with self.assertRaisesRegex(ValueError,'Stale compiled book'):audit.audit_publication()
   raw.assert_not_called()
 def test_full_audit_preserves_compiled_contract_checks_and_raw_report(self):
  with tempfile.TemporaryDirectory() as directory:
   manual=Path(directory);(manual/'generated').mkdir();book=dict(features={'feature':{}},scenes={'scene':{'id':'scene'}});(manual/'generated/book.json').write_text(json.dumps(book));raw_report=dict(passed=True,complete_regression_run=False,hardware_timing_verified=False,pilot={'frames':7})
   with patch.object(audit,'MANUAL',manual),patch.object(audit,'load',return_value={}),patch.object(audit,'compile_book',return_value=book),patch.object(audit,'audit_reader_projection',return_value=dict(passed=True,fixture=True)) as reader,patch.object(audit,'capture_catalogue',return_value={'scene':{'id':'raw'}}),patch.object(audit,'check_compiled_scene_contract') as contract,patch.object(audit,'audit_raw_publications',return_value=raw_report) as raw:
    report=audit.audit_publication()
   contract.assert_called_once_with({'id':'raw'},{'id':'scene'});raw.assert_called_once_with();self.assertEqual(report,dict(raw_report,features=1,reader_projection=dict(passed=True,fixture=True)));reader.assert_called_once_with()
 def test_cli_raw_only_dispatch_and_conflicting_modes(self):
  import io
  with patch.object(sys,'argv',['manual_publication_verify.py','--raw-only']),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True)) as raw,patch.object(audit,'audit_publication',side_effect=AssertionError('Full audit selected')),patch('sys.stdout',new_callable=io.StringIO) as output:
   audit.main();self.assertTrue(json.loads(output.getvalue())['passed'])
  raw.assert_called_once_with()
  with patch.object(sys,'argv',['manual_publication_verify.py','--raw-only','--refresh-editorial']),patch('sys.stderr',new_callable=io.StringIO):
   with self.assertRaises(SystemExit):audit.main()
class VerifiedCoursePublicationIntegrity(unittest.TestCase):
 def test_verified_course_requires_independent_durable_proof(self):
  import types
  from unittest.mock import Mock
  book=dict(features={},scenes={},project=dict(capture_status='verified'))
  with tempfile.TemporaryDirectory() as directory:
   manual=Path(directory);(manual/'generated').mkdir();(manual/'generated/book.json').write_text(json.dumps(book))
   verify=Mock(side_effect=ValueError('Missing durable course binding receipt'))
   with patch.object(audit,'MANUAL',manual),patch.object(audit,'load',return_value={}),patch.object(audit,'compile_book',return_value=book),patch.object(audit,'audit_reader_projection',return_value=dict(passed=True,fixture=True)) as reader,patch.object(audit,'capture_catalogue',return_value={}),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True)),patch.dict(sys.modules,{'manual_course_bind':types.SimpleNamespace(verify_publication=verify)}):
    with self.assertRaisesRegex(ValueError,'Missing durable course'):audit.audit_publication()
   verify.assert_called_once_with(root=audit.ROOT);reader.assert_called_once_with()
 def test_valid_course_proof_is_reported_and_pending_course_needs_no_proof(self):
  import types
  from unittest.mock import Mock
  for status in ('verified','pending'):
   book=dict(features={},scenes={},project=dict(capture_status=status));proof=dict(passed=True,mappings=[dict(stage='one')],lanes=['real','controlled']);verify=Mock(return_value=proof)
   with tempfile.TemporaryDirectory() as directory:
    manual=Path(directory);(manual/'generated').mkdir();(manual/'generated/book.json').write_text(json.dumps(book))
    with patch.object(audit,'MANUAL',manual),patch.object(audit,'load',return_value={}),patch.object(audit,'compile_book',return_value=book),patch.object(audit,'audit_reader_projection',return_value=dict(passed=True,fixture=True)) as reader,patch.object(audit,'capture_catalogue',return_value={}),patch.object(audit,'audit_raw_publications',return_value=dict(passed=True)),patch.dict(sys.modules,{'manual_course_bind':types.SimpleNamespace(verify_publication=verify)}):report=audit.audit_publication()
   reader.assert_called_once_with();self.assertEqual(report['reader_projection'],dict(passed=True,fixture=True))
   if status=='verified':verify.assert_called_once_with(root=audit.ROOT);self.assertEqual(report['course'],proof)
   else:verify.assert_not_called();self.assertNotIn('course',report)
 def test_raw_audit_never_invokes_course_promotion_or_proof(self):
  import types
  with tempfile.TemporaryDirectory() as directory:
   manual=Path(directory);(manual/'generated').mkdir()
   with patch.object(audit,'audit_audio_session_integrity',return_value={}),patch.object(audit,'MANUAL',manual),patch.object(audit,'audit_pilot',return_value={}),patch.dict(sys.modules,{'manual_audio':types.SimpleNamespace(audit_publication=lambda:dict(passed=True)),'manual_course_bind':types.SimpleNamespace(verify_publication=lambda **kw:(_ for _ in ()).throw(AssertionError('Raw audit cannot depend on course proof')))}):self.assertTrue(audit.audit_raw_publications()['passed'])
class SongQueuedNativeIntegrity(unittest.TestCase):
 def test_bound_documentation_image_can_repeat_after_sample_with_changed_midi(self):
  obs=[dict(monotonic_ns=i*10,state=dict(frame=dict(sha256='same'),grid=[1],midi_count=i)) for i in range(3)]
  row=dict(samples=[dict(observation_index=1)])
  events=[dict(kind='input',type=3,monotonic_ns=30)]
  audit.check_queue_documentation(row,dict(sha256='same'),[1],obs,events)
  for change in ('stale','grid','next_gesture'):
   bad=copy.deepcopy(obs)
   if change=='stale':bad[1]['state']['frame']['sha256']='other';bad[2]['state']['frame']['sha256']='other'
   elif change=='grid':bad[1]['state']['grid']=[7];bad[2]['state']['grid']=[7]
   else:bad[1]['state']['frame']['sha256']='other';bad[2]['monotonic_ns']=31
   with self.subTest(change=change),self.assertRaises(ValueError):audit.check_queue_documentation(row,dict(sha256='same'),[1],bad,events)

 def blink(self,clock='controlled-experimental'):
  import base64,hashlib
  observations=[];samples=[];pixels=bytes(32768);sha=hashlib.sha256(pixels).hexdigest()
  for index in range(7):
   t=1000000000+index*400000000;levels=[1 if index%2==0 else 7,15,2];state=dict(frame=dict(sha256=sha,pixels_base64=base64.b64encode(pixels).decode()),grid=levels+[0]*125,clock=dict(logical_ns=t))
   observations.append(dict(monotonic_ns=t,state=state));samples.append(dict(observation_index=index,frame_sha256=sha,grid_sha256=audit.canonical_hash(state['grid']),monotonic_ns=t,logical_ns=t if clock=='controlled-experimental' else None,levels=levels))
  row=dict(queued_slot=1,playing_slot=2,period_ns=400000000,samples=samples,recipe_start_index=0,recipe_end_index=2,input_sequence=1,native=dict(sequence=11,monotonic_ns=900000000))
  recipe=[dict(type='grid',x=1,y=1,state=v) for v in (1,0)];events=[];actions=[]
  for index,action in enumerate(recipe):
   native=dict(sequence=11+index,monotonic_ns=900000000+index);actions.append(dict(request=dict(sequence=1+index,action=action),ack=dict(status='applied',native=native)));events.append(dict(kind='input',sequence=11+index,type=3,args=[0,0,action['state']],monotonic_ns=native['monotonic_ns']))
  for action in actions:
   n=action['ack']['native'];events.extend([dict(kind=4,id=n['sequence'],monotonic_ns=n['monotonic_ns']),dict(kind='input_timing',sequence=n['sequence'],submission_start_ns=n['monotonic_ns'],submitted_ns=n['monotonic_ns'],native_ack_ns=n['monotonic_ns'],monotonic_ns=n['monotonic_ns'])])
  return row,observations,recipe,events,actions
 def test_blink_requires_exact_raw_samples_clock_and_both_public_edges(self):
  args=self.blink();audit.check_song_queue_blink(*args,'controlled-experimental')
  row,obs,recipe,events,actions=args
  bad=copy.deepcopy(row);bad['samples'][1]['levels'][0]=1
  with self.assertRaisesRegex(ValueError,'native queue sample'):audit.check_song_queue_blink(bad,obs,recipe,events,actions,'controlled-experimental')
  bad=copy.deepcopy(obs);bad[1]['state']['clock']['logical_ns']+=1
  with self.assertRaisesRegex(ValueError,'queue sample clock'):audit.check_song_queue_blink(row,bad,recipe,events,actions,'controlled-experimental')
  badrow=copy.deepcopy(row);badobs=copy.deepcopy(obs);badobs[1]['state']['clock']['logical_ns']+=1;badrow['samples'][1]['logical_ns']+=1
  with self.assertRaisesRegex(ValueError,'queue sample period'):audit.check_song_queue_blink(badrow,badobs,recipe,events,actions,'controlled-experimental')
  badrow=copy.deepcopy(row);badobs=copy.deepcopy(obs);badobs[1]['state']['grid'][0]=1;badrow['samples'][1]['levels'][0]=1;badrow['samples'][1]['grid_sha256']=audit.canonical_hash(badobs[1]['state']['grid'])
  with self.assertRaisesRegex(ValueError,'native queue sample'):audit.check_song_queue_blink(badrow,badobs,recipe,events,actions,'controlled-experimental')
  with self.assertRaisesRegex(ValueError,'native queue input|native applied input'):audit.check_song_queue_blink(row,obs,recipe,events[:1],actions,'controlled-experimental')
  bad=copy.deepcopy(row);bad['samples'][1]['observation_index']=0
  with self.assertRaisesRegex(ValueError,'seven distinct'):audit.check_song_queue_blink(bad,obs,recipe,events,actions,'controlled-experimental')
 def real_blink(self):
  row,old,recipe,events,actions=self.blink('real-time');events=events[:2];sha=old[0]['state']['frame']['sha256'];pixels=old[0]['state']['frame']['pixels_base64'];observations=[];samples=[]
  timing=dict(blink_period_ns=400000000,grid_flush_period_ns=50000000,real_clock_allowance_ns=10000000,min_transition_ns=340000000,max_transition_ns=460000000,observation_poll_ns=30000000,window_ns=3330000000,source='mosaic.lua blink clock.sleep(0.4); grid_redraw clock.sleep(1/20); existing real musical allowance0.01s')
  for i in range(9):events.append(dict(kind=2,id=3,monotonic_ns=1000000000+i*400000000,leds=[1 if i%2==0 else 7,15,2]+[0]*125))
  for i in range(112):
   t=1000000000+i*30000000;revision=(t-1000000000)//400000000+1;grid=events[revision+1]['leds'];state=dict(frame=dict(sha256=sha,pixels_base64=pixels),grid=grid,clock=dict(mode='real-time',logical_ns=None));observations.append(dict(monotonic_ns=t,grid_revision=revision,state=state));samples.append(dict(observation_index=i,frame_sha256=sha,grid_sha256=audit.canonical_hash(grid),grid_revision=revision,monotonic_ns=t,logical_ns=None,levels=grid[:3]))
  transitions=[dict(native_event_index=i,id=e['id'],monotonic_ns=e['monotonic_ns'],leds_sha256=audit.canonical_hash(e['leds']),levels=e['leds'][:3]) for i,e in enumerate(events) if e.get('kind')==2 and samples[0]['monotonic_ns']<e['monotonic_ns']<=samples[-1]['monotonic_ns']];row.update(samples=samples,timing_contract=timing,native_grid_transitions=transitions);events.append(dict(kind=1,sha256=sha))
  for action in actions:
   n=action['ack']['native'];events.extend([dict(kind=4,id=n['sequence'],monotonic_ns=n['monotonic_ns']),dict(kind='input_timing',sequence=n['sequence'],submission_start_ns=n['monotonic_ns'],submitted_ns=n['monotonic_ns'],native_ack_ns=n['monotonic_ns'],monotonic_ns=n['monotonic_ns'])])
  return row,observations,recipe,events,actions
 def test_real_applied_time_binds_native_timing_not_received_input_time(self):
  row,obs,recipe,events,actions=self.real_blink()
  for action in actions:
   native=action['ack']['native'];original=native['monotonic_ns'];native['monotonic_ns']=original+20
   next(e for e in events if e.get('kind')==4 and e.get('id')==native['sequence'])['monotonic_ns']=original+20
   next(e for e in events if e.get('kind')=='input_timing' and e.get('sequence')==native['sequence']).update(submission_start_ns=original+1,submitted_ns=original+2,native_ack_ns=original+20,monotonic_ns=original+21)
  row['native']=copy.deepcopy(actions[0]['ack']['native'])
  audit.check_song_queue_blink(row,obs,recipe,events,actions,'real-time')
  for change in ('wrong_applied','reordered','wrong_input','missing_timing'):
   bad=copy.deepcopy(events)
   if change=='wrong_applied':bad[-1]['native_ack_ns']+=1
   elif change=='reordered':bad[-1]['submitted_ns']=bad[-1]['monotonic_ns']+1
   elif change=='wrong_input':bad[0]['args']=[0,1,1]
   else:bad.pop()
   with self.subTest(change=change),self.assertRaises(ValueError):audit.check_song_queue_blink(row,obs,recipe,bad,actions,'real-time')
 def test_real_blink_uses_actual_complete_waveform_and_exact_grid_revision(self):
  args=self.real_blink();receipt=audit.check_song_queue_blink(*args,'real-time');self.assertEqual(receipt['sample_span_ns'],3330000000)
  for change in ('missing','forged','grid_revision','alias','neighbors','stuck','too_slow','too_fast','unbounded','dropout'):
   row,obs,recipe,events,actions=copy.deepcopy(args)
   if change=='missing':row.pop('native_grid_transitions')
   elif change=='forged':row['native_grid_transitions'][0]['levels'][0]=1
   elif change=='grid_revision':row['samples'][2]['grid_revision']=2
   elif change=='alias':row['samples']=row['samples'][::14]
   elif change=='neighbors':events[4]['leds'][1]=7
   elif change=='stuck':
    for e in events:
     if e.get('kind')==2:e['leds'][0]=1
   elif change=='too_slow':events[4]['monotonic_ns']+=61000000
   elif change=='too_fast':events[4]['monotonic_ns']-=100000000
   elif change=='unbounded':row['timing_contract']['max_transition_ns']=900000000
   else:events[:]=[e for i,e in enumerate(events) if i not in (4,5)]
   # For native timing/shape defects, keep all receipt hashes and samples
   # coherent so rejection proves the bound, not merely stale metadata.
   if change in ('stuck','too_slow','too_fast','dropout'):
    grids=[(i,e) for i,e in enumerate(events) if e.get('kind')==2]
    for sample in row['samples']:
     selected=[(ordinal,e) for ordinal,(i,e) in enumerate(grids,1) if e['monotonic_ns']<=sample['monotonic_ns']];revision,event=selected[-1];state=obs[sample['observation_index']]['state'];state['grid']=event['leds'];obs[sample['observation_index']]['grid_revision']=revision;sample.update(grid_revision=revision,levels=event['leds'][:3],grid_sha256=audit.canonical_hash(event['leds']))
    transitions=[];previous=row['samples'][0]['levels'][0]
    for i,e in grids:
     if row['samples'][0]['monotonic_ns']<e['monotonic_ns']<=row['samples'][-1]['monotonic_ns'] and e['leds'][0]!=previous:
      transitions.append(dict(native_event_index=i,id=e['id'],monotonic_ns=e['monotonic_ns'],leds_sha256=audit.canonical_hash(e['leds']),levels=e['leds'][:3]));previous=e['leds'][0]
    row['native_grid_transitions']=transitions
   with self.subTest(change=change),self.assertRaises(ValueError):audit.check_song_queue_blink(row,obs,recipe,events,actions,'real-time')
 def test_transition_checks_onset64_all_gates_and_final_transport(self):
  events=[]
  for index in range(69):
   pitch=[60,62,64,65][index%4]+(12 if index>=64 else 0);velocity=[127,117,107,97][index%4];t=1000000000+round(index/6*1e9)
   events.append(dict(kind=11,index=2*index+1,port=1,bytes=[144,pitch,velocity],logical_ns=t));events.append(dict(kind=11,index=2*index+2,port=1,bytes=[128,pitch,velocity],logical_ns=t+round((1/6 if index<68 else .01)*1e9)))
  events.sort(key=lambda e:(e['logical_ns'],e['index']))
  for index,event in enumerate(events):event['index']=index+1
  row=dict(midi_start_index=0,from_slot=2,to_slot=1,transition_index=64,old_phrase=[60,62,64,65],new_phrase=[72,74,76,77],velocities=[127,117,107,97],onsets=69,onset_spacing_seconds=1/6,tolerance_seconds=2e-9,levels=[15,7,2]);state=dict(grid=[15,7,2]+[0]*109+[2]+[0]*15,midi_count=len(events),midi_capture=dict(outstanding=[]))
  audit.check_song_queue_transition(row,state,events,'controlled-experimental')
  bad=copy.deepcopy(events);next(e for e in bad if e['bytes'][0]==144 and e['bytes'][1]==72)['bytes'][1]=60
  with self.assertRaisesRegex(ValueError,'queue wire phrase'):audit.check_song_queue_transition(row,state,bad,'controlled-experimental')
  bad=copy.deepcopy(events);next(e for e in bad if e['bytes'][0]==128)['logical_ns']+=10000000
  with self.assertRaisesRegex(ValueError,'queue gate'):audit.check_song_queue_transition(row,state,bad,'controlled-experimental')
  state['midi_capture']['outstanding']=[60]
  with self.assertRaisesRegex(ValueError,'queue transport'):audit.check_song_queue_transition(row,state,events,'controlled-experimental')
class AudioComparisonPublicationIntegrity(unittest.TestCase):
 def comparison(self):
  source=dict(id='ghost-note-comparison',purpose='lesson-comparison',tracks=[dict(channel=1,voice='Oilcan 1')],phase_changes=[])
  record=dict(midi_witness=dict(passed=True),phase_observations=[],lesson_pcm=dict(kind='ghost-note-interiors',passed=True),evidence=dict(path='/native/mix'))
  example=dict(source,**record,solo_contributions=[dict(record,channel=1,voice='Oilcan 1',evidence=dict(path='/native/solo'))],musical_evidence=[dict(clock_mode=clock,path='/native/'+clock,passed=True) for clock in ('real-time','controlled-experimental')])
  return dict(examples=[example]),dict(examples=[source])
 def test_comparison_presence_inventory_and_distinct_sessions_are_mandatory(self):
  report,source=self.comparison();sessions=audit.check_audio_capture_scope(report,source);self.assertEqual(len(sessions),4)
  bad=copy.deepcopy(report);bad['examples'][0]['solo_contributions'][0].pop('lesson_pcm')
  with self.assertRaisesRegex(ValueError,'lesson PCM'):audit.check_audio_capture_scope(bad,source)
  bad=copy.deepcopy(report);bad['examples'][0]['musical_evidence'][1]['clock_mode']='real-time'
  with self.assertRaisesRegex(ValueError,'both MIDI lanes'):audit.check_audio_capture_scope(bad,source)
  bad=copy.deepcopy(report);bad['examples'].append(copy.deepcopy(bad['examples'][0]))
  with self.assertRaisesRegex(ValueError,'unique audio inventory'):audit.check_audio_capture_scope(bad,source)
  bad=copy.deepcopy(report);bad['examples'][0]['solo_contributions'][0]['evidence']['path']='/native/mix'
  with self.assertRaisesRegex(ValueError,'distinct native audio sessions'):audit.check_audio_capture_scope(bad,source)
  bad=copy.deepcopy(report);authored=copy.deepcopy(source);bad['examples'][0]['id']='invented-lesson';authored['examples'][0]['id']='invented-lesson'
  with self.assertRaisesRegex(ValueError,'Unsupported new audio lesson'):audit.check_audio_capture_scope(bad,authored)
 def test_native_audio_session_must_match_clock_trace_cleanup_and_released_state(self):
  with tempfile.TemporaryDirectory() as directory:
   out=Path(directory);(out/'native').mkdir();files={'native/native-config.json':dict(clock_mode='real-time'),'native/identity.json':dict(application_identity=dict(files=[dict(path='mosaic/mosaic.lua',sha256='source')])), 'results.json':[dict(passed=True)],'recipe.json':[dict(type='key',n=3,state=1),dict(type='key',n=3,state=0)],'observations.json':[dict(state=dict(clock=dict(mode='real-time'),held=[],midi_capture=dict(outstanding=[])))],'native/cleanup.json':[dict(service='sclang',returncode=-15),dict(service='bridge',returncode=0)]}
   for name,value in files.items():(out/name).write_text(json.dumps(value))
   events=[dict(kind='input',type=1,args=[3,v]) for v in (1,0)];(out/'native/native-events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
   with patch.object(audit,'native_source_identity',return_value={}):
    audit.check_audio_native_session(out,'real-time',True)
    (out/'native/native-config.json').write_text(json.dumps(dict(clock_mode='controlled-experimental')))
    with self.assertRaisesRegex(ValueError,'actual native audio clock'):audit.check_audio_native_session(out,'real-time',True)
    (out/'native/native-config.json').write_text(json.dumps(files['native/native-config.json']))
    bad=copy.deepcopy(files['observations.json']);bad[-1]['state']['held']=[dict(type='key',n=3)];(out/'observations.json').write_text(json.dumps(bad))
    with self.assertRaisesRegex(ValueError,'released native audio'):audit.check_audio_native_session(out,'real-time',True)
    (out/'observations.json').write_text(json.dumps(files['observations.json']));(out/'native/native-events.jsonl').write_text(json.dumps(events[0])+'\n')
    with self.assertRaisesRegex(ValueError,'full-session inputs'):audit.check_audio_native_session(out,'real-time',True)
class NewPublicationSemanticDispatchIntegrity(unittest.TestCase):
 def test_new_merge_and_public_kinds_cannot_silently_bypass_native_audit(self):
  for kind in ('merge-strategy-invented','effective-invented-result','public-invented-readability'):
   with self.assertRaisesRegex(ValueError,'Unsupported'):audit.check_custom_kind(kind)
 def test_only_silence_cannot_pass_from_empty_authored_arrays(self):
  row=dict(kind='effective-only-silence',loops=2,loop_steps=8,expected=[],actual=[],passed=True)
  with self.assertRaisesRegex(ValueError,'witness'):audit.check_merge_music(row,[],[],[],'controlled-experimental')
 def test_only_requires_two_cycles_bounded_by_actual_public_play_stop(self):
  import base64,hashlib
  sha=hashlib.sha256(bytes(32768)).hexdigest();observations=[];witness={}
  for index,name in enumerate(('start','end')):
   time=index*3000000000;state=dict(frame=dict(sha256=sha,pixels_base64=base64.b64encode(bytes(32768)).decode()),grid=[0]*128,midi_count=0,clock=dict(mode='controlled-experimental',logical_ns=time),midi_capture=dict(outstanding=[]))
   observations.append(dict(monotonic_ns=time,state=state));witness[name]=dict(observation_index=index,frame_sha256=sha,midi_count=0,midi_outstanding=[],grid_sha256=audit.canonical_hash([0]*128),monotonic_ns=time,logical_ns=time,recipe_index=index*4)
  recipe=[dict(type='grid',x=1,y=8,state=z) for z in (1,0,1,0)]
  row=dict(kind='effective-only-silence',loops=2,loop_steps=8,expected=[],actual=[],passed=True,witness=witness)
  events=[dict(kind='input',type=3,args=[0,7,z],monotonic_ns=i*1000000000) for i,z in enumerate((1,0,1,0))];events.insert(2,dict(kind='input',type=8,args=[2,666666667],monotonic_ns=1500000000));events +=[dict(kind=1,sha256=sha),dict(kind=2,leds=[0]*128)]
  audit.check_merge_music(row,observations,recipe,events,'controlled-experimental')
  forged=copy.deepcopy(observations);forged[0]['state']['frame']['pixels_base64']=base64.b64encode(bytes([1])*32768).decode()
  with self.assertRaisesRegex(ValueError,'frame/hash'):audit.check_merge_music(row,forged,recipe,events,'controlled-experimental')
  short=copy.deepcopy(events);short[2]['args']=[1,0]
  with self.assertRaisesRegex(ValueError,'two complete'):audit.check_merge_music(row,observations,recipe,short,'controlled-experimental')
  bad=copy.deepcopy(row);bad['witness']['end']['logical_ns']=1000000000;bad_obs=copy.deepcopy(observations);bad_obs[-1]['state']['clock']['logical_ns']=1000000000
  with self.assertRaisesRegex(ValueError,'observation clock'):audit.check_merge_music(bad,bad_obs,recipe,events,'controlled-experimental')
  with self.assertRaisesRegex(ValueError,'Play and Stop'):audit.check_merge_music(row,observations,recipe[:2]+[dict(type='enc',n=3,delta=1)]*2,events,'controlled-experimental')
 def test_readability_requires_real_sample_receipts(self):
  row=dict(kind='public-assignment-marquee',enabled=True,label='Quantised Fixed Note',value='CURRENT',samples=[],passed=True)
  with self.assertRaisesRegex(ValueError,'sample'):audit.check_readability_samples(row,[],[],Path('/unavailable'))
class MiniReadabilityPublicationIntegrity(unittest.TestCase):
 def fixture(self):
  import base64,hashlib
  atlas=json.loads((audit.ROOT/'tests/behaviour/contract/mini_header_atlas_v2.json').read_text());spec=next(item for item in atlas['screens'] if item['id']=='C04');states=[];samples=[];events=[];seen=set()
  for index,frame in enumerate(spec['frames']):
   pixels=bytearray(32768)
   for y,line in enumerate(frame):
    for x,letter in enumerate(line):
     i=((spec['origin'][1]+y)*128+spec['origin'][0]+x)*4;pixels[i:i+3]=bytes([17*{'.':0,'a':7,'b':11,'c':15}[letter]])*3
   sha=hashlib.sha256(pixels).hexdigest();matching=[i for i,target in enumerate(spec['frames']) if target==frame];seen.update(matching)
   for part in (0,1):
    ns=index*250000000+part*125000000;diag=dict(beats=index*.25+.05+part*.05,tempo=90,clock_epoch=0,monotonic_ns=ns+10000000)
    states.append(dict(frame_revision=index+1,monotonic_ns=ns+20000000,state=dict(frame=dict(sha256=sha,pixels_base64=base64.b64encode(pixels).decode()),grid=[0]*128,midi_count=0,midi_capture=dict(outstanding=[]),clock=dict(mode='controlled-experimental',logical_ns=ns),diagnostics=diag)))
   samples.append(dict(observation_index=index*2+1,clock_before_observation_index=index*2,clock_after_observation_index=index*2+1,frame_sha256=sha,frame_revision=index+1,monotonic_ns=states[-1]['monotonic_ns'],matching_poses=matching,clock_before=copy.deepcopy(states[-2]['state']['diagnostics']),clock_after=copy.deepcopy(states[-1]['state']['diagnostics']),native_clock=copy.deepcopy(states[-1]['state']['diagnostics'])));events.append(dict(kind=1,sha256=sha,revision=index+1,monotonic_ns=index*250000000+60000000))
  row=dict(kind='public-mini-header',page='C04',enabled=True,tempo=90,clock_source='native-selected-norns-clock',transport='stopped',pose_count=len(spec['frames']),loop_quarter_beats=spec['loop_quarter_beats'],samples=samples,observed_poses=sorted(seen),all_distinct_poses_required=True,atlas_sha256='4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46')
  from mini_phase_oracle import check_stopped_phase
  for item in samples:item['phase_check']=check_stopped_phase(item,states,events,spec,True,90,'controlled-experimental')
  events.append(dict(kind=2,leds=[0]*128))
  return row,states,events
 def test_literal_mini_pose_and_stationary_controls_are_independently_checked(self):
  row,states,events=self.fixture()
  with self.assertRaisesRegex(ValueError,'native grid'):audit.check_mini_samples(row,states,events[:-1])
  audit.check_mini_samples(row,states,events)
  wrongclock=copy.deepcopy(states);wrongrow=copy.deepcopy(row)
  for i in (0,1):wrongclock[i]['state']['diagnostics']['beats']+=.25
  wrongrow['samples'][0]['clock_before']=copy.deepcopy(wrongclock[0]['state']['diagnostics']);wrongrow['samples'][0]['clock_after']=copy.deepcopy(wrongclock[1]['state']['diagnostics']);wrongrow['samples'][0]['native_clock']=copy.deepcopy(wrongclock[1]['state']['diagnostics'])
  with self.assertRaisesRegex(ValueError,'pose phase'):audit.check_mini_samples(wrongrow,wrongclock,events)
  bad=copy.deepcopy(row);bad['samples'][0]['matching_poses']=[999]
  with self.assertRaisesRegex(ValueError,'bitmap'):audit.check_mini_samples(bad,states,events)
  badstates=copy.deepcopy(states);badstates[-1]['state']['grid'][0]=15
  with self.assertRaisesRegex(ValueError,'native grid|stationary'):audit.check_mini_samples(row,badstates,events)
 def test_mini_cannot_accept_declared_pose_without_native_samples(self):
  with self.assertRaisesRegex(ValueError,'sample'):audit.check_mini_samples(dict(kind='public-mini-header',samples=[]),[],[])
class MergeFieldNativePublicationIntegrity(unittest.TestCase):
 def test_extra_fields_cannot_hide_missing_active_and_all_fields_are_rechecked(self):
  def field(label,value):return dict(layout='detail',label=label,value=value,observation_index=0,frame_sha256='sha')
  fields=[field('Strategy','FOUNDATION'),field('Unrelated','value')];row=dict(kind='merge-strategy-ui',checkpoint='foundation-active',strategy='FOUNDATION',active='FOUNDATION',witness={},fields=fields)
  results=[dict(kind='selected-field',**item) for item in fields]
  with patch.object(audit,'exact_observation',return_value={}),patch.object(audit,'verify_cached_ui') as verify:
   with self.assertRaisesRegex(ValueError,'coverage'):audit.check_merge_ui(row,[],[],Path('/native'),results,len(results))
   fields.append(field('Active','FOUNDATION'));results.append(dict(kind='selected-field',**fields[-1]))
   audit.check_merge_ui(row,[],[],Path('/native'),results,len(results));self.assertEqual(verify.call_count,5)
 def test_raw_dispatch_rejects_real_new_kind_without_any_native_witness(self):
  with tempfile.TemporaryDirectory() as directory:
   out=Path(directory);(out/'native').mkdir();(out/'native/native-events.jsonl').write_text('');(out/'recipe.json').write_text('[]')
   step=dict(output=dict(binding=dict(assertion=dict(kind='effective-only-silence',loops=2,loop_steps=8,expected=[],actual=[]))))
   with self.assertRaisesRegex(ValueError,'witness'):audit.verify_new_public_checkpoint(step,[],out,'controlled-experimental',[])
class PlayingPhaseRawDispatchIntegrity(unittest.TestCase):
 def test_summary_must_call_independent_emitted_clock_phase_audit(self):
  import ast,inspect
  tree=ast.parse(inspect.getsource(audit.check_readability_summary))
  self.assertTrue(any(isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='check_playing_phases' for node in ast.walk(tree)),'Raw summary cannot rely on live passed or bitmap membership alone')



class ReadabilityExactMiniFootprintIntegrity(unittest.TestCase):
 def synthetic(self,enabled=True,page='clock'):
  import base64,hashlib
  atlas=json.loads((audit.ROOT/'tests/behaviour/contract/mini_header_atlas_v2.json').read_text());ident={'clock':'C04','scale':'S01'}[page];spec=next(r for r in atlas['screens'] if r['id']==ident);obs=[];samples=[];events=[]
  for i in range(6):
   pixels=bytearray(32768);frame=spec['frames'][i%len(spec['frames']) if enabled else 0]
   for y,line in enumerate(frame):
    for x,letter in enumerate(line):
     at=((spec['origin'][1]+y)*128+spec['origin'][0]+x)*4;pixels[at:at+3]=bytes([17*{'.':0,'a':7,'b':11,'c':15}[letter]])*3
   sha=hashlib.sha256(pixels).hexdigest();state=dict(frame=dict(sha256=sha,pixels_base64=base64.b64encode(pixels).decode()),grid=[0]*128,midi_count=0);obs.append(dict(state=state));samples.append(dict(observation_index=i,frame_sha256=sha));events.extend([dict(kind=1,sha256=sha),dict(kind=2,leds=[0]*128)])
  label,value={'clock':('Rate','/1'),'scale':('Scale','Major')}[page];row=dict(kind='public-fitting-vertical-text',page=page,enabled=enabled,label=label,value=value,samples=samples);return row,obs,events,spec
 def test_literal_mini_animation_is_allowed_only_in_exact_authored_footprint(self):
  import frame_oracle,base64,hashlib
  for page in ('clock','scale'):
   row,obs,events,spec=self.synthetic(page=page)
   with tempfile.TemporaryDirectory() as directory:
    path=Path(directory);(path/'native').mkdir();(path/'native/identity.json').write_text(json.dumps(dict(runtime_identity=dict(source={}))))
    with patch.object(frame_oracle,'live_header_matches',return_value=True),patch.object(frame_oracle,'vertical_selected_field_matches',return_value=True):
     audit.check_readability_samples(row,obs,events,path)
     for change in ('icon','header','outside_box','neighbor','footer','grid','midi','off_nonrest'):
      r,o,e=copy.deepcopy((row,obs,events))
      if change=='grid':o[1]['state']['grid'][0]=15;e.append(dict(kind=2,leds=o[1]['state']['grid']))
      elif change=='midi':o[1]['state']['midi_count']=1
      elif change=='off_nonrest':r['enabled']=False
      else:
       x,y={'icon':(spec['origin'][0],0),'header':(5,3),'outside_box':(spec['origin'][0]-1,3),'neighbor':(5,45),'footer':(5,60)}[change];data=bytearray(base64.b64decode(o[1]['state']['frame']['pixels_base64']));at=(y*128+x)*4;data[at:at+3]=bytes([255])*3;sha=hashlib.sha256(data).hexdigest();o[1]['state']['frame']=dict(sha256=sha,pixels_base64=base64.b64encode(data).decode());r['samples'][1]['frame_sha256']=sha;e.append(dict(kind=1,sha256=sha))
      with self.subTest(page=page,change=change),self.assertRaises(ValueError):audit.check_readability_samples(r,o,e,path)
 def test_preserved_v10_native_on_rows_close_obsolete_120_geometry_false_rejection(self):
  source=Path('/home/andy/mosaic-mini-header-engineering-v10-qualification-20261003/controlled/2af9e6e4e34c4ec09bcdb42a08ce4980')
  if not source.is_dir():self.skipTest('Immutable local native engineering specimen unavailable; portable mutation regressions still apply')
  rows=json.loads((source/'results.json').read_text());obs=json.loads((source/'observations.json').read_text());events=[json.loads(line) for line in (source/'native/native-events.jsonl').read_text().splitlines()]
  selected=[r for r in rows if r.get('enabled') is True and r.get('kind') in ('public-assignment-marquee','public-fitting-vertical-text')];self.assertEqual(len(selected),3)
  for row in selected:audit.check_readability_samples(row,obs,events,source)

if __name__=='__main__':unittest.main()

class CourseDashboardNativeIntegrity(unittest.TestCase):
 def fixture(self):
  import base64,hashlib,frame_oracle
  if frame_oracle.ROOT is None:self.skipTest('Native oracle font requires MONOME_EMULATOR')
  pixels=frame_oracle.render(frame_oracle._dashboard_row_commands('Global length','16',40));sha=hashlib.sha256(pixels).hexdigest();state=dict(frame=dict(sha256=sha,pixels_base64=base64.b64encode(pixels).decode()),grid=[0]*128)
  row=dict(kind='manual-course-ui',stage='song-composition-global-length-slot1',page='song',params=dict(song_slot=1),header=dict(title='SONG PLAYBACK',scope='SONG 01',layout='dashboard'),dashboard_rows=[dict(row=4,label='Global length',value='16')],native_observation_index=1)
  return row,[dict(state=state),dict(state=copy.deepcopy(state))],dict(sha256=sha),[0]*128
 def test_existing_course_dispatch_cannot_ignore_declared_dashboard_value(self):
  row,obs,binding,grid=self.fixture();row.update(mask_fields=[],leds=[]);row['dashboard_rows'][0]['value']='1';step=dict(output=dict(binding=dict(binding,assertion=row),grid=grid))
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder);(path/'native').mkdir();(path/'native/native-events.jsonl').write_text('')
   # Existing header/field oracle is independently covered; isolate dispatch
   # of the new optional dashboard pixels, which must never be ignored.
   with patch.object(audit,'verify_cached_ui'),self.assertRaises(ValueError):audit.verify_teaching_checkpoint(step,obs,path,'real-time',[row])
 def test_dashboard_length_is_exact_native_pixels_and_own_observation(self):
  row,obs,binding,grid=self.fixture();audit.check_course_dashboard(row,obs,binding,grid)
  for change in ('missing','wrong_value','wrong_row','wrong_index','wrong_grid','stale_header','wrong_frame','native_wrong_value'):
   bad=copy.deepcopy(row);badobs=copy.deepcopy(obs)
   if change=='missing':bad.pop('dashboard_rows')
   elif change=='wrong_value':bad['dashboard_rows'][0]['value']='1'
   elif change=='wrong_row':bad['dashboard_rows'][0]['row']=3
   elif change=='wrong_index':bad['native_observation_index']=99
   elif change=='wrong_grid':badobs[1]['state']['grid'][0]=15
   elif change=='stale_header':bad['header']['scope']='SONG 02'
   elif change=='wrong_frame':badobs[1]['state']['frame']['sha256']='old'
   else:
    import base64,hashlib,frame_oracle
    pixels=frame_oracle.render(frame_oracle._dashboard_row_commands('Global length','1',40));sha=hashlib.sha256(pixels).hexdigest();badobs[1]['state']['frame']=dict(sha256=sha,pixels_base64=base64.b64encode(pixels).decode());binding=dict(sha256=sha)
   with self.subTest(change=change),self.assertRaises(ValueError):audit.check_course_dashboard(bad,badobs,binding,grid)

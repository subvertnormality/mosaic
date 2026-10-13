"""Independent publication-integrity characterisation; never launches native sessions."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import doctor_options_audit as audit
class DoctorScopeIntegrity(unittest.TestCase):
 def report(self):
  return dict(publication_kind='doctor-options-qualification',case='manual_stereo',passed=True,failure=None,cleanup_failure=None,clock_mode='real-time',complete_regression_run=False,hardware_timing_equivalent=False,controlled_time=dict(applicable=False,reason='Actual ADC requires real time'),source='source.json',results='results.json')
 def test_audio_cannot_claim_controlled_time_or_a_failed_qualification(self):
  value=self.report();audit.check_scope(value,'manual_stereo','real-time')
  for field,bad in [('passed',False),('failure','failure'),('cleanup_failure','cleanup'),('hardware_timing_equivalent',True),('complete_regression_run',True)]:
   changed=dict(value,**{field:bad})
   with self.assertRaises(ValueError):audit.check_scope(changed,'manual_stereo','real-time')
  changed=copy.deepcopy(value);changed['controlled_time']['applicable']=True
  with self.assertRaisesRegex(ValueError,'ADC'):audit.check_scope(changed,'manual_stereo','real-time')
  changed=dict(value,clock_mode='controlled-experimental')
  with self.assertRaises(ValueError):audit.check_scope(changed,'manual_stereo','controlled-experimental')
 def test_setup_ready_allow_two_ui_lanes_and_require_exact_role(self):
  value=self.report();value.update(case='setup_options',clock_mode='controlled-experimental',controlled_time=dict(applicable=True,reason='UI only'))
  audit.check_scope(value,'setup_options','controlled-experimental')
  with self.assertRaisesRegex(ValueError,'role'):audit.check_scope(value,'ready_options','controlled-experimental')
 def test_all_seven_unique_reports_are_required(self):
  roles={key:Path('/evidence')/(key+'.json') for key in audit.ROLES};audit.check_roles(roles)
  with self.assertRaisesRegex(ValueError,'seven'):audit.check_roles({key:value for key,value in roles.items() if key!='manual_right'})
  roles['ready_real']=roles['setup_real']
  with self.assertRaisesRegex(ValueError,'distinct'):audit.check_roles(roles)
class DoctorMusicalWindowIntegrity(unittest.TestCase):
 def events(self):
  events=[]
  for cycle in range(3):
   for step,velocity in [(1,100),(17,90)]:
    if cycle==2 and step==17:continue
    onset=1000000000+round((cycle*64+step-1)/6*1e9);events.append(dict(kind=11,index=len(events)+1,port=1,bytes=[144,60,velocity],logical_ns=onset));events.append(dict(kind=11,index=len(events)+1,port=1,bytes=[128,60,velocity],logical_ns=onset+round(1/6*1e9)))
  return events
 def test_whole_phrase_and_release_timing_not_just_positive_attack_count(self):
  events=self.events();audit.check_phrase(events,[1,17],[[1,[144,60,100]],[1,[144,60,90]]],'controlled-experimental',cycles=2,closing=True)
  changed=copy.deepcopy(events);changed[2]['bytes'][2]=100
  with self.assertRaisesRegex(ValueError,'phrase'):audit.check_phrase(changed,[1,17],[[1,[144,60,100]],[1,[144,60,90]]],'controlled-experimental',cycles=2,closing=True)
  with self.assertRaisesRegex(ValueError,'complete'):audit.check_phrase(events[:4],[1,17],[[1,[144,60,100]],[1,[144,60,90]]],'controlled-experimental',cycles=2,closing=True)
  changed=copy.deepcopy(events);changed[1]['logical_ns']+=10000000
  with self.assertRaisesRegex(ValueError,'gate'):audit.check_phrase(changed,[1,17],[[1,[144,60,100]],[1,[144,60,90]]],'controlled-experimental',cycles=2,closing=True)
 def test_setup_lookalikes_outside_explicit_window_are_excluded(self):
  events=self.events();self.assertEqual(audit.native_midi_window(events,2,6,'controlled-experimental'),events[2:6])
  with self.assertRaisesRegex(ValueError,'boundary'):audit.native_midi_window(events,6,2,'controlled-experimental')
class DoctorSelectedInputIntegrity(unittest.TestCase):
 def test_input_selection_requires_the_actual_selected_spectrum(self):
  import math
  left=[.3*math.sin(2*math.pi*60*i/48000) for i in range(48000)];right=[.15*math.sin(2*math.pi*90*i/48000) for i in range(48000)]
  audit.check_selected_channels([left,right],48000,'stereo')
  audit.check_selected_channels([left,left],48000,'left');audit.check_selected_channels([right,right],48000,'right')
  with self.assertRaisesRegex(ValueError,'selected ADC'):audit.check_selected_channels([left,left],48000,'right')
  with self.assertRaisesRegex(ValueError,'duplicate'):audit.check_selected_channels([left,right],48000,'left')
  with self.assertRaisesRegex(ValueError,'distinct'):audit.check_selected_channels([left,left],48000,'stereo')
class DoctorFixtureProvenanceIntegrity(unittest.TestCase):
 def test_fixture_requires_exact_manual_right_parent_and_real_autosave_origin(self):
  fixture=dict(project_seed_origin='application-autosave-after-public-adc',retained_audio=False,bank_bpm=120,window_max=80,beat_count=40,masks_by_sensitivity={'0':[1,17],'0.5':[1],'1':[]},midi_expected=[[1,[144,60,100]]])
  audit.check_fixture_contract(fixture)
  changed=dict(fixture,project_seed_origin='invented-bank')
  with self.assertRaisesRegex(ValueError,'autosave'):audit.check_fixture_contract(changed)
  changed=dict(fixture,retained_audio=True)
  with self.assertRaisesRegex(ValueError,'retained'):audit.check_fixture_contract(changed)
  changed=copy.deepcopy(fixture);changed['masks_by_sensitivity']['0.5']=[65]
  with self.assertRaisesRegex(ValueError,'mask'):audit.check_fixture_contract(changed)

class DoctorNewApiIntegrity(unittest.TestCase):
 def test_report_refuses_a_missing_final_harness_guard_before_any_acceptance(self):
  with tempfile.TemporaryDirectory() as directory:
   report=DoctorScopeIntegrity().report();path=Path(directory)/'report.json';path.write_text(json.dumps(report))
   with self.assertRaisesRegex(ValueError,'harness'):audit.audit_report(path,'manual_stereo','real-time')
 def test_fixture_digest_is_checked_before_parsing(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'fixture.json';path.write_text('not JSON')
   with self.assertRaisesRegex(ValueError,'fixture SHA'):audit.audit_fixture(path,'incorrect',Path(directory)/'report.json')
 def test_native_observation_cannot_replace_a_real_frame_or_grid(self):
  import base64,hashlib
  pixels=bytes(32768);sha=hashlib.sha256(pixels).hexdigest();events=[dict(kind=1,sha256=sha),dict(kind=2,leds=[0]*128)];observations=[dict(state=dict(frame=dict(sha256=sha,pixels_base64=base64.b64encode(pixels).decode()),grid=[0]*128))]
  audit.check_native_observations(events,observations)
  changed=copy.deepcopy(observations);changed[0]['state']['grid'][0]=15
  with self.assertRaisesRegex(ValueError,'native frame/grid'):audit.check_native_observations(events,changed)
 def test_closing_attack_requires_real_release_and_exact_packet_count(self):
  packets=DoctorMusicalWindowIntegrity().events();expected=[[1,[144,60,100]],[1,[144,60,90]]]
  with self.assertRaisesRegex(ValueError,'gate release'):audit.check_phrase(packets[:-1],[1,17],expected,'controlled-experimental',cycles=2,closing=True)
  changed=copy.deepcopy(packets);changed.append(dict(changed[-1],index=changed[-1]['index']+1))
  with self.assertRaisesRegex(ValueError,'unbalanced'):audit.check_phrase(changed,[1,17],expected,'controlled-experimental',cycles=2,closing=True)
 def test_cli_requires_all_seven_explicit_roles_and_fixture_identity(self):
  import io
  with patch.object(sys,'argv',['doctor_options_audit.py','--fixture','/fixture.json','--fixture-sha256','hash']),patch('sys.stderr',new_callable=io.StringIO),patch.object(audit,'audit_qualification',side_effect=AssertionError('Incomplete CLI must not audit')):
   with self.assertRaises(SystemExit):audit.main()

class DoctorPublicStopIntegrity(unittest.TestCase):
 def shortened(self):
  on=dict(kind=11,index=1,port=1,bytes=[144,60,100],logical_ns=1000000000,monotonic_ns=1000000000)
  off=dict(kind=11,index=2,port=1,bytes=[128,60,100],logical_ns=1020000000,monotonic_ns=1020000000)
  press=dict(kind='input',sequence=3,type=3,args=[0,7,1],monotonic_ns=1000000000)
  stop=dict(kind='input',sequence=4,type=3,args=[0,7,0],monotonic_ns=1020000000)
  events=[dict(kind='input',sequence=1,type=8,args=[1,0],monotonic_ns=900000000),on,dict(kind='input',sequence=2,type=8,args=[0,20000000],monotonic_ns=1015000000),press,stop,off]
  return [on,off],events,stop
 def test_shortened_final_gate_cannot_pass_without_actual_public_stop(self):
  packets,events,stop=self.shortened()
  with self.assertRaisesRegex(ValueError,'gate'):audit.check_phrase(packets,[1],[[1,[144,60,100]]],'controlled-experimental')
 def test_actual_stop_time_is_recomputed_from_native_inputs(self):
  packets,events,stop=self.shortened();receipt=audit.bind_public_stop(events,packets,'controlled-experimental');self.assertEqual(receipt['stop_time_ns'],1020000000)
  audit.check_phrase(packets,[1],[[1,[144,60,100]]],'controlled-experimental',stop_time_ns=receipt['stop_time_ns'])
  with self.assertRaisesRegex(ValueError,'gate'):audit.check_phrase(packets,[1],[[1,[144,60,100]]],'controlled-experimental',stop_time_ns=1010000000)
  with self.assertRaisesRegex(ValueError,'public Stop'):audit.bind_public_stop([value for value in events if value!=stop],packets,'controlled-experimental')
  wrong=copy.deepcopy(events);wrong[4]['args']=[1,7,0]
  with self.assertRaisesRegex(ValueError,'public Stop'):audit.bind_public_stop(wrong,packets,'controlled-experimental')
 def test_exact_zero_velocity_public_stop_release_is_a_real_owned_endpoint(self):
  packets,events,stop=self.shortened();packets[-1]['bytes']=[128,60,0]
  receipt=audit.bind_public_stop(events,packets,'controlled-experimental')
  audit.check_phrase(packets,[1],[[1,[144,60,100]]],'controlled-experimental',stop_time_ns=receipt['stop_time_ns'])
  with self.assertRaisesRegex(ValueError,'gate release'):audit.check_phrase(packets,[1],[[1,[144,60,100]]],'controlled-experimental')
 def test_stop_action_anchors_to_release_when_note_starts_during_held_gesture(self):
  on=dict(kind=11,index=1,port=1,bytes=[144,60,100],logical_ns=1010000000,monotonic_ns=1010000000)
  off=dict(kind=11,index=2,port=1,bytes=[128,60,100],logical_ns=1020000000,monotonic_ns=1020000000)
  press=dict(kind='input',sequence=2,type=3,args=[0,7,1],monotonic_ns=1005000000)
  release=dict(kind='input',sequence=5,type=3,args=[0,7,0],monotonic_ns=1020000000)
  events=[dict(kind='input',sequence=1,type=8,args=[1,0],monotonic_ns=1000000000),press,
   dict(kind='input',sequence=3,type=8,args=[0,10000000],monotonic_ns=1010000000),on,
   dict(kind='input',sequence=4,type=8,args=[0,10000000],monotonic_ns=1020000000),release,off]
  receipt=audit.bind_public_stop(events,[on,off],'controlled-experimental')
  self.assertEqual(receipt['stop_time_ns'],1020000000)
  audit.check_phrase([on,off],[1],[[1,[144,60,100]]],'controlled-experimental',stop_time_ns=receipt['stop_time_ns'])
 def test_real_stop_uses_native_monotonic_clock(self):
  packets,events,stop=self.shortened();receipt=audit.bind_public_stop(events,packets,'real-time');self.assertEqual(receipt['stop_time_ns'],1020000000)
  wrong=copy.deepcopy(events);wrong[4]['monotonic_ns']=1040000000
  with self.assertRaisesRegex(ValueError,'Stop release'):audit.bind_public_stop(wrong,packets,'real-time')
class DoctorProductionInventoryIntegrity(unittest.TestCase):
 def test_unloaded_production_source_cannot_be_omitted_from_snapshot(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'lib').mkdir();(root/'mosaic.lua').write_text('main');(root/'lib/unloaded.lua').write_text('changed route')
   with self.assertRaisesRegex(ValueError,'production inventory'):audit.check_production_inventory({'mosaic.lua':'sha'},root)
   audit.check_production_inventory({'mosaic.lua':'sha','lib/unloaded.lua':'sha'},root)
 def test_backend_templates_and_runtime_json_are_required_but_manual_outputs_are_not(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'mosaic.lua').write_text('main')
   for name in ('lib/runtime/map.json','tools/rhythm_doctor/data/templates.bin','docs/ui-reimplementation/code/render.lua','manual/generated/book.json'):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('bytes')
   names={'mosaic.lua','lib/runtime/map.json','tools/rhythm_doctor/data/templates.bin','docs/ui-reimplementation/code/render.lua'}
   audit.check_production_inventory(dict.fromkeys(names,'sha'),root)
   for omitted in names-{'mosaic.lua'}:
    with self.assertRaisesRegex(ValueError,'production inventory'):audit.check_production_inventory(dict.fromkeys(names-{omitted},'sha'),root)
 def test_startup_spec_is_mandatory_harness_dependency(self):
  with self.assertRaisesRegex(ValueError,'harness provenance'):audit.check_harness_inventory({'tests/behaviour/driver.py':'sha'})
  self.assertIn('docs/ui-reimplementation/spec.json',audit.REQUIRED_HARNESS)
class DoctorCompleteWindowIntegrity(unittest.TestCase):
 def test_ready_fixture_cannot_skip_held_browse_boundary(self):
  fixture=dict(project_seed_origin=audit.ORIGIN,retained_audio=False,bank_bpm=120,window_max=63,beat_count=40,masks_by_sensitivity={'0':[1,17],'0.5':[1],'1':[]},midi_expected=[[1,[144,60,100]]])
  with self.assertRaisesRegex(ValueError,'geometry'):audit.check_fixture_contract(fixture)
 def test_public_play_stop_pair_requires_forward_ordered_release(self):
  press=dict(kind='input',sequence=1,type=3,args=[0,7,1],monotonic_ns=100)
  release=dict(kind='input',sequence=2,type=3,args=[0,7,0],monotonic_ns=101)
  with self.assertRaisesRegex(ValueError,'release ordering'):audit.public_play_stop_gestures([press,dict(release,sequence=1)])
  with self.assertRaisesRegex(ValueError,'release ordering'):audit.public_play_stop_gestures([press,dict(release,monotonic_ns=99)])
  with self.assertRaisesRegex(ValueError,'release'):audit.public_play_stop_gestures([press])
 def test_adc_requires_actual_twelve_second_public_transport_window(self):
  on=dict(kind=3,index=1,port=1,bytes=[144,60,100],monotonic_ns=1000000000)
  off=dict(kind=3,index=2,port=1,bytes=[128,60,100],monotonic_ns=1166666667)
  play_down=dict(kind='input',type=3,args=[0,7,1],monotonic_ns=900000000,sequence=1)
  play_up=dict(kind='input',type=3,args=[0,7,0],monotonic_ns=1000000000,sequence=2)
  on=dict(kind=3,index=1,port=1,bytes=[144,60,100],monotonic_ns=12900000000)
  stop_down=dict(kind='input',type=3,args=[0,7,1],monotonic_ns=12995000000,sequence=3)
  stop_up=dict(kind='input',type=3,args=[0,7,0],monotonic_ns=13019000000,sequence=4)
  off=dict(kind=3,index=2,port=1,bytes=[128,60,100],monotonic_ns=13020000000)
  events=[play_down,play_up,on,stop_down,stop_up,off]
  audit.check_adc_playback_horizon(events,[on,off])
  audit.bind_public_stop(events,[on,off],'real-time')
  short_down=dict(stop_down,monotonic_ns=12980000000)
  short=dict(stop_up,monotonic_ns=12989000000)
  with self.assertRaisesRegex(ValueError,'12-second'):audit.check_adc_playback_horizon([play_down,play_up,on,short_down,short,off],[on,off])
  with self.assertRaisesRegex(ValueError,'release'):audit.check_adc_playback_horizon([play_down,play_up,on,stop_down,off],[on,off])
  duplicate=[play_down,dict(play_down,sequence=8),play_up,on,stop_down,stop_up,off]
  with self.assertRaisesRegex(ValueError,'Overlapping'):audit.check_adc_playback_horizon(duplicate,[on,off])
  with self.assertRaisesRegex(ValueError,'public playback'):audit.check_adc_playback_horizon([on,off,stop_down,stop_up],[on,off])
class DoctorFrameApiIntegrity(unittest.TestCase):
 def test_all_native_frame_checks_supply_the_actual_case_namespace(self):
  import ast,inspect
  arity=len(inspect.signature(audit.check_frame).parameters)
  calls=[node for node in ast.walk(ast.parse(Path(audit.__file__).read_text())) if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='check_frame']
  self.assertEqual(len(calls),2)
  for call in calls:self.assertEqual(len(call.args),arity,'Native frame verification must use its actual case namespace')
class DoctorInputDocumentationIntegrity(unittest.TestCase):
 def test_selected_input_frame_is_required_for_each_actual_adc_role(self):
  for case,value,count in [('manual_stereo','STEREO',4),('manual_left','L',4),('manual_right','R',12),('auto_stereo','STEREO',4),('auto_left','L',4),('auto_right','R',4)]:
   contract=audit.adc_checkpoint_contract(case);self.assertEqual(len(contract),count);self.assertEqual(contract[1],('setup-input-source',dict(route='R01',label='Input',value=value)))
   self.assertEqual(contract[0],('setup-manual-bpm',dict(route='R01',label='Manual BPM',value='100')))
   self.assertEqual(contract[-1],('alignment-lower-row',dict(route='R06',label='Fine start',value='0ms')) if count==4 else ('start-beat-restored-ready',dict(route='R05',label=None,value=None)))
  with self.assertRaisesRegex(ValueError,'Unsupported ADC documentation role'):
   audit.adc_checkpoint_contract('setup_options')

class DoctorManualStartBeatIntegrity(unittest.TestCase):
 def chain(self):
  envelopes=[]
  for revision,bpm,origin in [(0,100,0),(1,120,0),(2,120,24000),(3,120,0)]:
   analysis=dict(tempo_mode='manual',bpm=bpm,origin_sample=origin,phrase_start_sample=origin,beat_positions=list(range(0,1200000,24000 if bpm==120 else 28800)),candidates={'BD':[12,34]},detector={'backend_id':'nmf-pfnmf-drums-v1'})
   envelopes.append(dict(status='COMPLETED',command='ANALYSE',analysis_revision=revision,job_id='job'+str(revision),wav_sha256='wav',frames=1200000,sample_rate=48000,project_id='project',generation=1,analysis=analysis))
  row=dict(kind='doctor-manual-start-beat',passed=True,original=envelopes[1],advanced=envelopes[2],restored=envelopes[3],captured_sha256='wav',origins=[0,24000,0],bpm=120,candidate_absolute_positions_unchanged=True,controlled_time=dict(applicable=False,reason='actual public PCM'))
  return envelopes,[row]
 def test_exact_current_four_analysis_chain_and_final_restored_analysis(self):
  envelopes,rows=self.chain();self.assertEqual(audit.check_manual_start_beat(envelopes,rows,'wav'),envelopes[-1]['analysis'])
  for change in ('revision','job','WAV','candidate','origin','grid','missing','forged'):
   e,r=copy.deepcopy((envelopes,rows))
   if change=='revision':e[2]['analysis_revision']=9
   elif change=='job':e[2]['job_id']=e[1]['job_id']
   elif change=='WAV':e[3]['wav_sha256']='different'
   elif change=='candidate':e[2]['analysis']['candidates']['BD']=[99]
   elif change=='origin':e[2]['analysis']['origin_sample']=0
   elif change=='grid':e[2]['analysis']['beat_positions']=[24000]
   elif change=='missing':e.pop()
   else:r[0]['restored']=copy.deepcopy(e[1])
   with self.subTest(change=change),self.assertRaises(ValueError):audit.check_manual_start_beat(e,r,'wav')
 def test_start_beat_requires_five_exact_native_documentation_rows(self):
  expected=[('start-beat-original1',dict(route='R06',label='Start beat',value='1')),('start-beat-next2',dict(route='R06',label='Start beat',value='2')),('start-beat-next-ready',dict(route='R05',label=None,value=None)),('start-beat-restore1',dict(route='R06',label='Start beat',value='1')),('start-beat-restored-ready',dict(route='R05',label=None,value=None))]
  self.assertEqual(audit.adc_checkpoint_contract('manual_right')[-5:],expected)
 def test_checkpoint_pixels_must_match_its_own_native_frame_not_another_observation(self):
  frame=dict(expect=dict(route='R06',label='Start beat',value='2'),output=dict(binding=dict(sha256='selected'),grid=[0]*128))
  observations=[dict(state=dict(frame=dict(sha256='other'),grid=[0]*128,correct=True)),dict(state=dict(frame=dict(sha256='selected'),grid=[0]*128,correct=False))]
  def oracle(state,expected,out):
   self.assertEqual(expected['field']['label'],'Start beat');self.assertEqual(expected['field']['value'],'2')
   if not state['correct']:raise ValueError('wrong bound screen')
  with patch.object(audit,'verify_cached_ui',side_effect=oracle):
   with self.assertRaisesRegex(ValueError,'bound native'):audit.check_checkpoint_pixels(frame,observations,Path('/unused'))
   observations[-1]['state']['correct']=True;audit.check_checkpoint_pixels(frame,observations,Path('/unused'))
 def test_actual_adc_and_fixture_both_invoke_independent_current_chain(self):
  import ast
  module=ast.parse(Path(audit.__file__).read_text())
  for name in ('audit_adc','audit_fixture'):
   function=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name==name)
   self.assertTrue(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='check_manual_start_beat' for n in ast.walk(function)),name+' must bind final restored chain')


class DoctorSpecializedRegistrationIntegrity(unittest.TestCase):
 def fixture(self,root):
  name='tools/doctor-qualification-inventory.json';manifest=json.loads((audit.ROOT/name).read_text());current=root/name;current.parent.mkdir(parents=True);current.write_text(json.dumps(manifest));out=root/'run';out.mkdir();(out/'qualification-registration.json').write_bytes(current.read_bytes());frozen=out/'harness'/name;frozen.parent.mkdir(parents=True);frozen.write_bytes(current.read_bytes());sha=audit.digest(current)
  registration=dict(file='qualification-registration.json',source_path=name,sha256=sha);report=dict(case='manual_right',clock_mode='real-time',qualification_manifest=registration,specialized_qualifications=[dict(id='MA-DOCTOR-MANUAL-START-BEAT-001',citation='manual:rhythm-doctor')]);source=dict(qualification_manifest=registration,harness_snapshot=str(out/'harness'),harness_files={name:sha})
  for dependency in ('tools/doctor_options_capture.py','tests/behaviour/contract/rhythm_doctor_start_beat.py','tests/behaviour/contract/rhythm_doctor_options.py'):
   path=root/dependency;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('frozen source');copy_path=out/'harness'/dependency;copy_path.parent.mkdir(parents=True,exist_ok=True);copy_path.write_bytes(path.read_bytes());source['harness_files'][dependency]=audit.digest(path)
  rows=[dict(kind='doctor-manual-start-beat',case_id='MA-DOCTOR-MANUAL-START-BEAT-001',citation='manual:rhythm-doctor')]+[dict(kind='doctor-start-beat-checkpoint',id=key,case_id='MA-DOCTOR-MANUAL-START-BEAT-001',citation='manual:rhythm-doctor') for key in manifest['qualifications'][0]['checkpoint_ids']]
  return out,report,source,rows
 def test_current_manifest_hash_frozen_source_membership_and_exact_procedure_are_mandatory(self):
  for variant in ('good','missing_manifest','wrong_hash','missing_harness','frozen_changed','procedure','checkpoint','controlled','backend','global'):
   with self.subTest(variant=variant),tempfile.TemporaryDirectory() as directory:
    root=Path(directory);out,report,source,rows=self.fixture(root)
    if variant=='missing_manifest':report.pop('qualification_manifest')
    elif variant=='wrong_hash':report['qualification_manifest']['sha256']='wrong'
    elif variant=='missing_harness':source['harness_files']={}
    elif variant=='frozen_changed':(out/'harness/tools/doctor-qualification-inventory.json').write_text('{}')
    elif variant in ('procedure','checkpoint','controlled','backend','global'):
     path=root/'tools/doctor-qualification-inventory.json';m=json.loads(path.read_text());entry=m['qualifications'][0]
     if variant=='procedure':entry['procedure']['callable']='invented'
     elif variant=='checkpoint':entry['checkpoint_ids'].pop()
     elif variant=='controlled':entry['controlled_time']['applicable']=True
     elif variant=='backend':entry['ui_only_witness']['backend_regression']=True
     else:entry['global_inventory_member']=True
     path.write_text(json.dumps(m));(out/'qualification-registration.json').write_bytes(path.read_bytes());(out/'harness/tools/doctor-qualification-inventory.json').write_bytes(path.read_bytes());report['qualification_manifest']['sha256']=audit.digest(path);source['harness_files']['tools/doctor-qualification-inventory.json']=audit.digest(path)
    with patch.object(audit,'ROOT',root):
     if variant=='good':audit.check_qualification_registration(out,report,source,rows)
     else:
      with self.assertRaises(ValueError):audit.check_qualification_registration(out,report,source,rows)
 def test_setup_options_requires_staged_identity_and_ui_only_result(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);out,report,source,_=self.fixture(root)
   report.update(case='setup_options',clock_mode='controlled-experimental',
    specialized_qualifications=[dict(id='MA-DOCTOR-SETUP-OPTIONS-001',citation='manual:rhythm-doctor')])
   good=dict(kind='doctor-options',check='setup-complete',case_id='MA-DOCTOR-SETUP-OPTIONS-001',
    citation='manual:rhythm-doctor',backend_bpm_input_claim=False)
   field=dict(kind='doctor-options',check='field',case_id='MA-DOCTOR-SETUP-OPTIONS-001',
    citation='manual:rhythm-doctor',route='R01',label='Tempo',value='AUTO')
   with patch.object(audit,'ROOT',root):
    audit.check_qualification_registration(out,report,source,[good,field])
    for key,value in [('citation','other'),('case_id','invented')]:
     bad=copy.deepcopy(field);bad[key]=value
     with self.subTest(key=key),self.assertRaises(ValueError):
      audit.check_qualification_registration(out,report,source,[good,bad])
    for key,value in [('citation','other'),('case_id','invented'),('backend_bpm_input_claim',True)]:
     bad=copy.deepcopy(good);bad[key]=value
     with self.subTest(key=key),self.assertRaises(ValueError):
      audit.check_qualification_registration(out,report,source,[bad,field])
    with self.assertRaises(ValueError):
     audit.check_qualification_registration(out,report,source,[])
    changed=copy.deepcopy(report);changed['specialized_qualifications']=[]
    with self.assertRaises(ValueError):
     audit.check_qualification_registration(out,changed,source,[good])

 def test_report_role_and_all_existing_subprocedure_rows_need_stable_registered_identity(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);out,report,source,rows=self.fixture(root)
   with patch.object(audit,'ROOT',root):
    for variant in ('missing','citation','case_id','checkpoint','duplicate','other_role'):
     r,s,values=copy.deepcopy((report,source,rows))
     if variant=='missing':r['specialized_qualifications']=[]
     elif variant=='citation':values[1]['citation']='characterisation'
     elif variant=='case_id':values[0]['case_id']='fake'
     elif variant=='checkpoint':values.pop()
     elif variant=='duplicate':values.append(values[-1])
     else:r['case']='auto_left'
     with self.subTest(variant=variant),self.assertRaises(ValueError):audit.check_qualification_registration(out,r,s,values)
    report['case']='auto_left';report['specialized_qualifications']=[];audit.check_qualification_registration(out,report,source,[])


class DoctorPlayingRecordRefusalIntegrity(unittest.TestCase):
 def fixture(self):
  import base64,hashlib
  pixels=bytes(32768);sha=hashlib.sha256(pixels).hexdigest();grid=[0]*128;grid[48]=15;observations=[];witnesses={};names=['pre_play','held_record','released_record','post_stop_mask','stopped_bpm','end'];prefixes=[0,3,4,6,6,7]
  for i,name in enumerate(names):
   state=dict(frame=dict(sha256=sha,pixels_base64=base64.b64encode(pixels).decode()),grid=grid[:],midi_capture=dict(outstanding=[]),held=[]);o=dict(monotonic_ns=(i+1)*1000000000,state=state);observations.append(o);witnesses[name]=dict(observation_index=i,recipe_index=prefixes[i],state_sha256=audit.canonical_hash(state),frame_sha256=sha)
  actions=[dict(type='grid',x=1,y=8,state=1),dict(type='grid',x=1,y=8,state=0),dict(type='grid',x=1,y=2,state=1),dict(type='grid',x=1,y=2,state=0),dict(type='grid',x=1,y=8,state=1),dict(type='grid',x=1,y=8,state=0),dict(type='key',n=2,state=1)]
  times=[1100000000,1200000000,1500000000,2500000000,3500000000,3600000000];events=[dict(kind=1,sha256=sha),dict(kind=2,leds=grid[:])]+[dict(kind='input',type=3,args=[a['x']-1,a['y']-1,a['state']],monotonic_ns=t) for a,t in zip(actions,times)]+[dict(kind=3,index=1,port=1,bytes=[144,60,100],monotonic_ns=1300000000)]
  row=dict(kind='doctor-options',check='playing-record-refused',route='R05',released=True,bank_bpm=120,steps=[1],witnesses=witnesses);fixture=dict(bank_bpm=120,masks_by_sensitivity={'0.5':[1]});return row,observations,actions,events,fixture
 def test_missing_refusal_wrong_public_edges_or_borrowed_frame_and_bank_rejected(self):
  row,obs,recipe,events,fixture=self.fixture()
  with patch.object(audit,'verify_cached_ui') as verify:
   audit.check_playing_record_refusal([row],obs,recipe,events,fixture,'real-time',Path('/unused'));self.assertEqual(verify.call_count,3)
   for change in ('missing','held','released','state','mask','bpm','transport','order','pixels'):
    r,o,p,e,f=copy.deepcopy((row,obs,recipe,events,fixture));rows=[r]
    if change=='missing':rows=[]
    elif change=='held':e[4]['args']=[0,1,0]
    elif change=='released':e[5]['monotonic_ns']=3500000000
    elif change=='state':r['witnesses']['held_record']['state_sha256']='fake'
    elif change=='mask':o[3]['state']['grid'][49]=15;r['witnesses']['post_stop_mask']['state_sha256']=audit.canonical_hash(o[3]['state'])
    elif change=='bpm':r['bank_bpm']=100
    elif change=='transport':e=[v for v in e if v.get('kind')!=3]
    elif change=='order':r['witnesses']['released_record']['observation_index']=1
    with self.subTest(change=change):
     if change=='pixels':
      with patch.object(audit,'verify_cached_ui',side_effect=ValueError('bound selected pixels')),self.assertRaises(ValueError):audit.check_playing_record_refusal(rows,o,p,e,f,'real-time',Path('/unused'))
     else:
      with self.assertRaises(ValueError):audit.check_playing_record_refusal(rows,o,p,e,f,'real-time',Path('/unused'))

if __name__=='__main__':unittest.main()

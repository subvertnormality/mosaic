"""Transactional feature promotion requires independent publication and both lanes."""
import copy,json,pathlib,sys,tempfile,unittest
from unittest.mock import Mock,patch
import yaml
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'tools'))
import manual_feature_bind as binder

class FeatureBindingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=pathlib.Path(self.tmp.name);self.build=self.root/'build';self.build.mkdir()
  (self.root/'manual/features').mkdir(parents=True);(self.root/'manual/generated').mkdir()
  self.feature=self.root/'manual/features/content.yaml'
  self.feature.write_text(yaml.safe_dump(dict(features=[dict(id='f',prose='Keep exact wording',sources={'code':['lib/a.lua']},source_review={'sha256':'frozen'},scene_refs=['historic'],review=dict(status='pending',native_gap='Original gap',native_evidence=[{'scene':'historic'}]))])))
  self.original=self.feature.read_bytes();self.mapping={'f':['s']}
  self.raw=Mock(return_value=dict(passed=True,complete_regression_run=False))
  self.controlled_raw=Mock(return_value=dict(passed=True,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',complete_regression_run=False))
  self.lane=Mock(return_value=1)
  self.identity=Mock(return_value={'application_digest':'candidate'})
  self.functions=(self.raw,self.lane,self.identity)
  self.scene=dict(id='s',feature_id='f',behaviour_case='CASE',evidence={'path':'native'},steps=[dict(id='checkpoint',expect={'assertion':{'kind':'test','passed':True}},output={'binding':dict(passed=True,semantic_assertions=1,sha256='frame',grid_sha256='grid',assertion={'kind':'test','passed':True})})])
  self.source={key:{'file':'hash'} for key in ('plans_sha256','plan_files','adapter_sha256','case_sources','capture_sources','fixture_sources')}
  self.docs={}
  for mode,label in [('real-time','real'),('controlled-experimental','controlled')]:
   doc=dict(passed=True,clock_mode=mode,complete_regression_run=False,source=self.source,scenes=[self.scene])
   native=self.root/label/'reference-scenes.json';native.parent.mkdir();native.write_text(json.dumps(doc))
   name='reference-'+label+'-plan'
   log=self.build/(name+'.log');log.write_text(str(native.parent)+'\n')
   record=dict(name=name,passed=True,returncode=0,log_sha256=binder.sha(log),executed_command=['capture','--clock-mode',mode],native_report=dict(path=str(native),sha256=binder.sha(native)))
   (self.build/(name+'.json')).write_text(json.dumps(record));self.docs[mode]=(native,doc)
  (self.root/'manual/generated/reference-scenes.json').write_text(json.dumps(self.docs['real-time'][1]))
 def run_bind(self):
  return binder.bind(self.build,self.root/'binding',root=self.root,mappings=self.mapping,audit_functions=self.functions)
 def assert_unchanged(self):
  self.assertEqual(self.feature.read_bytes(),self.original)
 def change_controlled(self,change):
  path,doc=self.docs['controlled-experimental'];change(doc);path.write_text(json.dumps(doc))
  record_path=self.build/'reference-controlled-plan.json';r=json.loads(record_path.read_text());r['native_report']['sha256']=binder.sha(path);record_path.write_text(json.dumps(r))
 def test_success_preserves_prose_frozen_review_and_prior_native_history(self):
  result=self.run_bind();f=yaml.safe_load(self.feature.read_text())['features'][0]
  self.assertTrue(result['passed']);self.assertFalse(result['complete_regression_run'])
  self.assertEqual(f['prose'],'Keep exact wording');self.assertEqual(f['source_review'],{'sha256':'frozen'})
  self.assertEqual(f['scene_refs'],['historic','s'])
  self.assertEqual(f['review']['historical_native_evidence'][0]['review']['native_gap'],'Original gap')
  self.assertEqual(len(f['review']['controlled_baselines']),1)
  self.assertEqual((self.root/'binding/before/manual/features/content.yaml').read_bytes(),self.original)
  self.raw.assert_called_once();self.assertEqual(self.lane.call_count,2)
 def test_failed_raw_audit_cannot_promote(self):
  self.raw.side_effect=ValueError('raw failed')
  with self.assertRaisesRegex(ValueError,'raw failed'):self.run_bind()
  self.assert_unchanged();self.assertFalse(json.loads((self.root/'binding/manifest.json').read_text())['passed'])
 def test_missing_required_scene_cannot_partially_promote(self):
  self.mapping={'f':['s','missing']}
  with self.assertRaisesRegex(ValueError,'Missing audited scene'):self.run_bind()
  self.assert_unchanged()
 def test_unknown_feature_cannot_promote(self):
  self.mapping={'unknown':['s']}
  with self.assertRaisesRegex(ValueError,'Unknown feature'):self.run_bind()
  self.assert_unchanged()
 def test_missing_controlled_lane_cannot_promote(self):
  (self.build/'reference-controlled-plan.json').unlink()
  with self.assertRaisesRegex(ValueError,'two-lane'):self.run_bind()
  self.assert_unchanged()
 def test_failed_controlled_semantics_cannot_promote(self):
  self.lane.side_effect=ValueError('controlled failed')
  with self.assertRaisesRegex(ValueError,'controlled failed'):self.run_bind()
  self.assert_unchanged()
 def test_changed_stage_log_cannot_promote(self):
  (self.build/'reference-controlled-plan.log').write_text('tampered')
  with self.assertRaisesRegex(ValueError,'stage log'):self.run_bind()
  self.assert_unchanged()
 def test_two_lane_source_mismatch_cannot_promote(self):
  self.change_controlled(lambda doc:doc.update(source=dict(doc['source'],case_sources={'different':'hash'})))
  with self.assertRaisesRegex(ValueError,'source mismatch'):self.run_bind()
  self.assert_unchanged()
 def test_evidence_directory_is_immutable(self):
  (self.root/'binding').mkdir()
  with self.assertRaisesRegex(ValueError,'must be new'):self.run_bind()
  self.assert_unchanged()
 def test_audited_reference_success_without_top_level_passed_is_supported(self):
  for mode,(path,doc) in self.docs.items():
   doc.pop('passed');path.write_text(json.dumps(doc))
   label='real' if mode=='real-time' else 'controlled'
   rp=self.build/('reference-'+label+'-plan.json');r=json.loads(rp.read_text());r['native_report']['sha256']=binder.sha(path);rp.write_text(json.dumps(r))
  (self.root/'manual/generated/reference-scenes.json').write_text(json.dumps(self.docs['real-time'][1]))
  self.assertTrue(self.run_bind()['passed'])
 def test_failed_native_report_is_rejected_even_with_success_stage_receipt(self):
  self.change_controlled(lambda doc:doc.update(passed=False))
  with self.assertRaisesRegex(ValueError,'report failed'):self.run_bind()
  self.assert_unchanged()
 def test_two_lane_application_identity_mismatch_cannot_promote(self):
  self.identity.side_effect=[{'application_digest':'real'},{'application_digest':'other'}]
  with self.assertRaisesRegex(ValueError,'application identity mismatch'):self.run_bind()
  self.assert_unchanged()
 def test_multi_file_write_failure_rolls_back_every_source(self):
  other=self.root/'manual/features/second.yaml'
  other.write_text(yaml.safe_dump(dict(features=[dict(id='g',prose='second',review={'status':'pending'},scene_refs=[])])))
  original=other.read_bytes();self.mapping={'f':['s'],'g':['s']}
  replace=binder.os.replace
  def fail_second(source,target):
   if pathlib.Path(target)==other:raise OSError('injected replacement failure')
   return replace(source,target)
  with patch.object(binder.os,'replace',side_effect=fail_second):
   with self.assertRaisesRegex(OSError,'injected replacement'):self.run_bind()
  self.assert_unchanged();self.assertEqual(other.read_bytes(),original)
 def test_doctor_requires_two_explicit_fresh_real_reports(self):
  document={'controlled_time':{'applicable':False,'reason':'Native audio requires wall time'},'evidence':{'runs':[{'report':'manual','report_sha256':'a'},{'report':'auto','report_sha256':'b'}]}}
  rows=[{'stage':'doctor-manual-real','report':'manual','report_sha256':'a','clock_mode':'real-time'}]
  with self.assertRaisesRegex(ValueError,'both fresh build'):binder.doctor_proof(document,rows)
  rows.append({'stage':'doctor-auto-real','report':'auto','report_sha256':'b','clock_mode':'real-time'})
  proof,exception=binder.doctor_proof(document,rows)
  self.assertEqual(len(proof),2);self.assertFalse(exception['applicable'])
 def test_doctor_cannot_invent_controlled_inapplicability(self):
  with self.assertRaisesRegex(ValueError,'inapplicability'):binder.doctor_proof({},[])
 def test_changed_reviewed_semantic_case_cannot_promote(self):
  with patch.dict(binder.EXPECTED_CASES,{'s':'EXPECTED-CASE'}):
   with self.assertRaisesRegex(ValueError,'semantic case changed'):self.run_bind()
  self.assert_unchanged()
 def test_manifest_write_failure_rolls_back_feature_promotion(self):
  replace=binder.os.replace
  def fail_manifest(source,target):
   if pathlib.Path(target).name=='manifest.json':raise OSError('injected manifest failure')
   return replace(source,target)
  with patch.object(binder.os,'replace',side_effect=fail_manifest):
   with self.assertRaisesRegex(OSError,'manifest failure'):self.run_bind()
  self.assert_unchanged()
  self.assertFalse(json.loads((self.root/'binding/manifest.json').read_text())['passed'])
 def test_missing_frame_binding_cannot_promote(self):
  published=self.root/'manual/generated/reference-scenes.json'
  d=json.loads(published.read_text());d['scenes'][0]['steps'][0]['output']['binding'].pop('grid_sha256');published.write_text(json.dumps(d))
  with self.assertRaisesRegex(ValueError,'frame/grid'):self.run_bind()
  self.assert_unchanged()
 def test_report_path_must_equal_exact_final_stage_output(self):
  log=self.build/'reference-controlled-plan.log'
  log.write_text(log.read_text()+'another-final-path\n')
  rp=self.build/'reference-controlled-plan.json';record=json.loads(rp.read_text());record['log_sha256']=binder.sha(log);rp.write_text(json.dumps(record))
  with self.assertRaisesRegex(ValueError,'final stage output'):self.run_bind()
  self.assert_unchanged()
 def test_exact_expanded_reviewed_feature_scope(self):
  self.assertEqual(len(binder.MAPPINGS),40)
  self.assertEqual(binder.MAPPINGS['lfos-and-modulation'],['matrix-macro-route-clear','toolkit-clocked-lfo-menu','matrix-macro-modest-cc'])
  self.assertEqual(binder.MAPPINGS['reset-at-pattern-repeat'],['repeat-reset-policies','repeat-reset-first-boundary-public'])
  self.assertEqual(binder.MAPPINGS['snap-note-masks-to-scale'],['snap-note-masks-public-pair'])
  self.assertEqual(binder.MAPPINGS['ui-motion'],['screen-motion-on-and-off','public-display-readability','ui-motion-public-frames'])
  self.assertEqual(binder.MAPPINGS['rhythm-doctor'],['doctor-local-capture-and-paint','doctor-local-auto-capture-and-paint'])
  self.assertEqual(binder.MAPPINGS['screen-options'],binder.MAPPINGS['ui-motion'][:2])
 def test_shared_strategy_requires_all_thirteen_new_checkpoints(self):
  scene=copy.deepcopy(self.scene);scene['id']='shared-merge-strategy-workflow';scene['behaviour_case']='M-MERGE-STRATEGY-001'
  with self.assertRaisesRegex(ValueError,'checkpoint'):binder.verify_reviewed_scene(scene)
 def test_all_five_updated_features_require_shared_selector_acceptance(self):
  for fid in ('merge-modes','trig-merge-modes','musical-merge-and-voice-leading','merge-shape','fragments'):
   self.assertIn('shared-merge-strategy-workflow',binder.MAPPINGS.get(fid,[]))
 def reviewed_strategy_scene(self):
  root=pathlib.Path(__file__).resolve().parents[2]
  plan=yaml.safe_load((root/'manual/scene-plans-merge-strategy.yaml').read_text())['scenes'][0]
  return dict(plan,steps=[dict(id=step['id'],output={'binding':{'assertion':step['assertion']}}) for step in plan['steps']])
 def test_complete_reviewed_strategy_plan_has_exact_acceptance_selectors(self):
  binder.verify_reviewed_scene(self.reviewed_strategy_scene())
 def test_shared_strategy_wrong_semantic_or_fragment_seed_rejected(self):
  scene=self.reviewed_strategy_scene();step=next(s for s in scene['steps'] if s['id']=='fragments-phrase')
  step['output']['binding']['assertion']['seed']=1
  with self.assertRaisesRegex(ValueError,'literal fixture'):binder.verify_reviewed_scene(scene)
  scene=self.reviewed_strategy_scene();next(s for s in scene['steps'] if s['id'] in binder.STRATEGY_CHECKPOINTS)['output']['binding']['assertion']['checkpoint']='other'
  with self.assertRaisesRegex(ValueError,'selector'):binder.verify_reviewed_scene(scene)
 def test_shared_strategy_cannot_borrow_an_old_case(self):
  scene=self.reviewed_strategy_scene();scene['behaviour_case']='M-LIVEUI-MERGEMODES-001'
  with self.assertRaisesRegex(ValueError,'semantic case'):binder.verify_reviewed_scene(scene)
 def test_shared_strategy_only_requires_literal_two_loop_silence(self):
  scene=self.reviewed_strategy_scene();step=next(s for s in scene['steps'] if s['id']=='only-silence')
  step['output']['binding']['assertion']['actual']=[[1,1,60,80]]
  with self.assertRaisesRegex(ValueError,'Only silence'):binder.verify_reviewed_scene(scene)
 def test_readability_features_require_the_current_public_case(self):
  for fid in ('navigating-the-norns-display','screen-options','ui-motion'):
   self.assertIn('public-display-readability',binder.MAPPINGS[fid])
  self.assertEqual(binder.EXPECTED_CASES['public-display-readability'],'M-UI-READABILITY-001')
 def test_readability_requires_all_seventeen_native_checkpoints(self):
  scene=copy.deepcopy(self.scene);scene.update(id='public-display-readability',behaviour_case='M-UI-READABILITY-001')
  with self.assertRaisesRegex(ValueError,'seventeen'):binder.verify_reviewed_scene(scene)
 def reviewed_readability_scene(self):
  root=pathlib.Path(__file__).resolve().parents[2]
  plan=yaml.safe_load((root/'manual/scene-plans-readability.yaml').read_text())['scenes'][0]
  return dict(plan,steps=[dict(id=step['id'],output={'binding':{'assertion':step['assertion']}}) for step in plan['steps']])
 def test_reviewed_readability_plan_has_exact_seventeen_literals(self):
  binder.verify_reviewed_scene(self.reviewed_readability_scene())
 def test_readability_cannot_change_atlas_or_fast_clock_policy(self):
  scene=self.reviewed_readability_scene();step=next(s for s in scene['steps'] if s['id']=='mini-c04-on-240')
  step['output']['binding']['assertion']['all_distinct_poses_required']=True
  with self.assertRaisesRegex(ValueError,'literal selector'):binder.verify_reviewed_scene(scene)
  scene=self.reviewed_readability_scene();step=next(s for s in scene['steps'] if s['id']=='mini-s01-on-90')
  step['output']['binding']['assertion']['atlas_sha256']='inferred-atlas'
  with self.assertRaisesRegex(ValueError,'literal selector'):binder.verify_reviewed_scene(scene)
 def test_readability_cannot_omit_slow_clock_complete_pose_proof(self):
  scene=self.reviewed_readability_scene();step=next(s for s in scene['steps'] if s['id']=='mini-c04-on-40')
  step['output']['binding']['assertion']['all_distinct_poses_required']=False
  with self.assertRaisesRegex(ValueError,'literal selector'):binder.verify_reviewed_scene(scene)
 def nb_parent(self):
  data=yaml.safe_load(self.feature.read_text());data['features'].append(dict(id='norns-sound-sources-with-n-b',scene_refs=[],review=dict(status='verified',applicability='native-ui')))
  self.feature.write_text(yaml.safe_dump(data));return data
 def test_nb_parent_native_ui_cannot_be_verified_without_picker_replay(self):
  self.nb_parent()
  with self.assertRaisesRegex(ValueError,'player route'):binder.verify_nb_route_bindings(self.root,audit_projection=Mock())
 def test_nb_parent_reuses_exact_canonical_projection_without_copying_scene(self):
  data=self.nb_parent();parent=data['features'][-1]
  parent['scene_refs']=['software-player-oilcan','software-player-polyperc','software-player-doubledecker'];parent['review']['native_evidence_catalogues']=['generated/player-routes.json']
  self.feature.write_text(yaml.safe_dump(data))
  scenes=[]
  for voice,identifier,channel in [('Oilcan 1','software-player-oilcan',1),('Polyperc 1','software-player-polyperc',2),('Doubledecker','software-player-doubledecker',3)]:
   scenes.append(dict(id=identifier,feature_id='mods-and-software-devices',behaviour_case='MA-AUDIO-three-voice-conversation',steps=[dict(id='select',output={'binding':dict(passed=True,capture_stage='before-apply',assertion={'kind':'device-picker-frame','label':voice,'matched':True},frame_oracle={'page':'midi_config','channel':channel,'selected_label':'Device','selected_value':voice,'matched':True},following_apply=[{'apply':'K3'}])})]))
  projection=dict(publication_kind='audio-route-projection',passed=True,complete_regression_run=False,parent_publication={'acceptance_case':'MA-AUDIO-three-voice-conversation'},scenes=scenes)
  path=self.root/'manual/generated/player-routes.json';path.write_text(json.dumps(projection));audit=Mock(return_value={'passed':True,'scenes':3,'frames':3})
  result=binder.verify_nb_route_bindings(self.root,audit_projection=audit)
  self.assertTrue(result['passed']);self.assertEqual(result['scene_ids'],parent['scene_refs']);audit.assert_called_once_with(path)
  projection['scenes'][0]['behaviour_case']='different-case';path.write_text(json.dumps(projection))
  with self.assertRaisesRegex(ValueError,'provenance'):binder.verify_nb_route_bindings(self.root,audit_projection=audit)

 def test_controlled_local_binds_fresh_controlled_scene_without_claiming_realtime(self):
  manifest=dict(validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',complete_regression_run=False,clock_mode='controlled-experimental')
  (self.build/'manifest.json').write_text(json.dumps(manifest))
  self.change_controlled(lambda doc:doc.update(validation_scope='controlled-manual-generation',realtime_qualification='pending-ci'))
  path,doc=self.docs['controlled-experimental']
  (self.root/'manual/generated/reference-scenes.json').write_text(json.dumps(doc))
  scoped=dict(passed=True,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',complete_regression_run=False,controlled_stages=[])
  with patch.object(binder,'controlled_manual_audit',return_value=scoped) as audit:
   result=binder.bind(self.build,self.root/'controlled-binding',root=self.root,mappings=self.mapping,controlled_local=True,audit_functions=self.functions)
  feature=yaml.safe_load(self.feature.read_text())['features'][0]
  self.assertTrue(result['passed']);self.assertFalse(result['complete_regression_run'])
  self.assertEqual(result['validation_scope'],'controlled-manual-generation')
  self.assertEqual(result['realtime_qualification'],'pending-ci')
  self.assertFalse(result['complete_regression_run'])
  self.assertEqual(feature['review']['status'],'controlled-verified')
  self.assertEqual(feature['review']['validation_scope'],'controlled-manual-generation')
  self.assertEqual(feature['review']['realtime_qualification'],'pending-ci')
  audit.assert_called_once_with(self.build)
  self.raw.assert_not_called();self.assertEqual(self.lane.call_count,1)

 def test_controlled_local_rejects_failed_scoped_audit_without_mutation(self):
  self.change_controlled(lambda doc:doc.update(validation_scope='controlled-manual-generation',realtime_qualification='pending-ci'))
  path,doc=self.docs['controlled-experimental']
  (self.root/'manual/generated/reference-scenes.json').write_text(json.dumps(doc))
  with patch.object(binder,'controlled_manual_audit',return_value=dict(passed=False,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',complete_regression_run=False)):
   with self.assertRaisesRegex(ValueError,'audit failed'):
    binder.bind(self.build,self.root/'bad-controlled-binding',root=self.root,mappings=self.mapping,controlled_local=True,audit_functions=self.functions)
  self.assert_unchanged()

 # Plan and placement coherence: README.md#song-mode / #midi-panic scenes are bound to the cases that record them.
 @staticmethod
 def plan_scenes():
  root=pathlib.Path(__file__).resolve().parents[2];scenes={}
  for path in sorted((root/'manual').glob('scene-plans*.yaml')):
   document=yaml.safe_load(path.read_text())
   for scene in (document if isinstance(document,list) else document.get('scenes',[])):scenes[scene['id']]=scene
  return scenes
 def test_new_closure_scenes_are_bound_to_the_cases_that_record_them(self):
  plans=self.plan_scenes()
  for feature,scene,case in (('midi-panic','panic-stops-sounding-note','M-MANUAL-CLOSURE-PANIC-001'),('navigating-the-norns-display','song-repeats-advance','M-MANUAL-CLOSURE-SONG-002')):
   self.assertIn(scene,binder.MAPPINGS[feature])
   self.assertEqual(binder.EXPECTED_CASES.get(scene),case)
   self.assertEqual((plans[scene]['feature_id'],plans[scene]['behaviour_case']),(feature,case))

 def test_newly_owned_scene_bindings_match_authored_owner_and_case(self):
  # Each tuple is (review feature, scene, case, canonical scene-plan owner).
  expected=(
   ('build-a-phrase','workflow-patterns-and-scale','M-WORKFLOW-001','build-a-phrase'),
   ('build-a-phrase','workflow-second-channel','M-WORKFLOW-001','build-a-phrase'),
   ('build-a-phrase','workflow-song-chain','M-WORKFLOW-001','build-a-phrase'),
   ('chord-acceleration','chord-acceleration-termination','M-CHORDSHAPE-257','chord-acceleration'),
   ('chord-acceleration','chord-acceleration-slowing','M-CHORDSHAPE-260','chord-acceleration'),
   ('fully-quantise-mask','full-quantisation-precedence','M-MASK-021','fully-quantise-mask'),
   ('fully-quantise-mask','full-quantisation-inherit-and-step-off','M-MASK-021','fully-quantise-mask'),
   ('fully-quantise-mask','full-quantisation-channel-beats-global','M-MASK-021','fully-quantise-mask'),
   ('loops-that-meet','loops-four-against-three','M-RANGE-REJECT-006','loops-that-meet'),
   ('loops-that-meet','loops-sixteen-against-five','M-RANGE-LCM-001','loops-that-meet'),
   ('merge-shape','merge-shape-owns-trigs','M-LIVEUI-SHAPETRIG-001','merge-shape'),
   ('merge-shape','merge-shape-skip-shared-step','M-LIVEUI-SHAPETRIG-002','merge-shape'),
   ('trig-merge-modes','merge-shape-skip-shared-step','M-LIVEUI-SHAPETRIG-002','merge-shape'),
   ('note-dashboard','output-dashboard-readout','M-LIVEUI-DASH-001','note-dashboard'),
   ('note-dashboard','output-channel-selection','M-DASHBOARD-SELECT-001','note-dashboard'),
   ('note-dashboard','output-latest-event','M-UIACC-A19-001','note-dashboard'),
   ('pocket-rhythm','pocket-ghost-bar','M-MANUAL-CLOSURE-GHOST-001','channel-length'),
   ('reset-at-song-editor-pattern-change','polymeter-song-reset','M-MANUAL-CLOSURE-RESET-001','reset-at-song-editor-pattern-change'),
   ('scale-editor','scale-edit-versus-apply','M-SCALE-001','scale-editor'),
   ('scale-editor','scale-save-d-and-apply','M-SCALE-001','scale-editor'),
   ('scale-locks','scale-lock-scope-and-lifetime','M-SCALE-LOCK-003','scale-locks'),
   ('scale-locks','scale-lock-skipped-trig','M-SCALE-LOCK-003','scale-locks'),
   ('scale-locks','scale-lock-replacement','M-SCALE-LOCK-003','scale-locks'),
   ('song-mode-operations','song-mode-groups-and-selection','M-SONG-FLOW-001','song-mode-operations'),
   ('song-mode-operations','song-build-two-groups','M-SONG-FLOW-001','song-mode-operations'),
   ('structure','structure-anchor-chord-and-delete','M-MERGE-STRUCTURE-001','structure'),
   ('structure','structure-every-4-markers','M-MERGE-STRUCTURE-004','structure'),
   ('transposition','transpose-next-onset','M-TRANS-009','transposition'),
   ('transposition','transpose-song-slot-copy','M-TRANS-010','transposition'),
   ('transposition-locks','transpose-explicit-zero-and-clear','M-TRANS-001','transposition-locks'),
   ('transposition-locks','transpose-lock-direct-taps','M-TRANS-011','transposition-locks'),
   ('lfos-and-modulation','matrix-macro-modest-cc','M-MANUAL-MODULATION-001','lfos-and-modulation'),
   ('reset-at-pattern-repeat','repeat-reset-first-boundary-public','M-MANUAL-RESET-REPEAT-PUBLIC-001','reset-at-pattern-repeat'),
   ('snap-note-masks-to-scale','snap-note-masks-public-pair','M-MANUAL-SNAP-MASK-PUBLIC-001','snap-note-masks-to-scale'),
   ('ui-motion','ui-motion-public-frames','M-MANUAL-UI-MOTION-FRAME-001','ui-motion'),
  )
  plans=self.plan_scenes()
  for feature,scene,case,owner in expected:
   self.assertIn(scene,binder.MAPPINGS.get(feature,[]),(feature,scene))
   self.assertEqual(binder.EXPECTED_CASES.get(scene),case,scene)
   self.assertEqual((plans[scene]['feature_id'],plans[scene]['behaviour_case']),(owner,case),scene)

 def test_modulation_source_claim_has_matching_current_scene_and_case(self):
  feature_path=pathlib.Path(__file__).resolve().parents[2]/'manual/features/reference-musical.yaml'
  document=yaml.safe_load(feature_path.read_text())
  feature=next(row for row in document['features'] if row['id']=='lfos-and-modulation')
  self.assertIn('M-MANUAL-MODULATION-001',feature['sources']['behaviour_cases'])
  self.assertIn('matrix-macro-modest-cc',feature['scene_refs'])
  plan=self.plan_scenes()['matrix-macro-modest-cc']
  self.assertEqual((plan['feature_id'],plan['behaviour_case']),('lfos-and-modulation','M-MANUAL-MODULATION-001'))

 def test_expected_cases_match_the_authored_plans(self):
  plans=self.plan_scenes()
  for scene,case in binder.EXPECTED_CASES.items():
   if scene in plans:self.assertEqual(plans[scene]['behaviour_case'],case,scene)
 def test_every_authored_scene_ref_resolves_to_a_planned_or_feature_scene(self):
  root=pathlib.Path(__file__).resolve().parents[2];known=set(self.plan_scenes());documents=[]
  for path in sorted((root/'manual/features').glob('*.yaml')):
   document=yaml.safe_load(path.read_text())
   if isinstance(document,dict):documents.append((path,document))
  for path,document in documents:known.update(scene['id'] for scene in document.get('scenes',[]) if isinstance(scene,dict))
  for path,document in documents:
   if path.name.startswith('scenes-'):continue
   for feature in document.get('features',[])+([document['feature']] if 'feature' in document else []):
    for scene in feature.get('scene_refs',[]):self.assertIn(scene,known,path.name+':'+feature['id'])

if __name__=='__main__':unittest.main()


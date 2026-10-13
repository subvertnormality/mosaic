"""Fail-closed post-build documentary source review fixtures; no native launches."""
import copy,hashlib,json,tempfile,unittest
from unittest.mock import patch
from contextlib import ExitStack
from pathlib import Path
import yaml
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'docs/ui-reimplementation/tools'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import manual_reconcile_build as tool
import test_refresh_source_inventory as existing

def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))
def value_sha(value):return tool.sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
class MetadataReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.build=Path(self.tmp.name);self.name='manual/features/reference.yaml'
  self.old={'features':[{'id':'example','prose':'Read it','controls':[{'gesture':'E3','result':'Adjust'}],'sources':{'code':['owner.lua']},'review':{'status':'pending'},'scene_refs':[]}]}
  self.new=copy.deepcopy(self.old);self.new['features'][0]['review']={'status':'verified','historical_native_evidence':[{'review':{'status':'pending'},'scene_refs':[]}]} ;self.new['features'][0]['scene_refs']=['scene']
 def tearDown(self):self.tmp.cleanup()
 def bind_receipt(self):
  self.new['features'][0]['review']['binding_receipt']=str(self.build/'feature-bind/manifest.json')
  before=yaml.safe_dump(self.old).encode();after=yaml.safe_dump(self.new).encode()
  for folder,raw in [('before',before),('after',after)]:
   p=self.build/'feature-bind'/folder/self.name;p.parent.mkdir(parents=True);p.write_bytes(raw)
  f=self.new['features'][0]
  write(self.build/'feature-bind/manifest.json',{'passed':True,'complete_regression_run':False,'files':[{'path':self.name,'before_sha256':tool.sha(before),'after_sha256':tool.sha(after)}],'mappings':[{'feature':'example','source':self.name,'scene_ids':['scene'],'claims_sha256':value_sha({k:v for k,v in f.items() if k not in ('review','scene_refs')}),'prior_review_sha256':value_sha(self.old['features'][0]['review']),'current_review_sha256':value_sha(f['review'])}]})
  return before,after
 def test_valid_binding_metadata(self):
  a,b=self.bind_receipt();self.assertIn('receipted',tool.check_metadata(self.name,a,b,self.build))
 def test_reject_prose_control_citation_edits_even_matching_receipt(self):
  for field in ('prose','controls','sources'):
   with self.subTest(field=field):
    with tempfile.TemporaryDirectory() as temp:
     prior=self.build;self.build=Path(temp);self.new['features'][0][field]='Forged';a,b=self.bind_receipt()
     with self.assertRaisesRegex(ValueError,'Prose, controls, citations'):tool.check_metadata(self.name,a,b,self.build)
     self.new['features'][0][field]=copy.deepcopy(self.old['features'][0][field]);self.build=prior
 def test_reject_forged_receipt(self):
  a,b=self.bind_receipt();p=self.build/'feature-bind/manifest.json';d=json.loads(p.read_text());d['mappings'][0]['current_review_sha256']='bad';write(p,d)
  with self.assertRaisesRegex(ValueError,'claims mismatch'):tool.check_metadata(self.name,a,b,self.build)
 def test_reject_erased_historical_review_even_matching_receipt(self):
  self.new['features'][0]['review']['historical_native_evidence']=[];a,b=self.bind_receipt()
  with self.assertRaisesRegex(ValueError,'Historical'):tool.check_metadata(self.name,a,b,self.build)
 def test_reject_unknown_source_change(self):
  with self.assertRaisesRegex(ValueError,'Unapproved'):tool.check_metadata('manual/player-routes.yaml',b'a: old',b'a: new',self.build)
 def test_learning_text_not_metadata(self):
  a={'project':{'capture_status':'pending'},'learning_path':[{'stages':[{'id':'one','text':'Play','binding':{'status':'pending'}}]}]};b=copy.deepcopy(a);b['project']['capture_status']='verified';b['learning_path'][0]['stages'][0]['binding']={'status':'verified'}
  self.assertEqual(tool.course_claims(a),tool.course_claims(b));b['learning_path'][0]['stages'][0]['text']='Different';self.assertNotEqual(tool.course_claims(a),tool.course_claims(b))
 def test_manifest_pin_precedes_untrusted_receipt(self):
  write(self.build/'manifest.json',{'passed':True})
  with self.assertRaisesRegex(ValueError,'pin mismatch'):tool.verify_manifest(self.build,self.build,'bad')
 def test_paths_escape_rejected(self):
  with self.assertRaisesRegex(ValueError,'Unsafe'):tool.safe(self.build,'../outside')

class RetiredSourceTests(existing.SourceReviewTests):
 def retirement(self):
  name='manual/features/scenes-old.yaml';raw=b'scenes: []\n';self.old['files'][name]=tool.sha(raw);self.blobs[name]=raw;self.baseline.write_text(json.dumps(self.old));archive=self.root/'archived.yaml';archive.write_bytes(raw)
  self.review['retired_generated_files']={name:{'sha256':tool.sha(raw),'archive':str(archive),'meaning':'Exact generated obsolete source'}}
  return name,archive
 def test_valid_archived_generated_retirement(self):
  name,archive=self.retirement();out,receipt=self.invoke();self.assertNotIn(name,out['files']);self.assertEqual(out['manual_sections'][0]['id'],'MAN.001')
 def test_retirement_changed_archive_rejected(self):
  name,archive=self.retirement();archive.write_text('changed')
  with self.assertRaisesRegex(AssertionError,'retired'):self.invoke()
 def test_retirement_cannot_remove_runtime(self):
  self.review['files'].pop('owner.lua');self.review['retired_generated_files']={'owner.lua':{'sha256':tool.sha(self.source.encode()),'archive':str(self.root/'README.md'),'meaning':'Forged'}}
  with self.assertRaisesRegex(AssertionError,'retired'):self.invoke()
 def test_retired_path_cannot_still_exist(self):
  name,archive=self.retirement();p=self.root/name;p.parent.mkdir(parents=True);p.write_bytes(archive.read_bytes())
  with self.assertRaisesRegex(AssertionError,'retired'):self.invoke()

class CompletedBuildReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.top=Path(self.tmp.name);self.root=self.top/'repo';self.build=self.top/'build';self.snapshot=self.top/'snapshot'
  self.root.mkdir();self.build.mkdir();self.snapshot.mkdir()
  self.oldbook={'scene_sources':['features/scenes-old.yaml']};self.newbook={'scene_sources':['scene-plans-new.yaml','features/scenes-new.yaml','features/scenes-player-routes.yaml']}
  self.oldscene=b'scenes: []\n';self.newscene=b'scenes: [new]\n'
  self.before={'manual/book.yaml':yaml.safe_dump(self.oldbook).encode(),'manual/features/scenes-old.yaml':self.oldscene,'owner.lua':b'original controls\n','cheat_sheet.html':b'qualified quick reference'}
  self.review={'files':{n:{'sha256':tool.sha(b),'meaning':'Reviewed'} for n,b in self.before.items()}}
  for n,b in self.before.items():
   p=self.snapshot/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
   p=self.root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
  write(self.snapshot/'snapshot.json',{'files':{n:tool.sha(b) for n,b in self.before.items()}})
  for base in [self.snapshot,self.root]:write(base/'docs/ui-reimplementation/current-source-review.json',self.review)
  (self.root/'manual/features/scenes-old.yaml').unlink();(self.root/'manual/features/scenes-new.yaml').write_bytes(self.newscene)
  (self.root/'manual/book.yaml').write_text(yaml.safe_dump(self.newbook));(self.root/'manual/scene-plans-new.yaml').write_text('scenes: []\n')
  p=self.build/'previous-publication/manual/features/scenes-old.yaml';p.parent.mkdir(parents=True);p.write_bytes(self.oldscene)
  p=self.root/'tools/manual_build.py';p.parent.mkdir();p.write_text('frozen builder')
  before={n:tool.sha(b) for n,b in self.before.items() if n.endswith('.yaml')}
  for n in before:
   p=self.build/'authoring-before'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(self.before[n])
  stages=[]
  for name in ['refresh-scene-index','raw-publication-audit','feature-bind','course-bind','compile-book','quick-reference','publication-audit']:
   row={'name':name,'passed':True}
   if name=='refresh-scene-index':row['action']={'plans':['scene-plans-new.yaml'],'outputs':['new.json','player-routes.json']}
   if name=='quick-reference':
    row.update(executed_command=['python','generate','--output',str(self.root/'cheat_sheet.html')],returncode=0,log_sha256=tool.sha(b'ok'))
    (self.build/(name+'.log')).write_bytes(b'ok')
   write(self.build/(name+'.json'),row);stages.append(row)
  self.manifest={'passed':True,'build_complete':True,'renderer_validated':True,'complete_regression_run':False,'tool_sha256':tool.sha((self.root/'tools/manual_build.py').read_bytes()),'required_plans':['scene-plans-new.yaml'],'selected_plans':['scene-plans-new.yaml'],'stages':stages,'source_files_before':before,'source_files_after':{str(p.relative_to(self.root)):tool.sha(p.read_bytes()) for p in (self.root/'manual').rglob('*.yaml')}}
  write(self.build/'manifest.json',self.manifest);self.pin=tool.sha((self.build/'manifest.json').read_bytes())
 def tearDown(self):self.tmp.cleanup()
 def invoke(self):
  with ExitStack() as stack:
   stack.enter_context(patch('manual_build.verify_doctor_completion',return_value=None))
   stack.enter_context(patch('manual_publication_verify.audit_publication',return_value={'passed':True}))
   stack.enter_context(patch('manual_course_bind.verify_publication',return_value={'passed':True}))
   stack.enter_context(patch('manual_quick_reference.render',return_value='qualified quick reference'))
   stack.enter_context(patch('manual_book.load',return_value={}))
   stack.enter_context(patch.object(tool,'canonical_stage_names',return_value=[row['name'] for row in self.manifest['stages']]))
   stack.enter_context(patch.object(tool,'reproduced_scenes',return_value={'manual/features/scenes-new.yaml':self.newscene}))
   return tool.prepare(self.root,self.build,self.pin,self.snapshot)
 def test_complete_receipted_path_delta(self):
  result=self.invoke();self.assertNotIn('manual/features/scenes-old.yaml',result['files']);self.assertIn('manual/features/scenes-new.yaml',result['files']);self.assertEqual(result['files']['owner.lua'],self.review['files']['owner.lua']);self.assertEqual({v['kind'] for v in result['post_build_review']['changes']},{'changed','added','retired'})
 def test_lua_drift_rejected_without_writes(self):
  (self.root/'owner.lua').write_text('changed controls');before=(self.root/'docs/ui-reimplementation/current-source-review.json').read_bytes()
  with self.assertRaisesRegex(ValueError,'Runtime'):self.invoke()
  self.assertEqual(before,(self.root/'docs/ui-reimplementation/current-source-review.json').read_bytes())
 def test_forged_success_stage_rejected(self):
  write(self.build/'compile-book.json',{'name':'compile-book','passed':True,'forged':True})
  with self.assertRaisesRegex(ValueError,'Forged'):self.invoke()
 def test_retirement_missing_archive_rejected(self):
  (self.build/'previous-publication/manual/features/scenes-old.yaml').write_bytes(b'wrong')
  with self.assertRaisesRegex(ValueError,'archive mismatch'):self.invoke()
 def test_generated_bytes_must_reproduce(self):
  (self.root/'manual/features/scenes-new.yaml').write_bytes(b'changed')
  self.manifest['source_files_after']['manual/features/scenes-new.yaml']=tool.sha(b'changed');write(self.build/'manifest.json',self.manifest);self.pin=tool.sha((self.build/'manifest.json').read_bytes())
  with self.assertRaisesRegex(ValueError,'does not reproduce'):self.invoke()
 def test_root_cheat_must_reproduce(self):
  (self.root/'cheat_sheet.html').write_text('invented control')
  with self.assertRaisesRegex(ValueError,'Quick reference'):self.invoke()

# The six 2026-10-06 stages are covered by the receipts listed in test_manual_build.py.
# Three later stages are source-derived from committed tree 9efbd8ad7fe3ae96e36db7386e3a3d0fa5be5ca0:
# the full-only fresh-target producer plus real and controlled Save Dialog stages.
BASELINE_FULL_STAGES=73
STAGES_ADDED_20261006=("reference-real-scene-plans-modulation-macro-midi-modulation","reference-controlled-scene-plans-modulation-macro-midi-modulation",
 "reference-real-scene-plans-native-public-gaps-base-midi","reference-controlled-scene-plans-native-public-gaps-base-midi",
 "reference-controlled-scene-plans-player-apply-manual-player-ui","reader-projection")
STAGES_ADDED_20261008=("fresh-target-midi-producer","reference-real-scene-plans-save-dialog-base-midi","reference-controlled-scene-plans-save-dialog-base-midi")
STAGES_ADDED=STAGES_ADDED_20261006+STAGES_ADDED_20261008
def assert_canonical_inventory(case,names):
 case.assertEqual(len(names),BASELINE_FULL_STAGES+len(STAGES_ADDED));case.assertEqual(len(set(names)),len(names))
 for name in STAGES_ADDED:case.assertEqual(names.count(name),1,name)

class ReviewedDesignGapTests(unittest.TestCase):
 def test_reserialized_immutable_yaml_requires_receipt(self):
  with tempfile.TemporaryDirectory() as temp:
   with self.assertRaisesRegex(ValueError,'Unapproved'):tool.check_metadata('manual/player-routes.yaml',b'value: original\n',b'value: original\n\n',Path(temp))
 def test_canonical_full_plan_contains_all_qualification_and_browser_stages(self):
  root=tool.ROOT;plans=sorted(p.name for p in (root/'manual').glob('scene-plans*.yaml'));names=tool.canonical_stage_names(root,plans)
  assert_canonical_inventory(self,names);self.assertIn('doctor-options-audit',names);self.assertEqual(sum(name.startswith("browser-") for name in names),8)
 def test_canonical_plan_supplies_explicit_readability_install_argument(self):
  import manual_build
  actual=manual_build.plan;seen=[]
  def reviewed_plan(options,plans):
   self.assertEqual(getattr(options,'readability_real_install',None),'identity')
   rows=actual(options,plans);real=next(row for row in rows if row['name']=='reference-real-scene-plans-readability-base-midi');args=real['command']
   self.assertEqual(args[args.index('--experimental-install')+1],'identity');self.assertEqual(args[args.index('--clock-mode')+1],'real-time');seen.append(True);return rows
  with patch.object(manual_build,'plan',side_effect=reviewed_plan):
   names=tool.canonical_stage_names(tool.ROOT,sorted(p.name for p in (tool.ROOT/'manual').glob('scene-plans*.yaml')))
  assert_canonical_inventory(self,names);self.assertEqual(seen,[True])
 def test_canonical_plan_routes_distinct_qualified_real_midi_and_dsp_installations(self):
  import manual_build
  actual=manual_build.plan;seen=[]
  def reviewed_plan(options,plans):
   self.assertEqual(getattr(options,'real_install',None),'identity')
   options.real_install='qualified-real-install';options.readability_real_install='readability-install';options.audio_install='doctor-dsp-install';options.controlled_install='controlled-install'
   rows=actual(options,plans)
   for row in rows:
    args=row['command'];name=row['name']
    if name in ('masks-real','first-sound-real') or name.startswith('reference-real-'):
     expected='readability-install' if name=='reference-real-scene-plans-readability-base-midi' else 'qualified-real-install'
     self.assertEqual(args[args.index('--experimental-install')+1],expected)
     if '--clock-mode' in args:self.assertEqual(args[args.index('--clock-mode')+1],'real-time')
    if name in ('masks-controlled','first-sound-controlled') or name.startswith('reference-controlled-'):
     self.assertEqual(args[args.index('--experimental-install')+1],'controlled-install');self.assertEqual(args[args.index('--clock-mode')+1],'controlled-experimental')
    if name in ('doctor-manual-real','doctor-auto-real'):
     self.assertEqual(args[args.index('--audio-install')+1],'doctor-dsp-install')
    if row.get('doctor_options') and row['doctor_options']['clock_mode']=='real-time':
     self.assertEqual(args[args.index('--installation')+1],'doctor-dsp-install')
    if name=='musical-audio':
     self.assertEqual(args[args.index('--midi-real-install')+1],'qualified-real-install');self.assertEqual(args[args.index('--audio-install')+1],'doctor-dsp-install')
   seen.append(True);return rows
  with patch.object(manual_build,'plan',side_effect=reviewed_plan):
   names=tool.canonical_stage_names(tool.ROOT,sorted(p.name for p in (tool.ROOT/'manual').glob('scene-plans*.yaml')))
  assert_canonical_inventory(self,names);self.assertEqual(seen,[True])
 def test_missing_full_build_phase_rejected(self):
  fixture=CompletedBuildReviewTests();fixture.setUp()
  try:
   with patch.object(tool,'canonical_stage_names',return_value=[v['name'] for v in fixture.manifest['stages']]+['doctor-options-audit']):
    with self.assertRaisesRegex(ValueError,'canonical plan'):tool.verify_manifest(fixture.root,fixture.build,fixture.pin)
  finally:fixture.tearDown()
 def test_historical_doctor_publication_substitution_rejected(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);write(root/'manual/generated/doctor-scenes.json',{'evidence':{'runs':[{'report':'historical'}]},'scenes':[]})
   m={'stages':[{'name':'doctor-manual-real','native_report':{'path':'new-manual'}},{'name':'doctor-auto-real','native_report':{'path':'new-auto'}},{'name':'doctor-publish','executed_command':['publish','--manual-report','new-manual','--auto-report','new-auto']}]}
   with patch('manual_doctor_publish.collect_reports',return_value={'evidence':{'runs':[{'report':'new'}]}}):
    with self.assertRaisesRegex(ValueError,'same-build capture reports'):tool.reproduced_scenes(root,root,m)

class LedgerTransactionTests(unittest.TestCase):
 def test_failed_strict_validation_restores_all_ledger_bytes(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);targets=['docs/ui-reimplementation/current-source-review.json','docs/ui-reimplementation/source-inventory.json','docs/ui-reimplementation/generated/source-review-receipt.json'];previous={'files':{},'manual_sections':[],'grid_registrations':[],'controller_units':[]}
   for name in targets:write(root/name,previous)
   original={name:(root/name).read_bytes() for name in targets};review={'baseline_inventory':'historical.json','post_build_review':{'changes':[]}}
   with patch.object(tool,'ROOT',root),patch.object(tool,'prepare',return_value=review),patch.object(tool.refresher,'refresh',return_value=(previous,{'branches':[]})),patch('validate.validate',return_value=['deliberate rejection']):
    with self.assertRaisesRegex(ValueError,'Strict source validation failed'):tool.reconcile(root/'build','manifest-pin',root/'snapshot',root/'new-evidence')
   self.assertEqual(original,{name:(root/name).read_bytes() for name in targets});self.assertFalse(list(root.rglob('*.post-build-review')))

class ControlledGenerationManifestTests(unittest.TestCase):
 def fixture(self):
  f=CompletedBuildReviewTests();f.setUp();self.addCleanup(f.tearDown)
  f.manifest.update(build_complete=False,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',manual_generation_complete=True)
  write(f.build/'manifest.json',f.manifest);f.pin=tool.sha((f.build/'manifest.json').read_bytes());return f
 def verify(self,f):
  with patch.object(tool,'canonical_stage_names',return_value=[v['name'] for v in f.manifest['stages']]),patch('manual_build.verify_doctor_completion',side_effect=AssertionError('Full qualification must not be inferred')):
   return tool.verify_manifest(f.root,f.build,f.pin)
 def test_explicit_completed_generation_not_full_qualification(self):
  f=self.fixture();self.assertEqual(self.verify(f)['realtime_qualification'],'pending-ci')
 def test_missing_generation_completion_rejected(self):
  f=self.fixture();f.manifest['manual_generation_complete']=False;write(f.build/'manifest.json',f.manifest);f.pin=tool.sha((f.build/'manifest.json').read_bytes())
  with self.assertRaisesRegex(ValueError,'Incomplete'):self.verify(f)
 def test_generation_cannot_claim_full_build(self):
  f=self.fixture();f.manifest['build_complete']=True;write(f.build/'manifest.json',f.manifest);f.pin=tool.sha((f.build/'manifest.json').read_bytes())
  with self.assertRaisesRegex(ValueError,'qualification'):self.verify(f)
 def test_generation_cannot_claim_real_time_qualified(self):
  f=self.fixture();f.manifest['realtime_qualification']='passed';write(f.build/'manifest.json',f.manifest);f.pin=tool.sha((f.build/'manifest.json').read_bytes())
  with self.assertRaisesRegex(ValueError,'qualification'):self.verify(f)
 def test_generation_missing_canonical_phase_rejected(self):
  f=self.fixture()
  with patch.object(tool,'canonical_stage_names',return_value=[v['name'] for v in f.manifest['stages']]+['asset-audit']):
   with self.assertRaisesRegex(ValueError,'canonical plan'):tool.verify_manifest(f.root,f.build,f.pin)

class ControlledGenerationSourceTests(unittest.TestCase):
 def test_controlled_scene_publication_reproduces_exact_native_bytes(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);write(root/'case/capture-trace.json',[])
   plan=root/'plan-source/manual/plan.yaml';plan.parent.mkdir(parents=True);plan.write_text(yaml.safe_dump({'scenes':[{'id':'example','steps':[{'id':'step','assertion':{'kind':'led','passed':True}}]}]}))
   doc={'validation_scope':'controlled-manual-generation','realtime_qualification':'pending-ci','clock_mode':'controlled-experimental','complete_regression_run':False,'evidence':str(root),'source':{'plan_files':{'manual/plan.yaml':tool.sha(plan.read_bytes())}},'scenes':[{'id':'example','behaviour_case':'CASE','requirements':['R1'],'evidence':{'path':str(root/'case'),'capture_trace_sha256':tool.sha((root/'case/capture-trace.json').read_bytes())},'steps':[{'id':'step','inputs':[],'output':{'frame':'actual'},'expect':{'led':1,'assertion':{'kind':'led','passed':True}}}]}]}
   write(root/'native.json',doc);write(root/'manual/generated/reference-example.json',doc);write(root/'manual/generated/doctor-scenes.json',{'scenes':[]})
   m={'validation_scope':'controlled-manual-generation','stages':[{'name':'reference-controlled-example','executed_command':['capture','--publish','--output','reference-example.json'],'native_report':{'path':str(root/'native.json')}},{'name':'doctor-manual-real','native_report':{'path':'same-manual'}},{'name':'doctor-auto-real','native_report':{'path':'same-auto'}},{'name':'doctor-publish','executed_command':['publish','--manual-report','same-manual','--auto-report','same-auto']}]}
   with patch('manual_doctor_publish.collect_reports',return_value={'scenes':[]}),patch('manual_doctor_publish.authored_bindings',return_value={'scenes':[]}):
    result=tool.reproduced_scenes(root,root,m)
   scene=yaml.safe_load(result['manual/features/scenes-reference-example.yaml'])['scenes'][0];self.assertNotIn('evidence',scene);self.assertNotIn('output',scene['steps'][0]);self.assertEqual(scene['steps'][0]['expect'],{'led':1,'assertion':{'kind':'led','passed':True}})
 def test_controlled_publication_cannot_masquerade_as_real_time(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);doc={'validation_scope':'controlled-manual-generation','realtime_qualification':'pending-ci','clock_mode':'real-time','complete_regression_run':False,'scenes':[]}
   write(root/'native.json',doc);write(root/'manual/generated/example.json',doc)
   m={'validation_scope':'controlled-manual-generation','stages':[{'name':'reference-controlled-example','executed_command':['capture','--publish','--output','example.json'],'native_report':{'path':str(root/'native.json')}}]}
   with self.assertRaisesRegex(ValueError,'Controlled generation report scope'):tool.reproduced_scenes(root,root,m)
 def test_local_metadata_requires_scoped_binding_receipt(self):
  f=MetadataReviewTests();f.setUp()
  try:
   before,after=f.bind_receipt()
   with self.assertRaisesRegex(ValueError,'generation binding scope'):tool.check_metadata(f.name,before,after,f.build,controlled_local=True)
  finally:f.tearDown()

class ControlledGenerationIntegrationTests(unittest.TestCase):
 def test_prepare_dispatches_scoped_audit_and_records_ci_pending(self):
  f=CompletedBuildReviewTests();f.setUp();self.addCleanup(f.tearDown)
  f.manifest.update(build_complete=False,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',manual_generation_complete=True)
  write(f.build/'manifest.json',f.manifest);f.pin=tool.sha((f.build/'manifest.json').read_bytes())
  with patch('manual_publication_verify.audit_controlled_manual_generation',create=True,return_value={'passed':True}) as audit,patch('manual_publication_verify.audit_publication',side_effect=AssertionError('No full qualification')),patch('manual_course_bind.verify_publication',side_effect=AssertionError('No two-lane qualification')),patch('manual_quick_reference.render',return_value='qualified quick reference'),patch('manual_book.load',return_value={}),patch.object(tool,'canonical_stage_names',return_value=[v['name'] for v in f.manifest['stages']]),patch.object(tool,'reproduced_scenes',return_value={'manual/features/scenes-new.yaml':f.newscene}):
   result=tool.prepare(f.root,f.build,f.pin,f.snapshot)
  audit.assert_called_once_with(f.build);self.assertEqual(result['post_build_review']['realtime_qualification'],'pending-ci');self.assertTrue(result['post_build_review']['manual_generation_complete']);self.assertFalse(result['post_build_review']['complete_regression_run'])
 def test_local_metadata_preserves_claim_guards_and_scoped_receipt(self):
  f=MetadataReviewTests();f.setUp();self.addCleanup(f.tearDown);a,b=f.bind_receipt();p=f.build/'feature-bind/manifest.json';receipt=tool.read(p);receipt.update(validation_scope='controlled-manual-generation',realtime_qualification='pending-ci');write(p,receipt)
  self.assertIn('controlled-generation',tool.check_metadata(f.name,a,b,f.build,True))
  g=MetadataReviewTests();g.setUp();self.addCleanup(g.tearDown);g.new['features'][0]['controls']=[{'gesture':'invented','result':'invented'}];a,b=g.bind_receipt();p=g.build/'feature-bind/manifest.json';receipt=tool.read(p);receipt.update(validation_scope='controlled-manual-generation',realtime_qualification='pending-ci');write(p,receipt)
  with self.assertRaisesRegex(ValueError,'Prose, controls, citations'):tool.check_metadata(g.name,a,b,g.build,True)

class ActualControlledCanonicalPlanTests(unittest.TestCase):
 def test_local_canonical_sequence_uses_controlled_captures_and_asset_audio(self):
  plans=sorted(p.name for p in (tool.ROOT/'manual').glob('scene-plans*.yaml'));names=tool.canonical_stage_names(tool.ROOT,plans,True)
  self.assertIn('masks-controlled',names);self.assertIn('first-sound-controlled',names);self.assertIn('musical-audio-assets',names)
  self.assertIn('reference-controlled-scene-plans-save-dialog-base-midi',names)
  self.assertNotIn('reference-real-scene-plans-save-dialog-base-midi',names);self.assertIn('fresh-target-midi-producer',names)
  self.assertLess(names.index('compile-book'),names.index('fresh-target-midi-producer'))
  self.assertLess(names.index('fresh-target-midi-producer'),names.index('reader-projection'))
  self.assertNotIn('masks-real',names);self.assertNotIn('first-sound-real',names);self.assertNotIn('musical-audio',names)
  self.assertFalse(any(n.startswith('reference-real-') or n.startswith('doctor-options-') for n in names))
  self.assertIn('doctor-manual-real',names);self.assertIn('doctor-auto-real',names);self.assertIn('doctor-publish',names)
  full=tool.canonical_stage_names(tool.ROOT,plans);assert_canonical_inventory(self,full)
  self.assertLess(full.index('compile-book'),full.index('fresh-target-midi-producer'));self.assertLess(full.index('fresh-target-midi-producer'),full.index('reader-projection'))
  self.assertLess(full.index('reference-real-scene-plans-save-dialog-base-midi'),full.index('reference-controlled-scene-plans-save-dialog-base-midi'))
  for name in STAGES_ADDED:
   if name.startswith('reference-real-'):self.assertNotIn(name,names)
   else:self.assertIn(name,names)
  self.assertEqual(sum(n.startswith('reference-controlled-') for n in names),sum(n.startswith('reference-controlled-') for n in full));self.assertEqual(sum(n.startswith('browser-') for n in names),8)

class ControlledCourseScopeProjectionTests(unittest.TestCase):
 def test_scoped_course_metadata_keeps_all_learning_claims(self):
  with tempfile.TemporaryDirectory() as temp:
   build=Path(temp);old={'project':{'capture_status':'pending','description':'One bar'},'learning_path':[{'stages':[{'id':'one','text':'Play','binding':{'status':'pending'}}]}]};new=copy.deepcopy(old);new['project'].update(capture_status='controlled-verified',validation_scope='controlled-manual-generation',realtime_qualification='pending-ci');new['learning_path'][0]['stages'][0]['binding']={'status':'controlled-verified','scene':'course-one','step':'one'}
   a=yaml.safe_dump(old).encode();b=yaml.safe_dump(new).encode();p=build/'course-bind';p.mkdir();(p/'course-before.yaml').write_bytes(a);(p/'course-after.yaml').write_bytes(b);receipt={'passed':True,'course_written':True,'course_before_sha256':tool.sha(a),'course_after_sha256':tool.sha(b),'validation_scope':'controlled-manual-generation','realtime_qualification':'pending-ci','complete_regression_run':False};write(p/'binding-receipt.json',receipt)
   self.assertIn('controlled-generation',tool.check_metadata('manual/course.yaml',a,b,build,True))
   with self.assertRaisesRegex(ValueError,'Learning text or source claims'):tool.check_metadata('manual/course.yaml',a,b,build,False)
   new['project']['description']='Invented lesson';b=yaml.safe_dump(new).encode();(p/'course-after.yaml').write_bytes(b);receipt['course_after_sha256']=tool.sha(b);write(p/'binding-receipt.json',receipt)
   with self.assertRaisesRegex(ValueError,'Learning text or source claims'):tool.check_metadata('manual/course.yaml',a,b,build,True)

class ReferenceObjectReconstructionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.run=Path(self.tmp.name)
  self.trace=[{'type':'enc','n':2,'delta':2},{'type':'wait','seconds':.1}]
  trace=self.run/'case/capture-trace.json';write(trace,self.trace);self.trace_sha=tool.sha(trace.read_bytes())
  self.plans={'scenes':[{'id':sid,'steps':[{'id':'one','assertion':{'kind':'ensemble-polyrhythm','role_pitches':{1:48,2:55}}}]} for sid in ['first','second']]}
  p=self.run/'plan-source/manual/plan.yaml';p.parent.mkdir(parents=True);p.write_text(yaml.safe_dump(self.plans,sort_keys=False));self.plan=p
  requirements=['R1'];scenes=[]
  for sid in ['first','second']:
   scenes.append(dict(id=sid,behaviour_case='CASE',profile='base-midi',requirements=requirements,steps=[dict(id='one',inputs=self.trace[:],expect={'assertion':{'kind':'ensemble-polyrhythm','role_pitches':{1:48,2:55}}},output={})],evidence={'path':str(trace.parent),'capture_trace_sha256':self.trace_sha}))
  self.original={'scenes':scenes,'source':{'plan_files':{'manual/plan.yaml':tool.sha(p.read_bytes())}},'evidence':str(self.run)}
  self.document=json.loads(json.dumps(self.original))
 def expected(self):
  expected=copy.deepcopy(self.original['scenes'])
  for scene in expected:
   scene.pop('evidence')
   for step in scene['steps']:step.pop('output')
  return dict(schema_version=1,fixture_kind='behaviour-case',trace_contract='The original pinned case replays public inputs and verifies every authored semantic selector; per-scene deltas include native encoder units and waits.',scenes=expected)
 def test_source_typed_integer_selector_keys_reproduce_exact_yaml(self):
  expected=self.expected();expected['scenes']=expected['scenes'][:1];doc=copy.deepcopy(self.document);doc['scenes']=doc['scenes'][:1]
  self.assertEqual(yaml.safe_dump(tool.reference_authoring(doc),sort_keys=False),yaml.safe_dump(expected,sort_keys=False))
 def test_source_shared_trace_and_requirements_reproduce_exact_alias_bytes(self):
  expected=self.expected()
  for scene in expected['scenes']:scene['steps'][0]['expect']['assertion']={'kind':'plain','passed':True}
  for scene in self.document['scenes']:scene['steps'][0]['expect']['assertion']={'kind':'plain','passed':True}
  for scene in self.plans['scenes']:scene['steps'][0]['assertion']={'kind':'plain','passed':True}
  self.plan.write_text(yaml.safe_dump(self.plans,sort_keys=False));self.document['source']['plan_files']['manual/plan.yaml']=tool.sha(self.plan.read_bytes())
  self.assertEqual(yaml.safe_dump(tool.reference_authoring(self.document),sort_keys=False),yaml.safe_dump(expected,sort_keys=False))
 def test_reject_actual_value_differing_from_pinned_selector(self):
  self.document['scenes'][0]['steps'][0]['expect']['assertion']['role_pitches']['1']=99
  with self.assertRaisesRegex(ValueError,'selector'):tool.reference_authoring(self.document)
 def test_reject_actual_inputs_differing_from_immutable_trace(self):
  self.document['scenes'][0]['steps'][0]['inputs'][0]['delta']=9
  with self.assertRaisesRegex(ValueError,'trace'):tool.reference_authoring(self.document)

 def polymeter_fixture(self):
  assertion={'kind':'rejected-range-channel-isolation','phrases':{1:[[144,60,127]],2:[[145,79,40]]}}
  for plan in self.plans['scenes']:plan['steps'][0]['assertion']=copy.deepcopy(assertion)
  for scene in self.original['scenes']:scene['steps'][0]['expect']['assertion']=copy.deepcopy(assertion)
  self.plan.write_text(yaml.safe_dump(self.plans,sort_keys=False));self.original['source']['plan_files']['manual/plan.yaml']=tool.sha(self.plan.read_bytes());self.document=json.loads(json.dumps(self.original))
 def test_polymeter_source_typed_phrase_channels_reproduce_exact_yaml(self):
  self.polymeter_fixture()
  self.assertEqual(yaml.safe_dump(tool.reference_authoring(self.document),sort_keys=False),yaml.safe_dump(self.expected(),sort_keys=False))
 def test_polymeter_changed_actual_phrase_value_is_rejected(self):
  self.polymeter_fixture();self.document['scenes'][0]['steps'][0]['expect']['assertion']['phrases']['1'][0][1]=99
  with self.assertRaisesRegex(ValueError,'selector'):tool.reference_authoring(self.document)

 def shared_selector_fixture(self,shared=True,crosscase=False):
  assertion={'kind':'composition-workflow','stage':'default-skip','passed':True}
  for i,plan in enumerate(self.plans['scenes']):
   plan['behaviour_case']='OTHER' if crosscase and i else 'CASE'
   plan['steps'][0]['assertion']=assertion if shared else copy.deepcopy(assertion)
  for i,scene in enumerate(self.original['scenes']):
   scene['behaviour_case']='OTHER' if crosscase and i else 'CASE'
   scene['steps'][0]['expect']['assertion']=assertion if shared and not crosscase else copy.deepcopy(assertion)
   if crosscase and i:scene['requirements']=copy.deepcopy(scene['requirements'])
  self.plan.write_text(yaml.safe_dump(self.plans,sort_keys=False));self.original['source']['plan_files']['manual/plan.yaml']=tool.sha(self.plan.read_bytes());self.document=json.loads(json.dumps(self.original))
 def test_exact_source_shared_selector_reproduces_alias_bytes(self):
  self.shared_selector_fixture()
  self.assertEqual(yaml.safe_dump(tool.reference_authoring(self.document),sort_keys=False),yaml.safe_dump(self.expected(),sort_keys=False))
 def test_equal_but_distinct_source_selectors_remain_distinct(self):
  self.shared_selector_fixture(shared=False)
  result=tool.reference_authoring(self.document)
  self.assertIsNot(result['scenes'][0]['steps'][0]['expect']['assertion'],result['scenes'][1]['steps'][0]['expect']['assertion'])
  self.assertEqual(yaml.safe_dump(result,sort_keys=False),yaml.safe_dump(self.expected(),sort_keys=False))
 def test_source_alias_cannot_merge_assertions_across_cases(self):
  self.shared_selector_fixture(crosscase=True)
  result=tool.reference_authoring(self.document)
  self.assertIsNot(result['scenes'][0]['steps'][0]['expect']['assertion'],result['scenes'][1]['steps'][0]['expect']['assertion'])
  self.assertEqual(yaml.safe_dump(result,sort_keys=False),yaml.safe_dump(self.expected(),sort_keys=False))
 def test_changed_second_actual_shared_assertion_is_rejected(self):
  self.shared_selector_fixture();self.document['scenes'][1]['steps'][0]['expect']['assertion']['stage']='forged'
  with self.assertRaisesRegex(ValueError,'selector'):tool.reference_authoring(self.document)

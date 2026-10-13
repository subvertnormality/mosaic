"""Fail-closed post-build documentary source review fixtures; no native launches."""
import copy,hashlib,json,tempfile,unittest
from unittest.mock import patch
from contextlib import ExitStack
from pathlib import Path
import yaml
import reconcile_manual_build as tool
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

class ReviewedDesignGapTests(unittest.TestCase):
 def test_reserialized_immutable_yaml_requires_receipt(self):
  with tempfile.TemporaryDirectory() as temp:
   with self.assertRaisesRegex(ValueError,'Unapproved'):tool.check_metadata('manual/player-routes.yaml',b'value: original\n',b'value: original\n\n',Path(temp))
 def test_canonical_full_plan_contains_all_qualification_and_browser_stages(self):
  root=tool.ROOT;plans=sorted(p.name for p in (root/'manual').glob('scene-plans*.yaml'));names=tool.canonical_stage_names(root,plans)
  self.assertEqual(len(names),72);self.assertIn('doctor-options-audit',names);self.assertEqual(sum(name.startswith('browser-') for name in names),7)
 def test_canonical_plan_supplies_explicit_readability_install_argument(self):
  import manual_build
  actual=manual_build.plan;seen=[]
  def reviewed_plan(options,plans):
   self.assertEqual(getattr(options,'readability_real_install',None),'identity')
   rows=actual(options,plans);real=next(row for row in rows if row['name']=='reference-real-scene-plans-readability-base-midi');args=real['command']
   self.assertEqual(args[args.index('--experimental-install')+1],'identity');self.assertEqual(args[args.index('--clock-mode')+1],'real-time');seen.append(True);return rows
  with patch.object(manual_build,'plan',side_effect=reviewed_plan):
   names=tool.canonical_stage_names(tool.ROOT,sorted(p.name for p in (tool.ROOT/'manual').glob('scene-plans*.yaml')))
  self.assertEqual(len(names),72);self.assertEqual(seen,[True])
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

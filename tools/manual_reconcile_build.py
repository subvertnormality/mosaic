"""Explicit post-build source review; never run during native capture.

A separately pinned completed build and preserved prebuild ledger are required.
Only reproduced generated authoring and receipted binding metadata are admitted.
"""
import argparse,copy,hashlib,json,os,sys
from types import SimpleNamespace
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'docs/ui-reimplementation/tools'))
sys.path.insert(0,str(ROOT/'tools'))
import refresh_source_inventory as refresher

def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def safe(root,name):
 p=(root/name).resolve()
 if p==root.resolve() or root.resolve() not in p.parents:raise ValueError('Unsafe source path')
 return p
def require(ok,message):
 if not ok:raise ValueError(message)
def feature_claims(document):
 out=copy.deepcopy(document)
 for f in out.get('features',[]):f.pop('review',None);f.pop('scene_refs',None)
 return out
def course_claims(document,controlled_local=False):
 out=copy.deepcopy(document);out['project'].pop('capture_status',None)
 if controlled_local:
  out['project'].pop('validation_scope',None);out['project'].pop('realtime_qualification',None)
 for ch in out['learning_path']:
  for stage in ch['stages']:stage.pop('binding',None)
 return out
def controlled_generation(manifest):
 return manifest.get('validation_scope')=='controlled-manual-generation'

def canonical_stage_names(root,plans,controlled_local=False):
 import manual_build
 opts=SimpleNamespace(mod_code_root='identity',audio_emulator='identity',audio_install='identity',ffmpeg='identity',emulator='identity',controlled_install='identity',real_install='identity',modulation_code_root='identity',readability_real_install='identity',browser_tests=True,quick_output='cheat_sheet.html',controlled_local=controlled_local)
 previous=manual_build.ROOT
 try:
  manual_build.ROOT=root
  return [row['name'] for row in (manual_build.plan(opts,plans,controlled_local=True) if controlled_local else manual_build.plan(opts,plans))]
 finally:manual_build.ROOT=previous

def verify_manifest(root,build,pin):
 path=build/'manifest.json';require(sha(path.read_bytes())==pin,'Build manifest pin mismatch');m=read(path)
 local=controlled_generation(m)
 require(m.get('passed') is True and m.get('renderer_validated') is True and m.get('complete_regression_run') is False,'Incomplete build receipt')
 if local:
  require(m.get('build_complete') is False and m.get('realtime_qualification')=='pending-ci','Generation cannot claim full or real-time qualification')
  require(m.get('manual_generation_complete') is True,'Incomplete manual generation receipt')
 else:require(m.get('build_complete') is True,'Incomplete build receipt')
 require(m.get('tool_sha256')==sha((root/'tools/manual_build.py').read_bytes()),'Build tool identity changed')
 required=sorted(p.name for p in (root/'manual').glob('scene-plans*.yaml'))
 require(sorted(m.get('required_plans',[]))==required and sorted(m.get('selected_plans',[]))==required,'Build plan inventory changed')
 require([row['name'] for row in m['stages']]==(canonical_stage_names(root,m['selected_plans'],True) if local else canonical_stage_names(root,m['selected_plans'])),'Build stage sequence differs from selected canonical plan')
 names=set()
 for row in m['stages']:
  name=row['name'];require(name not in names,'Duplicate stage');names.add(name)
  require(read(build/(name+'.json'))==row and row.get('passed') is True,'Forged or failed stage receipt')
  if row.get('executed_command'):
   require(row.get('returncode')==0 and sha((build/(name+'.log')).read_bytes())==row.get('log_sha256'),'Changed stage log')
  if row.get('native_report'):
   report=row['native_report'];require(sha(Path(report['path']).read_bytes())==report['sha256'],'Changed native report')
 required_stages={'refresh-scene-index','raw-publication-audit','feature-bind','course-bind','compile-book','quick-reference','publication-audit'}
 require(required_stages<=names,'Missing mandatory build stage')
 from manual_build import verify_doctor_completion
 if not local:verify_doctor_completion(m['stages'])
 actual={str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted((root/'manual').rglob('*.yaml'))}
 require(m['source_files_after']==actual,'Build after source inventory mismatch')
 for name,h in m['source_files_before'].items():require(sha(safe(build/'authoring-before',name).read_bytes())==h,'Changed prebuild authoring')
 return m

def check_metadata(name,before,after,build,controlled_local=False):
 old,new=yaml.safe_load(before),yaml.safe_load(after)
 if before==after:return 'unchanged authored bytes'
 if name=='manual/course.yaml':
  receipt=read(build/'course-bind/binding-receipt.json')
  if controlled_local:require(receipt.get('validation_scope')=='controlled-manual-generation' and receipt.get('realtime_qualification')=='pending-ci' and receipt.get('complete_regression_run') is False,'Missing controlled generation binding scope')
  require(receipt.get('passed') is True and receipt.get('course_written') is True,'Missing course binding proof')
  require(receipt['course_before_sha256']==sha(before) and receipt['course_after_sha256']==sha(after),'Course binding identity mismatch')
  require((build/'course-bind/course-before.yaml').read_bytes()==before and (build/'course-bind/course-after.yaml').read_bytes()==after,'Course snapshots differ')
  if controlled_local:require(new['project'].get('validation_scope')=='controlled-manual-generation' and new['project'].get('realtime_qualification')=='pending-ci','Controlled course metadata scope mismatch')
  require(course_claims(old,controlled_local)==course_claims(new,controlled_local),'Learning text or source claims changed')
  return 'controlled-generation receipted course binding; real-time qualification pending CI' if controlled_local else 'two-lane receipted course binding only'
 if name.startswith('manual/features/') and 'features' in old:
  receipt=read(build/'feature-bind/manifest.json')
  if controlled_local:require(receipt.get('validation_scope')=='controlled-manual-generation' and receipt.get('realtime_qualification')=='pending-ci' and receipt.get('complete_regression_run') is False,'Missing controlled generation binding scope')
  require(receipt.get('passed') is True and receipt.get('complete_regression_run') is False,'Missing feature binding proof')
  files=[v for v in receipt['files'] if v['path']==name]
  require(len(files)==1 and files[0]['before_sha256']==sha(before) and files[0]['after_sha256']==sha(after),'Feature binding identity mismatch')
  require(safe(build/'feature-bind/before',name).read_bytes()==before and safe(build/'feature-bind/after',name).read_bytes()==after,'Feature snapshots differ')
  require(feature_claims(old)==feature_claims(new),'Prose, controls, citations or source claims changed')
  changed={a['id'] for a,b in zip(old['features'],new['features']) if a!=b}
  mappings={v['feature']:v for v in receipt['mappings'] if v['source']==name}
  require(changed<=set(mappings),'Unreceipted feature metadata change')
  for a,b in zip(old['features'],new['features']):
   if a['id'] not in changed:continue
   row=mappings[a['id']]
   history=a.get('review',{}).get('historical_native_evidence',[])+[{'review':{k:v for k,v in a.get('review',{}).items() if k!='historical_native_evidence'},'scene_refs':a.get('scene_refs',[])}]
   require(b.get('review',{}).get('historical_native_evidence')==history,'Historical feature review or evidence changed')
   require(row.get('scene_ids',[]) and set(row['scene_ids'])<=set(b.get('scene_refs',[])) and b.get('review',{}).get('binding_receipt')==str(build/'feature-bind/manifest.json'),'Feature scene receipt membership changed')
   canonical=lambda v:sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
   require(row['claims_sha256']==canonical({k:v for k,v in b.items() if k not in ('review','scene_refs')}) and row['prior_review_sha256']==canonical(a.get('review',{})) and row['current_review_sha256']==canonical(b.get('review',{})),'Feature receipt claims mismatch')
  return 'independently audited controlled-generation receipted feature review; real-time qualification pending CI' if controlled_local else 'independently audited receipted feature review and scene references only'
 raise ValueError('Unapproved authored source mutation: '+name)

def reference_authoring(doc):
 """Recover only source-proven Python types/sharing erased by JSON serialization."""
 run=Path(doc['evidence']);plans={}
 canonical=lambda value:json.dumps(json.loads(json.dumps(value)),sort_keys=True,separators=(',',':'))
 for name,expected in doc['source']['plan_files'].items():
  path=safe(run/'plan-source',name);require(sha(path.read_bytes())==expected,'Changed frozen selector source')
  for plan in yaml.safe_load(path.read_bytes())['scenes']:
   require(plan['id'] not in plans,'Duplicate frozen scene selector');plans[plan['id']]=plan
 scenes=copy.deepcopy(doc['scenes']);requirements={};traces={};selectors={}
 for scene in scenes:
  case=scene['behaviour_case'];shared=requirements.setdefault(case,scene['requirements'])
  require(shared==scene['requirements'],'Inconsistent source-shared case requirements');scene['requirements']=shared
  trace_path=Path(scene['evidence']['path'])/'capture-trace.json'
  require(sha(trace_path.read_bytes())==scene['evidence']['capture_trace_sha256'],'Changed immutable capture trace')
  trace=traces.setdefault(str(trace_path.resolve()),read(trace_path));cursor=0
  plan=plans.get(scene['id']);require(plan is not None,'Missing frozen scene selector')
  for step in scene['steps']:
   matches=[item for item in plan['steps'] if item['id']==step['id']]
   require(len(matches)==1,'Missing or duplicate frozen step selector');item=matches[0]
   accepted=[item['assertion']]+item.get('assertion_alternatives',[]);actual=step['expect']['assertion']
   matched=[value for value in accepted if canonical(value)==canonical(actual)]
   require(matched,'Actual assertion differs from frozen selector')
   # Only a shared frozen selector object within the same case proves aliasing.
   owner=(case,id(matched[0]));shared=selectors.setdefault(owner,actual)
   require(canonical(shared)==canonical(actual),'Shared actual assertion differs from frozen selector')
   actual=shared;step['expect']['assertion']=actual
   if actual.get('kind')=='ensemble-polyrhythm' and 'role_pitches' in actual:
    typed=matched[0].get('role_pitches')
    require(isinstance(typed,dict) and all(type(key)is int for key in typed),'Ensemble selector lacks integer channel keys')
    require(canonical(typed)==canonical(actual['role_pitches']),'Actual role pitches differ from source selector')
    actual['role_pitches']=copy.deepcopy(typed)
   if actual.get('kind')=='rejected-range-channel-isolation' and 'phrases' in actual:
    typed=matched[0].get('phrases')
    require(isinstance(typed,dict) and all(type(key)is int for key in typed),'Polymeter selector lacks integer channel keys')
    require(canonical(typed)==canonical(actual['phrases']),'Actual polymeter phrases differ from source selector')
    actual['phrases']=copy.deepcopy(typed)
   end=cursor+len(step['inputs'])
   require(trace[cursor:end]==step['inputs'],'Actual inputs differ from immutable capture trace')
   step['inputs']=trace[cursor:end];cursor=end;step.pop('output')
  scene.pop('evidence')
 return dict(schema_version=1,fixture_kind='behaviour-case',trace_contract='The original pinned case replays public inputs and verifies every authored semantic selector; per-scene deltas include native encoder units and waits.',scenes=scenes)

def reproduced_scenes(root,build,m):
 from manual_doctor_publish import authored_bindings,collect_reports
 result={}
 for row in m['stages']:
  prefix='reference-controlled-' if controlled_generation(m) else 'reference-real-'
  if not row['name'].startswith(prefix):continue
  args=row['executed_command'];require('--publish' in args and '--output' in args,'Reference publication command missing')
  output=args[args.index('--output')+1];require(Path(output).name==output and output.endswith('.json'),'Unsafe generated output')
  doc=read(row['native_report']['path']);require(read(root/'manual/generated'/output)==doc,'Published reference differs from native report')
  if controlled_generation(m):require(doc.get('validation_scope')=='controlled-manual-generation' and doc.get('realtime_qualification')=='pending-ci' and doc.get('clock_mode')=='controlled-experimental' and doc.get('complete_regression_run') is False,'Controlled generation report scope mismatch')
  authored=reference_authoring(doc)
  result['manual/features/scenes-'+Path(output).stem+'.yaml']=yaml.safe_dump(authored,sort_keys=False).encode()
 doctor=read(root/'manual/generated/doctor-scenes.json')
 byname={row['name']:row for row in m['stages']}
 manual=byname['doctor-manual-real']['native_report'];auto=byname['doctor-auto-real']['native_report']
 command=byname['doctor-publish']['executed_command']
 require('--manual-report' in command and command[command.index('--manual-report')+1]==manual['path'] and '--auto-report' in command and command[command.index('--auto-report')+1]==auto['path'],'Doctor publication differs from exact same-build capture paths')
 require(doctor==collect_reports(manual['path'],auto['path']),'Doctor publication differs from exact same-build capture reports')
 result['manual/features/scenes-doctor-scenes.yaml']=yaml.safe_dump(authored_bindings(doctor),sort_keys=False,allow_unicode=True).encode()
 # Player route YAML is normative authoring, not emitted by the projection stage.
 return result

def validate_snapshot_authoring(snapshot,snap,review,m):
 for name,item in review['files'].items():
  before=safe(snapshot,name).read_bytes()
  require(sha(before)==item['sha256']==snap['files'][name],'Prebuild ledger snapshot mismatch')
  if name.endswith('.yaml') and name.startswith('manual/'):
   require(m['source_files_before'].get(name)==sha(before),'Initial ledger differs from build authoring-before')

def prepare(root,build,pin,snapshot,approved_overlay=None,overlay_sha256=None):
 m=verify_manifest(root,build,pin);snap=read(snapshot/'snapshot.json');review=read(snapshot/'docs/ui-reimplementation/current-source-review.json')
 if approved_overlay is not None:
  require(controlled_generation(m),'Reviewed metadata transition requires controlled generation')
  from manual_metadata_transition import validate_prebuild_overlay,METADATA
  pre=validate_prebuild_overlay(root,approved_overlay,overlay_sha256,check_current=True,check_sources=False)
  for rel in METADATA:
   require(safe(snapshot,rel).read_bytes()==pre['before'][rel],'Physical prebuild snapshot ledger differs from captured overlay original')
  review=json.loads(pre['overlay'][METADATA[0]])
 require((root/'docs/ui-reimplementation/current-source-review.json').read_bytes()==(snapshot/'docs/ui-reimplementation/current-source-review.json').read_bytes(),'Reviewed ledger changed since preserved snapshot')
 validate_snapshot_authoring(snapshot,snap,review,m)
 if controlled_generation(m):
  from manual_publication_verify import audit_controlled_manual_generation
  require(audit_controlled_manual_generation(build).get('passed') is True,'Independent controlled generation audit failed')
 else:
  from manual_publication_verify import audit_publication
  require(audit_publication().get('passed') is True,'Independent publication audit failed')
  from manual_course_bind import verify_publication
  verify_publication(root)
 return derive_review(root,build,pin,snapshot,m,snap,review)

def derive_review(root,build,pin,snapshot,m=None,snap=None,review=None):
 if m is None: m=verify_manifest(root,build,pin)
 if snap is None: snap=read(snapshot/"snapshot.json")
 if review is None: review=read(snapshot/"docs/ui-reimplementation/current-source-review.json")
 validate_snapshot_authoring(snapshot,snap,review,m)
 generated=reproduced_scenes(root,build,m)
 index=next(s for s in m['stages'] if s['name']=='refresh-scene-index')['action']
 from manual_build import scene_sources
 oldbook=yaml.safe_load((snapshot/'manual/book.yaml').read_bytes());newbook=yaml.safe_load((root/'manual/book.yaml').read_bytes())
 expected=copy.deepcopy(oldbook);prior=[n for n in oldbook.get('scene_sources',[]) if not n.startswith('scene-plans') and not n.startswith('features/scenes-')]
 emitted=[Path(n).name for n in generated]+['scenes-player-routes.yaml']
 expected['scene_sources']=scene_sources(index['plans'],emitted)+prior
 require(newbook==expected,'Book changed outside reproduced scene index')
 require(set(index['outputs'])=={Path(n).stem[len('scenes-'):]+'.json' for n in generated}|{'player-routes.json'},'Scene output inventory differs from build stage')
 from manual_quick_reference import render
 from manual_book import load
 require((root/'cheat_sheet.html').read_text()==render(load(),'manual/','manual/legacy/'),'Quick reference differs from exact qualified authoring')
 require(any(s['name']=='quick-reference' and s['executed_command'][-1]==str(root/'cheat_sheet.html') for s in m['stages']),'Build did not generate root quick reference')
 changes=[];retired={};newreview=copy.deepcopy(review)
 for name,item in list(newreview['files'].items()):
  before=safe(snapshot,name).read_bytes();current=safe(root,name)
  if not current.exists():
   require(name.startswith('manual/features/scenes-') and name not in generated and name[7:] not in newbook['scene_sources'],'Unapproved source removal')
   archive=safe(build/'previous-publication',name)
   require(archive.read_bytes()==before,'Retired generated source archive mismatch')
   retired[name]={'sha256':sha(before),'archive':str(archive),'meaning':'Exact obsolete generated scene authoring retained by completed build, absent final scene index.'};newreview['files'].pop(name);changes.append({'path':name,'kind':'retired','sha256':sha(before)});continue
  after=current.read_bytes()
  if after==before:continue
  if name in generated:require(after==generated[name],'Generated scene YAML does not reproduce');meaning='Exact scene authoring reproduced from audited successful native publication.'
  elif name=='manual/book.yaml':meaning='Only completed-build reproduced scene source index changed.'
  elif name=='cheat_sheet.html':meaning='Exact root quick reference regenerated from qualified unchanged authored controls.'
  elif name.startswith('manual/') and name.endswith('.yaml'):meaning=check_metadata(name,before,after,build,controlled_generation(m))
  else:raise ValueError('Runtime or non-generated source drift: '+name)
  item['sha256']=sha(after);item['meaning']+=' Post-build review: '+meaning;changes.append({'path':name,'kind':'changed','before_sha256':sha(before),'after_sha256':sha(after),'meaning':meaning})
 for name,raw in generated.items():
  require(safe(root,name).read_bytes()==raw,'Generated scene YAML does not reproduce')
  if name not in newreview['files']:
   newreview['files'][name]={'sha256':sha(raw),'meaning':'Exact new scene authoring reproduced from audited successful native build report.'};changes.append({'path':name,'kind':'added','sha256':sha(raw)})
 newreview['retired_generated_files']=dict(newreview.get('retired_generated_files',{}),**retired)
 newreview['post_build_review']={'manifest':str(build/'manifest.json'),'sha256':pin,'prebuild_snapshot':str(snapshot/'snapshot.json'),'sha256_before':sha((snapshot/'snapshot.json').read_bytes()),'changes':changes,'complete_regression_run':False}
 if controlled_generation(m):newreview['post_build_review'].update(validation_scope='controlled-manual-generation',manual_generation_complete=True,realtime_qualification='pending-ci')
 return newreview

def ledger_payloads(review,out,receipt):
 # Raw UTF-8 like the ledgers, the approved overlay and the deterministic replay.
 return [json.dumps(value,indent=2,ensure_ascii=False)+'\n' for value in (review,out,receipt)]
def reconcile(build,pin,snapshot,evidence,approved_overlay=None,overlay_sha256=None,transition_proof=None,native_identity=None):
 root=ROOT;build=Path(build).resolve();snapshot=Path(snapshot).resolve();evidence=Path(evidence).resolve()
 require(not evidence.exists(),'Evidence destination already exists')
 options=(approved_overlay,overlay_sha256,transition_proof,native_identity)
 require(all(v is None for v in options) or all(v is not None for v in options),'Reviewed transition options must be supplied together')
 if transition_proof is not None:
  transition_proof=Path(transition_proof).resolve()
  require(not transition_proof.exists(),'Transition proof destination already exists')
  require(root.resolve() not in transition_proof.parents and transition_proof!=root.resolve(),'Transition proof must be external')
 review=prepare(root,build,pin,snapshot,approved_overlay,overlay_sha256)
 targets=[root/'docs/ui-reimplementation/current-source-review.json',root/'docs/ui-reimplementation/source-inventory.json',root/'docs/ui-reimplementation/generated/source-review-receipt.json']
 originals={p:p.read_bytes() for p in targets}
 baseline=refresher.ROOT/review['baseline_inventory'];out,receipt=refresher.refresh(baseline,review)
 previous=json.loads(originals[targets[1]])
 for key in ['manual_sections','grid_registrations','controller_units']:require(out[key]==previous[key],'Historical source identities or callbacks changed')
 payloads=ledger_payloads(review,out,receipt)
 evidence.mkdir(parents=True)
 for p,raw in originals.items():
  dest=evidence/'before'/p.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 temporaries={}
 try:
  for p,text in zip(targets,payloads):
   temporary=p.with_name('.'+p.name+'.post-build-review')
   with temporary.open('x') as handle:handle.write(text);handle.flush();os.fsync(handle.fileno())
   temporaries[p]=temporary
  require(all(p.read_bytes()==raw for p,raw in originals.items()),'Concurrent source ledger change')
  for p,temporary in temporaries.items():os.replace(temporary,p)
  import validate
  result=validate.validate()
  require(not result,'Strict source validation failed: '+str(result))
  if transition_proof is not None:
   from manual_metadata_transition import create_proof
   create_proof(root,transition_proof,approved_overlay,overlay_sha256,build,snapshot,native_identity,Path(__file__).resolve(),root/'docs/ui-reimplementation/tools/refresh_source_inventory.py')
   from manual_publication_verify import audit_controlled_manual_generation
   require(audit_controlled_manual_generation(build,require_manual_generation_complete=True,metadata_transition_proof=transition_proof).get('passed') is True,'Post-reconciliation controlled generation audit failed')
 except BaseException:
  for p,raw in originals.items():p.write_bytes(raw)
  if transition_proof is not None and transition_proof.exists():
   transition_proof.rename(evidence/'failed-metadata-transition-proof.json')
  raise
 finally:
  for temporary in temporaries.values():
   if temporary.exists():temporary.unlink()
 report={'passed':True,'complete_regression_run':False,'build_manifest_sha256':pin,'files_before':len(previous['files']),'files_after':len(out['files']),'manual_sections':len(out['manual_sections']),'callbacks':len(out['grid_registrations']),'branches':len(receipt['branches']),'changes':review['post_build_review']['changes'],'after':{str(p.relative_to(root)):sha(p.read_bytes()) for p in targets}}
 if review['post_build_review'].get('validation_scope'):report.update(validation_scope='controlled-manual-generation',manual_generation_complete=True,realtime_qualification='pending-ci')
 if transition_proof is not None:report['metadata_transition_proof']={'path':str(transition_proof),'sha256':sha(transition_proof.read_bytes()),'exact_application_files':243,'transitioned_metadata_files':3}
 (evidence/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build-evidence',required=True,type=Path);p.add_argument('--manifest-sha256',required=True);p.add_argument('--prebuild-snapshot',required=True,type=Path);p.add_argument('--evidence',required=True,type=Path);p.add_argument('--approved-review-overlay',type=Path);p.add_argument('--overlay-sha256');p.add_argument('--metadata-transition-proof',type=Path);p.add_argument('--native-identity',type=Path);args=p.parse_args()
 print(json.dumps(reconcile(args.build_evidence,args.manifest_sha256,args.prebuild_snapshot,args.evidence,args.approved_review_overlay,args.overlay_sha256,args.metadata_transition_proof,args.native_identity),indent=2))
if __name__=='__main__':main()

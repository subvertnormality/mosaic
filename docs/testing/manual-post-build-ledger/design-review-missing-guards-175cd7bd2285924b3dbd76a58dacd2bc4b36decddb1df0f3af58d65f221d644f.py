"""Explicit post-build source review; never run during native capture.

A separately pinned completed build and preserved prebuild ledger are required.
Only reproduced generated authoring and receipted binding metadata are admitted.
"""
import argparse,copy,hashlib,json,sys
from types import SimpleNamespace
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[3]
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
def course_claims(document):
 out=copy.deepcopy(document);out['project'].pop('capture_status',None)
 for ch in out['learning_path']:
  for stage in ch['stages']:stage.pop('binding',None)
 return out
def canonical_stage_names(root,plans):
 import manual_build
 opts=SimpleNamespace(mod_code_root='identity',audio_emulator='identity',audio_install='identity',ffmpeg='identity',emulator='identity',controlled_install='identity',modulation_code_root='identity',browser_tests=True,quick_output='cheat_sheet.html')
 previous=manual_build.ROOT
 try:
  manual_build.ROOT=root
  return [row['name'] for row in manual_build.plan(opts,plans)]
 finally:manual_build.ROOT=previous

def verify_manifest(root,build,pin):
 path=build/'manifest.json';require(sha(path.read_bytes())==pin,'Build manifest pin mismatch');m=read(path)
 require(m.get('passed') is True and m.get('build_complete') is True and m.get('renderer_validated') is True and m.get('complete_regression_run') is False,'Incomplete build receipt')
 require(m.get('tool_sha256')==sha((root/'tools/manual_build.py').read_bytes()),'Build tool identity changed')
 required=sorted(p.name for p in (root/'manual').glob('scene-plans*.yaml'))
 require(sorted(m.get('required_plans',[]))==required and sorted(m.get('selected_plans',[]))==required,'Build plan inventory changed')
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
 verify_doctor_completion(m['stages'])
 actual={str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted((root/'manual').rglob('*.yaml'))}
 require(m['source_files_after']==actual,'Build after source inventory mismatch')
 for name,h in m['source_files_before'].items():require(sha(safe(build/'authoring-before',name).read_bytes())==h,'Changed prebuild authoring')
 return m

def check_metadata(name,before,after,build):
 old,new=yaml.safe_load(before),yaml.safe_load(after)
 if old==new:return 'unchanged authored structure'
 if name=='manual/course.yaml':
  receipt=read(build/'course-bind/binding-receipt.json')
  require(receipt.get('passed') is True and receipt.get('course_written') is True,'Missing course binding proof')
  require(receipt['course_before_sha256']==sha(before) and receipt['course_after_sha256']==sha(after),'Course binding identity mismatch')
  require((build/'course-bind/course-before.yaml').read_bytes()==before and (build/'course-bind/course-after.yaml').read_bytes()==after,'Course snapshots differ')
  require(course_claims(old)==course_claims(new),'Learning text or source claims changed')
  return 'two-lane receipted course binding only'
 if name.startswith('manual/features/') and 'features' in old:
  receipt=read(build/'feature-bind/manifest.json')
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
  return 'independently audited receipted feature review and scene references only'
 raise ValueError('Unapproved authored source mutation: '+name)

def reproduced_scenes(root,build,m):
 from manual_doctor_publish import authored_bindings,collect_reports
 result={}
 for row in m['stages']:
  if not row['name'].startswith('reference-real-'):continue
  args=row['executed_command'];require('--publish' in args and '--output' in args,'Reference publication command missing')
  output=args[args.index('--output')+1];require(Path(output).name==output and output.endswith('.json'),'Unsafe generated output')
  doc=read(row['native_report']['path']);require(read(root/'manual/generated'/output)==doc,'Published reference differs from native report')
  authored=dict(schema_version=1,fixture_kind='behaviour-case',trace_contract='The original pinned case replays public inputs and verifies every authored semantic selector; per-scene deltas include native encoder units and waits.',scenes=copy.deepcopy(doc['scenes']))
  for scene in authored['scenes']:
   scene.pop('evidence',None)
   for step in scene['steps']:step.pop('output')
  result['manual/features/scenes-'+Path(output).stem+'.yaml']=yaml.safe_dump(authored,sort_keys=False).encode()
 doctor=read(root/'manual/generated/doctor-scenes.json')
 result['manual/features/scenes-doctor-scenes.yaml']=yaml.safe_dump(authored_bindings(doctor),sort_keys=False,allow_unicode=True).encode()
 # Player route YAML is normative authoring, not emitted by the projection stage.
 return result

def prepare(root,build,pin,snapshot):
 m=verify_manifest(root,build,pin);snap=read(snapshot/'snapshot.json');review=read(snapshot/'docs/ui-reimplementation/current-source-review.json')
 require((root/'docs/ui-reimplementation/current-source-review.json').read_bytes()==(snapshot/'docs/ui-reimplementation/current-source-review.json').read_bytes(),'Reviewed ledger changed since preserved snapshot')
 for name,item in review['files'].items():
  before=safe(snapshot,name).read_bytes();require(sha(before)==item['sha256']==snap['files'][name],'Prebuild ledger snapshot mismatch')
  if name.endswith('.yaml') and name.startswith('manual/'):
   require(m['source_files_before'].get(name)==sha(before),'Initial ledger differs from build authoring-before')
 from manual_publication_verify import audit_publication
 require(audit_publication().get('passed') is True,'Independent publication audit failed')
 from manual_course_bind import verify_publication
 verify_publication(root)
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
  elif name.startswith('manual/') and name.endswith('.yaml'):meaning=check_metadata(name,before,after,build)
  else:raise ValueError('Runtime or non-generated source drift: '+name)
  item['sha256']=sha(after);item['meaning']+=' Post-build review: '+meaning;changes.append({'path':name,'kind':'changed','before_sha256':sha(before),'after_sha256':sha(after),'meaning':meaning})
 for name,raw in generated.items():
  require(safe(root,name).read_bytes()==raw,'Generated scene YAML does not reproduce')
  if name not in newreview['files']:
   newreview['files'][name]={'sha256':sha(raw),'meaning':'Exact new scene authoring reproduced from audited successful native build report.'};changes.append({'path':name,'kind':'added','sha256':sha(raw)})
 newreview['retired_generated_files']=dict(newreview.get('retired_generated_files',{}),**retired)
 newreview['post_build_review']={'manifest':str(build/'manifest.json'),'sha256':pin,'prebuild_snapshot':str(snapshot/'snapshot.json'),'sha256_before':sha((snapshot/'snapshot.json').read_bytes()),'changes':changes,'complete_regression_run':False}
 return newreview

def reconcile(build,pin,snapshot,evidence):
 root=ROOT;build=Path(build).resolve();snapshot=Path(snapshot).resolve();evidence=Path(evidence).resolve()
 require(not evidence.exists(),'Evidence destination already exists')
 review=prepare(root,build,pin,snapshot)
 targets=[root/'docs/ui-reimplementation/current-source-review.json',root/'docs/ui-reimplementation/source-inventory.json',root/'docs/ui-reimplementation/generated/source-review-receipt.json']
 originals={p:p.read_bytes() for p in targets}
 baseline=refresher.ROOT/review['baseline_inventory'];out,receipt=refresher.refresh(baseline,review)
 previous=json.loads(originals[targets[1]])
 for key in ['manual_sections','grid_registrations','controller_units']:require(out[key]==previous[key],'Historical source identities or callbacks changed')
 payloads=[json.dumps(review,indent=2)+'\n',json.dumps(out,indent=2,ensure_ascii=False)+'\n',json.dumps(receipt,indent=2,ensure_ascii=False)+'\n']
 evidence.mkdir(parents=True)
 for p,raw in originals.items():
  dest=evidence/'before'/p.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 try:
  for p,text in zip(targets,payloads):
   require(p.read_bytes()==originals[p],'Concurrent source ledger change');p.write_text(text)
  import validate
  result=validate.validate()
  require(not result,'Strict source validation failed: '+str(result))
 except BaseException:
  for p,raw in originals.items():p.write_bytes(raw)
  raise
 report={'passed':True,'complete_regression_run':False,'build_manifest_sha256':pin,'files_before':len(previous['files']),'files_after':len(out['files']),'manual_sections':len(out['manual_sections']),'callbacks':len(out['grid_registrations']),'branches':len(receipt['branches']),'changes':review['post_build_review']['changes'],'after':{str(p.relative_to(root)):sha(p.read_bytes()) for p in targets}}
 (evidence/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build-evidence',required=True,type=Path);p.add_argument('--manifest-sha256',required=True);p.add_argument('--prebuild-snapshot',required=True,type=Path);p.add_argument('--evidence',required=True,type=Path);args=p.parse_args()
 print(json.dumps(reconcile(args.build_evidence,args.manifest_sha256,args.prebuild_snapshot,args.evidence),indent=2))
if __name__=='__main__':main()

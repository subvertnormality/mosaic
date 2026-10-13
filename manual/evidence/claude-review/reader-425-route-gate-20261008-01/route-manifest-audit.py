import json,hashlib,yaml
from pathlib import Path
from collections import Counter
OUT=Path('/mnt/c/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6/reader-425-route-gate-source-20261008-01')
ROOT=Path('/home/andy/mosaic-manual-1.4.0')
manifest=json.loads((OUT/'unit-route-manifest.json').read_text())
ledger=json.loads((ROOT/'manual/evidence/claude-review/final-425-reader-ledger-20261008-01/final-425-ledger.json').read_text())
book=json.loads((ROOT/'manual/generated/book.json').read_text()); idx=json.loads((ROOT/'manual/generated/reader-index.json').read_text())
meta=yaml.safe_load((ROOT/'manual/book.yaml').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def stable(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
feat={}
for rel in meta['sources']:
 p=Path('manual')/rel;d=yaml.safe_load((ROOT/p).read_text())
 for f in d.get('features',[]):feat[f['id']]=(f,p)
 if isinstance(d.get('feature'),dict):feat[d['feature']['id']]=(d['feature'],p)
chapters={x['id']:x for x in book['learning_path']}
sourcefiles={}
errors=[]
course=yaml.safe_load((ROOT/'manual/course.yaml').read_text())
recordings=yaml.safe_load((ROOT/'manual/recordings.yaml').read_text())
for row in manifest['routes']:
 try:
  k=row['unit_type']
  if k=='course':
   chapter,stage=row['route'][1:].split('/lesson/')
   source_chapter=next(x for x in course['learning_path'] if x['id']==chapter)
   source=next(x for x in source_chapter['stages'] if x['id']==stage)
   current=next(x for x in chapters[chapter]['stages'] if x['id']==stage)
   assert source['title']==current['title']==row['source_title']
   assert source['binding']['scene']==row['scene_id']
   assert source['teaching_binding']['from_step_id']==row['from_step_id']
   contract=idx['teaching_contracts'][row['contract_id']]
   assert contract['scene_id']==row['scene_id'] and contract['from_step_id']==row['from_step_id'] and contract['to_step_id']==row['target_step_id']
   path=ROOT/'manual/course.yaml';projection=current;row['contract_projection_sha256']=sha(stable(contract))
  elif k=='lesson':
   fid=row['route'][1:].split('/lesson/')[0]; feature,pathrel=feat[fid]
   binding=next(x for x in feature.get('teaching_bindings',[]) if x['id']==row['contract_id'])
   key='feature:'+fid+':'+row['contract_id']; contract=idx['teaching_contracts'][key]
   assert feature.get('category')!='developer' and feature.get('audience')!='developer'
   assert binding['title']==row['source_title']
   assert binding['binding']['scene']==contract['scene_id']==row['scene_id']
   assert binding['teaching_binding']['from_step_id']==contract['from_step_id']==row['from_step_id']
   assert binding['teaching_binding']['actions'] and len(binding['teaching_binding']['actions'])==len(contract['actions'])
   assert contract['to_step_id']==row['target_step_id']
   path=ROOT/pathrel;projection=contract;row['contract_projection_sha256']=sha(stable(contract))
  elif k=='scene':
   fid=row['selected_owner']; feature,pathrel=feat[fid]; scene=book['scenes'][row['scene_id']]
   refs=[r if isinstance(r,str) else r.get('scene_id',r.get('id')) for r in feature.get('scene_refs',[])]
   assert row['scene_id'] in refs and scene['title']==row['source_title']
   assert any(s['id']==row['from_step_id'] for s in scene['steps'])
   ref=idx['scene_chunks'][row['scene_id']]
   row['scene_chunk_sha256']=ref['sha256'];row['scene_chunk_path']=ref['path']
   path=ROOT/pathrel;projection={'scene':scene,'selected_owner':fid,'scene_refs':feature['scene_refs']}
  elif k=='recipe':
   fid=row['route'][1:].split('/recipe/')[0];feature,pathrel=feat[fid];i=row['recipe_index']
   source=feature['recipes'][i-1];current=next(x for x in book['features'] if x['id']==fid)['recipes'][i-1]
   assert source['title']==current['title']==row['source_title'] and i==int(row['route'].split('/recipe/')[1])
   assert feature.get('category')!='developer' and feature.get('audience')!='developer'
   path=ROOT/pathrel;projection=current
  elif k=='recording':
   rid=row['recording_id'];source=next(x for x in recordings['recordings'] if x['id']==rid)
   current=book['recordings_context']['recordings'][rid]
   assert source['title']==current['title']==row['source_title']
   path=ROOT/'manual/recordings.yaml';projection=current
   if rid=='masks-small-hours': row['runtime_requirement']='MosaicPlayer.pilot.audio resolves; verify visible recording context and paused state without calling play().'
  else: raise AssertionError(k)
  row['source_file']=str(path.relative_to(ROOT));row['source_file_sha256']=sha(path.read_bytes());row['projection_sha256']=sha(stable(projection))
  row['source_files']=[{'path':row['source_file'],'sha256':row['source_file_sha256']}]
  if k=='scene':
   row['source_files'].append({'path':'generated/reader-index.json#scene_chunks['+row['scene_id']+']','sha256':row['scene_chunk_sha256']})
  sourcefiles[row['source_file']]=row['source_file_sha256']
 except Exception as e: errors.append({'ledger_id':row['ledger_id'],'error':str(e)})
assert len(manifest['routes'])==425 and len({r['ledger_id'] for r in manifest['routes']})==425
assert {r['ledger_id'] for r in manifest['routes']}=={u['id'] for u in ledger['units']}
manifest.update({'schema':'reader-425-source-route-manifest-v3','book_sha256':sha((ROOT/'manual/generated/book.json').read_bytes()),'index_sha256':sha((ROOT/'manual/generated/reader-index.json').read_bytes()),'ledger_sha256':sha((ROOT/'manual/evidence/claude-review/final-425-reader-ledger-20261008-01/final-425-ledger.json').read_bytes()),'authority_sha256':manifest['authority_sha256'],'source_files':sourcefiles})
(OUT/'unit-route-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
counts=dict(Counter(r['unit_type'] for r in manifest['routes']))
report={'schema':'reader-425-current-route-preflight-v3','candidate_id':manifest['candidate_id'],'ledger_sha256':manifest['ledger_sha256'],'book_sha256':manifest['book_sha256'],'index_sha256':manifest['index_sha256'],'authority_sha256':manifest['authority_sha256'],'ledger_rows':425,'unique_ledger_ids':len({r['ledger_id'] for r in manifest['routes']}),'public_route_mappings':len(manifest['routes']),'unique_routes':len({r['route'] for r in manifest['routes']}),'unit_family_counts':counts,'source_projection_errors':errors,'source_file_hashes':sourcefiles,'browser_execution':'pending actual browser route gate','masks_small_hours':'explicit route mapping; browser must verify recording workspace and paused pilot audio without calling play().'}
(OUT/'preflight-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'counts':counts,'ids':report['unique_ledger_ids'],'routes':report['unique_routes'],'source_errors':len(errors),'first_errors':errors[:8],'source_files':len(sourcefiles)},indent=2))


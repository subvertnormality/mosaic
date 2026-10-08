import json,re
from pathlib import Path
OUT=Path('/mnt/c/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6/reader-425-route-gate-source-20261008-01')
ROOT=Path('/home/andy/mosaic-manual-1.4.0')
m=json.loads((OUT/'unit-route-manifest.json').read_text())
book=json.loads((ROOT/'manual/generated/book.json').read_text())
features={f['id']:f for f in book['features']}
aliases=[]
for r in m['routes']:
 r['expected_final_route']=r['route']
 if r['unit_type']=='lesson':
  fid=r['route'][1:].split('/lesson/')[0]
  owner=features[fid]
  link=next((x for x in owner.get('lesson_context_links',[]) if x.get('lesson_id')==r['contract_id']),None)
  if link:
   target=link['canonical_route']
   if not target.startswith('#'):target='#'+target
   target_fid=target[1:].split('/')[0]
   r['expected_final_route']=target
   r['expected_visible_owner_title']=features[target_fid]['title']
   r['context_handoff']=link
   aliases.append({'ledger_id':r['ledger_id'],'requested_route':r['route'],'expected_final_route':target,'owner_title':r['expected_visible_owner_title'],'kind':'lesson-context-link'})
 if r['unit_type']=='recipe':
  fid=r['route'][1:].split('/recipe/')[0]
  recipe=features[fid]['recipes'][r['recipe_index']-1]
  match=re.search(r'(?:Complete canonical walkthrough|Full walkthrough):\s*\[[^\]]+\]\(#([a-z0-9-]+/recipe/[1-9]\d*)\)',recipe.get('text',''),re.I)
  if match:
   target='#'+match.group(1)
   tfid,_,num=target[1:].partition('/recipe/')
   assert features[tfid]['recipes'][int(num)-1]['title']==r['source_title']
   r['expected_final_route']=target
   r['expected_visible_owner_title']=features[tfid]['title']
   r['canonical_recipe']={'feature_id':tfid,'recipe_index':int(num)}
   aliases.append({'ledger_id':r['ledger_id'],'requested_route':r['route'],'expected_final_route':target,'owner_title':r['expected_visible_owner_title'],'kind':'recipe-full-walkthrough'})
 if r['unit_type']=='recording':
  ctx=book['recordings_context']['recordings'][r['recording_id']]
  r['expected_purpose']=ctx['purpose'];r['expected_visible_text']=ctx['starting_point'];r['expected_build_steps']=ctx['build_steps']
m['route_handoffs']=aliases
m['route_handoff_counts']={'lesson_context_links':sum(x['kind']=='lesson-context-link' for x in aliases),'recipe_full_walkthroughs':sum(x['kind']=='recipe-full-walkthrough' for x in aliases)}
(OUT/'unit-route-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
p=OUT/'preflight-report.json';d=json.loads(p.read_text());d['route_handoff_counts']=m['route_handoff_counts'];d['route_handoffs']=aliases;d['browser_execution']='baseline run completed; candidate harness corrected for numeric scene-option, markdown list markers, recording expectations, and documented canonical handoffs; rerun pending';p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'handoff_counts':m['route_handoff_counts'],'handoffs':aliases},indent=2))


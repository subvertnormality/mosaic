import json, hashlib, pathlib, collections
root=pathlib.Path('/home/andy/mosaic-manual-1.4.0')
folder=pathlib.Path('/mnt/c/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6/reader-425-ledger-closure-candidate-20261008-01')
c=json.loads((folder/'final-425-ledger-closure-candidate.json').read_bytes())
b=json.loads((root/'manual/evidence/claude-review/final-425-reader-ledger-20261008-01/final-425-ledger.json').read_bytes())
basepath=root/'manual/evidence/claude-review/final-reader-rechecks-20261008-01/source19-course-crossref-score-refresh-20261008-01/ROOT-POSTSTYLE-PUBLIC-425-CANDIDATE-v07.json'
if not basepath.exists():
 matches=list(root.glob('manual/evidence/**/fe378-baseline-425-ledger.json')); assert len(matches)==1, matches
 basepath=matches[0]
raw=basepath.read_bytes(); assert hashlib.sha256(raw).hexdigest()=='fe378689a917dd0eedc2f77e13588bd9b6faba11b66dfc3d6e948dc78c1255f2'
h=json.loads(raw)
u={x['id']:x for x in c['units']}; bu={x['id']:x for x in b['units']}; hu={x['id']:x for x in h['units']}
a=c['current_425_row_adjudication']['rows']; assert len(a)==425 and set(u)==set(x['id'] for x in a)==set(bu)
assert u==bu
historic=[x['id'] for x in a if x['score_lineage']['status']=='carried_unchanged_existing_ledger_row']; assert len(historic)==387
assert all(u[i]==hu[i] for i in historic)
bad=[]; checked=set()
for row in a:
 for f in row['source']['source_files']:
  if f['path'] in checked: continue
  checked.add(f['path']); path=root/f['path']
  if f['path'].startswith('generated/reader-index.json#scene_chunks['):
   sid=f['path'].split('[',1)[1][:-1]; idx=json.loads((root/'manual/generated/reader-index.json').read_bytes()); ref=idx['scene_chunks'][sid]; assert ref['sha256']==f['sha256']; path=root/'manual/generated'/ref['path']
  if hashlib.sha256(path.read_bytes()).hexdigest()!=f['sha256']: bad.append(f['path'])
assert not bad,bad
for x in u.values(): assert len(x['scores'])==10 and min(x['scores'].values())>=8
assert c['publication_qualified'] is False
print(json.dumps({'units':len(u),'unit_objects_unchanged':True,'historic_objects_exact':len(historic),'source_files_pinned':len(checked),'source_mismatches':bad,'threshold':'all425/all10>=8','publication':False}))


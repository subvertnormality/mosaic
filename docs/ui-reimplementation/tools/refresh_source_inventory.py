"""Rebase reviewed UI source references while preserving the immutable legacy ledger.

This does not approve new behaviour: --review must pin each exact current file
and explain its reviewed meaning. Changed branch bodies fail unless an exact behavior replacement has a separate
semantic review with immutable original-body and dependency identities, or the
explicit algorithm extraction preserves the original guarded enter/leave actions.
"""
import argparse, copy, difflib, hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from validate import manual_slices, manual_source_text
REG=re.compile(r'press:register(?:_pre|_post|_dual|_long)?\s*\(')
def digest(b):return hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest()
def refresh(baseline,review):
 old=json.loads(baseline.read_text());out=copy.deepcopy(old);receipt={'baseline_sha256':digest(baseline.read_bytes()),'files':{},'registrations':[],'branches':[],'controllers':[]}
 lines={};maps={}
 retired=review.get('retired_generated_files',{})
 for path,item in retired.items():
  assert path.startswith('manual/features/scenes-') and path.endswith('.yaml') and '..' not in Path(path).parts, 'invalid retired generated path '+path
  assert path not in review['files'] and not (REPO/path).exists(), 'retired generated source still active '+path
  assert item.get('meaning') and digest(Path(item['archive']).read_bytes())==item['sha256'], 'retired generated archive identity '+path
  if path in old['files']:assert old['files'][path]==item['sha256'], 'retired baseline source identity '+path
  assert all(u['source']!=path for u in old['grid_registrations']+old['controller_units']), 'retired executable owner '+path
  out['files'].pop(path,None)
 if retired:receipt['retired_generated_files']=copy.deepcopy(retired)
 for path,item in review['files'].items():
  current=(REPO/path).read_bytes();assert digest(current)==item['sha256'], 'unreviewed source bytes '+path
  assert item.get('meaning'), 'missing semantic review '+path
  out['files'][path]=item['sha256'];receipt['files'][path]=item
  if path in old['files']:
   before=subprocess.check_output(['git','show',old['head']+':'+path],cwd=str(REPO))
   assert digest(before)==old['files'][path], 'historical source does not match ledger '+path
   a,b=before.decode().splitlines(),current.decode().splitlines();lines[path]=(a,b)
   maps[path]={x+1:y+1 for i,j,n in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_matching_blocks() for x,y in zip(range(i,i+n),range(j,j+n))}
 assert set(old['files'])<=set(review['files'])|set(retired), 'missing reviewed source'
 for u in out['grid_registrations']:
  a,b=lines[u['source']];oldregs=list(REG.finditer('\n'.join(a)));newregs=list(REG.finditer('\n'.join(b)))
  assert len(oldregs)==len(newregs), 'callback inventory changed '+u['source']
  o,n=oldregs[u['ordinal']-1],newregs[u['ordinal']-1];assert o.group()==n.group(), 'callback kind changed '+u['id']
  oldline=u['line'];u['line']='\n'.join(b).count('\n',0,n.start())+1
  upper='\n'.join(b).count('\n',0,newregs[u['ordinal']].start())+1 if u['ordinal']<len(newregs) else len(b)+1
  receipt['registrations'].append({'id':u['id'],'old_line':oldline,'line':u['line'],'kind':n.group()})
  for branch in u['branches']:
   lo,hi=map(int,branch['lines'].split('-'));m=maps[u['source']];prior=branch['lines'];supplement=None
   replacement=review.get('branch_transformations',{}).get(branch['id'])
   if replacement:
    assert replacement.get('meaning'), 'replacement semantic review '+branch['id']
    assert replacement.get('source')==u['source'], 'replacement source identity '+branch['id']
    assert digest('\n'.join(a[lo-1:hi]).encode())==replacement.get('old_sha256'), 'historical branch replacement identity '+branch['id']
    assert replacement.get('dependencies'), 'replacement dependency identity '+branch['id']
    for path,expected in replacement['dependencies'].items():
     assert path in review['files'] and review['files'][path]['sha256']==expected and digest((REPO/path).read_bytes())==expected, 'replacement dependency identity '+branch['id']
    block=replacement['replacement'].splitlines();starts=[k for k in range(len(b)-len(block)+1) if b[k:k+len(block)]==block]
    assert len(starts)==1, 'replacement exact source block '+branch['id']
    x,y=starts[0]+1,starts[0]+len(block)
    mode='explicit reviewed behavior replacement: '+replacement['meaning']
    branch['reviewed_behavior_replacement']={'old_sha256':replacement['old_sha256'],'dependencies':replacement['dependencies']}
   elif lo in m and hi in m:
    x,y=m[lo],m[hi];tokens=[v.strip() for v in a[lo-1:hi] if v.strip()];now=iter(v.strip() for v in b[x-1:y] if v.strip())
    assert all(any(v==token for v in now) for token in tokens), 'branch body changed '+branch['id']
    permitted={
     'channel_edit_page.08.trig_merge_all':'shape_in_use(target_channel, "trig")',
     'channel_edit_page.09.note_merge_pattern_wraps_to_average':'shape_in_use(target_channel, "note")',
     'channel_edit_page.10.velocity_merge_pattern_wraps_to_average':'shape_in_use(target_channel, "velocity")',
     'channel_edit_page.14.note_pattern_priority':'shape_in_use(target_channel, "note")',
     'channel_edit_page.14.velocity_pattern_priority':'shape_in_use(target_channel, "velocity")',
     'channel_edit_page.14.length_pattern_priority':'shape_in_use(target_channel, "length")'}
    newer=[v.strip() for v in b[x-1:y] if v.strip()]
    additions=[newer[k] for op,aa,zz,yy,qq in difflib.SequenceMatcher(a=tokens,b=newer,autojunk=False).get_opcodes() if op=='insert' for k in range(yy,qq)]
    assert all(v.startswith('--') or v==permitted.get(branch['id']) for v in additions), 'unreviewed branch addition '+branch['id']
    mode='original source lines retained in order; only comments or explicitly reviewed shape-in-use tooltip insertion'

   else:
    assert branch['id'] in {'trigger_edit_page.05.select_algorithm','trigger_edit_page.05.enter_doctor','trigger_edit_page.05.leave_doctor'}, 'unreviewed branch extraction '+branch['id']
    call='algorithm_selected(previous, trigger_edit_page_algorithm_fader:get_value())'
    found=[k+1 for k,v in enumerate(b) if v.strip()==call];assert len(found)==1
    x=y=found[0]
    body=['if previous ~= 5 and selected == 5 and rhythm_doctor and rhythm_doctor.enter then rhythm_doctor:enter() end','if previous == 5 and selected ~= 5 and rhythm_doctor and rhythm_doctor.leave then rhythm_doctor:leave() end']
    assert all(sum(v.strip()==token for v in b)==1 for token in body), 'algorithm enter/leave semantics changed'
    start=b.index('local function algorithm_selected(previous, selected)')
    end=next(k for k in range(start+1,len(b)) if b[k].strip()=='end')
    expected=body+['trigger_edit_page.refresh_trigger_edit_page_ui()', 'tooltip:show(get_algorithm_name(selected) .. " selected")','load_paint_pattern()']
    assert [v.strip() for v in b[start+1:end] if v.strip()]==expected, 'algorithm helper body changed'

    supplement=[k+1 for k,v in enumerate(b) if v.strip() in body]
    branch['implementation_lines']=str(min(supplement))+'-'+str(max(supplement))
    mode='callback invokes extracted helper with original guarded Doctor enter/leave actions'
   assert u['line']<=x<=y<upper, 'mapped branch outside actual callback '+branch['id']
   branch['lines']=str(x)+'-'+str(y);receipt['branches'].append({'id':branch['id'],'old_lines':prior,'lines':branch['lines'],'review':mode,'implementation_lines':branch.get('implementation_lines')})
 for u in out['controller_units']:
  prior=u['line'];assert prior in maps[u['source']], 'controller source anchor changed '+u['id']
  u['line']=maps[u['source']][prior];receipt['controllers'].append({'id':u['id'],'old_line':prior,'line':u['line']})
 byheading={s['heading']:s for s in old['manual_sections']};assert len(byheading)==len(old['manual_sections'])
 manual=manual_source_text(REPO,review.get('manual_source'),out['files'])
 heads,texts=manual_slices(manual);sections=[]
 if review.get('manual_source'):
  out['manual_source']=copy.deepcopy(review['manual_source']);receipt['manual_source']=copy.deepcopy(review['manual_source'])
 for head,text in zip(heads,texts):
  name=head[2]
  if name in byheading:s=copy.deepcopy(byheading.pop(name))
  else:
   s=copy.deepcopy(review['new_manual_sections'][name]);s['heading']=name
  s.update(line=manual.count('\n',0,head.start())+1,text=text,sha256=hashlib.sha256(text.encode()).hexdigest());sections.append(s)
 assert not byheading, 'historical manual heading disappeared'
 assert len({s['id'] for s in sections})==len(sections), 'manual identity collision'
 out.update(read_on=review['read_on'],head=review['head'],baseline='reviewed working-tree source',manual_sections=sections)
 out['source_review']={'baseline_inventory':str(baseline.relative_to(ROOT)),'baseline_sha256':receipt['baseline_sha256'],'review':review['identity'],'review_sha256':hashlib.sha256(json.dumps(review,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'method':'exact callback anchors, ordered retained branch source, explicitly checked helper extraction, exact current manual slices; historic IDs retained'}
 return out,receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--review',required=True,type=Path);p.add_argument('--check',action='store_true');args=p.parse_args()
 review=json.loads(args.review.read_text());baseline=ROOT/review['baseline_inventory'];out,receipt=refresh(baseline,review)
 text=json.dumps(out,indent=2,ensure_ascii=False)+'\n';target=ROOT/'source-inventory.json'
 if args.check:assert target.read_text()==text, 'current source inventory stale'
 else:target.write_text(text);(ROOT/'generated/source-review-receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
 print('reviewed source inventory',len(out['files']),'files',len(out['grid_registrations']),'callbacks',len(receipt['branches']),'branches',len(out['manual_sections']),'manual sections')

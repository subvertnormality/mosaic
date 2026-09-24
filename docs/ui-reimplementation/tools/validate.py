"""Validate the declared UI contract; does not certify the unimplemented application."""
import hashlib,itertools,json,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from model import initial,select

def read(name):return json.loads((ROOT/name).read_text(encoding='utf8'))
def validate(s=None,inventory=None,check_sources=True):
 s=s or read('spec.json');i=inventory or read('source-inventory.json');fixtures=read('fixtures.json');errors=[]
 def require(ok,message):
  if not ok:errors.append(message)
 require(s.get('format')=='mosaic-ui-contract','format')
 for k in ['screens','flows','providers','programs','input_algebra','effect_contracts','grid','migration','field_contracts']:require(k in s,'missing '+k)
 if errors:return errors
 for key,p in s['programs'].items():
  path=ROOT/p['file'];require(path.is_file(),'program missing '+key)
  if path.is_file():require(hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256'],'program fingerprint '+key)
 for sid,screen in s['screens'].items():
  require(screen['provider']in s['providers'],'unknown provider '+sid)
  require(screen['render']['program']in s['programs'],'unknown renderer '+sid)
  require(bool(screen['render']['specimens']),'missing specimens '+sid)
  for f in screen['render']['specimens']:require(f in fixtures and fixtures[f]['screen']==sid,'fixture '+sid+' '+f)
  require(bool(screen.get('entry_flow_ids')),'missing entry '+sid)
  for f in screen.get('entry_flow_ids',[]):require(f in s['flows'],'missing entry flow '+sid+' '+f)
 for edge in s.get('feature_action_edges',[]):
  require(edge['from']in s['screens']and edge['to']in s['screens'],'feature edge target')
 for owner,mapping in s.get('source_route_map',{}).items():
  for route,sid in mapping.items():require(sid in s['screens'],'source route '+owner+'.'+route)
 for case in s.get('acceptance_matrix',[]):
  for sid in case['screens']:require(sid in s['screens'],'acceptance screen '+case['id'])
  for mid in case['manual']:require(mid in {m['id']for m in i['manual_sections']},'acceptance manual '+case['id'])
 for fid,f in s['flows'].items():
  require(f['new']['screen']in s['screens'],'unknown target '+fid)
  for a in f['new'].get('alternatives',[]):require(a['screen']in s['screens'],'unknown alternative '+fid)
 for context,cells in s['grid']['contexts'].items():
  require(len(cells)==128,'grid count '+context)
  require({(c['x'],c['y'])for c in cells}==set(itertools.product(range(1,17),range(1,9))),'grid overlap/gap '+context)
 for collection in ['grid_registrations','controller_units']:
  ids=[u['id']for u in i[collection]];require(len(ids)==len(set(ids)),'duplicate source identity '+collection)
  for u in i[collection]:
   require(bool(u.get('replacement_flows')),'unmapped '+u['id'])
   for f in u.get('replacement_flows',[]):require(f in s['flows'],'missing replacement '+u['id'])
 for section in i['manual_sections']:
  require(hashlib.sha256(section['text'].encode()).hexdigest()==section['sha256'],'manual section digest '+section['id'])
  for sid in section['screens']:require(sid in s['screens'],'manual target '+section['id'])
 if check_sources:
  manual=(REPO/'README.md').read_text(encoding='utf8')
  heads=list(re.finditer(r'^(#{1,6}) (.+)$',manual,re.M))
  require(len(heads)==len(i['manual_sections']),'missing manual section')
  require([h[2]for h in heads]==[x['heading']for x in i['manual_sections']],'manual heading inventory')
  expected_regs=set()
  for path in i['files']:
   if not path.endswith('.lua'):continue
   source=(REPO/path).read_text(encoding='utf8')
   for ordinal,m in enumerate(re.finditer(r'press:register(?:_pre|_post|_dual|_long)?\s*\(',source),1):
    expected_regs.add((path,ordinal,source.count('\n',0,m.start())+1))
  require(expected_regs=={(x['source'],x['ordinal'],x['line'])for x in i['grid_registrations']},'grid registration inventory mismatch')
  for path,digest in i['files'].items():
   file=REPO/path;require(file.exists(),'missing source '+path)
   if file.exists():require(hashlib.sha256(file.read_bytes()).hexdigest()==digest,'source drift '+path)
 ids=[r['id']for r in s['input_algebra']['rules']];require(len(ids)==len(set(ids)),'duplicate rule')
 for r in s['input_algebra']['rules']:
  for op in r['effects']:require(op in s['effect_contracts'],'unknown effect '+op)
 # Representative of every screen, every event, and every Boolean ownership combination.
 # Guards are equality/membership only; each field-kind equivalence class is covered.
 failures=set()
 for sid,screen in s['screens'].items():
  for native,modal,held,shift,dirty in itertools.product([False,True],repeat=5):
   for kind in ['value','readonly','action','inspection','unavailable']:
    state=initial(sid,screen['context'] if screen['context']in s['contexts'] else 'Channel')
    state.update(native=native,modal=modal,held=held,shift=shift,dirty=dirty,field_kind=kind)
    for event in s['input_algebra']['events']:
     try:select(s,state,event)
     except (ValueError,KeyError)as e:failures.add(str(e))
 errors.extend(sorted(failures))
 return errors
if __name__=='__main__':
 errors=validate(check_sources='--skip-source-fingerprints'not in sys.argv)
 for error in errors:print('FAIL',error)
 print('FAIL'if errors else 'PASS','contract validation')
 sys.exit(bool(errors))

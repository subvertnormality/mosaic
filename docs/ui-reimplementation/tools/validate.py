"""Validate the declared UI contract; does not certify the unimplemented application."""
import hashlib,itertools,json,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from model import initial,select,contexts,matches,doctor_route
FIELD_ID=re.compile(r'^[a-z0-9_:<>]+$')
FILTERS={'all','selected','assigned_parameter_id_prefix'}
REQUIRES={None,'held','draft','pending_confirmation'}

def read(name):return json.loads((ROOT/name).read_text(encoding='utf8'))
def fingerprint(path):return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
def manual_slices(manual):
 heads=list(re.finditer(r'^(#{1,6}) (.+)$',manual,re.M))
 return heads,[manual[h.end():(heads[n+1].start()if n+1<len(heads)else len(manual))].strip()for n,h in enumerate(heads)]

def doctor_overlay_errors(s,check_sources=False):
 """grid.doctor_override must partition its declared region of the Trig grid with the adapter lane layout."""
 ov=s['grid'].get('doctor_override');errors=[]
 if not ov:return ['missing grid.doctor_override']
 cells=[(c['x'],c['y'])for c in ov['cells']]
 region={(x,y)for r in ov['region']for x in range(r['x'][0],r['x'][1]+1)for y in range(r['y'][0],r['y'][1]+1)}
 trig={(c['x'],c['y'])for c in s['grid']['contexts']['Trig']}
 if len(cells)!=len(set(cells)):errors.append('doctor overlay overlap')
 if set(cells)!=region:errors.append('doctor overlay gap/overflow')
 if not region<=trig:errors.append('doctor overlay outside Trig')
 if any(c['control']not in ov['controls']for c in ov['cells']):errors.append('doctor overlay unknown control')
 lay=ov['lane_layout'];lanes={c['index']:(c['x'],c['y'])for c in ov['cells']if c['control']=='doctor_lane'}
 if lay['max_lanes']!=lay['row_width']*len(lay['rows']):errors.append('doctor lane capacity')
 if sorted(lanes)!=list(range(1,lay['max_lanes']+1)):errors.append('doctor lane indices')
 elif any(lanes[i]!=(lay['origin_column']+(i-1)%lay['row_width'],lay['rows'][(i-1)//lay['row_width']])for i in lanes):errors.append('doctor lane layout')
 for control,cell in [('doctor_record',(1,2)),('doctor_reserved',(2,2))]:
  if [(c['x'],c['y'])for c in ov['cells']if c['control']==control]!=[cell]:errors.append('doctor '+control+' cell')
 if check_sources and (REPO/'lib/rhythm_doctor/ui_adapter.lua').is_file():
  ua=(REPO/'lib/rhythm_doctor/ui_adapter.lua').read_text(encoding='utf8')
  num=lambda k:int(re.search(r'Adapter\.'+k+r'\s*=\s*(\d+)',ua).group(1))
  rows=[int(v)for v in re.search(r'Adapter\.LANE_ROWS\s*=\s*\{([^}]*)\}',ua).group(1).split(',')]
  if (num('LANE_ORIGIN_COLUMN'),num('LANE_ROW_WIDTH'),rows)!=(lay['origin_column'],lay['row_width'],lay['rows']):errors.append('doctor lane layout drift from ui_adapter.lua')
 return errors

def doctor_route_errors(s):
 """doctor_routes partitions its domain and the doctor flows' alternatives resolve exactly as the table does."""
 table=s.get('doctor_routes');errors=[]
 if not table:return ['missing doctor_routes']
 keys=list(table['inputs']);domain=[dict(zip(keys,v))for v in itertools.product(*[table['inputs'][k]['values']for k in keys])]
 rows={r['id']:r for r in table['rows']}
 for r in table['rows']:
  if r['screen']not in s['screens']:errors.append('doctor_routes screen '+r['id'])
 for p in domain:
  if len([r for r in table['rows']if matches(r['when'],p)])!=1:errors.append('doctor_routes not a partition at '+str(p));break
 for fid,meta in table['flows'].items():
  f=s['flows'].get(fid)
  if f is None or f['new'].get('routes')!='doctor_routes':errors.append('doctor flow not table-derived '+fid);continue
  for o in meta['overrides']:
   if o['outcome']not in meta['outcomes']or not all(rows[x]['overridable']for x in o['rows']):errors.append('doctor override '+fid+' '+o['outcome'])
  for outcome in meta['outcomes']+[None]:
   bad=None
   for p in domain:
    q=dict(p,outcome=outcome)if outcome else p
    opts=sorted([a for a in f['new']['alternatives']if matches(a['when'],q)],key=lambda a:-a['priority'])
    got=opts[0]['screen']if opts else f['new']['screen']
    if(len(opts)>1 and opts[0]['priority']==opts[1]['priority'])or got!=doctor_route(s,q,fid):bad=q;break
   if bad:errors.append('doctor alternative drift '+fid+' '+str(bad))
 return errors
def validate(s=None,inventory=None,check_sources=True):
 s=s or read('spec.json');i=inventory or read('source-inventory.json');fixtures=read('fixtures.json');errors=[]
 def require(ok,message):
  if not ok:errors.append(message)
 require(s.get('format')=='mosaic-ui-contract','format')
 for k in ['screens','flows','providers','programs','input_algebra','effect_contracts','grid','migration','field_contracts']:require(k in s,'missing '+k)
 if errors:return errors
 for key,p in s['programs'].items():
  path=ROOT/p['file'];require(path.is_file(),'program missing '+key)
  if path.is_file():require(fingerprint(path)==p['sha256'],'program fingerprint '+key)
 lc=s.get('layout_contract',{}).get('families',{})
 for fam,g in lc.items():
  require('overflow_status' in g,'layout family without overflow_status '+fam)
  if fam.startswith('overview'):
   require('full_value_line' in g,'overview family without full_value_line '+fam)
   if 'full_value_line' in g:require(max(g['row_tops'])+g['slot_height']<=g['full_value_line'][1],'overview cells overlap full_value_line '+fam)
 for sid,screen in s['screens'].items():
  require(screen['provider']in s['providers'],'unknown provider '+sid)
  require(screen['render']['program']in s['programs'],'unknown renderer '+sid)
  require(bool(screen['render']['specimens']),'missing specimens '+sid)
  for f in screen['render']['specimens']:require(f in fixtures and fixtures[f]['screen']==sid,'fixture '+sid+' '+f)
  require(bool(screen.get('entry_flow_ids')),'missing entry '+sid)
  for f in screen.get('entry_flow_ids',[]):require(f in s['flows'],'missing entry flow '+sid+' '+f)
  require(screen['live_render']['layout']in lc,'undeclared layout '+sid)
 # Field identity: stable declared ids, never labels; repeated descriptors declare their key.
 repeat={}
 for name,contract in s['field_contracts'].items():
  rk=contract.get('repeat_key')if isinstance(contract,dict)else None
  if rk:
   for sid in rk['screens']:require(sid in s['screens'],'repeat key screen '+name+' '+sid);repeat.setdefault(sid,[]).append((re.compile(rk['pattern']),set(rk.get('fixed',[]))))
 for sid,screen in s['screens'].items():
  ids=[f['id']for f in screen.get('fields',[])]
  for fid in sorted({x for x in ids if ids.count(x)>1}):require(False,'duplicate field id '+sid+'.'+fid)
  for f in screen.get('fields',[]):
   require(bool(FIELD_ID.match(str(f['id']))),'field id syntax '+sid+'.'+str(f['id']))
   b=f.get('binding',{})
   if 'field'in b:require(b['field']==f['id'],'binding.field != id '+sid+'.'+f['id'])
   for pattern,fixed in repeat.get(sid,[]):require(bool(pattern.match(f['id']))or f['id']in fixed,'repeat key '+sid+' '+f['id'])
   if 'slot'in f:require(sid in repeat,'undeclared repeat key '+sid)
 viewer=s['field_contracts'].get('viewer',{})
 for sid in viewer.get('screens',{}):
  f=next((x for x in s['screens'].get(sid,{}).get('fields',[])if x['id']=='view_channel'),None)
  require(f is not None and f.get('kind')=='inspection'and f['binding'].get('target')=='view_state','viewer field '+sid)
 # Route maps: flat {old_route: screen} for controller routes, or a descriptor_filter view table.
 srm=s.get('source_route_map',{})
 def routes(owner):
  m=srm.get(owner)
  if m is None:return None
  return set(m['views'])if m.get('route_kind')=='descriptor_filter'else set(m)
 for owner,mapping in srm.items():
  require(owner in s['providers'],'source route owner '+owner)
  if mapping.get('route_kind')=='descriptor_filter':
   require(isinstance(mapping.get('descriptor_set'),str),'descriptor_set '+owner)
   for sid,v in mapping.get('views',{}).items():
    require(sid in s['screens']and s['screens'][sid]['provider']==owner,'source view '+owner+'.'+sid)
    require(v.get('filter')in FILTERS,'source view filter '+owner+'.'+sid)
    require(v.get('requires',None)in REQUIRES,'source view requires '+owner+'.'+sid)
   continue
  for route,sid in mapping.items():require(sid in s['screens'],'source route '+owner+'.'+route)
 for sid,screen in s['screens'].items():
  r=routes(screen['provider']);er=screen.get('existing_route')
  if r is None:continue
  require(er in r or(er=='snapshot:'+sid and sid in s.get('visual_variants',{})),'existing_route not in source_route_map '+sid+' '+str(er))
  require(screen['binding'].get('route')==er and screen['binding'].get('provider')==screen['provider'],'binding route/provider '+sid)
 # Feature action edges: stable ids, known effects, route edges agree with the owner's route map.
 targets={}
 for edge in s.get('feature_action_edges',[]):
  tag=edge['from']+'.'+str(edge.get('field_id'))
  require(edge['from']in s['screens']and edge['to']in s['screens'],'feature edge target '+tag)
  if edge['from']not in s['screens']or edge['to']not in s['screens']:continue
  require(bool(FIELD_ID.match(str(edge.get('field_id','')))),'feature edge field_id '+tag)
  require(targets.setdefault(tag,edge['to'])==edge['to'],'feature edge ambiguous '+tag)
  for op in edge['effects']:require(op in s['effect_contracts'],'unknown edge effect '+tag+' '+op)
  owner=s['screens'][edge['from']]['provider'];m=srm.get(owner,{})
  if edge.get('kind')=='route':
   require(m.get(edge['old_owner_route'])==edge['from'],'feature edge owner route '+tag)
   require(m.get(edge['old_action_route'])==edge['to'],'feature edge action route '+tag)
   require('owner.open_translated_route'in edge['effects'],'feature edge open '+tag)
  elif edge.get('kind')=='cross_owner_link':
   require(edge['old_action_route']not in m,'cross-owner link in source route map '+tag)
   require(s['screens'][edge['to']]['provider']==edge.get('target_owner')!=owner,'cross-owner link owner '+tag)
   require('owner.enter_root'in edge['effects']and'owner.cancel_unapplied'in edge['effects'],'cross-owner link effects '+tag)
   require('return.push'not in edge['effects']and'owner.open_translated_route'not in edge['effects'],'cross-owner link pushes '+tag)
  else:require(False,'feature edge kind '+tag)
 for case in s.get('acceptance_matrix',[]):
  for sid in case['screens']:require(sid in s['screens'],'acceptance screen '+case['id'])
  for mid in case['manual']:require(mid in {m['id']for m in i['manual_sections']},'acceptance manual '+case['id'])
 for fid,f in s['flows'].items():
  require(f['new']['screen']in s['screens'],'unknown target '+fid)
  for a in f['new'].get('alternatives',[]):require(a['screen']in s['screens'],'unknown alternative '+fid)
 for context,cells in s['grid']['contexts'].items():
  require(len(cells)==128,'grid count '+context)
  require({(c['x'],c['y'])for c in cells}==set(itertools.product(range(1,17),range(1,9))),'grid overlap/gap '+context)
 errors.extend(doctor_overlay_errors(s,check_sources));errors.extend(doctor_route_errors(s))
 for collection in ['grid_registrations','controller_units']:
  ids=[u['id']for u in i[collection]];require(len(ids)==len(set(ids)),'duplicate source identity '+collection)
  for u in i[collection]:
   require(bool(u.get('replacement_flows')),'unmapped '+u['id'])
   for f in u.get('replacement_flows',[]):require(f in s['flows'],'missing replacement '+u['id'])
 # Branch ledger: every registration lists its independent behavioural branches.
 branch_ids,case_ids=set(),set()
 for u in i['grid_registrations']:
  bs=u.get('branches');require(isinstance(bs,list)and bool(bs),'no branches '+u['id'])
  for b in bs if isinstance(bs,list)else[]:
   bid=str(b.get('id'))
   for k in['id','guard','edge','lines','outcome','case']:require(isinstance(b.get(k),str)and bool(b[k]),'branch field '+k+' '+u['id']+' '+bid)
   require(b.get('edge')in{'press','release','long','dual','pre','post'},'branch edge '+bid)
   require(bool(re.fullmatch(r'\d+-\d+',str(b.get('lines')))),'branch lines '+bid)
   require(bid not in branch_ids,'duplicate branch '+bid);branch_ids.add(bid)
   require(b.get('case')not in case_ids,'duplicate branch case '+bid);case_ids.add(b.get('case'))
   o=b.get('outcome');retain=o=='retain_without_navigation'
   require(retain or o in s['flows'],'unknown branch outcome '+bid)
   require(retain or o in u.get('replacement_flows',[]),'branch outcome outside replacement_flows '+bid)
 for section in i['manual_sections']:
  require(hashlib.sha256(section['text'].encode()).hexdigest()==section['sha256'],'manual section digest '+section['id'])
  for sid in section['screens']:require(sid in s['screens'],'manual target '+section['id'])
 if check_sources:
  manual=(REPO/'README.md').read_text(encoding='utf8').replace('\r\n','\n')
  heads,texts=manual_slices(manual)
  # Each manual section is checked against the README slice itself, not the inventory's stored copy.
  for section,text in zip(i['manual_sections'],texts):require(hashlib.sha256(text.encode()).hexdigest()==section['sha256'],'manual section drift '+section['id'])
  require(len(heads)==len(i['manual_sections']),'missing manual section')
  require([h[2]for h in heads]==[x['heading']for x in i['manual_sections']],'manual heading inventory')
  expected_regs=set()
  for path in i['files']:
   if not path.endswith('.lua'):continue
   source=(REPO/path).read_text(encoding='utf8')
   for ordinal,m in enumerate(re.finditer(r'press:register(?:_pre|_post|_dual|_long)?\s*\(',source),1):
    expected_regs.add((path,ordinal,source.count('\n',0,m.start())+1))
  require(expected_regs=={(x['source'],x['ordinal'],x['line'])for x in i['grid_registrations']},'grid registration inventory mismatch')
  # Branch line ranges must sit inside their callback: from the registration line to before the next one.
  spans={}
  for path in {x['source']for x in i['grid_registrations']}:
   lines=sorted(l for p,_,l in expected_regs if p==path);total=(REPO/path).read_text(encoding='utf8').count('\n')+1
   for a,b in zip(lines,lines[1:]+[total+1]):spans[(path,a)]=(a,b)
  for x in i['grid_registrations']:
   lo,hi=spans.get((x['source'],x['line']),(0,0))
   for b in x.get('branches')or[]:
    m=re.fullmatch(r'(\d+)-(\d+)',str(b.get('lines')))
    require(bool(m)and lo<=int(m[1])<=int(m[2])<hi,'branch lines outside callback '+str(b.get('id')))
  for path,digest in i['files'].items():
   file=REPO/path;require(file.exists(),'missing source '+path)
   if file.exists():require(fingerprint(file)==i['files'][path],'source drift '+path)
 # Router: registry contexts, hold policy, atomic page flows, single tasks authority.
 for sid,screen in s['screens'].items():
  c=screen['context'];cs=[c]if isinstance(c,str)else c
  require(bool(cs)and all(x in s['contexts']for x in cs),'screen context '+sid)
  require(screen.get('hold_policy')in s['state_schema']['hold_policy'],'hold_policy '+sid)
 for fid,f in s['flows'].items():
  n=f['new']
  if f['kind']=='grid_outcome'and n['navigation']=='replace'and n.get('invalidates_return'):require('context'in n,'page flow context '+fid)
  for a in [n]+n.get('alternatives',[]):
   ctx=a.get('context',n.get('context'))
   if ctx and a.get('navigation',n['navigation'])!='retain':require(ctx in contexts(s,a['screen']),'flow context '+fid+' '+a['screen'])
  if n.get('context')!=None and any(a.get('context',n['context'])!=n['context']for a in n.get('alternatives',[])):require(n.get('invalidates_return')is True,'context change without invalidation '+fid)
 t=s['tasks']
 for ctx in s['contexts']:
  nav=t['navigators'].get(ctx);require(nav in t['rows']and ctx in contexts(s,nav),'navigator '+ctx)
 for nav,rows in t['rows'].items():
  require(nav in s['screens']and s['screens'][nav]['profile']=='tasks','navigator screen '+nav)
  if nav not in s['screens']:continue
  require([(f['id'],f['label'])for f in s['screens'][nav]['fields']]==[(r['id'],r['label'])for r in rows],'navigator rows '+nav)
  require(nav in t['navigators'].values()or any(r.get('screen')==nav for rr in t['rows'].values()for r in rr),'unreachable navigator '+nav)
  for r in rows:
   if 'native'in r:require(s['screens'].get(r['native'],{}).get('profile')=='native','native row '+nav+'.'+r['id']);continue
   for ctx in r.get('contexts',contexts(s,nav)):
    dest=r['screen'][ctx]if isinstance(r['screen'],dict)else r['screen']
    require(dest in s['screens']and ctx in contexts(s,dest),'task destination '+nav+'.'+r['id']+' '+ctx)
    require(s['flows'].get('NAV.'+ctx+'.'+dest,{}).get('new',{}).get('screen')==dest,'task flow NAV.'+ctx+'.'+dest)
 ids=[r['id']for r in s['input_algebra']['rules']];require(len(ids)==len(set(ids)),'duplicate rule')
 for r in s['input_algebra']['rules']:
  for op in r['effects']:require(op in s['effect_contracts'],'unknown effect '+op)
 # Representative of every screen, every event, and every Boolean ownership combination.
 # Guards are equality/membership only; each field-kind equivalence class is covered.
 failures=set()
 for sid,screen in s['screens'].items():
  for context,native,modal,held,shift,dirty in itertools.product(contexts(s,sid),*[[False,True]]*5):
   for kind in ['value','readonly','action','inspection','unavailable']:
    state=initial(sid,context)
    state.update(native=native,modal=modal,held=held,shift=shift,dirty=dirty,field_kind=kind)
    for event in s['input_algebra']['events']:
     try:select(s,state,event)
     except (ValueError,KeyError)as e:failures.add(str(e))
 errors.extend(sorted(failures))
 # The runtime Lua copy of the routing data must be regenerated with the spec.
 runtime=REPO/'lib/ui_spec_data.lua'
 if runtime.is_file():
  import export_runtime
  require(runtime.read_text(encoding='utf8')==export_runtime.build(),'lib/ui_spec_data.lua is stale')
 traces=ROOT/'generated/router-traces.json'
 if traces.is_file():
  import router_traces
  require(traces.read_text(encoding='utf8')==router_traces.build(),'generated/router-traces.json is stale')
 return errors
if __name__=='__main__':
 errors=validate(check_sources='--skip-source-fingerprints'not in sys.argv)
 for error in errors:print('FAIL',error)
 print('FAIL'if errors else 'PASS','contract validation')
 sys.exit(bool(errors))

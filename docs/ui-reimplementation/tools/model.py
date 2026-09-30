"""Executable presentation model. It selects effects; never runs musical actions."""
from copy import deepcopy
FRAME=['screen','field_id','target','generation']

def matches(guard,state):
 return all(state.get(k) in v if isinstance(v,list) else state.get(k)==v for k,v in guard.items())

def contexts(spec,sid):
 c=spec['screens'][sid]['context'];return [c] if isinstance(c,str) else list(c)

def view(spec,state):
 x=spec['screens'][state['screen']];return dict(state,profile=x['profile'],provider=x['provider'],hold_policy=x['hold_policy'])

def select(spec,state,event):
 state=view(spec,state)
 rules=[r for r in spec['input_algebra']['rules']if r['event']==event and matches(r['when'],state)]
 if not rules:raise ValueError('unhandled input '+event)
 top=max(r['priority']for r in rules);rules=[r for r in rules if r['priority']==top]
 if len(rules)!=1:raise ValueError('ambiguous rules '+str([r['id']for r in rules]))
 return rules[0]

def field_kind(spec,screen,field_id):
 sc=spec['screens'][screen];f=next((x for x in sc['fields']if x['id']==field_id),None)
 if f is None:return 'unavailable'
 kind=f.get('kind','value')
 return 'readonly'if sc['profile']=='read_only'and kind not in('action','inspection')else kind

DOCTOR_KEYS=['doctor_state','modal_operation','draft','preview','playing']

def doctor_route(spec,payload,flow_id=None):
 """Resolve a Rhythm Doctor screen from spec.doctor_routes; fails loudly on an incomplete payload."""
 table=spec['doctor_routes'];missing=[k for k in DOCTOR_KEYS if k not in payload]
 if missing:raise ValueError('doctor payload missing '+','.join(missing))
 rows=[r for r in table['rows']if matches(r['when'],payload)]
 if len(rows)!=1:raise ValueError('doctor_routes rows '+str([r['id']for r in rows]))
 for o in table['flows'].get(flow_id,{}).get('overrides',[]):
  if payload.get('outcome')==o['outcome']and rows[0]['id']in o['rows']:return o['screen']
 return rows[0]['screen']

def doctor_lane_cells(spec,lanes):
 """Adapter:lane_cells() as declared by grid.doctor_override.lane_layout."""
 lay=spec['grid']['doctor_override']['lane_layout']
 return [{'lane':lane,'x':lay['origin_column']+i%lay['row_width'],'y':lay['rows'][i//lay['row_width']]}for i,lane in enumerate(lanes[:lay['max_lanes']])]

def doctor_lane_at(spec,lanes,x,y):
 return next((c['lane']for c in doctor_lane_cells(spec,lanes)if(c['x'],c['y'])==(x,y)),None)

def initial(screen='C01',context='Channel'):
 return dict(screen=screen,context=context,native=False,modal=False,held=False,shift=False,dirty=False,playing=False,family='masks',field_kind='value',field_id='trig',target={'channel':1,'song_slot':1,'step_set':[]},return_stack=[],generation=0)

def task_rows(spec,state,payload=None):
 v=dict(view(spec,state),**(payload or{}))
 return [r for r in spec['tasks']['rows'][state['screen']]if state['context']in r.get('contexts',[state['context']])and matches(r.get('visible_when',{}),v)]

def row_screen(row,context):
 return row['screen'][context]if isinstance(row['screen'],dict)else row['screen']

def step(spec,state,event,payload=None):
 payload=payload or{};s=deepcopy(state);r=select(spec,s,event);ops=[]
 family=lambda:'C02'if s['family']=='parameters'else'C01'
 primary=lambda:family()if s['context']=='Channel'else spec['contexts'][s['context']]
 push=lambda:s['return_stack'].append({k:deepcopy(s[k])for k in FRAME})
 def invalidate():s['return_stack']=[];s['generation']+=1
 queue=list(r['effects']);edge=None
 while queue:
  op=queue.pop(0)
  ops.append({'op':op,'target':deepcopy(s['target'])})
  if op=='owner.invoke_selected':
   # Static action edges: the selected stable field id picks the edge; its effects run in order.
   edge=next((e for e in spec.get('feature_action_edges',[])if e['from']==s['screen']and e.get('field_id')==s['field_id']),None)
   if edge:queue[:0]=edge['effects']
  elif op=='owner.open_translated_route':s['screen']=edge['to']
  elif op=='owner.enter_root':
   if not s['held']:s['screen']=edge['to'];s['return_stack']=[]
  elif op=='return.push':push()
  elif op=='return.invalidate':invalidate()
  elif op in ['return.parent','return.restore_if_generation_matches']:
   frames=[f for f in s['return_stack']if f['generation']==s['generation']]
   if frames:
    f=frames.pop();s.update({k:deepcopy(f[k])for k in ['screen','field_id','target']});s['return_stack']=frames
   elif spec['screens'][s['screen']]['profile']!='feature':s['screen']=primary()
  elif op=='scope.set_held':s['held']=True;s['target']['step_set']=list(payload.get('steps',[]))
  elif op=='scope.update_full_set':s['target']['step_set']=list(payload.get('steps',[]))
  elif op=='scope.clear':s['held']=False;s['target']['step_set']=[]
  elif op=='scope.restore_family':s['screen']=family()
  elif op=='scope.follow':
   if s['context']=='Channel'and spec['screens'][s['screen']]['hold_policy']=='follow_family':s['screen']=family()
  elif op=='family.switch_clamped':s['screen']='C02'if event=='E1+'else'C01';s['family']='parameters'if s['screen']=='C02'else'masks'
  elif op=='tasks.open':s['screen']=spec['tasks']['navigators'][s['context']]
  elif op=='tasks.enter_selected':
   rows={x['id']:x for x in task_rows(spec,s,payload)}
   if payload.get('task')not in rows or 'screen'not in rows[payload['task']]:raise ValueError('task not enterable '+str(payload.get('task')))
   s['screen']=row_screen(rows[payload['task']],s['context'])
   if s['screen']in ['C01','C02']:s['family']='parameters'if s['screen']=='C02'else'masks'
  elif op=='feature.return_then_tasks':
   root='M02'if spec['screens'][s['screen']]['provider']=='merge'else'H01'
   if s['dirty']or s['return_stack']or s['screen']!=root:s['dirty']=False;s['return_stack']=[];s['screen']=root
   else:s['screen']='N01'
  elif op=='owner.cancel_unapplied':s['dirty']=False
  elif op=='native.open':s['native']=True
  elif op=='native.close':s['native']=False
  elif op=='route.C07':s['screen']='C07'
  elif op=='outcome.follow':
   f=spec['flows'][payload['flow_id']]['new'];v=dict(view(spec,s),**payload)
   if f.get('routes')=='doctor_routes':doctor_route(spec,payload,payload['flow_id'])
   opts=sorted([a for a in f['alternatives']if matches(a['when'],v)],key=lambda a:a['priority'],reverse=True)
   if len(opts)>1 and opts[0]['priority']==opts[1]['priority']:raise ValueError('ambiguous outcome')
   a=opts[0]if opts else f;nav=a.get('navigation',f['navigation'])
   if f.get('invalidates_return'):s['dirty']=False;invalidate()
   if nav=='temporary'and not s['held']:push()
   if nav!='retain':
    s['context']=a.get('context',f.get('context',s['context']));s['screen']=a['screen']
    if 'target'in payload:s['target']=deepcopy(payload['target'])
  elif op=='owner.preserve_key_edge':
   if event in ['K1.down','K1.up']:s['shift']=event=='K1.down'
 # All other operations are adapter commands. Their musical result is deliberately not mocked.
 if s['context']not in contexts(spec,s['screen']):raise ValueError('context '+s['context']+' cannot show '+s['screen'])
 return s,ops,r['id']

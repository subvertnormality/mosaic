"""Executable presentation model. It selects effects; never runs musical actions."""
from copy import deepcopy

def matches(guard,state):
 return all(state.get(k) in v if isinstance(v,list) else state.get(k)==v for k,v in guard.items())

def select(spec,state,event):
 state=dict(state,profile=spec['screens'][state['screen']]['profile'])
 rules=[r for r in spec['input_algebra']['rules']if r['event']==event and matches(r['when'],state)]
 if not rules:raise ValueError('unhandled input '+event)
 top=max(r['priority']for r in rules);rules=[r for r in rules if r['priority']==top]
 if len(rules)!=1:raise ValueError('ambiguous rules '+str([r['id']for r in rules]))
 return rules[0]

def initial(screen='C01',context='Channel'):
 return dict(screen=screen,context=context,native=False,modal=False,held=False,shift=False,dirty=False,playing=False,family='masks',field_kind='value',field_id='trig',target={'channel':1,'song_slot':1,'step_set':[]},return_stack=[],generation=0)

def step(spec,state,event,payload=None):
 payload=payload or{};s=deepcopy(state);r=select(spec,s,event);ops=[]
 primary=lambda:('C02'if s['family']=='parameters'else'C01')if s['context']=='Channel'else spec['contexts'][s['context']]
 for op in r['effects']:
  ops.append({'op':op,'target':deepcopy(s['target'])})
  if op=='return.push':s['return_stack'].append({k:deepcopy(s[k])for k in ['screen','field_id','target','generation']})
  elif op=='return.invalidate':s['return_stack']=[];s['generation']+=1
  elif op in ['return.parent','return.restore_if_generation_matches']:
   frames=[f for f in s['return_stack']if f['generation']==s['generation']]
   if frames:
    f=frames.pop();s.update({k:deepcopy(f[k])for k in ['screen','field_id','target']});s['return_stack']=frames
   else:s['screen']=primary()
  elif op=='scope.set_held':s['held']=True;s['target']['step_set']=list(payload.get('steps',[]))
  elif op=='scope.update_full_set':s['target']['step_set']=list(payload.get('steps',[]))
  elif op=='scope.clear':s['held']=False;s['target']['step_set']=[]
  elif op in ['scope.restore_family','scope.follow']:
   if s['context']=='Channel':s['screen']='C02'if s['family']=='parameters'else'C01'
  elif op=='family.navigate':
   s['screen']={'C01':{'E1-':'C01','E1+':'C02'},'C02':{'E1-':'C01','E1+':'N01'}}[s['screen']][event]
   if s['screen']in ['C01','C02']:s['family']='parameters'if s['screen']=='C02'else'masks'
  elif op=='family.switch_clamped':s['screen']='C02'if event=='E1+'else'C01';s['family']='parameters'if s['screen']=='C02'else'masks'
  elif op=='tasks.channel_exit_or_clamp':s['screen']='C02'if event=='E1-'else'N01'
  elif op=='tasks.open':s['screen']={'Channel':'N01','Scale':'N02','Trig':'N03','Note':'N03','Velocity':'N03','Song':'N05'}[s['context']]
  elif op=='tasks.enter_selected':
   dest=payload['task'];assert dest in spec['tasks'][s['context']];s['screen']=dest
  elif op=='feature.return_then_tasks':
   root='M02'if spec['screens'][s['screen']]['provider']=='merge'else'H01'
   if s['dirty']or s['return_stack']or s['screen']!=root:s['dirty']=False;s['return_stack']=[];s['screen']=root
   else:s['screen']='N01'
  elif op=='owner.cancel_unapplied':s['dirty']=False
  elif op=='native.open':s['native']=True
  elif op=='native.close':s['native']=False
  elif op=='route.C07':s['screen']='C07'
  elif op=='context.follow_primary':s['context']=payload['context'];s['target']=deepcopy(payload.get('target',s['target']));s['screen']=primary()
  elif op=='outcome.follow':
   f=spec['flows'][payload['flow_id']]['new']
   if f['navigation']=='temporary'and not s['held']:
    s['return_stack'].append({k:deepcopy(s[k])for k in ['screen','field_id','target','generation']})
   if f.get('invalidates_return'):
    s['return_stack']=[];s['generation']+=1
   if f['navigation']!='retain':
    opts=[a for a in f['alternatives']if matches(a['when'],payload)]
    opts=sorted(opts,key=lambda a:a['priority'],reverse=True)
    if len(opts)>1 and opts[0]['priority']==opts[1]['priority']:raise ValueError('ambiguous outcome')
    s['screen']=opts[0]['screen']if opts else f['screen']
    if 'target'in payload:s['target']=deepcopy(payload['target'])
  elif op=='owner.preserve_key_edge':
   if event in ['K1.down','K1.up']:s['shift']=event=='K1.down'
 # All other operations are adapter commands. Their musical result is deliberately not mocked.
 return s,ops,r['id']

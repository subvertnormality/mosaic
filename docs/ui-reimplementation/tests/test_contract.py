import json,sys,unittest
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from model import initial,step,select,contexts,task_rows,row_screen,field_kind
from validate import read,validate
S=read('spec.json')
def run(state,*events):
 for e in events:state,_,_=step(S,state,*e)if isinstance(e,tuple)else step(S,state,e)
 return state
class PresentationContract(unittest.TestCase):
 def test_native_has_exclusive_ownership(self):
  for event in ['E1+','E2-','E3+','K2.down','K3.down']:
   state=initial();state.update(native=True,modal=True,held=True)
   after,ops,_=step(S,state,event);self.assertEqual([o['op']for o in ops],['native.dispatch'])
 def test_channel_family_edges(self):
  state=initial()
  for ev,dest in [('E1-','C01'),('E1+','C02'),('E1+','N01'),('E1+','N01'),('E1-','C02'),('E1-','C01')]:
   state,_,_=step(S,state,ev);self.assertEqual(state['screen'],dest)
 def test_readonly_never_edits(self):
  for sid,screen in S['screens'].items():
   if screen['profile']=='read_only':
    state=initial(sid,contexts(S,sid)[0]);_,ops,_=step(S,state,'E3+');self.assertEqual([o['op']for o in ops],['noop'])
 def test_held_steps_beat_confirmation_and_shift_clear(self):
  state=initial('H17');state.update(modal=True,shift=True,dirty=True)
  state,ops,rid=step(S,state,'hold.begin',{'steps':[2,17,64]})
  self.assertEqual(rid,'hold.begin');self.assertEqual(state['screen'],'C01');self.assertTrue(state['dirty'])
  after,ops,_=step(S,state,'K2.down');self.assertEqual(after['screen'],'C01');self.assertFalse(after['dirty'])
  self.assertEqual(ops[0]['op'],'owner.cancel_unapplied');self.assertEqual(ops[-1]['op'],'family.clear');self.assertEqual(ops[-1]['target']['step_set'],[2,17,64])
 def test_parameter_slide_never_applies_feature(self):
  state=initial('M03');state.update(dirty=True,family='parameters')
  state=run(state,('hold.begin',{'steps':[7]}));self.assertEqual(state['screen'],'C02')
  after,ops,_=step(S,state,'K3.down');self.assertEqual(after['screen'],'C02');self.assertFalse(after['dirty']);self.assertEqual(ops[-1]['op'],'family.slide_if_parameters');self.assertEqual(ops[-1]['target']['step_set'],[7])
 def test_hold_returns_to_parent_on_every_channel_edit_screen(self):
  for sid in ['M02','H01','C04','C05','C03']:
   state=initial(sid);state=run(state,('hold.begin',{'steps':[5]}),('grid.outcome',{'flow_id':'G44'if S['screens'][sid]['profile']=='feature'else'G08'}))
   self.assertEqual(state['screen'],'C01',sid);state=run(state,'hold.end');self.assertEqual(state['screen'],sid,sid)
 def test_native_return(self):
  state=initial('C02');state['family']='parameters'
  state,_,_=step(S,state,'K1.short');self.assertTrue(state['native'])
  state,_,_=step(S,state,'native.return');self.assertFalse(state['native']);self.assertEqual(state['screen'],'C02')
 def test_modal_does_not_block_k1_edges_or_menu(self):
  state=initial('S05','Scale');state['modal']=True
  _,ops,rid=step(S,state,'K1.down');self.assertEqual(rid,'edge.K1.down')
  after,_,rid=step(S,state,'K1.short');self.assertEqual(rid,'K1.short');self.assertTrue(after['native'])
 def test_grid_focus_retained_for_transport(self):
  state=initial('H02');after,_,_=step(S,state,'grid.outcome',{'flow_id':'G38'});self.assertEqual(after['screen'],'H02')
 def test_context_change_invalidates_return(self):
  state=initial();state,_,_=step(S,state,'K1.short');state,_,_=step(S,state,'grid.outcome',{'flow_id':'G04'})
  self.assertEqual((state['screen'],state['context']),('A03','Song'));self.assertEqual(state['return_stack'],[]);self.assertEqual(state['generation'],1)
 def test_page_buttons_set_screen_and_context_together(self):
  cases=[(('C01','Channel'),'G02',{},('S01','Scale')),(('S01','Scale'),'G04',{},('A03','Song')),(('A03','Song'),'G01',{},('C01','Channel')),
   (('C01','Channel'),'G03',{'page':'Trig'},('P01','Trig')),(('P01','Trig'),'G03',{'page':'Note'},('P03','Note')),
   (('P03','Note'),'G03',{'page':'Velocity'},('P04','Velocity')),(('P04','Velocity'),'G03',{'page':'Trig'},('P01','Trig'))]
  for (sid,ctx),fid,extra,want in cases:
   after,_,_=step(S,initial(sid,ctx),'grid.outcome',dict(flow_id=fid,**extra));self.assertEqual((after['screen'],after['context']),want,fid)
  state=initial();state['family']='parameters';after,_,_=step(S,state,'grid.outcome',{'flow_id':'G01'});self.assertEqual((after['screen'],after['context']),('C02','Channel'))
 def test_tasks_open_after_cycle_reaches_pattern_navigator(self):
  state=run(initial('P01','Trig'),('grid.outcome',{'flow_id':'G03','page':'Note'}),'E1+')
  self.assertEqual((state['screen'],state['context']),('N03','Note'))
  state,_,_=step(S,state,'K3.down',{'task':'pattern'});self.assertEqual(state['screen'],'P03')
 def test_every_navigator_row_enterable_from_each_context(self):
  for ctx,primary in S['contexts'].items():
   nav=run(initial(primary,ctx),'E1+');nav=run(nav,'E1+')if nav['screen']=='C02'else nav
   self.assertEqual(nav['screen'],S['tasks']['navigators'][ctx])
   for extra in [{},{'algorithm':5}]:
    for row in task_rows(S,nav,extra):
     after,ops,rid=step(S,nav,'K3.down',dict(task=row['id'],**extra))
     self.assertEqual((after['screen'],after['context']),(row_screen(row,ctx),ctx))
     if after['screen']in S['tasks']['rows']:
      for sub in task_rows(S,after,extra):
       _,ops,rid=step(S,after,'K3.down',dict(task=sub['id'],**extra))
       if 'native'in sub:self.assertEqual(rid,'tasks.native_hint')
  self.assertNotIn('rhythm_doctor',[r['id']for r in task_rows(S,initial('N03','Trig'))])
  with self.assertRaisesRegex(ValueError,'not enterable'):step(S,initial('N03','Note'),'K3.down',{'task':'options'})
 def test_hold_on_dashboard_observes_in_place(self):
  after,_,_=step(S,initial('C06'),'hold.begin',{'steps':[9,10]});self.assertEqual(after['screen'],'C06');self.assertEqual(after['target']['step_set'],[9,10])
  after=run(after,'hold.end');self.assertEqual(after['screen'],'C06');self.assertEqual(after['return_stack'],[])
 def test_hold_on_setup_follows_family_and_restores(self):
  after=run(initial('C04'),('hold.begin',{'steps':[3]}));self.assertEqual(after['screen'],'C01')
  self.assertEqual(run(after,'hold.end')['screen'],'C04')
 def test_merge_mode_taps_do_not_steal_workspace(self):
  for fid in ['G16','G17','G18']:
   after,_,_=step(S,initial('C01'),'grid.outcome',{'flow_id':fid});self.assertEqual(after['screen'],'C01');self.assertEqual(after['return_stack'],[])
   after,_,_=step(S,initial('M02'),'grid.outcome',{'flow_id':fid});self.assertEqual(after['screen'],'M09')
   self.assertEqual(run(after,'hold.end')['screen'],'M02')
  state=initial('C02');state['family']='parameters'
  after,_,_=step(S,state,'grid.outcome',{'flow_id':'G07'});self.assertEqual(after['screen'],'C02')
 def test_k1_k3_on_trig_params_is_noop(self):
  state=initial('C02');state['family']='parameters';state=run(state,'K1.down')
  _,ops,rid=step(S,state,'K3.down');self.assertEqual(rid,'param.slide.shift');self.assertEqual([o['op']for o in ops],['noop'])
  _,ops,rid=step(S,initial('C02'),'K3.down');self.assertEqual(rid,'param.slide')
 def test_hold_outcome_release_keeps_return_stack(self):
  base=run(initial('C02'),'K2.down');self.assertEqual(base['screen'],'C07');stack=deepcopy(base['return_stack'])
  for last in [[3],[9]]:
   state=run(base,('hold.begin',{'steps':[3]}),('hold.change',{'steps':[3,9]}),('grid.outcome',{'flow_id':'G08'}),('hold.change',{'steps':last}),'hold.end')
   self.assertEqual(state['screen'],'C07');self.assertEqual(state['return_stack'],stack);self.assertFalse(state['held'])
 def test_temporary_outcome_restores_parent(self):
  state=initial('C02');state['family']='parameters'
  state,_,_=step(S,state,'grid.outcome',{'flow_id':'G13'})
  state,_,_=step(S,state,'hold.end');self.assertEqual(state['screen'],'C02')
 def test_every_rule_effect_has_contract(self):
  for rule in S['input_algebra']['rules']:
   for op in rule['effects']:self.assertIn(op,S['effect_contracts'])
 def test_ambiguous_rule_is_detected(self):
  altered=deepcopy(S);rule=deepcopy(select(S,initial(),'E1+'));rule['id']='mutation.duplicate';altered['input_algebra']['rules'].append(rule)
  with self.assertRaisesRegex(ValueError,'ambiguous'):select(altered,initial(),'E1+')
 def test_missing_flow_is_detected(self):
  altered=deepcopy(S);del altered['flows']['G01'];self.assertTrue(any('replacement' in e or 'entry' in e for e in validate(altered,check_sources=False)))
 def test_router_mutations_are_detected(self):
  altered=deepcopy(S);del altered['flows']['G03']['new']['context'];self.assertIn('page flow context G03',validate(altered,check_sources=False))
  altered=deepcopy(S);altered['flows']['G03']['new']['alternatives'][0]['context']='Velocity';self.assertIn('flow context G03 P03',validate(altered,check_sources=False))
  altered=deepcopy(S);altered['screens']['N03']['fields'].reverse();self.assertIn('navigator rows N03',validate(altered,check_sources=False))
  altered=deepcopy(S);del altered['screens']['C06']['hold_policy'];self.assertIn('hold_policy C06',validate(altered,check_sources=False))
 def test_grid_overlap_is_detected(self):
  altered=deepcopy(S);altered['grid']['contexts']['Channel'][1]=deepcopy(altered['grid']['contexts']['Channel'][0]);self.assertTrue(any('overlap/gap'in e for e in validate(altered,check_sources=False)))
 def test_source_drift_is_detected(self):
  inventory=read('source-inventory.json');inventory['files']['README.md']='0'*64;self.assertTrue(any('source drift README.md'==e for e in validate(inventory=inventory)))
 def doctor(self,flow,start='R01',**kw):
  p={'flow_id':flow,'doctor_state':'EMPTY','modal_operation':'none','draft':'none','preview':'none','playing':False};p.update(kw)
  return step(S,initial(start,'Trig'),'grid.outcome',p)[0]['screen']
 def test_doctor_playing_without_ready_bank_resolves_stop_sequencer(self):
  for st in ['EMPTY','FAILED','ALIGNMENT_REQUIRED','RECORDING']:self.assertEqual(self.doctor('G40',doctor_state=st,playing=True,outcome='record_refused'),'R11')
  self.assertEqual(self.doctor('G43',doctor_state='EMPTY',playing=True,outcome='transport_started'),'R11')
 def test_doctor_ready_bank_works_while_playing(self):
  for flow,preview,outcome,dest in [('G42','armed','preview_armed','R08'),('G42','none','paint_committed','R09'),('G42','none','preview_cancelled','R05'),
                                    ('G46','none','window_moved','R15'),('G41','armed','lane_selected','R13'),('G40','none','record_refused','R05'),('G43','armed','transport_started','R08')]:
   self.assertEqual(self.doctor(flow,'R05',doctor_state='READY',playing=True,preview=preview,outcome=outcome),dest,flow+outcome)
 def test_doctor_questions_route_by_modal_operation(self):
  for st,op,dest in [('READY','clear','R10'),('ALIGNMENT_REQUIRED','clear','R10'),('ANALYSING','cancel_capture','R03'),('RECORDING','cancel_capture','R03'),('REANALYSING','cancel_correction','R16')]:
   self.assertEqual(self.doctor('G40',doctor_state=st,modal_operation=op,outcome='record_question'),dest)
   self.assertEqual(self.doctor('G41',doctor_state=st,modal_operation=op,outcome='lane_selected'),dest)
 def test_doctor_drafts_and_states_route(self):
  for kw,dest in [({'draft':'setup','doctor_state':'FAILED'},'R01'),({'draft':'alignment','doctor_state':'READY'},'R06'),({'draft':'alignment_refused','doctor_state':'EMPTY'},'R07'),
                  ({'doctor_state':'LISTENING'},'R02'),({'doctor_state':'REANALYSING'},'R04'),({'doctor_state':'ALIGNMENT_REQUIRED'},'R12'),({'doctor_state':'READY'},'R05')]:
   self.assertEqual(self.doctor('G40',outcome='entered',**kw),dest,str(kw))
  self.assertEqual(self.doctor('G41',doctor_state='RECORDING',outcome='lane_selected'),'R02')
 def test_doctor_incomplete_payload_fails_loudly(self):
  with self.assertRaisesRegex(ValueError,'doctor payload missing'):step(S,initial('P01','Trig'),'grid.outcome',{'flow_id':'G40','playing':True,'doctor_state':'RECORDING'})
 def test_doctor_ten_lane_bank_cells(self):
  from model import doctor_lane_at
  ten=['KICK','SNARE','HIHAT','CYMBALS','TOMS','BASS','GUITAR','PIANO','VOCALS','OTHER'];three=['BD','SD','CYM']
  self.assertEqual((doctor_lane_at(S,ten,7,2),doctor_lane_at(S,ten,3,3),doctor_lane_at(S,ten,7,3)),('TOMS','BASS','OTHER'))
  self.assertEqual((doctor_lane_at(S,three,5,2),doctor_lane_at(S,three,7,2),doctor_lane_at(S,three,3,3)),('CYM',None,None))
  self.assertIsNone(doctor_lane_at(S,ten+['EXTRA'],8,3));self.assertIsNone(doctor_lane_at(S,ten,2,2))
  cells={(c['x'],c['y']):c for c in S['grid']['doctor_override']['cells']}
  self.assertEqual((cells[(7,2)]['index'],cells[(3,3)]['index'],cells[(1,2)]['control'],cells[(2,2)]['control']),(5,6,'doctor_record','doctor_reserved'))
 def test_doctor_alternative_drift_is_detected(self):
  altered=deepcopy(S);alt=next(a for a in altered['flows']['G42']['new']['alternatives']if a['screen']=='R11');alt['screen']='R05'
  self.assertTrue(any('doctor alternative drift G42'in e for e in validate(altered,check_sources=False)))
 def test_doctor_overlay_gap_is_detected(self):
  altered=deepcopy(S);altered['grid']['doctor_override']['cells'].pop(3)
  self.assertTrue(any('doctor overlay gap'in e for e in validate(altered,check_sources=False)))
 def test_harmony_link_discards_merge_draft_and_enters_root(self):
  state=initial('M07');state.update(dirty=True,field_kind='action',field_id='harmony')
  state['return_stack']=[{'screen':'M02','field_id':'pitch','target':deepcopy(state['target']),'generation':0}]
  after,ops,rule=step(S,state,'K3.down')
  self.assertEqual(rule,'feature.action');self.assertFalse(after['dirty']);self.assertEqual(after['return_stack'],[]);self.assertEqual(after['screen'],'H01')
  self.assertEqual([o['op']for o in ops],['owner.invoke_selected','owner.before_if_present','owner.cancel_unapplied','return.invalidate','owner.enter_root'])
 def test_route_action_pushes_exact_parent(self):
  state=initial('M07');state.update(dirty=True,field_kind='action',field_id='target_setup')
  after,_,_=step(S,state,'K3.down');self.assertEqual(after['screen'],'M13');self.assertEqual(after['return_stack'][-1]['screen'],'M07');self.assertTrue(after['dirty'])
 def test_duplicate_field_id_is_detected(self):
  altered=deepcopy(S);fields=altered['screens']['M14']['fields'];fields.append(deepcopy(fields[0]))
  self.assertIn('duplicate field id M14.step',validate(altered,check_sources=False))
 def test_label_keyed_binding_is_detected(self):
  altered=deepcopy(S);altered['screens']['M12']['fields'][0]['binding']['field']='Add amount'
  self.assertIn('binding.field != id M12.add_amount',validate(altered,check_sources=False))
 def test_foreign_existing_route_is_detected(self):
  altered=deepcopy(S);altered['screens']['M10']['provider']='merge';altered['screens']['M10']['binding']['provider']='merge'
  self.assertTrue(any(e.startswith('existing_route not in source_route_map M10')for e in validate(altered,check_sources=False)))
 def test_cross_owner_link_never_in_route_map(self):
  altered=deepcopy(S);altered['source_route_map']['merge']['HARMONY_LINK']='H01'
  self.assertIn('cross-owner link in source route map M07.harmony',validate(altered,check_sources=False))
 def test_view_channel_is_inspection_only(self):
  for sid in S['field_contracts']['viewer']['screens']:
   state=initial(sid,contexts(S,sid)[0]);state.update(field_id='view_channel',field_kind=field_kind(S,sid,'view_channel'))
   self.assertEqual(state['field_kind'],'inspection')
   for ev in ['E3+','E3-']:
    after,ops,_=step(S,state,ev)
    self.assertEqual([o['op']for o in ops],['inspection.change_without_mutation'])
    self.assertEqual(S['effect_contracts'][ops[0]['op']]['kind'],'presentation')
    self.assertEqual(after['target'],state['target']);self.assertEqual(after['screen'],sid)
   _,ops,_=step(S,state,'E2+');self.assertEqual([o['op']for o in ops],['focus.move_clamped'])
 def test_readonly_non_inspection_field_is_readonly(self):
  self.assertEqual(field_kind(S,'P05','range'),'readonly')
  state=initial('P05','Song');state.update(field_id='range',field_kind=field_kind(S,'P05','range'))
  _,ops,_=step(S,state,'E3+');self.assertEqual([o['op']for o in ops],['noop'])
 def test_parameter_name_as_slot_key_is_detected(self):
  altered=deepcopy(S);f=altered['screens']['C13']['fields'][0];f['id']=f['binding']['field']='cc11'
  self.assertIn('repeat key C13 cc11',validate(altered,check_sources=False))
 def test_every_registration_has_branch_ledger(self):
  self.assertEqual([e for e in validate(check_sources=False)if 'branch' in e],[])
 def test_branch_ledger_mutations_are_detected(self):
  def errs(mutate):
   inventory=read('source-inventory.json');mutate(inventory['grid_registrations']);return validate(inventory=inventory,check_sources=False)
  self.assertIn('no branches LEGACY.m_grid.01',errs(lambda g:g[0].update(branches=[])))
  self.assertTrue(any(e.startswith('unknown branch outcome')for e in errs(lambda g:g[0]['branches'][0].update(outcome='G99'))))
  self.assertTrue(any(e.startswith('branch outcome outside replacement_flows')for e in errs(lambda g:g[0]['branches'][0].update(outcome='G38'))))
  self.assertTrue(any(e.startswith('duplicate branch ')for e in errs(lambda g:g[1]['branches'].append(deepcopy(g[0]['branches'][0])))))
  self.assertEqual([e for e in errs(lambda g:g[0]['branches'][0].update(outcome='retain_without_navigation'))if 'branch' in e],[])
 def test_overview_declares_full_value_line(self):
  altered=deepcopy(S);del altered['layout_contract']['families']['overview_params']['full_value_line']
  self.assertTrue(any('full_value_line' in e for e in validate(altered,check_sources=False)))
 def test_manual_section_is_checked_against_readme_slice(self):
  inventory=read('source-inventory.json');m=inventory['manual_sections'][32];m['text']='stale';import hashlib;m['sha256']=hashlib.sha256(b'stale').hexdigest()
  self.assertIn('manual section drift MAN.033',validate(inventory=inventory))
 def test_k2_on_feature_root_stays_and_cancels(self):
  for root in ['M02','H01']:
   state=initial(root);state.update(dirty=True);after,ops,_=step(S,state,'K2.down')
   self.assertEqual(after['screen'],root);self.assertFalse(after['dirty']);self.assertIn('owner.cancel_unapplied',[o['op']for o in ops])
if __name__=='__main__':unittest.main()

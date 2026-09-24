import json,sys,unittest
from copy import deepcopy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from model import initial,step,select
from validate import read,validate
S=read('spec.json')
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
    state=initial(sid);_,ops,_=step(S,state,'E3+');self.assertEqual([o['op']for o in ops],['noop'])
 def test_held_steps_beat_confirmation_and_shift_clear(self):
  state=initial('H17');state.update(held=True,modal=True,shift=True,dirty=True);state['target']['step_set']=[2,17,64]
  after,ops,_=step(S,state,'K2.down');self.assertFalse(after['dirty']);self.assertEqual(after['screen'],'C01');self.assertEqual(ops[-1]['op'],'family.clear');self.assertEqual(ops[-1]['target']['step_set'],[2,17,64])
 def test_parameter_slide_never_applies_feature(self):
  state=initial('M03');state.update(held=True,dirty=True,family='parameters');state['target']['step_set']=[7]
  after,ops,_=step(S,state,'K3.down');self.assertEqual(after['screen'],'C02');self.assertEqual(ops[-1]['op'],'family.slide_if_parameters');self.assertFalse(after['dirty'])
 def test_native_return(self):
  state=initial('C02');state['family']='parameters'
  state,_,_=step(S,state,'K1.short');self.assertTrue(state['native'])
  state,_,_=step(S,state,'native.return');self.assertFalse(state['native']);self.assertEqual(state['screen'],'C02')
 def test_grid_focus_retained_for_transport(self):
  state=initial('H02');after,_,_=step(S,state,'grid.outcome',{'flow_id':'G38'});self.assertEqual(after['screen'],'H02')
 def test_doctor_running_resolution_precedes_recording(self):
  state=initial('P01','Trig');after,_,_=step(S,state,'grid.outcome',{'flow_id':'G40','playing':True,'doctor_state':'RECORDING'});self.assertEqual(after['screen'],'R11')
 def test_context_change_invalidates_return(self):
  state=initial();state,_,_=step(S,state,'K1.short');state,_,_=step(S,state,'grid.context',{'context':'Song'});self.assertEqual(state['return_stack'],[]);self.assertEqual(state['generation'],1)
 def test_clean_feature_child_returns_root_before_tasks(self):
  state=initial('M03');state,_,_=step(S,state,'E1+');self.assertEqual(state['screen'],'M02')
  state,_,_=step(S,state,'E1+');self.assertEqual(state['screen'],'N01')
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
 def test_grid_overlap_is_detected(self):
  altered=deepcopy(S);altered['grid']['contexts']['Channel'][1]=deepcopy(altered['grid']['contexts']['Channel'][0]);self.assertTrue(any('overlap/gap'in e for e in validate(altered,check_sources=False)))
 def test_source_drift_is_detected(self):
  inventory=read('source-inventory.json');inventory['files']['README.md']='0'*64;self.assertTrue(any('source drift README.md'==e for e in validate(inventory=inventory)))
if __name__=='__main__':unittest.main()

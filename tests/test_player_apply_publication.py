import copy
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock
import yaml


def repository_root():
    for root in (Path.cwd(), *Path(__file__).resolve().parents):
        if (root/'tools/manual_publication_verify.py').is_file() and (root/'manual/voices.lock.json').is_file():
            return root
    raise RuntimeError('Run this portable suite from a Mosaic repository checkout')

REPO=repository_root()
CANDIDATE=Path(__file__).resolve().parents[1]

def source_path(relative):
    candidate=CANDIDATE/'source'/relative
    return candidate if candidate.is_file() else REPO/relative
sys.path[:0]=[str(REPO/'tools'),str(REPO/'tests/behaviour')]
VERIFY_PATH=CANDIDATE/'source/tools/manual_publication_verify.py'
if not VERIFY_PATH.is_file():VERIFY_PATH=REPO/'tools/manual_publication_verify.py'
spec=importlib.util.spec_from_file_location('candidate_publication_verify',VERIFY_PATH)
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)

class PlayerApplyPortableTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='player-apply-proof-')
  self.addCleanup(self.temp.cleanup)
  self.path=Path(self.temp.name);(self.path/'native').mkdir()
  (self.path/'native/identity.json').write_text(json.dumps({'session_id':'fixture-session'}))
  self.session='fixture-session';self.grid=[0]*64;self.frame='a'*64

 def make_context(self,kind,value=None,*,channel=1,inputs=None):
  selected_value=None if kind=='manual-player-apply-start' else value
  selected={'kind':'selected-field','layout':'detail','label':'Device','value':selected_value,'matched':True,
      'observation_index':0,'frame_sha256':self.frame}
  assertion={'kind':kind,'citation':'manual:mods-and-software-devices','channel':channel,'field':'Device','passed':True}
  if kind!='manual-player-apply-start':assertion['value']=value
  if kind=='manual-player-apply-pending':assertion['confirmation_prompt']='Press K3 to confirm'
  if kind in ('manual-player-apply-applied','manual-player-apply-reopened'):assertion['confirmation_prompt_absent']=True
  results=[selected,assertion]
  observations=[{'backend':'native','fidelity':'native-norns','session_id':self.session,
      'state':{'frame':{'sha256':self.frame},'grid':copy.deepcopy(self.grid)}}]
  step={'inputs':inputs or [],'output':{'grid':copy.deepcopy(self.grid),'binding':{'assertion_index':1,'sha256':self.frame,'assertion':copy.deepcopy(assertion)}}}
  return step,results,observations

 def check(self,step,results,observations):
  with mock.patch.object(verify,'verify_cached_ui') as pixels:
   verify.check_player_apply_checkpoint(step,results,observations,self.path)
   return pixels.call_args.args[1]

 def test_typed_checkpoint_requests_exact_pixel_state(self):
  step,results,observations=self.make_context('manual-player-apply-pending','Oilcan 1',inputs=[{'type':'enc','n':3,'delta':2}])
  expected=self.check(step,results,observations)
  self.assertEqual(expected['header'],{'page':'midi_config','params':{'channel':1}})
  self.assertEqual(expected['field'],{'layout':'detail','label':'Device','value':'Oilcan 1'})
  self.assertEqual(expected['footer'],{'text':'Press K3 to confirm','present':True})
  step,results,observations=self.make_context('manual-player-apply-applied','Oilcan 1',inputs=[{'type':'key','n':3,'state':1},{'type':'key','n':3,'state':0}])
  self.assertEqual(self.check(step,results,observations)['footer'],{'text':'Press K3 to confirm','present':False})

 def test_rejects_wrong_selected_field_label_or_value(self):
  step,results,observations=self.make_context('manual-player-apply-pending','Oilcan 1')
  results[0]['label']='Bank'
  with mock.patch.object(verify,'verify_cached_ui') as pixels, self.assertRaisesRegex(ValueError,'immediately preceded'):
   verify.check_player_apply_checkpoint(step,results,observations,self.path)
  pixels.assert_not_called()
  step,results,observations=self.make_context('manual-player-apply-pending','Oilcan 1')
  results[0]['value']='Oilcan 2'
  with self.assertRaisesRegex(ValueError,'differs from selected-field'):self.check(step,results,observations)

 def test_rejects_foreign_session_bad_frame_and_grid(self):
  step,results,observations=self.make_context('manual-player-apply-pending','Oilcan 1')
  observations[0]['session_id']='foreign-session'
  with self.assertRaisesRegex(ValueError,'selected native session'):self.check(step,results,observations)
  step,results,observations=self.make_context('manual-player-apply-pending','Oilcan 1')
  results[0]['frame_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'frame differs'):self.check(step,results,observations)
  step,results,observations=self.make_context('manual-player-apply-pending','Oilcan 1')
  step['output']['grid'][0]=15
  with self.assertRaisesRegex(ValueError,'grid differs'):self.check(step,results,observations)

 def test_rejects_confirmation_prompt_and_invalid_k3_edges(self):
  step,results,observations=self.make_context('manual-player-apply-pending','Oilcan 1',inputs=[{'type':'key','n':3,'state':1}])
  with self.assertRaisesRegex(ValueError,'already contains K3'):self.check(step,results,observations)
  step,results,observations=self.make_context('manual-player-apply-pending','Oilcan 1')
  results[1]['confirmation_prompt']='Press K2 to confirm'
  with self.assertRaisesRegex(ValueError,'prompt changed'):self.check(step,results,observations)
  step,results,observations=self.make_context('manual-player-apply-applied','Oilcan 1')
  with self.assertRaisesRegex(ValueError,'K3 press/release'):self.check(step,results,observations)

 def test_rejects_scene_order_and_value_loss(self):
  def scene():
   steps=[]
   for kind,value,inputs in [
    ('manual-player-apply-start',None,[]),
    ('manual-player-apply-pending','Oilcan 1',[{'type':'enc','n':3,'delta':2}]),
    ('manual-player-apply-applied','Oilcan 1',[{'type':'key','n':3,'state':1},{'type':'key','n':3,'state':0}]),
    ('manual-player-apply-reopened','Oilcan 1',[{'type':'key','n':3,'state':1},{'type':'key','n':3,'state':0}])]:
    step,results,obs=self.make_context(kind,value,inputs=inputs)
    step['output']['binding']['assertion']=results[1]
    steps.append(step)
   return {'behaviour_case':'M-MANUAL-PLAYER-APPLY-001','profile':'manual-player-ui','steps':steps}
  valid=scene();verify.check_player_apply_scene(valid)
  invalid=scene();invalid['steps'][2],invalid['steps'][3]=invalid['steps'][3],invalid['steps'][2]
  with self.assertRaisesRegex(ValueError,'missing or out of order'):verify.check_player_apply_scene(invalid)
  invalid=scene();invalid['steps'][3]['output']['binding']['assertion']['value']='Polyperc 1'
  with self.assertRaisesRegex(ValueError,'does not persist'):verify.check_player_apply_scene(invalid)

 def test_profile_rejects_enabled_mod_inventory_mismatch(self):
  (self.path/'native/native-config.json').write_text(json.dumps({'enabled_mods':['oilcan']}))
  app={'code_root':str(self.path),'files':[{'path':'mosaic/mosaic.lua'},{'path':'oilcan/lib/mod.lua'}]}
  with self.assertRaisesRegex(ValueError,'exact profile declaration'):verify.player_source_roots(self.path,app)

 def test_build_stage_and_feature_ownership_binding(self):
  build_path=source_path('tools/manual_build.py')
  spec=importlib.util.spec_from_file_location('candidate_manual_build',build_path)
  build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build);build.ROOT=REPO
  options=types.SimpleNamespace(real_install='real',python='python',mod_code_root='/pinned/voices',emulator='emu',
      controlled_install='controlled',audio_emulator='audio-emu',audio_install='audio-install',ffmpeg='ffmpeg',
      modulation_code_root='modulation',modulation_emulator=None,modulation_controlled_install=None,
      browser_tests=False,quick_output='manual/generated/quick.html',node='node')
  stages=build.plan(options,['scene-plans-player-apply.yaml'],controlled_local=True)
  row=next(stage for stage in stages if stage['name']=='reference-controlled-scene-plans-player-apply-manual-player-ui')
  self.assertIn('--profile',row['command']);self.assertIn('manual-player-ui',row['command'])
  self.assertIn('--mod-code-root',row['command']);self.assertIn('/pinned/voices',row['command'])
  self.assertIn('manual_player_apply_cases.py',' '.join(row['command']))
  self.assertIn('controlled-experimental',row['command']);self.assertNotIn('--mod-patches',row['command'])
  self.assertFalse(any(stage['name']=='reference-real-scene-plans-player-apply-manual-player-ui' for stage in stages))
  authored=yaml.safe_load((source_path('manual/features/reference-learn.yaml')).read_text())
  feature=next(item for item in authored['features'] if item['id']=='mods-and-software-devices')
  self.assertEqual(feature['scene_refs'],['software-player-oilcan','software-player-polyperc','software-player-doubledecker','player-apply-oilcan','player-apply-polyperc','player-apply-doubledecker'])
  self.assertIn('M-MANUAL-PLAYER-APPLY-001',feature['sources']['behaviour_cases'])
  book=yaml.safe_load((source_path('manual/book.yaml')).read_text())
  self.assertIn('scene-plans-player-apply.yaml',book['scene_sources'])
  binding=(source_path('tools/manual_feature_bind.py')).read_text()
  self.assertIn("'mods-and-software-devices':['player-apply-oilcan','player-apply-polyperc','player-apply-doubledecker']",binding)

if __name__=='__main__':unittest.main(verbosity=2)

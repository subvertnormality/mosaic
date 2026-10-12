"""Editorial characterization: title receipts never authorize native-field edits."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from manual_caption_overlay import apply_overlays, contract_sha256
import manual_publication_verify as audit


class CompiledTitleReceiptTests(unittest.TestCase):
    def pair(self, scene_title=True, step_title=True, caption=True, starting_state=False):
        raw={'id':'scene','title':'Captured scene','feature_id':'captured-owner',
             'evidence':{'results_sha256':'immutable'},'steps':[
                 {'id':'first','title':'Captured step','caption':'Captured caption',
                  'inputs':[{'type':'enc','n':3,'delta':2}], 'expect':{'value':63},
                  'citation':'manual:parameters',
                  'output':{'grid':[0], 'binding':{'sha256':'native','assertion_index':4}}},
                 {'id':'second','title':'Second step','caption':'Second caption',
                  'inputs':[], 'expect':{'value':64}, 'output':{'grid':[1]}}]}
        if starting_state:raw['starting_state']='Captured prepared state'
        entry={'scene_id':'scene','step_id':'first',
               'baseline_caption':'Captured caption',
               'caption':'Set the value to 63' if caption else 'Captured caption',
               'contract_sha256':contract_sha256(raw)}
        if scene_title:entry.update(scene_title='Choose an output',baseline_scene_title='Captured scene')
        if step_title:entry.update(step_title='Apply the setting',baseline_step_title='Captured step')
        compiled=apply_overlays({'scene':raw},{'schema_version':1,'overlays':[entry]})['scene']
        return raw,compiled

    def test_producer_title_receipts_pass_the_final_audit(self):
        for scene_title,step_title,caption in ((True,False,False),(False,True,False),
                                             (True,True,False),(True,True,True)):
            with self.subTest(scene_title=scene_title,step_title=step_title,caption=caption):
                raw,compiled=self.pair(scene_title,step_title,caption)
                original=copy.deepcopy(raw);revised=copy.deepcopy(compiled)
                audit.check_compiled_scene_contract(raw,compiled)
                self.assertEqual(raw,original);self.assertEqual(compiled,revised)

    def test_receipts_use_the_producer_contract_before_starting_state_presentation(self):
        raw,compiled=self.pair(starting_state=True)
        compiled['starting_state']='A musician-facing description of the prepared state'
        audit.check_compiled_scene_contract(raw,compiled)

    def test_missing_changed_extra_or_unneeded_title_receipts_are_rejected(self):
        for location,key in (('scene','scene_title_overlay'),('step','step_title_overlay')):
            for mutation in ('missing','original_title_sha256','title_sha256','contract_sha256','extra','unneeded'):
                with self.subTest(location=location,mutation=mutation):
                    raw,compiled=self.pair();node=compiled if location=='scene' else compiled['steps'][0]
                    if mutation=='missing':node.pop(key)
                    elif mutation=='extra':node[key]['extra']='unreviewed'
                    elif mutation=='unneeded':node['title']=raw['title'] if location=='scene' else raw['steps'][0]['title']
                    else:node[key][mutation]='changed'
                    with self.assertRaises(ValueError):audit.check_compiled_scene_contract(raw,compiled)

    def test_title_receipts_cannot_hide_native_contract_mutations(self):
        for mutation in ('inputs','expect','output','citation','evidence','feature_id','step_order'):
            with self.subTest(mutation=mutation):
                raw,compiled=self.pair()
                if mutation=='step_order':compiled['steps'].reverse()
                elif mutation in ('evidence','feature_id'):compiled[mutation]='changed'
                else:compiled['steps'][0][mutation]='changed'
                with self.assertRaises(ValueError):audit.check_compiled_scene_contract(raw,compiled)


if __name__=='__main__':unittest.main()

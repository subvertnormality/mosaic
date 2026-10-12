"""Editorial characterisation: captions cannot alter native acceptance evidence."""
import copy,json,sys,tempfile,unittest
from unittest.mock import patch
import yaml
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
import manual_publication_verify as audit
from manual_caption_overlay import apply_overlays,contract_sha256,text_sha256
import manual_book

class CaptionOverlayTests(unittest.TestCase):
    def setUp(self):
        self.scene={"id":"slide","title":"Slide", "feature_id":"captured-owner",
                    "data_path":"generated/native.json",
                    "evidence":{"results_sha256":"abc"},"steps":[
                    {"id":"a","caption":"Technical caption", "title":"Press K3",
                     "inputs":[{"key":3}],"expect":{"cc":96},
                     "output":{"binding":{"assertion_index":4},"screen":[1,2]}},
                    {"id":"b","caption":"Second technical caption","inputs":[],"output":{"grid":[3]}}]}
        self.entry={"scene_id":"slide","step_id":"a","caption":"Press K3. CC 1 slides to 96.",
                    "baseline_caption":"Technical caption","contract_sha256":contract_sha256(self.scene)}
    def apply(self,entries=None,scene=None):
        return apply_overlays({"slide":scene or self.scene},{"schema_version":1,"overlays":entries or [self.entry]})
    def test_changes_only_caption_and_adds_receipt_without_mutating_source(self):
        original=copy.deepcopy(self.scene); result=self.apply()["slide"]
        self.assertEqual(self.scene,original)
        self.assertEqual(result["steps"][0]["output"],original["steps"][0]["output"])
        self.assertEqual(result["evidence"],original["evidence"])
        receipt=result["steps"][0]["caption_overlay"]
        self.assertEqual(receipt["original_caption_sha256"],text_sha256("Technical caption"))
        self.assertEqual(receipt["caption_sha256"],text_sha256(self.entry["caption"]))
        self.assertEqual(receipt["contract_sha256"],self.entry["contract_sha256"])
    def test_semantic_changes_reject(self):
        for field in ("inputs","expect","output"):
            scene=copy.deepcopy(self.scene);scene["steps"][0][field]={"changed":True}
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"contract"):
                self.apply(scene=scene)
    def test_source_identity_and_step_titles_are_bound(self):
        scene=copy.deepcopy(self.scene);scene["evidence"]["results_sha256"]="changed"
        with self.assertRaisesRegex(ValueError,"contract"):self.apply(scene=scene)
        scene=copy.deepcopy(self.scene);scene["steps"][0]["title"]="Press K2"
        with self.assertRaisesRegex(ValueError,"contract"):self.apply(scene=scene)
        scene=copy.deepcopy(self.scene);scene["title"]="New editorial title";scene["data_path"]="generated/moved.json"
        self.assertEqual(self.apply(scene=scene)["slide"]["steps"][0]["caption"],self.entry["caption"])
    def test_all_entries_validate_before_any_mutation(self):
        bad=dict(self.entry,step_id="missing")
        original=copy.deepcopy(self.scene)
        with self.assertRaisesRegex(ValueError,"Unknown step"):self.apply([self.entry,bad])
        self.assertEqual(self.scene,original)
    def test_multiple_overlays_use_same_original_contract(self):
        second=dict(self.entry,step_id="b",baseline_caption="Second technical caption",caption="Press K2.")
        result=self.apply([self.entry,second])["slide"]
        self.assertEqual([s["caption"] for s in result["steps"]],[self.entry["caption"],"Press K2."])
    def test_unknown_scene_and_wrong_baseline_reject(self):
        with self.assertRaisesRegex(ValueError,"Unknown scene"):self.apply([dict(self.entry,scene_id="missing")])
        with self.assertRaisesRegex(ValueError,"baseline"):self.apply([dict(self.entry,baseline_caption="Other")])
    def test_regenerated_desired_caption_needs_no_historical_overlay(self):
        scene=copy.deepcopy(self.scene);scene["steps"][0]["caption"]=self.entry["caption"]
        scene["evidence"]["results_sha256"]="new-native-run"
        result=self.apply(scene=scene)
        self.assertNotIn("caption_overlay",result["slide"]["steps"][0])
    def test_compiler_applies_only_listed_overlay_source(self):
        data={"edition":"1.4.0","title":"Mosaic","aliases":{},"navigation":[],
              "legacy_source_sha256":"legacy","scene_sources":["scene-captions.yaml"],
              "features":[{"scene_refs":["slide"],"review":{"status":"pending"}}]}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            (path/"scene-captions.yaml").write_text(yaml.safe_dump({"schema_version":1,"overlays":[self.entry]}))
            with patch.object(manual_book,"MANUAL",path),patch.object(manual_book,"validate"), \
                 patch.object(manual_book,"authoring_identity",return_value={}), \
                 patch.object(manual_book,"capture_catalogue",return_value={"slide":self.scene}):
                result=manual_book.compile_book(data)
                self.assertEqual(result["scenes"]["slide"]["steps"][0]["caption"],self.entry["caption"])
                self.assertEqual(self.scene["steps"][0]["caption"],"Technical caption")
                data["scene_sources"]=[]
                with self.assertRaisesRegex(ValueError,"authoring identity"):
                    manual_book.compile_book(data)
    def test_duplicate_and_extra_fields_reject(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):self.apply([self.entry,self.entry])
        with self.assertRaisesRegex(ValueError,"fields"):self.apply([dict(self.entry,output={})])
    def test_scene_and_step_titles_apply_with_per_field_receipts(self):
        entry=dict(self.entry,scene_title="Edited scene",baseline_scene_title="Slide",
                   step_title="Select Channel",baseline_step_title="Press K3")
        original=copy.deepcopy(self.scene);result=self.apply([entry])["slide"]
        self.assertEqual(self.scene,original)
        self.assertEqual(result["title"],"Edited scene")
        self.assertEqual(result["steps"][0]["title"],"Select Channel")
        self.assertEqual(result["feature_id"],"captured-owner")
        self.assertEqual(result["scene_title_overlay"],{
            "original_title_sha256":text_sha256("Slide"),
            "title_sha256":text_sha256("Edited scene"),
            "contract_sha256":entry["contract_sha256"]})
        self.assertEqual(result["steps"][0]["step_title_overlay"],{
            "original_title_sha256":text_sha256("Press K3"),
            "title_sha256":text_sha256("Select Channel"),
            "contract_sha256":entry["contract_sha256"]})
    def test_title_pairs_are_required_and_titles_remain_contract_bound(self):
        with self.assertRaisesRegex(ValueError,"fields"):
            self.apply([dict(self.entry,step_title="Select Channel")])
        title_only={"scene_id":"slide","step_id":"a","scene_title":"Edited scene",
                    "baseline_scene_title":"Slide","contract_sha256":self.entry["contract_sha256"]}
        with self.assertRaisesRegex(ValueError,"fields"):
            self.apply([title_only])
        changed=copy.deepcopy(self.scene);changed["steps"][0]["title"]="Changed natively"
        with self.assertRaisesRegex(ValueError,"Step title baseline"):
            self.apply([dict(self.entry,step_title="Select Channel",baseline_step_title="Press K3")],scene=changed)
        changed=copy.deepcopy(self.scene);changed["steps"][0]["inputs"]=[{"key":4}]
        with self.assertRaisesRegex(ValueError,"contract"):
            self.apply([dict(self.entry,step_title="Select Channel",baseline_step_title="Press K3")],scene=changed)
    def test_contradictory_scene_title_edits_reject_before_applying(self):
        first=dict(self.entry,scene_title="Edited scene",baseline_scene_title="Slide")
        second=dict(self.entry,step_id="b",caption="Second caption.",
                    baseline_caption="Second technical caption",
                    scene_title="A different title",baseline_scene_title="Slide")
        original=copy.deepcopy(self.scene)
        with self.assertRaisesRegex(ValueError,"Contradictory scene title"):
            self.apply([first,second])
        self.assertEqual(self.scene,original)
    def test_title_fields_are_not_skipped_when_caption_is_already_desired(self):
        scene=copy.deepcopy(self.scene);scene["steps"][0]["caption"]=self.entry["caption"]
        scene["steps"][0]["title"]="Unexpected title"
        entry=dict(self.entry,step_title="Select Channel",baseline_step_title="Press K3")
        with self.assertRaisesRegex(ValueError,"Step title baseline"):
            self.apply([entry],scene=scene)
    def test_fully_regenerated_desired_titles_and_caption_are_idempotent(self):
        entry=dict(self.entry,scene_title="Edited scene",baseline_scene_title="Slide",
                   step_title="Select Channel",baseline_step_title="Press K3")
        scene=copy.deepcopy(self.scene);scene["title"]=entry["scene_title"]
        scene["steps"][0]["title"]=entry["step_title"]
        scene["steps"][0]["caption"]=entry["caption"]
        scene["evidence"]["results_sha256"]="new-native-capture"
        result=self.apply([entry],scene=scene)["slide"]
        self.assertEqual(result,scene)
    def test_mixed_fresh_scene_title_and_caption_changes_use_original_contract(self):
        desired_title="Edited scene"
        first=dict(self.entry,caption=self.entry["caption"],scene_title=desired_title,
                   baseline_scene_title="Slide")
        second=dict(self.entry,step_id="b",caption="Updated second caption.",
                    baseline_caption="Second technical caption",scene_title=desired_title,
                    baseline_scene_title="Slide")
        scene=copy.deepcopy(self.scene);scene["title"]=desired_title
        scene["steps"][0]["caption"]=first["caption"]
        result=self.apply([first,second],scene=scene)["slide"]
        self.assertEqual(result["title"],desired_title)
        self.assertEqual(result["steps"][1]["caption"],second["caption"])
        self.assertEqual(result["steps"][1]["caption_overlay"]["contract_sha256"],second["contract_sha256"])

# Compiled title receipt regressions
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

if __name__=="__main__":unittest.main()

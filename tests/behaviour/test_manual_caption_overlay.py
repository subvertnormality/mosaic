"""Editorial characterisation: captions cannot alter native acceptance evidence."""
import copy,json,sys,tempfile,unittest
from unittest.mock import patch
import yaml
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from manual_caption_overlay import apply_overlays,contract_sha256,text_sha256
import manual_book

class CaptionOverlayTests(unittest.TestCase):
    def setUp(self):
        self.scene={"id":"slide","title":"Slide", "data_path":"generated/native.json",
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
if __name__=="__main__":unittest.main()

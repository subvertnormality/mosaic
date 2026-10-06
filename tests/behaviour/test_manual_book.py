"""Full-manual authoring contracts; characterisation outside the instrument manual."""
import copy, importlib.util, unittest
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("manual_book",ROOT/"tools/manual_book.py")
book=importlib.util.module_from_spec(spec);spec.loader.exec_module(book)
class ManualBook(unittest.TestCase):
    def setUp(self):
        self.data=book.load()
        refs={scene for feature in self.data["features"] for scene in feature.get("scene_refs",[])}
        course=self.data.get("course",{})
        refs.update(stage["binding"]["scene"] for chapter in course.get("learning_path",[])
                    for stage in chapter.get("stages",[]) if stage.get("binding",{}).get("scene"))
        starting_states=book.MANUAL/"scene-starting-states.yaml"
        if starting_states.is_file():
            refs.update(entry["scene_id"] for entry in book.read(starting_states).get("starting_states",[]))
        self.catalogue={scene:{"id":scene,"steps":[]} for scene in refs}
        proof={"passed":True,"semantic_assertions":["Fixture binding evidence"],"sha256":"fixture-screen","grid_sha256":"fixture-grid"}
        for chapter in course.get("learning_path",[]):
            for stage in chapter.get("stages",[]):
                binding=stage.get("binding",{})
                scene_id,step_id=binding.get("scene"),binding.get("step")
                if scene_id and step_id:
                    self.catalogue[scene_id]["steps"].append(
                        {"id":step_id,"output":{"binding":proof} if binding.get("status")=="controlled-verified" else {}})
        for name,value in (("capture_catalogue",self.catalogue),("authoring_identity",{"scope":"isolated-book-test"})):
            patcher=patch.object(book,name,return_value=value);patcher.start();self.addCleanup(patcher.stop)
        overlay=patch.object(book,"apply_overlays",side_effect=lambda scenes,overlay:scenes);overlay.start();self.addCleanup(overlay.stop)
    def test_every_inventory_feature_has_a_stable_destination(self):
        book.validate(self.data)
        ids={f["id"] for f in self.data["features"]}
        self.assertGreaterEqual(len(ids),125)
        self.assertTrue({"install","adding-trigs","merge-modes","masks","save-and-load"}<=ids)
        self.assertEqual(book.resolve(self.data,"norns-sound-sources-with-nb"),"norns-sound-sources-with-n-b")
    def test_duplicate_ids_and_dangling_relationships_rejected(self):
        bad=copy.deepcopy(self.data);bad["features"].append(bad["features"][0])
        with self.assertRaisesRegex(ValueError,"Duplicate"):book.validate(bad)
        bad=copy.deepcopy(self.data);bad["features"][0]["related"]=["missing-feature"]
        with self.assertRaisesRegex(ValueError,"Unknown related"):book.validate(bad)
    def test_source_missing_or_escaping_repository_rejected(self):
        bad=copy.deepcopy(self.data);bad["features"][0]["sources"]["code"]=["../private.lua"]
        with self.assertRaisesRegex(ValueError,"Unsafe|Missing"):book.validate(bad)
    def test_captured_scene_cannot_be_invented(self):
        bad=copy.deepcopy(self.data);bad["features"][0]["scene_refs"]=["imaginary-scene"]
        with self.assertRaisesRegex(ValueError,"Unknown scene"):book.validate(bad)
    def test_build_preserves_unverified_status_and_original_hash(self):
        self.data["features"][0]["review"]["status"]="pending"
        result=book.compile_book(self.data)
        self.assertFalse(result["complete_manual"])
        self.assertEqual(result["schema_version"],2)
        self.assertTrue(result["legacy_source_sha256"])
        self.assertTrue(all(f["review"]["status"] in ("pilot-reviewed","pending","verified","controlled-verified") for f in result["features"]))
    def course(self):
        return dict(schema_version=1,title="Make a phrase",summary="Build one musical project.",
                    project=dict(name="Phrase",output="MIDI",incoming_state="Empty project",capture_status="pending"),
                    learning_path=[dict(id="masks",title="Shape the phrase",goal="Hear a quieter note",prerequisite="A four-note loop",outgoing_state="One quiet note",recovery="Clear its velocity mask",stages=[dict(id="quiet-note",title="Quiet note",goal="Create contrast",action="Hold step 13 and set Vel to 50.",result="The fourth note is quieter.",binding=dict(status="pending",scene=None,step=None))])])
    def with_course(self):
        data=copy.deepcopy(self.data);data.update(course_source="course.yaml",course=self.course())
        return data
    def test_pending_course_is_compiled_and_blocks_completeness(self):
        data=self.with_course()
        for feature in data["features"]:feature["review"]["status"]="verified"
        with patch.object(book,"apply_overlays",side_effect=lambda scenes,overlay:scenes):result=book.compile_book(data)
        self.assertEqual(result["learning_path"],data["course"]["learning_path"])
        self.assertEqual(result["project"]["capture_status"],"pending")
        self.assertFalse(result["complete_manual"])
    def test_course_rejects_duplicate_routes_and_stage_ids(self):
        data=self.with_course();data["course"]["learning_path"]*=2
        with self.assertRaisesRegex(ValueError,"Duplicate course route"):book.validate(data)
        data=self.with_course();data["course"]["learning_path"][0]["stages"]*=2
        with self.assertRaisesRegex(ValueError,"Duplicate course stage"):book.validate(data)
    def test_course_rejects_missing_teaching_and_unknown_routes(self):
        data=self.with_course();data["course"]["learning_path"][0]["goal"]=""
        with self.assertRaises(ValueError):book.validate(data)
        data=self.with_course();data["course"]["learning_path"][0]["id"]="imaginary-feature"
        with self.assertRaisesRegex(ValueError,"Unknown course route"):book.validate(data)
    def test_verified_course_requires_actual_scene_and_step(self):
        data=self.with_course();binding=data["course"]["learning_path"][0]["stages"][0]["binding"]
        binding["status"]="verified"
        with self.assertRaises(ValueError):book.validate(data)
        binding.update(scene="imaginary-scene",step="imaginary-step")
        with self.assertRaisesRegex(ValueError,"Unknown course scene"):book.validate(data)
        scene=next(iter(book.capture_catalogue()));binding["scene"]=scene
        with self.assertRaisesRegex(ValueError,"Unknown course step"):book.validate(data)
    def test_verified_course_rejects_missing_semantic_evidence(self):
        data=self.with_course();binding=data["course"]["learning_path"][0]["stages"][0]["binding"]
        binding.update(status="verified",scene="lesson",step="quieter")
        with patch.object(book,"capture_catalogue",return_value={**book.capture_catalogue(),"lesson":{"id":"lesson","steps":[{"id":"quieter","output":{"binding":{"passed":False}}}]}}):
            with self.assertRaisesRegex(ValueError,"Unverified course binding"):book.validate(data)
    def test_course_source_escape_rejected(self):
        data=self.with_course();data["course_source"]="../../private.yaml"
        with self.assertRaisesRegex(ValueError,"Unsafe course source"):book.validate(data)
    def test_verified_course_includes_evidenced_steps_in_compiled_catalogue(self):
        data=self.with_course()
        for feature in data["features"]:feature["review"]["status"]="verified"
        data["course"]["project"]["capture_status"]="verified"
        data["course"]["learning_path"][0]["stages"][0]["binding"].update(status="verified",scene="lesson",step="quieter")
        proof=dict(passed=True,semantic_assertions=["Fourth note velocity 50"],sha256="screen-proof",grid_sha256="grid-proof")
        scenes=dict(self.catalogue,lesson=dict(id="lesson",steps=[dict(id="quieter",output=dict(binding=proof))]))
        with patch.object(book,"capture_catalogue",return_value=scenes),patch.object(book,"apply_overlays",side_effect=lambda scenes,overlay:scenes):
            result=book.compile_book(data)
        self.assertTrue(result["complete_manual"])
        self.assertIn("lesson",result["scenes"])

    def test_controlled_verified_content_can_complete_without_realtime_qualification_claim(self):
        data=copy.deepcopy(self.data)
        data.pop("course",None);data.pop("course_source",None)
        for feature in data["features"]:
            feature["review"]["status"]="controlled-verified"
            feature["review"]["validation_scope"]="controlled-manual-generation"
            feature["review"]["realtime_qualification"]="pending-ci"
        with patch.object(book,"apply_overlays",side_effect=lambda scenes,overlay:scenes):
            result=book.compile_book(data)
        self.assertTrue(result["complete_manual"])
        self.assertEqual(result["validation_scope"],"controlled-manual-generation")
        self.assertEqual(result["realtime_qualification"],"pending-ci")
        self.assertTrue(all(feature["review"]["status"]=="controlled-verified" for feature in result["features"]))

    def test_controlled_verified_course_requires_bound_native_semantics(self):
        data=self.with_course();data["course"]["project"]["capture_status"]="controlled-verified"
        binding=data["course"]["learning_path"][0]["stages"][0]["binding"]
        binding.update(status="controlled-verified",scene="lesson",step="quieter")
        proof=dict(passed=True,semantic_assertions=["Fourth note velocity 50"],sha256="screen-proof",grid_sha256="grid-proof")
        scenes=dict(book.capture_catalogue(),lesson=dict(id="lesson",steps=[dict(id="quieter",output=dict(binding=proof))]))
        data["course"]["project"].update(validation_scope="controlled-manual-generation",realtime_qualification="pending-ci")
        for feature in data["features"]:
            feature["review"].update(status="controlled-verified",validation_scope="controlled-manual-generation",realtime_qualification="pending-ci")
        with patch.object(book,"capture_catalogue",return_value=scenes),patch.object(book,"apply_overlays",side_effect=lambda scenes,overlay:scenes):
            result=book.compile_book(data)
        self.assertTrue(result["complete_manual"])
        proof["grid_sha256"]=""
        with patch.object(book,"capture_catalogue",return_value=scenes):
            with self.assertRaisesRegex(ValueError,"Unverified course binding"):
                book.compile_book(data)

if __name__=="__main__":unittest.main()

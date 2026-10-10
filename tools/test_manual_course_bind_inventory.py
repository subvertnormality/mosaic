"""Course binding takes its stage and checkpoint inventory from the authored course and plan.

Regression: check_course/check_lane hard-coded 38 stages and 50 checkpoints, so adding a
prepared starting point or a finer course stage (plan now 62+ steps) made binding fail.
The authored files stay the single source; every authored stage must still map once.
"""
import copy
import os
import sys
import unittest
from pathlib import Path

import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools")]
import manual_course_bind as bind


class CourseInventory(unittest.TestCase):
    def setUp(self):
        self.course = yaml.safe_load((REPO / "manual/course.yaml").read_text())
        self.plan = yaml.safe_load((REPO / "manual/scene-plans-course.yaml").read_text())
        # These tests concern the stage/step inventory, not recorded capture bindings, so inventory runs start
        # from pending bindings. Recorded-binding currency and stale rejection are asserted separately below.
        self.recorded_bindings = {s["id"]: s["binding"] for c in self.course["learning_path"] for s in c["stages"]}
        for chapter in self.course["learning_path"]:
            for stage in chapter["stages"]:
                stage["binding"] = dict(status="pending")

    def test_every_authored_stage_maps_whatever_the_count(self):
        mappings = bind.check_course(self.course, self.plan, verify_only=False, controlled_local=True)
        self.assertEqual(len(mappings), sum(len(c["stages"]) for c in self.course["learning_path"]))

    def test_an_added_stage_bound_to_a_plan_step_is_accepted(self):
        course, plan = copy.deepcopy(self.course), copy.deepcopy(self.plan)
        chapter = course["learning_path"][0]; scene = next(s for s in plan["scenes"] if s["feature_id"] == chapter["id"])
        scene["steps"].append(dict(scene["steps"][-1], id="extra-stage"))
        chapter["stages"].append(dict(chapter["stages"][-1], id="extra-stage", binding=dict(status="pending")))
        self.assertEqual(len(bind.check_course(course, plan, verify_only=False, controlled_local=True)), len(bind.check_course(self.course, self.plan, verify_only=False, controlled_local=True)) + 1)

    def test_duplicate_stage_ids_are_still_rejected(self):
        course = copy.deepcopy(self.course)
        course["learning_path"][1]["stages"].append(dict(course["learning_path"][0]["stages"][0], binding=dict(status="pending")))
        course["learning_path"][1]["stages"][-1]["id"] = course["learning_path"][0]["stages"][0]["id"]
        plan = copy.deepcopy(self.plan)
        scene = next(s for s in plan["scenes"] if s["feature_id"] == course["learning_path"][1]["id"])
        scene["steps"].append(dict(scene["steps"][-1], id=course["learning_path"][0]["stages"][0]["id"]))
        with self.assertRaisesRegex(ValueError, "distinct teaching stages"):
            bind.check_course(course, plan, verify_only=False, controlled_local=True)

    def test_recorded_bindings_are_current_and_a_stale_one_is_rejected(self):
        course = yaml.safe_load((REPO / "manual/course.yaml").read_text())
        steps = {s["feature_id"]: s for s in self.plan["scenes"]}
        def stale(course):
            return sorted(stage["id"] for chapter in course["learning_path"] for stage in chapter["stages"]
                          if stage["binding"].get("status") in ("verified", bind.CONTROLLED_STATUS)
                          and stage["binding"] != dict(status=stage["binding"]["status"], scene=steps[chapter["id"]]["id"], step=stage["id"]))
        # Renamed stages (masks-default-restore, sequence-composition-bass-route) were reset to pending on
        # 2026-10-06 for the fresh controlled campaign to rebind; any recorded binding that drifts is a defect.
        self.assertEqual(stale(course), [])
        chapter, stage = next((c, s) for c in course["learning_path"] for s in c["stages"]
                              if s["binding"].get("status") in ("verified", bind.CONTROLLED_STATUS))
        recorded = dict(stage["binding"])
        stage["binding"]["step"] = stage["id"] + "-previous-name"
        self.assertEqual(stale(course), [stage["id"]])
        with self.assertRaisesRegex(ValueError, "Existing course stage mapping differs"):
            bind.check_course(course, self.plan, verify_only=False, controlled_local=True)
        with self.assertRaisesRegex(ValueError, "Course stage mapping is not verified"):
            bind.check_course(course, self.plan, verify_only=True, controlled_local=True)
        # Rebound to its current plan step, the stage is accepted again.
        stage["binding"] = recorded
        self.assertEqual(len(bind.check_course(course, self.plan, verify_only=False, controlled_local=True)), sum(len(c["stages"]) for c in course["learning_path"]))


if __name__ == "__main__":
    unittest.main()

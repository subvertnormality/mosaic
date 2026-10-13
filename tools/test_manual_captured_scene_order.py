"""The controlled generation audit expects the capture tool's grouped scene order.

Regression from the isolated dry run (feature-bind): manual_case_capture captures
scenes grouped by (behaviour case, profile) in first-appearance order, so the
parameters report lists trig-parameter-locks beside fixed-note-default-and-locks.
The audit compared against plain plan order and rejected the genuine report.
"""
import os
import sys
import unittest
from pathlib import Path
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_publication_verify as verify


class CapturedSceneOrder(unittest.TestCase):
    def test_groups_by_case_and_profile_in_first_appearance_order(self):
        scenes = [dict(id="a", behaviour_case="X"), dict(id="b", behaviour_case="Y"),
                  dict(id="c", behaviour_case="X"), dict(id="d", behaviour_case="X", profile="midi-modulation")]
        self.assertEqual(verify.captured_scene_order(scenes), ["a", "c", "b", "d"])

    def test_matches_the_capture_tool_on_every_real_plan(self):
        import manual_case_capture
        for path in sorted((REPO / "manual").glob("scene-plans*.yaml")):
            scenes = (yaml.safe_load(path.read_text()) or {}).get("scenes", [])
            expected = [plan["id"] for group in manual_case_capture.group_plans(scenes) for plan in group]
            self.assertEqual(verify.captured_scene_order(scenes), expected, path.name)


if __name__ == "__main__":
    unittest.main()

"""Authored starting states describe each scene's prepared starting point.

They are editorial: compiled onto scenes without changing the native contract,
and unknown scene ids are rejected.
"""
import os
import sys
import unittest
from pathlib import Path

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_starting_states
import manual_publication_verify


class StartingStates(unittest.TestCase):
    def scenes(self):
        return {"a": {"id": "a", "steps": [{"id": "s1", "caption": "x", "inputs": [1, 2]}]}, "b": {"id": "b", "steps": []}}

    def test_applies_text_to_named_scenes_only(self):
        result = manual_starting_states.apply(self.scenes(), {"schema_version": 1, "starting_states": [{"scene_id": "a", "text": "Channel 1 plays Oilcan."}]})
        self.assertEqual(result["a"]["starting_state"], "Channel 1 plays Oilcan.")
        self.assertNotIn("starting_state", result["b"])

    def test_unknown_or_duplicate_scene_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown scene"):
            manual_starting_states.apply(self.scenes(), {"schema_version": 1, "starting_states": [{"scene_id": "zz", "text": "t"}]})
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            manual_starting_states.apply(self.scenes(), {"schema_version": 1, "starting_states": [{"scene_id": "a", "text": "t"}, {"scene_id": "a", "text": "u"}]})

    def test_empty_text_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "text"):
            manual_starting_states.apply(self.scenes(), {"schema_version": 1, "starting_states": [{"scene_id": "a", "text": " "}]})

    def test_scene_with_a_start_step_keeps_one_starting_description(self):
        # The "start" step's caption already describes the prepared starting point;
        # a second banner duplicated it and drifted (round-3 review contradictions).
        scenes = {"a": {"id": "a", "steps": [{"id": "start", "caption": "Channel 1 is routed."}, {"id": "s1"}]}}
        with self.assertRaisesRegex(ValueError, "start step"):
            manual_starting_states.apply(scenes, {"schema_version": 1, "starting_states": [{"scene_id": "a", "text": "Channel 1 is routed at 90 BPM."}]})

    def test_starting_state_is_editorial_for_the_native_contract(self):
        raw = self.scenes()["a"]
        compiled = dict(raw, starting_state="Prepared: channel 1 routed.")
        manual_publication_verify.check_compiled_scene_contract(raw, compiled)


if __name__ == "__main__":
    unittest.main()

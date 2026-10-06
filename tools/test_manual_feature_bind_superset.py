"""Reviewed scenes keep every exact acceptance checkpoint; teaching steps may be added.

The restructured Shared Strategy and Readability plans add prepared starting points
and intermediate teaching checkpoints. Feature binding must still require each
original acceptance checkpoint with its exact literals, and reject a missing one.
"""
import copy
import os
import sys
import unittest
from pathlib import Path

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_feature_bind as fb


def readability_scene():
    steps = [dict(id=i, output=dict(binding=dict(assertion=dict(v)))) for i, v in fb.READABILITY_CHECKPOINTS.items()]
    return dict(id="public-display-readability", behaviour_case="M-UI-READABILITY-001", steps=steps)


class SupersetAcceptance(unittest.TestCase):
    def test_extra_teaching_step_with_passed_assertion_is_accepted(self):
        scene = readability_scene()
        scene["steps"].insert(0, dict(id="start", output=dict(binding=dict(assertion=dict(kind="screen-header", passed=True)))))
        fb.verify_readability_scene(scene)

    def test_missing_acceptance_checkpoint_is_still_rejected(self):
        scene = readability_scene()
        scene["steps"] = scene["steps"][1:]
        with self.assertRaisesRegex(ValueError, "Readability requires"):
            fb.verify_readability_scene(scene)

    def test_changed_acceptance_literal_is_still_rejected(self):
        scene = readability_scene()
        scene["steps"][0]["output"]["binding"]["assertion"]["enabled"] = "changed"
        with self.assertRaisesRegex(ValueError, "literal selector changed"):
            fb.verify_readability_scene(scene)

    def test_extra_step_on_a_failed_row_is_rejected(self):
        scene = readability_scene()
        scene["steps"].append(dict(id="extra", output=dict(binding=dict(assertion=dict(kind="x", passed=False)))))
        with self.assertRaisesRegex(ValueError, "teaching checkpoint"):
            fb.verify_readability_scene(scene)


if __name__ == "__main__":
    unittest.main()

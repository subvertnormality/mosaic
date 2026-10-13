"""The scale-phase audio frame is bound to its own behaviour case.

Regression for build f718168dd9644747b9042e57a1c9b0d6 (raw-publication-audit):
check_frame was called without its case argument (TypeError).
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_publication_verify as verify


class ScalePhaseFrame(unittest.TestCase):
    def test_phase_frame_is_checked_against_the_scale_phase_case(self):
        phase = dict(output=dict(binding=dict(name="manual/MA-AUDIO-SCALE-PHASE/RootD")))
        with patch.object(verify, "check_frame") as check:
            verify.check_scale_phase_frame(phase, ["results"], ["observations"])
        check.assert_called_once_with(phase["output"], "MA-AUDIO-SCALE-PHASE", ["results"], ["observations"])


if __name__ == "__main__":
    unittest.main()

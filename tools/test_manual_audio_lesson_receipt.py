"""The lesson PCM receipt keeps its own result kind and the proof's kind.

Regression for run cc6b15a9f52b4130a8b1739d65e572d5: a passed ghost-note PCM
proof (kind "ghost-note-interiors") crashed the capture when its kind collided
with the receipt's own kind keyword.
"""
import os
import sys
import unittest
from pathlib import Path

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
import manual_audio


class LessonPcmReceipt(unittest.TestCase):
    def test_ghost_note_proof_produces_one_receipt_naming_both_kinds(self):
        proof = dict(kind="ghost-note-interiors", windows=[dict(step=43, rms=.02)], minimum_difference_ratio=1.5, passed=True)
        receipt = manual_audio.lesson_pcm_receipt(proof)
        self.assertEqual(receipt["kind"], "manual-audio-lesson-PCM")
        self.assertEqual(receipt["pcm_kind"], "ghost-note-interiors")
        self.assertEqual(receipt["windows"], proof["windows"])
        self.assertIs(receipt["passed"], True)
        self.assertEqual(proof["kind"], "ghost-note-interiors")


if __name__ == "__main__":
    unittest.main()

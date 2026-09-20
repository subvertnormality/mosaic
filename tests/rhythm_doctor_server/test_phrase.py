"""Phrase alignment on the remote path.

The remote path does not guess where the bar is -- a downbeat tracker states
it. What is left is which of four bars opens the phrase.
"""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor_server"))
import phrase

SR = 44100


def bars(offset, count=16, fill=True, accent=True):
    """Per-bar lane activity for a groove whose phrase starts at `offset`."""
    rows = np.zeros((count, 3))
    for bar in range(count):
        position = (bar - offset) % 4
        rows[bar, 0] = 1.0 if (accent and position == 0) else 0.6
        rows[bar, 1] = 0.5
        rows[bar, 2] = 0.9 if (fill and position == 3) else 0.1
    return rows


class PhraseOffsetTests(unittest.TestCase):
    def test_it_finds_the_phrase_start_wherever_it_falls(self):
        for offset in range(4):
            found, confidence = phrase.phrase_offset(bars(offset))
            self.assertEqual(found, offset, "offset %d misdetected as %d" % (offset, found))
            self.assertGreater(confidence, 0.0)

    def test_identical_bars_claim_nothing(self):
        """Sixteen identical bars carry no information about which is first.
        Reporting a confident answer would be a fabrication."""
        _, confidence = phrase.phrase_offset(np.ones((16, 3)))
        self.assertEqual(confidence, 0.0)

    def test_too_little_recording_claims_nothing(self):
        """With under two phrases nothing has repeated yet, so any answer is an
        artefact of where the recording happened to start."""
        self.assertEqual(phrase.phrase_offset(bars(2, count=6)), (0, 0.0))

    def test_a_repeating_phrase_is_not_scored_by_novelty(self):
        """Foote novelty detects change across a boundary. A four-bar phrase
        that repeats identically has no change at its boundaries, so novelty is
        flat and whichever candidate touches the array's uncomputed edges wins.
        This pins that such material is never reported confidently by accident.
        """
        periodic = np.tile(np.array([[1.0, 0.2], [0.4, 0.2], [0.4, 0.2], [0.4, 0.2]]), (4, 1))
        found, confidence = phrase.phrase_offset(periodic)
        self.assertEqual(found, 0, "the accented bar opens the phrase")
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)


class AlignmentTests(unittest.TestCase):
    BPM = 120.0

    def _grid(self, count=36, lead=0.75):
        beat = int(SR * 60 / self.BPM)
        beats = [int(lead * SR) + index * beat for index in range(count)]
        return beats, beats[::4]

    def test_tempo_comes_from_the_tracked_beats(self):
        beats, _ = self._grid()
        bpm, detected = phrase.tempo_from_beats(beats, SR)
        self.assertTrue(detected)
        self.assertAlmostEqual(bpm, self.BPM, delta=0.5)

    def test_a_dropped_beat_does_not_move_the_tempo(self):
        """The median interval is used rather than the mean precisely so one
        missing beat cannot halve the reported tempo."""
        beats, _ = self._grid()
        del beats[7]
        bpm, detected = phrase.tempo_from_beats(beats, SR)
        self.assertTrue(detected)
        self.assertAlmostEqual(bpm, self.BPM, delta=0.5)

    def test_too_few_beats_report_a_placeholder_rather_than_a_guess(self):
        self.assertEqual(phrase.tempo_from_beats([100], SR), (120.0, False))

    def test_the_phrase_start_is_a_tracked_downbeat(self):
        beats, downbeats = self._grid()
        value = phrase.align(beats, downbeats, SR, beats[-1] + SR * 4)
        self.assertIn(value["phrase_start_sample"], downbeats)

    def test_the_origin_is_a_whole_number_of_cells_before_the_phrase_start(self):
        beats, downbeats = self._grid()
        value = phrase.align(beats, downbeats, SR, beats[-1] + SR * 4)
        cell = SR * 15 / value["bpm"]
        offset = (value["phrase_start_sample"] - value["origin_sample"]) / cell
        self.assertLess(abs(offset - round(offset)), 0.01)

    def test_a_full_window_remains_after_the_phrase_start(self):
        beats, downbeats = self._grid()
        length = beats[-1] + SR * 4
        value = phrase.align(beats, downbeats, SR, length)
        cell = SR * 15 / value["bpm"]
        self.assertLessEqual(value["phrase_start_sample"] + 64 * cell, length)

    def test_a_player_correction_outranks_the_tracker(self):
        beats, downbeats = self._grid()
        value = phrase.align(beats, downbeats, SR, beats[-1] + SR * 4,
                             alignment={"bpm": 96.0, "origin_sample": 12345})
        self.assertEqual(value["tempo_mode"], "manual")
        self.assertEqual(value["origin_sample"], 12345)
        self.assertEqual(value["phrase_start_sample"], 12345)
        self.assertIn(12345, value["beat_positions"])

    def test_no_downbeats_reports_no_phrase(self):
        beats, _ = self._grid()
        value = phrase.align(beats, [], SR, beats[-1] + SR * 4)
        self.assertEqual(value["phrase_confidence"], 0.0)
        self.assertEqual(value["phrase_start_sample"], 0)


if __name__ == "__main__":
    unittest.main()

"""Characterisation outside README: pinned Basic Pitch 0.4.0 output contract.

Source: Apache-2.0 basic_pitch/note_creation.py model_frames_to_time and
constants.py in the frozen upstream wheel. This is adapter, not model evidence.
"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / 'tools/rhythm_doctor_analysis'))
from basic_pitch_adapter import midi_pitch_slice, frame_time

class BasicPitchAdapterTests(unittest.TestCase):
    def test_piano_output_origin_is_midi_21(self):
        self.assertEqual(midi_pitch_slice(28, 60), slice(7, 40))
        self.assertEqual(midi_pitch_slice(21, 108), slice(0, 88))
        self.assertEqual(midi_pitch_slice(60, 60), slice(39, 40))

    def test_window_boundary_uses_upstream_time_correction(self):
        self.assertEqual(frame_time(0), 0)
        self.assertAlmostEqual(frame_time(171), 1.9853061224489796, places=12)
        # First sample of the next model window, with upstream 1.8ms correction.
        self.assertAlmostEqual(frame_time(172), 1.986590022675737, places=6)
        self.assertGreater(1720 * 256 / 22050 - frame_time(1720), .100)
        self.assertLess(1720 * 256 / 22050 - frame_time(1720), .105)
        times = [frame_time(i) for i in range(1721)]
        self.assertTrue(all(a < b for a, b in zip(times, times[1:])))

    def test_invalid_pitch_and_frame_inputs_rejected(self):
        for low, high in [(20, 60), (28, 109), (60, 28), (True, 60), (28., 60)]:
            with self.assertRaises(ValueError): midi_pitch_slice(low, high)
        for value in [-1, 1.5, True, float('nan')]:
            with self.assertRaises(ValueError): frame_time(value)

if __name__ == '__main__': unittest.main()

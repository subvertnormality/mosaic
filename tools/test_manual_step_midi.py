"""Each captured checkpoint carries the MIDI the emulator actually emitted since the
scene's previous checkpoint, so the reader can show what a step sends."""
import os
import sys
import unittest
from pathlib import Path

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_case_capture as cap


def m(index, data, ns, port=1):
    return dict(index=index, port=port, bytes=data, logical_ns=ns, monotonic_ns=ns + 7)


class StepMidi(unittest.TestCase):
    def test_returns_channel_messages_after_the_previous_checkpoint_with_relative_time(self):
        midi = [m(1, [144, 60, 100], 0), m(2, [248], 10), m(3, [128, 60, 0], 500_000_000), m(4, [176, 74, 64], 600_000_000)]
        events, last, truncated = cap.step_midi(midi, previous_index=1, clock_mode="controlled-experimental")
        self.assertEqual(events, [dict(port=1, bytes=[128, 60, 0], ms=0.0), dict(port=1, bytes=[176, 74, 64], ms=100.0)])
        self.assertEqual(last, 4)
        self.assertFalse(truncated)

    def test_reports_truncation_when_the_tail_skipped_messages(self):
        events, last, truncated = cap.step_midi([m(10, [144, 60, 1], 0)], previous_index=3, clock_mode="controlled-experimental")
        self.assertTrue(truncated)
        self.assertEqual(last, 10)

    def test_uses_monotonic_time_in_real_time(self):
        events, _, _ = cap.step_midi([m(1, [144, 60, 1], 0), m(2, [144, 62, 1], 1_000_000)], previous_index=0, clock_mode="real-time")
        self.assertEqual([e["ms"] for e in events], [0.0, 1.0])


if __name__ == "__main__":
    unittest.main()

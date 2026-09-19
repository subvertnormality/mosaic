"""Characterisation tests for the RD-02 weak-template candidate only.

These tests protect label selection before any classifier or template is fit.
They intentionally use literal MIDI-derived records rather than predictions.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor_analysis"))
from nmf_template import select_isolated_events


class NmfTemplateTests(unittest.TestCase):
    def test_rejects_other_lane_inside_symmetric_isolation_window(self):
        events = [(1.00, "BD"), (1.12, "SD"), (2.00, "HH")]
        selected = select_isolated_events(events, "BD", radius=0.15, tail_gap=0.10)
        assert selected == []


    def test_requires_preceding_tail_gap_but_preserves_same_lane_when_clear(self):
        events = [(0.85, "HH"), (0.94, "BD"), (1.00, "BD"), (1.30, "BD")]
        selected = select_isolated_events(events, "BD", radius=0.15, tail_gap=0.10)
        assert selected == [1.30]


    def test_keeps_single_class_event_with_no_nearby_drum_onset(self):
        events = [(0.40, "HH"), (1.00, "BD"), (1.40, "TOM")]
        assert select_isolated_events(events, "BD", radius=0.15, tail_gap=0.10) == [1.00]


if __name__ == "__main__":
    unittest.main()

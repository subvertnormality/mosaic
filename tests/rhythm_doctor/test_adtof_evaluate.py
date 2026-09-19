"""Characterisation for RD-02's ADTOF diagnostic adapter only."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "tools" / "rhythm_doctor_analysis"))
from adtof_evaluate import ADTOF_LABEL_TO_LANE, ADTOF_LANE_INDEX, scored_lanes


class AdtofAdapterTests(unittest.TestCase):
    def test_upstream_five_label_order_maps_only_requested_drum_lanes(self):
        self.assertEqual(ADTOF_LABEL_TO_LANE, {35: 'BD', 38: 'SD', 47: 'TOM', 42: 'HH', 49: None})
        self.assertEqual(ADTOF_LANE_INDEX, {'BD': 0, 'SD': 1, 'TOM': 2, 'HH': 3})
        self.assertEqual(scored_lanes(), ('BD', 'SD', 'HH', 'TOM'))


if __name__ == '__main__':
    unittest.main()

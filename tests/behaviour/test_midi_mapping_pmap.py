"""Deterministic evidence for the native norns PMAP entry case."""

import sys
import unittest
from pathlib import Path

BEHAVIOUR = Path(__file__).resolve().parent
if str(BEHAVIOUR) not in sys.path:
    sys.path.insert(0, str(BEHAVIOUR))

from midi_mapping import pmap_semantic_fields


class PmapProjectionTests(unittest.TestCase):
    def test_key_order_does_not_change_result(self):
        first = '"sel_ch_vel":"{cc=20, ch=1, dev=1, in_lo=1, in_hi=2, accum=true, echo=false, value=2, out_lo=-1, out_hi=1}"'
        reordered = '"sel_ch_vel":"{out_hi=1, value=2, echo=false, accum=true, in_hi=2, in_lo=1, dev=1, ch=1, cc=20, out_lo=-1}"'
        self.assertEqual(pmap_semantic_fields(first), pmap_semantic_fields(reordered))
        self.assertEqual(pmap_semantic_fields(first), dict(
            parameter='sel_ch_vel',
            fields=['accum=true', 'cc=20', 'ch=1', 'dev=1', 'echo=false',
                    'in_hi=2', 'in_lo=1', 'out_hi=1', 'out_lo=-1', 'value=2'],
        ))

    def test_changed_value_and_parameter_remain_visible(self):
        line = '"sel_ch_vel":"{cc=20, ch=1, dev=1, in_lo=1, in_hi=2, accum=true}"'
        projection = pmap_semantic_fields(line)
        self.assertNotEqual(projection, pmap_semantic_fields(line.replace('cc=20', 'cc=21')))
        self.assertNotEqual(projection, pmap_semantic_fields(line.replace('sel_ch_vel', 'ch2_vel')))

    def test_duplicate_or_malformed_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            pmap_semantic_fields('"sel_ch_vel":"{cc=20, cc=21}"')
        with self.assertRaises(ValueError):
            pmap_semantic_fields('"sel_ch_vel":"{cc=20, broken}"')


if __name__ == '__main__':
    unittest.main()

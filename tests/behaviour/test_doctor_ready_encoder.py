"""Characterisation outside README: public Doctor encoder fixture boundary.

This tests the independent public action schema, not Mosaic's musical state.
No emulator is launched.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/behaviour'))
from contract.rhythm_doctor_options import _turn


class Fake:
    def __init__(self):
        self.calls = []
        owner = self
        class Ui:
            def rhythm_doctor_setup_field(self, delta):
                owner.calls.append(('enc', 2, delta))
            def adjust_rhythm_doctor_setup_value(self, delta):
                owner.calls.append(('enc', 3, delta))
        self.ui = Ui()
    def elapse(self, seconds):
        self.calls.append(('elapse', seconds))


class DoctorEncoderBoundaryTests(unittest.TestCase):
    def test_large_negative_request_preserves_total_inside_public_delta_bound(self):
        c = Fake()
        _turn(c, 3, -1000)
        events = [call for call in c.calls if call[0] == 'enc']
        self.assertTrue(events)
        self.assertTrue(all(type(event[2]) is int and -127 <= event[2] <= 127
                            for event in events), 'public action delta must be integer[-127,127]')
        self.assertEqual(sum(event[2] for event in events), -2000)
        for index, call in enumerate(c.calls):
            if call[0] == 'enc':
                self.assertGreater(index, 0)
                self.assertEqual(c.calls[index - 1][0], 'elapse')
                self.assertGreaterEqual(c.calls[index - 1][1], .06)
                self.assertEqual(c.calls[index + 1][0], 'elapse')
                self.assertGreaterEqual(c.calls[index + 1][1], .1)

    def test_both_signs_and_boundary_requests_preserve_public_input(self):
        for encoder in (2, 3):
            for steps in (-64, -63, -1, 1, 63, 64, 201):
                c = Fake()
                _turn(c, encoder, steps)
                events = [call for call in c.calls if call[0] == 'enc']
                self.assertTrue(all(event[1] == encoder for event in events))
                self.assertTrue(all(-127 <= event[2] <= 127 for event in events))
                self.assertEqual(sum(event[2] for event in events), steps * 2)

    def test_zero_sends_no_public_event_or_wait(self):
        c = Fake()
        _turn(c, 2, 0)
        self.assertEqual(c.calls, [])

    def test_invalid_types_fail_before_any_public_event(self):
        for steps in (True, False, 1.5, '1', None):
            c = Fake()
            with self.assertRaises((TypeError, ValueError)):
                _turn(c, 2, steps)
            self.assertEqual(c.calls, [])


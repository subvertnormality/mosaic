"""Characterise public Doctor destination navigation composition.

This helper-level regression exercises the current `_destination` function.
The real READY lane retains its exact R05 framebuffer, grid, MIDI and playback
assertions; this test does not launch Mosaic.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/behaviour'))
sys.path.insert(0, str(ROOT / 'tools'))
from contract import rhythm_doctor_options as recipe


class _Case:
    doctor_options_case_id = 'destination-navigation'

    def __init__(self, algorithm_5):
        self.ui = _Ui(algorithm_5)
        self.results = []

    def snapshot(self):
        return {'route': self.ui.route}


class _Ui:
    def __init__(self, algorithm_5):
        self.algorithm_5 = algorithm_5
        self.route = 'START'
        self.calls = []

    def tap_control(self, name, index=None):
        self.calls.append(('grid', name, index))
        if name == 'pattern_select':
            self.route = 'P01'

    def wait_for_header(self, route, **kwargs):
        self.calls.append(('wait', route, kwargs))
        assert route == 'trigger_editor' and self.route == 'P01'

    def select_rhythm_doctor_algorithm(self, algorithm):
        self.calls.append(('choose-algorithm', algorithm))
        assert algorithm == 'rhythm_doctor'
        if not self.algorithm_5:
            self.algorithm_5 = True
            self.route = 'R05'

    def open_task(self, context, task):
        self.calls.append(('open-task', context, task, self.route))
        if not self.algorithm_5:
            raise AssertionError('Rhythm Doctor task hidden while algorithm is not 5')
        assert self.route in ('P01', 'R05')
        self.route = 'R05'

    def expect_rhythm_doctor_header(self, route):
        self.calls.append(('expect-header', route))
        assert route == 'R05' and self.route == 'R05'


class DoctorDestinationNavigationTests(unittest.TestCase):
    def run_destination(self, algorithm_5):
        case = _Case(algorithm_5)
        with patch('manual_capture.frame', return_value={'frame': 'stub'}):
            recipe._destination(case, 4)
        self.assertEqual(case.results[-1]['pattern'], 4)
        self.assertEqual(case.results[-1]['route'], 'P01')
        self.assertTrue(case.results[-1]['passed'])
        labels = [call[0] for call in case.ui.calls]
        self.assertLess(labels.index('grid'), labels.index('choose-algorithm'))
        self.assertLess(labels.index('choose-algorithm'), labels.index('open-task'))
        self.assertLess(labels.index('open-task'), labels.index('expect-header'))
        self.assertEqual(case.ui.calls[-1], ('expect-header', 'R05'))
        return case

    def test_destination_on_another_algorithm_selects_doctor_then_uses_task_handoff(self):
        case = self.run_destination(False)
        self.assertEqual(case.ui.calls[-2], ('open-task', 'Trig', 'rhythm_doctor', 'R05'))

    def test_destination_already_using_doctor_keeps_task_handoff(self):
        case = self.run_destination(True)
        self.assertEqual(case.ui.calls[-2], ('open-task', 'Trig', 'rhythm_doctor', 'P01'))


if __name__ == '__main__':
    unittest.main()

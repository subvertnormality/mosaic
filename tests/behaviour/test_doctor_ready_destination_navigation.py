"""Characterise public Doctor destination navigation composition.

The READY behavior lane retains its native frame/grid/MIDI assertions. These
helper-level cases cover route selection and prove a destination change leaves
Paint disarmed; no undocumented key press may stand in for that transition.
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / 'tests/behaviour'))
sys.path.insert(0, str(ROOT / 'tools'))
from contract import rhythm_doctor_options as recipe


ROUTES = {
    'R05': ('WINDOW', 'vertical_list'),
    'R08': ('PAINT', 'vertical_list'),
}


def _header_matches(state, title, scope, layout):
    route = next((route for route, screen in ROUTES.items()
                  if screen == (title, layout)), None)
    return route is not None and state.get('route') == route and scope == 'CH01'


class _Case:
    doctor_options_case_id = 'destination-navigation'

    def __init__(self, algorithm_5, remembered_route='R05', preview_steps=(), disarm_on_destination=True):
        self.ui = _Ui(algorithm_5, remembered_route, disarm_on_destination)
        self.ui.case = self
        self.ui.grid = [0] * 128
        for step in preview_steps:
            x = (step - 1) % 16 + 1
            y = (step - 1) // 16 + 4
            self.ui.grid[(y - 1) * 16 + x - 1] = 12
        self.results = []

    def snapshot(self):
        return {'route': self.ui.route, 'grid': list(self.ui.grid)}

    def wait(self, predicate):
        self.ui.calls.append(('wait', self.ui.route))
        assert predicate(self.snapshot()), 'required observable output did not arrive'


class _Ui:
    def __init__(self, algorithm_5, remembered_route, disarm_on_destination=True):
        self.algorithm_5 = algorithm_5
        self.disarm_on_destination = disarm_on_destination
        self.remembered_route = remembered_route
        self.route = 'START'
        self.calls = []
        self.case = None
        self.grid = []

    def tap_control(self, name, index=None):
        self.calls.append(('grid', name, index))
        if name == 'pattern_select':
            self.route = 'P01'
            if self.disarm_on_destination and self.remembered_route == 'R08':
                self.remembered_route = 'R05'
                self.grid = [0] * 128
                self.calls.append(('paint-disarmed-on-destination-change',))

    def wait_for_header(self, route, **kwargs):
        self.calls.append(('wait-header', route, kwargs))
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
        self.route = self.remembered_route

    def _rhythm_doctor_screen(self, route):
        return ROUTES[route]

    def expect_rhythm_doctor_header(self, route):
        self.calls.append(('expect-header', route))
        assert route == 'R05' and self.route == 'R05'

class DoctorDestinationNavigationTests(unittest.TestCase):
    def run_destination(self, algorithm_5, remembered_route='R05', preview_steps=()):
        case = _Case(algorithm_5, remembered_route, preview_steps)
        with patch.object(recipe, 'live_header_matches', side_effect=_header_matches), \
             patch('manual_capture.frame', return_value={'frame': 'stub'}):
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

    def test_destination_on_another_algorithm_enters_window_without_back(self):
        case = self.run_destination(False)
        self.assertEqual(case.ui.route, 'R05')
        self.assertNotIn(('key', 2), case.ui.calls)
        self.assertIn(('wait', 'R05'), case.ui.calls)

    def test_destination_switch_disarms_remembered_paint_without_key_workaround(self):
        case = self.run_destination(True, remembered_route='R08')
        self.assertEqual(case.ui.route, 'R05')
        self.assertIn(('paint-disarmed-on-destination-change',), case.ui.calls)
        self.assertNotIn(('key', 2), case.ui.calls)
        self.assertIn(('wait', 'R05'), case.ui.calls)

    def test_empty_but_still_armed_paint_route_fails_closed_without_key_workaround(self):
        case = _Case(True, remembered_route='R08', disarm_on_destination=False)
        with patch.object(recipe, 'live_header_matches', side_effect=_header_matches), \
             patch('manual_capture.frame', return_value={'frame': 'stub'}):
            with self.assertRaisesRegex(AssertionError, 'required observable output'):
                recipe._destination(case, 4)
        self.assertNotIn(('key', 2), case.ui.calls)
        self.assertFalse(any(result.get('kind') == 'doctor-ready-destination' for result in case.results))

    def test_dim_and_bright_preview_block_completion_before_route_change(self):
        x, y = 1, 4
        cell = (y - 1) * 16 + x - 1
        for level in (12, 15):
            with self.subTest(level=level):
                case = _Case(True, remembered_route='R08', disarm_on_destination=False)
                case.ui.grid[cell] = level
                with patch.object(recipe, 'live_header_matches', side_effect=_header_matches), \
                     patch('manual_capture.frame', return_value={'frame': 'stub'}):
                    with self.assertRaisesRegex(AssertionError, 'required observable output'):
                        recipe._destination(case, 4)
                self.assertNotIn(('key', 2), case.ui.calls)
                self.assertFalse(case.results)

    def test_unrecognized_route_fails_closed_without_key_workaround(self):
        case = _Case(True, remembered_route='R06')
        with patch.object(recipe, 'live_header_matches', side_effect=_header_matches), \
             patch('manual_capture.frame', return_value={'frame': 'stub'}):
            with self.assertRaisesRegex(AssertionError, 'required observable output'):
                recipe._destination(case, 4)
        self.assertNotIn(('key', 2), case.ui.calls)
        self.assertFalse(case.results)


if __name__ == '__main__':
    unittest.main()
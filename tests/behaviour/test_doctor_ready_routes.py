"""Characterisation outside README: actual presentation-model hold returns.

Exercises the existing independent model and the owned recipe observer only.
No emulator startup, musical bank mutation or native frame claim.
"""
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/behaviour'))
sys.path.insert(0, str(ROOT / 'tools'))
from contract.rhythm_doctor_options import _toggle_destination_steps

model_spec = importlib.util.spec_from_file_location(
    'doctor_ready_presentation_model', ROOT / 'docs/ui-reimplementation/tools/model.py')
model = importlib.util.module_from_spec(model_spec)
model_spec.loader.exec_module(model)
SPEC = json.loads((ROOT / 'docs/ui-reimplementation/spec.json').read_text())


def toggle(state, step):
    state, _, _ = model.step(SPEC, state, 'hold.begin', {'steps': [step]})
    state, _, _ = model.step(SPEC, state, 'grid.outcome', {
        'flow_id': 'G21', 'target': {'channel': 1, 'pattern': 3}})
    state, _, _ = model.step(SPEC, state, 'hold.end')
    return state


class DoctorHeldRouteTests(unittest.TestCase):
    def test_g21_preserves_doctor_return_frame_until_release(self):
        state = model.initial('R05', 'Trig')
        state, _, _ = model.step(SPEC, state, 'hold.begin', {'steps': [3]})
        self.assertEqual(state['screen'], 'R05')
        self.assertTrue(state['return_stack'])
        state, _, _ = model.step(SPEC, state, 'grid.outcome', {'flow_id': 'G21'})
        self.assertEqual(state['screen'], 'P01')
        self.assertTrue(state['return_stack'])
        state, _, _ = model.step(SPEC, state, 'hold.end')
        self.assertEqual(state['screen'], 'R05')
        self.assertEqual(state['return_stack'], [])

    def test_g20_without_step_hold_remains_destination_p01(self):
        state, _, _ = model.step(SPEC, model.initial('R05', 'Trig'),
                                'grid.outcome', {'flow_id': 'G20'})
        self.assertEqual(state['screen'], 'P01')
        self.assertEqual(state['return_stack'], [])

    def test_recipe_observes_release_return_without_extra_navigation(self):
        test = self
        class Driver:
            def __init__(self):
                self.results = []
                self.state = model.initial('R05', 'Trig')
                self.ui = self
            def tap_control(self, name, number):
                test.assertEqual(name, 'step')
                self.state = toggle(self.state, number)
            def wait_for_header(self, name, **values):
                test.assertEqual(self.state['screen'], 'P01',
                                 'old observer incorrectly expects P01 after held-step release')
            def expect_rhythm_doctor_header(self, route):
                test.assertEqual(self.state['screen'], route)
            def open_task(self, *args):
                test.fail('release already returned R05; task navigation is unnecessary')
        c = Driver()
        with patch('manual_capture.frame', return_value={'model_only': True}):
            _toggle_destination_steps(c, [3, 9], 3)
        self.assertEqual(c.state['screen'], 'R05')
        self.assertEqual(c.results[-1]['route'], 'R05')
        self.assertIn('hold', c.results[-1]['citation'])


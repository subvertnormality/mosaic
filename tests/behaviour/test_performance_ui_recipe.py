"""Characterisation: preserve performance input/measurement boundaries exactly."""
import ast
import unittest
from pathlib import Path
from unittest.mock import patch

from ui import Ui
import perf_input


class Sink:
    def __init__(self):
        self.events = []

    def action(self, value):
        self.events.append(value)


class PerformanceUiRecipeTests(unittest.TestCase):
    def test_performance_modules_have_no_raw_ui(self):
        from ui_layer_guard import raw_sites
        for name in ('perf_calibration_emulator', 'perf_dense', 'perf_input', 'perf_overload'):
            self.assertEqual(raw_sites(Path(__file__).with_name(name + '.py')), [], name)

    def test_action_sink_keeps_native_input_and_pause_boundaries(self):
        sink = Sink()
        ui = Ui.for_action_sink(sink.action, lambda delay: sink.events.append(('pause', delay)), encoder_pause=.03)
        ui.tap_step(16)
        ui.press_key(1)
        ui.turn(3, -2)
        self.assertEqual(sink.events, [
            dict(type='grid', x=16, y=4, state=1), dict(type='grid', x=16, y=4, state=0), ('pause', .06),
            dict(type='key', n=1, state=1), dict(type='key', n=1, state=0), ('pause', .06),
            dict(type='enc', n=3, delta=-2), ('pause', .03)])

    def test_pressure_preserves_all_216_inputs_without_waits(self):
        sink = Sink()
        controls = perf_input.Controls(sink)
        with patch('perf_input.time.sleep') as sleep:
            latencies = controls.playback_pressure()
        expected = [dict(type='enc', n=1, delta=delta) for _ in range(80) for delta in (1, -1)]
        expected += [dict(type='grid', x=16, y=4, state=state) for _ in range(12) for state in (1, 0)]
        expected += [dict(type='grid', x=x, y=4, state=state) for _ in range(4)
                     for x, state in ((15, 1), (16, 1), (16, 0), (15, 0))]
        expected += [dict(type='key', n=1, state=state) for _ in range(8) for state in (1, 0)]
        self.assertEqual(sink.events, expected)
        self.assertEqual(controls.trace, expected)
        self.assertEqual(len(latencies), 216)
        sleep.assert_not_called()

    def test_fingerprint_preserves_degree_inputs_and_delays(self):
        import perf_overload
        sink = Sink()
        ui = Ui.for_action_sink(sink.action, lambda delay: sink.events.append(('pause', delay)))
        driver = type('Driver', (), {'ui': ui})()
        perf_overload.configure_fingerprint(driver)
        cells = [(5, 8), (5, 8)] + [(step, (7, 6, 5, 4)[(step-1) % 4]) for step in range(1, 17)] + [(3, 8)]
        expected = []
        for x, y in cells:
            expected += [dict(type='grid', x=x, y=y, state=1), dict(type='grid', x=x, y=y, state=0), ('pause', .06)]
        self.assertEqual(sink.events, expected)

    def test_render_pressure_uses_same_30_native_gestures(self):
        from ui_map import PERFORMANCE_RENDER_PRESSURE_SCHEDULE, performance_gesture_recipe
        sink = Sink()
        ui = Ui.for_action_sink(sink.action, lambda delay: self.fail('pressure added delay'))
        for _, _, gesture in PERFORMANCE_RENDER_PRESSURE_SCHEDULE:
            ui.performance_gesture(*gesture)
        legacy = [
            (.25, 'page-channel', ('grid', 3, 8)), (.50, 'channel-16', ('grid', 16, 1)), (.75, 'browse-forward', ('enc', 1, 2)),
            (1.00, 'page-trig', ('grid', 5, 8)), (1.25, 'page-song', ('grid', 6, 8)), (1.50, 'page-channel', ('grid', 3, 8)),
            (1.75, 'channel-1', ('grid', 1, 1)), (2.00, 'browse-back', ('enc', 1, -2)), (2.25, 'page-trig', ('grid', 5, 8)),
            (2.50, 'page-song', ('grid', 6, 8)), (2.75, 'page-channel', ('grid', 3, 8)), (3.00, 'channel-16', ('grid', 16, 1)),
            (3.25, 'browse-forward', ('enc', 1, 2)), (3.50, 'page-trig', ('grid', 5, 8)), (3.75, 'page-song', ('grid', 6, 8)),
            (4.00, 'page-channel', ('grid', 3, 8)), (4.25, 'channel-1', ('grid', 1, 1)), (4.50, 'browse-back', ('enc', 1, -2)),
            (4.75, 'page-trig', ('grid', 5, 8)), (5.00, 'page-song', ('grid', 6, 8)), (5.25, 'page-channel', ('grid', 3, 8)),
            (5.50, 'channel-16', ('grid', 16, 1)), (5.75, 'browse-forward', ('enc', 1, 2)), (6.00, 'page-trig', ('grid', 5, 8)),
            (6.25, 'page-song', ('grid', 6, 8)), (6.50, 'page-channel', ('grid', 3, 8)), (6.75, 'channel-1', ('grid', 1, 1)),
            (7.00, 'browse-back', ('enc', 1, -2)), (7.25, 'page-trig', ('grid', 5, 8)), (7.50, 'page-song', ('grid', 6, 8)),
        ]
        self.assertEqual([(offset, label, performance_gesture_recipe(gesture))
                          for offset, label, gesture in PERFORMANCE_RENDER_PRESSURE_SCHEDULE], legacy)
        expected = []
        for _, _, (kind, a, b) in legacy:
            if kind == 'grid':
                expected += [dict(type='grid', x=a, y=b, state=1), dict(type='grid', x=a, y=b, state=0)]
            else:
                expected.append(dict(type='enc', n=a, delta=b))
        self.assertEqual(len(PERFORMANCE_RENDER_PRESSURE_SCHEDULE), 30)
        self.assertEqual(sink.events, expected)

    def test_hardware_lane_consumes_semantic_schedule_without_extra_waits(self):
        from hardware_performance import HardwareLane
        from ui_map import PERFORMANCE_RENDER_PRESSURE_SCHEDULE, performance_gesture_recipe
        sink = Sink()
        ui = Ui.for_action_sink(sink.action, lambda delay: self.fail('hardware gesture added delay'))
        lane = HardwareLane(None, type('Driver', (), {
            'ui': ui, 'action': lambda self, **event: sink.action(event),
        })())
        expected = []
        for _, _, gesture in PERFORMANCE_RENDER_PRESSURE_SCHEDULE:
            self.assertIsNone(lane.gesture(*gesture))
            kind, a, b = performance_gesture_recipe(gesture)
            if kind == 'grid':
                expected.extend(dict(type='grid', x=a, y=b, state=state) for state in (1, 0))
            else:
                expected.append(dict(type='enc', n=a, delta=b))
        self.assertEqual(sink.events, expected)

    def test_velocity_levels_have_semantic_bounds_and_exact_cells(self):
        from ui_map import control_cell
        self.assertEqual(control_cell('pattern_velocity_level', (1, 7)), (1, 1))
        self.assertEqual(control_cell('pattern_velocity_level', (16, 1)), (16, 7))
        for invalid in ((0, 1), (17, 1), (1, 0), (1, 8), (1, True), (1,)):
            with self.assertRaises(ValueError):
                control_cell('pattern_velocity_level', invalid)


if __name__ == '__main__':
    unittest.main()

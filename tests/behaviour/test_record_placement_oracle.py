from unittest.mock import patch
from cases import recorded_chord_release
from ui import Ui
import unittest

from record_placement_oracle import derive_boundary_recorded_step


class BoundaryRecordedStepTests(unittest.TestCase):
    def test_equal_deadline_witness_selects_the_step_active_at_processing(self):
        self.assertEqual(derive_boundary_recorded_step(60, 62, (1, 2)), 1)
        self.assertEqual(derive_boundary_recorded_step(62, 64, (1, 2)), 2)
        self.assertEqual(derive_boundary_recorded_step(64, 65, (3, 4)), 3)
        self.assertEqual(derive_boundary_recorded_step(65, 60, (3, 4)), 4)

    def test_nonadjacent_or_out_of_range_witness_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'adjacent'):
            derive_boundary_recorded_step(60, 64, (1, 2))
        with self.assertRaisesRegex(AssertionError, 'candidate'):
            derive_boundary_recorded_step(60, 62, (2, 3))

# Post-disarm stimulus regressions; the clock is simulated
class CaptureFinished(Exception):
    pass

class Simulation:
    clock_mode = 'real-time'

    def __init__(self, release_delay=0):
        self.now = 0
        self.results = []
        self.armed = False
        self.recorded = []
        self.pending = []
        self.midi = []
        self.schedule = {'events': [], 'delivered': []}
        self.native_schedule = None
        self.release_delay = release_delay
        self.ui = SimulationUi(self)

    def snapshot(self):
        return {'midi_count': len(self.midi), 'midi': list(self.midi),
                'midi_input_schedule': self.schedule,
                'native_input_schedule': self.native_schedule}

    def action(self, **action):
        if action['type'] == 'midi_schedule':
            self.schedule = {'events': action['events'], 'delivered': []}
            self.pending.extend((e['at_monotonic_ns'], 'midi', e) for e in action['events'])
        elif action['type'] == 'native_input_schedule':
            self.native_schedule = {'status': 'accepted', 'delivered': []}
            for e in action['events']:
                delay = self.release_delay if e['state'] == 0 else 0
                self.pending.append((e['at_monotonic_ns'] + delay, 'grid', e))
        else:
            raise AssertionError(action)

    def advance(self, target):
        for stamp, kind, event in sorted(self.pending, key=lambda row: row[0]):
            if stamp > target:
                continue
            if kind == 'grid':
                if event['state'] == 0:
                    self.armed = False
                self.native_schedule['delivered'].append({
                    'action': {k: v for k, v in event.items() if k != 'at_monotonic_ns'},
                    'callback_completed_monotonic_ns': stamp,
                })
                if len(self.native_schedule['delivered']) == 2:
                    self.native_schedule['status'] = 'completed'
            else:
                data = event['bytes']
                self.schedule['delivered'].append(dict(event, actual_monotonic_ns=stamp))
                self.midi.append({'index': len(self.midi) + 1, 'port': 1,
                                  'bytes': data, 'monotonic_ns': stamp})
                if data[0] == 144 and self.armed:
                    self.recorded.append(data[1])
        self.pending = [row for row in self.pending if row[0] > target]
        self.now = target

    def elapse(self, seconds):
        self.advance(self.now + round(seconds * 1e9))

    def wait(self, predicate, timeout=3):
        if not predicate(self.snapshot()):
            origin = min(e['at_monotonic_ns'] for e in self.schedule['events'])
            self.advance(max(self.now, origin + 80_000_000))
        if not predicate(self.snapshot()):
            self.advance(max(row[0] for row in self.pending))
        assert predicate(self.snapshot())
        return self.snapshot()

class SimulationUi:
    grid_events_at = Ui.grid_events_at

    def __init__(self, driver):
        self.driver = driver
        self.play_count = 0

    def configure(self):
        pass

    def tap_control(self, control):
        if control == 'record':
            if self.driver.armed:
                # A delayed client release reproduces the original CI race.
                self.driver.elapse(.04)
            self.driver.armed = not self.driver.armed
        elif control == 'play_stop':
            self.play_count += 1
            if self.play_count > 1:
                raise CaptureFinished()
            self.driver.midi.append({'index': 1, 'port': 1, 'bytes': [144, 60, 127],
                                     'monotonic_ns': self.driver.now})
        else:
            raise AssertionError(control)

class RecordedChordStimulusOrderTests(unittest.TestCase):
    def test_delayed_client_cannot_record_the_post_disarm_preview(self):
        case = Simulation()
        with patch('time.monotonic_ns', side_effect=lambda: case.now):
            with self.assertRaises(CaptureFinished):
                recorded_chord_release(case, preview_release_ns=250_000_000)
        self.assertEqual(case.recorded, [72, 76, 79])

    def test_late_native_disarm_is_rejected_as_invalid_stimulus(self):
        case = Simulation(release_delay=120_000_000)
        with patch('time.monotonic_ns', side_effect=lambda: case.now):
            with self.assertRaisesRegex(AssertionError, 'post-disarm stimulus order'):
                recorded_chord_release(case, preview_release_ns=250_000_000)

"""Recipe guards for documented stopped-only Doctor Record.

Execute the authored public-input recipe with observation doubles. These tests
prove gesture/oracle coverage and cleanup structure, not native acceptance.
"""
import sys
import json
import hashlib
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/behaviour'))
from contract import rhythm_doctor_options as recipe


class ReadyTransportCoverage(unittest.TestCase):
    def execute(self, fail_held=False, fail_output=False):
        events = []
        class UI:
            playing = False
            held = False
            def play(self):
                self.playing = True
                events.append(('play',))
                owner.recipe.append(dict(type='grid', x=1, y=8, state=1))
                owner.recipe.append(dict(type='grid', x=1, y=8, state=0))
            def stop(self):
                self.playing = False
                events.append(('stop',))
                owner.recipe.append(dict(type='grid', x=1, y=8, state=1))
                owner.recipe.append(dict(type='grid', x=1, y=8, state=0))
            def rhythm_doctor_capture_edge(self, pressed):
                self.held = pressed
                events.append(('record', self.playing, pressed))
                owner.recipe.append(dict(type='grid', x=1, y=2, state=int(pressed)))
            def expect_rhythm_doctor_header(self, route):
                events.append(('header', self.playing, self.held, route))
                if fail_held and self.playing and self.held:
                    raise AssertionError('visible route changed while Record held')
            def select_rhythm_doctor_lane(self, lane):
                events.append(('lane', self.playing, lane))
            def _rhythm_doctor_screen(self, route):
                return ('native title', 'native layout')
            def __getattr__(self, name):
                return lambda *args, **kwargs: None
        class Driver:
            def __init__(self):
                self.ui = UI()
                self.results = []
                self.observations = []
                self.recipe = []
                self.fail_output = fail_output
                self.wait_evaluations = []
                self.midi = [{'index': 1, 'port': 1, 'bytes': [144, 60, 100]}]
            def _state(self):
                return {'frame': {'sha256': 'f' * 64}, 'grid': [0] * 128,
                        'midi_capture': {'outstanding': []},
                        'midi_count': len(self.midi), 'midi': list(self.midi)}
            def snapshot(self):
                state = self._state()
                self.observations.append({'state': state})
                return state
            def elapse(self, seconds):
                pass
            def wait(self, predicate, timeout=3):
                probes = [self._state()]
                if self.ui.playing:
                    self.midi.append({'index': 2, 'port': 1, 'bytes': [144, 60, 99]})
                    probes.append(self._state())
                    if not self.fail_output:
                        self.midi.append({'index': 3, 'port': 1, 'bytes': [144, 60, 100]})
                        probes.append(self._state())
                for state in probes:
                    matched = predicate(state)
                    observed = tuple((m['index'], m['port'], tuple(m['bytes'])) for m in state['midi'])
                    self.wait_evaluations.append((self.ui.playing, self.ui.held, matched, observed, timeout))
                    events.append(('wait-eval', self.ui.playing, self.ui.held, matched, observed, timeout))
                    if matched:
                        return state
                raise AssertionError('Required observable output did not arrive')
        c = Driver()
        owner = c
        fixture = dict(window_max=173, bank_bpm=120, beat_count=60,
                       masks_by_sensitivity={'0': [], '1': [], '0.5': [10]},
                       midi_expected=[[1, [144, 60, 100]]],
                       acquisition_report='genuine-fixture-path')
        with ExitStack() as stack:
            for name in ('_qualify_fixture', '_select', '_turn', '_key',
                         '_browse', '_destination', '_toggle_destination_steps',
                         '_ready_playback'):
                stack.enter_context(patch.object(recipe, name))
            stack.enter_context(patch.object(recipe, '_saved_phrase_cell', return_value=0))
            stack.enter_context(patch.object(recipe, 'live_header_matches', return_value=True))
            stack.enter_context(patch.object(recipe, 'selected_field_matches', return_value=True))
            stack.enter_context(patch.object(recipe, '_field', side_effect=lambda c, route, label, value:
                events.append(('field', c.ui.playing, route, label, value))))
            stack.enter_context(patch.object(recipe, '_mask', side_effect=lambda c, steps, preview=False:
                events.append(('mask', c.ui.playing, tuple(sorted(steps)), preview))))
            try:
                recipe.ready_options(c, fixture)
            except AssertionError:
                if not (fail_held or fail_output):
                    raise
                return events, c, True
        return events, c, False

    def test_playing_record_waits_for_new_exact_fixture_midi_before_record(self):
        events, c, _ = self.execute()
        playing_waits = [row for row in events if row[0] == 'wait-eval' and row[1]]
        self.assertEqual([row[3] for row in playing_waits], [False, False, True],
                         'wait must reject stale and wrong-payload MIDI before accepting the new fixture note')
        self.assertTrue(all(abs(row[5] - (64 + 10) / 6) < 1e-9 for row in playing_waits),
                        'musical onset deadline must derive from one cycle plus the lane first gate')
        record_index = events.index(('record', True, True))
        accepted_index = max(i for i, row in enumerate(events)
                            if row[0] == 'wait-eval' and row[1] and row[3])
        self.assertLess(accepted_index, record_index,
                        'Record refusal must be exercised only after new playing MIDI is observed')
        self.assertIn((3, 1, (144, 60, 100)), playing_waits[-1][4])

    def test_missing_playing_midi_times_out_and_releases_transport(self):
        events, c, failed = self.execute(fail_output=True)
        self.assertTrue(failed, 'missing actual musical output must fail the READY recipe')
        self.assertFalse(c.ui.held)
        self.assertFalse(c.ui.playing, 'timeout must stop public playback in finally')
        self.assertFalse(any(row == ('record', True, True) for row in events),
                         'the refusal gesture must not run without prior MIDI output')

    def test_public_record_press_and_release_are_exercised_while_playing(self):
        events, _, _ = self.execute()
        down = ('record', True, True)
        up = ('record', True, False)
        self.assertIn(down, events, 'READY recipe omits public Record while playing')
        start = events.index(down)
        end = events.index(up, start)
        self.assertIn(('header', True, True, 'R05'), events[start:end])
        self.assertIn(('field', True, 'R05', 'Alignment', 'OPEN >'), events[start:end])
        self.assertIn(('header', True, False, 'R05'), events[end:])
        self.assertIn(('lane', True, 'SD'), events[end:])

    def test_failed_held_route_observation_releases_record_and_stops(self):
        events, c, failed = self.execute(fail_held=True)
        self.assertTrue(failed, 'public held Record route observation was never exercised')
        self.assertFalse(c.ui.held)
        self.assertFalse(c.ui.playing)
        self.assertEqual(events[-2:], [('record', True, False), ('stop',)])

    def test_after_stop_original_mask_and_bank_tempo_are_observed(self):
        events, c, _ = self.execute()
        self.assertIn(('mask', False, (10,), False), events)
        rows = [row for row in c.results if row.get('check') == 'playing-record-refused']
        self.assertEqual(len(rows), 1, 'no explicit public transport Record result')
        self.assertEqual(rows[0]['bank_bpm'], 120)
        self.assertEqual(rows[0]['steps'], [10])
        self.assertTrue(rows[0]['released'])
        self.assertEqual(rows[0]['route'], 'R05')
        self.assertEqual(rows[0]['contract'], 'README.md#rhythm-doctor')
        self.assertIn(('field', False, 'R06', 'Half tempo', 120), events)

    def test_record_refusal_witnesses_bind_exact_observations_and_input_prefixes(self):
        _, c, _ = self.execute()
        row = next(row for row in c.results if row.get('check') == 'playing-record-refused')
        self.assertIn('witnesses', row, 'Record acceptance lacks independently bound native witnesses')
        names = ['pre_play', 'held_record', 'released_record', 'post_stop_mask', 'stopped_bpm', 'end']
        self.assertEqual(list(row['witnesses']), names)
        previous = -1
        for name in names:
            witness = row['witnesses'][name]
            index = witness['observation_index']
            self.assertGreater(index, previous)
            previous = index
            state = c.observations[index]['state']
            wanted = hashlib.sha256(json.dumps(state, sort_keys=True, separators=(',', ':'),
                                               ensure_ascii=True).encode()).hexdigest()
            self.assertEqual(witness['state_sha256'], wanted)
            self.assertEqual(witness['frame_sha256'], state['frame']['sha256'])
        held = row['witnesses']['held_record']['recipe_index']
        released = row['witnesses']['released_record']['recipe_index']
        self.assertEqual(c.recipe[held-1], dict(type='grid', x=1, y=2, state=1))
        self.assertEqual(c.recipe[released-1], dict(type='grid', x=1, y=2, state=0))
        self.assertLess(row['witnesses']['pre_play']['recipe_index'], held)
        self.assertGreater(row['witnesses']['post_stop_mask']['recipe_index'], released)

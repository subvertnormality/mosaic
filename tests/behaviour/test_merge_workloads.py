"""Host tests for the Interlock device-timing campaign (plan §1.4).

The physical runs are release-gating and outstanding; these tests verify the
case definitions, capture durations, the pure admission/propagation/latency
and timing oracles, and the device-run orchestration against fakes.
"""
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hardware_performance
import merge_workloads as mw
from hardware_performance import CASES, TIMING_THRESHOLDS
from ui import Ui
from ui_map import control_cell

STEP_NS = round(15 / 130 * 1e9)
PLAY = control_cell('play_stop')
STEP1 = control_cell('step', 1)


def build(index, time, pulse, channel, k, expectation, leader_trig):
    status, cycles, anchors, plan_builds, candidates, removed, other, eligible, admitted = expectation
    return {'kind': 1, 'index': index, 'time': time, 'pulse': pulse, 'channel': channel, 'k': k, 'status': status,
            'cycles': cycles, 'anchors': anchors, 'plan_builds': plan_builds, 'eligible': eligible, 'admitted': admitted,
            'candidates': candidates, 'removed': removed, 'other': other, 'leader_trig': leader_trig,
            'build_us': 900, 'heap_kb': 2048, 'heap_delta_bytes': 4096}


def key(index, time, cell, leader_trig, k, kind=2):
    """A recorder grid row: kind 2 key-down, 3 key-up."""
    return {'kind': kind, 'index': index, 'time': time, 'pulse': 0, 'x': cell[0], 'y': cell[1], 'leader_trig': leader_trig,
            'k': {c: k for c in range(2, 17)}}


def worst_rows(wraps=3, edits=(), start=100.0, cycle_s=64 * 15 / 130):
    """Recorder rows of a WORST/EDIT window: Start, per-cycle wraps of all 15
    followers on one pulse, and each edit followed by an in-cycle rebuild.
    An edit is a step-1 tap as the device records it: Mosaic applies the tap
    on its release, so the key-down row still shows the old leader trig and
    the key-up row (placed before the rebuilds it causes) the new one."""
    rows = []
    state = 1

    def add(row):
        row['index'] = len(rows) + 1
        rows.append(row)

    add(key(0, start - .04, PLAY, state, -99))
    add(key(0, start, PLAY, state, -99, kind=3))   # Start acts on the key-up
    for c in range(1, 17):
        add(build(0, start + .001, 0, c, -99, (0,) * 9 if c == 1 else mw.VARIANTS['WORST']['on'](-99), state))
    pending = sorted(edits)
    for k in range(1, wraps + 1):
        wrap_time = start + k * cycle_s
        while pending and pending[0] < wrap_time:
            at = pending.pop(0)
            add(key(0, at, STEP1, state, k - 1))
            state = 1 - state
            add(key(0, at + .04, STEP1, state, k - 1, kind=3))
            for c in range(2, 17):
                add(build(0, at + .01, 5, c, k - 1, mw.VARIANTS['WORST']['on' if state else 'off'](k - 1), state))
        for c in range(2, 17):
            add(build(0, wrap_time, 1536 * k, c, k, mw.VARIANTS['WORST']['on' if state else 'off'](k), state))
    return rows


def note_events(times_by_channel, start_index=1, length_ns=20_000_000):
    events = []
    for channel, times in times_by_channel.items():
        for t in times:
            events.append((t, [144 + channel, 60, 100]))
            events.append((t + length_ns, [128 + channel, 60, 0]))
    events.sort(key=lambda row: (row[0], row[1][0] & 240, row[1][0]))
    return [{'index': start_index + i, 'monotonic_ns': t, 'port': 1, 'bytes': b} for i, (t, b) in enumerate(events)]


def worst_midi(origin_ns, seconds, late=None):
    """Leader every sixteenth; followers only their step-1 anchor (trig on)."""
    steps = int(seconds / (STEP_NS / 1e9)) + 1
    times = {0: [origin_ns + s * STEP_NS for s in range(steps)]}
    for c in range(1, 16):
        times[c] = [origin_ns + s * STEP_NS for s in range(0, steps, 64)]
    for channel, index, delta in (late or []):
        times[channel][index] += delta
    return note_events(times)


class CaseDefinitions(unittest.TestCase):
    def test_the_five_plan_cases_are_registered_on_the_dense_16_channel_project_at_130_bpm(self):
        merge = {case for case in CASES if case.startswith('PERF-MERGE-HW-')}
        self.assertEqual(merge, {'PERF-MERGE-HW-STEADY', 'PERF-MERGE-HW-WORST', 'PERF-MERGE-HW-EDIT',
                                 'PERF-MERGE-HW-DENSE', 'PERF-MERGE-HW-DENSE-EDIT'})
        for case in merge:
            self.assertEqual((CASES[case]['workload'], CASES[case]['channels'], CASES[case]['tempo_bpm']), ('dense', 16, 130))
            self.assertEqual(hardware_performance.project_fixture_name(case), 'dense-16')
            with self.assertRaisesRegex(ValueError, 'runs at 130 bpm, not 120'):
                hardware_performance.case_tempo(case, 120)
        self.assertEqual({case: CASES[case]['variant'] for case in merge},
                         {'PERF-MERGE-HW-STEADY': 'STEADY', 'PERF-MERGE-HW-WORST': 'WORST', 'PERF-MERGE-HW-EDIT': 'WORST',
                          'PERF-MERGE-HW-DENSE': 'DENSE', 'PERF-MERGE-HW-DENSE-EDIT': 'DENSE'})

    def test_capture_durations_cover_three_cycles_of_the_slowest_follower(self):
        # §1.4: WORST/EDIT 48 beats (~22 s), DENSE/DENSE-EDIT 192 beats
        # (~88.6 s), STEADY 12 beats raised to the 8 s default.
        self.assertEqual(CASES['PERF-MERGE-HW-STEADY']['seconds'], 8.0)
        for case in ('PERF-MERGE-HW-WORST', 'PERF-MERGE-HW-EDIT'):
            self.assertAlmostEqual(CASES[case]['seconds'], 48 * 60 / 130)
        for case in ('PERF-MERGE-HW-DENSE', 'PERF-MERGE-HW-DENSE-EDIT'):
            self.assertAlmostEqual(CASES[case]['seconds'], 192 * 60 / 130)
        self.assertAlmostEqual(round(CASES['PERF-MERGE-HW-DENSE']['seconds'], 1), 88.6)
        self.assertEqual(mw.capture_seconds('STEADY', minimum=0), 12 * 60 / 130)

    def test_edits_follow_the_plan_period_and_stay_off_the_follower_wraps(self):
        edit = CASES['PERF-MERGE-HW-EDIT']
        offsets = mw.edit_offsets_beats(edit['edit_every_beats'], edit['seconds'], 130, mw.follower_step_beats('WORST') / 2)
        self.assertEqual(offsets, [8.125, 16.125, 24.125, 32.125, 40.125])  # every two bars
        dense = CASES['PERF-MERGE-HW-DENSE-EDIT']
        offsets = mw.edit_offsets_beats(dense['edit_every_beats'], dense['seconds'], 130, mw.follower_step_beats('DENSE') / 2)
        self.assertEqual(offsets, [16 * n + .5 for n in range(1, 12)])  # every 16 beats
        for value in offsets:
            self.assertNotEqual(value % 64, 0)
        self.assertIsNone(CASES['PERF-MERGE-HW-WORST']['edit_every_beats'])
        self.assertIsNone(CASES['PERF-MERGE-HW-DENSE']['edit_every_beats'])

    def test_thresholds_are_the_shared_unchanged_gates(self):
        self.assertEqual(TIMING_THRESHOLDS['step_jitter_maximum_ns'], 10_000_000)
        self.assertFalse(hasattr(mw, 'TIMING_THRESHOLDS'))
        self.assertFalse(hasattr(hardware_performance, 'MERGE_TIMING_THRESHOLDS'))

    def test_expected_admissions_are_the_plan_figures(self):
        self.assertEqual(mw.VARIANTS['WORST']['on'](5), (1, 64, 64, 0, 31, 31, 0, 0, 0))
        self.assertEqual(mw.VARIANTS['WORST']['off'](5), (1, 64, 0, 0, 31, 0, 0, 31, 31))
        self.assertEqual(mw.VARIANTS['DENSE']['on'](5), (1, 64, 4096, 0, 64, 64, 0, 0, 0))
        self.assertEqual(mw.VARIANTS['DENSE']['off'](5), (1, 64, 4032, 0, 64, 0, 0, 64, 64))
        self.assertEqual(mw.VARIANTS['STEADY']['on'](0)[:4], (1, 2, 8, 0))
        self.assertEqual(mw.VARIANTS['STEADY']['on'](4)[:4], (1, 3, 12, 0))


class WorkloadChunk(unittest.TestCase):
    def test_chunk_is_ascii_and_defines_the_workload_api(self):
        text = mw.WORKLOAD_LUA.read_text()
        self.assertTrue(all(ord(ch) < 127 for ch in text))
        for name in ('configure', 'install', 'reset', 'dump', 'count', 'remove', 'rows'):
            self.assertRegex(text, r'function W\.%s\(' % name)

    def test_string_literal_round_trips_through_lua(self):
        if not shutil.which('lua'):
            self.skipTest('lua interpreter unavailable')
        sample = 'a "quoted" \\ back\nline\ttab -- end'
        with tempfile.NamedTemporaryFile('w', suffix='.lua', delete=False) as handle:
            handle.write('io.write(%s)' % mw.lua_string_literal(sample))
        self.assertEqual(subprocess.check_output(['lua', handle.name]).decode(), sample)
        with self.assertRaisesRegex(ValueError, 'ASCII'):
            mw.lua_string_literal('café')

    def test_install_command_fits_the_matron_repl_line_and_names_the_installed_file(self):
        from real_norns import REPL_LINE_LIMIT, check_repl_lines
        command = mw.install_command()
        self.assertIn(mw.DEVICE_WORKLOAD_PATH, command)
        self.assertTrue(mw.DEVICE_WORKLOAD_PATH.endswith('/' + mw.WORKLOAD_LUA.relative_to(mw.WORKLOAD_LUA.parents[2]).as_posix()))
        payload = (command + "; print('__MOSAIC_HW_0000000000000000__')\n").encode() + b'\0'
        check_repl_lines(payload)
        self.assertLess(len(command) + 40, REPL_LINE_LIMIT)
        # The inline chunk this replaces is longer than one REPL line.
        with self.assertRaises(ValueError):
            check_repl_lines((mw.install_chunk() + '\n').encode() + b'\0')

    def test_install_chunk_loads_the_workload_in_plain_lua(self):
        if not shutil.which('lua'):
            self.skipTest('lua interpreter unavailable')
        command = mw.install_chunk()
        self.assertNotIn('\n', command)
        with tempfile.NamedTemporaryFile('w', suffix='.lua', delete=False) as handle:
            handle.write('function include() return {} end\n' + command + '\n')
        self.assertIn('__MERGE_WORKLOAD__true', subprocess.check_output(['lua', handle.name]).decode())

    def test_dump_lines_parse_into_build_and_key_rows(self):
        output = '\n'.join(['noise', '__MERGE_ROW__1|2,12.500000000,7,1,8,4,-1,1,1,1,1,1,1,1,1,1,1,1,1,1,1',
                            '__MERGE_ROW__2|1,12.600000000,8,3,1,1,64,64,0,0,0,31,31,0,1',
                            '__MERGE_ROW__3|3,12.700000000,9,1,4,0,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2'])
        rows = mw.parse_rows(output)
        self.assertEqual((rows[2]['kind'], rows[2]['x'], rows[2]['y'], rows[2]['leader_trig'], rows[2]['k'][9]), (3, 1, 4, 0, 2))
        self.assertEqual((rows[0]['kind'], rows[0]['x'], rows[0]['y'], rows[0]['leader_trig'], rows[0]['k'][2], rows[0]['k'][16]),
                         (2, 1, 8, 4, -1, 1))
        self.assertEqual(mw._admission_tuple(rows[1]), (1, 64, 64, 0, 31, 31, 0, 0, 0))
        self.assertEqual((rows[1]['index'], rows[1]['channel'], rows[1]['k'], rows[1]['time']), (2, 3, 1, 12.6))


class AdmissionOracle(unittest.TestCase):
    def test_worst_window_passes(self):
        report = mw.admission_oracle('WORST', worst_rows(), STEP1)
        self.assertTrue(report['passed'], report['failures'])
        self.assertEqual((report['admissions_checked'], report['complete_wraps'], report['edits']), (60, 3, 0))

    def test_any_admission_off_the_plan_figures_fails(self):
        rows = worst_rows()
        rows[20]['anchors'] = 63
        report = mw.admission_oracle('WORST', rows, STEP1)
        self.assertFalse(report['passed'])
        self.assertEqual(report['failures'][0]['kind'], 'admission')
        rows = worst_rows()
        rows[20]['plan_builds'] = 1
        self.assertFalse(mw.admission_oracle('WORST', rows, STEP1)['passed'])
        rows = worst_rows()
        rows[20]['status'] = 3  # PLAN LIMIT
        self.assertFalse(mw.admission_oracle('WORST', rows, STEP1)['passed'])

    def test_followers_must_wrap_on_one_pulse_and_the_capture_must_cover_the_cycles(self):
        rows = worst_rows()
        next(row for row in rows if row['kind'] == 1 and row['k'] == 2 and row['channel'] == 9)['pulse'] += 1
        self.assertEqual(mw.admission_oracle('WORST', rows, STEP1)['failures'][0]['kind'], 'wrap-pulse')
        report = mw.admission_oracle('WORST', worst_rows(wraps=1), STEP1)
        self.assertEqual(report['failures'][0]['kind'], 'capture-too-short')

    def test_the_leader_never_carries_an_interlock_record(self):
        rows = worst_rows()
        next(row for row in rows if row['kind'] == 1 and row['channel'] == 1)['status'] = 1
        self.assertEqual(mw.admission_oracle('WORST', rows, STEP1)['failures'][0]['kind'], 'leader-has-interlock')

    def test_edits_propagate_to_every_follower_within_its_cycle(self):
        cycle = 64 * 15 / 130
        edits = [100 + cycle * .4, 100 + cycle * .8, 100 + cycle * 1.3]
        report = mw.admission_oracle('WORST', worst_rows(edits=edits), STEP1)
        self.assertTrue(report['passed'], report['failures'])
        self.assertEqual(report['edits'], 3)
        self.assertEqual(len(report['propagation']), 45)

    def test_an_edit_is_the_step_key_edge_after_which_the_leader_trig_changed(self):
        cycle = 64 * 15 / 130
        rows = worst_rows(edits=[100 + cycle * .4])
        down, up = [row for row in rows if row['kind'] in (2, 3) and (row['x'], row['y']) == STEP1]
        # As on the device (63da3611 PERF-MERGE-HW-EDIT): the key-down row
        # still shows the old trig; the release applied the edit.
        self.assertEqual((down['kind'], down['leader_trig'], up['kind'], up['leader_trig']), (2, 1, 3, 0))
        report = mw.admission_oracle('WORST', rows, STEP1)
        self.assertEqual(report['edits'], 1)
        self.assertEqual({entry['edit_row'] for entry in report['propagation']}, {up['index']})
        # A key-down alone (no release recorded) is not an edit.
        report = mw.admission_oracle('WORST', [row for row in rows if row is not up], STEP1)
        self.assertEqual(report['edits'], 0)

    def test_a_stale_or_late_propagation_fails(self):
        cycle = 64 * 15 / 130
        rows = worst_rows(edits=[100 + cycle * .4])
        # The first follower build after the edit still shows the old anchors.
        edit = next(row for row in rows if row['kind'] == 3 and (row['x'], row['y']) == STEP1)
        stale = next(row for row in rows if row['index'] > edit['index'] and row['kind'] == 1 and row['channel'] == 4)
        stale['leader_trig'] = 1
        stale.update(dict(zip(('status', 'cycles', 'anchors', 'plan_builds', 'candidates', 'removed', 'other', 'eligible', 'admitted'),
                              mw.VARIANTS['WORST']['on'](0))))
        kinds = {failure['kind'] for failure in mw.admission_oracle('WORST', rows, STEP1)['failures']}
        self.assertIn('propagation', kinds)
        # No mid-cycle rebuild: the first admission after the edit is the next wrap.
        rows = [row for row in worst_rows(edits=[100 + cycle * .4]) if not (row['kind'] == 1 and row['pulse'] == 5 and row['channel'] == 7)]
        for index, row in enumerate(rows, 1):
            row['index'] = index
        failures = mw.admission_oracle('WORST', rows, STEP1, follower_step_seconds=15 / 130)['failures']
        self.assertEqual([(f['kind'], f['channel']) for f in failures], [('propagation', 7)])

    def test_an_edit_landing_in_the_last_step_before_a_wrap_may_propagate_at_the_wrap(self):
        cycle = 64 * 15 / 130
        rows = worst_rows(edits=[100 + cycle - .05])
        for row in rows:
            if row['kind'] == 1 and row['pulse'] == 5:
                row['k'] = 1
                row['time'] = 100 + cycle
        self.assertFalse(mw.admission_oracle('WORST', rows, STEP1)['passed'])
        self.assertTrue(mw.admission_oracle('WORST', rows, STEP1, follower_step_seconds=15 / 130)['passed'])


class StartLatency(unittest.TestCase):
    def test_latency_runs_from_the_native_start_stamp_to_the_first_note_on(self):
        rows = [key(1, 10.0, PLAY, 1, -99)]
        events = note_events({3: [10_004_000_000, 10_100_000_000], 0: [9_000_000_000]})
        self.assertEqual(mw.start_latency_ns(rows, events, PLAY), 4_000_000)
        with self.assertRaisesRegex(AssertionError, 'No Start input'):
            mw.start_latency_ns([key(1, 10.0, STEP1, 1, 0)], events, PLAY)

    def test_the_enabled_start_may_be_at_most_ten_milliseconds_slower_than_off(self):
        self.assertTrue(mw.start_latency_gate(15_000_000, 5_000_000, TIMING_THRESHOLDS)['passed'])
        self.assertFalse(mw.start_latency_gate(15_000_001, 5_000_000, TIMING_THRESHOLDS)['passed'])
        self.assertTrue(mw.start_latency_gate(2_000_000, 9_000_000, TIMING_THRESHOLDS)['passed'])
        self.assertEqual(mw.start_latency_gate(12, 2, TIMING_THRESHOLDS)['bound_ns'], TIMING_THRESHOLDS['step_jitter_maximum_ns'])


class TimingOracle(unittest.TestCase):
    def test_worst_output_on_its_grids_passes_the_shared_gates(self):
        seconds = CASES['PERF-MERGE-HW-WORST']['seconds']
        report = mw.merge_timing_oracle(worst_midi(1_000_000_000, seconds), 'WORST', seconds, 15 / 130, TIMING_THRESHOLDS)
        self.assertTrue(report['passed'], report['gates'])
        self.assertEqual(report['timing']['maximum_ns'], 0)
        self.assertAlmostEqual(report['steps'], seconds / (15 / 130), delta=2)

    def test_a_late_note_is_measured_and_gated(self):
        seconds = CASES['PERF-MERGE-HW-WORST']['seconds']
        report = mw.merge_timing_oracle(worst_midi(1_000_000_000, seconds, late=[(4, 1, 45_000_000)]), 'WORST', seconds,
                                        15 / 130, TIMING_THRESHOLDS)
        self.assertEqual(report['timing']['maximum_ns'], 45_000_000)
        # Beyond half a sixteenth a note is placed on the next onset, still
        # further from it than the 50 ms maximum gate allows.
        report = mw.merge_timing_oracle(worst_midi(1_000_000_000, seconds, late=[(4, 1, 60_000_000)]), 'WORST', seconds,
                                        15 / 130, TIMING_THRESHOLDS)
        self.assertFalse(report['gates']['event_timing'])
        self.assertGreater(report['timing']['maximum_ns'], TIMING_THRESHOLDS['maximum_ns'])
        # Spread across steps: the one-stall tolerance does not hide it.
        late = [(0, index, 12_000_000) for index in range(10, 150, 7)]
        report = mw.merge_timing_oracle(worst_midi(1_000_000_000, seconds, late=late), 'WORST', seconds, 15 / 130, TIMING_THRESHOLDS)
        self.assertFalse(report['gates']['event_timing'])

    def test_x16_leader_notes_are_placed_one_by_one_without_aliasing(self):
        grid = STEP_NS / 16
        seconds = 8.0
        count = int(seconds * 1e9 / grid) + 16
        slots = [s for s in range(count) if s % 64 != 0 or s < 64]  # step 1 off after the first cycle
        leader = [1_000_000_000 + round(s * grid) for s in slots]
        leader[200] += 5_000_000  # later than half an x16 step
        events = note_events({0: leader}, length_ns=3_000_000)
        report = mw.merge_timing_oracle(events, 'DENSE', seconds, 15 / 130, TIMING_THRESHOLDS, mw.leader_step_one_skip('DENSE'))
        self.assertAlmostEqual(report['timing']['maximum_ns'], 5_000_000, delta=1_000)
        self.assertTrue(report['passed'], report['gates'])
        # A dropped note shifts every later one onto the next slot: the
        # like-for-like comparison with a window that played it is invalid.
        dropped = note_events({0: leader[:300] + leader[301:]}, length_ns=3_000_000)
        like = mw.like_for_like_timing(dropped, events, 'DENSE', seconds, 15 / 130, TIMING_THRESHOLDS, mw.leader_step_one_skip('DENSE'))
        self.assertFalse(like['valid'])

    def test_the_grid_origin_follows_the_steady_phase_not_a_late_start_burst(self):
        # The device's Start burst (16 notes) left 12.7 ms after its slot while
        # every later step was on time: anchoring the grid on the first note
        # made every later note read 12.7 ms early (c6e19128 WORST p99 13.8 ms).
        seconds = CASES['PERF-MERGE-HW-WORST']['seconds']
        events = worst_midi(1_000_000_000, seconds, late=[(c, 0, 12_700_000) for c in range(16)])
        report = mw.merge_timing_oracle(events, 'WORST', seconds, 15 / 130, TIMING_THRESHOLDS)
        self.assertEqual(report['origin_shift_ns'], -12_700_000)
        self.assertEqual(report['timing']['p50_ns'], 0)
        self.assertEqual(report['timing']['maximum_ns'], 12_700_000)          # the burst itself
        self.assertEqual(report['timing_one_stall_tolerated']['p99_ns'], 0)  # everything else on time
        self.assertEqual(report['final_phase_error_ns'], 0)

    def test_unbalanced_releases_fail(self):
        events = worst_midi(1_000_000_000, 8.0)
        events = [e for e in events if not (e['bytes'][0] == 128 + 3)]
        with self.assertRaisesRegex(AssertionError, 'Unbalanced releases'):
            mw.merge_timing_oracle(events, 'WORST', 8.0, 15 / 130, TIMING_THRESHOLDS)


def start_rows(at):
    """An Off window's recorder rows: the Play key-down and its key-up at `at`."""
    return [key(1, at - .04, PLAY, 1, -99), key(2, at, PLAY, 1, -99, kind=3)]


def window(mode, seconds, latency_ns, rows, midi_origin_ns):
    return {'mode': mode, 'seconds': seconds, 'rows': rows, 'state': {'midi': worst_midi(midi_origin_ns, seconds)},
            'stopped': True, 'step_cell': STEP1, 'play_cell': PLAY}


class LikeForLike(unittest.TestCase):
    SECONDS = CASES['PERF-MERGE-HW-WORST']['seconds']

    def compare(self, enabled_late=None, off_late=None, rows=None, enabled=None, off=None):
        enabled = enabled or worst_midi(100_000_000_000, self.SECONDS, late=enabled_late)
        off = off or worst_midi(50_000_000_000, self.SECONDS, late=off_late)
        return mw.like_for_like_timing(enabled, off, 'WORST', self.SECONDS, 15 / 130, TIMING_THRESHOLDS,
                                       None, rows, STEP1 if rows else None)

    def test_the_same_notes_on_time_add_nothing(self):
        report = self.compare()
        self.assertTrue(report['valid'])
        self.assertEqual(report['merge_added'], {'p99_ns': 0, 'step_jitter_maximum_ns': 0})
        self.assertTrue(all(report['gates'].values()))
        self.assertGreater(report['compared_steps'], 180)

    def test_merge_added_step_jitter_is_enabled_minus_off(self):
        wrap = [(c, 1, 12_000_000) for c in range(1, 16)] + [(0, 64, 12_000_000)]
        # Off: the same 16-note wrap step late by 7 ms (the base note path).
        off_wrap = [(c, 1, 7_000_000) for c in range(1, 16)] + [(0, 64, 7_000_000)]
        report = self.compare(enabled_late=wrap, off_late=off_wrap)
        self.assertTrue(report['valid'])
        self.assertEqual(report['merge_added']['step_jitter_maximum_ns'], 5_000_000)
        self.assertTrue(report['gates']['merge_added_step_jitter'])
        wrap = [(c, 1, 13_000_000) for c in range(1, 16)] + [(0, 64, 13_000_000)]
        report = self.compare(enabled_late=wrap, off_late=off_wrap)
        self.assertEqual(report['merge_added']['step_jitter_maximum_ns'], 6_000_000)
        self.assertFalse(report['gates']['merge_added_step_jitter'])
        self.assertEqual(report['enabled']['step_jitter']['maximum_ns'], 13_000_000)   # absolute, reported

    def test_different_notes_on_a_compared_step_make_the_comparison_invalid(self):
        enabled = worst_midi(100_000_000_000, self.SECONDS)
        # One follower note with another velocity at step 64.
        for event in enabled:
            if event['bytes'][0] == 144 + 5 and event['monotonic_ns'] > 100_000_000_000 + 60 * STEP_NS:
                event['bytes'] = [144 + 5, 60, 90]
                break
        report = self.compare(enabled=enabled)
        self.assertFalse(report['valid'])
        self.assertEqual(report['invalid_reasons'], ['note sets differ at 1 compared steps (first [64])'])

    def test_steps_with_the_leader_toggled_off_by_an_edit_are_excluded(self):
        cycle = 64 * 15 / 130
        rows = worst_rows(edits=[100 + cycle * .4, 100 + cycle * .8], start=100.0)
        enabled = worst_midi(100_000_000_000, self.SECONDS)
        off_from, off_to = 100_000_000_000 + round(cycle * .4e9) + 40_000_000, 100_000_000_000 + round(cycle * .8e9) + 40_000_000
        kept = [e for e in enabled if not (e['bytes'][0] & 15 == 0 and off_from <= e['monotonic_ns'] < off_to)]
        kept = [e for e in kept if e['bytes'][0] & 240 == 144 or
                any(on['bytes'][0] & 15 == e['bytes'][0] & 15 and on['monotonic_ns'] == e['monotonic_ns'] - 20_000_000
                    for on in kept if on['bytes'][0] & 240 == 144)]
        report = self.compare(rows=rows, enabled=kept)
        self.assertTrue(report['valid'], report['invalid_reasons'])
        self.assertGreater(report['excluded_step_count'], 20)
        self.assertFalse(self.compare(enabled=kept)['valid'])   # without the exclusion


class Verdict(unittest.TestCase):
    def test_all_gates_combine_and_the_start_latency_bound_is_enforced(self):
        seconds = CASES['PERF-MERGE-HW-WORST']['seconds']
        off = window('off', 8.0, 0, start_rows(50.0), 50_004_000_000)
        enabled = window('enabled', seconds, 0, worst_rows(), 100_006_000_000)
        verdict = hardware_performance.evaluate_merge_windows('PERF-MERGE-HW-WORST', off, enabled, 15 / 130)
        self.assertTrue(verdict['passed'], verdict['gates'])
        self.assertEqual(verdict['start_latency']['difference_ns'], 2_000_000)
        slow = window('enabled', seconds, 0, worst_rows(), 100_015_000_000)
        verdict = hardware_performance.evaluate_merge_windows('PERF-MERGE-HW-WORST', off, slow, 15 / 130)
        self.assertEqual(verdict['gates'], {'event_timing_maximum': True, 'sustained_service': True, 'hard_service': True,
                                            'merge_added_p99': True, 'merge_added_step_jitter': True,
                                            'admissions': True, 'start_latency': False, 'transport_stopped': True})

    def test_start_latency_is_measured_from_the_key_up_against_the_same_first_step(self):
        seconds = CASES['PERF-MERGE-HW-WORST']['seconds']
        off = window('off', 8.0, 0, start_rows(50.0), 50_004_000_000)
        enabled = window('enabled', seconds, 0, worst_rows(), 100_006_000_000)
        verdict = hardware_performance.evaluate_merge_windows('PERF-MERGE-HW-WORST', off, enabled, 15 / 130)
        latency = verdict['start_latency']
        self.assertEqual((latency['edge'], latency['valid'], latency['enabled_ns'], latency['off_ns']),
                         ('key-up', True, 6_000_000, 4_000_000))
        # The key-down figures are kept: 40 ms earlier in both windows.
        self.assertEqual((latency['key_down']['enabled_ns'], latency['key_down']['off_ns']), (46_000_000, 44_000_000))
        self.assertEqual(latency['first_step']['enabled'], [[c, 60] for c in range(16)])
        self.assertTrue(verdict['valid'] and verdict['passed'])

    def test_a_different_first_step_in_the_off_window_makes_the_case_invalid(self):
        seconds = CASES['PERF-MERGE-HW-WORST']['seconds']
        off = window('off', 8.0, 0, start_rows(50.0), 50_004_000_000)
        # The Off window's step 1 plays the leader only (legacy skip).
        first = min(e['monotonic_ns'] for e in off['state']['midi'])
        off['state']['midi'] = [e for e in off['state']['midi'] if not (e['monotonic_ns'] < first + 30_000_000 and e['bytes'][0] & 15 != 0)]
        enabled = window('enabled', seconds, 0, worst_rows(), 100_006_000_000)
        verdict = hardware_performance.evaluate_merge_windows('PERF-MERGE-HW-WORST', off, enabled, 15 / 130)
        self.assertFalse(verdict['valid'])
        self.assertFalse(verdict['passed'])
        self.assertEqual(verdict['invalid'], ['start latency: first-step note sets differ',
                                              'like-for-like timing: note sets differ at 1 compared steps (first [0])'])
        self.assertEqual(verdict['start_latency']['first_step']['off'], [[0, 60]])
        # Timing and admissions are judged as usual.
        self.assertTrue(verdict['gates']['admissions'])

    def test_a_start_without_a_recorded_key_up_is_invalid(self):
        seconds = CASES['PERF-MERGE-HW-WORST']['seconds']
        off = window('off', 8.0, 0, [key(1, 49.96, PLAY, 1, -99)], 50_004_000_000)
        enabled = window('enabled', seconds, 0, worst_rows(), 100_006_000_000)
        verdict = hardware_performance.evaluate_merge_windows('PERF-MERGE-HW-WORST', off, enabled, 15 / 130)
        self.assertEqual(verdict['invalid'], ['start latency: Start key-up not recorded'])

    def test_gc_observation_separates_builds_with_a_gc_step(self):
        rows = worst_rows()
        rows[3]['heap_delta_bytes'], rows[3]['build_us'] = -65536, 5000
        report = mw.gc_observation(rows)
        self.assertEqual((report['builds_with_gc_step'], report['build_us_max_with_gc_step'],
                          report['build_us_max_without_gc_step']), (1, 5000, 900))

    def test_an_edit_case_requires_every_scheduled_edit(self):
        seconds = CASES['PERF-MERGE-HW-EDIT']['seconds']
        off = window('off', 8.0, 0, start_rows(50.0), 50_004_000_000)
        enabled = window('enabled', seconds, 0, worst_rows(), 100_006_000_000)
        verdict = hardware_performance.evaluate_merge_windows('PERF-MERGE-HW-EDIT', off, enabled, 15 / 130)
        self.assertFalse(verdict['gates']['admissions'])
        self.assertEqual(verdict['admissions']['failures'][-1], {'kind': 'edits', 'observed': 0, 'expected': 5})


class FakeRecorderMaiden:
    """Answers the workload calls as the device would, one window at a time."""

    def __init__(self, windows):
        self.windows = windows
        self.calls = []
        self.current = None

    def eval(self, source, **kwargs):
        self.calls.append(source)
        if '__MOSAIC_LOCK_LEAD__' in source:
            return '__MOSAIC_LOCK_LEAD__0'
        if '__MOSAIC_LOCK_CONTRACT__' in source:
            return '__MOSAIC_LOCK_CONTRACT__legacy-delay-v1'
        if '__MERGE_WORKLOAD__' in source:
            return '__MERGE_WORKLOAD__true'
        match = re.search(r"configure\('(\w+)','(\w+)'\)", source)
        if match:
            self.current = self.windows[match.group(2)]
            return '__MERGE_CONFIG__%s|%s|1:foundation' % match.groups()
        if '.install(' in source:
            return '__MERGE_REC_INSTALLED__2'
        if '.reset()' in source:
            return '__MERGE_REC_RESET__'
        if '.count()' in source:
            return '__MERGE_REC_COUNT__%d' % len(self.current['rows'])
        match = re.search(r'dump\((\d+),(\d+)\)', source)
        if match:
            first, last = int(match.group(1)), int(match.group(2))
            lines = []
            for row in self.current['rows'][first - 1:last]:
                if row['kind'] == 1:
                    values = [str(row[name]) if name != 'time' else '%.9f' % row['time'] for name in mw.BUILD_FIELDS]
                else:
                    values = [str(row['kind']), '%.9f' % row['time'], str(row['pulse']), str(row['x']), str(row['y']), str(row['leader_trig'])] + \
                             [str(row['k'][c]) for c in range(2, 17)]
                lines.append('__MERGE_ROW__%d|%s' % (row['index'], ','.join(values)))
            return '\n'.join(lines)
        if '.remove()' in source:
            return '__MERGE_REC_REMOVED__'
        return ''


class FakeMergeDriver:
    windows = None

    def __init__(self, runner, *args, **kwargs):
        self.runner = runner
        self.tempo_bpm = 130.0
        self.expected_step_seconds = 15 / 130
        self.ui = Ui(self)
        self.taps = []
        self.finished = 0
        self.snapshots = [FakeMergeDriver.windows['off'], FakeMergeDriver.windows['enabled']]

    def tap(self, x, y):
        self.taps.append((x, y))

    def action(self, **kwargs):
        pass

    def key(self, *args):
        pass

    def enc(self, *args):
        pass

    def elapse(self, *args):
        pass

    def led_values(self, *args):
        pass

    def snapshot(self):
        return {'midi': self.snapshots.pop(0)['midi']}

    def finish(self):
        self.finished += 1


class DeviceRunOrchestration(unittest.TestCase):
    def run_case(self, case_id, enabled_rows):
        seconds = CASES[case_id]['seconds']
        windows = {'off': {'rows': start_rows(50.0), 'midi': worst_midi(50_004_000_000, 8.0)},
                   'enabled': {'rows': enabled_rows, 'midi': worst_midi(100_006_000_000, seconds)}}
        FakeMergeDriver.windows = windows
        maiden = FakeRecorderMaiden(windows)
        out = Path(tempfile.mkdtemp())
        runner = type('R', (), {'maiden': maiden, 'ssh': object(), 'out': out})()
        drivers = []

        def make_driver(*args, **kwargs):
            drivers.append(FakeMergeDriver(*args, **kwargs))
            return drivers[-1]
        with patch('hardware_performance.HardwareDriver', make_driver), patch('hardware_performance.build_project') as build, \
                patch('hardware_performance.functional_preflight', return_value={'passed': True}), \
                patch('hardware_performance.transport_state', return_value=(False, [])), \
                patch('hardware_performance.source_identity', return_value={'mosaic_revision': 'abc', 'dirty_patch_sha256': None}), \
                patch('hardware_performance.time.sleep'):
            value = hardware_performance.run_hardware_performance(runner, case_id, 2, 'map', out, type('T', (), {'reset': lambda self: None})(),
                                                                  hardware_performance.NoResourceSampler())
        return value, maiden, drivers[0], build, out

    def test_off_then_enabled_in_one_session_with_the_recorder_removed(self):
        value, maiden, driver, build, out = self.run_case('PERF-MERGE-HW-WORST', worst_rows())
        build.assert_called_once()
        self.assertEqual(build.call_args.args[1:3], (16, 'dense'))
        configures = [call for call in maiden.calls if call.startswith('print(_MOSAIC_MERGE_WORKLOAD.configure(')]
        self.assertEqual(configures, ["print(_MOSAIC_MERGE_WORKLOAD.configure('WORST','off'))",
                                      "print(_MOSAIC_MERGE_WORKLOAD.configure('WORST','enabled'))"])
        installed = maiden.calls.index('print(_MOSAIC_MERGE_WORKLOAD.install(%d))' % mw.LEADER_PATTERN)
        self.assertGreater(maiden.calls.index(configures[0]), installed)
        self.assertIn('print(_MOSAIC_MERGE_WORKLOAD.remove())', maiden.calls[-1])
        self.assertEqual(driver.finished, 1)
        self.assertTrue(value['passed'], value['oracle']['gates'])
        self.assertFalse(value['qualification_eligible'])
        self.assertTrue(any('outstanding' in text for text in value['limitations']))
        self.assertEqual(value['oracle']['admissions']['admissions_checked'], 60)
        self.assertTrue((out / 'performance-raw-off.json').is_file() and (out / 'performance-raw-enabled.json').is_file())
        # Both windows leave the Trigger editor on the leader's anchor pattern.
        self.assertEqual(driver.taps.count(control_cell('pattern_select', mw.LEADER_PATTERN)), 2)

    def test_edit_case_taps_step_one_on_schedule_and_requires_propagation(self):
        cycle = 64 * 15 / 130
        edits = [100 + (8.125 + 8 * n) * 60 / 130 for n in range(5)]
        value, maiden, driver, build, out = self.run_case('PERF-MERGE-HW-EDIT', worst_rows(edits=edits))
        self.assertEqual(driver.taps.count(STEP1), 5)
        self.assertEqual(len(value['edits_dispatched']), 5)
        self.assertTrue(value['oracle']['gates']['admissions'], value['oracle']['admissions']['failures'])
        self.assertEqual(value['oracle']['admissions']['edits'], 5)
        self.assertLess(edits[-1], 100 + 3 * cycle)

    def test_merge_cases_refuse_options_that_change_what_is_measured(self):
        runner = type('R', (), {'maiden': None, 'ssh': object(), 'out': Path(tempfile.mkdtemp())})()
        for options in ({'windows': 2}, {'lead_ms': 25}, {'timing_contract': 'pulse-advance'}, {'probe_mode': 'pulse-v1'},
                        {'measured_steps': 4}, {'timing_trace': True}):
            with self.assertRaisesRegex(ValueError, 'runs one window at lead 0'):
                hardware_performance.run_hardware_performance(runner, 'PERF-MERGE-HW-STEADY', 2, 'map', runner.out, **options)


if __name__ == '__main__':
    unittest.main()

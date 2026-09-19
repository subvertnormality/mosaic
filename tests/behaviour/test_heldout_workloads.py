import unittest
from unittest.mock import patch

from heldout_workloads import HELDOUT_CASES, LUA_LOAD_SOURCE, RENDER_PRESSURE_SCHEDULE, recovery_oracle, run_window

STEP = 166_666_667


def groups(steps, channels=4, gap_after=None, gap_steps=6, late_ns=0):
    rows, index, t = [], 0, 1_000_000_000
    for step in range(steps):
        if gap_after is not None and step == gap_after + 1:
            t += gap_steps * STEP
        note = (60, 62, 64, 65)[step % 4]
        for ch in range(channels):
            index += 1
            rows.append({'index': index, 'monotonic_ns': t + (late_ns if gap_after is not None and step > gap_after else 0), 'port': 1, 'bytes': [144 + ch, note, 100]})
        for ch in range(channels):
            index += 1
            rows.append({'index': index, 'monotonic_ns': t + STEP // 2, 'port': 1, 'bytes': [128 + ch, note, 0]})
        t += STEP
    return rows


class FakeLane:
    def __init__(self):
        self.calls = []

    def gesture(self, kind, a, b):
        self.calls.append(('gesture', kind, a, b))

    def lua_load(self, iterations):
        self.calls.append(('load', iterations))


class Tests(unittest.TestCase):
    def test_render_schedule_matches_perf_dense_and_load_chunk_matches_runtime(self):
        with open('perf_dense.py') as handle:
            text = handle.read().replace(' ', '')
        for offset, label, gesture in RENDER_PRESSURE_SCHEDULE:
            self.assertTrue(('(%s,%r,%r)' % (('%.2f' % offset).lstrip('0'), label, gesture)).replace(' ', '') in text, (offset, label))
        self.assertEqual(LUA_LOAD_SOURCE, "local n = ...\nlocal x = 0\nfor i = 1, n do x = (x + i * 3) % 1000003 end\nreturn x")

    def test_window_dispatches_renders_and_loads_in_time_order(self):
        lane = FakeLane()
        with patch('heldout_workloads.time.sleep'):
            result = run_window(lane, HELDOUT_CASES['MIX-HW-8'])
        kinds = [c[0] for c in lane.calls]
        self.assertEqual(kinds.count('load'), 1)
        self.assertEqual(kinds.count('gesture'), len(RENDER_PRESSURE_SCHEDULE))
        self.assertEqual(lane.calls[kinds.index('load') - 1][:2], ('gesture', 'grid'))  # 4.00 render precedes 4.00 load
        self.assertTrue(result['complete'])

    def test_recovery_from_midi_gap_passes_on_timeline_and_fails_when_phase_is_lost(self):
        ok = recovery_oracle(groups(48, gap_after=12, gap_steps=6), 4, STEP / 1e9, 2.0)
        self.assertEqual(round(ok['overload_gap_steps']), 7)
        lost = recovery_oracle(groups(48, gap_after=12, gap_steps=6, late_ns=40_000_000), 4, STEP / 1e9, 2.0)
        self.assertFalse(lost['passed'])


if __name__ == '__main__':
    unittest.main()

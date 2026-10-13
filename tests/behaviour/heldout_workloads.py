"""Held-out performance workloads shared by the physical-norns and emulator lanes.

These cases were defined before any device or profiled-emulator result for them
existed and are never used to tune the emulator performance profile.
"""
import time

from perf_overload import FINGERPRINT, assert_recovery, note_groups
from ui_map import PERFORMANCE_RENDER_PRESSURE_SCHEDULE, performance_gesture_recipe

# Shared with perf_dense without importing the emulator runtime: safe,
# non-musical page, channel and browse controls every 250 ms.
RENDER_PRESSURE_SCHEDULE = PERFORMANCE_RENDER_PRESSURE_SCHEDULE

# Same chunk as the emulator's runtime_lua_load binding; the device runs it
# through Maiden so both lanes execute identical Lua work.
LUA_LOAD_SOURCE = "local n = ...\nlocal x = 0\nfor i = 1, n do x = (x + i * 3) % 1000003 end\nreturn x"

HELDOUT_CASES = {
    'PERF-005-HW-1': {'workload': 'dense', 'channels': 1, 'seconds': 8, 'render': True, 'loads': [], 'oracle': 'timing'},
    'PERF-005-HW-4': {'workload': 'dense', 'channels': 4, 'seconds': 8, 'render': True, 'loads': [], 'oracle': 'timing'},
    'PERF-008L-HW-4': {'workload': 'dense', 'channels': 4, 'seconds': 8, 'render': False, 'loads': [(2.0, 4000000)],
                       'fingerprint': True, 'oracle': 'recovery'},
    'MIX-HW-8': {'workload': 'slides', 'channels': 8, 'seconds': 8, 'render': True, 'loads': [(4.0, 1500000)], 'oracle': 'timing'},
}


def run_window(lane, spec):
    """Dispatch the case's timed gestures and Lua loads during one play window.

    ``lane`` provides semantic ``gesture(kind, a, b)`` and ``lua_load(iterations)``; both
    return without waiting for the runtime to finish the work.
    """
    timeline = [(offset, 'render', label, gesture) for offset, label, gesture in (RENDER_PRESSURE_SCHEDULE if spec['render'] else [])]
    timeline += [(offset, 'load', 'lua-load', iterations) for offset, iterations in spec['loads']]
    timeline.sort(key=lambda row: row[0])
    started = time.monotonic_ns()
    deadline = started + round(spec['seconds'] * 1e9)
    rows = []
    for offset, kind, label, value in timeline:
        target = started + round(offset * 1e9)
        remaining = target - time.monotonic_ns()
        if remaining > 0:
            time.sleep(remaining / 1e9)
        if time.monotonic_ns() >= deadline:
            break
        before = time.monotonic_ns()
        if kind == 'render':
            lane.gesture(*value)
        else:
            lane.lua_load(value)
        rows.append({'offset_seconds': offset, 'kind': kind, 'label': label, 'value': list(performance_gesture_recipe(value)) if kind == 'render' else value,
                     'target_ns': target, 'dispatch_started_ns': before, 'dispatch_ended_ns': time.monotonic_ns(),
                     'dispatch_lateness_ns': before - target})
    remaining = deadline - time.monotonic_ns()
    if remaining > 0:
        time.sleep(remaining / 1e9)
    expected = sum(1 for row in timeline if started + round(row[0] * 1e9) < deadline)
    return {'started_ns': started, 'dispatched': rows, 'expected': expected, 'complete': len(rows) == expected}


def recovery_oracle(events, channels, step_seconds, load_offset_seconds=2.0):
    """Overload recovery measured only from the MIDI stream (same clock as the notes).

    The largest gap between consecutive onset groups that starts between 0.5 s
    before and 2.5 s after the scheduled load (relative to the first onset)
    marks the overload; recovery uses perf_overload's unchanged phase gates
    after one bar.
    """
    groups = note_groups(events, channels)
    onsets = [min(row['monotonic_ns'] for row in group) for group in groups]
    low = onsets[0] + round((load_offset_seconds - 0.5) * 1e9)
    high = onsets[0] + round((load_offset_seconds + 2.5) * 1e9)
    gaps = [(onsets[i + 1] - onsets[i], i) for i in range(len(onsets) - 1) if low <= onsets[i] <= high]
    if not gaps:
        raise AssertionError(('no onset gap near the scheduled load', load_offset_seconds))
    gap_ns, index = max(gaps)
    step_ns = round(step_seconds * 1e9)
    result = assert_recovery(groups, onsets[index], onsets[index + 1], step_ns=step_ns, one_bar_ns=16 * step_ns, enforce=False)
    ordered = sorted(abs(x) for x in result['recovered_errors_ns'])
    return {'passed': result['passed'], 'groups': len(groups), 'overload_gap_ns': gap_ns, 'overload_gap_steps': gap_ns / step_ns,
            'recovered_groups': len(ordered), 'recovered_p99_ns': ordered[(99 * len(ordered) + 99) // 100 - 1] if ordered else None,
            'recovered_max_ns': ordered[-1] if ordered else None,
            'final_phase_error_ns': result['recovered_errors_ns'][-1] if result['recovered_errors_ns'] else None,
            'gates': result['gates'], 'issues': result['issues'][:20], 'fingerprint': list(FINGERPRINT)}

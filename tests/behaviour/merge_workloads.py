"""Interlock device-timing workloads (docs/musical-merge-extensions-plan.md §1.4).

PERF-MERGE-HW-STEADY, -WORST, -EDIT, -DENSE and -DENSE-EDIT play the PERF-002
dense 16-channel project at 130 bpm with the Merge Shape configuration the
plan specifies, applied while stopped by ``merge_device_workload.lua`` (the
same chunk the host Lua suite runs in lib/tests/lib/
merge_device_workload_tests.lua). This module holds the pure parts: case
specifications, capture durations, the per-admission semantic oracle, edit
propagation, follower wrap alignment, the Start-latency comparison and a
timing oracle for merge output judged by the unchanged ``TIMING_THRESHOLDS``.
The device run itself lives in hardware_performance.run_merge_performance.

Until source-identified device reports of all five cases pass, the device
qualification is OUTSTANDING and release-gating (owner: repository
maintainer); host results never stand in for it.
"""
from pathlib import Path

WORKLOAD_LUA = Path(__file__).resolve().parent / 'merge_device_workload.lua'
TEMPO_BPM = 130
DEFAULT_SECONDS = 8
LEADER = 1
LEADER_PATTERN = 3
REASON = 'INTERLOCK CH01'
STATUS = {0: 'none', 1: 'ok', 2: 'RESYNC', 3: 'PLAN LIMIT', 4: 'LEADER OFF', 5: 'LEADER MISSING', 9: 'unknown'}

# Beats per step of each clock mod (§1.1: a /1 step is one sixteenth).
STEP_BEATS = {'/1': 0.25, '/4': 1.0, 'x16': 0.25 / 16}

# Per variant: channel -> (clock mod, playable steps); followers; admission
# expectations as (status, cycles, anchors, plan_builds, candidates, removed,
# other, eligible, admitted) with the leader's step-1 anchor trig on / off.
VARIANTS = {
    'STEADY': {
        'channels': {1: ('/1', 16), 2: ('/1', 16)},
        'followers': (2,),
        # Cycle 0 and the Start build meet leader cycles 0-1 (origin clip);
        # later cycles meet 3. Window 1 around anchors 1, 5, 9, 13 removes 10
        # of 14 candidates; Amount 100 admits the remaining 4.
        'on': lambda k: (1, 2 if k <= 0 else 3, 4 * (2 if k <= 0 else 3), 0, 14, 10, 0, 4, 4),
        'off': None,
    },
    'WORST': {
        'channels': dict([(1, ('/1', 1))] + [(c, ('/1', 64)) for c in range(2, 17)]),
        'followers': tuple(range(2, 17)),
        'on': lambda k: (1, 64, 64, 0, 31, 31, 0, 0, 0),
        'off': lambda k: (1, 64, 0, 0, 31, 0, 0, 31, 31),
    },
    'DENSE': {
        'channels': dict([(1, ('x16', 64))] + [(c, ('/4', 64)) for c in range(2, 17)]),
        'followers': tuple(range(2, 17)),
        'on': lambda k: (1, 64, 4096, 0, 64, 64, 0, 0, 0),
        'off': lambda k: (1, 64, 4032, 0, 64, 0, 0, 64, 64),
    },
}


def capture_seconds(variant, tempo_bpm=TEMPO_BPM, cycles=3, minimum=DEFAULT_SECONDS):
    """At least three complete cycles of the slowest follower (§1.4), never
    below the 8 s default: WORST/EDIT 48 beats, DENSE/DENSE-EDIT 192 beats,
    STEADY 12 beats raised to 8 s."""
    spec = VARIANTS[variant]
    beats = max(steps * STEP_BEATS[mod] for number, (mod, steps) in spec['channels'].items()
                if number in spec['followers'])
    return max(float(minimum), cycles * beats * 60.0 / tempo_bpm)


def follower_step_beats(variant):
    spec = VARIANTS[variant]
    return max(STEP_BEATS[spec['channels'][number][0]] for number in spec['followers'])


def edit_offsets_beats(every_beats, seconds, tempo_bpm=TEMPO_BPM, phase_beats=0.0):
    """Edit times after Start, every ``every_beats`` beats inside the capture,
    shifted by ``phase_beats`` (half a follower step keeps an edit off the
    follower wrap it would otherwise race)."""
    total = seconds * tempo_bpm / 60.0
    offsets = [every_beats * n + phase_beats for n in range(1, int(total // every_beats) + 1)]
    return [value for value in offsets if value < total]


MERGE_CASES = {
    'PERF-MERGE-HW-STEADY': {'variant': 'STEADY', 'edit_every_beats': None},
    'PERF-MERGE-HW-WORST': {'variant': 'WORST', 'edit_every_beats': None},
    # "a grid edit of channel 1's anchor pattern every two bars"
    'PERF-MERGE-HW-EDIT': {'variant': 'WORST', 'edit_every_beats': 8},
    'PERF-MERGE-HW-DENSE': {'variant': 'DENSE', 'edit_every_beats': None},
    # "a grid edit of channel 1's step-1 anchor trig every 16 beats"
    'PERF-MERGE-HW-DENSE-EDIT': {'variant': 'DENSE', 'edit_every_beats': 16},
}
for _case, _spec in MERGE_CASES.items():
    _spec.update(workload='dense', channels=16, tempo_bpm=TEMPO_BPM, merge=True,
                 seconds=capture_seconds(_spec['variant']))


def lua_string_literal(text):
    """A one-line Lua string literal for an ASCII chunk sent over Maiden."""
    if any(ord(ch) > 126 or (ord(ch) < 32 and ch not in '\n\t') for ch in text):
        raise ValueError('workload chunk must be printable ASCII')
    return '"' + text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t') + '"'


# The runner installs the committed tree at this path with a verified hash
# manifest, so the workload is loaded from the device with dofile: sent inline
# it is one ~10 KB Maiden line, beyond matron's 4096-byte REPL buffer.
DEVICE_WORKLOAD_PATH = '/home/we/dust/code/mosaic/tests/behaviour/merge_device_workload.lua'


def install_command(path=DEVICE_WORKLOAD_PATH):
    """Maiden command loading the installed workload file (one short line)."""
    return "dofile(%s); print('__MERGE_WORKLOAD__'..tostring(_MOSAIC_MERGE_WORKLOAD ~= nil))" % lua_string_literal(path)


def install_chunk(text=None):
    """Maiden command defining _MOSAIC_MERGE_WORKLOAD from the workload file."""
    text = WORKLOAD_LUA.read_text() if text is None else text
    return "load(%s, 'merge_device_workload')(); print('__MERGE_WORKLOAD__'..tostring(_MOSAIC_MERGE_WORKLOAD ~= nil))" % lua_string_literal(text)


BUILD_FIELDS = ('kind', 'time', 'pulse', 'channel', 'k', 'status', 'cycles', 'anchors', 'plan_builds',
                'eligible', 'admitted', 'candidates', 'removed', 'other', 'leader_trig',
                'build_us', 'heap_kb', 'heap_delta_bytes')


def parse_rows(output):
    """Recorder dump lines -> dict rows (build, grid key-down and key-up rows)."""
    rows = []
    for line in output.splitlines():
        if not line.startswith('__MERGE_ROW__'):
            continue
        index, payload = line[len('__MERGE_ROW__'):].split('|', 1)
        values = payload.split(',')
        kind = int(values[0])
        if kind == 1:
            row = {name: (float(v) if name == 'time' else int(v)) for name, v in zip(BUILD_FIELDS, values)}
        elif kind in (2, 3):
            row = {'kind': kind, 'time': float(values[1]), 'pulse': int(values[2]), 'x': int(values[3]), 'y': int(values[4]),
                   'leader_trig': int(values[5]), 'k': {c: int(v) for c, v in zip(range(2, 17), values[6:])}}
        else:
            raise ValueError('unknown recorder row kind %r' % kind)
        row['index'] = int(index)
        rows.append(row)
    return rows


def expected_admission(variant, row):
    expectation = VARIANTS[variant]['on' if row['leader_trig'] == 1 else 'off']
    if expectation is None:
        raise AssertionError(('No expectation with the leader anchor off for', variant))
    return expectation(row['k'])


def _admission_tuple(row):
    return tuple(row[name] for name in ('status', 'cycles', 'anchors', 'plan_builds', 'candidates', 'removed',
                                        'other', 'eligible', 'admitted'))


def admission_oracle(variant, rows, step_cell, minimum_wraps=2, follower_step_seconds=None):
    """Per follower admission: the state-dependent semantics of §1.4, follower
    wraps on one pulse (three captured cycles give at least two complete
    wraps), and propagation of every leader edit to every follower
    at its first admission after the edit, inside the follower's current cycle.
    Returns a report; ``passed`` is False with ``failures`` listed otherwise."""
    followers = VARIANTS[variant]['followers']
    builds = [row for row in rows if row['kind'] == 1]
    failures = []
    checked = 0
    for row in builds:
        if row['channel'] in followers:
            expected = expected_admission(variant, row)
            actual = _admission_tuple(row)
            if actual != expected:
                failures.append({'kind': 'admission', 'channel': row['channel'], 'k': row['k'], 'leader_trig': row['leader_trig'],
                                 'expected': list(expected), 'actual': list(actual)})
            checked += 1
        elif row['channel'] == LEADER and row['status'] != 0:
            failures.append({'kind': 'leader-has-interlock', 'row': row['index']})
    # Wrap alignment: the first build of cycle k >= 1 is the wrap's.
    first = {}
    for row in builds:
        if row['channel'] in followers and row['k'] >= 1:
            first.setdefault(row['k'], {}).setdefault(row['channel'], row['pulse'])
    complete_wraps = 0
    for k, seen in sorted(first.items()):
        missing = [c for c in followers if c not in seen]
        pulses = sorted(set(seen.values()))
        if missing and k != max(first):
            failures.append({'kind': 'wrap-missing', 'k': k, 'channels': missing})
        if len(pulses) > 1:
            failures.append({'kind': 'wrap-pulse', 'k': k, 'pulses': pulses})
        if not missing:
            complete_wraps += 1
    if complete_wraps < minimum_wraps:
        failures.append({'kind': 'capture-too-short', 'complete_wraps': complete_wraps, 'required': minimum_wraps})
    # Edits: grid key edges on the step-1 cell after which the leader trig
    # changed. Mosaic applies a tap on its release, so on the device the
    # key-up row carries the edit (the key-down row still shows the old trig).
    edits = []
    state = None
    for row in rows:
        if row['kind'] == 1 and state is None:
            state = row['leader_trig']
        if row['kind'] in (2, 3) and (row['x'], row['y']) == tuple(step_cell):
            previous = state
            state = row['leader_trig']
            if previous is not None and state != previous:
                edits.append(row)
        elif row['kind'] == 1:
            state = row['leader_trig']
    propagation = []
    for edit in edits:
        for channel in followers:
            after = next((row for row in builds if row['index'] > edit['index'] and row['channel'] == channel), None)
            entry = {'edit_row': edit['index'], 'channel': channel, 'state': edit['leader_trig']}
            if after is None:
                failures.append(dict(entry, kind='propagation-missing'))
                continue
            entry.update(k_at_edit=edit['k'][channel], k=after['k'], latency_s=after['time'] - edit['time'])
            # Inside the current cycle; the next cycle only when the edit
            # reached the device within the follower's last step before a wrap.
            in_cycle = after['k'] == edit['k'][channel] or (
                follower_step_seconds is not None and after['k'] == edit['k'][channel] + 1
                and after['time'] - edit['time'] <= follower_step_seconds)
            if after['leader_trig'] != edit['leader_trig'] or not in_cycle:
                failures.append(dict(entry, kind='propagation'))
            propagation.append(entry)
    return {'passed': not failures, 'admissions_checked': checked, 'complete_wraps': complete_wraps,
            'edits': len(edits), 'propagation': propagation, 'failures': failures[:50], 'failure_count': len(failures)}


def _note_ons(events):
    return [e for e in events if len(e['bytes']) >= 3 and e['bytes'][0] & 240 == 144 and e['bytes'][2] > 0]


def start_edges(rows, play_cell):
    """Native stamps (s) of the Start input's key-down and of its key-up, the
    edge Mosaic acts on (a grid tap is applied on release); the key-up is None
    when it was not recorded."""
    cell = tuple(play_cell)
    downs = [row for row in rows if row['kind'] == 2 and (row['x'], row['y']) == cell]
    if not downs:
        raise AssertionError('No Start input was recorded')
    down = downs[0]
    ups = [row for row in rows if row['kind'] == 3 and (row['x'], row['y']) == cell and row['index'] > down['index']]
    return down['time'], (ups[0]['time'] if ups else None)


def start_latency_ns(rows, events, play_cell):
    """Start input's key-down stamp (util.time) to the first emitted Note On,
    on the same device clock as the MIDI trace."""
    start_ns = round(start_edges(rows, play_cell)[0] * 1e9)
    ons = [e['monotonic_ns'] for e in _note_ons(events) if e['monotonic_ns'] >= start_ns]
    if not ons:
        raise AssertionError('No Note On after the Start input')
    return min(ons) - start_ns


def first_step_notes(events, after_ns, cluster_ns):
    """The first step's note set after `after_ns`: (MIDI channel, pitch) of
    every Note On within `cluster_ns` of the first one, sorted."""
    ons = sorted((e for e in _note_ons(events) if e['monotonic_ns'] >= after_ns), key=lambda e: e['monotonic_ns'])
    if not ons:
        return []
    first = ons[0]['monotonic_ns']
    return sorted({(e['bytes'][0] & 15, e['bytes'][1]) for e in ons if e['monotonic_ns'] - first < cluster_ns})


def start_latency(rows, events, play_cell, cluster_ns):
    """One window's Start measurement: latency from the key-down and from the
    key-up to the first Note On, and the first step's note set."""
    down, up = start_edges(rows, play_cell)
    down_ns = round(down * 1e9)
    ons = [e['monotonic_ns'] for e in _note_ons(events) if e['monotonic_ns'] >= down_ns]
    if not ons:
        raise AssertionError('No Note On after the Start input')
    first = min(ons)
    up_ns = round(up * 1e9) if up is not None else None
    return {'from_key_down_ns': first - down_ns, 'from_key_up_ns': first - up_ns if up_ns is not None else None,
            'first_step': [list(note) for note in first_step_notes(events, down_ns, cluster_ns)]}


def start_cluster_ns(variant, step_ns):
    """Half the finest onset grid of the variant: notes of one step's burst."""
    return min(channel_grids(variant, step_ns).values()) // 2


def start_latency_gate(enabled_ns, off_ns, thresholds):
    """§1.4: passes when enabled − Off is at most step_jitter_maximum_ns."""
    bound = thresholds['step_jitter_maximum_ns']
    return {'enabled_ns': enabled_ns, 'off_ns': off_ns, 'difference_ns': enabled_ns - off_ns, 'bound_ns': bound,
            'passed': enabled_ns - off_ns <= bound}


def start_latency_verdict(enabled, off, thresholds):
    """§1.4 Start latency, measured from the acting edge (key-up). Valid only
    when the Off baseline plays the same first step (channels and pitches)
    as the enabled window and both key-ups were recorded; an invalid
    comparison is reported as such, not as a timing pass or fail. The
    key-down figures are kept for reference."""
    reasons = []
    if enabled['first_step'] != off['first_step']:
        reasons.append('first-step note sets differ')
    if enabled['from_key_up_ns'] is None or off['from_key_up_ns'] is None:
        reasons.append('Start key-up not recorded')
    result = {'edge': 'key-up', 'valid': not reasons, 'invalid_reasons': reasons,
              'first_step': {'enabled': enabled['first_step'], 'off': off['first_step']},
              'key_down': start_latency_gate(enabled['from_key_down_ns'], off['from_key_down_ns'], thresholds)}
    if reasons:
        result.update({'enabled_ns': enabled['from_key_up_ns'], 'off_ns': off['from_key_up_ns'], 'passed': False})
        return result
    result.update(start_latency_gate(enabled['from_key_up_ns'], off['from_key_up_ns'], thresholds))
    return result


def gc_observation(rows):
    """Build cost and GC evidence from the recorder's build rows: builds whose
    heap shrank across them had a GC step inside."""
    builds = [row for row in rows if row['kind'] == 1 and 'build_us' in row]
    if not builds:
        return None
    stepped = [row for row in builds if row['heap_delta_bytes'] < 0]
    ordered = sorted(row['build_us'] for row in builds)
    return {'builds': len(builds), 'builds_with_gc_step': len(stepped),
            'build_us_median': ordered[len(ordered) // 2], 'build_us_max': ordered[-1],
            'build_us_max_with_gc_step': max((row['build_us'] for row in stepped), default=None),
            'build_us_max_without_gc_step': max((row['build_us'] for row in builds if row['heap_delta_bytes'] >= 0), default=None),
            'heap_kb_max': max(row['heap_kb'] for row in builds)}


def _percentile(values, percent):
    ordered = sorted(values)
    return ordered[(percent * len(ordered) + 99) // 100 - 1]


def channel_grids(variant, step_ns):
    """MIDI channel (0-based) -> onset grid in ns; the dense channels are /1."""
    grids = {c - 1: step_ns for c in range(1, 17)}
    for number, (mod, _) in VARIANTS[variant]['channels'].items():
        grids[number - 1] = round(step_ns * STEP_BEATS[mod] / STEP_BEATS['/1'])
    return grids


# Plan §1.4 like-for-like gates: the enabled window's p99 lateness and step
# jitter may exceed the Off window's (same session, same notes) by at most this.
MERGE_ADDED_BOUND_NS = 5_000_000


def place_notes(events, variant, seconds, step_seconds, thresholds, optional_skip=None):
    """Place every Note On on its channel's onset grid.

    Slots are counted from the first Note On. The grid origin is then the
    robust one: shifted by the median signed placement error, so the grid
    follows the steady clock phase rather than the first note (the Start
    burst leaves late and would otherwise bias every later error). Channels
    whose grid is wider than twice the maximum gate are placed on their
    nearest grid onset (a placement error can only exceed the maximum gate);
    finer grids (the x16 leader) are walked note by note, one onset per note,
    where ``optional_skip(channel, slot)`` names onsets that may be silent
    (the leader's toggled step 1). Each placed note carries its sixteenth
    step, fine slot, channel, pitch and velocity."""
    step_ns = round(step_seconds * 1e9)
    grids = channel_grids(variant, step_ns)
    finest = min(grids.values())
    ons = [e for e in events if len(e['bytes']) >= 3 and e['bytes'][0] & 240 == 144 and e['bytes'][2] > 0]
    offs = [e for e in events if len(e['bytes']) >= 3 and (e['bytes'][0] & 240 == 128 or (e['bytes'][0] & 240 == 144 and e['bytes'][2] == 0))]
    assert ons, 'No Note On captured'
    assert all(e['port'] == 1 for e in ons), 'Note On outside port 1'
    assert len(offs) == len(ons), ('Unbalanced releases', len(ons), len(offs))
    first = ons[0]['monotonic_ns']
    end = first + round(seconds * 1e9)
    placed = []
    by_channel = {}
    for event in ons:
        by_channel.setdefault(event['bytes'][0] & 15, []).append(event)
    for channel, notes in by_channel.items():
        grid = grids.get(channel, step_ns)
        slot = None
        for event in notes:
            offset = event['monotonic_ns'] - first
            if grid / 2 > thresholds['maximum_ns']:
                slot = round(offset / grid)
            elif slot is None:
                slot = round(offset / grid)
            else:
                nxt = slot + 1
                if optional_skip and optional_skip(channel, nxt):
                    choices = [nxt, nxt + 1]
                    nxt = min(choices, key=lambda s: abs(offset - s * grid))
                slot = nxt
            nominal = slot * grid
            if first + nominal < end:
                placed.append({'channel': channel, 'nominal_ns': nominal, 'step': nominal // step_ns,
                               'fine': nominal // finest, 'pitch': event['bytes'][1], 'velocity': event['bytes'][2],
                               'actual_ns': event['monotonic_ns'], 'error_ns': event['monotonic_ns'] - first - nominal})
    assert placed, 'No Note On inside the capture'
    shift = sorted(row['error_ns'] for row in placed)[(len(placed) - 1) // 2]
    for row in placed:
        row['error_ns'] -= shift
        row['expected_ns'] = first + shift + row['nominal_ns']
    return {'placed': placed, 'origin_ns': first + shift, 'origin_shift_ns': shift, 'step_ns': step_ns,
            'note_ons': len(ons), 'note_offs': len(offs)}


def timing_metrics(placement, seconds, step_seconds, thresholds, steps=None):
    """Lateness, service and step jitter of placed notes (optionally only
    those in the given sixteenth steps), with the absolute gates."""
    step_ns = placement['step_ns']
    placed = [row for row in placement['placed'] if steps is None or row['step'] in steps]
    assert placed, 'No Note On in the compared steps'
    absolute = [abs(row['error_ns']) for row in placed]
    timing = {name: _percentile(absolute, p) for name, p in (('p50_ns', 50), ('p95_ns', 95), ('p99_ns', 99), ('maximum_ns', 100))}
    # Sixteenth groups, as the dense oracle: one stalled step is tolerated.
    groups = {}
    for row in placed:
        groups.setdefault(row['step'], []).append(row)
    worst = {k: max(abs(r['error_ns']) for r in rows) for k, rows in groups.items()}
    stalled = max(worst, key=worst.get)
    others = [abs(r['error_ns']) for k, rows in groups.items() if k != stalled for r in rows]
    tolerance = {'excluded_step': stalled, 'excluded_step_maximum_ns': worst[stalled],
                 'p99_ns': _percentile(others, 99) if others else timing['p99_ns']}
    clusters = {}
    for row in placed:
        clusters.setdefault(row['nominal_ns'], []).append(row['actual_ns'])
    spans = [max(v) - min(v) for v in clusters.values()]
    service = {name: _percentile(spans, p) for name, p in (('p50_ns', 50), ('p95_ns', 95), ('p99_ns', 99), ('maximum_ns', 100))}
    service.update(p99_deadline_fraction=service['p99_ns'] / step_ns, maximum_deadline_fraction=service['maximum_ns'] / step_ns)
    boundary = {}
    for row in placed:
        if row['nominal_ns'] % step_ns == 0:
            boundary[row['step']] = min(boundary.get(row['step'], row['actual_ns']), row['actual_ns'])
    intervals = [boundary[k + 1] - boundary[k] for k in sorted(boundary) if k + 1 in boundary]
    jitter = [abs(value - step_ns) for value in intervals]
    step_jitter = ({name: _percentile(jitter, p) for name, p in (('p50_ns', 50), ('p95_ns', 95), ('p99_ns', 99), ('maximum_ns', 100))}
                   if jitter else {'p50_ns': 0, 'p95_ns': 0, 'p99_ns': 0, 'maximum_ns': 0})
    final_phase = sorted(placed, key=lambda r: r['expected_ns'])[-1]['error_ns']
    gates = {
        'event_timing': tolerance['p99_ns'] <= thresholds['p99_ns'] and timing['maximum_ns'] <= thresholds['maximum_ns']
        and abs(final_phase) <= thresholds['final_phase_ns'],
        'sustained_service': service['p99_deadline_fraction'] <= thresholds['service_p99_deadline_fraction'],
        'hard_service': service['maximum_deadline_fraction'] <= thresholds['service_maximum_deadline_fraction'],
        'step_jitter': step_jitter['p95_ns'] <= thresholds['step_jitter_p95_ns'] and step_jitter['maximum_ns'] <= thresholds['step_jitter_maximum_ns'],
    }
    return {'passed': all(gates.values()), 'steps': len(groups), 'placed_note_ons': len(placed), 'timing': timing,
            'timing_one_stall_tolerated': tolerance, 'final_phase_error_ns': final_phase, 'service': service,
            'step_jitter': step_jitter, 'skipped_deadlines': sum(value > step_ns * 1.5 for value in intervals),
            'origin_shift_ns': placement['origin_shift_ns'], 'gates': gates}


def merge_timing_oracle(events, variant, seconds, step_seconds, thresholds, optional_skip=None):
    """Absolute timing of one window's merge output on its own onset grids
    (robust origin, see place_notes), judged by the unchanged thresholds.
    Simultaneous expected onsets form a service cluster; sixteenth
    boundaries carry step jitter."""
    placement = place_notes(events, variant, seconds, step_seconds, thresholds, optional_skip)
    report = timing_metrics(placement, seconds, step_seconds, thresholds)
    expected_steps = int(seconds / step_seconds)
    assert abs(report['steps'] - expected_steps) <= 2, ('Step count', report['steps'], expected_steps)
    report.update(note_ons=placement['note_ons'], note_offs=placement['note_offs'])
    return report


def step_note_sets(placement):
    """Sixteenth step -> sorted (fine slot, channel, pitch, velocity) notes."""
    result = {}
    for row in placement['placed']:
        result.setdefault(row['step'], []).append((row['fine'], row['channel'], row['pitch'], row['velocity']))
    return {step: sorted(notes) for step, notes in result.items()}


def leader_off_steps(rows, step_cell, origin_ns, step_ns):
    """Sixteenth steps (from origin_ns) that overlap, widened by one step, a
    time when the enabled window's leader anchor was toggled off (edits)."""
    state = None
    intervals, off_since = [], None
    for row in rows:
        if row['kind'] == 1:
            if state is None:
                state = row['leader_trig']
                if state == 0:
                    off_since = row['time']
            continue
        if row['kind'] in (2, 3) and (row['x'], row['y']) == tuple(step_cell):
            if state == 1 and row['leader_trig'] == 0:
                off_since = row['time']
            elif state == 0 and row['leader_trig'] == 1 and off_since is not None:
                intervals.append((off_since, row['time']))
                off_since = None
            state = row['leader_trig']
    if off_since is not None:
        intervals.append((off_since, float('inf')))
    excluded = set()
    for start, stop in intervals:
        first = int((round(start * 1e9) - origin_ns) // step_ns) - 1
        last = int((round(stop * 1e9) - origin_ns) // step_ns) + 1 if stop != float('inf') else 10 ** 9
        excluded.update(range(max(first, 0), min(last, 10 ** 6) + 1))
    return excluded


def like_for_like_timing(enabled_events, off_events, variant, seconds, step_seconds, thresholds,
                         optional_skip=None, enabled_rows=None, step_cell=None):
    """Plan §1.4: merge-added lateness and step jitter, enabled − Off, over
    the sixteenth steps both windows captured, excluding steps where the
    enabled leader's anchor was toggled off by an edit (the Off window plays
    the leader-on notes). Invalid when any compared step's note set
    (fine slot, channel, pitch, velocity) differs between the windows."""
    enabled = place_notes(enabled_events, variant, seconds, step_seconds, thresholds, optional_skip)
    off = place_notes(off_events, variant, seconds, step_seconds, thresholds)
    enabled_sets, off_sets = step_note_sets(enabled), step_note_sets(off)
    last = min(max(enabled_sets), max(off_sets))
    excluded = set()
    if enabled_rows is not None and step_cell is not None:
        excluded = {k for k in leader_off_steps(enabled_rows, step_cell, enabled['origin_ns'], enabled['step_ns']) if k <= last}
    compared = [k for k in range(0, last + 1) if k not in excluded]
    differing = [k for k in compared if enabled_sets.get(k, []) != off_sets.get(k, [])]
    reasons = ['note sets differ at %d compared steps (first %s)' % (len(differing), differing[:5])] if differing else []
    result = {'valid': not reasons and bool(compared), 'invalid_reasons': reasons if compared else ['no compared steps'],
              'compared_steps': len(compared), 'excluded_steps': sorted(excluded)[:200], 'excluded_step_count': len(excluded),
              'bound_ns': MERGE_ADDED_BOUND_NS}
    if not result['valid']:
        return result
    steps = set(compared)
    e = timing_metrics(enabled, seconds, step_seconds, thresholds, steps)
    o = timing_metrics(off, seconds, step_seconds, thresholds, steps)
    added = {'p99_ns': e['timing_one_stall_tolerated']['p99_ns'] - o['timing_one_stall_tolerated']['p99_ns'],
             'step_jitter_maximum_ns': e['step_jitter']['maximum_ns'] - o['step_jitter']['maximum_ns']}
    result.update(enabled=e, off=o, merge_added=added,
                  gates={'merge_added_p99': added['p99_ns'] <= MERGE_ADDED_BOUND_NS,
                         'merge_added_step_jitter': added['step_jitter_maximum_ns'] <= MERGE_ADDED_BOUND_NS})
    return result


def leader_step_one_skip(variant):
    """The x16 leader's step-1 onsets may be silent while its trig is off."""
    if variant != 'DENSE':
        return None
    return lambda channel, slot: channel == LEADER - 1 and slot % 64 == 0

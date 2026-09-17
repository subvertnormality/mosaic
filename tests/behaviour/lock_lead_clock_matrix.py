"""Lock lead time under clock conditions: every parameter change lands on time.

README "Lock lead time": locks leave at step time and notes move later by the lead,
preserving gate lengths; when two notes on one MIDI channel are less than twice the
lead apart, a value waits until halfway between the previous note and its own note.
README "Trig Parameters" (Default Parameter Values, Handling Off Settings), "Trig
Param Locks", "Trigless Locks", "Param Slides", "Resend unchanged locks" and "Clocks,
Swing and Shuffle" define which value each step sends and when steps occur.

Each case boots Mosaic three times with the same project built through the public
controls: lead 0 (the reference), 25 ms and 50 ms. Channel 1 plays steps 1-5 with
trigs on steps 1-4 and CC 1 assigned with the default value 20:

  step 1 lock 11 | step 2 default 20 | step 3 lock 33 | step 4 lock Off | step 5 trigless lock 55

so a default follows a lock, a lock follows a default, an Off lock keeps the previous
value, and a trigless lock changes the sustaining sound between notes. Every run with a
lead must, against the lead 0 reference of the same condition:

- send the same CC 1 values in the same order;
- sound every note with the same CC 1 value in force, which is also the step's
  documented value (11, 20, 33, 33);
- place every note-on at its reference time plus the lead, with unchanged gates;
- send every value after the previous note-on, and at its documented time, measured
  from the reference step time x: max(x, midpoint between the previous note-on and
  x plus the lead), never before a value already queued on the channel. The lead
  covers the receiver's response time, so trigless, default and lock values follow
  the same rule.

Slides are checked value by value with the same timing rule; the MIDI value in
force at a delayed note is a later slide value by design, so that check is skipped.
Controlled time is exact to 1 microsecond (deadlines are float seconds on the norns
metro). Real time uses the existing 10 ms host tolerance, and after a live edit only
compares notes before the edit because its host moment varies between runs.
"""
import json
from device_configs import boot_with
from master_clock import configure_master_output
from midi_window import MidiWindow

DEFAULT = 20
# (step, lock) where None is no lock and 'off' an explicit Off lock.
STEP_LOCKS = ((1, 11), (2, None), (3, 33), (4, 'off'), (5, 55))
# Value in force at the notes of steps 1-4 (step 5 has no trig).
IN_FORCE = (11, 20, 33, 33)
LEADS = (0, 25, 50)
CLOCK_INDEX = {'/1': 13, 'x2': 10, 'x4': 7, 'x16': 1}

CONDITIONS = {
    # 130 bpm steps are 115 ms apart: values leave at step time for every lead.
    'normal': dict(bpm=130),
    # 200 bpm steps are 75 ms apart: under 2 x 50 ms, so 50 ms waits for the midpoint.
    'fast': dict(bpm=200),
    # x4 at 130 bpm: 29 ms apart, between the lead and twice the lead at 25 ms.
    'x4-130': dict(bpm=130, clock='x4'),
    # x4 at 200 bpm: 19 ms apart, closer than either lead.
    'x4-200': dict(bpm=200, clock='x4'),
    # x16 at 130 bpm: 7 ms apart.
    'x16-130': dict(bpm=130, clock='x16'),
    # Local swing brings alternate steps together.
    'swing': dict(bpm=130, clock='x2', swing=40),
    'swing-negative': dict(bpm=200, swing=-40),
    # Local shuffle (Heavy, basis 6, full amount).
    'shuffle': dict(bpm=130, clock='x2', shuffle=True),
    # Swing and shuffle switched on during playback, then off again.
    'swing-toggle': dict(bpm=130, clock='x2', swing=40, toggle=True),
    'shuffle-toggle': dict(bpm=130, clock='x2', shuffle=True, toggle=True),
    # A global slide between the locks on a fast channel.
    'slides': dict(bpm=130, clock='x4', slide=True),
    # Tempo raised from 130 to 200 bpm during playback.
    'tempo-change': dict(bpm=130, clock='x2', tempo_change=200),
    # README Resend unchanged locks: Off sends only values that changed.
    'resend-off': dict(bpm=130, resend=False),
    'resend-off-x4-200': dict(bpm=200, clock='x4', resend=False),
}


def set_tempo(c, bpm):
    from cases import menu_label, menu_value
    c.key(1); c.enc(1, 4); c.key(3); menu_label(c, 'LEVELS >')
    position = next(i for i, v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name'] == 'CLOCK')
    c.enc(2, position); c.key(3); menu_label(c, 'source')
    c.enc(2, 1); menu_label(c, 'tempo')
    c.enc(3, -300); menu_value(c, '1')
    c.enc(3, bpm - 1); menu_value(c, str(bpm))
    # Leave the menu the way the lead-time setup does, back on the HOME panel.
    c.key(2); c.action(type='enc', n=2, delta=-120); c.elapse(.15); menu_label(c, 'LEVELS >'); c.key(2)
    c.enc(1, -4); c.key(1)


def open_clocks(c):
    from frame_oracle import header, matches
    c.wait(lambda state: matches(state, header('Ch. 1 Clocks', selected=4)))


def build(c, condition):
    """Channel 1 steps 1-5 with the documented value pattern and the condition's clock."""
    from cases import assign_trig_parameter, set_mosaic_options
    configure_master_output(c)
    c.key(1)
    if condition.get('resend') is False:
        set_mosaic_options(c, [('Resend unchanged locks', False)])
    c.hold_tap((1, 4), (5, 4))  # Channel range 1-5; step 5 has no trig.
    c.enc(1, -3); assign_trig_parameter(c, 'CC 1')
    c.enc(3, DEFAULT + 1)  # Default Parameter Values: from Off to 20.
    for step, value in STEP_LOCKS:
        if value is None:
            continue
        c.action(type='grid', x=step, y=4, state=1)
        try:
            c.elapse(.05); c.action(type='enc', n=3, delta=-126)
            if value != 'off':
                c.enc(3, value + 1)
        finally:
            c.action(type='grid', x=step, y=4, state=0)
    if condition.get('slide'):
        c.key(3)  # README Param Slides: K3 toggles the selected parameter's global slide.
    c.enc(1, 2); open_clocks(c)
    clock = condition.get('clock')
    if clock:
        c.enc(3, CLOCK_INDEX['/1'] - CLOCK_INDEX[clock]); c.key(3)
    apply_feel(c, condition)
    if condition.get('toggle'):
        # Keep the feel's settings but start straight, with the type dial selected
        # so a live toggle is a single E3 turn and K3 (README Clocks, Swing and
        # Shuffle: playing edits apply at the next reset, global step 64).
        c.enc(2, 1); c.enc(3, -type_turns(condition)); c.key(3)


def type_turns(condition):
    return 1 if condition.get('swing') is not None else 2


def apply_feel(c, condition, on=True):
    """Select the swing or shuffle dial from the clock rate dial and return to it."""
    if condition.get('swing') is not None:
        c.enc(2, 1); c.enc(3, 1 if on else -1); c.key(3)
        if on:
            c.enc(2, 1); c.enc(3, condition['swing'] + 51); c.key(3); c.enc(2, -1)
        c.enc(2, -1)
    elif condition.get('shuffle'):
        c.enc(2, 1); c.enc(3, 2 if on else -2); c.key(3)
        if on:
            c.enc(2, 1); c.enc(3, 3); c.key(3)    # Heavy
            c.enc(2, 1); c.enc(3, 4); c.key(3)    # basis 6
            c.enc(2, 1); c.enc(3, 100); c.key(3)  # full amount
            c.enc(2, -3)
        c.enc(2, -1)


def play(c, condition, seconds=3.0):
    capture = MidiWindow(c.snapshot()['midi_count'])

    def hold(duration):
        for _ in range(int(round(duration / .25))):
            c.elapse(.25); capture.extend(c.snapshot())

    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    marker = None
    if condition.get('toggle'):
        # 64 global steps at /1: the reset where a playing edit applies.
        cycle = 64 * 15 / condition['bpm']
        hold(.5)
        c.enc(3, type_turns(condition)); c.key(3)        # on at global step 64
        hold(cycle + 1.5 - .5)
        c.enc(3, -type_turns(condition)); c.key(3)       # off at global step 128
        hold(cycle)
    else:
        hold(seconds / 2)
        if condition.get('tempo_change'):
            marker = capture.cursor
            set_tempo(c, condition['tempo_change'])
        hold(seconds / 2)
    capture.extend(c.snapshot()); stopped = capture.cursor
    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    c.elapse(.2); capture.extend(c.snapshot())
    c.wait(lambda state: capture.extend(state) and not state['midi_capture']['outstanding'])
    return capture.events, marker, stopped


def timeline(events, lead_ms, field, marker, stopped, controlled):
    """Notes and CC 1 values on port 1, timed from the first step (first note minus lead)."""
    port = [e for e in events if e['port'] == 1]
    notes = [e for e in port if e['bytes'][0] == 144 and e['bytes'][2] > 0]
    assert len(notes) >= 10, ('Too few notes', lead_ms, len(notes))
    origin = notes[0][field] - lead_ms * 1_000_000
    live = marker is not None and not controlled
    limit = marker if live else stopped
    values = [e for e in port if e['bytes'][:2] == [176, 1]]
    in_force = []; current = None; position = 0
    for e in port:
        if e['bytes'][:2] == [176, 1]:
            current = e['bytes'][2]
        elif e['bytes'][0] == 144 and e['bytes'][2] > 0:
            in_force.append(current)
    gates = []
    for e in notes:
        off = next((x for x in port if x['index'] > e['index'] and x['bytes'][0] == 128 and x['bytes'][1] == e['bytes'][1]), None)
        gates.append(None if off is None else off[field] - e[field])
    timed = lambda e: e['index'] <= limit
    return dict(port=port, notes=notes, values=values, in_force=in_force, gates=gates,
                origin=origin, timed=timed)


def compare(name, condition, lead_ms, run, reference, field, controlled):
    tolerance = 1000 if controlled else 10_000_000
    lead_ns = lead_ms * 1_000_000
    rel = lambda e, t: e[field] - t['origin']
    # Values in force: README Trig Param Locks, Default Parameter Values, Handling Off.
    notes = min(len(run['in_force']), len(reference['in_force']))
    if not condition.get('slide'):
        # A slide keeps moving while a note waits for the lead, so the MIDI value
        # in force at the delayed note is a later slide value by design; slides are
        # held to the per-value timing rule below instead.
        assert run['in_force'][:notes] == reference['in_force'][:notes], dict(rule='same value in force at each note', condition=name, lead_ms=lead_ms, run=run['in_force'][:notes], reference=reference['in_force'][:notes])
        wanted = [IN_FORCE[i % 4] for i in range(notes)]
        assert run['in_force'][:notes] == wanted, dict(rule='documented value in force', condition=name, lead_ms=lead_ms, run=run['in_force'][:notes], wanted=wanted)
    # Common timed prefix of notes and values.
    ref_notes = [n for n in reference['notes'] if reference['timed'](n)]
    run_notes = [n for n in run['notes'] if run['timed'](n)]
    count = min(len(ref_notes), len(run_notes))
    assert count >= 8, ('Too few timed notes', name, lead_ms, count)
    for i in range(count):
        # README Lock lead time: notes move later by the lead; gates unchanged.
        drift = rel(run_notes[i], run) - (rel(ref_notes[i], reference) + lead_ns)
        assert abs(drift) <= tolerance, dict(rule='note at reference time plus lead', condition=name, lead_ms=lead_ms, note=i, drift_ns=drift)
        if run['gates'][i] is not None and reference['gates'][i] is not None and i < count - 1:
            assert abs(run['gates'][i] - reference['gates'][i]) <= tolerance, dict(rule='gate unchanged', condition=name, lead_ms=lead_ms, note=i)
    last_note = ref_notes[count - 1]['index']
    ref_values = [v for v in reference['values'] if v['index'] < last_note]
    run_last = run_notes[count - 1]['index']
    run_values = [v for v in run['values'] if v['index'] < run_last]
    assert [v['bytes'][2] for v in run_values] == [v['bytes'][2] for v in ref_values], dict(rule='same values in the same order', condition=name, lead_ms=lead_ms, run=[v['bytes'][2] for v in run_values], reference=[v['bytes'][2] for v in ref_values])
    ref_note_times = [rel(n, reference) for n in ref_notes[:count]]
    queued = None; timed_values = 0
    for ref_value, value in zip(ref_values, run_values):
        x = rel(ref_value, reference)
        before = [i for i, n in enumerate(ref_notes[:count]) if n['index'] < ref_value['index']]
        previous = before[-1] if before else None
        if previous is not None:
            # README Lock lead time: a value never changes the receiver before the previous note sounds.
            assert value['index'] > run_notes[previous]['index'], dict(rule='value after previous note', condition=name, lead_ms=lead_ms, value=value['bytes'][2], note=previous)
        if previous is None:
            expected = x
        else:
            # README Lock lead time: step time, or halfway between the previous
            # note-on and this step's heard time when they are close.
            expected = max(x, (ref_note_times[previous] + lead_ns + x + lead_ns) / 2)
        if queued is not None and queued > expected:
            expected = queued
        queued = expected
        actual = rel(value, run)
        assert abs(actual - expected) <= tolerance, dict(rule='value at its documented time', condition=name, lead_ms=lead_ms, value=value['bytes'][2], reference_ns=x, expected_ns=expected, actual_ns=actual)
        timed_values += 1
    return dict(notes=count, values=len(run_values), timed_values=timed_values)


def lock_lead_clock_matrix(c, name):
    condition = CONDITIONS[name]
    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    c.finish()
    runs = {}
    for lead in LEADS:
        e = boot_with(c, 'lead-%d' % lead, {}, midi_lead_time_ms=lead)
        try:
            set_tempo(e, condition['bpm'])
            build(e, condition)
            events, marker, stopped = play(e, condition)
            (e.out / 'lead-events.json').write_text(json.dumps(events) + '\n')
            runs[lead] = timeline(events, lead, field, marker, stopped, controlled)
            e.results.append(dict(kind='lock-lead-clock-run', condition=name, lead_ms=lead, notes=len(runs[lead]['notes']), values=len(runs[lead]['values']), passed=True))
        finally:
            e.finish()
    reference = runs[0]
    gaps = [b[field] - a[field] for a, b in zip(reference['notes'], reference['notes'][1:]) if reference['timed'](b)]
    if condition.get('swing') is not None or condition.get('shuffle'):
        # The feel must actually move notes, or the case would test straight time.
        assert max(gaps) - min(gaps) > .2 * min(gaps), dict(rule='feel audible in reference', condition=name, min_gap_ns=min(gaps), max_gap_ns=max(gaps))
    if condition.get('toggle'):
        # README Clocks, Swing and Shuffle: straight until global step 64, felt
        # until step 128, then straight again.
        cycle_ns = 64 * 15 / condition['bpm'] * 1e9
        start = reference['notes'][0][field]
        def spread(lo, hi):
            window = [g for g, b in zip(gaps, reference['notes'][1:]) if lo + .25e9 < b[field] - start < hi - .25e9]
            return max(window) - min(window)
        tolerance = 1000 if controlled else 10_000_000
        assert spread(0, cycle_ns) <= tolerance, ('Feel applied before its reset', name)
        assert spread(cycle_ns, 2 * cycle_ns) > 10_000_000, ('Feel not applied at its reset', name)
    summary = {}
    for lead in LEADS[1:]:
        summary[str(lead)] = compare(name, condition, lead, runs[lead], runs[0], field, controlled)
    c.results.append(dict(kind='lock-lead-clock-matrix', condition=name, leads=list(LEADS), checked=summary, passed=True))
    (c.out / 'results.json').write_text(json.dumps(c.results, indent=2) + '\n')

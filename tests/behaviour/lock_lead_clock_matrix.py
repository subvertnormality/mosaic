"""Lock lead time under clock conditions: every parameter change lands on time.

README "Lock lead time": locks leave at step time and notes move later by the lead,
preserving gate lengths; when two notes on one MIDI channel are less than twice the
lead apart, a value waits until halfway between the previous note and its own note.
README "Trig Parameters" (Default Parameter Values, Handling Off Settings), "Trig
Param Locks", "Trigless Locks", "Param Slides", "Resend unchanged locks" and "Clocks,
Swing and Shuffle" define which value each step sends and when steps occur.

Each case boots Mosaic once, builds the project through the public controls, then
plays it at lead 0 (the reference), 25 ms and 50 ms, selecting each lead in the
settings menu between plays (which drains any pending output). Channel 1 plays steps 1-5 with
trigs on steps 1-4 and CC 1 assigned with the default value 20:

  step 1 lock 11 | step 2 default 20 | step 3 lock 33 | step 4 lock Off | step 5 trigless lock 55

so a default follows a lock, a lock follows a default, an Off lock keeps the previous
value, and a trigless lock changes the sustaining sound between notes. Every run with a
lead must, against the lead 0 reference of the same condition:

- send the same CC 1 values in the same order;
- sound every note with the same CC 1 value in force, which is also the step's
  documented value (11, 20, 33, 33);
- place every note-on at its reference time plus the lead, with gates unchanged
  within a pulse: a delayed note leaves on a clock pulse, so the lead is counted
  in whole pulses (rounded up, never shorter than the setting) and a gate can
  lose the fraction of a pulse the reference note spent inside its own pulse;
- send every value after the previous note-on, and at its documented time, measured
  from the reference step time x: max(x, midpoint between the previous note-on and
  x plus the lead, both taken at the pulses those notes wait for), never before a
  value already queued on the channel. The lead
  covers the receiver's response time, so trigless, default and lock values follow
  the same rule.

Slides are checked value by value with the same timing rule; the MIDI value in
force at a delayed note is a later slide value by design, so that check is skipped.
Controlled time is exact to 50 microseconds: the lead reaches the norns metro as
float seconds, which moves a deadline by about a microsecond. Real time uses the
existing 10 ms host tolerance, compares notes only up to a live edit (its host
moment varies between runs), and does not time the stored value sent at Play,
because the wait from Play to the first note varies by up to one clock pulse.
"""
import math
import json
from device_configs import boot_with
from master_clock import configure_master_output
from midi_window import MidiWindow

DEFAULT = 20
# (step, lock) where None is no lock and 'off' an explicit Off lock.
STEP_LOCKS = ((1, 11), (2, None), (3, 33), (4, 'off'), (5, 55))
# Value in force at the note of each step with a trig (step 5 has none): step 1
# locks 11, step 2 sends the default, step 3 locks 33, step 4's Off lock keeps it.
IN_FORCE = {1: 11, 2: 20, 3: 33, 4: 33}
# Pitch and velocity of each step's note, from the project the driver configures.
STEP_NOTES = {1: [60, 127], 2: [62, 117], 3: [64, 107], 4: [65, 97]}
LEADS = (0, 25, 50)
# A playing swing or shuffle edit applies at the next reset of the song's global
# pattern, which is 64 steps by default. A shorter global length was tried and the
# edit then never applied, so the cases keep the default and wait for its reset.
GLOBAL_LENGTH = 64     # global steps between resets, where playing feel edits apply
TOGGLE_ON_AT = 1.5     # seconds into playback: enough notes before the edit to compare
TOGGLE_HOLD = None     # set from the global reset interval
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
    # README Locks with a channel range that does not start at step 1.
    'range-late': dict(bpm=130, range=(2, 5), swing=40),
    # README Param Slides: a slide wrapping from the range end to its start.
    'range-wrap-slide': dict(bpm=130, range=(1, 5), slide=True, wrap=True),
    # README Adjusting Song Sequence Length: a global length capping the range.
    'global-cap': dict(bpm=130, range=(1, 5), global_length=3),
    # README CH-RANGE: the range changed while locked steps play.
    'range-live': dict(bpm=130, range=(1, 5), range_change=(2, 4)),
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
    leave_menu_home(c)


def set_global_length(c, length):
    """Set the song's global pattern length from its grid fader (README Adjusting
    Song Sequence Length: it caps how much of a channel's range plays)."""
    import base64
    from frame_oracle import render
    c.tap(6, 8); c.tap(2, 7)
    for _ in range(length - 1):
        c.tap(8, 7)
    expected = render([(0, 62, 10, 'Global pattern length: ' + str(length))])
    def feedback(state):
        actual = base64.b64decode(state['frame']['pixels_base64'])
        return all(actual[(y * 128 + x) * 4 + k] == expected[(y * 128 + x) * 4 + k] for y in range(55, 64) for x in range(128) for k in range(3))
    c.wait(feedback)
    c.tap(3, 8)


def leave_menu_home(c):
    """From a parameter group, back out to the PARAMETERS list top and close the menu
    on the HOME page, as the lead-time setup does, so later menu paths start there."""
    from cases import menu_label
    c.key(2); c.action(type='enc', n=2, delta=-120); c.elapse(.15); menu_label(c, 'LEVELS >'); c.key(2)
    c.enc(1, -4); c.key(1)


def open_clocks(c):
    from frame_oracle import header, matches
    c.wait(lambda state: matches(state, header('Ch. 1 Clocks', selected=4)))


def build(c, condition):
    """Channel 1 steps 1-5 with the documented value pattern and the condition's clock."""
    from cases import assign_trig_parameter, set_mosaic_options
    configure_master_output(c)
    leave_menu_home(c)  # configure_master_output leaves the menu inside CLOCK.
    options = []
    if condition.get('resend') is False:
        options.append(('Resend unchanged locks', False))
    if condition.get('wrap'):
        options.append(('Wrap param slides', True))
    if options:
        set_mosaic_options(c, options)
    start, end = condition.get('range', (1, 5))
    c.hold_tap((start, 4), (end, 4))  # Channel range; step 5 has no trig.
    if condition.get('global_length'):
        set_global_length(c, condition['global_length'])
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
        # Start straight with the toggled dial selected, so a live toggle is one E3
        # turn and K3 (README Clocks, Swing and Shuffle: playing edits apply at the
        # next reset, global step 64). Each dial inherits on its own: a local swing
        # amount applies whatever the type dial shows, so swing toggles its amount
        # (left selected by apply_feel), and shuffle toggles its local type.
        if condition.get('swing') is None:
            type_dial(c)
        c.enc(3, -toggle_turns(condition)); c.key(3)


def toggle_turns(condition):
    return condition['swing'] if condition.get('swing') is not None else 2


def type_dial(c):
    """Select the swing/shuffle type dial: dial selection stops at the first dial
    (the clock rate), so move there first rather than counting from wherever a
    previous edit left the selection."""
    c.enc(2, -10); c.enc(2, 1)


def apply_feel(c, condition):
    """Set the condition's local swing or shuffle, starting from the type dial."""
    if condition.get('swing') is not None:
        type_dial(c); c.enc(3, 1); c.key(3)
        c.enc(2, 1); c.enc(3, condition['swing'] + 51); c.key(3)
    elif condition.get('shuffle'):
        type_dial(c); c.enc(3, 2); c.key(3)
        c.enc(2, 1); c.enc(3, 3); c.key(3)    # Heavy
        c.enc(2, 1); c.enc(3, 4); c.key(3)    # basis 6
        c.enc(2, 1); c.enc(3, 100); c.key(3)  # full amount


def play(c, condition, seconds=2.0):
    import math
    capture = MidiWindow(c.snapshot()['midi_count'])

    def hold(duration):
        for _ in range(max(1, int(round(duration / .25)))):
            c.elapse(.25); capture.extend(c.snapshot())

    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    marker = None
    if condition.get('toggle'):
        cycle = GLOBAL_LENGTH * 15 / condition['bpm']
        hold(TOGGLE_ON_AT)
        marker = capture.cursor
        c.enc(3, toggle_turns(condition)); c.key(3)      # applies at the next reset
        hold(cycle + 1.0 - TOGGLE_ON_AT)
        c.enc(3, -toggle_turns(condition)); c.key(3)     # straight again at the reset after
        hold(cycle + 1.5)  # leave straight notes after that reset to check
    else:
        hold(seconds / 2)
        if condition.get('tempo_change'):
            marker = capture.cursor
            set_tempo(c, condition['tempo_change'])
        if condition.get('range_change'):
            marker = capture.cursor
            start, end = condition['range_change']
            c.hold_tap((start, 4), (end, 4))   # README CH-RANGE: a playing range edit
            hold(seconds)
        hold(seconds / 2)
    capture.extend(c.snapshot()); stopped = capture.cursor
    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    c.elapse(.2); capture.extend(c.snapshot())
    c.wait(lambda state: capture.extend(state) and not state['midi_capture']['outstanding'])
    if condition.get('tempo_change'):
        set_tempo(c, condition['bpm'])  # the next lead starts from the same tempo
    if condition.get('range_change'):
        start, end = condition.get('range', (1, 5))
        c.hold_tap((start, 4), (end, 4))  # restore the range for the next lead
    return capture.events, marker, stopped


PPQN = 96  # lattice pulses per quarter note (lib/clock/m_clock.lua)


def pulse_ns(bpm):
    """The spacing of the clock pulses delayed output leaves on."""
    return 60.0 / bpm / PPQN * 1_000_000_000


def lead_ns_at(lead_ms, bpm):
    """The lead a note actually waits: whole pulses, rounded up, never shorter.

    README "Lock lead time": a delayed note leaves on a clock pulse, so its lead
    is counted in pulses. At 130 bpm a pulse is 4.81 ms and a 25 ms lead is six
    of them, 28.85 ms."""
    lead = lead_ms * 1_000_000
    if lead <= 0:
        return 0.0
    pulse = pulse_ns(bpm)
    return math.ceil(lead / pulse - 1e-9) * pulse


def timeline(events, lead_ms, field, marker, stopped, controlled, bpm):
    """Notes and CC 1 values on port 1, timed from the first step (first note minus lead)."""
    port = [e for e in events if e['port'] == 1]
    notes = [e for e in port if e['bytes'][0] == 144 and e['bytes'][2] > 0]
    assert len(notes) >= 10, ('Too few notes', lead_ms, len(notes))
    origin = notes[0][field] - lead_ns_at(lead_ms, bpm)
    live = marker is not None
    limit = marker if live else stopped
    values = [e for e in port if e['bytes'][:2] == [176, 1]]
    in_force = []; steps = []; current = None
    by_note = {tuple(v): k for k, v in STEP_NOTES.items()}
    for e in port:
        if e['bytes'][:2] == [176, 1]:
            current = e['bytes'][2]
        elif e['bytes'][0] == 144 and e['bytes'][2] > 0:
            in_force.append(current)
            steps.append(by_note[tuple(e['bytes'][1:])])
    gates = []
    for e in notes:
        off = next((x for x in port if x['index'] > e['index'] and x['bytes'][0] == 128 and x['bytes'][1] == e['bytes'][1]), None)
        gates.append(None if off is None else off[field] - e[field])
    timed = lambda e: e['index'] <= limit
    return dict(port=port, notes=notes, timed_notes=[n for n in notes if timed(n)], values=values,
                in_force=in_force, steps=steps, gates=gates,
                origin=origin, timed=timed)


def compare(name, condition, lead_ms, run, reference, field, controlled):
    tolerance = 50_000 if controlled else 10_000_000
    # A delayed note leaves on a pulse, so the lead is whole pulses; a gate may
    # also lose the fraction of a pulse the reference spent inside its own pulse.
    lead_ns = lead_ns_at(lead_ms, condition['bpm'])
    pulse = pulse_ns(condition['bpm'])
    gate_tolerance = tolerance + (pulse if lead_ms else 0)
    rel = lambda e, t: e[field] - t['origin']
    # Values in force: README Trig Param Locks, Default Parameter Values, Handling Off.
    notes = min(len(run['in_force']), len(reference['in_force']))
    if not condition.get('slide'):
        # Each note's own step decides its value, whichever steps the range plays.
        wanted = [IN_FORCE[step] for step in run['steps']]
        assert run['in_force'] == wanted, dict(rule='documented value in force', condition=name, lead_ms=lead_ms, steps=run['steps'][:40], run=run['in_force'][:40], wanted=wanted[:40])
        # A live edit lands a pulse or so from the UI action, so the plays can differ
        # in how many notes precede it; compare the sequences up to that point.
        shared = min(len(run['timed_notes']), len(reference['timed_notes']), notes)
        assert run['in_force'][:shared] == reference['in_force'][:shared], dict(rule='same value in force at each note', condition=name, lead_ms=lead_ms, run=run['in_force'][:shared], reference=reference['in_force'][:shared])
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
            assert abs(run['gates'][i] - reference['gates'][i]) <= gate_tolerance, dict(rule='gate unchanged within a pulse', condition=name, lead_ms=lead_ms, note=i, run_ns=run['gates'][i], reference_ns=reference['gates'][i])
    last_note = ref_notes[count - 1]['index']
    ref_values = [v for v in reference['values'] if v['index'] < last_note]
    # Values sent while the last compared note waits for its lead may follow in
    # the run window, so the reference values must be a prefix of the run's.
    run_values = run['values'][:len(ref_values)]
    assert [v['bytes'][2] for v in run_values] == [v['bytes'][2] for v in ref_values], dict(rule='same values in the same order', condition=name, lead_ms=lead_ms, run=[v['bytes'][2] for v in run_values], reference=[v['bytes'][2] for v in ref_values])
    ref_note_times = [rel(n, reference) for n in ref_notes[:count]]
    queued = None; timed_values = 0
    for ref_value, value in zip(ref_values, run_values):
        x = rel(ref_value, reference)
        before = [i for i, n in enumerate(ref_notes[:count]) if n['index'] < ref_value['index']]
        previous = before[-1] if before else None
        if previous is not None:
            # README Lock lead time: a value never changes the receiver before the
            # previous note sounds. It is compared in time rather than in order,
            # because a value whose gap midpoint falls on the next note's own
            # deadline is sent with that note, just before it - which is what the
            # lead is for - while without a lead it followed that note.
            gap = rel(value, run) - rel(run_notes[previous], run)
            assert gap >= -tolerance, dict(rule='value not before the previous note', condition=name, lead_ms=lead_ms, value=value['bytes'][2], note=previous, gap_ns=gap)
        if previous is None:
            # The stored value sent at Play is not timed: the wait from Play to the
            # first note is whatever is left of the clock pulse, and each play starts
            # at its own phase. Its order before the first note is still checked.
            continue
        else:
            # README Lock lead time: step time, or halfway between the previous
            # note-on and this step's heard time when they are close.
            # Both ends of the gap are the notes' own deadlines, which are their
            # counted pulses: the previous note-on and this value's own note.
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
    e = boot_with(c, 'leads', {}, midi_lead_time_ms=LEADS[0])
    try:
        set_tempo(e, condition['bpm'])
        build(e, condition)
        for lead in LEADS:
            # One project, one boot: selecting a lead drains pending output, so each
            # play starts from the same state (README Lock lead time).
            if lead != LEADS[0]:
                e._set_midi_lead_time(lead)
            events, marker, stopped = play(e, condition)
            (e.out / ('lead-%d-events.json' % lead)).write_text(json.dumps(events) + '\n')
            runs[lead] = timeline(events, lead, field, marker, stopped, controlled, condition['bpm'])
            e.results.append(dict(kind='lock-lead-clock-run', condition=name, lead_ms=lead, notes=len(runs[lead]['notes']), values=len(runs[lead]['values']), passed=True))
    finally:
        e.finish()
    reference = runs[0]
    # Every note of the reference, including after a live edit: the feel checks
    # below span the whole play, while the run comparisons stop at the edit.
    notes = reference['notes']
    start = notes[0][field]
    # Straight steps fall on a grid of whole steps (step 5 has no trig, so some
    # gaps span two); swing and shuffle move notes off that grid by 18 ms or more
    # here. Real time allows the existing 10 ms host jitter for straight timing.
    factor = {'x2': 2, 'x4': 4, 'x16': 16}.get(condition.get('clock'), 1)
    step_ns = 15 / condition['bpm'] * 1e9 / factor
    def off_grid(lo=0, hi=float('inf')):
        worst = 0
        for a, b in zip(notes, notes[1:]):
            if lo <= b[field] - start < hi:
                gap = b[field] - a[field]
                worst = max(worst, abs(gap - max(1, round(gap / step_ns)) * step_ns))
        return worst
    straight = 50_000 if controlled else 10_000_000
    felt = 12_000_000
    if condition.get('swing') is not None or condition.get('shuffle'):
        if not condition.get('toggle'):
            # The feel must actually move notes, or the case would test straight time.
            assert off_grid() > felt, dict(rule='feel audible in reference', condition=name, off_grid_ns=off_grid())
    if condition.get('toggle'):
        # README Clocks, Swing and Shuffle: a playing edit applies at the next reset
        # of the global pattern. Find where the feel starts and stops in the
        # reference rather than assuming which reset that is: the global step count
        # carries across the plays of one boot.
        marks = []
        for a, b in zip(notes, notes[1:]):
            gap = b[field] - a[field]
            marks.append((b[field] - start, abs(gap - max(1, round(gap / step_ns)) * step_ns)))
        felt_at = [t for t, o in marks if o > felt]
        assert felt_at, dict(rule='feel applied at a reset', condition=name, worst_off_grid_ns=max(o for _, o in marks))
        first, last = felt_at[0], felt_at[-1]
        before = [o for t, o in marks if .25e9 < t < first]
        after = [o for t, o in marks if t > last + .25e9]
        assert before and max(before) <= straight, dict(rule='straight before the feel', condition=name, worst_off_grid_ns=max(before) if before else None)
        assert len(felt_at) >= 8, dict(rule='feel lasts a section', condition=name, felt_gaps=len(felt_at))
        assert after and max(after) <= straight, dict(rule='straight again after the feel', condition=name, worst_off_grid_ns=max(after) if after else None)
    summary = {}
    for lead in LEADS[1:]:
        summary[str(lead)] = compare(name, condition, lead, runs[lead], runs[0], field, controlled)
    c.results.append(dict(kind='lock-lead-clock-matrix', condition=name, leads=list(LEADS), checked=summary, passed=True))
    (c.out / 'results.json').write_text(json.dumps(c.results, indent=2) + '\n')

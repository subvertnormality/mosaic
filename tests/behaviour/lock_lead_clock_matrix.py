"""Lock lead time under clock conditions: every note sounds with its own step's value.

README "Lock lead time": locks leave at step time and notes move later by the lead,
preserving gate lengths; when two notes on one MIDI channel are less than twice the
lead apart, a value waits until halfway between the previous note and its own note.
README "Trig Param Locks": a locked step sends its lock value. README "Clocks, Swing
and Shuffle": channel clock rates, swing and shuffle move steps.

Each case boots Mosaic three times with the same project built through the public
controls: lead 0 (the reference), 25 ms and 50 ms. Channel 1 plays four steps with
CC 1 locked to a distinct value on each. Every run must satisfy:

- the CC 1 value in force at each note-on is that note's own step lock;
- each lock value leaves after the previous note-on and before its own note-on;
- a lock value leaves at the later of its step time (note-on minus the lead) and the
  midpoint between the previous note-on and its own note-on;
- note-on spacing and gate lengths equal the lead 0 reference, and MIDI Start leads
  the first note by the same amount as in the reference.

Controlled time is exact to 1 microsecond (lead deadlines are float seconds on the
norns metro). Real time uses the existing 10 ms host tolerance for times; the order
checks are exact in both lanes.
"""
import json
from device_configs import boot_with
from master_clock import configure_master_output
from midi_window import MidiWindow

LOCKS = (11, 22, 33, 44)
PHRASE = ((60, 127), (62, 117), (64, 107), (65, 97))
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
    """Channel 1: four trigs, CC 1 locked per step, the condition's clock settings."""
    from cases import assign_trig_parameter
    configure_master_output(c)
    c.key(1); c.enc(1, -3); assign_trig_parameter(c, 'CC 1')
    for step, value in zip(range(1, 5), LOCKS):
        c.action(type='grid', x=step, y=4, state=1)
        try:
            c.elapse(.05); c.action(type='enc', n=3, delta=-126); c.enc(3, value + 1)
        finally:
            c.action(type='grid', x=step, y=4, state=0)
    if condition.get('slide'):
        c.key(3)  # README Param Slides: K3 toggles the selected parameter's global slide.
    c.enc(1, 2); open_clocks(c)
    clock = condition.get('clock')
    if clock:
        c.enc(3, CLOCK_INDEX['/1'] - CLOCK_INDEX[clock]); c.key(3)
    if not condition.get('toggle'):
        apply_feel(c, condition)
    return condition.get('toggle')


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
    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    half = seconds / 2
    for part in range(int(half / .25)):
        c.elapse(.25); capture.extend(c.snapshot())
    marker = capture.cursor
    if condition.get('toggle'):
        apply_feel(c, condition, on=True)
    if condition.get('tempo_change'):
        set_tempo(c, condition['tempo_change'])
    for part in range(int(half / .25)):
        c.elapse(.25); capture.extend(c.snapshot())
    if condition.get('toggle'):
        apply_feel(c, condition, on=False)
        for part in range(int(half / .25)):
            c.elapse(.25); capture.extend(c.snapshot())
    capture.extend(c.snapshot()); stopped = capture.cursor
    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    c.elapse(.2); capture.extend(c.snapshot())
    c.wait(lambda state: capture.extend(state) and not state['midi_capture']['outstanding'])
    changed = bool(condition.get('toggle') or condition.get('tempo_change'))
    return capture.events, (marker if changed else None), stopped


def analyse(events, lead_ms, field, controlled, slide, marker, stopped):
    """Check one run against the value/note rules and return its note timeline."""
    port = [e for e in events if e['port'] == 1]
    note_idx = [i for i, e in enumerate(port) if e['bytes'][0] == 144 and e['bytes'][2] > 0]
    assert len(note_idx) >= 8, ('Too few notes', lead_ms, len(note_idx))
    tolerance = 1000 if controlled else 10_000_000
    lead_ns = lead_ms * 1_000_000
    value = None; value_event = None; checked = 0
    notes = []
    previous_note = None
    for i, e in enumerate(port):
        data = e['bytes']
        if data[:2] == [176, 1]:
            value = data[2]; value_event = e
            continue
        if data[0] == 144 and data[2] > 0:
            ordinal = len(notes)
            step = next(k for k, (n, v) in enumerate(PHRASE) if [n, v] == data[1:])
            wanted = LOCKS[step]
            # README Trig Param Locks: the note sounds with its own step's lock value.
            assert value == wanted, dict(rule='value in force at note', lead_ms=lead_ms, note=ordinal, step=step + 1, wanted=wanted, actual=value)
            # README Lock lead time: Stop sends queued output at once, so output
            # after the Stop tap keeps its values but not its timing.
            timed = e['index'] <= stopped
            if previous_note is not None and value_event is not None and timed:
                # README Lock lead time: the value leaves after the previous note-on
                # (it never changes the receiver before that note sounds).
                assert value_event['index'] > previous_note['index'], dict(rule='value after previous note', lead_ms=lead_ms, note=ordinal)
                if not slide:
                    step_time = e[field] - lead_ns
                    midpoint = (previous_note[field] + e[field]) / 2
                    expected = max(step_time, midpoint) if lead_ns else e[field]
                    actual = value_event[field]
                    assert abs(actual - expected) <= tolerance, dict(rule='value at max(step time, gap midpoint)', lead_ms=lead_ms, note=ordinal, expected_ns=expected, actual_ns=actual, previous_note_ns=previous_note[field], note_ns=e[field])
                    assert actual <= e[field], dict(rule='value before own note', lead_ms=lead_ms, note=ordinal)
                    checked += 1
            if timed: notes.append(e)
            previous_note = e
            value_event = None if not slide else value_event
    # Gates: each note-on's matching release.
    gates = []
    for e in notes:
        off = next((x for x in port if x['index'] > e['index'] and x['bytes'][0] == 128 and x['bytes'][1] == e['bytes'][1]), None)
        if off is not None:
            gates.append(off[field] - e[field])
    starts = [e for e in port if e['bytes'] == [250]]
    start_offset = notes[0][field] - starts[0][field] if starts else None
    # In real time a live edit lands at a host-dependent moment, so only notes
    # before it are compared with the reference; the value rules above still
    # cover every note.
    compared = len(notes) if marker is None or controlled else len([n for n in notes if n['index'] <= marker])
    return dict(onsets=[n[field] - notes[0][field] for n in notes][:compared], gates=gates[:compared], checked=checked, start_offset=start_offset)


def lock_lead_clock_matrix(c, name):
    condition = CONDITIONS[name]
    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    tolerance = 1000 if controlled else 10_000_000
    c.finish()
    runs = {}
    for lead in LEADS:
        e = boot_with(c, 'lead-%d' % lead, {}, midi_lead_time_ms=lead)
        try:
            set_tempo(e, condition['bpm'])
            build(e, condition)
            events, marker, stopped = play(e, condition)
            (e.out / 'lead-events.json').write_text(json.dumps(events) + '\n')
            runs[lead] = analyse(events, lead, field, controlled, condition.get('slide'), marker, stopped)
            e.results.append(dict(kind='lock-lead-clock-run', condition=name, lead_ms=lead, notes=len(runs[lead]['onsets']), timed_values=runs[lead]['checked'], passed=True))
        finally:
            e.finish()
    reference = runs[0]
    for lead in LEADS[1:]:
        run = runs[lead]
        count = min(len(run['onsets']), len(reference['onsets'])) - 1
        assert count >= 3, ('Too few comparable notes', name, lead, count)
        # README Lock lead time: notes keep their spacing; the lead moves them all.
        drift = [abs(a - b) for a, b in zip(run['onsets'][:count], reference['onsets'][:count])]
        assert max(drift) <= tolerance, dict(rule='note spacing unchanged', condition=name, lead_ms=lead, max_drift_ns=max(drift))
        gates = min(len(run['gates']), len(reference['gates']), count)
        assert gates >= 3, ('Too few comparable gates', name, lead, gates)
        gate_drift = [abs(a - b) for a, b in zip(run['gates'][:gates], reference['gates'][:gates])]
        assert max(gate_drift) <= tolerance, dict(rule='gate lengths unchanged', condition=name, lead_ms=lead, max_drift_ns=max(gate_drift))
        if run['start_offset'] is not None and reference['start_offset'] is not None:
            assert abs(run['start_offset'] - reference['start_offset']) <= tolerance, dict(rule='Start moves with notes', condition=name, lead_ms=lead)
    c.results.append(dict(kind='lock-lead-clock-matrix', condition=name, leads=list(LEADS),
                          timed_values={str(k): v['checked'] for k, v in runs.items()}, passed=True))
    (c.out / 'results.json').write_text(json.dumps(c.results, indent=2) + '\n')

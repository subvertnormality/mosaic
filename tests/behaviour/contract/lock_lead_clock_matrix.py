"""Lock lead time under clock conditions: every parameter change lands on time.

README "Lock lead time": a lead is achieved by sending a step's values early, not by
delaying anything, so a note keeps the timing it has at lead 0 and gate lengths are
unchanged. A value leaves on a clock pulse, so the wait it achieves is the requested
lead rounded up to the next whole pulse: at least what was asked for and less than one
pulse more. When two notes on one MIDI channel are less than twice the lead apart, a
value waits until halfway between the previous note and its own note.

Two cases give no lead at all, by the contract rather than by failure. The first step
of a play resolves its lock on the transport's own first pulse, so there is no earlier
pulse to send it in and it leaves with its note. A slot with a running slide owns its
wire until the slide's destination step, so its lock is not sent early either.

This oracle previously treated a pulse-rounded lead as a failure, because the delivery
it described was an exact figure in milliseconds achieved by delaying notes. That
contract was measured on a CM3+ and failed its step-jitter gates; sending values early
passes them. The rounding is now the contract and is asserted in both directions, so a
value that leaves too early fails exactly as one that leaves too late does.
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
- place every note-on at its reference time, with unchanged gates, since nothing is
  delayed to create the lead;
- send every value after the previous note-on, and at its documented time, measured
  from the reference step time x: max(x, midpoint between the previous note-on and
  x plus the lead), never before a value already queued on the channel. The lead
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
import json
import math
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
# Seconds from Play to 20 ms after the twelfth onset at 130 bpm (16th steps are
# 60 / 130 / 4 s apart): step 2 of the third pass through the range 1-5, with
# ten notes before it for the timed comparison and step 3's value still pending.
EDIT_AT_STEP_2 = 11 * 60 / 130 / 4 + .020

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
    # README CH-RANGE with the incoming step's lock Off: the range is changed to
    # 4-5 a moment after step 2 sounds, while step 3's lock has been resolved but
    # has not left. Step 3 never plays now, so its value must never be heard: at
    # lead 0 step 4's Off lock keeps step 2's value, and every lead must agree.
    # The edit lands at an exact time after Play, 15-20 ms after step 2's onset
    # (the transport starts within one pulse of Play), so it precedes the
    # dispatch of step 3's value at either lead. That makes every play's step
    # sequence identical in controlled time, where the whole play is compared.
    'range-live-off': dict(bpm=130, range=(1, 5), range_change=(4, 5), edit_at=EDIT_AT_STEP_2, full_sequence=True),
    # README Resend unchanged locks: Off sends only values that changed.
    'resend-off': dict(bpm=130, resend=False),
    'resend-off-x4-200': dict(bpm=200, clock='x4', resend=False),
}


def advanced_slide_locks(condition):
    """Lock values that start a slide from an idle slot, and so are sent early.

    README Param Slides: with the slide on, each lock glides to the next lock,
    so 11 (step 1) slides to 33 (step 3) and 33 to 55 (step 5); the Off lock on
    step 4 is skipped. A lock the slide is gliding towards is sent by the slide's
    handoff at its own onset, since the slot is still sliding when the previous
    onset resolves it: 33 and 55 always, and 11 too when "Wrap param slides" is
    on, because 55 then slides on to 11. Without wrapping the chain ends at
    step 5, the slot is idle when step 1 is resolved, and 11 is advanced.
    """
    if condition.get('wrap'):
        return set()
    locks = [value for _, value in STEP_LOCKS if value not in (None, 'off')]
    return {locks[0]}


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

    def hold_exactly(duration):
        """Hold for exactly this long, observing often enough to lose nothing."""
        whole, remainder = divmod(duration, .25)
        for _ in range(int(whole)):
            c.elapse(.25); capture.extend(c.snapshot())
        if remainder > 0:
            c.elapse(remainder); capture.extend(c.snapshot())

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
        if condition.get('edit_at'):
            hold_exactly(condition['edit_at'])
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


def timeline(events, lead_ms, field, marker, stopped, controlled):
    """Notes and CC 1 values on port 1, timed from the first step (first note minus lead)."""
    port = [e for e in events if e['port'] == 1]
    notes = [e for e in port if e['bytes'][0] == 144 and e['bytes'][2] > 0]
    assert len(notes) >= 10, ('Too few notes', lead_ms, len(notes))
    # Nothing is delayed to create a lead, so the first note sits at step time in
    # every play. Subtracting the lead here would be the old contract's origin,
    # where that note had been moved later by it.
    origin = notes[0][field]
    # An anchor outside the notes themselves. Transport is not delayed under this
    # contract, so the wait from Start to the first note must be the same at every
    # lead; if a lead ever moved notes again without moving transport, or moved
    # transport without the notes, this changes while every comparison measured
    # from the first note stays still. It cannot see a delay applied uniformly to
    # everything including transport, which no wire-only capture can.
    starts = [e for e in port if e['bytes'] == [250]]
    start_to_first_note = notes[0][field] - starts[0][field] if starts else None
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
                origin=origin, timed=timed, start_to_first_note=start_to_first_note)


def documented_in_force(steps):
    """The value in force at each note, from the steps that played (README Trig
    Param Locks, Default Parameter Values, Handling Off Settings, Trigless Locks).

    A step's lock, or the default where it has none, is in force at its note; an
    Off lock keeps whatever was in force before. Step 5 is trigless, so it sounds
    no note, but its lock still changes the value: it played between two notes
    exactly when the range wrapped between them, which is when the second note's
    step is not after the first's. A range that excludes a trig step never shows
    that step's note, so that step's value never enters here.
    """
    values = dict(STEP_LOCKS); values[2] = DEFAULT
    current = None; result = []
    for previous, step in zip([None] + steps, steps):
        if previous is not None and step <= previous:
            current = values[5]
        if values[step] != 'off':
            current = values[step]
        result.append(current)
    return result


def compare(name, condition, lead_ms, run, reference, field, controlled):
    tolerance = 50_000 if controlled else 10_000_000
    lead_ns = lead_ms * 1_000_000
    rel = lambda e, t: e[field] - t['origin']
    # Every other comparison here is measured from each play's own first note, so
    # a delay common to the whole play cancels and cannot be seen. Transport is
    # the one thing this contract does not move, so the wait from Start to the
    # first note pins the notes against something outside themselves: it must be
    # the same at every lead. A delay applied uniformly to transport as well
    # remains invisible, which no capture taken only from the wire can detect.
    if run.get('start_to_first_note') is not None and reference.get('start_to_first_note') is not None:
        drift = run['start_to_first_note'] - reference['start_to_first_note']
        assert abs(drift) <= tolerance, dict(rule='first note the same wait after Start', condition=name,
                                             lead_ms=lead_ms, drift_ns=drift,
                                             run_ns=run['start_to_first_note'],
                                             reference_ns=reference['start_to_first_note'])
    # Values in force: README Trig Param Locks, Default Parameter Values, Handling Off.
    notes = min(len(run['in_force']), len(reference['in_force']))
    if not condition.get('slide'):
        # Each note's own step decides its value, whichever steps the range plays.
        # A range that can exclude the step before a note leaves that note's
        # value to the steps that did play, so it is modelled from them.
        if condition.get('full_sequence'):
            wanted = documented_in_force(run['steps'])
        else:
            wanted = [IN_FORCE[step] for step in run['steps']]
        if run['in_force'] != wanted:
            # Report where it first parts company, with the notes either side.
            at = next((i for i, (a, b) in enumerate(zip(run['in_force'], wanted)) if a != b), min(len(wanted), len(run['in_force'])))
            lo, hi = max(0, at - 3), at + 4
            raise AssertionError(dict(rule='documented value in force', condition=name, lead_ms=lead_ms,
                                      note=at, of=len(wanted), steps=run['steps'][lo:hi],
                                      run=run['in_force'][lo:hi], wanted=wanted[lo:hi]))
        # A live edit lands a pulse or so from the UI action, so the plays can differ
        # in how many notes precede it; compare the sequences up to that point.
        shared = min(len(run['timed_notes']), len(reference['timed_notes']), notes)
        assert run['in_force'][:shared] == reference['in_force'][:shared], dict(rule='same value in force at each note', condition=name, lead_ms=lead_ms, run=run['in_force'][:shared], reference=reference['in_force'][:shared])
        if controlled and condition.get('full_sequence'):
            # README CH-RANGE and Lock lead time: after the edit the new range
            # decides which steps play, and a value resolved for a step it excludes
            # must not be heard. Compared over the whole play, not only up to the
            # edit: in controlled time the edit lands at the same musical moment
            # in every play, so the notes after it correspond one to one. The
            # stop lands the same way, so the run may have sent at most the one
            # value it resolved ahead of a step the reference never reached.
            assert run['in_force'] == reference['in_force'], dict(rule='same value in force at every note, including after the edit', condition=name, lead_ms=lead_ms, run=run['in_force'], reference=reference['in_force'])
            run_all = [v['bytes'][2] for v in run['values']]
            ref_all = [v['bytes'][2] for v in reference['values']]
            assert run_all[:len(ref_all)] == ref_all and len(run_all) <= len(ref_all) + 1, dict(rule='same values in the same order over the whole play', condition=name, lead_ms=lead_ms, run=run_all, reference=ref_all)
    # Common timed prefix of notes and values.
    ref_notes = [n for n in reference['notes'] if reference['timed'](n)]
    run_notes = [n for n in run['notes'] if run['timed'](n)]
    count = min(len(ref_notes), len(run_notes))
    assert count >= 8, ('Too few timed notes', name, lead_ms, count)
    for i in range(count):
        # README Lock lead time: a lead is achieved by sending values early, so a
        # note keeps the time it has at lead 0. These positions are relative to
        # each play's own first note, so this catches a note moving relative to
        # the others, not a shift common to all of them; the value-to-note wait
        # below is what holds the lead itself.
        drift = rel(run_notes[i], run) - rel(ref_notes[i], reference)
        assert abs(drift) <= tolerance, dict(rule='note at its reference time', condition=name, lead_ms=lead_ms, note=i, drift_ns=drift)
        if run['gates'][i] is not None and reference['gates'][i] is not None and i < count - 1:
            assert abs(run['gates'][i] - reference['gates'][i]) <= tolerance, dict(rule='gate unchanged', condition=name, lead_ms=lead_ms, note=i, run_ns=run['gates'][i], reference_ns=reference['gates'][i])
    last_note = ref_notes[count - 1]['index']
    ref_values = [v for v in reference['values'] if v['index'] < last_note]
    # Values sent while the last compared note waits for its lead may follow in
    # the run window, so the reference values must be a prefix of the run's.
    run_values = run['values'][:len(ref_values)]
    assert [v['bytes'][2] for v in run_values] == [v['bytes'][2] for v in ref_values], dict(rule='same values in the same order', condition=name, lead_ms=lead_ms, run=[v['bytes'][2] for v in run_values], reference=[v['bytes'][2] for v in ref_values])
    # README Lock lead time: the lead is the wait between a value and the note it
    # shapes. Every comparison above is relative to an origin taken from the
    # first note, so a delay common to every note cancels and cannot be seen
    # there. This measures each note against its own value, which the lead never
    # moves, and so holds the lead to the milliseconds it asks for rather than to
    # whatever the clock rounds them to. Notes and values are paired by their
    # order in the reference, where a value and its note are sent together: a
    # lead longer than a step puts other values between them, so their positions
    # in the stream cannot pair them. A step that sends no value of its own has
    # no pair and is left out.
    paired, seen = {}, 0
    for i, ref_note in enumerate(ref_notes[:count]):
        while seen < len(reference['values']) and reference['values'][seen]['index'] < ref_note['index']:
            seen += 1
        own = seen - 1
        if own >= 0 and abs(reference['values'][own][field] - ref_note[field]) <= tolerance:
            paired[i] = own
    # A value leaves on a clock pulse, so the wait it achieves is the requested
    # lead rounded up to the next whole pulse: at least what was asked for, and
    # less than one pulse more. Rounding the other way would deliver less lead
    # than requested. The bound is stated in both directions, so a value that
    # left too early fails just as a value that left too late does.
    pulse_ns = 60 / (condition['bpm'] * 96) * 1_000_000_000
    if condition.get('tempo_change'):
        # The slower tempo has the longer pulse, so it bounds the whole run.
        pulse_ns = 60 / (min(condition['bpm'], condition['tempo_change']) * 96) * 1_000_000_000
    for i, own in sorted(paired.items()):
        if own >= len(run_values):
            continue
        # A note less than two leads after the one before it has its value held
        # to the gap's midpoint instead, so it waits less than a lead by design.
        # Those are timed against that midpoint by the check below; the lead
        # itself is only claimed where the gap leaves room for all of it.
        if i > 0 and run_notes[i][field] - run_notes[i - 1][field] < 2 * lead_ns:
            continue
        wait = run_notes[i][field] - run_values[own][field]
        if i == 0:
            # The first step of a play resolves its lock on the transport's own
            # first pulse. There is no earlier pulse to send it in, so it leaves
            # with its note and achieves no lead. Nothing is delayed to conceal
            # that, so the wait is zero rather than the requested lead.
            assert abs(wait) <= tolerance, dict(rule='first note has no lead to give', condition=name,
                                                lead_ms=lead_ms, note=i, wait_ns=wait)
            continue
        # How much lead a value actually gets is decided by the midpoint rule
        # against the previous sounding note, which the documented-time check
        # below models exactly, including swing and shuffle moving notes around.
        # Restating it here in terms of the requested lead got it wrong wherever
        # the gap was uneven, so this holds only the bound that does not depend
        # on the gap: a value never waits longer than the lead it asked for,
        # rounded up to the pulse it leaves on, and never follows its own note.
        assert -tolerance <= wait < lead_ns + pulse_ns + tolerance, dict(
            rule='value no earlier than its lead and never after its note',
            condition=name, lead_ms=lead_ms, note=i, wait_ns=wait,
            lead_ns=lead_ns, pulse_ns=pulse_ns, error_ns=wait - lead_ns)
    ref_note_times = [rel(n, reference) for n in ref_notes[:count]]
    queued = None; timed_values = 0
    # A value is resolved at the onset before its own, so it cannot leave earlier
    # than that onset however much lead is asked for. In the lead 0 reference each
    # value leaves at its step, so the previous value's time is that onset. Where
    # the previous onset is closer than the lead, on the short side of a swung
    # pair, this is what shortens the lead rather than the spacing rule.
    available = None
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
            # README Lock lead time: the value leaves a lead before its step,
            # rounded up to a whole pulse because it leaves on one, and never
            # earlier than halfway between the previous note-on and its step.
            # Notes are not moved, so the midpoint is between the two step times.
            # Everything here lands on the pulse grid, because a value leaves
            # inside a pulse and every onset is a pulse. Working in pulses gives
            # one exact expected time rather than a window: the lead rounded up,
            # the midpoint from the last sounding note, and the onset that
            # resolved the value, whichever of the three is latest.
            def at(ns):
                return int(round(ns / pulse_ns))
            lead_pulses = math.ceil(lead_ns / pulse_ns) if lead_ns else 0
            onset_pulse = at(x)
            anchor_pulse = at(ref_note_times[previous])
            send = onset_pulse - lead_pulses
            midpoint = anchor_pulse + -(-(onset_pulse - anchor_pulse) // 2)
            if send < midpoint:
                send = midpoint
            if available is not None and send < at(available):
                send = at(available)
            if send > onset_pulse:
                send = onset_pulse
            expected = send * pulse_ns
            if condition.get('slide'):
                # A slot that is mid-slide keeps its wire until the slide's
                # destination step, so a lock the slide is gliding towards is
                # owed at its own onset, and so is every sample of the slide.
                # A lock that starts a slide from an idle slot is advanced like
                # any other value. Which locks are which follows from the
                # project the case builds, so each value gets one exact time:
                # allowing either would also accept a lookahead that never
                # advanced anything.
                actual_now = rel(value, run)
                if value['bytes'][2] in advanced_slide_locks(condition):
                    if queued is not None and queued > expected:
                        expected = queued
                    assert abs(actual_now - expected) <= tolerance, dict(
                        rule='slide-starting lock at its documented time', condition=name,
                        lead_ms=lead_ms, value=value['bytes'][2], reference_ns=x,
                        expected_ns=expected, actual_ns=actual_now, pulse_ns=pulse_ns)
                    queued = max(queued, expected) if queued is not None else expected
                else:
                    assert abs(actual_now - x) <= tolerance, dict(
                        rule='slide destination or sample at its step', condition=name,
                        lead_ms=lead_ms, value=value['bytes'][2], reference_ns=x,
                        actual_ns=actual_now, pulse_ns=pulse_ns)
                    queued = max(queued, x) if queued is not None else x
                available = x
                timed_values += 1
                continue
        if queued is not None and queued > expected:
            expected = queued
        queued = expected
        available = x
        actual = rel(value, run)
        # The expectation is an exact pulse, so this is the plain measurement
        # tolerance. Widening it by a pulse here would accept a value that left
        # one pulse late, which is less lead than was asked for.
        assert abs(actual - expected) <= tolerance, dict(rule='value at its documented time', condition=name, lead_ms=lead_ms, value=value['bytes'][2], reference_ns=x, expected_ns=expected, actual_ns=actual, pulse_ns=pulse_ns)
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
            runs[lead] = timeline(events, lead, field, marker, stopped, controlled)
            e.results.append(dict(kind='lock-lead-clock-run', condition=name, lead_ms=lead, notes=len(runs[lead]['notes']), values=len(runs[lead]['values']), passed=True))
    finally:
        e.finish()
    reference = runs[0]
    if condition.get('full_sequence'):
        # The edit was designed to land just after step 2 sounds, with step 3's
        # value resolved but not sent, and to leave the range at 4-5. Check that
        # in the reference, or the whole-play comparison would be testing some
        # other moment. Every play's transport starts within one pulse of Play,
        # so the same holds for the runs the reference is compared with.
        steps = reference['steps']
        # After the edit the range is 4-5 and step 5 has no trig, so every note
        # from then on is step 4. That property holds in both lanes and is what
        # the case is for.
        tail = next((i for i in range(len(steps)) if all(step == 4 for step in steps[i:])), len(steps))
        assert len(steps) - tail >= 6, dict(rule='enough steps sound after the edit', condition=name, steps=steps)
        assert all(step == 4 for step in steps[tail:]), dict(rule='only step 4 sounds after the edit', condition=name, steps=steps)
        if controlled:
            # Virtual time places the edit exactly, so pin the moment too: the
            # whole-play comparison below would otherwise be testing some other
            # instant. In real time the edit lands a step or two later depending
            # on the host, so the moment is checked only for being close.
            assert steps[:10] == [1, 2, 3, 4, 1, 2, 3, 4, 1, 2], dict(rule='edit lands after step 2 of the third pass', condition=name, steps=steps[:12])
            assert tail == 10, dict(rule='edit takes effect immediately', condition=name, steps=steps)
        else:
            assert 8 <= tail <= 16, dict(rule='edit lands near step 2 of the third pass', condition=name, tail=tail, steps=steps)
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


def lock_lead_clock_002_normal(c):
    return lock_lead_clock_matrix(c, 'normal')


def lock_lead_clock_003_fast(c):
    return lock_lead_clock_matrix(c, 'fast')


def lock_lead_clock_004_x4_130(c):
    return lock_lead_clock_matrix(c, 'x4-130')


def lock_lead_clock_005_x4_200(c):
    return lock_lead_clock_matrix(c, 'x4-200')


def lock_lead_clock_006_x16_130(c):
    return lock_lead_clock_matrix(c, 'x16-130')


def lock_lead_clock_007_swing(c):
    return lock_lead_clock_matrix(c, 'swing')


def lock_lead_clock_008_swing_negative(c):
    return lock_lead_clock_matrix(c, 'swing-negative')


def lock_lead_clock_009_shuffle(c):
    return lock_lead_clock_matrix(c, 'shuffle')


def lock_lead_clock_010_swing_toggle(c):
    return lock_lead_clock_matrix(c, 'swing-toggle')


def lock_lead_clock_011_shuffle_toggle(c):
    return lock_lead_clock_matrix(c, 'shuffle-toggle')


def lock_lead_clock_012_slides(c):
    return lock_lead_clock_matrix(c, 'slides')


def lock_lead_clock_013_tempo_change(c):
    return lock_lead_clock_matrix(c, 'tempo-change')


def lock_lead_clock_014_resend_off(c):
    return lock_lead_clock_matrix(c, 'resend-off')


def lock_lead_clock_015_resend_off_x4_200(c):
    return lock_lead_clock_matrix(c, 'resend-off-x4-200')


def lock_lead_clock_016_range_late(c):
    return lock_lead_clock_matrix(c, 'range-late')


def lock_lead_clock_017_range_wrap_slide(c):
    return lock_lead_clock_matrix(c, 'range-wrap-slide')


def lock_lead_clock_018_global_cap(c):
    return lock_lead_clock_matrix(c, 'global-cap')


def lock_lead_clock_019_range_live(c):
    return lock_lead_clock_matrix(c, 'range-live')


def lock_lead_clock_020_range_live_off(c):
    return lock_lead_clock_matrix(c, 'range-live-off')

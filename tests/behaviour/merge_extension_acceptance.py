"""README "Merge Shape" Interlock and Structure acceptance through public input.

Review D5 (docs/musical-merge-extensions-plan.md §1.2.1, §1.3, §4 and the
MM-09/MM-10 rows of §7): leader and follower edits while playing, retiming a
follower or its leader through the Clock screen, lock lookahead under a nonzero
lead, and Structure's mapped conflicts, root inspection, delayed roots and group
lifecycle while playing. Every oracle is public: emitted MIDI (pitch, velocity,
MIDI channel and loop-relative step), channel-page grid LEDs and the norns screen
through the UI layer. No Mosaic Lua state is read to manufacture an expectation.
Timing is exact in the controlled lane and within 20 ms in real time.
"""
import time

from midi_window import MidiWindow

# ui.configure(): Pattern 1 holds C4 D4 E4 F4 at steps 1-4 with velocities
# 127/117/107/97. A new trig is C4 (degree 0) at velocity 100; a Foundation
# addition plays it at the default Accent 70.
P1 = {1: (60, 127), 2: (62, 117), 3: (64, 107), 4: (65, 97)}
STEP = 1 / 6          # a /1 step at the 90 BPM fixture (README Clock)
LOOP = 8
ADDITION = (60, 70)


# Public MIDI -----------------------------------------------------------------------

class Capture:
    """Every native MIDI event after a mark, loss-checked (MidiWindow)."""

    def __init__(self, c):
        self.c = c
        self.window = MidiWindow(c.snapshot()['midi_count'])

    def update(self, state=None):
        self.window.extend(state if state is not None else self.c.snapshot())
        return self

    def messages(self):
        """Each decoded message as a dict with its native timestamps."""
        result = []
        for packet in self.window.events:
            for message in packet.get('decoded', []):
                event = dict(packet)
                event['type'] = message['type']
                event['channel'] = message.get('channel')
                event['data'] = message.get('data', [])
                result.append(event)
        return result

    def note_ons(self, channel=None):
        return [m for m in self.messages() if m['type'] == 'note_on' and m['data'][1] > 0
                and (channel is None or m['channel'] == channel)]

    def until(self, predicate, timeout):
        """Wait until ``predicate(self)`` holds, collecting every event."""
        def ready(state):
            self.update(state)
            return predicate(self)
        self.c.wait(ready, timeout=timeout)
        return self


def field(c):
    return 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'


def tolerance(c):
    return 2e-9 if c.clock_mode == 'controlled-experimental' else .02


def now_ns(c):
    """The lane's clock in the MIDI timestamp domain."""
    if c.clock_mode == 'controlled-experimental':
        return c.logical_ns
    return time.monotonic_ns()


def place(c, events, origin, step=STEP, loop=LOOP):
    """Each note-on as (loop, step, midi channel, pitch, velocity) counted from
    ``origin`` (the timestamp of step 1 of loop 0). Off-lattice onsets fail."""
    key, allowed = field(c), tolerance(c)
    placed = []
    for m in events:
        seconds = (m[key] - origin) / 1e9
        index = round(seconds / step)
        error = seconds - index * step
        assert abs(error) <= allowed, dict(event=m['data'], seconds=seconds, error=error, tolerance=allowed)
        placed.append((index // loop, index % loop + 1, m['channel'], m['data'][0], m['data'][1]))
    return placed


def by_loop(placed):
    loops = {}
    for loop, step, channel, pitch, velocity in placed:
        loops.setdefault(loop, []).append((step, channel, pitch, velocity))
    return {loop: sorted(value) for loop, value in loops.items()}


def stop_and_drain(c, capture):
    c.ui.stop()
    c.wait(lambda state: capture.update(state) and state['midi_capture']['outstanding'] == [])


# Grid ---------------------------------------------------------------------------------

def loop_leds(c, lit, loop=LOOP):
    """Channel-page grid: exactly the ``lit`` steps of the loop show a trig.

    While playing, the playhead lights its own step, so each half of the loop is
    checked at a moment the playhead is in the other half."""
    states = {step: "selected" if step in lit else "off" if step <= loop else "dark"
              for step in range(1, 17)}
    half = (loop + 1) // 2
    c.ui.expect_steps({s: v for s, v in states.items() if s <= half})
    c.ui.expect_steps({s: v for s, v in states.items() if s > half})


# Setup --------------------------------------------------------------------------------

def two_patterns(c, second):
    """ui.configure(), an 8-step channel 1 loop and Pattern 2 (trigs at
    ``second``) assigned beside Pattern 1."""
    c.configure()
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=LOOP)
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(2)
    for step in second:
        c.ui.tap_step(step)
    c.ui.tap_control("channel_editor"); c.ui.tap_control("pattern_slot", 2)


def foundation_on(c, channel):
    """Merge Shape Foundation on the selected channel with its first assigned
    pattern as Anchor, applied; Rhythm (M03) stays open."""
    c.ui.channel_page("merge_shape", channel=channel)
    c.ui.select_row("mode", 0); c.ui.turn(3, 1)
    c.ui.turn(2, 1); c.ui.press_key(3)
    c.ui.expect_header("merge_rhythm", channel=channel)
    c.ui.select_row("anchor", 0); c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")


def interlock_pair(c, leader_step=5):
    """Follower channel 1 (anchors P01 at 1-4, additions P02 at 5 and 7) and
    leader channel 2 (MIDI channel 2, anchor P03 at ``leader_step``), both /1 on
    8-step loops; Interlock Leader CH02, Window 0, applied from the Interlock
    screen."""
    two_patterns(c, (5, 7))
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(3); c.ui.tap_step(leader_step)
    c.ui.tap_control("channel_editor")
    c.ui.select_channel(2)
    c.ui.channel_page("midi_config", channel=2)
    c.ui.set_value(1); c.ui.turn(2, 1); c.ui.set_value(1); c.ui.press_key(3)
    c.ui.tap_control("pattern_slot", 3)
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=LOOP)
    foundation_on(c, 2)
    c.ui.select_channel(1)
    foundation_on(c, 1)
    c.ui.select_row("interlock", 6); c.ui.press_key(3)
    c.ui.expect_header("merge_interlock", channel=1)
    c.ui.select_row("interlock_leader", 0); c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Leader", "CH02")
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    # README Interlock: the addition starting exactly with the leader's anchor
    # is removed; the other stays.
    loop_leds(c, {1, 2, 3, 4, 12 - leader_step})


def onset_count(capture, channel, note):
    return len([m for m in capture.note_ons(channel) if m['data'][:2] == list(note)])


def at_scheduled(c, when_ns, control, index):
    """Tap ``control`` at the lane's exact time ``when_ns`` (grid press, then
    release 30 ms later), through the public native input schedule in real time
    (each schedule needs a new, larger identity)."""
    schedule = getattr(c, 'merge_acceptance_schedule', 0) + 1
    c.merge_acceptance_schedule = schedule
    c.ui.grid_events_at([(when_ns, control, index, 1), (when_ns + 30_000_000, control, index, 0)],
                        schedule_id=schedule)


def wait_until_ns(c, capture, when_ns):
    capture.until(lambda k: now_ns(c) >= when_ns, timeout=max(1, (when_ns - now_ns(c)) / 1e9 + 2))


def interlock_screen(c, channel=1):
    """Merge Shape > Rhythm > Interlock for ``channel``; returns on its Status row."""
    c.ui.channel_page("merge_shape", channel=channel)
    c.ui.select_row("rhythm", 1); c.ui.press_key(3)
    c.ui.select_row("interlock", 6); c.ui.press_key(3)
    c.ui.expect_header("merge_interlock", channel=channel)
    c.ui.select_row("interlock_status", 2)


def result_interlock(c, value):
    """Merge Shape > Result: its Interlock row (README Result and Reason)."""
    c.ui.feature_root()
    c.ui.select_row("result", 4); c.ui.press_key(3)
    c.ui.expect_header("merge_result", channel=1)
    c.ui.select_row("result_interlock", 4)
    c.ui.expect_selected_field("detail", "Interlock", value)


# Interlock: edits reach the follower while playing (plan §1.3) --------------------------

LOCK = (1, 77)   # CC 1 = 77 locked on channel 1 step 7


def interlock_freshness_workflow(c):
    """README Interlock and Lock lead time, plan §1.3 freshness: a leader
    source edit and a follower edit made mid-cycle through the pattern grid
    reach the follower at once, in MIDI and on the channel grid; with a 25 ms
    lock lead the edit also withdraws the follower's already-planned lock for
    the removed addition (no stale value, no stale note)."""
    c._set_midi_lead_time(25)
    # README Trigless Locks: with it off a lock on a step without a trig is not
    # sent, so any CC 1 = 77 after the edit could only be a stale lookahead.
    c.ui.set_mosaic_option_keys([("trigless_locks", False)])
    interlock_pair(c)
    # README Trig Param Locks: hold step 7 and turn the CC 1 value to 77.
    c.ui.channel_page("trig_locks", channel=1)
    c.ui.assign_trig_parameter_key("stored_patch_cc1")
    with c.ui.hold_step(7):
        c.elapse(.05); c.ui.encoder_event(3, -126); c.elapse(.15); c.ui.turn(3, LOCK[1] + 1)
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(3)   # Pattern 3 in the editor

    capture = Capture(c)
    c.ui.play()
    capture.until(lambda k: onset_count(k, 1, P1[1]) >= 2, timeout=5)
    origin = capture.note_ons(1)[0][field(c)]
    step_ns = round(STEP * 1e9)
    # Loop 1: the leader's Pattern 3 gains a trig at step 7 halfway through
    # step 6, after the follower's step-7 lock was planned (a step ahead) and
    # before the lead sends it.
    leader_edit = origin + 8 * step_ns + round(5.5 * step_ns)
    at_scheduled(c, leader_edit, "step", 7)
    wait_until_ns(c, capture, leader_edit + step_ns)
    # Loop 3: the follower's own Pattern 2 gains a trig at step 6, mid-step 3.
    c.ui.select_channel(2)                                          # Pattern 2
    capture.until(lambda k: onset_count(k, 1, P1[1]) >= 4, timeout=3)
    follower_edit = origin + 24 * step_ns + round(2.5 * step_ns)
    assert now_ns(c) < follower_edit - step_ns, 'follower edit setup missed loop 3'
    at_scheduled(c, follower_edit, "step", 6)
    capture.until(lambda k: onset_count(k, 1, P1[1]) >= 6, timeout=6)
    # The channel grid shows what MIDI now plays (README Interlock).
    c.ui.tap_control("channel_editor")
    loop_leds(c, {1, 2, 3, 4, 6})
    stop_and_drain(c, capture)

    loops = by_loop(place(c, capture.note_ons(), origin))
    anchors = [(s, 1, n, v) for s, (n, v) in P1.items()]
    before = sorted(anchors + [(7, 1) + ADDITION, (5, 2, 60, 100)])
    after_leader = sorted(anchors + [(5, 2, 60, 100), (7, 2, 60, 100)])
    after_follower = sorted(after_leader + [(6, 1) + ADDITION])
    expected = {0: before, 1: after_leader, 2: after_leader, 3: after_follower, 4: after_follower}
    actual = {loop: loops.get(loop) for loop in expected}
    assert actual == expected, dict(expected=expected, actual=actual)

    # README Lock lead time: the lock leaves a whole pulse or more ahead of its
    # note (25 ms rounded up to 4 pulses of 1/144 s at 90 BPM) while its step
    # still has an addition, and never after the edit removed it.
    key = field(c)
    locks = [m for m in capture.messages() if m['type'] == 'cc' and m['channel'] == 1
             and m['data'][:2] == list(LOCK)]
    assert len(locks) == 1, [(m['data'], m[key]) for m in locks]
    note = origin + 6 * step_ns
    lead = (note - locks[0][key]) / 1e9
    pulse = STEP / 24
    slack = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
    assert 4 * pulse - slack <= lead <= 4 * pulse + slack, dict(lead=lead, pulse=pulse)
    assert locks[0][key] < leader_edit
    c.results.append(dict(kind='interlock-freshness', loops={str(k): v for k, v in expected.items()},
                          leader_edit_step=13.5, follower_edit_step=27.5, lock_lead_seconds=lead,
                          stale_locks_after_edit=0, passed=True))


# Interlock: retiming while playing shows RESYNC at once (plan §1.2.1) ----------------------

BOUNDARY = 13   # global pattern length: the boundary lands on follower step 6 of loop 1


def _retime_expectation(retimed):
    """Nominal (old-step time, midi channel, pitch, velocity) of every onset up to
    step 33 when ``retimed`` (1 = follower, 2 = leader) changes /1 -> /2 at the
    pattern boundary after step 13 (README Clocks: a confirmed change takes
    effect at the next global pattern boundary). Leader anchor: step 7.
    Follower: P01 at 1-4, additions at 5 and 7. Before the boundary Interlock
    removes the follower's step-7 addition; from the boundary on the retimed
    pair plays every addition (README Interlock: RESYNC)."""
    follower = {1: P1[1], 2: P1[2], 3: P1[3], 4: P1[4], 5: ADDITION, 7: ADDITION}
    leader = {7: (60, 100)}
    events = []
    for channel, steps in ((1, follower), (2, leader)):
        t, index = 0, 0
        while t <= 33:
            step = index % LOOP + 1
            if step in steps and (t >= BOUNDARY or not (channel == 1 and step == 7)):
                events.append((t, channel) + steps[step])
            t += 2 if (channel == retimed and t >= BOUNDARY) else 1
            index += 1
    return sorted(events)


def _retime_phase(c, retimed):
    capture = Capture(c)
    c.ui.play()
    # Stage /2 on the Clock screen late in loop 0 (after the leader's step-7
    # anchor), then confirm it as soon as the follower's loop 1 has begun:
    # no build of the follower happens between the confirmation and the
    # pattern boundary (step 13).
    capture.until(lambda k: onset_count(k, 2, (60, 100)) >= 1, timeout=5)
    c.ui.set_value(-2)
    capture.until(lambda k: onset_count(k, 1, P1[1]) >= 2, timeout=5)
    origin = capture.note_ons(1)[0][field(c)]
    c.ui.press_key(3)
    confirmed = (now_ns(c) - origin) / 1e9 / STEP
    assert confirmed < BOUNDARY - .5, dict(confirmed_step=confirmed, boundary=BOUNDARY)
    capture.until(lambda k: onset_count(k, 1, P1[1]) >= 3, timeout=6)
    # README Interlock: the follower shows RESYNC and plays every addition
    # until the next Start; Result's Interlock row says the same, and the
    # channel grid shows every addition.
    c.ui.select_channel(1)
    interlock_screen(c)
    c.ui.expect_selected_field("detail", "Status", "RESYNC")
    result_interlock(c, "RESYNC")
    c.ui.tap_control("channel_editor")
    loop_leds(c, {1, 2, 3, 4, 5, 7})
    capture.until(lambda k: len([m for m in k.note_ons(1)
                                 if (m[field(c)] - origin) / 1e9 / STEP > 33.5]) > 0, timeout=8)
    stop_and_drain(c, capture)
    key, allowed = field(c), tolerance(c)
    actual = []
    for m in capture.note_ons():
        t = (m[key] - origin) / 1e9 / STEP
        if t <= 33.5:
            actual.append((round(t), m['channel'], m['data'][0], m['data'][1]))
            assert abs(t - round(t)) * STEP <= allowed, dict(event=m['data'], step_time=t)
    expected = _retime_expectation(retimed)
    assert sorted(actual) == expected, dict(expected=expected, actual=sorted(actual))
    # The follower's step-7 addition sounds in the loop the boundary retimed,
    # before the follower wraps again (review D6: a retimed follower is
    # replanned at once, not at its next wrap).
    next_wrap = 19 if retimed == 1 else 16
    assert [e for e in actual if e[1] == 1 and BOUNDARY < e[0] < next_wrap and e[2:] == ADDITION], actual
    c.results.append(dict(kind='interlock-retime', retimed='follower' if retimed == 1 else 'leader',
                          confirmed_step=confirmed, boundary_step=BOUNDARY, onsets=[list(e) for e in expected],
                          passed=True))


def interlock_retiming_workflow(c):
    """README Interlock ("after a clock division ... change while playing
    (RESYNC, until the next Start ...)") and README Clocks: retiming the
    follower, then (after a new Start) its leader, through the Clock screen
    while playing. When the new rate lands at the pattern boundary the follower
    plays all of its additions from that moment, before its next wrap, and the
    Interlock screen, Result and the channel grid show it; Start clears it."""
    c.ui.set_mosaic_option_keys([("song_mode", False)])
    interlock_pair(c, leader_step=7)
    c.ui.song_editor(); c.ui.tap_control("global_pattern_length", 3)
    c.ui.expect_dashboard_row("Global length", str(BOUNDARY))
    c.ui.channel_editor()
    c.ui.channel_page("clock_mods", channel=1, confirm=False)
    c.ui.expect_header("clock_mods", channel=1)
    _retime_phase(c, retimed=1)
    # README Clocks: stopped, a confirmed change applies at once; the follower
    # returns to /1. The next phase's first loop must again remove the
    # follower's step-7 addition (README Interlock, Window 0): the stopped
    # change replans the follower before Start (plan §1.3 "While stopped").
    c.ui.channel_page("clock_mods", channel=1, confirm=False)
    c.ui.set_value(2); c.ui.press_key(3)
    # README Interlock: RESYNC lasts until the next Start; stopped, Status is ON.
    interlock_screen(c)
    c.ui.expect_selected_field("detail", "Status", "ON")
    c.ui.channel_page("clock_mods", channel=1, confirm=False)
    c.ui.select_channel(2)
    c.ui.expect_header("clock_mods", channel=2)
    _retime_phase(c, retimed=2)


# Structure --------------------------------------------------------------------------

SNAPPED = {1: (60, 127), 2: (60, 117), 3: (64, 107), 4: (64, 97)}   # C D E F -> C C E E


def chord_group(c, channel=1):
    """Voice leading > Groups: group 1, a chord of scale degrees 0, 2 and 4
    (C E G in C major), enabled (README Harmony groups)."""
    c.ui.channel_page("harmony", channel=channel)
    c.ui.select_row("groups", 5); c.ui.press_key(3)
    c.ui.expect_header("harmony_ensemble", channel=channel)
    c.ui.select_row("create_group", 1); c.ui.press_key(3)
    c.ui.select_row("source", 4); c.ui.press_key(3)
    c.ui.select_row("template_count", 1); c.ui.turn(3, 2)
    c.ui.select_row("tone_2", 3); c.ui.turn(3, 2)
    c.ui.select_row("tone_3", 4); c.ui.turn(3, 4)
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    c.ui.press_key(2)
    c.ui.select_row("members", 3); c.ui.press_key(3)
    c.ui.expect_header("harmony_members", channel=channel)
    c.ui.select_row("group_enabled", 2); c.ui.turn(3, 1)
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")


def structure_markers(c, channel=1, markers=1, at_root=False):
    """Merge Shape > Pitch > Structure: Markers (1 = Anchors) with group 1,
    from a Merge Shape child screen (or its root)."""
    if not at_root:
        c.ui.feature_root()
    c.ui.select_row("pitch", 3); c.ui.press_key(3)
    c.ui.expect_header("merge_pitch", channel=channel)
    c.ui.select_row("structure", 3); c.ui.press_key(3)
    c.ui.expect_header("merge_structure", channel=channel)
    c.ui.select_row("structure_markers", 0); c.ui.turn(3, markers)
    c.ui.press_key(3)


def structure_setup(c):
    """README Structure: channel 1 Foundation on P01 (C D E F at 1-4), P02
    additions at 5 and 7, Anchors markers on an enabled C-E-G group."""
    two_patterns(c, (5, 7))
    chord_group(c)
    foundation_on(c, 1)
    structure_markers(c)
    c.ui.expect_selected_field("detail", "Markers", "ANCHORS")
    c.ui.expect_footer_text("APPLIED")


def play_structure(c, loops=2, strummed=(), delay_pulses=0, kind='structure-loops', **record):
    """From stopped: ``loops`` loops of channel 1 and the next loop's step 1,
    checked against SNAPPED anchors plus Foundation additions (5 and 7, or
    ``record['additions']``); a step in ``strummed`` sounds ``delay_pulses``
    late (README Chord Strum). ``silent`` steps play nothing."""
    silent = record.pop('silent', ())
    pitches = dict(SNAPPED); pitches.update(record.pop('pitches', {}))
    additions = record.pop('additions', {5: ADDITION, 7: ADDITION})
    per_loop = sorted([(s,) + v for s, v in pitches.items() if s not in silent] +
                      [(s,) + v for s, v in additions.items() if s not in silent])
    expected = [(n, s, p, v) for n in range(loops) for s, p, v in per_loop] + [(loops, 1) + pitches[1]]
    capture = Capture(c)
    c.ui.play()
    capture.until(lambda k: len(k.note_ons(1)) >= len(expected), timeout=2 + (loops + 1) * LOOP * STEP * 2)
    stop_and_drain(c, capture)
    ons = capture.note_ons(1)[:len(expected)]
    key, allowed = field(c), tolerance(c)
    origin = ons[0][key]
    actual = []
    for m in ons:
        t = (m[key] - origin) / 1e9 / STEP
        # Use the independently expected onset order; real-time jitter may put
        # a note just before its nominal step, where floor mislabels it.
        index = expected[len(actual)][0] * LOOP + expected[len(actual)][1] - 1
        step = index % LOOP + 1
        offset = (t - index) * 24
        want = delay_pulses if step in strummed else 0
        assert abs(offset - want) * STEP / 24 <= allowed, dict(event=m['data'], step=step, offset_pulses=offset,
                                                               expected_pulses=want)
        actual.append((index // LOOP, step, m['data'][0], m['data'][1]))
    assert actual == expected, dict(expected=expected, actual=actual)
    c.results.append(dict(kind=kind, loops=loops, expected=[list(e) for e in expected], strummed=list(strummed),
                          delay_pulses=delay_pulses, tolerance_seconds=allowed, passed=True, **record))


def merge_result_pitch(c, steps, value):
    """Merge Shape > Result: the Pitch row of each step (README Result and Reason)."""
    c.ui.channel_page("merge_shape", channel=1)
    c.ui.select_row("result", 4); c.ui.press_key(3)
    c.ui.expect_header("merge_result", channel=1)
    for step in steps:
        c.ui.select_row("step", 0); c.ui.turn(3, -64); c.ui.turn(3, step - 1)
        c.ui.expect_selected_field("detail", "Step", str(step))
        c.ui.select_row("pitch", 4)
        c.ui.expect_selected_field("detail", "Pitch", value)


def harmony_result(c, rows):
    """Voice leading > Result (H05): per step, the row ``label`` shows ``value``."""
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("result", 9); c.ui.press_key(3)
    c.ui.expect_header("harmony_result", channel=1)
    for step, index, label, value in rows:
        c.ui.select_row("step", 0); c.ui.turn(3, -64); c.ui.turn(3, step - 1)
        c.ui.expect_selected_field("detail", "Step", str(step))
        c.ui.select_row(label.lower(), index)
        c.ui.expect_selected_field("detail", label, value)


def note_grid(c, degrees):
    """Pattern 1's note page (README Pattern editor note view): each step's
    column lights the degree it plays (``shown``), not its authored one."""
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(1); c.ui.tap_control("pattern_editor")
    states = {}
    for step, (shown, authored) in degrees.items():
        states[("pattern_note_degree", (step, shown))] = "active"
        if authored != shown:
            states[("pattern_note_degree", (step, authored))] = "inactive"
    c.ui.expect_leds(states)
    c.ui.tap_control("channel_editor")


def structure_pitch_workflow(c):
    """README Structure (with Result and Reason, Chord Strum and Harmony
    Pattern): a snapped marker root is the same pitch in MIDI, on Pattern 1's
    note grid and on Merge Result and Voice leading Result; a reverse strum
    (Chord Pattern <- and <-->) that delays the root still plays the snapped
    root with Harmony Off; and a mapped note value that snaps at a marker but
    not between markers is silent at both under the Silence and Legacy
    failure fallbacks, with Voice leading Result naming the conflict."""
    structure_setup(c)
    play_structure(c, kind='structure-markers')
    # D (step 2) and F (step 4) sound C and E (README Structure). Plan §4:
    # grid inspection and MIDI consume the same final root, so Pattern 1's
    # note grid shows degrees 0 and 2 there; Merge Result says the pitch is
    # the group's chord tone (README Result and Reason: MARKER CHORD G01).
    # Characterisation outside the manual: Voice leading Result's per-channel
    # row reads "planned > sent" note names (C3 is MIDI 60).
    note_grid(c, {1: (0, 0), 2: (0, 1), 3: (2, 2), 4: (2, 3)})
    merge_result_pitch(c, (2, 4), "MARKER CHORD G01")
    harmony_result(c, [(2, 2, "CH1", "C3 > C3"), (4, 2, "CH1", "E3 > E3")])

    # README Chord Strum: Chord Note Strum 1/6 on the channel; Chord Pattern
    # <- or <--> locked on the marker steps 2 and 4 (README Trig Param Locks:
    # hold the step, turn E3). README Chord Shape: empty mask slots keep their
    # positions and consume spacing, so <- sounds the root after four empty
    # slots, 16 pulses late; the same 16-pulse root delay for <--> is a
    # characterisation outside the manual. The channel's own Chord Pattern is
    # -> (root first, on time): characterisation outside the manual, assigning
    # Chord Pattern at X silences the channel's roots entirely (a legacy defect
    # reported with review D5, not exercised here).
    c.ui.channel_page("trig_locks", channel=1)
    c.ui.assign_trig_parameter_key("chord_note_strum"); c.ui.turn(3, 4)
    c.ui.turn(2, 1); c.ui.assign_trig_parameter_key("chord_pattern"); c.ui.turn(3, 1)
    for shape, value in (("<-", 2), ("<-->", 4)):
        for step in (2, 4):
            with c.ui.hold_step(step):
                c.elapse(.05); c.ui.encoder_event(3, -126); c.elapse(.15); c.ui.turn(3, value)
        play_structure(c, strummed=(2, 4), delay_pulses=16, kind='structure-delayed-root', shape=shape)
    for step in (2, 4):                            # README: hold the step and press K2
        with c.ui.hold_step(step):
            c.elapse(.05); c.ui.press_key(2)
    merge_result_pitch(c, (2, 4), "MARKER CHORD G01")

    # README Structure: Harmony Pattern maps note value 1 (D) to Bass. Value 1
    # is the marker at step 2 (snapped to C) and, after this edit, the
    # addition at step 5 (D): no single mapped pitch, so both are silent
    # whichever fallback is chosen; unmapped values keep their own pitch.
    # Characterisation outside the manual: Voice leading Result's Status
    # names it NO VOICING SOURCE_CONFLICT under both fallbacks.
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(2); c.ui.tap_control("pattern_editor")
    c.ui.tap_control("pattern_note_degree", (5, 1))
    c.ui.tap_control("channel_editor")
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("mode", 0); c.ui.set_value(2)
    c.ui.select_row("tone_map", 3); c.ui.press_key(3)
    c.ui.expect_header("harmony_tone_map", channel=1)
    c.ui.select_row("value_1", 1); c.ui.set_value(1)
    c.ui.expect_selected_field("focused", "Tone 1", "BASS", art=True)
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    for fallback in ("SILENCE", "LEGACY"):
        if fallback == "LEGACY":
            c.ui.channel_page("harmony", channel=1)
            c.ui.select_row("entry", 8); c.ui.press_key(3)
            c.ui.expect_header("harmony_entry", channel=1)
            c.ui.select_row("failure_fallback", 3); c.ui.turn(3, 1)
            c.ui.expect_selected_field("detail", "Failure fallback", fallback)
            c.ui.press_key(3)
            c.ui.expect_footer_text("APPLIED")
        play_structure(c, silent=(2, 5), additions={5: (62, 70), 7: ADDITION},
                       kind='structure-mapped-conflict', fallback=fallback.lower())
        harmony_result(c, [(2, 1, "Status", "NO VOICING SOURCE_CONFLICT"),
                           (5, 1, "Status", "NO VOICING SOURCE_CONFLICT")])


# Structure: group delete/disable while playing (plan §4 Reference lifecycle) -----------

PATTERN_STEPS = 64          # the default global pattern length
LIFECYCLE_LOOPS = {1: 6, 2: 5}   # channel 1 steps 1-6, channel 2 steps 1-5


def _lifecycle_expectation(until, accent_after=None):
    """Nominal (step time, midi channel, pitch, velocity) up to ``until``:
    both channels snap their anchors (C D E F -> C C E E) until the pattern
    boundary at step 64 and play them authored after it; channel 1's addition
    at step 5 has velocity 70, or ``accent_after`` from the boundary."""
    events = []
    for channel, loop in LIFECYCLE_LOOPS.items():
        for t in range(until + 1):
            step = t % loop + 1
            pitches = SNAPPED if t < PATTERN_STEPS else P1
            if step in pitches:
                events.append((t, channel) + pitches[step])
            elif channel == 1 and step == 5:
                events.append((t, 1, 60, 70 if (accent_after is None or t < PATTERN_STEPS) else accent_after))
    return sorted(events)


def _lifecycle_play(c, change, accent_after=None, kind='structure-group-lifecycle', **record):
    """Play; ``change()`` runs early in the first pattern; every onset of both
    channels up to step 76 is checked against _lifecycle_expectation."""
    capture = Capture(c)
    c.ui.play()
    capture.until(lambda k: len(k.note_ons(1)) >= 2, timeout=5)
    origin = capture.note_ons(1)[0][field(c)]
    change()
    done = (now_ns(c) - origin) / 1e9 / STEP
    # The change and any edit waiting with it were made inside the first pattern.
    assert done < PATTERN_STEPS - 2, dict(change_finished_step=done)
    until = PATTERN_STEPS + 12
    capture.until(lambda k: (now_ns(c) - origin) / 1e9 / STEP > until + 1, timeout=until * STEP + 10)
    stop_and_drain(c, capture)
    key, allowed = field(c), tolerance(c)
    actual = []
    for m in capture.note_ons():
        t = (m[key] - origin) / 1e9 / STEP
        if t <= until + .5:
            assert abs(t - round(t)) * STEP <= allowed, dict(event=m['data'], step_time=t)
            actual.append((round(t), m['channel'], m['data'][0], m['data'][1]))
    expected = _lifecycle_expectation(until, accent_after)
    assert sorted(actual) == expected, dict(
        missing=sorted(set(expected) - set(actual)), extra=sorted(set(actual) - set(expected)))
    c.results.append(dict(kind=kind, change_finished_step=done, boundary_step=PATTERN_STEPS,
                          loops={str(k): v for k, v in LIFECYCLE_LOOPS.items()}, onsets=len(expected),
                          tolerance_seconds=allowed, passed=True, **record))


def _members_screen(c):
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("groups", 5); c.ui.press_key(3)
    c.ui.expect_header("harmony_ensemble", channel=1)
    c.ui.select_row("members", 3); c.ui.press_key(3)
    c.ui.expect_header("harmony_members", channel=1)
    c.ui.select_row("group_enabled", 2)


def structure_lifecycle_workflow(c):
    """README Structure: disabling, then deleting, the chord group while
    playing turns Markers Off for every channel that uses it at the next
    pattern boundary, not at an earlier channel wrap: channels 1 (6 steps) and
    2 (5 steps) keep snapping until step 64 and play their authored pitches
    after it. A Merge Shape edit applied to channel 1 while the deletion
    waits shows NEXT PATTERN and lands with it (review D1)."""
    c.configure()
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=LIFECYCLE_LOOPS[1])
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(2); c.ui.tap_step(5)
    c.ui.tap_control("channel_editor"); c.ui.tap_control("pattern_slot", 2)
    chord_group(c)
    foundation_on(c, 1)
    structure_markers(c)
    c.ui.expect_footer_text("APPLIED")
    # Channel 2 on MIDI channel 2 plays Pattern 1 alone over steps 1-5.
    c.ui.select_channel(2)
    c.ui.channel_page("midi_config", channel=2)
    c.ui.set_value(1); c.ui.turn(2, 1); c.ui.set_value(1); c.ui.press_key(3)
    c.ui.tap_control("pattern_slot", 1)
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=LIFECYCLE_LOOPS[2])
    foundation_on(c, 2)
    structure_markers(c, channel=2)
    c.ui.expect_footer_text("APPLIED")
    c.ui.select_channel(1)

    # Disable while playing.
    _members_screen(c)
    def disable():
        c.ui.turn(3, -1)
        c.ui.expect_selected_field("detail", "Group enabled", "OFF")
        c.ui.press_key(3)
    _lifecycle_play(c, disable, kind='structure-group-disabled')
    c.ui.select_channel(2)
    c.ui.channel_page("merge_shape", channel=2)
    c.ui.select_row("pitch", 3); c.ui.press_key(3)
    c.ui.select_row("structure", 3); c.ui.press_key(3)
    c.ui.expect_selected_field("detail", "Markers", "OFF")

    # Stopped: enable the group again and put both channels' markers back.
    c.ui.select_channel(1)
    _members_screen(c)
    c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    for channel in (1, 2):
        c.ui.select_channel(channel)
        c.ui.channel_page("merge_shape", channel=channel)
        structure_markers(c, channel=channel, at_root=True)
        c.ui.expect_footer_text("APPLIED")
    c.ui.select_channel(1)

    # Delete while playing; then a Merge Shape edit on channel 1 (Add accent
    # 70 -> 68) waits for the same pattern boundary.
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("groups", 5); c.ui.press_key(3)
    c.ui.select_row("delete_group", 8)
    def delete_and_edit():
        c.ui.press_key(3)
        c.ui.expect_header("harmony_delete_group", channel=1)
        c.ui.expect_selected_field("detail", "Delete group", "1")
        c.ui.press_key(3)
        # Short E2 clamps (M02 has five rows, M03 seven) keep the whole
        # gesture well inside the first pattern in real time.
        c.ui.channel_page("merge_shape", channel=1)
        c.ui.select_field("rhythm", saturate=-6, then=1); c.ui.press_key(3)
        c.ui.select_field("add_accent", saturate=-8, then=3); c.ui.turn(3, -2)
        c.ui.expect_selected_field("focused", "Add accent", "68", art=True)
        c.ui.press_key(3)
        c.ui.expect_footer_text("NEXT PATTERN")
    _lifecycle_play(c, delete_and_edit, accent_after=68, kind='structure-group-deleted-with-edit')
    c.ui.channel_page("merge_shape", channel=1)
    c.ui.select_row("pitch", 3); c.ui.press_key(3)
    c.ui.select_row("structure", 3); c.ui.press_key(3)
    c.ui.expect_selected_field("detail", "Markers", "OFF")


# Interlock: unequal leader and follower loops under a burst of edits ---------------------

LEADER_LOOP = 6


def _unequal_expectation(until, edit_step, adds_old, adds_new, leader_old, leader_new):
    """Independent model of README Interlock at Window 0 with both channels at
    /1 from Start: follower channel 1 loops 8 steps (P01 anchors at 1-4,
    additions at the follower steps in ``adds``), leader channel 2 loops 6
    steps (anchors at the leader steps in ``leader``). An addition is removed
    exactly when a leader anchor sounds at the same step time; both channels
    use the edited patterns for every step after ``edit_step``."""
    events = []
    for t in range(until + 1):
        new = edit_step is not None and t > edit_step
        follower, leader = t % LOOP + 1, t % LEADER_LOOP + 1
        adds = adds_new if new else adds_old
        anchors = leader_new if new else leader_old
        if follower in P1:
            events.append((t, 1) + P1[follower])
        elif follower in adds and leader not in anchors:
            events.append((t, 1) + ADDITION)
        if leader in anchors:
            events.append((t, 2, 60, 100))
    return sorted(events)


def interlock_unequal_workflow(c):
    """README Interlock, plan §1.2.3 and §1.3: a 6-step leader (anchor at its
    step 3) and an 8-step follower (additions at 5 and 7) meet at different
    places each loop, so which addition is removed changes from loop to loop in
    musical time from Start. While playing, one burst of grid taps inside a
    single step adds a leader anchor (its step 5) and then a follower addition
    (step 6); every later step of both channels follows the edited patterns at
    once. Checked against an independent model over six follower loops in
    exact MIDI, and on the stopped channel grid."""
    two_patterns(c, (5, 7))
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(3); c.ui.tap_step(3)
    c.ui.tap_control("channel_editor")
    c.ui.select_channel(2)
    c.ui.channel_page("midi_config", channel=2)
    c.ui.set_value(1); c.ui.turn(2, 1); c.ui.set_value(1); c.ui.press_key(3)
    c.ui.tap_control("pattern_slot", 3)
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=LEADER_LOOP)
    foundation_on(c, 2)
    c.ui.select_channel(1)
    foundation_on(c, 1)
    c.ui.select_row("interlock", 6); c.ui.press_key(3)
    c.ui.expect_header("merge_interlock", channel=1)
    c.ui.select_row("interlock_leader", 0); c.ui.turn(3, 1)
    c.ui.expect_selected_field("detail", "Leader", "CH02")
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    # Stopped, the grid shows the first loop: the leader anchor sounds at step
    # time 2 (and 8), neither of the additions' times 4 and 6.
    loop_leds(c, {1, 2, 3, 4, 5, 7})
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(3)      # Pattern 3 in the editor

    capture = Capture(c)
    c.ui.play()
    capture.until(lambda k: onset_count(k, 1, P1[1]) >= 2, timeout=5)
    origin = capture.note_ons(1)[0][field(c)]
    step_ns = round(STEP * 1e9)
    # The burst in follower loop 3, step 3 (step time 26), all releases (where
    # the grid applies a tap) before step time 27: Pattern 3 step 5, then
    # Pattern 2 selected, then Pattern 2 step 6.
    edit_step = 26
    at = origin + edit_step * step_ns + round(.15 * step_ns)
    # Native grid deadlines must be within the next two seconds.
    wait_until_ns(c, capture, at - 1_000_000_000)
    schedule = getattr(c, 'merge_acceptance_schedule', 0) + 1
    c.merge_acceptance_schedule = schedule
    c.ui.grid_events_at([(at, "step", 5, 1), (at + 25_000_000, "step", 5, 0),
                         (at + 40_000_000, "channel", 2, 1), (at + 65_000_000, "channel", 2, 0),
                         (at + 80_000_000, "step", 6, 1), (at + 105_000_000, "step", 6, 0)],
                        schedule_id=schedule)
    until = 6 * LOOP - 1
    capture.until(lambda k: (now_ns(c) - origin) / 1e9 / STEP > until + 1, timeout=until * STEP + 10)
    stop_and_drain(c, capture)
    key, allowed = field(c), tolerance(c)
    actual = []
    for m in capture.note_ons():
        t = (m[key] - origin) / 1e9 / STEP
        if t <= until + .5:
            assert abs(t - round(t)) * STEP <= allowed, dict(event=m['data'], step_time=t)
            actual.append((round(t), m['channel'], m['data'][0], m['data'][1]))
    expected = _unequal_expectation(until, edit_step, {5, 7}, {5, 6, 7}, {3}, {3, 5})
    assert sorted(actual) == expected, dict(missing=sorted(set(expected) - set(actual)),
                                            extra=sorted(set(actual) - set(expected)))
    # Stopped again, the grid shows the edited first loop: the leader anchors
    # at step times 2 and 4 remove the addition at step 5 (time 4) only.
    c.ui.tap_control("channel_editor"); c.ui.select_channel(1)
    loop_leds(c, {1, 2, 3, 4, 6, 7})
    c.results.append(dict(kind='interlock-unequal-loops', follower_loop=LOOP, leader_loop=LEADER_LOOP,
                          edit_step=edit_step, onsets=len(expected), tolerance_seconds=allowed, passed=True))


# Structure: marker sets, conflict recovery and Revoice priority ---------------------------

def capture_loop_notes(c, loops=1):
    """From stopped: channel 1's note-ons over ``loops`` loops and the next
    step 1, as (loop, step, pitch, velocity), each on its step's time."""
    capture = Capture(c)
    c.ui.play()
    capture.until(lambda k: len(k.note_ons(1)) >= 1 and (now_ns(c) - k.note_ons(1)[0][field(c)]) / 1e9
                  > (loops * LOOP + .5) * STEP, timeout=5 + loops * LOOP * STEP * 2)
    stop_and_drain(c, capture)
    key, allowed = field(c), tolerance(c)
    ons = capture.note_ons(1)
    origin = ons[0][key]
    notes = []
    for m in ons:
        t = (m[key] - origin) / 1e9 / STEP
        if t > loops * LOOP + .5:
            break
        assert abs(t - round(t)) * STEP <= allowed, dict(event=m['data'], step_time=t)
        index = round(t)
        notes.append((index // LOOP, index % LOOP + 1, m['data'][0], m['data'][1]))
    return notes


def structure_screen(c, markers_turn=0):
    """Merge Shape > Pitch > Structure on channel 1; turn Markers by
    ``markers_turn`` and apply when nonzero."""
    c.ui.channel_page("merge_shape", channel=1)
    c.ui.select_row("pitch", 3); c.ui.press_key(3)
    c.ui.select_row("structure", 3); c.ui.press_key(3)
    c.ui.expect_header("merge_structure", channel=1)
    c.ui.select_row("structure_markers", 0)
    if markers_turn:
        c.ui.turn(3, markers_turn); c.ui.press_key(3)
        c.ui.expect_footer_text("APPLIED")


def set_note_degree(c, pattern, step, degree):
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(pattern); c.ui.tap_control("pattern_editor")
    c.ui.tap_control("pattern_note_degree", (step, degree))
    c.ui.tap_control("channel_editor")


def structure_harmony_workflow(c):
    """README Structure: Every 4 and Every 8 mark steps 1, 5… and 1… of the
    loop, whatever plays there, and only those snap; after a Harmony Pattern
    mapped-value conflict is resolved the mapped value sounds again; with
    Harmony Revoice a snapped marker keeps its chord tone and Harmony's
    Result says MARKER PRIORITY."""
    structure_setup(c)
    set_note_degree(c, 2, 5, 1)          # Pattern 2 step 5 plays D, not C
    # Every 4: markers at 1 and 5. Step 5's D (an addition) snaps to C (tie
    # between C and E: the lower); anchors 2 and 4 are no longer markers.
    structure_screen(c, 1)
    c.ui.expect_selected_field("detail", "Markers", "EVERY 4")
    authored = {1: (60, 127), 2: (62, 117), 3: (64, 107), 4: (65, 97)}
    play_structure(c, pitches=authored, additions={5: (60, 70), 7: ADDITION},
                   kind='structure-every-4')
    # Every 8: only step 1; step 5 plays its own D.
    structure_screen(c, 1)
    c.ui.expect_selected_field("detail", "Markers", "EVERY 8")
    play_structure(c, pitches=authored, additions={5: (62, 70), 7: ADDITION},
                   kind='structure-every-8')

    # Anchors again; Harmony Pattern maps value 1 (D) to Bass. The marker at
    # step 2 (D, snapped to C) and the addition at step 5 (D) disagree, so
    # value 1 is silent at both (README Structure) ...
    structure_screen(c, -2)
    c.ui.expect_selected_field("detail", "Markers", "ANCHORS")
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("mode", 0); c.ui.set_value(2)
    c.ui.select_row("tone_map", 3); c.ui.press_key(3)
    c.ui.expect_header("harmony_tone_map", channel=1)
    c.ui.select_row("value_1", 1); c.ui.set_value(1)
    c.ui.expect_selected_field("focused", "Tone 1", "BASS", art=True)
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    play_structure(c, silent=(2, 5), additions={5: (62, 70), 7: ADDITION}, kind='structure-conflict')
    # ... and once step 5 plays C again, value 1 occurs only at the marker:
    # it sounds there again with the snapped pitch class C (README Harmony
    # Pattern: a placement keeps the resolved pitch class; the octave is the
    # Bass register's, so only the class and velocity are asserted).
    set_note_degree(c, 2, 5, 0)
    notes = capture_loop_notes(c)
    at = {(loop, step): (pitch, velocity) for loop, step, pitch, velocity in notes}
    assert (0, 2) in at and at[(0, 2)][0] % 12 == 0 and at[(0, 2)][1] == 117, dict(step_2=at.get((0, 2)), notes=notes)
    for step, want in ((1, SNAPPED[1]), (3, SNAPPED[3]), (4, SNAPPED[4]), (5, ADDITION), (7, ADDITION)):
        assert at.get((0, step)) == want, dict(step=step, want=want, got=at.get((0, step)), notes=notes)
    harmony_result(c, [(2, 1, "Status", "OK")])  # Characterisation: recovered mapping reports OK.
    c.results.append(dict(kind='structure-conflict-recovered', step_2=list(at[(0, 2)]), passed=True))

    # Harmony Revoice: the snapped marker roots keep their chord tones (C C E
    # E) and Result names the marker priority.
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("mode", 0); c.ui.set_value(-1)
    c.ui.expect_selected_field("focused", "Mode", "REVOICE", art=True)
    c.ui.press_key(3)
    c.ui.expect_footer_text("APPLIED")
    notes = capture_loop_notes(c)
    at = {(loop, step): (pitch, velocity) for loop, step, pitch, velocity in notes}
    for step in (1, 2, 3, 4):
        assert at.get((0, step)) == SNAPPED[step], dict(step=step, want=SNAPPED[step], got=at.get((0, step)))
    harmony_result(c, [(2, 1, "Status", "MARKER PRIORITY"), (4, 1, "Status", "MARKER PRIORITY")])
    c.results.append(dict(kind='structure-revoice-marker-priority', passed=True))


# Structure: undo, redo, Stop settlement and save/reload of a group deletion ---------------

def _delete_group(c):
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("groups", 5); c.ui.press_key(3)
    c.ui.select_row("delete_group", 8); c.ui.press_key(3)
    c.ui.expect_header("harmony_delete_group", channel=1)
    c.ui.press_key(3)


def _markers(c, value):
    structure_screen(c)
    c.ui.expect_selected_field("detail", "Markers", value)


def _memory(c, detents):
    """Channel Memory (README Memory): E3 steps back (-) or forward (+)."""
    c.ui.channel_page("memory", channel=1)
    c.ui.turn(3, detents)


def structure_history_workflow(c):
    """README Structure with Memory (undo and redo) and save and load: a group
    deletion that turned Markers Off is undone and redone as one step each; a
    deletion made while playing and settled by Stop is Off at the next Start;
    a saved project with markers reloads with them. Pitches are checked in
    MIDI (snapped C C E E with markers, authored C D E F without)."""
    structure_setup(c)
    authored = dict(P1)
    _delete_group(c)
    _markers(c, "OFF")
    play_structure(c, pitches=authored, kind='structure-deleted')
    _memory(c, -1)                                   # undo the deletion
    _markers(c, "ANCHORS")
    play_structure(c, kind='structure-undo')
    _memory(c, 1)                                    # redo it
    _markers(c, "OFF")
    play_structure(c, pitches=authored, kind='structure-redo')
    _memory(c, -1)
    _markers(c, "ANCHORS")

    # Delete while playing, then Stop before the pattern boundary: Stop
    # settles the change, so the next Start plays authored pitches at once.
    c.ui.channel_page("harmony", channel=1)
    c.ui.select_row("groups", 5); c.ui.press_key(3)
    c.ui.select_row("delete_group", 8)
    capture = Capture(c)
    c.ui.play()
    capture.until(lambda k: len(k.note_ons(1)) >= 2, timeout=5)
    c.ui.press_key(3)
    c.ui.expect_header("harmony_delete_group", channel=1)
    c.ui.press_key(3)
    stop_and_drain(c, capture)
    _markers(c, "OFF")
    play_structure(c, pitches=authored, kind='structure-stop-settled')

    # Save with markers, turn them off, load: markers and snapped pitches return.
    _memory(c, -1)
    _markers(c, "ANCHORS")
    c.ui.select_project_action('save'); c.ui.press_key(3); c.ui.press_key(1)
    structure_screen(c, -1)
    c.ui.expect_selected_field("detail", "Markers", "OFF")
    c.ui.select_project_file('new.ptn', returning=True); c.ui.press_key(3); c.ui.press_key(1)
    _markers(c, "ANCHORS")
    play_structure(c, kind='structure-reloaded')

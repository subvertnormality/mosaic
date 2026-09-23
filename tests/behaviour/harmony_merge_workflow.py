"""README Musical Merge and Voice Leading through physical grid/norns input.

The oracles below are literal and do not inspect Mosaic's Lua state.
"""


def documentation_frame(c, expected_sha256, name, stable_rows=None):
    import base64, hashlib
    frame = c.snapshot()['frame']
    if stable_rows is None:
        actual = frame['sha256']
    else:
        pixels = base64.b64decode(frame['pixels_base64'])[:128*stable_rows*4]
        actual = hashlib.sha256(pixels).hexdigest()
    assert actual == expected_sha256, dict(frame=name, expected=expected_sha256, actual=actual)
    c.results.append(dict(kind='documentation-frame', name=name, sha256=actual, passed=True))


def playback_note_messages(c, expected, cycles=2, timeout=6):
    """Assert logical MIDI messages even when Mosaic batches simultaneous voices."""
    before = c.snapshot()['midi_count']
    c.tap(1, 8)

    def messages(state):
        result = []
        for packet in state['midi']:
            if packet['index'] <= before:
                continue
            for message in packet['decoded']:
                if message['type'] == 'note_on' and message['data'][1] > 0:
                    result.append((packet['port'],
                                   [143 + message['channel']] + message['data']))
        return result

    state = c.wait(lambda value: len(messages(value)) >= len(expected) * cycles + 1,
                   timeout=timeout)
    actual = messages(state)
    wanted = [expected[index % len(expected)] for index in range(len(actual))]
    assert actual == wanted, dict(expected=wanted, actual=actual)
    c.tap(1, 8)
    c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    return actual


def setup_foundation(c):
    c.configure()
    # Extend the channel loop, author an independent second pattern, then assign it.
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=8)
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(2)
    c.ui.tap_step(5); c.ui.tap_step(7)
    c.ui.tap_control("channel_editor"); c.ui.tap_control("pattern_slot", 2)
    # Device Config -> Merge Shape. Enable Foundation and explicitly select P01.
    c.ui.turn(1, 2); c.ui.expect_header("merge_shape", channel=1)
    c.ui.turn(3, 1)       # Mode: Foundation (staged).
    c.ui.turn(2, 1); c.ui.press_key(3)  # Rhythm -> M02.
    c.ui.turn(3, 1); c.ui.press_key(3)  # Anchor: P01; apply the whole transaction.
    c.ui.expect_steps({step: "selected" for step in (1, 2, 3, 4, 5, 7)})


def foundation_workflow(c):
    setup_foundation(c)
    # The transport tooltip occupies the bottom rows in real time. Bind the
    # stable editor body; MIDI below separately proves the active result.
    documentation_frame(c, 'aa0964b5b48635be2942ef896c3508bb7e2dc28607e4aaee4522e20d6c42e8f6',
                        'images/merge-shape-foundation.png', stable_rows=55)
    expected = [(1, [144, note, velocity]) for note, velocity in
                ((60, 127), (62, 117), (64, 107), (65, 97), (60, 70), (60, 70))]
    c.playback(expected, cycles=2, timeout=7)
    c.results.append(dict(kind='foundation-physical-workflow', passed=True))


def phrase_build_workflow(c):
    setup_foundation(c)
    # Return to M01, open Phrase, select two cycles and the Build curve (50%, 100%).
    c.ui.turn(1, 1); c.ui.turn(2, 2); c.ui.press_key(3)
    c.ui.turn(3, 1); c.ui.turn(2, 1); c.ui.turn(3, 1); c.ui.press_key(3)
    anchor = [(1, [144, n, v]) for n, v in
              ((60, 127), (62, 117), (64, 107), (65, 97))]
    addition = (1, [144, 60, 70])
    cycles = [(anchor + [addition], [1, 2, 3, 4, 7]),
              (anchor + [addition, addition], [1, 2, 3, 4, 5, 7])]
    expected, positions = [], []
    for index in range(4):
        notes, steps = cycles[index % 2]
        expected.extend(notes); positions.extend(steps)
    expected.append(anchor[0]); positions.append(1)
    before = c.snapshot()['midi_count']; c.ui.play()
    def ons(state):
        result = []
        for packet in state['midi']:
            if packet['index'] <= before: continue
            for message in packet['decoded']:
                if message['type'] == 'note_on' and message['data'][1] > 0:
                    event = dict(packet)
                    event['bytes'] = [143+message['channel']] + message['data']
                    result.append(event)
        return result
    state = c.wait(lambda value: len(ons(value)) >= len(expected), timeout=8)
    actual = [(m['port'], m['bytes']) for m in ons(state)]
    assert actual == expected, dict(expected=expected, actual=actual)
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    times = [m[field] for m in ons(state)]
    expected_steps = []
    for left, right in zip(positions, positions[1:]):
        expected_steps.append(right-left if right > left else 8-left+right)
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .02
    actual_gaps = [(b-a)/1e9 for a, b in zip(times, times[1:])]
    assert all(abs(gap - steps/6) <= tolerance for gap, steps in
               zip(actual_gaps, expected_steps)), dict(expected_steps=expected_steps,
                                                       actual_gaps=actual_gaps)
    c.ui.stop(); c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    c.results.append(dict(kind='foundation-build-phrase', positions=positions,
                          exact_timing=True, passed=True))


def revoice_workflow(c):
    c.configure()
    # Device Config -> Masks; add one scale-degree chord voice.
    c.enc(1, -20); c.enc(2, 3); c.enc(3, 1)
    # Masks -> Harmony; Revoice is the first opt-in mode.
    c.enc(1, 7); c.screen_header('Ch. 1 Harmony')
    c.enc(3, 1); c.key(3)
    expected = []
    for root, upper, velocity in ((48, 50, 127), (50, 52, 117),
                                  (52, 53, 107), (53, 55, 97)):
        expected.extend(((1, [144, root, velocity]), (1, [144, upper, velocity])))
    playback_note_messages(c, expected, cycles=2, timeout=6)
    c.results.append(dict(kind='revoice-physical-workflow', passed=True))


def setup_pattern_harmony(c):
    c.configure()
    # Put the legacy material two octaves above the Bass role's legal register.
    c.ui.tap_control("shift_right")
    # Harmony: Pattern, then map the recurring written tone 0 to the Bass role.
    c.ui.turn(1, 3); c.ui.expect_header("harmony", channel=1)
    c.ui.turn(3, 2)
    c.ui.turn(2, 3); c.ui.press_key(3)
    c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.expect_header("harmony", channel=1)


def assert_pattern_progression_timing(c, notes, stage,
                                      active_steps=(1, 2, 3, 4)):
    """PATTERN-HARMONY PH-03: pitch placement adds no onset or gate delay."""
    from cases import assert_durations
    # configure() authors four consecutive default-division/default-length
    # steps.  At Mosaic's 90 BPM fixture that is one sixth of a second per
    # step.  The ninth Note On only closes two complete loops and is stopped
    # immediately by Driver.playback(), so the first eight are the literal
    # two-cycle timing oracle.
    complete_count = len(active_steps) * 2
    complete = notes[:complete_count]
    assert len(complete) == complete_count, notes
    field = ('logical_ns' if c.clock_mode == 'controlled-experimental'
             else 'monotonic_ns')
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
    expected_offsets = [((cycle * 4) + step - 1) / 6
                        for cycle in range(2) for step in active_steps]
    actual_offsets = [(note[field] - complete[0][field]) / 1e9
                      for note in complete]
    errors = [actual - expected for actual, expected
              in zip(actual_offsets, expected_offsets)]
    assert all(abs(error) <= tolerance for error in errors), dict(
        stage=stage, expected_offsets=expected_offsets,
        actual_offsets=actual_offsets, errors=errors)
    # This pairs each actual emitted pitch with its own Note Off and proves the
    # unchanged one-step gate, including the repeated B identity.
    assert_durations(c, complete, [1] * complete_count)
    c.results.append(dict(kind='pattern-harmony-progression-timing',
                          stage=stage, field=field,
                          expected_onset_offsets_seconds=expected_offsets,
                          actual_onset_offsets_seconds=actual_offsets,
                          expected_gate_seconds=1 / 6,
                          tolerance_seconds=tolerance, passed=True))


def expanded_midi_messages(events):
    """Expand native packets so simultaneous channels/messages remain observable."""
    expanded = []
    for packet in events:
        for message in packet.get('decoded', []):
            if message['type'] not in ('note_on', 'note_off'): continue
            event = dict(packet)
            event['packet_index'] = packet['index']
            event['index'] = len(expanded) + 1
            status = ((144 if message['type'] == 'note_on' else 128)
                      + message['channel'] - 1)
            event['bytes'] = [status] + message['data']
            expanded.append(event)
    return expanded


def pattern_harmony_independent_clocks_workflow(c):
    """PATTERN-HARMONY PH-03: independent public Pattern clocks stay independent."""
    import time
    from cases import assert_durations
    from midi_window import MidiWindow

    c.configure()
    # Leave one public trigger in Pattern 1. Pattern 2 gets its own C source at
    # the same lattice position; a public register edit makes both MIDI channel
    # and pitch identify its independent frame.
    c.ui.pattern_editor()
    for step in (2, 3, 4): c.ui.tap_step(step)
    c.ui.select_channel(2); c.ui.tap_step(1); c.ui.tap_control("channel_editor")

    # Route Channel 2 to MIDI channel 2, select Pattern 2, and set its public
    # channel clock from /1 to /2. Channel 1 remains /1.
    c.ui.select_channel(2); c.ui.expect_header("midi_config", channel=2)
    c.ui.turn(3, 1); c.ui.turn(2, 1); c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.tap_control("pattern_slot", 2); c.ui.hold_control_tap(
        "step", "step", held_index=1, target_index=4)
    c.ui.turn(1, -1); c.ui.expect_header("clock_mods", channel=2)
    c.ui.turn(3, -2); c.ui.press_key(3)

    # Each channel enters Pattern mode and maps its sole written identity to
    # Bass through the real Harmony editor. Defaults place C at 48 and F at 53.
    c.ui.turn(1, 4); c.ui.expect_header("harmony", channel=2)
    c.ui.turn(3, 2); c.ui.turn(2, 3); c.ui.press_key(3); c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.turn(1, -1); c.ui.turn(2, 4); c.ui.press_key(3)
    c.ui.turn(2, 2); c.ui.turn(3, -5); c.ui.press_key(3)
    c.ui.turn(1, -1); c.ui.expect_header("harmony", channel=2)
    c.ui.select_channel(1); c.ui.expect_header("harmony", channel=1)
    c.ui.turn(3, 2); c.ui.turn(2, 3); c.ui.press_key(3); c.ui.turn(3, 1); c.ui.press_key(3)

    capture = MidiWindow(c.snapshot()['midi_count'])
    c.ui.play(); c.elapse(3.0); capture.extend(c.snapshot())
    controlled = c.clock_mode == 'controlled-experimental'
    lower = c.logical_ns if controlled else time.monotonic_ns()
    c.ui.gesture([("play_stop", None)], [("play_stop", None)])
    upper = c.logical_ns if controlled else time.monotonic_ns()
    c.elapse(.5); capture.extend(c.snapshot())
    c.wait(lambda state: not state['midi_capture']['outstanding'])

    field = 'logical_ns' if controlled else 'monotonic_ns'
    tolerance = 2e-9 if controlled else .01
    messages = expanded_midi_messages(capture.events)
    by_channel = {
        1: [event for event in messages
            if event['bytes'][0] == 144 and event['bytes'][2] > 0],
        2: [event for event in messages
            if event['bytes'][0] == 145 and event['bytes'][2] > 0],
    }
    expected = {1: (60, 2/3, 1, 127), 2: (48, 4/3, 2, 100)}
    traces = {}
    for channel, (pitch, interval, gate_steps, velocity) in expected.items():
        notes = by_channel[channel]
        assert len(notes) >= (5 if channel == 1 else 3), (channel, notes)
        assert all(note['bytes'][1:] == [pitch, velocity] for note in notes), notes
        origin = notes[0][field]
        errors = [(note[field] - origin)/1e9 - index*interval
                  for index, note in enumerate(notes)]
        assert all(abs(error) <= tolerance for error in errors), (channel, errors)
        assert_durations(c, notes, [gate_steps] * len(notes), events=messages)
        traces[channel] = dict(pitch=pitch, interval_seconds=interval,
                               gate_seconds=gate_steps/6,
                               onset_count=len(notes), max_phase_error_seconds=max(
                                   abs(error) for error in errors))
    c.results.append(dict(kind='pattern-harmony-independent-public-clocks',
                          channels=traces, clock_labels={'1': '/1', '2': '/2'},
                          stop_bounds=[lower, upper], passed=True))


def pattern_harmony_delayed_bypass_workflow(c):
    """PATTERN-HARMONY PH-03: delayed reverse arp is a timed legacy bypass."""
    import time
    from cases import assign_trig_parameter
    from midi_window import MidiWindow
    from note_schedule import assert_schedule

    c.configure()
    c.ui.turn(1, 3); c.ui.expect_header("harmony", channel=1)
    c.ui.turn(3, 2); c.ui.turn(2, 3); c.ui.press_key(3)
    c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.expect_header("harmony", channel=1)
    # Isolate step 1, author a two-step gate and a third chord mask through the
    # public Pattern and Note Masks pages, then select a 1/6-step reverse arp.
    c.ui.pattern_editor()
    for step in (2, 3, 4): c.ui.tap_step(step)
    c.ui.tap_control("channel_editor"); c.ui.turn(1, -20); c.ui.expect_header("masks", channel=1)
    c.ui.turn(2, 2); c.ui.turn(3, 18)
    c.ui.turn(2, 1); c.ui.turn(3, 2)
    c.ui.turn(1, 1); c.ui.expect_header("trig_locks", channel=1)
    c.ui.assign_trig_parameter('Chord Note Arpeggio'); c.ui.turn(3, 4)
    c.ui.turn(2, 1); c.ui.assign_trig_parameter('Chord Pattern'); c.ui.turn(3, 2)

    capture = MidiWindow(c.snapshot()['midi_count'])
    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    trigger = c.logical_ns if controlled else time.monotonic_ns()
    c.ui.gesture([("play_stop", None)], [("play_stop", None)])
    # Two complete four-note arp phrases finish before the next Pattern cycle;
    # stop in that quiet interval so host input latency cannot admit cycle 3.
    c.elapse(1.3); capture.extend(c.snapshot())
    lower = c.logical_ns if controlled else time.monotonic_ns()
    c.ui.gesture([("play_stop", None)], [("play_stop", None)])
    upper = c.logical_ns if controlled else time.monotonic_ns()
    c.elapse(.5); capture.extend(c.snapshot())
    c.wait(lambda state: not state['midi_capture']['outstanding'])

    # Reverse five-slot order retains three leading empty slots: the audible
    # third begins at pulse 12, root at 16, and the four-step pattern repeats
    # every 96 pulses. Pattern Harmony must bypass both notes to legacy 64/60.
    expected = [(cycle*96 + offset, pitch, 127)
                for cycle in range(2)
                for offset, pitch in ((12, 64), (16, 60),
                                      (32, 64), (36, 60))]
    messages = expanded_midi_messages(capture.events)
    note_ons = [event for event in messages
                if event['bytes'][0] == 144 and event['bytes'][2] > 0]
    assert note_ons, messages
    # Controlled time can bind the three leading rests to the public Start
    # input exactly. In real time the host's transport-start scheduling phase
    # is outside Mosaic's musical clock contract, so bind the complete audible
    # schedule to the first onset while retaining the same 10 ms event bound.
    origin = trigger if controlled else note_ons[0][field] - round(12/144*1e9)
    rows = assert_schedule(
        messages, expected, [4] * len(expected), field=field,
        origin=origin, stop_bounds=(lower, upper),
        tolerance=2e-9 if controlled else .01)
    c.results.append(dict(kind='pattern-harmony-delayed-public-bypass',
                          status='CHORD MASK BYPASS', shape='reverse',
                          leading_rest_pulses=12, interval_pulses=4,
                          arpeggio_repeat_pulses=20,
                          cycle_pulses=96, pitches=[64, 60],
                          absolute_start_delay=controlled,
                          onsets=len(expected), releases=len(rows), passed=True))


def pattern_harmony_workflow(c):
    # Author the user's explicit broken-chord key case A-B-C-B through the
    # existing Pattern Note faders.  These are shared source cells; Harmony is
    # a channel projection and must never flatten its output back into them.
    c.configure(); c.ui.pattern_editor(); c.ui.pattern_editor()
    for step, degree in ((2, 2), (3, 4), (4, 2)):
        c.ui.tap_control("pattern_note_degree", (step, degree))
    c.ui.tap_control("channel_editor")

    # Existing global scale progression: C major for steps 1/2, then C minor
    # from step 3.  No Mosaic chord masks participate in this fixture.
    c.ui.scale_editor()
    with c.ui.hold_keys(1):
        c.elapse(.3); c.ui.tap_control("scale_slot", 2)
    c.ui.turn(3, 2); c.ui.press_key(3)  # Slot 2 Major -> Minor, root remains C.
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=4)
    c.ui.hold_control_tap("step", "scale_slot", held_index=3, target_index=2)
    c.ui.tap_control("channel_editor")

    # Pattern Harmony maps A/B/C identities to Bass/Inner1/Top.  Repeated B
    # occurrences therefore share one role and one placement per frame.
    c.ui.turn(1, 3); c.ui.expect_header("harmony", channel=1)
    c.ui.turn(3, 2); c.ui.turn(2, 3); c.ui.press_key(3)
    c.ui.turn(3, 1)             # Tone 0 -> Bass.
    c.ui.turn(2, 1); c.ui.turn(3, 2)  # Tone 2 -> Inner1.
    c.ui.turn(2, 1); c.ui.turn(3, 5)  # Tone 4 -> Top.
    c.ui.press_key(3)
    # Constrain Bass C below MIDI 56 and Inner1 E/Eb below MIDI 61.  These
    # public Register edits force audible placement while Top G can retain its
    # literal common tone at the C-major -> C-minor boundary.
    c.ui.turn(1, -1); c.ui.turn(2, 4); c.ui.press_key(3)
    c.ui.turn(2, 2); c.ui.turn(3, -5); c.ui.press_key(3)   # v1 High 60 -> 55.
    c.ui.turn(1, -1); c.ui.turn(2, 4); c.ui.press_key(3)
    c.ui.turn(3, 1); c.ui.turn(2, 2); c.ui.turn(3, -12); c.ui.press_key(3)  # v2 High 72 -> 60.
    c.ui.turn(1, -1); c.ui.expect_header("harmony", channel=1)
    mapped = [(1, [144, note, velocity]) for note, velocity in
              ((48, 127), (52, 117), (67, 107), (51, 97))]
    mapped_notes = c.playback(mapped, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, mapped_notes, 'pattern-active')

    # PH-03 rest/history interaction through the actual grid path: remove C's
    # fourth trig while Pattern is active, prove the sparse onset set and its
    # wrap gap, then restore it.  The retained map and following full phrase
    # prove that a rest neither consumes nor corrupts Pattern history.
    c.ui.pattern_editor(); c.ui.tap_step(4); c.ui.tap_control("channel_editor")
    sparse = mapped[:3]
    sparse_notes = c.playback(sparse, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, sparse_notes, 'pattern-rest-step4',
                                      active_steps=(1, 2, 3))
    c.ui.pattern_editor(); c.ui.tap_step(4); c.ui.tap_control("channel_editor")
    restored_notes = c.playback(mapped, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, restored_notes,
                                      'pattern-rest-restored')

    # PH-03 missing-output interaction through the emulator's native hotplug
    # input.  A disconnected route emits and owns no notes; reconnecting must
    # resume the same mapped frame and unchanged timing without a settings edit.
    c.action(type='midi_connection', port=1, connected=False); c.elapse(.1)
    disconnected_before = c.snapshot()['midi_count']
    c.ui.play(); c.elapse(1.0); disconnected = c.snapshot(); c.ui.stop()
    missing_output_notes = [event for event in disconnected['midi']
                            if event['index'] > disconnected_before
                            and event['port'] == 1
                            and len(event['bytes']) == 3
                            and event['bytes'][0] == 144
                            and event['bytes'][2] > 0]
    assert missing_output_notes == [], missing_output_notes
    assert disconnected['midi_capture']['outstanding'] == []
    c.action(type='midi_connection', port=1, connected=True); c.elapse(.3)
    hotplug_notes = c.playback(mapped, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, hotplug_notes,
                                      'pattern-output-reconnected')
    c.results.append(dict(kind='pattern-harmony-output-disconnection',
                          disconnected_note_ons=0,
                          disconnected_outstanding_notes=0,
                          recovered_without_edit=True, passed=True))

    # PH-03 probability rejection through the stock Channel Trig Locks page.
    # Harmony is page 8 and Trig Locks is page 2 in the documented clamped
    # Channel cycle.  Probability zero must schedule nothing and must not
    # consume/corrupt the Pattern frame; restoring 100 resumes it exactly.
    c.ui.turn(1, -6); c.ui.expect_header("trig_locks", channel=1)
    c.ui.assign_trig_parameter_key("trig_probability")
    c.ui.encoder_event(3, -126); c.elapse(.15); c.ui.turn(3, 1)
    rejected_before = c.snapshot()['midi_count']
    c.ui.play(); c.elapse(1.0); rejected = c.snapshot(); c.ui.stop()
    rejected_notes = [event for event in rejected['midi']
                      if event['index'] > rejected_before
                      and event['port'] == 1
                      and len(event['bytes']) == 3
                      and event['bytes'][0] == 144
                      and event['bytes'][2] > 0]
    assert rejected_notes == [], rejected_notes
    assert rejected['midi_capture']['outstanding'] == []
    c.ui.turn(3, 100); c.ui.turn(1, 6); c.ui.expect_header("harmony", channel=1)
    probability_notes = c.playback(mapped, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, probability_notes,
                                      'pattern-probability-restored')
    c.results.append(dict(kind='pattern-harmony-probability-rejection',
                          probability_zero_note_ons=0,
                          probability_zero_outstanding_notes=0,
                          probability_100_recovered=True, passed=True))

    # PH-03 song entry through the public Song grid: copy slot 1 to slot 2,
    # enter the copy, then re-enter the source.  Both entries must carry their
    # own copied Pattern configuration and start with the same literal frame,
    # onset phase and note ownership.
    c.ui.song_editor(); c.ui.hold_control_tap(
        "song_pattern_slot", "song_pattern_slot", held_index=1, target_index=2)
    c.ui.select_song_slot(2)
    copied_song_notes = c.playback(mapped, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, copied_song_notes,
                                      'pattern-copied-song-entry')
    c.ui.select_song_slot(1)
    source_song_notes = c.playback(mapped, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, source_song_notes,
                                      'pattern-source-song-reentry')
    c.ui.tap_control("channel_editor"); c.ui.expect_header("harmony", channel=1)
    c.results.append(dict(kind='pattern-harmony-song-entry',
                          copied_slot=2, source_slot=1,
                          copied_config_played=True,
                          source_reentry_played=True, passed=True))

    # The final played positions span both native seven-row note banks.  The
    # lower bank shows Bass A and both B occurrences; the centred bank shows C.
    c.ui.pattern_editor(); c.ui.pattern_editor()
    with c.ui.hold_control("paint"):
        c.elapse(1.1)
    c.elapse(.1)
    c.ui.expect_leds({("pattern_note_degree", (1, 0)): "active",
                      ("pattern_note_degree", (2, 2)): "active",
                      ("pattern_note_degree", (4, 2)): "active"})
    c.ui.tap_control("panic")
    c.ui.expect_leds({("pattern_note_degree", (3, 4)): "active"})

    # Editing through the visible projection still owns source step 2.  Change
    # B from value 2 to 1, restore it to 2, and prove the exact ordinary source
    # sequence below; no Harmony output is ever written into the pattern.
    c.ui.tap_control("pattern_note_degree", (2, 1)); c.ui.tap_control("pattern_note_degree", (2, 2))
    c.ui.tap_control("channel_editor"); c.ui.turn(1, 3); c.ui.expect_header("harmony", channel=1)
    # Turning Harmony Off through the same public Mode field must reveal the
    # untouched ordinary scale result immediately in both MIDI and grid.
    c.ui.turn(3, -2); c.ui.press_key(3)
    ordinary = [(1, [144, note, velocity]) for note, velocity in
                ((60, 127), (64, 117), (67, 107), (63, 97))]
    ordinary_notes = c.playback(ordinary, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, ordinary_notes, 'off-ordinary')
    c.ui.pattern_editor(); c.ui.pattern_editor()
    c.ui.expect_leds({("pattern_note_degree", (1, 0)): "active",
                      ("pattern_note_degree", (2, 2)): "active",
                      ("pattern_note_degree", (3, 4)): "active",
                      ("pattern_note_degree", (4, 2)): "active"})
    c.ui.tap_control("channel_editor"); c.ui.turn(1, 3); c.ui.expect_header("harmony", channel=1)
    c.ui.turn(3, 2); c.ui.press_key(3)
    recovered_notes = c.playback(mapped, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, recovered_notes, 'pattern-reenabled')
    c.results.append(dict(kind='pattern-harmony-broken-chord-progression',
                          source_values=[0, 2, 4, 2], scale_slots=[1, 1, 2, 2],
                          chord_masks_enabled=False, mapped=mapped,
                          ordinary_after_disable=ordinary,
                          projected_grid_values=[-7, -5, 4, -5],
                          ordinary_grid_values=[0, 2, 4, 2],
                          repeated_identity='inner1', source_edit_restored=True,
                          rest_active_steps=[1, 2, 3],
                          rest_recovery=True,
                          output_disconnect_silent=True,
                          output_reconnect_recovered=True,
                          probability_zero_silent=True,
                          probability_recovery=True,
                          copied_song_entry=True,
                          source_song_reentry=True,
                          exact_onset_and_gate_timing=True,
                          stop_restart_cycles=11, recovered=True, passed=True))


def pattern_harmony_persistence_workflow(c):
    from driver import Driver, digest
    setup_pattern_harmony(c)
    documentation_frame(c, '86194708548c7adb76d64ed25e3e59b8ef093e938b3a636da7b1b3c818c29836',
                        'images/harmony-tone-map.png')
    expected = [(1, [144, note, velocity]) for note, velocity in
                ((60, 127), (86, 117), (88, 107), (89, 97))]
    c.playback(expected, cycles=2, timeout=6)
    saved = c.data_directory/'autosave.ptn'; pset = c.data_directory/'autosave.pset'
    for seconds in (30, 30, 2): c.elapse(seconds)
    c.wait(lambda _: saved.is_file() and pset.is_file(), timeout=2)
    hashes = [digest(saved), digest(pset)]
    c.finish()
    out = c.out/'reloaded'; out.mkdir()
    loaded = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        loaded.playback(expected, cycles=2, timeout=6)
        loaded.results.append(dict(kind='pattern-harmony-cold-replay',
                                   hashes=hashes, passed=True))
    finally:
        loaded.finish()
    c.results.append(dict(kind='pattern-harmony-persistence-session',
                          nested=str(out), passed=True))


def ensemble_polyrhythm_workflow(c):
    import base64
    from frame_oracle import render
    c.configure()
    # Author independent sparse patterns, then route and assign one to each member.
    rhythms = {2: (1, 3), 3: (2, 4), 4: (4,)}
    for channel, trigs in rhythms.items():
        c.tap(5, 8); c.tap(channel, 1)
        for trig in trigs: c.tap(trig, 4)
        c.tap(3, 8)
        c.tap(channel, 1); c.screen_header(f'Ch. {channel} Device Config', selected=5)
        c.enc(3, 1); c.enc(2, 1); c.enc(3, channel-1); c.key(3)
        c.tap(channel, 2); c.hold_tap((1, 4), (4, 4))

    # Create a four-part group and assign its four explicit channel roles.
    c.tap(1, 1); c.enc(1, 3); c.screen_header('Ch. 1 Harmony')
    c.enc(2, 5); c.key(3)       # Groups
    c.enc(2, 1); c.key(3)       # Create group 1
    c.enc(2, 1); c.key(3)       # Four-part smooth
    c.enc(2, 1); c.key(3)       # Members
    for channel in range(1, 5):
        c.enc(2, 1); c.enc(3, channel)
    c.key(3)                     # Save the disabled, fully assigned group.

    # Opt each member into Ensemble/group 1 through its own Harmony page.
    c.enc(1, 1)
    for channel in range(1, 5):
        if channel > 1: c.tap(channel, 1)
        c.enc(2, -20)
        c.enc(3, 3); c.enc(2, 1); c.enc(3, 1); c.key(3)

    # Enable the now-valid group atomically from channel 4.
    c.enc(2, 4); c.key(3)
    c.enc(2, 3); c.key(3)
    c.enc(2, 5); c.enc(3, 1); c.key(3)

    before = c.snapshot()['midi_count']; c.tap(1, 8)
    def ons(state):
        result = []
        for packet in state['midi']:
            if packet['index'] <= before: continue
            for message in packet['decoded']:
                if message['type'] == 'note_on' and message['data'][1] > 0:
                    event = dict(packet)
                    event['bytes'] = [143+message['channel']] + message['data']
                    result.append(event)
        return result
    state = c.wait(lambda value: sum(m['bytes'][0] == 144 for m in ons(value)) >= 13,
                   timeout=8)
    messages = ons(state)
    expected = {
        1: (48, (127, 117, 107, 97), 1),
        2: (55, (100,), 2),
        3: (64, (100,), 2),
        4: (67, (100,), 4),
    }
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .02
    traces = {}
    for channel, (pitch, velocities, interval) in expected.items():
        trace = [m for m in messages if m['bytes'][0] == 143+channel]
        assert len(trace) >= (13 if channel == 1 else 3), (channel, trace)
        assert all(m['bytes'][1] == pitch for m in trace), (channel, pitch, trace)
        assert [m['bytes'][2] for m in trace] == [velocities[i % len(velocities)]
                                                  for i in range(len(trace))]
        times = [m[field] for m in trace]
        assert all(abs((b-a)/1e9 - interval/6) <= tolerance for a, b in
                   zip(times, times[1:])), (channel, times)
        traces[channel] = times
    c.tap(1, 8); c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    c.results.append(dict(kind='ensemble-polyrhythm', role_pitches={k:v[0] for k,v in expected.items()},
                          times_by_channel=traces, passed=True))

    # Give member 2 a conflicting local E-major lock through the public Scale
    # page. Its own written line must play unchanged by Ensemble and H05 must
    # name the bypass instead of presenting it as a solved/group event.
    c.tap(4, 8); c.tap(3, 3); c.enc(2, -1); c.enc(3, 4); c.key(3)
    c.tap(1, 3); c.tap(3, 8); c.tap(2, 1)
    c.hold_tap((1, 4), (3, 3)); c.elapse(.1)
    marker = c.snapshot()['midi_count']; c.tap(1, 8)
    def local_member(state):
        return [m for m in state['midi'] if m['index'] > marker and
                m['bytes'][0] == 145 and m['bytes'][2] > 0]
    state = c.wait(lambda value: len(local_member(value)) >= 5, timeout=8)
    local_pitches = [m['bytes'][1] for m in local_member(state)]
    assert local_pitches == [64, 64, 64, 64, 64], local_pitches
    c.tap(1, 8); c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    c.screen_header('Ch. 2 Harmony', selected=8)
    c.enc(2, 9); c.key(3)
    bypass = render([(2, 36, 4, 'Status LOCAL SCALE BYPASS')])
    indexes = [(y*128+x)*4+k for y in range(29, 38) for x in range(2, 128) for k in range(3)]
    c.wait(lambda value: all(base64.b64decode(value['frame']['pixels_base64'])[i] == bypass[i]
                             for i in indexes))
    c.results.append(dict(kind='local-scale-bypass', channel=2,
                          pitches=local_pitches, status='LOCAL SCALE BYPASS', passed=True))

    # A member-local octave setting is another explicit Ensemble conflict.
    # Channel 3 must use its ordinary +1-octave pitch instead of the shared
    # role, and H05 must name the exact bypass.
    c.enc(1, 1); c.enc(1, -3); c.tap(3, 1)
    c.tap(11, 8); c.elapse(.1)
    marker = c.snapshot()['midi_count']; c.tap(1, 8)
    def octave_member(state):
        return [m for m in state['midi'] if m['index'] > marker and
                m['bytes'][0] == 146 and m['bytes'][2] > 0]
    state = c.wait(lambda value: len(octave_member(value)) >= 6, timeout=8)
    octave_pitches = [m['bytes'][1] for m in octave_member(state)]
    assert octave_pitches == [72, 72, 72, 72, 72, 72], octave_pitches
    c.tap(1, 8); c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    c.enc(1, 3); c.screen_header('Ch. 3 Harmony', selected=8)
    c.enc(2, 9); c.key(3); c.enc(3, 1)
    octave_bypass = render([(2, 36, 4, 'Status LOCAL OCTAVE BYPASS')])
    c.wait(lambda value: all(base64.b64decode(value['frame']['pixels_base64'])[i] == octave_bypass[i]
                             for i in indexes))
    c.results.append(dict(kind='local-octave-bypass', channel=3, inspected_step=2,
                          pitches=octave_pitches, status='LOCAL OCTAVE BYPASS', passed=True))


def no_voicing_fallback_workflow(c):
    import base64
    from frame_oracle import render
    c.configure(); c.enc(1, 3); c.screen_header('Ch. 1 Harmony')
    c.enc(3, 2)                # Pattern
    c.enc(2, 4); c.key(3)      # Register
    c.enc(2, 1); c.enc(3, 26)  # Bass Low 50
    c.enc(2, 1); c.enc(3, -10) # Bass High 50
    c.enc(2, 1); c.enc(3, 2)   # Bass Centre 50; valid but excludes pitch class C
    c.key(3)
    c.enc(1, 1); c.enc(2, 3); c.key(3)
    c.enc(3, 1); c.key(3)      # Map written tone 0 to Bass.
    silent_mapped = [(1, [144, note, velocity]) for note, velocity in
                     ((62, 117), (64, 107), (65, 97))]
    # Stop at an exact completed output cycle before opening the inspector.
    # H05 deliberately shows the last emitted event; leaving transport running
    # made a documentation frame depend on which real-time step crossed capture.
    c.playback(silent_mapped, cycles=2, timeout=6)
    c.enc(1, 1); c.enc(2, 9); c.key(3)  # Result
    expected = render([(2, 36, 4, 'Status NO VOICING RANGE:V1')])
    indexes = [(y*128+x)*4+k for y in range(29, 38) for x in range(2, 108) for k in range(3)]
    c.wait(lambda state: all(base64.b64decode(state['frame']['pixels_base64'])[i] == expected[i]
                             for i in indexes))
    c.results.append(dict(kind='no-voicing-visible', reason='range', passed=True))
    # Playback is stopped, so both the semantic status and last-emitted rows are
    # stable in real and controlled time.
    documentation_frame(c, 'eddf4b563aa465680053b34cd8be8ebed77c803570c462d416ec99bfde9bc2b4',
                        'images/harmony-no-voicing.png', stable_rows=55)
    c.enc(3, 1)  # H05 Step 2: select one coherent event chain.
    selected = render([(2, 27, 15, 'Step 2'), (2, 45, 4, 'CH1 planned 62')])
    selected_indexes = ([(y*128+x)*4+k for y in range(19, 29) for x in range(2, 42) for k in range(3)] +
                        [(y*128+x)*4+k for y in range(37, 47) for x in range(2, 92) for k in range(3)])
    c.wait(lambda state: all(base64.b64decode(state['frame']['pixels_base64'])[i] == selected[i]
                             for i in selected_indexes))
    c.enc(3, 3)
    empty = render([(2, 27, 15, 'Step 5'), (2, 36, 4, 'Status NO EVENT'),
                    (2, 45, 4, 'CH1 planned NONE')])
    empty_indexes = [(y*128+x)*4+k for y in range(19, 47) for x in range(2, 108) for k in range(3)]
    c.wait(lambda state: all(base64.b64decode(state['frame']['pixels_base64'])[i] == empty[i]
                             for i in empty_indexes))
    c.results.append(dict(kind='unrecorded-step-inspection', step=5, status='NO EVENT', passed=True))
    c.enc(3, -4)
    c.enc(1, 1); c.enc(2, 8); c.key(3)   # Entry / Failure
    c.enc(2, 3); c.enc(3, 1); c.key(3)   # Fallback Legacy
    legacy = [(1, [144, note, velocity]) for note, velocity in
              ((60, 127), (62, 117), (64, 107), (65, 97))]
    c.playback(legacy, cycles=2, timeout=6)
    c.enc(1, 1); c.enc(2, 9); c.key(3)
    legacy_status = render([(2, 36, 4, 'Status LEGACY RANGE')])
    legacy_indexes = [(y*128+x)*4+k for y in range(29, 38) for x in range(2, 108) for k in range(3)]
    c.wait(lambda state: all(base64.b64decode(state['frame']['pixels_base64'])[i] == legacy_status[i]
                             for i in legacy_indexes))
    c.results.append(dict(kind='explicit-legacy-fallback', passed=True))


def held_step_precedence_workflow(c):
    import base64
    from frame_oracle import render
    c.configure()
    c.enc(1, -20); c.screen_header('Ch. 1 Note Masks')
    c.enc(1, 7); c.screen_header('Ch. 1 Harmony')
    c.enc(3, 1)  # Dirty Revoice draft; deliberately do not Apply.
    c.action(type='grid', x=1, y=4, state=1)
    try:
        c.action(type='midi', port=1, bytes=[144, 72, 90]); c.elapse(.05)
        c.action(type='midi', port=1, bytes=[128, 72, 0])
    finally:
        c.action(type='grid', x=1, y=4, state=0); c.elapse(.1)
    c.screen_header('Ch. 1 Trig Locks')
    expected = [(1, [144, note, velocity]) for note, velocity in
                ((72, 90), (62, 117), (64, 107), (65, 97))]
    c.playback(expected, cycles=2, timeout=6)
    c.enc(1, 4); c.screen_header('Ch. 1 Note Dashboard')
    c.action(type='grid', x=2, y=4, state=1)
    try:
        expected_frame = render([(2, 63, 4, 'P62 S62 E62')])
        indexes = [(y*128+x)*4+k for y in range(55, 64) for x in range(2, 72) for k in range(3)]
        c.wait(lambda state: all(base64.b64decode(state['frame']['pixels_base64'])[i] == expected_frame[i]
                                 for i in indexes))
    finally:
        c.action(type='grid', x=2, y=4, state=0)
    c.results.append(dict(kind='held-step-precedence',
                          draft_cancelled=True, gesture_routed_once=True,
                          selected_event_chain='step2:P62/S62/E62', passed=True))

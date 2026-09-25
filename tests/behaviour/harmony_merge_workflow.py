"""README Musical Merge and Voice Leading through physical grid/norns input.

The oracles below are literal and do not inspect Mosaic's Lua state.
"""


def documentation_frame(c, expected_sha256, name, stable_rows=None):
    from contract.harmony_merge_visual import documentation_frame as check
    check(c, expected_sha256, name, stable_rows)


def setup_foundation(c):
    c.configure()
    # Extend the channel loop, author an independent second pattern, then assign it.
    c.ui.hold_control_tap("step", "step", held_index=1, target_index=8)
    c.ui.tap_control("pattern_editor"); c.ui.select_channel(2)
    c.ui.tap_step(5); c.ui.tap_step(7)
    c.ui.tap_control("channel_editor"); c.ui.tap_control("pattern_slot", 2)
    # Device Config -> Merge Shape. Enable Foundation and explicitly select P01.
    c.ui.channel_page("merge_shape", "midi_config", channel=1)
    c.ui.expect_header("merge_shape", channel=1)
    c.ui.turn(3, 1)       # Mode: Foundation (staged).
    c.ui.turn(2, 1); c.ui.press_key(3)  # Rhythm -> M02.
    c.ui.turn(3, 1); c.ui.press_key(3)  # Anchor: P01; apply the whole transaction.
    c.ui.expect_steps({step: "selected" for step in (1, 2, 3, 4, 5, 7)})


def phrase_build_workflow(c):
    setup_foundation(c)
    # Return to M01, open Phrase, select two cycles and the Build curve (50%, 100%).
    # E1 returns to the clean root, which remembers its Rhythm focus.
    c.ui.feature_root(); c.ui.select_row("phrase", 2); c.ui.press_key(3)
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
    # channel clock from /1 to /2. Channel 1 remains /1. The Channel button
    # returns to the remembered edit family, so Device opens through Tasks.
    c.ui.select_channel(2); c.ui.channel_page("midi_config", channel=2)
    c.ui.expect_header("midi_config", channel=2)
    c.ui.set_value(1); c.ui.turn(2, 1); c.ui.set_value(1); c.ui.press_key(3)
    c.ui.tap_control("pattern_slot", 2); c.ui.hold_control_tap(
        "step", "step", held_index=1, target_index=4)
    c.ui.channel_page("clock_mods", "midi_config", channel=2, confirm=False)
    c.ui.expect_header("clock_mods", channel=2)
    c.ui.set_value(-2); c.ui.press_key(3)

    # Each channel enters Pattern mode and maps its sole written identity to
    # Bass through the real Harmony editor. Defaults place C at 48 and F at 53.
    c.ui.channel_page("harmony", "clock_mods", channel=2, confirm=False)
    c.ui.expect_header("harmony", channel=2)
    # The live UI remembers each screen's focus (also across channels), so
    # every row is selected from the first row.
    c.ui.select_row("mode", 0); c.ui.set_value(2); c.ui.select_row("tone_map", 3)
    c.ui.press_key(3); c.ui.expect_header("harmony_tone_map", channel=2)
    c.ui.set_value(1); c.ui.press_key(3)
    c.ui.feature_root(); c.ui.select_row("register", 4); c.ui.press_key(3)
    c.ui.expect_header("harmony_register", channel=2)
    c.ui.select_row("high", 2); c.ui.set_value(-5); c.ui.press_key(3)
    c.ui.feature_root(); c.ui.expect_header("harmony", channel=2)
    # A grid channel select returns to the edit family; reopen Harmony.
    c.ui.select_channel(1); c.ui.channel_page("harmony", channel=1)
    c.ui.expect_header("harmony", channel=1)
    c.ui.select_row("mode", 0); c.ui.set_value(2); c.ui.select_row("tone_map", 3)
    c.ui.press_key(3); c.ui.expect_header("harmony_tone_map", channel=1)
    c.ui.set_value(1); c.ui.press_key(3)

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
    c.ui.expect_header("harmony_tone_map", channel=1)
    # Isolate step 1, author a two-step gate and a third chord mask through the
    # public Pattern and Note Masks pages, then select a 1/6-step reverse arp.
    c.ui.pattern_editor()
    for step in (2, 3, 4): c.ui.tap_step(step)
    c.ui.tap_control("channel_editor"); c.ui.turn(1, -20); c.ui.expect_header("masks", channel=1)
    c.ui.turn(2, 2); c.ui.turn(3, 18)
    c.ui.turn(2, 1); c.ui.turn(3, 2)
    c.ui.turn(1, 1); c.ui.expect_header("trig_locks", channel=1)
    c.ui.assign_trig_parameter_key("chord_note_arpeggio"); c.ui.turn(3, 4)
    c.ui.turn(2, 1); c.ui.assign_trig_parameter_key("chord_pattern"); c.ui.turn(3, 2)

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
    # The Channel button returns to the edit family; Harmony opens through
    # Channel tasks.
    c.ui.channel_page("harmony", channel=1); c.ui.expect_header("harmony", channel=1)
    c.ui.turn(3, 2); c.ui.turn(2, 3); c.ui.press_key(3)
    c.ui.expect_header("harmony_tone_map", channel=1)
    c.ui.turn(3, 1)             # Tone 0 -> Bass.
    c.ui.turn(2, 1); c.ui.turn(3, 2)  # Tone 2 -> Inner1.
    c.ui.turn(2, 1); c.ui.turn(3, 5)  # Tone 4 -> Top.
    c.ui.press_key(3)
    # Constrain Bass C below MIDI 56 and Inner1 E/Eb below MIDI 61.  These
    # public Register edits force audible placement while Top G can retain its
    # literal common tone at the C-major -> C-minor boundary.  E1 returns to
    # the clean root; each screen remembers its focus, so rows are selected
    # from the first row.
    c.ui.feature_root(); c.ui.select_row("register", 4); c.ui.press_key(3)
    c.ui.expect_header("harmony_register", channel=1)
    c.ui.select_row("high", 2); c.ui.turn(3, -5); c.ui.press_key(3)   # v1 High 60 -> 55.
    c.ui.feature_root(); c.ui.select_row("register", 4); c.ui.press_key(3)
    c.ui.select_row("role", 0); c.ui.turn(3, 1)
    c.ui.select_row("high", 2); c.ui.turn(3, -12); c.ui.press_key(3)  # v2 High 72 -> 60.
    c.ui.feature_root(); c.ui.expect_header("harmony", channel=1)
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
    # The live UI opens Trig params and Harmony through Channel tasks.
    c.ui.channel_page("trig_locks", channel=1); c.ui.expect_header("trig_locks", channel=1)
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
    c.ui.turn(3, 100); c.ui.channel_page("harmony", channel=1)
    c.ui.expect_header("harmony", channel=1)
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
    c.ui.tap_control("song_pattern_slot", 2)
    copied_song_notes = c.playback(mapped, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, copied_song_notes,
                                      'pattern-copied-song-entry')
    c.ui.tap_control("song_pattern_slot", 1)
    source_song_notes = c.playback(mapped, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, source_song_notes,
                                      'pattern-source-song-reentry')
    # The Channel button returns to the remembered edit family (Trig params).
    c.ui.tap_control("channel_editor"); c.ui.expect_header("trig_locks", channel=1)
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
    c.ui.tap_control("channel_editor"); c.ui.channel_page("harmony", channel=1)
    c.ui.expect_header("harmony", channel=1)
    # Turning Harmony Off through the same public Mode field must reveal the
    # untouched ordinary scale result immediately in both MIDI and grid.
    c.ui.select_row("mode", 0); c.ui.turn(3, -2); c.ui.press_key(3)
    ordinary = [(1, [144, note, velocity]) for note, velocity in
                ((60, 127), (64, 117), (67, 107), (63, 97))]
    ordinary_notes = c.playback(ordinary, cycles=2, timeout=6)
    assert_pattern_progression_timing(c, ordinary_notes, 'off-ordinary')
    c.ui.pattern_editor(); c.ui.pattern_editor()
    c.ui.expect_leds({("pattern_note_degree", (1, 0)): "active",
                      ("pattern_note_degree", (2, 2)): "active",
                      ("pattern_note_degree", (3, 4)): "active",
                      ("pattern_note_degree", (4, 2)): "active"})
    c.ui.tap_control("channel_editor"); c.ui.channel_page("harmony", channel=1)
    c.ui.expect_header("harmony", channel=1)
    c.ui.select_row("mode", 0); c.ui.turn(3, 2); c.ui.press_key(3)
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

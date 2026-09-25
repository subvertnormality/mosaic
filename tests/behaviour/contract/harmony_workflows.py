"""Physical-input Harmony workflows prepared for the behavior contract owner."""

from contract.harmony_merge_visual import documentation_frame

def playback_note_messages(c, expected, cycles=2, timeout=6):
    """Assert logical MIDI messages even when Mosaic batches simultaneous voices."""
    before = c.snapshot()['midi_count']
    c.ui.play()

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
    c.ui.stop()
    c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    return actual
def setup_pattern_harmony(c):
    c.configure()
    # Put the legacy material two octaves above the Bass role's legal register.
    c.ui.tap_control("shift_right")
    # The octave shift shows Note Masks (the screen follows the grid), so
    # open Harmony through Channel tasks rather than the old page ring.
    # Harmony: Pattern, then map the recurring written tone 0 to the Bass role.
    c.ui.channel_page("harmony", channel=1); c.ui.expect_header("harmony", channel=1)
    c.ui.turn(3, 2)
    c.ui.turn(2, 3); c.ui.press_key(3)
    c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.expect_header("harmony_tone_map", channel=1)
    # Tone Map is a focused screen: its selected tone row shows the applied role.
    c.ui.expect_selected_field("focused", "Tone 0", "BASS", art=True)
def revoice_workflow(c):
    c.configure()
    # Device Config -> Masks; add one scale-degree chord voice.
    c.ui.turn(1, -20); c.ui.turn(2, 3); c.ui.set_value(1)
    # Masks -> Harmony; Revoice is the first opt-in mode.
    c.ui.channel_page("harmony", "masks", channel=1)
    c.ui.expect_header("harmony", channel=1)
    c.ui.set_value(1); c.ui.press_key(3)
    expected = []
    for root, upper, velocity in ((48, 50, 127), (50, 52, 117),
                                  (52, 53, 107), (53, 55, 97)):
        expected.extend(((1, [144, root, velocity]), (1, [144, upper, velocity])))
    playback_note_messages(c, expected, cycles=2, timeout=6)
    c.results.append(dict(kind='revoice-physical-workflow', passed=True))
def pattern_harmony_persistence_workflow(c):
    from driver import Driver, digest
    from persisted_digest import project_digest
    from persisted_ranges import serializer_source
    setup_pattern_harmony(c)
    # The footer carries the apply status and neighbour hints; bind the body.
    documentation_frame(c, '86484afec0974166f3d22cb0a9d71c9ccb5d154e4efca1122120efd94cc5fa58',
                        'images/harmony-tone-map.png', stable_rows=55)
    expected = [(1, [144, note, velocity]) for note, velocity in
                ((60, 127), (86, 117), (88, 107), (89, 97))]
    c.playback(expected, cycles=2, timeout=6)
    saved = c.data_directory/'autosave.ptn'; pset = c.data_directory/'autosave.pset'
    for seconds in (30, 30, 2): c.elapse(seconds)
    c.wait(lambda _: saved.is_file() and pset.is_file(), timeout=2)
    hashes = [project_digest(saved, serializer_source(c)), digest(pset)]
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
    c.configure()
    # Author independent sparse patterns, then route and assign one to each member.
    rhythms = {2: (1, 3), 3: (2, 4), 4: (4,)}
    for channel, trigs in rhythms.items():
        c.ui.pattern_editor(); c.ui.select_channel(channel)
        for trig in trigs: c.ui.tap_step(trig)
        c.ui.tap_control("channel_editor")
        # The Channel button returns to the edit family; Device opens
        # through Channel tasks.
        c.ui.select_channel(channel); c.ui.channel_page("midi_config", channel=channel)
        c.ui.expect_header("midi_config", channel=channel)
        c.ui.set_value(1); c.ui.turn(2, 1); c.ui.set_value(channel-1); c.ui.press_key(3)
        c.ui.tap_control("pattern_slot", channel); c.ui.set_range(1, 4)

    # Create a four-part group and assign its four explicit channel roles.
    c.ui.select_channel(1); c.ui.channel_page("harmony", "midi_config", channel=1)
    c.ui.expect_header("harmony", channel=1)
    c.ui.turn(2, 5); c.ui.press_key(3)       # Groups
    c.ui.turn(2, 1); c.ui.press_key(3)       # Create group 1
    c.ui.turn(2, 1); c.ui.press_key(3)       # Four-part smooth
    c.ui.turn(2, 1); c.ui.press_key(3)       # Members
    c.ui.expect_header("harmony_members", channel=1)
    for channel in range(1, 5):
        c.ui.turn(2, 1); c.ui.set_value(channel)
    c.ui.press_key(3)                     # Save the disabled, fully assigned group.

    # Opt each member into Ensemble/group 1 through its own Harmony page.
    # A grid channel select returns to the edit family, so each member's
    # Harmony opens through Channel tasks.
    c.ui.feature_root()
    for channel in range(1, 5):
        if channel > 1:
            c.ui.select_channel(channel); c.ui.channel_page("harmony", channel=channel)
        c.ui.turn(2, -20)
        c.ui.set_value(3); c.ui.turn(2, 1); c.ui.set_value(1); c.ui.press_key(3)

    # Enable the now-valid group atomically from channel 4. Each screen
    # remembers its focus, so rows are selected from the first row.
    c.ui.turn(2, 4); c.ui.press_key(3)
    c.ui.expect_header("harmony_ensemble", channel=4)
    c.ui.select_row("members", 3); c.ui.press_key(3)
    c.ui.select_row("group_enabled", 5); c.ui.set_value(1)
    c.ui.expect_selected_field("detail", "Group enabled", "ON")
    c.ui.press_key(3)

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
    c.ui.stop(); c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    c.results.append(dict(kind='ensemble-polyrhythm', role_pitches={k:v[0] for k,v in expected.items()},
                          times_by_channel=traces, passed=True))

    # Give member 2 a conflicting local E-major lock through the public Scale
    # page. Its own written line must play unchanged by Ensemble and H05 must
    # name the bypass instead of presenting it as a solved/group event.
    c.ui.scale_editor(); c.ui.tap_control("scale_slot", 3)
    c.ui.turn(2, -1); c.ui.set_value(4); c.ui.press_key(3)
    c.ui.tap_control("scale_slot", 1); c.ui.tap_control("channel_editor")
    c.ui.select_channel(2)
    c.ui.hold_control_tap("step", "channel_scale_slot",
                          held_index=1, target_index=3)
    c.elapse(.1)
    marker = c.snapshot()['midi_count']; c.ui.play()
    def local_member(state):
        return [m for m in state['midi'] if m['index'] > marker and
                m['bytes'][0] == 145 and m['bytes'][2] > 0]
    state = c.wait(lambda value: len(local_member(value)) >= 5, timeout=8)
    local_pitches = [m['bytes'][1] for m in local_member(state)]
    assert local_pitches == [64, 64, 64, 64, 64], local_pitches
    c.ui.stop(); c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    c.ui.channel_page("harmony", channel=2)
    c.ui.expect_header("harmony", channel=2)
    c.ui.select_row("result", 8); c.ui.press_key(3)
    # Result (H05) is focused: select its Status row to read it.
    c.ui.expect_header("harmony_result", channel=2)
    c.ui.select_row("status", 1)
    c.ui.expect_selected_field("focused", "Status", "LOCAL SCALE BYPASS", art=True)
    c.results.append(dict(kind='local-scale-bypass', channel=2,
                          pitches=local_pitches, status='LOCAL SCALE BYPASS', passed=True))

    # A member-local octave setting is another explicit Ensemble conflict.
    # Channel 3 must use its ordinary +1-octave pitch instead of the shared
    # role, and H05 must name the exact bypass. The grid channel select
    # leaves Result for channel 3's edit family, as the old E1 turns did.
    c.ui.select_channel(3)
    c.ui.tap_control("shift_reset"); c.elapse(.1)
    marker = c.snapshot()['midi_count']; c.ui.play()
    def octave_member(state):
        return [m for m in state['midi'] if m['index'] > marker and
                m['bytes'][0] == 146 and m['bytes'][2] > 0]
    state = c.wait(lambda value: len(octave_member(value)) >= 6, timeout=8)
    octave_pitches = [m['bytes'][1] for m in octave_member(state)]
    assert octave_pitches == [72, 72, 72, 72, 72, 72], octave_pitches
    c.ui.stop(); c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    c.ui.channel_page("harmony", "midi_config", channel=3, confirm=False)
    c.ui.expect_header("harmony", channel=3)
    c.ui.select_row("result", 8); c.ui.press_key(3)
    c.ui.expect_header("harmony_result", channel=3)
    c.ui.select_row("step", 0); c.ui.set_value(1)
    c.ui.expect_selected_field("focused", "Step", "2", art=True)
    c.ui.select_row("status", 1)
    c.ui.expect_selected_field("focused", "Status", "LOCAL OCTAVE BYPASS", art=True)
    c.results.append(dict(kind='local-octave-bypass', channel=3, inspected_step=2,
                          pitches=octave_pitches, status='LOCAL OCTAVE BYPASS', passed=True))
def no_voicing_fallback_workflow(c):
    c.configure(); c.ui.channel_page("harmony", "midi_config", channel=1)
    c.ui.expect_header("harmony", channel=1)
    c.ui.set_value(2)                # Pattern
    c.ui.turn(2, 4); c.ui.press_key(3)      # Register
    c.ui.expect_header("harmony_register", channel=1)
    c.ui.turn(2, 1); c.ui.set_value(26)  # Bass Low 50
    c.ui.turn(2, 1); c.ui.set_value(-10) # Bass High 50
    c.ui.turn(2, 1); c.ui.set_value(2)   # Bass Centre 50; valid but excludes pitch class C
    c.ui.expect_selected_field("focused", "Centre", "50", art=True)
    c.ui.press_key(3)
    # E1 returns to the clean root; each screen remembers its focus, so rows
    # are selected from the first row.
    c.ui.feature_root(); c.ui.select_row("tone_map", 3); c.ui.press_key(3)
    c.ui.set_value(1); c.ui.press_key(3)      # Map written tone 0 to Bass.
    silent_mapped = [(1, [144, note, velocity]) for note, velocity in
                     ((62, 117), (64, 107), (65, 97))]
    # Stop at an exact completed output cycle before opening the inspector.
    # H05 deliberately shows the last emitted event; leaving transport running
    # made a documentation frame depend on which real-time step crossed capture.
    c.ui.expect_header("harmony_tone_map", channel=1)
    c.playback(silent_mapped, cycles=2, timeout=6)
    c.ui.feature_root(); c.ui.select_row("result", 9); c.ui.press_key(3)  # Result
    c.ui.expect_header("harmony_result", channel=1)
    # H05 is a focused screen: select Status to read it. (The retired region
    # oracle stopped at x108, so it bound 'NO VOICING RANGE' exactly.)
    c.ui.select_row("status", 1)
    c.ui.expect_selected_field("focused", "Status", "NO VOICING RANGE", art=True)
    c.results.append(dict(kind='no-voicing-visible', reason='range', passed=True))
    # Playback is stopped, so both the semantic status and last-emitted rows are
    # stable in real and controlled time; the footer names neighbour rows.
    documentation_frame(c, '6a06e7cde0f7d2a784aa32575f57609df73910e0f9d4be005e9cdd5e57a641ad',
                        'images/harmony-no-voicing.png', stable_rows=55)
    c.ui.select_row("step", 0); c.ui.set_value(1)  # H05 Step 2: select one coherent event chain.
    c.ui.expect_selected_field("focused", "Step", "2", art=True)
    c.ui.select_row("ch1_planned", 2)
    c.ui.expect_selected_field("focused", "CH1 planned", "62", art=True)
    c.ui.select_row("step", 0); c.ui.set_value(3)
    c.ui.expect_selected_field("focused", "Step", "5", art=True)
    c.ui.select_row("status", 1)
    c.ui.expect_selected_field("focused", "Status", "NO EVENT", art=True)
    c.ui.select_row("ch1_planned", 2)
    c.ui.expect_selected_field("focused", "CH1 planned", "NONE", art=True)
    c.results.append(dict(kind='unrecorded-step-inspection', step=5, status='NO EVENT', passed=True))
    c.ui.select_row("step", 0); c.ui.set_value(-4)
    # K2 returns from the Result child to the Harmony root.
    c.ui.press_key(2); c.ui.expect_header("harmony", channel=1)
    c.ui.select_row("entry", 8); c.ui.press_key(3)   # Entry / Failure
    c.ui.expect_header("harmony_entry", channel=1)
    c.ui.select_row("failure_fallback", 3); c.ui.set_value(1)   # Fallback Legacy
    c.ui.expect_selected_field("detail", "Failure fallback", "LEGACY")
    c.ui.press_key(3)
    legacy = [(1, [144, note, velocity]) for note, velocity in
              ((60, 127), (62, 117), (64, 107), (65, 97))]
    c.playback(legacy, cycles=2, timeout=6)
    c.ui.feature_root(); c.ui.select_row("result", 9); c.ui.press_key(3)
    c.ui.expect_header("harmony_result", channel=1)
    c.ui.select_row("status", 1)
    c.ui.expect_selected_field("focused", "Status", "LEGACY RANGE", art=True)
    c.results.append(dict(kind='explicit-legacy-fallback', passed=True))
def held_step_precedence_workflow(c):
    c.configure()
    c.ui.turn(1, -20); c.ui.expect_header("masks", channel=1)
    c.ui.channel_page("harmony", "masks", channel=1)
    c.ui.expect_header("harmony", channel=1)
    c.ui.set_value(1)  # Dirty Revoice draft; deliberately do not Apply.
    c.ui.expect_selected_field("focused", "Mode", "REVOICE", art=True)
    try:
        with c.ui.hold_step(1):
            # The held step shows the last editable legacy workspace (Trig
            # params, the old Trig Locks) scoped to the held step.
            c.ui.expect_header("trig_locks", channel=1, held=(1,))
            c.action(type='midi', port=1, bytes=[144, 72, 90]); c.elapse(.05)
            c.action(type='midi', port=1, bytes=[128, 72, 0])
    finally:
        c.elapse(.1)
    # Releasing the hold returns to Harmony, whose draft was cancelled.
    c.ui.expect_header("harmony", channel=1)
    c.ui.expect_selected_field("focused", "Mode", "OFF", art=True)
    expected = [(1, [144, note, velocity]) for note, velocity in
                ((72, 90), (62, 117), (64, 107), (65, 97))]
    c.playback(expected, cycles=2, timeout=6)
    c.ui.channel_page("note_dashboard", "trig_locks", channel=1)
    c.ui.expect_header("note_dashboard", channel=1)
    with c.ui.hold_step(2):
        # Output (C06) inspects the held step in place and shows one field at
        # a time: select each stage of step 2's event chain.
        c.ui.expect_header("note_dashboard", channel=1, held=(2,))
        c.ui.select_row("inspected_step", 4)
        c.ui.expect_selected_field("focused", "Step", "STEP02")
        for row, label in ((6, "Planned"), (7, "Scheduled"), (8, "Emitted")):
            c.ui.select_row(label.lower(), row)
            c.ui.expect_selected_field("focused", label, "62")
    c.results.append(dict(kind='held-step-precedence',
                          draft_cancelled=True, gesture_routed_once=True,
                          selected_event_chain='step2:P62/S62/E62', passed=True))

"""Physical-input Harmony workflows prepared for the behavior contract owner."""

from contract.harmony_merge_visual import documentation_frame, expect_rendered_region

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
    # Harmony: Pattern, then map the recurring written tone 0 to the Bass role.
    c.ui.turn(1, 3); c.ui.expect_header("harmony", channel=1)
    c.ui.turn(3, 2)
    c.ui.turn(2, 3); c.ui.press_key(3)
    c.ui.turn(3, 1); c.ui.press_key(3)
    c.ui.expect_header("harmony", channel=1)
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
    documentation_frame(c, '86194708548c7adb76d64ed25e3e59b8ef093e938b3a636da7b1b3c818c29836',
                        'images/harmony-tone-map.png')
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
    from contract.harmony_merge_visual import expect_rendered_region
    c.configure()
    # Author independent sparse patterns, then route and assign one to each member.
    rhythms = {2: (1, 3), 3: (2, 4), 4: (4,)}
    for channel, trigs in rhythms.items():
        c.ui.pattern_editor(); c.ui.select_channel(channel)
        for trig in trigs: c.ui.tap_step(trig)
        c.ui.tap_control("channel_editor")
        c.ui.select_channel(channel); c.ui.expect_header("midi_config", channel=channel)
        c.ui.set_value(1); c.ui.turn(2, 1); c.ui.set_value(channel-1); c.ui.press_key(3)
        c.ui.tap_control("pattern_slot", channel); c.ui.set_range(1, 4)

    # Create a four-part group and assign its four explicit channel roles.
    c.ui.select_channel(1); c.ui.channel_page("harmony", "midi_config", channel=1)
    c.ui.expect_header("harmony", channel=1)
    c.ui.turn(2, 5); c.ui.press_key(3)       # Groups
    c.ui.turn(2, 1); c.ui.press_key(3)       # Create group 1
    c.ui.turn(2, 1); c.ui.press_key(3)       # Four-part smooth
    c.ui.turn(2, 1); c.ui.press_key(3)       # Members
    for channel in range(1, 5):
        c.ui.turn(2, 1); c.ui.set_value(channel)
    c.ui.press_key(3)                     # Save the disabled, fully assigned group.

    # Opt each member into Ensemble/group 1 through its own Harmony page.
    c.ui.turn(1, 1)
    for channel in range(1, 5):
        if channel > 1: c.ui.select_channel(channel)
        c.ui.turn(2, -20)
        c.ui.set_value(3); c.ui.turn(2, 1); c.ui.set_value(1); c.ui.press_key(3)

    # Enable the now-valid group atomically from channel 4.
    c.ui.turn(2, 4); c.ui.press_key(3)
    c.ui.turn(2, 3); c.ui.press_key(3)
    c.ui.turn(2, 5); c.ui.set_value(1); c.ui.press_key(3)

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
    c.ui.expect_header("harmony", channel=2)
    c.ui.turn(2, 9); c.ui.press_key(3)
    expect_rendered_region(c, [(2, 36, 4, 'Status LOCAL SCALE BYPASS')],
                           left=2, right=128, top=29, bottom=38)
    c.results.append(dict(kind='local-scale-bypass', channel=2,
                          pitches=local_pitches, status='LOCAL SCALE BYPASS', passed=True))

    # A member-local octave setting is another explicit Ensemble conflict.
    # Channel 3 must use its ordinary +1-octave pitch instead of the shared
    # role, and H05 must name the exact bypass.
    c.ui.turn(1, 1); c.ui.turn(1, -3); c.ui.select_channel(3)
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
    c.ui.turn(2, 9); c.ui.press_key(3); c.ui.set_value(1)
    expect_rendered_region(c, [(2, 36, 4, 'Status LOCAL OCTAVE BYPASS')],
                           left=2, right=128, top=29, bottom=38)
    c.results.append(dict(kind='local-octave-bypass', channel=3, inspected_step=2,
                          pitches=octave_pitches, status='LOCAL OCTAVE BYPASS', passed=True))
def no_voicing_fallback_workflow(c):
    from contract.harmony_merge_visual import expect_rendered_region
    c.configure(); c.ui.channel_page("harmony", "midi_config", channel=1)
    c.ui.expect_header("harmony", channel=1)
    c.ui.set_value(2)                # Pattern
    c.ui.turn(2, 4); c.ui.press_key(3)      # Register
    c.ui.turn(2, 1); c.ui.set_value(26)  # Bass Low 50
    c.ui.turn(2, 1); c.ui.set_value(-10) # Bass High 50
    c.ui.turn(2, 1); c.ui.set_value(2)   # Bass Centre 50; valid but excludes pitch class C
    c.ui.press_key(3)
    c.ui.turn(1, 1); c.ui.turn(2, 3); c.ui.press_key(3)
    c.ui.set_value(1); c.ui.press_key(3)      # Map written tone 0 to Bass.
    silent_mapped = [(1, [144, note, velocity]) for note, velocity in
                     ((62, 117), (64, 107), (65, 97))]
    # Stop at an exact completed output cycle before opening the inspector.
    # H05 deliberately shows the last emitted event; leaving transport running
    # made a documentation frame depend on which real-time step crossed capture.
    c.playback(silent_mapped, cycles=2, timeout=6)
    c.ui.turn(1, 1); c.ui.turn(2, 9); c.ui.press_key(3)  # Result
    expect_rendered_region(c, [(2, 36, 4, 'Status NO VOICING RANGE:V1')],
                           left=2, right=108, top=29, bottom=38)
    c.results.append(dict(kind='no-voicing-visible', reason='range', passed=True))
    # Playback is stopped, so both the semantic status and last-emitted rows are
    # stable in real and controlled time.
    documentation_frame(c, 'eddf4b563aa465680053b34cd8be8ebed77c803570c462d416ec99bfde9bc2b4',
                        'images/harmony-no-voicing.png', stable_rows=55)
    c.ui.set_value(1)  # H05 Step 2: select one coherent event chain.
    expect_rendered_region(
        c, [(2, 27, 15, 'Step 2'), (2, 45, 4, 'CH1 planned 62')],
        regions=[(2, 42, 19, 29), (2, 92, 37, 47)],
    )
    c.ui.set_value(3)
    expect_rendered_region(c, [(2, 27, 15, 'Step 5'),
                               (2, 36, 4, 'Status NO EVENT'),
                               (2, 45, 4, 'CH1 planned NONE')],
                           left=2, right=108, top=19, bottom=47)
    c.results.append(dict(kind='unrecorded-step-inspection', step=5, status='NO EVENT', passed=True))
    c.ui.set_value(-4)
    c.ui.turn(1, 1); c.ui.turn(2, 8); c.ui.press_key(3)   # Entry / Failure
    c.ui.turn(2, 3); c.ui.set_value(1); c.ui.press_key(3)   # Fallback Legacy
    legacy = [(1, [144, note, velocity]) for note, velocity in
              ((60, 127), (62, 117), (64, 107), (65, 97))]
    c.playback(legacy, cycles=2, timeout=6)
    c.ui.turn(1, 1); c.ui.turn(2, 9); c.ui.press_key(3)
    expect_rendered_region(c, [(2, 36, 4, 'Status LEGACY RANGE')],
                           left=2, right=108, top=29, bottom=38)
    c.results.append(dict(kind='explicit-legacy-fallback', passed=True))
def held_step_precedence_workflow(c):
    from contract.harmony_merge_visual import expect_rendered_region
    c.configure()
    c.ui.turn(1, -20); c.ui.expect_header("masks", channel=1)
    c.ui.channel_page("harmony", "masks", channel=1)
    c.ui.expect_header("harmony", channel=1)
    c.ui.set_value(1)  # Dirty Revoice draft; deliberately do not Apply.
    try:
        with c.ui.hold_step(1):
            c.action(type='midi', port=1, bytes=[144, 72, 90]); c.elapse(.05)
            c.action(type='midi', port=1, bytes=[128, 72, 0])
    finally:
        c.elapse(.1)
    c.ui.expect_header("trig_locks", channel=1)
    expected = [(1, [144, note, velocity]) for note, velocity in
                ((72, 90), (62, 117), (64, 107), (65, 97))]
    c.playback(expected, cycles=2, timeout=6)
    c.ui.channel_page("note_dashboard", "trig_locks", channel=1)
    c.ui.expect_header("note_dashboard", channel=1)
    with c.ui.hold_step(2):
        expect_rendered_region(c, [(2, 63, 4, 'P62 S62 E62')],
                               left=2, right=72, top=55, bottom=64)
    c.results.append(dict(kind='held-step-precedence',
                          draft_cancelled=True, gesture_routed_once=True,
                          selected_event_chain='step2:P62/S62/E62', passed=True))

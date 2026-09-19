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
    c.hold_tap((1, 4), (8, 4))
    c.tap(5, 8); c.tap(2, 1); c.tap(5, 4); c.tap(7, 4)
    c.tap(3, 8); c.tap(2, 2)
    # Device Config -> Merge Shape. Enable Foundation and explicitly select P01.
    c.enc(1, 2); c.screen_header('Ch. 1 Merge Shape')
    c.enc(3, 1)       # Mode: Foundation (staged).
    c.enc(2, 1); c.key(3)  # Rhythm -> M02.
    c.enc(3, 1); c.key(3)  # Anchor: P01; apply the whole transaction.
    c.led_values([(x, 4) for x in (1, 2, 3, 4, 5, 7)], [15] * 6)


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
    c.enc(1, 1); c.enc(2, 2); c.key(3)
    c.enc(3, 1); c.enc(2, 1); c.enc(3, 1); c.key(3)
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
    c.tap(1, 8); c.wait(lambda value: value['midi_capture']['outstanding'] == [])
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
    c.tap(12, 8)
    # Harmony: Pattern, then map the recurring written tone 0 to the Bass role.
    c.enc(1, 3); c.screen_header('Ch. 1 Harmony')
    c.enc(3, 2)
    c.enc(2, 3); c.key(3)
    c.enc(3, 1); c.key(3)
    c.screen_header('Ch. 1 Harmony')


def pattern_harmony_workflow(c):
    setup_pattern_harmony(c)
    documentation_frame(c, '86194708548c7adb76d64ed25e3e59b8ef093e938b3a636da7b1b3c818c29836',
                        'images/harmony-tone-map.png')
    expected = [(1, [144, note, velocity]) for note, velocity in
                ((60, 127), (86, 117), (88, 107), (89, 97))]
    c.playback(expected, cycles=2, timeout=6)
    c.results.append(dict(kind='pattern-harmony-physical-workflow', passed=True))


def pattern_harmony_persistence_workflow(c):
    from driver import Driver, digest
    setup_pattern_harmony(c)
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
    before = c.snapshot()['midi_count']; c.tap(1, 8)
    def ons(state):
        return [m for m in state['midi'] if m['index'] > before and
                m['bytes'][0] == 144 and m['bytes'][2] > 0]
    state = c.wait(lambda value: len(ons(value)) >= 7, timeout=6)
    actual = [(m['port'], m['bytes']) for m in ons(state)]
    wanted = [silent_mapped[i % len(silent_mapped)] for i in range(len(actual))]
    assert actual == wanted, dict(expected=wanted, actual=actual)
    c.enc(1, 1); c.enc(2, 9); c.key(3)  # Result
    expected = render([(2, 27, 15, 'Status NO VOICING')])
    indexes = [(y*128+x)*4+k for y in range(19, 29) for x in range(2, 108) for k in range(3)]
    c.wait(lambda state: all(base64.b64decode(state['frame']['pixels_base64'])[i] == expected[i]
                             for i in indexes))
    c.results.append(dict(kind='no-voicing-visible', reason='range', passed=True))
    # The bottom status line is transient while transport runs; bind every
    # stable UI row and separately assert the semantic NO VOICING glyphs above.
    documentation_frame(c, '355e76b9a69a873e5c34c453ca7657519eb1b34025605303f250403dcb1dc62e',
                        'images/harmony-no-voicing.png', stable_rows=55)
    c.tap(1, 8); c.wait(lambda value: value['midi_capture']['outstanding'] == [])
    c.enc(1, 1); c.enc(2, 8); c.key(3)   # Entry / Failure
    c.enc(2, 3); c.enc(3, 1); c.key(3)   # Fallback Legacy
    legacy = [(1, [144, note, velocity]) for note, velocity in
              ((60, 127), (62, 117), (64, 107), (65, 97))]
    c.playback(legacy, cycles=2, timeout=6)
    c.results.append(dict(kind='explicit-legacy-fallback', passed=True))


def held_step_precedence_workflow(c):
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
    c.results.append(dict(kind='held-step-precedence',
                          draft_cancelled=True, gesture_routed_once=True, passed=True))

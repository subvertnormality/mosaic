"""UI-independent accepted range and global-length workflows."""


def offset_range_clipping(c):
    from cases import assert_durations
    ui = c.ui
    ui.configure(); ui.set_range(2, 4); ui.song_editor()
    ui.tap_control('global_pattern_length', 2); ui.tap_control('global_pattern_length', 8); ui.menu('channel_editor')
    ui.expect_leds({('step', 1): 'dark', ('step', 2): 'selected',
                    ('step', 3): 'selected', ('step', 4): 'dark'})
    notes = c.playback([(1, [144, 62, 117]), (1, [144, 64, 107])], cycles=3, timeout=4)
    assert_durations(c, notes, [1] * 6)
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
    for i, note in enumerate(notes):
        assert abs((note[field] - notes[0][field]) / 1e9 - i / 6) <= tolerance
    c.results.append(dict(kind='offset-channel-global-cap', start=2, end=4,
                          global_length=2, passed=True))


def offset_range_rates(c):
    from cases import assert_durations
    ui = c.ui
    ui.configure(); ui.set_range(2, 4); ui.song_editor()
    ui.tap_control('global_pattern_length', 2); ui.tap_control('global_pattern_length', 8); ui.menu('channel_editor')
    ui.turn(1, -1); selected = 13
    for index, label, factor in [(8, 'x3', 1 / 3), (10, 'x2', .5),
                                 (13, '/1', 1), (15, '/2', 2), (17, '/3', 3)]:
        ui.turn(3, selected - index); ui.press_key(3); selected = index
        notes = c.playback([(1, [144, 62, 117]), (1, [144, 64, 107])],
                           cycles=10, timeout=12)
        assert_durations(c, notes, [factor] * 18)
        field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
        tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
        for i, note in enumerate(notes):
            assert abs((note[field] - notes[0][field]) / 1e9 - i * factor / 6) <= tolerance
        c.results.append(dict(kind='offset-global-range-clock-rate', label=label,
                              completed_loops=10, passed=True))


def accepted_live_range_transitions(c):
    from cases import assert_durations
    ui = c.ui
    ui.configure()
    phrase = [(60, 127), (62, 117), (64, 107), (65, 97)]
    scenarios = [('inside', 2, 2, 4, [3, 4, 2]),
                 ('below', 1, 3, 4, [3, 4]),
                 ('above', 4, 1, 2, [1, 2])]
    for label, after, start, end, tail in scenarios:
        ui.set_range(1, 4)
        marker = c.snapshot()['midi_count']; ui.play()
        def emitted(state):
            return [m for m in state['midi'] if m['index'] > marker
                    and 144 <= m['bytes'][0] <= 159 and m['bytes'][2] > 0]
        before = c.wait(lambda state: len(emitted(state)) >= after)
        assert len(emitted(before)) == after, 'Fixture missed its intended pre-edit onset'
        ui.gesture([('step', start), ('step', end)],
                   [('step', end), ('step', start)])
        assert len(emitted(c.snapshot())) == after, \
            'Fixture edit crossed an onset before its release; retain evidence'
        count = after + len(tail) * 3 + 1
        state = c.wait(lambda state: len(emitted(state)) >= count, 5); notes = emitted(state)
        steps = list(range(1, after + 1)) + [tail[i % len(tail)] for i in range(len(notes) - after)]
        expected = [(1, [144, *phrase[step - 1]]) for step in steps]
        actual = [(m['port'], m['bytes']) for m in notes]
        assert actual == expected, dict(label=label, expected=expected, actual=actual)
        field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
        tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
        for i, note in enumerate(notes):
            assert abs((note[field] - notes[0][field]) / 1e9 - i / 6) <= tolerance
        ui.stop(); c.wait(lambda state: not state['midi_capture']['outstanding'])
        assert_durations(c, notes, [1] * (count - 1))
        ui.expect_leds({('step', i): ('selected' if start <= i <= end else 'dark')
                        for i in range(1, 65)})
        c.results.append(dict(kind='accepted-live-range-transition', relation=label,
                              range=[start, end], after_step=after,
                              expected_steps=steps, passed=True))

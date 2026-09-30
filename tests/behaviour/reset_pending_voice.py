"""A note still sounding at a song transition with "Reset at Song Sequence Change" on
(README 1074, on by default: channels reset at the transition; README 805: "Pattern
resets likewise preserve the remaining duration of sounding notes").

Global length 4; slot 2 is a copy an octave up. Slot 1 step 4 carries a step length
mask of 3 steps, so its note (65) sounds across the transition. It must release 3
steps after its onset while slot 2 starts at its step 1 on time.
"""
PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def reset_pending_voice(c):
    ui = c.ui
    ui.configure()
    ui.song_editor(); ui.tap_control('global_pattern_length', 2)
    for _ in range(3): ui.tap_control('global_pattern_length', 8)       # global length 4
    ui.copy_slot(1, 2, control='song_pattern_slot'); ui.tap_control('song_pattern_slot', 2)
    ui.menu('channel_editor'); ui.tap_control('channel_octave', 1)  # slot 2 = copy, octave +1
    ui.song_editor(); ui.tap_control('song_pattern_slot', 1); ui.menu('channel_editor')
    ui.channel_page('masks', 'midi_config', saturate=True)
    ui.select_field('length', saturate=-5, then=3); ui.expect_field_value('length', 'X')   # Note Masks, Len
    with ui.hold_step(4):
        c.elapse(.05); ui.set_value(22); ui.expect_field_value('length', '3')       # step 4: 3 steps
    before = c.snapshot()['midi_count']; ui.play()
    def onsets(s): return [m for m in s['midi'] if m['index'] > before and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    state = c.wait(lambda s: len(onsets(s)) >= 9, timeout=4)
    ui.stop(); state = c.wait(lambda s: not s['midi_capture']['outstanding'])
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
    notes = onsets(state)[:8]
    expected = [n for n, _ in PHRASE] + [n + 12 for n, _ in PHRASE]
    assert [m['bytes'][1] for m in notes] == expected, [m['bytes'][1] for m in notes]
    start = notes[0][field]
    offsets = [(m[field] - start) / 1e9 for m in notes]
    assert all(abs(o - i / 6) <= tolerance for i, o in enumerate(offsets)), offsets
    long_note = notes[3]
    release = next(m for m in state['midi'] if m['index'] > long_note['index'] and m['port'] == 1 and
                   (m['bytes'][:2] == [128, 65] or (m['bytes'][0] == 144 and m['bytes'][1] == 65 and m['bytes'][2] == 0)))
    held = (release[field] - long_note[field]) / 1e9
    assert abs(held - 3 / 6) <= tolerance, dict(held_seconds=held, expected=.5)
    c.results.append(dict(kind='reset-pending-voice', held_seconds=held, onsets=offsets, passed=True))

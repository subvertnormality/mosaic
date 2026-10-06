"""M-TRANS-010: a copied song slot keeps its own transposition (README.md#transposition, README.md#song-editor)."""


def assert_sixteenths(c, notes):
    """README.md#channel-length: sixteenth-note steps at the default 90 BPM are 1/6 s apart."""
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .02
    gaps = [(b[field] - a[field]) / 1e9 for a, b in zip(notes, notes[1:])]
    assert all(abs(gap - 1 / 6) <= tolerance for gap in gaps), gaps


def transpose_song_slot_copy(c):
    """README.md#transposition and README.md#song-editor: a copied song slot takes its own
    global transposition; the original slot keeps its pitches."""
    c.configure()
    velocities = (127, 117, 107, 97)
    c.ui.song_editor()
    c.ui.copy_slot(1, 2, control='song_pattern_slot')
    c.ui.tap_control('song_pattern_slot', 2)
    c.ui.expect_leds({('song_pattern_slot', 1): 'alternate', ('song_pattern_slot', 2): 'selected'})
    c.ui.scale_editor()
    c.ui.tap_control('global_transpose_minimum')
    for _ in range(14):
        c.ui.tap_control('global_transpose_increment')   # -12 + 14 = +2
    c.ui.expect_dashboard_row('Transpose', '+2')
    copy = [(1, [144, n + 2, v]) for n, v in zip((60, 62, 64, 65), velocities)]
    notes = c.playback(copy, cycles=2, timeout=6)
    assert_sixteenths(c, notes)
    c.results.append(dict(kind='song-slot-transpose', stage='slot2-plus-two', pitches=[e[1][1] for e in copy], passed=True))
    c.ui.song_editor()
    c.ui.tap_control('song_pattern_slot', 1)
    c.ui.expect_leds({('song_pattern_slot', 1): 'selected', ('song_pattern_slot', 2): 'alternate'})
    original = [(1, [144, n, v]) for n, v in zip((60, 62, 64, 65), velocities)]
    notes = c.playback(original, cycles=2, timeout=6)
    assert_sixteenths(c, notes)
    c.results.append(dict(kind='song-slot-transpose', stage='slot1-original', pitches=[e[1][1] for e in original], passed=True))

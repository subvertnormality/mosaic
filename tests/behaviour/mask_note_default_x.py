"""Native behavior case for clearing a channel Note default back to X."""


def mask_note_default_unset(c):
    """Characterization for manual feature masks / scene mask-note-default-x.

    The public Masks selector changes the channel default only when no step is
    held. Returning it to X restores the merged pattern notes; this case does
    not press K2, which clears step exceptions instead.
    """
    from cases import assert_durations

    ui = c.ui
    ui.configure()
    ui.channel_page('masks', 'midi_config', channel=1)
    ui.select_field('note', offset=0)
    ui.expect_header('masks', channel=1)
    ui.expect_field_value('note', 'X')

    ui.set_value(68)
    ui.expect_field_value('note', 'G3')
    channel_phrase = [(1, [144, 67, velocity]) for velocity in (127, 117, 107, 97)]
    channel_notes = c.playback(channel_phrase, cycles=2, timeout=5)
    assert_durations(c, channel_notes, [1] * 8)

    ui.set_value(-68)
    ui.expect_field_value('note', 'X')
    pattern_phrase = [
        (1, [144, 60, 127]),
        (1, [144, 62, 117]),
        (1, [144, 64, 107]),
        (1, [144, 65, 97]),
    ]
    restored_notes = c.playback(pattern_phrase, cycles=2, timeout=5)
    assert_durations(c, restored_notes, [1] * 8)
    c.results.append({
        'kind': 'channel-note-default-unset-restores-pattern',
        'citation': 'manual:masks',
        'channel_default_before': 'G3',
        'channel_default_after': 'X',
        'channel_phrase': channel_phrase,
        'restored_pattern_phrase': pattern_phrase,
        'cycles': 2,
        'passed': True,
    })

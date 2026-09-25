"""A completed pattern edit just before a song boundary reaches a late channel.

README lines 447-465 describe pattern-note editing and lines 1070-1074 describe
song-pattern advancement. The source-pattern edit is committed by the final grid
release (user-confirmed characterisation, not manual text). Channel 16 widens the working-pattern rebuild window: Mosaic refreshes
one channel per scheduler tick, so a complete tap 30 ms before the boundary is
late enough to expose cancellation of the in-flight rebuild without relying on a
release that crosses the boundary.

The input-validity oracle is deliberately separate from the musical defect oracle:
both grid callbacks must complete before the boundary. Only then may stale MIDI
from channel 16 count as a reproduction.
"""


def pattern_boundary_edit(c):
    import time

    ui = c.ui
    ui.configure()

    # Give channel 16 an independently observable MIDI route and pattern 1.
    # This is the same tested second-channel device recipe used by
    # shuffle_mixed_channels.py, applied to the last channel in the rebuild sweep.
    ui.select_channel(16)
    ui.channel_page('midi_config', channel=16)  # channel select shows C01/C02; Device opens from Tasks
    ui.set_value(1); ui.select_field('midi_channel', offset=1); ui.set_value(1)
    ui.select_field('default_velocity', offset=1); ui.set_value(1); ui.press_key(3)
    ui.tap_control('pattern_slot', 1); ui.set_range(1, 4)

    # Silence channel 1 through the documented shift-press mute gesture, leaving
    # channel 16 as the sole musical oracle.
    with ui.hold_keys(1):
        ui.select_channel(1)
    ui.select_channel(16)

    # Two four-step song slots; slot 2 is copied from slot 1 and transposed +1 octave.
    ui.song_editor(); ui.tap_control('global_pattern_length', 2)
    for _ in range(3):
        ui.tap_control('global_pattern_length', 8)
    ui.copy_slot(1, 2, control='song_pattern_slot')
    ui.tap_control('song_pattern_slot', 2)
    ui.menu('channel_editor'); ui.tap_control('channel_octave', 1)

    # Return to pattern 1's note editor.
    ui.song_editor(); ui.tap_control('song_pattern_slot', 1)
    ui.pattern_editor(); ui.pattern_editor(view='note', from_view='trigger')

    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    before = c.snapshot()['midi_count']
    ui.play()

    def onsets(state):
        return [
            message for message in state['midi']
            if message['index'] > before
            and message['port'] == 2
            and message['bytes'][0] == 145
            and message['bytes'][2] > 0
        ]

    first = c.wait(lambda state: len(onsets(state)) >= 1, timeout=2)
    start = onsets(first)[0][field]
    boundary = start + round(4 / 6 * 1e9)
    press_at = boundary - 31_000_000
    release_at = boundary - 30_000_000

    if controlled:
        ui.grid_events_at([
            (press_at, 'pattern_note_degree', (1, 4), 1),
            (release_at, 'pattern_note_degree', (1, 4), 0),
        ])
        completions = [press_at, release_at]
        validity = dict(
            kind='pattern-boundary-input-validity',
            lane='controlled-experimental',
            boundary_ns=boundary,
            planned_ns=[press_at, release_at],
            callback_completed_ns=completions,
            both_callbacks_completed_before_boundary=all(value < boundary for value in completions),
        )
    else:
        # Submit both halves together before either is due. This prevents the
        # release timing from depending on the response to the press.
        now = time.monotonic_ns()
        assert press_at - now >= 100_000_000, dict(press_at=press_at, now=now)
        ack = ui.grid_events_at([
            (press_at, 'pattern_note_degree', (1, 4), 1),
            (release_at, 'pattern_note_degree', (1, 4), 0),
        ])
        assert ack['status'] == 'accepted', ack
        record = c.wait(
            lambda state: state.get('native_input_schedule', {}).get('status') == 'completed',
            timeout=2,
        )['native_input_schedule']
        assert [delivery['index'] for delivery in record['delivered']] == [0, 1], record
        completions = [
            delivery['callback_completed_monotonic_ns']
            for delivery in record['delivered']
        ]
        validity = dict(
            kind='pattern-boundary-input-validity',
            lane='real-time',
            boundary_ns=boundary,
            planned_ns=[press_at, release_at],
            callback_completed_ns=completions,
            both_callbacks_completed_before_boundary=all(value < boundary for value in completions),
        )

    c.results.append(validity)
    assert validity['both_callbacks_completed_before_boundary'], validity

    state = c.wait(lambda state: len(onsets(state)) >= 13, timeout=5)
    ui.stop()
    c.wait(lambda state: not state['midi_capture']['outstanding'])
    notes = [message['bytes'][1] for message in onsets(state)[:13]]
    expected = [60, 62, 64, 65, 72, 74, 76, 77, 67, 62, 64, 65, 72]
    c.results.append(dict(
        kind='pattern-boundary-edit',
        channel=16,
        expected=expected,
        actual=notes,
        input_validity=validity,
    ))
    assert notes == expected, dict(expected=expected, actual=notes, input_validity=validity)

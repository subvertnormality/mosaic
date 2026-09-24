"""Contract-owned Foundation merge-shape workflow."""

from contract.harmony_merge_visual import documentation_frame


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

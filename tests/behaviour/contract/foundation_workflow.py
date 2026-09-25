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
    # Rhythm (M03) is a focused screen: it shows only the selected row, so
    # select each applied setting to see its exact value.
    c.ui.select_field("add_amount", offset=1)
    c.ui.expect_selected_field("focused", "Add amount", "100", art=True)
    c.ui.select_field("add_accent", offset=2)
    c.ui.expect_selected_field("focused", "Add accent", "70", art=True)
    # The footer carries status/transport tooltips that vary by lane. Bind the
    # stable editor body; MIDI below separately proves the active result.
    documentation_frame(c, '7e00869b95cd393028d1a6371708b36c02b83f2e710aa5b64534d24f3fad9301',
                        'images/merge-shape-foundation.png', stable_rows=55)
    expected = [(1, [144, note, velocity]) for note, velocity in
                ((60, 127), (62, 117), (64, 107), (65, 97), (60, 70), (60, 70))]
    c.playback(expected, cycles=2, timeout=7)
    c.results.append(dict(kind='foundation-physical-workflow', passed=True))

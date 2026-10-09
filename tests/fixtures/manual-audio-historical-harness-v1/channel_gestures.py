"""Small public-input gestures shared by behaviour cases and the manual audio setups.

Each helper only drives the grid, keys and encoders; callers own the oracle.
"""

# Coarse positions of the Song editor's global length fader (grid x of row 7)
# and the length each one selects; cell 1 steps down by one and cell 8 up by one.
GLOBAL_LENGTH_CELLS = {2: 1, 3: 13, 4: 32, 5: 38, 6: 51, 7: 64}
GLOBAL_LENGTH_INCREMENT_CELL = 8


def set_channel_swing(ui, channel, amount, from_top=False):
    """README Clocks, Swing and Shuffle: choose the Swing mode, then its amount (-50..50),
    on the Clock screen of ``channel`` (already the selected channel). The Clock screen keeps
    its selected row when it is reopened for another channel; ``from_top`` first returns to the
    first row (E2 clamps), as a freshly opened screen starts."""
    ui.channel_page('clock_mods', channel=channel, confirm=False)
    if from_top:
        ui.select_field('clock_first_row', saturate=-12)
    ui.select_field('swing', offset=1); ui.set_value(1); ui.press_key(3)
    ui.select_field('swing_x', offset=1); ui.set_value(amount + 51); ui.press_key(3)


def shift_mute_channel(c, channel):
    """README Muting Channels: shift press (hold K1, tap the channel) toggles its mute."""
    with c.ui.hold_keys(1):
        c.elapse(.3)
        c.ui.tap_control("channel", channel)


def global_length_taps(length):
    """Fader presses (cell numbers) that set the selected song slot's global length."""
    if not 1 <= length <= 64:
        raise ValueError("global length must be 1..64")
    cell, base = max(((cell, value) for cell, value in GLOBAL_LENGTH_CELLS.items() if value <= length),
                     key=lambda pair: pair[1])
    return [cell] + [GLOBAL_LENGTH_INCREMENT_CELL] * (length - base)


def set_global_pattern_length(ui, length):
    """README Adjusting Song Sequence Length: set the Song editor fader to ``length`` and
    read the Global length row back."""
    for cell in global_length_taps(length):
        ui.tap_control("global_pattern_length", cell)
    ui.expect_dashboard_row("Global length", str(length))

"""Live norns screen contracts (README "Norns Menu Navigation").

The screen follows the grid, every Channel screen is reachable through Channel
tasks, E1 opens the page's task list from any screen, and the start-up
animation lays tiles, reveals the name and hands over to the first screen, or
is skipped by any input. Headers are checked with the live header oracle; the
splash is checked structurally (tile coverage), never by an image.
"""
import base64

import re
from pathlib import Path

# The splash draws the logo's blocks (lib/ui_splash_logo.lua, generated from
# images/logo.svg): dots and pills on a 15 x 9 grid of 8 x 7 px cells from x 4.
_LOGO = (Path(__file__).resolve().parents[3] / "lib" / "ui_splash_logo.lua").read_text()
_BLOCKS = [tuple(int(v) for v in m) for m in re.findall(
    r"\{row = (\d+), first = (\d+), last = (\d+), level = \d+\}", _LOGO)]
TILE_CENTRES = [(4 + column * 8 + 3, row * 7 + 3)
                for row, first, last in _BLOCKS for column in range(first, last + 1)]


def _lit_tiles(state):
    """Logo block cells whose 4 x 4 core is lit at its centre and corners: a laid
    block, never a letter stroke of the revealed wordmark."""
    pixels = base64.b64decode(state["frame"]["pixels_base64"])
    # A dot's centre is a pixel corner (x, y): its 4 x 4 core is pixels x-2..x+1.
    points = ((-1, -1), (-2, -2), (1, -2), (-2, 1), (1, 1))
    return sum(1 for x, y in TILE_CENTRES
               if all(pixels[((y + dy) * 128 + x + dx) * 4] > 0 for dx, dy in points))


def live_ui_follow(c):
    """README: the screen follows grid page buttons, channel selection and held steps."""
    ui = c.ui
    ui.tap_control("channel_editor"); ui.expect_header("masks", channel=1)
    ui.tap_control("scale_editor"); ui.expect_header("scale", slot=1)
    ui.tap_control("pattern_editor"); ui.expect_header("trigger_editor")
    ui.tap_control("pattern_editor"); ui.expect_header("note_editor")
    ui.tap_control("pattern_editor"); ui.expect_header("velocity_editor")
    ui.tap_control("song_editor"); ui.expect_header("song")
    ui.tap_control("channel_editor"); ui.expect_header("masks", channel=1)
    ui.select_channel(3); ui.expect_header("masks", channel=3)
    # Holding a step scopes the edit family to it; release restores the screen.
    with ui.hold_step(5):
        ui.expect_header("masks", channel=3, held=(5,))
        c.results.append(dict(kind="held-scope", step=5, passed=True))
    ui.expect_header("masks", channel=3)
    # From another Channel screen, a hold shows the remembered family (Masks: E1 opens
    # Channel tasks straight from it, so Trig params was never shown), then returns.
    ui.channel_page("clock_mods", channel=3)
    with ui.hold_step(9):
        ui.expect_header("masks", channel=3, held=(9,))
    ui.expect_header("clock_mods", channel=3)
    c.results.append(dict(kind="hold-returns-to-parent", screen="clock_mods", passed=True))


def live_ui_tasks(c):
    """README: E1 opens the page's task list from any screen, on the row of the
    screen it came from; E1 or E2 moves through the rows; K3 opens every Channel screen."""
    ui = c.ui
    ui.tap_control("channel_editor"); ui.expect_header("masks", channel=1)
    c.enc(1, 1); ui.expect_header("channel_tasks", channel=1); ui.expect_task_row("Masks")
    c.results.append(dict(kind="e1-opens-tasks", source="masks", passed=True))
    # Both encoders scroll the list, one row per detent, clamped at the ends.
    for encoder, delta, row in ((1, 1, "Trig params"), (1, 1, "Output"), (2, 1, "Harmony"),
                                (2, -1, "Output"), (1, -1, "Trig params")):
        c.enc(encoder, delta); ui.expect_header("channel_tasks", channel=1); ui.expect_task_row(row)
        c.results.append(dict(kind="task-scroll", encoder=encoder, delta=delta, row=row, passed=True))
    c.enc(1, -3); ui.expect_task_row("Masks")
    c.enc(2, 1); c.key(3); ui.expect_header("trig_locks", channel=1)
    # From Trig params, E1 (either way) opens the list again on Trig params.
    c.enc(1, -1); ui.expect_header("channel_tasks", channel=1); ui.expect_task_row("Trig params")
    c.results.append(dict(kind="e1-opens-tasks", source="trig_locks", passed=True))
    c.key(3); ui.expect_header("trig_locks", channel=1)
    for page in ("memory", "clock_mods", "midi_config", "note_dashboard", "merge_shape", "harmony",
                 "masks", "trig_locks"):
        ui.channel_page(page)
        c.results.append(dict(kind="channel-task", page=page, passed=True))


def live_ui_splash(c):
    """README: the logo's blocks lay down, lift to leave the wordmark, then the first screen; input skips it."""
    from driver import Driver

    c.finish()
    runs = [("played", False), ("skipped", True)]
    for name, skip in runs:
        out = c.out / name
        out.mkdir()
        # No lead-time setup: it would press keys, which ends the splash.
        d = Driver(out, midi_lead_time_ms=None, clock_mode=c.clock_mode,
                   experimental_install=c.launch_options.get("experimental_install"))
        try:
            if skip:
                d.key(2)
                d.ui.expect_header("masks", channel=1)
                state = d.snapshot()
                assert _lit_tiles(state) < 16, "splash still showing after input"
                d.results.append(dict(kind="splash-skipped", passed=True))
            else:
                # The whole logo: every cell a block covers is lit at once.
                d.wait(lambda s: _lit_tiles(s) == len(TILE_CENTRES), timeout=3)
                d.results.append(dict(kind="splash-tiles", passed=True))
                d.wait(lambda s: _lit_tiles(s) < 8, timeout=3)
                d.results.append(dict(kind="splash-lifted", passed=True))
                d.ui.expect_header("masks", channel=1)
                d.results.append(dict(kind="splash-handover", passed=True))
                # One input so the session has an input trace to verify (K2 on
                # Masks changes nothing without held steps or K1).
                d.key(2)
                d.ui.expect_header("masks", channel=1)
        finally:
            d.finish()
        c.results.append(dict(kind="splash-session", name=name, nested=str(out), passed=True))

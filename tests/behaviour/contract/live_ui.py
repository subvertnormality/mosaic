"""Live norns screen contracts (README "Norns Menu Navigation").

The screen follows the grid, every Channel screen is reachable through Channel
tasks, E1 moves Masks <-> Trig params <-> Channel tasks, and the start-up
animation lays tiles, reveals the name and hands over to the first screen, or
is skipped by any input. Headers are checked with the live header oracle; the
splash is checked structurally (tile coverage), never by an image.
"""
import base64

TILE_CENTRES = [(column * 8 + 3, row * 8 + 3) for row in range(8) for column in range(16)]


def _lit_tiles(state):
    """Tiles whose centre and inner corners (+/-2 px) are all lit: a laid tile,
    never a letter stroke of the revealed name."""
    pixels = base64.b64decode(state["frame"]["pixels_base64"])
    points = ((0, 0), (-2, -2), (2, -2), (-2, 2), (2, 2))
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
    # From another Channel screen, a hold shows the remembered family, then returns.
    ui.channel_page("clock_mods", channel=3)
    with ui.hold_step(9):
        ui.expect_header("trig_locks", channel=3, held=(9,))
    ui.expect_header("clock_mods", channel=3)
    c.results.append(dict(kind="hold-returns-to-parent", screen="clock_mods", passed=True))


def live_ui_tasks(c):
    """README: E1 moves Masks, Trig params and Channel tasks; tasks open every Channel screen."""
    ui = c.ui
    ui.tap_control("channel_editor"); ui.expect_header("masks", channel=1)
    for delta, page in ((1, "trig_locks"), (1, "channel_tasks"), (1, "channel_tasks"),
                        (-1, "trig_locks"), (-1, "masks"), (-1, "masks")):
        c.enc(1, delta); ui.expect_header(page, channel=1)
        c.results.append(dict(kind="e1-family", delta=delta, page=page, passed=True))
    for page in ("memory", "clock_mods", "midi_config", "note_dashboard", "merge_shape", "harmony",
                 "masks", "trig_locks"):
        ui.channel_page(page)
        c.results.append(dict(kind="channel-task", page=page, passed=True))


def live_ui_splash(c):
    """README: tiles lay down, lift to leave the name, then the first screen; input skips it."""
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
                d.wait(lambda s: _lit_tiles(s) >= 96, timeout=3)
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

"""Memory truncation is per channel and survives save/reload (README Memory 698-707:
each channel editor has its own Memory page; K1+K3 jumps to the latest action and
erases all subsequent memory). Channel 1 records two note-mask actions and channel 2
one. K1+K3 on channel 1 forgets channel 1's history (0 of 0) and leaves channel 2's
(1 of 1), where E3 still undoes. After an idle autosave and a cold restart both
positions and channel 1's applied masks are restored (characterisation of persistence,
as M-MEMORY-006).
"""
from driver import Driver

BASELINE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def memory_truncate_isolation(c):
    ui = c.ui

    def counter(d_ui, channel, current, total):
        d_ui.expect_header("memory", channel=channel)
        d_ui.expect_memory_position(current, total, channel=channel)

    def record(d, d_ui, channel, step, note, velocity):
        d_ui.channel_page("masks", "memory", channel=channel, confirm=False)
        d_ui.expect_header("masks", channel=channel)
        d_ui.record_key(step, note, velocity, hold_seconds=.05)
        d.elapse(.1)
        d_ui.channel_page("memory", "masks", channel=channel, confirm=False)

    def shift(d, d_ui, n):
        with d_ui.hold_keys(1):
            d.elapse(.4)
            d_ui.press_key(n)
        d.elapse(.1)

    applied = [(1, [144, 72, 90]), (1, [144, 76, 80]), *[(1, [144, n, v]) for n, v in BASELINE[2:]]]
    c.configure()
    ui.channel_page("memory", "midi_config", confirm=False)
    record(c, ui, 1, 1, 72, 90); record(c, ui, 1, 2, 76, 80); counter(ui, 1, 2, 2)
    ui.select_channel(2); record(c, ui, 2, 1, 67, 70); counter(ui, 2, 1, 1)
    ui.select_channel_on_page(1, "memory"); counter(ui, 1, 2, 2)
    shift(c, ui, 3); counter(ui, 1, 0, 0)                               # K1+K3: channel 1 forgets its history
    ui.select_channel_on_page(2, "memory"); counter(ui, 2, 1, 1); ui.turn(3, -1); counter(ui, 2, 0, 1)   # channel 2 keeps and undoes
    ui.select_channel_on_page(1, "memory"); counter(ui, 1, 0, 0); c.playback(applied, cycles=2)
    marks = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob('autosave.*')}
    for _ in range(3): c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and (c.data_directory/n).stat().st_mtime_ns != marks.get(n)
                         for n in ('autosave.ptn', 'autosave.pset')))
    c.finish()
    out = c.out/'restarted'; out.mkdir()
    d = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        d_ui = d.ui
        d_ui.tap_control("channel_editor")
        # Preserve the physical cold-restart page route: exactly -5, then +2.
        d_ui.turn(1, -5); d_ui.turn(1, 2)
        counter(d_ui, 1, 0, 0); d.playback(applied, cycles=2)
        d_ui.select_channel_on_page(2, "memory"); counter(d_ui, 2, 0, 1)
    except Exception:
        try: d.finish()
        except Exception: pass
        raise
    d.finish()
    c.results.append(dict(kind='memory-truncate-isolation', passed=True))

"""Memory history after autosave and a cold restart.

Characterisation, not manual text: a saved project carries its memory history
(program.prepare_for_save serialises it), so after a restart the Memory page shows
the same position and E3 undoes and redoes the restored actions (README Memory,
698-707, describes E3 navigation within a session).
"""
from driver import Driver

BASELINE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def memory_persistence(c):
    ui = c.ui

    def counter(d, current, total):
        d.ui.expect_memory_position(current, total)

    def record(step, note, velocity):
        ui.channel_page("masks", "memory", confirm=False)
        ui.expect_header("masks", channel=1)
        ui.record_key(step, note, velocity, hold_seconds=.05)
        c.elapse(.1)
        ui.channel_page("memory", "masks", confirm=False)
        ui.expect_header("memory", channel=1)

    both = [(1, [144, 72, 90]), (1, [144, 76, 80]),
            *[(1, [144, n, v]) for n, v in BASELINE[2:]]]
    first = [(1, [144, 72, 90]), *[(1, [144, n, v]) for n, v in BASELINE[1:]]]
    ui.configure()
    ui.channel_page("memory", "midi_config", confirm=False)
    ui.expect_header("memory", channel=1)
    record(1, 72, 90); record(2, 76, 80); counter(c, 2, 2)
    marks = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob("autosave.*")}
    for _ in range(3): c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and
                         (c.data_directory/n).stat().st_mtime_ns != marks.get(n)
                         for n in ("autosave.ptn", "autosave.pset")))
    # Preserve the historical root-results quirk: root results are serialized
    # here before the nested restart exists; the summary stays on root below.
    c.finish()
    out = c.out / "restarted"; out.mkdir()
    d = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        d.ui.menu("channel_editor")
        d.ui.turn(1, -5)
        d.ui.turn(1, 2)
        d.ui.expect_header("memory", channel=1)
        counter(d, 2, 2); d.playback(both, cycles=2)
        d.ui.turn(3, -1); counter(d, 1, 2); d.playback(first, cycles=2)
        d.ui.turn(3, 1); counter(d, 2, 2); d.playback(both, cycles=2)
    except Exception:
        try: d.finish()
        except Exception: pass
        raise
    d.finish()
    # Do not append this to d: the root summary is intentionally post-finish.
    c.results.append(dict(kind="memory-persistence", restored_position=[2, 2], passed=True))

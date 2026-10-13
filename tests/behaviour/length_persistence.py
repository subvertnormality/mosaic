"""Fractional length masks after save and reload (README "Masks" and autosave, line 1054).

README 1054: when Mosaic starts again it loads the most recent autosave. A
channel length mask of 1/3 and a step-2 length mask of 5/6 must play and display
the same after an idle autosave and a cold restart. These two values are stored
as floats that the norns tab serialiser writes with 14 significant digits.
"""
PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]
LENGTHS = [1/3, 5/6, 1/3, 1/3]


def length_persistence(c):
    from cases import assert_durations
    from driver import Driver

    def check(d, stage):
        # The original E1 -4 enters the masks page; E2 clamps at Trig, then
        # advances to Len. Keep both explicit offsets in the semantic calls.
        d.ui.channel_page('masks', 'midi_config', channel=1, confirm=False)
        d.ui.select_field('length', offset=-5)
        d.ui.select_field('length', offset=3)
        d.ui.expect_field_value('length', '1/3')
        with d.ui.hold_step(2):
            d.elapse(.05)
            d.ui.expect_field_value('length', '5/6')
        d.elapse(.06)
        d.ui.expect_field_value('length', '1/3')
        notes = d.playback([(1, [144, n, v]) for n, v in PHRASE], cycles=2)
        assert_durations(d, notes, LENGTHS * 2)
        d.results.append(dict(kind='fractional-length-persistence', stage=stage, lengths=['1/3', '5/6', '1/3', '1/3'], passed=True))

    ui = c.ui
    ui.configure()
    ui.channel_page('masks', 'midi_config', channel=1, confirm=False)
    ui.select_field('length', offset=2)
    ui.expect_field_value('length', 'X')
    ui.set_value(6)
    ui.expect_field_value('length', '1/3')
    with ui.hold_step(2):
        c.elapse(.05)
        ui.expect_field_value('length', '1/3')
        ui.set_value(6)
        ui.expect_field_value('length', '5/6')
    ui.channel_page('midi_config', 'masks', channel=1, confirm=False)  # leave the masks page before checking
    check(c, 'edited')
    before = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob('autosave.*')}
    for _ in range(3):
        c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and (c.data_directory/n).stat().st_mtime_ns != before.get(n)
                         for n in ('autosave.ptn', 'autosave.pset')))
    c.finish()
    out = c.out/'restarted'; out.mkdir()
    restarted = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        restarted.ui.menu('channel_editor')
        check(restarted, 'restored')
    except Exception:
        try:
            restarted.finish()                                   # keep the restarted evidence
        except Exception:
            pass
        raise
    restarted.finish()
    c.results.append(dict(kind='fractional-length-persistence', stage='restored', passed=True))

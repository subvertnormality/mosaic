"""Fractional length masks after save and reload (README "Masks" and autosave, line 1054).

README 1054: when Mosaic starts again it loads the most recent autosave. A
channel length mask of 1/3 and a step-2 length mask of 5/6 must play and display
the same after an idle autosave and a cold restart. These two values are stored
as floats that the norns tab serialiser writes with 14 significant digits.
"""
PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]
LENGTHS = [1/3, 5/6, 1/3, 1/3]


def length_persistence(c):
    from cases import length_mask_display, assert_durations
    from driver import Driver

    def check(d, stage):
        d.enc(1, -4); d.enc(2, -5); d.enc(2, 3); length_mask_display(d, '1/3')   # E2 clamps at Trig; Len is the fourth
        d.action(type='grid', x=2, y=4, state=1)
        try: d.elapse(.05); length_mask_display(d, '5/6')
        finally: d.action(type='grid', x=2, y=4, state=0)
        d.elapse(.06); length_mask_display(d, '1/3')
        notes = d.playback([(1, [144, n, v]) for n, v in PHRASE], cycles=2)
        assert_durations(d, notes, LENGTHS * 2)
        d.results.append(dict(kind='fractional-length-persistence', stage=stage, lengths=['1/3', '5/6', '1/3', '1/3'], passed=True))

    c.configure(); c.enc(1, -4); c.enc(2, 2); length_mask_display(c, 'X')
    c.enc(3, 6); length_mask_display(c, '1/3')                    # channel length mask
    c.action(type='grid', x=2, y=4, state=1)
    try: c.elapse(.05); length_mask_display(c, '1/3'); c.enc(3, 6); length_mask_display(c, '5/6')
    finally: c.action(type='grid', x=2, y=4, state=0)
    c.enc(1, 4)                                                   # leave the masks page before checking
    check(c, 'edited')
    before = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob('autosave.*')}
    for _ in range(3): c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and (c.data_directory/n).stat().st_mtime_ns != before.get(n)
                         for n in ('autosave.ptn', 'autosave.pset')))
    c.finish()
    out = c.out/'restarted'; out.mkdir()
    d = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        d.tap(3, 8); check(d, 'restored')
    except Exception:
        try: d.finish()                                           # keep the restarted evidence
        except Exception: pass
        raise
    d.finish()
    c.results.append(dict(kind='fractional-length-persistence', stage='restored', passed=True))

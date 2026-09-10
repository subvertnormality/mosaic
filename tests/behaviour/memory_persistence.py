"""Memory history after autosave and a cold restart.

Characterisation, not manual text: a saved project carries its memory history
(program.prepare_for_save serialises it), so after a restart the Memory page shows
the same position and E3 undoes and redoes the restored actions (README Memory,
698-707, describes E3 navigation within a session).
"""
import base64
BASELINE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def memory_persistence(c):
    from frame_oracle import render
    from driver import Driver

    def counter(d, current, total):
        expected = render([(0, 23, 15, str(current)), (0, 49, 15, str(total))], font_size=10, antialias=1)
        indexes = [(y*128+x)*4+k for y in list(range(13, 26))+list(range(39, 52)) for x in range(16) for k in range(3)]
        d.wait(lambda s: all(base64.b64decode(s['frame']['pixels_base64'])[i] == expected[i] for i in indexes))
        d.results.append(dict(kind='memory-position', current=current, total=total, frame_matched=True))

    def record(step, note, velocity):
        c.enc(1, -2); c.screen_header('Ch. 1 Note Masks')
        c.action(type='grid', x=step, y=4, state=1)
        try: c.action(type='midi', port=1, bytes=[144, note, velocity]); c.elapse(.05); c.action(type='midi', port=1, bytes=[128, note, 0])
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.1); c.enc(1, 2); c.screen_header('Ch. 1 Memory')

    both = [(1, [144, 72, 90]), (1, [144, 76, 80]), *[(1, [144, n, v]) for n, v in BASELINE[2:]]]
    first = [(1, [144, 72, 90]), *[(1, [144, n, v]) for n, v in BASELINE[1:]]]
    c.configure(); c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    record(1, 72, 90); record(2, 76, 80); counter(c, 2, 2)
    marks = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob('autosave.*')}
    for _ in range(3): c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and (c.data_directory/n).stat().st_mtime_ns != marks.get(n)
                         for n in ('autosave.ptn', 'autosave.pset')))
    c.finish()
    out = c.out/'restarted'; out.mkdir()
    d = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        d.tap(3, 8); d.enc(1, -5); d.enc(1, 2); d.screen_header('Ch. 1 Memory')
        counter(d, 2, 2); d.playback(both, cycles=2)
        d.enc(3, -1); counter(d, 1, 2); d.playback(first, cycles=2)
        d.enc(3, 1); counter(d, 2, 2); d.playback(both, cycles=2)
    except Exception:
        try: d.finish()
        except Exception: pass
        raise
    d.finish()
    c.results.append(dict(kind='memory-persistence', restored_position=[2, 2], passed=True))

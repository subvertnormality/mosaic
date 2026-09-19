"""Memory truncation is per channel and survives save/reload (README Memory 698-707:
each channel editor has its own Memory page; K1+K3 jumps to the latest action and
erases all subsequent memory). Channel 1 records two note-mask actions and channel 2
one. K1+K3 on channel 1 forgets channel 1's history (0 of 0) and leaves channel 2's
(1 of 1), where E3 still undoes. After an idle autosave and a cold restart both
positions and channel 1's applied masks are restored (characterisation of persistence,
as M-MEMORY-006).
"""
import base64
BASELINE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def memory_truncate_isolation(c):
    from frame_oracle import render
    from driver import Driver

    def counter(d, channel, current, total):
        d.screen_header('Ch. %d Memory' % channel, selected=3)
        expected = render([(0, 23, 15, str(current)), (0, 49, 15, str(total))], font_size=10, antialias=1)
        indexes = [(y*128+x)*4+k for y in list(range(13, 26))+list(range(39, 52)) for x in range(16) for k in range(3)]
        d.wait(lambda s: all(base64.b64decode(s['frame']['pixels_base64'])[i] == expected[i] for i in indexes))
        d.results.append(dict(kind='memory-position', channel=channel, current=current, total=total, frame_matched=True))

    def record(channel, step, note, velocity):
        c.enc(1, -2); c.screen_header('Ch. %d Note Masks' % channel, selected=1)
        c.action(type='grid', x=step, y=4, state=1)
        try: c.action(type='midi', port=1, bytes=[144, note, velocity]); c.elapse(.05); c.action(type='midi', port=1, bytes=[128, note, 0])
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.1); c.enc(1, 2)

    def shift(d, n):
        d.action(type='key', n=1, state=1)
        try: d.elapse(.4); d.key(n)
        finally: d.action(type='key', n=1, state=0)
        d.elapse(.1)

    applied = [(1, [144, 72, 90]), (1, [144, 76, 80]), *[(1, [144, n, v]) for n, v in BASELINE[2:]]]
    c.configure(); c.enc(1, -2)
    record(1, 1, 72, 90); record(1, 2, 76, 80); counter(c, 1, 2, 2)
    c.tap(2, 1); record(2, 1, 67, 70); counter(c, 2, 1, 1)
    c.tap(1, 1); counter(c, 1, 2, 2)
    shift(c, 3); counter(c, 1, 0, 0)                               # K1+K3: channel 1 forgets its history
    c.tap(2, 1); counter(c, 2, 1, 1); c.enc(3, -1); counter(c, 2, 0, 1)   # channel 2 keeps and undoes
    c.tap(1, 1); counter(c, 1, 0, 0); c.playback(applied, cycles=2)
    marks = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob('autosave.*')}
    for _ in range(3): c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and (c.data_directory/n).stat().st_mtime_ns != marks.get(n)
                         for n in ('autosave.ptn', 'autosave.pset')))
    c.finish()
    out = c.out/'restarted'; out.mkdir()
    d = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        d.tap(3, 8); d.enc(1, -5); d.enc(1, 2)
        counter(d, 1, 0, 0); d.playback(applied, cycles=2)
        d.tap(2, 1); counter(d, 2, 0, 1)
    except Exception:
        try: d.finish()
        except Exception: pass
        raise
    d.finish()
    c.results.append(dict(kind='memory-truncate-isolation', passed=True))

"""MIDI transport at startup (arbitrated 2026-09-11, SEM-018 no-stop-without-project).

README is silent. A fresh start with no autosave sends no transport message; a start
that loads the autosave stops the transport first (load_project), which sends MIDI Stop
to every connected MIDI device. Both are pinned from the complete native export of each
session, before any user input.
"""
import json


def transport_before_input(out):
    events = [json.loads(line) for line in (out/'native/native-events.jsonl').read_text().splitlines()]
    # Input and MIDI events carry separate sequence counters; order them by host time.
    first_input = min((e['monotonic_ns'] for e in events if e.get('kind') == 'input'), default=None)
    return [(e['port'], e['bytes']) for e in events if e.get('kind') in (3, 11) and e['bytes'][0] >= 248
            and (first_input is None or e['monotonic_ns'] < first_input)]


def startup_transport(c):
    from driver import Driver
    c.configure()
    marks = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob('autosave.*')}
    for _ in range(3): c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and (c.data_directory/n).stat().st_mtime_ns != marks.get(n)
                         for n in ('autosave.ptn', 'autosave.pset')))
    ports = sorted({p['port'] for p in c.snapshot().get('midi_ports', []) if isinstance(p, dict) and 'port' in p}) or [1, 2, 3]
    c.finish()
    fresh = transport_before_input(c.out)
    assert fresh == [], ('Fresh start sent transport', fresh)
    out = c.out/'restarted'; out.mkdir()
    d = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        d.tap(3, 8); d.snapshot()                  # one observation, so repeats compare this segment
    finally: d.finish()
    loaded = transport_before_input(out)
    assert loaded and all(b == [252] for _, b in loaded) and len({p for p, _ in loaded}) == len(loaded), ('Autosave load transport', loaded)
    c.results.append(dict(kind='startup-transport', fresh=fresh, autosave_load=loaded, connected_ports=ports, passed=True))

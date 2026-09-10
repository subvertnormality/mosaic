"""Frozen saved projects must keep playing identically (README 1052-1054: saved and
autosaved projects load again).

`build_fixture_project` makes a project through native gestures: global length 4, a
CC lock and a CC slide, a note mask, a channel length mask of 1/2, an E major channel
scale lock, a second song slot with octave +1, and memory history. The builder run
(persisted_fixture_builder.py) autosaves it, records two song cycles of MIDI
output as golden.json and freezes the project data beside it. M-PERSIST-FIXTURE-CURRENT
cold-loads the fixture saved by the current version and must reproduce its golden
stream (characterisation: what that version played after reload). A legacy fixture is
compared with the current golden: the same gestures saved by release 1.2.12 must play
exactly as the current version's own save. The 1.2.12 golden.json is kept as
provenance only; it differs through defects fixed since (onset drift, slide timing).
"""
import json
from pathlib import Path

FIXTURES = Path(__file__).parent/'fixtures'/'persisted'


def build_fixture_project(c):
    from cases import assign_trig_parameter
    c.configure()
    c.tap(6, 8); c.tap(2, 7)
    for _ in range(3): c.tap(8, 7)                                # global length 4
    c.tap(3, 8); c.enc(1, -3)                                     # channel 1 Trig Locks
    def lock(step, value):
        c.action(type='grid', x=step, y=4, state=1)
        try: c.elapse(.05); c.action(type='enc', n=3, delta=-126); c.enc(3, value + 1)
        finally: c.action(type='grid', x=step, y=4, state=0)
    assign_trig_parameter(c, 'CC 1'); lock(2, 90)
    c.enc(2, 1); assign_trig_parameter(c, 'CC 2'); lock(1, 10); lock(3, 50); c.key(3)
    c.enc(1, -1)                                                  # Note Masks
    c.action(type='grid', x=4, y=4, state=1)
    try: c.action(type='midi', port=1, bytes=[144, 72, 90]); c.elapse(.05); c.action(type='midi', port=1, bytes=[128, 72, 0])
    finally: c.action(type='grid', x=4, y=4, state=0)
    c.enc(2, -5); c.enc(2, 3); c.enc(3, 8)                        # channel length mask 1/2
    c.tap(4, 8); c.tap(3, 3); c.enc(2, -1); c.enc(3, 4); c.key(3); c.tap(1, 3); c.tap(3, 8)  # slot 3 E major; slot 1 applied
    c.action(type='grid', x=3, y=4, state=1)
    try: c.tap(3, 3)                                              # channel scale lock step 3 -> slot 3
    finally: c.action(type='grid', x=3, y=4, state=0)
    c.tap(6, 8); c.hold_tap((1, 1), (2, 1)); c.tap(2, 1); c.tap(3, 8); c.tap(1, 1); c.tap(11, 8)  # slot 2 copy, octave +1
    c.tap(6, 8); c.tap(1, 1); c.tap(3, 8)


def capture_stream(c, onsets=17):
    """Play from slot 1 and return notes and CCs on port 1 relative to the first onset."""
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    before = c.snapshot()['midi_count']; c.tap(1, 8)
    def notes(s): return [m for m in s['midi'] if m['index'] > before and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    state = c.wait(lambda s: len(notes(s)) >= onsets, timeout=10)
    c.tap(1, 8); c.wait(lambda s: not s['midi_capture']['outstanding'])
    first = notes(state)[0]
    last = notes(state)[onsets - 1]
    return [dict(seconds=round((m[field] - first[field]) / 1e9, 6), bytes=m['bytes']) for m in state['midi']
            if first['index'] <= m['index'] <= last['index'] and m['port'] == 1 and m['bytes'][0] in (144, 128, 176)]


def compare(c, golden, actual):
    controlled = c.clock_mode == 'controlled-experimental'
    def notes(stream): return [e for e in stream if e['bytes'][0] == 144 and e['bytes'][2] > 0]
    assert [e['bytes'] for e in notes(actual)] == [e['bytes'] for e in notes(golden)], \
        dict(golden=[e['bytes'] for e in notes(golden)], actual=[e['bytes'] for e in notes(actual)])
    tolerance = 2e-6 if controlled else .01
    timing = [(g['bytes'], g['seconds'], a['seconds']) for a, g in zip(notes(actual), notes(golden)) if abs(a['seconds'] - g['seconds']) > tolerance]
    assert not timing, dict(onset_timing=timing[:6])
    if controlled:
        if [e['bytes'] for e in actual] != [e['bytes'] for e in golden]:
            import difflib
            diff = list(difflib.unified_diff([str(e) for e in golden], [str(e) for e in actual], 'golden', 'actual', n=1, lineterm=''))
            raise AssertionError(dict(stream_differs=diff[:60]))
    else:
        def locks(stream): return sorted({tuple(e['bytes']) for e in stream if e['bytes'][:2] == [176, 1]})
        assert locks(actual) == locks(golden), dict(golden=locks(golden), actual=locks(actual))


def persisted_fixture(c, label, expected=None):
    """Cold-load fixture LABEL and compare with the golden stream of EXPECTED (default LABEL)."""
    from driver import Driver
    fixture = FIXTURES/label
    golden = json.loads((FIXTURES/(expected or label)/'golden.json').read_text())
    assert golden['clock_mode'] == 'controlled-experimental'
    c.configure(); c.finish()                                     # the fixture replaces this empty session
    out = c.out/'fixture'; out.mkdir()
    d = Driver(out, project_seed=fixture/'data', **c.launch_options)
    try:
        d.tap(3, 8)
        actual = capture_stream(d)
        d.results.append(dict(kind='persisted-fixture-stream', label=label, stream=actual))
        compare(d, golden['stream'], actual)
    except Exception:
        try: d.finish()
        except Exception: pass
        raise
    d.results.append(dict(kind='persisted-fixture', label=label, events=len(actual), passed=True)); d.finish()
    c.results.append(dict(kind='persisted-fixture', label=label, saved_by=golden['saved_by'], events=len(actual), passed=True))

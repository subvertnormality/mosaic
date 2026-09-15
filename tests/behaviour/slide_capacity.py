"""Many replaced slides behind one long slide (README "Param Slides", line 964).

README: with slides enabled, locks smoothly transition between each other. Channel
2 (clock /8) slides CC 20 from step 1 to step 24 (about 31 s at 90 BPM). Channel 1
(clock x2, steps 1-2) slides CC 1..9 from 0 at step 1 to 127 at step 2 in every
cycle (1/6 s), each new slide replacing the previous one for that slot. For 25 s
every channel 1 slide must still pass through an intermediate value. Characterisation,
not manual text: slides are sampled every 1/36 s at 90 BPM (a 1/12 s ramp has two
or more samples) and capacity is a fixed ring of 1024 actions.
"""
import base64, json

SLOTS = 9; WINDOW_S = 25


def slide_capacity(c):
    from cases import assign_trig_parameter
    from frame_oracle import render, header, matches

    def clock_rate(detents, label):
        c.enc(1, 2); c.wait(lambda s: matches(s, header('Ch. %d Clocks' % channel, selected=4)))
        c.enc(3, detents); c.key(3)
        expected = render([(0, 26, 15, label)])
        pixels = [(y*128+x)*4+k for y in range(20, 30) for x in range(48) for k in range(3)]
        c.wait(lambda s: all(base64.b64decode(s['frame']['pixels_base64'])[i] == expected[i] for i in pixels))
        c.enc(1, -2)

    def lock(step, value):
        x, y = (step - 1) % 16 + 1, 4 + (step - 1) // 16
        c.action(type='grid', x=x, y=y, state=1)
        try: c.elapse(.05); c.action(type='enc', n=3, delta=-126); c.enc(3, value + 1)
        finally: c.action(type='grid', x=x, y=y, state=0)

    c.configure(); c.enc(1, -3)
    channel = 1
    c.hold_tap((1, 4), (2, 4))                                    # channel 1 steps 1-2
    for slot in range(1, SLOTS + 1):
        if slot > 1: c.enc(2, 1)
        assign_trig_parameter(c, 'CC %d' % slot)
        lock(1, 0); lock(2, 127); c.key(3)                        # global slide on for this slot
    clock_rate(3, 'x2')
    channel = 2
    c.tap(2, 1); c.enc(1, 3); c.screen_header('Ch. 2 Device Config', selected=5)
    c.enc(3, 1); c.key(3)                                         # the same device configure() gives channel 1
    c.enc(1, -3); c.screen_header('Ch. 2 Trig Locks', selected=2); c.enc(2, -20)
    assign_trig_parameter(c, 'CC 20')                             # same MIDI channel as channel 1: a distinct CC
    lock(1, 0); lock(24, 127); c.key(3)
    clock_rate(-10, '/8')
    before = c.snapshot()['midi_count']; c.tap(1, 8)
    remaining = WINDOW_S + .2
    while remaining > 0:
        chunk = min(5, remaining); c.elapse(chunk); remaining -= chunk; c.snapshot()
    after = c.snapshot()['midi_count']; c.tap(1, 8)
    c.wait(lambda s: not s['midi_capture']['outstanding']); c.finish()
    raw = [json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
    midi = [e for e in raw if e.get('kind') in (3, 11)][before:after]
    field = 'logical_ns' if c.clock_mode != 'real-time' else 'monotonic_ns'
    onsets = [e for e in midi if e['bytes'][0] == 144 and e['bytes'][2] > 0]
    first = onsets[0][field]
    starts = [e for e in onsets if e['bytes'][1] == 60 and (e[field] - first) / 1e9 < WINDOW_S - .2]
    assert len(starts) >= 140, len(starts)
    cycles = []
    for source in starts:
        destination = next(e for e in onsets if e['sequence'] > source['sequence'] and e['bytes'][1] == 62)
        for slot in range(1, SLOTS + 1):
            inner = [e['bytes'][2] for e in midi if e['bytes'][:2] == [176, slot] and
                     source['sequence'] < e['sequence'] < destination['sequence'] and 0 < e['bytes'][2] < 127]
            assert inner, dict(missing_slide_at_seconds=round((source[field] - first) / 1e9, 3), slot=slot)
        cycles.append(round((source[field] - first) / 1e9, 3))
    long = [e['bytes'][2] for e in midi if e['bytes'][:2] == [176, 20]]
    assert long == sorted(long) and long[0] == 0 and 60 < long[-1] < 127, ('Long slide still rising', long[:3], long[-3:])
    c.results.append(dict(kind='slide-capacity', slots=SLOTS, cycles=len(cycles), last_cycle_seconds=cycles[-1],
                          long_slide_last_value=long[-1], passed=True))
    (c.out/'results.json').write_text(json.dumps(c.results, indent=2) + '\n')

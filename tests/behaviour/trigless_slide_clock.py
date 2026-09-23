"""High-risk triple: trigless lock x global slide x external-clock tempo change
(BEHAVIOUR_PLAN "trigless + slide + external-clock change").

As M-PATCH-029: "Trigless locks" On, step 3's trig removed, CC 1 locks step 1 =
24 and silent step 3 = 96 with the global slide On, stored patch value 63. The
channel follows an external 24 PPQN MIDI clock (6 clocks per step, 24 per
four-step cycle) that steps from 100 to 150 BPM three clocks into the second
cycle's slide.
Manual (README 964, 759): with slides on, locks "smoothly transition between
each other", a slide reaches the destination lock, and an unlocked step
without an active slide sends the stored value.
Characterisation, not manual text (pinned for refactor safety, as M-PATCH-029):
the ramp is linear in received clock ordinals across the tempo change, and
Play sends the stored value before step 1's lock.
"""
import time

TICK_NS = 25_000_000; FAST_NS = 16_666_667
CHANGE = 27; TICKS = 72           # tempo steps after clock 27; clocks 0..72 after Start
PHRASE = {0: (60, 127), 1: (62, 117), 3: (65, 97)}
ONSET_TOLERANCE_NS = 3_000_002     # M-SYNC-018 abrupt tempo-step bound on native following


def trigless_slide_clock(c):
    from cases import menu_label, menu_value, assign_trig_parameter, set_mosaic_options
    from patch_params import open_patch_control, turn
    from external_clock_faults import _assert_notes, _actual_delivery, _schedule
    c.configure(); set_mosaic_options(c, [('Trigless locks', True)])
    c.tap(5, 8); c.tap(3, 4); c.tap(3, 8)                        # remove step 3's trig; keep its lock
    open_patch_control(c, setup=False); turn(c, 63); turn(c, 1); menu_value(c, '63'); c.key(1)
    c.enc(1, -3); assign_trig_parameter(c, 'CC 1')
    for step, value in [(1, 24), (3, 96)]:
        c.action(type='grid', x=step, y=4, state=1)
        try: c.elapse(.05); c.action(type='enc', n=3, delta=-126); c.enc(3, value + 1)
        finally: c.action(type='grid', x=step, y=4, state=0)
    c.key(3)                                                      # global slide On
    # norns reopens the menu inside the patch group; return to the parameter list top.
    c.key(1); c.key(2); c.enc(2, -60); menu_label(c, 'LEVELS >')
    position = next(i for i, v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name'] == 'CLOCK')
    c.enc(2, position); c.key(3); menu_label(c, 'source'); c.enc(3, 1); menu_value(c, 'midi')
    controlled = c.clock_mode == 'controlled-experimental'
    domain = 'logical' if controlled else 'monotonic'; key = 'at_' + domain + '_ns'; field = domain + '_ns'
    origin = (c.logical_ns if controlled else time.monotonic_ns()) + 1_750_000_000
    offsets = [0]
    for index in range(TICKS): offsets.append(offsets[-1] + (TICK_NS if index < CHANGE else FAST_NS))
    events = [dict(port=1, bytes=[248], **{key: origin - 1_250_000_000 + i * TICK_NS}) for i in range(1, 50)]
    events += [dict(port=1, bytes=[250], **{key: origin})]
    events += [dict(port=1, bytes=[248], **{key: origin + offset}) for offset in offsets]
    stop = origin + offsets[-1] + 8_000_000
    events += [dict(port=1, bytes=[252], **{key: stop})]
    events += [dict(port=1, bytes=[248], **{key: stop + i * FAST_NS}) for i in range(1, 13)]
    events.sort(key=lambda e: (e[key], 0 if e['bytes'] == [250] else 1))
    capture, state = _schedule(c, events, 404, 8)
    tick = [origin + offset for offset in offsets]
    jitter = 0 if controlled else 10_000_000
    steps = [s for s in range(TICKS // 6 + 1) if s % 4 in PHRASE]
    onsets = [(tick[6 * s], *PHRASE[s % 4]) for s in steps]
    releases = [tick[6 * s + 6] for s in steps[:-1]] + [stop]
    actual_stop = _actual_delivery(state['midi_input_schedule']['delivered'], [252], stop, domain)
    accounting = _assert_notes(capture.events, field, onsets, releases, ONSET_TOLERANCE_NS + jitter,
                               causal_releases={len(onsets) - 1: actual_stop},
                               transport_tolerance_ns=2 if controlled else 10_000_000)
    cc = [e for e in capture.events if e['port'] == 1 and e['bytes'][:2] == [176, 1]]
    tolerance = ONSET_TOLERANCE_NS + jitter

    def ordinal(t):
        """Received-clock position of a time, interpolated between intended clocks."""
        i = max(j for j in range(len(tick)) if tick[j] <= t) if t >= tick[0] else 0
        return i + (t - tick[i]) / ((tick[i + 1] if i + 1 < len(tick) else tick[i] + FAST_NS) - tick[i])

    cycles = []
    for cycle in range(TICKS // 24):
        source, destination, recall = tick[24 * cycle], tick[24 * cycle + 12], tick[24 * cycle + 18]
        ramp = [e for e in cc if source - tolerance <= e[field] <= destination + tolerance]
        # Play recalls the stored patch before the first step's lock (M-PATCH play recall).
        lead = [e['bytes'][2] for e in ramp[:1]] if cycle == 0 else []
        assert lead == ([63] if cycle == 0 else []), ('Start recall', lead)
        ramp = ramp[len(lead):]
        values = [e['bytes'][2] for e in ramp]
        assert len(ramp) >= 4 and values[0] == 24 and values[-1] == 96, ('Ramp endpoints', cycle, values)
        assert values == sorted(values), ('Ramp not monotonic', cycle, values)
        assert abs(ramp[0][field] - source) <= tolerance and abs(ramp[-1][field] - destination) <= tolerance, \
            ('Ramp does not span source to destination lock', cycle)
        samples = []
        for e in ramp:
            position = ordinal(e[field]) - 24 * cycle
            ideal = 24 + 72 * max(0, min(1, position / 12))
            interval = FAST_NS if 24 * cycle + position > CHANGE else TICK_NS
            allowance = 1 + 6 * tolerance / interval               # one CC unit + clock-following error
            samples.append(dict(ordinal=round(position, 4), value=e['bytes'][2], ideal=round(ideal, 3)))
            assert abs(e['bytes'][2] - ideal) <= allowance, ('Ramp not linear in clock ordinals', cycle, samples[-1], allowance)
        after = [(e['bytes'][2], round(ordinal(e[field]) - 24 * cycle, 3)) for e in cc
                 if destination + tolerance < e[field] < tick[24 * cycle + 24] - tolerance]
        assert [v for v, _ in after] == [63] and abs(after[0][1] - 18) <= 6 * tolerance / FAST_NS, \
            ('Unlocked step 4 recall only', cycle, after)
        cycles.append(dict(cycle=cycle, tempo_change_inside=24 * cycle < CHANGE < 24 * cycle + 12, samples=samples))
    assert any(c_['tempo_change_inside'] for c_ in cycles)
    c.results.append(dict(kind='trigless-slide-external-tempo-step', change_after_clock=CHANGE,
                          bpm=[100, 150], accounting=accounting, cycles=cycles, passed=True))

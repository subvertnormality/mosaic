"""A param slide on a fractional-rate channel restarted in the middle of a step by "Reset at
Pattern Repeat" (README 1078: with it on, every repeat "resets all channels ... back to
that channel's starting step at every start of the pattern") must play every repeat as
the first one from Play: the same step onsets and the same slide (README 964: with slides
on, "locks will smoothly transition between each other").

Channel 1 runs at /2.6 (2.6 x 24 = 62.4 pulses a step, 96 PPQN at 90 BPM) with CC 1
locks 0 on step 1 and 127 on step 2 and the global slide on. Global length 4 (96
pulses), song mode on with one slot, so every repeat is a reset; the channel's step 2
starts at 62 or 63 pulses (nearest-pulse steps) and each reset at 96 falls inside it.
The baseline left the restarted step 1 at the unrounded 62.4 pulses (suspected defect
S53, m_lattice.lua:704): it lasted 62 pulses instead of the 63 it lasts from Play, and
the slide over it was planned for 62.4 pulses, so its samples differed from the first
repeat's.
"""
PHRASE = [(60, 127), (62, 117)]
PULSE_RATE = 144
SLOT = 96                                   # global length 4 x 24 pulses
TICK = 8                                    # slide samples every 1/48 (8 pulses)


def slide_reset_mid_step(c):
    import json
    from cases import menu_value, assign_trig_parameter, set_mosaic_options
    from frame_oracle import header, matches
    from patch_params import open_patch_control, turn
    c.configure()
    c.tap(6, 8); c.tap(2, 7)
    for _ in range(3): c.tap(8, 7)                                # global length 4
    c.tap(3, 8)
    set_mosaic_options(c, [('Song mode', True), ('Reset on pattern repeat', True)])
    open_patch_control(c, setup=False); turn(c, 63); turn(c, 1); menu_value(c, '63'); c.key(1)
    c.enc(1, -3); assign_trig_parameter(c, 'CC 1')
    for step, value in [(1, 0), (2, 127)]:
        c.action(type='grid', x=step, y=4, state=1)
        try: c.elapse(.05); c.action(type='enc', n=3, delta=-126); c.enc(3, value + 1)
        finally: c.action(type='grid', x=step, y=4, state=0)
    c.key(3)                                                      # global slide on
    c.enc(1, 2); c.wait(lambda s: matches(s, header('Ch. 1 Clocks', selected=4)))
    c.enc(3, -3); c.key(3)                                        # /1 -> /2.6 (index 13 -> 16)
    before = c.snapshot()['midi_count']
    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    def onsets(s): return [e for e in s['midi'] if e['index'] > before and e['bytes'][0] == 144 and e['bytes'][2] > 0]
    c.wait(lambda s: len(onsets(s)) >= 9, timeout=6)
    after = c.snapshot()['midi_count']
    c.action(type='grid', x=1, y=8, state=1); c.action(type='grid', x=1, y=8, state=0)
    c.wait(lambda s: not s['midi_capture']['outstanding']); c.finish()
    checks = []
    try:
        raw = [json.loads(line) for line in (c.out / 'native/native-events.jsonl').read_text().splitlines()]
        events = [e for e in raw if e.get('kind') in (3, 11)][before:after]
        notes = [e for e in events if e['bytes'][0] == 144 and e['bytes'][2] > 0]
        assert len(notes) >= 9, [e['bytes'] for e in notes]
        controlled = c.clock_mode != 'real-time'
        field = 'logical_ns' if controlled else 'monotonic_ns'
        tolerance = 2e-9 if controlled else .01
        origin = notes[0][field]
        def pulse(event): return (event[field] - origin) * PULSE_RATE / 1e9
        # Every repeat restarts channel 1 at step 1 (README 1078): each slot's two onsets
        # sit where the first slot's do, one slot (96 pulses) later.
        first_step = round(pulse(notes[1]))                      # step 2's onset, whole pulses
        for index, note in enumerate(notes):
            slot, position = divmod(index, 2)
            pitch, velocity = PHRASE[position]
            assert (note['port'], note['bytes']) == (1, [144, pitch, velocity]), (index, note['bytes'])
            expected = slot * SLOT + (first_step if position else 0)
            assert abs(pulse(note) - expected) / PULSE_RATE <= tolerance, \
                dict(onset=index, expected_pulse=expected, actual_pulse=pulse(note))
        # CC 1 per slot: step 1's lock 0, the slide samples, step 2's lock 127.
        cc = [e for e in events if e['port'] == 1 and e['bytes'][:2] == [176, 1]]
        groups = []
        for event in cc:
            if event['bytes'][2] == 0: groups.append([])
            if groups: groups[-1].append(event)
        complete = [g for g in groups if g[-1]['bytes'][2] == 127]
        assert len(complete) >= 4, [[e['bytes'][2] for e in g] for g in groups]
        reference = [e['bytes'][2] for e in complete[0]]
        # README 964: a smooth rise from the step 1 lock to the step 2 lock.
        assert reference[0] == 0 and reference[-1] == 127 and len(reference) > 3 and \
            all(a < b for a, b in zip(reference, reference[1:])), reference
        for slot, group in enumerate(complete):
            values = [e['bytes'][2] for e in group]
            checks.append(dict(slot=slot, values=values))
            # README 1078: each repeat's slide is the first repeat's slide.
            assert values == reference, dict(slot=slot, values=values, first_repeat=reference)
            start = slot * SLOT
            for j, event in enumerate(group[:-1]):
                assert abs(pulse(event) - (start + TICK * j)) / PULSE_RATE <= tolerance, \
                    dict(slot=slot, sample=j, expected_pulse=start + TICK * j, actual_pulse=pulse(event))
            assert abs(pulse(group[-1]) - (start + first_step)) / PULSE_RATE <= tolerance, \
                dict(slot=slot, destination_pulse=pulse(group[-1]), step_2_pulse=start + first_step)
        c.results.append(dict(kind='slide-reset-mid-step', first_repeat=reference, step_2_pulse=first_step,
                              slots=len(complete), passed=True))
    finally:
        c.results.append(dict(kind='slide-reset-mid-step-samples', checks=checks))
        (c.out / 'results.json').write_text(json.dumps(c.results, indent=2) + '\n')

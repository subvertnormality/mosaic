"""Stepping memory back over a step-slid trig lock takes that lock's step slide with it, also
while another parameter's lock stays on the step (README Param Slides 964-969: holding a step
and pressing K3 on a trig parameter locks a slide to that step, toward the next lock; README
Memory 698-703: memory retains trig lock actions and E3 left explores the past action).
Human decision 2026-09-11 on S34: undoing a lock clears that lock's slide.

The Emulator test device plays 60/62/64/65 on steps 1-4 at 1/6 s. Slot 1 is Control 1 (CC1),
slot 2 SparseLow (CC2). Control 1 locks step 3 = 90; SparseLow locks step 1 = 110; Control 1
locks step 1 = 10 and step 1 + K3 slides it toward step 3. E3 back one on the Memory page
removes only the step-1 Control 1 lock, so the SparseLow lock keeps the step's lock table
non-empty. A fresh Control 1 lock on step 1 = 40 (no K3) must then jump, not slide.

Control, not memory: hold + K3 on step 2 with no Control 1 lock there still arms a step
slide, and a lock set there afterwards slides toward step 3.

Input sequence from the 2026-09-11 probe (probe_locks.py s34, the 'other-history' order).
Every check runs before the case fails, so a baseline run reports each one.
"""
import base64


def memory_lock_slide_undo(c):
    from cases import assign_trig_parameter
    c.configure(); c.enc(3, 1); c.key(3)
    c.enc(1, -3); c.screen_header('Ch. 1 Trig Locks', selected=2)
    assign_trig_parameter(c, 'Control 1')
    c.enc(2, 1); assign_trig_parameter(c, 'SparseLow'); c.enc(2, -1)
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    tol = 0 if c.clock_mode == 'controlled-experimental' else 5e6
    failures = []

    def check(name, ok, detail):
        c.results.append(dict(kind='memory-lock-slide-check', check=name, passed=ok, detail=detail))
        if not ok: failures.append((name, detail))

    def lock(step, value):
        # Hold a step and lock the selected slot to an absolute value (README 937-940).
        c.action(type='grid', x=step, y=4, state=1)
        try:
            c.elapse(.05); c.action(type='enc', n=3, delta=-126); c.elapse(.15)
            c.enc(3, value + 1)
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.3)

    def step_k3(step):
        # README 966-967: hold the step, press K3 on the chosen trig parameter.
        c.action(type='grid', x=step, y=4, state=1)
        try: c.elapse(.1); c.key(3); c.elapse(.3)
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.3)

    def outline(state):
        # Slot 1 dial's step-slide outline: its top edge (row 11) and right edge (column 22).
        p = base64.b64decode(state['frame']['pixels_base64'])
        lit = lambda x, y: p[(y * 128 + x) * 4 + 2] > 0
        return all(lit(x, 11) for x in range(2, 21)) and all(lit(22, y) for y in range(13, 30))

    def held_outline(step, label):
        c.action(type='grid', x=step, y=4, state=1)
        try: c.elapse(.4); shown = outline(c.snapshot())
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.2)
        c.results.append(dict(kind='memory-lock-slide-outline', stage=label, step=step, outline=shown))
        return shown

    def heard(stage):
        # About three pattern cycles; per step interval, the CC values sent between onsets.
        marker = c.snapshot()['midi_count']; c.tap(1, 8); c.elapse(2.1); c.tap(1, 8); c.elapse(.4)
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        events = [m for m in state['midi'] if m['index'] > marker]
        ons = [m for m in events if (m['bytes'][0] & 0xF0) == 0x90 and m['bytes'][2] > 0]
        assert len(ons) >= 9, ('Pattern not heard', stage, len(ons))
        cycles = []
        for start in range(0, len(ons) - 4, 4):
            steps = []
            for k in range(4):
                a, b = ons[start + k], ons[start + k + 1]
                # CC sent with the onset (a lock goes just before its note) up to the next onset.
                steps.append({cc: [m['bytes'][2] for m in events if m['bytes'][:2] == [176, cc]
                                   and a[field] - tol <= m[field] < b[field] - tol]
                              for cc in (1, 2)})
            cycles.append(steps)
        c.results.append(dict(kind='memory-lock-slide-heard', stage=stage, cycles=cycles))
        return cycles

    def slid(values, low, high):
        return [v for v in values if low < v < high]

    lock(3, 90)
    c.enc(2, 1); lock(1, 110); c.enc(2, -1)
    lock(1, 10)
    step_k3(1)
    armed = held_outline(1, 'after-k3')
    # characterisation, not manual text: precondition, the held step shows the slot's slide outline.
    assert armed, 'Step slide outline not shown after hold + K3'
    with_slide = heard('with-step1-slide')
    for steps in with_slide:
        # README 964-969: the step-1 lock moves smoothly toward the next lock (step 3 = 90).
        assert steps[0][1][:1] == [10] and slid(steps[0][1] + steps[1][1], 10, 90), ('Step slide not heard', steps)
        # README 937-940: the SparseLow step-1 lock is sent with step 1.
        assert steps[0][2], ('SparseLow step-1 lock not heard', steps)
    sparse_value = with_slide[0][0][2]

    c.enc(1, 1); c.screen_header('Ch. 1 Memory')
    c.enc(3, -1)
    c.enc(1, -1); c.screen_header('Ch. 1 Trig Locks', selected=2)
    undone = heard('after-undo')
    for steps in undone:
        # README 698-703: E3 back one explores the state before the step-1 Control 1 lock ...
        assert not steps[0][1] and not steps[1][1], ('Step-1 Control 1 lock survived its undo', steps)
        # ... and leaves the earlier SparseLow lock and the step-3 lock in place.
        assert steps[0][2] == sparse_value and steps[2][1][-1:] == [90], ('Earlier locks changed by the undo', steps)
    after_undo_outline = held_outline(1, 'after-undo')
    # characterisation, not manual text (the outline marks a step slide on the held step); human
    # decision S34: undoing a lock clears that lock's slide.
    check('S34-undo-clears-held-step-slide-outline', not after_undo_outline, dict(outline=after_undo_outline))

    lock(1, 40)
    relocked = heard('after-new-lock40-no-k3')
    inner = [slid(steps[0][1] + steps[1][1], 40, 90) for steps in relocked]
    starts = [steps[0][1][:1] for steps in relocked]
    arrivals = [steps[2][1][-1:] for steps in relocked]
    # README 964-969 (a step slides only after hold + K3 on it) and human decision S34: the new
    # step-1 lock jumps: 40 with step 1, nothing between 40 and 90, 90 with step 3.
    check('S34-new-lock-after-undo-does-not-slide',
          all(s == [40] for s in starts) and not any(inner) and all(a == [90] for a in arrivals),
          dict(starts=starts, inner=inner, arrivals=arrivals))

    # Control: hold + K3 on a step without a Control 1 lock still arms its slide (README 964-969).
    step_k3(2)
    lockless = held_outline(2, 'lockless-k3')
    # characterisation, not manual text: the held lock-less step shows the slide outline.
    check('control-lockless-k3-shows-outline', lockless, dict(outline=lockless))
    lock(2, 50)
    control = heard('lockless-k3-then-lock50')
    ramps = [steps[1][1] for steps in control]
    # README 964-969: the step-2 lock slides smoothly toward the next lock (step 3 = 90).
    check('control-lockless-k3-then-lock-slides',
          all(r[:1] == [50] and slid(r, 50, 90) for r in ramps), dict(step2=ramps))

    c.results.append(dict(kind='memory-lock-slide-summary', passed=not failures, failures=failures))
    # README 964-969, 698-703 and the human decision (S34): every check above.
    assert not failures, failures

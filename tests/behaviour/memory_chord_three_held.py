"""A held-step chord 3 edit that turns E3 up and then back down is one remembered action and
sounds the chord note finally selected (README 601: hold the step and select each chord note;
README 698-700: memory retains mask actions, each shown as one icon). Human decision
2026-09-11 on S25: the chord 3 held-step decrement must match the other mask handlers.

Channel 1 plays 60/62/64/65 at velocities 127/117/107/97. On the Note Masks page, holding
step 2 and turning E3 up two detents on Chd3 is the reference: one action, and a chord voice
on step 2. After K1+K2 forgets it, the same hold turns Chd3 up three and back one, so the
screen again selects the reference value; the step must sound the reference chord, as one
action. The same up-three-down-one gesture on Chd4 (step 3) comes first, as the control for
"one action". The action count is characterisation of the other handlers, per the decision.
"""


def memory_chord_three_held(c):
    from frame_oracle import render
    import base64
    c.configure()
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'

    def heard(stage):
        # One pattern cycle (4 steps at 1/6 s): every voice sounding from the first onset.
        marker = c.snapshot()['midi_count']; c.tap(1, 8); c.elapse(1.4); c.tap(1, 8)
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        ons = [m for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0]
        assert ons, ('Nothing heard', stage)
        cycle = [[m['bytes'][1], m['bytes'][2]] for m in ons if (m[field] - ons[0][field]) / 1e9 < .6]
        c.results.append(dict(kind='chord-three-held-heard', stage=stage, cycle=cycle))
        return cycle

    def counter(stage, current, total):
        expected = render([(0, 23, 15, str(current)), (0, 49, 15, str(total))], font_size=10, antialias=1)
        indexes = [(y * 128 + x) * 4 + k for y in list(range(13, 26)) + list(range(39, 52)) for x in range(16) for k in range(3)]
        def match(state):
            actual = base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[i] == expected[i] for i in indexes)
        try: c.wait(match)
        except AssertionError: raise AssertionError(('Memory counter', stage, dict(current=current, total=total)))
        c.results.append(dict(kind='chord-three-held-counter', stage=stage, current=current, total=total, frame_matched=True))

    def held_chord(step, field_offset, turns):
        # From the Memory page: hold a step on Note Masks and turn E3 on one chord field.
        c.enc(1, -2); c.screen_header('Ch. 1 Note Masks', selected=1)
        c.enc(2, -9); c.enc(2, field_offset)
        c.action(type='grid', x=step, y=4, state=1); c.elapse(.05)
        try:
            for t in turns: c.enc(3, t)
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.1); c.enc(1, 2); c.screen_header('Ch. 1 Memory')

    def shift(n):
        # norns passes K1 to the script only after its 0.25 s menu threshold.
        c.action(type='key', n=1, state=1)
        try: c.elapse(.4); c.key(n)
        finally: c.action(type='key', n=1, state=0)
        c.elapse(.1)

    c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    original = heard('original')
    # characterisation, not manual text: the configured phrase the case starts from.
    assert original == [[60, 127], [62, 117], [64, 107], [65, 97]], original

    # Control: the same up-three-down-one gesture on Chd4 (step 3) is one action.
    held_chord(3, 7, [3, -1]); control = heard('chd4-up-three-down-one')
    # README 601: holding a step and selecting a chord mask adds a voice to the root.
    assert len(control) == len(original) + 1, ('Chord 4 voice not heard', control)
    # characterisation, not manual text: the other handlers remember one hold as one action.
    counter('chd4-up-three-down-one', 1, 1)
    # README 707: K1+K2 jumps to the first action (before the edit) and erases the memory.
    shift(2); counter('chd4-forgotten', 0, 0)
    # README 707: the first action is the phrase before any edit.
    assert heard('chd4-forgotten') == original

    # Reference: Chd3 up two detents on step 2.
    held_chord(2, 6, [2]); reference = heard('chd3-up-two')
    # README 601: the chord 3 voice is added to the root.
    assert len(reference) == len(original) + 1, ('Chord 3 voice not heard', reference)
    counter('chd3-up-two', 1, 1)   # characterisation, not manual text (as the control)
    shift(2); counter('chd3-forgotten', 0, 0)   # README 707
    # README 707: the first action is the phrase before any edit.
    assert heard('chd3-forgotten') == original

    # Chd3 up three and back one in the same hold selects the reference value again.
    held_chord(2, 6, [3, -1]); up_down = heard('chd3-up-three-down-one')
    failures = []
    # README 601: the chord note sounding is the one finally selected, as for the reference.
    if up_down != reference: failures.append(('chord', dict(expected=reference, actual=up_down)))
    # characterisation, not manual text: one action, as the Chd4 control (S25 decision: match the other handlers).
    try: counter('chd3-up-three-down-one', 1, 1)
    except AssertionError as error: failures.append(('memory', str(error)))

    c.results.append(dict(kind='chord-three-held-summary', passed=not failures, failures=failures))
    assert not failures, failures

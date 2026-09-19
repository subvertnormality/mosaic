"""Stepping memory back one action restores the whole step as it was before that action
(README Memory 698-707: memory "retains all masks and trig lock actions"; E3 scrolls left to
explore past actions and right towards more recent ones; K3 jumps to the latest action).
Human decision 2026-09-11 on S42-S44: undo restores the full prior step state.

Channel 1 plays 60/62/64/65 at velocities 127/117/107/97. Every edit is a real held-step
gesture on the Note Masks or Trig Locks page; every check is one heard pattern cycle,
chord voices included. Each scenario compares the cycle heard after stepping back with the
cycle heard before the undone action, so no pitch table is assumed.

- S42 (step 2): note lock, velocity lock 30, second note lock; E3 back one must give the
  first note lock at velocity 30, not keep the second note.
- S43 (step 3): chord 1 lock, note lock, second note lock; E3 back one must keep the chord,
  and K3 (latest) must give the second note with the chord.
- S44a (step 4): note lock, then a Fixed Note trig lock; E3 back one must drop the trig lock.
- S44b (step 1): Quantised Fixed Note lock in slot 2, then a Fixed Note lock in slot 1;
  E3 back one must drop the slot-1 lock and leave the slot-2 lock sounding.

Every scenario runs before the case fails, so a baseline run reports each one.
"""


def memory_step_undo(c):
    from cases import assign_trig_parameter
    c.configure()
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    failures = []

    def heard(stage):
        # One pattern cycle (4 steps at 1/6 s): every voice sounding from the first onset.
        marker = c.snapshot()['midi_count']; c.tap(1, 8); c.elapse(1.4); c.tap(1, 8)
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        ons = [m for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0]
        assert ons, ('Nothing heard', stage)
        cycle = [[m['bytes'][1], m['bytes'][2]] for m in ons if (m[field] - ons[0][field]) / 1e9 < .6]
        c.results.append(dict(kind='memory-step-undo-heard', stage=stage, cycle=cycle))
        return cycle

    def check(scenario, ok, detail):
        c.results.append(dict(kind='memory-step-undo-check', scenario=scenario, passed=ok, detail=detail))
        if not ok: failures.append((scenario, detail))

    def to_memory(back):
        c.enc(1, back); c.screen_header('Ch. 1 Memory')

    def held_mask(step, field_offset, turns):
        # From the Memory page: hold a step on Note Masks and turn E3 on one field.
        c.enc(1, -2); c.screen_header('Ch. 1 Note Masks', selected=1)
        c.enc(2, -9); c.enc(2, field_offset)
        c.action(type='grid', x=step, y=4, state=1); c.elapse(.05)
        try: c.enc(3, turns)
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.1); to_memory(2)

    def held_lock(step, value):
        # On Trig Locks: hold a step and lock the selected slot to an absolute value.
        c.action(type='grid', x=step, y=4, state=1)
        try:
            c.elapse(.05); c.action(type='enc', n=3, delta=-126); c.elapse(.15)
            c.enc(3, value + 1)
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.15)

    to_memory(-2)
    original = heard('original')
    # characterisation, not manual text: the configured phrase every scenario starts from.
    assert original == [[60, 127], [62, 117], [64, 107], [65, 97]], original

    # S42: note, velocity 30, note on step 2.
    held_mask(2, 1, 5); first_note = heard('s42-first-note')
    held_mask(2, 2, 31); with_velocity = heard('s42-velocity-30')
    # README 572: a velocity mask changes the velocity without changing other settings.
    assert with_velocity[1][1] == 30 and with_velocity[1][0] == first_note[1][0], with_velocity
    held_mask(2, 1, 2); second_note = heard('s42-second-note')
    # characterisation, not manual text: precondition, the second note lock is audible.
    assert second_note[1][0] != first_note[1][0], ('Second note lock not heard', second_note)
    c.enc(3, -1); undone = heard('s42-undone')
    # README 703: E3 left explores the past action, the step as it was before the note edit.
    check('S42-undo-restores-note-and-keeps-velocity', undone == with_velocity,
          dict(expected=with_velocity, actual=undone))
    # README 703: E3 right moves towards the more recent action.
    c.enc(3, 1); redone = heard('s42-redone')
    check('S42-redo-returns-to-latest', redone == second_note, dict(expected=second_note, actual=redone))

    # S43: chord 1, note, note on step 3.
    held_mask(3, 4, 2); chord = heard('s43-chord')
    # README 601: holding a step and selecting a chord mask adds a voice to the root.
    assert len(chord) == len(original) + 1, ('Chord voice not heard', chord)
    held_mask(3, 1, 5); chord_first_note = heard('s43-first-note')
    held_mask(3, 1, 2); chord_second_note = heard('s43-second-note')
    # characterisation, not manual text: precondition, the second note lock is audible.
    assert chord_second_note != chord_first_note, ('Second note lock not heard', chord_second_note)
    c.enc(3, -1); chord_undone = heard('s43-undone')
    # README 703: stepping back one action keeps the chord made two actions earlier.
    check('S43-undo-keeps-earlier-chord', chord_undone == chord_first_note,
          dict(expected=chord_first_note, actual=chord_undone))
    c.key(3); chord_latest = heard('s43-latest')
    # README 704: K3 jumps to the latest action, which includes the chord.
    check('S43-latest-keeps-chord', chord_latest == chord_second_note,
          dict(expected=chord_second_note, actual=chord_latest))

    # S44a: a note lock, then a Fixed Note trig lock, on step 4.
    held_mask(4, 1, 5); note_locked = heard('s44a-note-lock')
    c.enc(1, -1); c.screen_header('Ch. 1 Trig Locks', selected=2)
    assign_trig_parameter(c, 'Fixed Note')
    held_lock(4, 72); to_memory(1)
    trig_locked = heard('s44a-trig-lock')
    # README 781 and 785: a Fixed Note lock sets the step's MIDI note and takes precedence.
    assert trig_locked[-1][0] == 72, ('Fixed Note lock not heard', trig_locked)
    c.enc(3, -1); trig_undone = heard('s44a-undone')
    # README 703: stepping back over the trig lock returns to the note-locked step.
    check('S44a-undo-drops-trig-lock-after-note-lock', trig_undone == note_locked,
          dict(expected=note_locked, actual=trig_undone))
    # README 703: E3 right moves towards the more recent action.
    c.enc(3, 1); trig_redone = heard('s44a-redone')
    check('S44a-redo-returns-to-latest', trig_redone == trig_locked, dict(expected=trig_locked, actual=trig_redone))

    # S44b: slot 2 Quantised Fixed Note lock, then slot 1 Fixed Note lock, on step 1.
    c.enc(1, -1); c.screen_header('Ch. 1 Trig Locks', selected=2)
    c.enc(2, 1); assign_trig_parameter(c, 'Quantised Fixed Note')
    held_lock(1, 67); to_memory(1)
    quantised = heard('s44b-slot2-lock')
    # README 785: a Quantised Fixed Note lock replaces the step's pattern pitch.
    assert quantised[0][0] != 60, ('Quantised Fixed Note lock not heard', quantised)
    c.enc(1, -1); c.screen_header('Ch. 1 Trig Locks', selected=2)
    c.enc(2, -1); held_lock(1, 74); to_memory(1)
    fixed = heard('s44b-slot1-lock')
    # README 781 and 785: Fixed Note takes precedence over the Quantised Fixed Note lock.
    assert fixed[0][0] == 74, ('Fixed Note lock not heard', fixed)
    c.enc(3, -1); fixed_undone = heard('s44b-undone')
    # README 703, 781 and 785 (Fixed Note takes precedence): after stepping back, only the slot-2 lock remains.
    check('S44b-undo-drops-other-slot-lock', fixed_undone == quantised,
          dict(expected=quantised, actual=fixed_undone))

    c.results.append(dict(kind='memory-step-undo-summary', passed=not failures, failures=failures))
    # README 698-707 and the human decision (S42-S44): every scenario above.
    assert not failures, failures

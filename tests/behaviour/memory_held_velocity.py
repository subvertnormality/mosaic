"""Undoing a held-step velocity lock (README Memory 697-702: memory "retains all masks
and trig lock actions"; E3 scrolls left to past actions). Gap-scan item 16: the
held-step velocity increment writes the step's velocity mask while the step is still
held, before the release commits the action to memory, whereas note and decrement
edits wait for the release.

Channel 1 plays velocities 127/117/107/97. Holding step 2 on the Note Masks page and
turning E3 locks velocity 50 on step 2; stepping memory back must restore 117, also
after a later working-pattern rebuild (a tap on step 4). A note lock on step 2 made first
(undone, then rebuilt) is the control. Redo is checked separately (M-MEMORY-009).
"""
PATTERN = [127, 117, 107, 97]


def memory_held_velocity(c):
    c.configure()

    def heard(stage, expected_velocities=None, expected_notes=None):
        marker = c.snapshot()['midi_count']; c.tap(1, 8); c.elapse(1.4); c.tap(1, 8)
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        ons = [m['bytes'] for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0][:4]
        actual = dict(notes=[b[1] for b in ons], velocities=[b[2] for b in ons])
        c.results.append(dict(kind='memory-held-velocity', stage=stage, **actual))
        if expected_velocities is not None: assert actual['velocities'] == expected_velocities, (stage, actual)
        if expected_notes is not None: assert actual['notes'] == expected_notes, (stage, actual)
        return actual

    def held_edit(field_offset, turns):
        c.enc(1, -2); c.screen_header('Ch. 1 Note Masks', selected=1)
        c.enc(2, -5); c.enc(2, field_offset)
        c.action(type='grid', x=2, y=4, state=1); c.elapse(.05)
        try: c.enc(3, turns)
        finally: c.action(type='grid', x=2, y=4, state=0)
        c.elapse(.1); c.enc(1, 2); c.screen_header('Ch. 1 Memory')

    def rebuild():
        c.enc(1, -2); c.screen_header('Ch. 1 Note Masks', selected=1)
        c.tap(4, 4); c.elapse(.2); c.enc(1, 2); c.screen_header('Ch. 1 Memory')

    c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    original = heard('original', PATTERN)

    held_edit(1, 5)                                            # control: note lock on step 2
    locked = heard('note-locked', PATTERN)
    assert locked['notes'] != original['notes'], ('Note lock not heard', locked)
    c.enc(3, -1); heard('note-undone', PATTERN, original['notes'])
    rebuild(); heard('note-undone-after-rebuild', PATTERN, original['notes'])

    held_edit(2, 51)                                           # velocity lock 50 on step 2 (new action)
    heard('velocity-locked', [127, 50, 107, 97], original['notes'])
    c.enc(3, -1); heard('velocity-undone', PATTERN, original['notes'])
    rebuild(); heard('velocity-undone-after-rebuild', PATTERN, original['notes'])
    c.results.append(dict(kind='memory-held-velocity-summary', passed=True))

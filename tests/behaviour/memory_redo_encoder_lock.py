"""Redo of a held-step mask lock made with the encoder (README Memory 697-702: memory
"retains all masks and trig lock actions"; E3 scrolls left to past actions and right
towards more recent ones).

Channel 1 plays 60/62/64/65 at velocities 127/117/107/97. Holding step 2 on the Note Masks
page and turning E3 on the Note field locks a note on step 2 (heard as a different pitch at
velocity 117). Stepping memory back and then forward again must return to the locked
state: step 2 sounds with the locked note, immediately and after a working-pattern rebuild
(a tap on step 4). The same is checked for a velocity lock of 50 on step 3.
"""
PATTERN = [127, 117, 107, 97]


def memory_redo_encoder_lock(c):
    c.configure()

    def heard(stage):
        marker = c.snapshot()['midi_count']; c.tap(1, 8); c.elapse(1.4); c.tap(1, 8)
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        ons = [m['bytes'] for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0][:4]
        actual = dict(notes=[b[1] for b in ons], velocities=[b[2] for b in ons])
        c.results.append(dict(kind='memory-redo-encoder-lock', stage=stage, **actual))
        return actual

    def held_edit(field_offset, step, turns):
        c.enc(1, -2); c.screen_header('Ch. 1 Note Masks', selected=1)
        c.enc(2, -5); c.enc(2, field_offset)
        c.action(type='grid', x=step, y=4, state=1); c.elapse(.05)
        try: c.enc(3, turns)
        finally: c.action(type='grid', x=step, y=4, state=0)
        c.elapse(.1); c.enc(1, 2); c.screen_header('Ch. 1 Memory')

    def rebuild():
        c.enc(1, -2); c.screen_header('Ch. 1 Note Masks', selected=1)
        c.tap(4, 4); c.elapse(.2); c.enc(1, 2); c.screen_header('Ch. 1 Memory')

    c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    original = heard('original')
    assert original == dict(notes=[60, 62, 64, 65], velocities=PATTERN), original

    held_edit(1, 2, 5)                                          # note lock on step 2
    locked = heard('note-locked')
    assert locked['notes'][0] == 60 and locked['notes'][2:] == [64, 65] and locked['notes'][1] != 62, locked
    assert locked['velocities'] == PATTERN, locked
    c.enc(3, -1); undone = heard('note-undone'); assert undone == original, undone
    c.enc(3, 1); redone = heard('note-redone'); assert redone == locked, ('Redo differs from the locked state', redone, locked)
    rebuild(); again = heard('note-redone-after-rebuild'); assert again == locked, ('Redo differs after a rebuild', again, locked)

    held_edit(2, 3, 51)                                         # velocity lock 50 on step 3
    vlocked = heard('velocity-locked'); assert vlocked['velocities'] == [127, 117, 50, 97], vlocked
    c.enc(3, -1); heard('velocity-undone')
    c.enc(3, 1); vredone = heard('velocity-redone'); assert vredone == vlocked, ('Velocity redo differs', vredone, vlocked)
    rebuild(); vagain = heard('velocity-redone-after-rebuild'); assert vagain == vlocked, ('Velocity redo differs after a rebuild', vagain, vlocked)
    c.results.append(dict(kind='memory-redo-encoder-lock-summary', passed=True))

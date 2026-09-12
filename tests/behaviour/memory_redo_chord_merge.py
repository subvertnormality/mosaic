"""K3 after undoing two chord edits on one step restores both chord voices (suspected
defect S57; human decision 2026-09-12: fix).

README Memory 698-705: memory "retains all masks and trig lock actions", E3 scrolls left
to past actions, and "Press K3 to jump directly to the latest action" - so jumping to the
latest action must leave the step as the last action left it, with both chord voices.
README 597: a chord mask adds a chord note to every trigger of the step.

Channel 1 plays C D E F (60/62/64/65) at velocities 127/117/107/97. Holding step 2 and
turning Chd1 one detent up adds the 2nd above D (E, 64); a second action on the same step
turns Chd3 up to the 5th above (A, 69). Stepping back twice removes both; K3 must bring
both back. The baseline restored only the Chd3 voice, because redo-all merged the two
actions' event data field by field and the later chord_degrees table replaced the earlier.
"""
PATTERN = [60, 62, 64, 65]


def memory_redo_chord_merge(c):
    def heard(stage, limit=12):
        marker = c.snapshot()['midi_count']
        c.tap(1, 8); c.elapse(1.4); c.tap(1, 8)
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        ons = [m['bytes'] for m in state['midi']
               if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0][:limit]
        notes = [b[1] for b in ons]
        c.results.append(dict(kind='memory-redo-chord-merge', stage=stage, notes=notes))
        return notes

    def chord_edit(field_offset, turns):
        c.enc(1, -2); c.screen_header('Ch. 1 Note Masks', selected=1)
        c.enc(2, -9); c.enc(2, field_offset)
        c.action(type='grid', x=2, y=4, state=1); c.elapse(.05)
        try: c.enc(3, turns)
        finally: c.action(type='grid', x=2, y=4, state=0)
        c.elapse(.15); c.enc(1, 2); c.screen_header('Ch. 1 Memory')

    c.configure()
    c.enc(1, -2); c.screen_header('Ch. 1 Memory')
    base = heard('pattern')
    assert base[:4] == PATTERN, base

    chord_edit(4, 1)                                   # Chd1: 2nd above D = E (64)
    one = heard('chd1-set')
    assert one[:3] == [60, 62, 64], one                 # E sounds with D on step 2

    chord_edit(6, 4)                                   # Chd3: 5th above D = A (69)
    both = heard('chd1-and-chd3-set')
    assert both[:4] == [60, 62, 64, 69], both           # both voices sound with D

    c.enc(3, -2)                                       # E3 back over both actions
    undone = heard('after-memory-back-two')
    assert undone[:4] == PATTERN, undone

    c.key(3); c.elapse(.2)                             # K3: jump to the latest action
    redone = heard('after-k3-jump-to-latest')
    assert redone[:4] == both[:4], ('K3 lost a chord voice', redone[:4], both[:4])
    c.results.append(dict(kind='memory-redo-chord-merge-summary', voices=redone[:4], passed=True))

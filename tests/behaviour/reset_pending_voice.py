"""A note still sounding at a song transition with "Reset at Song Sequence Change" on
(README 1074, on by default: channels reset at the transition; README 805: "Pattern
resets likewise preserve the remaining duration of sounding notes").

Global length 4; slot 2 is a copy an octave up. Slot 1 step 4 carries a step length
mask of 3 steps, so its note (65) sounds across the transition. It must release 3
steps after its onset while slot 2 starts at its step 1 on time.
"""
PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def reset_pending_voice(c):
    from cases import length_mask_display
    c.configure()
    c.tap(6, 8); c.tap(2, 7)
    for _ in range(3): c.tap(8, 7)                                # global length 4
    c.hold_tap((1, 1), (2, 1)); c.tap(2, 1); c.tap(3, 8); c.tap(11, 8)   # slot 2 = copy, octave +1
    c.tap(6, 8); c.tap(1, 1); c.tap(3, 8)
    c.enc(1, -5); c.enc(2, -5); c.enc(2, 3); length_mask_display(c, 'X')   # Note Masks, Len
    c.action(type='grid', x=4, y=4, state=1)
    try: c.elapse(.05); c.enc(3, 22); length_mask_display(c, '3')       # step 4: 3 steps
    finally: c.action(type='grid', x=4, y=4, state=0)
    before = c.snapshot()['midi_count']; c.tap(1, 8)
    def onsets(s): return [m for m in s['midi'] if m['index'] > before and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    state = c.wait(lambda s: len(onsets(s)) >= 9, timeout=4)
    c.tap(1, 8); state = c.wait(lambda s: not s['midi_capture']['outstanding'])
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
    notes = onsets(state)[:8]
    expected = [n for n, _ in PHRASE] + [n + 12 for n, _ in PHRASE]
    assert [m['bytes'][1] for m in notes] == expected, [m['bytes'][1] for m in notes]
    start = notes[0][field]
    offsets = [(m[field] - start) / 1e9 for m in notes]
    assert all(abs(o - i / 6) <= tolerance for i, o in enumerate(offsets)), offsets
    long_note = notes[3]
    release = next(m for m in state['midi'] if m['index'] > long_note['index'] and m['port'] == 1 and
                   (m['bytes'][:2] == [128, 65] or (m['bytes'][0] == 144 and m['bytes'][1] == 65 and m['bytes'][2] == 0)))
    held = (release[field] - long_note[field]) / 1e9
    assert abs(held - 3 / 6) <= tolerance, dict(held_seconds=held, expected=.5)
    c.results.append(dict(kind='reset-pending-voice', held_seconds=held, onsets=offsets, passed=True))

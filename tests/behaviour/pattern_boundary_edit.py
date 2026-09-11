"""A pattern edit made just before a song boundary (README 910 and "Pattern editor":
painted pattern edits apply to the playing sequence).

Working patterns are rebuilt by a debounced sweep of one channel per scheduler tick
(1/300 s); the song boundary starts its own sweep for the next slot. Global length 4,
song mode on: slot 1 plays channel 1's phrase, slot 2 is a copy an octave up. With
1 ms left in slot 1's first pass, step 1's note in slot 1's pattern is raised to
degree 4 (G). The next time slot 1 plays, step 1 must play G (real time: 80 ms before).
"""
PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def pattern_boundary_edit(c):
    import time
    c.configure()
    c.tap(6, 8); c.tap(2, 7)
    for _ in range(3): c.tap(8, 7)                                # global length 4
    c.hold_tap((1, 1), (2, 1)); c.tap(2, 1); c.tap(3, 8); c.tap(11, 8)   # slot 2 = copy, octave +1
    c.tap(6, 8); c.tap(1, 1)
    c.tap(5, 8); c.tap(5, 8)                                      # pattern note editor (pattern 1)
    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    before = c.snapshot()['midi_count']; c.tap(1, 8)
    def onsets(s): return [m for m in s['midi'] if m['index'] > before and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    first = c.wait(lambda s: len(onsets(s)) >= 1, timeout=2)
    start = onsets(first)[0][field]
    # 1 ms before the slot 1 -> 2 boundary (inside the first sweep tick); real time cannot place an
    # input that precisely, so it edits 80 ms before and checks the ordinary case.
    edit_at = start + round(4 / 6 * 1e9) - (1_000_000 if controlled else 80_000_000)
    now = c.logical_ns if controlled else time.monotonic_ns()
    c.elapse((edit_at - now) / 1e9)
    c.action(type='grid', x=1, y=3, state=1); c.action(type='grid', x=1, y=3, state=0)  # step 1 -> degree 4
    state = c.wait(lambda s: len(onsets(s)) >= 13, timeout=5)
    c.tap(1, 8); c.wait(lambda s: not s['midi_capture']['outstanding'])
    notes = [m['bytes'][1] for m in onsets(state)[:13]]
    expected = [60, 62, 64, 65, 72, 74, 76, 77, 67, 62, 64, 65, 72]
    c.results.append(dict(kind='pattern-boundary-edit', expected=expected, actual=notes))
    assert notes == expected, dict(expected=expected, actual=notes)

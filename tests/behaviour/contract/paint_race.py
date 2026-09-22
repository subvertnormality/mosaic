"""Paint pressed before the primed preview settles (README 424-428: prime shows the
algorithm's pattern; "Pressing it again paints your edits", deactivating the dimly
blinking overlaps). Gap-scan item G: the prime job rebuilds the paint pattern from
empty over about 18 scheduler ticks (1/300 s each), and the paint press saves
whatever is built so far; the job then shows the preview again.

Eight-step loop with steps 1-4 active; Euclidean 3 in 8 proposes steps 1, 4, 7 of every
eight. The paint press comes 20 ms after the prime press (controlled time; real time
cannot place it reliably and uses the same gap as best effort). The painted grid must
be the full exclusive-or of the original and proposed steps on all 64 cells, and it
must stay so across the blink period (no preview re-shown). The same prime and paint with the
preview settled runs first as the control that proves the oracle.
"""


def paint_race(c):
    c.configure(); c.hold_tap((1, 4), (8, 4))
    c.tap(5, 8); c.tap(5, 8)
    for x, y in [(5, 3), (6, 2), (7, 1), (8, 6)]: c.tap(x, y)
    c.tap(3, 8); c.tap(5, 8)                                      # trig editor
    c.tap(14, 2); c.tap(2, 2)                                     # Euclidean, one pulse
    for _ in range(2): c.tap(10, 2)
    c.tap(2, 3)
    for _ in range(7): c.tap(10, 3)                               # 3 in 8
    cells = [((step - 1) % 16 + 1, (step - 1) // 16 + 4) for step in range(1, 65)]
    original = {1, 2, 3, 4}
    proposed = {step for step in range(1, 65) if (step - 1) % 8 + 1 in (1, 4, 7)}
    painted = original.symmetric_difference(proposed)
    expected = [15 if step in painted else 2 for step in range(1, 65)]
    c.led_values(cells, [15 if step in original else 2 for step in range(1, 65)])

    def settled_frames(label):
        frames = []
        for _ in range(4):
            grid = c.snapshot()['grid']
            frames.append([grid[(y - 1) * 16 + x - 1] for x, y in cells]); c.elapse(.25)
        c.results.append(dict(kind='paint-frames', label=label, expected=expected, frames=frames))
        return [[step for step, (a, b) in enumerate(zip(frame, expected), 1) if a != b] for frame in frames]

    # Control: the same prime and paint with the preview settled (0.5 s) must give the full
    # exclusive-or, proving the oracle; priming and painting again restores the original.
    c.tap(16, 8); c.elapse(.5); c.tap(16, 8); c.elapse(.3)
    wrong = settled_frames('control')
    assert not any(wrong), ('Control paint differs from the primed pattern', wrong)
    c.tap(16, 8); c.elapse(.5); c.tap(16, 8); c.elapse(.3)
    c.led_values(cells, [15 if step in original else 2 for step in range(1, 65)])

    c.action(type='grid', x=16, y=8, state=1); c.action(type='grid', x=16, y=8, state=0)   # prime
    c.elapse(.02)
    c.action(type='grid', x=16, y=8, state=1); c.action(type='grid', x=16, y=8, state=0)   # paint
    c.elapse(.3)
    wrong = settled_frames('race')
    assert not any(wrong), ('Paint 20 ms after prime differs from the primed pattern', wrong)
    c.results.append(dict(kind='paint-race-summary', passed=True))

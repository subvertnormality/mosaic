"""Selected-pattern flicker on every step page of the note and velocity editors (README 471:
"The gentle flicker on the top row indicates the currently chosen pattern"; README 461:
"Switch between the four sets of 16 steps using the dedicated buttons"; README 485: the
velocity editor "functions similarly to the note page").

Pattern 1 is selected in the trig editor, so column 1 is the chosen pattern's column. On each
of the four step pages (grid buttons 9-12 on row 8) the first two columns are set to their
top row, which puts each column's active LED on the top row. The chosen pattern's column must
flicker there on every page, not only on page 1; column 2 (not the chosen pattern) must not.
"""

PAGES = ((9, 'steps 1-16'), (10, 'steps 17-32'), (11, 'steps 33-48'), (12, 'steps 49-64'))


def editor_pattern_flicker(c):
    c.configure(); c.tap(5, 8); c.tap(1, 1)                      # trig editor, pattern 1
    c.tap(5, 8)                                                  # note editor
    wrong = []
    for editor in ('note', 'velocity'):
        for button, label in PAGES:
            c.tap(button, 8); c.tap(1, 1); c.tap(2, 1)
            c.wait(lambda s: s['grid'][0] >= 11 and s['grid'][1] >= 11)
            chosen, other = [], []
            for _ in range(8):                                   # blink toggles every 0.4 s
                grid = c.snapshot()['grid']; chosen.append(grid[0]); other.append(grid[1]); c.elapse(.15)
            c.results.append(dict(kind='top-row-flicker', editor=editor, page=label, chosen=chosen, other=other))
            # README 471: the chosen pattern's top-row cell flickers; another column does not.
            # The levels 11/13 around the active 12 are characterisation, not manual text.
            if sorted(set(chosen)) != [11, 13] or set(other) != {12}:
                wrong.append((editor, label, sorted(set(chosen)), sorted(set(other))))
        c.tap(5, 8)                                              # velocity editor
    assert not wrong, ('Chosen pattern top-row active LED does not flicker', wrong)
    c.results.append(dict(kind='top-row-flicker-summary', passed=True))

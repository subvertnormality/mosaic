"""An unset chord mask starts from X (human decision 2026-09-11, suspected-defects S26; README
597: a channel mask set without holding a step "add[s] a chord note to every trigger").

On the Masks page an unset chord slot shows X. Turning it one detent must move one chord step
away from X: up to the 2nd, down to the 7th below. Channel 1 plays C D E F (C major, velocities
127/117/107/97); with Chd1 one step up and Chd2 one step down every trig sounds its root, the
scale degree above and the scale degree below. The chord labels ("X", "2nd", "-7th") are
characterisation, not manual text.
"""

LABELS = ["--oct", "--2nd", "--3rd", "--4th", "--5th", "--6th", "--7th", "-oct", "-2nd", "-3rd",
          "-4th", "-5th", "-6th", "-7th", "X", "2nd", "3rd", "4th", "5th", "6th", "7th", "+oct",
          "+2nd", "+3rd", "+4th", "+5th", "+6th", "+7th", "++oct"]


# Live Masks page (C01): a selected slot is read from the selected field's value line
# ("Chord N" and its exact value); an unselected slot from its own overview cell (Chd N).
def expect_cell(c, slot, selected, label, stage):
    field = 'chord_%d' % slot
    try:
        if selected:
            c.ui.expect_selected_mask(field, label)
        else:
            c.ui.expect_field_value(field, label)
    except AssertionError:
        shown = c.ui.selected_mask_value(field, LABELS) if selected else '?'
        raise AssertionError('Chd%d after %s' % (slot, stage), dict(expected=label, shown=shown))
    c.results.append(dict(kind='chord-mask-cell', slot=slot, stage=stage, label=label, passed=True))


def settled_cell(c, slot, selected, label):
    """The selected slot's label once it shows `label`, or what it shows after the wait expires."""
    assert selected
    field = 'chord_%d' % slot
    try:
        c.ui.expect_selected_mask(field, label)
    except AssertionError:
        pass
    return c.ui.selected_mask_value(field, LABELS)


def chord_mask_start_x(c):
    from cases import assert_durations
    c.configure(); c.ui.turn(1, -4); c.enc(2, 3)                    # Masks page, Chd1 selected
    expect_cell(c, 1, True, 'X', 'unset')
    expect_cell(c, 2, False, 'X', 'unset')
    c.enc(3, 1); up = settled_cell(c, 1, True, '2nd')
    c.enc(2, 1); expect_cell(c, 2, True, 'X', 'unset')
    c.enc(3, -1); down = settled_cell(c, 2, True, '-7th')
    c.results.append(dict(kind='chord-mask-first-turn', up=up, down=down))
    assert (up, down) == ('2nd', '-7th'), ('One turn from an unset chord mask', dict(expected=('2nd', '-7th'), shown=(up, down)))
    major = [0, 2, 4, 5, 7, 9, 11]

    def pitch(degree): return 60 + 12 * (degree // 7) + major[degree % 7]
    expected = []
    for degree, velocity in enumerate([127, 117, 107, 97]):
        expected += [(1, [144, pitch(degree + offset), velocity]) for offset in (0, 1, -1)]
    notes = c.playback(expected, cycles=2, timeout=5)
    assert_durations(c, notes, [1] * 24)
    c.results.append(dict(kind='chord-mask-start-x-summary', passed=True))

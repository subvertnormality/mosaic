"""Trig Locks dials at Off (suspected defects S20 and S62, human decision 2026-09-11: the dial
shows X at Off, and a parameter without off_value is Off at -1).

README 546: "Setting a MIDI parameter to its configured Off value (default -1) ensures that
the current setting on the device remains unchanged." README 761: an Off parameter sends no
value. The norns params menu shows the Off value as "X" (patch_params.patch_boundaries), and
so does the Trig Probability dial, whose Off lies inside its range.

Seeded Emulator test device (tests/behaviour/config/emu-midi.json):
  Control 1  CC1   0..127  off -1        (S20 shape; 54 stock Digitakt params share it)
  CCdefault  CC1  -1..127  no off_value  (S62: README 546 "default -1")
  Trig Probability, stock, off inside its range (control)

Each slot's value is read pixel-exactly on the live Trig params overview (C02): the selected
slot's whole value on the full value line, another slot's in its cell, compared with rendered
candidate texts; '?' is anything else. The old dial settled from a number to a bar; the live
screen has no bar and keeps showing the number, so the settled check reads '0'. All
observations are recorded before the assertions run.
"""

def dial_value(c, slot, label, selected, short_label=None, candidates=('X', '0', '-1')):
    """The slot's shown value on the live Trig params overview (C02), read
    exactly: the selected slot on the full value line beside its parameter
    name, another slot in its own cell under its short label. '?' is none."""
    from frame_oracle import overview_cell_matches, selected_field_matches
    state = c.snapshot()
    if selected:
        hit = [t for t in candidates if selected_field_matches(state, 'overview_params', label, t)]
    else:
        hit = [t for t in candidates if overview_cell_matches(state, 'overview_params', slot, short_label, t)]
    return hit[0] if len(hit) == 1 else ('?' if not hit else '|'.join(hit))


def cc1_values(c, marker):
    return [m['bytes'][2] for m in c.snapshot()['midi']
            if m['index'] > marker and m['bytes'][0] & 0xF0 == 0xB0 and m['bytes'][1] == 1]


def play_cycle(c):
    marker = c.snapshot()['midi_count']
    c.tap(1, 8); c.elapse(1.6); c.tap(1, 8)
    c.wait(lambda s: not s['midi_capture']['outstanding']); c.elapse(.3)
    notes = [m for m in c.snapshot()['midi'] if m['index'] > marker and m['bytes'][0] & 0xF0 == 0x90 and m['bytes'][2] > 0]
    return len(notes), cc1_values(c, marker)


def dial_off_display(c):
    from cases import assign_trig_parameter
    checks = []

    def check(label, actual, expected, cite):
        checks.append(dict(label=label, actual=actual, expected=expected, cite=cite, passed=actual == expected))
        c.results.append(dict(kind='dial-off-display', **checks[-1]))

    c.configure(); c.enc(3, 1); c.key(3)  # Emulator test device, as patch_params.open_patch_control
    c.ui.turn(1, -3); c.screen_header('Ch. 1 Trig Locks', selected=2)

    # Slot 1: Control 1 (off -1 below min 0). Assigned at its Off default.
    assign_trig_parameter(c, 'Control 1'); c.elapse(2.5)
    check('Control 1 assigned at Off', dial_value(c, 1, 'Control 1', True), 'X', 'README 546 + human decision S20')
    c.enc(3, 1); c.elapse(.2)
    check('Control 1 read-out at 0', dial_value(c, 1, 'Control 1', True), '0', 'characterisation, not manual text')
    c.elapse(2.5)
    check('Control 1 settled at 0', dial_value(c, 1, 'Control 1', True), '0', 'characterisation, not manual text')
    notes, cc = play_cycle(c)
    check('Control 1 at 0 plays CC1 value 0', (notes > 0, bool(cc) and set(cc) == {0}), (True, True), 'README 546')
    c.enc(3, -1); c.elapse(.2)
    check('Control 1 read-out after turning to Off', dial_value(c, 1, 'Control 1', True), 'X', 'README 546 + human decision S20')
    c.elapse(2.5)
    check('Control 1 settled at Off', dial_value(c, 1, 'Control 1', True), 'X', 'README 546 + human decision S20')

    # Slot 2: Trig Probability, Off inside its range (control).
    c.enc(2, 1); assign_trig_parameter(c, 'Trig Probability'); c.elapse(2.5)
    check('Trig Probability at Off (control)', dial_value(c, 2, 'Trig Probability', True), 'X', 'characterisation, not manual text')

    # Slot 3: CCdefault, no off_value (README 546: default -1). Assigned at -1.
    c.enc(2, 1); assign_trig_parameter(c, 'CCdefault'); c.elapse(2.5)
    check('CCdefault assigned at -1 (Off)', dial_value(c, 3, 'CCdefault', True), 'X', 'README 546 "default -1" + human decision S62')
    c.enc(3, 1); c.elapse(.2)
    check('CCdefault read-out at 0', dial_value(c, 3, 'CCdefault', True), '0', 'characterisation, not manual text')
    c.enc(3, -1); c.elapse(.2)
    check('CCdefault read-out after turning to Off', dial_value(c, 3, 'CCdefault', True), 'X', 'README 546 "default -1" + human decision S62')
    c.elapse(2.5)
    check('CCdefault settled at Off', dial_value(c, 3, 'CCdefault', True), 'X', 'README 546 "default -1" + human decision S62')

    # The other dials keep their display once deselected; the parameters stay Off.
    check('Control 1 still Off when deselected', dial_value(c, 1, 'Control 1', False, short_label='CC'), 'X', 'README 546 + human decision S20')
    notes, cc = play_cycle(c)
    check('Both Off: notes play and no CC1 is sent', (notes > 0, cc), (True, []), 'README 546, 761')

    failed = [x for x in checks if not x['passed']]
    assert not failed, ('Dial at Off', failed)
    c.results.append(dict(kind='dial-off-display-summary', checks=len(checks), passed=True))

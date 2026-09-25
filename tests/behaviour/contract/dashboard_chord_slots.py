"""Note Dashboard chord slots show the chord notes that were sent (suspected defect S51).

README 679: "On the Norns first page in the channel mode you can see the last played notes
on the currently selected channel." Human decision 2026-09-11 (S51): chord slots show
exactly the notes sent (clamped to 0-127, as MIDI sends them) and X when none has played.

Channel 1 plays four steps with the channel Note mask at C-1 (MIDI 12) and the channel
Chord 1 mask set on the Masks page (README 569-600). In C major the Chd1 mask degrees give:
  -6th   -> MIDI 9  (A-2)
  -oct   -> MIDI 0  (C-2)                      the voice at note 0, (a)
  --7th  -> computed -1, sent as MIDI 0 (C-2)  (b)
  --6th  -> computed -3, sent as MIDI 0 (C-2)  (b)
Between them -6th is played again (the first detent down from an unset
channel Chd1 reads -6th) so each result differs from the one before. After each
play the Chd1 cell must name the chord voice the MIDI output received, and Chd2..Chd4,
which never play, must show X (c); a fresh dashboard shows X in all four chord slots (c).
The X marker is characterisation (as in M-DASHBOARD-SELECT-001), not manual text. Cells are
read pixel-exactly against rendered candidates. All observations are recorded before the
assertions run.

C06 OUTPUT (the live Note Dashboard) shows one field at a time. Its Chord field shows the four
slots' values in slot order, space separated, so each check reads that field exactly (label
and value) after E2 selects it: "<Chd1> X X X". On the Masks page (C01) the Chd1 mask label is
read from the selected field's value line ("Chord 1", exact value).
"""

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
TOP_FIELDS = (('Note', 'root'), ('Vel', 'velocity'), ('Len', 'length'))
ROOT = 12


def note_name(n):
    """musicutil.note_num_to_name(n, true): name, then floor(n / 12 - 2)."""
    return NAMES[n % 12] + str(n//12 - 2)


def chord_field(c, expected):
    """The Chord field shows exactly `expected`; else what it shows among the slot candidates."""
    try:
        c.ui.expect_output_field('chord', expected)
        return expected
    except AssertionError:
        return c.ui.output_field_value('chord', [expected, 'X X X X'], select=False)


def dashboard_chord_slots(c):
    checks = []

    def check(label, actual, expected, cite):
        checks.append(dict(label=label, actual=actual, expected=expected, cite=cite, passed=actual == expected))
        c.results.append(dict(kind='dashboard-chord-slot', **checks[-1]))

    def to_dashboard():
        c.ui.turn(1, 5); c.screen_header('Ch. 1 Note Dashboard', selected=6)

    def to_masks():
        c.ui.turn(1, -5); c.screen_header('Ch. 1 Note Masks')

    def chord_mask(label, direction):
        for _ in range(20):
            c.elapse(.15)  # let the screen redraw after the previous detent
            if c.ui.selected_mask_value('chord_1', [label]) == label:
                c.results.append(dict(kind='chord-mask-screen', label=label, passed=True)); return
            c.enc(3, direction)
        raise AssertionError('Chd1 mask label not reached: ' + label)

    def play(label):
        to_dashboard()
        marker = c.snapshot()['midi_count']
        c.tap(1, 8); c.elapse(1.5); c.tap(1, 8)
        c.wait(lambda s: not s['midi_capture']['outstanding']); c.elapse(.3)
        ons = [m['bytes'][1] for m in c.snapshot()['midi']
               if m['index'] > marker and m['bytes'][0] & 0xF0 == 0x90 and m['bytes'][2] > 0]
        voices = sorted(set(ons) - {ROOT})
        # Setup sanity: the root and exactly one chord voice sounded.
        assert ROOT in ons and len(voices) == 1, ('Unexpected notes for Chd1 ' + label, ons)
        expected = ' '.join([note_name(voices[0])] + ['X'] * 3)
        shown = chord_field(c, expected)
        c.results.append(dict(kind='dashboard-chord-play', mask=label, sent=sorted(set(ons)), chord=shown))
        check('Chd1 sent voice, Chd2..Chd4 X after playing ' + label, shown, expected,
              'README 679 + human decision S51 (X is characterisation)')
        to_masks()
        return voices[0]

    c.configure(); c.ui.turn(1, -4); c.screen_header('Ch. 1 Note Masks')

    # (c) a fresh dashboard: nothing has played.
    to_dashboard()
    fresh = chord_field(c, 'X X X X')
    top = {name: c.ui.output_field_value(field, ['X', 'C-2', '0', '0.0', '-1', '-1.0'])
           for name, field in TOP_FIELDS}
    c.results.append(dict(kind='dashboard-fresh', chords=fresh, top=top,
                          note='Note/Vel/Len recorded only: characterisation, not asserted'))
    check('Fresh dashboard chord slots', fresh, 'X X X X',
          'README 679 + human decision S51 (X is characterisation)')
    to_masks()

    c.enc(3, 13)  # Note mask X -> C-1 (MIDI 12), as the S51 probe
    c.enc(2, 3)   # Note -> Chd1
    sent = {}
    for label, direction in (('-6th', -1), ('-oct', -1), ('-6th', 1), ('--7th', -1), ('-6th', 1), ('--6th', -1)):
        chord_mask(label, direction)
        sent.setdefault(label, set()).add(play(label))
    # Setup sanity: the expected voices were sent (MIDI clamps -1 and -3 to 0, m_midi.lua).
    assert sent == {'-6th': {9}, '-oct': {0}, '--7th': {0}, '--6th': {0}}, ('Chord voices sent', sent)

    failed = [x for x in checks if not x['passed']]
    assert not failed, ('Note Dashboard chord slots', failed)
    c.results.append(dict(kind='dashboard-chord-slots-summary', checks=len(checks), passed=True))

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
"""
import base64

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
CHORD_CELLS = (('Chd1', 0), ('Chd2', 25), ('Chd3', 50), ('Chd4', 75))
TOP_CELLS = (('Note', 0), ('Vel', 25), ('Len', 50))
ROOT = 12


def note_name(n):
    """musicutil.note_num_to_name(n, true): name, then floor(n / 12 - 2)."""
    return NAMES[n % 12] + str(n//12 - 2)


def read_cells(c, cells, baseline, candidates):
    from frame_oracle import render
    pixels = base64.b64decode(c.snapshot()['frame']['pixels_base64'])
    out = {}
    for name, x in cells:
        idx = [(y*128+xx)*4+k for y in range(baseline-7, baseline+3) for xx in range(x, x+24) for k in range(3)]
        hit = []
        for t in candidates:
            expected = render([(x, baseline, 1, t)])
            if all(pixels[i] == expected[i] for i in idx):
                hit.append(t)
        out[name] = hit[0] if len(hit) == 1 else ('?' if not hit else '|'.join(hit))
    return out


def chord_cells(c):
    return read_cells(c, CHORD_CELLS, 48, ['X'] + [note_name(n) for n in range(-24, 128)])


def dashboard_chord_slots(c):
    from frame_oracle import render
    checks = []

    def check(label, actual, expected, cite):
        checks.append(dict(label=label, actual=actual, expected=expected, cite=cite, passed=actual == expected))
        c.results.append(dict(kind='dashboard-chord-slot', **checks[-1]))

    def to_dashboard():
        c.enc(1, 5); c.screen_header('Ch. 1 Note Dashboard', selected=6)

    def to_masks():
        c.enc(1, -5); c.screen_header('Ch. 1 Note Masks')

    chord_label_rows = [(y*128+x)*4+k for y in range(41, 51) for x in range(25) for k in range(3)]

    def chord_mask(label, direction):
        expected = render([(0, 40, 15, 'Chd1'), (0, 48, 15, label)])
        for _ in range(20):
            c.elapse(.15)  # let the screen redraw after the previous detent
            actual = base64.b64decode(c.snapshot()['frame']['pixels_base64'])
            if all(actual[i] == expected[i] for i in chord_label_rows):
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
        cells = chord_cells(c)
        c.results.append(dict(kind='dashboard-chord-play', mask=label, sent=sorted(set(ons)), cells=cells))
        # Setup sanity: the root and exactly one chord voice sounded.
        assert ROOT in ons and len(voices) == 1, ('Unexpected notes for Chd1 ' + label, ons)
        check('Chd1 after playing ' + label, cells['Chd1'], note_name(voices[0]), 'README 679 + human decision S51')
        check('Chd2..Chd4 after playing ' + label, [cells[k] for k in ('Chd2', 'Chd3', 'Chd4')], ['X']*3,
              'README 679 + human decision S51 (X is characterisation)')
        to_masks()
        return voices[0]

    c.configure(); c.enc(1, -4); c.screen_header('Ch. 1 Note Masks')

    # (c) a fresh dashboard: nothing has played.
    to_dashboard()
    fresh = chord_cells(c)
    top = read_cells(c, TOP_CELLS, 26, ['X', 'C-2', '0', '0.0', '-1', '-1.0'])
    c.results.append(dict(kind='dashboard-fresh', chords=fresh, top=top,
                          note='Note/Vel/Len recorded only: characterisation, not asserted'))
    check('Fresh dashboard chord slots', [fresh[k] for k, _ in CHORD_CELLS], ['X']*4,
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

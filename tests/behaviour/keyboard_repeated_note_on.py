"""A repeated Note On for a held key leaves no stuck note (suspected defect S8, human
decision 2026-09-11: "a repeated Note On for a held key must not leave a stuck note").

Two keyboards merged onto one MIDI input port and channel both press the same key: the
port receives Note On, Note On, then one Note Off per key. README 195: "By default, the
keyboard plays the keys you press", so both presses sound on the selected channel; once
both keys are released nothing may keep sounding. README 805 states, for sequenced
notes, that "Overlapping notes of the same MIDI pitch still send a corresponding Note Off
for each Note On"; the S8 decision applies the same balance to keyboard input.
Both release forms (Note Off, and Note On with velocity zero) are exercised.
"""


def keyboard_repeated_note_on(c):
    c.configure()
    for release in (128, 144):
        marker = c.snapshot()['midi_count']
        c.action(type='midi', port=1, bytes=[144, 72, 90]); c.elapse(.05)
        c.action(type='midi', port=1, bytes=[144, 72, 80]); c.elapse(.05)   # the second keyboard, same key
        c.action(type='midi', port=1, bytes=[release, 72, 0]); c.elapse(.05)
        c.action(type='midi', port=1, bytes=[release, 72, 0]); c.elapse(.1)
        state = c.snapshot()
        emitted = [(m['port'], m['bytes']) for m in state['midi'] if m['index'] > marker and 128 <= m['bytes'][0] <= 159]
        onsets = [e for e in emitted if e[1][0] & 0xf0 == 0x90 and e[1][2] > 0]
        releases = [e for e in emitted if e[1][0] & 0xf0 == 0x80 or (e[1][0] & 0xf0 == 0x90 and e[1][2] == 0)]
        c.results.append(dict(kind='repeated-note-on-release', release_status=release, emitted=emitted,
                              outstanding=state['midi_capture']['outstanding']))
        # README 195: both presses play on the selected channel (port 1, MIDI channel 1).
        assert [b for _, b in onsets] == [[144, 72, 90], [144, 72, 80]], emitted
        # Human decision S8 (README 805 balance): every onset has its own release, and
        # nothing is left sounding after both keys are released.
        assert len(releases) == len(onsets) and all(p == 1 and b[1] == 72 for p, b in releases), emitted
        assert state['midi_capture']['outstanding'] == [], ('Stuck note after both keys released', state['midi_capture']['outstanding'], emitted)
    c.results.append(dict(kind='repeated-note-on-summary', passed=True))

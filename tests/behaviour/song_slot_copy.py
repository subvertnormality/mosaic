"""Song slot copy and erase by two-key gestures (README 903-904: "press and hold the
source slot, then the destination slot"; "To clear a slot, copy an empty slot over
it"). The slot pressed first is the source whichever key is released first
(arbitrated 2026-09-11, press-order-slot-copy-only; decisions.md SEM-016).
"""
PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def song_slot_copy(c):
    c.configure(); c.tap(6, 8)
    def gesture(source, destination, release_source_first):
        c.action(type='grid', x=source, y=1, state=1); c.elapse(.05)
        c.action(type='grid', x=destination, y=1, state=1); c.elapse(.05)
        order = (source, destination) if release_source_first else (destination, source)
        for x in order: c.action(type='grid', x=x, y=1, state=0); c.elapse(.05)
    def slot(number, stage, octave):
        c.tap(number, 1)
        marker = c.snapshot()['midi_count']; c.tap(1, 8); c.elapse(1.0); c.tap(1, 8)
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        notes = [m['bytes'] for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0][:4]
        expected = [] if octave is None else [[144, n + 12 * octave, v] for n, v in PHRASE]
        assert notes == expected, (stage, number, notes, expected)
        c.results.append(dict(kind='song-slot-copy', stage=stage, slot=number, notes=[n[1] for n in notes], passed=True))
    gesture(1, 2, release_source_first=False)                    # the usual order
    slot(2, 'copy-release-destination-first', 0)
    c.tap(3, 8); c.tap(11, 8); c.tap(6, 8)                        # slot 2 (selected): octave +1
    gesture(2, 3, release_source_first=True)
    slot(3, 'copy-release-source-first', 1); slot(2, 'source-unchanged', 1)
    gesture(4, 3, release_source_first=True)                     # empty slot 4 over slot 3
    slot(3, 'erase-release-source-first', None); slot(1, 'untouched', 0)

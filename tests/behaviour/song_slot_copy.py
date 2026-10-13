"""Song slot copy and erase by two-key gestures (README 903-904: "press and hold the
source slot, then the destination slot"; "To clear a slot, copy an empty slot over
it"). The slot pressed first is the source whichever key is released first
(arbitrated 2026-09-11, press-order-slot-copy-only; decisions.md SEM-016).
"""
PHRASE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def song_slot_copy(c):
    c.configure(); c.ui.song_editor()
    def gesture(source, destination, release_source_first):
        c.ui.gesture([('song_pattern_slot', source)], []); c.elapse(.05)
        c.ui.gesture([('song_pattern_slot', destination)], []); c.elapse(.05)
        order = (source, destination) if release_source_first else (destination, source)
        for slot_number in order:
            c.ui.gesture([], [('song_pattern_slot', slot_number)]); c.elapse(.05)
    def slot(number, stage, octave):
        c.ui.tap_control('song_pattern_slot', number)
        marker = c.snapshot()['midi_count']; c.ui.play(); c.elapse(1.0); c.ui.stop()
        state = c.wait(lambda s: not s['midi_capture']['outstanding'])
        notes = [m['bytes'] for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0][:4]
        expected = [] if octave is None else [[144, n + 12 * octave, v] for n, v in PHRASE]
        assert notes == expected, (stage, number, notes, expected)
        c.results.append(dict(kind='song-slot-copy', stage=stage, slot=number, notes=[n[1] for n in notes], passed=True))
    gesture(1, 2, release_source_first=False)                    # the usual order
    slot(2, 'copy-release-destination-first', 0)
    c.ui.menu('channel_editor'); c.ui.tap_control('channel_octave', 1); c.ui.song_editor()  # slot 2 (selected): octave +1
    gesture(2, 3, release_source_first=True)
    slot(3, 'copy-release-source-first', 1); slot(2, 'source-unchanged', 1)
    gesture(4, 3, release_source_first=True)                     # empty slot 4 over slot 3
    slot(3, 'erase-release-source-first', None); slot(1, 'untouched', 0)

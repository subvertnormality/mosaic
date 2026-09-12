"""Native virtual-grid disconnect during a held channel-range gesture.

README 718-724 defines the ordinary two-key channel-range gesture and its
bright-range LED feedback. The native virtual-grid lifecycle's release-before-
remove behaviour is an emulator characterisation, not a README claim about a
physical grid disconnect.
"""

PHRASE = [[144, 60, 127], [144, 62, 117], [144, 64, 107], [144, 65, 97]]


def grid_disconnect_two_key_range(c):
    c.configure()
    row = lambda state: [state['grid'][48 + x] for x in range(16)]
    c.wait(lambda state: row(state) == [15, 15, 15, 15] + [0] * 12)
    before = c.snapshot()['midi_count']

    # The first synthetic release leaves step 1 held, so Mosaic receives the
    # ordinary valid 1..8 range gesture before the device removal callback.
    c.action(type='grid', x=8, y=4, state=1); c.elapse(.05)
    c.action(type='grid', x=1, y=4, state=1); c.elapse(.05)
    c.action(type='grid_connection', connected=False)
    disconnected = c.wait(lambda state: not state['grid_device']['connected'])
    assert disconnected['grid'] == [0] * 128
    assert disconnected['midi_count'] == before

    c.action(type='grid_connection', connected=True)
    restored = c.wait(lambda state: state['grid_device']['connected'] and row(state) == [15, 15, 15, 15, 2, 2, 2, 2] + [0] * 8)
    assert restored['midi_count'] == before
    c.results.append(dict(kind='native-grid-lifecycle-range',
        synthetic_release_order=[[8, 4], [1, 4]], range_leds=row(restored),
        midi_count_before=before, midi_count_after=restored['midi_count'], passed=True))

    # README 265-280: the next ordinary menu tap must be a normal Pattern-page
    # navigation, rather than the tail of the interrupted dual gesture.
    c.tap(5, 8); c.led_values([(5, 8)], [5])
    assert c.snapshot()['midi_count'] == before
    c.results.append(dict(kind='native-grid-lifecycle-clean-next-tap',
        menu_cell=[5, 8], expected_level=5, passed=True))

    # The expanded range is also observable musically: four configured notes,
    # then four silent steps, so the next C lands eight sixteenth-notes later.
    marker = c.snapshot()['midi_count']; c.tap(1, 8)
    def onsets(state):
        return [m for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    state = c.wait(lambda state: len(onsets(state)) >= 5, timeout=4)
    notes = onsets(state)[:5]
    assert [note['bytes'] for note in notes] == PHRASE + [PHRASE[0]]
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    expected = [0, 1 / 6, 2 / 6, 3 / 6, 8 / 6]
    actual = [(note[field] - notes[0][field]) / 1e9 for note in notes]
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
    assert all(abs(got - want) <= tolerance for got, want in zip(actual, expected)), dict(actual=actual, expected=expected)
    c.tap(1, 8); c.wait(lambda state: not state['midi_capture']['outstanding'])
    c.results.append(dict(kind='native-grid-lifecycle-midi-range',
        notes=[note['bytes'] for note in notes], onset_seconds=actual,
        expected_seconds=expected, tolerance_seconds=tolerance, passed=True))

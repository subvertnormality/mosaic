"""Live recording while a page key is held (suspected defect S32, human decision
2026-09-11: "record normally when the held key is not a step").

README 239: "When record mode is active, any notes played on a MIDI keyboard will be
captured as note masks on the currently selected channel. This includes note lengths
... quantised to align with the current step". README 316: "Holding the selected page
button does not trigger panic, and releasing a panic hold does not change pages", so
holding the channel editor's own page key (3,8) is an ordinary, inert grid hold.

Channel 1 plays C D E F over steps 1-4 at 90 BPM (a sixteenth is 1/6 s). With record
armed and the page key held, key 72 is pressed 50 ms into step 1 of the next loop and
released 500 ms later. Step 1 must replay 72 at the recorded velocity with a 0.5 s length.
"""


def recorded_note_page_key_held(c):
    c.configure(); c.tap(2, 8)                          # arm recording through the grid
    marker = c.snapshot()['midi_count']; c.tap(1, 8)
    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    state = c.wait(lambda state: any(m['index'] > marker and m['port'] == 1 and m['bytes'] == [144, 60, 127] for m in state['midi']))
    anchor = next(m[field] for m in state['midi'] if m['index'] > marker and m['port'] == 1 and m['bytes'] == [144, 60, 127])
    origin = anchor + 666666667 + 50000000              # 50 ms into step 1 of the next loop
    events = [dict(port=1, bytes=data, **{'at_' + field: origin + offset}) for offset, data in ((0, [144, 72, 90]), (500000000, [128, 72, 0]))]
    request = dict(type='midi_schedule', schedule_id=1, events=events)
    if controlled: request['time_domain'] = 'logical'
    c.action(type='grid', x=3, y=8, state=1)            # hold the selected page key
    try:
        c.action(**request)
        if controlled: c.elapse((origin + 510000000 - c.logical_ns) / 1e9)
        else: c.wait(lambda state: len(state['midi_input_schedule']['delivered']) == len(events), timeout=3)
    finally:
        c.action(type='grid', x=3, y=8, state=0)
    state = c.snapshot()
    c.results.append(dict(kind='scheduled-note-with-page-key-held', events=events, delivered=state['midi_input_schedule']['delivered']))
    c.tap(2, 8)                                         # disarm after the release
    c.tap(1, 8); c.wait(lambda state: not state['midi_capture']['outstanding'])
    marker = c.snapshot()['midi_count']; c.tap(1, 8)
    def notes(state): return [m for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    phrase = [(72, 90), (62, 117), (64, 107), (65, 97)]
    state = c.wait(lambda state: len(notes(state)) >= 3 * len(phrase) + 1, timeout=5)
    rows = notes(state)
    expected = [(1, [144, *phrase[i % len(phrase)]]) for i in range(len(rows))]
    actual = [(m['port'], m['bytes']) for m in rows]
    c.results.append(dict(kind='page-key-held-replay', expected=expected, actual=actual))
    # README 239: the note is captured as a note mask on the current step (step 1).
    assert actual == expected, dict(expected=expected, actual=actual)
    durations = []
    for note in [m for m in rows[:3 * len(phrase)] if m['bytes'][1] == 72]:
        off = next(m for m in state['midi'] if m['index'] > note['index'] and m['port'] == 1 and m['bytes'][:2] == [128, 72])
        durations.append((off[field] - note[field]) / 1e9)
    tolerance = 2e-9 if controlled else .01
    c.results.append(dict(kind='page-key-held-length', expected=.5, actual=durations))
    # README 239: the note length is captured (0.5 s held -> three sixteenths).
    assert len(durations) == 3 and all(abs(value - .5) <= tolerance for value in durations), dict(expected=.5, durations=durations)
    c.tap(1, 8); c.wait(lambda state: not state['midi_capture']['outstanding'])

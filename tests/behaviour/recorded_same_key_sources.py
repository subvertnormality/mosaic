"""The same key held from two MIDI inputs while recording (suspected defects S9 and S38,
human decision 2026-09-11: fix, reproduce with two MIDI inputs first).

README 239: "A recorded chord has one shared note length, measured from the first key
press to the final key release and quantised to the nearest supported note length. This
applies even when the chord keys are pressed or released at different times."

Channel 1 plays C D E F over steps 1-4 at 90 BPM (a sixteenth is 1/6 s). With record
armed, two keyboards on input ports 1 and 2 both press key 72 on step 1 of the next loop.
- 'held' (S9): port 1 releases after 200 ms, port 2 after 500 ms. The chord is held until
  the final release, so step 1 records 72 with a length of 0.5 s (three sixteenths).
- 'joined' (S38): port 1 releases 72 at 40 ms while port 2 still holds it; key 76 is then
  pressed on port 1 at 60 ms, still within step 1, so it joins the held chord. Port 2
  releases 72 at 300 ms and 76 is released last at 500 ms: the chord is 72 with a 76
  voice, sharing the first-press to final-release length of 0.5 s.
Recording stays armed until after the final release; it is then disarmed so the replay
records nothing new.
"""

SCENARIOS = {
    # offset ns, port, bytes
    'held': [(0, 1, [144, 72, 90]), (40000000, 2, [144, 72, 80]),
             (200000000, 1, [128, 72, 0]), (500000000, 2, [128, 72, 0])],
    'joined': [(0, 1, [144, 72, 90]), (20000000, 2, [144, 72, 80]), (40000000, 1, [128, 72, 0]),
               (60000000, 1, [144, 76, 85]), (300000000, 2, [128, 72, 0]), (500000000, 1, [128, 76, 0])],
}
REPLAY = {
    'held': [(72, 90), (62, 117), (64, 107), (65, 97)],
    'joined': [(72, 90), (76, 90), (62, 117), (64, 107), (65, 97)],
}


def recorded_same_key_sources(c, scenario):
    c.configure(); c.tap(2, 8)                          # arm recording through the grid
    marker = c.snapshot()['midi_count']; c.tap(1, 8)
    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    state = c.wait(lambda state: any(m['index'] > marker and m['port'] == 1 and m['bytes'] == [144, 60, 127] for m in state['midi']))
    anchor = next(m[field] for m in state['midi'] if m['index'] > marker and m['port'] == 1 and m['bytes'] == [144, 60, 127])
    # The next four-step loop starts 2/3 s after the observed first onset; enter 50 ms into step 1.
    origin = anchor + 666666667 + 50000000
    packets = SCENARIOS[scenario]
    events = [dict(port=port, bytes=data, **{'at_' + field: origin + offset}) for offset, port, data in packets]
    request = dict(type='midi_schedule', schedule_id=1, events=events)
    if controlled: request['time_domain'] = 'logical'
    c.action(**request)
    if controlled: c.elapse((origin + 510000000 - c.logical_ns) / 1e9)
    else: c.wait(lambda state: len(state['midi_input_schedule']['delivered']) == len(events), timeout=2)
    state = c.snapshot()
    c.tap(2, 8)                                         # disarm after the final release
    c.results.append(dict(kind='scheduled-same-key-sources', scenario=scenario, events=events, delivered=state['midi_input_schedule']['delivered']))
    c.tap(1, 8); c.wait(lambda state: not state['midi_capture']['outstanding'])
    marker = c.snapshot()['midi_count']; c.tap(1, 8)
    def notes(state): return [m for m in state['midi'] if m['index'] > marker and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    phrase = REPLAY[scenario]
    state = c.wait(lambda state: len(notes(state)) >= 3 * len(phrase) + 1, timeout=5)
    rows = notes(state)
    expected = [(1, [144, *phrase[i % len(phrase)]]) for i in range(len(rows))]
    actual = [(m['port'], m['bytes']) for m in rows]
    c.results.append(dict(kind='same-key-sources-replay', scenario=scenario, expected=expected, actual=actual))
    # README 239: every key of the chord is recorded on the step active at its note-on.
    assert actual == expected, dict(scenario=scenario, expected=expected, actual=actual)
    durations = []
    for note in [m for m in rows[:3 * len(phrase)] if m['bytes'][1] in (72, 76)]:   # three complete loops
        off = next(m for m in state['midi'] if m['index'] > note['index'] and m['port'] == 1 and m['bytes'][:2] == [128, note['bytes'][1]])
        durations.append((off[field] - note[field]) / 1e9)
    tolerance = 2e-9 if controlled else .01
    c.results.append(dict(kind='same-key-sources-length', scenario=scenario, expected=.5, actual=durations))
    # README 239: one shared length from the first key press to the final key release (0.5 s).
    assert durations and all(abs(value - .5) <= tolerance for value in durations), dict(scenario=scenario, expected=.5, durations=durations)
    c.tap(1, 8); c.wait(lambda state: not state['midi_capture']['outstanding'])

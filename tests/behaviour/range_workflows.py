"""UI-independent accepted range and global-length workflows."""


def offset_range_clipping(c):
    from cases import assert_durations
    ui = c.ui
    ui.configure(); ui.set_range(2, 4); ui.song_editor()
    ui.tap_control('global_pattern_length', 2); ui.tap_control('global_pattern_length', 8); ui.menu('channel_editor')
    ui.expect_leds({('step', 1): 'dark', ('step', 2): 'selected',
                    ('step', 3): 'selected', ('step', 4): 'dark'})
    notes = c.playback([(1, [144, 62, 117]), (1, [144, 64, 107])], cycles=3, timeout=4)
    assert_durations(c, notes, [1] * 6)
    field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
    tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
    for i, note in enumerate(notes):
        assert abs((note[field] - notes[0][field]) / 1e9 - i / 6) <= tolerance
    c.results.append(dict(kind='offset-channel-global-cap', start=2, end=4,
                          global_length=2, passed=True))


def offset_range_rates(c):
    from cases import assert_durations
    ui = c.ui
    ui.configure(); ui.set_range(2, 4); ui.song_editor()
    ui.tap_control('global_pattern_length', 2); ui.tap_control('global_pattern_length', 8); ui.menu('channel_editor')
    ui.turn(1, -1); selected = 13
    for index, label, factor in [(8, 'x3', 1 / 3), (10, 'x2', .5),
                                 (13, '/1', 1), (15, '/2', 2), (17, '/3', 3)]:
        ui.turn(3, selected - index); ui.press_key(3); selected = index
        notes = c.playback([(1, [144, 62, 117]), (1, [144, 64, 107])],
                           cycles=10, timeout=12)
        assert_durations(c, notes, [factor] * 18)
        field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
        tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
        for i, note in enumerate(notes):
            assert abs((note[field] - notes[0][field]) / 1e9 - i * factor / 6) <= tolerance
        c.results.append(dict(kind='offset-global-range-clock-rate', label=label,
                              completed_loops=10, passed=True))


LIVE_ONSET_NS = 1e9 / 6
LIVE_EDIT_MARGIN_NS = 10_000_000
LIVE_PLAY_LEAD_NS = 250_000_000


def live_range_edit_real_time(c, label, after, start, end, schedule_ids):
    """Place Play and the range gesture as one native schedule, then decide it.

    Real time cannot place the edit by observing onset ``after`` and replying:
    the onset gap is 166.7 ms and the native input schedule needs 100 ms of
    admission lead, so observe latency alone can push the edit past onset
    ``after + 1``. Instead Play and the same four gesture edges (press start,
    press end, release end, release start) are delivered by the native
    scheduler at fixed times, the gesture centred in the intended gap. The
    placement is then DECIDED from native timestamps only: every gesture
    callback must complete strictly more than 10 ms after onset ``after`` and
    more than 10 ms before onset ``after + 1``. An undecided placement is
    stopped and re-placed, corrected by its measured error (at most three
    attempts, all recorded); a decided placement returns for the unchanged
    musical oracle, so wrong musical output fails at once.
    """
    import time
    ui = c.ui
    attempts = []; lead_ns = 0
    try:
        for attempt in range(1, 4):
            ui.set_range(1, 4)
            marker = c.snapshot()['midi_count']
            def emitted(state, marker=marker):
                return [m for m in state['midi'] if m['index'] > marker
                        and 144 <= m['bytes'][0] <= 159 and m['bytes'][2] > 0]
            play_at = time.monotonic_ns() + LIVE_PLAY_LEAD_NS
            centre = play_at + 1_000_000 + round((after - .5) * LIVE_ONSET_NS) + lead_ns
            events = [(play_at, 'play_stop', None, 1),
                      (play_at + 1_000_000, 'play_stop', None, 0),
                      (centre - 3_000_000, 'step', start, 1),
                      (centre - 1_000_000, 'step', end, 1),
                      (centre + 1_000_000, 'step', end, 0),
                      (centre + 3_000_000, 'step', start, 0)]
            schedule_id = next(schedule_ids)
            ack = ui.grid_events_at(events, schedule_id=schedule_id)
            row = dict(attempt=attempt, schedule_id=schedule_id, ack_status=(ack or {}).get('status'),
                       planned_ns=[event[0] for event in events], lead_ns=lead_ns, decided=False)
            attempts.append(row)
            def settled(state):
                record = state.get('native_input_schedule') or {}
                return record.get('schedule_id') == schedule_id and record.get('status') != 'accepted'
            record = c.wait(settled, 3)['native_input_schedule']
            row['schedule_status'] = record.get('status')
            assert record.get('status') == 'completed', dict(label=label, schedule=record)
            notes = emitted(c.wait(lambda state: len(emitted(state)) >= after + 1, 3))
            reference, following = notes[after - 1].get('monotonic_ns'), notes[after].get('monotonic_ns')
            delivered = {item.get('index'): item.get('callback_completed_monotonic_ns')
                         for item in record.get('delivered') or []}
            applied = [delivered.get(index) for index in range(2, 6)]
            row.update(play_callback_completed_ns=[delivered.get(0), delivered.get(1)],
                       edit_callback_completed_ns=applied, reference_onset=after,
                       reference_onset_ns=reference, next_onset_ns=following,
                       margin_ns=LIVE_EDIT_MARGIN_NS)
            complete = all(isinstance(value, int) for value in applied + [reference, following])
            if complete:
                row.update(after_reference_ns=min(applied) - reference,
                           before_next_ns=following - max(applied))
                row['decided'] = (applied == sorted(applied)
                                  and row['after_reference_ns'] > LIVE_EDIT_MARGIN_NS
                                  and row['before_next_ns'] > LIVE_EDIT_MARGIN_NS)
            if row['decided']:
                return emitted, attempts
            ui.stop(); c.wait(lambda state: not state['midi_capture']['outstanding'])
            if complete:
                lead_ns += (reference + following) // 2 - (min(applied) + max(applied)) // 2
        raise AssertionError(dict(
            label=label, attempts=attempts,
            reason='Three live range placements lacked native evidence of an edit '
                   'more than 10 ms inside the intended onset gap'))
    except BaseException:
        c.results.append(dict(kind='accepted-live-range-transition', relation=label,
                              range=[start, end], after_step=after, passed=False,
                              placement_attempts=attempts))
        raise


def accepted_live_range_transitions(c):
    from cases import assert_durations
    import itertools
    ui = c.ui
    ui.configure()
    phrase = [(60, 127), (62, 117), (64, 107), (65, 97)]
    scenarios = [('inside', 2, 2, 4, [3, 4, 2]),
                 ('below', 1, 3, 4, [3, 4]),
                 ('above', 4, 1, 2, [1, 2])]
    schedule_ids = itertools.count(1)
    for label, after, start, end, tail in scenarios:
        attempts = None
        if c.clock_mode == 'real-time':
            emitted, attempts = live_range_edit_real_time(c, label, after, start, end, schedule_ids)
        else:
            ui.set_range(1, 4)
            marker = c.snapshot()['midi_count']; ui.play()
            def emitted(state):
                return [m for m in state['midi'] if m['index'] > marker
                        and 144 <= m['bytes'][0] <= 159 and m['bytes'][2] > 0]
            before = c.wait(lambda state: len(emitted(state)) >= after)
            assert len(emitted(before)) == after, 'Fixture missed its intended pre-edit onset'
            ui.gesture([('step', start), ('step', end)],
                       [('step', end), ('step', start)])
            assert len(emitted(c.snapshot())) == after, \
                'Fixture edit crossed an onset before its release; retain evidence'
        try:
            count = after + len(tail) * 3 + 1
            state = c.wait(lambda state: len(emitted(state)) >= count, 5); notes = emitted(state)
            steps = list(range(1, after + 1)) + [tail[i % len(tail)] for i in range(len(notes) - after)]
            expected = [(1, [144, *phrase[step - 1]]) for step in steps]
            actual = [(m['port'], m['bytes']) for m in notes]
            assert actual == expected, dict(label=label, expected=expected, actual=actual)
            field = 'logical_ns' if c.clock_mode == 'controlled-experimental' else 'monotonic_ns'
            tolerance = 2e-9 if c.clock_mode == 'controlled-experimental' else .01
            for i, note in enumerate(notes):
                assert abs((note[field] - notes[0][field]) / 1e9 - i / 6) <= tolerance
            ui.stop(); c.wait(lambda state: not state['midi_capture']['outstanding'])
            assert_durations(c, notes, [1] * (count - 1))
            ui.expect_leds({('step', i): ('selected' if start <= i <= end else 'dark')
                            for i in range(1, 65)})
        except BaseException:
            # A decided real-time placement is final: record its evidence, then fail.
            if attempts is not None:
                c.results.append(dict(kind='accepted-live-range-transition', relation=label,
                                      range=[start, end], after_step=after, passed=False,
                                      placement_attempts=attempts))
            raise
        record = dict(kind='accepted-live-range-transition', relation=label,
                      range=[start, end], after_step=after,
                      expected_steps=steps, passed=True)
        if attempts is not None:
            record['placement_attempts'] = attempts
        c.results.append(record)

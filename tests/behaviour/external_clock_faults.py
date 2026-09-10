"""Mosaic follows degraded external clocks without losing musical event identity."""
TICK_NS = 25_000_000


def _offsets(kind):
    if kind == 'jitter':
        intervals = [TICK_NS + (5_000_000 if index % 2 == 0 else -5_000_000)
                     for index in range(42)]
        tolerance = 5_000_002
    elif kind == 'missing':
        return ([value for index, value in enumerate(range(0, 44 * TICK_NS, TICK_NS)) if index != 7], 2)
    elif kind == 'extra':
        return (sorted(list(range(0, 42 * TICK_NS, TICK_NS)) + [7 * TICK_NS + TICK_NS // 2]),
                2_000_002)
    elif kind == 'step':
        intervals = [TICK_NS] * 18 + [16_666_667] * 24
        tolerance = 3_000_002
    elif kind == 'drift':
        intervals = [round(TICK_NS - index * (TICK_NS - 16_666_667) / 41)
                     for index in range(42)]
        tolerance = 3_000_000
    else:
        raise ValueError('Unknown external-clock fault: ' + kind)
    offsets = [0]
    for interval in intervals:
        offsets.append(offsets[-1] + interval)
    return offsets, tolerance


def _configure_midi_source(c):
    from cases import menu_label, menu_value
    c.configure(); c.key(1); c.enc(1, 4); c.key(3); menu_label(c, 'LEVELS >')
    position = next(index for index, value in enumerate(c.snapshot()['diagnostics']['parameter_roots'])
                    if value['name'] == 'CLOCK')
    c.enc(2, position); c.key(3); menu_label(c, 'source'); menu_value(c, 'internal')
    c.enc(3, 1); menu_value(c, 'midi')
    # Native norns defaults clock input to all connected devices. Select vport1
    # explicitly so the port2 prelude is a meaningful routing negative.
    # The long selected label scrolls horizontally in the native menu, so the
    # stable proof of this setting is its routing effect below, not OCR text.
    c.enc(2, 11); c.enc(3, 2)


def _assert_notes(events, field, onsets, releases, tolerance_ns,
                  causal_releases=None, transport_tolerance_ns=None):
    causal_releases = causal_releases or {}
    transport_tolerance_ns = tolerance_ns if transport_tolerance_ns is None else transport_tolerance_ns
    note_events = [event for event in events if (event['bytes'][0] & 240) in (128, 144)]
    active = {}; onset_index = 0; release_index = 0; previous_index = -1
    for event in note_events:
        assert event['index'] > previous_index, ('Reordered MIDI event', event)
        previous_index = event['index']
        data = event['bytes']; key = (data[0] & 15, data[1])
        if data[0] & 240 == 144 and data[2] > 0:
            assert onset_index < len(onsets), ('Extra onset', event)
            target, pitch, velocity = onsets[onset_index]
            assert not active, ('Prior voice not released before onset', onset_index, active, event)
            assert event['port'] == 1 and data == [144, pitch, velocity], ('Wrong onset', onset_index, event)
            assert abs(event[field] - target) <= tolerance_ns, ('Onset phase', onset_index, event[field] - target)
            assert key not in active, ('Overlapping same-pitch voice', onset_index, event)
            active[key] = (event, onset_index)
            onset_index += 1
        else:
            assert event['port'] == 1 and key in active, ('Extra or wrong-pitch release', event)
            onset, owner = active.pop(key)
            target = releases[owner]
            allowance = transport_tolerance_ns if owner in causal_releases else tolerance_ns
            assert abs(event[field] - target) <= allowance, ('Release phase', owner, event[field] - target)
            assert event[field] >= onset[field], ('Release preceded owned onset', owner, event)
            if owner in causal_releases:
                assert event[field] >= causal_releases[owner], ('Transport release preceded input', owner, event)
            assert data[2] == onset['bytes'][2] or data[2] == 0, ('Release velocity', owner, event)
            release_index += 1
    assert onset_index == len(onsets), ('Missing onset', onset_index, len(onsets))
    assert release_index == len(onsets) and not active, ('Unbalanced notes', release_index, active)
    return dict(onsets=onset_index, releases=release_index,
                maximum_onset_error_ns=max(abs(event[field] - target)
                    for event, (target, _, _) in zip(
                        [e for e in note_events if e['bytes'][0] & 240 == 144 and e['bytes'][2] > 0], onsets)))


def _actual_delivery(delivered, data, intended_ns, domain):
    intended_key = 'intended_' + domain + '_ns'
    actual_key = 'actual_' + domain + '_ns'
    matches = [event for event in delivered
               if event['bytes'] == data and event[intended_key] == intended_ns]
    assert len(matches) == 1, ('Missing or ambiguous delivered MIDI input', data, intended_ns, matches)
    return matches[0][actual_key]


def _schedule(c, events, schedule_id, timeout):
    from midi_window import MidiWindow
    controlled = c.clock_mode == 'controlled-experimental'
    capture = MidiWindow(c.snapshot()['midi_count'])
    request = dict(type='midi_schedule', schedule_id=schedule_id, events=events)
    if controlled: request['time_domain'] = 'logical'
    c.action(**request)
    state = c.wait(lambda state: capture.extend(state) and
                   len(state['midi_input_schedule']['delivered']) == len(events), timeout=timeout)
    c.wait(lambda state: capture.extend(state) and not state['midi_capture']['outstanding'])
    return capture, state


def external_clock_fault(c, kind):
    import time
    _configure_midi_source(c)
    controlled = c.clock_mode == 'controlled-experimental'
    domain = 'logical' if controlled else 'monotonic'; key = 'at_' + domain + '_ns'
    offsets, fault_tolerance = _offsets(kind)
    now = c.logical_ns if controlled else time.monotonic_ns()
    origin = now + 1_750_000_000
    warm_origin = origin - 1_250_000_000
    events = [dict(port=1, bytes=[248], **{key: warm_origin + index * TICK_NS})
              for index in range(1, 50)]
    # Transport bytes on a clock-disabled port cannot start Mosaic.
    events += [dict(port=2, bytes=[250], **{key: origin - 20_000_000}),
               dict(port=2, bytes=[248], **{key: origin - 10_000_000})]
    events += [dict(port=1, bytes=[250], **{key: origin})]
    events += [dict(port=1, bytes=[248], **{key: origin + offset}) for offset in offsets]
    stop = origin + offsets[-1] + 12_500_000
    events += [dict(port=1, bytes=[252], **{key: stop})]
    tail_interval = offsets[-1] - offsets[-2]
    events += [dict(port=1, bytes=[248], **{key: stop + index * tail_interval})
               for index in range(1, 13)]
    events.sort(key=lambda event: (event[key], 0 if event['bytes'] == [250] else 1))
    capture, state = _schedule(c, events, 400 + ('jitter','missing','extra','step','drift').index(kind), 6)
    field = domain + '_ns'; tolerance = fault_tolerance + (0 if controlled else 10_000_000)
    targets = [origin + offsets[6 * index] for index in range(8)]
    pitches = (60, 62, 64, 65); velocities = (127, 117, 107, 97)
    onsets = [(target, pitches[index % 4], velocities[index % 4]) for index, target in enumerate(targets)]
    releases = targets[1:] + [stop]
    transport_tolerance = 2 if controlled else 10_000_000
    actual_stop = _actual_delivery(state['midi_input_schedule']['delivered'], [252], stop, domain)
    accounting = _assert_notes(capture.events, field, onsets, releases, tolerance,
                               causal_releases={7: actual_stop}, transport_tolerance_ns=transport_tolerance)
    assert not any(event['port'] == 1 and event['bytes'][0] & 240 == 144 and event['bytes'][2] > 0 and
                   event[field] < origin for event in capture.events), 'Disabled input port started Mosaic'
    assert state['midi_capture']['outstanding'] == []
    c.results.append(dict(kind='external-clock-fault', fault=kind, pulse_count=len(offsets),
                          target_ns=targets, tolerance_ns=tolerance, post_stop_clock_pulses=12,
                          stimulus=events, delivered=state['midi_input_schedule']['delivered'],
                          actual_stop_ns=actual_stop, passed=True, **accounting))


def external_clock_explicit_recovery(c):
    import time
    _configure_midi_source(c)
    controlled = c.clock_mode == 'controlled-experimental'
    domain = 'logical' if controlled else 'monotonic'; key = 'at_' + domain + '_ns'
    now = c.logical_ns if controlled else time.monotonic_ns()
    first = now + 1_750_000_000; warm_origin = first - 1_250_000_000
    recovery = first + 825_000_000
    events = [dict(port=1, bytes=[248], **{key: warm_origin + index * TICK_NS}) for index in range(1, 50)]
    events += [dict(port=1, bytes=[250], **{key: first})]
    events += [dict(port=1, bytes=[248], **{key: first + index * TICK_NS}) for index in range(13)]
    events += [dict(port=1, bytes=[250], **{key: recovery})]
    events += [dict(port=1, bytes=[248], **{key: recovery + index * TICK_NS}) for index in range(43)]
    stop = recovery + 42 * TICK_NS + 12_500_000
    events += [dict(port=1, bytes=[252], **{key: stop})]
    events += [dict(port=1, bytes=[248], **{key: stop + index * TICK_NS}) for index in range(1, 13)]
    events.sort(key=lambda event: (event[key], 0 if event['bytes'] == [250] else 1))
    capture, state = _schedule(c, events, 406, 7)
    field = domain + '_ns'; tolerance = 2 if controlled else 10_000_000
    first_targets = [first + index * 150_000_000 for index in range(6)]
    recovery_targets = [recovery + index * 150_000_000 for index in range(8)]
    pitches = (60, 62, 64, 65); velocities = (127, 117, 107, 97)
    onsets = [(target, pitches[index % 4], velocities[index % 4])
              for index, target in enumerate(first_targets)]
    onsets += [(target, pitches[index % 4], velocities[index % 4])
               for index, target in enumerate(recovery_targets)]
    releases = first_targets[1:] + [recovery] + recovery_targets[1:] + [stop]
    delivered = state['midi_input_schedule']['delivered']
    actual_recovery_clock = _actual_delivery(delivered, [248], recovery, domain)
    actual_stop = _actual_delivery(delivered, [252], stop, domain)
    accounting = _assert_notes(capture.events, field, onsets, releases, tolerance,
                               causal_releases={5: actual_recovery_clock, 13: actual_stop},
                               transport_tolerance_ns=tolerance)
    assert state['midi_capture']['outstanding'] == []
    c.results.append(dict(kind='external-clock-explicit-recovery', holdover_onsets=len(first_targets),
                          restarted_onsets=len(recovery_targets), restart_ns=recovery,
                          tolerance_ns=tolerance, post_stop_clock_pulses=12, stimulus=events,
                          delivered=delivered, actual_recovery_clock_ns=actual_recovery_clock,
                          actual_stop_ns=actual_stop, passed=True, **accounting))

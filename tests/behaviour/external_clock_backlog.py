"""External MIDI Stop must preempt stale musical work after runtime overload."""
import time

from external_clock_faults import TICK_NS, _actual_delivery, _schedule


def _configure_raw(c):
    # Raw primitive copy of 4108035 Driver.configure (pre-semantic UI layer).
    c.tap(3,8);c.enc(1,4);c.enc(3,1);c.key(3);c.tap(5,8)
    for x in range(1,5):c.tap(x,4)
    c.tap(5,8)
    for x,y in ((1,7),(2,6),(3,5),(4,4)):c.tap(x,y)
    c.tap(5,8)
    for x,y in ((1,1),(2,2),(3,3),(4,4)):c.tap(x,y)
    c.tap(3,8);c.tap(1,2);c.hold_tap((1,4),(4,4))
    c.led_values([(1,2)],[15]);c.screen_header('Ch. 1 Device Config')


def _menu_label_raw(c, text, x=0):
    from frame_oracle import selected_line
    c.wait(lambda s: selected_line(s, text, x)); c.results.append(dict(kind='selected-menu-label', text=text))


def _menu_value_raw(c, text):
    from frame_oracle import selected_value
    c.wait(lambda s: selected_value(s, text)); c.results.append(dict(kind='selected-menu-value', text=text))


def _configure_midi_source_raw(c):
    # Raw primitive copy of 4108035 external_clock_faults._configure_midi_source.
    _configure_raw(c); c.key(1); c.enc(1, 4); c.key(3); _menu_label_raw(c, 'LEVELS >')
    position = next(index for index, value in enumerate(c.snapshot()['diagnostics']['parameter_roots'])
                    if value['name'] == 'CLOCK')
    c.enc(2, position); c.key(3); _menu_label_raw(c, 'source'); _menu_value_raw(c, 'internal')
    c.enc(3, 1); _menu_value_raw(c, 'midi')
    # Native norns defaults clock input to all connected devices. Select vport1
    # explicitly so the port2 prelude is a meaningful routing negative.
    # The long selected label scrolls horizontally in the native menu, so the
    # stable proof of this setting is its routing effect below, not OCR text.
    c.enc(2, 11); c.enc(3, 2)


def external_clock_runtime_backlog(c):
    # A wall-clock stall models the constrained norns Lua event thread. Controlled
    # time deliberately has no wall-clock execution cost, so this case is real-time only.
    assert c.clock_mode == 'real-time', 'Runtime backlog is a real-time-only boundary'
    _configure_midi_source_raw(c)
    now = time.monotonic_ns()
    origin = now + 1_750_000_000
    warm_origin = origin - 1_250_000_000
    interval = 8_333_333  # 300 BPM at MIDI's 24 PPQN.
    events = [dict(port=1, bytes=[248], at_monotonic_ns=warm_origin + index * TICK_NS)
              for index in range(1, 50)]
    events.append(dict(port=1, bytes=[250], at_monotonic_ns=origin))
    events.extend(dict(port=1, bytes=[248], at_monotonic_ns=origin + index * interval)
                  for index in range(1, 133))
    stop = origin + 900_000_000
    events.append(dict(port=1, bytes=[252], at_monotonic_ns=stop))
    events.extend(dict(port=1, bytes=[248], at_monotonic_ns=stop + index * interval)
                  for index in range(1, 13))
    events.sort(key=lambda event: (event['at_monotonic_ns'],
                                   0 if event['bytes'] == [250] else 1))

    # Schedule first so the independent native MIDI thread owns every deadline.
    from midi_window import MidiWindow
    capture = MidiWindow(c.snapshot()['midi_count'])
    c.action(type='midi_schedule', schedule_id=423, events=events)
    stall_at = origin + 100_000_000
    time.sleep(max(0, (stall_at - time.monotonic_ns()) / 1e9))
    stall_before = time.monotonic_ns()
    stall_ack = c.action(type='runtime_stall', milliseconds=1000)
    stall_after = time.monotonic_ns()
    state = c.wait(lambda value: capture.extend(value) and
                   len(value['midi_input_schedule']['delivered']) == len(events), timeout=5)
    state = c.wait(lambda value: capture.extend(value) and
                   not value['midi_capture']['outstanding'], timeout=5)
    delivered = state['midi_input_schedule']['delivered']
    actual_stop = _actual_delivery(delivered, [252], stop, 'monotonic')
    stop_error = abs(actual_stop - stop)
    assert stop_error <= 15_000_000, ('Native Stop missed its deadline', stop_error)
    assert stall_before < actual_stop < stall_after, (stall_before, actual_stop, stall_after)
    post_stop_onsets = [event for event in capture.events
                        if event['port'] == 1 and event['bytes'][0] & 240 == 144 and
                        event['bytes'][2] > 0 and event['monotonic_ns'] > actual_stop]
    assert post_stop_onsets == [], ('Stale note burst emitted after external Stop', post_stop_onsets)
    assert state['midi_capture']['outstanding'] == [], state['midi_capture']['outstanding']
    c.results.append(dict(kind='external-clock-runtime-backlog', input_bpm=300,
                          stall_ms=1000, clocks_during_stall=120,
                          actual_stop_ns=actual_stop, stop_deadline_error_ns=stop_error,
                          stop_deadline_tolerance_ns=15_000_000, stall_before_ns=stall_before,
                          stall_after_ns=stall_after, native_ack=stall_ack['native'],
                          post_stop_onsets=post_stop_onsets, passed=True,
                          oracle='README external MIDI transport Stop plus characterization: no stale post-Stop note burst'))

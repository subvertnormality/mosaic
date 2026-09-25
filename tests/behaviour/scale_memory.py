"""Scale, pattern, channel and memory cases using the semantic UI layer."""


def scale_edit_selection(c):
    ui = c.ui

    def selected(slot, applied):
        ui.expect_scale_slot_header(slot)
        c.results.append(dict(kind="scale-edit-header", slot=slot))
        ui.expect_leds({
            ("scale_slot", number): (
                "selected" if number == applied else
                "blink_low" if number == slot else "off"
            )
            for number in range(1, 17)
        })

    def phrase(pitches):
        c.playback([(1, [144, pitch, velocity])
                    for pitch, velocity in zip(pitches, [127, 117, 107, 97])])

    def shift_slot(slot):
        with ui.hold_keys(1):
            c.elapse(.3)  # Native K1 hold threshold is 250 ms before dispatch.
            ui.tap_control("scale_slot", slot)

    def long_slot(slot):
        with ui.hold_control("scale_slot", slot):
            c.elapse(1.1)
        c.elapse(.06)

    ui.configure()
    ui.tap_control("scale_editor")
    selected(1, 1)
    shift_slot(2)
    selected(2, 1)
    # Root C -> D, saved through E2/E3/K3. Editing an unused scale must not
    # change playback: the applied C-major scale still governs these notes.
    ui.turn(2, -1)
    ui.turn(3, 2)
    ui.press_key(3)
    selected(2, 1)
    phrase([60, 62, 64, 65])
    ui.tap_control("scale_slot", 2)
    selected(2, 2)
    phrase([62, 64, 66, 67])
    # Long-selecting a different editor retains the D-major applied scale.
    long_slot(3)
    selected(3, 2)
    phrase([62, 64, 66, 67])
    # Saving an already applied scale does alter playback, even when selected
    # through the edit-only gesture. D -> E remains a major scale.
    shift_slot(2)
    selected(2, 2)
    ui.turn(3, 2)
    ui.press_key(3)
    phrase([64, 66, 68, 69])
    # Select another editing slot, then long-press it again. Global off must
    # restore chromatic relative intervals and clear the editor indicator.
    long_slot(3)
    selected(3, 2)
    long_slot(3)
    selected(0, 0)
    phrase([60, 61, 62, 63])
    # State can be re-entered following global off; stored scale edits persist.
    ui.tap_control("scale_slot", 2)
    selected(2, 2)
    phrase([64, 66, 68, 69])


def scale_lock_lifetime(c):
    ui = c.ui

    def phrase(pitches):
        c.playback([(1, [144, pitch, velocity])
                    for pitch, velocity in zip(pitches, [127, 117, 107, 97])])

    def edit_slot(slot, semitones):
        with ui.hold_keys(1):
            c.elapse(.3)  # Native K1 hold threshold is 250 ms before dispatch.
            ui.tap_control("scale_slot", slot)
        ui.turn(3, semitones)
        ui.press_key(3)

    ui.configure()
    ui.tap_control("scale_editor")
    ui.turn(2, -1)
    edit_slot(2, 2)
    edit_slot(3, 4)  # Unused D-major and E-major scales.
    # Global D lock at step 1; channel E lock at step 2. Four-step channel
    # length wraps repeatedly inside the independent 64-step global scale track.
    ui.hold_control_tap("step", "scale_slot", 1, 2)
    ui.tap_control("channel_editor")
    ui.hold_control_tap("step", "channel_scale_slot", 2, 3)
    phrase([62, 66, 68, 69])
    # Native menu navigation keeps the selected row and option observations.
    ui.press_key(1)
    ui.turn(1, 4)
    ui.press_key(3)
    ui.expect_native_menu_label("levels_root")
    ui.seek_native_parameter_root("mosaic")
    ui.press_key(3)
    ui.seek_mosaic_option_from_current("scale_lock_until_pattern_end")
    ui.expect_mosaic_option_label("scale_lock_until_pattern_end")
    ui.expect_mosaic_option_value(True)
    ui.turn(3, -1)
    ui.expect_mosaic_option_value(False)
    ui.press_key(1)
    phrase([62, 66, 66, 67])
    # Remove the channel lock by repeating its physical gesture. The global D
    # lock must still apply on every channel note with channel hold disabled.
    ui.hold_control_tap("step", "channel_scale_slot", 2, 3)
    phrase([62, 64, 66, 67])
    # Remove global lock too: this restores the C-major default, proving the
    # preceding D phrase came from global persistence rather than stale state.
    ui.tap_control("scale_editor")
    ui.hold_control_tap("step", "scale_slot", 1, 2)
    ui.tap_control("channel_editor")
    phrase([60, 62, 64, 65])


def trig_merge_sets(c):
    ui = c.ui
    ui.configure()
    ui.tap_control("pattern_editor")
    ui.tap_control("pattern_editor")
    ui.tap_control("scale_slot", 4)  # Pattern 1 fourth note F -> G.
    ui.tap_control("pattern_editor")
    ui.tap_control("pattern_editor")  # Return to the trig editor.
    ui.tap_control("pattern_select", 2)
    for step in (2, 4):
        ui.tap_step(step)
    ui.tap_control("channel_editor")
    ui.tap_control("pattern_slot", 2)
    ui.hold_control_tap("note_merge_mode", "pattern_slot", None, 1)
    ui.hold_control_tap("velocity_merge_mode", "pattern_slot", None, 1)
    notes = {1: (60, 127), 2: (62, 117), 3: (64, 107), 4: (67, 97)}

    def phrase(steps):
        observed = c.playback([(1, [144, *notes[step]]) for step in steps])
        field = "logical_ns" if c.clock_mode == "controlled-experimental" else "monotonic_ns"
        errors = []
        for index, (left, right) in enumerate(zip(observed, observed[1:])):
            first = steps[index % len(steps)]
            second = steps[(index + 1) % len(steps)]
            expected = ((second - first) % 4 or 4) / 6
            errors.append((right[field] - left[field]) / 1e9 - expected)
        c.results.append(dict(kind="merge-rest-spacing", steps=steps,
                              errors_seconds=errors))
        tolerance = 2e-9 if c.clock_mode == "controlled-experimental" else .01
        assert errors and all(abs(error) <= tolerance for error in errors), errors

    def mode(level, steps):
        ui.expect_leds({("trig_merge_mode", None): {
            2: "off", 5: "in_range", 8: "medium",
        }[level]})
        phrase(steps)

    mode(2, [1, 3])  # Exactly one contributing pattern.
    ui.tap_control("trig_merge_mode")
    mode(5, [2, 4])  # Two contributors only.
    ui.tap_control("trig_merge_mode")
    mode(8, [1, 2, 3, 4])  # Set union.
    # A third pattern overlapping step 2 distinguishes exactly-one from odd
    # parity and proves Only accepts two or more contributors.
    ui.tap_control("pattern_editor")
    ui.tap_control("pattern_select", 3)
    for step in (2, 3):
        ui.tap_step(step)
    ui.tap_control("channel_editor")
    ui.tap_control("pattern_slot", 3)
    ui.tap_control("trig_merge_mode")
    mode(2, [1])
    ui.tap_control("trig_merge_mode")
    mode(5, [2, 3, 4])
    ui.tap_control("trig_merge_mode")
    mode(8, [1, 2, 3, 4])
    # With one assigned pattern there are no overlaps. Only must be silent,
    # not keep a stale merged pattern after unassignment.
    ui.tap_control("pattern_slot", 2)
    ui.tap_control("pattern_slot", 3)
    ui.tap_control("trig_merge_mode")
    ui.tap_control("trig_merge_mode")
    ui.expect_leds({("trig_merge_mode", None): "in_range"})
    before = c.snapshot()["midi_count"]
    ui.tap_control("play_stop")
    c.elapse(1.5)
    ui.tap_control("play_stop")
    state = c.snapshot()
    emitted = [message for message in state["midi"]
               if message["index"] > before and message["bytes"][0] == 144
               and message["bytes"][2] > 0]
    assert not emitted, emitted
    assert not state["midi_capture"]["outstanding"]
    c.results.append(dict(kind="only-without-overlap-silent", seconds=1.5))


def all_pattern_slots(c):
    ui = c.ui
    ui.configure()
    ui.tap_control("pattern_editor")
    for step in range(1, 5):
        ui.tap_step(step)  # Clear only the fixture's initial trigs.
    pitches = [60, 62, 64, 65, 67, 69, 71]
    authored = {}
    previous = 1
    for slot in range(1, 17):
        ui.tap_control("pattern_select", slot)
        ui.expect_steps({step: "off" for step in range(1, 65)})
        x = 1 + (slot - 1) % 4
        active = {x, 16 + slot, 48 + (17 - slot)}
        ordered = sorted(active, key=lambda step: ui.step(step))
        for step in ordered:
            ui.tap_step(step)
        ui.pattern_editor("note", from_view="trigger")
        ui.tap_control("pattern_note_degree", (x, (slot - 1) % 7))
        ui.pattern_editor("trigger", from_view="note")
        expected = {step: "selected" if step in active else "off"
                    for step in range(1, 65)}
        ui.expect_steps(expected)
        authored[slot] = expected
        ui.tap_control("channel_editor")
        if slot != previous:
            ui.tap_control("pattern_slot", previous)
            ui.tap_control("pattern_slot", slot)
        ui.expect_leds({("pattern_slot", slot): "selected"})
        # Four-step channel length excludes both deliberately authored outer
        # trigs. Exactly one pitched event per loop may reach the MIDI port.
        velocity = [127, 117, 107, 97][x - 1] if slot == 1 else 100
        notes = c.playback([(1, [144, pitches[(slot - 1) % 7], velocity])])
        field = "logical_ns" if c.clock_mode == "controlled-experimental" else "monotonic_ns"
        errors = [(right[field] - left[field]) / 1e9 - 4 / 6
                  for left, right in zip(notes, notes[1:])]
        tolerance = 2e-9 if c.clock_mode == "controlled-experimental" else .01
        assert errors and all(abs(error) <= tolerance for error in errors), errors
        c.results.append(dict(kind="pattern-slot-playback", slot=slot,
                              pitch=pitches[(slot - 1) % 7],
                              spacing_errors_seconds=errors))
        previous = slot
        ui.tap_control("pattern_editor")
    # Revisit every slot after all edits: editing slot 16 must not overwrite
    # earlier slots, even where pitches or active short-loop steps coincide.
    for slot in range(1, 17):
        ui.tap_control("pattern_select", slot)
        ui.expect_steps(authored[slot])


def scale_stop_indicator(c):
    ui = c.ui
    ui.configure()
    ui.tap_control("scale_editor")
    ui.tap_control("scale_slot", 2)
    ui.expect_leds({("scale_slot", 2): "selected"})
    c.playback([(1, [144, note, velocity])
                for note, velocity in [(60, 127), (62, 117), (64, 107), (65, 97)]])
    # Stopping transport does not disable the applied scale. The bright
    # applied indicator must survive the playing-to-stopped transition.
    ui.expect_leds({("scale_slot", 2): "selected"})
    # A held global step displays its own lock, not the stopped default.
    with ui.hold_control("step", 2):
        ui.tap_control("scale_slot", 3)
        ui.expect_leds({("scale_slot", 2): "off",
                         ("scale_slot", 3): "selected"})
    ui.expect_leds({("scale_slot", 2): "selected",
                    ("scale_slot", 3): "off"})


def channel_long_hold(c):
    ui = c.ui
    ui.configure()
    with ui.hold_control("step", 2):
        c.elapse(1.1)
    ui.expect_steps({step: "selected" for step in range(1, 5)})
    c.playback([(1, [144, note, velocity])
                for note, velocity in [(60, 127), (62, 117), (64, 107), (65, 97)]])
    with ui.hold_control("step", 2):
        c.elapse(1.1)
        ui.tap_step(4)
    ui.expect_steps({step: "dark" if step == 1 else "selected"
                     for step in range(1, 5)})
    notes = c.playback([(1, [144, note, velocity])
                        for note, velocity in [(62, 117), (64, 107), (65, 97)]])
    field = "logical_ns" if c.clock_mode == "controlled-experimental" else "monotonic_ns"
    gaps = [(right[field] - left[field]) / 1e9 for left, right in zip(notes, notes[1:])]
    c.results.append(dict(kind="range-loop-spacing", expected_seconds=1 / 6,
                          actual_seconds=gaps))
    tolerance = 2e-9 if c.clock_mode == "controlled-experimental" else .01
    assert all(abs(gap - 1 / 6) <= tolerance for gap in gaps), gaps


def adjacent_channel_ranges(c):
    ui = c.ui
    # Fill every step through the pattern editor. The first four authored
    # pitches/velocities distinguish step addressing; later steps use C/100.
    ui.configure()
    ui.tap_control("pattern_editor")
    for step in range(5, 65):
        ui.tap_step(step)
    ui.tap_control("channel_editor")
    values = [(60, 127), (62, 117), (64, 107), (65, 97)] + [(60, 100)] * 60
    # Every possible adjacent pair, including all row boundaries and step 64.
    # Ascending ranges are documented; reversed endpoints remain a separate
    # failure-mode investigation, never silently normalized by this oracle.
    for start, end in ([(step, step + 1) for step in range(1, 64)] + [(1, 64)]):
        ui.set_range(start, end)
        ui.expect_steps({step: "selected" if start <= step <= end else "dark"
                         for step in range(1, 65)})
        expected = [(1, [144, note, velocity]) for note, velocity in values[start - 1:end]]
        notes = c.playback(expected, cycles=2, timeout=(end - start + 1) / 3 + 3)
        field = "logical_ns" if c.clock_mode == "controlled-experimental" else "monotonic_ns"
        gaps = [(right[field] - left[field]) / 1e9 for left, right in zip(notes, notes[1:])]
        c.results.append(dict(kind="adjacent-range", start=start, end=end,
                              expected_gap_seconds=1 / 6, actual_gaps=gaps))
        tolerance = 2e-9 if c.clock_mode == "controlled-experimental" else .01
        assert all(abs(gap - 1 / 6) <= tolerance for gap in gaps), dict(
            start=start, end=end, gaps=gaps
        )


def channel_mute_gestures(c):
    ui = c.ui
    ui.configure()
    phrase = [(1, [144, note, velocity])
              for note, velocity in [(60, 127), (62, 117), (64, 107), (65, 97)]]

    def hold(seconds):
        with ui.hold_control("channel", 1):
            c.elapse(seconds)

    def shift_mute():
        with ui.hold_keys(1):
            c.elapse(.3)
            ui.tap_control("channel", 1)

    def silence(seconds):
        before = c.snapshot()["midi_count"]
        c.elapse(seconds)
        state = c.snapshot()
        notes = [message for message in state["midi"]
                 if message["index"] > before and 144 <= message["bytes"][0] <= 159
                 and message["bytes"][2] > 0]
        c.results.append(dict(kind="mute-silence", seconds=seconds, new_note_ons=notes))
        assert not notes, notes
        assert not state["midi_capture"]["outstanding"], "Muted phrase retained active notes"

    hold(.8)
    ui.expect_leds({("channel", 1): "selected"})
    c.playback(phrase)
    hold(1.1)
    ui.expect_leds({("channel", 1): "alternate"})
    ui.tap_control("play_stop")
    silence(1.5)
    ui.tap_control("play_stop")
    shift_mute()
    ui.expect_leds({("channel", 1): "selected"})
    c.playback(phrase)
    # Muting and unmuting during playback must leave transport running and
    # release existing notes; resumed pitches follow the unchanged phrase.
    ui.tap_control("play_stop")
    c.wait(lambda state: state["midi_capture"]["outstanding"] != [])
    hold(1.1)
    ui.expect_leds({("channel", 1): "alternate"})
    silence(1.5)
    marker = c.snapshot()["midi_count"]
    shift_mute()
    ui.expect_leds({("channel", 1): "selected"})

    def emitted(state):
        return [message for message in state["midi"]
                if message["index"] > marker and message["bytes"][0] == 144
                and message["bytes"][2] > 0]

    state = c.wait(lambda state: len(emitted(state)) >= 9)
    actual = [(message["port"], message["bytes"]) for message in emitted(state)]
    start = phrase.index(actual[0])
    expected = [phrase[(start + index) % 4] for index in range(len(actual))]
    assert actual == expected, dict(expected=expected, actual=actual)
    c.results.append(dict(kind="unmute-live-phrase", expected=expected, actual=actual))
    ui.tap_control("play_stop")
    c.wait(lambda state: not state["midi_capture"]["outstanding"])


def channel_routing_isolation(c):
    ui = c.ui
    ui.configure()
    phrase = [(60, 127), (62, 117), (64, 107), (65, 97)]
    for channel in range(2, 17):
        ui.select_channel(channel)
        ui.expect_header("midi_config", channel=channel)
        ui.turn(3, 1)  # none -> generic CC device
        ui.turn(2, 1)
        ui.turn(3, channel - 1)  # distinct MIDI channel
        ui.turn(2, 1)
        if channel % 2 == 0:
            ui.turn(3, 1)  # second virtual port
        ui.press_key(3)
        ui.tap_control("pattern_slot", 1)
        ui.set_range(1, 4)
        ui.expect_leds({("channel", channel): "selected",
                         ("pattern_slot", 1): "selected"})

    def verify(active):
        marker = c.snapshot()["midi_count"]
        ui.tap_control("play_stop")

        def ons(state):
            return [message for message in state["midi"]
                    if message["index"] > marker and 144 <= message["bytes"][0] <= 159
                    and message["bytes"][2] > 0]

        if active:
            state = c.wait(lambda state: all(
                sum(message["bytes"][0] == 143 + channel for message in ons(state)) >= 9
                for channel in active
            ), timeout=5)
        else:
            c.elapse(1.5)
            state = c.snapshot()
        notes = ons(state)
        assert {message["bytes"][0] - 143 for message in notes} == set(active), dict(
            active=active, actual=[message["bytes"] for message in notes]
        )
        traces = {}
        for channel in active:
            trace = [message for message in notes
                     if message["bytes"][0] == 143 + channel]
            actual = [(message["port"], message["bytes"]) for message in trace]
            expected = [(1 if channel % 2 else 2,
                         [143 + channel, *phrase[index % 4]])
                        for index in range(len(trace))]
            assert actual == expected, dict(channel=channel, expected=expected, actual=actual)
            field = "logical_ns" if c.clock_mode == "controlled-experimental" else "monotonic_ns"
            times = [message[field] for message in trace]
            tolerance = 2e-9 if c.clock_mode == "controlled-experimental" else .01
            assert all(abs((right - left) / 1e9 - 1 / 6) <= tolerance
                       for left, right in zip(times, times[1:])), dict(channel=channel, times=times)
            traces[channel] = times
        # Equal-rate channels must stay aligned; retain within-channel order.
        if traces:
            firsts = [times[0] for times in traces.values()]
            tolerance_ns = 2 if c.clock_mode == "controlled-experimental" else 10000000
            assert max(firsts) - min(firsts) <= tolerance_ns, firsts
        c.results.append(dict(kind="channel-routing-isolation", active_channels=active,
                              note_on_count=len(notes), times_by_channel=traces))
        ui.tap_control("play_stop")
        c.wait(lambda state: not state["midi_capture"]["outstanding"])

    def toggle(channel):
        with ui.hold_keys(1):
            c.elapse(.3)
            ui.tap_control("channel", channel)

    verify(list(range(1, 17)))
    for channel in range(1, 17):
        toggle(channel)
        ui.expect_leds({("channel", channel): "alternate" if channel == 16 else "dark"})
        verify(list(range(channel + 1, 17)))
    for channel in range(16, 0, -1):
        toggle(channel)
        ui.expect_leds({("channel", channel): "selected" if channel == 16 else "off"})
        verify(list(range(channel, 17)))


def memory_navigation(c):
    ui = c.ui
    ui.configure()
    ui.turn(1, -2)
    ui.expect_header("memory", channel=1)
    baseline = [(60, 127), (62, 117), (64, 107), (65, 97)]
    first = [(72, 90), *baseline[1:]]
    both = [(72, 90), (76, 80), *baseline[2:]]
    branch = [(72, 90), (62, 117), (79, 70), (65, 97)]

    def counter(current, total):
        ui.expect_memory_position(current, total)

    def phrase(values):
        c.playback([(1, [144, note, velocity]) for note, velocity in values], cycles=2)

    def record(step, note, velocity):
        ui.record_midi_mask_on_step(step, note, velocity)

    counter(0, 0)
    ui.press_key(2)
    ui.press_key(3)
    ui.turn(3, -3)
    ui.turn(3, 3)
    counter(0, 0)
    phrase(baseline)
    ui.turn(1, -2)
    ui.expect_header("masks", channel=1)
    record(1, 72, 90)
    record(2, 76, 80)
    ui.turn(1, 2)
    counter(2, 2)
    phrase(both)
    ui.turn(3, -1)
    counter(1, 2)
    phrase(first)
    ui.turn(3, -1)
    counter(0, 2)
    phrase(baseline)
    ui.turn(3, -3)
    counter(0, 2)
    phrase(baseline)
    ui.turn(3, 1)
    counter(1, 2)
    phrase(first)
    ui.turn(3, 1)
    counter(2, 2)
    phrase(both)
    ui.turn(3, 3)
    counter(2, 2)
    phrase(both)
    ui.press_key(2)
    counter(0, 2)
    phrase(baseline)
    ui.press_key(3)
    counter(2, 2)
    phrase(both)
    ui.turn(3, -1)
    counter(1, 2)
    ui.turn(1, -2)
    record(3, 79, 70)
    ui.turn(1, 2)
    counter(2, 2)
    phrase(branch)
    ui.press_key(3)
    counter(2, 2)
    phrase(branch)
    ui.press_key(2)
    counter(0, 2)
    phrase(baseline)
    ui.press_key(3)
    counter(2, 2)
    phrase(branch)


def memory_channel_isolation(c):
    ui = c.ui
    ui.configure()
    ui.select_channel_on_page(2,"midi_config")
    ui.turn(3, 1)
    ui.turn(2, 1)
    ui.turn(3, 1)
    ui.turn(2, 1)
    ui.turn(3, 1)
    ui.press_key(3)
    ui.tap_control("pattern_slot", 1)
    ui.set_range(1, 4)
    ui.turn(1, -4)
    baseline = [(60, 127), (62, 117), (64, 107), (65, 97)]
    edited_one = [(72, 90), *baseline[1:]]
    edited_two = [baseline[0], (79, 80), *baseline[2:]]

    def record(step, note, velocity):
        ui.record_midi_mask_on_step(step, note, velocity)

    def history(channel, current, total=1):
        ui.wait_for_header("memory", channel=channel)
        ui.wait_memory_position(current, total)
        c.results.append(dict(kind="channel-history-counter", channel=channel,
                              current=current, total=total))

    def verify(one, two):
        marker = c.snapshot()["midi_count"]
        ui.tap_control("play_stop")

        def notes(state):
            return [message for message in state["midi"]
                    if message["index"] > marker and 144 <= message["bytes"][0] <= 159
                    and message["bytes"][2] > 0]

        state = c.wait(lambda state: all(
            sum(message["bytes"][0] == status for message in notes(state)) >= 9
            for status in (144, 145)
        ), timeout=5)
        observed = notes(state)
        assert {message["bytes"][0] for message in observed} == {144, 145}
        for port, status, values in [(1, 144, one), (2, 145, two)]:
            actual = [(message["port"], message["bytes"])
                      for message in observed if message["bytes"][0] == status]
            expected = [(port, [status, *values[index % 4]])
                        for index in range(len(actual))]
            assert actual == expected, dict(channel=status - 143,
                                             expected=expected, actual=actual)
            c.results.append(dict(kind="history-musical-isolation", channel=status - 143,
                                  expected=expected, actual=actual))
        ui.tap_control("play_stop")
        c.wait(lambda state: not state["midi_capture"]["outstanding"])

    record(2, 79, 80)
    ui.select_channel(1)
    record(1, 72, 90)
    ui.turn(1, 2)
    history(1, 1)
    verify(edited_one, edited_two)
    ui.turn(3, -1)
    history(1, 0)
    verify(baseline, edited_two)
    ui.select_channel_on_page(2, "memory")
    history(2, 1)
    ui.press_key(2)
    history(2, 0)
    verify(baseline, baseline)
    ui.select_channel_on_page(1, "memory")
    history(1, 0)
    ui.press_key(3)
    history(1, 1)
    verify(edited_one, baseline)
    ui.select_channel_on_page(2, "memory")
    history(2, 0)
    ui.turn(3, 1)
    history(2, 1)
    verify(edited_one, edited_two)
    # Switching to an untouched channel and navigating its empty history must
    # not affect either audible channel or borrow their history counters.
    ui.select_channel_on_page(3, "memory")
    history(3, 0, 0)
    ui.press_key(2)
    ui.press_key(3)
    ui.turn(3, -2)
    ui.turn(3, 2)
    history(3, 0, 0)
    verify(edited_one, edited_two)
    ui.select_channel_on_page(1, "memory")
    history(1, 1)
    ui.select_channel_on_page(2, "memory")
    history(2, 1)

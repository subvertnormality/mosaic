"""Semantic UI migration candidate for the ordinary mask gesture cases.

The MIDI actions and musical assertions are intentionally unchanged.  Grid
press/release choreography is routed through ``c.ui`` so the recipe remains
identical while the case no longer owns grid coordinates.
"""


def held_keyboard_chord(c, grid_first=False, extra_note=False, rearticulate=False):
    from cases import assert_durations

    ui = c.ui
    c.configure()
    ui.turn(1, -4)
    pitches = [72, 76, 79, 83, 86]
    velocities = [90, 80, 70, 60, 50]
    if extra_note:
        pitches.append(88)
        velocities.append(40)
    marker = c.snapshot()["midi_count"]
    ui.gesture([("step", 2)], [])
    for pitch, velocity in zip(pitches, velocities):
        c.action(type="midi", port=1, bytes=[144, pitch, velocity])
    if rearticulate:
        c.action(type="midi", port=1, bytes=[128, 72, 0])
        c.elapse(.05)
        c.action(type="midi", port=1, bytes=[144, 72, 45])
    if grid_first:
        ui.gesture([], [("step", 2)])
    for pitch in pitches:
        c.action(type="midi", port=1, bytes=[128, pitch, 0])
    if not grid_first:
        ui.gesture([], [("step", 2)])
    c.elapse(.15)
    state = c.wait(lambda state: not state["midi_capture"]["outstanding"])
    preview = [
        (m["port"], m["bytes"])
        for m in state["midi"]
        if m["index"] > marker and 128 <= m["bytes"][0] <= 159
    ]
    expected = [(1, [144, p, v]) for p, v in zip(pitches, velocities)]
    if rearticulate:
        expected += [(1, [128, 72, 0]), (1, [144, 72, 45])]
    expected += [(1, [128, p, 0]) for p in pitches]
    assert preview == expected, dict(expected=expected, actual=preview)

    def verify(chord, velocity, stage):
        phrase = [(1, [144, 60, 127])] + [
            (1, [144, p, velocity]) for p in chord
        ] + [(1, [144, 64, 107]), (1, [144, 65, 97])]
        positions = [0] + [1] * len(chord) + [2, 3]
        notes = c.playback(phrase, cycles=2, timeout=4)
        assert_durations(c, notes, [1] * (len(phrase) * 2))
        field = "logical_ns" if c.clock_mode == "controlled-experimental" else "monotonic_ns"
        tolerance = 2e-9 if c.clock_mode == "controlled-experimental" else .01
        for i, note in enumerate(notes):
            wanted = ((i // len(phrase)) * 4 + positions[i % len(phrase)]) / 6
            assert abs((note[field] - notes[0][field]) / 1e9 - wanted) <= tolerance
        c.results.append(dict(
            kind="held-keyboard-mask", stage=stage,
            grid_released_first=grid_first, extra_note=extra_note,
            rearticulate=rearticulate, chord=chord, velocity=velocity,
            passed=True,
        ))

    verify(pitches[:5], 90, "five-voice-chord-committed")
    ui.gesture([("step", 2)], [])
    c.action(type="midi", port=1, bytes=[144, 67, 55])
    c.action(type="midi", port=1, bytes=[128, 67, 0])
    ui.gesture([], [("step", 2)])
    c.elapse(.15)
    verify([67], 55, "single-note-replaces-old-chord")


def multiheld_keyboard(c, release_first=True):
    from cases import assert_durations

    ui = c.ui
    c.configure()
    ui.turn(1, -4)
    marker = c.snapshot()["midi_count"]
    ui.gesture([("step", 2), ("step", 4)], [])
    c.action(type="midi", port=1, bytes=[144, 72, 90])
    c.action(type="midi", port=1, bytes=[128, 72, 0])
    released = 2 if release_first else 4
    remaining = 4 if release_first else 2
    ui.gesture([], [("step", released)])
    c.elapse(.1)
    c.action(type="midi", port=1, bytes=[144, 79, 55])
    c.action(type="midi", port=1, bytes=[128, 79, 0])
    ui.gesture([], [("step", remaining)])
    c.elapse(.15)
    state = c.wait(lambda state: not state["midi_capture"]["outstanding"])
    preview = [
        (m["port"], m["bytes"])
        for m in state["midi"]
        if m["index"] > marker and 128 <= m["bytes"][0] <= 159
    ]
    assert preview == [
        (1, [144, 72, 90]), (1, [128, 72, 0]),
        (1, [144, 79, 55]), (1, [128, 79, 0]),
    ], preview
    phrase = (
        [(1, [144, 72, 90]), (1, [144, 64, 107]), (1, [144, 79, 55])]
        if release_first else
        [(1, [144, 79, 55]), (1, [144, 64, 107]), (1, [144, 65, 97])]
    )
    # Preserve the historical hold-step-then-tap recipe through the semantic verb.
    ui.set_range(2, 4)
    notes = c.playback(phrase, cycles=3, timeout=4)
    assert_durations(c, notes, [1] * 9)
    field = "logical_ns" if c.clock_mode == "controlled-experimental" else "monotonic_ns"
    tolerance = 2e-9 if c.clock_mode == "controlled-experimental" else .01
    for i, note in enumerate(notes):
        assert abs((note[field] - notes[0][field]) / 1e9 - i / 6) <= tolerance
    ui.expect_leds({("step", 1): "dark", ("step", 5): "dark", ("step", 64): "dark"})
    c.results.append(dict(
        kind="multiheld-keyboard", first_released=release_first,
        range=[2, 4], expected=phrase, passed=True,
    ))

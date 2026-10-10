"""Literal manual random domains with a separate native PRNG oracle."""


def random_note_domains(c, twos=False, pentatonic=False, mask=None):
    import subprocess
    import json

    from cases import assert_durations

    domains = [[0], [0, 1], [-1, 0, 1], [-1, 0, 1, 2], [-2, -1, 0, 1, 2]]
    stages = [(0, value) if twos else (value, 0) for value in range(5)] + [(4, 4), (0, 0)]
    if pentatonic:
        stages = [(4, 0), (0, 4), (4, 4), (0, 0)]

    # Use independently authored domain lists, not Mosaic transforms. Lua's
    # platform PRNG supplies an index; never fit an offset to captured output.
    code = ["math.randomseed(42)"]
    for a, b in stages:
        for _ in range(33):
            expr = []
            for value, multiplier in [(a, 1), (b, 2)]:
                domain = [n * multiplier for n in domains[value]]
                expr.append(
                    "0" if value == 0 else
                    "({" + ",".join(map(str, domain)) + "})[math.random(1," +
                    str(len(domain)) + ")]"
                )
            code.append(
                "do local a=" + expr[0] + ";local b=" + expr[1] +
                ";print(a,b,a+b) end"
            )
    proc = subprocess.run(
        ["lua5.3", "-e", ";".join(code)],
        capture_output=True,
        text=True,
        check=True,
    )
    components = [tuple(map(int, line.split())) for line in proc.stdout.splitlines()]
    offsets = [row[2] for row in components]
    assert len(offsets) == 33 * len(stages)

    c.ui.configure()
    c.ui.set_mosaic_options([
        ("Lock random to pent.", pentatonic),
        ("Lock merged to pent.", False),
    ])
    if mask:
        assert mask in ("full", "snap", "raw")
        c.ui.set_mosaic_options([
            ("Quantise note masks", mask == "full"),
            ("Snap note masks to scale", mask == "snap"),
        ])
        c.ui.turn(1, -4)
        for step, pitch in enumerate([60, 62, 64, 65], 1):
            with c.ui.hold_step(step):
                c.ui.set_value(pitch + 1)
            c.elapse(.06)
        c.ui.turn(1, 1)
    else:
        c.ui.turn(1, -3)

    c.ui.assign_trig_parameter("Random Note")
    c.ui.turn(2, 1)
    c.ui.assign_trig_parameter("Twos Random Note")
    c.ui.turn(2, -1)

    previous = (0, 0)
    field = "logical_ns" if c.clock_mode == "controlled-experimental" else "monotonic_ns"
    tolerance = 2e-9 if c.clock_mode == "controlled-experimental" else .01
    for stage, (a, b) in enumerate(stages):
        c.ui.set_value(a - previous[0])
        c.ui.turn(2, 1)
        c.ui.set_value(b - previous[1])
        c.ui.turn(2, -1)
        previous = (a, b)
        shifts = offsets[33 * stage:33 * (stage + 1)]
        allowed = {x + 2 * y for x in domains[a] for y in domains[b]}
        assert set(shifts) <= allowed
        if (a == 0) != (b == 0):
            assert set(shifts) == allowed, "Seed must exercise every documented single-param offset"

        pitches = []
        for i, shift in enumerate(shifts):
            degree = i % 4 + shift
            pitch = 60 + 12 * (degree // 7) + [0, 2, 4, 5, 7, 9, 11][degree % 7]
            if pentatonic and shift != 0 and mask not in ("raw", "snap"):
                # Codex-arbitrated nonzero sum: both signs snap; sampled zero
                # and cancellation preserve the unmodified note.
                available = [
                    12 * octave + note
                    for octave in range(11)
                    for note in [0, 2, 4, 7, 9]
                ]
                pitch = min(available, key=lambda note: (abs(note - pitch), note))
            if mask in ("raw", "snap"):
                pitch = [60, 62, 64, 65][i % 4] + shift
                if mask == "snap":
                    available = [
                        12 * octave + note
                        for octave in range(11)
                        for note in [0, 2, 4, 5, 7, 9, 11]
                    ]
                    pitch = min(available, key=lambda note: (abs(note - pitch), note))
            pitches.append(pitch)

        before = c.snapshot()["midi_count"]
        c.ui.play()

        def onsets(state):
            return [
                midi for midi in state["midi"]
                if midi["index"] > before and midi["bytes"][0] & 240 == 144
                and midi["bytes"][2] > 0
            ]

        state = c.wait(lambda state: len(onsets(state)) >= 33, timeout=8)
        notes = onsets(state)
        expected = [
            (1, [144, pitch, [127, 117, 107, 97][i % 4]])
            for i, pitch in enumerate(pitches)
        ]
        assert [(note["port"], note["bytes"]) for note in notes] == expected, {
            "expected": expected,
            "actual": [(note["port"], note["bytes"]) for note in notes],
        }
        c.ui.stop()
        c.wait(lambda state: state["midi_capture"]["outstanding"] == [])
        assert_durations(c, notes, [1] * 32)
        for i, note in enumerate(notes):
            assert abs((note[field] - notes[0][field]) / 1e9 - i / 6) <= tolerance
        c.results.append(dict(
            kind="random-note-domain",
            pentatonic=pentatonic,
            random=a,
            twos=b,
            seed=42,
            mask=mask,
            components=components[33 * stage:33 * (stage + 1)],
            offsets=shifts,
            allowed=sorted(allowed),
            pitches=pitches,
            passed=True,
        ))

"""UI-clean stored patch boundary/recall cases for the next migration batch.

The bodies intentionally retain the established MIDI and persistence oracles;
only navigation ownership moved to ``c.ui``.  The four registry entries can be
routed here while the remaining slide/contract bodies stay in patch_params.py.
"""
import json


def open_patch_control(c, configured=False, setup=True):
    return c.ui.open_patch_control(configured=configured, setup=setup)


def turn(c, steps):
    return c.ui.turn_patch_control(steps)


def patch_boundaries(c, configured=False):
    from cases import menu_value

    open_patch_control(c, configured)
    menu_value(c, "X")
    before = c.snapshot()["midi_count"]
    expected = []
    value = -1
    for delta in (-1, 1, 1, 62, 1, 62, 1, 1, -63, -63, -2, -1):
        wanted = max(-1, min(127, value + delta))
        turn(c, delta)
        if wanted != value and wanted != -1:
            expected.append((1, [176, 1, wanted]))
        value = wanted
        menu_value(c, "X" if value == -1 else str(value))
        actual = [
            (event["port"], event["bytes"])
            for event in c.snapshot()["midi"]
            if event["index"] > before
        ]
        assert actual == expected, dict(expected=expected, actual=actual)
    c.results.append(dict(
        kind="stored-patch-sentinel-boundaries", configured=configured,
        values=[-1, 0, 1, 63, 64, 126, 127], clamped_attempts=True,
        expected=expected, passed=True,
    ))


def patch_play_recall(c, repetitions=1):
    from cases import menu_value

    open_patch_control(c)
    menu_value(c, "X")
    turn(c, 63)
    turn(c, 1)
    menu_value(c, "63")
    c.ui.press_key(1)
    windows = []
    for _ in range(repetitions):
        before = c.snapshot()["midi_count"]
        c.playback(
            [(1, [144, n, v]) for n, v in ((60, 127), (62, 117),
                                              (64, 107), (65, 97))],
            cycles=2,
        )
        windows.append((before, c.snapshot()["midi_count"]))
    c.finish()
    try:
        events = [json.loads(line) for line in
                  (c.out / "native/native-events.jsonl").read_text().splitlines()]
        midi = [event for event in events if event.get("kind") in (3, 11)]
        assert [event["sequence"] for event in midi] == list(range(1, len(midi) + 1))
        for before, after in windows:
            window = midi[before:after]
            cc = [event for event in window if event["bytes"][0] & 240 == 176]
            actual = [(event["port"], event["bytes"]) for event in cc]
            c.results.append(dict(kind="stored-unmapped-patch-play-recall",
                                  actual=actual,
                                  expected=[(1, [176, 1, 63])]))
            assert actual == [(1, [176, 1, 63])], \
                "Play did not recall exactly the stored unassigned CC parameter"
            first_note = next(event for event in window
                              if event["bytes"][0] & 240 == 144 and event["bytes"][2] > 0)
            assert cc[0]["sequence"] < first_note["sequence"], \
                "Patch recall followed the first note"
            c.results.append(dict(kind="stored-unmapped-patch-play-recall-complete",
                                  passed=True))
    finally:
        (c.out / "results.json").write_text(json.dumps(c.results, indent=2) + "\n")

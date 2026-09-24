"""Ordinary patch edge cases for the second independently gateable slice."""
import json


def open_patch_control(c, configured=False, setup=True):
    return c.ui.open_patch_control(configured=configured, setup=setup)


def turn(c, steps):
    return c.ui.turn_patch_control(steps)


def patch_muted_recall(c):
    open_patch_control(c)
    turn(c, 63)
    turn(c, 1)
    c.ui.expect_patch_value(63)
    c.ui.press_key(1)
    with c.ui.hold_control("channel", 1):
        c.elapse(1.1)
    c.ui.expect_leds({("channel", 1): "alternate"})
    before = c.snapshot()["midi_count"]
    c.ui.play()
    c.elapse(1.5)
    c.ui.stop()
    state = c.snapshot()
    after = state["midi_count"]
    assert not state["midi_capture"]["outstanding"]
    c.finish()
    try:
        events = [json.loads(line) for line in
                  (c.out / "native/native-events.jsonl").read_text().splitlines()]
        midi = [event for event in events if event.get("kind") in (3, 11)]
        assert [event["sequence"] for event in midi] == list(range(1, len(midi) + 1))
        window = midi[before:after]
        cc = [(event["port"], event["bytes"]) for event in window
              if event["bytes"][0] & 240 == 176]
        notes = [event for event in window
                 if event["bytes"][0] & 240 == 144 and event["bytes"][2] > 0]
        assert cc == [(1, [176, 1, 63])], cc
        assert not notes, notes
        c.results.append(dict(kind="muted-stored-patch-recall", seconds=1.5,
                              cc=cc, note_ons=0, passed=True))
    finally:
        (c.out / "results.json").write_text(json.dumps(c.results, indent=2) + "\n")


def patch_nrpn_bytes(c):
    c.ui.seek_patch_parameter("nrpn14", configured=True)
    c.ui.expect_patch_value("off")
    before = c.snapshot()["midi_count"]
    turn(c, 1)
    c.ui.expect_patch_value(126)
    actual = [(event["port"], event["bytes"])
              for event in c.snapshot()["midi"] if event["index"] > before]
    expected = [(1, [176, 99, 4]), (1, [176, 98, 5]),
                (1, [176, 6, 0]), (1, [176, 38, 126])]
    c.results.append(dict(kind="nrpn-native-byte-regression",
                          expected=expected, actual=actual))
    assert actual == expected, dict(expected=expected, actual=actual)

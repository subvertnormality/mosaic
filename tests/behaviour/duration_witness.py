"""Stable musical projection for controlled duration witnesses."""


_REQUIRED_FIELDS = {
    "device_id", "port", "port_name", "monotonic_ns", "index",
    "bytes", "decoded", "logical_ns",
}


def _validate_event(event, expected_status, label):
    assert isinstance(event, dict), "%s witness must be an object" % label
    missing = _REQUIRED_FIELDS - set(event)
    assert not missing, "%s witness missing fields: %s" % (label, sorted(missing))
    for field in ("device_id", "port", "monotonic_ns", "index", "logical_ns"):
        assert type(event[field]) is int, "%s %s must be an integer" % (label, field)
    assert isinstance(event["port_name"], str), "%s port_name must be a string" % label
    assert isinstance(event["bytes"], list) and all(
        type(value) is int for value in event["bytes"]
    ), "%s bytes must be an integer array" % label
    assert len(event["bytes"]) == 3, "%s must carry one complete channel-voice message" % label
    assert isinstance(event["decoded"], list) and event["decoded"], (
        "%s decoded must contain the native MIDI decode" % label
    )
    assert event["bytes"][0] & 0xF0 == expected_status, (
        "%s must be a %s" % (label, "note-on" if expected_status == 0x90 else "note-off")
    )
    expected_type = "note_on" if expected_status == 0x90 else "note_off"
    assert event["decoded"][0].get("type") == expected_type, (
        "%s decoded event type is inconsistent with bytes" % label
    )
    assert event["decoded"][0].get("data") == event["bytes"][1:], (
        "%s decoded payload is inconsistent with bytes" % label
    )


def assert_duration_witness_observed(observations, first_on, first_off):
    """Require full native MIDI records, including host timestamps, in snapshots."""
    expected = (first_on, first_off)
    by_index = {}
    for observation in observations:
        state = observation.get("state") if isinstance(observation, dict) else None
        midi = state.get("midi") if isinstance(state, dict) else None
        if isinstance(midi, list):
            by_index.update((event.get("index"), event) for event in midi
                            if isinstance(event, dict) and isinstance(event.get("index"), int))
    for label, event in zip(("first_on", "first_off"), expected):
        actual = by_index.get(event.get("index"))
        assert actual == event, "%s raw witness was not preserved in observations" % label


def controlled_duration_witness_pair(first_on, first_off):
    """Keep logical time, MIDI payload, and ordering in results; retain raw rows elsewhere."""
    _validate_event(first_on, 0x90, "first_on")
    _validate_event(first_off, 0x80, "first_off")
    assert first_on["index"] < first_off["index"], "MIDI witness order is invalid"
    assert first_on["logical_ns"] <= first_off["logical_ns"], "logical MIDI witness order is invalid"
    assert (first_on["bytes"][0] & 0x0F, first_on["bytes"][1]) == (
        first_off["bytes"][0] & 0x0F, first_off["bytes"][1]
    ), "note-on and note-off witnesses must match channel and pitch"
    return {
        "first_on": {
            "index": first_on["index"],
            "logical_ns": first_on["logical_ns"],
            "bytes": list(first_on["bytes"]),
        },
        "first_off": {
            "index": first_off["index"],
            "logical_ns": first_off["logical_ns"],
            "bytes": list(first_off["bytes"]),
        },
    }

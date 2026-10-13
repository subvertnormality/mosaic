import manual_teaching_contract as contract


def native(expect):
    return {"to_step": {"expect": expect}, "scene_input_prefix": []}


PHRASE = [{"port": 1, "bytes": [176, 1, 63]}]


def test_authored_phrase_is_still_enforced():
    assert contract.validate_semantics(native({"midi_phrase": PHRASE}), {"midi_phrase_contains": PHRASE})
    assert not contract.validate_semantics(native({"midi_phrase": []}), {"midi_phrase_contains": PHRASE})


def test_typed_midi_target_leaves_the_phrase_to_the_captured_packet_proof():
    assert contract.validate_semantics(native({"assertion": {"kind": "midi"}}), {"midi_phrase_contains": PHRASE})

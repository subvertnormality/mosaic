import pytest

from manual_teaching_v8 import (
    Error, _native, _validate_output, _validate_semantics,
)


def test_held_control_predicate_rejects_unknown_types_and_bad_bounds():
    with pytest.raises(Error, match="held controls"):
        _validate_semantics({"held_controls_at_target": [{"type": "bogus", "n": 1}]})
    with pytest.raises(Error, match="held controls"):
        _validate_semantics({"held_controls_at_target": [{"type": "grid", "x": 0, "y": 1}]})
    with pytest.raises(Error, match="held controls"):
        _validate_semantics({"held_controls_at_target": [{"type": "key", "n": True}]})


def test_selected_field_public_adapter_accepts_exact_captured_top_level_variant():
    native = {"to_step": {"output": {"binding": {"assertion": {
        "kind": "selected-field", "layout": "detail", "label": "Strategy", "value": "ONLY",
        "matched": True, "citation": "private", "passed": True,
    }}}}}
    _validate_output(native, {"public_readout_equals": {
        "selected_field.layout": "detail",
        "selected_field.label": "Strategy",
        "selected_field.value": "ONLY",
    }})
    with pytest.raises(Error, match="public readout differs"):
        _validate_output(native, {"public_readout_equals": {"selected_field.value": "MIX"} })


def test_public_predicates_reject_internal_or_unsupported_fields():
    with pytest.raises(Error, match="unknown public fields"):
        _validate_semantics({"public_readout_equals": {"passed": True}})
    with pytest.raises(Error, match="needs a concrete observable"):
        _validate_semantics({"held_controls_at_target": []})


def test_interval_contains_every_real_native_step_and_hash_tracks_intermediate_evidence():
    scene = {"id": "scene", "behaviour_case": "case",
        "evidence": {"identity_sha256": "a" * 64, "results_sha256": "b" * 64},
        "steps": [
            {"id": "start", "inputs": [], "expect": {"screen": []}, "output": {"grid": [0] * 128}},
            {"id": "middle", "inputs": [{"type": "enc", "n": 2, "delta": 1}], "expect": {"screen": []}, "output": {"grid": [1] * 128}},
            {"id": "target", "inputs": [{"type": "grid", "x": 1, "y": 1, "state": 1}], "expect": {"screen": []}, "output": {"grid": [2] * 128}},
        ]}
    native = _native(scene, "start", "target", "interval")
    assert [step["id"] for step in native["step_interval"]] == ["start", "middle", "target"]
    assert [row["step_id"] for row in native["scene_input_prefix"]] == ["start", "middle", "target"]
    changed = {**scene, "steps": [dict(step) for step in scene["steps"]]}
    changed["steps"][1] = {**changed["steps"][1], "output": {"grid": [3] * 128}}
    assert _native(changed, "start", "target", "interval")["step_interval"][1]["output"] != native["step_interval"][1]["output"]
    with pytest.raises(Error, match="adjacent"):
        _native(scene, "start", "target", "adjacent")


def test_device_configuration_is_exact_public_readout_and_value_checkpoint():
    assertion = {"kind": "device-configuration", "device_configuration": {
        "device": "CC Device", "midi_channel": "CC1", "midi_port": "OUT1",
    }, "passed": True, "internal_index": 4}
    native = {"to_step": {"output": {"binding": {"assertion": assertion}}}}
    _validate_output(native, {"public_readout_equals": {"device_configuration": {
        "device": "CC Device", "midi_channel": "CC1", "midi_port": "OUT1",
    }}})
    from manual_teaching_v8 import _matches_field_value
    assert _matches_field_value(assertion, "midi_channel", "CC1")
    assert not _matches_field_value(assertion, "midi_channel", "CC2")
    preselection = {"device_configuration": {"device": "None"}}
    _validate_semantics({"public_readout_equals": preselection})
    assert _matches_field_value(preselection, "device", "None")
    assert not _matches_field_value(preselection, "midi_port", "OUT1")
    with pytest.raises(Error, match="public readout differs"):
        _validate_output(native, {"public_readout_equals": {"device_configuration": {
            "device": "CC Device", "midi_channel": "CC2", "midi_port": "OUT1",
        }}})
    with pytest.raises(Error, match="device_configuration"):
        _validate_semantics({"public_readout_equals": {"device_configuration": {
            "device": "CC Device", "midi_channel": "CC1", "midi_port": "OUT1", "internal_index": "4",
        }}})


def _native_with_step(inputs, assertion=None, midi=None):
    output = {"grid": [0] * 128}
    if assertion is not None:
        output["binding"] = {"assertion": assertion}
    if midi is not None:
        output["midi"] = midi
    return {
        "contract_schema": "mosaic-native-transition-v2",
        "from_step_id": "start",
        "from_step": {"id": "start", "inputs": [], "expect": {}, "output": {"grid": [0] * 128}},
        "to_step": {"id": "target", "inputs": inputs, "expect": {"midi_phrase": [{"port": 1, "bytes": [144, 60, 80]}]} if midi else {}, "output": output},
        "scene_input_prefix": [{"step_id": "start", "inputs": []}, {"step_id": "target", "inputs": inputs}],
    }


def test_action_checkpoints_bind_select_value_menu_and_phrase_to_later_captured_outputs():
    from manual_teaching_v8 import _validate_actions
    selected = _native_with_step(
        [{"type": "enc", "n": 3, "delta": 1}],
        {"kind": "selected-field", "layout": "detail", "label": "Rate", "value": "1/2"},
    )
    select_actions = [
        {"id": "rate", "kind": "select-value", "control": "E3", "field_label": "Rate", "label": "Set Rate", "value": "1/2"},
        {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"},
    ]
    select_proofs = _validate_actions({"actions": select_actions}, selected, "target", {})
    assert select_proofs == [
        {"action_id": "rate", "raw_inputs": [{"step_id": "target", "index": 0}],
         "checkpoint_step_id": "target", "proof": {"kind": "field-value", "field_label": "Rate", "value": "1/2"}},
        {"action_id": "preview", "raw_inputs": [], "checkpoint_step_id": "target",
         "proof": {"kind": "recorded-target", "to_step_id": "target"}},
    ]

    menu = _native_with_step(
        [{"type": "enc", "n": 2, "delta": 1}],
        {"kind": "selected-menu-label", "text": "Save"},
    )
    menu_actions = [
        {"id": "save", "kind": "choose-menu", "trigger": {"type": "enc", "n": 2, "direction": "clockwise"},
         "menu_text": "Save", "label": "Save the project"},
        {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"},
    ]
    menu_proofs = _validate_actions({"actions": menu_actions}, menu, "target", {})
    assert menu_proofs[0]["checkpoint_step_id"] == "target"
    assert menu_proofs[0]["proof"] == {"kind": "menu-text", "text": "Save"}

    phrase = _native_with_step(
        [{"type": "grid", "x": 1, "y": 8, "state": 1}, {"type": "grid", "x": 1, "y": 8, "state": 0}],
        None, {"truncated": False, "events": [{"port": 1, "bytes": [144, 60, 80]}]},
    )
    phrase_actions = [
        {"id": "play", "kind": "play-phrase", "trigger": {"type": "grid", "x": 1, "y": 8, "gesture": "tap"}, "label": "Play the phrase"},
        {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"},
    ]
    phrase_proofs = _validate_actions({"actions": phrase_actions}, phrase, "target", {})
    assert phrase_proofs[0]["raw_inputs"] == [{"step_id": "target", "index": 0}, {"step_id": "target", "index": 1}]
    assert phrase_proofs[0]["proof"] == {"kind": "midi-phrase", "events": [{"port": 1, "bytes": [144, 60, 80]}]}


@pytest.mark.parametrize("control,inputs,action", [
    ({"type": "key", "n": 1}, [{"type": "key", "n": 1, "state": 1}, {"type": "key", "n": 1, "state": 0}],
     {"id": "hold", "kind": "hold-key", "n": 1, "label": "Hold K1"}),
    ({"type": "grid", "x": 5, "y": 4}, [{"type": "grid", "x": 5, "y": 4, "state": 1}, {"type": "grid", "x": 5, "y": 4, "state": 0}],
     {"id": "hold", "kind": "hold-grid", "x": 5, "y": 4, "label": "Hold the step"}),
])
def test_authored_hold_must_match_native_final_held_state(control, inputs, action):
    from manual_teaching_v8 import _validate_actions
    native = _native_with_step(inputs)
    actions = [action, {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"}]
    with pytest.raises(Error, match="held-control lifecycle"):
        _validate_actions({"actions": actions}, native, "target", {})


@pytest.mark.parametrize("control,inputs,action", [
    (("key", 1), [{"type": "key", "n": 1, "state": 1}, {"type": "key", "n": 1, "state": 0}],
     {"id": "tap", "kind": "tap-key", "n": 1, "label": "Tap K1"}),
    (("grid", 5, 4), [{"type": "grid", "x": 5, "y": 4, "state": 1}, {"type": "grid", "x": 5, "y": 4, "state": 0}],
     {"id": "tap", "kind": "tap-grid", "x": 5, "y": 4, "label": "Tap the step"}),
])
def test_tap_rejects_control_already_held_at_source_checkpoint(control, inputs, action):
    from manual_teaching_v8 import _validate_actions
    native = _native_with_step(inputs)
    kind, *coords = control
    held = [{"type": kind, **({"n": coords[0]} if kind=="key" else {"x": coords[0], "y": coords[1]})}]
    native["from_step"] = {"id": "start", "inputs": [], "expect": {}, "output": {"grid": [0] * 128}}
    native["scene_input_prefix"] = [
        {"step_id": "start", "inputs": [{"type": kind, **({"n": coords[0]} if kind=="key" else {"x": coords[0], "y": coords[1]}), "state": 1}]},
        {"step_id": "target", "inputs": inputs},
    ]
    # The native transition begins while this control is still held; target releases it.
    with pytest.raises(Error, match="ordered captured press/release"):
        _validate_actions({"actions": [action, {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"}]},
                          native, "target", {})


def test_transient_hold_release_matches_captured_empty_final_state():
    from manual_teaching_v8 import _validate_actions
    native = _native_with_step([
        {"type": "key", "n": 1, "state": 1},
        {"type": "grid", "x": 5, "y": 4, "state": 1},
        {"type": "grid", "x": 5, "y": 4, "state": 0},
        {"type": "key", "n": 1, "state": 0},
    ])
    actions = [
        {"id": "hold", "kind": "hold-key", "n": 1, "label": "Hold K1"},
        {"id": "tap", "kind": "tap-grid", "x": 5, "y": 4, "label": "Add the step"},
        {"id": "release", "kind": "release-key", "n": 1, "label": "Release K1"},
        {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"},
    ]
    proofs = _validate_actions({"actions": actions}, native, "target", {})
    assert [p["action_id"] for p in proofs] == ["hold", "tap", "release", "preview"]
    assert proofs[0]["proof"] == {"kind": "key-hold", "n": 1}
    assert proofs[2]["proof"] == {"kind": "key-release", "n": 1}


def _play_actions():
    return [
        {"id": "play", "kind": "play-phrase", "trigger": {"type": "grid", "x": 1, "y": 8, "gesture": "tap"}, "label": "Play the phrase"},
        {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"},
    ]


def test_play_phrase_requires_actual_target_midi_to_match_captured_phrase():
    from manual_teaching_v8 import _validate_actions
    native = _native_with_step(
        [{"type": "grid", "x": 1, "y": 8, "state": 1}, {"type": "grid", "x": 1, "y": 8, "state": 0}],
        None, {"truncated": False, "events": [{"port": 1, "bytes": [144, 61, 80]}]},
    )
    with pytest.raises(Error, match="later public/MIDI checkpoint"):
        _validate_actions({"actions": _play_actions()}, native, "target", {})


def test_play_phrase_rejects_phrase_output_that_precedes_trigger_checkpoint():
    from manual_teaching_v8 import _validate_actions
    phrase = [{"port": 1, "bytes": [144, 60, 80]}]
    native = {
        "contract_schema": "mosaic-native-transition-v3",
        "transition_scope": "interval",
        "from_step_id": "start", "to_step_id": "target",
        "scene_input_prefix": [
            {"step_id": "start", "inputs": []},
            {"step_id": "before-play", "inputs": [{"type": "enc", "n": 2, "delta": 1}]},
            {"step_id": "target", "inputs": [
                {"type": "grid", "x": 1, "y": 8, "state": 1},
                {"type": "grid", "x": 1, "y": 8, "state": 0},
            ]},
        ],
        "step_interval": [
            {"id": "start", "inputs": [], "expect": {}, "output": {"grid": [0]*128}},
            {"id": "before-play", "inputs": [{"type": "enc", "n": 2, "delta": 1}],
             "expect": {"midi_phrase": phrase},
             "output": {"grid": [0]*128, "midi": {"truncated": False, "events": phrase}}},
            {"id": "target", "inputs": [
                {"type": "grid", "x": 1, "y": 8, "state": 1},
                {"type": "grid", "x": 1, "y": 8, "state": 0},
            ], "expect": {}, "output": {"grid": [0]*128, "midi": {"truncated": False, "events": []}}},
        ],
        "from_step": {"id":"start","inputs":[],"expect":{},"output":{"grid":[0]*128}},
        "to_step": {"id":"target","inputs":[
            {"type":"grid","x":1,"y":8,"state":1},{"type":"grid","x":1,"y":8,"state":0}],
            "expect":{},"output":{"grid":[0]*128,"midi":{"truncated":False,"events":[]}}},
    }
    with pytest.raises(Error, match="later public/MIDI checkpoint"):
        _validate_actions({"actions": _play_actions()}, native, "target", {})


def test_play_phrase_can_use_exact_authored_midi_output_predicate_without_expect_phrase():
    from manual_teaching_v8 import _validate_actions
    phrase = [{"port": 1, "bytes": [144, 60, 80]}]
    native = _native_with_step(
        [{"type": "grid", "x": 1, "y": 8, "state": 1}, {"type": "grid", "x": 1, "y": 8, "state": 0}],
        None, {"truncated": False, "events": phrase},
    )
    native["to_step"]["expect"] = {"screen": [["Play", "Phrase"]]}
    proofs = _validate_actions({"actions": _play_actions()}, native, "target",
        {"midi_events_at_target": phrase})
    assert proofs[0]["proof"] == {"kind": "midi-phrase", "events": phrase}


def test_play_phrase_with_no_asserted_phrase_evidence_fails_closed():
    from manual_teaching_v8 import _validate_actions
    phrase = [{"port": 1, "bytes": [144, 60, 80]}]
    native = _native_with_step(
        [{"type": "grid", "x": 1, "y": 8, "state": 1}, {"type": "grid", "x": 1, "y": 8, "state": 0}],
        None, {"truncated": False, "events": phrase},
    )
    native["to_step"]["expect"] = {"screen": [["Play", "Phrase"]]}
    with pytest.raises(Error, match="later public/MIDI checkpoint"):
        _validate_actions({"actions": _play_actions()}, native, "target", {})


def _interval_native(records):
    interval=[]
    for row in records:
        interval.append({"id":row["id"],"inputs":row["inputs"],"expect":row.get("expect",{}),"output":row["output"]})
    return {
        "contract_schema":"mosaic-native-transition-v3","transition_scope":"interval",
        "from_step_id":records[0]["id"],"to_step_id":records[-1]["id"],
        "from_step":interval[0],"to_step":interval[-1],"step_interval":interval,
        "scene_input_prefix":[{"step_id":r["id"],"inputs":r["inputs"]} for r in records],
    }


def test_choose_menu_rejects_matching_public_label_from_before_trigger():
    from manual_teaching_v8 import _validate_actions
    native = _interval_native([
        {"id":"start","inputs":[],"output":{"grid":[0]*128}},
        {"id":"menu-before-trigger","inputs":[{"type":"key","n":3,"state":1},{"type":"key","n":3,"state":0}],
         "expect":{},"output":{"grid":[0]*128,"binding":{"assertion":{"kind":"selected-menu-label","text":"Save"}}}},
        {"id":"target","inputs":[{"type":"enc","n":2,"delta":1}],"expect":{},"output":{"grid":[0]*128}},
    ])
    actions=[
        {"id":"save","kind":"choose-menu","label":"Save the project",
         "trigger":{"type":"enc","n":2,"direction":"clockwise"},"menu_text":"Save"},
        {"id":"preview","kind":"preview-recorded-result","label":"Preview","target_step_id":"target"},
    ]
    with pytest.raises(Error,match="later public/MIDI checkpoint"):
        _validate_actions({"actions":actions},native,"target",{})


def test_select_value_checkpoint_consumption_blocks_tap_that_happened_before_value():
    from manual_teaching_v8 import _validate_actions
    native = _interval_native([
        {"id":"start","inputs":[],"output":{"grid":[0]*128}},
        {"id":"tap-first","inputs":[{"type":"grid","x":3,"y":4,"state":1},{"type":"grid","x":3,"y":4,"state":0}],
         "expect":{},"output":{"grid":[0]*128}},
        {"id":"target","inputs":[{"type":"enc","n":3,"delta":1}],"expect":{},
         "output":{"grid":[0]*128,"binding":{"assertion":{"kind":"selected-field","label":"Rate","value":"/2","layout":"detail"}}}},
    ])
    actions=[
        {"id":"rate","kind":"select-value","control":"E3","field_label":"Rate","label":"Set Rate","value":"/2"},
        {"id":"tap","kind":"tap-grid","x":3,"y":4,"label":"Tap the step"},
        {"id":"preview","kind":"preview-recorded-result","label":"Preview","target_step_id":"target"},
    ]
    with pytest.raises(Error,match="tap-grid has no ordered captured press/release"):
        _validate_actions({"actions":actions},native,"target",{})


def test_choose_menu_accepts_captured_e1_navigation_but_play_phrase_does_not():
    from manual_teaching_v8 import _validate_actions
    native = _native_with_step(
        [{"type":"enc","n":1,"delta":1}],
        {"kind":"manual-course-ui","page":"channel_tasks","header":{"title":"Channel tasks"}},
    )
    actions=[
        {"id":"scroll","kind":"choose-menu","label":"Open Channel tasks",
         "trigger":{"type":"enc","n":1,"direction":"clockwise"},
         "destination":{"header_title":"Channel tasks"}},
        {"id":"preview","kind":"preview-recorded-result","target_step_id":"target","label":"Preview"},
    ]
    proofs=_validate_actions({"actions":actions},native,"target",{})
    assert proofs[0]["proof"]=={"kind":"destination","header_title":"Channel tasks"}
    play=[
        {"id":"play","kind":"play-phrase","label":"Play","trigger":{"type":"enc","n":1,"direction":"clockwise"}},
        {"id":"preview","kind":"preview-recorded-result","target_step_id":"target","label":"Preview"},
    ]
    with pytest.raises(Error,match="trigger is not a valid"):
        _validate_actions({"actions":play},native,"target",{})


def test_dashboard_assertion_uses_only_exact_ordered_public_rows():
    rows = [
        ["Playing", "SONG 01"],
        ["Next", "SONG 01"],
        ["Pass", "1 / 1"],
        ["Global length", "63"],
        ["Song mode", "AUTO"],
    ]
    expected = [
        {"row": index, "label": row[0], "value": row[1]}
        for index, row in enumerate(rows)
    ]
    native = {"to_step": {"output": {"binding": {"assertion": {
        "kind": "dashboard", "title": "SONG PLAYBACK", "scope": "SONG 01",
        "rows": rows, "passed": True,
    }}}}}
    _validate_output(native, {"public_readout_equals": {"dashboard_rows": expected}})
    changed = [dict(item) for item in expected]
    changed[3]["value"] = "64"
    with pytest.raises(Error, match="dashboard row differs"):
        _validate_output(native, {"public_readout_equals": {"dashboard_rows": changed}})
    malformed = {"to_step": {"output": {"binding": {"assertion": {
        "kind": "dashboard", "rows": [["Global length", 63]],
    }}}}}
    with pytest.raises(Error, match="dashboard row differs"):
        _validate_output(malformed, {"public_readout_equals": {"dashboard_rows": expected}})


def test_captured_song_dashboard_readout_is_exact_and_mutation_sensitive():
    import hashlib
    import json
    from pathlib import Path

    from manual_test_fixtures import load_pinned_projection_book

    book = load_pinned_projection_book()
    scene = book["scenes"]["song-global-length"]
    step = next(row for row in scene["steps"] if row["id"] == "shorten")
    expected = [
        {"row": 0, "label": "Playing", "value": "SONG 01"},
        {"row": 1, "label": "Next", "value": "SONG 01"},
        {"row": 2, "label": "Pass", "value": "1 / 1"},
        {"row": 3, "label": "Global length", "value": "63"},
        {"row": 4, "label": "Song mode", "value": "AUTO"},
    ]
    _validate_output({"to_step": step}, {"public_readout_equals": {"dashboard_rows": expected}})
    changed = [dict(row) for row in expected]
    changed[3]["value"] = "64"
    with pytest.raises(Error, match="dashboard row differs"):
        _validate_output({"to_step": step}, {"public_readout_equals": {"dashboard_rows": changed}})


def test_select_value_binds_ordered_e2_held_cell_e3_and_public_value():
    from manual_teaching_v8 import _validate_actions
    native = _native_with_step(
        [
            {"type": "enc", "n": 2, "delta": 1},
            {"type": "grid", "x": 1, "y": 4, "state": 1},
            {"type": "enc", "n": 3, "delta": 1},
        ],
        {"kind": "selected-field", "layout": "detail", "label": "Note", "value": "D3"},
    )
    native["scene_input_prefix"][0]["inputs"] = []
    actions = [
        {"id": "note", "kind": "select-value", "field_control": "E2", "control": "E3",
         "field_label": "Note", "value": "D3", "label": "Hold the step and set its note to D3",
         "between_hold": {"type": "grid", "x": 1, "y": 4, "gesture": "hold"}},
        {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"},
    ]
    proofs = _validate_actions({"actions": actions}, native, "target", {})
    assert proofs[0] == {
        "action_id": "note",
        "raw_inputs": [
            {"step_id": "target", "index": 0},
            {"step_id": "target", "index": 1},
            {"step_id": "target", "index": 2},
        ],
        "checkpoint_step_id": "target",
        "proof": {"kind": "field-value-with-held-grid", "field_label": "Note", "value": "D3",
                  "held_grid": {"x": 1, "y": 4}},
    }


@pytest.mark.parametrize("inputs", [
    # Wrong cell: the declared hold never occurs.
    [{"type": "enc", "n": 2, "delta": 1}, {"type": "grid", "x": 2, "y": 4, "state": 1}, {"type": "enc", "n": 3, "delta": 1}],
    # E3 precedes the declared held cell.
    [{"type": "enc", "n": 2, "delta": 1}, {"type": "enc", "n": 3, "delta": 1}, {"type": "grid", "x": 1, "y": 4, "state": 1}],
    # A release before E3 means the target is no longer in the declared held state.
    [{"type": "enc", "n": 2, "delta": 1}, {"type": "grid", "x": 1, "y": 4, "state": 1}, {"type": "grid", "x": 1, "y": 4, "state": 0}, {"type": "enc", "n": 3, "delta": 1}],
])
def test_select_value_rejects_wrong_or_reordered_between_hold(inputs):
    from manual_teaching_v8 import _validate_actions
    native = _native_with_step(inputs, {"kind": "selected-field", "layout": "detail", "label": "Note", "value": "D3"})
    actions = [
        {"id": "note", "kind": "select-value", "field_control": "E2", "control": "E3",
         "field_label": "Note", "value": "D3", "label": "Set note to D3",
         "between_hold": {"type": "grid", "x": 1, "y": 4, "gesture": "hold"}},
        {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"},
    ]
    with pytest.raises(Error):
        _validate_actions({"actions": actions}, native, "target", {})


def test_select_value_rejects_between_hold_without_e2_e3_pair_or_bad_cell():
    from manual_teaching_v8 import _validate_actions
    native = _native_with_step([], {"kind": "selected-field", "layout": "detail", "label": "Note", "value": "D3"})
    base = {"id": "note", "kind": "select-value", "control": "E3", "field_label": "Note", "value": "D3", "label": "Set note to D3",
            "between_hold": {"type": "grid", "x": 1, "y": 4, "gesture": "hold"}}
    actions = [base, {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "target", "label": "Preview"}]
    with pytest.raises(Error, match="valid captured controls"):
        _validate_actions({"actions": actions}, native, "target", {})
    bad = {**base, "field_control": "E2", "between_hold": {"type": "grid", "x": 17, "y": 4, "gesture": "hold"}}
    with pytest.raises(Error, match="valid captured controls"):
        _validate_actions({"actions": [bad, actions[1]]}, native, "target", {})

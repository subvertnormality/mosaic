import base64
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

TEST_ROOT = Path(__file__).parents[1]
CANDIDATE_TOOLS = TEST_ROOT / "tools"
PROJECT_TOOLS = TEST_ROOT / "tools"
if not PROJECT_TOOLS.is_dir():
    PROJECT_TOOLS = CANDIDATE_TOOLS
PRODUCER_PATH = CANDIDATE_TOOLS / "manual_teaching_v8.py"
if not PRODUCER_PATH.is_file():
    PRODUCER_PATH = PROJECT_TOOLS / "manual_teaching_v8.py"
sys.path[:0] = [str(CANDIDATE_TOOLS), str(PROJECT_TOOLS)]
spec = importlib.util.spec_from_file_location("manual_teaching_v8_candidate", PRODUCER_PATH)
teaching = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teaching)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def producer_fixture(tmp_path, *, field="note", value="G3", typed=False):
    run = tmp_path / ("a" * 32)
    evidence = run / "evidence"
    evidence.mkdir(parents=True)
    row = ({"kind": "mask-field-value", "passed": True,
            "mask_fields": [{"field": field, "value": value, "layout": "overview_masks"}]}
           if typed else {"kind": "mask-field", "passed": True, "expected": {"screen": [[field, value]]}})
    pixels = bytes(128 * 64 * 4)
    frame_sha = sha_bytes(pixels)
    doc = {"kind": "documentation-frame", "name": "manual/M-MASK-008/default",
           "semantic_assertions": 1, "passed": True, "sha256": frame_sha}
    results = [row, doc]
    grid = [0] * 128
    inputs = [{"type": "enc", "n": 3, "delta": 2}]
    step = {"id": "default", "inputs": inputs, "expect": {},
            "output": {"binding": {"assertion_index": 0, "assertion": row,
                                     "assertion_sha256": sha_bytes(canonical(row)),
                                     "trace_sha256": sha_bytes(canonical(inputs)),
                                     "grid_sha256": sha_bytes(bytes(grid))}, "grid": grid}}
    start = {"id": "route", "inputs": [], "expect": {}, "output": {"grid": grid}}
    (evidence / "results.json").write_text(json.dumps(results), encoding="utf-8")
    for relative, payload in (("native/identity.json", {"native": True}),
                              ("recipe.json", {"recipe": "fixture"}),
                              ("native/cleanup.json", {"cleanup": True})):
        path = evidence / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    session = "native-session-mask-fixture"
    (evidence / "observations.json").write_text(json.dumps([{
        "session_id": session, "backend": "native", "fidelity": "native-norns",
        "state": {"grid": grid, "frame": {"width": 128, "height": 64, "format": "BGRA8",
                "pixels_base64": base64.b64encode(pixels).decode(), "sha256": frame_sha}},
    }]), encoding="utf-8")
    files = {"results_sha256": evidence / "results.json", "identity_sha256": evidence / "native/identity.json",
             "recipe_sha256": evidence / "recipe.json", "cleanup_sha256": evidence / "native/cleanup.json"}
    evidence_meta = {key: sha_bytes(path.read_bytes()) for key, path in files.items()}
    scene = {"id": "mask-precedence", "behaviour_case": "M-MASK-008", "steps": [start, step],
             "evidence": {"path": str(evidence), **evidence_meta,
                 "session_context": {"finished": True, "cleanup_verified": True,
                                     "held_inputs": [], "session_id": session}}}
    native = {"contract_schema": "mosaic-native-transition-v3", "transition_scope": "interval",
        "scene": {"id": scene["id"], "behaviour_case": scene["behaviour_case"], "evidence": scene["evidence"]},
        "from_step_id": "route", "to_step_id": "default",
        "scene_input_prefix": [{"step_id": "route", "inputs": []}, {"step_id": "default", "inputs": inputs}],
        "step_interval": [start, step], "from_step": start, "to_step": step}
    return scene, native


def binding(field="note", value="G3"):
    return {"id": "set-g3", "kind": "select-value", "control": "E3", "field_label": "Note",
            "label": "Set Note to G3", "value": value, "direction": "clockwise", "mask_field": field}


def run_producer(tmp_path, *, action_field="note", action_value="G3", readout_field="note", readout_value="G3", typed=False):
    scene, native = producer_fixture(tmp_path, field=readout_field, value=readout_value, typed=typed)
    actions = [binding(action_field, action_value),
               {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "default", "label": "Preview"}]
    authored = {"transition_scope": "interval", "from_step_id": "route", "actions": actions,
        "semantic_requires": {"public_readout_equals": {"mask_fields": [
            {"field": readout_field, "value": readout_value, "layout": "overview_masks"}]},
            "screen_contains": "G3"}, "human_outcome": "The channel default is G3."}
    book = {"scenes": {"mask-precedence": scene}, "learning_path": [],
            "features": [{"id": "masks", "scene_refs": ["mask-precedence"], "teaching_bindings": [
                {"id": "note-default-g3", "binding": {"status": "verified", "scene": "mask-precedence", "step": "default"},
                 "teaching_binding": authored}]}]}
    fake_native = lambda _scene, _from, _to, _scope: native
    with patch.object(teaching, "_native", fake_native), patch.object(teaching, "validate_semantics", return_value=True), \
         patch.object(teaching, "replay_held_controls", return_value=set()), patch.object(teaching, "validate_binding", return_value=True), \
         patch("manual_publication_verify.verify_cached_ui", return_value=True):
        return teaching.build_teaching_contracts(book, {"mask-precedence": {"sha256": "b" * 64}}, project_root=str(tmp_path))


def test_producer_build_resolves_full_source_scene_and_verified_expected_screen_projection(tmp_path):
    contracts = run_producer(tmp_path)
    result = contracts["feature:masks:note-default-g3"]
    cp = next(row for row in result["action_checkpoints"] if row["action_id"] == "set-g3")
    assert cp["checkpoint_step_id"] == "default"
    assert cp["proof"]["kind"] == "mask-field-value"
    assert cp["mask_readout_receipt"]["native"] is True
    assert result["semantic_requires"]["public_readout_equals"]["mask_fields"][0]["value"] == "G3"


@pytest.mark.parametrize("kwargs", [
    {"action_value": "D4"},
    {"action_field": "velocity"},
    {"readout_value": "D4"},
    {"readout_field": "velocity"},
])
def test_producer_rejects_mask_action_or_public_value_mismatch(tmp_path, kwargs):
    with pytest.raises(Exception):
        run_producer(tmp_path, **kwargs)


def test_producer_rejects_frame_bytes_that_no_longer_match_bound_documentation_frame(tmp_path):
    scene, _ = producer_fixture(tmp_path)
    observations = Path(scene["evidence"]["path"]) / "observations.json"
    rows = json.loads(observations.read_text(encoding="utf-8"))
    rows[0]["state"]["frame"]["pixels_base64"] = base64.b64encode(bytes([1]) * (128 * 64 * 4)).decode()
    observations.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(Exception):
        run_producer(tmp_path)


def test_producer_preserves_existing_typed_course_mask_readout(tmp_path):
    contracts = run_producer(tmp_path, typed=True)
    result = contracts["feature:masks:note-default-g3"]
    cp = next(row for row in result["action_checkpoints"] if row["action_id"] == "set-g3")
    assert cp["checkpoint_step_id"] == "default"
    assert "mask_readout_receipt" not in cp


def test_producer_rejects_wrong_value_in_existing_typed_course_mask_readout(tmp_path):
    scene, native = producer_fixture(tmp_path, field="note", value="D4", typed=True)
    req = {"public_readout_equals": {"mask_fields": [
        {"field": "note", "value": "G3", "layout": "overview_masks"}]}}
    with pytest.raises(Exception, match="Mask public readout"):
        teaching._validate_output(native, req)

import base64
import copy
import hashlib
import importlib.util
import json

import pytest

MODULE = __import__("pathlib").Path(__file__).parents[1] / "tools" / "manual_mask_public_readout.py"
SPEC = importlib.util.spec_from_file_location("manual_mask_public_readout_candidate", MODULE)
ADAPTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ADAPTER)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _fixture(tmp_path):
    run = tmp_path / ("a" * 32)
    evidence = run / "evidence"
    evidence.mkdir(parents=True)
    results = [
        {"kind": "mask-field", "passed": True, "expected": {"screen": [["velocity", "35"]]}},
        {"kind": "documentation-frame", "name": "manual/M-MASK-008/ghost-held",
         "semantic_assertions": 1, "passed": True, "sha256": ""},
    ]
    pixels = bytes(128 * 64 * 4)
    frame_sha = _sha(pixels)
    results[1]["sha256"] = frame_sha
    grid = [0] * 128
    assertion = results[0]
    step = {"id": "ghost-held", "inputs": [{"type": "grid", "x": 2, "y": 4, "state": 1}],
            "output": {"binding": {"assertion_index": 0, "assertion": assertion,
                                     "assertion_sha256": _sha(_canonical(assertion)),
                                     "trace_sha256": _sha(_canonical([{"type": "grid", "x": 2, "y": 4, "state": 1}])),
                                     "grid_sha256": hashlib.sha256(bytes(grid)).hexdigest()},
                        "grid": grid}}
    (evidence / "results.json").write_text(json.dumps(results), encoding="utf-8")
    for relative, payload in (("native/identity.json", {"native": True}),
                              ("recipe.json", {"recipe": "fixture"}),
                              ("native/cleanup.json", {"cleanup": True})):
        path = evidence / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")
    session = "native-session-1"
    (evidence / "observations.json").write_text(json.dumps([{
        "session_id": session, "backend": "native", "fidelity": "native-norns",
        "state": {"grid": grid, "frame": {"width": 128, "height": 64, "format": "BGRA8",
                                              "pixels_base64": base64.b64encode(pixels).decode(),
                                              "sha256": frame_sha}},
    }]), encoding="utf-8")
    paths = {"results_sha256": evidence / "results.json", "identity_sha256": evidence / "native/identity.json",
             "recipe_sha256": evidence / "recipe.json", "cleanup_sha256": evidence / "native/cleanup.json"}
    evidence_meta = {key: _sha(path.read_bytes()) for key, path in paths.items()}
    scene = {"id": "masks-overview", "behaviour_case": "M-MASK-008", "steps": [step],
             "evidence": {"path": str(evidence), **evidence_meta,
                          "session_context": {"finished": True, "cleanup_verified": True,
                                              "held_inputs": [], "session_id": session}}}
    def pixel_verifier(state, expected):
        return expected == {"mask_fields": [{"field": "velocity", "value": "35", "layout": "overview_masks"}]}
    return scene, pixel_verifier


def test_fresh_mask_receipt_binds_current_run_assertion_and_native_frame(tmp_path):
    scene, pixel_verifier = _fixture(tmp_path)
    receipt = ADAPTER.validate_current_scene(scene, "ghost-held", "velocity", "35", pixel_verifier)
    assert receipt["kind"] == "native-mask-public-readout-current-run-v1"
    assert receipt["native"] is True
    assert receipt["session_id"] == "native-session-1"


@pytest.mark.parametrize("mutation", ["wrong-value", "doc-order", "wrong-session", "changed-pixels", "pixel-oracle"])
def test_fresh_mask_receipt_rejects_broken_source_or_pixel_link(tmp_path, mutation):
    scene, pixel_verifier = _fixture(tmp_path)
    if mutation == "wrong-value":
        scene["steps"][0]["output"]["binding"]["assertion"]["expected"]["screen"] = [["velocity", "80"]]
    elif mutation == "doc-order":
        result_path = __import__("pathlib").Path(scene["evidence"]["path"]) / "results.json"
        rows = json.loads(result_path.read_text())
        rows.reverse()
        result_path.write_text(json.dumps(rows))
        scene["evidence"]["results_sha256"] = _sha(result_path.read_bytes())
    elif mutation == "wrong-session":
        scene["evidence"]["session_context"]["session_id"] = "other-session"
    elif mutation == "changed-pixels":
        obs_path = __import__("pathlib").Path(scene["evidence"]["path"]) / "observations.json"
        rows = json.loads(obs_path.read_text())
        rows[0]["state"]["frame"]["pixels_base64"] = base64.b64encode(bytes([1]) * (128 * 64 * 4)).decode()
        obs_path.write_text(json.dumps(rows))
    else:
        pixel_verifier = lambda _state, _expected: False
    with pytest.raises(ADAPTER.MaskReadoutError):
        ADAPTER.validate_current_scene(scene, "ghost-held", "velocity", "35", pixel_verifier)

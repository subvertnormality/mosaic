import hashlib
import json

from manual_reader_projection import build_projection
import manual_teaching_v8
from manual_teaching_v8_contract import native_transition_hash_v8


def _midi_log(path):
    rows = []
    for index in range(1, 257):
        if index in (179, 180, 181):
            port, data = index - 178, [250]
        elif index in (254, 255, 256):
            port, data = index - 253, [252]
        else:
            port, data = 3, [192, 0]
        rows.append({"kind": 11, "index": index, "sequence": index, "port": port, "bytes": data})
    raw = b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in rows)
    (path / "native-events.jsonl").write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _scene(scene_id, evidence, steps):
    return {"id": scene_id, "title": scene_id, "behaviour_case": "M-TEST-001",
        "evidence": evidence, "steps": steps}

def _output(grid, assertion, midi=None):
    return {"grid": grid, "binding": {"assertion": assertion},
        "midi": midi or {"events": [], "total": 0, "truncated": False}}

def _binding_fixture(tmp_path):
    event_sha = _midi_log(tmp_path)
    (tmp_path / "native").mkdir(exist_ok=True)
    session = {"session_id": "run-projection", "finished": True, "cleanup_verified": True, "held_inputs": []}
    identity_raw = json.dumps({"session_id": "run-projection"}, separators=(",", ":")).encode()
    results_raw = b"[]\n"
    session_raw = json.dumps(session, separators=(",", ":")).encode()
    (tmp_path / "native" / "identity.json").write_bytes(identity_raw)
    (tmp_path / "results.json").write_bytes(results_raw)
    (tmp_path / "observations.json").write_text("[]", encoding="utf-8")
    (tmp_path / "native" / "cleanup.json").write_text("[{\"returncode\":0}]\n", encoding="utf-8")
    (tmp_path / "session-context.json").write_bytes(session_raw)
    evidence = {"path": str(tmp_path), "identity_sha256": hashlib.sha256(identity_raw).hexdigest(),
        "results_sha256": hashlib.sha256(results_raw).hexdigest(), "session_context_sha256": hashlib.sha256(session_raw).hexdigest(),
        "native_events_sha256": event_sha, "session_context": session}
    zero_grid = [0] * 128
    play_grid = zero_grid.copy(); play_grid[112] = 12
    stop_grid = zero_grid.copy(); stop_grid[112] = 2
    play_assert = {"kind": "probability-play-led", "phase": "active", "control": "play_stop", "state": "active", "passed": True}
    stop_assert = {"kind": "probability-play-led", "phase": "stopped", "control": "play_stop", "state": "off", "passed": True}
    target_assert = {"kind": "probability-zero-silence", "passed": True, "play_step_id": "play", "stop_step_id": "stop",
        "window_result_id": "silent", "seconds": 2.8, "logical_duration_s": 2.8, "window_start_index": 178,
        "window_end_index": 253, "positive_velocity_note_on_count": 0, "note_ons": [],
        "play_led_during": "active", "stop_led_after": "off"}
    zero_scene = _scene("zero-scene", evidence, [
        {"id": "always", "title": "Before play", "caption": "Before play", "inputs": [], "expect": {"screen": []}, "output": _output(zero_grid, {"kind": "baseline"})},
        {"id": "play", "title": "Play", "caption": "Play", "inputs": [{"type": "grid", "x": 1, "y": 8, "state": 1}, {"type": "grid", "x": 1, "y": 8, "state": 0}], "expect": {"screen": []},
            "output": _output(play_grid, play_assert, {"events": [{"port": 1, "bytes": [250]}, {"port": 2, "bytes": [250]}, {"port": 3, "bytes": [250]}], "total": 3, "truncated": False})},
        {"id": "stop", "title": "Stop", "caption": "Stop", "inputs": [{"type": "advance", "nanoseconds": 2800000000}, {"type": "grid", "x": 1, "y": 8, "state": 1}, {"type": "grid", "x": 1, "y": 8, "state": 0}], "expect": {"screen": []},
            "output": _output(stop_grid, stop_assert, {"events": [{"port": 1, "bytes": [252]}, {"port": 2, "bytes": [252]}, {"port": 3, "bytes": [252]}], "total": 3, "truncated": False})},
        {"id": "silent", "title": "Zero probability", "caption": "Zero probability", "inputs": [], "expect": {"screen": []}, "output": _output(stop_grid, target_assert)},
    ])
    plain_scene = _scene("plain-scene", evidence, [
        {"id": "plain-start", "title": "Start", "caption": "Start", "inputs": [], "expect": {"screen": []}, "output": _output(zero_grid, {"kind": "baseline"})},
        {"id": "plain-target", "title": "Target", "caption": "Target", "inputs": [{"type": "grid", "x": 2, "y": 2, "state": 1}, {"type": "grid", "x": 2, "y": 2, "state": 0}],
            "expect": {"screen": []}, "output": _output(zero_grid, {"kind": "plain"})},
    ])
    silence = {"id": "zero-play", "binding": {"scene": "zero-scene", "step": "silent", "status": "verified"},
        "teaching_binding": {"from_step_id": "always", "transition_scope": "interval",
            "actions": [{"id": "play-window", "kind": "play-note-silence", "play_step_id": "play", "stop_step_id": "stop",
                "window_result_id": "silent", "window_duration_s": 2.8, "label": "Play the zero-probability pattern"},
                {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "silent", "label": "Review the result"}],
            "semantic_requires": {"play_note_silence_at_target": True}, "human_outcome": "No positive-velocity note-on occurs during the window.",
            "practice_prompt": "Play, wait for the measured window, and stop."}}
    plain = {"id": "plain", "binding": {"scene": "plain-scene", "step": "plain-target", "status": "verified"},
        "teaching_binding": {"from_step_id": "plain-start", "transition_scope": "interval",
            "actions": [{"id": "tap", "kind": "tap-grid", "x": 2, "y": 2, "label": "Tap the captured cell"},
                {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "plain-target", "label": "Review the result"}],
            "semantic_requires": {"grid_cells": [{"x": 2, "y": 2, "level": 0}]}, "human_outcome": "The captured grid state is shown.",
            "practice_prompt": "Tap the marked cell and compare the result."}}
    book = {"schema_version": 1, "features": [
        {"id": "probability", "title": "Probability", "scene_refs": ["zero-scene"], "teaching_bindings": [silence]},
        {"id": "other-feature", "title": "Other", "scene_refs": ["plain-scene"], "teaching_bindings": [plain]}],
        "scenes": {"zero-scene": zero_scene, "plain-scene": plain_scene}, "learning_path": []}
    return book


def test_build_projection_exports_exact_native_receipt_arrays_and_preserves_empty_contracts(tmp_path, monkeypatch):
    book = _binding_fixture(tmp_path)
    native_by_scene = {}
    original = manual_teaching_v8._native
    def capture_with_receipts(scene, from_id, to_id, scope):
        native = original(scene, from_id, to_id, scope)
        if scene["id"] == "zero-scene":
            native["mask_readout_receipts"] = [{"kind": "mask-readout", "scene_id": "zero-scene"}]
            native["parameter_readout_receipts"] = [{"kind": "parameter-readout", "scene_id": "zero-scene"}]
        native_by_scene[scene["id"]] = native
        return native
    monkeypatch.setattr(manual_teaching_v8, "_native", capture_with_receipts)
    index, _ = build_projection(book, {"examples": []})
    contract = index["teaching_contracts"]["feature:probability:zero-play"]
    feature = next(row for row in index["features"] if row["id"] == "probability")
    lesson = feature["teaching_bindings"][0]
    native = native_by_scene["zero-scene"]
    assert contract["native_transition_contract_sha256"] == native_transition_hash_v8(native)
    for field in ("mask_readout_receipts", "parameter_readout_receipts", "play_note_silence_receipts"):
        assert contract[field] == native[field]
        assert lesson[field] == native[field]
    assert contract["play_note_silence_receipts"][0]["window_event_count"] == 75
    plain_contract = index["teaching_contracts"]["feature:other-feature:plain"]
    plain_lesson = next(row for row in index["features"] if row["id"] == "other-feature")["teaching_bindings"][0]
    for field in ("mask_readout_receipts", "parameter_readout_receipts", "play_note_silence_receipts"):
        assert field not in plain_contract
        assert field not in plain_lesson

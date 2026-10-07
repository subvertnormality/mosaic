import hashlib
import json

import pytest

from manual_teaching_v8 import (
    Error, _export_native_receipts, _validate_actions,
)
from manual_teaching_v8_contract import native_transition_hash_v8


def _fixture(tmp_path):
    rows = []
    for index in range(1, 257):
        if index in (179, 180, 181):
            port, data = index - 178, [250]
        elif index in (254, 255, 256):
            port, data = index - 253, [252]
        else:
            port, data = 3, [192, 0]
        rows.append({"kind": 11, "index": index, "sequence": index, "port": port, "bytes": data, "logical_ns": index * 1000000})
    raw = b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in rows)
    (tmp_path / "native-events.jsonl").write_bytes(raw)
    (tmp_path / "native").mkdir(exist_ok=True)
    identity_raw = json.dumps({"session_id": "run-1"}, separators=(",", ":")).encode()
    results_raw = b"[]\n"
    cleanup_raw = b"[{\"returncode\":0}]\n"
    session = {"session_id": "run-1", "finished": True, "cleanup_verified": True, "held_inputs": []}
    session_raw = json.dumps(session, separators=(",", ":")).encode()
    (tmp_path / "native" / "identity.json").write_bytes(identity_raw)
    (tmp_path / "results.json").write_bytes(results_raw)
    (tmp_path / "observations.json").write_text("[]", encoding="utf-8")
    (tmp_path / "native" / "cleanup.json").write_bytes(cleanup_raw)
    (tmp_path / "session-context.json").write_bytes(session_raw)
    evidence = {"path": str(tmp_path), "native_events_sha256": hashlib.sha256(raw).hexdigest(),
        "identity_sha256": hashlib.sha256(identity_raw).hexdigest(), "results_sha256": hashlib.sha256(results_raw).hexdigest(),
        "session_context_sha256": hashlib.sha256(session_raw).hexdigest(), "session_context": session}
    def output(level, assertion, events):
        return {"grid": [level if i == 112 else 0 for i in range(128)],
                "binding": {"assertion": assertion},
                "midi": {"events": events, "total": len(events), "truncated": False}}
    play_assert = {"kind": "probability-play-led", "phase": "active", "control": "play_stop", "state": "active", "passed": True}
    stop_assert = {"kind": "probability-play-led", "phase": "stopped", "control": "play_stop", "state": "off", "passed": True}
    target_assert = {"kind": "probability-zero-silence", "passed": True, "play_step_id": "play", "stop_step_id": "stop",
        "window_result_id": "silent", "seconds": 2.8, "logical_duration_s": 2.8, "window_start_index": 178,
        "window_end_index": 253, "positive_velocity_note_on_count": 0, "note_ons": [],
        "play_led_during": "active", "stop_led_after": "off"}
    play = {"id": "play", "inputs": [{"type": "grid", "x": 1, "y": 8, "state": 1}, {"type": "grid", "x": 1, "y": 8, "state": 0}],
        "output": output(12, play_assert, [{"port": 1, "bytes": [250]}, {"port": 2, "bytes": [250]}, {"port": 3, "bytes": [250]}])}
    stop = {"id": "stop", "inputs": [{"type": "advance", "nanoseconds": 2800000000}, {"type": "grid", "x": 1, "y": 8, "state": 1}, {"type": "grid", "x": 1, "y": 8, "state": 0}],
        "output": output(2, stop_assert, [{"port": 1, "bytes": [252]}, {"port": 2, "bytes": [252]}, {"port": 3, "bytes": [252]}])}
    silent = {"id": "silent", "inputs": [], "output": output(0, target_assert, [])}
    start = {"id": "always", "inputs": [], "output": output(0, {"kind": "baseline"}, [])}
    native = {"contract_schema": "mosaic-native-transition-v3", "transition_scope": "interval",
        "scene": {"id": "probability-endpoints", "evidence": evidence},
        "from_step_id": "always", "to_step_id": "silent", "from_step": start, "to_step": silent,
        "step_interval": [start, play, stop, silent],
        "scene_input_prefix": [{"step_id": "always", "inputs": []}, {"step_id": "play", "inputs": play["inputs"]},
            {"step_id": "stop", "inputs": stop["inputs"]}, {"step_id": "silent", "inputs": []}]}
    actions = [{"id": "zero-play", "kind": "play-note-silence", "play_step_id": "play", "stop_step_id": "stop",
        "window_result_id": "silent", "window_duration_s": 2.8, "label": "Play the zero-probability pattern"},
        {"id": "preview", "kind": "preview-recorded-result", "target_step_id": "silent", "label": "Review the captured result"}]
    return native, actions, rows


def test_zero_note_proof_uses_same_session_global_event_window_and_exports_hashed_receipt(tmp_path):
    native, actions, _ = _fixture(tmp_path)
    checkpoints = _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})
    receipt = checkpoints[0]["proof"]
    assert receipt["window_start_index"] == 178
    assert receipt["window_end_index"] == 253
    assert receipt["window_event_count"] == 75
    assert receipt["native_event_count"] == 256
    assert receipt["positive_velocity_note_on_count"] == 0
    assert receipt["play_input_refs"] == [{"step_id": "play", "index": 0}, {"step_id": "play", "index": 1}]
    assert receipt["stop_input_refs"] == [{"step_id": "stop", "index": 1}, {"step_id": "stop", "index": 2}]
    assert native["play_note_silence_receipts"] == [receipt]
    native["mask_readout_receipts"] = [{"kind": "mask-readout", "field": "velocity"}]
    native["parameter_readout_receipts"] = [{"kind": "parameter-readout", "slot": 2}]
    digest = native_transition_hash_v8(native)
    binding = _export_native_receipts(native, {"native_transition_contract_sha256": digest})
    assert binding["play_note_silence_receipts"] == native["play_note_silence_receipts"]
    assert binding["mask_readout_receipts"] == native["mask_readout_receipts"]
    assert binding["parameter_readout_receipts"] == native["parameter_readout_receipts"]
    assert binding["native_transition_contract_sha256"] == digest


def test_zero_note_proof_rejects_positive_note_and_changed_native_file(tmp_path):
    native, actions, rows = _fixture(tmp_path)
    rows[200]["bytes"] = [144, 65, 100]
    raw = b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in rows)
    (tmp_path / "native-events.jsonl").write_bytes(raw)
    native["scene"]["evidence"]["native_events_sha256"] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(Error, match="positive-velocity"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})
    native, actions, _ = _fixture(tmp_path)
    native["scene"]["evidence"]["native_events_sha256"] = "0" * 64
    with pytest.raises(Error, match="source identity"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})


def test_zero_note_proof_rejects_index_gap_and_play_stop_delta_boundary_mutations(tmp_path):
    native, actions, rows = _fixture(tmp_path)
    rows[200]["index"] = 999
    raw = b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in rows)
    (tmp_path / "native-events.jsonl").write_bytes(raw)
    native["scene"]["evidence"]["native_events_sha256"] = hashlib.sha256(raw).hexdigest()
    with pytest.raises(Error, match="ordered stream"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})
    native, actions, _ = _fixture(tmp_path)
    native["step_interval"][1]["output"]["midi"]["events"][0]["bytes"] = [251]
    with pytest.raises(Error, match="Play-step MIDI delta"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})
    native, actions, _ = _fixture(tmp_path)
    native["scene"]["evidence"]["session_context"]["held_inputs"] = ["grid"]
    with pytest.raises(Error, match="cleaned native session"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})


def test_zero_note_proof_rejects_changed_end_boundary_stop_delta_and_missing_receipt_exports(tmp_path):
    native, actions, _ = _fixture(tmp_path)
    native["to_step"]["output"]["binding"]["assertion"]["window_end_index"] = 252
    with pytest.raises(Error, match="Stop-step MIDI delta"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})
    native, actions, _ = _fixture(tmp_path)
    native["step_interval"][2]["output"]["midi"]["events"][0]["bytes"] = [250]
    with pytest.raises(Error, match="Stop-step MIDI delta"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})
    assert _export_native_receipts({}, {"native_transition_contract_sha256": "x"}) == {"native_transition_contract_sha256": "x"}


def test_zero_note_proof_rejects_foreign_session_identity_and_wrong_evidence_path(tmp_path):
    native, actions, _ = _fixture(tmp_path)
    native["scene"]["evidence"]["session_context"]["session_id"] = "foreign-session"
    with pytest.raises(Error, match="source identity audit"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})
    native, actions, _ = _fixture(tmp_path)
    foreign = tmp_path / "foreign-session-path"
    foreign.mkdir()
    (foreign / "native-events.jsonl").write_bytes((tmp_path / "native-events.jsonl").read_bytes())
    native["scene"]["evidence"]["path"] = str(foreign)
    with pytest.raises(Error, match="source identity audit"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})


def test_zero_note_proof_accepts_the_real_capture_layout(tmp_path):
    """Real captures keep native-events.jsonl under native/ and list channel traffic only in each per-step delta,
    the Stop delta being everything since the Play checkpoint."""
    native, actions, rows = _fixture(tmp_path)
    (tmp_path / "native").mkdir(exist_ok=True)
    (tmp_path / "native" / "native-events.jsonl").write_bytes((tmp_path / "native-events.jsonl").read_bytes())
    (tmp_path / "native-events.jsonl").unlink()
    channel = {"port": 3, "bytes": [192, 0]}
    window_channel = [row for row in rows[178:253] if len(row["bytes"]) > 1]
    play, stop = native["step_interval"][1], native["step_interval"][2]
    play["output"]["midi"] = {"events": [channel] * 4, "total": 4, "truncated": False}
    remaining = len(window_channel) - 4
    stop["output"]["midi"] = {"events": [channel] * remaining, "total": remaining, "truncated": False}
    checkpoints = _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})
    assert checkpoints[0]["proof"]["window_event_count"] == 75
    stop["output"]["midi"] = {"events": [channel] * (remaining + 1), "total": remaining + 1, "truncated": False}
    with pytest.raises(Error, match="Stop-step MIDI delta"):
        _validate_actions({"actions": actions}, native, "silent", {"play_note_silence_at_target": True})

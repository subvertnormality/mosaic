import copy
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pytest
import yaml

from manual_parameter_recording_readout import (
    FIXTURE_ARCHIVE_SHA256,
    FIXTURE_MEMBER_SHA256,
    RecordingReadoutError,
    extract_pinned_fixture,
    verify_parameter_recording_checkpoint,
)
from manual_publication_verify import verify_cached_ui

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "tests/fixtures/manual-mrec-parameter-recording-v1.zip"


@pytest.fixture(scope="module")
def capture(tmp_path_factory):
    destination = tmp_path_factory.mktemp("mrec-portable") / "fixture"
    root = extract_pinned_fixture(ARCHIVE, destination)
    report = json.loads((root / "manual/generated/reference-parameter-recording-scenes.json").read_text())
    scene = next(item for item in report["scenes"] if item["id"] == "record-parameter-lock")
    step = next(item for item in scene["steps"] if item["id"] == "recorded-lock")
    evidence = root / "evidence/M-REC-PARAM-001-base-midi"
    results = json.loads((evidence / "results.json").read_text())
    observations = json.loads((evidence / "observations.json").read_text())
    plan_doc = yaml.safe_load((root / "manual/scene-plans-options.yaml").read_text())
    plan_scene = next(item for item in plan_doc["scenes"] if item["id"] == scene["id"])
    plan_step = next(item for item in plan_scene["steps"] if item["id"] == step["id"])
    return root, scene, step, plan_step, results, observations, evidence


def audit(capture, *, step=None, plan_step=None, results=None, observations=None, evidence=None):
    _, scene, original_step, original_plan, original_results, original_observations, original_evidence = capture
    return verify_parameter_recording_checkpoint(
        step or original_step,
        original_plan if plan_step is None else plan_step,
        scene,
        original_results if results is None else results,
        original_observations if observations is None else observations,
        original_evidence if evidence is None else evidence,
        "controlled-experimental",
        verify_cached_ui,
    )


def copy_evidence(capture, tmp_path):
    target = tmp_path / "evidence-copy"
    shutil.copytree(capture[-1], target)
    return target


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows))


def test_actual_native_readout_and_complete_recipe_window_pass(capture):
    receipt = audit(capture)
    assert receipt["source_assertion_index"] < receipt["target_assertion_index"]
    assert receipt["replay"]["window_recipe_indices"] == [2058, 2759]
    assert len(receipt["replay"]["cc_event_indices"]) == 9
    assert len(receipt["replay"]["note_event_indices"]) == 9
    assert len(receipt["replay"]["note_off_event_indices"]) == 9
    assert receipt["replay"]["final_gate_truncated_at_stop"] is True


def test_native_note_on_lattice_is_exact(capture, tmp_path):
    evidence = copy_evidence(capture, tmp_path)
    receipt = audit(capture)
    path = evidence / "native/native-events.jsonl"
    rows = read_jsonl(path)
    selected = receipt["replay"]["note_event_indices"][1]
    row = next(item for item in rows if item.get("index") == selected)
    row["logical_ns"] += 1_000_000
    write_jsonl(path, rows)
    with pytest.raises(RecordingReadoutError, match="musical lattice"):
        audit(capture, evidence=evidence)


def test_native_natural_note_gate_is_exact(capture, tmp_path):
    evidence = copy_evidence(capture, tmp_path)
    receipt = audit(capture)
    path = evidence / "native/native-events.jsonl"
    rows = read_jsonl(path)
    selected = receipt["replay"]["note_off_event_indices"][0]
    row = next(item for item in rows if item.get("index") == selected)
    row["logical_ns"] += 1_000_000
    write_jsonl(path, rows)
    with pytest.raises(RecordingReadoutError, match="natural note gates"):
        audit(capture, evidence=evidence)


def test_final_note_off_is_tied_to_stop_message(capture, tmp_path):
    evidence = copy_evidence(capture, tmp_path)
    receipt = audit(capture)
    path = evidence / "native/native-events.jsonl"
    rows = read_jsonl(path)
    selected = receipt["replay"]["note_off_event_indices"][-1]
    row = next(item for item in rows if item.get("index") == selected)
    row["logical_ns"] -= 1_000_000
    write_jsonl(path, rows)
    with pytest.raises(RecordingReadoutError, match="truncated gate immediately tied to MIDI Stop"):
        audit(capture, evidence=evidence)


def test_copied_selected_param_row_must_be_exact(capture):
    _, _, step, _, results, _, _ = capture
    changed = copy.deepcopy(results)
    row = step["output"]["binding"]["assertion"]
    changed[row["source_assertion_index"]]["value"] = "63"
    with pytest.raises(RecordingReadoutError, match="exact copy"):
        audit(capture, results=changed)


def test_native_pixel_readout_cannot_be_relabelled(capture):
    _, _, _, plan_step, _, _, _ = capture
    changed = copy.deepcopy(plan_step)
    changed["native_readout"]["label"] = "Wrong label"
    with pytest.raises((RecordingReadoutError, ValueError)):
        audit(capture, plan_step=changed)


def test_native_replay_cc_expectation_is_exact(capture):
    _, _, _, plan_step, _, _, _ = capture
    changed = copy.deepcopy(plan_step)
    changed["native_replay"]["cc_values"][1] = 63
    with pytest.raises(RecordingReadoutError, match="route window|replay values"):
        audit(capture, plan_step=changed)


def test_extra_controller_event_inside_window_is_rejected(capture, tmp_path):
    evidence = copy_evidence(capture, tmp_path)
    path = evidence / "native/native-events.jsonl"
    rows = read_jsonl(path)
    insertion = next(i for i, row in enumerate(rows)
                     if row.get("kind") == 11 and row.get("port") == 1
                     and row.get("bytes") == [176, 1, 24]
                     and 105279844512068 < row.get("monotonic_ns", 0) < 105306867193630)
    timestamp = rows[insertion]["monotonic_ns"] - 50_000
    rows.insert(insertion, {"kind": 11, "port": 1, "bytes": [176, 1, 65],
                            "index": 433, "monotonic_ns": timestamp})
    write_jsonl(path, rows)
    with pytest.raises(RecordingReadoutError, match="complete native route window"):
        audit(capture, evidence=evidence)


def test_shifted_raw_window_boundary_is_rejected(capture):
    _, _, _, plan_step, _, _, _ = capture
    changed = copy.deepcopy(plan_step)
    changed["native_replay"]["window"]["start_recipe_index"] += 1
    with pytest.raises(RecordingReadoutError, match="recipe input boundaries"):
        audit(capture, plan_step=changed)


def test_duplicate_native_event_index_is_rejected(capture, tmp_path):
    evidence = copy_evidence(capture, tmp_path)
    path = evidence / "native/native-events.jsonl"
    rows = read_jsonl(path)
    selected = [i for i, row in enumerate(rows) if row.get("kind") == 11 and row.get("port") == 1
                and 105279844512068 < row.get("monotonic_ns", 0) < 105306867193630]
    rows[selected[1]]["index"] = rows[selected[0]]["index"]
    write_jsonl(path, rows)
    with pytest.raises(RecordingReadoutError, match="duplicate or out of order"):
        audit(capture, evidence=evidence)


def test_failed_owned_cleanup_is_rejected(capture, tmp_path):
    evidence = copy_evidence(capture, tmp_path)
    path = evidence / "native/cleanup.json"
    cleanup = json.loads(path.read_text())
    cleanup[0]["returncode"] = 1
    path.write_text(json.dumps(cleanup))
    with pytest.raises(RecordingReadoutError, match="cleanup is incomplete or unsuccessful"):
        audit(capture, evidence=evidence)


def test_dropped_native_midi_events_are_rejected(capture):
    _, _, _, _, _, observations, _ = capture
    changed = copy.deepcopy(observations)
    changed[-1]["state"]["midi_capture"]["dropped"] = 1
    with pytest.raises(RecordingReadoutError, match="dropped MIDI events"):
        audit(capture, observations=changed)


def test_fixture_archive_is_repo_relative_and_pinned(capture):
    assert ARCHIVE.is_file()
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == FIXTURE_ARCHIVE_SHA256
    assert len(FIXTURE_MEMBER_SHA256) == 12


def test_fixture_archive_rejects_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("../escaped.txt", b"outside")
    member = {"../escaped.txt": hashlib.sha256(b"outside").hexdigest()}
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with pytest.raises(RecordingReadoutError, match="unsafe member path"):
        extract_pinned_fixture(archive, tmp_path / "extract", expected_archive_sha256=digest,
                               expected_members=member)
    assert not (tmp_path / "escaped.txt").exists()


def test_plan_schema_requires_windowed_replay(capture):
    import jsonschema

    _, scene, step, _, _, _, _ = capture
    schema = json.loads((ROOT / "manual/case-scenes.schema.json").read_text())
    plan_root = yaml.safe_load((capture[0] / "manual/scene-plans-options.yaml").read_text())
    jsonschema.Draft7Validator(schema).validate(plan_root)
    broken = copy.deepcopy(plan_root)
    stage = next(s for s in broken["scenes"] if s["id"] == "record-parameter-lock")
    target = next(s for s in stage["steps"] if s["id"] == "recorded-lock")
    target["native_replay"]["window"].pop("stop_recipe_index")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(schema).validate(broken)
    broken_timing = copy.deepcopy(plan_root)
    timing_step = next(s for s in broken_timing["scenes"] if s["id"] == scene["id"])["steps"]
    recorded = next(s for s in timing_step if s["id"] == step["id"])
    recorded["native_replay"]["timing"].pop("natural_gate_ns")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft7Validator(schema).validate(broken_timing)


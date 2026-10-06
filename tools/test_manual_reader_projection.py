from __future__ import annotations

import copy
import hashlib
import json
import sys
import tarfile
from pathlib import Path

import pytest

CANDIDATE_TOOLS = Path(__file__).parent
sys.path.insert(0, str(CANDIDATE_TOOLS))
import manual_reader_projection as projection

ROOT = Path(__file__).parents[1]
PORTABLE_ASSETS = ROOT / "test-fixtures/reader-projection-portable-v1.tar.gz"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def portable_assets(tmp_path_factory):
    """Restore exact, pinned historical generated inputs and native fixtures to temp."""
    out = tmp_path_factory.mktemp("manual-reader-projection-assets")
    with tarfile.open(PORTABLE_ASSETS, "r:gz") as archive:
        root = out.resolve()
        for member in archive.getmembers():
            target = (out / member.name).resolve()
            if target != root and root not in target.parents:
                raise ValueError("portable fixture archive contains an unsafe path")
        archive.extractall(out)
    return {
        "root": out,
        "book": out / "inputs/manual/generated/book.json",
        "audio": out / "inputs/manual/generated/audio-scenes.json",
    }


@pytest.fixture(scope="module")
def sources(portable_assets):
    return load(portable_assets["book"]), load(portable_assets["audio"])


@pytest.fixture(scope="module")
def materialized(sources, portable_assets, tmp_path_factory):
    out = tmp_path_factory.mktemp("reader-projection")
    index = projection.write_projection(portable_assets["book"], portable_assets["audio"], out)
    return index, out, projection.Projection(index, out / "reader-chunks")


def test_index_preserves_reader_features_aliases_course_and_source_identity(sources, materialized, portable_assets):
    book, audio = sources
    index, _, _ = materialized
    assert index["features"] == book["features"]
    for key in ("aliases", "navigation", "course_title", "course_summary", "project", "learning_path"):
        assert index[key] == book[key]
    for key in ("edition", "source_sha256", "legacy_source_sha256", "complete_manual"):
        assert index[key] == book[key]
    assert index["canonical_inputs"] == {
        "book_json_sha256": hashlib.sha256(portable_assets["book"].read_bytes()).hexdigest(),
        "audio_scenes_json_sha256": hashlib.sha256(portable_assets["audio"].read_bytes()).hexdigest(),
    }
    assert index["audio_metadata"] == {key: value for key, value in audio.items() if key != "examples"}
    assert index["teaching_contracts"] == {}


def test_scene_search_projection_is_exact_and_all_full_chunks_round_trip(sources, materialized):
    book, audio = sources
    index, out, loaded = materialized
    assert index["inventory"]["scene_ids"] == list(book["scenes"])
    for scene_id, canonical in book["scenes"].items():
        summary = index["scenes"][scene_id]
        assert {key: summary[key] for key in ("id", "title", "behaviour_case", "profile")} == {
            key: canonical.get(key) for key in ("id", "title", "behaviour_case", "profile")
        }
        assert summary["steps"] == [
            {key: step.get(key) for key in ("id", "title", "caption")} for step in canonical["steps"]
        ]
        loaded_scene = loaded.load_scene(scene_id)
        assert loaded_scene == canonical
        ref = index["scene_chunks"][scene_id]
        assert hashlib.sha256((out / ref["path"]).read_bytes()).hexdigest() == ref["sha256"]


def test_search_records_match_current_reader_fields_for_every_feature(sources, materialized):
    book, _ = sources
    index, _, _ = materialized
    expected_scenes = book["scenes"]
    actual_scenes = index["scenes"]

    def search_records(feature, scenes):
        records = [
            {"title": feature["title"], "text": feature["summary"] + " " + feature["prose"], "section": None},
            *({"title": "Controls", "text": control["gesture"] + " — " + control["result"], "section": "reference"}
              for control in feature["controls"]),
            *({"title": detail["title"], "text": detail["text"], "section": "reference"}
              for detail in feature["details"]),
            *({"title": recipe["title"], "text": recipe["text"], "section": "cookbook"}
              for recipe in feature["recipes"]),
        ]
        for ref in feature.get("scene_refs", []):
            scene_id = ref if isinstance(ref, str) else ref["id"]
            for step in scenes[scene_id]["steps"]:
                records.append({"title": step.get("title") or "Captured example", "text": step["caption"],
                                "scene": scene_id, "step": step["id"]})
        return records

    for feature in book["features"]:
        assert search_records(feature, expected_scenes) == search_records(feature, actual_scenes)


def test_all_audio_selector_fields_and_full_examples_round_trip(sources, materialized):
    _, audio = sources
    index, out, loaded = materialized
    expected = [
        {key: example[key] for key in ("id", "title", "purpose", "feature_ids", "course", "tracks") if key in example}
        for example in audio["examples"]
    ]
    assert index["audio_examples"] == expected
    assert index["inventory"]["audio_example_ids"] == [example["id"] for example in audio["examples"]]
    for example in audio["examples"]:
        assert loaded.load_audio(example["id"]) == example
        ref = index["audio_chunks"][example["id"]]
        assert hashlib.sha256((out / ref["path"]).read_bytes()).hexdigest() == ref["sha256"]


def test_rejects_duplicate_and_unsafe_ids_and_unknown_references(sources):
    book, audio = sources
    duplicate = copy.deepcopy(book)
    duplicate["features"].append(copy.deepcopy(duplicate["features"][0]))
    with pytest.raises(projection.ProjectionError, match="duplicate book features ID"):
        projection.build_projection(duplicate, audio)

    unsafe = copy.deepcopy(book)
    scene = next(iter(unsafe["scenes"].values()))
    unsafe["scenes"]["../escape"] = unsafe["scenes"].pop(scene["id"])
    with pytest.raises(projection.ProjectionError, match="unsafe or invalid ID"):
        projection.build_projection(unsafe, audio)

    dangling = copy.deepcopy(book)
    dangling["features"][0]["scene_refs"] = ["missing-scene"]
    with pytest.raises(projection.ProjectionError, match="unknown scene reference"):
        projection.build_projection(dangling, audio)

    duplicate_audio = copy.deepcopy(audio)
    duplicate_audio["examples"].append(copy.deepcopy(duplicate_audio["examples"][0]))
    with pytest.raises(projection.ProjectionError, match="duplicate audio examples ID"):
        projection.build_projection(book, duplicate_audio)


def test_projection_validation_rejects_stale_files_corruption_and_changed_sources(sources, materialized, portable_assets, tmp_path):
    book, audio = sources
    index, out, loaded = materialized
    index_path = out / "reader-index.json"
    chunk_root = out / "reader-chunks"
    summary = projection.validate_projection(index_path, chunk_root, portable_assets["book"], portable_assets["audio"])
    assert summary["passed"] is True
    assert summary["scene_count"] == len(book["scenes"])
    assert summary["audio_example_count"] == len(audio["examples"])
    assert summary["reader_index_sha256"] == hashlib.sha256(index_path.read_bytes()).hexdigest()

    extra = chunk_root / "stale.json"
    extra.write_text("{}", encoding="utf-8")
    with pytest.raises(projection.ProjectionError, match="inventory"):
        projection.validate_projection(index_path, chunk_root, portable_assets["book"], portable_assets["audio"])
    extra.unlink()

    scene_ref = next(iter(index["scene_chunks"].values()))
    chunk_path = out / scene_ref["path"]
    original = chunk_path.read_bytes()
    chunk_path.write_bytes(original + b" ")
    with pytest.raises(projection.ProjectionError, match="digest mismatch"):
        projection.validate_projection(index_path, chunk_root, portable_assets["book"], portable_assets["audio"])
    chunk_path.write_bytes(original)

    original_index = index_path.read_bytes()
    index_path.write_bytes(original_index.replace(b'"projection_schema":1', b'"projection_schema":2', 1))
    with pytest.raises(projection.ProjectionError, match="reader index"):
        projection.validate_projection(index_path, chunk_root, portable_assets["book"], portable_assets["audio"])
    index_path.write_bytes(original_index)

    changed_book = copy.deepcopy(book)
    changed_book["title"] += " changed"
    with pytest.raises(projection.ProjectionError, match="reader index"):
        projection.validate_projection(index_path, chunk_root, changed_book, audio)

    projection.validate_projection(index_path, chunk_root, portable_assets["book"], portable_assets["audio"])


def test_chunk_paths_reject_traversal_absolute_and_backslash(sources, materialized):
    _, out, _ = materialized
    root = out / "reader-chunks"
    for path in ("../outside.json", "/absolute.json", "reader-chunks\\escape.json"):
        with pytest.raises(projection.ProjectionError):
            projection._safe_chunk_path(root, path)


def test_loader_checks_digest_before_returning_chunk(sources, materialized, portable_assets):
    _, out, _ = materialized
    loaded = projection.load_projection(out / "reader-index.json", portable_assets["book"], portable_assets["audio"])
    scene_id = next(iter(loaded.index["scene_chunks"]))
    ref = loaded.index["scene_chunks"][scene_id]
    chunk_path = out / ref["path"]
    original = chunk_path.read_bytes()
    chunk_path.write_bytes(original[:-2] + b"xx")
    with pytest.raises(projection.ProjectionError, match="digest mismatch"):
        loaded.load_scene(scene_id)
    chunk_path.write_bytes(original)


def test_inventory_scanner_ignores_reader_index_as_a_native_capture(tmp_path):
    import manual_inventory

    generated = tmp_path / "manual/generated"
    generated.mkdir(parents=True)
    (generated / "reader-index.json").write_text(json.dumps({
        "scenes": {"metadata-only": {"id": "metadata-only", "steps": []}}
    }), encoding="utf-8")
    (generated / "reference-scenes.json").write_text(json.dumps({
        "clock_mode": "controlled-experimental",
        "scenes": [{"id": "native-capture"}],
    }), encoding="utf-8")
    assert set(manual_inventory.native_catalogue(tmp_path)) == {"native-capture"}


def test_teaching_contract_is_derived_from_raw_adjacent_native_steps(sources):
    from manual_teaching import build_native_transition, build_teaching_contracts
    from manual_teaching_contract import native_transition_hash

    book, _ = sources
    authored_book = copy.deepcopy(book)
    authored_book["learning_path"][0]["stages"].append({
        "id": "fixture-held-mask-step",
        "binding": {"status": "controlled-verified", "scene": "mask-precedence", "step": "step-one"},
        "teaching_binding": {
            "from_step_id": "default",
            "semantic_requires": {
                "screen_contains": [["note", "C4"]],
                "held_controls_at_target": [{"type": "grid", "x": 1, "y": 4}],
            },
            "actions": [
                {"id": "hold-step-one", "kind": "hold-grid", "x": 1, "y": 4, "label": "Hold step 1"},
                {"id": "preview-step-one", "kind": "preview-recorded-result", "target_step_id": "step-one", "label": "View recorded result"},
            ],
            "human_outcome": "Step 1 shows C4 while the captured control remains held.",
                "preserve_holds_at_target": True,
        },
    })
    refs = {"mask-precedence": {"path": "reader-chunks/scenes/mask.json", "sha256": "a" * 64}}
    result = build_teaching_contracts(authored_book, refs)
    binding = result["fixture-held-mask-step"]
    native = build_native_transition(authored_book["scenes"]["mask-precedence"], "default", "step-one")
    assert binding["native_transition_contract_sha256"] == native_transition_hash(native)
    assert binding["scene_chunk_sha256"] == refs["mask-precedence"]["sha256"]
    assert binding["semantic_verified"] is True
    assert binding["actions"] == authored_book["learning_path"][0]["stages"][-1]["teaching_binding"]["actions"]


def test_teaching_contract_rejects_false_semantics_or_raw_held_release(sources):
    from manual_teaching import TeachingContractError, build_teaching_contracts

    book, _ = sources
    authored_book = copy.deepcopy(book)
    stage = {
        "id": "fixture-held-mask-step",
        "binding": {"status": "controlled-verified", "scene": "mask-precedence", "step": "step-one"},
        "teaching_binding": {
            "from_step_id": "default",
            "semantic_requires": {
                "screen_contains": [["note", "C4"]],
                "held_controls_at_target": [{"type": "grid", "x": 1, "y": 4}],
            },
            "actions": [{"id": "hold", "kind": "hold-grid", "x": 1, "y": 4, "label": "Hold"}],
            "human_outcome": "The captured result shows C4.",
            "preserve_holds_at_target": True,
        },
    }
    authored_book["learning_path"][0]["stages"].append(copy.deepcopy(stage))
    refs = {"mask-precedence": {"path": "scene.json", "sha256": "b" * 64}}
    authored_book["scenes"]["mask-precedence"]["steps"][2]["expect"]["screen"] = [["note", "C#4"]]
    with pytest.raises(TeachingContractError, match="semantics mismatch"):
        build_teaching_contracts(authored_book, refs)

    authored_book = copy.deepcopy(book)
    authored_book["learning_path"][0]["stages"].append(stage)
    # The target frame remains bright; ordered raw event replay must still catch release.
    authored_book["scenes"]["mask-precedence"]["steps"][2]["inputs"].append(
        {"type": "grid", "x": 1, "y": 4, "state": 0}
    )
    assert authored_book["scenes"]["mask-precedence"]["steps"][2]["output"]["grid"][48] == 15
    with pytest.raises(TeachingContractError, match="semantics mismatch"):
        build_teaching_contracts(authored_book, refs)


def test_teaching_contract_rejects_missing_or_nonadjacent_endpoints(sources):
    from manual_teaching import TeachingContractError, build_teaching_contracts

    book, _ = sources
    authored_book = copy.deepcopy(book)
    authored_book["learning_path"][0]["stages"].append({
        "id": "fixture-nonadjacent",
        "binding": {"status": "controlled-verified", "scene": "mask-precedence", "step": "release-one"},
        "teaching_binding": {
            "from_step_id": "default",
            "semantic_requires": {"screen_contains": [["note", "G3"]]},
            "actions": [{"id": "preview", "kind": "preview-recorded-result", "target_step_id": "release-one", "label": "View"}],
            "human_outcome": "The recorded result returns to G3.",
        },
    })
    refs = {"mask-precedence": {"path": "scene.json", "sha256": "b" * 64}}
    with pytest.raises(TeachingContractError, match="adjacent"):
        build_teaching_contracts(authored_book, refs)


def test_real_course_mask_held_fixture_binds_ordered_edit_then_release(portable_assets, tmp_path):
    fixture = portable_assets["root"] / "test-fixtures" / "course-mask-held-transition-v2"
    receipt = load(fixture / "fixture-receipt.json")
    assert receipt["passed"] is True
    assert receipt["fixture_scope"].startswith("test-only historical")
    projection_fixture = projection.load_projection(
        fixture / "generated/reader-index.json",
        fixture / "book.fixture.json",
        fixture / "audio-scenes.fixture.json",
    )
    index = projection_fixture.index
    scene = projection_fixture.load_scene("course-masks")
    contract = index["teaching_contracts"]["masks-quiet"]
    assert contract["preserve_holds_at_target"] is False
    by_action = {row["action_id"]: row for row in contract["action_checkpoints"]}
    hold_edit = by_action["a02"]
    assert hold_edit["checkpoint_step_id"] == "masks-quiet-held"
    assert hold_edit["proof"] == {
        "kind": "field-value-with-held-grid",
        "field_label": "velocity",
        "value": "50",
        "held_grid": {"x": 13, "y": 4},
    }
    assert [ref["step_id"] for ref in hold_edit["raw_inputs"]] == ["masks-quiet-held"] * 3
    inputs = next(row for row in scene["steps"] if row["id"] == "masks-quiet-held")["inputs"]
    assert [inputs[ref["index"]] for ref in hold_edit["raw_inputs"]] == [
        {"type": "enc", "n": 2, "delta": 2},
        {"type": "grid", "x": 13, "y": 4, "state": 1},
        {"type": "enc", "n": 3, "delta": -2},
    ]
    mask_rows = next(row for row in scene["steps"] if row["id"] == "masks-quiet-held")["output"]["binding"]["assertion"]["mask_fields"]
    assert {"field": "velocity", "value": "50", "layout": "overview_masks"} in mask_rows
    release = by_action["a05"]
    assert release["checkpoint_step_id"] == "masks-quiet"
    assert release["proof"] == {"kind": "grid-release", "x": 13, "y": 4}
    assert contract["semantic_requires"]["held_controls_at_target"] == []


def test_real_course_mask_midpoint_fixture_keeps_held_cell_at_target(portable_assets):
    fixture = portable_assets["root"] / "test-fixtures" / "course-mask-quiet-held-midpoint-v3"
    receipt = load(fixture / "fixture-receipt.json")
    assert receipt["passed"] is True
    assert receipt["fixture_scope"].startswith("test-only fresh capture")
    projection_fixture = projection.load_projection(
        fixture / "generated/reader-index.json",
        fixture / "book.fixture.json",
        fixture / "audio-scenes.fixture.json",
    )
    index = projection_fixture.index
    scene = projection_fixture.load_scene("course-masks")
    contract = index["teaching_contracts"]["masks-quiet"]
    assert contract["to_step_id"] == "masks-quiet-held"
    assert contract["preserve_holds_at_target"] is True
    assert contract["semantic_requires"]["held_controls_at_target"] == [
        {"type": "grid", "x": 13, "y": 4}
    ]
    action = contract["action_checkpoints"][0]
    assert action["proof"] == {
        "kind": "field-value-with-held-grid",
        "field_label": "velocity",
        "value": "50",
        "held_grid": {"x": 13, "y": 4},
    }
    target = next(row for row in scene["steps"] if row["id"] == "masks-quiet-held")
    assertion = target["output"]["binding"]["assertion"]
    assert {"field": "velocity", "value": "50", "layout": "overview_masks"} in assertion["mask_fields"]
    assert assertion["params"]["held"] == [13]
    assert contract["semantic_requires"]["public_readout_equals"]["mask_fields"] == assertion["mask_fields"]


def test_real_course_mask_held_source_can_begin_with_exact_release(portable_assets):
    fixture = portable_assets["root"] / "test-fixtures" / "course-mask-held-source-release-v1"
    receipt = load(fixture / "fixture-receipt.json")
    index_path = fixture / "generated" / "reader-index.json"
    assert hashlib.sha256(index_path.read_bytes()).hexdigest() == receipt["reader_index_sha256"]
    loaded = projection.load_projection(index_path, fixture / "book.fixture.json", fixture / "audio-scenes.fixture.json")
    scene = loaded.load_scene("course-masks")
    steps = {row["id"]: row for row in scene["steps"]}
    source = steps["masks-quiet-held"]
    target = steps["masks-quiet"]
    assert source["output"]["binding"]["assertion"]["params"]["held"] == [13]
    assert target["output"]["binding"]["assertion"]["params"].get("held", []) == []
    assert target["inputs"][0] == {"type": "grid", "x": 13, "y": 4, "state": 0}
    contract = loaded.index["teaching_contracts"]["masks-held-source-release-test"]
    assert contract["from_step_id"] == "masks-quiet-held"
    assert contract["actions"][0]["kind"] == "release-grid"
    proof = contract["action_checkpoints"][0]
    assert proof["checkpoint_step_id"] == "masks-quiet"
    assert proof["raw_inputs"] == [{"step_id": "masks-quiet", "index": 0}]
    assert proof["proof"] == {"kind": "grid-release", "x": 13, "y": 4}
    assert contract["semantic_requires"]["held_controls_at_target"] == []
    assert contract["preserve_holds_at_target"] is False

    book = load(fixture / "book.fixture.json")
    from manual_teaching import build_teaching_contracts, TeachingContractError
    scene_rows = {"course-masks": scene}
    bad_action = copy.deepcopy(book)
    authored = bad_action["learning_path"][0]["stages"][0]["teaching_binding"]
    authored["actions"][0]["x"] = 12
    with pytest.raises(TeachingContractError):
        build_teaching_contracts(bad_action, scene_rows)
    missing_release = copy.deepcopy(book)
    authored = missing_release["learning_path"][0]["stages"][0]["teaching_binding"]
    authored["actions"] = [authored["actions"][-1]]
    with pytest.raises(TeachingContractError):
        build_teaching_contracts(missing_release, scene_rows)

"""Compile source-authored course actions into native-bound reader contracts."""
from __future__ import annotations

from typing import Any, Mapping

from manual_teaching_contract import native_transition_hash, validate_binding, validate_semantics


from manual_teaching_errors import TeachingContractError


def _step_contract(step: Mapping[str, Any]) -> dict:
    required = ("id", "inputs", "expect", "output")
    if any(key not in step for key in required):
        raise TeachingContractError("native transition step is missing source fields")
    return {key: step[key] for key in required}


def build_native_transition(scene: Mapping[str, Any], from_step_id: str, to_step_id: str) -> dict:
    """Build the v7 native contract from unchanged canonical capture fields."""
    steps = scene.get("steps")
    if not isinstance(steps, list) or not isinstance(scene.get("evidence"), dict):
        raise TeachingContractError("scene lacks ordered steps or native evidence")
    step_ids = [step.get("id") if isinstance(step, dict) else None for step in steps]
    if len(step_ids) != len(set(step_ids)):
        raise TeachingContractError("scene step IDs are missing or duplicated")
    try:
        from_index, to_index = step_ids.index(from_step_id), step_ids.index(to_step_id)
    except ValueError as exc:
        raise TeachingContractError("teaching endpoints are absent from native scene") from exc
    if from_index + 1 != to_index:
        raise TeachingContractError("teaching endpoints must be adjacent in the native scene")
    if not {"identity_sha256", "results_sha256"} <= set(scene["evidence"]):
        raise TeachingContractError("scene evidence lacks native identity/results digests")
    native_scene = {"id": scene["id"]}
    for key in ("behaviour_case", "evidence"):
        if key in scene:
            native_scene[key] = scene[key]
    prefix = []
    for step in steps[:to_index + 1]:
        inputs = step.get("inputs")
        if not isinstance(inputs, list):
            raise TeachingContractError("native scene inputs must be ordered lists")
        prefix.append({"step_id": step["id"], "inputs": inputs})
    return {
        "contract_schema": "mosaic-native-transition-v2",
        "scene": native_scene,
        "scene_input_prefix": prefix,
        "from_step": _step_contract(steps[from_index]),
        "to_step": _step_contract(steps[to_index]),
    }


def _validate_authoring(authored: Mapping[str, Any], to_step_id: str) -> dict:
    if not isinstance(authored, Mapping):
        raise TeachingContractError("teaching_binding must be an object")
    actions = authored.get("actions")
    if not isinstance(actions, list) or not actions:
        raise TeachingContractError("teaching_binding requires explicit actions")
    action_ids = set()
    for action in actions:
        if not isinstance(action, dict) or not all(
            isinstance(action.get(key), str) and action[key].strip()
            for key in ("id", "kind", "label")
        ):
            raise TeachingContractError("each teaching action needs an id, kind and label")
        if action["id"] in action_ids:
            raise TeachingContractError("teaching action IDs must be unique")
        action_ids.add(action["id"])
        if action.get("kind") == "preview-recorded-result" and action.get("target_step_id") != to_step_id:
            raise TeachingContractError("preview action must point at the bound target step")
    requirements = authored.get("semantic_requires")
    allowed = {"screen_contains", "midi_phrase_contains", "held_controls_at_target"}
    if not isinstance(requirements, dict) or not set(requirements) <= allowed or not requirements:
        raise TeachingContractError("semantic_requires must use the verified native predicates")
    if not any(requirements.get(key) for key in allowed):
        raise TeachingContractError("semantic_requires must include at least one native predicate")
    outcome = authored.get("human_outcome")
    if not isinstance(outcome, str) or not outcome.strip():
        raise TeachingContractError("teaching_binding requires a human_outcome")
    return {
        "semantic_requires": requirements,
        "actions": actions,
        "human_outcome": outcome,
    }


def build_teaching_contracts(book: Mapping[str, Any], scene_chunks: Mapping[str, dict]) -> dict:
    """Return every verified authored contract, or fail closed on any authored gap."""
    scenes = book.get("scenes")
    chapters = book.get("learning_path", [])
    if not isinstance(scenes, dict) or not isinstance(chapters, list):
        raise TeachingContractError("book scene/course data has an invalid shape")
    candidates = []
    native_by_stage = {}
    for chapter in chapters:
        for stage in chapter.get("stages", []):
            authored = stage.get("teaching_binding")
            if authored is None:
                continue
            stage_id = stage.get("id")
            target = stage.get("binding")
            if not isinstance(stage_id, str) or not stage_id or stage_id in native_by_stage:
                raise TeachingContractError("teaching stage IDs must be unique and nonempty")
            if not isinstance(target, dict) or target.get("status") not in ("verified", "controlled-verified"):
                raise TeachingContractError("authored teaching stage lacks a verified scene binding")
            scene_id, to_step_id = target.get("scene"), target.get("step")
            if not isinstance(scene_id, str) or not isinstance(to_step_id, str) or scene_id not in scenes:
                raise TeachingContractError("authored teaching stage references an unknown native scene")
            if not isinstance(authored, dict):
                raise TeachingContractError("teaching_binding must be an object")
            from_step_id = authored.get("from_step_id")
            if not isinstance(from_step_id, str) or not from_step_id:
                raise TeachingContractError("teaching_binding requires from_step_id")
            native = build_native_transition(scenes[scene_id], from_step_id, to_step_id)
            values = _validate_authoring(authored, to_step_id)
            if not validate_semantics(native, values["semantic_requires"]):
                raise TeachingContractError("authored semantic requirements fail against native transition")
            ref = scene_chunks.get(scene_id)
            if not isinstance(ref, dict) or not isinstance(ref.get("sha256"), str):
                raise TeachingContractError("teaching stage has no verified scene chunk digest")
            binding = {
                "scene_id": scene_id,
                "from_step_id": from_step_id,
                "to_step_id": to_step_id,
                "native_transition_contract_sha256": native_transition_hash(native),
                "scene_chunk_sha256": ref["sha256"],
                "semantic_verified": True,
                **values,
            }
            native_by_stage[stage_id] = native
            candidates.append((stage_id, native, binding))
    result = {}
    for stage_id, native, binding in candidates:
        if not validate_binding(binding, native, [candidate for _, _, candidate in candidates]):
            raise TeachingContractError("native teaching transition binding is stale or ambiguous: " + stage_id)
        result[stage_id] = binding
    return result


def validate_teaching_contracts(book: Mapping[str, Any], scene_chunks: Mapping[str, dict], supplied: Any) -> dict:
    expected = build_teaching_contracts(book, scene_chunks)
    if supplied != expected:
        raise TeachingContractError("reader teaching-contract map is stale, missing, extra or altered")
    return expected


# Use the external v8 adapter; the copied v7 digest helper stays immutable.
from manual_teaching_v8 import build_teaching_contracts, validate_teaching_contracts

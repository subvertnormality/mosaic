"""Strict, external-candidate proof for Trig Params public readouts.

This helper is intentionally separate from the generic field/mask predicates.
It derives a source-bound assignment/readout receipt from the exact captured
scene, result rows and native observations.  The caller supplies the existing
frame_oracle module; this module does not synthesize or weaken pixel oracles.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path


SCHEMA_VERSION = 1
SOURCE_CONTRACT = {
    "lib/ui_live.lua": "bbdee8cf4cef9eedac03bf435095b0324fee31d6fcb81714bc6d7a06e54242ab",
    "lib/pages/channel_edit_page/channel_edit_navigation.lua": "158fc5a26c68e0ac6da4b86e5e2b848d803bcfb5f6828b6719ce0be9f92ea54e",
    "lib/pages/channel_edit_page/channel_edit_page_ui_handlers.lua": "f5e2035cec55c7ab568802dd595e6b9ac779384305c70de4fb2551a64a96dde6",
    "lib/pages/channel_edit_page/channel_edit_parameters.lua": "435fe1841f32efc06cf8a09bfadddb9ca8c366f106d02d5b0105f69cf6a911f5",
    "lib/devices/param_manager.lua": "a685409220e194f430976ae87839e6a42c52ebb5ed8e8e3982907f9cb6ded6a8",
    "lib/devices/param_lock_assignments.lua": "ae58d470aa e22ccbb99ed083464aa7ec96878473d393298dd8cb4c3565147770".replace(" ", ""),
    "tests/behaviour/ui.py": "1382109a56d940e3abae4ad6585b8c51d801b05b63665b41a432725072c56d8e",
    "tests/behaviour/frame_oracle.py": "44c29d29034eb5060501be628394331312a9e23d41bdc45903e48983b5059b1e",
}

REQUEST_KEYS = {
    "schema_version", "parameter_label", "display_label", "slot", "value",
    "marker", "picker_step_id", "assignment_step_id", "readout_step_id",
    "effect_step_id", "effect_assertion",
}


class ParameterReadoutError(ValueError):
    pass


def _canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require(condition, message):
    if not condition:
        raise ParameterReadoutError(message)


def validate_request(request):
    _require(isinstance(request, dict) and set(request) == REQUEST_KEYS,
             "parameter_readout_equals has unknown or missing fields")
    _require(request["schema_version"] == SCHEMA_VERSION, "unsupported parameter readout schema")
    for name in ("parameter_label", "display_label", "value", "picker_step_id",
                 "assignment_step_id", "readout_step_id", "effect_step_id"):
        _require(isinstance(request[name], str) and request[name].strip(),
                 "parameter readout requires concrete " + name)
    _require(type(request["slot"]) is int and request["slot"] >= 1,
             "parameter readout slot must be a positive integer")
    _require(request["marker"] is None or request["marker"] in ("L", "S"),
             "parameter readout marker must be null, L, or S")
    _require(isinstance(request["effect_assertion"], dict)
             and request["effect_assertion"].get("passed") is True,
             "parameter readout requires an exact passed downstream assertion")
    return request


def verify_source_contract(project_root):
    root = Path(project_root)
    evidence = []
    for relative, expected in SOURCE_CONTRACT.items():
        path = root / relative
        _require(path.is_file(), "missing source contract file: " + relative)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        _require(actual == expected, "source assignment/readout contract changed: " + relative)
        evidence.append({"path": relative, "sha256": actual})
    return evidence


def _steps(native):
    interval = native.get("step_interval")
    _require(isinstance(interval, list) and interval, "typed parameter proof requires a native interval")
    by_id = {}
    for step in interval:
        _require(isinstance(step, dict) and isinstance(step.get("id"), str), "invalid native step interval")
        _require(step["id"] not in by_id, "duplicate native interval step")
        by_id[step["id"]] = step
    return interval, by_id


def _inputs_between(interval, start_id, end_id):
    ids = [step["id"] for step in interval]
    _require(start_id in ids and end_id in ids and ids.index(start_id) < ids.index(end_id),
             "parameter readout checkpoints are absent or unordered")
    records = []
    for step in interval[ids.index(start_id) + 1:ids.index(end_id) + 1]:
        for index, item in enumerate(step.get("inputs", [])):
            _require(isinstance(item, dict), "invalid captured public input")
            records.append((step["id"], index, item))
    return records


def _check_assignment_inputs(interval, request):
    records = _inputs_between(interval, request["picker_step_id"], request["readout_step_id"])
    assignment_id = request["assignment_step_id"]
    ids = [step["id"] for step in interval]
    _require(ids.index(request["picker_step_id"]) < ids.index(assignment_id) < ids.index(request["readout_step_id"]),
             "assignment checkpoint is outside the picker/readout window")
    seen_assignment = []
    readout_encoders = []
    for step_id, index, item in records:
        kind = item.get("type")
        if kind == "wait":
            continue
        if step_id == assignment_id and kind == "key":
            seen_assignment.append(item)
            continue
        if step_id != assignment_id and step_id != request["readout_step_id"]:
            raise ParameterReadoutError("unexpected input between selected label and postapply readout")
        if step_id == request["readout_step_id"] and kind == "enc" and item.get("n") == 3:
            readout_encoders.append(item)
            continue
        raise ParameterReadoutError("slot navigation or reassignment input interrupts parameter readout proof")
    expected = [
        {"type": "key", "n": 3, "state": 1}, {"type": "key", "n": 3, "state": 0},
        {"type": "key", "n": 2, "state": 1}, {"type": "key", "n": 2, "state": 0},
    ]
    _require(seen_assignment == expected,
             "assignment must be the exact K3 apply followed by K2 return sequence")
    _require(readout_encoders, "select-value readout lacks a captured E3 value change")
    assignment_step = next(step for step in interval if step["id"] == assignment_id)
    non_wait = [item for item in assignment_step.get("inputs", []) if item.get("type") != "wait"]
    _require(non_wait == expected, "assignment checkpoint contains extra input or cancel-only navigation")
    return [{"step_id": step_id, "input_index": index, "input": item}
            for step_id, index, item in records if item.get("type") != "wait"]


def _assertion_ref(step, results, required_kind):
    output = step.get("output")
    binding = output.get("binding") if isinstance(output, dict) else None
    _require(isinstance(binding, dict), "parameter readout step lacks publication binding")
    index = binding.get("assertion_index")
    _require(type(index) is int and 0 <= index < len(results), "assertion result index is invalid")
    assertion = binding.get("assertion")
    row = results[index]
    _require(isinstance(assertion, dict) and row == assertion, "native assertion result differs from published row")
    _require(assertion.get("kind") == required_kind and assertion.get("passed") is True,
             "native public assertion has the wrong kind or did not pass")
    assertion_sha = _canonical_sha(assertion)
    _require(binding.get("assertion_sha256") == assertion_sha, "native assertion digest is invalid")
    _require(binding.get("trace_sha256") == _canonical_sha(step.get("inputs", [])),
             "public input trace digest is invalid")
    grid = output.get("grid")
    _require(isinstance(grid, list) and len(grid) == 128 and all(type(v) is int and 0 <= v <= 15 for v in grid),
             "published target grid is invalid")
    _require(binding.get("grid_sha256") == hashlib.sha256(bytes(grid)).hexdigest(),
             "published grid digest is invalid")
    return {"step_id": step["id"], "assertion_index": index,
            "assertion_sha256": assertion_sha, "frame_sha256": binding.get("sha256"),
            "grid_sha256": binding.get("grid_sha256"), "trace_sha256": binding.get("trace_sha256"),
            "assertion": assertion}


def _frame_observation(step, ref, observations, session_id):
    grid = step["output"].get("grid")
    matches = []
    for index, observation in enumerate(observations):
        state = observation.get("state", {})
        frame = state.get("frame", {})
        if (observation.get("session_id") == session_id
                and frame.get("sha256") == ref["frame_sha256"]
                and state.get("grid") == grid):
            pixels = base64.b64decode(frame.get("pixels_base64", ""), validate=True)
            _require(hashlib.sha256(pixels).hexdigest() == ref["frame_sha256"],
                     "native frame pixels differ from the published digest")
            matches.append((index, observation, state))
    _require(matches, "published frame has no same-session native observation")
    return matches[0]


def _verify_picker_pixels(state, label, frame_oracle):
    _require(frame_oracle.selected_field_matches(state, "detail", label, "")
             or frame_oracle.selected_field_matches(state, "detail", label, "CURRENT"),
             "native picker pixels do not show the selected parameter label")


def _verify_readout_pixels(state, request, frame_oracle):
    pixels = base64.b64decode(state["frame"]["pixels_base64"], validate=True)
    slot = request["slot"]
    _require(frame_oracle._selected_overview_index(pixels, "overview_params") == slot,
             "native Trig Params pixels show a different selected slot")
    _require(frame_oracle.selected_field_matches(state, "overview_params",
             request["display_label"], request["value"]),
             "native Trig Params pixels show a different value or display label")
    _require(frame_oracle.overview_cell_marker(state, "overview_params", slot) == request["marker"],
             "native Trig Params pixels show a different lock/slide marker")


def derive_parameter_readout_receipt(native, request, action_id, *, evidence_root,
                                     project_root, frame_oracle):
    """Return a strict receipt for one `select-value` action.

    This proves the *postapply-observed* slot, not a slot state before K3.
    `evidence_root` is the exact behavior-case result directory from scene evidence.
    """
    validate_request(request)
    _require(isinstance(action_id, str) and action_id, "parameter proof needs a bound action_id")
    _require(native.get("contract_schema") == "mosaic-native-transition-v3",
             "parameter readout proof requires an interval-native transition")
    scene = native.get("scene", {})
    scene_id = scene.get("id")
    case_id = scene.get("behaviour_case")
    evidence = scene.get("evidence", {})
    session = evidence.get("session_context", {}).get("session_id")
    _require(scene_id and case_id and session, "parameter proof lacks exact scene/case/session identity")
    interval, by_id = _steps(native)
    ids = [step["id"] for step in interval]
    for field in ("picker_step_id", "assignment_step_id", "readout_step_id", "effect_step_id"):
        _require(request[field] in by_id, "parameter proof checkpoint missing from native interval: " + field)
    _require(native.get("from_step_id") == request["picker_step_id"]
             and native.get("to_step_id") == request["effect_step_id"],
             "parameter proof endpoints must be exact picker and downstream effect steps")
    index_order = [ids.index(request[key]) for key in ("picker_step_id", "assignment_step_id", "readout_step_id", "effect_step_id")]
    _require(index_order == sorted(index_order) and len(set(index_order)) == 4,
             "parameter proof checkpoints are not strictly ordered")

    picker = by_id[request["picker_step_id"]]
    assigned = by_id[request["assignment_step_id"]]
    readout = by_id[request["readout_step_id"]]
    effect = by_id[request["effect_step_id"]]
    results = json.loads((Path(evidence_root) / "results.json").read_text())
    _require(hashlib.sha256((Path(evidence_root) / "results.json").read_bytes()).hexdigest()
             == evidence.get("results_sha256"), "native result evidence digest is invalid")
    picker_ref = _assertion_ref(picker, results, "parameter-list-label")
    _require(picker_ref["assertion"].get("label") == request["parameter_label"],
             "picker assertion label differs from requested parameter")
    assignment_ref = _assertion_ref(assigned, results, "selected-param")
    _require(assignment_ref["assertion"].get("slot") == request["slot"],
             "postapply slot differs from requested slot")
    readout_ref = _assertion_ref(readout, results, "selected-param")
    actual_readout = readout_ref["assertion"]
    _require(actual_readout.get("slot") == request["slot"]
             and actual_readout.get("value") == request["value"]
             and actual_readout.get("marker") == request["marker"],
             "postapply readout differs from requested slot/value/marker")
    effect_ref = _assertion_ref(effect, results, request["effect_assertion"].get("kind"))
    _require(effect_ref["assertion"] == request["effect_assertion"],
             "downstream musical assertion differs from the exact requested outcome")

    input_refs = _check_assignment_inputs(interval, request)
    between_readout_and_effect = _inputs_between(interval, request["readout_step_id"], request["effect_step_id"])
    for _, _, item in between_readout_and_effect:
        if item.get("type") in ("enc", "key", "midi"):
            raise ParameterReadoutError("intervening input changes the selected parameter before its effect")
    observations = json.loads((Path(evidence_root) / "observations.json").read_text())
    picker_observation = _frame_observation(picker, picker_ref, observations, session)
    assignment_observation = _frame_observation(assigned, assignment_ref, observations, session)
    readout_observation = _frame_observation(readout, readout_ref, observations, session)
    effect_observation = _frame_observation(effect, effect_ref, observations, session)
    ordered = [picker_observation, assignment_observation, readout_observation, effect_observation]
    obs_indices = [entry[0] for entry in ordered]
    _require(obs_indices == sorted(obs_indices) and len(set(obs_indices)) == len(obs_indices),
             "native observations do not prove strict picker/assignment/readout/effect order")
    _verify_picker_pixels(picker_observation[2], request["parameter_label"], frame_oracle)
    _verify_readout_pixels(assignment_observation[2], dict(request, value=assignment_ref["assertion"]["value"]), frame_oracle)
    _verify_readout_pixels(readout_observation[2], request, frame_oracle)

    source_files = verify_source_contract(project_root)
    results_sha = hashlib.sha256((Path(evidence_root) / "results.json").read_bytes()).hexdigest()
    observations_sha = hashlib.sha256((Path(evidence_root) / "observations.json").read_bytes()).hexdigest()
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "kind": "parameter-readout-assignment",
        "case_id": case_id,
        "scene_id": scene_id,
        "session_id": session,
        "from_step_id": request["picker_step_id"],
        "to_step_id": request["effect_step_id"],
        "action_id": action_id,
        "request": {key: request[key] for key in sorted(request)},
        "refs": {"picker": picker_ref, "assignment": assignment_ref,
                 "readout": readout_ref, "effect": effect_ref},
        "observation_indices": dict(zip(("picker", "assignment", "readout", "effect"), obs_indices)),
        "input_refs": input_refs,
        "source_contract": source_files,
        "evidence_digests": {"results_sha256": results_sha, "observations_sha256": observations_sha},
    }
    receipt["proof_sha256"] = _canonical_sha(receipt)
    return {"value": {"parameter_label": request["parameter_label"],
                      "slot": request["slot"], "value": request["value"],
                      "marker": request["marker"]},
            "receipt": receipt}


def verify_action_link(action, derived, action_checkpoint):
    """Require a lesson action to name the same selection and carry its receipt."""
    _require(isinstance(action, dict) and action.get("kind") == "select-value",
             "parameter readout receipt may bind only a select-value action")
    receipt = derived.get("receipt") if isinstance(derived, dict) else None
    _require(isinstance(receipt, dict) and receipt.get("action_id") == action.get("id"),
             "parameter readout receipt action_id does not match select-value action")
    request = receipt.get("request", {})
    _require(action.get("field_label") == request.get("parameter_label")
             and action.get("value") == request.get("value"),
             "select-value action label/value differs from source-bound readout")
    _require(isinstance(action_checkpoint, dict)
             and action_checkpoint.get("action_id") == action.get("id")
             and action_checkpoint.get("checkpoint_step_id") == request.get("readout_step_id"),
             "select-value checkpoint does not land on the captured parameter readout")
    proof = action_checkpoint.get("proof", {})
    _require(proof == {"kind": "field-value", "field_label": request.get("parameter_label"),
                       "value": request.get("value")},
             "select-value action proof differs from the parameter readout")
    action_refs = action_checkpoint.get("raw_inputs")
    _require(isinstance(action_refs, list) and action_refs,
             "select-value action lacks exact captured input references")
    receipt_refs = {(row["step_id"], row["input_index"]) for row in receipt.get("input_refs", [])}
    _require(all(isinstance(ref, dict) and (ref.get("step_id"), ref.get("index")) in receipt_refs
                 for ref in action_refs),
             "select-value action input is not part of the source-bound parameter chain")
    return receipt


def receipt_digest(receipt):
    _require(isinstance(receipt, dict), "missing parameter readout receipt")
    candidate = dict(receipt)
    digest = candidate.pop("proof_sha256", None)
    _require(isinstance(digest, str) and digest == _canonical_sha(candidate),
             "parameter readout receipt digest is invalid")
    return digest

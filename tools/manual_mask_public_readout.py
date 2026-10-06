"""Fresh-run Mask readout receipt derived from authored scene assertions.

The historical manual_masks_native_readout_adapter pin set remains unchanged.
This adapter validates a newly captured scene through its publication evidence,
same-run raw rows, same-session native observation, and the independent UI
pixel oracle. It does not generate or accept digest pins supplied by the caller.
"""
import base64
import hashlib
import json
import re
from pathlib import Path


class MaskReadoutError(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise MaskReadoutError(message)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def validate_current_scene(scene, step_id, field, value, pixel_verifier):
    """Validate current captured public field evidence; return a derived receipt."""
    _need(isinstance(scene, dict) and isinstance(scene.get("id"), str), "Mask receipt lacks a bound scene")
    _need(isinstance(step_id, str) and step_id and isinstance(field, str) and field
          and isinstance(value, str) and value, "Mask receipt needs exact step, field and value")
    evidence = scene.get("evidence")
    _need(isinstance(evidence, dict), "Mask scene lacks publication evidence")
    root = Path(evidence.get("path", "")).resolve()
    _need(root.is_dir() and root.parent.name and re.fullmatch(r"[0-9a-f]{32}", root.parent.name),
          "Mask evidence is not inside an identified behavior run")
    run_root = root.parent
    context = evidence.get("session_context")
    _need(isinstance(context, dict) and context.get("finished") is True
          and context.get("cleanup_verified") is True and context.get("held_inputs") == [],
          "Mask run is unfinished or cleanup is unverified")
    session_id = context.get("session_id")
    _need(isinstance(session_id, str) and session_id, "Mask scene lacks a native session identity")
    expected_files = {
        "results_sha256": root / "results.json",
        "identity_sha256": root / "native" / "identity.json",
        "recipe_sha256": root / "recipe.json",
        "cleanup_sha256": root / "native" / "cleanup.json",
    }
    for key, path in expected_files.items():
        expected = evidence.get(key)
        _need(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected)
              and path.is_file() and _sha(path) == expected,
              "Mask source evidence digest changed: " + key)
    results = json.loads((root / "results.json").read_text(encoding="utf-8"))
    observations_path = root / "observations.json"
    _need(observations_path.is_file(), "Mask run lacks raw native observations")
    observation_sha = _sha(observations_path)
    observations = json.loads(observations_path.read_text(encoding="utf-8"))
    scene_step = next((row for row in scene.get("steps", []) if row.get("id") == step_id), None)
    _need(isinstance(scene_step, dict), "Mask readout step is absent from the published scene")
    output = scene_step.get("output", {})
    binding = output.get("binding", {}) if isinstance(output, dict) else {}
    index = binding.get("assertion_index") if isinstance(binding, dict) else None
    _need(type(index) is int and 0 <= index < len(results), "Mask assertion index is invalid")
    assertion = binding.get("assertion")
    row = results[index]
    _need(isinstance(assertion, dict) and row == assertion and assertion.get("passed") is True,
          "published Mask assertion differs from the exact passed source row")
    _need(binding.get("assertion_sha256") == hashlib.sha256(_canonical(assertion)).hexdigest(),
          "published Mask assertion digest is invalid")
    _need(binding.get("trace_sha256") == hashlib.sha256(_canonical(scene_step.get("inputs", []))).hexdigest(),
          "Mask public input trace digest is invalid")
    screens = assertion.get("expected", {}).get("screen") if isinstance(assertion.get("expected"), dict) else None
    if screens is None:
        screens = assertion.get("screen")
    _need(screens == [[field, value]], "authored Mask assertion does not require the requested field/value")
    docs = [(i, item) for i, item in enumerate(results)
            if item.get("kind") == "documentation-frame" and item.get("name") == "manual/" + scene.get("behaviour_case", "") + "/" + step_id]
    _need(len(docs) == 1, "Mask step lacks one exact documentation-frame row")
    doc_index, doc = docs[0]
    _need(doc_index == index + 1 and doc.get("semantic_assertions") == index + 1 and doc.get("passed") is True,
          "Mask documentation frame does not follow its exact assertion")
    grid = output.get("grid")
    _need(isinstance(grid, list) and len(grid) == 128 and binding.get("grid_sha256") == hashlib.sha256(bytes(grid)).hexdigest(),
          "Mask published grid digest is invalid")
    matches = []
    for observation_index, observation in enumerate(observations):
        state = observation.get("state", {})
        frame = state.get("frame", {})
        if (observation.get("session_id") == session_id and frame.get("sha256") == doc.get("sha256")
                and state.get("grid") == grid):
            matches.append((observation_index, observation, state, frame))
    _need(bool(matches), "Mask frame/grid has no same-session raw observation")
    observation_index, observation, state, frame = matches[-1]
    _need(observation.get("backend") == "native" and observation.get("fidelity") == "native-norns",
          "Mask readout pixels are not from a native-norns observation")
    _need((frame.get("width"), frame.get("height"), frame.get("format")) == (128, 64, "BGRA8"),
          "Mask native frame format or dimensions changed")
    pixels = base64.b64decode(frame.get("pixels_base64", ""), validate=True)
    _need(len(pixels) == 128 * 64 * 4 and hashlib.sha256(pixels).hexdigest() == doc.get("sha256") == frame.get("sha256"),
          "Mask raw frame bytes differ from the documented frame hash")
    expected = {"mask_fields": [{"field": field, "value": value, "layout": "overview_masks"}]}
    _need(callable(pixel_verifier) and pixel_verifier(state, expected) is True,
          "Independent Mask pixel oracle rejected the source-authored field")
    _need((root / "native" / "identity.json").is_file(), "Mask native identity is missing")
    return {
        "kind": "native-mask-public-readout-current-run-v1", "scene": scene["id"], "step": step_id,
        "field": field, "value": value, "assertion_index": index, "documentation_frame_index": doc_index,
        "observation_index": observation_index, "frame_sha256": doc["sha256"],
        "results_sha256": evidence["results_sha256"], "observations_sha256": observation_sha,
        "identity_sha256": evidence["identity_sha256"], "recipe_sha256": evidence["recipe_sha256"],
        "cleanup_sha256": evidence["cleanup_sha256"], "session_id": session_id,
        "pixel_oracle": "manual_publication_verify.verify_cached_ui + frame_oracle.overview_cell_matches",
        "native": True,
    }

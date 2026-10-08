"""Admit the retained native player-Apply Device readout from its exact frame."""
import base64
import hashlib
import json
import re
from pathlib import Path

class PlayerDeviceReadoutError(ValueError):
    pass

def _need(ok, message):
    if not ok:
        raise PlayerDeviceReadoutError(message)

def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def validate_player_device_readout(scene, step_id, want, project_root, resolve_evidence=Path):
    """Verify the one retained Polyperc Apply capture against raw native bytes and pixel oracles."""
    _need(scene.get("id") == "player-apply-polyperc" and step_id == "polyperc-applied",
          "Player Device receipt is restricted to the retained Apply endpoint")
    _need(want == {"device": "Polyperc 1"}, "Player Device receipt requires the exact authored Device value")
    evidence = scene.get("evidence", {})
    path = Path(resolve_evidence(evidence.get("path", ""))).resolve()
    context = evidence.get("session_context")
    _need(path.is_dir() and isinstance(context, dict) and context.get("finished") is True
          and context.get("cleanup_verified") is True and context.get("held_inputs") == [],
          "Player Apply evidence is unfinished or cleanup is unverified")
    session_id = context.get("session_id")
    _need(isinstance(session_id, str) and session_id, "Player Apply evidence lacks native session identity")
    files = {"results_sha256": path / "results.json", "identity_sha256": path / "native/identity.json",
             "recipe_sha256": path / "recipe.json", "cleanup_sha256": path / "native/cleanup.json"}
    for key, file in files.items():
        expected = evidence.get(key)
        _need(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected)
              and file.is_file() and _sha(file) == expected, "Player Apply evidence digest changed: " + key)
    step = next((item for item in scene.get("steps", []) if item.get("id") == step_id), None)
    _need(isinstance(step, dict), "Player Apply target step is missing")
    assertion = {"kind": "manual-player-apply-applied", "citation": "manual:mods-and-software-devices",
                 "channel": 2, "page": "midi_config", "field": "Device", "value": "Polyperc 1",
                 "confirmation_prompt_absent": True, "passed": True}
    binding = step.get("output", {}).get("binding", {})
    _need(binding.get("assertion") == assertion, "Player Apply assertion differs from its exact retained native assertion")
    identity = json.loads((path / "native/identity.json").read_text(encoding="utf-8"))
    _need(identity.get("session_id") == session_id, "Player Apply native identity belongs to another session")
    from manual_publication_verify import canonical_hash, mosaic_file_map
    _need(context.get("runtime_identity_sha256") == canonical_hash(identity.get("runtime_identity"))
          and context.get("application_identity_sha256") == canonical_hash(mosaic_file_map(identity)),
          "Player Apply runtime or application identity differs from its session context")
    results = json.loads((path / "results.json").read_text(encoding="utf-8"))
    index = binding.get("assertion_index")
    _need(type(index) is int and 0 <= index < len(results) and results[index] == assertion,
          "Player Apply assertion index does not identify the exact raw result")
    _need(binding.get("assertion_sha256") == hashlib.sha256(_canonical(assertion)).hexdigest()
          and binding.get("trace_sha256") == hashlib.sha256(_canonical(step.get("inputs", []))).hexdigest(),
          "Player Apply assertion or input-trace digest is invalid")
    doc_index = index + 1
    doc = results[doc_index] if doc_index < len(results) else None
    name = "manual/" + scene.get("behaviour_case", "") + "/" + scene["id"] + "/" + step_id
    _need(isinstance(doc, dict) and doc.get("kind") == "documentation-frame" and doc.get("name") == name
          and doc.get("passed") is True and doc.get("assertion_index") == index and doc.get("assertion") == assertion,
          "Player Apply frame is not the immediate retained frame for its assertion")
    output = step.get("output", {})
    _need(binding.get("sha256") == doc.get("sha256") and binding.get("grid_sha256") == doc.get("grid_sha256")
          and output.get("grid") and hashlib.sha256(bytes(output["grid"])).hexdigest() == doc.get("grid_sha256"),
          "Player Apply documentation frame or grid digest differs from published output")
    observations_path = path / "observations.json"
    _need(observations_path.is_file(), "Player Apply evidence lacks raw native observations")
    observations = json.loads(observations_path.read_text(encoding="utf-8"))
    matches = [(i, row) for i, row in enumerate(observations)
               if row.get("session_id") == session_id and row.get("backend") == "native"
               and row.get("fidelity") == "native-norns"
               and row.get("state", {}).get("grid") == output["grid"]
               and row.get("state", {}).get("frame", {}).get("sha256") == doc["sha256"]]
    _need(matches, "Player Apply frame has no matching same-session raw native observation")
    observation_index, observation = matches[-1]
    state = observation["state"]
    frame = state.get("frame", {})
    _need((frame.get("width"), frame.get("height"), frame.get("format")) == (128, 64, "BGRA8"),
          "Player Apply raw native frame has unexpected dimensions or format")
    pixels = base64.b64decode(frame.get("pixels_base64", ""), validate=True)
    _need(len(pixels) == 128 * 64 * 4 and hashlib.sha256(pixels).hexdigest() == frame.get("sha256") == doc["sha256"],
          "Player Apply raw pixels differ from the retained documented frame hash")
    from manual_screen_codec import encode_native_frame
    _need(encode_native_frame(pixels) == {k: output[k] for k in ("screen_rle",)},
          "Player Apply public screen payload differs from its raw native pixels")
    from manual_publication_verify import verify_cached_ui
    verify_cached_ui(state, {"header": {"page": "midi_config", "params": {"channel": 2}},
                             "field": {"layout": "detail", "label": "Device", "value": "Polyperc 1"},
                             "footer": {"text": "Press K3 to confirm", "present": False}}, path)
    return {"kind": "native-player-device-public-readout-v1", "scene": scene["id"], "step": step_id,
            "device_configuration": want, "channel": 2, "page": "midi_config", "field": "Device",
            "assertion_index": index, "documentation_frame_index": doc_index,
            "observation_index": observation_index, "frame_sha256": doc["sha256"],
            "results_sha256": evidence["results_sha256"], "observations_sha256": _sha(observations_path),
            "identity_sha256": evidence["identity_sha256"], "recipe_sha256": evidence["recipe_sha256"],
            "cleanup_sha256": evidence["cleanup_sha256"], "session_id": session_id,
            "pixel_oracle": "manual_publication_verify.verify_cached_ui + frame_oracle.selected_field_matches/footer_matches/live_header_matches",
            "adapter_source": "tools/manual_player_device_readout.py",
            "adapter_source_sha256": _sha(Path(project_root) / "tools/manual_player_device_readout.py"),
            "native": True}

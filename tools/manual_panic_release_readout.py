"""Verify the retained sounding-note Panic endpoint from its complete native event journal."""
import base64
import hashlib
import json
import re
from pathlib import Path

class PanicReleaseReadoutError(ValueError):
    pass

RETAINED_PANIC_SOURCE = {
    "path": "/home/andy/mosaic-manual-runs/d2199e5374224ea6b9a6c672f17e0eab/M-MANUAL-CLOSURE-PANIC-001-base-midi",
    "session_id": "29ffbe64c7fd4976a38412676016b334",
    "results_sha256": "20d7c1e34a00165d53e3d519e36c4f79b915757b5a9631b55e756a7503d737af",
    "native_events_sha256": "6d43e3ae66c2c053f543feb67bd0c5523f1191bd63eb2b8f7e54761c311a9f12",
}

def is_retained_panic_source(scene):
    evidence = scene.get("evidence", {}) if isinstance(scene, dict) else {}
    context = evidence.get("session_context", {})
    try:
        path = str(Path(evidence.get("path", "")).resolve())
    except (OSError, RuntimeError):
        return False
    return (path == RETAINED_PANIC_SOURCE["path"]
            and context.get("session_id") == RETAINED_PANIC_SOURCE["session_id"]
            and evidence.get("results_sha256") == RETAINED_PANIC_SOURCE["results_sha256"]
            and evidence.get("native_events_sha256") == RETAINED_PANIC_SOURCE["native_events_sha256"])

def _validated_midi_60_release(midi_rows, assertion):
    _need(bool(midi_rows) and [row.get("index") for row in midi_rows] == list(range(1, len(midi_rows) + 1)),
          "Panic full native MIDI journal has missing or unordered event indices")
    if midi_rows[0].get("kind") == 11:
        _need([row.get("sequence") for row in midi_rows] == list(range(1, len(midi_rows) + 1)),
              "Panic native MIDI sequence is incomplete")
    offs = [row for row in midi_rows if row.get("port") == 1 and row.get("bytes") == [128, 60, 0]]
    _need(len(offs) == 1, "Panic journal lacks the unique actual sounding-C note-off")
    ons = [row for row in midi_rows if row.get("port") == 1 and row.get("bytes") == [144, 60, 127]
           and row.get("index", 0) < offs[0]["index"]]
    _need(len(ons) == 1, "Panic journal lacks the unique preceding sounding-C onset")
    delta_ns = offs[0].get("logical_ns") - ons[0].get("logical_ns")
    _need(delta_ns == round(assertion["release_seconds_after_note_on"] * 1_000_000_000)
          and delta_ns / 1_000_000_000 < assertion["natural_end_seconds"]
          and assertion["released_early"] is True and assertion["playback_continued"] is True,
          "Panic MIDI 60 cutoff differs from the exact early-release assertion")
    return ons[0], offs[0], delta_ns

def _need(ok, message):
    if not ok:
        raise PanicReleaseReadoutError(message)

def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def validate_panic_release_readout(scene, step_id, wanted, project_root):
    _need(scene.get("id") == "panic-stops-sounding-note" and step_id == "panic-released"
          and is_retained_panic_source(scene),
          "Panic sounding-note receipt is restricted to its pinned retained endpoint")
    _need(wanted == [{"port": 1, "bytes": [128, 60, 0]}],
          "Panic endpoint must require the actual MIDI 60 note-off")
    evidence = scene.get("evidence", {})
    root = Path(evidence.get("path", "")).resolve()
    context = evidence.get("session_context")
    _need(root.is_dir() and isinstance(context, dict) and context.get("finished") is True
          and context.get("cleanup_verified") is True and context.get("held_inputs") == [],
          "Panic evidence is unfinished or cleanup is unverified")
    session_id = context.get("session_id")
    _need(isinstance(session_id, str) and session_id, "Panic evidence lacks native session identity")
    pins = {"results_sha256": root / "results.json", "identity_sha256": root / "native/identity.json",
            "recipe_sha256": root / "recipe.json", "cleanup_sha256": root / "native/cleanup.json",
            "native_events_sha256": root / "native/native-events.jsonl",
            "capture_trace_sha256": root / "capture-trace.json",
            "session_context_sha256": root / "session-context.json"}
    for key, path in pins.items():
        expected = evidence.get(key)
        _need(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected)
              and path.is_file() and _sha(path) == expected, "Panic evidence digest changed: " + key)
    identity = json.loads((root / "native/identity.json").read_text(encoding="utf-8"))
    _need(identity.get("session_id") == session_id, "Panic native identity belongs to another session")
    from manual_publication_verify import canonical_hash, mosaic_file_map
    _need(context.get("runtime_identity_sha256") == canonical_hash(identity.get("runtime_identity"))
          and context.get("application_identity_sha256") == canonical_hash(mosaic_file_map(identity)),
          "Panic runtime or application identity differs from its session context")
    session_context = json.loads((root / "session-context.json").read_text(encoding="utf-8"))
    _need(session_context == context, "Panic session context differs from its retained scene")
    cleanup = json.loads((root / "native/cleanup.json").read_text(encoding="utf-8"))
    _need(isinstance(cleanup, list) and cleanup and all(isinstance(row, dict) and row.get("returncode") is not None for row in cleanup),
          "Panic cleanup records are incomplete")
    step = next((row for row in scene.get("steps", []) if row.get("id") == step_id), None)
    _need(isinstance(step, dict), "Panic target step is missing")
    assertion = {"kind": "panic-releases-sounding-note", "citation": "README.md#midi-panic", "natural_end_seconds": 4.0,
                 "next_note_on_seconds": 4.0, "note": 60, "passed": True, "playback_continued": True, "port": 1,
                 "ports": 3, "release_seconds_after_note_on": 1.260002156, "released_early": True, "sweep_messages": 6144}
    binding = step.get("output", {}).get("binding", {})
    _need(binding.get("assertion") == assertion, "Panic assertion differs from its exact retained typed oracle")
    results = json.loads((root / "results.json").read_text(encoding="utf-8"))
    assertion_index = binding.get("assertion_index")
    _need(type(assertion_index) is int and 0 <= assertion_index < len(results)
          and results[assertion_index] == assertion
          and binding.get("assertion_sha256") == hashlib.sha256(_canonical(assertion)).hexdigest(),
          "Panic assertion index or digest does not match the retained result")
    _need(binding.get("trace_sha256") == hashlib.sha256(_canonical(step.get("inputs", []))).hexdigest(),
          "Panic public input trace digest is invalid")
    trace = json.loads((root / "capture-trace.json").read_text(encoding="utf-8"))
    inputs = step.get("inputs", [])
    _need(any(inputs == trace[i:i + len(inputs)] for i in range(len(trace) - len(inputs) + 1)),
          "Panic target inputs are absent from the retained full capture trace")
    doc_index = assertion_index + 1
    doc = results[doc_index] if doc_index < len(results) else None
    expected_name = "manual/" + scene.get("behaviour_case", "") + "/" + scene["id"] + "/" + step_id
    _need(isinstance(doc, dict) and doc.get("kind") == "documentation-frame" and doc.get("name") == expected_name
          and doc.get("passed") is True and doc.get("assertion_index") == assertion_index
          and doc.get("assertion") == assertion and binding.get("sha256") == doc.get("sha256"),
          "Panic documentation frame is not bound to the exact assertion")
    output = step.get("output", {})
    grid = output.get("grid")
    _need(isinstance(grid, list) and len(grid) == 128 and hashlib.sha256(bytes(grid)).hexdigest() == doc.get("grid_sha256"),
          "Panic target grid does not match its documented frame")
    event_rows = [json.loads(line) for line in (root / "native/native-events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    midi_rows = [row for row in event_rows if row.get("kind") in (3, 11)]
    onset, cutoff, delta_ns = _validated_midi_60_release(midi_rows, assertion)
    observations_path = root / "observations.json"
    _need(observations_path.is_file(), "Panic evidence lacks native observations")
    observations = json.loads(observations_path.read_text(encoding="utf-8"))
    _need(observations and observations[-1].get("session_id") == session_id
          and observations[-1].get("state", {}).get("midi_count") == len(midi_rows),
          "Panic full MIDI journal is not closed by the same-session final observation")
    matching = [(i, row) for i, row in enumerate(observations)
                if row.get("session_id") == session_id and row.get("backend") == "native"
                and row.get("fidelity") == "native-norns"
                and row.get("state", {}).get("grid") == grid
                and row.get("state", {}).get("frame", {}).get("sha256") == doc.get("sha256")]
    _need(matching, "Panic documented frame has no same-session native observation")
    observation_index, observation = matching[-1]
    state = observation["state"]
    frame = state["frame"]
    pixels = base64.b64decode(frame.get("pixels_base64", ""), validate=True)
    _need((frame.get("width"), frame.get("height"), frame.get("format")) == (128, 64, "BGRA8")
          and len(pixels) == 32768 and hashlib.sha256(pixels).hexdigest() == frame.get("sha256") == doc["sha256"]
          and state.get("midi_count", 0) >= cutoff["index"],
          "Panic frame pixels or event ordering differ from the retained native observation")
    from manual_screen_codec import encode_native_frame
    _need(encode_native_frame(pixels) == {"screen_rle": output.get("screen_rle")},
          "Panic published screen RLE differs from its raw native frame")
    return {"kind": "native-panic-sounding-note-readout-v1", "scene": scene["id"], "step": step_id,
            "events": [{"port": 1, "bytes": cutoff["bytes"]}], "assertion_index": assertion_index,
            "documentation_frame_index": doc_index, "observation_index": observation_index,
            "native_event_index": cutoff["index"], "note_on_event_index": onset["index"],
            "release_seconds_after_note_on": delta_ns / 1_000_000_000, "frame_sha256": doc["sha256"],
            "results_sha256": evidence["results_sha256"], "native_events_sha256": evidence["native_events_sha256"],
            "capture_trace_sha256": evidence["capture_trace_sha256"], "identity_sha256": evidence["identity_sha256"],
            "recipe_sha256": evidence["recipe_sha256"], "cleanup_sha256": evidence["cleanup_sha256"],
            "session_id": session_id,
            "adapter_source": "tools/manual_panic_release_readout.py",
            "adapter_source_sha256": _sha(Path(project_root) / "tools/manual_panic_release_readout.py"),
            "native": True}

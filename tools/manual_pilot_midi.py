"""Project complete retained pilot playback windows; never project expectations."""
import copy
import hashlib
import json
from pathlib import Path

class PilotMidiError(ValueError):
    pass

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def project_pilot_midi(scene, resolve=Path):
    """Use ordered native Start/Stop windows matched to original actual assertions."""
    steps = scene.get("steps", [])
    if not any("midi" not in s.get("output", {}) and s.get("expect", {}).get("midi_phrase") for s in steps):
        return scene
    # This adapter applies only to the original public pilot documentation-frame format.
    if not all(s.get("output", {}).get("binding", {}).get("kind") == "documentation-frame" for s in steps):
        return scene
    ev = scene["evidence"]; root = resolve(ev["path"])
    files = {name: (root / name).read_bytes() for name in
             ("results.json", "observations.json", "native/identity.json", "native/native-events.jsonl")}
    if _sha(files["results.json"]) != ev["results_sha256"] or _sha(files["native/identity.json"]) != ev["identity_sha256"]:
        raise PilotMidiError("retained results or native identity changed")
    results = json.loads(files["results.json"])
    if any(r.get("passed") is False or r.get("matched") is False for r in results):
        raise PilotMidiError("failed original assertion")
    observations = json.loads(files["observations.json"])
    identity = json.loads(files["native/identity.json"])
    rows = [json.loads(line) for line in files["native/native-events.jsonl"].splitlines() if line.strip()]
    midi = [row for row in rows if row.get("kind") == 11]
    if [r.get("index") for r in midi] != list(range(1, len(midi)+1)) or any(r.get("sequence") != r["index"] for r in midi):
        raise PilotMidiError("native journal has missing or unordered MIDI packets")
    # Cross-check every retained journal packet against the independently stored snapshot tail.
    seen = {}
    for obs in observations:
        if obs.get("session_id") != identity.get("session_id"):
            raise PilotMidiError("snapshot belongs to another native session")
        state = obs["state"]; capture = state["midi_capture"]
        if capture.get("dropped") != 0 or capture.get("count") != state["midi_count"]:
            raise PilotMidiError("snapshot MIDI capture missing or truncated")
        for packet in state["midi"]:
            i = packet["index"]
            if i in seen and seen[i] != packet:
                raise PilotMidiError("snapshot packet changed")
            seen[i] = packet
    if observations[-1]["state"]["midi_count"] != len(midi) or set(seen) != set(range(1,len(midi)+1)):
        raise PilotMidiError("snapshots do not cover the complete native MIDI journal")
    for packet in midi:
        snap = seen[packet["index"]]
        if any(packet.get(k) != snap.get(k) for k in ("port", "bytes", "monotonic_ns", "logical_ns", "device_id", "port_name")):
            raise PilotMidiError("journal packet differs from observed snapshot")
    windows = []; active = None
    for i, packet in enumerate(midi):
        if packet["bytes"] == [250]:
            if active is None: active = i
        elif packet["bytes"] == [252] and active is not None:
            # Include the complete contiguous Stop burst across ports, plus the closing note off.
            if i+1 < len(midi) and midi[i+1]["bytes"] == [252]: continue
            windows.append(midi[active:i+1]); active = None
    if active is not None:
        raise PilotMidiError("playback window has no complete Stop boundary")
    witnessed = []
    for index, result in enumerate(results):
        if result.get("kind") == "documentation-frame":
            n = result.get("semantic_assertions")
            if n != index or index == 0 or results[index-1].get("kind") != "manual-semantic":
                raise PilotMidiError("frame/semantic result adjacency changed")
            semantic = results[index-1]
            earlier = next((j for j in range(index-2,-1,-1) if results[j].get("kind")=="documentation-frame"), -1)
            assertions = [(j,r) for j,r in enumerate(results[earlier+1:index-1],earlier+1) if r.get("kind")=="midi"]
            if semantic.get("expected",{}).get("midi_phrase"):
                if len(assertions) != 1: raise PilotMidiError("target lacks a unique actual playback assertion")
                witnessed.append((semantic["step"], result, assertions[0]))
            elif assertions:
                raise PilotMidiError("unassociated actual playback assertion")
    if len(windows) != len(witnessed):
        raise PilotMidiError("native transport windows and actual assertions differ in count")
    out = copy.deepcopy(scene)
    by_id = {s["id"]:s for s in out["steps"]}
    for window, (sid, frame, (result_index, witness)) in zip(windows, witnessed):
        actual = [[v["port"],v["bytes"]] for v in window if len(v["bytes"])>=3 and v["bytes"][0]&240==144 and v["bytes"][2]>0]
        if actual != witness.get("actual") or witness.get("complete_cycles") != 2:
            raise PilotMidiError("native playback differs from original actual witness")
        step = by_id[sid]
        if step["output"]["binding"] != frame or step["expect"] != results[frame["semantic_assertions"]-1]["expected"]:
            raise PilotMidiError("step differs from original bound frame/semantic target")
        onsets = [v for v in window if len(v["bytes"])>=3 and v["bytes"][0]&240==144 and v["bytes"][2]>0]
        start, end = window[0], window[-1]
        step["output"]["midi"] = {"events":window, "total":len(window), "truncated":False,
            "note_on_observation": {"kind":"original-actual-note-on-observation-v1",
             "actual":witness["actual"], "result_index":result_index,
             "result_row_sha256":_sha(json.dumps(witness,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")),
             "results_file_sha256":ev["results_sha256"], "target_frame_sha256":frame["sha256"],
             "complete_cycles":witness["complete_cycles"]},
            "provenance":{"kind":"retained-pilot-native-playback-window-v1", "evidence_path":ev["path"],
             "session_id":identity["session_id"], "source_sha256":{k:_sha(v) for k,v in files.items()},
             "historically_pinned_sources":["results.json","native/identity.json"],
             "newly_sealed_retained_sources":["observations.json","native/native-events.jsonl"],
             "window_sha256":_sha(json.dumps(window,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")),
             "result_index":result_index, "window_start_index":start["index"],
             "window_end_index":end["index"], "complete_native_event_count":len(midi),
             "start_logical_ns":start["logical_ns"], "end_logical_ns":end["logical_ns"],
             "start_monotonic_ns":start["monotonic_ns"], "end_monotonic_ns":end["monotonic_ns"],
             "complete_cycles":witness["complete_cycles"], "actual_note_on_count":len(onsets),
             "first_note_on_logical_ns":onsets[0]["logical_ns"], "closing_note_on_logical_ns":onsets[-1]["logical_ns"],
             "scope":"complete public playback validation, including two cycles, closing onset, releases and Stop"}}
    return out

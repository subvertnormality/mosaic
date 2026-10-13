"""Strict per-run audit for recorded Trig Params readouts and replay."""
import base64
import json
from pathlib import Path


class RecordingReadoutError(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise RecordingReadoutError(message)


def validate_declarations(step_plan):
    visual = step_plan.get("native_readout")
    _need(isinstance(visual, dict) and set(visual) == {"layout", "slot", "label", "value", "marker"},
          "recorded-value step requires exact native_readout")
    _need(visual["layout"] == "overview_params" and type(visual["slot"]) is int
          and 1 <= visual["slot"] <= 64 and isinstance(visual["label"], str)
          and visual["label"] and isinstance(visual["value"], str) and visual["value"]
          and visual["marker"] in (None, "L", "S"), "invalid public Trig Params readout")
    replay = step_plan.get("native_replay")
    _need(isinstance(replay, dict) and set(replay) == {"port", "channel", "controller", "cc_values", "notes", "window", "timing"},
          "recorded-value step requires exact native_replay")
    window = replay.get("window")
    _need(isinstance(window, dict) and set(window) == {"start_recipe_index", "start_action", "stop_recipe_index", "stop_action", "prefix_messages", "suffix_messages"}
          and type(window.get("start_recipe_index")) is int and type(window.get("stop_recipe_index")) is int
          and 0 <= window["start_recipe_index"] < window["stop_recipe_index"]
          and window.get("start_action") == {"type": "grid", "x": 1, "y": 8, "state": 1}
          and window.get("stop_action") == {"type": "grid", "x": 15, "y": 8, "state": 1},
          "invalid source-bound native replay window")
    timing = replay.get("timing")
    _need(isinstance(timing, dict) and set(timing) == {"step_ns", "natural_gate_ns", "tolerance_ns"}
          and type(timing.get("step_ns")) is int and timing["step_ns"] > 0
          and type(timing.get("natural_gate_ns")) is int and timing["natural_gate_ns"] > 0
          and type(timing.get("tolerance_ns")) is int and timing["tolerance_ns"] >= 0,
          "invalid trusted native replay timing")
    for field in ("prefix_messages", "suffix_messages"):
        messages = window.get(field)
        _need(isinstance(messages, list) and all(isinstance(message, list) and 1 <= len(message) <= 3
              and all(type(byte) is int and 0 <= byte <= 255 for byte in message) for message in messages),
              "native replay window messages must be exact MIDI byte arrays")
    _need(type(replay["port"]) is int and replay["port"] >= 1
          and type(replay["channel"]) is int and 1 <= replay["channel"] <= 16
          and type(replay["controller"]) is int and 0 <= replay["controller"] <= 127,
          "invalid native replay CC route")
    values, notes = replay["cc_values"], replay["notes"]
    _need(isinstance(values, list) and len(values) >= 2
          and all(type(value) is int and 0 <= value <= 127 for value in values),
          "native replay needs an exact ordered CC value sequence")
    _need(isinstance(notes, list) and len(notes) == len(values)
          and all(isinstance(note, list) and len(note) == 2
                  and all(type(value) is int for value in note)
                  and 0 <= note[0] <= 127 and 1 <= note[1] <= 127 for note in notes),
          "native replay needs one exact note/velocity pair per CC value")
    return visual, replay


def _verify_replay(results, evidence_path, replay, clock_mode):
    window = replay.get("window")
    _need(isinstance(window, dict), "native replay requires an explicit input window")
    recipe = json.loads((Path(evidence_path) / "recipe.json").read_text())
    actions = [json.loads(line) for line in
               (Path(evidence_path) / "native/actions.jsonl").read_text().splitlines()]
    _need(isinstance(recipe, list) and len(recipe) == len(actions),
          "native action trace does not cover the complete recipe")
    for index, (planned, row) in enumerate(zip(recipe, actions)):
        request, ack = row.get("request", {}), row.get("ack", {})
        _need(request.get("sequence") == index + 1 and request.get("action") == planned
              and request.get("session_id") == ack.get("session_id")
              and ack.get("sequence") == index + 1 and ack.get("status") == "applied"
              and isinstance(ack.get("native"), dict),
              "native action trace diverges from the complete recipe")
    start_index, stop_index = window.get("start_recipe_index"), window.get("stop_recipe_index")
    _need(type(start_index) is int and type(stop_index) is int
          and 0 <= start_index < stop_index < len(recipe)
          and recipe[start_index] == window.get("start_action")
          and recipe[stop_index] == window.get("stop_action"),
          "native replay window no longer matches its exact recipe input boundaries")
    start_ack = actions[start_index]["ack"]["native"]
    stop_ack = actions[stop_index]["ack"]["native"]
    _need(start_ack.get("monotonic_ns", 0) < stop_ack.get("monotonic_ns", 0),
          "native replay input acknowledgements are not chronologically ordered")
    events = [json.loads(line) for line in
              (Path(evidence_path) / "native/native-events.jsonl").read_text().splitlines()]
    kind = 11 if clock_mode == "controlled-experimental" else 3
    # Each recipe boundary must have one native acknowledgement event with the exact sequence/time.
    for native_ack in (start_ack, stop_ack):
        matches = [row for row in events if row.get("kind") == "input_timing"
                   and row.get("sequence") == native_ack.get("sequence")
                   and row.get("native_ack_ns") == native_ack.get("monotonic_ns")]
        _need(len(matches) == 1, "replay boundary lacks a unique native input acknowledgement")
    port = replay["port"]
    route = [row for row in events if row.get("kind") == kind and row.get("port") == port
             and start_ack["monotonic_ns"] < row.get("monotonic_ns", 0)
             < stop_ack["monotonic_ns"]]
    indices = [row.get("index") for row in route]
    _need(all(type(index) is int and index >= 0 for index in indices)
          and len(indices) == len(set(indices))
          and all(left < right for left, right in zip(indices, indices[1:])),
          "native replay route event indexes are duplicate or out of order")
    prefix, suffix = window.get("prefix_messages"), window.get("suffix_messages")
    _need(isinstance(prefix, list) and isinstance(suffix, list),
          "native replay window requires exact prefix and suffix route messages")
    cc_status = 0xB0 + replay["channel"] - 1
    on_status = 0x90 + replay["channel"] - 1
    off_status = 0x80 + replay["channel"] - 1
    expected = list(prefix)
    paired = []
    for value, (pitch, velocity) in zip(replay["cc_values"], replay["notes"]):
        paired.extend([[cc_status, replay["controller"], value],
                       [on_status, pitch, velocity], [off_status, pitch, velocity]])
    expected.extend(paired)
    expected.extend(suffix)
    actual = [row.get("bytes") for row in route]
    _need(actual == expected,
          "complete native route window differs from trusted prefix, lock CCs, note gates, and suffix")
    phrase_rows = route[len(prefix):-len(suffix) if suffix else None]
    cc_rows = [phrase_rows[index] for index in range(0, len(phrase_rows), 3)]
    note_rows = [phrase_rows[index + 1] for index in range(0, len(phrase_rows), 3)]
    off_rows = [phrase_rows[index + 2] for index in range(0, len(phrase_rows), 3)]
    _need(len(cc_rows) == len(replay["cc_values"])
          and all(cc["index"] < note["index"] < off["index"]
                  for cc, note, off in zip(cc_rows, note_rows, off_rows)),
          "each native CC must precede its paired note and completed note-off gate")
    timing = replay["timing"]
    onset_times = [row.get("logical_ns") for row in note_rows]
    release_times = [row.get("logical_ns") for row in off_rows]
    stop_rows = route[-len(suffix):] if suffix else []
    _need(clock_mode == "controlled-experimental"
          and all(type(value) is int for value in onset_times + release_times)
          and len(stop_rows) == len(suffix)
          and all(type(row.get("logical_ns")) is int for row in stop_rows),
          "trusted musical replay timing requires complete logical timestamps")
    step_ns, gate_ns, tolerance_ns = (timing["step_ns"], timing["natural_gate_ns"],
                                      timing["tolerance_ns"])
    _need(all(abs((right - left) - step_ns) <= tolerance_ns
              for left, right in zip(onset_times, onset_times[1:])),
          "native note onsets do not follow the trusted musical lattice")
    _need(all(abs((release_times[index] - onset_times[index]) - gate_ns) <= tolerance_ns
              for index in range(len(note_rows) - 1)),
          "native natural note gates differ from the trusted duration")
    final_gate = release_times[-1] - onset_times[-1]
    _need(0 < final_gate < gate_ns - tolerance_ns
          and stop_rows[-1].get("bytes") == suffix[-1]
          and release_times[-1] == stop_rows[-1]["logical_ns"]
          and off_rows[-1]["index"] + 1 == stop_rows[-1]["index"],
          "final note-off is not the truncated gate immediately tied to MIDI Stop")
    expected_result = [[replay["port"], [on_status, pitch, velocity]]
                       for pitch, velocity in replay["notes"]]
    rows = [row for row in results if row.get("kind") == "midi"]
    _need(len(rows) == 1 and rows[0].get("expected") == expected_result
          and rows[0].get("actual") == expected_result,
          "downstream MIDI result differs from trusted replay phrase")
    return {"window_recipe_indices": [start_index, stop_index],
            "cc_event_indices": [row["index"] for row in cc_rows],
            "note_event_indices": [row["index"] for row in note_rows],
            "note_off_event_indices": [row["index"] for row in off_rows],
            "onset_logical_ns": onset_times,
            "release_logical_ns": release_times,
            "final_gate_truncated_at_stop": True}

def verify_parameter_recording_checkpoint(step, step_plan, scene, results,
                                         observations, evidence_path, clock_mode,
                                         verify_cached_ui):
    visual, replay = validate_declarations(step_plan)
    binding = step["output"]["binding"]
    row = binding.get("assertion")
    _need(isinstance(row, dict) and row.get("kind") == "parameter-recording-selected-value"
          and row.get("passed") is True, "missing passed recorded-value assertion")
    _need(all(row.get(key) == visual[key] for key in ("slot", "value", "marker")),
          "recorded-value assertion differs from trusted public readout")
    source_index, target_index = row.get("source_assertion_index"), binding.get("assertion_index")
    _need(type(source_index) is int and type(target_index) is int
          and 0 <= source_index < target_index < len(results),
          "copied selected-param row is absent or unordered")
    source = results[source_index]
    _need(source.get("kind") == "selected-param" and source.get("passed") is True
          and all(source.get(key) == visual[key] for key in ("slot", "value", "marker"))
          and row.get("source_assertion") == source and results[target_index] == row,
          "recorded-value row is not an exact copy of a prior native selected-param result")

    evidence_path = Path(evidence_path)
    identity = json.loads((evidence_path / "native/identity.json").read_text())
    context = json.loads((evidence_path / "session-context.json").read_text())
    session = identity.get("session_id")
    ordinal = scene.get("session_ordinal", 0)
    _need(isinstance(session, str) and session and context.get("session_id") == session
          and context.get("session_ordinal") == ordinal and binding.get("session_ordinal") == ordinal,
          "recorded-value frame belongs to a different native session")
    frame_sha, grid = binding.get("sha256"), step["output"].get("grid")
    _need(isinstance(frame_sha, str) and len(frame_sha) == 64 and isinstance(grid, list) and len(grid) == 128,
          "recorded-value frame binding is incomplete")
    matches = []
    for observation in observations:
        state = observation.get("state", {})
        frame = state.get("frame", {})
        if observation.get("session_id") == session and frame.get("sha256") == frame_sha and state.get("grid") == grid:
            pixels = base64.b64decode(frame.get("pixels_base64", ""), validate=True)
            _need(__import__("hashlib").sha256(pixels).hexdigest() == frame_sha,
                  "native Trig Params frame bytes changed")
            matches.append(state)
    _need(matches, "recorded-value frame has no same-session native observation")
    for state in matches:
        verify_cached_ui(state, {"parameter_readout": visual}, evidence_path)

    from manual_publication_verify import check_native_input_trace
    recipe = json.loads((evidence_path / "recipe.json").read_text())
    events = [json.loads(line) for line in (evidence_path / "native/native-events.jsonl").read_text().splitlines()]
    check_native_input_trace(recipe, events)
    replay_proof = _verify_replay(results, evidence_path, replay, clock_mode)
    final = observations[-1]["state"] if observations else {}
    cleanup = json.loads((evidence_path / "native/cleanup.json").read_text())
    _need(final.get("held") == [] and final.get("midi_capture", {}).get("outstanding") == [],
          "native recording session ended with held controls or notes")
    stopped = json.loads((evidence_path / "native/stopped.json").read_text())
    all_actions = [json.loads(line) for line in
                   (evidence_path / "native/actions.jsonl").read_text().splitlines()]
    last_native_ack = max(row.get("ack", {}).get("native", {}).get("monotonic_ns", 0)
                          for row in all_actions)
    _need(context.get("finished") is True and context.get("cleanup_verified") is True
          and stopped.get("session_id") == session
          and type(stopped.get("monotonic_ns")) is int
          and stopped["monotonic_ns"] > last_native_ack,
          "native recording session lacks a verified terminal stop")
    expected_services = {"matron", "sclang", "crone", "jack"}
    _need(isinstance(cleanup, list) and {row.get("service") for row in cleanup} == expected_services
          and len(cleanup) == len(expected_services)
          and all(type(row.get("pid")) is int and row["pid"] > 0
                  and (row.get("returncode") == 0
                       or (row.get("service") == "sclang" and row.get("returncode") == -15))
                  and type(row.get("seconds")) in (int, float) and row["seconds"] >= 0
                  for row in cleanup),
          "native recording session cleanup is incomplete or unsuccessful")
    raw_events = [json.loads(line) for line in
                  (evidence_path / "native/native-events.jsonl").read_text().splitlines()]
    _need(all(row.get("dropped", 0) == 0 for row in raw_events)
          and not any(row.get("kind") in ("dropped", "overflow", "event_overflow")
                      for row in raw_events),
          "native recording event log reports dropped or overflowed events")
    captures = [item.get("state", {}).get("midi_capture") for item in observations]
    captures = [capture for capture in captures if isinstance(capture, dict)]
    _need(captures and all(type(capture.get("dropped")) is int and capture["dropped"] == 0
                           for capture in captures),
          "native recording session dropped MIDI events")
    return {"source_assertion_index": source_index, "target_assertion_index": target_index,
            "frame_sha256": frame_sha, "session_id": session, "replay": replay_proof}


# Committed regression fixture pins the original evidence archive and every member.
FIXTURE_ARCHIVE_SHA256 = "4f76de28ad452b898f5f04685b7542f6d35c602b6e05af3990798cdbc369ba6a"
FIXTURE_MEMBER_SHA256 = {
    "evidence/M-REC-PARAM-001-base-midi/capture-trace.json": "ac1941a58fde7a3983d128ea610d3067a9bb3c84bc79fb757ad192e8c347de35",
    "evidence/M-REC-PARAM-001-base-midi/native/actions.jsonl": "9da31fa09d6abe01eac55f3839f345cb30994707835deee6774886ebc53251a2",
    "evidence/M-REC-PARAM-001-base-midi/native/cleanup.json": "d7f1ab69c0fe7e44304c8f16455b81947f3c134db8e618f8920d278a10d095a5",
    "evidence/M-REC-PARAM-001-base-midi/native/identity.json": "fc89c488970bdebb44222726eac34814a314859b1185cf83a34aedfc070f61e0",
    "evidence/M-REC-PARAM-001-base-midi/native/native-events.jsonl": "295ed903ffe0caa2b8e6c5e706035379a95556a7bae61ec178c923a180166614",
    "evidence/M-REC-PARAM-001-base-midi/native/stopped.json": "c3fa4e6e3f65efd76b4f6770d33f8cf024af76d65e2eca5af62d34a2b64b5b11",
    "evidence/M-REC-PARAM-001-base-midi/observations.json": "a748d2b500490ff3ef485fcbe12e3b70f795cd361ffc17b437f82e236e02c78b",
    "evidence/M-REC-PARAM-001-base-midi/recipe.json": "6a674acf1073ca3fdb5ebabec60191b08d99b67a59bf23d9bd8ad0f6c417f119",
    "evidence/M-REC-PARAM-001-base-midi/results.json": "b3574a02f4da80de58a16568c9f8a87e60ff59f8d69a32cb7697bce355189195",
    "evidence/M-REC-PARAM-001-base-midi/session-context.json": "555d6e3b11655a4a9c24851eb6e08d0de2a63acebe92d13b1da0b2f2633d127b",
    "manual/generated/reference-parameter-recording-scenes.json": "b2cea3fc506b3856b9b72ac1f2bd36efa68dc03afe07600766efafd4e6ee47cd",
    "manual/scene-plans-options.yaml": "3443477b6c8077671d97b94d0b9f1f2088de61fb0c246a51d18e9423a1a59f9e",
}

def extract_pinned_fixture(archive_path, destination, *, expected_archive_sha256=FIXTURE_ARCHIVE_SHA256,
                           expected_members=FIXTURE_MEMBER_SHA256):
    import hashlib
    import stat
    import zipfile
    archive_path, destination = Path(archive_path), Path(destination)
    archive_bytes = archive_path.read_bytes()
    _need(hashlib.sha256(archive_bytes).hexdigest() == expected_archive_sha256,
          "MREC fixture archive digest mismatch")
    _need(not destination.exists(), "MREC fixture extraction destination already exists")
    destination.mkdir(parents=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            _need(len(names) == len(set(names)) and set(names) == set(expected_members),
                  "MREC fixture archive has duplicate, missing, or unexpected members")
            for item in infos:
                name = item.filename
                _need("\\" not in name and not name.startswith("/")
                      and all(part not in ("", ".", "..") for part in name.split("/")),
                      "MREC fixture archive contains an unsafe member path")
                mode = item.external_attr >> 16
                _need(not stat.S_ISLNK(mode) and not item.is_dir()
                      and item.file_size <= 20_000_000,
                      "MREC fixture archive contains an unsafe or oversized member")
                data = archive.read(item)
                _need(hashlib.sha256(data).hexdigest() == expected_members[name],
                      "MREC fixture member digest mismatch")
                target = destination.joinpath(*name.split("/"))
                _need(destination.resolve() in target.resolve().parents,
                      "MREC fixture member escapes extraction root")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    except Exception:
        import shutil
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return destination

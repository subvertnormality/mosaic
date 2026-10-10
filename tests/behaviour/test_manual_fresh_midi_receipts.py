"""Portable synthetic regressions for fresh Panic and Masks MIDI receipts.

Characterisation outside the manual: these fixtures exercise derived-unit receipts only; they do not qualify a native
run, CI real-time lane, or physical-norns scheduling behavior.
"""
import base64
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import manual_fresh_target_midi as fresh
from manual_screen_codec import encode_native_frame

MASKS = {
    "mask-precedence": ("route", "default"),
    "mask-ghost-note": ("accent", "ghost"),
    "mask-melody-ending": ("step-four", "ending-d"),
    "mask-chords": ("chord", "thirds"),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def frame(value):
    pixels = bytes((value, value, value, 255)) * 8192
    return {
        "sha256": sha(pixels),
        "pixels_base64": base64.b64encode(pixels).decode("ascii"),
        "width": 128,
        "height": 64,
        "format": "BGRA8",
    }, encode_native_frame(pixels)["screen_rle"]


def event(index, port, data):
    return {
        "kind": 3,
        "index": index,
        "sequence": index,
        "port": port,
        "bytes": data,
        "monotonic_ns": 1000 + index,
        "logical_ns": 2000 + index,
        "device_id": "synthetic-midi",
        "port_name": "synthetic-midi",
    }


def observation(session, count, packets, frame_data, grid):
    return {
        "session_id": session,
        "backend": "native",
        "fidelity": "native-norns",
        "state": {
            "midi_count": count,
            "midi_capture": {"count": count, "dropped": 0},
            "midi": packets,
            "grid": grid,
            "frame": frame_data,
        },
    }


def make_masks_fixture(base):
    project = base / "project"
    build = base / "build" / "current"
    evidence = build / "scene-captures"
    build.mkdir(parents=True)
    (project / "tools").mkdir(parents=True)
    (project / "manual" / "features").mkdir(parents=True)
    (project / "tools" / "manual_capture.py").write_text("# synthetic capture producer\n", encoding="utf-8")
    (project / "tools" / "manual_build.py").write_text("# synthetic build producer\n", encoding="utf-8")
    mask_source = project / "manual" / "features" / "masks.yaml"
    mask_source.write_text("features: []\n", encoding="utf-8")
    app_files = [
        ("mosaic/manual/features/masks.yaml", mask_source),
        ("mosaic/tools/manual_build.py", project / "tools" / "manual_build.py"),
        ("mosaic/tools/manual_capture.py", project / "tools" / "manual_capture.py"),
    ]
    app_entries = [
        {"path": rel, "size": path.stat().st_size, "sha256": sha(path.read_bytes())}
        for rel, path in app_files
    ]
    app_entries.sort(key=lambda row: row["path"])
    app_digest = sha(json.dumps(app_entries, sort_keys=True).encode("utf-8"))
    scenes = []
    for offset, (scene_id, (from_id, to_id)) in enumerate(MASKS.items()):
        source = evidence / scene_id
        native = source / "native"
        native.mkdir(parents=True)
        session = "session-" + scene_id
        grid = [offset] * 128
        grid_digest = sha(bytes(grid))
        before_frame, before_rle = frame(17 + offset * 17)
        target_frame, target_rle = frame(34 + offset * 17)
        later_frame, _ = frame(51 + offset * 17)
        target_packet = [0x90, 60 + offset, 100]
        target_phrase = [{"port": 1, "bytes": target_packet}]
        target_events = [[1, target_packet]]
        packets = [
            event(1, 1, [0x80, 40 + offset, 0]),
            event(2, 1, target_packet),
            event(3, 1, [0x90, 70 + offset, 90]),
        ]
        before_expect = {"kind": "mask-source-frame", "passed": True}
        target_expect = {"kind": "mask-target-frame", "passed": True, "midi_phrase": target_phrase}
        before_name = "manual/masks/" + scene_id + "/" + from_id
        target_name = "manual/masks/" + scene_id + "/" + to_id
        before_binding = {"name": before_name, "semantic_assertions": 1,
                          "sha256": before_frame["sha256"], "grid_sha256": grid_digest}
        target_binding = {"name": target_name, "semantic_assertions": 4,
                          "sha256": target_frame["sha256"], "grid_sha256": grid_digest}
        before_step = {"id": from_id, "inputs": [], "expect": before_expect,
                       "output": {"binding": before_binding, "grid": grid, "screen_rle": before_rle}}
        target_step = {"id": to_id, "inputs": [{"type": "grid", "x": 1, "y": 1, "pressed": True}],
                       "expect": target_expect,
                       "output": {"binding": target_binding, "grid": grid, "screen_rle": target_rle}}
        results = [
            {"kind": "manual-semantic", "step": from_id, "passed": True, "expected": before_expect},
            {"kind": "documentation-frame", "name": before_name, "passed": True,
             "sha256": before_frame["sha256"], "grid_sha256": grid_digest},
            {"kind": "midi", "expected": target_events, "actual": target_events},
            {"kind": "manual-semantic", "step": to_id, "passed": True, "expected": target_expect},
            {"kind": "documentation-frame", "name": target_name, "passed": True,
             "sha256": target_frame["sha256"], "grid_sha256": grid_digest},
        ]
        identity = {"session_id": session,
                    "application_identity": {"digest": app_digest, "files": app_entries}}
        write_json(native / "identity.json", identity)
        write_json(native / "cleanup.json", [{"returncode": 0}])
        write_json(source / "results.json", results)
        write_json(source / "recipe.json", {"fixture": "synthetic"})
        write_json(source / "capture-trace.json", target_step["inputs"])
        write_json(source / "session-context.json", {"session_id": session, "finished": True})
        with (source / "native" / "native-events.jsonl").open("w", encoding="utf-8") as stream:
            for packet in packets:
                stream.write(json.dumps(packet, sort_keys=True, separators=(",", ":")) + "\n")
        observations = [
            observation(session, 1, packets[:1], before_frame, grid),
            observation(session, 2, packets[:2], target_frame, grid),
            observation(session, 3, packets, later_frame, grid),
        ]
        write_json(source / "observations.json", observations)
        scenes.append({"id": scene_id, "behaviour_case": "manual/masks/" + scene_id,
                       "evidence": {"path": str(source)}, "steps": [before_step, target_step]})
    evidence.mkdir(parents=True, exist_ok=True)
    log = ("Masks controlled fixture\nEvidence " + str(evidence.resolve()) + "\n").encode("utf-8")
    (build / "masks-controlled.log").write_bytes(log)
    command = ["python", str(project / "tools" / "manual_capture.py"),
               "--clock-mode", "controlled-experimental",
               "--experimental-install", str(base / "install.json"), "--controlled-local"]
    write_json(build / "masks-controlled.json", {
        "name": "masks-controlled", "passed": True, "returncode": 0,
        "exclusive_lock": True, "action": None, "command": command,
        "executed_command": command, "started_utc": "2026-10-10T00:00:00Z",
        "finished_utc": "2026-10-10T00:00:01Z", "log_sha256": sha(log),
    })
    write_json(build / "generation-context.json", {
        "validation_scope": "controlled-manual-generation",
        "clock_mode": "controlled-experimental", "complete_regression_run": False,
        "source_files_before": {"manual/features/masks.yaml": sha(mask_source.read_bytes())},
        "producer_source_sha256": {
            "tools/manual_capture.py": sha((project / "tools" / "manual_capture.py").read_bytes()),
            "tools/manual_build.py": sha((project / "tools" / "manual_build.py").read_bytes()),
        },
    })
    return scenes, project, build


def make_panic_fixture(base):
    project = base / "project"
    build = base / "build" / "panic-current"
    source = build / "scene-captures" / "panic-from-song-channel"
    native = source / "native"
    native.mkdir(parents=True)
    build.mkdir(parents=True, exist_ok=True)
    session = "synthetic-panic-session"
    inputs = [{"type": "grid", "x": 3, "y": 8, "pressed": True}]
    assertion = {"kind": "panic-full-stream-accounting", "note_events": 6144,
                 "windows": 1, "unaccounted": 0, "passed": True}
    pixel_frame, screen_rle = frame(17)
    grid = [0] * 128
    grid_digest = sha(bytes(grid))
    binding = {"capture_stage": "before-finish", "assertion_index": 0,
               "assertion": assertion, "assertion_sha256": sha(canonical(assertion)),
               "trace_sha256": sha(canonical(inputs)), "sha256": pixel_frame["sha256"],
               "grid_sha256": grid_digest, "stable_sha256": sha(base64.b64decode(pixel_frame["pixels_base64"])[0:128 * 55 * 4])}
    counts = {"kind": "panic-port-counts", "counts": {"1": 2048, "2": 2048, "3": 2048},
              "button": 4, "source": "grid"}
    result = [assertion, binding, counts]
    step = {"id": "hold-and-release", "inputs": inputs,
            "expect": {"kind": "panic-sweep", "passed": True},
            "output": {"binding": binding, "grid": grid, "screen_rle": screen_rle}}
    scene = {"id": "panic-from-song-channel", "behaviour_case": "manual/midi-panic",
             "evidence": {"path": str(source)}, "steps": [step]}
    identity = {"session_id": session, "application_identity": {"digest": "synthetic-app-digest"}}
    context = {"session_id": session, "finished": True, "cleanup_verified": True, "held_inputs": []}
    scene["evidence"]["session_context"] = context
    write_json(native / "identity.json", identity)
    write_json(native / "cleanup.json", [{"returncode": 0}])
    write_json(source / "results.json", result)
    write_json(source / "recipe.json", {"fixture": "synthetic"})
    write_json(source / "capture-trace.json", inputs)
    write_json(source / "session-context.json", context)
    original = {"id": scene["id"], "steps": copy.deepcopy(scene["steps"])}
    write_json(source / "captured-scenes.json", [original])
    window = {"type": "panic", "after": 0, "cursor": 6144, "button": 4, "source": "grid",
              "minimum_ns": 1,
              "press_ack": {"session_id": session, "status": "applied", "action_id": "panic-action",
                             "native": {"sequence": 1}},
              "input_origin": {"action_id": "panic-action", "native_sequence": 1,
                               "origin_ns": 50, "applied_ns": 60}}
    write_json(source / "panic-windows.json", [window])
    midi = []
    for port in (1, 2, 3):
        for channel in range(16):
            for note in range(128):
                index = len(midi) + 1
                midi.append(event(index, port, [0x80 + channel, note, 0]))
    rows = [
        {"kind": "input", "sequence": 1, "type": 3, "args": [3, 7, 1], "monotonic_ns": 50},
        {"kind": "input_timing", "sequence": 1, "native_ack_ns": 60},
    ] + midi
    with (native / "native-events.jsonl").open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    empty_frame, _ = frame(34)
    observations = [
        observation(session, 0, [], empty_frame, grid),
        observation(session, 6144, [midi[-1]], pixel_frame, grid),
    ]
    write_json(source / "observations.json", observations)
    write_json(source / "session-context.json", context)
    return scene, project, build, source


class FreshMidiReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fresh-midi-receipt-unit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_masks_current_stage_authority_and_exact_target_windows(self):
        scenes, project, build = make_masks_fixture(self.root)
        manifest = fresh.build_fresh_target_midi_manifest(scenes, project, build, "derived-unit-fixture")
        records = fresh.validate_fresh_target_midi_manifest(scenes, project, build, manifest)
        self.assertEqual(set(manifest["scenes"]), set(MASKS))
        self.assertEqual(manifest["masks_stage"]["stage_name"], "masks-controlled")
        for scene_id, (_, target_id) in MASKS.items():
            scene = next(row for row in scenes if row["id"] == scene_id)
            projected = fresh.project_fresh_target_midi(scene, project, build, manifest, records)
            target = next(row for row in projected["steps"] if row["id"] == target_id)
            receipt = target["output"]["midi"]
            wanted = target["expect"]["midi_phrase"]
            self.assertEqual(receipt["events"], [{"index": 2, "sequence": 2, "port": 1,
                "bytes": wanted[0]["bytes"], "kind": 3, "monotonic_ns": 1002,
                "logical_ns": 2002, "device_id": "synthetic-midi", "port_name": "synthetic-midi"}])
            self.assertEqual(receipt["provenance"]["transition"]["baseline_midi_count"], 1)
            self.assertEqual(receipt["provenance"]["transition"]["target_midi_count"], 2)
            self.assertEqual(receipt["provenance"]["complete_native_event_count"], 3)
            self.assertFalse(receipt["truncated"])

    def test_masks_stage_log_tamper_invalidates_manifest(self):
        scenes, project, build = make_masks_fixture(self.root)
        manifest = fresh.build_fresh_target_midi_manifest(scenes, project, build, "derived-unit-fixture")
        log = build / "masks-controlled.log"
        original = log.read_bytes()
        try:
            log.write_bytes(original + b"tampered\n")
            with self.assertRaisesRegex(fresh.FreshMidiError, "Masks stage log differs from its sidecar hash"):
                fresh.validate_fresh_target_midi_manifest(scenes, project, build, manifest)
        finally:
            log.write_bytes(original)

    def test_masks_target_frame_without_new_midi_is_rejected_after_reseal(self):
        scenes, project, build = make_masks_fixture(self.root)
        scene = next(row for row in scenes if row["id"] == "mask-precedence")
        obs_path = Path(scene["evidence"]["path"]) / "observations.json"
        observations = json.loads(obs_path.read_text(encoding="utf-8"))
        observations[1]["state"]["midi_count"] = 1
        observations[1]["state"]["midi_capture"]["count"] = 1
        observations[1]["state"]["midi"] = observations[1]["state"]["midi"][:1]
        write_json(obs_path, observations)
        manifest = fresh.build_fresh_target_midi_manifest(scenes, project, build, "derived-unit-fixture")
        records = fresh.validate_fresh_target_midi_manifest(scenes, project, build, manifest)
        with self.assertRaisesRegex(fresh.FreshMidiError, "Masks target frame MIDI count is ambiguous"):
            fresh.project_fresh_target_midi(scene, project, build, manifest, records)

    def test_panic_full_sweep_projects_exact_6144_packet_window(self):
        scene, project, build, source = make_panic_fixture(self.root)
        manifest = fresh.build_fresh_target_midi_manifest([scene], project, build, "derived-unit-fixture")
        records = fresh.validate_fresh_target_midi_manifest([scene], project, build, manifest)
        projected = fresh.project_fresh_target_midi(scene, project, build, manifest, records)
        target = projected["steps"][0]
        midi = target["output"]["midi"]
        journal = [json.loads(line) for line in (source / "native" / "native-events.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(midi["events"], [row for row in journal if row.get("kind") in (3, 11)])
        self.assertEqual(midi["total"], 6144)
        self.assertEqual(midi["provenance"]["window_start_index"], 1)
        self.assertEqual(midi["provenance"]["window_end_index"], 6144)
        self.assertFalse(midi["truncated"])

    def test_panic_window_cutoff_is_rejected_even_when_source_manifest_is_resealed(self):
        scene, project, build, source = make_panic_fixture(self.root)
        window_path = source / "panic-windows.json"
        windows = json.loads(window_path.read_text(encoding="utf-8"))
        windows[0]["cursor"] = 6143
        write_json(window_path, windows)
        manifest = fresh.build_fresh_target_midi_manifest([scene], project, build, "derived-unit-fixture")
        records = fresh.validate_fresh_target_midi_manifest([scene], project, build, manifest)
        with self.assertRaisesRegex(fresh.FreshMidiError, "panic actual full window count changed"):
            fresh.project_fresh_target_midi(scene, project, build, manifest, records)


if __name__ == "__main__":
    unittest.main()





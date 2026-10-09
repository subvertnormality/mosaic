"""Portable pipeline characterisation outside the manual.

The DERIVED fixture preserves a qualified manual:masks / M-MASK-007 native
observation. These tests qualify admission/projection logic, not another native run.
"""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import manual_pilot_midi
import manual_reader_projection
import manual_teaching_v8

FIXTURE = ROOT / "test-fixtures" / "retained-pilot-midi-v1"

def read(path):
    return json.loads(path.read_bytes())

def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class RetainedPilotMidi(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "native-case"
        shutil.copytree(FIXTURE, self.root)
        self.scene = read(self.root / "scene.json")
        self.scene["evidence"]["path"] = str(self.root)

    def project(self):
        return manual_pilot_midi.project_pilot_midi(self.scene)

    def journal(self):
        return [json.loads(line) for line in (self.root / "native/native-events.jsonl").read_bytes().splitlines()]

    def write_journal(self, rows):
        (self.root / "native/native-events.jsonl").write_text(
            "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows) + "\n",
            encoding="utf-8")

    def test_complete_original_window_preserves_packets_times_programs_and_closing_release(self):
        original = copy.deepcopy(self.scene)
        projected = self.project()
        self.assertEqual(self.scene, original)
        midi = projected["steps"][1]["output"]["midi"]
        self.assertEqual(midi["events"], self.journal()[10:70])
        self.assertEqual(midi["total"], 60)
        self.assertFalse(midi["truncated"])
        self.assertEqual([row["index"] for row in midi["events"]], list(range(11, 71)))
        self.assertEqual({row["port"] for row in midi["events"]}, {1, 2, 3})
        self.assertEqual(midi["events"][0]["bytes"], [250])
        self.assertEqual(midi["events"][-1]["bytes"], [252])
        ons = [r for r in midi["events"] if len(r["bytes"]) == 3 and r["bytes"][0] == 144 and r["bytes"][2] > 0]
        offs = [r for r in midi["events"] if len(r["bytes"]) == 3 and r["bytes"][0] == 128]
        programs = [r for r in midi["events"] if r["bytes"][0] & 240 == 192]
        self.assertEqual(len(ons), 9)
        self.assertEqual(len(offs), 9)
        self.assertTrue(programs)
        self.assertEqual(ons[-1]["logical_ns"] - ons[0]["logical_ns"], 1333333334)
        self.assertEqual(ons[0]["monotonic_ns"], self.journal()[17]["monotonic_ns"])
        self.assertEqual(midi["note_on_observation"]["actual"], read(self.root / "results.json")[13]["actual"])
        self.assertEqual(midi["note_on_observation"]["result_index"], 13)
        self.assertEqual(midi["provenance"]["complete_native_event_count"], 70)
        self.assertEqual(midi["provenance"]["window_start_index"], 11)
        self.assertEqual(midi["provenance"]["window_end_index"], 70)
        self.assertEqual(midi["provenance"]["newly_sealed_retained_sources"],
                         ["observations.json", "native/native-events.jsonl"])

    def test_real_producer_publishes_exact_observed_window_in_hash_verified_chunk(self):
        # Real teaching assembly runs with an empty lesson inventory; no stubs or AST extraction.
        book = {"features": [], "scenes": {self.scene["id"]: self.scene}}
        index, chunks = manual_reader_projection.build_projection(book, {"examples": []})
        ref = index["scene_chunks"][self.scene["id"]]
        self.assertEqual(hashlib.sha256(chunks[ref["path"]]).hexdigest(), ref["sha256"])
        chunk = json.loads(chunks[ref["path"]])
        self.assertEqual(chunk["steps"][1]["output"].get("midi"),
                         self.project()["steps"][1]["output"]["midi"])
        self.assertNotIn("midi", self.scene["steps"][1]["output"])
        output = self.root / "projection"
        manual_reader_projection.write_projection(book, {"examples": []}, output)
        report = manual_reader_projection.validate_projection(
            output / "reader-index.json", output / "reader-chunks", book, {"examples": []})
        self.assertTrue(report["passed"])
        # A different published native packet must fail chunk hash verification.
        published = output / ref["path"]
        bad = copy.deepcopy(chunk)
        bad["steps"][1]["output"]["midi"]["events"][0]["port"] = 9
        write(published, bad)
        with self.assertRaises(manual_reader_projection.ProjectionError):
            manual_reader_projection.validate_projection(
                output / "reader-index.json", output / "reader-chunks", book, {"examples": []})

    def test_expected_only_phrase_is_rejected_by_real_teaching_producer(self):
        phrase = self.scene["steps"][1]["expect"]["midi_phrase"]
        native = {"to_step": {"output": {}, "expect": {"midi_phrase": phrase}}}
        with self.assertRaisesRegex(ValueError, "target MIDI missing or truncated"):
            manual_teaching_v8._validate_output(native, {"midi_events_at_target": phrase})

    def test_missing_note_off_and_reordered_stream_are_rejected(self):
        original = self.journal()
        missing = copy.deepcopy(original)
        missing.pop(next(i for i, row in enumerate(missing) if row["bytes"][0] == 128))
        reordered = copy.deepcopy(original)
        reordered[18], reordered[19] = reordered[19], reordered[18]
        for rows in (missing, reordered):
            with self.subTest(mutation="missing" if len(rows) < 70 else "reordered"):
                self.write_journal(rows)
                with self.assertRaisesRegex(manual_pilot_midi.PilotMidiError, "missing or unordered"):
                    self.project()

    def test_raw_pitch_or_timestamp_tamper_is_rejected(self):
        original = self.journal()
        for field in ("bytes", "logical_ns", "monotonic_ns", "port"):
            with self.subTest(field=field):
                rows = copy.deepcopy(original)
                row = next(r for r in rows if r["bytes"] == [144, 67, 127])
                row[field] = [144, 68, 127] if field == "bytes" else row[field] + 1
                self.write_journal(rows)
                with self.assertRaisesRegex(manual_pilot_midi.PilotMidiError, "differs from observed snapshot"):
                    self.project()

    def test_foreign_identity_and_unpinned_identity_are_rejected(self):
        identity_path = self.root / "native/identity.json"
        identity = read(identity_path)
        identity["session_id"] = "foreign-native-session"
        write(identity_path, identity)
        with self.assertRaisesRegex(manual_pilot_midi.PilotMidiError, "identity changed"):
            self.project()
        # Repinning a derived fixture identity does not excuse foreign observed sessions.
        self.scene["evidence"]["identity_sha256"] = digest(identity_path)
        with self.assertRaisesRegex(manual_pilot_midi.PilotMidiError, "another native session"):
            self.project()

    def test_foreign_frame_and_actual_witness_are_rejected(self):
        self.scene["steps"][1]["output"]["binding"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(manual_pilot_midi.PilotMidiError, "original bound frame"):
            self.project()
        self.scene = read(self.root / "scene.json")
        self.scene["evidence"]["path"] = str(self.root)
        results_path = self.root / "results.json"
        rows = read(results_path)
        rows[13]["actual"][0][1][1] = 68
        write(results_path, rows)
        self.scene["evidence"]["results_sha256"] = digest(results_path)
        with self.assertRaisesRegex(manual_pilot_midi.PilotMidiError, "original actual witness"):
            self.project()

    def test_capture_loss_and_incomplete_stop_boundary_are_rejected(self):
        path = self.root / "observations.json"
        observations = read(path)
        observations[0]["state"]["midi_capture"]["dropped"] = 1
        write(path, observations)
        with self.assertRaisesRegex(manual_pilot_midi.PilotMidiError, "missing or truncated"):
            self.project()
        observations = read(FIXTURE / "observations.json")
        rows = self.journal()
        for row in rows:
            if row["bytes"] == [252]:
                row["bytes"] = [248]
        for row in observations[0]["state"]["midi"]:
            if row["bytes"] == [252]:
                row["bytes"] = [248]
        self.write_journal(rows)
        write(path, observations)
        with self.assertRaisesRegex(manual_pilot_midi.PilotMidiError, "complete Stop boundary"):
            self.project()

if __name__ == "__main__":
    unittest.main()

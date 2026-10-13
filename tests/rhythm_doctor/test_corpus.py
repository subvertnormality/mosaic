"""RD-02 corpus manifest characterisation outside the manual; PLAN.md gates."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from corpus import CorpusValidationError, validate_manifest
from corpus_materialize import drum_lane


LANES = ("BD", "SD", "CHH", "OHH", "BASS")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_file(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {"path": relative, "sha256": digest(path)}


def fixture(root, clip_id, split, index, *, events=None, tags=None, bpm=120, stratum="full_mix"):
    events = events if events is not None else {lane: [{"time_seconds": step / 8, "velocity": 96} for step in range(5)] for lane in LANES}
    timbres = {lane: "acoustic" if index % 2 else "electronic" for lane in LANES}
    annotation = write_file(root, f"annotations/{clip_id}.json", json.dumps({
        "reference_origin": "independent_render_metadata", "annotator_id": "frozen-midi-v1", "events": events,
    }, sort_keys=True).encode())
    return {
        "id": clip_id, "split": split, "source_id": "slakh", "source_song_id": f"{split}-song-{index}",
        "kit_id": f"{split}-kit-{index}", "audio": write_file(root, f"audio/{clip_id}.wav", clip_id.encode()),
        "source_start_seconds": 0,
        "render": {"kind": "source_mix", "recipe": write_file(root, f"recipes/{clip_id}.json", b'{"gain_db":0}')},
        "annotation": annotation, "duration_seconds": 960 / bpm if split != "acquisition" else 24,
        "bpm": bpm, "stratum": stratum,
        "timbres": timbres,
        "timbre_evidence": write_file(root, f"timbres/{clip_id}.json", json.dumps({"lanes": {
            lane: {"timbre": timbres[lane], "basis": "source_patch_metadata", "source": "frozen-patch-map-v1"}
            for lane in LANES
        }}, sort_keys=True).encode()),
        "tags": tags or [],
    }


def complete_manifest(root):
    archive = write_file(root, "downloads/babyslakh.tar.gz", b"official archive bytes")
    evidence = write_file(root, "provenance/zenodo-record.json", b'{"license":"CC-BY-4.0"}')
    clips = []
    for index in range(40):
        clips.append(fixture(root, f"dev-{index}", "development", index))
    strata = ["full_mix"] * 6 + ["sparse"] * 2 + ["isolated"] * 2
    for index in range(40):
        events = {lane: [{"time_seconds": step / 8, "velocity": 96} for step in range(5)] for lane in LANES}
        if 10 <= index < 35:
            events[LANES[(index - 10) // 5]] = []
        if index >= 35:
            events = {lane: [] for lane in LANES}
        tags = []
        if index in (35, 36, 37): tags.append("silence")
        if index == 38: tags.append("clipping")
        if index == 39: tags.extend(("phase_inverted_stereo", "kick_bass_unison"))
        clips.append(fixture(root, f"held-{index}", "held_out", index, events=events, tags=tags,
                             stratum=strata[index] if index < 10 else "full_mix"))
    scenarios = [
        (40, "random_record_phase"), (60, "silence_or_intro"), (120, "syncopation"),
        (180, "half_double_ambiguous"), (240, "changing_tempo"), (120, "uncertain_downbeat"),
    ]
    for index, (bpm, tag) in enumerate(scenarios):
        clips.append(fixture(root, f"acq-{index}", "acquisition", index, bpm=bpm, tags=[tag]))
    return {
        "schema_version": 2, "corpus_id": "rd02-test-corpus-schema-v2", "sources": [{
            "id": "slakh", "record_url": "https://zenodo.org/records/4603870",
            "license": {"spdx": "CC-BY-4.0", "url": "https://creativecommons.org/licenses/by/4.0/"},
            "archive": archive, "license_evidence": evidence, "domain": "rendered",
        }], "clips": clips,
    }


class CorpusManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.manifest = complete_manifest(self.root)

    def validate(self):
        path = self.root / "manifest.json"; path.write_text(json.dumps(self.manifest)); return validate_manifest(path)

    def test_complete_independent_corpus_proves_every_structural_gate(self):
        report = self.validate()
        self.assertEqual((report["development_clips"], report["held_out_clips"]), (40, 40))
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["held_out_events"], {lane: 150 for lane in LANES})

    def test_general_midi_hat_notes_are_split_into_closed_and_open_lanes(self):
        self.assertEqual(drum_lane(42), "CHH")
        self.assertEqual(drum_lane(44), "CHH")
        self.assertEqual(drum_lane(46), "OHH")
        self.assertIsNone(drum_lane(47))

    def test_pinned_gpl_source_is_licensed_corpus_evidence(self):
        self.manifest["sources"][0]["license"]["spdx"] = "GPL-2.0"
        self.manifest["sources"][0]["license"]["url"] = "https://www.gnu.org/licenses/old-licenses/gpl-2.0.html"
        self.assertEqual(self.validate()["development_clips"], 40)

    def test_legacy_schema_v1_manifest_is_rejected(self):
        self.manifest["schema_version"] = 1
        with self.assertRaisesRegex(CorpusValidationError, "unsupported"):
            self.validate()

    def test_hash_checked_annotations_cannot_be_replaced_after_manifest_freeze(self):
        self.manifest["clips"][0]["annotation"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(CorpusValidationError, "hash mismatch"):
            self.validate()

    def test_windows_absolute_descriptor_cannot_escape_the_corpus_root(self):
        self.manifest["clips"][0]["audio"]["path"] = r"C:\\outside.wav"
        with self.assertRaisesRegex(CorpusValidationError, "relative path"):
            self.validate()

    def test_event_at_exact_clip_endpoint_is_rejected(self):
        clip = self.manifest["clips"][0]
        annotation = self.root / clip["annotation"]["path"]
        payload = json.loads(annotation.read_text())
        payload["events"]["BD"][-1]["time_seconds"] = clip["duration_seconds"]
        annotation.write_text(json.dumps(payload)); clip["annotation"]["sha256"] = digest(annotation)
        with self.assertRaisesRegex(CorpusValidationError, "exceeds clip duration"):
            self.validate()

    def test_song_and_kit_leakage_is_rejected(self):
        self.manifest["clips"][40]["source_song_id"] = self.manifest["clips"][0]["source_song_id"]
        with self.assertRaisesRegex(CorpusValidationError, "source songs overlap"):
            self.validate()
        self.manifest["clips"][40]["source_song_id"] = "held-song-0"
        self.manifest["clips"][40]["kit_id"] = self.manifest["clips"][0]["kit_id"]
        with self.assertRaisesRegex(CorpusValidationError, "kits overlap"):
            self.validate()

    def test_duplicate_non_silence_held_pcm_cannot_pose_as_distinct_songs(self):
        first, second = self.manifest["clips"][40], self.manifest["clips"][41]
        second["audio"] = dict(first["audio"])
        self.assertNotEqual(first["source_song_id"], second["source_song_id"])
        with self.assertRaisesRegex(CorpusValidationError, "non-silence PCM is duplicated"):
            self.validate()

    def test_additional_mixture_sources_must_be_distinct_and_known(self):
        second_source = dict(self.manifest["sources"][0]); second_source["id"] = "bass-source"
        self.manifest["sources"].append(second_source)
        clip = self.manifest["clips"][40]
        clip["additional_source_ids"] = ["bass-source"]
        self.assertEqual(self.validate()["held_out_clips"], 40)
        clip["additional_source_ids"] = ["bass-source", "bass-source"]
        with self.assertRaisesRegex(CorpusValidationError, "invalid additional_source_ids"):
            self.validate()

    def test_adjacent_segments_of_one_recording_are_rejected(self):
        second = self.manifest["clips"][1]
        first = self.manifest["clips"][0]
        second["source_song_id"] = first["source_song_id"]
        second["source_start_seconds"] = first["duration_seconds"]
        with self.assertRaisesRegex(CorpusValidationError, "adjacent source clips"):
            self.validate()

    def test_timbre_names_require_pinned_matching_source_evidence(self):
        clip = self.manifest["clips"][40]
        path = self.root / clip["timbre_evidence"]["path"]
        evidence = json.loads(path.read_text())
        evidence["lanes"]["BD"]["timbre"] = "acoustic"
        path.write_text(json.dumps(evidence)); clip["timbre_evidence"]["sha256"] = digest(path)
        with self.assertRaisesRegex(CorpusValidationError, "lacks matching source-backed evidence"):
            self.validate()

    def test_missing_lane_stratum_negative_or_independence_is_rejected(self):
        for clip in self.manifest["clips"][40:50]:
            clip["stratum"] = "full_mix"
        with self.assertRaisesRegex(CorpusValidationError, "required full/sparse/isolated strata"):
            self.validate()
        self.manifest = complete_manifest(self.root)
        held_bd_negatives = [clip for clip in self.manifest["clips"] if clip["split"] == "held_out"
                             and clip["id"] not in {"held-35", "held-36", "held-37"}]
        for clip in held_bd_negatives:
            annotation = self.root / clip["annotation"]["path"]
            payload = json.loads(annotation.read_text())
            payload["events"]["BD"] = [
                {"time_seconds": step / 8, "velocity": 90} for step in range(5)
            ]
            annotation.write_text(json.dumps(payload)); clip["annotation"]["sha256"] = digest(annotation)
        with self.assertRaisesRegex(CorpusValidationError, "absent-lane negatives"):
            self.validate()
        self.manifest = complete_manifest(self.root)
        annotation = self.root / self.manifest["clips"][40]["annotation"]["path"]
        payload = json.loads(annotation.read_text()); payload["reference_origin"] = "detector_output"; annotation.write_text(json.dumps(payload))
        self.manifest["clips"][40]["annotation"]["sha256"] = digest(annotation)
        with self.assertRaisesRegex(CorpusValidationError, "not independent"):
            self.validate()

    def test_acquisition_envelope_is_not_waived(self):
        self.manifest["clips"][-1]["tags"] = ["different"]
        with self.assertRaisesRegex(CorpusValidationError, "scenario tags"):
            self.validate()
        self.manifest = complete_manifest(self.root)
        self.manifest["clips"][-1]["duration_seconds"] = 45.1
        with self.assertRaisesRegex(CorpusValidationError, "exceeds 45"):
            self.validate()


if __name__ == "__main__":
    unittest.main()

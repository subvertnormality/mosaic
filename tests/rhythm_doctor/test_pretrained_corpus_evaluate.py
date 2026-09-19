"""Characterisation of the pretrained-corpus quality evaluator outside README."""
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import wave


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor_analysis"))
import pretrained_corpus_evaluate as evaluator


LANES = ("BD", "SD", "CHH", "OHH", "BASS")
STRATA = ("isolated", "sparse", "full_mix")


def clip(clip_id, split, stratum, audio, events):
    return {
        "id": clip_id, "split": split, "stratum": stratum, "bpm": 120,
        "audio": {"path": "audio/%s.wav" % clip_id, "sha256": audio},
        "annotation": {"path": "annotations/%s.json" % clip_id, "sha256": "a" * 64},
        "events": events,
        "tags": ["gain_ladder", "independent_velocity"] if stratum == "isolated" else [],
    }


class PretrainedCorpusEvaluateTests(unittest.TestCase):
    def test_development_threshold_is_deterministic_and_never_reads_held_out(self):
        development = [{"events": {name: ([{"time_seconds": 1, "velocity": 80}] if name == "BD" else []) for name in LANES},
                        "prediction": {"candidates": [
                            {"lane": "BD", "sample_index": 16000, "confidence": .8, "velocity": 80},
                            {"lane": "BD", "sample_index": 32000, "confidence": .2, "velocity": 80},
                        ]}, "bpm": 120}]
        # A hypothetical held-out perfect low-confidence onset must not affect
        # selection: the .8 development gate wins over .2's false positive.
        gates = evaluator.select_development_thresholds(development, 16000)
        self.assertEqual(gates["BD"], .8)

    def test_held_rows_aggregate_one_to_one_onsets_cells_negatives_and_velocity(self):
        clips = []
        predictions = {}
        for lane_index, lane in enumerate(LANES):
            for stratum_index, stratum in enumerate(STRATA):
                clip_id = "%s-%s" % (lane, stratum)
                events = {name: [] for name in LANES}
                events[lane] = [{"time_seconds": .25, "velocity": 32},
                                {"time_seconds": .75, "velocity": 96}]
                clips.append(clip(clip_id, "held_out", stratum, "%064x" % (lane_index * 3 + stratum_index + 1), events))
                predictions[clip_id] = {"bpm": 120, "candidates": [
                    {"lane": lane, "sample_index": 4000, "confidence": .9, "velocity": 36},
                    {"lane": lane, "sample_index": 12000, "confidence": .9, "velocity": 100},
                ]}
        rows = evaluator.held_out_rows(clips, predictions, dict.fromkeys(LANES, .5), 16000)
        self.assertEqual(len(rows), 15)
        self.assertTrue(all(row["onset_tp"] == row["cell_tp"] == 2 for row in rows))
        self.assertTrue(all(row["negative_control_painted_events"] == 0 for row in rows))
        self.assertTrue(all(row["velocity_monotonic"] for row in rows))
        self.assertTrue(all(row["velocity_absolute_errors"] == [4, 4]
                            if row["stratum"] == "isolated" else not row["velocity_absolute_errors"]
                            for row in rows))

    def test_raw_predictions_cache_under_both_hashes_and_resumes_without_runtime(self):
        with tempfile.TemporaryDirectory(prefix="rd-evaluator-") as raw:
            root = Path(raw)
            item = clip("held", "held_out", "full_mix", "b" * 64,
                        {lane: [] for lane in LANES})
            calls = []

            def infer(one):
                calls.append(one["id"])
                return {"bpm": 120, "candidates": []}

            first = evaluator.cached_prediction(root, "model", "corpus", item, infer)
            second = evaluator.cached_prediction(root, "model", "corpus", item,
                                                 lambda _: self.fail("cache miss"))
            self.assertEqual((first, second, calls), ({"bpm": 120, "candidates": []},
                                                        {"bpm": 120, "candidates": []}, ["held"]))
            cache = root / "model" / "corpus" / "held.json"
            payload = json.loads(cache.read_text(encoding="utf-8"))
            self.assertEqual(payload["clip"]["audio_sha256"], "b" * 64)

    def test_candidate_floor_sets_every_drum_lane_and_basic_pitch_before_inference(self):
        runtime = type("Runtime", (), {})()
        runtime.drum_gates = dict.fromkeys(LANES[:-1], .2)
        runtime.bass_gate = .2
        runtime.bass_pipeline = type("Bass", (), {"onset": type("Onset", (), {"threshold": .2})()})()
        evaluator.force_candidate_floor(runtime)
        self.assertEqual(runtime.drum_gates, dict.fromkeys(LANES[:-1], 0.0))
        self.assertEqual((runtime.bass_gate, runtime.bass_pipeline.onset.threshold), (0.0, 0.0))

    def test_corpus_root_is_explicit_when_manifest_lives_below_external_cache(self):
        with tempfile.TemporaryDirectory(prefix="rd-evaluator-root-") as raw:
            root = Path(raw)
            def descriptor(relative, data):
                path = root / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
                return {"path": relative, "sha256": hashlib.sha256(data).hexdigest()}
            audio_path = root / "audio" / "clip.wav"; audio_path.parent.mkdir()
            with wave.open(str(audio_path), "wb") as target:
                target.setparams((1, 2, 16000, 1, "NONE", "not compressed")); target.writeframes(b"\x00\x00")
            annotation = descriptor("annotations/clip.json", json.dumps({
                "reference_origin": "independent_human", "annotator_id": "person",
                "events": {lane: [] for lane in LANES},
            }).encode())
            audio = {"path": "audio/clip.wav", "sha256": hashlib.sha256(audio_path.read_bytes()).hexdigest()}
            recipe = descriptor("recipes/clip.json", b"{}")
            timbre = descriptor("timbres/clip.json", b"{}")
            manifest = {"sources": [], "clips": [{"id": "clip", "audio": audio, "annotation": annotation,
                        "render": {"recipe": recipe}, "timbre_evidence": timbre}]}
            manifest_path = root / "manifests" / "v12" / "manifest.json"; manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with mock.patch.object(evaluator, "validate_manifest") as validate:
                _, clips, _, _ = evaluator.load_corpus(manifest_path, root)
            validate.assert_called_once_with(manifest_path, root.resolve())
            self.assertEqual((clips[0]["audio_path"], clips[0]["sample_rate"]), (audio_path.resolve(), 16000))

    def test_run_loads_the_pinned_runtime_once_and_marks_the_report_quality_only(self):
        def quality_rows():
            return [dict(lane=lane, stratum=stratum, onset_tp=8, onset_fp=0, onset_fn=0,
                         cell_tp=8, cell_fp=0, cell_fn=0, negative_control_painted_events=0,
                         negative_control_clips=5, velocity_absolute_errors=[4], velocity_monotonic=True)
                    for lane in LANES for stratum in STRATA]
        with tempfile.TemporaryDirectory(prefix="rd-evaluator-run-") as raw:
            root = Path(raw)
            items = []
            for split in ("development", "held_out"):
                item = clip(split, split, "full_mix", split[0] * 64,
                            {lane: [{"time_seconds": .25, "velocity": 80}] for lane in LANES})
                item["sample_rate"] = 16000
                item["audio_path"] = root / (split + ".wav")
                items.append(item)
            runtime = type("Runtime", (), {})()
            runtime.drum_gates = dict.fromkeys(LANES[:-1], .2)
            runtime.bass_gate = .2
            runtime.bass_pipeline = type("Bass", (), {
                "artifact_sha256": "f" * 64,
                "onset": type("Onset", (), {"threshold": .2})(),
            })()
            with mock.patch.object(evaluator, "load_corpus", return_value=({}, items, "corpus", {"manifest_sha256": "c" * 64})), \
                 mock.patch.object(evaluator.pretrained_runtime_factory, "make", return_value=runtime) as make, \
                 mock.patch.object(evaluator, "compose", return_value={"bpm": 120, "candidates": []}) as compose, \
                 mock.patch.object(evaluator, "select_development_thresholds", return_value=dict.fromkeys(LANES, .5)), \
                 mock.patch.object(evaluator, "held_out_rows", return_value=quality_rows()):
                report = evaluator.run(root / "manifest.json", root, root / "cache", root / "report.json")
            self.assertEqual((make.call_count, compose.call_count), (1, 2))
            self.assertFalse(report["complete_rd02_acceptance"])
            self.assertIn("quality-only", report["scope"])
            self.assertTrue(report["quality_report"]["passed"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

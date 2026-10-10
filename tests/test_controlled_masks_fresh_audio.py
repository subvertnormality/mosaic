"""Focused regressions for same-run controlled Masks audio publication."""
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

CANDIDATE = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))


def load_candidate(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build = load_candidate("controlled_masks_candidate_build", CANDIDATE / "tools/manual_build.py")
verify = load_candidate("controlled_masks_candidate_verify", CANDIDATE / "tools/manual_publication_verify.py")


class ControlledMasksBuild(unittest.TestCase):
    def options(self):
        return SimpleNamespace(
            emulator="/native/base", audio_emulator="/native/audio",
            controlled_install="/native/control.json", audio_install="/native/audio.json",
            mod_code_root="/voices", ffmpeg="/ffmpeg", real_install="/native/qualified-real.json",
            python="python3", browser_tests=False,
        )

    def test_paired_plan_keeps_controlled_masks_visuals_only_verify_only_flags(self):
        with mock.patch.object(build, "ROOT", REPO):
            stages = build.plan(self.options(), ["scene-plans.yaml"], controlled_local=False)
        command = next(row for row in stages if row["name"] == "masks-controlled")["command"]
        self.assertIn("--visuals-only", command)
        self.assertIn("--verify-only", command)
        self.assertNotIn("--controlled-local", command)
        self.assertIn("--mod-code-root", command)
        self.assertIn("--audio-emulator", command)
        self.assertIn("--audio-install", command)
        self.assertIn("--ffmpeg", command)
        self.assertNotIn("--preserve-published-audio", command)

    def test_controlled_local_masks_stage_captures_audio_and_visuals_in_one_run(self):
        with mock.patch.object(build, "ROOT", REPO):
            stages = build.plan(self.options(), ["scene-plans.yaml"], controlled_local=True)
        stage = next(row for row in stages if row["name"] == "masks-controlled")
        command = stage["command"]
        self.assertIn("--controlled-local", command)
        self.assertIn("--mod-code-root", command)
        self.assertIn("/voices", command)
        self.assertIn("--audio-emulator", command)
        self.assertIn("--audio-install", command)
        self.assertIn("--ffmpeg", command)
        self.assertIn("--clock-mode", command)
        self.assertNotIn("--visuals-only", command)
        self.assertNotIn("--verify-only", command)
        self.assertNotIn("--preserve-published-audio", command)


class FreshControlledMasksAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name) / "mosaic-manual-1.4.0"
        self.manual = root / "manual"
        (self.manual / "generated").mkdir(parents=True)
        (self.manual / "features").mkdir()
        self.authored_path = self.manual / "features/masks.yaml"
        self.authored_path.write_text("feature: masks\nscenes: []\n", encoding="utf-8")
        import yaml
        self.authored = yaml.safe_load(self.authored_path.read_text(encoding="utf-8"))
        self.source_sha = verify.source_hash(self.authored)
        self.run_id = "a" * 32
        self.run_root = root.parent / "mosaic-manual-runs" / self.run_id
        (self.run_root / "scene").mkdir(parents=True)
        (self.run_root / "case").mkdir()
        (self.run_root / "audio").mkdir()
        self.audio_path = self.run_root / "audio"
        self.data = {
            "source_sha256": self.source_sha,
            "scenes": [{"evidence": {"path": str(self.run_root / "scene")}}],
            "audio": {"evidence": {"path": str(self.audio_path)}, "files": []},
            "validation": {
                "validation_scope": "controlled-manual-generation",
                "realtime_qualification": "pending-ci",
                "clock_mode": "controlled-experimental",
                "complete_regression_run": False,
                "scene_build_complete": True,
                "pilot_complete": False,
                "source_sha256": self.source_sha,
                "run_id": self.run_id,
                "behaviour_cases": [{"case": "masks", "passed": True,
                                     "path": str(self.run_root / "case")}],
            },
        }
        self.publication = self.manual / "generated/pilot.json"
        self.publication.write_text(json.dumps(self.data), encoding="utf-8")
        self.patches = (
            mock.patch.object(verify, "ROOT", root),
            mock.patch.object(verify, "MANUAL", self.manual),
            mock.patch.object(verify, "audit_generic", return_value={"frames": 2, "baseline_cases": []}),
            mock.patch.object(verify, "audit_pilot_audio", return_value=3),
        )
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def audit(self):
        self.publication.write_text(json.dumps(self.data), encoding="utf-8")
        return verify.audit_controlled_pilot()

    def test_fresh_visual_and_audio_evidence_from_one_run_is_accepted(self):
        result = self.audit()
        self.assertEqual(result["frames"], 5)
        verify.audit_pilot_audio.assert_called_once_with(self.data, self.authored, check_receipt=True)

    def test_audio_from_another_run_is_rejected(self):
        other = self.run_root.parent / ("b" * 32) / "audio"
        other.mkdir(parents=True)
        self.data["audio"]["evidence"]["path"] = str(other)
        with self.assertRaisesRegex(ValueError, "exact visual capture run"):
            self.audit()

    def test_scene_evidence_outside_run_is_rejected(self):
        outside = Path(self.temp.name) / "unrelated-scene"
        outside.mkdir()
        self.data["scenes"][0]["evidence"]["path"] = str(outside)
        with self.assertRaisesRegex(ValueError, "scene is outside"):
            self.audit()

    def test_behavior_case_evidence_outside_run_is_rejected(self):
        outside = Path(self.temp.name) / "unrelated-case"
        outside.mkdir()
        self.data["validation"]["behaviour_cases"][0]["path"] = str(outside)
        with self.assertRaisesRegex(ValueError, "behaviour case is outside"):
            self.audit()

    def test_invalid_run_id_is_rejected(self):
        self.data["validation"]["run_id"] = "../escape"
        with self.assertRaisesRegex(ValueError, "exact capture run id"):
            self.audit()

    def test_missing_behavior_case_receipt_is_rejected(self):
        self.data["validation"]["behaviour_cases"] = []
        with self.assertRaisesRegex(ValueError, "lacks same-run behaviour"):
            self.audit()

    def test_failed_behavior_case_receipt_is_rejected(self):
        self.data["validation"]["behaviour_cases"][0]["passed"] = False
        with self.assertRaisesRegex(ValueError, "case receipt is not successful"):
            self.audit()

    def test_missing_audio_directory_is_rejected(self):
        self.audio_path.rmdir()
        with self.assertRaisesRegex(ValueError, "audio evidence is missing"):
            self.audit()

    def test_fresh_report_source_identity_must_match_current_authored_source(self):
        self.data["validation"]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source identity changed"):
            self.audit()

    def test_malformed_preserved_audio_does_not_fall_through_to_fresh_mode(self):
        self.data["validation"]["preserved_audio"] = None
        with self.assertRaisesRegex(ValueError, "preserved audio source receipt"):
            self.audit()
        verify.audit_pilot_audio.assert_not_called()

    def test_legacy_preserved_audio_path_remains_strict_and_supported(self):
        audio_file = self.manual / "generated/masks.wav"
        audio_file.write_bytes(b"preserved fixture")
        file_hash = verify.digest(audio_file)
        self.data["audio"]["files"] = ["generated/masks.wav"]
        self.data["validation"].pop("run_id")
        self.data["validation"]["behaviour_cases"] = []
        self.data["validation"]["preserved_audio"] = {
            "source_sha256": self.source_sha,
            "publication_path": str(self.publication),
            "file_sha256": {"generated/masks.wav": file_hash},
        }
        result = self.audit()
        self.assertEqual(result["frames"], 5)

    def test_legacy_preserved_audio_file_mutation_is_rejected(self):
        audio_file = self.manual / "generated/masks.wav"
        audio_file.write_bytes(b"preserved fixture")
        self.data["audio"]["files"] = ["generated/masks.wav"]
        self.data["validation"]["preserved_audio"] = {
            "source_sha256": self.source_sha,
            "publication_path": str(self.publication),
            "file_sha256": {"generated/masks.wav": "0" * 64},
        }
        with self.assertRaisesRegex(ValueError, "preserved audio files changed"):
            self.audit()


if __name__ == "__main__":
    unittest.main()

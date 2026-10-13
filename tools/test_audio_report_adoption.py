"""Regression coverage for explicit standalone controlled-audio report adoption."""
import hashlib
import json
import os
import contextlib
import copy
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
REPO = Path(os.environ.get("MOSAIC_REPO_ROOT", "/home/andy/mosaic-manual-1.4.0")).resolve()
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(REPO / "tools"))
sys.path.append(str(REPO / "tests" / "behaviour"))

import audio_report_adoption as adoption

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class AudioReportAdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.evidence = Path(self.temp.name) / "build"
        (self.root / "manual/generated").mkdir(parents=True)
        (self.root / "manual").mkdir(exist_ok=True)
        (self.root / "tests/behaviour").mkdir(parents=True)
        (self.root / "tools").mkdir()
        self.report_path = self.root / adoption.REPORT_RELATIVE
        self.report = {
            "passed": True,
            "complete_regression_run": False,
            "validation_scope": "controlled-manual-generation",
            "realtime_qualification": "pending-ci",
            "clock_mode": "controlled-experimental",
            "audio_capture_clock_mode": "real-time",
            "harness_sha256": {"manual_audio_browser.cjs": "a" * 64},
        }
        self.report_path.write_text(json.dumps(self.report, sort_keys=True) + "\n")
        for relative in (*adoption.SOURCE_PATHS, "tests/behaviour/manual_audio_browser.cjs"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("source:" + relative)
        (self.root / "tools/manual_build.py").write_text("builder candidate")
        self.evidence.mkdir()
        self.patches = [
            patch("manual_audio.audit_controlled_publication", return_value={"passed": True, "mocked_test_oracle": True}),
            patch("manual_publication_verify.audit_audio_session_integrity", return_value={"passed": True, "mocked_test_oracle": True}),
        ]
        # Imports are intentionally lazy in production; patch after importing both modules.
        import manual_audio
        import manual_publication_verify
        self.patches = [
            patch.object(manual_audio, "audit_controlled_publication", return_value={"passed": True, "mocked_test_oracle": True}),
            patch.object(manual_publication_verify, "audit_audio_session_integrity", return_value={"passed": True, "mocked_test_oracle": True}),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(self._stop_patches)

    def _stop_patches(self):
        for item in self.patches:
            item.stop()
        self.temp.cleanup()

    def prepare(self):
        return adoption.prepare_audio_report_adoption(
            self.report_path, sha(self.report_path), self.root, self.evidence
        )

    def build_manifest(self):
        record = self.prepare()
        record.update(name="musical-audio-assets")
        (self.evidence / "musical-audio-assets.json").write_text(json.dumps(record, indent=2) + "\n")
        manifest = {
            "audio_adoption": {"path": adoption.PROOF_NAME, "sha256": sha(self.evidence / adoption.PROOF_NAME)},
            "stages": [record],
        }
        return record, manifest

    def test_recorder_python_harness_names_are_accepted_and_unsafe_names_rejected(self):
        # Regression: the recorder pins driver.py, ui.py, ui_map.py, pcm_oracle.py and
        # channel_gestures.py, but adoption accepted only .cjs names and refused every real report.
        report = {"harness_sha256": {name: "a" * 64 for name in ("driver.py", "ui.py", "manual_audio_browser.cjs")}}
        for name in report["harness_sha256"]:
            path = self.root / "tests/behaviour" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("harness:" + name)
        hashes = adoption._source_hashes(self.root, report)
        self.assertIn("tests/behaviour/driver.py", hashes)
        self.assertIn("tests/behaviour/manual_audio_browser.cjs", hashes)
        for unsafe in ("../driver.py", "sub/driver.py", "driver.sh", "/tmp/driver.py"):
            with self.subTest(name=unsafe), self.assertRaisesRegex(ValueError, "Unsafe audio harness identity"):
                adoption._source_hashes(self.root, {"harness_sha256": {unsafe: "a" * 64}})

    def test_complete_published_report_is_adopted_and_reaudited_at_final_gate(self):
        record, manifest = self.build_manifest()
        result = adoption.audit_build_audio_adoption(self.evidence, manifest, self.root)
        self.assertTrue(result["audio"]["mocked_test_oracle"])
        self.assertTrue(result["sessions"]["mocked_test_oracle"])
        self.assertEqual(record["execution_status"], "adopted-verified")
        self.assertEqual(Path(record["native_report"]["path"]).read_bytes(), self.report_path.read_bytes())

    def test_final_gate_dispatches_audio_only_adoption_and_rechecks_tampering(self):
        import manual_publication_verify
        record, manifest = self.build_manifest()
        result = manual_publication_verify.audit_controlled_stage_adoptions(
            self.evidence, manifest, self.root
        )
        self.assertTrue(result["audio"]["audio"]["mocked_test_oracle"])
        self.assertTrue(result["audio"]["sessions"]["mocked_test_oracle"])
        self.assertIsNone(result["checkpoint"])

        bad_proof = copy.deepcopy(manifest)
        bad_proof["audio_adoption"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "proof changed or is missing"):
            manual_publication_verify.audit_controlled_stage_adoptions(
                self.evidence, bad_proof, self.root
            )

        bad_stage = copy.deepcopy(manifest)
        bad_stage["stages"][0]["execution_status"] = "executed"
        with self.assertRaisesRegex(ValueError, "stage receipt must be present exactly once"):
            manual_publication_verify.audit_controlled_stage_adoptions(
                self.evidence, bad_stage, self.root
            )

        changed_source = copy.deepcopy(manifest)
        (self.root / "tools/manual_audio_origin_audit.py").write_text("changed audit source")
        with self.assertRaisesRegex(ValueError, "source identity changed"):
            manual_publication_verify.audit_controlled_stage_adoptions(
                self.evidence, changed_source, self.root
            )
    def test_stage_dispatch_keeps_checkpoint_and_audio_audits_independent(self):
        import manual_publication_verify
        _, manifest = self.build_manifest()
        checkpoint_row = {"name": "reference-controlled-course", "execution_status": "adopted-verified"}
        manifest["stages"].append(checkpoint_row)
        with patch("resume_adoption.audit_resume_lineage", return_value={"checked": "checkpoint"}) as checkpoint_audit, \
             patch("audio_report_adoption.audit_build_audio_adoption", return_value={"checked": "audio"}) as audio_audit:
            result = manual_publication_verify.audit_controlled_stage_adoptions(
                self.evidence, manifest, self.root
            )
        checkpoint_audit.assert_called_once_with(self.evidence.resolve(), manifest, self.root.resolve())
        audio_audit.assert_called_once_with(self.evidence.resolve(), manifest, self.root.resolve())
        self.assertEqual(result, {"checkpoint": {"checked": "checkpoint"}, "audio": {"checked": "audio"}})
    def test_explicit_sha_mismatch_fails_before_adoption(self):
        with self.assertRaisesRegex(ValueError, "explicit pin"):
            adoption.prepare_audio_report_adoption(self.report_path, "0" * 64, self.root, self.evidence)

    def test_external_report_must_match_current_publication_byte_for_byte(self):
        external = self.root / "external.json"
        external.write_text(self.report_path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "exact current published report"):
            adoption.prepare_audio_report_adoption(external, sha(external), self.root, self.evidence)

    def test_incomplete_or_wrong_scope_report_is_rejected(self):
        self.report["passed"] = False
        self.report_path.write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, "passed controlled report"):
            adoption.prepare_audio_report_adoption(self.report_path, sha(self.report_path), self.root, self.evidence)

    def test_report_replacement_after_adoption_fails_final_gate(self):
        _, manifest = self.build_manifest()
        self.report_path.write_text(self.report_path.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "report or current publication changed"):
            adoption.audit_build_audio_adoption(self.evidence, manifest, self.root)

    def test_missing_or_modified_adoption_receipt_fails_final_gate(self):
        record, manifest = self.build_manifest()
        manifest.pop("audio_adoption")
        with self.assertRaisesRegex(ValueError, "marker and stage receipt"):
            adoption.audit_build_audio_adoption(self.evidence, manifest, self.root)
        manifest["audio_adoption"] = {"path": adoption.PROOF_NAME, "sha256": sha(self.evidence / adoption.PROOF_NAME)}
        record["native_report"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "stage receipt changed"):
            adoption.audit_build_audio_adoption(self.evidence, manifest, self.root)

    def test_authoring_or_producer_change_after_adoption_fails_closed(self):
        _, manifest = self.build_manifest()
        (self.root / "manual/audio-scenes.yaml").write_text("changed")
        with self.assertRaisesRegex(ValueError, "source identity changed"):
            adoption.audit_build_audio_adoption(self.evidence, manifest, self.root)

    def test_adoption_requires_full_existing_audio_and_session_oracles(self):
        self.prepare()
        import manual_audio
        import manual_publication_verify
        manual_audio.audit_controlled_publication.assert_called_once_with(self.report_path)
        manual_publication_verify.audit_audio_session_integrity.assert_called_once_with(self.report_path, controlled_local=True)

    def load_builder(self):
        import importlib.util
        builder_path = TOOLS / "manual_build.py"
        spec = importlib.util.spec_from_file_location("manual_build_candidate", builder_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_builder_requires_report_sha_and_controlled_local_mode(self):
        builder = self.load_builder()
        arguments = ["manual_build.py", "--emulator", "emu", "--audio-emulator", "audio",
            "--controlled-install", "controlled", "--audio-install", "audio-install",
            "--mod-code-root", "mods", "--adopt-audio-report", str(self.report_path),
            "--adopt-audio-report-sha256", sha(self.report_path)]
        with patch.object(sys, "argv", arguments), self.assertRaises(SystemExit) as caught:
            builder.main()
        self.assertEqual(caught.exception.code, 2)
        arguments.insert(arguments.index("--adopt-audio-report"), "--controlled-local")
        arguments.remove("--adopt-audio-report-sha256")
        arguments.remove(sha(self.report_path))
        with patch.object(sys, "argv", arguments), self.assertRaises(SystemExit) as caught:
            builder.main()
        self.assertEqual(caught.exception.code, 2)

    def test_controlled_plan_accepts_audio_and_checkpoint_resume_together(self):
        builder=self.load_builder()
        root=Path(tempfile.mkdtemp())
        (root/"manual").mkdir()
        (root/"manual/scene-plans-course.yaml").write_text("scenes: []\n")
        builder.ROOT=root
        arguments=["manual_build.py","--controlled-local","--emulator","emu",
            "--audio-emulator","audio","--controlled-install","controlled",
            "--audio-install","audio-install","--mod-code-root","mods",
            "--resume-from",str(self.root/"parent"),
            "--resume-manifest-sha256","1"*64,
            "--adopt-audio-report",str(self.report_path),
            "--adopt-audio-report-sha256",sha(self.report_path),"--plan-only"]
        with patch.object(sys,"argv",arguments), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(builder.main(),0)
        plan=json.loads(output.getvalue())
        self.assertIn("musical-audio-assets",[row["name"] for row in plan])

    def test_audio_and_checkpoint_adoptions_merge_only_when_stage_keys_are_disjoint(self):
        builder = self.load_builder()
        audio = {"musical-audio-assets": {"proof": "audio"}}
        checkpoint = {"reference-controlled-course": {"proof": "checkpoint"}}
        merged = builder.merge_stage_adoptions(audio, checkpoint)
        self.assertEqual(set(merged), {"musical-audio-assets", "reference-controlled-course"})
        with self.assertRaisesRegex(ValueError, "Conflicting adopted stage proofs"):
            builder.merge_stage_adoptions(audio, {"musical-audio-assets": {"proof": "other"}})

    def test_checkpoint_lineage_filters_only_the_separately_proven_audio_stage(self):
        import resume_adoption
        build = Path(tempfile.mkdtemp())
        audio_only = {"stages": [{"name": "musical-audio-assets", "execution_status": "adopted-verified"}]}
        self.assertIsNone(resume_adoption.audit_resume_lineage(build, audio_only, REPO))
        with self.assertRaisesRegex(ValueError, "no resume lineage"):
            resume_adoption.audit_resume_lineage(build, {"stages": [
                {"name": "musical-audio-assets", "execution_status": "adopted-verified"},
                {"name": "reference-controlled-course", "execution_status": "adopted-verified"},
            ]}, REPO)

    def test_builder_records_adoption_without_running_audio_producer(self):
        manual_build = self.load_builder()
        record, _ = self.build_manifest()
        record["command"] = ["python3", "manual_audio.py", "--controlled-local"]
        record["emulator"] = "/not-launched"
        (self.evidence / "musical-audio-assets.json").unlink()
        stages = [record]
        manifest = {"stages": []}
        with patch.object(manual_build, "await_stage_gate"), patch.object(manual_build, "run_stage") as run_stage:
            manual_build.run_build_stages(stages, self.evidence, object(), None,
                {"musical-audio-assets": record}, manifest)
        run_stage.assert_not_called()
        saved = json.loads((self.evidence / "musical-audio-assets.json").read_text())
        self.assertEqual(saved["execution_status"], "adopted-verified")
        self.assertEqual(manifest["stages"], [saved])
        log = (self.evidence / "musical-audio-assets.log").read_text()
        self.assertIn("source_report_sha256=" + saved["adopted_from"]["report_sha256"], log)
        self.assertNotIn("parent_manifest_sha256", log)

if __name__ == "__main__":
    unittest.main()

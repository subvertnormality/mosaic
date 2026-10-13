"""The reviewed setup driver is frozen with each audio run and bound by hash
(characterisation of manual-audio publication integrity, outside README.md)."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import yaml

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(REPO / "tools"))
import manual_audio


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        (self.root / "tools").mkdir(parents=True)
        (self.root / "tools/manual_audio_setups.py").write_text("SETUPS = {}\n")
        self.run = Path(self.tmp.name) / "run"
        self.run.mkdir()
        patcher = patch.object(manual_audio, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)


class FrozenWithTheRun(Fixture):
    def test_the_setup_driver_is_copied_into_the_run_and_hashed(self):
        digest = manual_audio.freeze_setups(self.run)
        self.assertEqual((self.run / "capture-setups.py").read_text(), "SETUPS = {}\n")
        self.assertEqual(digest, manual_audio.digest(self.root / "tools/manual_audio_setups.py"))


class AuditedIdentity(Fixture):
    def report(self):
        return dict(setups_sha256=manual_audio.freeze_setups(self.run))

    def test_matching_current_copy_and_report_pass(self):
        self.assertTrue(manual_audio.audit_setups_identity(self.report(), self.run))

    def test_edited_current_setup_driver_is_rejected(self):
        report = self.report()
        (self.root / "tools/manual_audio_setups.py").write_text("SETUPS = {'x': 1}\n")
        with self.assertRaisesRegex(ValueError, "Audio setups identity"):
            manual_audio.audit_setups_identity(report, self.run)

    def test_edited_run_copy_is_rejected(self):
        report = self.report()
        (self.run / "capture-setups.py").write_text("SETUPS = {'x': 1}\n")
        with self.assertRaisesRegex(ValueError, "Audio setups identity"):
            manual_audio.audit_setups_identity(report, self.run)

    def test_edited_report_hash_is_rejected(self):
        report = dict(self.report(), setups_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "Audio setups identity"):
            manual_audio.audit_setups_identity(report, self.run)

    def test_missing_report_hash_or_run_copy_is_rejected(self):
        report = self.report()
        with self.assertRaisesRegex(ValueError, "Audio setups identity"):
            manual_audio.audit_setups_identity({}, self.run)
        (self.run / "capture-setups.py").unlink()
        with self.assertRaisesRegex(ValueError, "Audio setups identity"):
            manual_audio.audit_setups_identity(report, self.run)


class WiredIntoThePublicationAudit(unittest.TestCase):
    def test_audit_publication_calls_the_setups_identity_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            source = manual_audio.MANUAL / "audio-scenes.yaml"
            authored = yaml.safe_load(source.read_text())
            (run / "source.yaml").write_text(source.read_text())
            (run / "capture-tool.py").write_text("tool")
            report = dict(source_sha256=manual_audio.digest(source), passed=True, complete_regression_run=False,
                          tool_sha256=manual_audio.digest(run / "capture-tool.py"),
                          examples=[dict(id=v["id"], evidence=dict(path=str(run / "x"))) for v in authored["examples"]])
            path = Path(tmp) / "report.json"
            path.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "Audio setups identity"):
                manual_audio.audit_publication(path)


if __name__ == "__main__":
    unittest.main()

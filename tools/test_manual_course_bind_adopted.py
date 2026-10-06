"""Course binding accepts an adopted course capture only through its adoption proof.

Regression from the isolated dry run: course-bind read the report path from the
stage log, but an adopted stage's log is the ADOPTED VERIFIED stub, so the
resumed controlled build failed ("Missing final case report path").
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(os.environ.get("MOSAIC_MANUAL_ROOT", Path(__file__).resolve().parents[1]))
sys.path[:0] = [str(REPO / "tools"), str(REPO / "tests/behaviour")]
import manual_build
import resume_adoption


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


NAME = "reference-controlled-scene-plans-course-base-midi"


class AdoptedCourseCapture(unittest.TestCase):
    def fixture(self, base):
        parent = base / "parent"; evidence = base / "resume"; parent.mkdir(); evidence.mkdir()
        report = base / "runs/abc/reference-scenes.json"; report.parent.mkdir(parents=True)
        report.write_text(json.dumps(dict(schema_version=1, scenes=[{"id": "course"}], **resume_adoption.SCOPE)))
        ref = {"path": str(report), "sha256": sha(report)}
        log = parent / (NAME + ".log"); log.write_text(str(report.parent) + "\n")
        row = {"name": NAME, "passed": True, "returncode": 0, "native_report": ref, "log_sha256": sha(log)}
        (parent / (NAME + ".json")).write_text(json.dumps(row))
        manifest = dict(passed=False, build_complete=False, controlled_local=True,
                        tool_sha256=resume_adoption.SUPPORTED_PARENT_BUILDER_SHA256, stages=[row], **resume_adoption.SCOPE)
        manifest_path = parent / "manifest.json"; manifest_path.write_text(json.dumps(manifest))
        item = {"name": NAME, "kind": "controlled-reference", "native_report": ref,
                "parent_stage_receipt_sha256": sha(parent / (NAME + ".json")), "parent_log_sha256": sha(log)}
        (evidence / "resume-adoption.json").write_text(json.dumps(
            {"parent_manifest": str(manifest_path), "parent_manifest_sha256": sha(manifest_path), "adopted": [item]}))
        record = dict(row, execution_status="adopted-verified",
                      adopted_from={"parent_manifest_sha256": sha(manifest_path),
                                    "parent_stage_receipt_sha256": item["parent_stage_receipt_sha256"],
                                    "parent_log_sha256": sha(log)})
        (evidence / (NAME + ".json")).write_text(json.dumps(record))
        (evidence / (NAME + ".log")).write_text("ADOPTED VERIFIED\n")
        return evidence, report, record

    def test_adopted_reference_resolves_to_its_proven_parent_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, report, record = self.fixture(Path(temporary))
            with patch("manual_publication_verify.audit_reference") as strict, \
                 patch.object(resume_adoption, "verify_current_native_inputs") as inputs:
                self.assertEqual(resume_adoption.verify_adopted_reference_stage(evidence, NAME, record, REPO), str(report))
                strict.assert_called_once(); inputs.assert_called_once()
                report.write_text(report.read_text().replace("course", "changed"))
                with self.assertRaisesRegex(ValueError, "parent report changed"):
                    resume_adoption.verify_adopted_reference_stage(evidence, NAME, record, REPO)

    def test_controlled_course_bind_uses_the_adopted_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence, report, record = self.fixture(Path(temporary))
            with patch.object(resume_adoption, "verify_adopted_reference_stage", return_value=str(report)) as verify:
                command = manual_build.course_bind_command(evidence, "/usr/bin/python3", controlled_local=True)
            verify.assert_called_once()
            self.assertEqual(command[command.index("--controlled-report") + 1], str(report))
            self.assertIn("--controlled-local", command)


if __name__ == "__main__":
    unittest.main()

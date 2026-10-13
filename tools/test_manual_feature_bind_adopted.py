"""Feature binding proves adopted native stages through the adoption proof.

Regression from the isolated dry run: stage_reports parsed each native stage's
log for its report, but adopted-verified stages carry an ADOPTED VERIFIED stub
log ("Missing final Doctor result").
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
import manual_feature_bind
import resume_adoption


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class AdoptedStageReports(unittest.TestCase):
    def stage(self, build, name, report, document, mode):
        report.parent.mkdir(parents=True, exist_ok=True); report.write_text(json.dumps(document))
        log = build / (name + ".log"); log.write_text("ADOPTED VERIFIED\nparent_manifest_sha256=x\n")
        record = dict(name=name, passed=True, returncode=0, log_sha256=sha(log), execution_status="adopted-verified",
                      native_report=dict(path=str(report), sha256=sha(report)), executed_command=["--clock-mode", mode])
        (build / (name + ".json")).write_text(json.dumps(record))
        return record

    def test_adopted_reference_and_doctor_reports_are_proven_not_parsed(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); build = base / "build"; build.mkdir()
            reference = base / "runs/r/reference-scenes.json"; doctor = base / "doctor/report.json"
            self.stage(build, "reference-controlled-scene-plans-course-base-midi", reference,
                       dict(clock_mode="controlled-experimental", scenes=[{}], complete_regression_run=False), "controlled-experimental")
            self.stage(build, "doctor-manual-real", doctor,
                       dict(passed=True, clock_mode="real-time", scenes=[{}], complete_regression_run=False), "real-time")
            with patch.object(resume_adoption, "verify_adopted_reference_stage", return_value=str(reference)) as ref, \
                 patch.object(resume_adoption, "verify_adopted_doctor_stage", return_value=str(doctor)) as doc:
                rows = manual_feature_bind.stage_reports(build, controlled_local=True)
            self.assertEqual(sorted(row["report"] for row in rows), sorted([str(reference), str(doctor)]))
            ref.assert_called_once(); doc.assert_called_once()

    def test_adopted_stage_whose_proof_names_another_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); build = base / "build"; build.mkdir()
            reference = base / "runs/r/reference-scenes.json"
            self.stage(build, "reference-controlled-scene-plans-course-base-midi", reference,
                       dict(clock_mode="controlled-experimental", scenes=[{}], complete_regression_run=False), "controlled-experimental")
            with patch.object(resume_adoption, "verify_adopted_reference_stage", return_value="/elsewhere/reference-scenes.json"):
                with self.assertRaisesRegex(ValueError, "adoption proof"):
                    manual_feature_bind.stage_reports(build, controlled_local=True)


if __name__ == "__main__":
    unittest.main()

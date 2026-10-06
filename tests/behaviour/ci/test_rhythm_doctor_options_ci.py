"""Static and portable contract tests for Doctor options CI orchestration."""
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from ci import rhythm_doctor_options_ci as matrix

ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "behaviour.yml"


class DoctorOptionsCiPlanTests(unittest.TestCase):
    def test_exact_six_adc_roles_plus_setup_and_ready_both_lanes(self):
        self.assertEqual(matrix.SIX_ADC_CASES, (
            "manual_stereo", "manual_left", "manual_right",
            "auto_stereo", "auto_left", "auto_right"))
        self.assertEqual(matrix.ROLE_PLAN, (
            ("manual_stereo", "real-time"), ("manual_left", "real-time"),
            ("manual_right", "real-time"), ("auto_stereo", "real-time"),
            ("auto_left", "real-time"), ("auto_right", "real-time"),
            ("setup_options", "real-time"),
            ("setup_options", "controlled-experimental"),
            ("ready_options", "real-time"),
            ("ready_options", "controlled-experimental")))
        self.assertFalse(any(case in matrix.SIX_ADC_CASES and lane != "real-time"
                             for case, lane in matrix.ROLE_PLAN))

    def test_manual_right_is_only_fixture_producer_and_ready_uses_exact_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installation = root / "install.json"
            installation.write_text("{}")
            app = root / "app"
            app.mkdir()
            fixture_path = root / "fixture.json"
            fixture_path.write_text('{"genuine":"autosave receipt"}')
            import hashlib
            fixture = {"path": str(fixture_path),
                       "sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest()}
            manual = matrix.capture_command("python3", "manual_right", "real-time",
                                            installation, root / "manual", app)
            self.assertEqual(manual.count("--save-ready-fixture"), 1)
            self.assertNotIn("--ready-fixture", manual)
            for case, lane in matrix.ROLE_PLAN:
                if case != "ready_options":
                    continue
                command = matrix.capture_command("python3", case, lane,
                                                 installation, root / "ready", app,
                                                 fixture)
                self.assertEqual(command[command.index("--ready-fixture") + 1],
                                 str(fixture_path))
                self.assertEqual(command[command.index("--ready-fixture-sha256") + 1],
                                 fixture["sha256"])
                self.assertNotIn("--save-ready-fixture", command)

    def test_summary_audits_all_ten_distinct_roles_before_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture.json"
            fixture.write_text("genuine fixture bytes")
            sessions = []
            for index, (case, lane) in enumerate(matrix.ROLE_PLAN):
                report = root / (str(index) + ".json")
                report.write_text(json.dumps({"case": case, "lane": lane}))
                row = {"case": case, "clock_mode": lane, "report": str(report)}
                if case == "manual_right":
                    import hashlib
                    row["fixture"] = {"path": str(fixture),
                                       "sha256": hashlib.sha256(fixture.read_bytes()).hexdigest()}
                sessions.append(row)
            calls = {"qualification": None, "extra": []}
            fake_audit = types.SimpleNamespace(
                ROLES={role: None for role in matrix.QUALIFIED_SEVEN},
                audit_qualification=lambda reports, path, sha: calls.update(
                    qualification=(set(reports), path, sha)) or {"passed": True},
                audit_report=lambda path, case, clock: calls["extra"].append(
                    (case, clock, path)) or {"passed": True})
            with patch.dict(sys.modules, {"doctor_options_audit": fake_audit}):
                summary = matrix.audit_sessions(sessions, root)
            self.assertTrue(summary["passed"])
            self.assertEqual(len(summary["roles"]), 10)
            self.assertEqual(calls["qualification"][0], matrix.QUALIFIED_SEVEN)
            self.assertEqual({row[0] for row in calls["extra"]}, matrix.EXTRA_THREE)
            self.assertTrue(all(row[1] == "real-time" for row in calls["extra"]))
            self.assertFalse(summary["complete_regression_run"])
            self.assertFalse(summary["hardware_timing_equivalent"])

    def test_behaviour_workflow_invokes_and_uploads_separate_options_qualification(self):
        text = WORKFLOW.read_text()
        self.assertIn("ci.test_rhythm_doctor_options_ci", text)
        self.assertIn("tests/behaviour/ci/rhythm_doctor_options_ci.py", text)
        self.assertIn("--audio-install /tmp/ci-audio-crow-tools/installation.json", text)
        self.assertIn("name: rhythm-doctor-options", text)


if __name__ == "__main__":
    unittest.main()

"""Run and independently audit the complete Rhythm Doctor option matrix in CI.

This is a scoped options qualification, not the global exhaustive suite. Public
ADC/softcut cases run only in real time; UI and persisted READY cases use both
available clock lanes. The READY fixture is exported by the real Manual/R run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAPTURE = ROOT / "tools" / "doctor_options_capture.py"
OUTPUT = ROOT / "tests" / "behaviour"
SIX_ADC_CASES = (
    "manual_stereo", "manual_left", "manual_right",
    "auto_stereo", "auto_left", "auto_right",
)
ROLE_PLAN = tuple((case, "real-time") for case in SIX_ADC_CASES) + (
    ("setup_options", "real-time"),
    ("setup_options", "controlled-experimental"),
    ("ready_options", "real-time"),
    ("ready_options", "controlled-experimental"),
)
QUALIFIED_SEVEN = {
    "manual_stereo", "auto_left", "manual_right",
    "setup_real", "setup_controlled", "ready_real", "ready_controlled",
}
EXTRA_THREE = {"manual_left", "auto_stereo", "auto_right"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def role_name(case: str, clock: str) -> str:
    return case if case not in ("setup_options", "ready_options") else (
        ("setup_" if case == "setup_options" else "ready_")
        + ("real" if clock == "real-time" else "controlled")
    )


def capture_command(python: str, case: str, clock: str, installation: Path,
                    output_root: Path, app_root: Path, fixture=None):
    command = [python, str(CAPTURE), "--case", case,
               "--installation", str(installation), "--clock-mode", clock,
               "--app-root", str(app_root), "--output-root", str(output_root)]
    if case == "manual_right":
        command.append("--save-ready-fixture")
    if case == "ready_options":
        if not fixture or not Path(fixture["path"]).is_file():
            raise ValueError("READY role lacks the genuine Manual/R fixture")
        if digest(Path(fixture["path"])) != fixture["sha256"]:
            raise ValueError("READY fixture changed before launch")
        command += ["--ready-fixture", fixture["path"],
                    "--ready-fixture-sha256", fixture["sha256"]]
    return command


def run_session(python: str, case: str, clock: str, installation: Path,
                out: Path, app_root: Path, fixture=None):
    directory = out / (case + "-" + clock)
    directory.mkdir(parents=True, exist_ok=False)
    command = capture_command(python, case, clock, installation, directory,
                              app_root, fixture)
    completed = subprocess.run(command, cwd=ROOT, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (directory / "orchestrator.log").write_text(completed.stdout)
    if completed.returncode:
        raise RuntimeError("Doctor capture failed for " + role_name(case, clock)
                           + " with exit " + str(completed.returncode))
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("Doctor capture emitted no receipt for " + case)
    receipt = json.loads(lines[-1])
    if receipt.get("passed") is not True:
        raise RuntimeError("Doctor capture receipt failed for " + case)
    report = Path(receipt["report"]).resolve()
    if not report.is_file():
        raise RuntimeError("Doctor capture report is missing for " + case)
    result = {"case": case, "clock_mode": clock, "report": str(report),
              "report_sha256": digest(report)}
    if case == "manual_right":
        fixture_path = receipt.get("fixture")
        if not fixture_path or not Path(fixture_path).is_file():
            raise RuntimeError("Manual/R did not export a genuine READY fixture")
        result["fixture"] = {"path": str(Path(fixture_path).resolve()),
                             "sha256": digest(Path(fixture_path))}
    return result


def audit_sessions(sessions, out):
    sys.path.insert(0, str(ROOT / "tools"))
    import doctor_options_audit as audit

    reports = {role_name(row["case"], row["clock_mode"]): Path(row["report"])
               for row in sessions}
    if set(reports) != QUALIFIED_SEVEN | EXTRA_THREE:
        raise ValueError("CI Doctor role inventory is incomplete: " + repr(sorted(reports)))
    fixture = reports["manual_right"]
    manual_right_session = next(row for row in sessions if row["case"] == "manual_right")
    fixture_info = manual_right_session.get("fixture")
    if not fixture_info:
        raise ValueError("Manual/R fixture receipt is absent")
    qualification = {role: reports[role] for role in audit.ROLES}
    base_audit = audit.audit_qualification(
        qualification, Path(fixture_info["path"]), fixture_info["sha256"])
    extra_audits = {}
    for role in sorted(EXTRA_THREE):
        extra_audits[role] = audit.audit_report(
            reports[role], role, "real-time")
    summary = {
        "schema_version": 1,
        "publication_kind": "doctor-options-ci-matrix",
        "passed": True,
        "roles": {key: dict(report=str(value), sha256=digest(value))
                  for key, value in sorted(reports.items())},
        "ready_fixture": fixture_info,
        "seven_role_audit": base_audit,
        "additional_adc_audits": extra_audits,
        "real_time_adc_cases": list(SIX_ADC_CASES),
        "controlled_time_audio": {
            "applicable": False,
            "reason": "Public ADC and softcut acquisition require real-time audio.",
        },
        "complete_regression_run": False,
        "hardware_timing_equivalent": False,
    }
    (out / "doctor-options-ci-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n")
    return summary


def run_matrix(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sessions = []
    fixture = None
    for case, clock in ROLE_PLAN:
        install = args.controlled_install if clock == "controlled-experimental" else args.audio_install
        session = run_session(sys.executable, case, clock, install, out,
                              args.app_root.resolve(), fixture)
        sessions.append(session)
        if case == "manual_right":
            fixture = session["fixture"]
    summary = audit_sessions(sessions, out)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-root", type=Path, required=True)
    parser.add_argument("--audio-install", type=Path, required=True)
    parser.add_argument("--controlled-install", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        summary = run_matrix(args)
    except Exception:
        args.output.mkdir(parents=True, exist_ok=True)
        failure = {"schema_version": 1,
                   "publication_kind": "doctor-options-ci-matrix",
                   "passed": False, "failure": traceback.format_exc(),
                   "complete_regression_run": False,
                   "hardware_timing_equivalent": False}
        (args.output / "doctor-options-ci-summary.json").write_text(
            json.dumps(failure, indent=2) + "\n")
        print(json.dumps(failure), flush=True)
        return 1
    print(json.dumps({"passed": summary["passed"],
                      "summary": str(args.output / "doctor-options-ci-summary.json")} ),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

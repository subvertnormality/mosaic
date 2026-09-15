#!/usr/bin/env python3
"""Fail closed unless the exact CI smoke selection completed in both lanes."""
import json
import sys
from pathlib import Path

EXPECTED = {
    "controlled-experimental": {"M-LEN-001", "M-TIME-001", "M-SYNC-001"},
    "real-time": {"M-PAT-001", "M-SAVE-001", "M-MAP-001"},
}

if len(sys.argv) != 3:
    raise SystemExit("usage: verify-smoke.py CONTROLLED_SUITE_JSON REAL_TIME_SUITE_JSON")
reports = []
for name in sys.argv[1:]:
    path = Path(name)
    if not path.is_file():
        raise SystemExit(f"behavior suite did not produce {path}")
    reports.append(json.loads(path.read_text()))

runs = [row for report in reports for row in report.get("cases", [])]
pairs = [(row.get("case"), row.get("lane")) for row in runs]
expected_pairs = {(case, lane) for lane, cases in EXPECTED.items() for case in cases}

problems = []
if any(report.get("status") != "finished" for report in reports):
    problems.append("a suite did not finish")
if any(report.get("passed") is not True for report in reports):
    problems.append("a suite did not pass")
if any(report.get("complete_regression_run") is not False for report in reports):
    problems.append("a smoke run was incorrectly labelled complete")
if set(pairs) != expected_pairs or len(pairs) != len(expected_pairs):
    problems.append("missing or duplicate case/lane pairs")
if any(row.get("passed") is not True for row in runs):
    problems.append("one or more case lanes failed")
summaries = [report.get("summary", {}) for report in reports]
if any(summary.get("sources_stable") is not True for summary in summaries):
    problems.append("tested source changed during the run")
if sum(summary.get("case_runs", 0) for summary in summaries) != len(expected_pairs):
    problems.append("unexpected case-run count")
if any(summary.get("case_runs_failed") for summary in summaries):
    problems.append("report contains failed case runs")
if problems:
    raise SystemExit("; ".join(problems))
print(f"verified {len(expected_pairs)} behavior smoke case lanes")

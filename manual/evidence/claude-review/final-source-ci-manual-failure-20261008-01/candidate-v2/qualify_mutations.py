"""Run external semantic mutations without editing repository authoring."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import yaml

root = Path("/home/andy/mosaic-manual-1.4.0")
candidate = Path("/mnt/c/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6/final-source-ci-manual-failure-20261008-01/candidate-v2")
test_file = candidate / "test_manual_recording_review_fixes.py"
base_feature = yaml.safe_load((root / "manual/features/reference-locks.yaml").read_text())
base_recording = yaml.safe_load((root / "manual/recordings.yaml").read_text())

def changed_data(mutator):
    feature = copy.deepcopy(base_feature)
    recording = copy.deepcopy(base_recording)
    mutator(feature, recording)
    return feature, recording

def run_case(name, feature, recording, expect_pass):
    fixture = candidate / "mutation-fixtures" / name / "manual"
    (fixture / "features").mkdir(parents=True, exist_ok=True)
    (fixture / "features/reference-locks.yaml").write_text(yaml.safe_dump(feature, sort_keys=False, allow_unicode=True))
    (fixture / "recordings.yaml").write_text(yaml.safe_dump(recording, sort_keys=False, allow_unicode=True))
    env = dict(os.environ)
    env.update({
        "MOSAIC_REPO_ROOT": str(fixture.parent),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": "tools:tests/behaviour",
    })
    proc = subprocess.run([
        sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(test_file),
        "-k", "decay_recipe_replays_recorded_gestures_and_separates_endpoint_practice",
    ], cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    passed = proc.returncode == 0
    result = {
        "case": name,
        "expected": "pass" if expect_pass else "fail",
        "actual": "pass" if passed else "fail",
        "exit_code": proc.returncode,
        "assertion_failure": "AssertionError" in proc.stdout,
        "summary": next((line for line in proc.stdout.splitlines() if " passed" in line or " failed" in line), "no pytest summary"),
    }
    if passed != expect_pass or (not expect_pass and not result["assertion_failure"]):
        result["output"] = proc.stdout[-6000:]
    return result

recipe_mutations = {
    "wrong-gesture-size": lambda f, r: f["features"][0]["recipes"][4].__setitem__("text", f["features"][0]["recipes"][4]["text"].replace("clockwise by 200 detents", "clockwise by 20 detents", 1)),
    "wrong-step-group": lambda f, r: f["features"][0]["recipes"][4].__setitem__("text", f["features"][0]["recipes"][4]["text"].replace("200-detent turn on step 9", "200-detent turn on step 8", 1)),
    "wrong-endpoint": lambda f, r: f["features"][0]["recipes"][4].__setitem__("text", f["features"][0]["recipes"][4]["text"].replace("0.1 s minimum", "0.2 s minimum", 1)),
    "copy-after-edit": lambda f, r: f["features"][0]["recipes"][4].__setitem__("text", f["features"][0]["recipes"][4]["text"].replace("Copy slot 1 to slot 2 and keep slot 2 at 32 steps. Tap slot 2 before editing its locks.", "Tap slot 2 before editing its locks. Copy slot 1 to slot 2 and keep slot 2 at 32 steps.", 1)),
    "wrong-restore-slot": lambda f, r: f["features"][0]["recipes"][4].__setitem__("text", f["features"][0]["recipes"][4]["text"].replace("Restore: Select slot 1 to restore", "Restore: Select slot 2 to restore", 1)),
    "false-captured-display-provenance": lambda f, r: r["recordings"][next(i for i, x in enumerate(r["recordings"]) if x["id"] == "param-lock-comparison")]["limits"].__setitem__(0, next(x for x in r["recordings"] if x["id"] == "param-lock-comparison")["limits"][0].replace("does not record the displayed Decay values", "records the displayed Decay values", 1)),
}

results = []
for name, mutate in recipe_mutations.items():
    feature, recording = changed_data(mutate)
    results.append(run_case(name, feature, recording, False))

def prose_paraphrase(feature, recording):
    text = feature["features"][0]["recipes"][4]["text"]
    text = text.replace("Comparison purpose:", "Why compare:")
    text = text.replace("Relative-turn comparison —", "Relative gesture exercise:")
    text = text.replace("Separate endpoint practice —", "A separate endpoint exercise:")
    text = text.replace("\n\n", "\n\n\n")
    feature["features"][0]["recipes"][4]["text"] = text

feature, recording = changed_data(prose_paraphrase)
results.append(run_case("benign-prose-paraphrase", feature, recording, True))

receipt = {
    "kind": "locks-decay-recipe-semantic-mutation-qualification-v1",
    "baseline_root": str(root),
    "candidate_test": str(test_file),
    "cases": results,
    "all_expectations_met": all(
        row["actual"] == row["expected"] and (row["expected"] == "pass" or row["assertion_failure"])
        for row in results
    ),
}
(candidate / "mutation-qualification.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
if not receipt["all_expectations_met"]:
    raise SystemExit(1)

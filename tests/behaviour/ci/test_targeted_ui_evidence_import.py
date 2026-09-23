"""Harness characterisation outside README: immutable targeted CI evidence import."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("targeted_ui_evidence_import.py")
spec = importlib.util.spec_from_file_location("targeted_ui_evidence_import", SCRIPT)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)

CASE = "M-PROJECT-LIVE-001"
BEFORE = "a" * 40
AFTER = "b" * 40


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def fixture(root):
    """A complete two-lane gate whose native log is intentionally not uploaded."""
    report = dict(schema_version=1, passed=True, complete_regression_run=False,
                  before_sha=BEFORE, after_sha=AFTER, selected_cases=[CASE],
                  lanes=list(importer.LANES),
                  source_delta={"production_tree_unchanged": True}, cases=[])
    row = dict(case=CASE, lanes=[])
    report["cases"].append(row)
    for clock_mode in importer.LANES:
        lane = dict(lane=clock_mode, gate_errors=[], runs={})
        row["lanes"].append(lane)
        for side, sha in (("before", BEFORE), ("after", AFTER)):
            run = root / CASE / clock_mode / side / "session-1"
            pairs = ["recipe.json", "results.json", "restarted/recipe.json",
                     "restarted/results.json"]
            artifacts = []
            for name in pairs:
                value = [{"type": "grid", "x": 1}] if name.endswith("recipe.json") \
                    else [{"kind": "midi", "value": 1}]
                write_json(run / name, value)
                raw = (run / name).read_bytes()
                artifacts.append(dict(path=name, size=len(raw), sha256=importer.digest(raw)))
            # CI verifies this file at runtime, but the upload intentionally omits it.
            artifacts.append(dict(path="native/matron.log", size=1, sha256="0" * 64))
            manifest = dict(schema_version=1, mosaic_revision=sha, case=CASE,
                            clock_mode=clock_mode, profile="base-midi", passed=True,
                            failure=None, campaign_complete=False,
                            diagnostic_only=(clock_mode == "controlled-experimental"),
                            artifacts=artifacts)
            write_json(run / "manifest.json", manifest)
            relative = (run / "manifest.json").relative_to(root).as_posix()
            lane["runs"][side] = dict(returncode=0, manifest=relative,
                                       manifest_sha256=importer.digest(
                                           (run / "manifest.json").read_bytes()))
    write_json(root / "targeted-ui-migration.json", report)
    write_json(root / "targeted-ui-repeatability.json",
               dict(schema_version=1, passed=True, complete_regression_run=False,
                    after_sha=AFTER, selected_cases=[CASE],
                    selected_modules={"tests/behaviour/project_dialog_lifecycle.py": CASE},
                    repeats=[dict(module="tests/behaviour/project_dialog_lifecycle.py",
                                  case=CASE, returncode=0, passed=True)]))
    return report


class TargetedEvidenceImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.download = self.root / "download"
        self.output = self.root / "baselines"
        fixture(self.download)

    def run_import(self, dry_run=False):
        return importer.import_targeted(self.download, self.output, "35802998566",
                                        BEFORE, AFTER, [CASE], dry_run=dry_run)

    def test_imports_both_lanes_sides_and_nested_pairs_with_provenance(self):
        dry = self.run_import(dry_run=True)
        self.assertEqual(len(dry["imported"]), 4)
        self.assertFalse(self.output.exists())
        self.run_import()
        for lane in ("real-time", "controlled"):
            for side, sha in (("before", BEFORE), ("after", AFTER)):
                target = self.output / CASE / lane / side
                self.assertEqual((target / "restarted/results.json").read_bytes(),
                                 (self.download / CASE /
                                  ("real-time" if lane == "real-time"
                                   else "controlled-experimental") / side /
                                  "session-1/restarted/results.json").read_bytes())
                provenance = json.loads((target / "provenance.json").read_text())
                self.assertEqual(provenance["source_revision"], sha)
                self.assertFalse(provenance["complete_regression_run"])
                self.assertIn("source-manifest.json", [p.name for p in target.iterdir()])

    def test_refuses_existing_destination_without_replacement(self):
        target = self.output / CASE / "controlled" / "before"
        target.mkdir(parents=True)
        (target / "sentinel").write_text("do not replace")
        with self.assertRaisesRegex(ValueError, "overwritten"):
            self.run_import()
        self.assertEqual((target / "sentinel").read_text(), "do not replace")
        self.assertFalse((self.output / CASE / "real-time").exists())

    def test_refuses_missing_or_modified_nested_evidence_before_writes(self):
        nested = (self.download / CASE / "controlled-experimental" /
                  "after/session-1/restarted/results.json")
        nested.unlink()
        with self.assertRaisesRegex(ValueError, "set differs"):
            self.run_import()
        self.assertFalse(self.output.exists())
        write_json(nested, [{"kind": "changed"}])
        with self.assertRaisesRegex(ValueError, "digest differs"):
            self.run_import()
        self.assertFalse(self.output.exists())

    def test_refuses_failed_or_mismatched_reports(self):
        path = self.download / "targeted-ui-migration.json"
        report = json.loads(path.read_text())
        for change in (dict(passed=False), dict(after_sha="c" * 40),
                       dict(complete_regression_run=True)):
            with self.subTest(change=change):
                write_json(path, {**report, **change})
                with self.assertRaises(ValueError):
                    self.run_import()
        write_json(path, report)
        repeat = self.download / "targeted-ui-repeatability.json"
        data = json.loads(repeat.read_text())
        write_json(repeat, {**data, "passed": False})
        with self.assertRaisesRegex(ValueError, "repeatability"):
            self.run_import()

    def test_refuses_manifest_identity_and_report_digest_mismatch(self):
        manifest = (self.download / CASE / "real-time" /
                    "before/session-1/manifest.json")
        item = json.loads(manifest.read_text())
        write_json(manifest, {**item, "mosaic_revision": "c" * 40})
        with self.assertRaisesRegex(ValueError, "manifest digest differs"):
            self.run_import()
        self.assertFalse(self.output.exists())

    def test_refuses_duplicate_json_keys_and_traversal(self):
        report = self.download / "targeted-ui-migration.json"
        report.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.run_import()
        fixture(self.download)
        data = json.loads(report.read_text())
        data["cases"][0]["lanes"][0]["runs"]["before"]["manifest"] = "../outside/manifest.json"
        write_json(report, data)
        with self.assertRaisesRegex(ValueError, "unsafe path"):
            self.run_import()

    def test_refuses_symlinked_download_when_platform_permits(self):
        evidence = self.download / CASE / "real-time" / "before/session-1/recipe.json"
        link_target = self.root / "external.json"
        link_target.write_bytes(evidence.read_bytes())
        evidence.unlink()
        try:
            evidence.symlink_to(link_target)
        except OSError as error:
            self.skipTest("host cannot create symlinks: " + str(error))
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.run_import()


if __name__ == "__main__":
    unittest.main()

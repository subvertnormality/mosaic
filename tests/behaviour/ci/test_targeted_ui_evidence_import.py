"""Harness characterisation outside README: immutable targeted CI evidence import."""

import importlib.util
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("targeted_ui_evidence_import.py")
spec = importlib.util.spec_from_file_location("targeted_ui_evidence_import", SCRIPT)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)

CASE = "M-PROJECT-LIVE-001"
BEFORE = "a" * 40
AFTER = "b" * 40
TOOLING = "c" * 40
TOOLING_PATHS = (
    "tests/behaviour/ui_migration_gate.py",
    "tests/behaviour/ci/targeted-ui-migration.py",
    "tests/behaviour/ci/compare_ptn_graph.lua",
)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def fixture(root, profile="base-midi", controlled_only=False, qualified_runtime=False,
            real_time_only=False):
    """A complete selected-lane gate whose native log is intentionally not uploaded."""
    clock_modes = (["controlled-experimental"] if controlled_only
                   else ["real-time"] if real_time_only else list(importer.LANES))
    report = dict(schema_version=1, passed=True, complete_regression_run=False,
                  before_sha=BEFORE, after_sha=AFTER, selected_cases=[CASE],
                  lanes=clock_modes, profile=profile,
                  source_delta={"production_tree_unchanged": True}, cases=[])
    if qualified_runtime:
        report["runtime"] = dict(importer.QUALIFIED_RUNTIME)
    row = dict(case=CASE, lanes=[])
    report["cases"].append(row)
    for clock_mode in clock_modes:
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
                            clock_mode=clock_mode, profile=profile, passed=True,
                            failure=None, campaign_complete=False,
                            diagnostic_only=(qualified_runtime
                                             or clock_mode == "controlled-experimental"),
                            artifacts=artifacts)
            write_json(run / "manifest.json", manifest)
            relative = (run / "manifest.json").relative_to(root).as_posix()
            lane["runs"][side] = dict(returncode=0, manifest=relative,
                                       manifest_sha256=importer.digest(
                                           (run / "manifest.json").read_bytes()))
    write_json(root / "targeted-ui-migration.json", report)
    write_json(root / "targeted-ui-repeatability.json",
               dict(schema_version=1, passed=True, complete_regression_run=False,
                    after_sha=AFTER, profile=profile, selected_cases=[CASE],
                    selected_modules={"tests/behaviour/project_dialog_lifecycle.py": CASE},
                    repeats=[dict(module="tests/behaviour/project_dialog_lifecycle.py",
                                  case=CASE, returncode=0, passed=True)]))
    return report


def historical_fixture(root):
    report = fixture(root)
    report["source_delta"]["historical_tooling_paths"] = sorted(TOOLING_PATHS)
    report["tooling"] = dict(
        sha=TOOLING, sha256={path: "d" * 64 for path in TOOLING_PATHS})
    write_json(root / "targeted-ui-migration.json", report)
    repeat_path = root / "targeted-ui-repeatability.json"
    repeat = json.loads(repeat_path.read_text())
    repeat["tooling_sha"] = TOOLING
    write_json(repeat_path, repeat)
    return report


class TargetedEvidenceImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.download = self.root / "download"
        self.output = self.root / "baselines"
        fixture(self.download)

    def run_import(self, dry_run=False, profile="base-midi"):
        return importer.import_targeted(self.download, self.output, "35802998566",
                                        BEFORE, AFTER, [CASE], dry_run=dry_run,
                                        profile=profile)

    def add_persisted_project_evidence(self):
        report_path = self.download / "targeted-ui-migration.json"
        report = json.loads(report_path.read_text())
        for lane in report["cases"][0]["lanes"]:
            clock_mode = lane["lane"]
            for side in ("before", "after"):
                run = self.download / CASE / clock_mode / side / "session-1"
                project = run / "generated-project/autosave.ptn"
                project.parent.mkdir(parents=True, exist_ok=True)
                project.write_bytes(("project-" + side).encode())
                manifest_path = run / "manifest.json"
                manifest = json.loads(manifest_path.read_text())
                manifest["artifacts"].append(dict(
                    path="generated-project/autosave.ptn",
                    size=project.stat().st_size,
                    sha256=importer.digest(project.read_bytes())))
                write_json(manifest_path, manifest)
                lane["runs"][side]["manifest_sha256"] = importer.digest(
                    manifest_path.read_bytes())
        write_json(report_path, report)

    def test_imports_manifest_verified_persisted_project_for_strict_gate(self):
        self.add_persisted_project_evidence()
        with patch.object(importer, "PERSISTED_PROJECTS",
                          {CASE: ("generated-project/autosave.ptn",)}, create=True):
            self.run_import()
        target = (self.output / CASE / "controlled" / "before" /
                  "generated-project/autosave.ptn")
        self.assertEqual(target.read_bytes(), b"project-before")
        provenance = json.loads((target.parents[1] / "provenance.json").read_text())
        self.assertEqual(provenance["evidence_sha256"]["generated-project/autosave.ptn"],
                         importer.digest(target.read_bytes()))

    def test_refuses_missing_required_project_before_any_write(self):
        self.add_persisted_project_evidence()
        (self.download / CASE / "real-time" / "before" / "session-1" /
         "generated-project/autosave.ptn").unlink()
        with patch.object(importer, "PERSISTED_PROJECTS",
                          {CASE: ("generated-project/autosave.ptn",)}, create=True):
            with self.assertRaisesRegex(ValueError, "persisted project"):
                self.run_import(dry_run=True)
        self.assertFalse(self.output.exists())

    def test_selective_import_validates_existing_witness_without_overwriting_it(self):
        witness = "M-WITNESS-001"
        shutil.copytree(self.download / CASE, self.download / witness)
        report_path = self.download / "targeted-ui-migration.json"
        report = json.loads(report_path.read_text())
        row = copy.deepcopy(report["cases"][0])
        row["case"] = witness
        for lane in row["lanes"]:
            for side in ("before", "after"):
                run = lane["runs"][side]
                original = Path(run["manifest"])
                relative = Path(witness) / original.relative_to(CASE)
                path = self.download / relative
                manifest = json.loads(path.read_text())
                manifest["case"] = witness
                write_json(path, manifest)
                run["manifest"] = relative.as_posix()
                run["manifest_sha256"] = importer.digest(path.read_bytes())
        report["selected_cases"] = [CASE, witness]
        report["cases"].append(row)
        write_json(report_path, report)
        repeat_path = self.download / "targeted-ui-repeatability.json"
        repeat = json.loads(repeat_path.read_text())
        repeat["selected_cases"] = [CASE, witness]
        write_json(repeat_path, repeat)

        existing = self.output / witness / "controlled" / "before"
        existing.mkdir(parents=True)
        (existing / "sentinel").write_text("untouched")
        imported = importer.import_targeted(
            self.download, self.output, "35802998566", BEFORE, AFTER,
            [CASE, witness], import_cases=[CASE])
        self.assertEqual(len(imported["imported"]), 4)
        self.assertEqual((existing / "sentinel").read_text(), "untouched")
        self.assertFalse((self.output / witness / "real-time").exists())
        self.assertTrue((self.output / CASE / "controlled/after/provenance.json").is_file())

        (self.download / witness / "controlled-experimental/after/session-1/results.json").write_text("tampered")
        with self.assertRaisesRegex(ValueError, "digest differs"):
            importer.import_targeted(self.download, self.root / "another-output",
                                     "35802998566", BEFORE, AFTER, [CASE, witness],
                                     import_cases=[CASE], dry_run=True)
        with self.assertRaisesRegex(ValueError, "import cases"):
            importer.import_targeted(self.download, self.root / "another-output",
                                     "35802998566", BEFORE, AFTER, [CASE, witness],
                                     import_cases=["M-UNKNOWN-001"], dry_run=True)

    def test_imports_requested_non_default_profile(self):
        fixture(self.download, profile="midi-modulation")
        dry = self.run_import(dry_run=True, profile="midi-modulation")
        self.assertEqual(len(dry["imported"]), 4)
        self.assertFalse(self.output.exists())
        self.run_import(profile="midi-modulation")
        provenance = json.loads((self.output / CASE / "controlled" /
                                 "before/provenance.json").read_text())
        self.assertEqual(provenance["profile"], "midi-modulation")

    def test_imports_controlled_only_case_lane_selection(self):
        fixture(self.download, controlled_only=True)
        dry = self.run_import(dry_run=True)
        self.assertEqual(len(dry["imported"]), 2)
        self.assertTrue(all("/controlled/" in path.replace("\\", "/")
                            for path in dry["imported"]))

    def test_imports_real_time_only_case_lane_selection(self):
        shutil.rmtree(self.download)
        fixture(self.download, real_time_only=True)
        dry = self.run_import(dry_run=True)
        self.assertEqual(len(dry["imported"]), 2)
        self.assertTrue(all("/real-time/" in path.replace("\\", "/")
                            for path in dry["imported"]))

    def test_historical_tooling_identity_is_preserved_in_provenance(self):
        historical_fixture(self.download)
        self.run_import()
        provenance = json.loads((self.output / CASE / "controlled" /
                                 "before/provenance.json").read_text())
        self.assertEqual(provenance["tooling_revision"], TOOLING)
        self.assertEqual(provenance["tooling_sha256"],
                         {path: "d" * 64 for path in TOOLING_PATHS})

    def test_historical_tooling_identity_must_match_repeat_report(self):
        historical_fixture(self.download)
        repeat_path = self.download / "targeted-ui-repeatability.json"
        repeat = json.loads(repeat_path.read_text())
        repeat["tooling_sha"] = "e" * 40
        write_json(repeat_path, repeat)
        with self.assertRaisesRegex(ValueError, "tooling"):
            self.run_import(dry_run=True)
        self.assertFalse(self.output.exists())

    def test_historical_report_without_pinned_hashes_is_rejected(self):
        report = historical_fixture(self.download)
        del report["tooling"]["sha256"]
        write_json(self.download / "targeted-ui-migration.json", report)
        with self.assertRaisesRegex(ValueError, "tooling"):
            self.run_import(dry_run=True)
        self.assertFalse(self.output.exists())

    def test_refuses_report_or_manifest_profile_mismatch(self):
        fixture(self.download, profile="midi-modulation")
        with self.assertRaisesRegex(ValueError, "profile"):
            self.run_import(dry_run=True)

        fixture(self.download, profile="midi-modulation")
        report_path = self.download / "targeted-ui-migration.json"
        report = json.loads(report_path.read_text())
        manifest_path = (self.download / CASE / "real-time" /
                         "before/session-1/manifest.json")
        manifest = json.loads(manifest_path.read_text())
        write_json(manifest_path, {**manifest, "profile": "base-midi"})
        run = report["cases"][0]["lanes"][0]["runs"]["before"]
        run["manifest_sha256"] = importer.digest(manifest_path.read_bytes())
        write_json(report_path, report)
        with self.assertRaisesRegex(ValueError, "profile"):
            self.run_import(dry_run=True, profile="midi-modulation")
        self.assertFalse(self.output.exists())

    def test_refuses_repeatability_profile_mismatch_and_unknown_profile(self):
        repeat_path = self.download / "targeted-ui-repeatability.json"
        repeat = json.loads(repeat_path.read_text())
        write_json(repeat_path, {**repeat, "profile": "midi-modulation"})
        with self.assertRaisesRegex(ValueError, "repeatability"):
            self.run_import(dry_run=True)
        fixture(self.download)
        with self.assertRaisesRegex(ValueError, "invalid profile"):
            self.run_import(dry_run=True, profile="crow-jf")

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

    def set_real_time_diagnostic_marker(self, value):
        report_path = self.download / "targeted-ui-migration.json"
        report = json.loads(report_path.read_text())
        for side in ("before", "after"):
            manifest_path = (self.download / CASE / "real-time" / side /
                             "session-1/manifest.json")
            write_json(manifest_path, {**json.loads(manifest_path.read_text()),
                                       "diagnostic_only": value})
            report["cases"][0]["lanes"][0]["runs"][side]["manifest_sha256"] = \
                importer.digest(manifest_path.read_bytes())
        write_json(report_path, report)

    def test_qualified_runtime_report_imports_qualified_real_time_runs(self):
        shutil.rmtree(self.download)
        fixture(self.download, qualified_runtime=True)
        self.run_import()
        self.assertTrue((self.output / CASE / "real-time/after/results.json").is_file())

    def test_qualified_runtime_report_refuses_default_runtime_real_time_run(self):
        shutil.rmtree(self.download)
        fixture(self.download, qualified_runtime=True)
        self.set_real_time_diagnostic_marker(False)
        with self.assertRaisesRegex(ValueError, "identity differs"):
            self.run_import()
        self.assertFalse(self.output.exists())

    def test_legacy_report_refuses_undeclared_qualified_real_time_run(self):
        self.set_real_time_diagnostic_marker(True)
        with self.assertRaisesRegex(ValueError, "identity differs"):
            self.run_import()
        self.assertFalse(self.output.exists())

    def test_refuses_unknown_runtime_identity(self):
        path = self.download / "targeted-ui-migration.json"
        report = json.loads(path.read_text())
        for runtime in ({"real-time": "default", "controlled-experimental": "qualified"},
                        "qualified", None):
            with self.subTest(runtime=runtime):
                write_json(path, {**report, "runtime": runtime})
                with self.assertRaisesRegex(ValueError, "runtime identity"):
                    self.run_import()
        self.assertFalse(self.output.exists())

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


    def test_preserves_manifest_listed_fractional_clock_sidecar_verbatim(self):
        sidecar_bytes = b'{"clock_mode":"controlled-experimental","verified_inputs":[]}\n'
        for lane in ("real-time", "controlled-experimental"):
            for side in ("before", "after"):
                run = self.download / CASE / lane / side / "session-1"
                path = run / "fractional-clock-input-evidence.json"
                path.write_bytes(sidecar_bytes)
                manifest_path = run / "manifest.json"
                manifest = json.loads(manifest_path.read_text())
                manifest["artifacts"].append(dict(
                    path=path.name, size=len(sidecar_bytes),
                    sha256=importer.digest(sidecar_bytes)))
                write_json(manifest_path, manifest)
                report_path = self.download / "targeted-ui-migration.json"
                report = json.loads(report_path.read_text())
                lane_row = next(row for row in report["cases"][0]["lanes"]
                                if row["lane"] == lane)
                lane_row["runs"][side]["manifest_sha256"] = importer.digest(
                    manifest_path.read_bytes())
                write_json(report_path, report)

        self.run_import()
        target = (self.output / CASE / "controlled" / "before" /
                  "fractional-clock-input-evidence.json")
        self.assertEqual(target.read_bytes(), sidecar_bytes)
        provenance = json.loads((target.parent / "provenance.json").read_text())
        self.assertEqual(provenance["evidence_sha256"][target.name],
                         importer.digest(sidecar_bytes))

    def test_refuses_manifest_listed_sidecar_when_upload_omits_it(self):
        run = self.download / CASE / "real-time" / "before/session-1"
        manifest_path = run / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        missing = b"{}"
        manifest["artifacts"].append(dict(
            path="fractional-clock-input-evidence.json", size=len(missing),
            sha256=importer.digest(missing)))
        write_json(manifest_path, manifest)
        report_path = self.download / "targeted-ui-migration.json"
        report = json.loads(report_path.read_text())
        report["cases"][0]["lanes"][0]["runs"]["before"]["manifest_sha256"] = \
            importer.digest(manifest_path.read_bytes())
        write_json(report_path, report)
        with self.assertRaisesRegex(ValueError, "sidecar set differs"):
            self.run_import(dry_run=True)
        self.assertFalse(self.output.exists())

    def test_refuses_manifest_listed_sidecar_with_wrong_digest(self):
        run = self.download / CASE / "real-time" / "before/session-1"
        path = run / "fractional-clock-input-evidence.json"
        sidecar_bytes = b'{"verified_inputs":[]}\n'
        path.write_bytes(sidecar_bytes)
        manifest_path = run / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["artifacts"].append(dict(
            path=path.name, size=len(sidecar_bytes), sha256="0" * 64))
        write_json(manifest_path, manifest)
        report_path = self.download / "targeted-ui-migration.json"
        report = json.loads(report_path.read_text())
        report["cases"][0]["lanes"][0]["runs"]["before"]["manifest_sha256"] = \
            importer.digest(manifest_path.read_bytes())
        write_json(report_path, report)
        with self.assertRaisesRegex(ValueError, "evidence size/digest differs"):
            self.run_import(dry_run=True)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()

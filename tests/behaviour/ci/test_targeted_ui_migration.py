"""Harness characterisation outside README: partial targeted CI gate contracts."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).with_name("targeted-ui-migration.py")
spec = importlib.util.spec_from_file_location("targeted_ui_migration", SCRIPT)
targeted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(targeted)


class TargetedMigrationTests(unittest.TestCase):
    def test_explicit_case_ids_allow_registered_dotted_ids(self):
        self.assertEqual(targeted.cases_from_input("M-GRID-001, M-PERSIST-FIXTURE-1.2.12"),
                         ["M-GRID-001", "M-PERSIST-FIXTURE-1.2.12"])
        for invalid in ("", "M-GRID-001,", "M-GRID-001,M-GRID-001", "../M-GRID-001",
                        "M-.*", "M-GRID-001|M-MASK-001"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                targeted.cases_from_input(invalid)

    def test_lambda_wrapped_dotted_case_resolves_owner_module(self):
        self.assertEqual(targeted.selected_case_modules(
            ROOT, ["M-PERSIST-FIXTURE-1.2.12"]),
            {"tests/behaviour/persisted_fixture.py"})

    def test_manifest_binds_success_source_lane_and_all_nested_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            (run / "restarted").mkdir()
            for name in ("recipe.json", "results.json", "restarted/recipe.json",
                         "restarted/results.json"):
                (run / name).write_text("[]")
            artifacts = [dict(path=name, sha256=targeted.sha256(run / name),
                              size=(run / name).stat().st_size)
                         for name in ("recipe.json", "results.json",
                                      "restarted/recipe.json", "restarted/results.json")]
            item = dict(case="M-GRID-001", clock_mode="controlled-experimental",
                        mosaic_revision="a" * 40, profile="base-midi", passed=True,
                        campaign_complete=False, diagnostic_only=True, failure=None,
                        artifacts=artifacts)
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps(item))
            targeted.verified_manifest(manifest, "M-GRID-001",
                                       "controlled-experimental", "a" * 40)
            for changed in (dict(passed=False), dict(mosaic_revision="b" * 40),
                            dict(diagnostic_only=False), dict(campaign_complete=True)):
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    manifest.write_text(json.dumps({**item, **changed}))
                    targeted.verified_manifest(manifest, "M-GRID-001",
                                               "controlled-experimental", "a" * 40)
            manifest.write_text(json.dumps(item))
            (run / "restarted/results.json").write_text("[1]")
            with self.assertRaisesRegex(ValueError, "digest differs"):
                targeted.verified_manifest(manifest, "M-GRID-001",
                                           "controlled-experimental", "a" * 40)

    def test_manifest_rejects_symlinked_file_and_ancestor_before_hashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "run"
            run.mkdir()
            (run / "recipe.json").write_text("[]")
            (run / "results.json").write_text("[]")
            item = dict(case="M-GRID-001", clock_mode="real-time",
                        mosaic_revision="a" * 40, profile="base-midi", passed=True,
                        campaign_complete=False, diagnostic_only=False, failure=None,
                        artifacts=[dict(path=name, sha256=targeted.sha256(run / name), size=2)
                                   for name in ("recipe.json", "results.json")])
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps(item))
            original = Path.is_symlink
            def simulated_symlink(path):
                return path == run / "recipe.json" or original(path)
            with patch.object(Path, "is_symlink", simulated_symlink):
                with self.assertRaisesRegex(ValueError, "symlinked evidence path"):
                    targeted.verified_manifest(manifest, "M-GRID-001", "real-time", "a" * 40)
            # A symlinked containing directory is equally unsafe, even when
            # the recipe path itself is a regular file in its target.
            with patch.object(Path, "is_symlink", lambda path: path == run or original(path)):
                with self.assertRaisesRegex(ValueError, "symlinked evidence path"):
                    targeted.verified_manifest(manifest, "M-GRID-001", "real-time", "a" * 40)

    def test_real_symlinked_recipe_is_not_accepted_when_platform_permits_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "run"
            run.mkdir()
            target = root / "outside.json"
            target.write_text("[]")
            try:
                (run / "recipe.json").symlink_to(target)
            except OSError as error:
                self.skipTest("host cannot create symlinks: " + str(error))
            (run / "results.json").write_text("[]")
            item = dict(case="M-GRID-001", clock_mode="real-time",
                        mosaic_revision="a" * 40, profile="base-midi", passed=True,
                        campaign_complete=False, diagnostic_only=False, failure=None,
                        artifacts=[dict(path=name, sha256=targeted.sha256(run / name), size=2)
                                   for name in ("recipe.json", "results.json")])
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps(item))
            with self.assertRaisesRegex(ValueError, "symlinked evidence path"):
                targeted.verified_manifest(manifest, "M-GRID-001", "real-time", "a" * 40)

    def test_source_delta_rejects_production_and_shared_harness_changes(self):
        production = {"mosaic.lua": ("100644", "blob", "a" * 40),
                      "lib/nb": ("160000", "commit", "b" * 40)}
        tests = {"tests/behaviour/driver.py": ("100644", "blob", "c" * 40),
                 "tests/behaviour/scale_lock_precedence.py": ("100644", "blob", "d" * 40),
                 "tests/behaviour/ui_migration_gate.py": ("100644", "blob", "f" * 40),
                 "tests/behaviour/ci/targeted-ui-migration.py": ("100644", "blob", "1" * 40)}
        case_file = "tests/behaviour/scale_lock_precedence.py"
        with patch.object(targeted, "selected_case_modules", return_value={case_file}):
            changed_prod = {**production, "lib/nb": ("160000", "commit", "e" * 40)}
            with patch.object(targeted, "tree_entries",
                              side_effect=[production, changed_prod, tests, tests]):
                with self.assertRaisesRegex(ValueError, "production/manual source changed"):
                    targeted.check_source_delta(Path("before"), Path("after"), ["M-SCALE-LOCK-003"])
            changed_harness = {**tests, "tests/behaviour/driver.py":
                               ("100644", "blob", "e" * 40)}
            with patch.object(targeted, "tree_entries",
                              side_effect=[production, production, tests, changed_harness]):
                with self.assertRaisesRegex(ValueError, "unrelated behaviour harness/fixture"):
                    targeted.check_source_delta(Path("before"), Path("after"), ["M-SCALE-LOCK-003"])
            for gate_path in targeted.PINNED_GATE_PATHS:
                changed_gate = {**tests, gate_path: ("100644", "blob", "e" * 40)}
                with self.subTest(gate_path=gate_path), patch.object(
                        targeted, "tree_entries",
                        side_effect=[production, production, tests, changed_gate]):
                    with self.assertRaisesRegex(ValueError, "targeted gate/runner differs"):
                        targeted.check_source_delta(
                            Path("before"), Path("after"), ["M-SCALE-LOCK-003"])
            changed_case = {**tests, case_file: ("100644", "blob", "e" * 40)}
            with patch.object(targeted, "tree_entries",
                              side_effect=[production, production, tests, changed_case]):
                result = targeted.check_source_delta(
                    Path("before"), Path("after"), ["M-SCALE-LOCK-003"])
                self.assertEqual(result["changed_behaviour_paths"], [case_file])
            symlink_case = {**tests, case_file: ("120000", "blob", "e" * 40)}
            with patch.object(targeted, "tree_entries",
                              side_effect=[production, production, tests, symlink_case]):
                with self.assertRaisesRegex(ValueError, "not a regular file"):
                    targeted.check_source_delta(
                        Path("before"), Path("after"), ["M-SCALE-LOCK-003"])

    def test_strict_gate_sees_nested_recipe_and_controlled_oracle_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for side in ("before", "after"):
                (root / side / "restarted").mkdir(parents=True)
                for session in ("", "restarted/"):
                    (root / side / session / "recipe.json").write_text(
                        '[{"type":"advance","nanoseconds":100}]')
                    (root / side / session / "results.json").write_text(
                        '[{"kind":"midi","pitch":60}]')
            self.assertEqual(targeted.check_session_roots(root / "before", root / "after",
                                                          "controlled"), [])
            (root / "after/restarted/results.json").write_text(
                '[{"kind":"midi","pitch":61}]')
            self.assertIn("controlled results differ", " ".join(
                targeted.check_session_roots(root / "before", root / "after", "controlled")))
            (root / "after/restarted/recipe.json").write_text(
                '[{"type":"advance","nanoseconds":101}]')
            self.assertIn("normalized recipes differ", " ".join(
                targeted.check_session_roots(root / "before", root / "after", "real-time")))

    def test_dispatch_never_feeds_partial_report_to_full_aggregation(self):
        workflow = (ROOT / ".github/workflows/behaviour.yml").read_text()
        self.assertIn("ui_migration_targeted:", workflow)
        self.assertIn("if: ${{ !inputs.ui_migration_targeted }}", workflow)
        self.assertIn("if: ${{ always() && !inputs.ui_migration_targeted }}", workflow)
        self.assertIn("name: targeted-ui-migration-${{ github.run_id }}", workflow)
        self.assertIn("--before-sha \"$BEFORE_SHA\"", workflow)
        self.assertIn("--after-sha \"$AFTER_SHA\"", workflow)
        self.assertIn("--case-ids \"$CASE_IDS\"", workflow)


if __name__ == "__main__":
    unittest.main()

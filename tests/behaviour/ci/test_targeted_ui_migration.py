"""Harness characterisation outside README: partial targeted CI gate contracts."""

import ast
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

    def test_real_selected_contract_shims_resolve_exact_owners(self):
        for case, module in (("M-SYNC-009", "master_clock"),
                             ("M-SYNC-LEAD-001", "lock_lead_time")):
            with self.subTest(case=case):
                owner = "tests/behaviour/" + module + ".py"
                contract_owner = "tests/behaviour/contract/" + module + ".py"
                tree = ast.parse((ROOT / owner).read_text())
                body = tree.body
                if body and isinstance(body[0], ast.Expr) \
                        and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    body = body[1:]
                definitions = [node for node in body if isinstance(node, ast.FunctionDef)
                               and node.name == module]
                if definitions:
                    expected = {owner}  # pre-extraction baseline
                else:
                    self.assertEqual(len(body), 1)
                    self.assertIsInstance(body[0], ast.ImportFrom)
                    self.assertEqual(body[0].module, "contract." + module)
                    self.assertIn(module, [alias.asname or alias.name
                                           for alias in body[0].names])
                    self.assertTrue((ROOT / contract_owner).is_file())
                    expected = {owner, contract_owner}
                self.assertEqual(targeted.selected_case_modules(ROOT, [case]), expected)

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

    def test_manifest_binds_requested_non_base_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            for name in ("recipe.json", "results.json"):
                (run / name).write_text("[]")
            item = dict(case="M-MOD-001", clock_mode="controlled-experimental",
                        mosaic_revision="a" * 40, profile="midi-modulation", passed=True,
                        campaign_complete=False, diagnostic_only=True, failure=None,
                        artifacts=[dict(path=name, sha256=targeted.sha256(run / name), size=2)
                                   for name in ("recipe.json", "results.json")])
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps(item))
            targeted.verified_manifest(manifest, "M-MOD-001",
                                       "controlled-experimental", "a" * 40,
                                       profile="midi-modulation")
            with self.assertRaisesRegex(ValueError, "profile differs"):
                targeted.verified_manifest(manifest, "M-MOD-001",
                                           "controlled-experimental", "a" * 40)

    def test_run_command_passes_profile_and_fixture_setup_to_both_lanes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            (source / "tests/behaviour").mkdir(parents=True)
            (source / "tests/behaviour/run.py").write_text("")
            install = root / "installation.json"
            install.write_text("{}")
            fixture = root / "fixtures"
            fixture.mkdir()
            for lane in ("real-time", "controlled-experimental"):
                output = root / lane
                expected = output / "run-1/manifest.json"
                def launch(command, cwd, stdout, stderr, check, expected=expected):
                    expected.parent.mkdir(parents=True)
                    expected.write_text("{}")
                    self.assertEqual(command[command.index("--profile") + 1],
                                     "midi-modulation")
                    self.assertEqual(command[command.index("--mod-code-root") + 1],
                                     str(fixture))
                    self.assertIn("--mod-patches", command)
                    if lane == "controlled-experimental":
                        self.assertIn("--experimental-install", command)
                    return type("Completed", (), {"returncode": 0})()
                with patch.object(targeted.subprocess, "run", side_effect=launch):
                    status, manifest = targeted.run_one(
                        source, "M-MOD-001", lane, output, install,
                        "midi-modulation", fixture, True)
                self.assertEqual(status, 0)
                self.assertEqual(manifest, expected)

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

    def test_selected_contract_extraction_allows_only_exact_reexport_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            before = Path(temporary) / "before"
            after = Path(temporary) / "after"
            for root in (before, after):
                folder = root / "tests/behaviour"
                folder.mkdir(parents=True)
                (folder / "cases.py").write_text(
                    "from master_clock import master_clock\n"
                    "CASES={'M-SYNC-009':dict(run=master_clock)}\n")
            (before / "tests/behaviour/master_clock.py").write_text(
                "def master_clock(c): pass\n")
            (after / "tests/behaviour/master_clock.py").write_text(
                '"""Compatibility shim."""\n'
                "from contract.master_clock import master_clock\n")
            contract = after / "tests/behaviour/contract"
            contract.mkdir()
            (contract / "master_clock.py").write_text("def master_clock(c): pass\n")
            shim = "tests/behaviour/master_clock.py"
            owner = "tests/behaviour/contract/master_clock.py"
            self.assertEqual(targeted.selected_case_modules(before, ["M-SYNC-009"]), {shim})
            self.assertEqual(targeted.selected_case_modules(after, ["M-SYNC-009"]),
                             {shim, owner})
            production = {"mosaic.lua": ("100644", "blob", "a" * 40),
                          "lib/nb": ("160000", "commit", "b" * 40)}
            pinned = {path: ("100644", "blob", "c" * 40)
                      for path in targeted.PINNED_GATE_PATHS}
            before_tests = {**pinned, shim: ("100644", "blob", "d" * 40)}
            after_tests = {**pinned, shim: ("100644", "blob", "e" * 40),
                           owner: ("100644", "blob", "f" * 40)}
            with patch.object(targeted, "tree_entries", side_effect=[
                    production, production, before_tests, after_tests]):
                result = targeted.check_source_delta(before, after, ["M-SYNC-009"])
                self.assertEqual(result["changed_behaviour_paths"], [owner, shim])
            unrelated = "tests/behaviour/contract/unrelated.py"
            with patch.object(targeted, "tree_entries", side_effect=[
                    production, production, before_tests,
                    {**after_tests, unrelated: ("100644", "blob", "1" * 40)}]):
                with self.assertRaisesRegex(ValueError, "unrelated behaviour harness/fixture"):
                    targeted.check_source_delta(before, after, ["M-SYNC-009"])
            (after / shim).write_text(
                "from contract.master_clock import master_clock\n"
                "UNRELATED = 1\n")
            self.assertEqual(targeted.selected_case_modules(after, ["M-SYNC-009"]), {shim})
            with patch.object(targeted, "tree_entries", side_effect=[
                    production, production, before_tests, after_tests]):
                with self.assertRaisesRegex(ValueError, "unrelated behaviour harness/fixture"):
                    targeted.check_source_delta(before, after, ["M-SYNC-009"])
            (after / shim).write_text(
                "from contract.master_clock import master_clock\n")
            (contract / "master_clock.py").write_text("def unrelated(c): pass\n")
            self.assertEqual(targeted.selected_case_modules(after, ["M-SYNC-009"]), {shim})
            with patch.object(targeted, "tree_entries", side_effect=[
                    production, production, before_tests, after_tests]):
                with self.assertRaisesRegex(ValueError, "unrelated behaviour harness/fixture"):
                    targeted.check_source_delta(before, after, ["M-SYNC-009"])


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
        self.assertIn("ui_migration_profile:", workflow)
        self.assertIn("options: [base-midi, midi-modulation]", workflow)
        self.assertIn("if: ${{ !inputs.ui_migration_targeted }}", workflow)
        self.assertIn("if: ${{ always() && !inputs.ui_migration_targeted }}", workflow)
        self.assertIn("name: targeted-ui-migration-${{ github.run_id }}", workflow)
        self.assertIn("--before-sha \"$BEFORE_SHA\"", workflow)
        self.assertIn("--after-sha \"$AFTER_SHA\"", workflow)
        self.assertIn("--case-ids \"$CASE_IDS\"", workflow)
        self.assertIn('profile_args+=(--profile "$PROFILE" --mod-code-root', workflow)
        self.assertIn('--case-ids "$CASE_IDS" "${profile_args[@]}"', workflow)
        self.assertIn("--mod-code-root /tmp/mosaic-output-mods --mod-patches", workflow)
        self.assertIn("actual.get('profile', 'base-midi') == profile", workflow)
        self.assertIn("gate.get('profile', 'base-midi') == profile", workflow)
        self.assertIn("chown -R mosaic-ci:mosaic-ci /tmp/mosaic-output-mods", workflow)

    def test_targeted_bash_only_steps_declare_bash(self):
        workflow = (ROOT / ".github/workflows/behaviour.yml").read_text()
        for name in ("Prepare unprivileged behaviour user",
                     "Run passing before/after cases and strict gates"):
            block = workflow.split("      - name: " + name + "\n")[-1].split("      - name:", 1)[0]
            self.assertIn("        shell: bash\n", block, name)

    def test_dispatch_installs_git_before_sha_submodule_checkouts(self):
        workflow = (ROOT / ".github/workflows/behaviour.yml").read_text()
        install = workflow.index("- name: Install Git before SHA checkouts")
        checkout = workflow.index("- name: Check out baseline source")
        self.assertLess(install, checkout)
        self.assertIn("apt-get install -y --no-install-recommends git ca-certificates",
                      workflow[install:checkout])

    def test_dispatch_repeats_one_candidate_per_module_without_full_coverage_claim(self):
        workflow = (ROOT / ".github/workflows/behaviour.yml").read_text()
        self.assertIn("Repeat one candidate case per migrated module", workflow)
        self.assertIn("targeted.selected_case_modules(source, [case])", workflow)
        self.assertIn("selection.setdefault(owner, case)", workflow)
        self.assertIn("len(item['runs']) == 3", workflow)
        self.assertIn("actual['mosaic_revision'] == after_sha", workflow)
        self.assertIn("item.get('profile', 'base-midi') == profile", workflow)
        self.assertIn("actual.get('profile', 'base-midi') == profile", workflow)
        self.assertIn("item.get('mod_patches', False)", workflow)
        self.assertIn("targeted-ui-repeatability.json", workflow)
        self.assertIn("complete_regression_run=False", workflow)
        script = workflow.split("runuser -u mosaic-ci --preserve-environment -- python3 - <<'PY'\n", 1)[1]
        script = script.split("\n          PY", 1)[0]
        body = ast.parse("\n".join(line[10:] for line in script.splitlines())).body
        guarded = next(node for node in body if isinstance(node, ast.Try))
        repeat_loop = next(node for node in guarded.body if isinstance(node, ast.For))
        direct_assignments = {target.id for node in repeat_loop.body
                              if isinstance(node, ast.Assign)
                              for target in node.targets if isinstance(target, ast.Name)}
        self.assertIn("command", direct_assignments)
        self.assertTrue(any(isinstance(node, ast.Assign)
                            and isinstance(node.value, ast.Call)
                            and isinstance(node.value.func, ast.Attribute)
                            and node.value.func.attr == "run"
                            for node in repeat_loop.body))
        profile_branch = next(node for node in repeat_loop.body if isinstance(node, ast.If))
        command_assignment = next(node for node in repeat_loop.body
                                  if isinstance(node, ast.Assign)
                                  and any(isinstance(target, ast.Name)
                                          and target.id == "command"
                                          for target in node.targets))
        self.assertFalse(any(isinstance(node, ast.Constant)
                             and node.value == "--profile"
                             for node in ast.walk(command_assignment)))
        self.assertTrue(any(isinstance(node, ast.Constant)
                            and node.value == "--profile"
                            for node in ast.walk(profile_branch)))
        self.assertFalse(any(isinstance(node, ast.Call)
                             and isinstance(node.func, ast.Attribute)
                             and node.func.attr == "run"
                             for node in ast.walk(profile_branch)))

    def test_dispatch_repeat_selection_uses_exact_contract_owner(self):
        workflow = (ROOT / ".github/workflows/behaviour.yml").read_text()
        script = workflow.split("runuser -u mosaic-ci --preserve-environment -- python3 - <<'PY'\n", 1)[1]
        script = "\n".join(line[10:] for line in script.split("\n          PY", 1)[0].splitlines())
        body = ast.parse(script).body
        start = next(index for index, node in enumerate(body)
                     if isinstance(node, ast.Assign) and
                     any(isinstance(target, ast.Name) and target.id == "selection"
                         for target in node.targets))
        selection_code = compile(ast.Module(body=body[start:start + 2], type_ignores=[]),
                                 "repeat-selection", "exec")
        shim = "tests/behaviour/master_clock.py"
        contract = "tests/behaviour/contract/master_clock.py"
        scenarios = ((set(), "tests/behaviour/cases.py"),
                     ({shim}, shim),
                     ({contract}, contract),
                     ({shim, contract}, contract))
        for owners, expected in scenarios:
            with self.subTest(owners=owners):
                namespace = {"cases": ["M-SYNC-009"], "source": ROOT, "Path": Path,
                             "targeted": targeted}
                with patch.object(targeted, "selected_case_modules", return_value=owners):
                    exec(selection_code, namespace)
                self.assertEqual(namespace["selection"], {expected: "M-SYNC-009"})
        for owners in (({shim, "tests/behaviour/other.py"}),
                       ({shim, "tests/behaviour/contract/unrelated.py"}),
                       ({shim, contract, "tests/behaviour/other.py"})):
            with self.subTest(rejected=owners):
                namespace = {"cases": ["M-SYNC-009"], "source": ROOT, "Path": Path,
                             "targeted": targeted}
                with patch.object(targeted, "selected_case_modules", return_value=owners), \
                        self.assertRaises(ValueError):
                    exec(selection_code, namespace)


if __name__ == "__main__":
    unittest.main()

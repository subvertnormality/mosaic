"""Harness characterisation outside README: partial targeted CI gate contracts."""

import ast
import copy
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).with_name("targeted-ui-migration.py")
spec = importlib.util.spec_from_file_location("targeted_ui_migration", SCRIPT)
targeted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(targeted)
from cases import deterministic_case_results, reexpress_case_results


def recording_results(monotonic_base):
    return [
        {"kind": "boundary-active-step-midi-witness", "events": [
            {"recorded_step": 1,
             "preview": {"index": 10, "port": 1, "bytes": [144, 72, 90],
                         "logical_ns": 1_400_000_000,
                         "monotonic_ns": monotonic_base},
             "active_step_onset": {"index": 9, "port": 2,
                                    "bytes": [145, 60, 127],
                                    "logical_ns": 1_400_000_000,
                                    "monotonic_ns": monotonic_base - 1},
             "next_step_onset": {"index": 11, "port": 2,
                                 "bytes": [145, 62, 117],
                                 "logical_ns": 1_400_000_001,
                                 "monotonic_ns": monotonic_base + 1},
             "gap_to_next_ns": 1}],
         "other_stable_value": "preserve"},
        {"kind": "grid", "cells": [[1, 4], [16, 7]],
         "expected": [0, 15], "actual": [0, 15]},
    ]


def panic_results(identity):
    def origin(which, start, applied):
        sequence = 985 if which == "start" else 996
        return {"action_id": which + identity, "native_sequence": sequence,
                "origin_ns": start, "applied_ns": applied,
                "input_to_applied_ns": applied - start,
                "boundary": "backend-input-submission"}
    return [{"kind": "panic-pending-chord", "arp": True, "shape": 2,
             "sweep_events": 6144, "onsets": 5, "releases": 5,
             "metrics": None, "start_origin": origin("start", 10_000, 12_000),
             "stop_origin": origin("stop", 20_000, 31_000), "passed": True}]


class CaseResultReexpressionTests(unittest.TestCase):
    @staticmethod
    def acceptance(case, rows):
        return deterministic_case_results(case, rows)

    def test_recording_host_clocks_move_to_diagnostics_only(self):
        for case in ("M-REC-004", "M-REC-032", "M-REC-033"):
            with self.subTest(case=case):
                before, after = recording_results(50_000), recording_results(80_000)
                before_copy, after_copy = copy.deepcopy(before), copy.deepcopy(after)
                stable_before, diagnostic_before = self.acceptance(case, before)
                stable_after, diagnostic_after = self.acceptance(case, after)
                self.assertEqual(stable_before, stable_after)
                self.assertEqual(before, before_copy)
                self.assertEqual(after, after_copy)
                self.assertEqual(diagnostic_before[0]["raw_events"], before[0]["events"])
                self.assertEqual(diagnostic_after[0]["raw_events"], after[0]["events"])
                self.assertNotEqual(
                    diagnostic_before[0]["raw_events"][0]["preview"]["monotonic_ns"],
                    diagnostic_after[0]["raw_events"][0]["preview"]["monotonic_ns"])

    def test_recording_musical_fields_deadline_and_coordinates_remain_acceptance(self):
        mutations = (
            lambda rows: rows[0]["events"][0]["active_step_onset"]["bytes"].__setitem__(2, 126),
            lambda rows: rows[0]["events"][0]["active_step_onset"].__setitem__("logical_ns", 1_399_999_999),
            lambda rows: rows[0]["events"][0].__setitem__("gap_to_next_ns", 2),
            lambda rows: rows[0]["events"][0].__setitem__("recorded_step", 2),
            lambda rows: rows[1]["cells"][1].__setitem__(0, 13),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                before, after = recording_results(50_000), recording_results(80_000)
                mutate(after)
                self.assertNotEqual(self.acceptance("M-REC-032", before)[0],
                                    self.acceptance("M-REC-032", after)[0])

    def test_panic_action_clocks_move_to_diagnostics_and_stable_origin_is_verified(self):
        for case in ("M-PANIC-007", "M-PANIC-008", "M-PANIC-009", "M-PANIC-010"):
            with self.subTest(case=case):
                before, after = panic_results("before"), panic_results("after")
                stable_before, diagnostic_before = self.acceptance(case, before)
                stable_after, diagnostic_after = self.acceptance(case, after)
                self.assertEqual(stable_before, stable_after)
                self.assertEqual(stable_before[0]["start_origin"],
                                 {"verified": True, "native_sequence": 985,
                                  "boundary": "backend-input-submission"})
                self.assertEqual(diagnostic_before[0]["start_origin"],
                                 before[0]["start_origin"])
                self.assertEqual(diagnostic_after[0]["stop_origin"],
                                 after[0]["stop_origin"])
                self.assertNotEqual(diagnostic_before[0]["start_origin"]["action_id"],
                                    diagnostic_after[0]["start_origin"]["action_id"])

    def test_panic_musical_counts_shape_mode_metrics_and_stable_boundary_still_fail(self):
        mutations = (
            lambda row: row.__setitem__("onsets", 4),
            lambda row: row.__setitem__("releases", 4),
            lambda row: row.__setitem__("sweep_events", 6143),
            lambda row: row.__setitem__("arp", False),
            lambda row: row.__setitem__("shape", 1),
            lambda row: row.__setitem__("metrics", {"within_event_profile": False}),
            lambda row: row["start_origin"].__setitem__("boundary", "other-boundary"),
            lambda row: row["start_origin"].__setitem__("native_sequence", 984),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                before, after = panic_results("same"), panic_results("same")
                mutate(after[0])
                self.assertNotEqual(self.acceptance("M-PANIC-009", before)[0],
                                    self.acceptance("M-PANIC-009", after)[0])

    def test_real_time_and_unlisted_cases_are_verbatim(self):
        rows = recording_results(50_000)
        for case in ("M-REC-001", "M-REC-004"):
            with self.subTest(case=case):
                stable, diagnostic = deterministic_case_results(case, rows, lane="real-time")
                self.assertEqual(stable, rows)
                self.assertEqual(diagnostic, [])
        stable, diagnostic = deterministic_case_results("M-PANIC-006", rows)
        self.assertEqual(stable, rows)
        self.assertEqual(diagnostic, [])

    def test_diagnostics_attach_to_final_observation_without_replacing_state(self):
        class Context:
            pass
        with tempfile.TemporaryDirectory() as temporary:
            context = Context()
            context.clock_mode = "controlled-experimental"
            context.results = recording_results(50_000)
            context.observations = [{"state": {"diagnostics": {"beats": 4}}}]
            context.out = Path(temporary)
            reexpress_case_results(context, "M-REC-004")
            persisted = json.loads((context.out / "observations.json").read_text())
            self.assertEqual(persisted[-1]["state"]["diagnostics"]["beats"], 4)
            raw = persisted[-1]["case_result_diagnostics"][0]["raw_events"]
            self.assertEqual(raw, recording_results(50_000)[0]["events"])
            self.assertNotIn("monotonic_ns", context.results[0]["events"][0]["preview"])


class TargetedMigrationTests(unittest.TestCase):
    def test_case_lanes_follow_registry_controlled_only_metadata(self):
        selected = targeted.selected_case_lanes(ROOT, ROOT, [
            "M-ARP-005", "M-ARP-012", "M-ARP-013",
            "M-SPREAD-023", "M-SPREAD-026", "M-SPREAD-027",
            "M-GRID-001",
        ])
        self.assertEqual(selected, {
            "M-ARP-005": ("controlled-experimental",),
            "M-ARP-012": ("controlled-experimental",),
            "M-ARP-013": ("controlled-experimental",),
            "M-SPREAD-023": ("controlled-experimental",),
            "M-SPREAD-026": ("controlled-experimental",),
            "M-SPREAD-027": ("controlled-experimental",),
            "M-GRID-001": ("real-time", "controlled-experimental"),
        })

    def test_case_lane_applicability_must_match_both_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            before, after = Path(temporary) / "before", Path(temporary) / "after"
            before.mkdir()
            after.mkdir()
            for source, registration in ((before, "dict(controlled_only='reason')"),
                                         (after, "dict()")):
                case_file = source / "tests/behaviour/cases.py"
                case_file.parent.mkdir(parents=True)
                case_file.write_text("CASES = {'M-CASE-001': " + registration + "}\n")
            with self.assertRaisesRegex(ValueError, "lane applicability differs"):
                targeted.selected_case_lanes(before, after, ["M-CASE-001"])

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
                        behaviour_source_sha256={},
                        artifacts=artifacts)
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps(item))
            targeted.verified_manifest(manifest, "M-GRID-001",
                                       "controlled-experimental", "a" * 40,
                                       expected_behaviour_source_sha256={})
            for changed in (dict(passed=False), dict(mosaic_revision="b" * 40),
                            dict(diagnostic_only=False), dict(campaign_complete=True)):
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    manifest.write_text(json.dumps({**item, **changed}))
                    targeted.verified_manifest(manifest, "M-GRID-001",
                                               "controlled-experimental", "a" * 40,
                                               expected_behaviour_source_sha256={})
            manifest.write_text(json.dumps(item))
            (run / "restarted/results.json").write_text("[1]")
            with self.assertRaisesRegex(ValueError, "digest differs"):
                targeted.verified_manifest(manifest, "M-GRID-001",
                                           "controlled-experimental", "a" * 40,
                                           expected_behaviour_source_sha256={})

    def test_manifest_binds_requested_non_base_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            for name in ("recipe.json", "results.json"):
                (run / name).write_text("[]")
            item = dict(case="M-MOD-001", clock_mode="controlled-experimental",
                        mosaic_revision="a" * 40, profile="midi-modulation", passed=True,
                        campaign_complete=False, diagnostic_only=True, failure=None,
                        behaviour_source_sha256={},
                        artifacts=[dict(path=name, sha256=targeted.sha256(run / name), size=2)
                                   for name in ("recipe.json", "results.json")])
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps(item))
            targeted.verified_manifest(manifest, "M-MOD-001",
                                       "controlled-experimental", "a" * 40,
                                       profile="midi-modulation",
                                       expected_behaviour_source_sha256={})
            with self.assertRaisesRegex(ValueError, "profile differs"):
                targeted.verified_manifest(manifest, "M-MOD-001",
                                           "controlled-experimental", "a" * 40,
                                           expected_behaviour_source_sha256={})

    def test_manifest_binds_behavior_source_to_pre_run_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            for name in ("recipe.json", "results.json"):
                (run / name).write_text("[]")
            expected = {"tests/behaviour/cases.py": "a" * 64}
            item = dict(case="M-GRID-001", clock_mode="real-time",
                        mosaic_revision="a" * 40, profile="base-midi", passed=True,
                        campaign_complete=False, diagnostic_only=False, failure=None,
                        behaviour_source_sha256=expected,
                        artifacts=[dict(path=name, sha256=targeted.sha256(run / name), size=2)
                                   for name in ("recipe.json", "results.json")])
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps(item))
            with self.assertRaisesRegex(ValueError, "behaviour_source_sha256"):
                targeted.verified_manifest(
                    manifest, "M-GRID-001", "real-time", "a" * 40,
                    expected_behaviour_source_sha256={
                        "tests/behaviour/cases.py": "b" * 64})

    def test_execute_rechecks_checkout_cleanliness_after_each_run(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before, after = root / "before", root / "after"
            for source in (before, after):
                behaviour = source / "tests/behaviour"
                behaviour.mkdir(parents=True)
                (behaviour / "cases.py").write_text("# fixture\n")
            install = root / "installation.json"
            install.write_text("{}")
            output = root / "output"
            output.mkdir()
            expected_before = targeted.behaviour_source_hashes(before)
            args = SimpleNamespace(
                case_ids="M-GRID-001", before=before, after=after,
                before_sha="a" * 40, after_sha="b" * 40,
                profile="base-midi", mod_code_root=None, mod_patches=False,
                install=install, emulator=root, output=output)
            state = {"before_run_finished": False}

            def source_identity(source, expected):
                if source == before and state["before_run_finished"]:
                    raise ValueError("source checkout is dirty: " + str(source))
                return expected

            def run_one(source, case, lane, run_output, *rest):
                run = run_output / "run-1"
                run.mkdir(parents=True)
                manifest = run / "manifest.json"
                manifest.write_text("{}")
                if source == before:
                    state["before_run_finished"] = True
                return 0, manifest

            with patch.object(targeted, "source_identity", side_effect=source_identity), \
                    patch.object(targeted, "registry_profile",
                                 return_value={"M-GRID-001": "base-midi"}), \
                    patch.object(targeted, "selected_case_lanes",
                                 return_value={"M-GRID-001": ("real-time",)}), \
                    patch.object(targeted, "check_source_delta", return_value={}), \
                    patch.object(targeted.subprocess, "check_output", return_value="e" * 40), \
                    patch.object(targeted, "run_one", side_effect=run_one), \
                    patch.object(targeted, "verified_manifest") as verify_manifest, \
                    patch.object(targeted, "check_session_roots", return_value=[]):
                status = targeted.execute(args)

            report = json.loads((output / "targeted-ui-migration.json").read_text())
            self.assertEqual(
                verify_manifest.call_args_list[0].kwargs[
                    "expected_behaviour_source_sha256"],
                expected_before)
            self.assertEqual(status, 1)
            self.assertFalse(report["passed"])
            self.assertTrue(any("source checkout is dirty" in error
                                for error in report["cases"][0]["lanes"][0]["gate_errors"]))

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
                def launch(command, cwd, stdout, stderr, check, env, expected=expected):
                    expected.parent.mkdir(parents=True)
                    expected.write_text("{}")
                    self.assertEqual(command[command.index("--profile") + 1],
                                     "midi-modulation")
                    self.assertEqual(command[command.index("--mod-code-root") + 1],
                                     str(fixture))
                    self.assertIn("--mod-patches", command)
                    self.assertEqual(env["MOSAIC_BEHAVIOUR_INSTALLATION"], str(install))
                    if lane == "controlled-experimental":
                        self.assertIn("--experimental-install", command)
                    else:
                        self.assertNotIn("--experimental-install", command)
                    return type("Completed", (), {"returncode": 0})()
                with patch.object(targeted.subprocess, "run", side_effect=launch):
                    status, manifest = targeted.run_one(
                        source, "M-MOD-001", lane, output, install,
                        "midi-modulation", fixture, True)
                self.assertEqual(status, 0)
                self.assertEqual(manifest, expected)

    def test_nrpn_conversion_reads_inert_install_metadata_in_real_time(self):
        from patch_params import _nrpn_conversion_installation

        class DriverStub:
            launch_options = {"experimental_install": None}

        with tempfile.TemporaryDirectory() as temporary:
            install = Path(temporary) / "installation.json"
            install.write_text(json.dumps({"source": "/pinned/norns"}))
            with patch.dict(os.environ,
                            {"MOSAIC_BEHAVIOUR_INSTALLATION": str(install)}):
                self.assertEqual(_nrpn_conversion_installation(DriverStub()),
                                 {"source": "/pinned/norns"})

    def test_nrpn_conversion_prefers_driver_installation_when_present(self):
        from patch_params import _nrpn_conversion_installation

        class DriverStub:
            launch_options = {"experimental_install": "/driver/install.json"}

        with patch.dict(os.environ,
                        {"MOSAIC_BEHAVIOUR_INSTALLATION": "/other/install.json"}):
            with patch("pathlib.Path.read_text", return_value='{"source":"/driver/norns"}'):
                self.assertEqual(_nrpn_conversion_installation(DriverStub()),
                                 {"source": "/driver/norns"})

    def test_manifest_rejects_symlinked_file_and_ancestor_before_hashing(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "run"
            run.mkdir()
            (run / "recipe.json").write_text("[]")
            (run / "results.json").write_text("[]")
            item = dict(case="M-GRID-001", clock_mode="real-time",
                        mosaic_revision="a" * 40, profile="base-midi", passed=True,
                        campaign_complete=False, diagnostic_only=False, failure=None,
                        behaviour_source_sha256={},
                        artifacts=[dict(path=name, sha256=targeted.sha256(run / name), size=2)
                                   for name in ("recipe.json", "results.json")])
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps(item))
            original = Path.is_symlink
            def simulated_symlink(path):
                return path == run / "recipe.json" or original(path)
            with patch.object(Path, "is_symlink", simulated_symlink):
                with self.assertRaisesRegex(ValueError, "symlinked evidence path"):
                    targeted.verified_manifest(
                        manifest, "M-GRID-001", "real-time", "a" * 40,
                        expected_behaviour_source_sha256={})
            # A symlinked containing directory is equally unsafe, even when
            # the recipe path itself is a regular file in its target.
            with patch.object(Path, "is_symlink", lambda path: path == run or original(path)):
                with self.assertRaisesRegex(ValueError, "symlinked evidence path"):
                    targeted.verified_manifest(
                        manifest, "M-GRID-001", "real-time", "a" * 40,
                        expected_behaviour_source_sha256={})

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
                        behaviour_source_sha256={},
                        artifacts=[dict(path=name, sha256=targeted.sha256(run / name), size=2)
                                   for name in ("recipe.json", "results.json")])
            manifest = run / "manifest.json"
            manifest.write_text(json.dumps(item))
            with self.assertRaisesRegex(ValueError, "symlinked evidence path"):
                targeted.verified_manifest(
                    manifest, "M-GRID-001", "real-time", "a" * 40,
                    expected_behaviour_source_sha256={})

    def test_source_delta_rejects_production_and_shared_harness_changes(self):
        production = {"mosaic.lua": ("100644", "blob", "a" * 40),
                      "lib/nb": ("160000", "commit", "b" * 40)}
        tests = {"tests/behaviour/driver.py": ("100644", "blob", "c" * 40),
                 "tests/behaviour/scale_lock_precedence.py": ("100644", "blob", "d" * 40),
                 "tests/behaviour/ui_migration_gate.py": ("100644", "blob", "f" * 40),
                 "tests/behaviour/ci/compare_ptn_graph.lua": ("100644", "blob", "0" * 40),
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
            ui_test = "tests/behaviour/test_ui.py"
            changed_case_and_ui_test = {**changed_case, ui_test:
                                        ("100644", "blob", "e" * 40)}
            with patch.object(targeted, "tree_entries", side_effect=[
                    production, production, tests, changed_case_and_ui_test]):
                result = targeted.check_source_delta(
                    Path("before"), Path("after"), ["M-SCALE-LOCK-003"])
                self.assertEqual(result["changed_behaviour_paths"],
                                 [case_file, ui_test])
            with patch.object(targeted, "tree_entries", side_effect=[
                    production, production, tests,
                    {**tests, ui_test: ("100644", "blob", "e" * 40)}]):
                with self.assertRaisesRegex(ValueError, "UI unit tests changed without"):
                    targeted.check_source_delta(
                        Path("before"), Path("after"), ["M-SCALE-LOCK-003"])
            ui_layer_test = "tests/behaviour/test_ui_layer.py"
            with patch.object(targeted, "tree_entries", side_effect=[
                    production, production, tests,
                    {**changed_case, ui_layer_test: ("100644", "blob", "e" * 40)}]):
                result = targeted.check_source_delta(
                    Path("before"), Path("after"), ["M-SCALE-LOCK-003"])
                self.assertEqual(result["changed_behaviour_paths"],
                                 [case_file, ui_layer_test])
            with patch.object(targeted, "tree_entries", side_effect=[
                    production, production, tests,
                    {**tests, ui_layer_test: ("100644", "blob", "e" * 40)}]):
                with self.assertRaisesRegex(ValueError, "UI unit tests changed without"):
                    targeted.check_source_delta(
                        Path("before"), Path("after"), ["M-SCALE-LOCK-003"])
            symlink_case = {**tests, case_file: ("120000", "blob", "e" * 40)}
            with patch.object(targeted, "tree_entries",
                              side_effect=[production, production, tests, symlink_case]):
                with self.assertRaisesRegex(ValueError, "not a regular file"):
                    targeted.check_source_delta(
                        Path("before"), Path("after"), ["M-SCALE-LOCK-003"])

    def test_inline_case_source_permits_its_ui_regression(self):
        production = {"mosaic.lua": ("100644", "blob", "a" * 40),
                      "lib/nb": ("160000", "commit", "b" * 40)}
        pinned = {path: ("100644", "blob", "c" * 40)
                  for path in targeted.PINNED_GATE_PATHS}
        case_path = "tests/behaviour/cases.py"
        test_path = "tests/behaviour/test_ui_layer.py"
        before = {**pinned, case_path: ("100644", "blob", "d" * 40)}
        after = {**before, case_path: ("100644", "blob", "e" * 40),
                 test_path: ("100644", "blob", "f" * 40)}
        with patch.object(targeted, "selected_case_modules", return_value=set()), \
                patch.object(targeted, "tree_entries", side_effect=[
                    production, production, before, after]):
            result = targeted.check_source_delta(
                Path("before"), Path("after"), ["M-REC-001"])
        self.assertEqual(result["changed_behaviour_paths"], [case_path, test_path])

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

    def test_patch_persistence_requires_equal_decoded_graph_and_preserves_raw_hashes(self):
        import hashlib
        import shutil

        from ui_migration_gate import check_session_roots

        lua = shutil.which("lua5.3") or shutil.which("lua")
        if not lua:
            self.skipTest("Lua 5.3 runtime unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for side in ("before", "after"):
                run = root / side
                run.mkdir()
                (run / "recipe.json").write_text("[]")
                (run / "generated-project").mkdir()
            before = (root / "before/generated-project/autosave.ptn")
            after = (root / "after/generated-project/autosave.ptn")
            before.write_text('return { {"autosave", {2}}, { shared={3}, again={3} }, { value=7 } }\n')
            # Different table-pool layout and raw bytes; decoded field values
            # and the shared child alias remain identical.
            after.write_text('return { { "autosave", {3} }, { orphan=9 }, { again={4}, shared={4} }, { value=7 } }\n')
            self.assertNotEqual(hashlib.sha256(before.read_bytes()).digest(),
                                hashlib.sha256(after.read_bytes()).digest())
            def save_results(side_path, pset_sha="c" * 64):
                project_sha = hashlib.sha256(side_path.read_bytes()).hexdigest()
                (side_path.parents[1] / "results.json").write_text(json.dumps([
                    {"kind": "patch-autosave", "files": [
                        {"name": "autosave.ptn", "sha256": project_sha},
                        {"name": "autosave.pset", "sha256": pset_sha},
                    ]},
                ]))
            save_results(before)
            save_results(after)
            self.assertEqual(check_session_roots(root / "before", root / "after",
                                                 "controlled", case="M-PATCH-008"), [])
            for changed in (
                    'return { {"autosave", {2}}, { shared={3}, again={3} }, { value=8 } }\n',
                    'return { {"autosave", {2}}, { shared={3}, again={4} }, { value=7 }, { value=7 } }\n',
                    'return { {"autosave", {999}}, { shared={3}, again={3} }, { value=7 } }\n'):
                after.write_text(changed)
                save_results(after)
                self.assertTrue(any("persisted project graphs differ" in error
                                    for error in check_session_roots(
                                        root / "before", root / "after", "controlled",
                                        case="M-PATCH-008")))
            after.write_text('return { { "autosave", {3} }, { orphan=9 }, { again={4}, shared={4} }, { value=7 } }\n')
            save_results(after)
            save_results(after, pset_sha="d" * 64)
            self.assertTrue(any("controlled results differ" in error
                                for error in check_session_roots(
                                    root / "before", root / "after", "controlled",
                                    case="M-PATCH-008")))
            after.unlink()
            self.assertTrue(any("missing persisted project artifact" in error
                                for error in check_session_roots(
                                    root / "before", root / "after", "controlled",
                                    case="M-PATCH-009")))

    def test_transpose_autosave_requires_equal_decoded_graph_and_preserves_raw_hashes(self):
        import hashlib
        import json
        import shutil

        from ui_migration_gate import check_session_roots

        if not (shutil.which("lua5.3") or shutil.which("lua")):
            self.skipTest("Lua 5.3 runtime unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            after_results = root / "after/results.json"
            projects = {}
            for side in ("before", "after"):
                run = root / side
                (run / "generated-project").mkdir(parents=True)
                (run / "recipe.json").write_text("[]")
                project = run / "generated-project/autosave.ptn"
                project.write_text(
                    'return { {song={2}}, {source={3}, copy={3}}, {value=7} }\n'
                    if side == "before" else
                    'return { {song={3}}, {unused=0}, {source={4}, copy={4}}, {value=7} }\n')
                projects[side] = project
                ptn_sha = hashlib.sha256(project.read_bytes()).hexdigest()
                (run / "results.json").write_text(json.dumps([{
                    "kind": "transpose-autosave",
                    "files": {"autosave.ptn": ptn_sha, "autosave.pset": "a" * 64},
                    "passed": True,
                }]))
            before_sha = hashlib.sha256(projects["before"].read_bytes()).hexdigest()
            after_sha = hashlib.sha256(projects["after"].read_bytes()).hexdigest()
            self.assertNotEqual(before_sha, after_sha)
            self.assertEqual(check_session_roots(
                root / "before", root / "after", "controlled", case="M-TRANS-008"), [])

            after_project = projects["after"]
            after_project.write_text(
                'return { {song={3}}, {unused=0}, {source={4}, copy={4}}, {value=8} }\n')
            row = json.loads(after_results.read_text())
            row[0]["files"]["autosave.ptn"] = hashlib.sha256(
                after_project.read_bytes()).hexdigest()
            after_results.write_text(json.dumps(row))
            self.assertTrue(any("persisted project graphs differ" in error
                                for error in check_session_roots(
                                    root / "before", root / "after", "controlled",
                                    case="M-TRANS-008")))

            after_project.write_text(
                'return { {song={3}}, {unused=0}, {source={4}, copy={5}}, '
                '{value=7}, {value=7} }\n')
            row = json.loads(after_results.read_text())
            row[0]["files"]["autosave.ptn"] = hashlib.sha256(
                after_project.read_bytes()).hexdigest()
            after_results.write_text(json.dumps(row))
            errors = check_session_roots(
                root / "before", root / "after", "controlled", case="M-TRANS-008")
            self.assertTrue(any("reference/alias mismatch" in error for error in errors), errors)

            after_project.write_text(
                'return { {song={3}}, {unused=0}, {source={4}, copy={4}}, {value=7} }\n')
            row = json.loads(after_results.read_text())
            row[0]["files"]["autosave.ptn"] = hashlib.sha256(
                after_project.read_bytes()).hexdigest()
            row[0]["files"]["autosave.pset"] = "b" * 64
            after_results.write_text(json.dumps(row))
            self.assertTrue(any("controlled results differ" in error
                                for error in check_session_roots(
                                    root / "before", root / "after", "controlled",
                                    case="M-TRANS-008")))

            row[0]["files"]["autosave.pset"] = "a" * 64
            after_results.write_text(json.dumps(row))
            row[0]["files"]["autosave.ptn"] = "f" * 64
            after_results.write_text(json.dumps(row))
            errors = check_session_roots(
                root / "before", root / "after", "controlled", case="M-TRANS-008")
            self.assertTrue(any("transpose autosave .ptn SHA differs from artifact" in error
                                for error in errors), errors)
            after_project.unlink()
            errors = check_session_roots(
                root / "before", root / "after", "controlled", case="M-TRANS-008")
            self.assertTrue(any("after missing persisted project artifact" in error
                                for error in errors), errors)

    def test_pre_policy_project_fixtures_are_compared_as_graphs(self):
        import shutil

        from ui_migration_gate import check_session_roots

        import hashlib
        import json

        if not (shutil.which("lua5.3") or shutil.which("lua")):
            self.skipTest("Lua 5.3 runtime unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for side in ("before", "after"):
                run = root / side
                run.mkdir()
                (run / "recipe.json").write_text("[]")
                (run / "results.json").write_text("[]")
                fixture = "pre-policy-seed"
                (run / fixture).mkdir()
                project = run / fixture / "autosave.ptn"
                project.write_text(
                    'return { {"autosave", {2}}, { policy={3} }, { enabled=true } }\n')
                (run / "results.json").write_text(json.dumps([{
                    "kind": "pre-policy-project-fixture",
                    "removed_fields": ["nrpn_policy_version", "nrpn_stored_modes"],
                    "sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
                    "numeric_values_unchanged": True,
                }]))
            (root / "after/pre-policy-seed/autosave.ptn").write_text(
                'return { { "autosave", {3} }, { spare=0 }, { policy={4} }, { enabled=true } }\n')
            after_project = root / "after/pre-policy-seed/autosave.ptn"
            (root / "after/results.json").write_text(json.dumps([{
                "kind": "pre-policy-project-fixture",
                "removed_fields": ["nrpn_policy_version", "nrpn_stored_modes"],
                "sha256": hashlib.sha256(after_project.read_bytes()).hexdigest(),
                "numeric_values_unchanged": True,
            }]))
            self.assertEqual(check_session_roots(
                root / "before", root / "after", "controlled", case="M-PATCH-051"), [])
            self.assertEqual(check_session_roots(
                root / "before", root / "after", "controlled", case="M-PATCH-059"), [])
            (root / "after/pre-policy-seed/autosave.ptn").write_text(
                'return { {"autosave", {2}}, { policy={3} }, { enabled=false } }\n')
            after_project = root / "after/pre-policy-seed/autosave.ptn"
            (root / "after/results.json").write_text(json.dumps([{
                "kind": "pre-policy-project-fixture",
                "removed_fields": ["nrpn_policy_version", "nrpn_stored_modes"],
                "sha256": hashlib.sha256(after_project.read_bytes()).hexdigest(),
                "numeric_values_unchanged": True,
            }]))
            self.assertTrue(any("persisted project graphs differ for pre-policy-seed/autosave.ptn" in error
                                for error in check_session_roots(
                                    root / "before", root / "after", "controlled",
                                    case="M-PATCH-059")))

    def test_recording_persistence_compares_root_and_reload_project_graphs(self):
        import hashlib
        import json
        import shutil

        from ui_migration_gate import check_session_roots

        if not (shutil.which("lua5.3") or shutil.which("lua")):
            self.skipTest("Lua 5.3 runtime unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = root / "before"
            after = root / "after"
            for side in (before, after):
                for session in (Path("."), Path("recording-reload-1"),
                                Path("recording-reload-2")):
                    run = side / session
                    run.mkdir(parents=True, exist_ok=True)
                    (run / "recipe.json").write_text("[]")
                    (run / "results.json").write_text("[]")
                for session in (Path("."), Path("recording-reload-1")):
                    run = side / session
                    capture = run / "generated-project"
                    capture.mkdir()
                    project = capture / "autosave.ptn"
                    project.write_text(
                        'return { {"autosave", {2}}, {state={3}}, {value=7} }\n'
                        if side == before else
                        'return { {"autosave", {3}}, {unused=0}, {state={4}}, {value=7} }\n')
                    (run / "results.json").write_text(json.dumps([{
                        "kind": "recording-autosave-files",
                        "files": {"autosave.ptn": hashlib.sha256(project.read_bytes()).hexdigest(),
                                  "autosave.pset": "a" * 64},
                    }]))
            self.assertEqual(check_session_roots(
                before, after, "controlled", case="M-REC-PARAM-027"), [])
            nested = after / "recording-reload-1/generated-project/autosave.ptn"
            nested.write_text('return { {"autosave", {2}}, {state={3}}, {value=8} }\n')
            nested_result = after / "recording-reload-1/results.json"
            row = json.loads(nested_result.read_text())
            row[0]["files"]["autosave.ptn"] = hashlib.sha256(nested.read_bytes()).hexdigest()
            nested_result.write_text(json.dumps(row))
            self.assertTrue(any("persisted project graphs differ" in error
                                for error in check_session_roots(
                                    before, after, "controlled", case="M-REC-PARAM-027")))
            nested.write_text('return { {"autosave", {3}}, {unused=0}, {state={4}}, {value=7} }\n')
            row[0]["files"]["autosave.ptn"] = hashlib.sha256(nested.read_bytes()).hexdigest()
            row[0]["files"]["autosave.pset"] = "b" * 64
            nested_result.write_text(json.dumps(row))
            self.assertTrue(any("controlled results differ" in error
                                for error in check_session_roots(
                                    before, after, "controlled", case="M-REC-PARAM-027")))

    def test_save_001_graph_gate_rejects_unverified_ptn_hash(self):
        import json
        import shutil

        from ui_migration_gate import check_session_roots

        if not (shutil.which("lua5.3") or shutil.which("lua")):
            self.skipTest("Lua 5.3 runtime unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for side in ("before", "after"):
                run = root / side
                (run / "generated-project").mkdir(parents=True)
                (run / "recipe.json").write_text("[]")
                project = run / "generated-project/autosave.ptn"
                project.write_text('return { {x={1},y={1}} }\n')
                (run / "results.json").write_text(json.dumps([{
                    "kind": "saved-project",
                    "files": [
                        {"name": "autosave.ptn", "sha256": "f" * 64},
                        {"name": "autosave.pset", "sha256": "a" * 64},
                    ],
                }]))
            errors = check_session_roots(
                root / "before", root / "after", "controlled", case="M-SAVE-001")
            self.assertTrue(any("saved-project autosave.ptn SHA differs from artifact" in error
                                for error in errors), errors)

    def test_save_001_compares_captured_graph_and_preserves_pset(self):
        import hashlib
        import json
        import shutil

        from ui_migration_gate import check_session_roots

        if not (shutil.which("lua5.3") or shutil.which("lua")):
            self.skipTest("Lua 5.3 runtime unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            projects = {}
            for side in ("before", "after"):
                run = root / side
                (run / "generated-project").mkdir(parents=True)
                (run / "recipe.json").write_text("[]")
                project = run / "generated-project/autosave.ptn"
                project.write_text(
                    'return { {song={2}}, {source={3}, copy={3}}, {value=7} }\n'
                    if side == "before" else
                    'return { {song={3}}, {unused=0}, {source={4}, copy={4}}, {value=7} }\n')
                projects[side] = project
                (run / "results.json").write_text(json.dumps([{
                    "kind": "saved-project",
                    "files": [
                        {"name": "autosave.ptn", "sha256": hashlib.sha256(project.read_bytes()).hexdigest()},
                        {"name": "autosave.pset", "sha256": "a" * 64},
                    ],
                }]))
            self.assertNotEqual(hashlib.sha256(projects["before"].read_bytes()).hexdigest(),
                                hashlib.sha256(projects["after"].read_bytes()).hexdigest())
            self.assertEqual(check_session_roots(
                root / "before", root / "after", "controlled", case="M-SAVE-001"), [])
            values_path = root / "after/results.json"
            values = json.loads(values_path.read_text())
            values[0]["files"][1]["sha256"] = "b" * 64
            values_path.write_text(json.dumps(values))
            self.assertTrue(any("controlled results differ" in error for error in check_session_roots(
                root / "before", root / "after", "controlled", case="M-SAVE-001")))

    def test_save_001_requires_exact_ptn_and_pset_file_rows(self):
        import hashlib
        import json
        import shutil

        from ui_migration_gate import check_session_roots

        if not (shutil.which("lua5.3") or shutil.which("lua")):
            self.skipTest("Lua 5.3 runtime unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_rows = []
            for side in ("before", "after"):
                run = root / side
                (run / "generated-project").mkdir(parents=True)
                (run / "recipe.json").write_text("[]")
                project = run / "generated-project/autosave.ptn"
                project.write_text('return { {x={1},y={1}} }\n')
                valid_rows.append([
                    {"name": "autosave.ptn",
                     "sha256": hashlib.sha256(project.read_bytes()).hexdigest()},
                    {"name": "autosave.pset", "sha256": "a" * 64},
                ])

            malformed_rows = (
                ("missing autosave.pset", lambda rows: rows[:1]),
                ("duplicate autosave.pset", lambda rows: rows + [dict(rows[1])]),
                ("unexpected saved-project file", lambda rows: rows + [
                    {"name": "other.json", "sha256": "b" * 64}]),
                ("malformed saved-project file row", lambda rows: [rows[0],
                    {"name": [], "sha256": "b" * 64}]),
            )
            for label, malformed in malformed_rows:
                with self.subTest(label=label):
                    for side, rows in zip(("before", "after"), valid_rows):
                        (root / side / "results.json").write_text(json.dumps([{
                            "kind": "saved-project",
                            "files": malformed(rows),
                        }]))
                    errors = check_session_roots(
                        root / "before", root / "after", "controlled", case="M-SAVE-001")
                    self.assertTrue(any("requires exactly autosave.ptn and autosave.pset files"
                                        in error for error in errors), errors)

            for side, rows in zip(("before", "after"), valid_rows):
                (root / side / "results.json").write_text(json.dumps([{
                    "kind": "saved-project",
                    "files": [rows[0], {"name": "autosave.pset"}],
                }]))
            errors = check_session_roots(
                root / "before", root / "after", "controlled", case="M-SAVE-001")
            self.assertTrue(any("autosave.pset SHA is missing or invalid" in error
                                for error in errors), errors)

    def test_archived_project_result_rows_allow_only_the_verified_ptn_hash(self):
        from ui_migration_gate import compare_results_with_verified_project

        archived_pairs = (
            ("patch-autosave", {
                "kind": "patch-autosave", "files": [
                    {"name": "autosave.ptn", "sha256": "2f5a39ca4c87b7b0c3fc0951fd69e6f571bee164ece9b4a93efbe930a4ee908b"},
                    {"name": "autosave.pset", "sha256": "d7b81b2402067f472d9a7a317486444111cec332a33d1b7054b0c2aa9183f7fa"},
                ]}, {
                "kind": "patch-autosave", "files": [
                    {"name": "autosave.ptn", "sha256": "28508a40bc409b87cc901db1774ec722606b7cbd3001d7ca73a851b527b7724d"},
                    {"name": "autosave.pset", "sha256": "d7b81b2402067f472d9a7a317486444111cec332a33d1b7054b0c2aa9183f7fa"},
                ]}, "2f5a39ca4c87b7b0c3fc0951fd69e6f571bee164ece9b4a93efbe930a4ee908b",
                "28508a40bc409b87cc901db1774ec722606b7cbd3001d7ca73a851b527b7724d"),
            ("patch-autosave", {
                "kind": "patch-autosave", "files": [
                    {"name": "autosave.ptn", "sha256": "9f6f77f6797158538a249b58ae187b3301fe7163d1b5a5b9f3672e371828f9b4"},
                    {"name": "autosave.pset", "sha256": "c9d3d14e0170c9c189e179c670a0f8c383ce13c5e14d2a730d70be70b011bde2"},
                ]}, {
                "kind": "patch-autosave", "files": [
                    {"name": "autosave.ptn", "sha256": "30a89766fb37223750eeb2589f6bd80b693ef825daed6e1bae0fbd65102cd0af"},
                    {"name": "autosave.pset", "sha256": "c9d3d14e0170c9c189e179c670a0f8c383ce13c5e14d2a730d70be70b011bde2"},
                ]}, "9f6f77f6797158538a249b58ae187b3301fe7163d1b5a5b9f3672e371828f9b4",
                "30a89766fb37223750eeb2589f6bd80b693ef825daed6e1bae0fbd65102cd0af"),
            ("pre-policy-project-fixture", {
                "kind": "pre-policy-project-fixture",
                "removed_fields": ["nrpn_policy_version", "nrpn_stored_modes"],
                "sha256": "f5413b2e6055fe3bf8d08979254e5d1d040eb79a54d2ee54d6a46966bf9c9be6",
                "numeric_values_unchanged": True}, {
                "kind": "pre-policy-project-fixture",
                "removed_fields": ["nrpn_policy_version", "nrpn_stored_modes"],
                "sha256": "064a575659a2e895e28124f1dfa6127c33f16eb98e0c09e0400a22174db37038",
                "numeric_values_unchanged": True},
                "f5413b2e6055fe3bf8d08979254e5d1d040eb79a54d2ee54d6a46966bf9c9be6",
                "064a575659a2e895e28124f1dfa6127c33f16eb98e0c09e0400a22174db37038"),
            ("pre-policy-project-fixture", {
                "kind": "pre-policy-project-fixture",
                "removed_fields": ["nrpn_policy_version", "nrpn_stored_modes"],
                "sha256": "949b978148972e56db02166d31c09bd5569612640457e4dc7a83431837c4dd84",
                "numeric_values_unchanged": True}, {
                "kind": "pre-policy-project-fixture",
                "removed_fields": ["nrpn_policy_version", "nrpn_stored_modes"],
                "sha256": "782e05e6f8544e0649be5d8259735d96ae1b8bbbf14aa4622c3cfac5eefe47ac",
                "numeric_values_unchanged": True},
                "949b978148972e56db02166d31c09bd5569612640457e4dc7a83431837c4dd84",
                "782e05e6f8544e0649be5d8259735d96ae1b8bbbf14aa4622c3cfac5eefe47ac"),
        )
        for kind, before_entry, after_entry, before_sha, after_sha in archived_pairs:
            with self.subTest(kind=kind):
                self.assertEqual(compare_results_with_verified_project(
                    [before_entry], [after_entry], "controlled", kind,
                    before_sha, after_sha), [])

        patch_before, patch_after = archived_pairs[0][1:3]
        changed_pset = json.loads(json.dumps(patch_after))
        changed_pset["files"][1]["sha256"] = "e" * 64
        errors = compare_results_with_verified_project(
            [patch_before], [changed_pset], "controlled", "patch-autosave",
            archived_pairs[0][3], archived_pairs[0][4])
        self.assertTrue(any("controlled results differ" in error for error in errors), errors)
        duplicate = [patch_after, dict(patch_after)]
        errors = compare_results_with_verified_project(
            [patch_before], duplicate, "controlled", "patch-autosave",
            archived_pairs[0][3], archived_pairs[0][4])
        self.assertTrue(any("exactly one patch-autosave" in error for error in errors), errors)
        errors = compare_results_with_verified_project(
            [], [patch_after], "controlled", "patch-autosave",
            archived_pairs[0][3], archived_pairs[0][4])
        self.assertTrue(any("exactly one patch-autosave" in error for error in errors), errors)
        other_payload = json.loads(json.dumps(patch_after))
        other_payload["unrelated"] = "changed"
        errors = compare_results_with_verified_project(
            [patch_before], [other_payload], "controlled", "patch-autosave",
            archived_pairs[0][3], archived_pairs[0][4])
        self.assertTrue(any("controlled results differ" in error for error in errors), errors)
        other_hash = {"kind": "other-artifact", "sha256": "e" * 64}
        changed_other_hash = {"kind": "other-artifact", "sha256": "f" * 64}
        errors = compare_results_with_verified_project(
            [patch_before, other_hash], [patch_after, changed_other_hash],
            "controlled", "patch-autosave", archived_pairs[0][3], archived_pairs[0][4])
        self.assertTrue(any("controlled results differ" in error for error in errors), errors)

    def test_persisted_project_gate_is_scoped_to_patch_recall_cases_and_controlled_lane(self):
        from ui_migration_gate import check_session_roots

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for side in ("before", "after"):
                (root / side).mkdir()
                (root / side / "recipe.json").write_text("[]")
                (root / side / "results.json").write_text("[]")
            self.assertEqual(check_session_roots(root / "before", root / "after",
                                                 "controlled", case="M-PAT-001"), [])
            self.assertEqual(check_session_roots(root / "before", root / "after",
                                                 "real-time", case="M-PATCH-008"), [])

    def test_project_gate_fails_closed_when_lua_runtime_is_missing(self):
        from unittest.mock import patch

        from ui_migration_gate import check_session_roots

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for side in ("before", "after"):
                run = root / side
                (run / "generated-project").mkdir(parents=True)
                (run / "recipe.json").write_text("[]")
                (run / "results.json").write_text("[]")
                (run / "generated-project/autosave.ptn").write_text(
                    'return { {"autosave", {2}}, { value=true } }\n')
            with patch("ui_migration_gate.shutil.which", return_value=None):
                errors = check_session_roots(
                    root / "before", root / "after", "controlled", case="M-PATCH-008")
        self.assertTrue(any("Lua 5.3 runtime unavailable" in error for error in errors), errors)

    def test_project_result_gate_rejects_non_array_json_without_raising(self):
        import json
        import hashlib
        import shutil

        from ui_migration_gate import check_session_roots

        if not (shutil.which("lua5.3") or shutil.which("lua")):
            self.skipTest("Lua 5.3 runtime unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for side in ("before", "after"):
                run = root / side
                (run / "generated-project").mkdir(parents=True)
                (run / "recipe.json").write_text("[]")
                project = run / "generated-project/autosave.ptn"
                project.write_text('return { {"autosave", {2}}, { value=true } }\n')
                (run / "results.json").write_text(json.dumps([{
                    "kind": "patch-autosave", "files": [{
                        "name": "autosave.ptn",
                        "sha256": hashlib.sha256(project.read_bytes()).hexdigest(),
                    }],
                }]))
            (root / "after/results.json").write_text("null")
            errors = check_session_roots(
                root / "before", root / "after", "controlled", case="M-PATCH-008")
        self.assertTrue(any("after results are not an array" in error for error in errors), errors)

    def test_dispatch_never_feeds_partial_report_to_full_aggregation(self):
        workflow = (ROOT / ".github/workflows/behaviour.yml").read_text()
        self.assertIn("ui_migration_targeted:", workflow)
        self.assertIn("ui_migration_profile:", workflow)
        self.assertIn("options: [base-midi, midi-modulation]", workflow)
        self.assertEqual(workflow.count(
            "if: ${{ !inputs.ui_migration_targeted && !inputs.ui_migration_drift }}"), 4)
        self.assertIn(
            "if: ${{ always() && !inputs.ui_migration_targeted && !inputs.ui_migration_drift }}",
            workflow)
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

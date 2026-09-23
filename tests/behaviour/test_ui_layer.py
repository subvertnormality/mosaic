import sys
import tempfile
import unittest
from pathlib import Path


BEHAVIOUR = Path(__file__).resolve().parent
if str(BEHAVIOUR) not in sys.path:
    sys.path.insert(0, str(BEHAVIOUR))


def _raw_helper_for_reachability(driver):
    driver.tap(1, 8)


def _case_reaching_raw_helper(driver):
    _raw_helper_for_reachability(driver)


class UiLayerGuardTests(unittest.TestCase):
    def test_recording_lifetimes_use_semantic_ui(self):
        from recording_lifetimes import (
            recording_lifetime, recording_nrpn,
            recording_ten_slots, recording_ten_slots_trigless,
        )
        from ui_layer_guard import callable_raw_dependencies

        for run in (recording_lifetime, recording_nrpn,
                    recording_ten_slots, recording_ten_slots_trigless):
            self.assertEqual(callable_raw_dependencies(run), [], run.__name__)

    def test_harmony_page_navigation_preserves_header_observations(self):
        """README MERGE-FOUNDATION/HARMONY-REVOICE: show the selected page."""
        import ast
        import inspect
        import textwrap

        from harmony_merge_workflow import revoice_workflow, setup_foundation

        for run, page in ((setup_foundation, "merge_shape"),
                          (revoice_workflow, "harmony")):
            calls = [node for node in ast.walk(ast.parse(
                textwrap.dedent(inspect.getsource(run))))
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "ui"
                and node.args and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == page]
            navigation = [node.lineno for node in calls
                          if node.func.attr == "channel_page"]
            observations = [node.lineno for node in calls
                            if node.func.attr == "expect_header"]
            self.assertEqual(len(navigation), 1, run.__name__)
            self.assertTrue(any(line > navigation[0] for line in observations),
                            "%s lost its screen-header result" % run.__name__)

    def test_harmony_replay_retains_page_observations_and_navigation(self):
        """README Harmony workflows retain their visible page checkpoints."""
        import ast
        import inspect
        import textwrap

        from harmony_merge_workflow import (
            ensemble_polyrhythm_workflow, held_step_precedence_workflow,
            no_voicing_fallback_workflow,
        )

        for run, page, minimum in (
            (ensemble_polyrhythm_workflow, "harmony", 3),
            (no_voicing_fallback_workflow, "harmony", 1),
            (held_step_precedence_workflow, "harmony", 1),
            (held_step_precedence_workflow, "note_dashboard", 1),
        ):
            tree = ast.parse(textwrap.dedent(inspect.getsource(run)))
            calls = [node for node in ast.walk(tree)
                     if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Attribute)
                     and isinstance(node.func.value, ast.Attribute)
                     and node.func.value.attr == "ui"
                     and node.args and isinstance(node.args[0], ast.Constant)
                     and node.args[0].value == page]
            observations = [node for node in calls
                            if node.func.attr == "expect_header"]
            self.assertGreaterEqual(len(observations), minimum,
                                    "%s lost a %s screen-header result" %
                                    (run.__name__, page))
        tree = ast.parse(textwrap.dedent(inspect.getsource(
            ensemble_polyrhythm_workflow)))
        channel_three = [node for node in ast.walk(tree)
                         if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute)
                         and node.func.attr == "channel_page"
                         and node.args and isinstance(node.args[0], ast.Constant)
                         and node.args[0].value == "harmony"
                         and any(keyword.arg == "channel"
                                 and isinstance(keyword.value, ast.Constant)
                                 and keyword.value.value == 3
                                 for keyword in node.keywords)]
        self.assertEqual(len(channel_three), 1,
                         "ensemble must navigate back to Ch. 3 Harmony")

    def test_allowlist_is_exact_and_fail_closed(self):
        from ui_layer_guard import validate_allowlist

        self.assertEqual(validate_allowlist(), [])
    def test_raw_state_access_is_detected_on_supported_python(self):
        from ui_layer_guard import raw_sites

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "case.py"
            path.write_text("def run(c):\n    return c.snapshot()['frame'], c.snapshot()['grid']\n")
            sites = raw_sites(path)
        self.assertEqual(sites, [(2, "state:frame"), (2, "state:grid")])

    def test_reachable_raw_ui_in_a_helper_is_detected(self):
        from ui_layer_guard import callable_raw_dependencies

        self.assertEqual(
            callable_raw_dependencies(_case_reaching_raw_helper),
            [("test_ui_layer._raw_helper_for_reachability", 13, "tap")],
        )

    def test_migrated_case_has_no_reachable_raw_ui(self):
        from cases import CASES
        from ui_layer_guard import callable_raw_dependencies

        self.assertEqual(callable_raw_dependencies(CASES["M-OPT-ELEK-004"]["run"]), [])

    def test_numeric_merging_module_has_no_raw_ui(self):
        from ui_layer_guard import raw_sites

        self.assertEqual(raw_sites(BEHAVIOUR / "numeric_merging.py"), [])

    def test_numeric_note_blink_contracts_are_owned_by_contract_module(self):
        from cases import CASES
        from contract.numeric_merging import numeric_note_merge
        from ui_layer_guard import raw_sites

        case_ids = ("M-MERGE-009", "M-MERGE-010", "M-MERGE-011",
                    "M-MERGE-019", "M-MERGE-023", "M-MERGE-043", "M-MERGE-044")
        self.assertEqual(CASES["M-MERGE-009"]["run"], numeric_note_merge)
        for case_id in case_ids[1:]:
            self.assertIs(CASES[case_id]["run"].__globals__["numeric_note_merge"],
                          numeric_note_merge, case_id)
        self.assertEqual(numeric_note_merge.__module__, "contract.numeric_merging")
        self.assertIn((5, "state:grid"), raw_sites(BEHAVIOUR / "contract" / "numeric_merging.py"))

    def test_recording_stop_case_is_owned_by_its_contract_module(self):
        from cases import CASES
        from contract.recording_stop_safety import recording_stop_safety
        from ui_layer_guard import callable_raw_dependencies

        run = CASES["M-REC-PARAM-022"]["run"]
        self.assertIs(run, recording_stop_safety)
        self.assertEqual(run.__module__, "contract.recording_stop_safety")
        self.assertEqual(callable_raw_dependencies(run), [])

    def test_lock_lead_clock_matrix_cases_are_owned_by_contract_module(self):
        from cases import CASES
        from contract.lock_lead_clock_matrix import lock_lead_clock_matrix

        self.assertEqual(lock_lead_clock_matrix.__module__,
                         "contract.lock_lead_clock_matrix")
        self.assertFalse((BEHAVIOUR / "lock_lead_clock_matrix.py").exists())
        for index in range(2, 21):
            case_id = "M-SYNC-LEAD-%03d" % index
            self.assertIs(CASES[case_id]["run"].__globals__["lock_lead_clock_matrix"],
                          lock_lead_clock_matrix, case_id)

    def test_chord_contract_family_is_owned_by_contract_module(self):
        from cases import CASES

        dashboard = {"M-DASHBOARD-%03d" % index for index in range(1, 9)}
        chord = {
            case_id for case_id in CASES
            if case_id.startswith(("M-CHORDSHAPE-", "M-CHORDVEL-"))
            or case_id in dashboard
        }
        self.assertEqual(len(chord), 278)
        self.assertEqual(
            {CASES[case_id]["run"].__module__ for case_id in chord},
            {"contract.chord_shapes"},
        )

    def test_saved_range_rejection_contracts_have_one_owner(self):
        from cases import CASES
        from cases import rejected_manual_range

        case_ids = {"M-RANGE-SAVED-001", "M-RANGE-SAVED-002"}
        self.assertEqual(
            {CASES[case_id]["run"].__module__ for case_id in case_ids},
            {"contract.persisted_range_rejection"},
        )
        self.assertEqual(rejected_manual_range.__module__,
                         "contract.persisted_range_rejection")

    def test_contract_classifier_follows_helpers_and_baseline_failures(self):
        from cases import CASES
        from ui_layer_guard import callable_is_contract, classify_contract_cases

        self.assertFalse(callable_is_contract(CASES["M-PAT-001"]["run"]))
        self.assertFalse(callable_is_contract(CASES["M-OPT-ELEK-004"]["run"]))
        self.assertTrue(callable_is_contract(CASES["M-DASHBOARD-001"]["run"]))
        classified = classify_contract_cases(CASES)
        self.assertIn("M-HARMONY-REVOICE-001", classified)
        self.assertIn("M-LIFECYCLE-001", classified)
        self.assertIn("M-SAVE-002", classified)
        self.assertIn("M-SYNC-005", classified)
        self.assertIn("M-SYNC-003", classified)
        self.assertIn("M-SYNC-007", classified)
        self.assertIn("M-SYNC-010", classified)
        self.assertNotIn("M-MAP-PAGE-RETURN-001", classified)
        self.assertNotIn("M-SCALE-CACHE-001", classified)
    def test_memory_position_result_preserves_optional_channel(self):
        from unittest.mock import patch
        from ui import Ui

        class Driver:
            def __init__(self):
                self.results = []

        driver = Driver()
        ui = Ui(driver)
        with patch.object(ui, "wait_memory_position"):
            ui.expect_memory_position(1, 2)
            ui.expect_memory_position(0, 1, channel=2)

        self.assertEqual(driver.results, [
            dict(kind="memory-position", current=1, total=2, frame_matched=True),
            dict(kind="memory-position", current=0, total=1, frame_matched=True,
                 channel=2),
        ])



    def test_contract_inventory_has_a_fixed_ceiling(self):
        import json
        from cases import CASES

        value = json.loads((BEHAVIOUR / "contract_cases.json").read_text())
        self.assertEqual(sorted(value), ["cases", "ceiling"])
        self.assertIsInstance(value["cases"], list)
        self.assertLessEqual(len(value["cases"]), value["ceiling"])
        self.assertEqual(len(value["cases"]), len(set(value["cases"])))
        self.assertTrue(set(value["cases"]) <= set(CASES))
        navigation = {case_id for case_id, case in CASES.items()
                      if any(requirement.startswith("NAV-")
                             for requirement in case.get("requirements", []))}
        self.assertTrue(navigation <= set(value["cases"]))
        from ui_layer_guard import classify_contract_cases
        classified = classify_contract_cases(CASES)
        self.assertEqual(value["cases"], sorted(classified))
        self.assertEqual(value["ceiling"], 450)
        self.assertGreaterEqual(value["ceiling"], (len(classified) * 11 + 9) // 10)


if __name__ == "__main__":
    unittest.main()

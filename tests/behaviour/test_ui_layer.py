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

    def test_recording_stop_case_is_owned_by_its_contract_module(self):
        from cases import CASES
        from contract.recording_stop_safety import recording_stop_safety
        from ui_layer_guard import callable_raw_dependencies

        run = CASES["M-REC-PARAM-022"]["run"]
        self.assertIs(run, recording_stop_safety)
        self.assertEqual(run.__module__, "contract.recording_stop_safety")
        self.assertEqual(callable_raw_dependencies(run), [])

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

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
    def test_live_recording_and_panic_cases_use_semantic_inputs(self):
        """Keep case recipes on Ui verbs while preserving their existing oracles."""
        import ast

        from ui_layer_guard import _raw_sites_in_node, _tree

        source = BEHAVIOUR / "cases.py"
        tree = _tree(str(source.resolve()))
        names = {
            "live_record_placement", "recorded_note_channel_switch",
            "live_playhead_feedback", "keyboard_input_channels",
            "overlapping_keyboard_sources", "recorded_chord_release",
            "recorded_input_sources", "keyboard_pitch_range", "panic_hold",
            "panic_navigation", "panic_hold_matrix", "panic_live_note_stop",
            "panic_overlapping_holds", "panic_pending_chord",
            "muted_sparse_reverse_arp", "arp_rest_live_scale",
            "arp_empty_muted_replacement", "navigation_matrix",
        }
        functions = {node.name: node for node in tree.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue(names <= functions.keys(), names - functions.keys())
        for name in sorted(names):
            with self.subTest(function=name):
                sites = _raw_sites_in_node(functions[name])
                sites = [site for site in sites if site[1] in {
                    "tap", "key", "enc", "hold_tap", "action:grid",
                    "action:key", "action:enc",
                }]
                self.assertEqual(sites, [], name)

    def test_live_recording_uses_semantic_step_led_oracles(self):
        """Keep both 64-cell recording LED vectors behind the mapped UI layer."""
        import ast

        from ui_layer_guard import _raw_sites_in_node, _tree

        tree = _tree(str((BEHAVIOUR / "cases.py").resolve()))
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "live_record_placement")
        raw_leds = [site for site in _raw_sites_in_node(function)
                    if site[1] == "led_values"]
        semantic_leds = [node for node in ast.walk(function)
                         if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute)
                         and node.func.attr == "expect_steps"
                         and isinstance(node.func.value, ast.Name)
                         and node.func.value.id == "ui"]

        self.assertEqual(raw_leds, [])
        self.assertEqual(len(semantic_leds), 2)

    def test_migrated_arp_cases_have_no_reachable_raw_ui_dependencies(self):
        from cases import CASES
        from ui_layer_guard import callable_raw_dependencies

        for case_id in ("M-ARP-010", "M-ARP-011", "M-ARP-012",
                        "M-ARP-013", "M-ARP-014"):
            with self.subTest(case=case_id):
                self.assertEqual(
                    callable_raw_dependencies(CASES[case_id]["run"]), [], case_id
                )

    def test_hardware_driver_and_performance_modules_use_semantic_ui(self):
        from ui_layer_guard import raw_sites

        for name in ("hardware_driver.py", "hardware_performance.py"):
            with self.subTest(module=name):
                self.assertEqual(raw_sites(BEHAVIOUR / name), [])

    def test_rhythm_doctor_recipes_have_no_raw_ui_dependencies(self):
        from ui_layer_guard import raw_sites

        for name in ("rhythm_doctor.py", "rhythm_doctor_correction.py",
                     "rhythm_doctor_surface.py"):
            with self.subTest(module=name):
                self.assertEqual(raw_sites(BEHAVIOUR / name), [])

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


class DurationMigrationTests(unittest.TestCase):
    MIGRATIONS = {
        "M-PAT-001": "four_notes",
        "M-LEN-001": "next_trig_cutoff",
        "M-LEN-002": "restore_length",
        "M-LEN-003": "wrapped_length",
        "M-MIDI-001": "wrapped_length",
        "M-PAT-003": "pattern_duration_domain",
        "M-LEN-004": "pattern_duration_domain",
        "M-PAT-004": "pattern_duration_controls",
        "M-PAT-005": "live_pattern_duration",
    }

    class InputRecorder:
        def __init__(self):
            self.events = []

        def action(self, **event):
            self.events.append(("input", event))

        def elapse(self, seconds):
            self.events.append(("elapse", seconds))

        def tap(self, x, y):
            self.action(type="grid", x=x, y=y, state=1)
            self.action(type="grid", x=x, y=y, state=0)
            self.elapse(.06)

        def hold_tap(self, first, last):
            self.action(type="grid", x=first[0], y=first[1], state=1)
            self.tap(*last)
            self.action(type="grid", x=first[0], y=first[1], state=0)

    def test_duration_cases_have_no_reachable_raw_input(self):
        from cases import CASES
        from ui_layer_guard import callable_raw_dependencies

        raw_input_kinds = {
            "tap", "key", "enc", "hold_tap", "action:grid",
            "action:key", "action:enc",
        }
        for case_id in self.MIGRATIONS:
            with self.subTest(case_id=case_id):
                self.assertEqual(
                    [site for site in callable_raw_dependencies(
                        CASES[case_id]["run"]
                    ) if site[2] in raw_input_kinds], [], case_id
                )

    def test_duration_case_callables_remain_in_cases_module(self):
        import ast

        tree = ast.parse((BEHAVIOUR / "cases.py").read_text())
        defined = {
            node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertTrue(set(self.MIGRATIONS.values()) <= defined)

    def test_semantic_duration_gestures_emit_the_legacy_input_recipe(self):
        from ui import Ui

        legacy = self.InputRecorder()
        legacy.tap(5, 8)
        legacy.tap(5, 8)
        legacy.tap(4, 3)
        legacy.hold_tap((1, 4), (8, 4))
        legacy.tap(15, 7)
        legacy.hold_tap((15, 7), (2, 4))
        legacy.action(type="grid", x=1, y=4, state=1)
        legacy.elapse(1.1)
        legacy.action(type="grid", x=1, y=4, state=0)
        legacy.elapse(.06)

        semantic = self.InputRecorder()
        ui = Ui(semantic)
        ui.pattern_editor()
        ui.pattern_editor()
        ui.tap_pattern_note_position((4, 3))
        ui.set_range(1, 8)
        ui.tap_step(63)
        ui.set_range(63, 2)
        with ui.hold_control("step", 1):
            semantic.elapse(1.1)
        semantic.elapse(.06)

        self.assertEqual(semantic.events, legacy.events)

    def test_pattern_note_position_map_rejects_menu_and_out_of_grid_cells(self):
        from ui_map import control_cell

        self.assertEqual(control_cell("pattern_note_position", (15, 3)), (15, 3))
        for position in ((0, 3), (4, 8), (1.5, 2)):
            with self.subTest(position=position):
                with self.assertRaises(ValueError):
                    control_cell("pattern_note_position", position)


if __name__ == "__main__":
    unittest.main()

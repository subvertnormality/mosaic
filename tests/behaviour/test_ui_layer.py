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
    def test_inactive_note_positions_has_exact_contract_owner(self):
        from cases import CASES
        import contract.inactive_note_positions as owner

        run = CASES['M-PAT-006']['run']
        self.assertIs(run, owner.inactive_note_positions)
        self.assertEqual(run.__module__, 'contract.inactive_note_positions')

    def test_contract_duration_oracle_matches_existing_helper(self):
        import ast
        import inspect
        from cases import assert_durations as existing
        from contract.duration_assertions import assert_durations as contract

        self.assertEqual(ast.dump(ast.parse(inspect.getsource(contract))),
                         ast.dump(ast.parse(inspect.getsource(existing))))

    def test_memory_redo_encoder_lock_has_exact_contract_owner(self):
        from cases import CASES
        import contract.memory_redo_encoder_lock as owner

        run = CASES['M-MEMORY-009']['run']
        self.assertIs(run, owner.memory_redo_encoder_lock)
        self.assertEqual(run.__module__, 'contract.memory_redo_encoder_lock')

    def test_external_sync_cases_have_exact_contract_owners(self):
        from importlib import import_module
        from cases import CASES

        owners = {
            'M-SYNC-005': 'external_started_handoff',
            'M-SYNC-007': 'acquisition_stop',
            'M-SYNC-010': 'master_lifecycle',
        }
        for case_id, name in owners.items():
            with self.subTest(case=case_id):
                module = import_module('contract.' + name)
                run = CASES[case_id]['run']
                self.assertIs(run, getattr(module, name))
                self.assertEqual(run.__module__, module.__name__)

    def test_cold_lifecycle_has_exact_contract_owner(self):
        from cases import CASES
        import contract.lifecycle_cycles as owner

        run = CASES['M-LIFECYCLE-001']['run']
        self.assertIs(run, owner.lifecycle_cycles)
        self.assertEqual(run.__module__, 'contract.lifecycle_cycles')

    def test_unreadable_device_config_has_exact_contract_owner(self):
        from cases import CASES
        import contract.unreadable_device_config as owner

        run = CASES['M-SETUP-UNREADABLE-CONFIG-001']['run']
        self.assertIs(run, owner.unreadable_device_config)
        self.assertEqual(run.__module__, 'contract.unreadable_device_config')

    def test_idle_autosave_has_exact_contract_owner(self):
        from cases import CASES
        import contract.autosave_idle as owner

        run = CASES['M-SAVE-002']['run']
        self.assertIs(run, owner.autosave_idle_lifecycle)
        self.assertEqual(run.__module__, 'contract.autosave_idle')

    def test_navigation_matrix_has_exact_contract_owner(self):
        from cases import CASES
        import contract.navigation_matrix as owner

        run = CASES['M-NAV-001']['run']
        self.assertIs(run, owner.navigation_matrix)
        self.assertEqual(run.__module__, 'contract.navigation_matrix')

    def test_mosaic_options_case_callers_use_semantic_ui_verb(self):
        """Keep native-menu seeks out of the six non-contract case bodies."""
        import ast

        tree = ast.parse((BEHAVIOUR / "cases.py").read_text())
        names = {
            "repeated_pattern_reset_policy", "fractional_clock_continuity",
            "song_transition_reset_policy", "inactive_shuffle_transition",
            "strum_reset_continuity", "arp_basic_timing",
        }
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual({node.name for node in functions}, names)
        calls = [node for function in functions for node in ast.walk(function)
                 if isinstance(node, ast.Call)]
        raw_calls = [node for node in calls
                     if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name)
                     and node.func.id == "set_mosaic_options"]
        semantic_calls = [node for node in calls
                          if isinstance(node, ast.Call)
                          and isinstance(node.func, ast.Attribute)
                          and node.func.attr == "set_mosaic_options"
                          and isinstance(node.func.value, ast.Attribute)
                          and node.func.value.attr == "ui"]

        self.assertEqual(raw_calls, [])
        self.assertEqual(len(semantic_calls), 6)

    def test_live_playhead_cases_have_exact_contract_owners(self):
        from cases import CASES
        from unittest.mock import patch, sentinel
        import contract.playhead_feedback as owner

        self.assertIs(CASES['M-UI-001']['run'], owner.live_playhead_feedback)
        run = CASES['M-UI-002']['run']
        self.assertIs(run, owner.live_playhead_feedback_twice_rate)
        for case_id in ('M-UI-001', 'M-UI-002'):
            self.assertEqual(CASES[case_id]['run'].__module__,
                             'contract.playhead_feedback')
        self.assertIsNone(run.__closure__)
        with patch.object(owner, 'live_playhead_feedback',
                          return_value=sentinel.result) as helper:
            self.assertIs(run(sentinel.driver), sentinel.result)
        helper.assert_called_once_with(sentinel.driver, clock_delta=3)

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
        contract_trees = [_tree(str((BEHAVIOUR / "contract" / name).resolve()))
                          for name in ("playhead_feedback.py", "navigation_matrix.py")]
        functions = {node.name: node for owner in (tree, *contract_trees)
                     for node in owner.body
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

    def test_numeric_note_merge_cases_have_named_contract_owners(self):
        from unittest.mock import patch

        from cases import CASES
        from contract import numeric_merging as contract_numeric
        import numeric_merging
        from ui_layer_guard import classify_contract_cases, raw_sites

        cases = {
            "M-MERGE-010": ("numeric_note_merge_exclude_foreign_velocity", (True, False, False, False), {}),
            "M-MERGE-011": ("numeric_note_merge_pentatonic_velocity", (True, True, False, False), {}),
            "M-MERGE-019": ("numeric_note_merge_all_scales", (True, False, True, False), {}),
            "M-MERGE-023": ("numeric_note_merge_all_pentatonic_scales", (True, True, True, False), {}),
            "M-MERGE-043": ("numeric_note_merge_harmony", (True, False, False, True), {}),
            "M-MERGE-044": ("numeric_note_merge_harmony_pentatonic", (True, True, False, True), {}),
        }
        self.assertIn("M-MERGE-009", classify_contract_cases(CASES))
        for case_id, (name, args, kwargs) in cases.items():
            with self.subTest(case=case_id):
                owner = getattr(contract_numeric, name)
                run = CASES[case_id]["run"]
                self.assertIs(run, owner)
                self.assertEqual(run.__module__, "contract.numeric_merging")
                self.assertIsNone(run.__closure__)
                self.assertIn(case_id, classify_contract_cases(CASES))
                driver = object()
                with patch.object(numeric_merging, "numeric_note_merge") as called:
                    run(driver)
                called.assert_called_once_with(
                    driver, *args, **kwargs,
                    blink_observer=contract_numeric._expect_selected_pattern_top_note_blink,
                )
        self.assertEqual(contract_numeric.numeric_note_merge.__module__,
                         "contract.numeric_merging")
        self.assertIn((5, "state:grid"),
                      raw_sites(BEHAVIOUR / "contract" / "numeric_merging.py"))

    def test_recording_stop_case_is_owned_by_its_contract_module(self):
        from cases import CASES
        from contract.recording_stop_safety import recording_stop_safety
        from ui_layer_guard import callable_raw_dependencies

        run = CASES["M-REC-PARAM-022"]["run"]
        self.assertIs(run, recording_stop_safety)
        self.assertEqual(run.__module__, "contract.recording_stop_safety")
        self.assertEqual(callable_raw_dependencies(run), [])

    def test_persisted_recording_case_has_named_contract_owner(self):
        from unittest.mock import patch
        from cases import CASES
        from contract import recording_lock_song as contract_recording
        from ui_layer_guard import classify_contract_cases

        run = CASES["M-PERSIST-COMBINED-001"]["run"]
        owner = getattr(contract_recording, "recording_lock_song_persisted", None)
        self.assertIs(run, owner)
        self.assertEqual(run.__module__, "contract.recording_lock_song")
        self.assertIsNone(run.__closure__)
        self.assertIn("M-PERSIST-COMBINED-001", classify_contract_cases(CASES))
        driver = object()
        with patch.object(contract_recording, "recording_lock_song") as called:
            run(driver)
        called.assert_called_once_with(driver, persist=True)

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

    def test_range_rejection_registry_wrappers_preserve_owner_and_recipe(self):
        from unittest.mock import patch
        from cases import CASES
        from contract import range_rejection
        from ui_layer_guard import callable_is_contract, classify_contract_cases

        expected = {
            "M-RANGE-REJECT-001": ("range_reject_001",
                                   range_rejection.rejected_range, (False,)),
            "M-RANGE-REJECT-002": ("range_reject_002",
                                   range_rejection.rejected_range, (True,)),
            "M-RANGE-REJECT-003": ("range_reject_003",
                                   range_rejection.rejected_range_while_playing, (False,)),
            "M-RANGE-REJECT-004": ("range_reject_004",
                                   range_rejection.rejected_range_while_playing, (True,)),
        }
        self.assertTrue(set(expected) <= classify_contract_cases(CASES))
        for case_id, (wrapper_name, helper, args) in expected.items():
            run = CASES[case_id]["run"]
            with self.subTest(case=case_id):
                self.assertEqual(run.__module__, "contract.range_rejection")
                self.assertEqual(run.__name__, wrapper_name)
                self.assertIs(run, getattr(range_rejection, wrapper_name))
                self.assertIsNone(run.__closure__)
                self.assertIs(run.__globals__[helper.__name__], helper)
                self.assertTrue(callable_is_contract(run))
                driver = object()
                sentinel = object()
                with patch.object(range_rejection, helper.__name__,
                                  return_value=sentinel) as called:
                    self.assertIs(run(driver), sentinel)
                called.assert_called_once_with(driver, *args)

    def test_saved_range_rejection_contracts_have_one_owner(self):
        from cases import CASES
        from cases import rejected_manual_range
        import contract.persisted_range_rejection as owner
        from unittest.mock import patch, sentinel

        case_ids = {"M-RANGE-SAVED-001", "M-RANGE-SAVED-002"}
        self.assertEqual(
            {CASES[case_id]["run"].__module__ for case_id in case_ids},
            {"contract.persisted_range_rejection"},
        )
        self.assertEqual(rejected_manual_range.__module__,
                         "contract.persisted_range_rejection")
        for case_id, name, recovery in (
            ('M-RANGE-SAVED-003', 'rejected_manual_range_save', 'save'),
            ('M-RANGE-SAVED-004', 'rejected_manual_range_new', 'new'),
        ):
            with self.subTest(case_id=case_id):
                run = CASES[case_id]['run']
                self.assertIs(run, getattr(owner, name))
                self.assertEqual(run.__module__, 'contract.persisted_range_rejection')
                self.assertIsNone(run.__closure__)
                with patch.object(owner, 'rejected_manual_range',
                                  return_value=sentinel.result) as helper:
                    self.assertIs(run(sentinel.driver), sentinel.result)
                helper.assert_called_once_with(sentinel.driver, recovery=recovery)

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



    def test_memory_navigation_contract_callable_ownership(self):
        from cases import CASES
        from ui_layer_guard import classify_contract_cases

        case_id = "M-MEMORY-001"
        run = CASES[case_id]["run"]
        source = Path(run.__code__.co_filename).resolve()
        contract_root = (BEHAVIOUR / "contract").resolve()

        self.assertEqual(case_id in classify_contract_cases(CASES),
                         source.parent == contract_root)


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


class FractionalResultEvidenceTests(unittest.TestCase):
    def test_controlled_input_identity_drops_only_volatile_coordinates(self):
        from fractional_deadlines import result_input_evidence

        evidence = {
            "action_id": "run-specific-action",
            "native_sequence": 1536,
            "origin_ns": 1_648_608_152_219,
            "applied_ns": 1_648_610_307_010,
            "input_to_applied_ns": 2_154_791,
            "boundary": "backend-input-submission",
            "verified": True,
        }
        original = evidence.copy()
        self.assertEqual(result_input_evidence(evidence, controlled=True), {
            "native_sequence": 1536,
            "boundary": "backend-input-submission",
            "verified": True,
        })
        self.assertEqual(evidence, original)

    def test_real_time_input_evidence_is_returned_unchanged(self):
        from fractional_deadlines import result_input_evidence

        evidence = {"action_id": "wall-clock-id", "native_sequence": 12,
                    "origin_ns": 100, "applied_ns": 130,
                    "input_to_applied_ns": 30,
                    "boundary": "backend-input-submission"}
        self.assertIs(result_input_evidence(evidence, controlled=False), evidence)


if __name__ == "__main__":
    unittest.main()

import sys
import ast
import base64
import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path


BEHAVIOUR = Path(__file__).resolve().parent
if str(BEHAVIOUR) not in sys.path:
    sys.path.insert(0, str(BEHAVIOUR))


class FakeDriver:
    def __init__(self, states=None, clock_mode="controlled-experimental"):
        self.clock_mode = clock_mode
        self.calls = []
        self.results = []
        self._states = iter(states or [])

    def action(self, **value):
        self.calls.append(("action", value))
        return {"native": "ack"}

    def elapse(self, seconds):
        self.calls.append(("elapse", seconds))

    def tap(self, x, y):
        self.calls.append(("tap", x, y))

    def key(self, n):
        self.calls.append(("key", n))

    def enc(self, n, detents):
        self.calls.append(("enc", n, detents))

    def wait(self, predicate):
        self.calls.append(("wait",))
        state = next(self._states)
        if not predicate(state):
            raise AssertionError("predicate did not match")
        return state

    def led_values(self, cells, expected):
        self.calls.append(("led_values", cells, expected))

    def hold_tap(self, first, last):
        self.calls.append(("hold_tap", first, last))

    def snapshot(self):
        self.calls.append(("snapshot",))
        return next(self._states)

    def wait(self, predicate):
        self.calls.append(("wait",))
        state = next(self._states)
        if not predicate(state):
            raise AssertionError("wait predicate rejected staged state")
        return state


class UiMapTests(unittest.TestCase):
    def test_euclidean_dense_fill_probes_bottom_right_boundary(self):
        from types import SimpleNamespace
        from cases import euclidean_workflow

        probes = []

        class UiProbe:
            def configure(self):
                pass

            def set_range(self, first, last):
                pass

            def tap_control(self, control):
                pass

            def expect_steps(self, levels):
                probes.append(levels)

        case = SimpleNamespace(ui=UiProbe(), playback=lambda *a, **k: [],
                               results=[])
        euclidean_workflow(case)
        self.assertIn({1: "dark", 4: "dark", 5: "selected",
                       64: "selected"}, probes)
        self.assertEqual(list(probes[0]), list(range(1, 65)))
        self.assertEqual(list(probes[1]), list(range(1, 65)))
        self.assertIn({step: "selected" if step <= 4 else "off"
                       for step in range(1, 65)}, probes)

    def test_algorithm_workflow_controls_resolve_to_raw_baseline_cells(self):
        from ui import Ui
        from ui_map import control_cell

        expected = {
            "tresillo_tool": (13, 2),
            "drum_pattern_two": (12, 2),
            "rhythm_fill_minimum": (2, 2),
            "rhythm_fill_maximum": (10, 2),
            "rhythm_factor_minimum": (2, 3),
            "rhythm_factor_maximum": (10, 3),
            "numeric_prime_one": (15, 2),
        }
        driver = FakeDriver()
        ui = Ui(driver)
        expected_taps = []
        for control, cell in expected.items():
            with self.subTest(control=control):
                self.assertEqual(control_cell(control), cell)
                ui.tap_control(control)
                expected_taps.append(("tap", *cell))
        for bank in range(1, 6):
            with self.subTest(control="drum_bank", bank=bank):
                cell = (11 + bank, 3)
                self.assertEqual(control_cell("drum_bank", bank), cell)
                ui.tap_control("drum_bank", bank)
                expected_taps.append(("tap", *cell))
        for mask in range(1, 5):
            with self.subTest(control="numeric_mask", mask=mask):
                cell = (11 + mask, 3)
                self.assertEqual(control_cell("numeric_mask", mask), cell)
                ui.tap_control("numeric_mask", mask)
                expected_taps.append(("tap", *cell))
        self.assertEqual(driver.calls, expected_taps)

    def test_m_alg_001_to_004_literal_tap_controls_are_mapped(self):
        from ui_map import control_cell

        source = ast.parse((BEHAVIOUR / "cases.py").read_text())
        names = {
            "euclidean_workflow", "tresillo_setup", "tresillo_rhythm",
            "tresillo_multipliers", "tresillo_drum_boundary",
            "rhythm_bank_workflow",
        }
        functions = {node.name: node for node in source.body
                     if isinstance(node, ast.FunctionDef)}
        self.assertTrue(names <= functions.keys(), names - functions.keys())
        controls = set()
        for name in names:
            function = functions[name]
            literal_iterables = {
                node.target.id: tuple(item.value for item in node.iter.elts)
                for node in ast.walk(function)
                if isinstance(node, ast.For)
                and isinstance(node.target, ast.Name)
                and isinstance(node.iter, ast.Tuple)
                and all(isinstance(item, ast.Constant)
                        and isinstance(item.value, str) for item in node.iter.elts)
            }
            for node in ast.walk(function):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "tap_control"
                        and node.args):
                    continue
                control = node.args[0]
                if isinstance(control, ast.Constant) and isinstance(control.value, str):
                    controls.add(control.value)
                elif isinstance(control, ast.Name):
                    self.assertIn(control.id, literal_iterables, name)
                    controls.update(literal_iterables[control.id])

        for control in sorted(controls):
            with self.subTest(control=control):
                if control == "drum_bank":
                    for index in range(1, 6):
                        control_cell(control, index)
                elif control == "numeric_mask":
                    for index in range(1, 5):
                        control_cell(control, index)
                elif control == "pattern_note":
                    control_cell(control, (1, 1))
                else:
                    control_cell(control)

    def test_pattern_note_mapping_covers_authored_rows_one_through_seven(self):
        from ui_map import control_cell

        for step in range(1, 17):
            for row in range(1, 8):
                with self.subTest(step=step, row=row):
                    self.assertEqual(control_cell("pattern_note", (step, row)),
                                     (step, row))
        for invalid in ((0, 1), (17, 1), (1, 0), (1, 8),
                        (True, 1), (1, 1.0), (1,), None):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    control_cell("pattern_note", invalid)

    def test_rhythm_bank_authored_note_recipe_resolves_all_sixteen_source_cells(self):
        from types import SimpleNamespace
        from cases import rhythm_bank_workflow
        from ui import Ui

        class StopAfterNoteEntry(Exception):
            pass

        driver = FakeDriver()
        ui = Ui(driver)
        ui.configure = lambda: None
        ui.set_range = lambda *args: None
        original_tap_control = ui.tap_control
        note_taps = 0

        def stop_after_notes(control, index=None):
            nonlocal note_taps
            if control == "channel_editor" and note_taps == 16:
                raise StopAfterNoteEntry
            result = original_tap_control(control, index)
            if control == "pattern_note":
                note_taps += 1
            return result

        ui.tap_control = stop_after_notes
        with self.assertRaises(StopAfterNoteEntry):
            rhythm_bank_workflow(SimpleNamespace(ui=ui))

        expected = [("tap", 5, 8)]
        expected.extend(("tap", step, 4) for step in range(1, 5))
        expected.append(("tap", 5, 8))
        expected.extend(("tap", step, 7 - ((step - 1) % 7))
                        for step in range(1, 17))
        self.assertEqual(driver.calls, expected)

    def test_tresillo_setup_emits_exact_key_hold_note_tap_release_recipe(self):
        from types import SimpleNamespace
        from cases import tresillo_setup
        from ui import Ui

        class StopAfterNoteEntry(Exception):
            pass

        driver = FakeDriver()
        ui = Ui(driver)
        ui.configure = lambda: None
        original_tap_control = ui.tap_control
        note_taps = 0

        def stop_after_notes(control, index=None):
            nonlocal note_taps
            if control == "channel_editor" and note_taps == 16:
                raise StopAfterNoteEntry
            result = original_tap_control(control, index)
            if control == "pattern_note":
                note_taps += 1
            return result

        ui.tap_control = stop_after_notes
        with self.assertRaises(StopAfterNoteEntry):
            tresillo_setup(SimpleNamespace(ui=ui, elapse=driver.elapse))

        expected = [("tap", 5, 8)]
        expected.extend(("tap", step, 4) for step in range(1, 5))
        expected.append(("tap", 5, 8))
        for step in range(1, 17):
            expected.extend([
                ("action", {"type": "key", "n": 1, "state": 1}),
                ("elapse", .3),
                ("tap", step, 7 - ((step - 1) % 6)),
                ("action", {"type": "key", "n": 1, "state": 0}),
            ])
        self.assertEqual(driver.calls, expected)

    def test_trigger_editor_confirmation_header_names_its_own_live_screen(self):
        """P02 (Trig options) is its own live screen, distinct from P01 (Pattern trig)."""
        from ui import Ui
        from ui_map import HEADERS, header_parts, header_text

        self.assertEqual(header_text("trigger_editor_confirmation"),
                         "TRIG OPTIONS CH01")
        self.assertEqual(HEADERS["trigger_editor_confirmation"],
                         {"title": "TRIG OPTIONS", "layout": "focused", "scope": "channel"})
        self.assertEqual(header_parts("trigger_editor_confirmation", channel=1),
                         ("TRIG OPTIONS", "CH01", "focused"))
        self.assertEqual(header_parts("trigger_editor", channel=1),
                         ("PATTERN TRIG", "CH01", "pattern64"))
        state = {"frame": {"pixels_base64": "ignored"}}
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.live_header_matches", return_value=True) as live:
            Ui(driver).expect_header("trigger_editor_confirmation")
        live.assert_called_once_with(state, "TRIG OPTIONS", "CH01", "focused")
        self.assertEqual(driver.results, [dict(
            kind="screen-header", expected="TRIG OPTIONS CH01", matched=True)])

    def test_euclidean_workflow_controls_match_raw_baseline_cells(self):
        """Every semantic Euclidean tap retains the original authored cell."""
        from ui import Ui
        from ui_map import control_cell

        expected = {
            "pattern_note_c": ((None,), (5, 3)),
            "pattern_note_d": ((None,), (6, 2)),
            "pattern_note_e": ((None,), (7, 1)),
            "pattern_note_f": ((None,), (8, 6)),
            "channel_editor": ((None,), (3, 8)),
            "pattern_editor": ((None,), (5, 8)),
            "euclidean_tool": ((None,), (14, 2)),
            "euclidean_fill_minimum": ((None,), (2, 2)),
            "euclidean_fill_maximum": ((None,), (10, 2)),
            "euclidean_rotation_minimum": ((None,), (2, 3)),
            "euclidean_rotation_maximum": ((None,), (10, 3)),
            "paint": ((None,), (16, 8)),
            "cancel": ((None,), (14, 8)),
            "shift_right": ((None,), (12, 8)),
            "shift_left": ((None,), (10, 8)),
            "shift_reset": ((None,), (11, 8)),
            "euclidean_fill_boundary": ((None,), (9, 2)),
        }

        source = ast.parse((BEHAVIOUR / "cases.py").read_text())
        workflow = next(node for node in source.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "euclidean_workflow")
        literal_iterables = {}
        for node in ast.walk(workflow):
            if (isinstance(node, ast.For) and isinstance(node.target, ast.Name)
                    and isinstance(node.iter, ast.Tuple)
                    and all(isinstance(item, ast.Constant)
                            and isinstance(item.value, str) for item in node.iter.elts)):
                literal_iterables[node.target.id] = tuple(
                    item.value for item in node.iter.elts)
        calls = []
        for node in ast.walk(workflow):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "tap_control"
                    and isinstance(node.func.value, ast.Attribute)
                    and node.func.value.attr == "ui"
                    and isinstance(node.func.value.value, ast.Name)
                    and node.func.value.value.id == "c"):
                self.assertEqual(len(node.args), 1,
                                 "workflow tap_control must not hide a dynamic index")
                argument = node.args[0]
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    calls.append(argument.value)
                else:
                    self.assertIsInstance(argument, ast.Name)
                    self.assertIn(argument.id, literal_iterables)
                    calls.extend(literal_iterables[argument.id])

        self.assertEqual(set(calls), set(expected))
        for control, ((index,), baseline_cell) in expected.items():
            with self.subTest(control=control):
                self.assertEqual(control_cell(control, index), baseline_cell)
                driver = FakeDriver()
                Ui(driver).tap_control(control, index)
                self.assertEqual(driver.calls, [("tap", *baseline_cell)])

    def test_pattern_note_pitch_keys_preserve_authored_grid_cells(self):
        from ui_map import PATTERN_NOTE_PITCHES, control_cell

        self.assertEqual(PATTERN_NOTE_PITCHES, {
            "pattern_note_c": (5, 3),
            "pattern_note_d": (6, 2),
            "pattern_note_e": (7, 1),
            "pattern_note_f": (8, 6),
        })
        for key, cell in PATTERN_NOTE_PITCHES.items():
            with self.subTest(key=key):
                self.assertEqual(control_cell(key), cell)
                with self.assertRaises(ValueError):
                    control_cell(key, 1)

    def test_macro_clock_cases_use_semantic_ui_verbs(self):
        source = (BEHAVIOUR / "cases.py").read_text()
        module = ast.parse(source)
        names = {
            "autosave_restart", "route_fixed_note", "toolkit_parameter_group",
            "macro_route_clear", "held_macro_rebind", "pulse_lfo", "pulse_lfo_real_time",
            "phrase_timing",
            "restart_phase_edges", "midi_clock_transport", "live_clock_handoff",
            "reverse_live_clock_handoff",
        }
        functions = [node for node in module.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        self.assertEqual({node.name for node in functions}, names)
        raw_methods = {"key", "enc", "tap", "hold_tap", "led_values"}
        raw_calls = []
        raw_action_types = []
        for function in functions:
            for node in ast.walk(function):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "c"):
                    if node.func.attr in raw_methods:
                        raw_calls.append("%s:%d c.%s" %
                                         (function.name, node.lineno, node.func.attr))
                    if node.func.attr == "action" and node.args == []:
                        for keyword in node.keywords:
                            if keyword.arg == "type" and isinstance(keyword.value, ast.Constant):
                                if keyword.value.value in {"grid", "enc", "key"}:
                                    raw_action_types.append("%s:%d %s" %
                                                            (function.name, node.lineno,
                                                             keyword.value.value))
        self.assertEqual(raw_calls, [])
        self.assertEqual(raw_action_types, [])

    def test_modulation_source_route_preserves_native_recipe_and_maps(self):
        from ui import Ui

        roots = [{"id": "other", "name": "OTHER"},
                 {"id": "midi_device_params_group_channel_1", "name": "Channel 1"}]
        driver = FakeDriver(states=[{"diagnostics": {"parameter_roots": roots}}])
        ui = Ui(driver)
        ui.expect_native_menu_label = lambda key: driver.calls.append(("menu-label-key", key))
        ui.expect_menu_label = lambda label: driver.calls.append(("menu-label", label))
        ui.expect_menu_value = lambda value: driver.calls.append(("menu-value", value))
        for source, offset, label_key in (("lfo_1", 4, "mod_source_lfo_1"),
                                          ("macro_1", 12, "mod_macro_1")):
            driver.calls.clear()
            driver._states = iter([{"diagnostics": {"parameter_roots": roots}}])
            ui.route_fixed_note_from_modulation_source(source)
            self.assertEqual(driver.calls, [
                ("key", 1), ("enc", 2, 1), ("key", 3),
                ("menu-label-key", "mod_devices_root"), ("enc", 2, 2),
                ("menu-label-key", "mod_mods_root"), ("key", 3),
                ("menu-label-key", "mod_matrix_root"), ("key", 3),
                ("menu-label-key", "levels_root"), ("snapshot",), ("enc", 2, 1),
                ("key", 3), ("menu-label-key", "mod_fixed_note"), ("key", 3),
                ("menu-label-key", "mod_source_rhythm_1"), ("enc", 2, offset),
                ("menu-label-key", label_key), ("enc", 3, 100),
                ("menu-value", "1.00"),
            ])

    def test_native_clock_group_selection_keeps_observed_root_position(self):
        from ui import Ui

        driver = FakeDriver(states=[{"diagnostics": {"parameter_roots": [
            {"name": "OTHER"}, {"name": "CLOCK"},
        ]}}])
        ui = Ui(driver)
        ui.expect_native_menu_label = lambda key: driver.calls.append(("menu-label-key", key))
        ui.select_native_parameter_group("clock")
        self.assertEqual(driver.calls, [
            ("menu-label-key", "levels_root"), ("snapshot",), ("enc", 2, 1),
            ("key", 3), ("menu-label-key", "clock_source"),
        ])

    def test_native_levels_entry_recipes_preserve_each_callers_origin(self):
        from types import SimpleNamespace
        from cases import toolkit_parameter_group
        from ui import Ui

        roots = [{"name": "OTHER"}, {"name": "macro 1"}]
        driver = FakeDriver(states=[{"diagnostics": {"parameter_roots": roots}}])
        ui = Ui(driver)
        ui.expect_native_menu_label = lambda key: driver.calls.append(
            ("menu-label-key", key))
        toolkit_parameter_group(SimpleNamespace(ui=ui), "macro_1")
        self.assertEqual(driver.calls, [
            ("enc", 1, 4), ("key", 3), ("menu-label-key", "levels_root"),
            ("snapshot",), ("enc", 2, 1), ("key", 3),
        ])

        # Clock callers start from a different screen and retain the native
        # recipe that includes K1. The helper must continue to emit that order.
        driver = FakeDriver()
        ui = Ui(driver)
        ui.enter_native_levels_menu()
        self.assertEqual(driver.calls, [("key", 1), ("enc", 1, 4), ("key", 3)])

        source = ast.parse((BEHAVIOUR / "cases.py").read_text())
        functions = {node.name: node for node in source.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name in {"midi_clock_transport", "live_clock_handoff"}}
        self.assertEqual(set(functions), {"midi_clock_transport", "live_clock_handoff"})
        for name, function in functions.items():
            calls = sorted((node for node in ast.walk(function)
                            if isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Attribute)),
                           key=lambda node: (node.lineno, node.col_offset))
            attrs = [call.func.attr for call in calls]
            with self.subTest(caller=name):
                self.assertIn("enter_native_levels_menu", attrs)
                self.assertIn("select_native_parameter_group", attrs)
                self.assertLess(attrs.index("enter_native_levels_menu"),
                                attrs.index("select_native_parameter_group"))

    def test_arp_and_spread_cases_use_semantic_ui_verbs_and_parameter_keys(self):
        from ui_layer_guard import _raw_sites_in_node
        from ui_map import TRIG_PARAMETERS

        source = (BEHAVIOUR / "cases.py").read_text()
        module = ast.parse(source)
        owners = (
            module,
            ast.parse((BEHAVIOUR / "contract" / "strum_reset_continuity.py").read_text()),
            ast.parse((BEHAVIOUR / "contract" / "parameter_divisions.py").read_text()),
        )
        names = {
            "assign_trig_parameter", "strum_reset_continuity", "arp_basic_timing",
            "parameter_division_bounds", "spread_acceleration_contract",
            "arp_empty_masks", "arp_rest_slots", "fractional_spread_contract",
            "minimum_swung_gap_contract",
        }
        functions = {node.name: node for owner in owners for node in owner.body
                     if isinstance(node, ast.FunctionDef) and node.name in names}
        self.assertEqual(set(functions), names)
        raw_sites = {
            name: [site for site in _raw_sites_in_node(node)
                   if not site[1].startswith("state:")]
            for name, node in functions.items()
        }
        self.assertEqual({name: sites for name, sites in raw_sites.items() if sites}, {})
        self.assertEqual({name for name, node in functions.items()
                          if any(site[1] == "state:frame"
                                 for site in _raw_sites_in_node(node))},
                         {"strum_reset_continuity", "parameter_division_bounds"})

        forbidden_labels = {
            "Chord Note Arpeggio", "Chord Note Strum", "Chord Spread",
            "Chord Accel Mod", "Mute Chord Root",
        }
        labels = {node.value for node in ast.walk(module)
                  if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        for name in names - {"assign_trig_parameter"}:
            node_labels = {node.value for node in ast.walk(functions[name])
                           if isinstance(node, ast.Constant)
                           and isinstance(node.value, str)}
            self.assertFalse(node_labels & forbidden_labels, name)
        self.assertEqual({key: TRIG_PARAMETERS[key] for key in (
            "chord_note_arpeggio", "chord_note_strum", "chord_spread",
            "chord_accel_mod", "mute_chord_root",
        )}, {
            "chord_note_arpeggio": "Chord Note Arpeggio",
            "chord_note_strum": "Chord Note Strum",
            "chord_spread": "Chord Spread",
            "chord_accel_mod": "Chord Accel Mod",
            "mute_chord_root": "Mute Chord Root",
        })

    def test_pattern_grid_viewer_has_exact_contract_owner(self):
        from cases import CASES
        from contract.grid_viewer import pattern_grid_viewer

        self.assertIs(CASES['M-VIEW-001']['run'], pattern_grid_viewer)
        self.assertEqual(pattern_grid_viewer.__module__, 'contract.grid_viewer')
        self.assertIsNone(pattern_grid_viewer.__closure__)

    def test_parameter_division_bounds_have_named_contract_owners(self):
        from cases import CASES
        from unittest.mock import patch, sentinel
        import contract.parameter_divisions as owner

        for case_id, name, parameter in (
            ('M-PARAM-001', 'chord_note_strum_divisions', 'chord_note_strum'),
            ('M-PARAM-002', 'chord_note_arpeggio_divisions', 'chord_note_arpeggio'),
            ('M-PARAM-003', 'chord_spread_divisions', 'chord_spread'),
        ):
            with self.subTest(case_id=case_id):
                run = CASES[case_id]['run']
                self.assertIs(run, getattr(owner, name))
                self.assertEqual(run.__module__, 'contract.parameter_divisions')
                self.assertIsNone(run.__closure__)
                with patch.object(owner, 'parameter_division_bounds',
                                  return_value=sentinel.result) as helper:
                    self.assertIs(run(sentinel.driver), sentinel.result)
                helper.assert_called_once_with(sentinel.driver, parameter)

    def test_editor_range_and_selector_cases_use_semantic_inputs(self):
        source = (BEHAVIOUR / "cases.py").read_text()
        module = ast.parse(source)
        contract_modules = (
            ast.parse((BEHAVIOUR / "contract" / "grid_viewer.py").read_text()),
            ast.parse((BEHAVIOUR / "contract" / "inactive_note_positions.py").read_text()),
        )
        names = {
            "editor_shift_tap", "editor_range_hold", "editor_note_ranges",
            "editor_velocity_ranges", "editor_step_groups", "note_pattern_selectors",
            "editor_hold_boundaries", "pattern_grid_viewer", "inactive_note_priority",
            "priority_field_isolation", "inactive_note_positions", "all_note_priorities",
        }
        raw_methods = {"tap", "action", "hold_tap", "enc", "configure"}
        functions = [node for owner in (module, *contract_modules)
                     for node in owner.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and node.name in names]
        self.assertEqual({node.name for node in functions}, names)
        raw_calls = []
        for function in functions:
            for node in ast.walk(function):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "c" and node.func.attr in raw_methods):
                    raw_calls.append("%s:%d c.%s" %
                                     (function.name, node.lineno, node.func.attr))
        self.assertEqual(raw_calls, [])

    def test_pattern_group_selectors_have_semantic_names(self):
        from ui_map import control_cell

        self.assertEqual(
            [control_cell("pattern_group", index) for index in range(1, 5)],
            [(9, 8), (10, 8), (11, 8), (12, 8)],
        )
        self.assertEqual(control_cell("pattern_velocity_range_down"), (16, 8))
        self.assertEqual(control_cell("pattern_velocity_range_reset"), (15, 8))
        for invalid in (0, 5, True, 1.0):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                control_cell("pattern_group", invalid)

    def test_rhythm_doctor_controls_have_distinct_semantic_names(self):
        from ui_map import control_cell

        self.assertEqual(control_cell("legacy_drum_algorithm"), (12, 2))
        self.assertEqual(control_cell("legacy_tresillo_algorithm"), (13, 2))
        self.assertEqual(control_cell("legacy_euclidean_algorithm"), (14, 2))
        self.assertEqual(control_cell("legacy_numeric_repetitor_algorithm"), (15, 2))
        self.assertEqual(control_cell("algorithm"), (16, 2))
        self.assertEqual(control_cell("reserved_lane"), (2, 2))
        self.assertEqual(control_cell("lane_bd"), (3, 2))
        self.assertEqual(control_cell("lane_sd"), (4, 2))
        self.assertEqual(control_cell("lane_cym"), (5, 2))
        self.assertEqual(control_cell("withdrawn_lane_bass"), (6, 2))
        self.assertEqual(control_cell("retired_lane"), (7, 2))
        self.assertEqual(control_cell("capture"), (1, 2))
        self.assertEqual(control_cell("phrase_left"), (10, 8))
        self.assertEqual(control_cell("phrase_centre"), (11, 8))
        self.assertEqual(control_cell("phrase_right"), (12, 8))
        with self.assertRaises(ValueError):
            control_cell("lane_cym", 1)

    def test_channel_page_order_is_current_1_4_surface(self):
        from ui_map import CHANNEL_PAGES

        self.assertEqual(
            list(CHANNEL_PAGES),
            ["masks", "trig_locks", "memory", "clock_mods", "midi_config",
             "note_dashboard", "merge_shape", "harmony"],
        )

    def test_patch_menu_surface_has_stable_keys(self):
        from ui_map import NATIVE_MENU, PATCH_PARAMETERS, PATCH_PARAMETER_VALUES

        self.assertEqual(NATIVE_MENU["patch_control_default"], "CC 1")
        self.assertEqual(NATIVE_MENU["patch_control_configured"], "Control 1")
        self.assertEqual(PATCH_PARAMETERS["nrpn14"]["label"], "NRPN14")
        self.assertEqual(PATCH_PARAMETER_VALUES["off"], "X")

    def test_trig_parameter_surface_has_stable_keys(self):
        from ui_map import TRIG_PARAMETERS

        self.assertEqual(TRIG_PARAMETERS, {
            "stored_patch_cc1": "CC 1",
            **{"stored_patch_cc%d" % slot: "CC %d" % slot for slot in range(2, 11)},
            "stored_patch_control1": "Control 1",
            "stored_patch_nrpn14": "NRPN14",
            "configured_control_1": "Control 1",
            "ns0": "NS0",
            "ns6": "NS6",
            "fixed_note": "Fixed Note",
            "quantised_fixed_note": "Quantised Fixed Note",
            "trig_probability": "Trig Probability",
            "chord_note_arpeggio": "Chord Note Arpeggio",
            "chord_note_strum": "Chord Note Strum",
            "chord_spread": "Chord Spread",
            "chord_accel_mod": "Chord Accel Mod",
            "mute_chord_root": "Mute Chord Root",
            "chord_pattern": "Chord Pattern",
            "random_note": "Random Note",
            "twos_random_note": "Twos Random Note",
            "none": "None",
            "nrpn14": "NRPN14", "sparse_high": "SparseHigh", "sparse_low": "SparseLow",
            "cc_default": "CCdefault", "nrpn_old": "NRPNold", "nrpn_default": "NRPNdef",
            **{'nrpn_%s_%d' % (mode, index): prefix + str(index)
               for mode, prefix in [('standard', 'NS'), ('legacy', 'NL')]
               for index in range(7)},
        })

    def test_mosaic_option_keys_match_documented_native_labels(self):
        from ui_map import MOSAIC_OPTIONS

        self.assertEqual(MOSAIC_OPTIONS["scale_lock_until_pattern_end"],
                         "Scales lock until ptn end")
        self.assertEqual(MOSAIC_OPTIONS["lock_merged_to_pentatonic"],
                         "Lock merged to pent.")
        self.assertEqual(MOSAIC_OPTIONS["elektron_program_changes"],
                         "Elektron program changes")
        self.assertEqual(MOSAIC_OPTIONS["trigless_locks"],
                         "Trigless locks")

    def test_pattern_note_degree_and_note_merge_have_page_specific_keys(self):
        from ui_map import control_cell, grid_partition

        self.assertEqual(control_cell("pattern_note_degree", (1, 0)), (1, 7))
        self.assertEqual(control_cell("pattern_note_degree", (16, 6)), (16, 1))
        self.assertEqual(control_cell("note_merge_mode"), (15, 8))
        self.assertEqual(grid_partition("channel_editor")[(15, 8)],
                         ("note_merge_mode", None))
        for invalid in ((0, 0), (17, 0), (1, -1), (1, 7), 1):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                control_cell("pattern_note_degree", invalid)
        with self.assertRaises(ValueError):
            control_cell("note_merge_mode", 1)

    def test_every_grid_cell_has_exactly_one_control_on_each_page(self):
        from ui_map import grid_partition

        for page in ("trigger_editor", "channel_editor", "song_editor", "scale_editor"):
            cells = grid_partition(page)
            self.assertEqual(len(cells), 128, page)
            self.assertEqual(len(set(cells)), 128, page)
    def test_song_pattern_slot_ordinals_cover_all_six_rows_uniquely(self):
        from ui_map import control_cell

        expected = {
            1: (1, 1), 16: (16, 1),
            17: (1, 2), 48: (16, 3),
            49: (1, 4), 96: (16, 6),
        }
        for ordinal, cell in expected.items():
            with self.subTest(ordinal=ordinal):
                self.assertEqual(control_cell("song_pattern_slot", ordinal), cell)
        cells = {control_cell("song_pattern_slot", ordinal)
                 for ordinal in range(1, 97)}
        self.assertEqual(len(cells), 96)

    def test_song_pattern_slot_rejects_invalid_ordinals(self):
        from ui_map import control_cell

        for ordinal in (0, 97, 1.5, "1", None, True):
            with self.subTest(ordinal=ordinal), self.assertRaises(ValueError):
                control_cell("song_pattern_slot", ordinal)

    def test_song_editor_partition_assigns_all_slots_and_preserves_lower_controls(self):
        from ui_map import grid_partition

        cells = grid_partition("song_editor")
        for ordinal in range(1, 97):
            x = (ordinal - 1) % 16 + 1
            y = (ordinal - 1) // 16 + 1
            with self.subTest(ordinal=ordinal):
                self.assertEqual(cells[(x, y)], ("song_pattern_slot", ordinal))
        self.assertEqual(cells[(8, 7)], ("global_pattern_length", 8))
        self.assertEqual(cells[(1, 8)], ("play_stop", None))
        self.assertEqual(len(cells), 128)
        self.assertEqual(len(set(cells)), 128)

    def test_song_pattern_slots_have_stable_row_one_keys(self):
        from ui_map import control_cell

        self.assertEqual(control_cell("song_pattern_slot", 2), (2, 1))

    def test_channel_octave_uses_a_stable_signed_key(self):
        from ui_map import control_cell, grid_partition

        self.assertEqual(control_cell("channel_octave", 1), (11, 8))
        self.assertEqual(grid_partition("channel_editor")[(11, 8)],
                         ("channel_octave", 1))

    def test_pattern_note_page_uses_four_stable_selector_keys(self):
        from ui_map import control_cell

        self.assertEqual([control_cell("pattern_note_page", page)
                          for page in range(1, 5)],
                         [(9, 8), (10, 8), (11, 8), (12, 8)])
        for page in (0, 5, True, 1.0):
            with self.subTest(page=page), self.assertRaises(ValueError):
                control_cell("pattern_note_page", page)

    def test_octave_verbs_preserve_physical_actions_and_feedback_order(self):
        from ui import Ui

        driver = FakeDriver()
        ui = Ui(driver)
        ui.set_channel_octave(-1)
        ui.set_step_octave(17, 2)
        with ui.hold_step(17):
            ui.expect_channel_octave(-1)
        ui.select_pattern_note_page(4)
        ui.tap_pattern_note_fader(16, 7)
        self.assertEqual(driver.calls, [
            ("tap", 9, 8),
            ("action", {"type": "grid", "x": 1, "y": 5, "state": 1}),
            ("tap", 12, 8),
            ("action", {"type": "grid", "x": 1, "y": 5, "state": 0}),
            ("action", {"type": "grid", "x": 1, "y": 5, "state": 1}),
            ("led_values", [(8, 8), (9, 8), (10, 8), (11, 8), (12, 8)],
             [2, 15, 2, 2, 2]),
            ("action", {"type": "grid", "x": 1, "y": 5, "state": 0}),
            ("tap", 12, 8),
            ("tap", 16, 7),
        ])

    def test_pattern_note_octave_controls_have_stable_keys(self):
        from ui import Ui
        from ui_map import control_cell

        driver = FakeDriver()
        ui = Ui(driver)
        self.assertEqual(control_cell("pattern_note_octave_down"), (16, 8))
        self.assertEqual(control_cell("pattern_note_octave_reset"), (15, 8))
        self.assertEqual(control_cell("pattern_note_octave_up"), (14, 8))
        ui.tap_control("pattern_note_octave_reset")
        with ui.hold_control("pattern_note_octave_down"):
            ui.driver.elapse(1.2)
        self.assertEqual(driver.calls, [
            ("tap", 15, 8),
            ("action", {"type": "grid", "x": 16, "y": 8, "state": 1}),
            ("elapse", 1.2),
            ("action", {"type": "grid", "x": 16, "y": 8, "state": 0}),
        ])

    def test_composition_controls_have_page_semantic_keys(self):
        from ui_map import control_cell, grid_partition

        self.assertEqual(control_cell("pattern_select", 2), (2, 1))
        self.assertEqual(control_cell("pattern_note_fader", (1, 3)), (1, 3))
        self.assertEqual(control_cell("trig_merge_mode"), (14, 8))
        self.assertEqual(control_cell("velocity_merge_mode"), (16, 8))
        self.assertEqual(control_cell("global_pattern_length", 8), (8, 7))
        self.assertEqual(grid_partition("trigger_editor")[(2, 1)],
                         ("pattern_select", 2))
        self.assertEqual(grid_partition("channel_editor")[(14, 8)],
                         ("trig_merge_mode", None))
        self.assertEqual(grid_partition("channel_editor")[(16, 8)],
                         ("velocity_merge_mode", None))
        self.assertEqual(grid_partition("song_editor")[(8, 7)],
                         ("global_pattern_length", 8))

    def test_scale_global_transpose_fader_has_semantic_keys(self):
        from ui_map import control_cell, grid_partition

        self.assertEqual(control_cell("global_transpose_minimum"), (9, 8))
        self.assertEqual(control_cell("global_transpose_increment"), (16, 8))
        self.assertEqual(grid_partition("scale_editor")[(9, 8)],
                         ("global_transpose_minimum", None))
        self.assertEqual(grid_partition("scale_editor")[(16, 8)],
                         ("global_transpose_increment", None))

    def test_channel_scale_slots_are_distinct_from_global_scale_slots(self):
        from ui_map import control_cell, grid_partition

        self.assertEqual(control_cell("scale_slot", 2), (2, 3))
        self.assertEqual(control_cell("channel_scale_slot", 2), (2, 3))
        self.assertEqual(grid_partition("scale_editor")[(2, 3)],
                         ("scale_slot", 2))
        self.assertEqual(grid_partition("channel_editor")[(2, 3)],
                         ("channel_scale_slot", 2))



class UiInputTests(unittest.TestCase):
    def test_step_transpose_plus_twelve_keeps_its_original_grid_recipe(self):
        from ui import Ui
        from ui_map import control_cell

        driver = FakeDriver()
        ui = Ui(driver)
        self.assertEqual(control_cell("step_transpose_plus_twelve"), (15, 8))
        ui.hold_control_tap("step", "step_transpose_plus_twelve", 3)
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 3, "y": 4, "state": 1}),
            ("tap", 15, 8),
            ("action", {"type": "grid", "x": 3, "y": 4, "state": 0}),
        ])

    def test_transpose_cases_return_to_channel_editor_before_scale_editor(self):
        source = (BEHAVIOUR / "cases.py").read_text()
        module = ast.parse(source)
        names = {"transpose_song_copy_isolation", "transpose_song_persistence"}
        functions = {node.name: node for node in module.body
                     if isinstance(node, ast.FunctionDef) and node.name in names}
        self.assertEqual(set(functions), names)
        for function in functions.values():
            calls = sorted((node for node in ast.walk(function)
                            if isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Attribute)),
                           key=lambda node: (node.lineno, node.col_offset))
            channel_editor = next((call.lineno, call.col_offset) for call in calls
                                  if call.func.attr == "menu"
                                  and call.args
                                  and isinstance(call.args[0], ast.Constant)
                                  and call.args[0].value == "channel_editor")
            scale_editors = [(call.lineno, call.col_offset) for call in calls
                             if call.func.attr == "scale_editor"]
            self.assertGreaterEqual(len(scale_editors), 2)
            self.assertLess(scale_editors[0], channel_editor)
            self.assertLess(channel_editor, scale_editors[1])

    def test_control_cell_exposes_mapped_diagnostic_coordinates(self):
        _, ui = self.ui()
        self.assertEqual(ui.control_cell("pattern_note_octave_up"), (14, 8))
        self.assertEqual(ui.control_cell("pattern_velocity_range_down"), (16, 8))

    def test_editor_hold_results_resolve_x_from_the_control_map(self):
        source = (BEHAVIOUR / "cases.py").read_text()
        module = ast.parse(source)
        function = next(node for node in module.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "editor_hold_boundaries")
        hold = next(node for node in function.body
                    if isinstance(node, ast.FunctionDef) and node.name == "hold")
        assignment = next(node for node in hold.body
                          if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "x"
                                  for target in node.targets))
        self.assertIsInstance(assignment.value, ast.Subscript)
        self.assertIsInstance(assignment.value.value, ast.Call)
        self.assertEqual(assignment.value.value.func.attr, "control_cell")

    def test_arp_setup_semantic_inputs_match_legacy_driver_recipe(self):
        from ui import Ui

        legacy = FakeDriver()
        legacy.action(type="grid", x=1, y=4, state=1)
        legacy.tap(16, 7)
        legacy.action(type="grid", x=1, y=4, state=0)
        legacy.tap(5, 8)
        legacy.tap(2, 4)
        legacy.tap(3, 4)
        legacy.tap(4, 4)
        legacy.tap(3, 8)
        legacy.enc(1, -4)
        legacy.enc(2, 1)
        legacy.enc(3, 51)
        legacy.key(3)
        legacy.action(type="grid", x=1, y=8, state=1)
        legacy.action(type="grid", x=1, y=8, state=0)

        semantic = FakeDriver()
        ui = Ui(semantic)
        ui.set_range(1, 64)
        ui.pattern_editor()
        for step in (2, 3, 4):
            ui.tap_step(step)
        ui.channel_editor()
        ui.turn(1, -4)
        ui.turn(2, 1)
        ui.set_value(51)
        ui.press_key(3)
        ui.gesture([("play_stop", None)], [("play_stop", None)])

        self.assertEqual(semantic.calls, legacy.calls)

    def ui(self):
        from ui import Ui

        driver = FakeDriver()
        return driver, Ui(driver)

    def test_channel_page_opens_its_mapped_task_row_from_any_origin(self):
        """E1 to Channel Tasks, E2 clamps to the first row, E2 to the page's row, K3.

        The live UI has no E1 page ring, so the recipe depends only on the
        target page's Channel Tasks row, never on the page it starts from.
        """
        from ui_map import CHANNEL_PAGES, CHANNEL_TASKS

        self.assertEqual(CHANNEL_TASKS, [
            "masks", "trig_params", "output", "harmony", "clock", "merge", "device",
            "history", "mask_detail", "trig_detail", "merge_shape", "norns"])
        rows = {"masks": 0, "trig_locks": 1, "memory": 7, "clock_mods": 4,
                "midi_config": 6, "note_dashboard": 2, "merge_shape": 10, "harmony": 3}
        self.assertEqual(set(rows), set(CHANNEL_PAGES))
        for page, row in rows.items():
            expected = [("enc", 1, 3), ("enc", 2, -12)]
            if row:
                expected.append(("enc", 2, row))
            expected.append(("key", 3))
            for origin in [None, *CHANNEL_PAGES]:
                with self.subTest(page=page, origin=origin):
                    driver, ui = self.ui()
                    ui.channel_page(page, origin, confirm=False)
                    self.assertEqual(driver.calls, expected)

    def test_channel_page_confirms_the_live_header_and_rejects_unknown_pages(self):
        from ui import UiMapError

        driver, ui = self.ui()
        confirmed = []
        ui.confirm_header = lambda page, **params: confirmed.append((page, params))
        ui.channel_page("harmony", "masks", channel=2)
        self.assertEqual(driver.calls, [
            ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 3), ("key", 3),
        ])
        self.assertEqual(confirmed, [("harmony", {"channel": 2})])
        for page in ("channel_tasks", "not_a_page"):
            with self.subTest(page=page):
                driver, ui = self.ui()
                with self.assertRaises(UiMapError):
                    ui.channel_page(page, confirm=False)
                self.assertEqual(driver.calls, [])

    def test_pattern_harmony_clock_page_and_value_verbs_keep_native_recipe(self):
        driver, ui = self.ui()
        ui.channel_page("clock_mods", "midi_config", channel=2, confirm=False)
        ui.set_value(-2)
        ui.channel_page("harmony", "clock_mods", channel=2, confirm=False)
        ui.set_value(2)
        ui.select_field("tone_0_role", offset=3)
        self.assertEqual(driver.calls, [
            ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 4), ("key", 3),
            ("enc", 3, -2),
            ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 3), ("key", 3),
            ("enc", 3, 2),
            ("enc", 2, 3),
        ])

    def test_pattern_group_hold_tap_keeps_octave_modifier_recipe(self):
        driver, ui = self.ui()
        ui.hold_control_tap("pattern_note_octave_up", "pattern_group", None, 1)
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 14, "y": 8, "state": 1}),
            ("tap", 9, 8),
            ("action", {"type": "grid", "x": 14, "y": 8, "state": 0}),
        ])

    def test_editor_range_holds_keep_native_grid_edges_and_duration(self):
        driver, ui = self.ui()
        with ui.hold_control("pattern_velocity_range_down"):
            driver.elapse(1.1)
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 16, "y": 8, "state": 1}),
            ("elapse", 1.1),
            ("action", {"type": "grid", "x": 16, "y": 8, "state": 0}),
        ])

    def test_rejected_saved_range_controls_keep_native_tap_recipe(self):
        driver, ui = self.ui()
        ui.menu("channel_editor")
        ui.play()
        ui.stop()
        self.assertEqual(driver.calls, [
            ("tap", 3, 8),
            ("tap", 1, 8),
            ("tap", 1, 8),
        ])

    def test_rejected_saved_range_starts_with_semantic_setup(self):
        from types import SimpleNamespace
        from contract.persisted_range_rejection import rejected_saved_range

        class StoppedAfterSetup(Exception):
            pass

        calls = []
        case = SimpleNamespace(
            ui=SimpleNamespace(configure=lambda: calls.append("semantic-configure")),
            configure=lambda: self.fail("raw case setup must not be used"),
            elapse=lambda seconds: (_ for _ in ()).throw(StoppedAfterSetup()),
        )
        with self.assertRaises(StoppedAfterSetup):
            rejected_saved_range(case)
        self.assertEqual(calls, ["semantic-configure"])

    def test_song_pattern_copy_and_leds_use_first_and_last_semantic_slots(self):
        driver, ui = self.ui()

        ui.copy_slot(1, 96, control="song_pattern_slot")
        ui.expect_leds({
            ("song_pattern_slot", 1): "selected",
            ("song_pattern_slot", 96): "in_range",
        })

        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 1, "y": 1, "state": 1}),
            ("tap", 16, 6),
            ("action", {"type": "grid", "x": 1, "y": 1, "state": 0}),
            ("led_values", [(1, 1), (16, 6)], [15, 5]),
        ])

    def test_note_degree_and_merge_led_keep_the_existing_physical_recipe(self):
        driver, ui = self.ui()
        ui.tap_control("pattern_note_degree", (4, 3))
        ui.tap_control("note_merge_mode")
        ui.expect_leds({("note_merge_mode", None): "off"})
        ui.expect_leds({("note_merge_mode", None): "in_range"})
        ui.expect_leds({("note_merge_mode", None): "medium"})
        self.assertEqual(driver.calls, [
            ("tap", 4, 4), ("tap", 15, 8),
            ("led_values", [(15, 8)], [2]),
            ("led_values", [(15, 8)], [5]),
            ("led_values", [(15, 8)], [8]),
        ])

    def test_mosaic_option_keys_delegate_to_existing_observed_label_recipe(self):
        driver, ui = self.ui()
        with patch.object(ui, "set_mosaic_options") as set_options:
            ui.set_mosaic_option_keys([
                ("scale_lock_until_pattern_end", False),
                ("lock_merged_to_pentatonic", True),
            ])
            set_options.assert_called_once_with([
                ("Scales lock until ptn end", False),
                ("Lock merged to pent.", True),
            ])
            with self.assertRaisesRegex(AssertionError, "unknown Mosaic option"):
                ui.set_mosaic_option_keys([("not_an_option", True)])
            self.assertEqual(set_options.call_count, 1)
        self.assertEqual(driver.calls, [])

    def test_mapped_grid_events_keep_exact_controlled_timestamps_and_order(self):
        from ui import Ui

        class ControlledDriver(FakeDriver):
            logical_ns = 900_000_000

            def elapse(self, seconds):
                nanoseconds = round(seconds * 1e9)
                self.action(type="advance", nanoseconds=nanoseconds)
                self.logical_ns += nanoseconds

        driver = ControlledDriver()
        Ui(driver).grid_events_at([
            (969_000_000, "pattern_note_degree", (1, 4), 1),
            (970_000_000, "pattern_note_degree", (1, 4), 0),
        ])
        self.assertEqual(driver.logical_ns, 970_000_000)
        self.assertEqual(driver.calls, [
            ("action", dict(type="advance", nanoseconds=69_000_000)),
            ("action", dict(type="grid", x=1, y=3, state=1)),
            ("action", dict(type="advance", nanoseconds=1_000_000)),
            ("action", dict(type="grid", x=1, y=3, state=0)),
        ])

    def test_mapped_grid_events_keep_one_native_real_time_batch(self):
        from ui import Ui

        driver = FakeDriver(clock_mode="real-time")
        ack = Ui(driver).grid_events_at([
            (969_000_000, "pattern_note_degree", (1, 4), 1),
            (970_000_000, "pattern_note_degree", (1, 4), 0),
        ], schedule_id=1)
        self.assertEqual(ack, {"native": "ack"})
        self.assertEqual(driver.calls, [("action", dict(
            type="native_input_schedule", schedule_id=1, events=[
                dict(type="grid", x=1, y=3, state=1,
                     at_monotonic_ns=969_000_000),
                dict(type="grid", x=1, y=3, state=0,
                     at_monotonic_ns=970_000_000),
            ],
        ))])

    def test_channel_page_ring_turns_clamp_at_the_boundary_through_tasks(self):
        """A saturating E1 turn on a Channel page opens the clamped ring page through Tasks.

        ``saturate`` no longer changes the recipe: Masks is the first Channel
        Tasks row, so E2 clamping to the top and K3 open it from any page.
        """
        from ui import Ui

        driver, ui = self.ui()
        ui.channel_page("masks", "midi_config", confirm=False, saturate=True)
        self.assertEqual(driver.calls, [("enc", 1, 3), ("enc", 2, -12), ("key", 3)])

        class ObservedDriver(FakeDriver):
            def wait(self, predicate, timeout=3):
                self.calls.append(("wait", timeout))
                state = next(self._states)
                if not predicate(state):
                    raise AssertionError("wait predicate rejected staged state")
                return state

        def shows(title, scope, layout):
            return {"frame": {"pixels_base64": "ignored"},
                    "diagnostics": {"menu_mode": False}, "shows": (title, scope, layout)}

        device = shows("DEVICE", "CH01", "detail")
        masks = shows("NOTE MASKS", "CH01", "overview_masks")
        harmony = shows("VOICE LEADING", "CH01", "focused")
        oracle = lambda state, title, scope, layout: state["shows"] == (title, scope, layout)
        with patch("frame_oracle.live_header_matches", side_effect=oracle):
            # Device (ring 5th) turned -5 clamps to Masks: opened through Tasks and awaited.
            driver = ObservedDriver(states=[device, masks])
            Ui(driver).turn(1, -5)
            self.assertEqual(driver.calls, [
                ("wait", 1),
                ("enc", 1, 3), ("enc", 2, -12), ("key", 3),
                ("wait", 3),
            ])
            # Already at either end, a saturating turn emits no input at all.
            for state, detents in ((masks, -5), (harmony, 5)):
                with self.subTest(detents=detents):
                    driver = ObservedDriver(states=[state])
                    Ui(driver).turn(1, detents)
                    self.assertEqual(driver.calls, [("wait", 1)])
            # An ordinary ring move: Merge shape -1 is Note dashboard (Output, task row 2).
            driver = ObservedDriver(states=[shows("MERGE SHAPE", "CH01", "focused"),
                                            shows("OUTPUT", "CH01", "focused")])
            Ui(driver).turn(1, -1)
            self.assertEqual(driver.calls, [
                ("wait", 1),
                ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 2), ("key", 3),
                ("wait", 3),
            ])
            # A screen on no page ring (Channel Tasks itself) matches neither the
            # Channel ring nor another context's ring: the physical E1 stands.
            tasks = shows("CHANNEL TASKS", "CH01", "detail")
            driver = ObservedDriver(states=[tasks, tasks])
            Ui(driver).turn(1, -5)
            self.assertEqual(driver.calls, [("wait", 1), ("wait", 1), ("enc", 1, -5)])

    def test_native_parameters_observes_controlled_menu_mode_before_navigation(self):
        from ui import Ui

        driver = FakeDriver(states=[{"diagnostics": {"menu_mode": True}}])
        ui = Ui(driver)
        with patch.object(ui, "expect_menu_label") as expect:
            ui.open_native_parameters()
        self.assertEqual(driver.calls, [
            ("key", 1), ("snapshot",), ("enc", 1, 4), ("key", 3),
        ])
        expect.assert_called_once_with("LEVELS >")

    def test_native_parameters_controlled_mode_fails_closed_on_opposite_state(self):
        from ui import Ui, UiMapError

        driver = FakeDriver(states=[{"diagnostics": {"menu_mode": False}}])
        ui = Ui(driver)
        with patch.object(ui, "expect_menu_label") as expect, self.assertRaises(UiMapError):
            ui.open_native_parameters()
        self.assertEqual(driver.calls, [
            ("key", 1), ("snapshot",),
        ])
        expect.assert_not_called()

    def test_native_parameters_real_time_rejects_opposite_then_accepts_open(self):
        from ui import Ui

        class Driver(FakeDriver):
            # First wait: the menu-mode transition. Second and third waits:
            # the E1 Channel-ring and other-ring observations, which both stand
            # down in the native menu so the physical E1 reaches PARAMETERS.
            menu = {"diagnostics": {"menu_mode": True},
                    "frame": {"pixels_base64": "ignored"}}
            staged = [
                [{"diagnostics": {"menu_mode": False}},
                 {"diagnostics": {"menu_mode": True}}],
                [menu],
                [menu],
            ]
            matches = []

            def wait(self, predicate, timeout=3):
                self.calls.append(("wait", timeout))
                states = self.staged[len(self.matches)]
                self.matches.append([predicate(state) for state in states])
                return states[-1]

        driver = Driver(clock_mode="real-time")
        ui = Ui(driver)
        with patch.object(ui, "expect_menu_label"), \
                patch("frame_oracle.live_header_matches",
                      side_effect=AssertionError("menu mode must not read a header")):
            ui.open_native_parameters()
        self.assertEqual(driver.calls, [
            ("key", 1), ("wait", 1), ("wait", 1), ("wait", 1), ("enc", 1, 4), ("key", 3),
        ])
        self.assertEqual(driver.matches, [[False, True], [True], [True]])

    def test_leave_native_menu_controlled_mode_rejects_still_open(self):
        from ui import Ui, UiMapError

        driver = FakeDriver(states=[{"diagnostics": {"menu_mode": True}}])
        ui = Ui(driver)
        with self.assertRaises(UiMapError):
            ui.leave_native_menu()
        self.assertEqual(driver.calls, [("key", 1), ("snapshot",)])

    def test_leave_native_menu_real_time_rejects_open_then_accepts_closed(self):
        from ui import Ui

        class Driver(FakeDriver):
            def wait(self, predicate, timeout=3):
                self.calls.append(("wait", timeout))
                states = [
                    {"diagnostics": {"menu_mode": True}},
                    {"diagnostics": {"menu_mode": False}},
                ]
                self.matches = [predicate(state) for state in states]
                return states[-1]

        driver = Driver(clock_mode="real-time")
        ui = Ui(driver)
        ui.leave_native_menu()
        self.assertEqual(driver.calls, [("key", 1), ("wait", 1)])
        self.assertEqual(driver.matches, [False, True])

    def test_trig_parameter_keys_delegate_exact_labels_and_offsets(self):
        from ui import Ui

        driver, ui = self.ui()
        for key, label in (("fixed_note", "Fixed Note"),
                           ("quantised_fixed_note", "Quantised Fixed Note"),
                           ("random_note", "Random Note"),
                           ("twos_random_note", "Twos Random Note")):
            for offset in (None, 0, 2, 49, -1):
                with self.subTest(key=key, offset=offset):
                    with patch.object(ui, "assign_trig_parameter",
                                      return_value=offset) as assign:
                        self.assertEqual(
                            ui.assign_trig_parameter_key(key, offset=offset), offset
                        )
                    assign.assert_called_once_with(label, offset=offset)
        self.assertEqual(driver.calls, [])

    def test_chord_parameter_keys_keep_the_existing_native_input_recipe(self):
        from ui import Ui

        for key, label in (("chord_note_arpeggio", "Chord Note Arpeggio"),
                           ("chord_note_strum", "Chord Note Strum"),
                           ("chord_spread", "Chord Spread"),
                           ("chord_accel_mod", "Chord Accel Mod"),
                           ("mute_chord_root", "Mute Chord Root"),
                           ("chord_pattern", "Chord Pattern")):
            with self.subTest(key=key):
                driver = FakeDriver()
                ui = Ui(driver)
                with patch.object(ui, "expect_list_label", return_value=True) as expect:
                    ui.assign_trig_parameter_key(key, offset=2)

                expect.assert_called_once_with(label)
                self.assertEqual(driver.calls, [
                    ("key", 2),
                    ("enc", 3, -50),
                    ("enc", 3, 2),
                    ("key", 3),
                    ("key", 2),
                ])

    def test_parameter_label_lookup_preserves_migrated_result_labels(self):
        from ui import Ui, UiMapError

        ui = Ui(FakeDriver())
        for key, label in (("chord_note_arpeggio", "Chord Note Arpeggio"),
                           ("chord_note_strum", "Chord Note Strum"),
                           ("chord_spread", "Chord Spread")):
            with self.subTest(key=key):
                self.assertEqual(ui.trig_parameter_label(key), label)
        with self.assertRaises(UiMapError):
            ui.trig_parameter_label("Chord Spread")

    def test_header_surface_verb_checks_live_header_oracle_and_result(self):
        """The surface verb checks the live title row and scope text, exactly."""
        from ui import Ui

        driver = FakeDriver(states=[{}])
        ui = Ui(driver)
        with patch("frame_oracle.live_header_matches", return_value=True) as live:
            ui.expect_header_surface("midi_config", channel=1)
        live.assert_called_once_with({}, "DEVICE", "CH01", "detail")
        self.assertEqual(driver.results, [{
            "kind": "screen-header", "expected": "DEVICE CH01", "matched": True
        }])
        driver = FakeDriver(states=[{}])
        with patch("frame_oracle.live_header_matches", return_value=False), \
                self.assertRaises(AssertionError):
            Ui(driver).expect_header_surface("midi_config", channel=1)
        self.assertEqual(driver.results, [])

    def test_unknown_trig_parameter_key_fails_before_input(self):
        from ui import UiMapError

        driver, ui = self.ui()
        with patch.object(ui, "assign_trig_parameter") as assign:
            for key in ("missing", "Fixed Note"):
                with self.subTest(key=key), self.assertRaises(UiMapError):
                    ui.assign_trig_parameter_key(key)
        assign.assert_not_called()
        self.assertEqual(driver.calls, [])
        self.assertEqual(driver.results, [])

    def test_range_recipe_is_identical_to_hold_then_tap(self):
        driver, ui = self.ui()
        ui.set_range(1, 20)
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 1}),
            ("tap", 4, 5),
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 0}),
        ])

    def test_hold_control_tap_preserves_nested_hold_recipe(self):
        driver, ui = self.ui()
        ui.hold_control_tap("velocity_merge_mode", "pattern_slot", target_index=1)
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 16, "y": 8, "state": 1}),
            ("tap", 1, 2),
            ("action", {"type": "grid", "x": 16, "y": 8, "state": 0}),
        ])

    def test_hold_control_releases_the_mapped_cell_after_failure(self):
        driver, ui = self.ui()
        with self.assertRaisesRegex(RuntimeError, "stop"):
            with ui.hold_control("channel", 1):
                raise RuntimeError("stop")
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 1, "y": 1, "state": 1}),
            ("action", {"type": "grid", "x": 1, "y": 1, "state": 0}),
        ])

    def test_gesture_preserves_non_nested_release_order(self):
        driver, ui = self.ui()
        ui.gesture([("step", 1), ("song_slot", 2)], [("step", 1), ("song_slot", 2)])
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 1}),
            ("action", {"type": "grid", "x": 2, "y": 3, "state": 1}),
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 0}),
            ("action", {"type": "grid", "x": 2, "y": 3, "state": 0}),
        ])

    def test_gesture_maps_play_stop_pulse_without_advancing(self):
        driver, ui = self.ui()
        ui.gesture([("play_stop", None)], [("play_stop", None)])
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 1, "y": 8, "state": 1}),
            ("action", {"type": "grid", "x": 1, "y": 8, "state": 0}),
        ])

    def test_encoder_event_preserves_one_native_event_without_timing(self):
        driver, ui = self.ui()
        result = ui.encoder_event(3, -2)
        self.assertEqual(driver.calls, [
            ("action", {"type": "enc", "n": 3, "delta": -2}),
        ])
        self.assertEqual(result, {"native": "ack"})

    def test_control_and_key_edges_keep_exact_timing_free_event_shape(self):
        driver, ui = self.ui()
        ui.control_edge("step", True, index=3)
        ui.control_edge("step", False, index=3)
        ui.key_edge(1, True)
        ui.key_edge(1, False)
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 3, "y": 4, "state": 1}),
            ("action", {"type": "grid", "x": 3, "y": 4, "state": 0}),
            ("action", {"type": "key", "n": 1, "state": 1}),
            ("action", {"type": "key", "n": 1, "state": 0}),
        ])

    def test_hardware_adapter_verbs_keep_the_exact_timed_input_recipe(self):
        driver, ui = self.ui()
        ui.hardware_tap(1, 8)
        ui.hardware_key(3)
        ui.hardware_turn(2, -1)
        ui.hardware_hold_tap((1, 4), (4, 4))
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 1, "y": 8, "state": 1}),
            ("elapse", .04),
            ("action", {"type": "grid", "x": 1, "y": 8, "state": 0}),
            ("elapse", .12),
            ("action", {"type": "key", "n": 3, "state": 1}),
            ("action", {"type": "key", "n": 3, "state": 0}),
            ("elapse", .06),
            ("action", {"type": "enc", "n": 2, "delta": -1}),
            ("elapse", .05),
            ("elapse", .15),
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 1}),
            ("action", {"type": "grid", "x": 4, "y": 4, "state": 1}),
            ("elapse", .04),
            ("action", {"type": "grid", "x": 4, "y": 4, "state": 0}),
            ("elapse", .12),
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 0}),
        ])

    def test_hardware_led_observation_keeps_the_vector_result_shape(self):
        grid = [0] * 128
        grid[17] = 15
        driver = FakeDriver(states=[{"grid": grid}])
        ui = __import__("ui").Ui(driver)
        ui.hardware_led_values([(2, 2)], [15])
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [{
            "kind": "grid", "cells": [(2, 2)], "expected": [15], "actual": [15],
        }])

    def test_stored_patch_control_slots_are_resolved_from_stable_keys(self):
        driver, ui = self.ui()
        ui.assign_trig_parameter = lambda label, offset=None: driver.calls.append(
            ("assign", label, offset)
        )
        ui.assign_stored_patch_control(10)
        self.assertEqual(driver.calls, [("assign", "CC 10", None)])
        with self.assertRaisesRegex(AssertionError, "slot must be in 1..10"):
            ui.assign_stored_patch_control(11)

    def test_configure_keeps_its_exact_physical_recipe_through_device_task(self):
        driver, ui = self.ui()
        ui.expect_header = lambda page, **params: driver.calls.append(("header", page, params))
        ui.configure()
        self.assertEqual(driver.calls, [
            ("tap", 3, 8), ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
            ("enc", 3, 1), ("key", 3),
            ("tap", 5, 8),
            ("tap", 1, 4), ("tap", 2, 4), ("tap", 3, 4), ("tap", 4, 4),
            ("tap", 5, 8),
            ("tap", 1, 7), ("tap", 2, 6), ("tap", 3, 5), ("tap", 4, 4),
            ("tap", 5, 8),
            ("tap", 1, 1), ("tap", 2, 2), ("tap", 3, 3), ("tap", 4, 4),
            ("tap", 3, 8), ("tap", 1, 2),
            ("hold_tap", (1, 4), (4, 4)),
            ("led_values", [(1, 2)], [15]),
            ("header", "trig_locks", {"channel": 1}),
            ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
            ("header", "midi_config", {"channel": 1}),
        ])

    def test_quantised_fixed_major_uses_semantic_setup_and_preserves_trace(self):
        from types import ModuleType, SimpleNamespace
        from trig_parameter_interactions import quantised_fixed_table

        driver, ui = self.ui()
        ui.expect_header = lambda page, **params: driver.calls.append(("header", page, params))
        ui.assign_trig_parameter_key = lambda parameter: driver.calls.append(
            ("assign_trig_parameter_key", parameter)
        )
        case = SimpleNamespace(
            ui=ui,
            clock_mode="controlled-experimental",
            results=[],
            configure=lambda: self.fail("case-level raw setup must not be used"),
            playback=lambda *args, **kwargs: [
                {"logical_ns": index * 166666666} for index in range(4)
            ],
        )
        cases = ModuleType("cases")
        cases.assign_trig_parameter = lambda *args, **kwargs: self.fail(
            "case-level native assignment helper must not be used"
        )
        cases.assert_durations = lambda context, notes, lengths: self.assertEqual(
            lengths, [1, 1, 1]
        )

        with patch.dict(sys.modules, {"cases": cases}):
            quantised_fixed_table(case, profile="major")

        self.assertEqual(driver.calls[:7], [
            ("tap", 3, 8), ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
            ("enc", 3, 1), ("key", 3),
        ])
        self.assertEqual(driver.calls[22:32], [
            ("tap", 3, 8), ("tap", 1, 2),
            ("hold_tap", (1, 4), (4, 4)),
            ("led_values", [(1, 2)], [15]),
            ("header", "trig_locks", {"channel": 1}),
            ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
            ("header", "midi_config", {"channel": 1}),
        ])
        self.assertEqual(driver.calls[32:37], [
            ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 1), ("key", 3),
            ("assign_trig_parameter_key", "quantised_fixed_note"),
        ])
        self.assertEqual(driver.calls[37:51], [
            ("enc", 3, delta) for delta in
            (1, 1, 2, 3, 1, 4, 1, 48, 1, 2, 3, 4, 56, 1)
        ])
        self.assertEqual(len(case.results), 14)

    def test_seeded_probability_uses_semantic_setup_with_same_event_trace(self):
        from types import ModuleType, SimpleNamespace
        from trig_parameter_interactions import seeded_probability

        class StopAfterSetup(Exception):
            pass

        driver, ui = self.ui()
        ui.expect_header = lambda page, **params: driver.calls.append(("header", page, params))
        selected = []

        def stop_on_channel(channel):
            selected.append(channel)
            raise StopAfterSetup()

        ui.select_channel = stop_on_channel
        case = SimpleNamespace(
            ui=ui,
            results=[],
            configure=lambda: self.fail("case-level raw setup must not be used"),
        )
        cases = ModuleType("cases")
        cases.assert_durations = lambda *args, **kwargs: None
        draws = [98, 99] + [0] * 63
        stdout = "".join(str(value) + "\n" for value in draws)

        with patch.dict(sys.modules, {"cases": cases}), patch(
            "subprocess.run", return_value=SimpleNamespace(stdout=stdout)
        ), self.assertRaises(StopAfterSetup):
            seeded_probability(case, probability=99, opportunities=64)

        self.assertEqual(driver.calls[:7], [
            ("tap", 3, 8), ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
            ("enc", 3, 1), ("key", 3),
        ])
        self.assertEqual(driver.calls[22:32], [
            ("tap", 3, 8), ("tap", 1, 2),
            ("hold_tap", (1, 4), (4, 4)),
            ("led_values", [(1, 2)], [15]),
            ("header", "trig_locks", {"channel": 1}),
            ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
            ("header", "midi_config", {"channel": 1}),
        ])
        self.assertEqual(selected, [2])

    def test_fixed_note_domain_uses_semantic_ui_and_preserves_input_trace(self):
        from types import ModuleType, SimpleNamespace
        from trig_parameter_interactions import fixed_note_domain

        driver, ui = self.ui()
        ui.expect_header = lambda page, **params: driver.calls.append(("header", page, params))
        ui.assign_trig_parameter_key = lambda parameter: driver.calls.append(
            ("assign_trig_parameter_key", parameter)
        )
        case = SimpleNamespace(
            ui=ui,
            clock_mode="controlled-experimental",
            results=[],
            configure=lambda: self.fail("case-level raw setup must not be used"),
            enc=lambda *args: self.fail("case-level raw encoder must not be used"),
            action=lambda **kwargs: self.fail("case-level raw action must not be used"),
            elapse=driver.elapse,
            playback=lambda *args, **kwargs: [
                {"logical_ns": index * 166666666} for index in range(4)
            ],
        )
        cases = ModuleType("cases")
        cases.assign_trig_parameter = lambda *args, **kwargs: self.fail(
            "case-level native assignment helper must not be used"
        )
        cases.assert_durations = lambda context, notes, lengths: self.assertEqual(
            lengths, [1, 1, 1]
        )

        with patch.dict(sys.modules, {"cases": cases}):
            fixed_note_domain(case, start=0, count=1)

        self.assertEqual(driver.calls, [
            ("tap", 3, 8), ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
            ("enc", 3, 1), ("key", 3),
            ("tap", 5, 8),
            ("tap", 1, 4), ("tap", 2, 4), ("tap", 3, 4), ("tap", 4, 4),
            ("tap", 5, 8),
            ("tap", 1, 7), ("tap", 2, 6), ("tap", 3, 5), ("tap", 4, 4),
            ("tap", 5, 8),
            ("tap", 1, 1), ("tap", 2, 2), ("tap", 3, 3), ("tap", 4, 4),
            ("tap", 3, 8), ("tap", 1, 2),
            ("hold_tap", (1, 4), (4, 4)),
            ("led_values", [(1, 2)], [15]),
            ("header", "trig_locks", {"channel": 1}),
            ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
            ("header", "midi_config", {"channel": 1}),
            ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 1), ("key", 3),
            ("assign_trig_parameter_key", "fixed_note"),
            ("enc", 2, 1), ("assign_trig_parameter_key", "quantised_fixed_note"),
            ("enc", 3, 8),
            ("enc", 2, 1), ("assign_trig_parameter_key", "random_note"),
            ("enc", 3, 4),
            ("enc", 2, 1), ("assign_trig_parameter_key", "twos_random_note"),
            ("enc", 3, 4),
            ("enc", 2, -3), ("enc", 3, 1),
            ("elapse", .05), ("action", {"type": "enc", "n": 3, "delta": -126}),
            ("elapse", .15),
            ("enc", 2, 1), ("elapse", .05),
            ("action", {"type": "enc", "n": 3, "delta": -126}), ("elapse", .15),
            ("enc", 2, 1), ("elapse", .05),
            ("action", {"type": "enc", "n": 3, "delta": -126}), ("elapse", .15),
            ("enc", 2, 1), ("elapse", .05),
            ("action", {"type": "enc", "n": 3, "delta": -126}), ("elapse", .15),
        ])
        self.assertEqual(
            [(result["phase"], result["pitches"]) for result in case.results],
            [("0", [0, 0, 0, 0]), ("all-overrides-off", [60, 62, 64, 65])],
        )

    def test_stock_pitch_lock_variants_use_semantic_ui_and_preserve_trace(self):
        from types import ModuleType, SimpleNamespace
        from trig_parameter_interactions import stock_pitch_lock_inheritance

        def expected_trace():
            calls = [
                ("tap", 3, 8), ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
            ("enc", 3, 1), ("key", 3),
                ("tap", 5, 8),
                ("tap", 1, 4), ("tap", 2, 4), ("tap", 3, 4), ("tap", 4, 4),
                ("tap", 5, 8),
                ("tap", 1, 7), ("tap", 2, 6), ("tap", 3, 5), ("tap", 4, 4),
                ("tap", 5, 8),
                ("tap", 1, 1), ("tap", 2, 2), ("tap", 3, 3), ("tap", 4, 4),
                ("tap", 3, 8), ("tap", 1, 2),
                ("hold_tap", (1, 4), (4, 4)),
                ("led_values", [(1, 2)], [15]),
                ("header", "trig_locks", {"channel": 1}),
                ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 6), ("key", 3),
                ("header", "midi_config", {"channel": 1}),
                ("enc", 1, 3), ("enc", 2, -12), ("enc", 2, 1), ("key", 3),
                ("key", 2), ("enc", 3, -50), ("key", 3), ("key", 2),
                ("enc", 3, 61),
            ]

            def lock(step, value):
                calls.append(("action", {"type": "grid", "x": step, "y": 4, "state": 1}))
                calls.extend([
                    ("elapse", .05),
                    ("action", {"type": "enc", "n": 3, "delta": -126}),
                    ("elapse", .15),
                ])
                if value >= 0:
                    calls.append(("enc", 3, value + 1))
                calls.append(("action", {"type": "grid", "x": step, "y": 4, "state": 0}))
                calls.append(("elapse", .15))

            def clear(step):
                calls.extend([
                    ("action", {"type": "grid", "x": step, "y": 4, "state": 1}),
                    ("elapse", .05), ("key", 2),
                    ("action", {"type": "grid", "x": step, "y": 4, "state": 0}),
                    ("elapse", .15),
                ])

            lock(2, 63)
            lock(1, 0)
            lock(4, -1)
            calls.append(("enc", 3, 5))
            clear(2)
            calls.extend([
                ("action", {"type": "enc", "n": 3, "delta": -126}),
                ("elapse", .15),
            ])
            clear(1)
            lock(2, 0)
            clear(2)
            return calls

        cases = ModuleType("cases")
        cases.assign_trig_parameter = lambda *args, **kwargs: self.fail(
            "case-level native assignment helper must not be used"
        )
        cases.assert_durations = lambda context, notes, lengths: self.assertEqual(
            lengths, [1] * (len(notes) - 1)
        )
        with patch.dict(sys.modules, {"cases": cases}):
            for quantised in (True, False):
                driver, ui = self.ui()
                labels = []
                ui.expect_header = lambda page, **params: driver.calls.append(
                    ("header", page, params)
                )
                ui.expect_list_label = lambda label, wait=True: (
                    labels.append((label, wait)) or not wait
                )
                pitches_by_phase = iter([
                    [60] * 4,
                    [60, 62 if quantised else 63, 60, 60],
                    [0, 62 if quantised else 63, 60, 60],
                    [0, 62 if quantised else 63, 60, 60],
                    [0, 62 if quantised else 63, 65, 65],
                    [0, 65, 65, 65],
                    [0, 62, 64, 65],
                    [60, 62, 64, 65],
                    [60, 0, 64, 65],
                    [60, 62, 64, 65],
                ])
                case = SimpleNamespace(
                    ui=ui,
                    clock_mode="controlled-experimental",
                    results=[],
                    configure=lambda: self.fail("case-level raw setup must not be used"),
                    enc=lambda *args: self.fail("case-level raw encoder must not be used"),
                    key=lambda *args: self.fail("case-level raw key must not be used"),
                    action=lambda **kwargs: self.fail("case-level raw action must not be used"),
                    elapse=driver.elapse,
                    playback=lambda *args, **kwargs: [
                        {"logical_ns": index * 166666666} for index in range(4)
                    ],
                )
                stock_pitch_lock_inheritance(case, quantised=quantised)
                self.assertEqual(driver.calls, expected_trace())
                label = "Quantised Fixed Note" if quantised else "Fixed Note"
                self.assertEqual(labels, [(label, False), (label, True)])
                self.assertEqual(
                    [result["pitches"] for result in case.results],
                    [next(pitches_by_phase) for _ in range(10)],
                )

    def test_set_mosaic_options_preserves_observed_seek_recipe_and_results(self):
        from ui import Ui

        states = [
            {"diagnostics": {"parameter_roots": [
                {"id": "other"}, {"id": "other-2"}, {"id": "mosaic"},
            ]}},
            {"frame": {}},
            {"frame": {}},
        ]
        driver = FakeDriver(states=states)
        ui = Ui(driver)
        ui.expect_menu_label = lambda label: driver.calls.append(("menu-label", label))
        ui.expect_menu_option_row = lambda label, value, top=None: driver.calls.append(
            ("menu-option-row", label, value, top)
        )
        with patch("frame_oracle.selected_line", side_effect=[False, True]):
            ui.set_mosaic_options([("Elektron program changes", True)])
        self.assertEqual(driver.calls, [
            ("key", 1), ("enc", 1, 4), ("key", 3), ("menu-label", "LEVELS >"),
            ("snapshot",), ("enc", 2, 2), ("key", 3), ("enc", 2, -60),
            ("snapshot",), ("enc", 2, 1), ("snapshot",), ("enc", 3, 3),
            ("menu-option-row", "Elektron program changes", "On", 22),
            ("key", 2), ("enc", 2, -60), ("menu-label", "LEVELS >"),
            ("key", 2), ("key", 1),
        ])
        self.assertEqual(driver.results, [{
            "kind": "mosaic-option-input",
            "label": "Elektron program changes",
            "enabled": True,
        }])

    def test_set_mosaic_number_preserves_observed_seek_recipe_and_result(self):
        from ui import Ui

        states = [
            {"diagnostics": {"parameter_roots": [
                {"id": "other"}, {"id": "other-2"}, {"id": "mosaic"},
            ]}},
            {"frame": {}},
        ]
        driver = FakeDriver(states=states)
        ui = Ui(driver)
        ui.expect_menu_label = lambda label: driver.calls.append(("menu-label", label))
        ui.expect_menu_option_row = lambda label, value, top=None: driver.calls.append(
            ("menu-option-row", label, value, top)
        )
        with patch("frame_oracle.selected_line", return_value=True):
            ui.set_mosaic_number("elektron_program_change_channel", -9, "1")
        self.assertEqual(driver.calls, [
            ("key", 1), ("enc", 1, 4), ("key", 3), ("menu-label", "LEVELS >"),
            ("snapshot",), ("enc", 2, 2), ("key", 3), ("enc", 2, -60),
            ("snapshot",), ("enc", 3, -9),
            ("menu-option-row", "Elektron p.change channel", "1", 22),
            ("key", 2), ("enc", 2, -60), ("menu-label", "LEVELS >"),
            ("key", 2), ("key", 1),
        ])
        self.assertEqual(driver.results, [{
            "kind": "mosaic-number-input",
            "label": "Elektron p.change channel",
            "value": "1",
        }])

    def test_patch_control_preserves_setup_scan_and_observed_label(self):
        from ui import Ui

        driver = FakeDriver(states=[
            {"diagnostics": {"parameter_roots": [
                {"id": "other"},
                {"id": "midi_device_params_group_channel_1"},
            ]}},
            {},
            {},
        ])
        driver.configure = lambda: driver.calls.append(("configure",))
        ui = Ui(driver)
        ui.expect_menu_label = lambda label: driver.calls.append(("menu-label", label))
        with patch("frame_oracle.selected_line", side_effect=[False, True]):
            self.assertEqual(ui.open_patch_control(configured=True), "Control 1")
        self.assertEqual(driver.calls, [
            ("configure",), ("enc", 3, 1), ("key", 3),
            ("key", 1), ("enc", 1, 4), ("key", 3),
            ("menu-label", "LEVELS >"), ("snapshot",),
            ("enc", 2, 1), ("key", 3),
            ("snapshot",), ("enc", 2, 1), ("snapshot",),
            ("menu-label", "Control 1"),
        ])

    def test_patch_control_turn_keeps_native_event_spacing_and_bounds(self):
        driver, ui = self.ui()
        ui.turn_patch_control(-63)
        self.assertEqual(driver.calls, [
            ("elapse", .05),
            ("action", {"type": "enc", "n": 3, "delta": -126}),
            ("elapse", .03),
        ])
        for invalid in (-64, 0, 64):
            with self.assertRaises(AssertionError):
                ui.turn_patch_control(invalid)

    def test_patch_parameter_seek_uses_stable_key_and_preserves_scan_recipe(self):
        from ui import Ui

        driver = FakeDriver(states=[{}, {}])
        ui = Ui(driver)
        ui.open_patch_control = lambda configured=False: driver.calls.append(
            ("open-patch-control", configured)
        )
        ui.expect_menu_label = lambda label: driver.calls.append(("menu-label", label))
        with patch("frame_oracle.selected_line", side_effect=[False, True]):
            ui.seek_patch_parameter("nrpn14", configured=True)
        self.assertEqual(driver.calls, [
            ("open-patch-control", True),
            ("snapshot",), ("enc", 2, 1), ("snapshot",),
            ("menu-label", "NRPN14"),
        ])

    def test_patch_parameter_seek_preserves_exhaustion_boundary_and_failure(self):
        from ui import Ui

        driver = FakeDriver(states=[{}, {}])
        ui = Ui(driver)
        ui.open_patch_control = lambda configured=False: driver.calls.append(
            ("open-patch-control", configured)
        )
        with patch("frame_oracle.selected_line", return_value=False):
            with self.assertRaisesRegex(AssertionError, "NRPN14 control not reachable"):
                ui.seek_patch_parameter("nrpn14", configured=True, attempts=2)
        self.assertEqual(driver.calls, [
            ("open-patch-control", True),
            ("snapshot",), ("enc", 2, 1),
            ("snapshot",), ("enc", 2, 1),
        ])

    def test_mapping_parameter_seek_keeps_native_recipe_and_top_fallback(self):
        from ui import Ui

        states = [{"diagnostics": {"parameter_roots": [
            {"id": "other"}, {"id": "mosaic_mask_midi_maps"},
        ]}}] + [{"frame": {}} for _ in range(3)]
        driver = FakeDriver(states=states)
        ui = Ui(driver)
        ui.expect_menu_label = lambda label: driver.calls.append(("menu-label", label))
        checks = []
        def selected(state, label, top=22):
            checks.append((label, top))
            return len(checks) == 5
        with patch("frame_oracle.selected_line", side_effect=selected):
            ui.seek_native_mapping_parameter("selected_channel_velocity")
        self.assertEqual(driver.calls, [
            ("key", 1), ("enc", 1, 4), ("key", 3), ("menu-label", "LEVELS >"),
            ("snapshot",), ("enc", 2, 1), ("key", 3),
            ("snapshot",), ("enc", 2, 1),
            ("snapshot",), ("enc", 2, 1),
            ("snapshot",),
        ])
        self.assertEqual(checks, [
            ("Selected Ch. Velocity", 23), ("Selected Ch. Velocity", 22),
            ("Selected Ch. Velocity", 23), ("Selected Ch. Velocity", 22),
            ("Selected Ch. Velocity", 23),
        ])
        self.assertEqual(driver.results, [])

    def test_mapping_parameter_seek_keeps_twelve_check_failure_boundary(self):
        from ui import Ui

        states = [{"diagnostics": {"parameter_roots": [
            {"id": "mosaic_mask_midi_maps"},
        ]}}] + [{"frame": {}} for _ in range(12)]
        driver = FakeDriver(states=states)
        ui = Ui(driver)
        ui.expect_menu_label = lambda label: driver.calls.append(("menu-label", label))
        with patch("frame_oracle.selected_line", return_value=False) as selected:
            with self.assertRaisesRegex(AssertionError, "Mapping parameter not reached"):
                ui.seek_native_mapping_parameter("selected_channel_velocity")
        self.assertEqual(selected.call_count, 24)
        self.assertEqual(driver.calls.count(("snapshot",)), 13)
        self.assertEqual(driver.calls.count(("enc", 2, 1)), 12)
        self.assertEqual(driver.calls[-1], ("enc", 2, 1))
        self.assertEqual(driver.results, [])


    def test_native_parameter_root_seek_uses_stable_keys_and_exact_position(self):
        from ui import Ui

        roots = [
            {"id": "midi_device_params_group_channel_1", "name": "MIDI"},
            {"id": "other", "name": "macro 1"},
        ]
        state = {"diagnostics": {"parameter_roots": roots}}
        driver = FakeDriver(states=[state, state])
        ui = Ui(driver)
        self.assertEqual(ui.seek_native_parameter_root("channel_1_device_parameters"), 0)
        self.assertEqual(ui.seek_native_parameter_root("macro_1"), 1)
        self.assertEqual(driver.calls, [
            ("snapshot",), ("enc", 2, 0),
            ("snapshot",), ("enc", 2, 1),
        ])

    def test_native_menu_parameter_seek_preserves_observed_scan_and_bound(self):
        from ui import Ui

        driver = FakeDriver(states=[{}, {}])
        ui = Ui(driver)
        with patch("frame_oracle.selected_line", side_effect=[False, True]) as selected:
            ui.seek_native_menu_parameter("configured_control_1")
        self.assertEqual(driver.calls, [
            ("snapshot",), ("enc", 2, 1), ("snapshot",),
        ])
        self.assertEqual(selected.call_args_list[0].args[1:], ("Control 1",))
        self.assertEqual(selected.call_args_list[1].args[1:], ("Control 1",))
        self.assertEqual(driver.results, [])

    def test_native_menu_parameter_seek_keeps_180_check_failure_and_message(self):
        from ui import Ui

        driver = FakeDriver(states=[{} for _ in range(180)])
        with patch("frame_oracle.selected_line", return_value=False) as selected:
            with self.assertRaisesRegex(
                    AssertionError, "Configured Control 1 unavailable in Matrix target group"):
                Ui(driver).seek_native_menu_parameter("configured_control_1")
        self.assertEqual(selected.call_count, 180)
        self.assertEqual(driver.calls.count(("snapshot",)), 180)
        self.assertEqual(driver.calls.count(("enc", 2, 1)), 180)
        self.assertEqual(driver.calls[-1], ("enc", 2, 1))
        self.assertEqual(driver.results, [])

    def test_native_menu_parameter_seek_rejects_unknown_key_without_input(self):
        from ui import Ui, UiMapError

        driver = FakeDriver()
        with self.assertRaisesRegex(UiMapError, "unknown native menu parameter"):
            Ui(driver).seek_native_menu_parameter("not-a-parameter")
        self.assertEqual(driver.calls, [])

    def test_native_parameter_root_missing_preserves_stop_iteration(self):
        from ui import Ui

        driver = FakeDriver(states=[{"diagnostics": {"parameter_roots": []}}])
        with self.assertRaises(StopIteration):
            Ui(driver).seek_native_parameter_root("macro_1")
        self.assertEqual(driver.calls, [("snapshot",)])

    def test_native_menu_parameter_seek_preserves_callers_failure_message(self):
        from ui import Ui

        driver = FakeDriver(states=[{}])
        with patch("frame_oracle.selected_line", return_value=False):
            with self.assertRaisesRegex(AssertionError, "second call unavailable"):
                Ui(driver).seek_native_menu_parameter(
                    "configured_control_1", attempts=1,
                    failure="second call unavailable")
        self.assertEqual(driver.calls, [("snapshot",), ("enc", 2, 1)])

    def test_patch_value_resolves_stable_and_numeric_values_and_rejects_unknown(self):
        driver, ui = self.ui()
        ui.expect_menu_value = lambda value: driver.calls.append(("menu-value", value))
        ui.expect_patch_value("off")
        ui.expect_patch_value(126)
        with self.assertRaisesRegex(AssertionError, "unknown patch parameter value"):
            ui.expect_patch_value("rendered-text")
        self.assertEqual(driver.calls, [
            ("menu-value", "X"), ("menu-value", "126"),
        ])

    def test_select_midi_clock_source_preserves_observed_seek_recipe(self):
        from ui import Ui

        driver = FakeDriver(states=[{"diagnostics": {"parameter_roots": [
            {"name": "OTHER"}, {"name": "CLOCK"},
        ]}}])
        ui = Ui(driver)
        ui.configure = lambda: driver.calls.append(("configure",))
        ui.expect_menu_label = lambda label: driver.calls.append(("menu-label", label))
        ui.expect_menu_value = lambda value: driver.calls.append(("menu-value", value))
        ui.select_midi_clock_source()
        self.assertEqual(driver.calls, [
            ("configure",), ("key", 1), ("enc", 1, 4), ("key", 3),
            ("menu-label", "LEVELS >"), ("snapshot",), ("enc", 2, 1),
            ("key", 3), ("menu-label", "source"), ("menu-value", "internal"),
            ("enc", 3, 1), ("menu-value", "midi"),
        ])


    def test_select_midi_clock_source_from_levels_preserves_suffix_recipe(self):
        from ui import Ui

        driver = FakeDriver(states=[{"diagnostics": {"parameter_roots": [
            {"name": "OTHER"}, {"name": "CLOCK"},
        ]}}])
        ui = Ui(driver)
        ui.expect_menu_label = lambda label: driver.calls.append(("menu-label", label))
        ui.expect_menu_value = lambda value: driver.calls.append(("menu-value", value))
        ui.select_midi_clock_source_from_levels()
        self.assertEqual(driver.calls, [
            ("menu-label", "LEVELS >"), ("snapshot",), ("enc", 2, 1),
            ("key", 3), ("menu-label", "source"), ("menu-value", "internal"),
            ("enc", 3, 1), ("menu-value", "midi"),
        ])

class UiObservationTests(unittest.TestCase):
    def test_modulation_values_are_mapped_and_resolve_without_result_changes(self):
        from ui import Ui
        from ui_map import NATIVE_MENU_VALUES

        values = NATIVE_MENU_VALUES["modulation_control_1"]
        self.assertEqual(values, {
            "off": "X",
            "base_32": "32",
            "positive_half": "0.50",
            "full_depth": "1.0",
            "base_96": "96",
            "base_97": "97",
            "clear_depth": "-",
            "negative_quarter": "-0.25",
        })
        class Driver:
            def __init__(self):
                self.calls = []
                self.results = []

            def wait(self, predicate):
                self.calls.append(("wait",))
                state = {}
                if not predicate(state):
                    raise AssertionError("mapped menu value rejected")
                return state

        driver = Driver()
        ui = Ui(driver)
        with patch("frame_oracle.selected_value", return_value=True) as selected:
            for key, rendered in values.items():
                ui.expect_native_menu_value("modulation_control_1", key)
                self.assertEqual(selected.call_args.args[1], rendered)
        self.assertEqual(driver.calls, [("wait",)] * len(values))
        self.assertEqual(driver.results, [
            {"kind": "selected-menu-value", "text": rendered}
            for rendered in values.values()
        ])

    def test_modulation_menu_labels_are_mapped_to_rendered_text(self):
        from ui_map import NATIVE_MENU, NATIVE_MENU_LABEL_GEOMETRY

        self.assertEqual({key: NATIVE_MENU[key] for key in (
            "mod_devices_root", "mod_mods_root", "mod_matrix_root",
            "mod_rhythm_1", "mod_macro_1", "mod_active", "mod_value",
        )}, {
            "mod_devices_root": "DEVICES > ",
            "mod_mods_root": "MODS >",
            "mod_matrix_root": "MATRIX >",
            "mod_rhythm_1": "rhythm 1",
            "mod_macro_1": "macro 1",
            "mod_active": "active",
            "mod_value": "value",
        })
        self.assertEqual(NATIVE_MENU_LABEL_GEOMETRY["mod_matrix_root"], {"x": 4})

    def test_native_menu_label_uses_key_specific_mapped_geometry(self):
        from ui import Ui

        driver = FakeDriver()
        ui = Ui(driver)
        with patch.object(ui, "expect_menu_label") as expect:
            ui.expect_native_menu_label("mod_matrix_root")
        expect.assert_called_once_with("MATRIX >", x=4)

    def test_trig_parameter_label_resolves_stable_key(self):
        from ui import Ui, UiMapError

        driver = FakeDriver()
        ui = Ui(driver)
        with patch.object(ui, "expect_menu_label") as expect:
            ui.expect_trig_parameter("fixed_note")
            expect.assert_called_once_with("Fixed Note")
            with self.assertRaises(UiMapError):
                ui.expect_trig_parameter("rendered_label")
        self.assertEqual(driver.results, [])

    def test_native_parameter_seek_uses_mapped_menu_label_geometry(self):
        from ui import Ui

        driver = FakeDriver(states=[{}])
        with patch("frame_oracle.selected_line", return_value=True) as selected:
            Ui(driver).seek_native_menu_parameter("configured_control_1")
        self.assertEqual(selected.call_args.args[1:], ("Control 1",))
        self.assertEqual(selected.call_args.kwargs, {"x": 0, "width": 70, "top": 22})

    def test_native_menu_label_key_preserves_rendered_oracle(self):
        from ui import Ui, UiMapError

        driver = FakeDriver()
        ui = Ui(driver)
        with patch.object(ui, "expect_menu_label") as expect:
            ui.expect_native_menu_label("clock_tempo")
            expect.assert_called_once_with("tempo")
            with self.assertRaises(UiMapError):
                ui.expect_native_menu_label("not_a_menu_item")
        self.assertEqual(driver.results, [])

    def test_wait_for_header_uses_driver_wait_state_without_result(self):
        from unittest.mock import patch
        from ui import Ui

        state = {"frame": {"pixels_base64": "ignored"}}
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.live_header_matches", side_effect=lambda observed, *expected:
                   observed is state and expected == ("DEVICE", "CH01", "detail")) as live:
            result = Ui(driver).wait_for_header("midi_config", channel=1)
        live.assert_called_once_with(state, "DEVICE", "CH01", "detail")
        self.assertIs(result, state)
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [])
        # Another channel's scope is a different header: the wait fails closed.
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.live_header_matches", side_effect=lambda observed, *expected:
                   expected == ("DEVICE", "CH01", "detail")), self.assertRaises(AssertionError):
            Ui(driver).wait_for_header("midi_config", channel=2)
        self.assertEqual(driver.results, [])

    def test_expect_scale_slot_header_preserves_exact_oracle_without_result(self):
        from unittest.mock import patch
        from ui import Ui

        state = {"frame": {"pixels_base64": "ignored"}}
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.live_header_matches", return_value=True) as live:
            Ui(driver).expect_scale_slot_header(13)
        live.assert_called_once_with(state, "SCALE", "SLOT 13", "focused")
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [])
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.live_header_matches", return_value=False), \
                self.assertRaises(AssertionError):
            Ui(driver).expect_scale_slot_header(13)
        self.assertEqual(driver.results, [])

    def test_expect_steps_keeps_one_atomic_led_values_call(self):
        from ui import Ui

        driver = FakeDriver()
        Ui(driver).expect_steps({1: "selected", 2: "in_range", 64: "off"})
        self.assertEqual(driver.calls, [
            ("led_values", [(1, 4), (2, 4), (16, 7)], [15, 5, 2])
        ])

    def test_expect_steps_preserves_full_recording_led_vectors(self):
        from ui import Ui

        driver = FakeDriver()
        before_recording = {
            step: ("off" if 61 <= step <= 64 else "dark")
            for step in range(1, 65)
        }
        after_recording = {
            step: ("selected" if step in (1, 64) else
                   "off" if 61 <= step <= 64 else "dark")
            for step in range(1, 65)
        }

        ui = Ui(driver)
        ui.expect_steps(before_recording)
        ui.expect_steps(after_recording)

        cells = [((step - 1) % 16 + 1, (step - 1) // 16 + 4)
                 for step in range(1, 65)]
        self.assertEqual(driver.calls, [
            ("led_values", cells,
             [2 if 61 <= step <= 64 else 0 for step in range(1, 65)]),
            ("led_values", cells,
             [15 if step in (1, 64) else
              2 if 61 <= step <= 64 else 0
              for step in range(1, 65)]),
        ])

    def test_expect_header_waits_and_preserves_screen_header_result(self):
        from ui import Ui

        state = {"frame": {"pixels_base64": "ignored"}}
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.live_header_matches", return_value=True) as live:
            Ui(driver).expect_header("midi_config", channel=1)
        live.assert_called_once_with(state, "DEVICE", "CH01", "detail")
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [
            {"kind": "screen-header", "expected": "DEVICE CH01", "matched": True}
        ])
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.live_header_matches", return_value=False), \
                self.assertRaises(AssertionError):
            Ui(driver).expect_header("midi_config", channel=1)
        self.assertEqual(driver.results, [])

    def test_confirmation_uses_one_snapshot_and_records_identity(self):
        from ui import Ui

        driver = FakeDriver(states=[{"frame": {"pixels_base64": "ignored"}}])
        ui = Ui(driver)
        ui._header_matches = lambda state, page, params: True
        ui.confirm_header("midi_config", channel=3)
        self.assertEqual(driver.calls, [("snapshot",)])
        self.assertEqual(driver.results, [
            {"kind": "ui-confirm", "page": "midi_config", "channel": 3}
        ])

    def test_confirmation_fails_closed_with_expected_and_observed_title(self):
        from ui import Ui, UiMapError

        driver = FakeDriver(states=[{"frame": {"pixels_base64": "ignored"}}] * 34)
        ui = Ui(driver)
        ui._header_matches = lambda state, page, params: False
        ui._observed_title = lambda state: "MEMORY CH03"
        with self.assertRaisesRegex(UiMapError, "expected 'DEVICE CH03', observed 'MEMORY CH03'"):
            ui.confirm_header("midi_config", channel=3)
        # Controlled time runs one bounded logical second for the screen wipe.
        self.assertEqual(driver.calls.count(("elapse", .03)), 33)
        self.assertEqual(driver.results, [])

    def test_controlled_confirmation_lets_the_screen_wipe_finish(self):
        from ui import Ui

        wiped, settled = {"frame": "wipe"}, {"frame": "settled"}
        driver = FakeDriver(states=[wiped, wiped, settled])
        ui = Ui(driver)
        ui._header_matches = lambda state, page, params: state is settled
        ui.confirm_header("harmony", channel=1)
        self.assertEqual(driver.calls, [("snapshot",), ("elapse", .03), ("snapshot",),
                                        ("elapse", .03), ("snapshot",)])
        self.assertEqual(driver.results, [{"kind": "ui-confirm", "page": "harmony", "channel": 1}])

    def test_pick_device_preserves_seek_recipe_and_result(self):
        from ui import Ui

        expected = bytes(128 * 64 * 4)
        states = [
            {"frame": {"pixels_base64": base64.b64encode(bytes([1]) * len(expected)).decode()}},
            {"frame": {"pixels_base64": base64.b64encode(expected).decode()}},
        ]
        driver = FakeDriver(states=states)
        with patch("frame_oracle.render", return_value=expected):
            Ui(driver).pick_device("Digitakt")
        self.assertEqual(driver.calls, [
            ("snapshot",), ("enc", 3, 1), ("snapshot",), ("key", 3),
        ])
        self.assertEqual(driver.results, [
            {"kind": "device-picker-frame", "label": "Digitakt", "matched": True}
        ])


class MigrationGateTests(unittest.TestCase):
    def test_lane_path_passes_case_identity_to_persisted_project_gate(self):
        from ui_migration_gate import check_lane

        with tempfile.TemporaryDirectory() as directory:
            lane = Path(directory) / "M-PATCH-008" / "controlled"
            lane.mkdir(parents=True)
            with patch("ui_migration_gate.check_session_roots", return_value=[]) as gate:
                self.assertEqual(check_lane(lane, "controlled"), [])
            gate.assert_called_once_with(
                lane / "before", lane / "after", "controlled", case="M-PATCH-008")

    def test_cli_rejects_lane_override_that_disagrees_with_directory(self):
        from ui_migration_gate import main

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "controlled"
            path.mkdir()
            with self.assertRaises(SystemExit) as raised:
                main([str(path), "--lane", "real-time"])
        self.assertEqual(raised.exception.code, 2)

    def test_cli_accepts_lane_matching_directory(self):
        from ui_migration_gate import main

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "controlled"
            path.mkdir()
            with self.assertRaises(SystemExit) as raised:
                main([str(path), "--lane", "controlled"])
        self.assertEqual(raised.exception.code, 1)

    def test_normalize_removes_monotonic_origin_recursively(self):
        from ui_migration_gate import normalize_recipe

        recipe = [{
            "type": "midi_schedule",
            "at_monotonic_ns": 1,
            "events": [{"type": "midi", "at_monotonic_ns": 2, "bytes": [144, 60, 100]}],
        }]
        self.assertEqual(normalize_recipe(recipe), [{
            "type": "midi_schedule",
            "events": [{"type": "midi", "bytes": [144, 60, 100]}],
        }])

    def test_controlled_results_allow_only_added_ui_confirm_entries(self):
        from ui_migration_gate import compare_results

        before = [{"kind": "grid", "expected": [15], "actual": [15]}]
        after = [
            {"kind": "ui-confirm", "page": "masks", "channel": 1},
            {"kind": "grid", "expected": [15], "actual": [15]},
        ]
        self.assertEqual(compare_results(before, after, "controlled"), [])

    def test_existing_ui_confirm_is_preserved_before_allowing_additions(self):
        from ui_migration_gate import compare_results

        existing = {"kind": "ui-confirm", "page": "clock_mods", "channel": 1}
        grid = {"kind": "grid", "expected": [15], "actual": [15]}
        before = [grid, existing, {"kind": "midi", "onsets": 4}]
        extra = {"kind": "ui-confirm", "page": "masks", "channel": 1}
        after = [grid, extra, existing, {"kind": "midi", "onsets": 4}]
        self.assertEqual(compare_results(before, after, "controlled"), [])
        self.assertEqual(compare_results(before, after, "real-time"), [])
        self.assertTrue(compare_results(before, [grid, extra,
                                                {"kind": "midi", "onsets": 4}],
                                        "controlled"))
        self.assertTrue(compare_results(before, [grid,
                                                {"kind": "midi", "onsets": 4}],
                                        "real-time"))
        changed = [grid, {"kind": "ui-confirm", "page": "memory", "channel": 1},
                   {"kind": "midi", "onsets": 4}]
        self.assertTrue(compare_results(before, changed, "controlled"))

    def test_real_time_results_compare_ordered_kinds(self):
        from ui_migration_gate import compare_results

        before = [{"kind": "jitter", "maximum": .01}, {"kind": "midi", "onsets": 8}]
        after = [{"kind": "jitter", "maximum": .02}, {"kind": "midi", "onsets": 9}]
        self.assertEqual(compare_results(before, after, "real-time"), [])

    def test_gate_fails_closed_for_missing_files(self):
        from ui_migration_gate import check_lane

        with tempfile.TemporaryDirectory() as directory:
            errors = check_lane(Path(directory), "controlled")
        self.assertTrue(any("missing" in error.lower() for error in errors), errors)

    def test_gate_compares_nested_restart_sessions(self):
        from ui_migration_gate import check_lane

        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for side in ("before","after"):
                for session in (Path(),Path("restarted")):
                    target=root/side/session;target.mkdir(parents=True,exist_ok=True)
                    (target/"recipe.json").write_text("[]")
                    (target/"results.json").write_text("[]")
            (root/"after/restarted/recipe.json").write_text('[{"type":"grid"}]')
            errors=check_lane(root,"controlled")
        self.assertIn("restarted normalized recipes differ",errors)


class RecordingLifetimeInputTests(unittest.TestCase):
    def test_long_stop_keeps_shift_and_play_stop_edges_and_release_delay(self):
        from contract.recording_stop_safety import long_stop
        from ui import Ui

        driver = FakeDriver()
        driver.ui = Ui(driver)
        long_stop(driver)
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 1, "y": 8, "state": 1}),
            ("elapse", 1.2),
            ("action", {"type": "grid", "x": 1, "y": 8, "state": 0}),
            ("elapse", .06),
        ])


class MemoryUiMapTests(unittest.TestCase):
    def test_memory_counter_map_locks_captured_render_and_disjoint_geometry(self):
        """Memory's Position counter is the live detail row: four disjoint row bands."""
        from frame_oracle import DETAIL_ROWS

        self.assertEqual(DETAIL_ROWS, (27, 36, 45, 54))
        bands = [(y - 7, y + 2) for y in DETAIL_ROWS]
        self.assertTrue(all(0 <= top < bottom <= 64 for top, bottom in bands))
        self.assertTrue(all(first[1] <= second[0] for first, second in zip(bands, bands[1:])))

    def test_project_menu_map_locks_distinct_save_and_normal_rows(self):
        from ui_map import SCREEN

        menu = SCREEN["project_menu"]
        self.assertEqual(menu["root_id"], "mosaic")
        self.assertEqual(SCREEN["menu_label"], {"x": 0, "width": 70, "top": 22})
        self.assertEqual(menu["actions"]["save"], {
            "label": "< Save project", "offset": 0,
            "x": 0, "width": 70, "top": 23,
        })
        self.assertEqual(menu["actions"]["new"], {
            "label": "+ New", "offset": 2,
            "x": 0, "width": 70, "top": 22,
        })


class MemoryUiVerbTests(unittest.TestCase):
    class Driver:
        clock_mode = "controlled-experimental"

        def __init__(self, payload):
            self.payload = payload
            self.results = []
            self.calls = []

        def wait(self, predicate):
            self.calls.append(("wait",))
            state = {"frame": {"pixels_base64": base64.b64encode(self.payload).decode()}}
            if not predicate(state):
                raise AssertionError("Memory counter framebuffer rejected")
            return state

        def action(self, **value):
            self.calls.append(("action", value))

        def elapse(self, seconds):
            self.calls.append(("elapse", seconds))

    @staticmethod
    def frame_bytes():
        return 128 * 64 * 4

    def test_memory_position_waits_once_and_keeps_result_shape(self):
        from ui import Ui

        payload = bytes(self.frame_bytes())
        driver = self.Driver(payload)
        ui = Ui(driver)
        with patch("frame_oracle.selected_field_matches", return_value=True) as oracle:
            ui.expect_memory_position(2, 5)
            ui.expect_memory_position(3, 5, channel=2)
        state = {"frame": {"pixels_base64": base64.b64encode(payload).decode()}}
        self.assertEqual(oracle.call_args_list, [
            unittest.mock.call(state, "detail", "Position", "2 of 5"),
            unittest.mock.call(state, "detail", "Position", "3 of 5"),
        ])
        self.assertEqual(driver.calls, [("wait",), ("wait",)])
        self.assertEqual(driver.results, [
            {"kind": "memory-position", "current": 2, "total": 5, "frame_matched": True},
            {"kind": "memory-position", "current": 3, "total": 5, "frame_matched": True,
             "channel": 2},
        ])
        driver = self.Driver(payload)
        with patch("frame_oracle.selected_field_matches", return_value=False), \
                self.assertRaises(AssertionError):
            Ui(driver).expect_memory_position(2, 5)
        self.assertEqual(driver.results, [])

    def test_memory_position_wait_only_returns_state_without_a_result(self):
        from ui import Ui

        payload = bytes(self.frame_bytes())
        driver = self.Driver(payload)
        with patch("frame_oracle.selected_field_matches", return_value=True) as oracle:
            state = Ui(driver).wait_memory_position(2, 5)
        oracle.assert_called_once_with(state, "detail", "Position", "2 of 5")
        self.assertEqual(state["frame"]["pixels_base64"],
                         base64.b64encode(payload).decode())
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [])
        driver = self.Driver(payload)
        with patch("frame_oracle.selected_field_matches", return_value=False), \
                self.assertRaises(AssertionError):
            Ui(driver).wait_memory_position(2, 5)
        self.assertEqual(driver.results, [])

    def test_memory_position_ignores_outside_pixels(self):
        """A rendered Position row matches at every detail baseline; pixels outside it are ignored."""
        from frame_oracle import DETAIL_ROWS, _detail_row
        from ui import Ui

        for y in DETAIL_ROWS:
            with self.subTest(baseline=y):
                expected = _detail_row("Position", "2 of 5", y)
                outside = bytearray(expected)
                row_top = 0 if y - 7 > 0 else y + 2
                outside[(row_top * 128 + 5) * 4] ^= 0x7f
                for payload in (expected, bytes(outside)):
                    driver = self.Driver(payload)
                    Ui(driver).expect_memory_position(2, 5)
                    self.assertEqual(driver.results, [{
                        "kind": "memory-position", "current": 2,
                        "total": 5, "frame_matched": True,
                    }])
                # The same frame is not another count.
                with self.assertRaises(AssertionError):
                    Ui(self.Driver(expected)).expect_memory_position(2, 6)

    def test_memory_position_rejects_a_changed_pixel_in_each_counter_band(self):
        """One changed pixel in the row's label or its "2 of 5" value fails closed."""
        from frame_oracle import DETAIL_ROWS, _detail_row
        from ui import Ui

        for y in DETAIL_ROWS:
            expected = _detail_row("Position", "2 of 5", y)
            lit = [(row, col) for row in range(y - 7, y + 2) for col in range(128)
                   if expected[(row * 128 + col) * 4]]
            label = next(cell for cell in lit if 7 <= cell[1] < 64)
            value = next(cell for cell in lit if cell[1] >= 64)
            for part, (row, col) in (("label", label), ("value", value)):
                with self.subTest(baseline=y, part=part):
                    changed = bytearray(expected)
                    changed[(row * 128 + col) * 4] ^= 0x7f
                    driver = self.Driver(bytes(changed))
                    with self.assertRaises(AssertionError):
                        Ui(driver).expect_memory_position(2, 5)
                    self.assertEqual(driver.results, [])

    def test_record_key_keeps_delay_inside_held_step(self):
        from ui import Ui

        driver = self.Driver(bytes(self.frame_bytes()))
        Ui(driver).record_key(1, 72, 90, hold_seconds=.05)
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 1}),
            ("action", {"type": "midi", "port": 1, "bytes": [144, 72, 90]}),
            ("elapse", .05),
            ("action", {"type": "midi", "port": 1, "bytes": [128, 72, 0]}),
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 0}),
        ])


class ProjectActionUiVerbTests(unittest.TestCase):
    class Driver:
        clock_mode = "controlled-experimental"

        def __init__(self):
            self.calls = []
            self.results = []

        def key(self, number):
            self.calls.append(("key", number))

        def enc(self, encoder, detents):
            self.calls.append(("enc", encoder, detents))

        def action(self, **value):
            self.calls.append(("action", value))

        def elapse(self, seconds):
            self.calls.append(("elapse", seconds))

        def snapshot(self):
            self.calls.append(("snapshot",))
            return {"diagnostics": {"parameter_roots": [
                {"id": "other"}, {"id": "mosaic"},
            ]}}

        def wait(self, predicate):
            self.calls.append(("wait",))
            if not predicate({"frame": {}}):
                raise AssertionError("project action label not selected")
            return {"frame": {}}

    def test_new_action_recipe_results_and_geometry_are_stable(self):
        from ui import Ui

        driver = self.Driver()
        ui = Ui(driver)
        with patch("frame_oracle.selected_line", return_value=True) as selected:
            ui.select_project_action("new")
        self.assertEqual(driver.calls, [
            ("key", 1), ("enc", 1, 4), ("key", 3), ("wait",),
            ("snapshot",), ("enc", 2, 1), ("key", 3),
            ("enc", 2, -60), ("enc", 2, 1), ("wait",),
            ("enc", 2, 2), ("wait",), ("key", 3),
        ])
        self.assertEqual(driver.results, [
            {"kind": "selected-menu-label", "text": "LEVELS >"},
            {"kind": "selected-menu-label", "text": "< Save project"},
            {"kind": "selected-menu-label", "text": "+ New"},
        ])
        self.assertEqual([item.args[1] for item in selected.call_args_list],
                         ["LEVELS >", "< Save project", "+ New"])
        self.assertEqual([item.kwargs for item in selected.call_args_list], [
            {"x": 0, "width": 70, "top": 22},
            {"x": 0, "width": 70, "top": 23},
            {"x": 0, "width": 70, "top": 22},
        ])

    def test_unknown_project_action_fails_closed_without_input(self):
        from ui import Ui, UiMapError

        driver = self.Driver()
        with self.assertRaisesRegex(UiMapError, "unknown project action"):
            Ui(driver).select_project_action("not-a-project-action")
        self.assertEqual(driver.calls, [])

    def test_project_file_search_keeps_native_event_recipe_and_no_new_results(self):
        from ui import Ui

        driver = self.Driver()
        with patch("frame_oracle.selected_line",
                   side_effect=[True, True, False, False, True]) as selected:
            Ui(driver).select_project_file("newB.ptn", returning=True)
        self.assertEqual(driver.calls, [
            ("key", 1), ("enc", 2, -60), ("enc", 2, 1), ("wait",),
            ("enc", 2, 1), ("wait",), ("key", 3),
            ("action", {"type": "enc", "n": 2, "delta": -100}),
            ("snapshot",),
            ("action", {"type": "enc", "n": 2, "delta": 1}),
            ("elapse", .03), ("snapshot",),
            ("action", {"type": "enc", "n": 2, "delta": 1}),
            ("elapse", .03), ("snapshot",),
        ])
        self.assertEqual([call.args[1] for call in selected.call_args_list],
                         ["< Save project", "> Load project", "newB.ptn",
                          "newB.ptn", "newB.ptn"])
        self.assertEqual(driver.results, [
            {"kind": "selected-menu-label", "text": "< Save project"},
            {"kind": "selected-menu-label", "text": "> Load project"},
        ])

    def test_project_file_search_fails_after_exactly_thirty_checks(self):
        from ui import Ui

        driver = self.Driver()
        with patch("frame_oracle.selected_line",
                   side_effect=[True, True] + [False] * 30):
            with self.assertRaisesRegex(AssertionError,
                                        "Project file not reached: missing.ptn"):
                Ui(driver).select_project_file("missing.ptn", returning=True)
        self.assertEqual(driver.calls.count(("snapshot",)), 30)
        self.assertEqual(driver.calls.count(("action", {
            "type": "enc", "n": 2, "delta": 1,
        })), 30)
        self.assertEqual(driver.calls.count(("elapse", .03)), 30)

    def test_rhythm_doctor_controls_keep_the_native_input_trace(self):
        from ui import Ui

        driver = FakeDriver()
        ui = Ui(driver)
        ui.select_rhythm_doctor_algorithm("rhythm_doctor")
        ui.select_rhythm_doctor_algorithm("drum")
        ui.select_rhythm_doctor_lane("CYM")
        ui.tap_control("withdrawn_lane_bass")
        ui.tap_rhythm_doctor_phrase_button("centre")
        ui.rhythm_doctor_setup_field(-2)
        ui.adjust_rhythm_doctor_setup_value(14)
        ui.rhythm_doctor_key_edge("discard_draft", True)
        ui.rhythm_doctor_key_edge("discard_draft", False)
        ui.rhythm_doctor_capture_edge(True)
        ui.rhythm_doctor_capture_edge(False)
        ui.expect_rhythm_doctor_lanes({"reserved": "dark", "BD": "blink_low",
                                       "SD": "blink_low", "CYM": "selected",
                                       "withdrawn_BASS": "dark", "retired": "dark"})

        self.assertEqual(driver.calls, [
            ("tap", 16, 2), ("tap", 12, 2), ("tap", 5, 2), ("tap", 6, 2),
            ("tap", 11, 8),
            ("action", {"type": "enc", "n": 2, "delta": -2}),
            ("action", {"type": "enc", "n": 3, "delta": 14}),
            ("action", {"type": "key", "n": 2, "state": 1}),
            ("action", {"type": "key", "n": 2, "state": 0}),
            ("action", {"type": "grid", "x": 1, "y": 2, "state": 1}),
            ("action", {"type": "grid", "x": 1, "y": 2, "state": 0}),
            ("led_values", [(2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2)],
             [0, 4, 4, 15, 0, 0]),
        ])

    def test_rhythm_doctor_screen_verbs_keep_exact_rendered_regions(self):
        from ui import Ui

        driver = FakeDriver()
        ui = Ui(driver)
        with patch.object(ui, "_wait_rhythm_doctor_render") as observe:
            ui.expect_rhythm_doctor_header()
            ui.expect_rhythm_doctor_tooltip("NOT_READY")
            ui.expect_rhythm_doctor_setup("INPUT", "auto", 120, "STEREO")
            ui.expect_rhythm_doctor_status("CYM / READY")

        self.assertEqual(observe.call_args_list[0].args[0], [
            (0, 9, 10, "RHYTHM DOCTOR"), (120, 9, 10, "m"),
        ])
        self.assertEqual(observe.call_args_list[0].kwargs, {})
        self.assertEqual(observe.call_args_list[1].args[0], [(0, 62, 10, "NOT_READY")])
        self.assertEqual(observe.call_args_list[1].args[1],
                         {"left": 0, "right": 100, "top": 55, "bottom": 64})
        self.assertEqual(observe.call_args_list[2].args[0], [
            (0, 9, 10, "RHYTHM DOCTOR"), (120, 9, 10, "m"),
            (0, 22, 10, "SETUP / INPUT"), (0, 34, 10, " TEMPO AUTO"),
            (0, 46, 10, " MANUAL BPM 120"), (0, 58, 10, ">INPUT STEREO"),
        ])
        self.assertEqual(observe.call_args_list[2].kwargs, {"full": True})
        self.assertEqual(observe.call_args_list[3].args[0], [(0, 22, 10, "CYM / READY")])
        self.assertEqual(observe.call_args_list[3].args[1],
                         {"left": 0, "right": 97, "top": 15, "bottom": 26})
        self.assertEqual(driver.results, [])

    def test_rhythm_doctor_pixel_verbs_preserve_rgb_only_regions(self):
        import base64
        from ui import Ui

        expected = bytes(128 * 64 * 4)
        actual = bytearray(expected)
        # The legacy frame oracle deliberately ignores alpha. Its tooltip
        # oracle also ignores pixels to the right of the text-owning region.
        for y in range(64):
            for x in range(128):
                alpha = (y * 128 + x) * 4 + 3
                actual[alpha] = 255
        actual[(60 * 128 + 110) * 4] = 9
        driver = FakeDriver(states=[{
            "frame": {"pixels_base64": base64.b64encode(actual).decode("ascii")},
        }])
        ui = Ui(driver)
        with patch("frame_oracle.render", return_value=expected):
            ui.expect_rhythm_doctor_tooltip("NOT_READY")

        inside_region = bytearray(actual)
        inside_region[(60 * 128 + 10) * 4] = 9
        driver = FakeDriver(states=[{
            "frame": {"pixels_base64": base64.b64encode(inside_region).decode("ascii")},
        }])
        ui = Ui(driver)
        with patch("frame_oracle.render", return_value=expected), \
                self.assertRaises(AssertionError):
            ui.expect_rhythm_doctor_tooltip("NOT_READY")


    def test_midi_mask_recording_verb_preserves_native_edge_and_timing_recipe(self):
        from ui import Ui

        driver = FakeDriver()
        Ui(driver).record_midi_mask_on_step(2, 72, 90)

        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 2, "y": 4, "state": 1}),
            ("action", {"type": "midi", "port": 1, "bytes": [144, 72, 90]}),
            ("elapse", .05),
            ("action", {"type": "midi", "port": 1, "bytes": [128, 72, 0]}),
            ("action", {"type": "grid", "x": 2, "y": 4, "state": 0}),
            ("elapse", .1),
        ])

    def test_mosaic_option_scan_and_observations_keep_existing_row_schema(self):
        from ui import Ui

        driver = FakeDriver(states=[{}, {}, {}, {}])
        ui = Ui(driver)
        with patch("frame_oracle.selected_line", side_effect=[False, True]):
            ui.seek_mosaic_option_from_current("scale_lock_until_pattern_end")
        with patch("frame_oracle.selected_line", return_value=True), \
                patch("frame_oracle.selected_value", return_value=True):
            ui.expect_mosaic_option_label("scale_lock_until_pattern_end")
            ui.expect_mosaic_option_value(True)

        self.assertEqual(driver.calls, [
            ("snapshot",), ("enc", 2, 1), ("snapshot",), ("wait",), ("wait",),
        ])
        self.assertEqual(driver.results, [
            {"kind": "selected-menu-label", "text": "Scales lock until ptn end"},
            {"kind": "selected-menu-value", "text": "On"},
        ])


class RhythmDoctorSurfaceRecipeTests(unittest.TestCase):
    def test_owned_input_routes_through_driver_ui(self):
        from rhythm_doctor_surface import owned_input_and_transport_gate

        driver = Mock()
        driver.results = []
        with patch("rhythm_doctor_surface.fifth_algorithm"), \
                patch("rhythm_doctor_surface.stopped_setup_controls"):
            owned_input_and_transport_gate(driver)

        self.assertEqual(driver.ui.expect_rhythm_doctor_lanes.call_count, 5)
        driver.ui.rhythm_doctor_capture_edge.assert_any_call(True)
        driver.ui.rhythm_doctor_capture_edge.assert_any_call(False)
        driver.ui.play.assert_called_once_with()
        driver.ui.stop.assert_called_once_with()
        self.assertEqual([row["kind"] for row in driver.results], [
            "rhythm-doctor-record-ownership",
            "rhythm-doctor-norns-keys",
            "rhythm-doctor-transport-gate",
        ])


if __name__ == "__main__":
    unittest.main()

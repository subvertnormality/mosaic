"""Characterisation of the UI migration boundary, outside the player manual."""
import ast
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BEHAVIOUR = Path(__file__).resolve().parent
if str(BEHAVIOUR) not in sys.path:
    sys.path.insert(0, str(BEHAVIOUR))


class TrigParameterUiMigrationTests(unittest.TestCase):
    def test_pending_song_transition_uses_row_one_pattern_slots(self):
        from ui_map import control_cell

        source = ast.parse((BEHAVIOUR / "trig_parameter_interactions.py").read_text())
        workflow = next(node for node in source.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "pending_parameter_lock_song_transition")
        calls = [node for node in ast.walk(workflow)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
        copies = [node for node in calls if node.func.attr == "copy_slot"]
        self.assertEqual(len(copies), 1)
        self.assertEqual([(item.arg, item.value.value) for item in copies[0].keywords],
                         [("control", "song_pattern_slot")])
        pattern_taps = [node for node in calls if node.func.attr == "tap_control"
                        and node.args and isinstance(node.args[0], ast.Constant)
                        and node.args[0].value == "song_pattern_slot"]
        self.assertGreaterEqual(len(pattern_taps), 2)
        self.assertEqual([control_cell("song_pattern_slot", slot) for slot in (1, 2)],
                         [(1, 1), (2, 1)])

    def test_ordinary_parameter_cases_have_no_raw_ui(self):
        from ui_layer_guard import raw_sites
        self.assertEqual(raw_sites(BEHAVIOUR / "trig_parameter_interactions.py"), [])

    def test_ordinary_case_has_no_rendered_navigation_labels(self):
        source = ast.parse((BEHAVIOUR / "trig_parameter_interactions.py").read_text())
        forbidden = {"CC 1", "Control 1", "NRPN14", "Fixed Note",
                     "Quantised Fixed Note", "Trigless locks",
                     "LEVELS >", "Ch. 1 Trig Locks", "Ch. 2 Device Config"}
        found = {node.value for node in ast.walk(source)
                 if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        self.assertEqual(found & forbidden, set())

    def test_recording_option_seek_keeps_native_saturation_and_scan(self):
        from ui import Ui
        from test_ui import FakeDriver
        driver = FakeDriver(states=[{}, {}, {}])
        with patch("frame_oracle.selected_line", side_effect=[False, False, True]) as selected:
            Ui(driver).seek_mosaic_option("trigless_locks",
                                         failure="Trigless option not reached during recording")
        self.assertEqual(driver.calls, [
            ("action", {"type": "enc", "n": 2, "delta": -126}),
            ("elapse", .15), ("snapshot",), ("enc", 2, 1),
            ("snapshot",), ("enc", 2, 1), ("snapshot",),
        ])
        self.assertEqual(selected.call_args.kwargs, {"top": 23})
        self.assertEqual(selected.call_args.args[1], "Trigless locks")

    def test_recording_option_seek_fails_after_exactly_forty_observations(self):
        from ui import Ui
        from test_ui import FakeDriver
        driver = FakeDriver(states=[{}] * 40)
        with patch("frame_oracle.selected_line", return_value=False):
            with self.assertRaisesRegex(AssertionError, "Trigless option not reached during recording"):
                Ui(driver).seek_mosaic_option(
                    "trigless_locks", failure="Trigless option not reached during recording")
        self.assertEqual(driver.calls.count(("snapshot",)), 40)
        self.assertEqual(driver.calls.count(("enc", 2, 1)), 40)

    def test_recording_option_seek_accepts_first_and_last_row(self):
        from ui import Ui
        from test_ui import FakeDriver
        for offset in (0, 39):
            with self.subTest(offset=offset):
                driver = FakeDriver(states=[{}] * (offset + 1))
                with patch("frame_oracle.selected_line",
                           side_effect=[False] * offset + [True]):
                    Ui(driver).seek_mosaic_option("trigless_locks")
                self.assertEqual(driver.calls.count(("snapshot",)), offset + 1)
                self.assertEqual(driver.calls.count(("enc", 2, 1)), offset)
                self.assertEqual(driver.results, [])

    def test_invalid_recording_option_fails_before_input(self):
        from ui import Ui, UiMapError
        from test_ui import FakeDriver
        driver = FakeDriver()
        with self.assertRaises(UiMapError):
            Ui(driver).seek_mosaic_option("missing")
        self.assertEqual(driver.calls, [])

    def test_recording_native_entry_preserves_immediate_key_recipe(self):
        from ui import Ui
        from test_ui import FakeDriver
        driver = FakeDriver()
        ui = Ui(driver)
        with patch.object(ui, "expect_menu_label") as label:
            ui.open_native_parameters(observe_entry=False)
        self.assertEqual(driver.calls, [("key", 1), ("enc", 1, 4), ("key", 3)])
        label.assert_called_once_with("LEVELS >")

    def test_page_selection_contract_retains_its_registered_owner(self):
        import cases
        from cases import CASES
        from unittest.mock import sentinel
        import contract.trig_parameter_interactions as owner
        from trig_parameter_interactions import live_parameter_recording as ordinary
        run = CASES["M-REC-PARAM-004"]["run"]
        self.assertIs(run, owner.live_parameter_recording_scale_page)
        self.assertEqual(run.__module__, 'contract.trig_parameter_interactions')
        self.assertIsNone(run.__closure__)
        with patch.object(owner, 'live_parameter_recording',
                          return_value=sentinel.result) as helper:
            self.assertIs(run(sentinel.driver), sentinel.result)
        helper.assert_called_once_with(sentinel.driver,
                                       switch_return=True, scale_page=True)
        self.assertIs(CASES["M-REC-PARAM-001"]["run"],
                      cases.live_parameter_recording_with_visual_checkpoints)

    def test_record_button_contract_oracle_requires_native_dark_blink_phase_or_unlit_state(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from contract.trig_parameter_interactions import expect_record_button_state

        for armed, level, expected, kind in (
                (True, 12, 12, "parameter-recording-arm-led"),
                (False, 2, 2, "parameter-recording-disarmed-led")):
            with self.subTest(armed=armed, level=level):
                ui = SimpleNamespace(control_cell=Mock(return_value=(2, 8)))
                context = SimpleNamespace(ui=ui, results=[])
                grid = [0] * 128
                grid[(8 - 1) * 16 + 2 - 1] = level
                state = {"grid": grid}
                def wait(predicate, timeout=None):
                    self.assertEqual(timeout, 1)
                    if not predicate(state):
                        raise AssertionError("Record LED did not reach the requested native phase")
                    return state
                context.wait = wait

                self.assertIs(expect_record_button_state(context, armed), state)
                ui.control_cell.assert_called_once_with("record")
                result = context.results[0]
                self.assertEqual(result["kind"], kind)
                self.assertEqual(result["cell"], [2, 8])
                self.assertEqual(result["expected"], expected)
                self.assertEqual(result["actual"], level)
                self.assertEqual(result["citation"], "manual:arm-live-record")
                self.assertIn("characterisation", result)

        # 9/15 were guesses from nominal levels, not this renderer's captured
        # native phase. Level 2 is also a valid *other* armed blink phase, so a
        # static frame at 2 must wait rather than be misreported as disarmed.
        for armed, level in ((True, 9), (True, 15), (True, 2),
                             (False, 12), (False, 15)):
            with self.subTest(rejected_armed=armed, level=level):
                ui = SimpleNamespace(control_cell=Mock(return_value=(2, 8)))
                context = SimpleNamespace(ui=ui, results=[])
                grid = [0] * 128
                grid[(8 - 1) * 16 + 2 - 1] = level
                state = {"grid": grid}
                def wait(predicate, timeout=None):
                    self.assertEqual(timeout, 1)
                    if not predicate(state):
                        raise AssertionError("Record LED did not reach the requested native phase")
                    return state
                context.wait = wait
                with self.assertRaisesRegex(AssertionError, "requested native phase"):
                    expect_record_button_state(context, armed)
                self.assertEqual(context.results, [])
    def test_live_record_case_forwards_visual_checkpoint_opt_in(self):
        import inspect
        import cases
        from trig_parameter_interactions import live_parameter_recording as helper
        from unittest.mock import sentinel

        self.assertEqual(inspect.signature(helper).parameters["visual_checkpoints"].default,
                         False)
        run = cases.CASES["M-REC-PARAM-001"]["run"]
        self.assertIs(run, cases.live_parameter_recording_with_visual_checkpoints)
        with patch.object(cases, "live_parameter_recording",
                          return_value=sentinel.result) as delegated:
            self.assertIs(run(sentinel.driver), sentinel.result)
        delegated.assert_called_once_with(sentinel.driver, visual_checkpoints=True)

    def test_recording_option_oracle_retains_label_value_and_row(self):
        from ui import Ui
        from test_ui import FakeDriver
        ui = Ui(FakeDriver())
        with patch.object(ui, "expect_menu_option_row") as oracle:
            ui.expect_mosaic_option("trigless_locks", True)
            ui.expect_mosaic_option("trigless_locks", False)
        self.assertEqual([call.args for call in oracle.call_args_list],
                         [("Trigless locks", "On"), ("Trigless locks", "Off")])
        self.assertEqual([call.kwargs for call in oracle.call_args_list],
                         [{"top": 23}, {"top": 23}])

    def test_page_navigation_uses_named_origins(self):
        source = ast.parse((BEHAVIOUR / "trig_parameter_interactions.py").read_text())
        for node in ast.walk(source):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "turn" and node.args and isinstance(node.args[0], ast.Constant):
                    self.assertNotEqual(node.args[0].value, 1,
                                        "Channel page offsets belong in the UI map")

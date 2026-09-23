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
    def test_ordinary_parameter_cases_have_no_raw_ui(self):
        from ui_layer_guard import raw_sites
        self.assertEqual(raw_sites(BEHAVIOUR / "trig_parameter_interactions.py"), [])

    def test_ordinary_case_has_no_rendered_navigation_labels(self):
        source = ast.parse((BEHAVIOUR / "trig_parameter_interactions.py").read_text())
        forbidden = {"CC 1", "Control 1", "NRPN14", "Fixed Note",
                     "Quantised Fixed Note", "Trig Probability", "Trigless locks",
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
        from cases import CASES
        from contract.trig_parameter_interactions import live_parameter_recording
        from trig_parameter_interactions import live_parameter_recording as ordinary
        self.assertIs(CASES["M-REC-PARAM-004"]["run"].__globals__[
            "contract_live_parameter_recording"], live_parameter_recording)
        self.assertIs(CASES["M-REC-PARAM-001"]["run"], ordinary)

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

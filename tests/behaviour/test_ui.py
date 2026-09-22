import sys
import base64
import tempfile
import unittest
from unittest.mock import patch
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
    def test_channel_page_order_is_current_1_4_surface(self):
        from ui_map import CHANNEL_PAGES

        self.assertEqual(
            list(CHANNEL_PAGES),
            ["masks", "trig_locks", "memory", "clock_mods", "midi_config",
             "note_dashboard", "merge_shape", "harmony"],
        )

    def test_every_grid_cell_has_exactly_one_control_on_each_page(self):
        from ui_map import grid_partition

        for page in ("trigger_editor", "channel_editor", "song_editor", "scale_editor"):
            cells = grid_partition(page)
            self.assertEqual(len(cells), 128, page)
            self.assertEqual(len(set(cells)), 128, page)
    def test_song_pattern_slots_have_stable_row_one_keys(self):
        from ui_map import control_cell

        self.assertEqual(control_cell("song_pattern_slot", 2), (2, 1))

    def test_channel_octave_uses_a_stable_signed_key(self):
        from ui_map import control_cell, grid_partition

        self.assertEqual(control_cell("channel_octave", 1), (11, 8))
        self.assertEqual(grid_partition("channel_editor")[(11, 8)],
                         ("channel_octave", 1))

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
    def ui(self):
        from ui import Ui

        driver = FakeDriver()
        return driver, Ui(driver)

    def test_channel_page_uses_explicit_origin_and_map_offset(self):
        driver, ui = self.ui()
        ui.channel_page("harmony", "masks", confirm=False)
        self.assertEqual(driver.calls, [("enc", 1, 7)])

    def test_channel_page_can_preserve_a_clamped_boundary_recipe(self):
        driver, ui = self.ui()
        ui.channel_page("masks", "midi_config", confirm=False, saturate=True)
        self.assertEqual(driver.calls, [("enc", 1, -5)])

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

    def test_gesture_preserves_non_nested_release_order(self):
        driver, ui = self.ui()
        ui.gesture([("step", 1), ("song_slot", 2)], [("step", 1), ("song_slot", 2)])
        self.assertEqual(driver.calls, [
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 1}),
            ("action", {"type": "grid", "x": 2, "y": 3, "state": 1}),
            ("action", {"type": "grid", "x": 1, "y": 4, "state": 0}),
            ("action", {"type": "grid", "x": 2, "y": 3, "state": 0}),
        ])

    def test_encoder_event_preserves_one_native_event_without_timing(self):
        driver, ui = self.ui()
        result = ui.encoder_event(3, -2)
        self.assertEqual(driver.calls, [
            ("action", {"type": "enc", "n": 3, "delta": -2}),
        ])
        self.assertEqual(result, {"native": "ack"})

    def test_configure_keeps_the_historical_physical_recipe(self):
        driver, ui = self.ui()
        ui.expect_header = lambda page, **params: driver.calls.append(("header", page, params))
        ui.configure()
        self.assertEqual(driver.calls, [
            ("tap", 3, 8), ("enc", 1, 4), ("enc", 3, 1), ("key", 3),
            ("tap", 5, 8),
            ("tap", 1, 4), ("tap", 2, 4), ("tap", 3, 4), ("tap", 4, 4),
            ("tap", 5, 8),
            ("tap", 1, 7), ("tap", 2, 6), ("tap", 3, 5), ("tap", 4, 4),
            ("tap", 5, 8),
            ("tap", 1, 1), ("tap", 2, 2), ("tap", 3, 3), ("tap", 4, 4),
            ("tap", 3, 8), ("tap", 1, 2),
            ("hold_tap", (1, 4), (4, 4)),
            ("led_values", [(1, 2)], [15]),
            ("header", "midi_config", {"channel": 1}),
        ])

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


class UiObservationTests(unittest.TestCase):
    def test_wait_for_header_uses_driver_wait_state_without_result(self):
        from unittest.mock import patch
        from ui import Ui

        state = {"frame": {"pixels_base64": "ignored"}}
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.header", return_value=b"expected") as header, \
             patch("frame_oracle.matches", side_effect=lambda observed, expected:
                   observed is state and expected == b"expected") as matches:
            result = Ui(driver).wait_for_header("midi_config", channel=1)
        header.assert_called_once_with("Ch. 1 Device Config", selected=5, tabs=8)
        matches.assert_called_once_with(state, b"expected")
        self.assertIs(result, state)
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [])

    def test_expect_scale_slot_header_preserves_exact_oracle_without_result(self):
        from unittest.mock import patch
        from ui import Ui

        state = {"frame": {"pixels_base64": "ignored"}}
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.header", return_value=b"expected") as header, \
             patch("frame_oracle.matches", return_value=True) as matches:
            Ui(driver).expect_scale_slot_header(13)
        header.assert_called_once_with("Scale slot 13 ", selected=1, tabs=3)
        matches.assert_called_once_with(state, b"expected")
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [])

    def test_expect_steps_keeps_one_atomic_led_values_call(self):
        from ui import Ui

        driver = FakeDriver()
        Ui(driver).expect_steps({1: "selected", 2: "in_range", 64: "off"})
        self.assertEqual(driver.calls, [
            ("led_values", [(1, 4), (2, 4), (16, 7)], [15, 5, 2])
        ])

    def test_expect_header_waits_and_preserves_screen_header_result(self):
        from ui import Ui

        state = {"frame": {"pixels_base64": "ignored"}}
        driver = FakeDriver(states=[state])
        with patch("frame_oracle.header", return_value=b"expected") as header, \
             patch("frame_oracle.matches", return_value=True) as matches:
            Ui(driver).expect_header("midi_config", channel=1)
        header.assert_called_once_with("Ch. 1 Device Config", selected=5, tabs=8)
        matches.assert_called_once_with(state, b"expected")
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [
            {"kind": "screen-header", "expected": "Ch. 1 Device Config", "matched": True}
        ])

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

        driver = FakeDriver(states=[{"frame": {"pixels_base64": "ignored"}}])
        ui = Ui(driver)
        ui._header_matches = lambda state, page, params: False
        ui._observed_title = lambda state: "Ch. 3 Memory"
        with self.assertRaisesRegex(UiMapError, "Ch. 3 Device Config.*Ch. 3 Memory"):
            ui.confirm_header("midi_config", channel=3)

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


if __name__ == "__main__":
    unittest.main()

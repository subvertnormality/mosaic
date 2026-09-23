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
            "fixed_note": "Fixed Note",
            "quantised_fixed_note": "Quantised Fixed Note",
            "trig_probability": "Trig Probability",
            "chord_note_arpeggio": "Chord Note Arpeggio",
            "chord_pattern": "Chord Pattern",
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
    def ui(self):
        from ui import Ui

        driver = FakeDriver()
        return driver, Ui(driver)

    def test_channel_page_uses_explicit_origin_and_map_offset(self):
        driver, ui = self.ui()
        ui.channel_page("harmony", "masks", confirm=False)
        self.assertEqual(driver.calls, [("enc", 1, 7)])

    def test_pattern_harmony_clock_page_and_value_verbs_keep_native_recipe(self):
        driver, ui = self.ui()
        ui.channel_page("clock_mods", "midi_config", channel=2, confirm=False)
        ui.set_value(-2)
        ui.channel_page("harmony", "clock_mods", channel=2, confirm=False)
        ui.set_value(2)
        ui.select_field("tone_0_role", offset=3)
        self.assertEqual(driver.calls, [
            ("enc", 1, -1),
            ("enc", 3, -2),
            ("enc", 1, 4),
            ("enc", 3, 2),
            ("enc", 2, 3),
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
        from persisted_ranges import rejected_saved_range

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

    def test_channel_page_can_preserve_a_clamped_boundary_recipe(self):
        driver, ui = self.ui()
        ui.channel_page("masks", "midi_config", confirm=False, saturate=True)
        self.assertEqual(driver.calls, [("enc", 1, -5)])

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
            def wait(self, predicate, timeout=3):
                self.calls.append(("wait", timeout))
                states = [
                    {"diagnostics": {"menu_mode": False}},
                    {"diagnostics": {"menu_mode": True}},
                ]
                self.matches = [predicate(state) for state in states]
                return states[-1]

        driver = Driver(clock_mode="real-time")
        ui = Ui(driver)
        with patch.object(ui, "expect_menu_label"):
            ui.open_native_parameters()
        self.assertEqual(driver.calls, [
            ("key", 1), ("wait", 1), ("enc", 1, 4), ("key", 3),
        ])
        self.assertEqual(driver.matches, [False, True])

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
                           ("quantised_fixed_note", "Quantised Fixed Note")):
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
        cases.assert_durations = lambda context, notes, lengths: self.assertEqual(
            lengths, [1, 1, 1]
        )

        with patch.dict(sys.modules, {"cases": cases}):
            quantised_fixed_table(case, profile="major")

        self.assertEqual(driver.calls[:4], [
            ("tap", 3, 8), ("enc", 1, 4), ("enc", 3, 1), ("key", 3),
        ])
        self.assertEqual(driver.calls[19:24], [
            ("tap", 3, 8), ("tap", 1, 2),
            ("hold_tap", (1, 4), (4, 4)),
            ("led_values", [(1, 2)], [15]),
            ("header", "midi_config", {"channel": 1}),
        ])
        self.assertEqual(driver.calls[24:26], [
            ("enc", 1, -3),
            ("assign_trig_parameter_key", "quantised_fixed_note"),
        ])
        self.assertEqual(driver.calls[26:40], [
            ("enc", 3, delta) for delta in
            (1, 1, 2, 3, 1, 4, 1, 48, 1, 2, 3, 4, 56, 1)
        ])
        self.assertEqual(len(case.results), 14)

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


class MemoryUiMapTests(unittest.TestCase):
    def test_memory_counter_map_locks_captured_render_and_disjoint_geometry(self):
        from ui_map import SCREEN

        self.assertEqual(SCREEN["memory_position"], {
            "frame_width": 128,
            "frame_height": 64,
            "channels": 3,
            "bytes_per_pixel": 4,
            "font_size": 10,
            "antialias": 1,
            "level": 15,
            "bands": {
                "current": {
                    "left": 0, "right": 16, "top": 13, "bottom": 26,
                    "x": 0, "baseline": 23,
                },
                "total": {
                    "left": 0, "right": 16, "top": 39, "bottom": 52,
                    "x": 0, "baseline": 49,
                },
            },
        })

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
        from ui_map import SCREEN

        data = SCREEN["memory_position"]
        return data["frame_width"] * data["frame_height"] * data["bytes_per_pixel"]

    def test_memory_position_waits_once_and_keeps_result_shape(self):
        from ui import Ui
        from ui_map import SCREEN

        payload = bytes(self.frame_bytes())
        driver = self.Driver(payload)
        ui = Ui(driver)
        with patch("frame_oracle.render", return_value=payload) as render:
            ui.expect_memory_position(2, 5)
        bands = SCREEN["memory_position"]["bands"]
        self.assertEqual(render.call_args.args[0], [
            [bands["current"]["x"], bands["current"]["baseline"], 15, "2"],
            [bands["total"]["x"], bands["total"]["baseline"], 15, "5"],
        ])
        self.assertEqual(render.call_args.kwargs, {"font_size": 10, "antialias": 1})
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [{
            "kind": "memory-position", "current": 2,
            "total": 5, "frame_matched": True,
        }])

    def test_memory_position_wait_only_returns_state_without_a_result(self):
        from ui import Ui

        payload = bytes(self.frame_bytes())
        driver = self.Driver(payload)
        with patch("frame_oracle.render", return_value=payload):
            state = Ui(driver).wait_memory_position(2, 5)
        self.assertEqual(state["frame"]["pixels_base64"],
                         base64.b64encode(payload).decode())
        self.assertEqual(driver.calls, [("wait",)])
        self.assertEqual(driver.results, [])

    def test_memory_position_ignores_outside_pixels(self):
        from ui import Ui

        expected = bytes(self.frame_bytes())
        outside = bytearray(expected)
        outside[0] = 7
        driver = self.Driver(bytes(outside))
        with patch("frame_oracle.render", return_value=expected):
            Ui(driver).expect_memory_position(2, 2)
        self.assertTrue(driver.results[0]["frame_matched"])

    def test_memory_position_rejects_a_changed_pixel_in_each_counter_band(self):
        from ui import Ui
        from ui_map import SCREEN

        data = SCREEN["memory_position"]
        expected = bytes(self.frame_bytes())
        for band_name, band in data["bands"].items():
            with self.subTest(band=band_name):
                changed = bytearray(expected)
                index = ((band["top"] * 128 + band["left"]) * 4)
                changed[index] = 7
                driver = self.Driver(bytes(changed))
                with patch("frame_oracle.render", return_value=expected):
                    with self.assertRaises(AssertionError):
                        Ui(driver).expect_memory_position(2, 2)

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


if __name__ == "__main__":
    unittest.main()

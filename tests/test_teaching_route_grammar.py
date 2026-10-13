import copy
import json
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator

from manual_teaching_v8 import _validate_actions


def grid(x, y, state):
    return {"type": "grid", "x": x, "y": y, "state": state}


def base_native(interval, target, prefix=None):
    return {
        "contract_schema": "mosaic-native-transition-v3",
        "transition_scope": "interval",
        "from_step_id": "start",
        "to_step_id": "target",
        "scene_input_prefix": prefix or [{"step_id": "start", "inputs": []}],
        "step_interval": interval,
        "to_step": target,
    }


class TeachingRouteGrammarTests(unittest.TestCase):
    def test_selected_parameter_requires_exact_slot_value_marker_and_held_cell(self):
        held = {"kind": "selected-param", "passed": True, "field_label": "Trig Probability",
                "field_slot": 2, "value": "0", "field_marker": "L"}
        inputs = [grid(3, 4, 1), {"type": "enc", "n": 3, "delta": -1}, grid(3, 4, 0)]
        interval = [
            {"id": "start", "inputs": [], "expect": {},
             "output": {"binding": {"assertion": {"kind": "start"}}, "grid": [0] * 128}},
            {"id": "step2-lock-readout", "inputs": inputs[:2], "expect": {},
             "output": {"binding": {"assertion": held}, "grid": [0] * 128}},
            {"id": "release-step2", "inputs": [inputs[2]], "expect": {},
             "output": {"binding": {"assertion": {"kind": "released"}}, "grid": [0] * 128}},
            {"id": "target", "inputs": [], "expect": {},
             "output": {"binding": {"assertion": {"kind": "target"}}, "grid": [0] * 128}},
        ]
        native = base_native(interval, interval[-1])
        authored = {"actions": [
            {"id": "hold-step2", "kind": "hold-grid", "label": "Hold Step 2", "x": 3, "y": 4},
            {"id": "set-zero", "kind": "select-value", "label": "Set Trig Probability to 0",
             "control": "E3", "field_label": "Trig Probability", "field_slot": 2,
             "expected_marker": "L", "while_held_grid": {"x": 3, "y": 4}, "value": "0"},
            {"id": "release-step2", "kind": "release-grid", "label": "Release Step 2", "x": 3, "y": 4},
            {"id": "preview", "kind": "preview-recorded-result", "label": "Preview", "target_step_id": "target"},
        ]}
        proof = _validate_actions(authored, native, "target", {})
        self.assertEqual(proof[1]["checkpoint_step_id"], "step2-lock-readout")
        self.assertEqual(proof[1]["proof"]["field_slot"], 2)
        self.assertEqual(proof[1]["proof"]["field_marker"], "L")
        for field, wrong in (("field_slot", 3), ("expected_marker", None), ("value", "1"),
                             ("while_held_grid", {"x": 4, "y": 4})):
            mutated = copy.deepcopy(authored)
            mutated["actions"][1][field] = wrong
            with self.assertRaises(Exception):
                _validate_actions(mutated, native, "target", {})
        missing_hold = copy.deepcopy(authored)
        missing_hold["actions"].pop(0)
        with self.assertRaises(Exception):
            _validate_actions(missing_hold, native, "target", {})

    def test_parameter_request_match_also_checks_the_exact_held_cell(self):
        raw = {"kind": "selected-param", "passed": True, "slot": 2, "value": "0", "marker": "L"}
        native = self._held_native(raw)
        authored = self._held_actions()
        req = {"parameter_readout_equals": {"readout_step_id": "step2-lock-readout", "slot": 2,
                                             "value": "0", "parameter_label": "Trig Probability", "marker": "L"}}
        _validate_actions(authored, native, "target", req)
        authored["actions"][1]["while_held_grid"] = {"x": 4, "y": 4}
        with self.assertRaises(Exception):
            _validate_actions(authored, native, "target", req)

    @staticmethod
    def _held_native(assertion):
        interval = [
            {"id": "start", "inputs": [], "expect": {},
             "output": {"binding": {"assertion": {"kind": "start"}}, "grid": [0] * 128}},
            {"id": "step2-lock-readout", "inputs": [grid(3, 4, 1), {"type": "enc", "n": 3, "delta": -1}],
             "expect": {}, "output": {"binding": {"assertion": assertion}, "grid": [0] * 128}},
            {"id": "release-step2", "inputs": [grid(3, 4, 0)], "expect": {},
             "output": {"binding": {"assertion": {"kind": "released"}}, "grid": [0] * 128}},
            {"id": "target", "inputs": [], "expect": {},
             "output": {"binding": {"assertion": {"kind": "target"}}, "grid": [0] * 128}},
        ]
        return base_native(interval, interval[-1])

    @staticmethod
    def _held_actions():
        return {"actions": [
            {"id": "hold-step2", "kind": "hold-grid", "label": "Hold Step 2", "x": 3, "y": 4},
            {"id": "set-zero", "kind": "select-value", "label": "Set Trig Probability to 0",
             "control": "E3", "field_label": "Trig Probability", "field_slot": 2,
             "expected_marker": "L", "while_held_grid": {"x": 3, "y": 4}, "value": "0"},
            {"id": "release-step2", "kind": "release-grid", "label": "Release Step 2", "x": 3, "y": 4},
            {"id": "preview", "kind": "preview-recorded-result", "label": "Preview", "target_step_id": "target"},
        ]}

    def test_schema_accepts_only_valid_while_held_action(self):
        schema_path = Path(__file__).parents[1] / "manual" / "teaching-binding.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        select_schema = None
        def find(node):
            nonlocal select_schema
            if isinstance(node, dict):
                props = node.get("properties", {})
                if isinstance(props.get("kind"), dict) and props["kind"].get("const") == "select-value":
                    select_schema = node
                for value in node.values(): find(value)
            elif isinstance(node, list):
                for value in node: find(value)
        find(schema)
        self.assertIsNotNone(select_schema)
        validator = Draft202012Validator(select_schema)
        action = {"id": "set-zero", "kind": "select-value", "label": "Set Trig Probability to 0",
                  "control": "E3", "field_label": "Trig Probability", "field_slot": 2,
                  "expected_marker": "L", "while_held_grid": {"x": 3, "y": 4}, "value": "0"}
        validator.validate(action)
        for field, value in (("while_held_grid", {"x": 0, "y": 4}), ("expected_marker", None)):
            broken = copy.deepcopy(action)
            broken[field] = value
            with self.assertRaises(Exception):
                validator.validate(broken)

    def test_zero_note_action_binds_complete_log_leds_and_exact_controlled_window(self):
        active_grid = [0] * 128
        stopped_grid = [0] * 128
        active_grid[112] = 12
        stopped_grid[112] = 2
        active_assertion = {"kind": "probability-play-led", "phase": "active", "control": "play_stop",
                            "state": "active", "passed": True}
        stopped_assertion = {"kind": "probability-play-led", "phase": "stopped", "control": "play_stop",
                             "state": "off", "passed": True}
        silent_assertion = {"kind": "probability-zero-silence", "passed": True,
                            "play_step_id": "zero-play-active", "stop_step_id": "zero-play-stopped",
                            "window_result_id": "silent", "seconds": 2.8, "logical_duration_s": 2.8,
                            "window_start_index": 1, "window_end_index": 2,
                            "play_led_during": "active", "stop_led_after": "off",
                            "positive_velocity_note_on_count": 0, "note_ons": []}
        events = [{"port": 1, "bytes": "192 0"}, {"port": 1, "bytes": "176 1 2"}]
        interval = [
            {"id": "start", "inputs": [], "expect": {},
             "output": {"binding": {"assertion": {"kind": "start"}}, "grid": [0] * 128}},
            {"id": "zero-play-active", "inputs": [grid(1, 8, 1), grid(1, 8, 0),
             {"type": "advance", "nanoseconds": 2_800_000_000}], "expect": {},
             "output": {"binding": {"assertion": active_assertion}, "grid": active_grid}},
            {"id": "zero-play-stopped", "inputs": [grid(1, 8, 1), grid(1, 8, 0)], "expect": {},
             "output": {"binding": {"assertion": stopped_assertion}, "grid": stopped_grid}},
            {"id": "silent", "inputs": [], "expect": {},
             "output": {"binding": {"assertion": silent_assertion}, "grid": stopped_grid,
                        "midi": {"events": events, "total": 2, "truncated": False}}},
        ]
        native = base_native(interval, interval[-1])
        authored = {"actions": [
            {"id": "zero-play", "kind": "play-note-silence", "label": "Play at zero probability",
             "play_step_id": "zero-play-active", "stop_step_id": "zero-play-stopped",
             "window_result_id": "silent", "window_duration_s": 2.8},
            {"id": "preview", "kind": "preview-recorded-result", "label": "Preview", "target_step_id": "silent"},
        ]}
        proof = _validate_actions(authored, native, "silent", {"play_note_silence_at_target": True})
        receipt = proof[0]["proof"]
        self.assertEqual(receipt["native_event_count"], 2)
        self.assertEqual(receipt["window_event_count"], 1)
        self.assertEqual(receipt["positive_velocity_note_on_count"], 0)
        for mutate in ("truncated", "note-on", "off-led", "missing-advance", "overlong-window", "wrong-index"):
            bad = copy.deepcopy(native)
            if mutate == "truncated":
                bad["to_step"]["output"]["midi"]["truncated"] = True
            elif mutate == "note-on":
                bad["to_step"]["output"]["midi"]["events"][1]["bytes"] = "144 65 1"
            elif mutate == "off-led":
                bad["step_interval"][2]["output"]["grid"][112] = 12
            elif mutate == "missing-advance":
                bad["step_interval"][1]["inputs"][2]["nanoseconds"] = 2_700_000_000
            elif mutate == "overlong-window":
                bad["step_interval"][1]["inputs"].append({"type": "advance", "nanoseconds": 100_000_000})
            else:
                bad["to_step"]["output"]["binding"]["assertion"]["window_end_index"] = 3
            with self.assertRaises(Exception):
                _validate_actions(authored, bad, "silent", {"play_note_silence_at_target": True})


if __name__ == "__main__":
    unittest.main()

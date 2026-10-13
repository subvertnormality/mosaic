import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


BEHAVIOUR = Path(__file__).resolve().parent
if str(BEHAVIOUR) not in sys.path:
    sys.path.insert(0, str(BEHAVIOUR))


MIGRATIONS = {
    "M-SCALE-001": "scale_edit_selection",
    "M-SCALE-002": "scale_lock_lifetime",
    "M-SCALE-003": "scale_stop_indicator",
    "M-MERGE-001": "trig_merge_sets",
    "M-PAT-002": "all_pattern_slots",
    "M-RANGE-001": "channel_long_hold",
    "M-RANGE-002": "adjacent_channel_ranges",
    "M-MUTE-001": "channel_mute_gestures",
    "M-CHANNEL-001": "channel_routing_isolation",
    "M-MEMORY-001": "memory_navigation",
    "M-MEMORY-002": "memory_channel_isolation",
}


class ScaleMemoryMigrationTests(unittest.TestCase):
    def test_memory_navigation_configures_before_editor_move(self):
        from scale_memory import memory_navigation

        class ReachedHeader(Exception):
            pass

        class UiProbe:
            def __init__(self):
                self.calls = []

            def configure(self):
                self.calls.append(("configure",))

            def turn(self, encoder, detents):
                self.calls.append(("turn", encoder, detents))

            def expect_header(self, page, **params):
                self.calls.append(("expect_header", page, params))
                raise ReachedHeader

        ui = UiProbe()
        with self.assertRaises(ReachedHeader):
            memory_navigation(SimpleNamespace(ui=ui))
        self.assertEqual(ui.calls, [
            ("configure",),
            ("turn", 1, -2),
            ("expect_header", "memory", {"channel": 1}),
        ])

    def test_selected_cases_have_one_ui_independent_owner(self):
        from cases import CASES
        from ui_layer_guard import callable_raw_dependencies

        for case_id, name in MIGRATIONS.items():
            with self.subTest(case_id=case_id):
                run = CASES[case_id]["run"]
                self.assertEqual(run.__module__, "scale_memory")
                self.assertEqual(run.__name__, name)
                self.assertEqual(callable_raw_dependencies(run), [])

    def test_cases_registry_no_longer_defines_migrated_callables(self):
        import ast

        tree = ast.parse((BEHAVIOUR / "cases.py").read_text())
        defined = {node.name for node in tree.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue(set(MIGRATIONS.values()).isdisjoint(defined))


if __name__ == "__main__":
    unittest.main()

"""Collection must not silently select an overwritten case registration."""
import contextlib,io,json,sys,tempfile,unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import run
from editor_hold_evidence import record_hold_input_bounds, raw_editor_range_hold
from ui import Ui

class CollectionTests(unittest.TestCase):
    def test_edit005_controlled_results_are_stable_and_keep_raw_observations(self):
        sample = {
            "kind": "hold-input-bounds", "x": 14, "interrupted": False,
            "expected_long": False, "logical_seconds": 0.999999999,
            "wall_lower_seconds": 1.003418, "wall_upper_seconds": 1.006927,
        }
        driver = SimpleNamespace(clock_mode="controlled-experimental",
                                 observations=[], results=[])

        result = record_hold_input_bounds(driver, sample)

        self.assertEqual(result, {
            "kind": "hold-input-bounds", "x": 14, "interrupted": False,
            "expected_long": False, "logical_seconds": 0.999999999,
        })
        self.assertEqual(driver.results, [result])
        self.assertEqual(driver.observations, [{
            "kind": "hold-input-bounds-sample", "x": 14, "interrupted": False,
            "expected_long": False, "logical_seconds": 0.999999999,
            "wall_lower_seconds": 1.003418, "wall_upper_seconds": 1.006927,
        }])
        self.assertNotIn("wall_lower_seconds", driver.results[0])

    def test_edit005_real_time_results_keep_wall_bounds_and_observations(self):
        sample = {
            "kind": "hold-input-bounds", "x": 16, "interrupted": False,
            "expected_long": True, "logical_seconds": 1.05,
            "wall_lower_seconds": 1.021, "wall_upper_seconds": 1.073,
        }
        driver = SimpleNamespace(clock_mode="real-time", observations=[], results=[])

        result = record_hold_input_bounds(driver, sample)

        self.assertEqual(result, sample)
        self.assertEqual(driver.results, [sample])
        self.assertEqual(driver.observations[0]["kind"], "hold-input-bounds-sample")
        self.assertEqual(driver.observations[0]["wall_lower_seconds"], 1.021)
        self.assertEqual(driver.observations[0]["wall_upper_seconds"], 1.073)

    def test_edit005_raw_range_hold_keeps_original_primitive_recipe(self):
        recipe = []

        class Driver:
            def action(self, **action):
                recipe.append(action)

            def elapse(self, seconds):
                recipe.append({"type": "advance", "seconds": seconds})

        raw_editor_range_hold(Driver(), 15, 8)

        self.assertEqual(recipe, [
            {"type": "grid", "x": 15, "y": 8, "state": 1},
            {"type": "advance", "seconds": 1.1},
            {"type": "grid", "x": 15, "y": 8, "state": 0},
        ])

    def test_edit005_semantic_controls_expand_to_raw_grid_recipe(self):
        recipe = []
        ui = Ui.for_action_sink(
            recipe.append,
            lambda seconds: recipe.append({"type": "advance", "seconds": seconds}),
        )
        controls = (
            ("pattern_editor", None, (5, 8)),
            ("pattern_note_octave_reset", None, (15, 8)),
            ("pattern_note_octave_up", None, (14, 8)),
            ("pattern_note_degree", (4, 4), (4, 3)),
            ("pattern_note_degree", (4, 6), (4, 1)),
            ("pattern_velocity_level", (4, 7), (4, 1)),
        )
        expected = []
        for control, index, (x, y) in controls:
            ui.tap_control(control, index)
            expected.extend((
                {"type": "grid", "x": x, "y": y, "state": 1},
                {"type": "grid", "x": x, "y": y, "state": 0},
                {"type": "advance", "seconds": 0.06},
            ))
        for control, x in (("pattern_velocity_range_reset", 15),
                           ("pattern_velocity_range_down", 16)):
            with ui.hold_control(control):
                ui.driver.elapse(1.1)
            expected.extend((
                {"type": "grid", "x": x, "y": 8, "state": 1},
                {"type": "advance", "seconds": 1.1},
                {"type": "grid", "x": x, "y": 8, "state": 0},
            ))

        self.assertEqual(recipe, expected)

    def test_behaviour_source_hashes_include_nested_contract_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            behaviour = root / 'tests' / 'behaviour'
            contract = behaviour / 'contract'
            contract.mkdir(parents=True)
            top_level = behaviour / 'cases.py'
            nested = contract / 'song_divisions.py'
            top_level.write_text('CASES = {}\\n')
            nested.write_text('def song_tempo_divisions(c): pass\\n')
            self.assertEqual(
                run.behaviour_source_hashes(root),
                {
                    'tests/behaviour/cases.py': run.digest(top_level),
                    'tests/behaviour/contract/song_divisions.py': run.digest(nested),
                },
            )

    def test_unique_duration_case_and_duplicate_rejection(self):
        with patch.object(sys,'argv',['run.py','--list']),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run.main(),0)
        self.assertEqual(json.loads(output.getvalue())['M-PAT-003']['requirements'],['PAT-DURATION'])
        source=(run.REPO/'tests/behaviour/cases.py').read_text()
        self.assertEqual(source.count("'M-PAT-003':dict(run=pattern_duration_domain"),1)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'tests/behaviour';path.mkdir(parents=True)
            (path/'cases.py').write_text(source.replace("'M-PAT-003':dict(run=pattern_duration_domain","'M-PAT-002':dict(run=pattern_duration_domain"))
            with patch.object(run,'REPO',root),patch.object(sys,'argv',['run.py','--list']):
                with self.assertRaisesRegex(AssertionError,'Duplicate case IDs'):
                    run.main()

if __name__=='__main__':unittest.main()

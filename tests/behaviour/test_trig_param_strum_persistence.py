"""Portable wrapper test for the registered slot-Strum persistence case."""
import importlib.util
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

CASE_PATH = pathlib.Path(__file__).with_name("trig_param_strum_persistence.py")


class SlotStrumPersistenceWrapper(unittest.TestCase):
    def test_public_case_drives_both_exact_schedules_and_preserves_child_evidence(self):
        calls = []

        class FakeUI:
            def __init__(self, owner):
                self.owner = owner

            def __getattr__(self, name):
                def call(*args, **kwargs):
                    calls.append((self.owner.name, name, args, kwargs))
                    if name == "trig_parameter_label":
                        return {"chord_note_strum": "Strum", "chord_spread": "Spread"}[args[0]]
                    if name == "press_key" and args == (1,) and self.owner.pending_save:
                        data = self.owner.data_directory
                        (data / "new.ptn").write_text("saved project")
                        (data / "new.pset").write_text("saved params")
                        self.owner.pending_save = False
                return call

        class FakeDriver:
            instances = []

            def __init__(self, out, **kwargs):
                self.name = "child"
                self.out = pathlib.Path(out)
                self.out.mkdir(parents=True, exist_ok=True)
                self.data_directory = self.out / "data" / "mosaic"
                self.data_directory.mkdir(parents=True)
                self.launch_options = kwargs
                self.project_seed = kwargs.get("project_seed")
                self.results = [dict(kind="midi-schedule", passed=True)]
                self.observations = [dict(state=dict(midi_count=7))]
                self.identity = dict(application_identity=dict(files=[dict(path="mosaic/mosaic.lua", sha256="app-sha")]))
                self.ui = FakeUI(self)
                self.finished = False
                self.pending_save = False
                self.clock_mode = "controlled-experimental"
                self.logical_ns = 0
                self.instances.append(self)

            def finish(self):
                self.finished = True
                native = self.out / "native"
                native.mkdir(exist_ok=True)
                (native / "identity.json").write_text(json.dumps(self.identity))
                (self.out / "recipe.json").write_text("[]")
                (self.out / "results.json").write_text(json.dumps(self.results))
                (self.out / "observations.json").write_text(json.dumps(self.observations))

        class FakeRoot:
            def __init__(self, folder):
                self.name = "root"
                self.out = pathlib.Path(folder)
                self.out.mkdir(exist_ok=True)
                self.data_directory = self.out / "data" / "mosaic"
                self.data_directory.mkdir(parents=True)
                self.launch_options = dict(clock_mode="controlled-experimental", profile="base-midi")
                self.results = []
                self.ui = FakeUI(self)
                self.finished = False
                self.pending_save = True

            def configure(self):
                calls.append(("root", "configure", (), {}))

            def wait(self, predicate, timeout=3):
                self.assert_timeout = timeout
                return predicate(None)

            def finish(self):
                self.finished = True
                native = self.out / "native"
                native.mkdir(exist_ok=True)
                identity = dict(application_identity=dict(files=[dict(path="mosaic/mosaic.lua", sha256="root-sha")]))
                (native / "identity.json").write_text(json.dumps(identity))
                (self.out / "results.json").write_text(json.dumps(self.results))

        def build(c, length, strum, mask_turns):
            calls.append(("root", "build", (length, strum, mask_turns), {}))

        def check(c, seconds, schedule, durations, kind):
            calls.append((c.name, "schedule", (seconds, schedule, durations, kind), {}))
            if kind == "slot-strum-persist-2-strum":
                last_release = max(tick + duration for (tick, _, _), duration in zip(schedule, durations))
                period_ticks = 64 * 216
                if not (last_release / 144 < seconds < period_ticks / 144):
                    raise AssertionError(("capture must include all gates before pattern retrigger", seconds, last_release, period_ticks))
                if seconds != 6:
                    raise AssertionError(("expected controlled capture window", seconds))
            expected = [(0, 60, 127), (0, 64, 127), (0, 67, 127)]
            if kind == "slot-strum-persist-2-strum":
                expected = [(0, 60, 127), (162, 64, 127), (324, 67, 127)]
            if schedule != expected or durations != [432] * 3:
                raise AssertionError((kind, schedule, durations))
            return [dict(truncated=False) for _ in schedule]

        fake_cases = types.ModuleType("cases")
        fake_cases.STRUM_SLOT_PITCHES = (60, 64, 67, 69, 72)
        fake_cases.STRUM_SLOT_VELOCITY = 127
        fake_cases.strum_slot_chord_channel = build
        fake_cases.strum_slot_play_and_check = check
        fake_driver_module = types.ModuleType("driver")
        fake_driver_module.Driver = FakeDriver
        fake_driver_module.write = lambda path, value: pathlib.Path(path).write_text(json.dumps(value))

        spec = importlib.util.spec_from_file_location("candidate_strum_persistence", CASE_PATH)
        candidate = importlib.util.module_from_spec(spec)
        with tempfile.TemporaryDirectory() as folder, patch.dict(
            sys.modules, {"cases": fake_cases, "driver": fake_driver_module}
        ):
            spec.loader.exec_module(candidate)
            root = FakeRoot(folder)
            candidate.trig_param_strum_persistence(root)
            child = FakeDriver.instances[-1]
            self.assertTrue(root.finished)
            self.assertTrue(child.finished)
            self.assertEqual(child.project_seed, root.data_directory)
            self.assertIn(("child", "select_project_file", ("new.ptn",), {}), calls)
            self.assertIn(("child", "expect_dashboard_row", ("Global length", "64"), {}), calls)
            visible = [call[2] for call in calls if call[0] == "child" and call[1] == "expect_selected_field"]
            self.assertEqual(visible, [
                ("overview_params", "Strum", "X"),
                ("overview_params", "Spread", "X"),
                ("overview_params", "Strum", "1/2"),
                ("overview_params", "Spread", "1/4"),
                ("overview_params", "Strum", "X"),
                ("overview_params", "Spread", "X"),
            ])
            schedules = [call[2] for call in calls if call[1] == "schedule"]
            self.assertEqual([row[3] for row in schedules], [
                "slot-strum-persist-1-block",
                "slot-strum-persist-2-strum",
                "slot-strum-persist-1-again",
            ])
            parent_results = json.loads((root.out / "results.json").read_text())
            record = parent_results[-1]
            self.assertTrue(record["passed"])
            self.assertEqual(record["slot2_onsets"], [0, 162, 324])
            self.assertEqual(record["slot2_releases"], [432, 594, 756])
            self.assertEqual(record["slot2_capture_seconds"], 6)
            self.assertEqual(record["slot2_period_ticks"], 64 * 216)
            self.assertEqual(record["nested_session"]["results"], [dict(kind="midi-schedule", passed=True)])
            self.assertEqual(record["nested_session"]["observation_count"], 1)
            self.assertEqual(record["nested_session"]["application_identity"]["files"][0]["sha256"], "app-sha")
            self.assertTrue((root.out / "nested-session-evidence.json").is_file())


if __name__ == "__main__":
    unittest.main()

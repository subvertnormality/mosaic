"""Interactive-manual data contracts; characterisation outside the README."""
import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("manual_model", ROOT / "tools/manual_model.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)

class ManualModelTests(unittest.TestCase):
    def setUp(self):
        self.data = model.load()
    def test_pilot_has_semantic_contracts_and_fixed_seed(self):
        model.validate(self.data)
        self.assertEqual(self.data["feature"]["id"], "masks")
        for scene in self.data["scenes"]:
            self.assertEqual(scene["setup"]["seed"], 42)
            self.assertTrue(scene["behaviour_case"])
            self.assertTrue(scene["steps"])
            for step in scene["steps"]:
                self.assertTrue(step["expect"])
                self.assertTrue(step["citation"])
    def test_invalid_coordinate_fails_closed(self):
        bad = copy.deepcopy(self.data)
        bad["scenes"][0]["steps"][0]["inputs"] = [{"type":"grid","x":17,"y":4,"state":1}]
        with self.assertRaises(ValueError):
            model.validate(bad)
    def test_unknown_action_and_unreleased_hold_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["scenes"][0]["steps"][0]["inputs"] = [{"type":"evaluate","code":"anything"}]
        with self.assertRaises(ValueError):
            model.validate(bad)
        bad = copy.deepcopy(self.data)
        bad["scenes"][0]["steps"][-1]["inputs"].append({"type":"key","n":1,"state":1})
        with self.assertRaises(ValueError):
            model.validate(bad)
    def test_capture_integrity_and_dimensions(self):
        capture = {"levels":[0]*8192,"grid":[0]*128}
        model.validate_capture(capture)
        capture["levels"][0] = 16
        with self.assertRaises(ValueError):
            model.validate_capture(capture)
    def test_unsafe_audio_path_and_missing_case_rejected(self):
        bad = copy.deepcopy(self.data)
        bad["audio"]["files"] = ["../escape.mp3"]
        with self.assertRaises(ValueError):
            model.validate(bad)
        bad = copy.deepcopy(self.data)
        bad["scenes"][0]["behaviour_case"] = "M-UNKNOWN-000"
        with self.assertRaises(ValueError):
            model.validate(bad)

if __name__ == "__main__":
    unittest.main()

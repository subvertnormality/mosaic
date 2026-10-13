import copy
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
PROJECT = Path(os.environ["MOSAIC_PROJECT_ROOT"])
REPORT = Path(os.environ["MOSAIC_PARAMETER_REPORT"])
EVIDENCE = Path(os.environ["MOSAIC_PARAMETER_EVIDENCE"])
spec = importlib.util.spec_from_file_location("manual_parameter_readout", HERE / "tools/manual_parameter_readout.py")
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def interval_native(scene, from_id, to_id):
    steps = scene["steps"]
    ids = [step["id"] for step in steps]
    first, last = ids.index(from_id), ids.index(to_id)
    interval = [{key: step[key] for key in ("id", "inputs", "expect", "output")}
                for step in steps[first:last + 1]]
    prefix = [{"step_id": step["id"], "inputs": step["inputs"]} for step in steps[:last + 1]]
    return {"contract_schema": "mosaic-native-transition-v3", "transition_scope": "interval",
            "scene": {key: scene[key] for key in ("id", "behaviour_case", "evidence")},
            "from_step_id": from_id, "to_step_id": to_id, "step_interval": interval,
            "scene_input_prefix": prefix,
            "from_step": interval[0], "to_step": interval[-1]}


def setup_pixel_oracle(frame_oracle, source):
    temp = tempfile.TemporaryDirectory(prefix="parameter-readout-oracle-")
    root = Path(temp.name)
    (root / ".runtime").mkdir()
    (root / ".runtime/current.json").write_text(json.dumps({"source": source}))
    frame_oracle.ROOT = root
    return temp


class ParameterReadoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        report = json.loads(REPORT.read_text())
        cls.scene = next(row for row in report["scenes"] if row["id"] == "fixed-note-default-and-locks")
        cls.native = interval_native(cls.scene, "list", "channel60")
        cls.steps = {step["id"]: step for step in cls.native["step_interval"]}
        cls.results = json.loads((EVIDENCE / "results.json").read_text())
        cls.effect = cls.steps["channel60"]["output"]["binding"]["assertion"]
        cls.request = {
            "schema_version": 1,
            "parameter_label": "Fixed Note",
            "display_label": "Note",
            "slot": 1,
            "value": "C5",
            "marker": None,
            "picker_step_id": "list",
            "assignment_step_id": "assigned",
            "readout_step_id": "default",
            "effect_step_id": "channel60",
            "effect_assertion": cls.effect,
        }
        sys.path.insert(0, str(PROJECT / "tests/behaviour"))
        import frame_oracle
        cls.frame_oracle = frame_oracle
        cls.temp = setup_pixel_oracle(frame_oracle, "/home/andy/projects/monome-runtime-candidates/final-qualification-controlled-01/norns")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def derive(self, native=None, request=None, evidence_root=None):
        return adapter.derive_parameter_readout_receipt(
            copy.deepcopy(native or self.native), copy.deepcopy(request or self.request), "fixed-note-default",
            evidence_root=evidence_root or EVIDENCE, project_root=PROJECT, frame_oracle=self.frame_oracle)

    def test_exact_native_picker_assignment_readout_and_musical_effect(self):
        derived = self.derive()
        receipt = derived["receipt"]
        self.assertEqual(derived["value"], {"parameter_label": "Fixed Note", "slot": 1, "value": "C5", "marker": None})
        self.assertEqual(receipt["observation_indices"], {"picker": 29, "assignment": 34, "readout": 36, "effect": 41})
        self.assertEqual(receipt["refs"]["picker"]["assertion"]["label"], "Fixed Note")
        self.assertEqual(receipt["refs"]["readout"]["assertion"], {"kind": "selected-param", "slot": 1, "value": "C5", "marker": None, "passed": True})
        self.assertEqual(receipt["refs"]["effect"]["assertion"], self.effect)
        action = {"id": "fixed-note-default", "kind": "select-value", "field_label": "Fixed Note", "value": "C5"}
        action_checkpoint = {"action_id": "fixed-note-default", "raw_inputs": [{"step_id": "default", "index": 1}],
                             "checkpoint_step_id": "default",
                             "proof": {"kind": "field-value", "field_label": "Fixed Note", "value": "C5"}}
        self.assertEqual(adapter.verify_action_link(action, derived, action_checkpoint), receipt)
        self.assertEqual(adapter.receipt_digest(receipt), receipt["proof_sha256"])

    def test_rejects_wrong_label_slot_value_or_marker(self):
        for field, value in (("parameter_label", "Probability"), ("slot", 2), ("value", "D5"), ("marker", "L")):
            request = copy.deepcopy(self.request)
            request[field] = value
            with self.subTest(field=field), self.assertRaises(adapter.ParameterReadoutError):
                self.derive(request=request)

    def test_rejects_wrong_frame_or_reordered_checkpoint(self):
        native = copy.deepcopy(self.native)
        native["step_interval"][1]["output"]["binding"]["sha256"] = "0" * 64
        with self.assertRaises(adapter.ParameterReadoutError):
            self.derive(native=native)
        request = copy.deepcopy(self.request)
        request["readout_step_id"] = "assigned"
        with self.assertRaises(adapter.ParameterReadoutError):
            self.derive(request=request)

    def test_rejects_missing_apply_cancel_only_or_intervening_slot_input(self):
        cases = []
        native = copy.deepcopy(self.native)
        native["step_interval"][1]["inputs"] = native["step_interval"][1]["inputs"][2:]
        cases.append(native)
        native = copy.deepcopy(self.native)
        native["step_interval"][1]["inputs"] = [{"type": "key", "n": 2, "state": 1}, {"type": "key", "n": 2, "state": 0}]
        cases.append(native)
        native = copy.deepcopy(self.native)
        native["step_interval"][2]["inputs"].append({"type": "enc", "n": 2, "delta": 2})
        cases.append(native)
        native = copy.deepcopy(self.native)
        native["step_interval"][2]["inputs"].append({"type": "key", "n": 3, "state": 1})
        cases.append(native)
        native = copy.deepcopy(self.native)
        native["step_interval"][2]["inputs"] = [{"type": "wait", "seconds": 0.1}]
        cases.append(native)
        native = copy.deepcopy(self.native)
        native["step_interval"][-1]["inputs"].append({"type": "key", "n": 2, "state": 1})
        cases.append(native)
        for native in cases:
            with self.assertRaises(adapter.ParameterReadoutError):
                self.derive(native=native)

    def test_rejects_effect_mutation_truncation_and_wrong_action_binding(self):
        request = copy.deepcopy(self.request)
        request["effect_assertion"]["pitches"] = [60, 62]
        with self.assertRaises(adapter.ParameterReadoutError):
            self.derive(request=request)
        native = copy.deepcopy(self.native)
        native["step_interval"][-1]["output"]["binding"]["assertion_index"] = 999999
        with self.assertRaises(adapter.ParameterReadoutError):
            self.derive(native=native)
        derived = self.derive()
        with self.assertRaises(adapter.ParameterReadoutError):
            adapter.verify_action_link({"id": "another", "kind": "select-value", "field_label": "Fixed Note", "value": "C5"}, derived, {})

    def test_rejects_native_observation_session_and_pixel_mutations(self):
        with tempfile.TemporaryDirectory(prefix="parameter-readout-mutated-evidence-") as directory:
            evidence_copy = Path(directory)
            for name in ("results.json", "observations.json"):
                shutil.copyfile(EVIDENCE / name, evidence_copy / name)
            observations_path = evidence_copy / "observations.json"
            observations = json.loads(observations_path.read_text())
            target_sha = self.steps["default"]["output"]["binding"]["sha256"]
            for observation in observations:
                if observation["state"]["frame"]["sha256"] == target_sha:
                    observation["session_id"] = "different-session"
            observations_path.write_text(json.dumps(observations))
            with self.assertRaises(adapter.ParameterReadoutError):
                self.derive(evidence_root=evidence_copy)

            observations = json.loads((EVIDENCE / "observations.json").read_text())
            target = next(row for row in observations if row["state"]["frame"]["sha256"] == target_sha)
            pixels = target["state"]["frame"]["pixels_base64"]
            target["state"]["frame"]["pixels_base64"] = ("A" if pixels[0] != "A" else "B") + pixels[1:]
            observations_path.write_text(json.dumps(observations))
            with self.assertRaises(adapter.ParameterReadoutError):
                self.derive(evidence_root=evidence_copy)


if __name__ == "__main__":
    unittest.main(verbosity=2)

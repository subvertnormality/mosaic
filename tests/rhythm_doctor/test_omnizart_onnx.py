"""Characterisation outside README: fixed Omnizart ONNX drum-head contract.

These tests use a deterministic session double.  They neither download nor
exercise a model weight; a real deployment still has to prove source-Keras to
ONNX activation parity on frozen audio.
"""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor"))
import rd_omnizart_onnx as omnizart


class _Input:
    name = "patches"


class FakeSession:
    def __init__(self, output):
        self.output = output
        self.inputs = []

    def get_inputs(self):
        return [_Input()]

    def run(self, names, feed):
        self.inputs.append(feed["patches"].copy())
        return [self.output]


class OmnizartOnnxTests(unittest.TestCase):
    def test_pinned_artifact_sha_mismatch_fails_before_session_construction(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "drum.onnx"
            model.write_bytes(b"published-model-bytes")
            with self.assertRaises(omnizart.ArtifactMismatch):
                omnizart.verify_artifact(model, "0" * 64)

    def test_strict_source_tensor_shape_rejects_nearby_onnx_output(self):
        features = np.zeros((4, 120, 120), dtype=np.float32)
        session = FakeSession(np.zeros((1, 13, 4), dtype=np.float32))
        with self.assertRaises(omnizart.TensorContractError):
            omnizart.predict_raw_heads(session, features, batch_size=1)

    def test_short_feature_input_discards_padding_activations_before_decode(self):
        raw = omnizart.predict_raw_heads(
            FakeSession(np.zeros((1, 13, 4, 1), dtype=np.float32)),
            np.zeros((1, 120, 120), dtype=np.float32), batch_size=1,
        )
        self.assertEqual(raw.shape, (1, 13))

    def test_fake_session_uses_upstream_patch_shape_and_preserves_each_hat_head(self):
        features = np.zeros((5, 120, 120), dtype=np.float32)
        output = np.zeros((2, 13, 4, 1), dtype=np.float32)
        output[0, 0, 0, 0] = .90  # BD
        output[0, 1, 1, 0] = .80  # SD
        output[1, 1, 0, 0] = .80
        output[0, 4, 2, 0] = .70  # CHH / GM 42
        output[1, 4, 1, 0] = .70
        output[1, 6, 3, 0] = .60  # OHH / GM 46
        session = FakeSession(output)

        raw = omnizart.predict_raw_heads(session, features, batch_size=2)

        self.assertEqual(raw.shape, (5, 13))
        self.assertEqual(len(session.inputs), 1)
        self.assertEqual(session.inputs[0].shape, (2, 120, 120, 4))
        events = omnizart.decode_drum_heads(
            raw, np.linspace(0.0, 0.4, 5), 8000,
            {"BD": .5, "SD": .5, "CHH": .5, "OHH": .5},
        )
        self.assertEqual({event["lane"] for event in events}, {"BD", "SD", "CHH", "OHH"})
        self.assertNotIn("HH", {event["lane"] for event in events})

    def test_backend_result_carries_verified_artifact_and_four_distinct_gates(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "drum.onnx"
            model.write_bytes(b"published-model-bytes")
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            output = np.zeros((32, 13, 4, 1), dtype=np.float32)
            for batch_index, step_index in ((2, 3), (3, 2), (4, 1), (5, 0)):
                output[batch_index, 4, step_index, 0] = .75
            result = omnizart.analyse_features(
                session=FakeSession(output), model_path=model, expected_sha256=digest,
                features=np.zeros((35, 120, 120), dtype=np.float32),
                mini_beats=np.arange(35) / 10, sample_rate=8000,
                gates={"BD": .5, "SD": .5, "CHH": .5, "OHH": .5}, bpm=120,
                origin_sample=0,
            )
        self.assertEqual(result["drum_component"]["drum_artifact_sha256"], digest)
        self.assertEqual(result["drum_component"]["backend_id"], "omnizart-onnx-raw-heads-v1")
        self.assertEqual(result["lane_onset_gates"], {"BD": .5, "SD": .5, "CHH": .5, "OHH": .5})
        self.assertEqual(result["candidates"], [{"lane": "CHH", "sample_index": 4000, "velocity": 96, "confidence": .75}])


if __name__ == "__main__":
    unittest.main()

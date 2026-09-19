"""Executable protocol checks for the fail-closed Omnizart drum component."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "tools" / "rhythm_doctor" / "rd_omnizart_onnx_backend.py"


def _request(drum_sha256: str) -> dict[str, object]:
    return {"pretrained": {
        "backend_sha256": "a" * 64,
        "drum_artifact_sha256": drum_sha256,
        "bass_artifact_sha256": "b" * 64,
    }}


class OmnizartOnnxBackendTests(unittest.TestCase):
    def _run(self, request: dict[str, object], environment: dict[str, str]) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            request_path, result_path = directory / "request.json", directory / "result.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(BACKEND), "--request", str(request_path), "--result", str(result_path)],
                cwd=ROOT, env=environment, check=False, capture_output=True, text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return json.loads(result_path.read_text(encoding="utf-8"))

    def test_missing_model_configuration_is_a_safe_backend_error(self):
        environment = dict(os.environ)
        environment.pop("RD_OMNIZART_ONNX_MODEL", None)
        environment.pop("RD_OMNIZART_ONNX_SHA256", None)
        self.assertEqual(
            self._run(_request("c" * 64), environment),
            {"backend_error": "OMNIZART_ARTIFACT_NOT_CONFIGURED"},
        )

    def test_executable_rejects_a_worker_drum_pin_that_differs_from_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "drum.onnx"
            model.write_bytes(b"pinned-omnizart-model")
            environment = dict(os.environ, RD_OMNIZART_ONNX_MODEL=str(model),
                               RD_OMNIZART_ONNX_SHA256=hashlib.sha256(model.read_bytes()).hexdigest())
            self.assertEqual(
                self._run(_request("d" * 64), environment),
                {"backend_error": "OMNIZART_REQUEST_ARTIFACT_MISMATCH"},
            )

    def test_verified_drum_component_refuses_to_publish_without_bass_component(self):
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / "drum.onnx"
            model.write_bytes(b"pinned-omnizart-model")
            digest = hashlib.sha256(model.read_bytes()).hexdigest()
            environment = dict(os.environ, RD_OMNIZART_ONNX_MODEL=str(model), RD_OMNIZART_ONNX_SHA256=digest)
            self.assertEqual(
                self._run(_request(digest), environment),
                {"backend_error": "OMNIZART_BASS_BACKEND_REQUIRED"},
            )


if __name__ == "__main__":
    unittest.main()

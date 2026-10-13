"""The remote analysis client, and above all its fallback.

The server is an advanced option on someone's home network. It will be switched
off, moved, upgraded mid-capture and asked to analyse while still loading
models. Every one of those has to end with the player getting gates, so these
tests are mostly about what happens when the server does not cooperate.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "tools" / "rhythm_doctor" / "rd_remote_backend.py"
SR = 44100
FRAMES = SR * 4


def good_analysis(frames=FRAMES):
    return {
        "protocol_version": 1, "bpm": 120.0, "tempo_detected": True,
        "origin_sample": 0, "phrase_start_sample": 22050, "phrase_confidence": 0.8,
        "beat_positions": [0, 22050, 44100], "tempo_mode": "auto",
        "lane_onset_gates": {"KICK": 0.3, "SNARE": 0.3},
        "candidates": [{"lane": "KICK", "sample_index": 100, "velocity": 90, "confidence": 0.7}],
        "detector": {"backend_id": "remote-test"},
        "capture_sha256": "0" * 64,
    }


class Fake(BaseHTTPRequestHandler):
    payload = None          # dict -> 200 JSON, bytes -> raw body, int -> status
    delay = 0.0

    def log_message(self, *_):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        if self.delay:
            import time
            time.sleep(self.delay)
        payload = type(self).payload
        if isinstance(payload, int):
            self.send_response(payload); self.end_headers(); return
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class RemoteBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.thread.join(timeout=5)

    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        root = Path(self.work.name)
        self.wav = root / "capture.wav"
        with wave.open(str(self.wav), "wb") as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(SR)
            out.writeframes((np.zeros(FRAMES) + 1000).astype("<i2").tobytes())
        self.request = root / "request.json"
        self.result = root / "result.json"
        self.request.write_text(json.dumps(
            {"protocol_version": 1, "job_id": "j", "project_id": "p", "generation": 1,
             "analysis_revision": 1, "wav_path": str(self.wav), "frames": FRAMES,
             "sample_rate": SR}))
        # A stand-in local backend: writes a result that names itself, so a
        # test can tell which path produced the analysis.
        self.fallback = root / "fallback.py"
        self.fallback.write_text(
            "#!/usr/bin/env python3\n"
            "import json,sys\n"
            "out = sys.argv[sys.argv.index('--result')+1]\n"
            "json.dump({'bpm':100.0,'detector':{'backend_id':'local-fallback'},"
            "'lane_onset_gates':{'BD':0.4},'candidates':[]}, open(out,'w'))\n")
        os.chmod(self.fallback, 0o755)

    def tearDown(self):
        self.work.cleanup()

    def run_client(self, endpoint=None, timeout=30.0, with_fallback=True):
        argv = [sys.executable, str(CLIENT), "--request", str(self.request),
                "--result", str(self.result), "--timeout", str(timeout)]
        if endpoint is not None:
            argv += ["--endpoint", endpoint]
        if with_fallback:
            argv += ["--fallback", str(self.fallback)]
        done = subprocess.run(argv, capture_output=True, text=True, timeout=120)
        value = json.loads(self.result.read_text()) if self.result.is_file() else None
        return done.returncode, value

    def endpoint(self):
        return "http://127.0.0.1:%d" % self.port

    def test_a_good_server_result_is_used(self):
        Fake.payload = good_analysis()
        code, value = self.run_client(self.endpoint())
        self.assertEqual(code, 0)
        self.assertEqual(value["detector"]["backend_id"], "remote-test")
        self.assertEqual(value["phrase_start_sample"], 22050)

    def test_transport_fields_are_stripped_before_the_worker_sees_them(self):
        Fake.payload = good_analysis()
        _, value = self.run_client(self.endpoint())
        self.assertNotIn("protocol_version", value)
        self.assertNotIn("capture_sha256", value)

    def test_an_unreachable_server_falls_back_instead_of_losing_the_capture(self):
        code, value = self.run_client("http://127.0.0.1:1")     # nothing listening
        self.assertEqual(code, 0)
        self.assertEqual(value["detector"]["backend_id"], "local-fallback")

    def test_a_server_error_falls_back(self):
        Fake.payload = 503
        code, value = self.run_client(self.endpoint())
        self.assertEqual(code, 0)
        self.assertEqual(value["detector"]["backend_id"], "local-fallback")

    def test_a_timeout_falls_back(self):
        Fake.payload, Fake.delay = good_analysis(), 2.0
        try:
            code, value = self.run_client(self.endpoint(), timeout=0.25)
        finally:
            Fake.delay = 0.0
        self.assertEqual(code, 0)
        self.assertEqual(value["detector"]["backend_id"], "local-fallback")

    def test_rubbish_from_the_server_falls_back(self):
        Fake.payload = b"<html>router login page</html>"
        code, value = self.run_client(self.endpoint())
        self.assertEqual(code, 0)
        self.assertEqual(value["detector"]["backend_id"], "local-fallback")

    def test_no_endpoint_configured_uses_the_local_backend(self):
        code, value = self.run_client(None)
        self.assertEqual(code, 0)
        self.assertEqual(value["detector"]["backend_id"], "local-fallback")

    def test_a_result_that_would_poison_the_bank_falls_back(self):
        """The server is a separate program on a machine Mosaic does not
        control, so its output is checked rather than trusted because it
        answered."""
        poisons = [
            ("tempo out of contract", {"bpm": 900.0}),
            ("origin past the capture", {"origin_sample": FRAMES * 2}),
            ("onset past the capture", {"candidates": [
                {"lane": "KICK", "sample_index": FRAMES + 1, "velocity": 90, "confidence": 0.5}]}),
            ("velocity out of range", {"candidates": [
                {"lane": "KICK", "sample_index": 10, "velocity": 200, "confidence": 0.5}]}),
            ("a lane with no gate", {"candidates": [
                {"lane": "TROMBONE", "sample_index": 10, "velocity": 90, "confidence": 0.5}]}),
            ("confidence out of range", {"phrase_confidence": 4.0}),
            ("a beat past the capture", {"beat_positions": [0, FRAMES * 3]}),
            ("no detector identity", {"detector": {}}),
        ]
        for label, override in poisons:
            with self.subTest(label):
                Fake.payload = {**good_analysis(), **override}
                code, value = self.run_client(self.endpoint())
                self.assertEqual(code, 0, label)
                self.assertEqual(value["detector"]["backend_id"], "local-fallback",
                                 "%s was accepted" % label)

    def test_without_a_fallback_a_dead_server_reports_failure(self):
        """The worker turns a non-zero exit into a reported error. Writing no
        result at all would leave the UI waiting forever."""
        code, value = self.run_client("http://127.0.0.1:1", with_fallback=False)
        self.assertNotEqual(code, 0)
        self.assertIsNone(value)


if __name__ == "__main__":
    unittest.main()

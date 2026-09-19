"""Actual PCM/hash -> pretrained-worker protocol integration.

The disposable backend is a protocol fixture, not a classifier.  It proves the
worker invokes only an already executable backend, preserves all five explicit
lane gates, and fails closed when no backend was configured.
"""
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import wave

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "tools" / "rhythm_doctor" / "rd_analysis_worker.py"
LANES = ("BD", "SD", "CHH", "OHH", "BASS")
sys.path.insert(0, str(WORKER.parent))
import rd_analysis_worker


def request(wav: Path) -> dict:
    return {"protocol_version": 1, "job_id": "analysis-job", "project_id": "project-a",
            "generation": 3, "analysis_revision": 2, "command": "ANALYSE", "wav_path": str(wav),
            "wav_sha256": hashlib.sha256(wav.read_bytes()).hexdigest(), "frames": 64000,
            "sample_rate": 8000, "result_schema_version": 2, "max_candidates": 22500}


class AnalysisWorkerValidation(unittest.TestCase):
    def valid(self):
        return {"bpm": 120, "origin_sample": 0, "detector": {"backend_id": "pinned-v1", "artifact_sha256": "a" * 64},
                "lane_onset_gates": dict.fromkeys(LANES, .5), "candidates": [
                    {"lane": "CHH", "sample_index": 10, "velocity": 90, "confidence": .8},
                    {"lane": "OHH", "sample_index": 20, "velocity": 91, "confidence": .7},
                ]}

    def test_every_active_lane_requires_its_own_gate(self):
        value = self.valid(); del value["lane_onset_gates"]["OHH"]
        self.assertFalse(rd_analysis_worker.analysis_is_pretrained(value))

    def test_unknown_lane_and_unpinned_artifact_are_rejected(self):
        value = self.valid(); value["candidates"][0]["lane"] = "HH"
        self.assertFalse(rd_analysis_worker.analysis_is_pretrained(value))
        value = self.valid(); value["detector"]["artifact_sha256"] = "not-a-hash"
        self.assertFalse(rd_analysis_worker.analysis_is_pretrained(value))


@unittest.skipUnless(hasattr(socket, "AF_UNIX") and hasattr(socket, "SOCK_SEQPACKET"), "requires AF_UNIX SOCK_SEQPACKET")
class AnalysisWorkerIPC(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-analysis-worker-")
        self.root = Path(self.temporary.name); self.runtime = self.root / "runtime"; self.runtime.mkdir()
        self.wav = self.root / "capture.wav"
        with wave.open(str(self.wav), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(8000); output.writeframes(b"\0\0" * 64000)

    def tearDown(self): self.temporary.cleanup()

    def start(self, backend=None):
        command = [sys.executable, str(WORKER), "--runtime", str(self.runtime)]
        if backend: command += ["--backend", str(backend)]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        path = process.stdout.readline().strip()
        if not path or not Path(path).exists():
            detail = process.stderr.read(); process.wait(timeout=3)
            self.fail(detail or "analysis worker did not publish a socket")
        peer = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET); peer.connect(path)
        return process, peer

    def stop(self, process, peer):
        peer.close(); process.terminate(); process.wait(timeout=3)
        if process.stdout: process.stdout.close()
        if process.stderr: process.stderr.close()

    def receive(self, peer):
        peer.settimeout(3)
        return json.loads(peer.recv(8192).decode("utf-8"))

    def test_pinned_backend_receives_verified_pcm_and_publishes_five_lane_gates(self):
        backend = self.root / "backend.py"
        backend.write_text("""#!%s
import argparse,json
p=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--result');a=p.parse_args()
r=json.load(open(a.request)); assert r['wav_sha256'] and r['frames']==64000
json.dump({'bpm':120,'origin_sample':0,'tempo_mode':'manual','detector':{'backend_id':'fixture-pretrained','artifact_sha256':'a'*64},'lane_onset_gates':dict.fromkeys(('BD','SD','CHH','OHH','BASS'),.5),'candidates':[]},open(a.result,'w'))
""" % sys.executable, encoding="utf-8")
        backend.chmod(0o700)
        process, peer = self.start(backend)
        try:
            peer.send(json.dumps(request(self.wav)).encode("utf-8"))
            message = self.receive(peer)
            self.assertEqual(message["status"], "COMPLETED")
            result = Path(message["result_path"])
            stored = json.loads(result.read_text())
            self.assertEqual(stored["wav_sha256"], request(self.wav)["wav_sha256"])
            self.assertEqual(set(stored["analysis"]["lane_onset_gates"]), set(LANES))
            self.assertEqual(stored["analysis"]["detector"]["backend_id"], "fixture-pretrained")
        finally:
            self.stop(process, peer)

    def test_absent_backend_fails_without_a_result_or_ready_payload(self):
        process, peer = self.start()
        try:
            peer.send(json.dumps(request(self.wav)).encode("utf-8"))
            message = self.receive(peer)
            self.assertEqual(message, {**{key: request(self.wav)[key] for key in ("protocol_version", "job_id", "project_id", "generation", "analysis_revision")},
                                       "command": "ANALYSE", "status": "FAILED", "analysis_error": "ANALYSIS_BACKEND_UNAVAILABLE"})
            self.assertFalse(any((self.runtime / "results").glob("*.json")))
        finally:
            self.stop(process, peer)


if __name__ == "__main__": unittest.main()

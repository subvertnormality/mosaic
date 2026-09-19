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
LAUNCHER = ROOT / "tools" / "rhythm_doctor" / "launch_analysis_worker.py"
LANES = ("BD", "SD", "CYM", "BASS")
BACKEND_HASH = "a" * 64
DRUM_HASH = "b" * 64
BASS_HASH = "c" * 64
sys.path.insert(0, str(WORKER.parent))
import rd_analysis_worker


def request(wav: Path) -> dict:
    with wave.open(str(wav), "rb") as source:
        frames, sample_rate = source.getnframes(), source.getframerate()
    return {"protocol_version": 1, "job_id": "analysis-job", "project_id": "project-a",
            "generation": 3, "analysis_revision": 2, "command": "ANALYSE", "wav_path": str(wav),
            "wav_sha256": hashlib.sha256(wav.read_bytes()).hexdigest(), "frames": frames,
            "sample_rate": sample_rate, "result_schema_version": 2, "max_candidates": 22500}


class AnalysisWorkerValidation(unittest.TestCase):
    def valid(self):
        return {"bpm": 120, "origin_sample": 0, "detector": {"backend_id": "pinned-v1",
                "backend_sha256": BACKEND_HASH, "drum_artifact_sha256": DRUM_HASH,
                "bass_artifact_sha256": BASS_HASH},
                "lane_onset_gates": dict.fromkeys(LANES, .5), "candidates": [
                    {"lane": "CYM", "sample_index": 10, "velocity": 90, "confidence": .8},
                    {"lane": "BASS", "sample_index": 20, "velocity": 91, "confidence": .7},
                ]}

    def test_every_active_lane_requires_its_own_gate(self):
        value = self.valid(); del value["lane_onset_gates"]["CYM"]
        self.assertFalse(rd_analysis_worker.analysis_is_pretrained(value, BACKEND_HASH, DRUM_HASH, BASS_HASH))

    def test_unknown_lane_and_unpinned_artifact_are_rejected(self):
        value = self.valid(); value["candidates"][0]["lane"] = "HH"
        self.assertFalse(rd_analysis_worker.analysis_is_pretrained(value, BACKEND_HASH, DRUM_HASH, BASS_HASH))
        value = self.valid(); value["detector"]["drum_artifact_sha256"] = "d" * 64
        self.assertFalse(rd_analysis_worker.analysis_is_pretrained(value, BACKEND_HASH, DRUM_HASH, BASS_HASH))

    def test_capture_contract_cannot_exceed_forty_five_seconds(self):
        self.assertTrue(rd_analysis_worker.capture_is_bounded({"frames": 45 * 8000, "sample_rate": 8000}))
        self.assertFalse(rd_analysis_worker.capture_is_bounded({"frames": 45 * 8000 + 1, "sample_rate": 8000}))

    def test_launcher_refuses_partial_or_changed_local_backend_profile(self):
        with tempfile.TemporaryDirectory(prefix="rd-analysis-launch-") as directory:
            root = Path(directory); runtime = root / "runtime"; backend = root / "backend"
            backend.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8"); backend.chmod(0o700)
            partial = subprocess.run([sys.executable, str(LAUNCHER), "--runtime", str(runtime), "--backend", str(backend)],
                                     text=True, capture_output=True, timeout=3)
            self.assertNotEqual(partial.returncode, 0)
            self.assertIn("incomplete analysis backend configuration", (runtime / "error").read_text())
            changed = subprocess.run([sys.executable, str(LAUNCHER), "--runtime", str(runtime), "--backend", str(backend),
                                       "--backend-sha256", "0" * 64, "--drum-artifact-sha256", DRUM_HASH,
                                       "--bass-artifact-sha256", BASS_HASH], text=True, capture_output=True, timeout=3)
            self.assertNotEqual(changed.returncode, 0)
            self.assertIn("invalid analysis backend", (runtime / "error").read_text())


@unittest.skipUnless(hasattr(socket, "AF_UNIX") and hasattr(socket, "SOCK_SEQPACKET"), "requires AF_UNIX SOCK_SEQPACKET")
class AnalysisWorkerIPC(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-analysis-worker-")
        self.root = Path(self.temporary.name); self.runtime = self.root / "runtime"; self.runtime.mkdir()
        self.wav = self.root / "capture.wav"
        with wave.open(str(self.wav), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(8000); output.writeframes(b"\0\0" * 64000)
        self.long_wav = self.root / "too-long.wav"
        with wave.open(str(self.long_wav), "wb") as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(8000); output.writeframes(b"\0\0" * (45 * 8000 + 1))

    def tearDown(self): self.temporary.cleanup()

    def start(self, backend=None):
        command = [sys.executable, str(WORKER), "--runtime", str(self.runtime)]
        if backend: command += ["--backend", str(backend), "--backend-sha256", hashlib.sha256(backend.read_bytes()).hexdigest(),
                                "--drum-artifact-sha256", DRUM_HASH, "--bass-artifact-sha256", BASS_HASH]
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

    def test_pinned_backend_receives_verified_pcm_and_publishes_every_lane_gate(self):
        backend = self.root / "backend.py"
        backend.write_text("""#!%s
import argparse,json
p=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--result');a=p.parse_args()
r=json.load(open(a.request)); assert r['wav_sha256'] and r['frames']==64000
p=r['pretrained']; assert p['drum_artifact_sha256']=='%s' and p['bass_artifact_sha256']=='%s'
json.dump({'bpm':120,'origin_sample':0,'tempo_mode':'manual','detector':{'backend_id':'fixture-pretrained','backend_sha256':p['backend_sha256'],'drum_artifact_sha256':p['drum_artifact_sha256'],'bass_artifact_sha256':p['bass_artifact_sha256']},'lane_onset_gates':dict.fromkeys(('BD','SD','CYM','BASS'),.5),'candidates':[]},open(a.result,'w'))
""" % (sys.executable, DRUM_HASH, BASS_HASH), encoding="utf-8")
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
            self.assertEqual(stored["analysis"]["detector"]["drum_artifact_sha256"], DRUM_HASH)
            self.assertEqual(stored["analysis"]["detector"]["bass_artifact_sha256"], BASS_HASH)
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

    def test_omnizart_partial_drum_backend_reports_its_missing_bass_component(self):
        backend = self.root / "omnizart_backend.py"
        backend.write_text("""#!%s
import argparse,json
p=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--result');a=p.parse_args()
json.dump({'backend_error':'OMNIZART_BASS_BACKEND_REQUIRED'},open(a.result,'w'))
""" % sys.executable, encoding="utf-8")
        backend.chmod(0o700)
        process, peer = self.start(backend)
        try:
            peer.send(json.dumps(request(self.wav)).encode("utf-8"))
            message = self.receive(peer)
            self.assertEqual(message["status"], "FAILED")
            self.assertEqual(message["analysis_error"], "OMNIZART_BASS_BACKEND_REQUIRED")
            self.assertFalse(any((self.runtime / "results").glob("*.json")))
        finally:
            self.stop(process, peer)

    def test_forty_five_second_capture_bound_is_enforced_before_backend_execution(self):
        backend = self.root / "unexpected-backend.py"
        backend.write_text("#!%s\nraise SystemExit('backend must not run')\n" % sys.executable, encoding="utf-8")
        backend.chmod(0o700)
        process, peer = self.start(backend)
        try:
            peer.send(json.dumps(request(self.long_wav)).encode("utf-8"))
            self.assertEqual(self.receive(peer)["analysis_error"], "ANALYSIS_CAPTURE_BOUNDS")
        finally:
            self.stop(process, peer)

    def test_cancel_terminates_pinned_backend_without_publishing_a_result(self):
        backend = self.root / "blocking-backend.py"
        marker = self.root / "completed"
        backend.write_text("""#!%s
import argparse, pathlib, time
p=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--result');a=p.parse_args()
time.sleep(30)
pathlib.Path(%r).write_text('completed')
""" % (sys.executable, str(marker)), encoding="utf-8")
        backend.chmod(0o700)
        process, peer = self.start(backend)
        try:
            value = request(self.wav)
            peer.send(json.dumps(value).encode("utf-8"))
            cancel = {key: value[key] for key in ("protocol_version", "job_id", "project_id", "generation", "analysis_revision")}
            cancel["command"] = "CANCEL"
            peer.send(json.dumps(cancel).encode("utf-8"))
            self.assertEqual(self.receive(peer)["status"], "CANCELLED")
            time.sleep(.1)
            self.assertFalse(marker.exists())
            self.assertFalse(any((self.runtime / "results").glob("*.json")))
        finally:
            self.stop(process, peer)



class DspBackendConfigurationTests(unittest.TestCase):
    """The launcher must be able to configure the shipped DSP backend.

    It previously demanded model-artifact digests that a model-free backend
    does not have, so the detector that ships could not be launched at all.
    """

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-dspcfg-")
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def _backend(self):
        path = self.root / "backend.py"
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o700)
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def _launch(self, runtime, *extra):
        return subprocess.call([sys.executable, str(LAUNCHER), "--runtime", str(runtime), *extra],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_a_template_identity_is_accepted(self):
        runtime = self.root / "rt-ok"
        backend, digest = self._backend()
        code = self._launch(runtime, "--backend", str(backend), "--backend-sha256", digest,
                            "--template-sha256", "b" * 64)
        self.assertNotEqual((runtime / "error").exists() and (runtime / "error").read_text(), 
                            "incomplete analysis backend configuration\n")

    def test_mixing_the_two_identity_shapes_is_refused(self):
        runtime = self.root / "rt-mixed"
        backend, digest = self._backend()
        self._launch(runtime, "--backend", str(backend), "--backend-sha256", digest,
                     "--template-sha256", "b" * 64, "--drum-artifact-sha256", "c" * 64)
        self.assertIn("incomplete analysis backend configuration", (runtime / "error").read_text())

    def test_a_template_identity_missing_its_digest_is_refused(self):
        runtime = self.root / "rt-partial"
        backend, digest = self._backend()
        self._launch(runtime, "--backend", str(backend), "--backend-sha256", digest)
        self.assertIn("incomplete analysis backend configuration", (runtime / "error").read_text())


if __name__ == "__main__": unittest.main()

"""The analysis launcher must actually publish a usable mailbox path.

Nothing drove this helper end to end, so a name collision between the status
file it writes and the directory the worker creates reached a device: the
launcher raised IsADirectoryError, wrote an error file instead of a mailbox,
and Rhythm Doctor sat on ANALYSING forever with no worker to talk to.
"""
import hashlib
import json
import math
import shutil
import struct
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mailbox_client import MailboxClient

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "tools" / "rhythm_doctor" / "launch_analysis_worker.py"
DRUM = "a" * 64
BASS = "b" * 64


class LaunchAnalysisWorker(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-launch-analysis-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / "runtime"
        self.backend = self.root / "backend.py"
        self.backend.write_text(
            "#!%s\nimport argparse,json\n"
            "p=argparse.ArgumentParser();p.add_argument('--request');p.add_argument('--result')\n"
            "a=p.parse_args();json.dump({}, open(a.result,'w'))\n" % sys.executable, encoding="utf-8")
        self.backend.chmod(0o700)
        self.digest = hashlib.sha256(self.backend.read_bytes()).hexdigest()

    def launch(self):
        return subprocess.run(
            [sys.executable, str(LAUNCHER), "--runtime", str(self.runtime),
             "--backend", str(self.backend), "--backend-sha256", self.digest,
             "--drum-artifact-sha256", DRUM, "--bass-artifact-sha256", BASS],
            capture_output=True, text=True, timeout=120)

    def stop(self):
        pid = (self.runtime / "pid").read_text().strip()
        subprocess.run(["kill", pid], capture_output=True)

    def test_it_publishes_a_mailbox_the_host_can_read(self):
        result = self.launch()
        problem = self.runtime / "error"
        self.assertFalse(problem.is_file(), problem.read_text() if problem.is_file() else "")
        self.assertEqual(result.returncode, 0, result.stderr)
        published = self.runtime / "mailbox"
        self.assertTrue(published.is_file(), "the launcher must publish a mailbox path as a file")
        self.addCleanup(self.stop)
        root = Path(published.read_text().strip())
        self.assertTrue(root.is_absolute() and root.is_dir(), "the published path must be the worker's mailbox root")
        for direction in ("c2w", "w2c"):
            self.assertTrue((root / direction).is_dir(), direction + " is missing from the mailbox")
        # And it must actually answer, which is what the host does next.
        peer = MailboxClient(root)
        peer.send(json.dumps({"protocol_version": 1, "job_id": "j", "project_id": "p",
                              "generation": 1, "analysis_revision": 1, "command": "CANCEL"}).encode())
        reply = json.loads(peer.receive(10).decode())
        self.assertEqual(reply["status"], "FAILED")
        self.assertEqual(reply["analysis_error"], "ANALYSIS_STALE_CANCEL")

    def test_a_relaunch_over_a_live_runtime_still_publishes(self):
        """The runtime directory is reused across sessions, not created fresh."""
        self.launch()
        self.addCleanup(self.stop)
        first = (self.runtime / "mailbox").read_text().strip()
        self.stop()
        result = self.launch()
        self.assertFalse((self.runtime / "error").is_file(), (self.runtime / "error").read_text()
                         if (self.runtime / "error").is_file() else "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.runtime / "mailbox").is_file())
        self.assertTrue(Path(first).name)



def capture_wav(path, seconds=3.0, rate=44100):
    """A short stereo capture with clear transients on a steady pulse."""
    frames = int(seconds * rate)
    period = int(rate * 0.5)                      # 120 BPM
    body = bytearray()
    for i in range(frames):
        phase = i % period
        envelope = math.exp(-phase / (rate * 0.02)) if phase < rate * 0.2 else 0.0
        value = int(20000 * envelope * math.sin(2 * math.pi * 110 * i / rate))
        body += struct.pack("<hh", value, value)
    head = b"RIFF" + struct.pack("<I", 36 + len(body)) + b"WAVEfmt " + \
        struct.pack("<IHHIIHH", 16, 1, 2, rate, rate * 4, 4, 16) + \
        b"data" + struct.pack("<I", len(body))
    path.write_bytes(head + bytes(body))
    return frames, rate


@unittest.skipUnless(shutil.which("gcc"), "requires GCC to build the native backend")
class NativeBackendEndToEnd(LaunchAnalysisWorker):
    """The out-of-the-box path: no backend configured, so Mosaic builds its own.

    Nothing drove the launcher and the worker together on this path, and they
    disagreed about what --backend-sha256 means: the launcher passes the C
    source digest, because that is the reproducible identity a result declares,
    while the worker hashed the compiled binary. Every analysis on a stock
    install failed with ANALYSIS_BACKEND_MISMATCH.
    """

    def launch(self):
        tools = ROOT / "tools" / "rhythm_doctor"
        return subprocess.run(
            [sys.executable, str(LAUNCHER), "--runtime", str(self.runtime),
             "--native-source", str(tools / "rd_analysis_backend.c"),
             "--templates", str(tools / "data" / "nmf_drum_templates.bin")],
            capture_output=True, text=True, timeout=900)

    def test_the_native_backend_analyses_a_capture(self):
        result = self.launch()
        problem = self.runtime / "error"
        self.assertFalse(problem.is_file(), problem.read_text() if problem.is_file() else "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(self.stop)
        root = Path((self.runtime / "mailbox").read_text().strip())
        wav = self.root / "capture.wav"
        frames, rate = capture_wav(wav)
        peer = MailboxClient(root)
        peer.send(json.dumps({
            "protocol_version": 1, "job_id": "j", "project_id": "p",
            "generation": 1, "analysis_revision": 1, "command": "ANALYSE",
            "wav_path": str(wav), "wav_sha256": hashlib.sha256(wav.read_bytes()).hexdigest(),
            "frames": frames, "sample_rate": rate,
            "result_schema_version": 1, "max_candidates": 512}).encode())
        reply = json.loads(peer.receive(600).decode())
        self.assertEqual(reply["status"], "COMPLETED",
                         "a stock install must be able to analyse: " + str(reply.get("analysis_error")))
        stored = json.loads(Path(reply["result_path"]).read_text())
        detector = stored["analysis"]["detector"]
        self.assertEqual(detector["backend_id"], "nmf-pfnmf-drums-v1")
        # The identity a result declares is the source and template it was
        # built from, which reproduces; a compiled binary does not.
        tools = ROOT / "tools" / "rhythm_doctor"
        self.assertEqual(detector["backend_sha256"],
                         hashlib.sha256((tools / "rd_analysis_backend.c").read_bytes()).hexdigest())
        self.assertEqual(detector["template_sha256"],
                         hashlib.sha256((tools / "data" / "nmf_drum_templates.bin").read_bytes()).hexdigest())
        self.assertGreater(stored["analysis"]["bpm"], 0)


if __name__ == "__main__":
    unittest.main()

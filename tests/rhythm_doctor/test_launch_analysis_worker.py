"""The analysis launcher must actually publish a usable mailbox path.

Nothing drove this helper end to end, so a name collision between the status
file it writes and the directory the worker creates reached a device: the
launcher raised IsADirectoryError, wrote an error file instead of a mailbox,
and Rhythm Doctor sat on ANALYSING forever with no worker to talk to.
"""
import hashlib
import json
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


if __name__ == "__main__":
    unittest.main()

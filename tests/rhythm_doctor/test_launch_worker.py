"""The capture launcher must publish a mailbox the host can actually open.

Its sibling, the analysis launcher, shipped a name collision between the status
file it writes and the directory the worker creates, and nothing caught it
because no test drove either helper end to end. This drives this one. It needs
no JACK server: the worker publishes its mailbox before it ever opens an audio
client, which is precisely why a missing server is reportable rather than fatal.
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mailbox_client import MailboxClient

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "tools" / "rhythm_doctor" / "launch_worker.py"
SOURCE = ROOT / "tools" / "rhythm_doctor"


@unittest.skipUnless(shutil.which("gcc"), "requires GCC to build the worker")
class LaunchWorker(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rd-launch-worker-")
        self.addCleanup(self.temporary.cleanup)
        self.runtime = Path(self.temporary.name) / "runtime"

    def launch(self):
        return subprocess.run(
            [sys.executable, str(LAUNCHER), "--source", str(SOURCE), "--runtime", str(self.runtime),
             "--left", "missing:left", "--right", "missing:right"],
            capture_output=True, text=True, timeout=300)

    def stop(self):
        published = self.runtime / "pid"
        if published.is_file():
            subprocess.run(["kill", published.read_text().strip()], capture_output=True)

    def test_it_publishes_a_mailbox_the_host_can_open(self):
        result = self.launch()
        problem = self.runtime / "error"
        self.assertFalse(problem.is_file(), problem.read_text() if problem.is_file() else "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(self.stop)
        published = self.runtime / "mailbox"
        self.assertTrue(published.is_file(), "the launcher must publish a mailbox path as a file")
        root = Path(published.read_text().strip())
        self.assertTrue(root.is_absolute() and root.is_dir(), "the published path must be the worker's root")
        for direction in ("c2w", "w2c"):
            self.assertTrue((root / direction).is_dir(), direction + " is missing from the mailbox")
        # And it answers, which is the next thing the host does.
        peer = MailboxClient(root, limit=1023)
        peer.send(b"RD1\tj\tp\t0\t0\tPREFLIGHT\t1,manual")
        reply = peer.receive(10).decode().split("\t")
        self.assertEqual(reply[:6], ["RD1", "j", "p", "0", "0", "PREFLIGHT"])
        # Without a JACK server this fails, and naming why is the whole point.
        self.assertEqual(reply[6], "FAILED")
        self.assertEqual(reply[7], "AUDIO_SERVER_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()

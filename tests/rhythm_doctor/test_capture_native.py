"""Dedicated-JACK RD-01 acceptance: actual PCM reaches the native input ports."""
import ctypes
import os
import pathlib
import shutil
import struct
import subprocess
import tempfile
import time
import unittest
import uuid


ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools" / "rhythm_doctor" / "rd_capture.c"
INJECTOR = ROOT / "tests" / "rhythm_doctor" / "test_capture_injector.c"


@unittest.skipUnless(all(shutil.which(name) for name in ("gcc", "jackd", "jack_connect")),
                     "requires gcc and JACK tools")
class NativeJackCaptureTests(unittest.TestCase):
    @staticmethod
    def _terminate_process(process):
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)
        if process.stderr:
            process.stderr.close()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="rd-capture-jack-")
        self.addCleanup(self.temp.cleanup)
        self.path = pathlib.Path(self.temp.name)
        self.server_name = "rd-capture-" + uuid.uuid4().hex
        self.environment = os.environ.copy()
        self.environment["JACK_DEFAULT_SERVER"] = self.server_name
        previous_server = os.environ.get("JACK_DEFAULT_SERVER")
        os.environ["JACK_DEFAULT_SERVER"] = self.server_name
        self.addCleanup(self._restore_server_environment, previous_server)
        self.server = subprocess.Popen(["jackd", "--name", self.server_name, "-d", "dummy", "-r", "48000", "-p", "128"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, env=self.environment)
        self.addCleanup(self._terminate_process, self.server)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if self.server.poll() is not None:
                self.fail("dedicated jackd exited: " + self.server.stderr.read())
            if subprocess.run(["jack_lsp"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              env=self.environment).returncode == 0:
                break
            time.sleep(.05)
        else:
            self.fail("dedicated jackd did not become ready")
        self.library_path = self.path / "librd_capture.so"
        self.injector_path = self.path / "rd_injector"
        subprocess.run(["gcc", "-shared", "-fPIC", "-std=c11", "-O2", str(SOURCE), "-o",
                        str(self.library_path), "-ljack"], check=True, cwd=ROOT)
        subprocess.run(["gcc", "-std=c11", "-O2", str(INJECTOR), "-o", str(self.injector_path), "-ljack"],
                       check=True, cwd=ROOT)
        self.lib = ctypes.CDLL(str(self.library_path))
        self.lib.rd_capture_preflight.argtypes = [ctypes.c_uint32]
        self.lib.rd_capture_preflight.restype = ctypes.c_void_p
        self.lib.rd_capture_destroy.argtypes = [ctypes.c_void_p]
        self.lib.rd_capture_start.argtypes = [ctypes.c_void_p]
        self.lib.rd_capture_stop.argtypes = [ctypes.c_void_p]
        self.lib.rd_capture_state.argtypes = [ctypes.c_void_p]
        self.lib.rd_capture_state.restype = ctypes.c_int
        self.lib.rd_capture_error.argtypes = [ctypes.c_void_p]
        self.lib.rd_capture_error.restype = ctypes.c_int
        self.lib.rd_capture_frames.argtypes = [ctypes.c_void_p]
        self.lib.rd_capture_frames.restype = ctypes.c_uint64
        self.lib.rd_capture_input_port.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        self.lib.rd_capture_input_port.restype = ctypes.c_char_p
        self.lib.rd_capture_publish_wav.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.lib.rd_capture_publish_wav.restype = ctypes.c_int
        self.lib.rd_capture_preflight_nanoseconds.argtypes = [ctypes.c_void_p]
        self.lib.rd_capture_preflight_nanoseconds.restype = ctypes.c_uint64
        self.lib.rd_capture_pcm_locked.argtypes = [ctypes.c_void_p]
        self.lib.rd_capture_pcm_locked.restype = ctypes.c_int

    @staticmethod
    def _restore_server_environment(previous_server):
        if previous_server is None:
            os.environ.pop("JACK_DEFAULT_SERVER", None)
        else:
            os.environ["JACK_DEFAULT_SERVER"] = previous_server

    def test_preflight_never_autostarts_or_attaches_to_another_server_name(self):
        original = os.environ["JACK_DEFAULT_SERVER"]
        os.environ["JACK_DEFAULT_SERVER"] = self.server_name + "-missing"
        try:
            self.assertFalse(self.lib.rd_capture_preflight(45))
        finally:
            os.environ["JACK_DEFAULT_SERVER"] = original

    def test_server_shutdown_fails_an_armed_capture(self):
        self.capture = self.lib.rd_capture_preflight(45)
        self.assertTrue(self.capture)
        self.addCleanup(self.lib.rd_capture_destroy, self.capture)
        self.assertEqual(self.lib.rd_capture_start(self.capture), 0)
        self.server.terminate()
        self.server.wait(timeout=3)
        deadline = time.monotonic() + 2
        while (self.lib.rd_capture_state(self.capture) != 6 or self.lib.rd_capture_error(self.capture) != 6) and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(self.lib.rd_capture_state(self.capture), 6)
        self.assertEqual(self.lib.rd_capture_error(self.capture), 6)  # SERVER_SHUTDOWN

    def test_injected_stereo_pcm_is_contiguous_and_atomically_published_after_stop(self):
        self.capture = self.lib.rd_capture_preflight(45)
        self.assertTrue(self.capture, "JACK preflight must own and activate input ports")
        self.addCleanup(self.lib.rd_capture_destroy, self.capture)
        self.assertGreater(self.lib.rd_capture_preflight_nanoseconds(self.capture), 0)
        self.assertIn(self.lib.rd_capture_pcm_locked(self.capture), (0, 1), "mlock is optional but accounted")
        self.injector = subprocess.Popen([str(self.injector_path)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                         text=True, env=self.environment)
        self.addCleanup(self._terminate_process, self.injector)
        time.sleep(.15)
        for source, destination in (("rd-capture-injector:left", 0), ("rd-capture-injector:right", 1)):
            subprocess.run(["jack_connect", source, self.lib.rd_capture_input_port(self.capture, destination).decode()],
                           check=True, env=self.environment)
        self.assertEqual(self.lib.rd_capture_start(self.capture), 0)
        time.sleep(.12)
        self.assertEqual(self.lib.rd_capture_stop(self.capture), 0)
        deadline = time.monotonic() + 2
        while self.lib.rd_capture_state(self.capture) != 4 and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertEqual(self.lib.rd_capture_state(self.capture), 4)
        self.assertGreater(self.lib.rd_capture_frames(self.capture), 256)
        wav = self.path / "capture.wav"
        self.assertFalse(wav.exists())
        self.assertEqual(self.lib.rd_capture_publish_wav(self.capture, str(wav).encode()), 0)
        self.assertTrue(wav.exists())
        self.assertFalse((self.path / "capture.wav.tmp").exists())
        payload = wav.read_bytes()
        self.assertEqual(payload[:4] + payload[8:12], b"RIFFWAVE")
        self.assertEqual(struct.unpack_from("<HHIIHH", payload, 20), (3, 2, 48000, 384000, 8, 32))
        data_bytes = struct.unpack_from("<I", payload, 40)[0]
        self.assertEqual(data_bytes, len(payload) - 44)
        values = struct.unpack("<" + "f" * (data_bytes // 4), payload[44:])
        left, right = values[::2], values[1::2]
        self.assertTrue(all(abs(l + r) < 1e-7 for l, r in zip(left, right)))
        deltas = [round((b - a) * 1000) for a, b in zip(left, left[1:])]
        self.assertTrue(all(delta in (1, -999) for delta in deltas), "no dropped or rewritten PCM frames")
        prior = self.path / "prior.wav"
        prior.write_bytes(b"previous-published-file")
        self.assertEqual(self.lib.rd_capture_publish_wav(self.capture, str(prior).encode()), -1)
        self.assertEqual(prior.read_bytes(), b"previous-published-file")
        self.assertEqual((self.lib.rd_capture_state(self.capture), self.lib.rd_capture_error(self.capture)), (4, 4))


if __name__ == "__main__":
    unittest.main()

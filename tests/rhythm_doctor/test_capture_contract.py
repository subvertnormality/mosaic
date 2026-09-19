"""RD-01 native capture characterisation outside the manual; see CAPTURE.md.

The baseline named in CAPTURE.md had no owned native capture source, so this
module is intentionally an acceptance test for the spike rather than Mosaic UI.
"""
import ctypes
import pathlib
import subprocess
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools" / "rhythm_doctor" / "rd_capture.c"


class CaptureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix="rd-capture-unit-")
        cls.library_path = pathlib.Path(cls.build.name) / "librd_capture.so"
        subprocess.run([
            "gcc", "-shared", "-fPIC", "-std=c11", "-O2", "-DRD_CAPTURE_TESTING",
            str(SOURCE), "-o", str(cls.library_path), "-ljack",
        ], check=True, cwd=ROOT)
        cls.lib = ctypes.CDLL(str(cls.library_path))
        cls.lib.rd_capture_test_create.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        cls.lib.rd_capture_test_create.restype = ctypes.c_void_p
        cls.lib.rd_capture_test_destroy.argtypes = [ctypes.c_void_p]
        cls.lib.rd_capture_start.argtypes = [ctypes.c_void_p]
        cls.lib.rd_capture_stop.argtypes = [ctypes.c_void_p]
        cls.lib.rd_capture_cancel.argtypes = [ctypes.c_void_p]
        cls.lib.rd_capture_state.argtypes = [ctypes.c_void_p]
        cls.lib.rd_capture_state.restype = ctypes.c_int
        cls.lib.rd_capture_error.argtypes = [ctypes.c_void_p]
        cls.lib.rd_capture_error.restype = ctypes.c_int
        cls.lib.rd_capture_frames.argtypes = [ctypes.c_void_p]
        cls.lib.rd_capture_frames.restype = ctypes.c_uint64
        cls.lib.rd_capture_start_frame.argtypes = [ctypes.c_void_p]
        cls.lib.rd_capture_start_frame.restype = ctypes.c_uint64
        cls.lib.rd_capture_end_frame.argtypes = [ctypes.c_void_p]
        cls.lib.rd_capture_end_frame.restype = ctypes.c_uint64
        cls.lib.rd_capture_test_process.argtypes = [ctypes.c_void_p, ctypes.c_uint64,
                                                    ctypes.POINTER(ctypes.c_float),
                                                    ctypes.POINTER(ctypes.c_float), ctypes.c_uint32]
        cls.lib.rd_capture_test_copy.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float),
                                                  ctypes.POINTER(ctypes.c_float), ctypes.c_uint32]
        cls.lib.rd_capture_test_copy.restype = ctypes.c_uint32
        cls.lib.rd_capture_test_xrun.argtypes = [ctypes.c_void_p]

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def new(self, seconds=1, rate=8):
        capture = self.lib.rd_capture_test_create(rate, seconds)
        self.assertTrue(capture)
        self.addCleanup(self.lib.rd_capture_test_destroy, capture)
        return capture

    def process(self, capture, frame, left, right):
        nframes = len(left)
        l = (ctypes.c_float * nframes)(*left)
        r = (ctypes.c_float * nframes)(*right)
        self.lib.rd_capture_test_process(capture, frame, l, r, nframes)

    def copied(self, capture, count):
        left, right = (ctypes.c_float * count)(), (ctypes.c_float * count)()
        actual = self.lib.rd_capture_test_copy(capture, left, right, count)
        return list(left)[:actual], list(right)[:actual]

    def test_first_callback_sets_authoritative_sample_origin_and_preserves_stereo(self):
        capture = self.new()
        self.assertEqual(self.lib.rd_capture_state(capture), 0)  # READY
        self.assertEqual(self.lib.rd_capture_start(capture), 0)
        self.process(capture, 912, [0.25, -0.5, 0.75], [-0.25, 0.5, -0.75])
        self.assertEqual(self.lib.rd_capture_start_frame(capture), 912)
        self.assertEqual(self.lib.rd_capture_frames(capture), 3)
        self.assertEqual(self.lib.rd_capture_end_frame(capture), 915)
        self.assertEqual(self.copied(capture, 3), ([0.25, -0.5, 0.75], [-0.25, 0.5, -0.75]))

    def test_stop_is_completed_by_callback_and_never_accepts_a_later_block(self):
        capture = self.new()
        self.lib.rd_capture_start(capture)
        self.process(capture, 40, [1.0, 2.0], [-1.0, -2.0])
        self.assertEqual(self.lib.rd_capture_stop(capture), 0)
        self.assertEqual(self.lib.rd_capture_state(capture), 3)  # STOP_REQUESTED
        self.process(capture, 42, [3.0, 4.0], [-3.0, -4.0])
        self.assertEqual(self.lib.rd_capture_state(capture), 4)  # COMPLETED
        self.assertEqual(self.lib.rd_capture_frames(capture), 2)
        self.assertEqual(self.copied(capture, 8), ([1.0, 2.0], [-1.0, -2.0]))

    def test_cancel_discards_and_cannot_be_published_or_restarted(self):
        capture = self.new()
        self.lib.rd_capture_start(capture)
        self.process(capture, 8, [0.1], [-0.1])
        self.assertEqual(self.lib.rd_capture_cancel(capture), 0)
        self.process(capture, 9, [0.2], [-0.2])
        self.assertEqual(self.lib.rd_capture_state(capture), 5)  # CANCELLED
        self.assertEqual(self.lib.rd_capture_start(capture), -1)

    def test_capacity_automatically_completes_and_retains_partial_final_block(self):
        capture = self.new(seconds=1, rate=4)
        self.lib.rd_capture_start(capture)
        self.process(capture, 0, [1.0, 2.0, 3.0], [-1.0, -2.0, -3.0])
        self.process(capture, 3, [4.0, 5.0, 6.0], [-4.0, -5.0, -6.0])
        self.assertEqual(self.lib.rd_capture_state(capture), 4)  # COMPLETED at cap
        self.assertEqual(self.lib.rd_capture_frames(capture), 4)
        self.assertEqual(self.copied(capture, 4), ([1.0, 2.0, 3.0, 4.0], [-1.0, -2.0, -3.0, -4.0]))

    def test_discontinuous_callback_frame_is_visible_failure(self):
        capture = self.new()
        self.lib.rd_capture_start(capture)
        self.process(capture, 100, [1.0, 2.0], [-1.0, -2.0])
        self.process(capture, 103, [3.0], [-3.0])
        self.assertEqual(self.lib.rd_capture_state(capture), 6)
        self.assertEqual(self.lib.rd_capture_error(capture), 5)  # DISCONTINUITY

    def test_cancel_wins_over_pending_stop_completion(self):
        capture = self.new()
        self.lib.rd_capture_start(capture)
        self.process(capture, 20, [1.0], [-1.0])
        self.assertEqual(self.lib.rd_capture_stop(capture), 0)
        self.assertEqual(self.lib.rd_capture_cancel(capture), 0)
        self.process(capture, 21, [2.0], [-2.0])
        self.assertEqual(self.lib.rd_capture_state(capture), 5)

    def test_invalid_commands_are_rejected(self):
        capture = self.new()
        self.assertEqual(self.lib.rd_capture_stop(capture), -1)
        self.assertEqual(self.lib.rd_capture_cancel(capture), -1)
        self.lib.rd_capture_start(capture)
        self.assertEqual(self.lib.rd_capture_start(capture), -1)

    def test_xrun_is_a_visible_terminal_failure(self):
        capture = self.new()
        self.lib.rd_capture_start(capture)
        self.lib.rd_capture_test_xrun(capture)
        self.assertEqual(self.lib.rd_capture_state(capture), 6)  # FAILED
        self.assertEqual(self.lib.rd_capture_error(capture), 3)  # XRUN
        self.assertEqual(self.lib.rd_capture_stop(capture), -1)


if __name__ == "__main__":
    unittest.main()

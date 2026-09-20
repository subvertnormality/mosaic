"""The native analysis backend is what a stock install actually runs.

It is a port of dsp_drum_backend.py, so these check that it builds, satisfies
the worker's result contract, and finds the same onsets as the reference. They
do not demand identical output: the reference seeds numpy's PCG64 and the port
uses its own generator, and the reference already moves by an onset or two
between its own seeds. What must hold is that the two agree on essentially
every onset, which is what a player would notice.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools" / "rhythm_doctor"
SOURCE = TOOLS / "rd_analysis_backend.c"
TEMPLATES = TOOLS / "data" / "nmf_drum_templates.bin"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import dsp_drum_backend as dsp                                    # noqa: E402
from test_dsp_drum_backend import click_train                     # noqa: E402

TOLERANCE_SECONDS = 0.050


def build(target):
    """Compile exactly as the launcher does, minus the optional tuning flags."""
    done = subprocess.run(
        ["gcc", "-std=c11", "-O2", "-Wall", "-Wextra",
         '-DRD_TEMPLATE_PATH="' + str(TEMPLATES) + '"',
         '-DRD_SOURCE_PATH="' + str(SOURCE) + '"',
         str(SOURCE), "-o", str(target), "-lm"],
        capture_output=True, text=True, timeout=600)
    if done.returncode:
        raise AssertionError("native backend did not build: " + done.stderr[-2000:])
    return target


@unittest.skipUnless(shutil.which("gcc"), "a C compiler is required")
class NativeBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.binary = build(Path(cls.work.name) / "rd_analysis_backend")

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def capture(self, samples, rate=44100, channels=1):
        path = Path(self.work.name) / ("capture-%d.wav" % len(os.listdir(self.work.name)))
        frames = (np.clip(np.asarray(samples, dtype=np.float32), -1, 1) * 32767).astype("<i2")
        if channels == 2:
            frames = np.repeat(frames[:, None], 2, axis=1).ravel()
        with wave.open(str(path), "wb") as out:
            out.setnchannels(channels); out.setsampwidth(2); out.setframerate(rate)
            out.writeframes(frames.tobytes())
        return path

    def analyse(self, wav, alignment=None):
        request = Path(self.work.name) / "request.json"
        result = Path(self.work.name) / "result.json"
        result.unlink(missing_ok=True)
        payload = {"wav_path": str(wav)}
        if alignment is not None:
            payload["alignment"] = alignment
        request.write_text(json.dumps(payload))
        done = subprocess.run([str(self.binary), "--request", str(request), "--result", str(result)],
                              capture_output=True, text=True, timeout=900)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(result.read_text())

    def test_result_satisfies_the_worker_contract(self):
        value = self.analyse(self.capture(click_train([0.5, 1.0, 1.5, 2.0], kind="bd")))
        self.assertGreaterEqual(value["bpm"], dsp.BPM_MIN)
        self.assertLessEqual(value["bpm"], dsp.BPM_MAX)
        self.assertIsInstance(value["origin_sample"], int)
        self.assertIn(value["tempo_mode"], ("auto", "manual"))
        self.assertEqual(set(value["lane_onset_gates"]), set(dsp.LANES))
        self.assertEqual(value["detector"]["backend_id"], dsp.BACKEND_ID)
        for key in ("backend_sha256", "template_sha256"):
            self.assertRegex(value["detector"][key], r"^[0-9a-f]{64}$")
        for candidate in value["candidates"]:
            self.assertIn(candidate["lane"], dsp.LANES)
            self.assertGreaterEqual(candidate["sample_index"], 0)
            self.assertTrue(1 <= candidate["velocity"] <= 127)
            self.assertTrue(0 <= candidate["confidence"] <= 1)

    def test_identity_is_its_own_source_and_templates(self):
        import hashlib
        value = self.analyse(self.capture(click_train([0.5, 1.0], kind="bd")))
        for key, path in (("backend_sha256", SOURCE), ("template_sha256", TEMPLATES)):
            self.assertEqual(value["detector"][key],
                             hashlib.sha256(path.read_bytes()).hexdigest(),
                             key + " must be the digest of the real file")

    def test_silence_is_a_valid_empty_result(self):
        value = self.analyse(self.capture(np.zeros(44100)))
        self.assertEqual(value["candidates"], [])
        self.assertFalse(value["tempo_detected"])

    def test_a_confirmed_alignment_is_honoured(self):
        wav = self.capture(click_train([0.5, 1.0, 1.5, 2.0, 2.5], kind="bd"))
        value = self.analyse(wav, alignment={"bpm": 77.0, "origin_sample": 12345})
        self.assertEqual(value["bpm"], 77.0)
        self.assertEqual(value["origin_sample"], 12345)
        self.assertEqual(value["tempo_mode"], "manual")
        self.assertTrue(value["tempo_detected"])

    def test_it_finds_the_same_onsets_as_the_reference(self):
        signal = click_train([0.5, 1.0, 1.5, 2.0, 2.5, 3.0], kind="bd")
        snare = click_train([1.0, 2.0, 3.0], kind="sd")
        signal = signal + np.pad(snare, (0, max(0, len(signal) - len(snare))))[:len(signal)]
        wav = self.capture(signal)
        native, reference = self.analyse(wav), dsp.analyse_request(str(wav))
        rate = 44100
        for lane in dsp.LANES:
            want = sorted(c["sample_index"] for c in reference["candidates"] if c["lane"] == lane)
            got = sorted(c["sample_index"] for c in native["candidates"] if c["lane"] == lane)
            matched = sum(1 for a in want
                          if any(abs(a - b) <= TOLERANCE_SECONDS * rate for b in got))
            self.assertGreaterEqual(matched, len(want) - 1,
                                    "%s: reference %d, native %d, matched %d" %
                                    (lane, len(want), len(got), matched))
            self.assertLessEqual(abs(len(got) - len(want)), 1, lane)

    def test_a_forty_eight_kilohertz_capture_is_not_read_fast(self):
        times = [0.5, 1.0, 1.5, 2.0]
        at_44k = self.analyse(self.capture(click_train(times, kind="bd"), rate=44100))
        # click_train lays samples at 44.1k; to land at the same wall-clock
        # times in a 48k file those sample positions have to be stretched.
        signal = click_train([t * 48000 / 44100 for t in times], kind="bd")
        at_48k = self.analyse(self.capture(signal, rate=48000))
        first44 = min((c["sample_index"] / 44100 for c in at_44k["candidates"]), default=None)
        first48 = min((c["sample_index"] / 48000 for c in at_48k["candidates"]), default=None)
        self.assertIsNotNone(first44); self.assertIsNotNone(first48)
        self.assertLess(abs(first44 - first48), 0.030)


if __name__ == "__main__":
    unittest.main()

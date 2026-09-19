"""Regressions for the classical-DSP drum backend.

Characterisation outside README: this backend has no learned model. It uses
the GPL-3 partially-fixed NMF drum dictionary published with Wu & Lerch
(ISMIR 2015) and the peak-picking constants grid-searched by Boeck, Krebs &
Schedl (ISMIR 2012). See tools/rhythm_doctor/data/NMF_TEMPLATES_PROVENANCE.md.
"""
import json
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import os
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor"))
import dsp_drum_backend as dsp
import rd_analysis_worker


def click_train(times, sr=44100, seconds=4.0, kind="bd"):
    """Synthesise a crude but spectrally distinct drum-like train."""
    x = np.zeros(int(seconds * sr), dtype=np.float32)
    rng = np.random.default_rng(0)
    for t in times:
        i = int(t * sr)
        n = int(0.12 * sr)
        env = np.exp(-np.linspace(0, 12, n)).astype(np.float32)
        if kind == "bd":
            tone = np.sin(2 * np.pi * 60 * np.arange(n) / sr).astype(np.float32)
        elif kind == "chh":
            tone = rng.standard_normal(n).astype(np.float32)
            env = np.exp(-np.linspace(0, 60, n)).astype(np.float32)
        else:
            tone = rng.standard_normal(n).astype(np.float32) * 0.6
            tone += np.sin(2 * np.pi * 200 * np.arange(n) / sr).astype(np.float32)
        seg = tone * env
        x[i:i + len(seg)] += seg[:max(0, len(x) - i)]
    return x / (np.abs(x).max() + 1e-9)


class TemplateTests(unittest.TestCase):
    def test_published_templates_load_in_documented_lane_order(self):
        lanes, B, geom = dsp.load_templates()
        self.assertEqual(list(lanes), ["BD", "SD", "CHH"])
        self.assertEqual(B.shape, (1025, 3))
        self.assertEqual(geom, (2048, 512))
        freqs = np.fft.rfftfreq(2048, 1.0 / dsp.SR)
        cents = [float((freqs * B[:, i]).sum() / B[:, i].sum()) for i in range(3)]
        self.assertLess(cents[0], cents[1])
        self.assertLess(cents[1], cents[2])
        # The dictionary is only valid for its own STFT geometry.
        self.assertAlmostEqual(cents[0], 774.5, delta=5.0)
        self.assertAlmostEqual(cents[2], 12134.0, delta=20.0)


class PeakPickerTests(unittest.TestCase):
    """Each of Boeck's three conditions must actually be enforced."""

    def test_local_maximum_condition_rejects_a_shoulder(self):
        a = np.zeros(200, dtype=np.float32); a[100] = 1.0; a[101] = 0.9
        picked = dsp.pick_peaks(a, delta=0.1)
        self.assertIn(100, picked)
        self.assertNotIn(101, picked)

    def test_mean_threshold_condition_rejects_a_peak_inside_a_loud_plateau(self):
        a = np.full(200, 0.5, dtype=np.float32); a[100] = 0.55
        self.assertEqual(dsp.pick_peaks(a, delta=0.5), [])

    def test_minimum_interval_condition_suppresses_a_close_second_peak(self):
        a = np.zeros(200, dtype=np.float32); a[100] = 1.0; a[102] = 1.0
        picked = dsp.pick_peaks(a, delta=0.1, w5=5)
        self.assertEqual(len(picked), 1)

    def test_empty_and_silent_curves_yield_no_onsets(self):
        self.assertEqual(dsp.pick_peaks(np.zeros(0, dtype=np.float32), delta=0.1), [])
        self.assertEqual(dsp.pick_peaks(np.zeros(500, dtype=np.float32), delta=0.1), [])


class LaneScopeTests(unittest.TestCase):
    def test_the_third_lane_is_cymbals_not_closed_hi_hat(self):
        """The lane is CYM by design, and the distinction is load bearing.

        The hat template has high recall for metal but cannot separate a hat
        from a ride. Scored as closed-hat-only the same detector output reaches
        0.4374 F1 at 0.2965 precision on held-out real music; scored as CYM it
        reaches 0.7165 at 0.7006. Renaming this lane back to CHH would silently
        turn real cymbal detections into errors.
        """
        self.assertEqual(dsp.LANES, ("BD", "SD", "CYM", "BASS"))
        self.assertEqual(set(dsp.DEFAULT_DELTA), set(dsp.LANES))
        out = dsp.analyse(click_train([0.5, 1.0], kind="chh"))
        self.assertEqual(set(out), set(dsp.LANES))


class BackendTests(unittest.TestCase):
    def test_digital_silence_paints_nothing_on_every_lane(self):
        out = dsp.analyse(np.zeros(44100 * 2, dtype=np.float32))
        self.assertEqual(set(out), set(dsp.LANES))
        self.assertTrue(all(v == [] for v in out.values()))

    def test_repeated_analysis_is_deterministic(self):
        x = click_train([0.5, 1.0, 1.5, 2.0])
        self.assertEqual(dsp.analyse(x), dsp.analyse(x))

    def test_a_low_frequency_pulse_train_activates_the_bass_drum_lane(self):
        times = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        out = dsp.analyse(click_train(times, kind="bd"))
        matched = sum(1 for t in times if any(abs(t - g) <= 0.05 for g in out["BD"]))
        self.assertGreaterEqual(matched, 4, f"BD lane found {out['BD']}")

    def test_analysis_rejects_malformed_input_rather_than_guessing(self):
        with self.assertRaises(ValueError):
            dsp.analyse(np.zeros((2, 100), dtype=np.float32))
        with self.assertRaises(ValueError):
            dsp.analyse(np.array([np.nan, 0.0], dtype=np.float32))


class TempoTests(unittest.TestCase):
    def test_a_steady_pulse_recovers_its_tempo(self):
        fps = dsp.SR / dsp.HOP
        env = np.zeros(int(8 * fps), dtype=np.float32)
        period = int(round(60.0 / 120.0 * fps))          # 120 BPM
        env[::period] = 1.0
        bpm, detected = dsp.estimate_bpm(env, fps)
        self.assertTrue(detected)
        self.assertAlmostEqual(bpm, 120.0, delta=4.0)

    def test_an_unpulsed_envelope_reports_a_placeholder_rather_than_a_guess(self):
        fps = dsp.SR / dsp.HOP
        bpm, detected = dsp.estimate_bpm(np.zeros(400, dtype=np.float32), fps)
        self.assertFalse(detected)
        self.assertEqual(bpm, dsp.DEFAULT_BPM)

    def test_every_estimate_satisfies_the_bank_tempo_contract(self):
        fps = dsp.SR / dsp.HOP
        rng = np.random.default_rng(3)
        for _ in range(12):
            env = rng.random(int(6 * fps)).astype(np.float32)
            bpm, _ = dsp.estimate_bpm(env, fps)
            self.assertGreaterEqual(bpm, dsp.BPM_MIN)
            self.assertLessEqual(bpm, dsp.BPM_MAX)


class WorkerContractTests(unittest.TestCase):
    """The result must satisfy what rd_analysis_worker accepts, or the app
    silently rejects every analysis."""

    def _capture(self, samples, sr=44100, channels=2):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        handle.close()
        data = np.asarray(samples, dtype=np.float32)
        frames = (np.clip(data, -1, 1) * 32767).astype("<i2")
        if channels == 2:
            frames = np.repeat(frames[:, None], 2, axis=1).ravel()
        with wave.open(handle.name, "wb") as out:
            out.setnchannels(channels); out.setsampwidth(2); out.setframerate(sr)
            out.writeframes(frames.tobytes())
        return handle.name

    def test_result_shape_matches_the_worker_contract(self):
        path = self._capture(click_train([0.5, 1.0, 1.5, 2.0], kind="bd"))
        value = dsp.analyse_request(path)
        self.assertEqual(set(value) >= {"bpm", "origin_sample", "detector",
                                        "lane_onset_gates", "candidates"}, True)
        self.assertGreaterEqual(value["bpm"], dsp.BPM_MIN)
        self.assertLessEqual(value["bpm"], dsp.BPM_MAX)
        self.assertIsInstance(value["origin_sample"], int)
        self.assertEqual(set(value["lane_onset_gates"]), set(dsp.LANES))
        for lane, gate in value["lane_onset_gates"].items():
            self.assertTrue(0 <= gate <= 1, lane)
        for candidate in value["candidates"]:
            self.assertIn(candidate["lane"], dsp.LANES)
            self.assertIsInstance(candidate["sample_index"], int)
            self.assertGreaterEqual(candidate["sample_index"], 0)
            self.assertTrue(1 <= candidate["velocity"] <= 127)
            self.assertTrue(0 <= candidate["confidence"] <= 1)
        os.unlink(path)

    def test_detector_identity_pins_the_backend_and_its_templates(self):
        path = self._capture(click_train([0.5, 1.0], kind="bd"))
        d = dsp.analyse_request(path)["detector"]
        self.assertEqual(d["backend_id"], dsp.BACKEND_ID)
        for key in ("backend_sha256", "template_sha256"):
            self.assertRegex(d[key], r"^[0-9a-f]{64}$")
        os.unlink(path)

    def test_silence_yields_an_empty_but_still_valid_result(self):
        path = self._capture(np.zeros(44100))
        value = dsp.analyse_request(path)
        self.assertEqual(value["candidates"], [])
        self.assertFalse(value["tempo_detected"])
        self.assertGreaterEqual(value["bpm"], dsp.BPM_MIN)
        os.unlink(path)

    def test_cli_writes_a_result_and_reports_failure_without_one(self):
        path = self._capture(click_train([0.5, 1.0], kind="bd"))
        req = tempfile.NamedTemporaryFile(suffix=".json", delete=False); req.close()
        res = tempfile.NamedTemporaryFile(suffix=".json", delete=False); res.close()
        Path(req.name).write_text(json.dumps({"wav_path": path}), encoding="utf-8")
        code = subprocess.call([sys.executable, str(ROOT/"tools"/"rhythm_doctor"/"dsp_drum_backend.py"),
                                "--request", req.name, "--result", res.name])
        self.assertEqual(code, 0)
        self.assertIn("candidates", json.loads(Path(res.name).read_text()))
        Path(req.name).write_text(json.dumps({"wav_path": "/nonexistent.wav"}), encoding="utf-8")
        self.assertEqual(subprocess.call([sys.executable,
            str(ROOT/"tools"/"rhythm_doctor"/"dsp_drum_backend.py"),
            "--request", req.name, "--result", res.name]), 2)
        for f in (path, req.name, res.name): os.unlink(f)


class BassLaneTests(unittest.TestCase):
    """BASS reclassifies pitched low-band onsets rather than detecting afresh."""

    @staticmethod
    def _tone(times, hz, seconds=4.0, sr=44100, decay=3.0):
        x = np.zeros(int(seconds*sr), dtype=np.float32)
        for t in times:
            i = int(t*sr); n = int(0.35*sr)
            env = np.exp(-np.linspace(0, decay, n)).astype(np.float32)
            wave_ = np.sin(2*np.pi*hz*np.arange(n)/sr).astype(np.float32)
            seg = (wave_*env)[:max(0, len(x)-i)]
            x[i:i+len(seg)] += seg
        return x/(np.abs(x).max()+1e-9)

    def test_a_sustained_low_tone_is_reported_as_bass(self):
        times = [0.5, 1.0, 1.5, 2.0, 2.5]
        out = dsp.analyse(self._tone(times, 55.0, decay=1.5))
        hit = sum(1 for t in times if any(abs(t-g) <= 0.05 for g in out["BASS"]))
        self.assertGreaterEqual(hit, 3, f"BASS lane found {out['BASS']}")

    def test_bass_and_bass_drum_are_not_exclusive(self):
        """A kick and a bass note land together constantly; forcing a choice
        between the lanes would drop one of them."""
        times = [0.5, 1.0, 1.5, 2.0, 2.5]
        out = dsp.analyse(self._tone(times, 55.0, decay=1.5))
        shared = [b for b in out["BASS"] if any(abs(b-d) <= 1e-9 for d in out["BD"])]
        self.assertTrue(shared, "a pitched low onset must be able to occupy both lanes")

    def test_pitch_confidence_separates_a_tone_from_noise(self):
        sr = 44100
        tone = np.sin(2*np.pi*55*np.arange(int(0.08*sr))/sr).astype(np.float32)
        noise = np.random.default_rng(1).standard_normal(int(0.08*sr)).astype(np.float32)
        self.assertGreater(dsp.pitch_confidence(tone, sr), dsp.PITCH_CONFIDENCE_CUT)
        self.assertLess(dsp.pitch_confidence(noise, sr), dsp.PITCH_CONFIDENCE_CUT)

    def test_silence_and_short_segments_are_not_called_pitched(self):
        self.assertEqual(dsp.pitch_confidence(np.zeros(4000, dtype=np.float32), 44100), 0.0)
        self.assertEqual(dsp.pitch_confidence(np.zeros(4, dtype=np.float32), 44100), 0.0)


class WorkerIntegrationTests(unittest.TestCase):
    """The worker must actually accept this backend's output.

    The two agree only if the lane sets match and the detector identity the
    backend publishes is the one the worker was configured to expect. A
    mismatch here would make every capture fail with ANALYSIS_BACKEND_INVALID
    while both components looked correct in isolation.
    """

    def _wav(self, samples, sr=44100):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); handle.close()
        frames = (np.clip(np.asarray(samples, dtype=np.float32), -1, 1) * 32767).astype("<i2")
        with wave.open(handle.name, "wb") as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(sr)
            out.writeframes(frames.tobytes())
        return handle.name

    def test_backend_lane_set_matches_the_worker(self):
        self.assertEqual(tuple(dsp.LANES), tuple(rd_analysis_worker.LANES))

    def test_worker_accepts_a_real_backend_result(self):
        path = self._wav(click_train([0.5, 1.0, 1.5, 2.0], kind="bd"))
        value = dsp.analyse_request(path)
        detector = value["detector"]
        self.assertTrue(rd_analysis_worker.analysis_is_dsp(
            value, detector["backend_sha256"], detector["template_sha256"]))
        os.unlink(path)

    def test_worker_rejects_a_result_whose_identity_does_not_match(self):
        path = self._wav(click_train([0.5, 1.0], kind="bd"))
        value = dsp.analyse_request(path)
        detector = value["detector"]
        self.assertFalse(rd_analysis_worker.analysis_is_dsp(
            value, "0" * 64, detector["template_sha256"]))
        self.assertFalse(rd_analysis_worker.analysis_is_dsp(
            value, detector["backend_sha256"], "0" * 64))
        os.unlink(path)

    def test_an_unconfigured_worker_accepts_nothing(self):
        path = self._wav(click_train([0.5], kind="bd"))
        self.assertFalse(rd_analysis_worker.analysis_matches_detector(
            dsp.analyse_request(path), {}))
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()

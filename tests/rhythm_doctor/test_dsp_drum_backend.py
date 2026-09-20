"""Regressions for the classical-DSP drum backend.

Characterisation outside README: this backend has no learned model. It uses
the GPL-3 partially-fixed NMF drum dictionary published with Wu & Lerch
(ISMIR 2015) and the peak-picking constants grid-searched by Boeck, Krebs &
Schedl (ISMIR 2012). See tools/rhythm_doctor/data/NMF_TEMPLATES_PROVENANCE.md.
"""
import json
import struct
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
        self.assertEqual(dsp.LANES, ("BD", "SD", "CYM"))
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


class AlignmentTests(unittest.TestCase):
    """A correction the player accepted must survive reanalysis.

    The backend read only wav_path from the request, so the confirmed tempo and
    origin were discarded and the bank came back with the automatic estimate and
    a zero origin - the correction silently undone.
    """

    def _capture(self, samples, sr=44100):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        handle.close()
        frames = (np.clip(np.asarray(samples, dtype=np.float32), -1, 1) * 32767).astype("<i2")
        with wave.open(handle.name, "wb") as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(sr)
            out.writeframes(frames.tobytes())
        return handle.name

    def test_a_confirmed_alignment_overrides_the_automatic_estimate(self):
        path = self._capture(click_train([0.5, 1.0, 1.5, 2.0, 2.5, 3.0], kind="bd"))
        automatic = dsp.analyse_request(path)
        alignment = {"bpm": 77.0, "start_beat": 1, "fine_start_ms": 0.0,
                     "origin_sample": 12345}
        corrected = dsp.analyse_request(path, alignment=alignment)
        self.assertEqual(corrected["bpm"], 77.0,
                         "the confirmed tempo was discarded")
        self.assertEqual(corrected["origin_sample"], 12345,
                         "the confirmed origin was discarded")
        self.assertTrue(corrected["tempo_detected"],
                        "a confirmed tempo is known, not guessed")
        self.assertEqual(corrected.get("tempo_mode"), "manual")
        # Onsets are absolute positions in the capture and must not move.
        self.assertEqual([c["sample_index"] for c in corrected["candidates"]],
                         [c["sample_index"] for c in automatic["candidates"]])
        os.unlink(path)

    def test_an_out_of_range_or_malformed_alignment_is_ignored(self):
        path = self._capture(click_train([0.5, 1.0, 1.5], kind="bd"))
        automatic = dsp.analyse_request(path)
        for bad in ({"bpm": 5.0, "origin_sample": 0}, {"bpm": 9000.0, "origin_sample": 0},
                    {"bpm": "fast", "origin_sample": 0}, {"bpm": 120.0, "origin_sample": -1},
                    {"bpm": float("nan"), "origin_sample": 0}, "not-a-table", None):
            value = dsp.analyse_request(path, alignment=bad)
            self.assertEqual(value["bpm"], automatic["bpm"], repr(bad))
            self.assertEqual(value["origin_sample"], automatic["origin_sample"], repr(bad))
        os.unlink(path)

    def test_the_cli_passes_the_requested_alignment_to_the_detector(self):
        path = self._capture(click_train([0.5, 1.0, 1.5, 2.0], kind="bd"))
        with tempfile.TemporaryDirectory() as folder:
            request = Path(folder) / "request.json"
            result = Path(folder) / "result.json"
            request.write_text(json.dumps({"wav_path": path,
                                           "alignment": {"bpm": 88.0, "start_beat": 1,
                                                         "fine_start_ms": 0.0,
                                                         "origin_sample": 4410}}))
            self.assertEqual(dsp.main(["--request", str(request), "--result", str(result)]), 0)
            value = json.loads(result.read_text())
        self.assertEqual(value["bpm"], 88.0, "the CLI never forwarded the alignment")
        self.assertEqual(value["origin_sample"], 4410)
        os.unlink(path)


class WithdrawnBassLaneTests(unittest.TestCase):
    """BASS was withdrawn in 1.4.0 and must not return by accident.

    The lane never detected bass. It re-scored the low-band onsets BD had
    already found, keeping the ones whose attack held a stable pitch; on real
    captures that test rejected none of them, so BASS reproduced BD exactly
    (48 of 48 onsets identical). A lane that duplicates another lane costs the
    player a grid column and teaches them to distrust the analysis.
    """

    def test_the_backend_does_not_offer_a_bass_lane(self):
        self.assertNotIn("BASS", dsp.LANES)
        self.assertNotIn("BASS", dsp.DEFAULT_DELTA)

    def test_no_analysis_can_emit_a_bass_candidate(self):
        """The withdrawal is in the output, not only in the lane table."""
        sr = 44100
        x = np.zeros(int(4.0*sr), dtype=np.float32)
        for t in (0.5, 1.0, 1.5, 2.0, 2.5):
            i = int(t*sr); n = int(0.35*sr)
            env = np.exp(-np.linspace(0, 1.5, n)).astype(np.float32)
            seg = (np.sin(2*np.pi*55*np.arange(n)/sr).astype(np.float32)*env)[:len(x)-i]
            x[i:i+len(seg)] += seg
        x = x/(np.abs(x).max()+1e-9)
        self.assertNotIn("BASS", dsp.analyse(x))
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); handle.close()
        _riff(handle.name, x, sample_rate=sr)
        try:
            value = dsp.analyse_request(handle.name)
        finally:
            os.unlink(handle.name)
        self.assertNotIn("BASS", value["lane_onset_gates"])
        self.assertEqual([c for c in value["candidates"] if c["lane"] == "BASS"], [])

    def test_the_pitch_test_that_powered_the_lane_is_gone(self):
        """Leaving the helper behind invites a future caller to revive it."""
        self.assertFalse(hasattr(dsp, "pitch_confidence"))
        self.assertFalse(hasattr(dsp, "PITCH_CONFIDENCE_CUT"))


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


def _riff(path, samples, sample_rate=44100, tag=3, bits=32, channels=2):
    """Write a WAV exactly as rd_capture.c does when tag/bits are left default."""
    mono = np.asarray(samples, dtype=np.float32)
    inter = np.repeat(mono[:, None], channels, axis=1).ravel() if channels == 2 else mono
    if tag == 3:
        body = inter.astype("<f4").tobytes()
    else:
        body = (np.clip(inter, -1, 1) * 32767).astype("<i2").tobytes()
    block = channels * bits // 8
    head = (b"RIFF" + struct.pack("<I", 36 + len(body)) + b"WAVEfmt " + struct.pack("<I", 16)
            + struct.pack("<H", tag) + struct.pack("<H", channels) + struct.pack("<I", sample_rate)
            + struct.pack("<I", sample_rate * block) + struct.pack("<H", block)
            + struct.pack("<H", bits) + b"data" + struct.pack("<I", len(body)))
    Path(path).write_bytes(head + body)
    return len(body) // block


class CaptureFormatTests(unittest.TestCase):
    """The native recorder publishes IEEE float, which `wave` refuses.

    Fixtures were 16-bit, so the whole backend passed its tests while being
    unable to read a single real capture. These pin the actual published format.
    """

    def _tmp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); handle.close()
        return handle.name

    def test_reads_the_float32_stereo_format_the_recorder_publishes(self):
        path = self._tmp()
        frames = _riff(path, click_train([0.5, 1.0, 1.5], kind="bd"), tag=3, bits=32)
        mono, rate, count = dsp.read_capture_wav(path)
        self.assertEqual(rate, 44100)
        self.assertEqual(count, frames)
        self.assertTrue(np.isfinite(mono).all())
        self.assertGreater(np.abs(mono).max(), 0.0)
        os.unlink(path)

    def test_a_float32_capture_produces_a_worker_valid_analysis(self):
        path = self._tmp()
        _riff(path, click_train([0.5, 1.0, 1.5, 2.0], kind="bd"), tag=3, bits=32)
        value = dsp.analyse_request(path)
        d = value["detector"]
        self.assertTrue(rd_analysis_worker.analysis_is_dsp(
            value, d["backend_sha256"], d["template_sha256"]))
        os.unlink(path)

    def test_the_worker_accepts_a_float32_capture_asset(self):
        import hashlib
        path = self._tmp()
        frames = _riff(path, click_train([0.5], kind="bd"), tag=3, bits=32)
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        self.assertTrue(rd_analysis_worker.asset_is_exact(
            {"wav_path": path, "wav_sha256": digest, "frames": frames, "sample_rate": 44100}))
        os.unlink(path)

    def test_integer_pcm_still_reads(self):
        path = self._tmp()
        _riff(path, click_train([0.5, 1.0], kind="bd"), tag=1, bits=16)
        mono, rate, _ = dsp.read_capture_wav(path)
        self.assertEqual(rate, 44100)
        self.assertGreater(np.abs(mono).max(), 0.0)
        os.unlink(path)

    def test_an_unsupported_encoding_is_refused_rather_than_misread(self):
        path = self._tmp()
        _riff(path, click_train([0.5], kind="bd"), tag=1, bits=8, channels=1)
        with self.assertRaises(ValueError):
            dsp.read_capture_wav(path)
        os.unlink(path)


class SampleRateTests(unittest.TestCase):
    def test_onsets_land_at_the_same_time_at_44k1_and_48k(self):
        """Frames come from the resampled signal, so timing must use the
        analysis rate. Using the source rate read a 48 kHz capture ~8.8% fast,
        corrupting tempo and quantisation."""
        times = [0.5, 1.0, 1.5, 2.0, 2.5]
        got = {}
        for rate in (44100, 48000):
            handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False); handle.close()
            x = click_train(times, sr=rate, kind="bd")
            _riff(handle.name, x, sample_rate=rate, tag=3, bits=32)
            value = dsp.analyse_request(handle.name)
            got[rate] = sorted(c["sample_index"] / rate for c in value["candidates"]
                               if c["lane"] == "BD")
            os.unlink(handle.name)
        self.assertTrue(got[44100] and got[48000], f"no BD onsets: {got}")
        for a in got[44100]:
            nearest = min(abs(a - b) for b in got[48000])
            self.assertLess(nearest, 0.05, f"44.1k onset {a:.3f}s unmatched at 48k: {got[48000]}")


if __name__ == "__main__":
    unittest.main()

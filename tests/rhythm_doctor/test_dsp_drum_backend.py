"""Regressions for the classical-DSP drum backend.

Characterisation outside README: this backend has no learned model. It uses
the GPL-3 partially-fixed NMF drum dictionary published with Wu & Lerch
(ISMIR 2015) and the peak-picking constants grid-searched by Boeck, Krebs &
Schedl (ISMIR 2012). See tools/rhythm_doctor/data/NMF_TEMPLATES_PROVENANCE.md.
"""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor"))
import dsp_drum_backend as dsp


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
        self.assertEqual(set(dsp.DEFAULT_DELTA), {"BD", "SD", "CYM"})
        out = dsp.analyse(click_train([0.5, 1.0], kind="chh"))
        self.assertEqual(set(out), {"BD", "SD", "CYM"})


class BackendTests(unittest.TestCase):
    def test_digital_silence_paints_nothing_on_every_lane(self):
        out = dsp.analyse(np.zeros(44100 * 2, dtype=np.float32))
        self.assertEqual(set(out), {"BD", "SD", "CYM"})
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


if __name__ == "__main__":
    unittest.main()

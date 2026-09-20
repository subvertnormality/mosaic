"""Onset and velocity extraction for the remote analysis server.

These run on synthetic stems, which is the honest scope: the separator's job is
to hand this module an isolated instrument, so testing it against a full mix
would be testing the separator instead.
"""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "rhythm_doctor_server"))
import onsets
import lanes


SR = 44100


def hits(times, amplitudes=None, freq=80.0, noise=0.0, seconds=3.0, sr=SR, decay=10.0):
    """A stem: decaying strikes at known times with known relative force."""
    x = np.zeros(int(seconds * sr), dtype=np.float32)
    rng = np.random.default_rng(0)
    amplitudes = amplitudes or [1.0] * len(times)
    span = int(0.1 * sr)
    env = np.exp(-np.linspace(0, decay, span)).astype(np.float32)
    for time, amplitude in zip(times, amplitudes):
        tone = np.sin(2 * np.pi * freq * np.arange(span) / sr).astype(np.float32)
        if noise:
            tone = tone * (1 - noise) + rng.standard_normal(span).astype(np.float32) * noise
        start = int(time * sr)
        seg = (tone * env * amplitude)[:max(0, len(x) - start)]
        x[start:start + len(seg)] += seg
    return x


class OnsetPositionTests(unittest.TestCase):
    TIMES = [0.5, 1.0, 1.5, 2.0]

    def _errors_ms(self, stem, delta=0.3):
        found = onsets.analyse_stem(stem, SR, delta)
        self.assertEqual(len(found), len(self.TIMES), "wrong number of onsets")
        return [(c["sample_index"] / SR - t) * 1000 for c, t in zip(found, self.TIMES)]

    def test_a_low_pitched_stem_lands_on_its_attacks(self):
        """A kick's rectified waveform swings 160 times a second. Refining the
        onset by differencing that directly finds a carrier peak rather than
        the attack, which moves onsets by a random part of a cycle."""
        for error in self._errors_ms(hits(self.TIMES, freq=80.0)):
            self.assertLess(abs(error), 5.0, "kick onset off by %.1fms" % error)

    def test_a_broadband_stem_lands_on_its_attacks(self):
        for error in self._errors_ms(hits(self.TIMES, freq=6000.0, noise=0.5)):
            self.assertLess(abs(error), 5.0, "hat onset off by %.1fms" % error)

    def test_onsets_are_not_reported_systematically_early(self):
        """An analysis frame sees an attack before its centre reaches it, so a
        raw flux peak sits about one hop early. The beat grid comes from a
        different model, so a constant offset between the two is visible as
        every gate sitting ahead of the beat."""
        errors = self._errors_ms(hits(self.TIMES, freq=200.0, noise=0.3))
        mean = sum(errors) / len(errors)
        self.assertLess(abs(mean), 3.0, "mean onset bias %.1fms" % mean)

    def test_refinement_never_invents_an_onset_in_silence(self):
        quiet = np.zeros(int(1.0 * SR), dtype=np.float32)
        self.assertEqual(onsets.refine(quiet, 10000), 10000)

    def test_silence_and_short_stems_produce_nothing(self):
        self.assertEqual(onsets.analyse_stem(np.zeros(SR, dtype=np.float32), SR, 0.3), [])
        self.assertEqual(onsets.analyse_stem(np.zeros(16, dtype=np.float32), SR, 0.3), [])


class VelocityTests(unittest.TestCase):
    def test_velocity_follows_how_hard_the_stem_was_struck(self):
        amplitudes = [1.0, 0.5, 0.8, 0.25]
        found = onsets.analyse_stem(hits([0.5, 1.0, 1.5, 2.0], amplitudes), SR, 0.3)
        got = [c["velocity"] for c in found]
        self.assertEqual(len(got), len(amplitudes))
        # Rank agreement, not exact values: the claim is that a harder strike
        # reports a higher velocity, for every pair of strikes.
        for i in range(len(amplitudes)):
            for j in range(len(amplitudes)):
                if amplitudes[i] > amplitudes[j]:
                    self.assertGreater(got[i], got[j],
                                       "%s does not rank like %s" % (got, amplitudes))
        self.assertEqual(max(got), 127, "the hardest strike in a stem is full scale")

    def test_velocity_is_scaled_within_the_stem_not_across_stems(self):
        """A guitar stem's absolute level says nothing about how hard the
        guitar was played relative to the kick. Scaling globally would make
        every quiet stem produce uniformly weak gates."""
        loud = onsets.analyse_stem(hits([0.5, 1.0], [1.0, 0.5]), SR, 0.3)
        quiet = onsets.analyse_stem(hits([0.5, 1.0], [0.01, 0.005]), SR, 0.3)
        self.assertEqual([c["velocity"] for c in loud], [c["velocity"] for c in quiet],
                         "the same performance 40dB down must produce the same velocities")

    def test_every_velocity_satisfies_the_bank_contract(self):
        for candidate in onsets.analyse_stem(hits([0.5, 1.0, 1.5], [1.0, 0.02, 0.5]), SR, 0.3):
            self.assertTrue(1 <= candidate["velocity"] <= 127)
            self.assertEqual(int(candidate["velocity"]), candidate["velocity"])
            self.assertTrue(0 <= candidate["confidence"] <= 1)
            self.assertGreaterEqual(candidate["sample_index"], 0)


class LaneTableTests(unittest.TestCase):
    def test_the_server_offers_more_lanes_than_the_local_backend(self):
        self.assertGreater(len(lanes.LANES), 3)
        self.assertEqual(len(set(lanes.LANES)), len(lanes.LANES), "lane names must be unique")

    def test_every_lane_has_a_gate_and_every_melodic_lane_has_a_stem(self):
        # Every lane the server can emit, split or unsplit. DRUMS only appears
        # when LarsNet is absent, and still needs a gate.
        self.assertEqual(set(lanes.DEFAULT_GATE), set(lanes.ALL_LANES))
        self.assertEqual(set(lanes.STEM_FOR_LANE), set(lanes.MELODIC_LANES))
        for stem in lanes.STEM_FOR_LANE.values():
            self.assertIn(stem, lanes.DEMUCS_STEMS)

    def test_the_lane_set_degrades_without_the_drum_splitter(self):
        """LarsNet's checkpoints are CC BY-NC 4.0 and a separate 562MB
        download, so a server legitimately runs without them. One drums lane
        beside five melodic ones is still twice what the device produces, and
        refusing to start would let the licence decide whether the feature
        exists at all."""
        split = lanes.lane_set(True)
        whole = lanes.lane_set(False)
        self.assertEqual(len(split), 10)
        self.assertEqual(len(whole), 6)
        self.assertIn("DRUMS", whole)
        self.assertNotIn("DRUMS", split)
        self.assertNotIn("KICK", whole)
        for names in (split, whole):
            self.assertEqual(set(lanes.gates_for(names)), set(names))
            self.assertGreater(len(names), 3, "the point is more lanes than the device")


if __name__ == "__main__":
    unittest.main()

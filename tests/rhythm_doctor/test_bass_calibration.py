import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parents[2] / "tools" / "rhythm_doctor_analysis"))
import bass_calibration


class BassCalibration(unittest.TestCase):
    def test_low_frequency_gate_reads_the_current_detector_feature_block(self):
        row = np.zeros((1, 198), dtype=float)
        base = row[:, 66:132]
        low = bass_calibration.LOW_BAND_INDICES[:3]
        non_low = next(i for i in range(32) if i not in bass_calibration.LOW_BAND_INDICES)
        mid = bass_calibration.MID_BAND_INDICES[0]
        base[0, 2 * low] = np.log1p([10.0, 5.0, 3.0])
        base[0, 2 * mid] = np.log1p(4.0)
        base[0, 2 * low + 1] = [4.0, 2.0, 1.0]
        base[0, 2 * non_low + 1] = 3.0
        low_delta, low_to_mid = bass_calibration.low_frequency_gate(row)
        self.assertAlmostEqual(low_delta[0], 7 / 10)
        self.assertGreater(low_to_mid[0], 1.0)

    def test_gate_requires_both_calibrated_low_frequency_signals(self):
        probability = np.array([.9, .9, .9])
        low_delta = np.array([.7, .3, .7])
        low_to_mid = np.array([1.2, 1.2, .6])
        kept = bass_calibration.apply_gate(probability, low_delta, low_to_mid, .5, 1.)
        self.assertEqual(kept.tolist(), [.9, 0., 0.])

    def test_soft_fusion_does_not_raise_rf_probability(self):
        probability = np.array([.8])
        fused = bass_calibration.fuse_probability(
            probability, np.array([.35]), np.array([.65]), .6, .7, 1.3
        )
        self.assertGreater(fused[0], 0.0)
        self.assertLessEqual(fused[0], probability[0])


if __name__ == "__main__":
    unittest.main()

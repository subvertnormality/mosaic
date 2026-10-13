import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parents[2] / 'tools' / 'rhythm_doctor_analysis'))
import bass_harmonic_rf as candidate

class BassHarmonicFeatures(unittest.TestCase):
 def test_phase_safe_mono_keeps_non_cancelled_stereo_and_uses_strongest_on_cancel(self):
  signal=np.array([.2,-.4,.6],dtype=np.float32)
  self.assertTrue(np.allclose(candidate.phase_safe_mono(np.c_[signal,signal]),signal))
  self.assertTrue(np.allclose(candidate.phase_safe_mono(np.c_[signal,-signal]),signal))
 def test_feature_matrix_has_one_bounded_row_per_analysis_time(self):
  audio=np.random.default_rng(4).normal(size=(16000,2)).astype(np.float32)
  times,features=candidate.feature_matrix(audio,16000)
  self.assertEqual(features.shape[0],len(times))
  self.assertEqual(features.ndim,2)
  self.assertGreater(features.shape[1],20)
  self.assertTrue(np.isfinite(features).all())
 def test_bass_feature_frame_size_stays_bounded(self):
  self.assertEqual(candidate.FFT_SIZE,2048)
  self.assertLessEqual(candidate.FFT_SIZE,4096)

if __name__ == '__main__': unittest.main()

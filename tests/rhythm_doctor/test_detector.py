import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / 'tools' / 'rhythm_doctor_analysis'))
import detector
class Detector(unittest.TestCase):
 def test_peak_picker_collapses_dense_frames(self):
  self.assertEqual(detector.peak_times([.1,.8,.7,.2],[0,.02,.04,.06],.5),[.02])
 def test_fixed_source_manifest_is_disjoint(self): self.assertFalse(set(detector.DEV) & set(detector.HELD))
 def test_phase_inversion_keeps_magnitude_features(self):
  import numpy as np
  signal=np.random.default_rng(2).normal(size=(3000,1)); stereo=np.c_[signal,-signal]
  self.assertTrue(np.allclose(detector.features(signal,16000,[.1]),detector.features(stereo,16000,[.1])))

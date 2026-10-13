import unittest
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[2]/'tools'/'rhythm_doctor_analysis'))
from audio_frontend import phase_safe_mono
class TestPhaseSafeMono(unittest.TestCase):
 def test_ordinary_stereo_averages(self):
  x=np.array([[1.,3.],[2.,4.]])
  np.testing.assert_allclose(phase_safe_mono(x),[2.,3.])
 def test_opposite_phase_uses_strongest_channel(self):
  x=np.array([[1.,-1.],[.5,-.5]])
  np.testing.assert_allclose(phase_safe_mono(x),x[:,0])
 def test_mono_preserved(self):
  x=np.array([1.,-2.]);np.testing.assert_allclose(phase_safe_mono(x),x)
if __name__=='__main__':unittest.main()

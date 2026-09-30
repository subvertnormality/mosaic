import unittest
from acquisition_quality import evaluate
def fixture(**overrides):
 d={"id":"ok","eligible":True,"control":"steady","reference_bpm":120,"reference_beats":[i*.5 for i in range(20)],"reference_downbeat":0,"captured_duration":20,"predicted_bpm":120,"predicted_origin":0,"predicted_region":[0,8],"status":"accepted","predicted_bar_start":0,"timeout_seconds":20};d.update(overrides);return d
class AcquisitionTests(unittest.TestCase):
 def test_boundary_and_gate(self):
  r=evaluate([fixture(id=str(i))for i in range(9)]+[fixture(id="bad",predicted_bpm=123)]);self.assertEqual((r["passed"],r["octave_errors"]),(9,0));self.assertTrue(r["gate_pass"])
 def test_octave_short_phase_and_uncertain_controls(self):
  r=evaluate([fixture(predicted_bpm=240),fixture(id="short",predicted_region=[0,7.5]),fixture(id="phase",predicted_bpm=121,predicted_region=[0,8]),fixture(id="ambiguous",control="ambiguous",eligible=False,status="uncertain")]);self.assertEqual(r["octave_errors"],1);self.assertEqual(r["passed"],0)
 def test_ambiguous_requires_assumed_label(self):
  self.assertTrue(evaluate([fixture(id="ambiguous",control="ambiguous",eligible=False,status="uncertain",predicted_bar_start="START ASSUMED"),fixture()])["results"][0]["ok"])
 def test_unknown_bar_requires_assumed_label(self):
  self.assertTrue(evaluate([fixture(reference_downbeat=None,predicted_bar_start='START ASSUMED')])['gate_pass'])
  self.assertFalse(evaluate([fixture(reference_downbeat=None,predicted_bar_start=0)])['gate_pass'])
 def test_entire_retained_span_phase_is_checked(self):
  self.assertFalse(evaluate([fixture(predicted_bpm=120.5,predicted_region=[0,19],reference_beats=[i*.5 for i in range(41)])])['gate_pass'])
 def test_controls_are_unconditional_gate(self):
  self.assertFalse(evaluate([fixture(),fixture(id='amb',eligible=False,control='ambiguous',status='accepted')])['gate_pass'])
 def test_zero_and_negative_values_rejected(self):
  for changes in ({'reference_bpm':0},{'predicted_bpm':0},{'captured_duration':-1},{'timeout_seconds':-1}):
   with self.subTest(changes=changes),self.assertRaises(ValueError):evaluate([fixture(**changes)])
 def test_duplicate_and_nonfinite_control_rejected(self):
  with self.assertRaises(ValueError):evaluate([fixture(),fixture()])
  with self.assertRaises(ValueError):evaluate([fixture(),fixture(id='amb',eligible=False,control='ambiguous',status='uncertain',predicted_origin=float('nan'))])
 def test_region_must_be_captured_before_decision(self):
  self.assertFalse(evaluate([fixture(timeout_seconds=7.9)])['gate_pass'])
  self.assertFalse(evaluate([fixture(predicted_region=[1,9])])['gate_pass'])
 def test_malformed_and_no_eligible_rejected(self):
  with self.assertRaises(ValueError):evaluate([])
  with self.assertRaises(ValueError):evaluate([fixture(reference_beats=[0]*16)])
  with self.assertRaises(ValueError):evaluate([fixture(id="silent",control="silent",status="uncertain",reference_beats=[],reference_bpm=None,reference_downbeat=None,predicted_bpm=None,predicted_origin=None,predicted_region=None,predicted_bar_start=None)])
if __name__=="__main__":unittest.main()

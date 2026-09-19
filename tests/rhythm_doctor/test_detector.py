import sys, unittest, tempfile
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
 def test_literal_metadata_missing_midi_marks_declared_lanes_unknown(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary); track=root/'selected'/'Track00017'; meta=root/'meta'/'Track00017'
   (track/'MIDI').mkdir(parents=True); meta.mkdir(parents=True)
   (meta/'metadata.yaml').write_text('stems:\n  S01:\n    inst_class: Bass\n  S04:\n    inst_class: Bass\n  S07:\n    is_drum: true\n',encoding='utf-8')
   # S01 is present, but declared Bass S04 and Drum S07 MIDI are absent.
   import mido
   mido.MidiFile().save(track/'MIDI'/'S01.mid')
   found=detector.labels(track,root/'meta',0,1)
   self.assertIsNone(found['BASS'])
   for lane in ('BD','SD','HH','TOM'): self.assertIsNone(found[lane])
 def test_subsample_keeps_all_positive_rows_when_positive_count_exceeds_cap(self):
  import numpy as np
  features=np.arange(20).reshape(10,2); labels=np.array([True]*7+[False]*3)
  kept_features,kept_labels=detector.balanced_training_rows(features,labels,max_rows=5,rng=np.random.default_rng(1))
  self.assertEqual(kept_features.tolist(),features[:7].tolist())
  self.assertEqual(kept_labels.tolist(),[True]*7)
 def test_single_class_probability_uses_the_observed_positive_class(self):
  import numpy as np
  class OneClass:
   classes_=np.array([True])
   def predict_proba(self, matrix): return np.ones((len(matrix),1))
  self.assertEqual(detector.classifier_probabilities(OneClass(),np.zeros((3,2))).tolist(),[1.,1.,1.])
 def test_single_negative_class_probability_is_zero(self):
  import numpy as np
  class OneClass:
   classes_=np.array([False])
   def predict_proba(self, matrix): return np.ones((len(matrix),1))
  self.assertEqual(detector.classifier_probabilities(OneClass(),np.zeros((2,2))).tolist(),[0.,0.])
 def test_onset_frame_targets_marks_only_nearest_frames(self):
  import numpy as np
  targets=detector.onset_frame_targets(np.array([.10,.12,.14,.16]),[.101,.139],.05)
  self.assertEqual(targets.tolist(),[True,False,True,False])
 def test_onset_frame_targets_is_linear_sized_for_dense_reference_lists(self):
  import numpy as np
  times=np.arange(0.,120.,.02); references=np.arange(.001,120.,.02)
  targets=detector.onset_frame_targets(times,references,.05)
  self.assertEqual(targets.shape,(len(times),))
  self.assertEqual(int(targets.sum()),len(times))
 def test_probability_selects_the_explicit_positive_class_column(self):
  import numpy as np
  class TwoClass:
   classes_=np.array([True,False])
   def predict_proba(self, matrix): return np.array([[.8,.2],[.7,.3]])
  self.assertEqual(detector.classifier_probabilities(TwoClass(),np.zeros((2,2))).tolist(),[.8,.7])
 def test_no_declared_bass_is_a_known_empty_negative(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary); track=root/'selected'/'Track00001'; meta=root/'meta'/'Track00001'
   (track/'MIDI').mkdir(parents=True); meta.mkdir(parents=True)
   (meta/'metadata.yaml').write_text('stems:\n  S01:\n    inst_class: Piano\n',encoding='utf-8')
   self.assertEqual(detector.labels(track,root/'meta',0,1)['BASS'],[])

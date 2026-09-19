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
 def test_no_declared_bass_is_a_known_empty_negative(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary); track=root/'selected'/'Track00001'; meta=root/'meta'/'Track00001'
   (track/'MIDI').mkdir(parents=True); meta.mkdir(parents=True)
   (meta/'metadata.yaml').write_text('stems:\n  S01:\n    inst_class: Piano\n',encoding='utf-8')
   self.assertEqual(detector.labels(track,root/'meta',0,1)['BASS'],[])

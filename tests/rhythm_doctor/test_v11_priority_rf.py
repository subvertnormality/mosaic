import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2] / 'tools' / 'rhythm_doctor_analysis'))
import v11_priority_rf as candidate

class SplitTests(unittest.TestCase):
 def test_fixed_validation_partition_excludes_held_and_is_kit_disjoint(self):
  clips=[
   {'id':'d0','split':'development','kit_id':'pop_kit.nkm'},
   {'id':'d1','split':'development','kit_id':'ar_modern_white_kit_full.nkm'},
   {'id':'h0','split':'held_out','kit_id':'hydrogen-gmrock'},
  ]
  train, validation=candidate.partition_development(clips)
  self.assertEqual([c['id'] for c in train],['d0'])
  self.assertEqual([c['id'] for c in validation],['d1'])
  self.assertFalse({c['kit_id'] for c in train}&{c['kit_id'] for c in validation})

 def test_nearest_frame_targets_do_not_widen_one_onset_to_three_frames(self):
  labels=candidate.nearest_frame_labels([.10,.12,.14],[.121])
  self.assertEqual(labels.tolist(),[False,True,False])

if __name__=='__main__': unittest.main()

# Characterisation outside README: independent PLAN sample-authoritative oracle.
import unittest
from grid_quality import grid_score

class GridQuality(unittest.TestCase):
    def test_collision(self):
        self.assertEqual(grid_score([0,.01],[0],48000,120)['tp'],1)
    def test_end_excluded(self):
        self.assertEqual(grid_score([8],[8],48000,120)['tp'],0)
    def test_quantize_sample_before_region_filter(self):
        self.assertEqual(grid_score([0],[-0.00001],16000,120)['tp'],1)
        self.assertEqual(grid_score([7.99999],[],16000,120)['fn'],0)
    def test_cell_ties_go_later(self):
        self.assertEqual(grid_score([.0625],[.125],16000,120)['tp'],1)
    def test_origin_and_partial_tail(self):
        self.assertEqual(grid_score([0,.125,8.124,8.126],[.125,8.124],16000,120,origin=.125,end=8.2)['tp'],2)
        self.assertEqual(grid_score([8.126],[],16000,120,origin=.125,end=8.2)['fn'],0)
    def test_final_event_clamps(self):
        self.assertEqual(grid_score([7.999],[7.875],16000,120)['tp'],1)
    def test_invalid_values_fail_closed(self):
        for bad in (float('nan'),float('inf'),'1',True):
            with self.assertRaises(ValueError): grid_score([bad],[],16000,120)
        for kwargs in ({'bpm':0},{'bpm':241},{'sr':0},{'origin':9},{'end':float('nan')}):
            args=dict(sr=16000,bpm=120);args.update(kwargs)
            with self.assertRaises(ValueError): grid_score([],[],**args)
if __name__=='__main__':unittest.main()

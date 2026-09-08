import unittest
from note_accounting import note_pairs
def event(index,kind=144,pitch=60,velocity=100,port=1):return dict(index=index,port=port,bytes=[kind,pitch,velocity])
class AccountingTests(unittest.TestCase):
    def test_valid_retrigger(self):self.assertEqual(len(note_pairs([event(1),event(2,128),event(3),event(4,128,velocity=0)])),2)
    def test_velocity_zero(self):self.assertEqual(len(note_pairs([event(1),event(2,velocity=0)])),1)
    def test_extra_release(self):
        with self.assertRaises(AssertionError):note_pairs([event(1),event(2,128),event(3),event(4,128),event(5,128)])
    def test_missing_release(self):
        with self.assertRaises(AssertionError):note_pairs([event(1)])
    def test_overlap(self):
        with self.assertRaises(AssertionError):note_pairs([event(1),event(2),event(3,128)])
    def test_wrong_port(self):
        with self.assertRaises(AssertionError):note_pairs([event(1),event(2,128,port=2)])
    def test_wrong_channel(self):
        with self.assertRaises(AssertionError):note_pairs([event(1),event(2,129)])
    def test_reordered(self):
        with self.assertRaises(AssertionError):note_pairs([event(2),event(1,128)])
if __name__=='__main__':unittest.main()

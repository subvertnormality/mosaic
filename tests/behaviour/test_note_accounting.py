import unittest
from types import SimpleNamespace
from note_accounting import continuation_onsets, note_pairs, window_onsets
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
def onset(index,seconds,pitch=60,velocity=100):return dict(index=index,port=1,bytes=[144,pitch,velocity],monotonic_ns=round(seconds*1e9))
class ContinuationTests(unittest.TestCase):
    expected=[(1,[144,60,100]),(1,[144,62,90])]
    def setUp(self):
        self.notes=[onset(i+1,i/6,*self.expected[i%2][1][1:]) for i in range(5)]
    def late(self,seconds=5/6,pitch=62,velocity=90):return onset(6,seconds,pitch,velocity)
    def check(self,mode,onsets):
        return continuation_onsets(SimpleNamespace(clock_mode=mode),self.notes,onsets,self.expected,lambda i:i/6)
    def test_exact_window_needs_no_continuation(self):
        for mode in ('real-time','controlled-experimental'):self.assertEqual(self.check(mode,self.notes),[])
    def test_real_time_accepts_exact_continuation(self):
        self.assertEqual(self.check('real-time',self.notes+[self.late(5/6+.009)]),[self.late(5/6+.009)])
    def test_controlled_admits_no_continuation(self):
        with self.assertRaises(AssertionError):self.check('controlled-experimental',self.notes+[self.late()])
    def test_continuation_must_keep_the_cyclic_pattern(self):
        with self.assertRaises(AssertionError):self.check('real-time',self.notes+[self.late(pitch=60)])
        with self.assertRaises(AssertionError):self.check('real-time',self.notes+[self.late(velocity=100)])
    def test_continuation_must_keep_its_scheduled_time(self):
        with self.assertRaises(AssertionError):self.check('real-time',self.notes+[self.late(5/6+.011)])
    def test_played_notes_must_be_the_exact_prefix(self):
        with self.assertRaises(AssertionError):self.check('real-time',self.notes[1:]+[self.late()])
        with self.assertRaises(AssertionError):self.check('real-time',self.notes[:-1])
    def test_window_onsets_match_playback_selection(self):
        events=[event(1),event(2,128),event(3,velocity=0),event(4,145)]
        self.assertEqual([m['index'] for m in window_onsets(events)],[1,4])
if __name__=='__main__':unittest.main()

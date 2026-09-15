import unittest
from midi_window import MidiWindow

def state(indexes,count=None,tail_start=None):
    count=max(indexes,default=0) if count is None else count
    return dict(midi_count=count,midi_capture=dict(count=count,dropped=0,tail_start=min(indexes,default=1) if tail_start is None else tail_start),midi=[dict(index=n,port=n%2+1,bytes=[144,60,n%127+1],logical_ns=n*100) for n in indexes])

class MidiWindowTest(unittest.TestCase):
    def test_overlap_and_tail_rotation_preserve_original_order(self):
        window=MidiWindow(2);window.extend(state([1,2,3,4]));window.extend(state([3,4,5,6]));window.extend(state([3,4,5,6]))
        self.assertEqual([e['index'] for e in window.note_ons()],[3,4,5,6])
        self.assertEqual([e['logical_ns'] for e in window.events],[300,400,500,600])
    def test_retention_gap_fails(self):
        with self.assertRaisesRegex(AssertionError,'retention gap'):MidiWindow(1).extend(state([3,4]))
    def test_interior_gap_fails(self):
        with self.assertRaisesRegex(AssertionError,'missing or unordered'):MidiWindow(0).extend(state([1,3]))
    def test_wrong_order_fails(self):
        with self.assertRaisesRegex(AssertionError,'missing or unordered'):MidiWindow(0).extend(state([2,1]))
    def test_backwards_count_fails(self):
        with self.assertRaisesRegex(AssertionError,'regressed'):MidiWindow(4).extend(state([1,2]))
    def test_count_disagreement_fails(self):
        value=state([1]);value['midi_capture']['count']=2
        with self.assertRaisesRegex(AssertionError,'disagrees'):MidiWindow(0).extend(value)
    def test_dropped_event_report_fails(self):
        value=state([1]);value['midi_capture']['dropped']=1
        with self.assertRaisesRegex(AssertionError,'dropped'):MidiWindow(0).extend(value)

if __name__=='__main__':unittest.main()

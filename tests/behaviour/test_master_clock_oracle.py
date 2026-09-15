"""Independent receiver rejects the observed failure modes without native boot."""
import copy
import unittest
from master_clock import assert_master_receiver

def sequence():
    result=[dict(port=1,bytes=[250],logical_ns=0)]
    for tick in range(44):
        at=round(1e9*(.01+tick/36))
        result.append(dict(port=1,bytes=[248],logical_ns=at))
        if tick%6==0:
            i=tick//6
            result.append(dict(port=1,bytes=[144,(60,62,64,65)[i%4],(127,117,107,97)[i%4]],logical_ns=at))
    result.append(dict(port=1,bytes=[252],logical_ns=1_220_000_000))
    return result

class MasterReceiverTests(unittest.TestCase):
    def check(self,events):
        return assert_master_receiver(events,'logical_ns',2e-9)
    def test_independent_valid_clock(self):
        self.assertEqual(self.check(sequence())['notes'],8)
    def test_note_before_start(self):
        events=sequence();note=events.pop(2);events.insert(0,note)
        with self.assertRaisesRegex(AssertionError,'before Start'):self.check(events)
    def test_first_note_after_second_clock(self):
        events=sequence();note=events.pop(2);events.insert(3,note)
        with self.assertRaisesRegex(AssertionError,'step/clock mismatch'):self.check(events)
    def test_note_phase_cannot_rebase(self):
        events=sequence()
        for e in events:
            if e['bytes'][0]==144:e['logical_ns']+=1_000_000
        with self.assertRaisesRegex(AssertionError,'absolute note phase'):self.check(events)
    def test_clock_drift(self):
        events=sequence()
        for e in events:
            if e['bytes']==[248]:e['logical_ns']+=round(e['logical_ns']*.001)
        with self.assertRaises(AssertionError):self.check(events)
    def test_other_port_does_not_supply_missing_clock(self):
        events=sequence();events[1]['port']=2
        with self.assertRaisesRegex(AssertionError,'step/clock mismatch'):self.check(events)
    def test_duplicate_start_does_not_pass(self):
        events=sequence();events.insert(1,copy.deepcopy(events[0]))
        with self.assertRaises(AssertionError):self.check(events)

if __name__=='__main__':unittest.main()

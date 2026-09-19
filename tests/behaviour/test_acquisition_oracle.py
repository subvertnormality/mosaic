import unittest
from fast_acquisition import assert_acquisition_release_order

class AcquisitionOrderTests(unittest.TestCase):
    def test_release_then_onset_at_same_deadline(self):
        assert_acquisition_release_order([dict(port=1,bytes=[128,60,127],index=1,logical_ns=125000000),dict(port=1,bytes=[144,62,117],index=2,logical_ns=125000000)])

    def test_swapped_equal_deadline_events_fail(self):
        with self.assertRaisesRegex(AssertionError,'preceded'):
            assert_acquisition_release_order([dict(port=1,bytes=[144,62,117],index=1,logical_ns=125000000),dict(port=1,bytes=[128,60,127],index=2,logical_ns=125000000)])

    def test_other_port_release_cannot_satisfy_transition(self):
        with self.assertRaisesRegex(AssertionError,'Missing'):
            assert_acquisition_release_order([dict(port=2,bytes=[128,60,127],index=1),dict(port=1,bytes=[144,62,117],index=2)])

if __name__=='__main__':unittest.main()

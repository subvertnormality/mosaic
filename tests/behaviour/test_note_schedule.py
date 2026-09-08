import unittest
from note_schedule import assert_schedule
def event(i,t,kind=144,pitch=60,velocity=100):return dict(index=i,logical_ns=round(t*1e9),port=1,bytes=[kind,pitch,velocity])
def check(events,onsets=[(0,60,100)],durations=[1],bounds=(2000000000,2100000000)):
    return assert_schedule(events,onsets,durations,field='logical_ns',origin=0,stop_bounds=bounds,pulse_rate=1)
class ScheduleTests(unittest.TestCase):
    def test_regular(self):self.assertEqual(len(check([event(1,0),event(2,1,128)])),1)
    def test_overlap(self):
        rows=check([event(1,0),event(2,.5,velocity=101),event(3,1,128),event(4,1.5,128,velocity=101)],[(0,60,100),(.5,60,101)],[1,1]);self.assertEqual(len(rows),2)
    def test_stop_truncation(self):self.assertTrue(check([event(1,0),event(2,2.05,128,velocity=0)],durations=[10])[0]['truncated'])
    def test_early_release(self):
        with self.assertRaises(AssertionError):check([event(1,0),event(2,.99,128)])
    def test_late_release(self):
        with self.assertRaises(AssertionError):check([event(1,0),event(2,1.01,128)])
    def test_extra_release(self):
        with self.assertRaises(AssertionError):check([event(1,0),event(2,1,128),event(3,1.1,128)])
    def test_missing_release(self):
        with self.assertRaises(AssertionError):check([event(1,0)])
    def test_late_order(self):
        with self.assertRaises(AssertionError):check([event(1,0),event(2,1),event(3,1,128),event(4,2,128)],[(0,60,100),(1,60,100)],[1,1])
    def test_wrong_channel(self):
        with self.assertRaises(AssertionError):check([event(1,0,145),event(2,1,129)])
    def test_bad_stop(self):
        with self.assertRaises(AssertionError):check([event(1,0),event(2,1.9,128,velocity=0)],durations=[10])
    def test_regular_deadline_after_stop(self):
        with self.assertRaises(AssertionError):check([event(1,0),event(2,3,128)],durations=[3])
if __name__=='__main__':unittest.main()

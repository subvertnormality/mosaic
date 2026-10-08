"""Deterministic receipt-latency regression for M-EDIT-005 hold bounds."""
import unittest
from unittest.mock import patch

from contract.hold_input_bounds import assert_hold_input_boundary, hold_input_bounds_sample, hold_sample_durations


class FakePublicUI:
    """Model public edge calls with the measured host-call envelope and input times."""
    def __init__(self, driver):
        self.driver=driver
        self.edges=[]
    def control_edge(self, control, down):
        d=self.driver
        if down:
            self.edges.append((control,True,d.now_ns))
            d.now_ns += d.press_call_ns
        else:
            self.edges.append((control,False,d.now_ns+d.release_event_offset_ns))
            d.now_ns += d.release_call_ns
    def control_cell(self, control):
        return (14,8)
    def tap_control(self, *args):
        raise AssertionError('non-interrupted hold must not tap another control')


class FakePublicDriver:
    def __init__(self, mode='real-time', press_call_ns=25_000_000,
                 release_call_ns=26_289_198, release_event_offset_ns=969_870,
                 sleep_overshoot_ns=982_538):
        self.clock_mode=mode
        self.now_ns=0
        self.logical_ns=0
        self.press_call_ns=press_call_ns
        self.release_call_ns=release_call_ns
        self.release_event_offset_ns=release_event_offset_ns
        self.sleep_overshoot_ns=sleep_overshoot_ns
        self.ui=FakePublicUI(self)
        self.observations=[];self.results=[]
    def now(self):
        return self.now_ns
    def elapse(self, seconds):
        elapsed=round(seconds*1e9)
        if self.clock_mode=='real-time' and seconds>=.5:
            elapsed += self.sleep_overshoot_ns
        self.now_ns += elapsed
        if self.clock_mode=='controlled-experimental':
            self.logical_ns += round(seconds*1e9)


class HoldInputBoundsRegression(unittest.TestCase):
    def measure(self, driver, seconds, expected_long):
        with patch('time.monotonic_ns',driver.now):
            return hold_input_bounds_sample(driver,'pattern_note_octave_up',seconds,expected_long)

    def test_observed_real_time_call_envelope_stays_inside_short_boundary(self):
        before,after=hold_sample_durations('real-time')
        self.assertEqual((before,after),(.90,1.05))
        driver=FakePublicDriver()
        sample=self.measure(driver,before,False)
        assert_hold_input_boundary(driver.clock_mode,sample)
        self.assertAlmostEqual(sample['wall_lower_seconds'],.900982538,places=9)
        self.assertAlmostEqual(sample['wall_upper_seconds'],.952271736,places=9)
        press,release=driver.ui.edges
        self.assertAlmostEqual((release[2]-press[2])/1e9,.926952408,places=9)
        self.assertLess(sample['wall_upper_seconds'],1.0)

    def test_genuinely_over_one_second_is_still_rejected_as_a_short_hold(self):
        driver=FakePublicDriver()
        sample=self.measure(driver,1.05,False)
        driver.observations.append(dict(sample))
        driver.results.append(dict(sample))
        with self.assertRaisesRegex(AssertionError,'one-second hold boundary'):
            assert_hold_input_boundary(driver.clock_mode,sample)
        self.assertEqual(driver.observations[0],sample)
        self.assertEqual(driver.results[0],sample)
        press,release=driver.ui.edges
        self.assertGreater((release[2]-press[2])/1e9,1.0)

    def test_long_hold_still_requires_and_proves_lower_bound_over_one_second(self):
        driver=FakePublicDriver();sample=self.measure(driver,1.05,True)
        assert_hold_input_boundary(driver.clock_mode,sample)
        self.assertGreater(sample['wall_lower_seconds'],1.0)

    def test_controlled_lane_keeps_exact_adjacent_thresholds(self):
        before,after=hold_sample_durations('controlled-experimental')
        self.assertEqual((before,after),(.999999999,1.000000001))
        first_driver=FakePublicDriver('controlled-experimental');second_driver=FakePublicDriver('controlled-experimental')
        first=self.measure(first_driver,before,False);second=self.measure(second_driver,after,True)
        assert_hold_input_boundary(first_driver.clock_mode,first);assert_hold_input_boundary(second_driver.clock_mode,second)
        self.assertEqual(first['logical_seconds'],before)
        self.assertEqual(second['logical_seconds'],after)


if __name__=='__main__':unittest.main()

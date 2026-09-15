import unittest

from perf_input import (assert_delivery, assert_external_phrase, assert_timing_profile,
                        correlate_external_clock, correlate_cgroup_throttling, TICK_NS)


class PerfInputOracleTests(unittest.TestCase):
    def test_delivery_rejects_reordered_or_early_input(self):
        expected = [dict(port=1, bytes=[248], at_monotonic_ns=100),
                    dict(port=1, bytes=[250], at_monotonic_ns=200)]
        delivered = [dict(port=1, bytes=[248], intended_monotonic_ns=100, actual_monotonic_ns=101),
                     dict(port=1, bytes=[250], intended_monotonic_ns=200, actual_monotonic_ns=202)]
        self.assertEqual(assert_delivery(expected, delivered), [1, 2])
        with self.assertRaises(AssertionError):
            assert_delivery(expected, list(reversed(delivered)))
        early = [dict(delivered[0], actual_monotonic_ns=99), delivered[1]]
        with self.assertRaises(AssertionError):
            assert_delivery(expected, early)

    def test_external_clock_correlation_distinguishes_trigger_lateness(self):
        origin = 1_000_000_000
        delivered = []
        for index in range(13):
            intended = origin + index * TICK_NS
            lateness = 40_000_000 if index == 6 else 0
            delivered.append(dict(bytes=[248], intended_monotonic_ns=intended,
                                  actual_monotonic_ns=intended + lateness))
        shared = correlate_external_clock([1_000_000, 41_000_000, 2_000_000],
                                          delivered, origin)
        self.assertEqual(shared['late_output_count'], 1)
        self.assertEqual(shared['shared_late_trigger_count'], 1)
        self.assertTrue(shared['all_late_outputs_follow_late_trigger'])
        self.assertEqual(shared['pairs'][1]['residual_ns'], 1_000_000)

        independent = correlate_external_clock([1_000_000, 41_000_000, 2_000_000],
                                               [dict(row, actual_monotonic_ns=row['intended_monotonic_ns'])
                                                for row in delivered], origin)
        self.assertEqual(independent['late_output_count'], 1)
        self.assertEqual(independent['shared_late_trigger_count'], 0)
        self.assertFalse(independent['all_late_outputs_follow_late_trigger'])

        samples = [dict(monotonic_ns=origin, throttled_periods=0, throttled_ns=0),
                   dict(monotonic_ns=origin + 190_000_000,
                        throttled_periods=1, throttled_ns=40_000_000)]
        throttling = correlate_cgroup_throttling(shared, samples)
        self.assertEqual(throttling['matched_late_trigger_count'], 1)
        self.assertTrue(throttling['all_late_triggers_near_throttle_edge'])

        distant = [dict(monotonic_ns=origin, throttled_periods=0, throttled_ns=0),
                   dict(monotonic_ns=origin + 250_000_000,
                        throttled_periods=1, throttled_ns=40_000_000)]
        throttling = correlate_cgroup_throttling(shared, distant)
        self.assertEqual(throttling['matched_late_trigger_count'], 0)
        self.assertFalse(throttling['all_late_triggers_near_throttle_edge'])

        shifted = list(delivered)
        shifted[6] = dict(shifted[6], intended_monotonic_ns=shifted[6]['intended_monotonic_ns'] + 1)
        with self.assertRaisesRegex(AssertionError, 'trigger deadline'):
            correlate_external_clock([1_000_000, 41_000_000, 2_000_000],
                                     shifted, origin)

    def test_phrase_rejects_wrong_byte_and_wrong_deadline(self):
        origin = 1_000_000_000
        onsets = []
        releases = []
        notes = ((60, 127), (62, 117), (64, 107), (65, 97))
        expected = 1 + (200 - 1) // 6
        for index in range(expected):
            at = origin + index * 6 * TICK_NS
            note, velocity = notes[index % 4]
            onsets.append(dict(port=1, bytes=[144, note, velocity], monotonic_ns=at))
            releases.append(dict(port=1, bytes=[128, note, 0], monotonic_ns=at + TICK_NS))
        self.assertEqual(len(assert_external_phrase(onsets + releases, origin, 200)), expected)
        broken = [dict(row, bytes=list(row['bytes'])) for row in onsets + releases]
        broken[7]['bytes'][1] = 99
        with self.assertRaises(AssertionError):
            assert_external_phrase(broken, origin, 200)
        late = [dict(row, bytes=list(row['bytes'])) for row in onsets + releases]
        late[8]['monotonic_ns'] += 10_000_001
        with self.assertRaisesRegex(AssertionError, 'p99'):
            assert_timing_profile(assert_external_phrase(late, origin, 200))

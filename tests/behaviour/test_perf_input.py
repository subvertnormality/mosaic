import unittest

from perf_input import assert_delivery, assert_external_phrase, assert_timing_profile, TICK_NS


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

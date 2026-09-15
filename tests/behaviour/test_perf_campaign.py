import unittest

from perf_campaign import normalise_location, verdict, window_metrics


def window(index, p99, service99, passed=True, final=1_000_000):
    return {'window': index, 'passed': passed, 'oracle': {'timing': {'p99_ns': p99}, 'final_phase_error_ns': final,
                                                          'service': {'p50_ns': service99 // 2, 'p99_ns': service99}}}


class Tests(unittest.TestCase):
    def test_warmup_window_is_excluded_and_medians_are_reported(self):
        metrics = window_metrics({'windows': [window(1, 99_000_000, 99_000_000, False), window(2, 10_000_000, 4_000_000),
                                              window(3, 12_000_000, 6_000_000, False), window(4, 11_000_000, 5_000_000)]})
        self.assertEqual(metrics['windows'], 3)
        self.assertEqual(metrics['passed'], 2)
        self.assertAlmostEqual(metrics['onset_p99_ms'], 11.0)
        self.assertAlmostEqual(metrics['service_p99_ms'], 5.0)

    def test_verdict_requires_three_non_overlapping_repeats(self):
        self.assertTrue(verdict([10.0], [5.0]).startswith('no-claim'))
        self.assertEqual(verdict([10, 11, 12], [7, 8, 9]), 'improved')
        self.assertEqual(verdict([10, 11, 12], [13, 14, 15]), 'regressed')
        self.assertTrue(verdict([10, 11, 12], [9, 10.5, 13]).startswith('no-claim'))

    def test_profile_locations_ignore_session_paths(self):
        a = normalise_location('...1cb3fc6a31422e9/dust/code/mosaic/lib/clock/m_lattice.lua:204 pulse')
        b = normalise_location('...b55f7c66c718954/dust/code/mosaic/lib/clock/m_lattice.lua:204 pulse')
        self.assertEqual(a, 'mosaic/lib/clock/m_lattice.lua:204 pulse')
        self.assertEqual(a, b)

    def test_functional_failures_yield_no_metrics(self):
        self.assertIsNone(window_metrics({'windows': [{'window': 2, 'oracle': None, 'passed': False}]}))


if __name__ == '__main__':
    unittest.main()

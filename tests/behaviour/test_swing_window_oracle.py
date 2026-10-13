"""Unit tests for the inter-onset window oracle used by M-TIME-006/007.

The oracle decides whether a run's inter-onset windows show that inactive
shuffle settings moved Swing timing. Measured distributions from real runs are
used as fixtures here so the decision can be tested without a two-minute
behaviour run.
"""
import unittest

from swing_window_oracle import assert_stable, stall_budget


TOLERANCE = .01          # the real-time bound, unchanged
CEILING = 3 / 144        # one inter-onset window


def distribution(count, bulk, stalls=()):
    """A run's |window error| list: `count` windows at `bulk`, plus `stalls`."""
    return [bulk] * (count - len(stalls)) + list(stalls)


class StallBudget(unittest.TestCase):
    def test_budget_is_a_thousandth_of_the_windows_with_a_floor(self):
        self.assertEqual(stall_budget(4709), 4)
        self.assertEqual(stall_budget(1000), 3, 'a short run still gets the floor')
        self.assertEqual(stall_budget(0), 3)
        self.assertEqual(stall_budget(50000), 50)


class RealTimeLane(unittest.TestCase):
    def test_a_clean_run_passes(self):
        # Measured: n=4687, median .000124, p99 .001129, max .004715.
        assert_stable(distribution(4687, .000124, stalls=[.001129, .004715]),
                      TOLERANCE, 'clean', stalls_allowed=stall_budget(4687), ceiling=CEILING)

    def test_one_isolated_host_stall_passes(self):
        # Measured failure: n=4709, exactly one window at .010517 while every
        # bulk statistic matched the clean run. That is the scheduler, not a
        # timing change, and it is what made this case fail intermittently.
        assert_stable(distribution(4709, .000112, stalls=[.001161, .010517]),
                      TOLERANCE, 'one stall', stalls_allowed=stall_budget(4709), ceiling=CEILING)

    def test_a_systematic_shift_still_fails(self):
        # If inactive settings moved Swing, the whole distribution moves. The
        # bound is unchanged, so this fails exactly as it did before.
        with self.assertRaises(AssertionError) as caught:
            assert_stable(distribution(4709, .012), TOLERANCE, 'shifted',
                          stalls_allowed=stall_budget(4709), ceiling=CEILING)
        self.assertIn('shifted', str(caught.exception))

    def test_more_stalls_than_the_budget_fails(self):
        # A handful of stalls is the host. Hundreds is not, and must not be
        # waved through just because each one is isolated.
        with self.assertRaises(AssertionError):
            assert_stable(distribution(4709, .000112, stalls=[.0105] * 200),
                          TOLERANCE, 'many stalls',
                          stalls_allowed=stall_budget(4709), ceiling=CEILING)

    def test_a_single_gross_glitch_still_fails(self):
        # One note landing a whole window late is a defect, not jitter, however
        # isolated it is.
        with self.assertRaises(AssertionError):
            assert_stable(distribution(4709, .000112, stalls=[CEILING + .001]),
                          TOLERANCE, 'gross', stalls_allowed=stall_budget(4709), ceiling=CEILING)

    def test_the_message_carries_the_distribution(self):
        # A failure that only says "max was 0.0104" cost hours of guessing.
        with self.assertRaises(AssertionError) as caught:
            assert_stable(distribution(4709, .012), TOLERANCE, 'shifted',
                          stalls_allowed=stall_budget(4709), ceiling=CEILING)
        message = str(caught.exception)
        for field in ('median', 'p99', 'max', 'over'):
            self.assertIn(field, message)


class ControlledLane(unittest.TestCase):
    """Logical time is exact and stays exact: no stalls, bound is the ceiling."""

    def test_the_strict_contract_is_unchanged(self):
        assert_stable([0.0] * 4709, 2e-9, 'logical', stalls_allowed=0, ceiling=2e-9)
        with self.assertRaises(AssertionError):
            assert_stable([0.0] * 4708 + [3e-9], 2e-9, 'logical',
                          stalls_allowed=0, ceiling=2e-9)


if __name__ == '__main__':
    unittest.main()

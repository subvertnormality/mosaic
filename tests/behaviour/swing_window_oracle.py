"""Whether a run's inter-onset windows show that Swing timing moved.

M-TIME-006 and M-TIME-007 assert that changing *inactive* shuffle fields does
not move Swing timing. In logical time that property is exact and stays exact,
so the controlled lane keeps its 2 ns bound on the largest window error and
nothing here changes it.

Real time is a different measurement. The same windows are read from the host's
monotonic clock, so each one carries the scheduler's delivery noise on top of
Mosaic's timing. Measured over repeated runs on an idle machine:

    median   0.11 ms      p95   0.97 ms      p99   1.16 ms
    max      4.7 ms (clean run)   10.5 ms (failing run)

A failing run and a passing run were identical in every bulk statistic; the
failure was one window out of 4709 crossing the bound. Asserting on the maximum
of ~4700 wall-clock samples therefore measured the host, not Mosaic, and its
failure probability grew with the sample count rather than with any property of
the code -- `max` over n samples is an extreme-value statistic, so a rare stall
becomes near-certain as n grows.

A timing change does not look like that. If inactive settings moved Swing, they
would move the whole distribution: thousands of windows, not one. So the bound
itself is unchanged at 10 ms and is applied where a real change shows up, with
an explicit, bounded allowance for isolated stalls and a hard ceiling so that a
single gross glitch -- a note landing a whole window late -- still fails.

This is deliberately more tolerant of host noise and no more tolerant of the
property under test. It is not a licence for a run to be late: the count of
stalls is capped at a thousandth of the windows, every stall must still sit
under one inter-onset window, and the exact contract is verified on every
controlled-lane run at 2 ns.
"""


def stall_budget(count):
    """How many isolated host stalls a real-time run of `count` windows may have.

    A thousandth of the windows, with a floor so a short run is not held to a
    budget of zero. At the observed ~4700 windows this is four.
    """
    return max(3, count // 1000)


def summarise(windows):
    """Order statistics of |window error|, in seconds."""
    values = sorted(abs(x) for x in windows)
    count = len(values)
    if count == 0:
        return dict(count=0, median=0.0, p95=0.0, p99=0.0, max=0.0)

    def at(fraction):
        return values[min(count - 1, max(0, int(count * fraction) - 1))]

    return dict(count=count, median=at(.5), p95=at(.95), p99=at(.99), max=values[-1])


def assert_stable(windows, tolerance, label, *, stalls_allowed, ceiling):
    """Fail unless the windows are consistent with unchanged Swing timing.

    `tolerance` bounds the bulk of the distribution (99th percentile).
    `stalls_allowed` windows may exceed it, each still bounded by `ceiling`.
    With stalls_allowed=0 and ceiling=tolerance this is exactly `max <= tolerance`.
    """
    stats = summarise(windows)
    over = sorted((abs(x) for x in windows if abs(x) > tolerance), reverse=True)
    report = ('%s: count=%d median=%.6f p95=%.6f p99=%.6f max=%.6f over=%d '
              '(allowed %d) tolerance=%.6f ceiling=%.6f' %
              (label, stats['count'], stats['median'], stats['p95'], stats['p99'],
               stats['max'], len(over), stalls_allowed, tolerance, ceiling))

    assert stats['p99'] <= tolerance, (
        'Inactive shuffle settings changed Swing timing: the distribution moved, '
        'not one sample. ' + report)
    assert len(over) <= stalls_allowed, (
        'Inactive shuffle settings changed Swing timing: too many windows exceed '
        'the bound to be host stalls. ' + report)
    assert stats['max'] <= ceiling, (
        'A window exceeded one inter-onset window, which is a dropped or misplaced '
        'onset rather than delivery jitter. ' + report)
    return stats

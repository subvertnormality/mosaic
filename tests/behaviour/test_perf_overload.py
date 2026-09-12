import unittest

from perf_overload import (CHANNELS, FINGERPRINT, PHASE_P99_NS, STEP_NS,
                           assert_recovery, assert_visual_recovery, note_groups)


def group(ordinal, origin, shift=0):
    at = origin + ordinal * STEP_NS + shift
    rows = []
    for channel in range(CHANNELS):
        note = FINGERPRINT[ordinal % len(FINGERPRINT)]
        rows.append(dict(port=1, bytes=[144 + channel, note, 100], monotonic_ns=at + channel))
    return rows


def events(ordinals, origin, shift_after=None):
    ons = []
    for ordinal in ordinals:
        shift = shift_after[1] if shift_after and ordinal >= shift_after[0] else 0
        ons += group(ordinal, origin, shift)
    offs = [dict(row, bytes=[128 + (row['bytes'][0] & 15), row['bytes'][1], 0],
                 monotonic_ns=row['monotonic_ns'] + STEP_NS // 2) for row in ons]
    return ons + offs


class PerfOverloadOracleTests(unittest.TestCase):
    def test_complete_groups_and_release_ownership_fail_closed(self):
        origin = 1_000_000_000
        valid = events(range(32), origin)
        self.assertEqual(len(note_groups(valid)), 32)
        with self.assertRaisesRegex(AssertionError, 'incomplete onset group'):
            note_groups(valid[:-1] + [dict(valid[0], bytes=[144, 60, 100])])
        wrong = [dict(row, bytes=list(row['bytes'])) for row in valid]
        wrong[3]['bytes'][1] = 61
        with self.assertRaises(AssertionError):
            note_groups(wrong)
        missing_release = valid[:-1]
        with self.assertRaisesRegex(AssertionError, 'unbalanced note ownership'):
            note_groups(missing_release)

    def test_recovery_rejects_phase_rebase_pitch_drift_and_missing_steps(self):
        origin = 1_000_000_000
        overload_start = origin + 10 * STEP_NS
        overload_end = origin + 14 * STEP_NS
        groups = note_groups(events(range(40), origin))
        self.assertGreaterEqual(len(assert_recovery(groups, overload_start, overload_end)
                                    ['recovered_errors_ns']), 8)
        shifted = note_groups(events(range(40), origin,
                                     shift_after=(31, PHASE_P99_NS + 1)))
        with self.assertRaisesRegex(AssertionError, 'post-recovery p99'):
            assert_recovery(shifted, overload_start, overload_end)
        skipped = note_groups(events([n for n in range(40) if n != 34], origin))
        with self.assertRaisesRegex(AssertionError, 'missing/duplicate'):
            assert_recovery(skipped, overload_start, overload_end)
        wrong_pitch = [dict(row, bytes=list(row['bytes'])) for row in events(range(40), origin)]
        for offset in range(CHANNELS):
            wrong_pitch[32 * CHANNELS + offset]['bytes'][1] = 62
            wrong_pitch[40 * CHANNELS + 32 * CHANNELS + offset]['bytes'][1] = 62
        with self.assertRaisesRegex(AssertionError, 'timeline/pitch mismatch'):
            assert_recovery(note_groups(wrong_pitch), overload_start, overload_end)
        diagnostic = assert_recovery(note_groups(wrong_pitch), overload_start,
                                     overload_end, enforce=False)
        self.assertFalse(diagnostic['passed'])
        self.assertEqual(diagnostic['issues'][0]['kind'], 'timeline-pitch-mismatch')

    def test_visual_recovery_requires_both_user_perceived_outputs(self):
        before = dict(grid_revision=2, frame_revision=3,
                      state=dict(grid=[0, 1], frame=dict(sha256='a')))
        changed = dict(grid_revision=3, frame_revision=4,
                       state=dict(grid=[1, 0], frame=dict(sha256='b')))
        self.assertEqual(assert_visual_recovery(before, changed)['grid_revisions'], [2, 3])
        for field in ('grid_revision', 'frame_revision'):
            broken = dict(changed)
            broken[field] = before[field]
            with self.assertRaises(AssertionError):
                assert_visual_recovery(before, broken)
        same_grid = dict(changed, state=dict(grid=before['state']['grid'], frame=dict(sha256='b')))
        with self.assertRaisesRegex(AssertionError, 'grid image'):
            assert_visual_recovery(before, same_grid)


if __name__ == '__main__':
    unittest.main()

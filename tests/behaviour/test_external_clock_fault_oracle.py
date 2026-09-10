"""Mutation guards for the degraded-clock MIDI event oracle."""
import copy
import unittest
from external_clock_faults import _assert_notes

TARGETS = [1_000_000_000, 1_150_000_000, 1_300_000_000]
ONSETS = [(TARGETS[0], 60, 100), (TARGETS[1], 62, 90), (TARGETS[2], 64, 80)]
RELEASES = [TARGETS[1], TARGETS[2], 1_350_000_000]


def valid_events():
    rows = []
    index = 1
    for position, (target, pitch, velocity) in enumerate(ONSETS):
        rows.append(dict(index=index, port=1, bytes=[144, pitch, velocity], logical_ns=target)); index += 1
        rows.append(dict(index=index, port=1, bytes=[128, pitch, velocity], logical_ns=RELEASES[position])); index += 1
    return rows


class ExternalClockFaultOracle(unittest.TestCase):
    def accept(self, rows):
        result = _assert_notes(rows, 'logical_ns', ONSETS, RELEASES, 2)
        self.assertEqual((result['onsets'], result['releases']), (3, 3))

    def reject(self, rows):
        with self.assertRaises(AssertionError):
            self.accept(rows)

    def test_accepts_exact_balanced_trace(self):
        self.accept(valid_events())

    def test_rejects_missing_or_extra_onset_and_release(self):
        for remove in (0, 1, 4, 5):
            with self.subTest(remove=remove):
                rows = valid_events(); rows.pop(remove); self.reject(rows)
        rows = valid_events(); rows.append(dict(index=7, port=1, bytes=[144, 65, 70], logical_ns=1_400_000_000)); self.reject(rows)
        rows = valid_events(); rows.append(dict(index=7, port=1, bytes=[128, 65, 0], logical_ns=1_400_000_000)); self.reject(rows)

    def test_rejects_wrong_port_channel_pitch_velocity_and_release_velocity(self):
        for row, change in ((0, {'port': 2}), (0, {'bytes': [145, 60, 100]}),
                            (0, {'bytes': [144, 61, 100]}), (0, {'bytes': [144, 60, 99]}),
                            (1, {'port': 2}), (1, {'bytes': [128, 61, 100]}),
                            (1, {'bytes': [128, 60, 99]})):
            with self.subTest(row=row, change=change):
                rows = valid_events(); rows[row].update(change); self.reject(rows)

    def test_rejects_onset_and_release_outside_tolerance(self):
        for row in range(6):
            for delta in (-3, 3):
                with self.subTest(row=row, delta=delta):
                    rows = valid_events(); rows[row]['logical_ns'] += delta; self.reject(rows)

    def test_rejects_reordering_and_same_pitch_overlap(self):
        rows = valid_events(); rows[2]['index'] = rows[1]['index']; self.reject(rows)
        rows = valid_events(); rows[2]['bytes'] = [144, 60, 90]; self.reject(rows)

    def test_rejects_equal_deadline_onset_before_prior_release(self):
        rows = valid_events(); rows[1], rows[2] = rows[2], rows[1]
        for index, row in enumerate(rows, 1): row['index'] = index
        self.reject(rows)

    def test_transport_release_cannot_precede_actual_delivery(self):
        rows = valid_events(); rows[-1]['logical_ns'] = RELEASES[-1] + 5
        with self.assertRaises(AssertionError):
            _assert_notes(rows, 'logical_ns', ONSETS, RELEASES, 10,
                          causal_releases={2: RELEASES[-1] + 6}, transport_tolerance_ns=10)

    def test_restart_release_cannot_precede_actual_beat_zero_clock(self):
        rows = valid_events(); rows[1]['logical_ns'] = RELEASES[0] + 5
        with self.assertRaises(AssertionError):
            _assert_notes(rows, 'logical_ns', ONSETS, RELEASES, 10,
                          causal_releases={0: RELEASES[0] + 6}, transport_tolerance_ns=10)


if __name__ == '__main__':
    unittest.main()

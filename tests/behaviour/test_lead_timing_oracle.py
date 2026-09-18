"""Proposed-contract characterisation for the independent lock-lead capture oracle.

README does not yet describe this delivery.  These assertions characterize section 3
of docs/parameter-lock-lead-foundations-plan.md without importing production timing
or projection code.
"""
import unittest

from lead_timing_oracle import evaluate


NS = 1_000_000


def event(event_id, port, packet, intended_ns, role, **extra):
    return dict(id=event_id, port=port, bytes=packet, intended_ns=intended_ns,
                role=role, **extra)


def actual(expected, offsets=None):
    """Make a raw capture whose only identity is its port, bytes and capture time."""
    offsets = offsets or {}
    return [dict(port=row['port'], bytes=list(row['bytes']),
                 monotonic_ns=row['intended_ns'] + offsets.get(row['id'], 0))
            for row in expected]


def simple_timeline():
    # The two distinct values prevent accidental zip/min truncation from associating
    # a note with a neighbouring lock.  Values lead their audible notes by 25 ms.
    return [
        event('v-1', 1, [176, 7, 11], 975 * NS, 'value'),
        event('n-1', 1, [144, 60, 100], 1000 * NS, 'note', value_id='v-1', expected_lead_ns=25 * NS),
        event('v-2', 1, [176, 7, 22], 1075 * NS, 'value'),
        event('n-2', 1, [144, 62, 100], 1100 * NS, 'note', value_id='v-2', expected_lead_ns=25 * NS),
    ]


class LeadTimingOracleTests(unittest.TestCase):
    def evaluate(self, expected, rows=None, **kwargs):
        return evaluate(expected, actual(expected) if rows is None else rows, **kwargs)

    def test_exact_controlled_capture_passes_and_reports_all_contract_fields(self):
        result = self.evaluate(simple_timeline(), controlled=True)
        self.assertTrue(result['passed'])
        self.assertEqual(result['placement_errors_ns'], [0, 0, 0, 0])
        self.assertEqual(result['interval_jitter_ns'], [0])
        self.assertEqual(result['lead_errors_ns'], [0, 0])
        self.assertEqual(result['lead_metrics'], {'p95_ns': 0, 'maximum_ns': 0})
        self.assertEqual(result['gates'], {
            'lead_exact': True, 'event_timing': True,
            'step_jitter': True, 'final_phase': True,
        })

    def test_uniform_hidden_note_delay_cannot_be_absorbed_by_first_note_alignment(self):
        expected = simple_timeline()
        result = self.evaluate(expected, actual(expected, {'n-1': 12 * NS, 'n-2': 12 * NS}), controlled=True)
        self.assertFalse(result['passed'])
        self.assertEqual(result['placement_errors_ns'], [0, 12 * NS, 0, 12 * NS])
        self.assertEqual(result['lead_errors_ns'], [12 * NS, 12 * NS])
        self.assertFalse(result['gates']['lead_exact'])
        self.assertFalse(result['gates']['event_timing'])

    def test_pulse_ceiling_lead_fails_the_50_microsecond_gap_gate(self):
        expected = simple_timeline()
        # A one-millisecond dispatch pulse after each intended value is not exact-ms
        # lead, even though the notes themselves still arrive at their intended time.
        result = self.evaluate(expected, actual(expected, {'v-1': NS, 'v-2': NS}), controlled=True)
        self.assertFalse(result['passed'])
        self.assertEqual(result['lead_errors_ns'], [-NS, -NS])
        self.assertFalse(result['gates']['lead_exact'])

    def test_hardware_gap_allows_only_capture_uncertainty_in_addition_to_50_microseconds(self):
        expected = simple_timeline()
        rows = actual(expected, {'v-1': -90_000, 'v-2': -90_000})
        self.assertTrue(self.evaluate(expected, rows, capture_uncertainty_ns=40_000)['gates']['lead_exact'])
        self.assertFalse(self.evaluate(expected, rows, capture_uncertainty_ns=39_999)['gates']['lead_exact'])
        for uncertainty in (-1, 50_001, 1.5):
            with self.subTest(uncertainty=uncertainty):
                with self.assertRaises(ValueError):
                    self.evaluate(expected, capture_uncertainty_ns=uncertainty)

    def test_startup_and_gap_limited_values_keep_their_explicit_effective_leads(self):
        expected = [
            event('startup-value', 1, [176, 7, 10], 1000 * NS, 'value'),
            event('startup-note', 1, [144, 60, 100], 1000 * NS, 'note', value_id='startup-value', expected_lead_ns=0),
            event('gap-value', 1, [176, 7, 20], 1025 * NS, 'value'),
            event('gap-note', 1, [144, 62, 100], 1050 * NS, 'note', value_id='gap-value', expected_lead_ns=25 * NS),
        ]
        result = self.evaluate(expected, controlled=True)
        self.assertTrue(result['passed'])
        self.assertEqual(result['lead_errors_ns'], [0, 0])

    def test_nrpn_uses_its_final_serialized_cc38_as_the_value_timestamp(self):
        expected = [
            event('nrpn-99', 1, [176, 99, 1], 970 * NS, 'value'),
            event('nrpn-98', 1, [176, 98, 2], 971 * NS, 'value'),
            event('nrpn-6', 1, [176, 6, 3], 972 * NS, 'value'),
            event('nrpn-final', 1, [176, 38, 4], 975 * NS, 'value'),
            event('note', 1, [144, 60, 100], 1000 * NS, 'note', value_id='nrpn-final', expected_lead_ns=25 * NS),
        ]
        # These delayed prefix bytes remain before CC38.  They must still fail the
        # event-placement gate, while the lead pair is defined by final CC38 only.
        late_prefix = actual(expected, {'nrpn-99': NS, 'nrpn-98': NS, 'nrpn-6': NS})
        self.assertTrue(self.evaluate(expected, late_prefix, controlled=True)['gates']['lead_exact'])
        late_final = actual(expected, {'nrpn-final': NS})
        result = self.evaluate(expected, late_final, controlled=True)
        self.assertEqual(result['lead_errors_ns'], [-NS])
        self.assertFalse(result['gates']['lead_exact'])

    def test_missing_extra_and_wrong_or_reordered_messages_fail_identity_checks(self):
        expected = simple_timeline()
        cases = {
            'missing': actual(expected)[:-1],
            'extra': actual(expected) + [dict(port=1, bytes=[176, 7, 99], monotonic_ns=1200 * NS)],
            'wrong': actual(expected),
            'reordered': actual(expected),
        }
        cases['wrong'][2]['bytes'] = [176, 7, 99]
        cases['reordered'][2], cases['reordered'][3] = cases['reordered'][3], cases['reordered'][2]
        for name, rows in cases.items():
            with self.subTest(name=name):
                result = self.evaluate(expected, rows, controlled=True)
                self.assertFalse(result['passed'])

    def test_clock_phase_shift_is_an_absolute_final_phase_failure(self):
        expected = [
            event('value', 1, [176, 7, 10], 975 * NS, 'value'),
            event('note', 1, [144, 60, 100], 1000 * NS, 'note', value_id='value', expected_lead_ns=25 * NS),
            event('clock', 2, [248], 1000 * NS, 'clock'),
        ]
        result = self.evaluate(expected, actual(expected, {'clock': 25 * NS}), controlled=True)
        self.assertFalse(result['passed'])
        self.assertFalse(result['gates']['event_timing'])
        self.assertFalse(result['gates']['final_phase'])

    def test_same_suppressed_value_can_be_referenced_by_multiple_notes(self):
        expected = [
            event('one-value', 1, [176, 7, 44], 975 * NS, 'value'),
            event('first-note', 1, [144, 60, 100], 1000 * NS, 'note', value_id='one-value', expected_lead_ns=25 * NS),
            # Resend-off suppresses the unchanged second value.  The in-force first
            # value remains the deliberate association for the second note.
            event('second-note', 1, [144, 62, 100], 1100 * NS, 'note', value_id='one-value', expected_lead_ns=125 * NS),
        ]
        result = self.evaluate(expected, controlled=True)
        self.assertTrue(result['passed'])
        self.assertEqual(result['lead_errors_ns'], [0, 0])

    def test_note_interval_jitter_is_channel_local_and_has_hardware_limits(self):
        expected = [
            event('value-a', 1, [176, 7, 1], 975 * NS, 'value'),
            event('note-a', 1, [144, 60, 100], 1000 * NS, 'note', value_id='value-a', expected_lead_ns=25 * NS),
            event('value-b', 2, [177, 7, 2], 985 * NS, 'value'),
            event('note-b', 2, [145, 61, 100], 1010 * NS, 'note', value_id='value-b', expected_lead_ns=25 * NS),
            event('value-c', 1, [176, 7, 3], 1075 * NS, 'value'),
            event('note-c', 1, [144, 62, 100], 1100 * NS, 'note', value_id='value-c', expected_lead_ns=25 * NS),
        ]
        result = self.evaluate(expected, actual(expected, {'note-c': 11 * NS}))
        self.assertEqual(result['interval_jitter_ns'], [11 * NS])
        self.assertFalse(result['gates']['step_jitter'])

    def test_fixture_and_capture_must_be_the_declared_lists_of_well_formed_events(self):
        expected = simple_timeline()
        malformed = [
            tuple(expected),
            [dict(row, bytes=tuple(row['bytes'])) for row in expected],
            [dict(row, value_id='not-a-note') if row['id'] == 'v-1' else row for row in expected],
            [dict(row, expected_lead_ns=0) if row['id'] == 'v-1' else row for row in expected],
            [dict(row, expected_lead_ns=float(row['expected_lead_ns'])) if row['id'] == 'n-1' else row for row in expected],
            expected + [event('unexpected-role', 3, [250], 1200 * NS, 'unexpected')],
        ]
        for bad_expected in malformed:
            with self.subTest(expected=repr(bad_expected)[:80]):
                result = evaluate(bad_expected, actual(bad_expected) if type(bad_expected) is list else actual(expected))
                self.assertFalse(result['passed'])
        self.assertFalse(evaluate(expected, tuple(actual(expected)))['passed'])

    def test_empty_or_malformed_raw_capture_cannot_claim_a_timing_gate(self):
        expected = simple_timeline()
        malformed_actual = [
            [],
            [dict(row, bytes=tuple(row['bytes'])) for row in actual(expected)],
            [dict(row, monotonic_ns=float(row['monotonic_ns'])) for row in actual(expected)],
            [dict(row) if index else dict(port=row['port'], bytes=row['bytes'])
             for index, row in enumerate(actual(expected))],
        ]
        for rows in malformed_actual:
            with self.subTest(rows=repr(rows)[:80]):
                self.assertFalse(evaluate(expected, rows)['passed'])
        self.assertFalse(evaluate([], [])['passed'])

    def test_value_must_be_serialized_before_the_same_time_note_it_shapes(self):
        expected = [
            # A timestamp tie does not permit the note to precede its value packet.
            event('note', 1, [144, 60, 100], 1000 * NS, 'note', value_id='value', expected_lead_ns=0),
            event('value', 1, [176, 7, 10], 1000 * NS, 'value'),
        ]
        self.assertFalse(self.evaluate(expected, controlled=True)['passed'])

    def test_repeated_serialized_values_remain_distinct_expected_occurrences(self):
        expected = simple_timeline()
        expected[2]['bytes'] = list(expected[0]['bytes'])
        # Wire bytes alone cannot distinguish a dropped value from an identical
        # substitution.  The fixture therefore supplies the ordered occurrence
        # stream; resend-off instead uses one value_id for multiple notes above.
        self.assertTrue(self.evaluate(expected, controlled=True)['passed'])

    def test_expected_times_must_be_monotonic_within_each_port(self):
        expected = simple_timeline() + [event('late-listed-clock', 1, [248], 1099 * NS + 999_999, 'clock')]
        rows = actual(expected, {'late-listed-clock': 2})
        self.assertFalse(self.evaluate(expected, rows, controlled=True)['passed'])

    def test_final_phase_checks_the_last_expected_event_on_every_port(self):
        expected = [
            event('value', 1, [176, 7, 10], 975 * NS, 'value'),
            event('note', 1, [144, 60, 100], 1000 * NS, 'note', value_id='value', expected_lead_ns=25 * NS),
            # This last global item must not hide port 1's final phase error.
            event('clock', 2, [248], 1000 * NS, 'clock'),
        ]
        result = self.evaluate(expected, actual(expected, {'note': 25 * NS}))
        self.assertFalse(result['gates']['final_phase'])

    def test_invalid_or_ambiguous_byte_packets_never_pass(self):
        expected = simple_timeline()
        bad = [
            expected + [event('empty-clock', 2, [], 1200 * NS, 'clock')],
            expected + [event('boolean-clock', 2, [True], 1200 * NS, 'clock')],
            expected + [event('out-of-range-clock', 2, [256], 1200 * NS, 'clock')],
        ]
        for timeline in bad:
            with self.subTest(timeline=repr(timeline[-1]['bytes'])):
                self.assertFalse(self.evaluate(timeline)['passed'])


if __name__ == '__main__':
    unittest.main()

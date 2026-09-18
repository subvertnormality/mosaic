"""Characterisation outside the manual: checkpoint-A diagnostic probe contract."""
import unittest
import math

from pulse_probe import PulseProbe, correlate_callback_deadlines, correlate_deadlines, summarize_snapshot


class FakeMaiden:
    def __init__(self,meta='__MOSAIC_PULSE_PROBE_META__1|2|2|0',rows=None):
        self.calls=[];self.meta=meta
        self.rows=rows if rows is not None else ('__MOSAIC_PULSE_PROBE_ROW__1250000|1|7|41|1500000|1|3|4\n'
                                                     '__MOSAIC_PULSE_PROBE_ROW__1251000|1|7|41|1500000|2|3|4')

    def eval(self,source,allow_lua_error=False):
        self.calls.append((source,allow_lua_error))
        if '__MOSAIC_PULSE_PROBE_META__' in source:return self.meta
        if '__MOSAIC_PULSE_PROBE_ROW__' in source:return self.rows
        return ''


class PulseProbeLifecycle(unittest.TestCase):
    def test_core_callback_correlation_classifies_earliest_deadlines_and_write_durations_without_causal_claim(self):
        snapshot = {'schema_version': 1, 'capacity': 16, 'count': 16, 'dropped': 0,
                    'records': [
                        [10, 1, 1, 0, 0, 1, 0, 0],
                        [12, 5, 1, 0, 15, 1, 0, 0], [13, 4, 1, 1, 0, 1, 3, 1],
                        [14, 4, 1, 1, 0, 2, 3, 1], [16, 5, 1, 0, 15, 2, 0, 0], [20, 1, 1, 0, 0, 2, 0, 0],
                        [21, 5, 2, 0, 20, 1, 0, 0], [21.5, 4, 2, 1, 0, 1, 3, 1],
                        [22, 4, 2, 1, 0, 2, 3, 1], [23, 5, 2, 0, 20, 2, 0, 0],
                        [30, 1, 3, 0, 0, 1, 0, 0], [40, 1, 3, 0, 0, 2, 0, 0],
                        [45, 5, 3, 0, 60, 1, 0, 0], [47, 5, 3, 0, 60, 2, 0, 0],
                        [48, 5, 4, 0, 0, 1, 0, 0], [49, 5, 4, 0, 0, 2, 0, 0],
                    ]}
        result = correlate_callback_deadlines(snapshot)
        self.assertTrue(result['diagnostic_only'])
        self.assertEqual({name: value['count'] for name, value in result['classes'].items()},
                         {'during_pulse_work': 1, 'between_pulses': 1,
                          'outside_capture': 1, 'deadline_unavailable': 1})
        self.assertEqual(result['classes']['during_pulse_work']['callback_lateness_seconds']['maximum'], -3)
        self.assertEqual(result['classes']['during_pulse_work']['write_duration_seconds']['maximum'], 1)
        self.assertEqual(result['classes']['between_pulses']['callback_lateness_seconds']['maximum'], 1)
        self.assertEqual(result['classes']['between_pulses']['write_duration_seconds']['maximum'], .5)
        self.assertIsNone(result['classes']['outside_capture']['write_duration_seconds'])
        self.assertIsNone(result['classes']['deadline_unavailable']['callback_lateness_seconds'])
        self.assertIn('callback-level', result['limitation'])
        self.assertIn('not a group', result['limitation'])

    def test_core_callback_correlation_reuses_validation_and_rejects_noncore_kinds(self):
        invalid = {
            'drops': {'schema_version': 1, 'capacity': 2, 'count': 2, 'dropped': 1,
                      'records': [[1, 1, 1, 0, 0, 1, 0, 0], [2, 1, 1, 0, 0, 2, 0, 0]]},
            'noncore': {'schema_version': 1, 'capacity': 4, 'count': 4, 'dropped': 0,
                        'records': [[1, 1, 1, 0, 0, 1, 0, 0], [2, 1, 1, 0, 0, 2, 0, 0],
                                    [3, 6, 1, 1, 0, 1, 0, 0], [4, 6, 1, 1, 0, 2, 0, 0]]},
        }
        for name, snapshot in invalid.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                correlate_callback_deadlines(snapshot)

    def test_core_callback_correlation_uses_recorded_nesting_not_equal_timestamp_inclusion(self):
        snapshot = {'schema_version': 1, 'capacity': 8, 'count': 8, 'dropped': 0,
                    'records': [
                        [10, 1, 1, 0, 0, 1, 0, 0],
                        # This pulse write finishes before the callback begins at
                        # the same rounded timestamp and must not be attributed.
                        [12, 4, 1, 9, 0, 1, 3, 1], [12, 4, 1, 9, 0, 2, 3, 1],
                        [12, 5, 1, 0, 11, 1, 0, 0], [13, 4, 1, 1, 0, 1, 3, 1],
                        [14, 4, 1, 1, 0, 2, 3, 1], [15, 5, 1, 0, 11, 2, 0, 0],
                        [20, 1, 1, 0, 0, 2, 0, 0],
                    ]}
        writes = correlate_callback_deadlines(snapshot)['classes']['during_pulse_work']['write_duration_seconds']
        self.assertEqual(writes['count'], 1)
        self.assertEqual(writes['maximum'], 1)

    def test_deadline_correlation_classifies_half_open_pulse_occupancy_without_causality_claims(self):
        snapshot = {
            'schema_version': 1, 'capacity': 32, 'count': 18, 'dropped': 0,
            'records': [
                [10, 1, 1, 0, 0, 1, 0, 0], [20, 1, 1, 0, 0, 2, 0, 0],
                [30, 1, 2, 0, 0, 1, 0, 0],
                [31, 6, 2, 1, 10, 1, 0, 1], [31, 6, 2, 1, 10, 2, 0, 1],
                [32, 6, 2, 2, 15, 1, 0, 1], [32, 6, 2, 2, 15, 2, 0, 1],
                [33, 6, 2, 3, 20, 1, 0, 1], [33, 6, 2, 3, 20, 2, 0, 1],
                [34, 6, 2, 4, 25, 1, 0, 1], [34, 6, 2, 4, 25, 2, 0, 1],
                [35, 6, 2, 5, 5, 1, 0, 1], [35, 6, 2, 5, 5, 2, 0, 1],
                [36, 6, 2, 6, 0, 1, 0, 1], [36, 6, 2, 6, 0, 2, 0, 1],
                [40, 1, 2, 0, 0, 2, 0, 0],
                [50, 1, 3, 0, 0, 1, 0, 0], [50, 1, 3, 0, 0, 2, 0, 0],
            ],
        }
        # Add a group after the zero-duration pulse: deadline 50 remains between
        # pulses because pulse occupancy is [begin,end), so [50,50) is empty.
        snapshot['records'].extend([[51, 6, 3, 7, 50, 1, 0, 1], [51, 6, 3, 7, 50, 2, 0, 1]])
        snapshot['count'] = len(snapshot['records'])
        correlation = correlate_deadlines(snapshot)
        self.assertTrue(correlation['diagnostic_only'])
        classes = correlation['classes']
        self.assertEqual({name: classes[name]['count'] for name in classes}, {
            'during_pulse_work': 2, 'between_pulses': 3,
            'outside_capture': 1, 'deadline_unavailable': 1,
        })
        self.assertEqual(classes['deadline_unavailable']['lateness_seconds'], None)
        self.assertEqual(classes['during_pulse_work']['lateness_seconds']['count'], 2)
        self.assertEqual(classes['during_pulse_work']['lateness_seconds']['maximum'], 21)
        self.assertEqual(classes['between_pulses']['lateness_seconds']['maximum'], 13)
        self.assertEqual(classes['outside_capture']['lateness_seconds']['maximum'], 30)

    def test_deadline_correlation_rejects_invalid_probe_snapshots(self):
        with self.assertRaises(ValueError):
            correlate_deadlines({'schema_version': 1, 'capacity': 1, 'count': 1, 'dropped': 0,
                                 'records': [[1, 6, 1, 1, 0, 1, 0, 1]]})

    def test_deadline_correlation_keeps_negative_lateness_and_merges_nested_pulse_spans(self):
        snapshot = {'schema_version': 1, 'capacity': 16, 'count': 14, 'dropped': 0,
                    'records': [
                        [10, 1, 1, 0, 0, 1, 0, 0], [12, 1, 2, 0, 0, 1, 0, 0],
                        [13, 6, 2, 1, 11, 1, 0, 1], [13, 6, 2, 1, 11, 2, 0, 1],
                        [14, 6, 2, 2, 14, 1, 0, 1], [14, 6, 2, 2, 14, 2, 0, 1],
                        [15, 1, 2, 0, 0, 2, 0, 0], [16, 6, 1, 3, 12, 1, 0, 1],
                        [16, 6, 1, 3, 12, 2, 0, 1], [20, 1, 1, 0, 0, 2, 0, 0],
                        # A deadline after the capture end remains signed-negative
                        # latency; a deadline equal to the final captured timestamp
                        # remains inside capture coverage.
                        [21, 6, 3, 4, 30, 1, 0, 1], [21, 6, 3, 4, 30, 2, 0, 1],
                        [22, 6, 3, 5, 22, 1, 0, 1], [22, 6, 3, 5, 22, 2, 0, 1],
                    ]}
        classes = correlate_deadlines(snapshot)['classes']
        self.assertEqual(classes['during_pulse_work']['count'], 3)
        self.assertEqual(classes['during_pulse_work']['lateness_seconds']['p50'], 2)
        self.assertEqual(classes['outside_capture']['lateness_seconds']['maximum'], -9)
        self.assertEqual(classes['between_pulses']['lateness_seconds']['maximum'], 0)
    def test_summary_validates_complete_ordered_boundary_spans_and_reports_diagnostics(self):
        snapshot = {
            'schema_version': 1, 'capacity': 8, 'count': 4, 'dropped': 0,
            'records': [
                [1.000, 1, 7, 0, 0, 1, 0, 0], [1.010, 1, 7, 0, 0, 2, 0, 0],
                [1.020, 4, 7, 2, 1.015, 1, 3, 1], [1.030, 4, 7, 2, 1.015, 2, 3, 1],
            ],
        }
        summary = summarize_snapshot(snapshot)
        self.assertEqual(summary['schema_version'], 1)
        self.assertEqual(summary['capacity'], 8)
        self.assertEqual(summary['span_counts'], {'pulse': 1, 'midi_write': 1})
        self.assertAlmostEqual(summary['duration_seconds']['pulse']['maximum'], .01)
        self.assertAlmostEqual(summary['duration_seconds']['midi_write']['p95'], .01)
        self.assertAlmostEqual(summary['lateness_seconds']['midi_write']['maximum'], .005)
        self.assertNotIn('pulse', summary['lateness_seconds'])

    def test_summary_rejects_drops_and_invalid_or_mispaired_records(self):
        valid = {'schema_version': 1, 'capacity': 2, 'count': 2, 'dropped': 0,
                 'records': [[1, 1, 4, 0, 0, 1, 0, 0], [2, 1, 4, 0, 0, 2, 0, 0]]}
        bad = {
            'drops': dict(valid, dropped=1),
            'unknown kind': dict(valid, records=[[1, 9, 4, 0, 0, 1, 0, 0], [2, 9, 4, 0, 0, 2, 0, 0]]),
            'time backwards': dict(valid, records=[[2, 1, 4, 0, 0, 1, 0, 0], [1, 1, 4, 0, 0, 2, 0, 0]]),
            'missing end': dict(valid, count=1, records=[[1, 1, 4, 0, 0, 1, 0, 0]]),
            'wrong end': dict(valid, records=[[1, 1, 4, 0, 0, 1, 0, 0], [2, 4, 4, 0, 0, 2, 0, 0]]),
        }
        for label, snapshot in bad.items():
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, label.split()[0]):
                    summarize_snapshot(snapshot)

    def test_summary_requires_a_real_pulse_span_and_strict_finite_numeric_rows(self):
        end = [2, 1, 4, 0, 0, 2, 0, 0]
        malformed = {
            'missing pulse empty': {'schema_version': 1, 'capacity': 1, 'count': 0, 'dropped': 0, 'records': []},
            'missing pulse other span': {'schema_version': 1, 'capacity': 2, 'count': 2, 'dropped': 0,
                                         'records': [[1, 4, 4, 0, 0, 1, 0, 0], [2, 4, 4, 0, 0, 2, 0, 0]]},
            'invalid nan time': {'schema_version': 1, 'capacity': 2, 'count': 2, 'dropped': 0,
                                 'records': [[math.nan, 1, 4, 0, 0, 1, 0, 0], end]},
            'invalid infinite deadline': {'schema_version': 1, 'capacity': 2, 'count': 2, 'dropped': 0,
                                          'records': [[1, 1, 4, 0, math.inf, 1, 0, 0], [2, 1, 4, 0, math.inf, 2, 0, 0]]},
            'invalid float kind': {'schema_version': 1, 'capacity': 2, 'count': 2, 'dropped': 0,
                                   'records': [[1, 1.0, 4, 0, 0, 1, 0, 0], [2, 1.0, 4, 0, 0, 2, 0, 0]]},
            'invalid bool kind': {'schema_version': 1, 'capacity': 2, 'count': 2, 'dropped': 0,
                                  'records': [[1, True, 4, 0, 0, 1, 0, 0], [2, True, 4, 0, 0, 2, 0, 0]]},
        }
        for label, snapshot in malformed.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    summarize_snapshot(snapshot)

    def test_install_reset_snapshot_and_remove_use_single_line_bounded_maiden_operations(self):
        maiden=FakeMaiden();probe=PulseProbe(maiden,capacity=2)
        probe.install();probe.reset();snapshot=probe.snapshot();probe.remove()
        self.assertEqual(snapshot,{'schema_version':1,'capacity':2,'count':2,'dropped':0,
                                   'records':[[1.25,1,7,41,1.5,1,3,4],[1.251,1,7,41,1.5,2,3,4]]})
        self.assertEqual(len(maiden.calls),5)
        self.assertTrue(all('\n' not in source for source,_ in maiden.calls))
        self.assertIn('timing_probe',maiden.calls[0][0])
        self.assertIn('__MOSAIC_PULSE_PROBE_META__',maiden.calls[2][0])
        self.assertIn('snapshot(1,128)',maiden.calls[3][0])
        self.assertIn('mosaic_pulse_probe=nil',maiden.calls[4][0])
        self.assertEqual(probe.raw_replies,[maiden.meta,maiden.rows])

    def test_pulse_core_mode_installs_only_pulse_write_and_callback_kind_mask(self):
        core_maiden = FakeMaiden(); core = PulseProbe(core_maiden, capacity=2, mode='pulse-core-v1')
        core.install()
        self.assertIn('kinds={[1]=true,[4]=true,[5]=true}', core_maiden.calls[0][0])
        full_maiden = FakeMaiden(); PulseProbe(full_maiden, capacity=2).install()
        self.assertNotIn('kinds=', full_maiden.calls[0][0])
        with self.assertRaises(ValueError):
            PulseProbe(FakeMaiden(), mode='unknown')

    def test_probe_mode_selects_a_bounded_core_capacity_without_overriding_explicit_capacity(self):
        self.assertEqual(PulseProbe(FakeMaiden(), capacity=None, mode='pulse-core-v1').capacity, 16_384)
        self.assertEqual(PulseProbe(FakeMaiden(), capacity=None, mode='pulse-v1').capacity, 65_536)
        self.assertEqual(PulseProbe(FakeMaiden(), capacity=17, mode='pulse-core-v1').capacity, 17)
        self.assertEqual(PulseProbe(FakeMaiden(), capacity=19, mode='pulse-v1').capacity, 19)

    def test_snapshot_rejects_discarded_or_corrupt_rows(self):
        missing=PulseProbe(FakeMaiden(rows='__MOSAIC_PULSE_PROBE_ROW__1250000|1|7|41|1500000|1|3|4'),capacity=2)
        missing.install()
        with self.assertRaisesRegex(RuntimeError,'row count'):missing.snapshot()
        malformed=PulseProbe(FakeMaiden(rows='__MOSAIC_PULSE_PROBE_ROW__not-a-number|1|7|41|1500000|1|3|4\n__MOSAIC_PULSE_PROBE_ROW__1251000|1|7|41|1500000|2|3|4'),capacity=2)
        malformed.install()
        with self.assertRaisesRegex(RuntimeError,'invalid row'):malformed.snapshot()

    def test_snapshot_preserves_a_drop_count_for_the_campaign_to_invalidate(self):
        probe=PulseProbe(FakeMaiden(meta='__MOSAIC_PULSE_PROBE_META__1|2|2|3'),capacity=2)
        probe.install();snapshot=probe.snapshot()
        self.assertEqual(snapshot['dropped'],3)
        self.assertEqual(len(probe.raw_replies),2)

    def test_context_removes_the_probe_when_capture_raises(self):
        maiden=FakeMaiden()
        with self.assertRaisesRegex(RuntimeError,'capture failed'):
            with PulseProbe(maiden,capacity=4):
                raise RuntimeError('capture failed')
        self.assertIn('mosaic_pulse_probe=nil',maiden.calls[-1][0])


if __name__ == '__main__':
    unittest.main()

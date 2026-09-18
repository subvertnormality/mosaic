import unittest
import math

from pulse_probe import PulseProbe, summarize_snapshot


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

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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

    def test_recovery_rejects_whole_fingerprint_cycle_lost_during_overload(self):
        origin = 1_000_000_000
        groups = note_groups(events(range(44), origin,
                                    shift_after=(12, len(FINGERPRINT) * STEP_NS)))
        with self.assertRaisesRegex(AssertionError, 'musical position'):
            assert_recovery(groups, origin + 10 * STEP_NS, origin + 18 * STEP_NS)

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
        same_frame = dict(changed, state=dict(grid=changed['state']['grid'],
                                               frame=dict(sha256=before['state']['frame']['sha256'])))
        with self.assertRaisesRegex(AssertionError, 'screen image'):
            assert_visual_recovery(before, same_frame)


    def test_builder_recipe_is_exported_before_measurement_starts(self):
        import driver
        import perf_overload

        source = Path(__file__).resolve().parent / 'perf_dense.py'
        node = next(item for item in ast.parse(source.read_text()).body
                    if isinstance(item, ast.ClassDef) and item.name == 'ContainerDriver')
        namespace = {'driver': driver}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
        container_driver = namespace['ContainerDriver']
        order = []
        class ExportingContainerDriver(container_driver):
            def finish(self):
                order.append('export')
                super().finish()

        class FakeHttp:
            def __init__(self, port, token, session_id):
                self.port, self.token, self.session_id = port, token, session_id

            def action(self, value):
                return {'accepted': value}

            def request(self, path, payload):
                order.append(path)
                raise RuntimeError('measurement stopped by test')

        def fake_docker(*args, **kwargs):
            outputs = {
                'image': 'sha256:pinned-image',
                'logs': json.dumps({'status': 'ready', 'token': 'token',
                                    'session_id': 'session'}),
                'port': '127.0.0.1:8765',
            }
            return SimpleNamespace(stdout=outputs.get(args[0], ''))

        def fake_build(session, channels):
            self.assertEqual(channels, perf_overload.CHANNELS)
            order.append('build')
            session.action(type='grid', x=5, y=8, state=1)
            session.results.append({'kind': 'setup'})

        def fake_fingerprint(session):
            order.append('fingerprint')
            session.action(type='grid', x=5, y=8, state=0)

        dependencies = (None, None, None, None, ExportingContainerDriver, FakeHttp, fake_build)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'overload'
            with patch.object(perf_overload, 'runtime_dependencies', return_value=dependencies), \
                    patch.object(perf_overload, 'docker', side_effect=fake_docker), \
                    patch.object(perf_overload, 'configure_fingerprint', side_effect=fake_fingerprint):
                result = perf_overload.run_one('pinned-image', output)
            self.assertEqual(order, ['build', 'fingerprint', 'export', '/performance/start'])
            self.assertFalse(result['passed'])
            self.assertIn('measurement stopped by test', result['error'])
            self.assertEqual(json.loads((output / 'recipe.json').read_text()), [
                {'type': 'grid', 'x': 5, 'y': 8, 'state': 1},
                {'type': 'grid', 'x': 5, 'y': 8, 'state': 0},
            ])
            self.assertEqual(json.loads((output / 'results.json').read_text()),
                             [{'kind': 'setup'}])
            self.assertEqual(len(json.loads((output / 'action-acks.json').read_text())), 2)
            self.assertFalse(json.loads((output / 'result.json').read_text())['passed'])

    def test_report_identifies_the_source_of_the_exported_session(self):
        import perf_overload

        def git_output(command, **kwargs):
            if command[1] == 'rev-parse':
                self.assertTrue(kwargs['text'])
                return 'a' * 40
            if command[1] == 'diff':
                return b''
            if command[1] == 'status':
                return ''
            raise AssertionError(command)

        def fake_run_one(image, output, clock_trace=False):
            output.mkdir()
            return {'passed': True, 'image_id': 'sha256:pinned-image'}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'overload'
            with patch.object(perf_overload.subprocess, 'check_output', side_effect=git_output), \
                    patch.object(perf_overload, 'run_one', side_effect=fake_run_one), \
                    patch.object(sys, 'argv', ['perf_overload.py', '--output', str(output)]):
                self.assertEqual(perf_overload.main(), 0)
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(report['mosaic_revision'], 'a' * 40)
            self.assertIsNone(report['dirty_patch_sha256'])
            self.assertEqual(report['source_status'], [])
            self.assertEqual(report['image_id'], 'sha256:pinned-image')

if __name__ == '__main__':
    unittest.main()

"""Characterisation outside the manual: bounded hardware-run options and windows."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import hardware_performance
import real_norns
from real_norns import main as real_norns_main


class Trace:
    def reset(self):
        pass


class Sampler:
    thread = True
    def start(self):
        pass
    def stop(self):
        return {'identity': {}, 'samples': []}


class Driver:
    instance = None
    def __init__(self, *unused, **ignored):
        type(self).instance = self
        self.expected_step_seconds = .25
        self.tempo_bpm = 90
        self.elapsed = []
        self.finished = False
    def tap(self, *unused):
        return None
    def led_values(self, *unused):
        pass
    def elapse(self, seconds):
        self.elapsed.append(seconds)
    def snapshot(self):
        return {'midi': [], 'grid_writes': 0, 'grid_refreshes': 0}
    def finish(self):
        self.finished = True


class HardwareRunOptionsTests(unittest.TestCase):
    def test_invalid_cli_options_fail_before_constructing_a_remote_transport(self):
        for flag, value, reason in (('--seed', '-1', 'seed must be'), ('--seed', str(2 ** 31), 'seed must be'),
                                    ('--measured-windows', '0', 'measured-windows must be positive'),
                                    ('--measured-windows', '-1', 'measured-windows must be positive'),
                                    ('--measured-steps', '0', 'measured-steps must be positive'),
                                    ('--measured-steps', '-1', 'measured-steps must be positive')):
            with self.subTest(flag=flag, value=value), patch('real_norns.SSH') as ssh:
                stderr = io.StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit):
                    real_norns_main(['performance', flag, value])
                self.assertIn(reason, stderr.getvalue())
                ssh.assert_not_called()

    def test_measured_steps_controls_duration_and_is_reported_without_relaxing_thresholds(self):
        runner = type('Runner', (), {
            'maiden': type('Maiden', (), {'eval': lambda self, source: ''})(),
            'ssh': object(), 'out': Path(tempfile.mkdtemp()),
            'device_map_index': staticmethod(lambda device, channel: 1),
        })()
        oracle_calls = []
        def oracle(events, channels, seconds, step_seconds, workload, **kwargs):
            oracle_calls.append((seconds, step_seconds, kwargs))
            return {'passed': True, 'gates': {'event_timing': True}}
        with patch('hardware_performance.HardwareDriver', Driver), \
             patch('hardware_performance.build_project'), \
             patch('hardware_performance.set_lock_lead', return_value=0), \
             patch('hardware_performance.functional_preflight', return_value={}), \
             patch('hardware_performance.ready_to_play'), \
             patch('hardware_performance.stopped_after_window', return_value=True), \
             patch('hardware_performance.dense_oracle', side_effect=oracle), \
             patch('hardware_performance.resource_metrics', return_value={}), \
             patch('hardware_performance.source_identity', return_value={'mosaic_revision': 'test'}), \
             patch('hardware_performance.time.sleep'):
            result = hardware_performance.run_hardware_performance(
                runner, 'PERF-002-HW-1', 1, 'map', runner.out, Trace(), Sampler(),
                measured_steps=80)
        self.assertEqual(Driver.instance.elapsed, [20.0, .3])
        self.assertEqual(oracle_calls, [(20.0, .25, {'step_stride': 1, 'lead_ms': 0})])
        self.assertEqual(result['requested_window_seconds'], 20.0)
        self.assertEqual(result['run_identity']['measured_steps'], 80)
        self.assertEqual(result['source_identity']['measured_steps'], 80)
        self.assertEqual(hardware_performance.TIMING_THRESHOLDS,
                         {'p99_ns': 10_000_000, 'maximum_ns': 50_000_000, 'final_phase_ns': 20_000_000,
                          'service_p99_deadline_fraction': .5, 'service_maximum_deadline_fraction': 1.0,
                          'step_jitter_p95_ns': 5_000_000, 'step_jitter_maximum_ns': 10_000_000})

    def test_invalid_measured_steps_are_rejected_before_driver_construction(self):
        runner = type('Runner', (), {'maiden': object()})()
        for steps in (0, -1, 1.0, True, '80'):
            with self.subTest(steps=steps), patch('hardware_performance.HardwareDriver') as driver:
                with self.assertRaisesRegex(ValueError, 'measured_steps'):
                    hardware_performance.run_hardware_performance(runner, 'PERF-002-HW-1', 1, 'map', '.',
                                                                   measured_steps=steps)
                driver.assert_not_called()

    def test_cli_forwards_measured_steps_without_opening_a_real_device_session(self):
        calls = []
        class Maiden:
            def close(self):
                pass
        class Runner:
            clock_error_drains = []
            def __init__(self, *unused):
                pass
            def probe(self):
                return {}
            def deploy(self, source):
                return []
            def seed_config(self, *unused):
                pass
            def grid_device(self, device_id):
                return device_id
            def synthetic_grid(self, *unused):
                pass
            def logs(self):
                pass
        with tempfile.TemporaryDirectory() as temporary, \
             patch('real_norns.SSH'), patch('real_norns.Maiden', return_value=Maiden()), \
             patch('real_norns.MaidenInput'), patch('real_norns.Runner', Runner), \
             patch('real_norns.run_hardware_performance', side_effect=lambda *args, **kwargs:
                   calls.append(kwargs) or {'passed': True}):
            status = real_norns.main([
                'performance', '--host', 'test-host', '--maiden-url', 'ws://test', '--osc-host', '127.0.0.1',
                '--artifacts', str(Path(temporary) / 'artifacts'), '--run-id', 'test-run',
                '--performance-case', 'PERF-002-HW-1', '--config-source', temporary,
                '--maiden-input', '--synthetic-grid', '--measured-steps', '80', '--pulse-probe-core',
            ])
        self.assertEqual(status, 0)
        self.assertEqual(calls, [{'thread_sampler': None, 'windows': 1, 'timing_trace': False,
                                  'resource_sampler': True, 'native_screen_trace': False,
                                  'redraw_count_trace': False, 'project_fixture': None,
                                  'save_project_fixture': None, 'lead_ms': None, 'probe_mode': 'pulse-core-v1',
                                  'seed': 0, 'measured_steps': 80,
                                  # A run states which lock lead contract it measured, and
                                  # defaults to the superseded one so an existing command
                                  # line still means what it did.
                                  'timing_contract': 'legacy-delay-v1'}])

    def test_cli_refuses_both_probe_modes_before_remote_construction(self):
        with patch('real_norns.SSH') as ssh:
            stderr = io.StringIO()
            with redirect_stderr(stderr), self.assertRaises(SystemExit):
                real_norns_main(['performance', '--pulse-probe', '--pulse-probe-core'])
            self.assertIn('not allowed with argument', stderr.getvalue())
            ssh.assert_not_called()

    def test_core_probe_profile_records_the_active_kind_mask_in_run_identity(self):
        class CoreProbe:
            instance = None
            def __init__(self, maiden, mode='pulse-v1'):
                type(self).instance = self
                self.capacity = 8
                self.mode = mode
                self.raw_replies = []
                self.removed = False
            def install(self):
                return self
            def reset(self):
                pass
            def snapshot(self):
                return {'schema_version': 1, 'capacity': 8, 'count': 2, 'dropped': 0,
                        'records': [[1, 1, 1, 0, 0, 1, 0, 0], [2, 1, 1, 0, 0, 2, 0, 0]]}
            def remove(self):
                self.removed = True
        runner = type('Runner', (), {
            'maiden': type('Maiden', (), {'eval': lambda self, source: ''})(),
            'ssh': object(), 'out': Path(tempfile.mkdtemp()),
            'device_map_index': staticmethod(lambda device, channel: 1),
        })()
        with patch('hardware_performance.HardwareDriver', Driver), \
             patch('hardware_performance.build_project'), patch('hardware_performance.set_lock_lead', return_value=0), \
             patch('hardware_performance.functional_preflight', return_value={}), \
             patch('hardware_performance.ready_to_play'), patch('hardware_performance.stopped_after_window', return_value=True), \
             patch('hardware_performance.dense_oracle', return_value={'passed': True, 'gates': {}}), \
             patch('hardware_performance.resource_metrics', return_value={}), \
             patch('hardware_performance.source_identity', return_value={'mosaic_revision': 'test'}), \
             patch('hardware_performance.time.sleep'), patch('pulse_probe.PulseProbe', CoreProbe):
            result = hardware_performance.run_hardware_performance(
                runner, 'PERF-002-HW-1', 1, 'map', runner.out, Trace(), Sampler(), probe_mode='pulse-core-v1')
        self.assertEqual(CoreProbe.instance.mode, 'pulse-core-v1')
        self.assertEqual(result['run_identity']['probe_kinds'], [1, 4, 5])
        self.assertEqual(result['source_identity']['probe_kinds'], [1, 4, 5])
        self.assertTrue(result['oracle']['gates']['probe_complete'])
        self.assertTrue(CoreProbe.instance.removed)

    def test_probe_snapshot_failure_keeps_raw_midi_and_replies_then_cleans_up(self):
        class BrokenProbe:
            instance = None
            def __init__(self, maiden, mode='pulse-v1'):
                type(self).instance = self; self.capacity = 1; self.raw_replies = ['install reply']; self.removed = False
            def install(self):
                return self
            def reset(self):
                pass
            def snapshot(self):
                self.raw_replies.append('snapshot reply')
                return {'schema_version': 1, 'capacity': 1, 'count': 1, 'dropped': 1,
                        'records': [[1, 1, 1, 0, 0, 1, 0, 0]]}
            def remove(self):
                self.removed = True
        runner = type('Runner', (), {
            'maiden': type('Maiden', (), {'eval': lambda self, source: ''})(),
            'ssh': object(), 'out': Path(tempfile.mkdtemp()),
            'device_map_index': staticmethod(lambda device, channel: 1),
        })()
        with patch('hardware_performance.HardwareDriver', Driver), \
             patch('hardware_performance.build_project'), patch('hardware_performance.set_lock_lead', return_value=0), \
             patch('hardware_performance.functional_preflight', return_value={}), \
             patch('hardware_performance.ready_to_play'), patch('hardware_performance.stopped_after_window', return_value=True), \
             patch('hardware_performance.resource_metrics', return_value={}), patch('hardware_performance.time.sleep'), \
             patch('pulse_probe.PulseProbe', BrokenProbe):
            with self.assertRaisesRegex(ValueError, 'drops'):
                hardware_performance.run_hardware_performance(
                    runner, 'PERF-002-HW-1', 1, 'map', runner.out, Trace(), Sampler(), probe_mode='pulse-v1')
        raw = json.loads((runner.out / 'performance-raw.json').read_text())
        self.assertEqual(raw['midi'], [])
        self.assertEqual((raw['run_identity']['probe_schema_version'], raw['run_identity']['probe_capacity']), (1, 1))
        self.assertEqual(json.loads((runner.out / 'pulse-probe-replies.json').read_text()), ['install reply', 'snapshot reply'])
        self.assertTrue(BrokenProbe.instance.removed)
        self.assertTrue(Driver.instance.finished)

    def test_probe_schedule_is_validated_before_constructing_a_driver(self):
        runner = type('Runner', (), {'maiden': object()})()
        for schedule in (['off'], ['unknown'], ('off',), 'off', [None]):
            with self.subTest(schedule=schedule), patch('hardware_performance.HardwareDriver') as driver:
                with self.assertRaisesRegex(ValueError, 'probe_schedule'):
                    hardware_performance.run_hardware_performance(
                        runner, 'PERF-002-HW-1', 1, 'map', '.', windows=2,
                        probe_schedule=schedule)
                driver.assert_not_called()

    def test_probe_schedule_uses_a_fresh_probe_only_for_enabled_windows(self):
        class ScheduledProbe:
            instances = []
            def __init__(self, maiden, mode='pulse-v1'):
                self.capacity = 8
                self.mode = mode
                self.calls = []
                self.raw_replies = ['created:' + mode]
                type(self).instances.append(self)
            def install(self):
                self.calls.append('install')
                self.raw_replies.append('installed')
                return self
            def reset(self):
                self.calls.append('reset')
            def snapshot(self):
                self.calls.append('snapshot')
                self.raw_replies.append('snapshot')
                return {'schema_version': 1, 'capacity': 8, 'count': 2, 'dropped': 0,
                        'records': [[1, 1, 1, 0, 0, 1, 0, 0], [2, 1, 1, 0, 0, 2, 0, 0]]}
            def remove(self):
                self.calls.append('remove')
                self.raw_replies.append('removed')
        runner = type('Runner', (), {
            'maiden': type('Maiden', (), {'eval': lambda self, source: ''})(),
            'ssh': object(), 'out': Path(tempfile.mkdtemp()),
            'device_map_index': staticmethod(lambda device, channel: 1),
        })()
        with patch('hardware_performance.HardwareDriver', Driver), \
             patch('hardware_performance.build_project'), patch('hardware_performance.set_lock_lead', return_value=0), \
             patch('hardware_performance.functional_preflight', return_value={}), \
             patch('hardware_performance.ready_to_play'), patch('hardware_performance.stopped_after_window', return_value=True), \
             patch('hardware_performance.dense_oracle', return_value={'passed': True, 'gates': {}}), \
             patch('hardware_performance.resource_metrics', return_value={}), \
             patch('hardware_performance.source_identity', return_value={'mosaic_revision': 'test'}), \
             patch('hardware_performance.time.sleep'), patch('pulse_probe.PulseProbe', ScheduledProbe):
            result = hardware_performance.run_hardware_performance(
                runner, 'PERF-002-HW-1', 1, 'map', runner.out, Trace(), Sampler(), windows=3,
                resource_sampler=False, probe_schedule=['off', 'pulse-v1', 'pulse-core-v1'])
        self.assertEqual([probe.mode for probe in ScheduledProbe.instances], ['pulse-v1', 'pulse-core-v1'])
        self.assertEqual([probe.calls for probe in ScheduledProbe.instances],
                         [['install', 'reset', 'snapshot', 'remove'], ['install', 'reset', 'snapshot', 'remove']])
        self.assertEqual([window['probe_mode'] for window in result['windows']],
                         ['off', 'pulse-v1', 'pulse-core-v1'])
        for window, mode in enumerate(['off', 'pulse-v1', 'pulse-core-v1'], 1):
            raw = json.loads((runner.out / ('performance-raw-window-%d.json' % window)).read_text())
            self.assertEqual(raw['run_identity']['probe_mode'], mode)
        self.assertFalse((runner.out / 'pulse-probe-replies-window-1.json').exists())
        self.assertEqual(json.loads((runner.out / 'pulse-probe-replies-window-2.json').read_text()),
                         ['created:pulse-v1', 'installed', 'snapshot', 'removed'])
        self.assertEqual(json.loads((runner.out / 'pulse-probe-replies-window-3.json').read_text()),
                         ['created:pulse-core-v1', 'installed', 'snapshot', 'removed'])

    def test_probe_schedule_preserves_raw_replies_when_snapshot_or_install_fails(self):
        class FailingProbe:
            instances = []
            def __init__(self, maiden, mode='pulse-v1'):
                self.capacity = 8
                self.mode = mode
                self.calls = []
                self.raw_replies = ['created:' + mode]
                type(self).instances.append(self)
            def install(self):
                self.calls.append('install')
                self.raw_replies.append('installed')
                if self.mode == 'pulse-core-v1':
                    raise RuntimeError('install failed')
                return self
            def reset(self):
                self.calls.append('reset')
            def snapshot(self):
                self.calls.append('snapshot')
                self.raw_replies.append('snapshot failed')
                raise RuntimeError('snapshot failed')
            def remove(self):
                self.calls.append('remove')
                self.raw_replies.append('removed')
        runner = type('Runner', (), {
            'maiden': type('Maiden', (), {'eval': lambda self, source: ''})(),
            'ssh': object(), 'out': Path(tempfile.mkdtemp()),
            'device_map_index': staticmethod(lambda device, channel: 1),
        })()
        common = [patch('hardware_performance.HardwareDriver', Driver), patch('hardware_performance.build_project'),
                  patch('hardware_performance.set_lock_lead', return_value=0),
                  patch('hardware_performance.functional_preflight', return_value={}),
                  patch('hardware_performance.ready_to_play'), patch('hardware_performance.stopped_after_window', return_value=True),
                  patch('hardware_performance.resource_metrics', return_value={}), patch('hardware_performance.time.sleep'),
                  patch('pulse_probe.PulseProbe', FailingProbe)]
        with common[0], common[1], common[2], common[3], common[4], common[5], common[6], common[7], common[8]:
            with self.assertRaisesRegex(RuntimeError, 'snapshot failed'):
                hardware_performance.run_hardware_performance(
                    runner, 'PERF-002-HW-1', 1, 'map', runner.out, Trace(), Sampler(),
                    probe_schedule=['pulse-v1'])
        self.assertEqual(FailingProbe.instances[0].calls, ['install', 'reset', 'snapshot', 'remove'])
        self.assertEqual(json.loads((runner.out / 'pulse-probe-replies.json').read_text()),
                         ['created:pulse-v1', 'installed', 'snapshot failed', 'removed'])
        self.assertTrue((runner.out / 'performance-raw.json').exists())

        install_runner = type('Runner', (), {
            'maiden': type('Maiden', (), {'eval': lambda self, source: ''})(),
            'ssh': object(), 'out': Path(tempfile.mkdtemp()),
            'device_map_index': staticmethod(lambda device, channel: 1),
        })()
        with common[0], common[1], common[2], common[3], common[4], common[5], common[6], common[7], common[8]:
            with self.assertRaisesRegex(RuntimeError, 'install failed'):
                hardware_performance.run_hardware_performance(
                    install_runner, 'PERF-002-HW-1', 1, 'map', install_runner.out, Trace(), Sampler(),
                    probe_schedule=['pulse-core-v1'])
        self.assertEqual(FailingProbe.instances[1].calls, ['install', 'remove'])
        self.assertEqual(json.loads((install_runner.out / 'pulse-probe-replies.json').read_text()),
                         ['created:pulse-core-v1', 'installed', 'removed'])
        self.assertTrue(Driver.instance.finished)

    def test_seed_schedule_is_validated_before_constructing_a_driver(self):
        runner = type('Runner', (), {'maiden': object()})()
        for schedule in ([1], [1, -1], [1, 2 ** 31], [1, 1.0], [True, 1], (1, 2), '1,2'):
            with self.subTest(schedule=schedule), patch('hardware_performance.HardwareDriver') as driver:
                with self.assertRaisesRegex(ValueError, 'seed_schedule'):
                    hardware_performance.run_hardware_performance(
                        runner, 'PERF-002-HW-1', 1, 'map', '.', windows=2,
                        seed_schedule=schedule)
                driver.assert_not_called()

    def test_seed_schedule_reseeds_each_window_and_records_its_actual_seed(self):
        class Maiden:
            def __init__(self):
                self.evaluations = []
            def eval(self, source):
                self.evaluations.append(source)
                return ''
        maiden = Maiden()
        runner = type('Runner', (), {
            'maiden': maiden, 'ssh': object(), 'out': Path(tempfile.mkdtemp()),
            'device_map_index': staticmethod(lambda device, channel: 1),
        })()
        with patch('hardware_performance.HardwareDriver', Driver), \
             patch('hardware_performance.build_project'), patch('hardware_performance.set_lock_lead', return_value=0), \
             patch('hardware_performance.functional_preflight', return_value={}), \
             patch('hardware_performance.ready_to_play'), patch('hardware_performance.stopped_after_window', return_value=True), \
             patch('hardware_performance.dense_oracle', return_value={'passed': True, 'gates': {}}), \
             patch('hardware_performance.resource_metrics', return_value={}), \
             patch('hardware_performance.source_identity', return_value={'mosaic_revision': 'test'}), \
             patch('hardware_performance.time.sleep'):
            result = hardware_performance.run_hardware_performance(
                runner, 'PERF-002-HW-1', 1, 'map', runner.out, Trace(), Sampler(), windows=2,
                resource_sampler=False, seed_schedule=[7, 11])
        self.assertEqual(maiden.evaluations, ['math.randomseed(7)', 'math.randomseed(11)'])
        self.assertEqual([window['seed'] for window in result['windows']], [7, 11])
        self.assertEqual([window['run_identity']['seed'] for window in result['windows']], [7, 11])
        for window, seed in enumerate([7, 11], 1):
            raw = json.loads((runner.out / ('performance-raw-window-%d.json' % window)).read_text())
            self.assertEqual(raw['run_identity']['seed'], seed)


if __name__ == '__main__':
    unittest.main()

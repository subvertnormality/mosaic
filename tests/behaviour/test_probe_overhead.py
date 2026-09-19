"""Proposed diagnostic contract: dispatch-only probe-overhead campaign."""
import copy
import unittest

from probe_overhead import build_campaign, evaluate_campaign, validate_campaign


SOURCE = {'mosaic_revision': 'frozen-test', 'fixture_sha256': 'fixture-test'}


def reports_for(campaign, *, jitter_delta_ns=100_000, cpu_delta=1.0):
    reports = []
    for expected in campaign['windows']:
        core = expected['probe_mode'] == 'pulse-core-v1'
        reports.append({
            'order': expected['order'],
            # Spread rather than dict | dict, which needs Python 3.9 and is not
            # available on the interpreter CI runs this suite with.
            'run_identity': {**{name: expected[name] for name in ('seed', 'workload', 'measured_steps', 'probe_mode')},
                             'midi_lock_lead_time': expected['lead_ms']},
            'source_identity': copy.deepcopy(SOURCE),
            'oracle': {'passed': True, 'gates': {'event_timing': True, 'step_jitter': True,
                       'sustained_service': True, 'hard_service': True,
                       **({'probe_complete': True} if core else {})},
                       'step_jitter': {'p95_ns': 1_000_000 + (jitter_delta_ns if core else 0)}},
            'resources': {'matron_cpu_percent': 40.0 + (cpu_delta if core else 0)},
            **({'pulse_probe': {'dropped': 0, 'capacity': expected.get('probe_capacity')}} if core else {}),
        })
        if core and expected.get('probe_capacity') is not None:
            reports[-1]['run_identity']['probe_capacity'] = expected['probe_capacity']
    return reports


class ProbeOverheadCampaignTests(unittest.TestCase):
    def test_campaign_predeclares_a_deterministic_randomized_order_for_ten_complete_pairs(self):
        first = build_campaign(seed=918, workload='locks-16', lead_ms=25, source_identity=SOURCE)
        second = build_campaign(seed=918, workload='locks-16', lead_ms=25, source_identity=SOURCE)
        self.assertEqual(first, second)
        self.assertEqual(first['receiver_qualification_eligible'], False)
        self.assertEqual(len(first['windows']), 20)
        self.assertEqual([row['order'] for row in first['windows']], list(range(20)))
        self.assertEqual({row['measured_steps'] for row in first['windows']}, {80})
        self.assertEqual({row['workload'] for row in first['windows']}, {'locks-16'})
        self.assertEqual({row['lead_ms'] for row in first['windows']}, {25})
        self.assertEqual(first['probe_capacity'], 16_384)
        for pair in first['pairs']:
            rows = [first['windows'][index] for index in pair['orders']]
            self.assertEqual({row['probe_mode'] for row in rows}, {'off', 'pulse-core-v1'})
            self.assertEqual(len({row['seed'] for row in rows}), 1)
            self.assertEqual(pair['source_identity'], SOURCE)
        self.assertEqual({row['probe_capacity'] for row in first['windows'] if row['probe_mode'] == 'pulse-core-v1'}, {16_384})
        self.assertEqual({row['probe_capacity'] for row in first['windows'] if row['probe_mode'] == 'off'}, {None})

    def test_complete_matching_windows_pass_the_dispatch_only_overhead_gate_but_never_receiver_qualify(self):
        campaign = build_campaign(seed=71, workload='dense-16', lead_ms=50, source_identity=SOURCE)
        result = evaluate_campaign(campaign, reports_for(campaign))
        self.assertTrue(result['passed'])
        self.assertTrue(result['gates']['dispatch_only_probe_overhead'])
        self.assertFalse(result['receiver_qualification_eligible'])
        self.assertEqual(len(result['pairs']), 10)
        self.assertTrue(all(pair['passed'] for pair in result['pairs']))

    def test_missing_duplicate_out_of_order_config_or_source_mismatch_fails_closed(self):
        campaign = build_campaign(seed=72, workload='slides-16', lead_ms=0, source_identity=SOURCE)
        mutations = {
            'missing': lambda rows: rows.pop(),
            'duplicate': lambda rows: rows.__setitem__(1, copy.deepcopy(rows[0])),
            'order': lambda rows: rows.__setitem__(0, rows[1]),
            'config': lambda rows: rows[0]['run_identity'].__setitem__('measured_steps', 79),
            'source': lambda rows: rows[0]['source_identity'].__setitem__('mosaic_revision', 'other'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                rows = reports_for(campaign)
                mutate(rows)
                result = evaluate_campaign(campaign, rows)
                self.assertFalse(result['passed'])
                self.assertFalse(result['gates']['dispatch_only_probe_overhead'])
                self.assertTrue(result['failures'])

    def test_existing_oracle_failure_or_core_probe_drop_or_incomplete_fails_the_pair(self):
        campaign = build_campaign(seed=73, workload='extreme-16', lead_ms=25, source_identity=SOURCE)
        mutations = {
            'oracle_gate': lambda rows, core: core['oracle']['gates'].__setitem__('event_timing', False),
            'drop': lambda rows, core: core.__getitem__('pulse_probe').__setitem__('dropped', 1),
            'incomplete': lambda rows, core: core['oracle']['gates'].__setitem__('probe_complete', False),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                rows = reports_for(campaign)
                core = next(row for row in rows if row['run_identity']['probe_mode'] == 'pulse-core-v1')
                mutate(rows, core)
                result = evaluate_campaign(campaign, rows)
                self.assertFalse(result['passed'])
                self.assertFalse(next(pair for pair in result['pairs'] if core['order'] in pair['orders'])['passed'])

    def test_each_pair_rejects_jitter_or_cpu_delta_above_the_unrelaxed_limits_without_exclusion(self):
        campaign = build_campaign(seed=74, workload='locks-16', lead_ms=25, source_identity=SOURCE)
        for name, jitter, cpu in (('jitter', 250_001, 1.0), ('cpu', 100_000, 2.001)):
            with self.subTest(name=name):
                rows = reports_for(campaign)
                core = next(row for row in rows if row['run_identity']['probe_mode'] == 'pulse-core-v1')
                core['oracle']['step_jitter']['p95_ns'] += jitter
                core['resources']['matron_cpu_percent'] += cpu
                result = evaluate_campaign(campaign, rows)
                self.assertFalse(result['passed'])
                self.assertEqual(len(result['pairs']), 10)
                self.assertEqual(sum(pair['passed'] for pair in result['pairs']), 9)
                failed = next(pair for pair in result['pairs'] if not pair['passed'])
                self.assertGreater(abs(failed['jitter_p95_delta_ns']), 250_000) if name == 'jitter' else self.assertGreater(abs(failed['cpu_delta_percentage_points']), 2)

    def test_invalid_campaign_input_and_missing_metric_values_fail_closed(self):
        for lead in (-1, 51, True):
            with self.subTest(lead=lead), self.assertRaises(ValueError):
                build_campaign(seed=75, workload='locks-16', lead_ms=lead, source_identity=SOURCE)
        with self.assertRaises(ValueError):
            build_campaign(seed=True, workload='locks-16', lead_ms=25, source_identity=SOURCE)
        campaign = build_campaign(seed=75, workload='locks-16', lead_ms=25, source_identity=SOURCE)
        rows = reports_for(campaign)
        rows[0]['resources']['matron_cpu_percent'] = None
        result = evaluate_campaign(campaign, rows)
        self.assertFalse(result['passed'])
        self.assertTrue(result['failures'])

    def test_manifest_validation_requires_strict_schema_contiguous_windows_and_a_complete_pair_partition(self):
        campaign = build_campaign(seed=76, workload='locks-16', lead_ms=25, source_identity=SOURCE)
        mutations = {
            'schema': lambda value: value.__setitem__('schema_version', True),
            'window-order': lambda value: value['windows'][19].__setitem__('order', 18),
            'pair-id': lambda value: value['pairs'][9].__setitem__('pair', 8),
            'reused-order': lambda value: value['pairs'][1].__setitem__('orders', value['pairs'][0]['orders']),
            'pair-seed': lambda value: value['pairs'][0].__setitem__('seed', value['pairs'][0]['seed'] + 1),
            'pair-mode': lambda value: value['pairs'][0].__setitem__('probe_modes', ['off', 'off']),
            'pair-config': lambda value: value['pairs'][0].__setitem__('lead_ms', 26),
            'core-capacity': lambda value: next(row for row in value['windows'] if row['probe_mode'] == 'pulse-core-v1').__setitem__('probe_capacity', 8192),
        }
        self.assertEqual(validate_campaign(campaign), campaign)
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                bad = copy.deepcopy(campaign)
                mutate(bad)
                with self.assertRaises(ValueError):
                    validate_campaign(bad)

    def test_core_capacity_is_predeclared_and_actual_core_identity_must_match_it(self):
        campaign = build_campaign(seed=78, workload='locks-16', lead_ms=25, source_identity=SOURCE, probe_capacity=8192)
        self.assertEqual(campaign['probe_capacity'], 8192)
        core_window = next(row for row in campaign['windows'] if row['probe_mode'] == 'pulse-core-v1')
        self.assertEqual(core_window['probe_capacity'], 8192)
        rows = reports_for(campaign)
        core_report = next(row for row in rows if row['run_identity']['probe_mode'] == 'pulse-core-v1')
        for value in (None, 16_384):
            with self.subTest(value=value):
                changed = copy.deepcopy(rows)
                changed_core = next(row for row in changed if row['run_identity']['probe_mode'] == 'pulse-core-v1')
                if value is None:
                    changed_core['run_identity'].pop('probe_capacity')
                else:
                    changed_core['run_identity']['probe_capacity'] = value
                self.assertFalse(evaluate_campaign(campaign, changed)['passed'])
        self.assertEqual(core_report['run_identity']['probe_capacity'], 8192)

    def test_capacity_schema_is_strict_and_raw_core_snapshot_must_match_the_declared_identity(self):
        for capacity in (0, -1, True, 1.0, 262_145):
            with self.subTest(capacity=capacity), self.assertRaises(ValueError):
                build_campaign(seed=79, workload='locks-16', lead_ms=25, source_identity=SOURCE,
                               probe_capacity=capacity)
        campaign = build_campaign(seed=79, workload='locks-16', lead_ms=25, source_identity=SOURCE)
        old_schema = copy.deepcopy(campaign)
        old_schema['schema_version'] = 1
        with self.assertRaises(ValueError):
            validate_campaign(old_schema)
        rows = reports_for(campaign)
        core = next(row for row in rows if row['run_identity']['probe_mode'] == 'pulse-core-v1')
        core['pulse_probe']['capacity'] = campaign['probe_capacity'] - 1
        result = evaluate_campaign(campaign, rows)
        self.assertFalse(result['passed'])
        self.assertIn('raw probe capacity', ' '.join(result['failures']))

    def test_required_existing_gate_names_and_strict_nonnegative_core_metrics_cannot_be_weakened(self):
        campaign = build_campaign(seed=77, workload='locks-16', lead_ms=25, source_identity=SOURCE)
        mutations = {
            'omitted-required-gate': lambda core: core['oracle']['gates'].pop('hard_service'),
            'renamed-required-gate': lambda core: core['oracle']['gates'].__setitem__('hard-service', core['oracle']['gates'].pop('hard_service')),
            'extra-false-gate': lambda core: core['oracle']['gates'].__setitem__('future_gate', False),
            'negative-jitter': lambda core: core['oracle']['step_jitter'].__setitem__('p95_ns', -1),
            'negative-cpu': lambda core: core['resources'].__setitem__('matron_cpu_percent', -1),
            'bool-cpu': lambda core: core['resources'].__setitem__('matron_cpu_percent', False),
            'bool-drop': lambda core: core['pulse_probe'].__setitem__('dropped', False),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                rows = reports_for(campaign)
                core = next(row for row in rows if row['run_identity']['probe_mode'] == 'pulse-core-v1')
                mutate(core)
                result = evaluate_campaign(campaign, rows)
                self.assertFalse(result['passed'])
                self.assertFalse(result['gates']['dispatch_only_probe_overhead'])


if __name__ == '__main__':
    unittest.main()

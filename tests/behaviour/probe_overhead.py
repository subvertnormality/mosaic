"""Predeclared, dispatch-only probe-overhead campaign evaluation."""
import copy
import math
import random


PAIR_COUNT = 10
MEASURED_STEPS = 80
JITTER_P95_DELTA_NS = 250_000
CPU_DELTA_PERCENTAGE_POINTS = 2.0
MODES = ('off', 'pulse-core-v1')
REQUIRED_ORACLE_GATES = ('event_timing', 'sustained_service', 'hard_service', 'step_jitter')


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('%s must be an integer at least %d' % (name, minimum))


def build_campaign(*, seed, workload, lead_ms, source_identity, probe_capacity=16384):
    """Return the complete manifest before any dispatch-only run starts."""
    _integer(seed, 'seed')
    if seed >= 2 ** 31:
        raise ValueError('seed must be below 2**31')
    if not isinstance(workload, str) or not workload:
        raise ValueError('workload must be a non-empty string')
    _integer(lead_ms, 'lead_ms')
    if lead_ms > 50:
        raise ValueError('lead_ms must be in 0..50')
    if not isinstance(source_identity, dict) or not source_identity:
        raise ValueError('source_identity must be a non-empty dict')
    _integer(probe_capacity, 'probe_capacity', 1)
    if probe_capacity > 262144:
        raise ValueError('probe_capacity must be at most 262144')
    generator = random.Random(seed)
    windows, pairs = [], []
    for pair in range(PAIR_COUNT):
        pair_seed = generator.randrange(2 ** 31)
        modes = list(MODES)
        generator.shuffle(modes)
        orders = []
        for mode in modes:
            order = len(windows)
            orders.append(order)
            windows.append({'order': order, 'pair': pair, 'seed': pair_seed,
                            'workload': workload, 'lead_ms': lead_ms,
                            'measured_steps': MEASURED_STEPS, 'probe_mode': mode,
                            'probe_capacity': probe_capacity if mode == 'pulse-core-v1' else None})
        pairs.append({'pair': pair, 'orders': orders, 'seed': pair_seed,
                      'workload': workload, 'lead_ms': lead_ms, 'measured_steps': MEASURED_STEPS,
                      'probe_modes': modes, 'source_identity': copy.deepcopy(source_identity)})
    campaign = {'schema_version': 2, 'campaign_seed': seed, 'workload': workload,
            'lead_ms': lead_ms, 'measured_steps': MEASURED_STEPS,
            'probe_capacity': probe_capacity,
            'source_identity': copy.deepcopy(source_identity), 'pairs': pairs,
            'windows': windows, 'receiver_qualification_eligible': False}
    validate_campaign(campaign)
    return campaign


def validate_campaign(campaign):
    """Reject a malformed or incomplete predeclared campaign before remote use."""
    root_keys = {'schema_version', 'campaign_seed', 'workload', 'lead_ms', 'measured_steps',
                 'source_identity', 'pairs', 'windows', 'receiver_qualification_eligible', 'probe_capacity'}
    window_keys = {'order', 'pair', 'seed', 'workload', 'lead_ms', 'measured_steps', 'probe_mode', 'probe_capacity'}
    pair_keys = {'pair', 'orders', 'seed', 'workload', 'lead_ms', 'measured_steps', 'probe_modes', 'source_identity'}
    if not isinstance(campaign, dict) or set(campaign) != root_keys or type(campaign['schema_version']) is not int or campaign['schema_version'] != 2:
        raise ValueError('unknown or malformed overhead campaign schema')
    _integer(campaign['probe_capacity'], 'probe_capacity', 1)
    if campaign['probe_capacity'] > 262144:
        raise ValueError('probe_capacity must be at most 262144')
    _integer(campaign['campaign_seed'], 'campaign_seed')
    if campaign['campaign_seed'] >= 2 ** 31 or not isinstance(campaign['workload'], str) or not campaign['workload']:
        raise ValueError('invalid campaign seed or workload')
    _integer(campaign['lead_ms'], 'lead_ms')
    if campaign['lead_ms'] > 50 or campaign['measured_steps'] != MEASURED_STEPS or type(campaign['measured_steps']) is not int:
        raise ValueError('invalid campaign lead or measured steps')
    if not isinstance(campaign['source_identity'], dict) or not campaign['source_identity'] or campaign['receiver_qualification_eligible'] is not False:
        raise ValueError('invalid campaign source or qualification setting')
    windows, pairs = campaign['windows'], campaign['pairs']
    if not isinstance(windows, list) or not isinstance(pairs, list) or len(windows) != PAIR_COUNT * 2 or len(pairs) != PAIR_COUNT:
        raise ValueError('invalid overhead campaign length')
    for order, window in enumerate(windows):
        if not isinstance(window, dict) or set(window) != window_keys or window['order'] != order or type(window['order']) is not int:
            raise ValueError('windows must have unique contiguous orders 0..19')
        if type(window['pair']) is not int or not 0 <= window['pair'] < PAIR_COUNT or window['probe_mode'] not in MODES:
            raise ValueError('invalid window pair or mode')
        if window['probe_mode'] == 'pulse-core-v1':
            if type(window['probe_capacity']) is not int or window['probe_capacity'] != campaign['probe_capacity']:
                raise ValueError('window probe capacity differs from campaign')
        elif window['probe_capacity'] is not None:
            raise ValueError('off window must not specify probe capacity')
        _integer(window['seed'], 'window seed')
        if (window['seed'] >= 2 ** 31 or not isinstance(window['workload'], str)
                or type(window['lead_ms']) is not int or type(window['measured_steps']) is not int
                or window['workload'] != campaign['workload'] or window['lead_ms'] != campaign['lead_ms']
                or window['measured_steps'] != MEASURED_STEPS):
            raise ValueError('window configuration differs from campaign')
    seen_orders = set()
    for pair_id, pair in enumerate(pairs):
        if not isinstance(pair, dict) or set(pair) != pair_keys or pair.get('pair') != pair_id or type(pair['pair']) is not int:
            raise ValueError('pairs must have unique contiguous ids 0..9')
        if not isinstance(pair['orders'], list) or len(pair['orders']) != 2 or any(type(order) is not int for order in pair['orders']):
            raise ValueError('invalid pair orders')
        if len(set(pair['orders'])) != 2 or any(order not in range(PAIR_COUNT * 2) for order in pair['orders']) or seen_orders.intersection(pair['orders']):
            raise ValueError('pairs must partition each window exactly once')
        seen_orders.update(pair['orders'])
        selected = [windows[order] for order in pair['orders']]
        if any(window['pair'] != pair_id for window in selected):
            raise ValueError('pair id differs from its windows')
        if type(pair['seed']) is not int or pair['seed'] < 0 or pair['seed'] >= 2 ** 31 or any(window['seed'] != pair['seed'] for window in selected):
            raise ValueError('pair seed differs from its windows')
        if (not isinstance(pair['workload'], str) or type(pair['lead_ms']) is not int
                or type(pair['measured_steps']) is not int or pair['workload'] != campaign['workload']
                or pair['lead_ms'] != campaign['lead_ms'] or pair['measured_steps'] != MEASURED_STEPS):
            raise ValueError('pair configuration differs from campaign')
        if pair['source_identity'] != campaign['source_identity'] or pair['probe_modes'] != [window['probe_mode'] for window in selected] or set(pair['probe_modes']) != set(MODES):
            raise ValueError('pair mode or source differs from its windows')
    if seen_orders != set(range(PAIR_COUNT * 2)):
        raise ValueError('pairs must partition all windows')
    return campaign


def _finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _report_failure(report, expected, source_identity):
    """Return every per-window failure; never turn absent evidence into a pass."""
    if not isinstance(report, dict):
        return ['report is not a dict'], None
    failures = []
    if report.get('order') != expected['order']:
        failures.append('report order does not match its predeclared window')
    identity = report.get('run_identity')
    if not isinstance(identity, dict):
        failures.append('missing run identity')
    else:
        required = dict(seed=expected['seed'], workload=expected['workload'],
                        midi_lock_lead_time=expected['lead_ms'], measured_steps=MEASURED_STEPS,
                        probe_mode=expected['probe_mode'])
        if any(identity.get(name) != value for name, value in required.items()):
            failures.append('run configuration does not match its predeclared window')
        if expected['probe_mode'] == 'pulse-core-v1' and (
                type(identity.get('probe_capacity')) is not int or identity['probe_capacity'] != expected['probe_capacity']):
            failures.append('core probe capacity does not match its predeclared window')
    if report.get('source_identity') != source_identity:
        failures.append('source identity does not match campaign manifest')
    oracle = report.get('oracle')
    if not isinstance(oracle, dict) or oracle.get('passed') is not True:
        failures.append('existing oracle did not pass')
    gates = oracle.get('gates') if isinstance(oracle, dict) else None
    if (not isinstance(gates, dict) or any(name not in gates for name in REQUIRED_ORACLE_GATES)
            or any(value is not True for value in gates.values())):
        failures.append('an existing oracle gate is absent or false')
    metrics = None
    jitter = oracle.get('step_jitter') if isinstance(oracle, dict) else None
    resources = report.get('resources')
    if not isinstance(jitter, dict) or not _finite_number(jitter.get('p95_ns')) or jitter.get('p95_ns') < 0:
        failures.append('missing finite p95 step jitter')
    if not isinstance(resources, dict) or not _finite_number(resources.get('matron_cpu_percent')) or resources.get('matron_cpu_percent') < 0:
        failures.append('missing finite matron CPU percentage')
    if (isinstance(jitter, dict) and isinstance(resources, dict) and _finite_number(jitter.get('p95_ns'))
            and _finite_number(resources.get('matron_cpu_percent')) and jitter['p95_ns'] >= 0 and resources['matron_cpu_percent'] >= 0):
        metrics = {'jitter_p95_ns': jitter['p95_ns'], 'cpu_percentage_points': resources['matron_cpu_percent']}
    if expected['probe_mode'] == 'pulse-core-v1':
        probe = report.get('pulse_probe')
        if not isinstance(probe, dict) or type(probe.get('dropped')) is not int or probe.get('dropped') != 0:
            failures.append('core probe is missing or dropped records')
        if not isinstance(probe, dict) or type(probe.get('capacity')) is not int or probe['capacity'] != expected['probe_capacity']:
            failures.append('raw probe capacity does not match its predeclared window')
        if not isinstance(gates, dict) or gates.get('probe_complete') is not True:
            failures.append('core probe is incomplete')
    return failures, metrics


def evaluate_campaign(campaign, reports):
    """Evaluate all ten predeclared pairs without averaging or excluding windows."""
    campaign = validate_campaign(campaign)
    windows, pairs, source_identity = campaign['windows'], campaign['pairs'], campaign['source_identity']
    result = {'schema_version': 1, 'diagnostic_only': True, 'receiver_qualification_eligible': False,
              'gates': {'dispatch_only_probe_overhead': False}, 'passed': False, 'failures': [], 'pairs': []}
    indexed = {}
    if not isinstance(reports, list):
        result['failures'].append('reports must be a list')
        reports = []
    if len(reports) != len(windows):
        result['failures'].append('report count does not match the 20 predeclared windows')
    for position, report in enumerate(reports):
        if not isinstance(report, dict) or type(report.get('order')) is not int:
            result['failures'].append('report has no integer order')
            continue
        order = report['order']
        if order in indexed:
            result['failures'].append('duplicate report order %d' % order)
            continue
        indexed[order] = (position, report)
    for expected in windows:
        if expected['order'] not in indexed:
            result['failures'].append('missing report order %d' % expected['order'])
    window_results = {}
    for expected in windows:
        entry = indexed.get(expected['order'])
        if entry is None:
            window_results[expected['order']] = (['missing predeclared window'], None)
            continue
        position, report = entry
        failures, metrics = _report_failure(report, expected, source_identity)
        if position != expected['order']:
            failures.append('report sequence is not the predeclared randomized order')
        window_results[expected['order']] = (failures, metrics)
        result['failures'].extend('window %d: %s' % (expected['order'], item) for item in failures)
    by_order = {row['order']: row for row in windows}
    for pair in pairs:
        orders = pair.get('orders') if isinstance(pair, dict) else None
        pair_result = {'pair': pair.get('pair') if isinstance(pair, dict) else None, 'orders': orders,
                       'passed': False, 'failures': [], 'jitter_p95_delta_ns': None,
                       'cpu_delta_percentage_points': None}
        if not isinstance(orders, list) or len(orders) != 2 or any(order not in by_order for order in orders):
            pair_result['failures'].append('invalid pair orders')
        else:
            expected = [by_order[order] for order in orders]
            if {row['probe_mode'] for row in expected} != set(MODES):
                pair_result['failures'].append('pair does not contain exactly off and pulse-core-v1')
            failed = [(order, window_results[order]) for order in orders if window_results[order][0]]
            if failed:
                pair_result['failures'].extend('window %d failed: %s' % (order, ', '.join(data[0])) for order, data in failed)
            else:
                metrics = {by_order[order]['probe_mode']: window_results[order][1] for order in orders}
                if any(metrics[mode] is None for mode in MODES):
                    pair_result['failures'].append('pair metrics are incomplete')
                else:
                    pair_result['jitter_p95_delta_ns'] = metrics['pulse-core-v1']['jitter_p95_ns'] - metrics['off']['jitter_p95_ns']
                    pair_result['cpu_delta_percentage_points'] = metrics['pulse-core-v1']['cpu_percentage_points'] - metrics['off']['cpu_percentage_points']
                    if abs(pair_result['jitter_p95_delta_ns']) > JITTER_P95_DELTA_NS:
                        pair_result['failures'].append('paired p95 jitter delta exceeds 0.25 ms')
                    if abs(pair_result['cpu_delta_percentage_points']) > CPU_DELTA_PERCENTAGE_POINTS:
                        pair_result['failures'].append('paired CPU delta exceeds 2 percentage points')
        pair_result['passed'] = not pair_result['failures']
        result['pairs'].append(pair_result)
    result['failures'].extend('pair %s: %s' % (pair['pair'], item)
                              for pair in result['pairs'] for item in pair['failures'])
    result['passed'] = not result['failures'] and all(pair['passed'] for pair in result['pairs'])
    result['gates']['dispatch_only_probe_overhead'] = result['passed']
    return result

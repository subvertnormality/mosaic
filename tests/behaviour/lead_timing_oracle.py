"""Independent capture metrics for the proposed foundations contract.

Expected times come from a fixture/input clock, never from observed note times.
This supplemental oracle does not replace the legacy dense workload/service gate.
It cannot qualify a rig whose timebase calibration has not been measured.
"""
import math
from collections import defaultdict


def _percentile(values, percent):
    if not values:
        return 0
    return sorted(values)[math.ceil(len(values) * percent / 100) - 1]


def _packet(event):
    if not isinstance(event, dict) or type(event.get('bytes')) is not list or not event['bytes']:
        raise ValueError('Event must contain a nonempty byte list')
    if any(type(byte) is not int or not 0 <= byte <= 255 for byte in event['bytes']):
        raise ValueError('Packet byte outside 0..255')


def evaluate(expected, actual, *, capture_uncertainty_ns=0, controlled=False):
    if type(capture_uncertainty_ns) is not int or not 0 <= capture_uncertainty_ns <= 50_000:
        raise ValueError('Capture uncertainty must be an integer in 0..50000 ns')
    result = dict(passed=False, placement_errors_ns=[], interval_jitter_ns=[],
                  lead_errors_ns=[], lead_metrics={'p95_ns': 0, 'maximum_ns': 0},
                  gates=dict.fromkeys(('lead_exact', 'event_timing', 'step_jitter', 'final_phase'), False))
    try:
        if type(expected) is not list or type(actual) is not list:
            raise ValueError('Expected timeline and capture must be lists')
        if not expected or len(expected) != len(actual):
            raise ValueError('Missing or extra capture events')
        by_port = defaultdict(list)
        for event in actual:
            _packet(event)
            if type(event['monotonic_ns']) is not int:
                raise ValueError('Capture timestamp must be integer nanoseconds')
            stream = by_port[event['port']]
            if stream and event['monotonic_ns'] < stream[-1]['monotonic_ns']:
                raise ValueError('Capture time runs backwards on a port')
            stream.append(event)
        positions, matched, specifications, ordinal, last_intended = defaultdict(int), {}, {}, {}, {}
        for event in expected:
            _packet(event)
            if event.get('role') not in ('note', 'value', 'clock', 'other'):
                raise ValueError('Unknown expected event role')
            if event['role'] != 'note' and ('value_id' in event or 'expected_lead_ns' in event):
                raise ValueError('Value association belongs only on notes')
            identity, port = event['id'], event['port']
            if identity in specifications or type(event['intended_ns']) is not int:
                raise ValueError('Duplicate identity or invalid intended time')
            if port in last_intended and event['intended_ns'] < last_intended[port]:
                raise ValueError('Intended time runs backwards on a port')
            last_intended[port] = event['intended_ns']
            stream = by_port[port]
            pos = positions[port]
            if pos >= len(stream) or event['bytes'] != stream[pos]['bytes']:
                raise ValueError('Capture identity/order does not match fixture')
            specifications[identity], matched[identity] = event, stream[pos]
            ordinal[identity] = pos
            positions[port] += 1
        if any(positions[port] != len(stream) for port, stream in by_port.items()):
            raise ValueError('Extra capture port/events')
        last_note, jitter, gaps, errors, final_errors = {}, [], [], [], {}
        for event in expected:
            found = matched[event['id']]
            errors.append(found['monotonic_ns'] - event['intended_ns'])
            final_errors[event['port']] = errors[-1]
            if event['role'] != 'note':
                continue
            packet = event['bytes']
            if len(packet) != 3 or not 0x90 <= packet[0] <= 0x9f or packet[2] <= 0:
                raise ValueError('Note fixture has invalid bytes')
            key = (event['port'], packet[0] & 15)
            previous = last_note.get(key)
            if previous:
                prev_spec, prev_actual = previous
                jitter.append(abs((found['monotonic_ns'] - prev_actual['monotonic_ns']) -
                                  (event['intended_ns'] - prev_spec['intended_ns'])))
            last_note[key] = event, found
            value = specifications[event['value_id']]
            if type(event['expected_lead_ns']) is not int:
                raise ValueError('Expected lead must be integer nanoseconds')
            if value['role'] != 'value' or value['port'] != event['port'] or (value['bytes'][0] & 15) != key[1]:
                raise ValueError('Note references a value for another receiver')
            if value['intended_ns'] > event['intended_ns'] or event['expected_lead_ns'] < 0:
                raise ValueError('Value is later than the note it shapes')
            if ordinal[value['id']] >= ordinal[event['id']]:
                raise ValueError('Value must precede its note in the wire stream')
            if event['intended_ns'] - value['intended_ns'] != event['expected_lead_ns']:
                raise ValueError('Expected lead disagrees with fixture timeline')
            gaps.append(found['monotonic_ns'] - matched[event['value_id']]['monotonic_ns'] - event['expected_lead_ns'])
        if not gaps:
            raise ValueError('Capture has no note/value pairs')
        absolute, gap_abs = list(map(abs, errors)), list(map(abs, gaps))
        gap_tolerance = 50_000 + (0 if controlled else capture_uncertainty_ns)
        gates = dict(lead_exact=max(gap_abs) <= gap_tolerance,
                     event_timing=(max(absolute) <= 50_000 if controlled else
                                   _percentile(absolute, 99) <= 10_000_000 and max(absolute) <= 50_000_000),
                     step_jitter=(max(jitter, default=0) <= 50_000 if controlled else
                                  _percentile(jitter, 95) <= 5_000_000 and max(jitter, default=0) <= 10_000_000),
                     final_phase=max(map(abs, final_errors.values())) <= (50_000 if controlled else 20_000_000))
        result.update(passed=all(gates.values()), placement_errors_ns=errors, interval_jitter_ns=jitter,
                      lead_errors_ns=gaps, lead_metrics={'p95_ns': _percentile(gap_abs, 95), 'maximum_ns': max(gap_abs)}, gates=gates)
    except (KeyError, TypeError, ValueError, IndexError) as error:
        result['failure'] = str(error)
    return result

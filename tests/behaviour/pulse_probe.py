"""Opt-in pulse diagnostics; no production hook is replaced by the adapter."""
import re
import uuid
import math


SPAN_NAMES = {
    1: 'pulse', 2: 'parameter_resolution', 3: 'note_production',
    4: 'midi_write', 5: 'delay_callback', 6: 'delayed_group_dispatch',
}


def _distribution(values):
    ordered = sorted(values)
    def percentile(percent):
        return ordered[(len(ordered) * percent + 99) // 100 - 1]
    return {'count': len(ordered), 'p50': percentile(50), 'p95': percentile(95),
            'p99': percentile(99), 'maximum': ordered[-1]}


def summarize_snapshot(snapshot):
    """Validate schema-1 diagnostic spans and summarize them without causal claims.

    Context is only hook-local diagnostic context, as documented by the checkpoint;
    it is never promoted to a musical occurrence identity or an intended timeline.
    """
    if not isinstance(snapshot, dict) or snapshot.get('schema_version') != 1:
        raise ValueError('unknown probe schema')
    capacity, count, dropped, records = (snapshot.get(name) for name in ('capacity', 'count', 'dropped', 'records'))
    if type(capacity) is not int or capacity < 1 or type(count) is not int or not 0 <= count <= capacity:
        raise ValueError('invalid probe capacity/count')
    if type(dropped) is not int or dropped < 0:
        raise ValueError('invalid probe drops')
    if dropped:
        raise ValueError('drops invalidate probe diagnostics')
    if type(records) is not list or len(records) != count:
        raise ValueError('invalid probe records')
    spans, lateness, stack, previous_time = {}, {}, [], None
    for row in records:
        if type(row) not in (list, tuple) or len(row) != 8:
            raise ValueError('invalid probe row')
        timestamp, kind, pulse, context, deadline, boundary, bytes_count, batches = row
        if type(timestamp) not in (int, float) or type(deadline) not in (int, float) or not math.isfinite(timestamp) or not math.isfinite(deadline):
            raise ValueError('invalid probe time')
        if previous_time is not None and timestamp < previous_time:
            raise ValueError('time ordering is invalid')
        previous_time = timestamp
        if type(kind) is not int or kind not in SPAN_NAMES:
            raise ValueError('unknown probe kind')
        if any(type(value) is not int for value in (pulse, context, boundary, bytes_count, batches)):
            raise ValueError('invalid probe fields')
        if boundary not in (1, 2) or bytes_count < 0 or batches < 0:
            raise ValueError('invalid probe boundary')
        signature = (kind, pulse, context, deadline)
        if boundary == 1:
            stack.append((signature, timestamp))
            continue
        if not stack:
            raise ValueError('wrong end boundary')
        expected, began = stack.pop()
        if signature != expected:
            raise ValueError('wrong end boundary')
        duration = timestamp - began
        if duration < 0:
            raise ValueError('time ordering is invalid')
        name = SPAN_NAMES[kind]
        spans.setdefault(name, []).append(duration)
        if deadline:
            lateness.setdefault(name, []).append(began - deadline)
    if stack:
        raise ValueError('missing end boundary')
    if not spans.get('pulse'):
        raise ValueError('missing pulse span')
    return {
        'schema_version': 1, 'capacity': capacity, 'count': count,
        'span_counts': {name: len(values) for name, values in spans.items()},
        'duration_seconds': {name: _distribution(values) for name, values in spans.items()},
        'lateness_seconds': {name: _distribution(values) for name, values in lateness.items()},
    }


def correlate_deadlines(snapshot):
    """Describe deadline overlap with recorded pulse work; never infer causation.

    Pulse occupancy is half-open. Coverage is the inclusive capture extent; zero
    deadlines are the schema's unavailable sentinel. This is offline analysis.
    """
    from bisect import bisect_right
    summarize_snapshot(snapshot)
    stack, pulses, dispatches = [], [], []
    for row in snapshot['records']:
        if row[5] == 1:
            stack.append(row)
        else:
            began = stack.pop()  # Pair integrity was checked above.
            if row[1] == 1 and began[0] < row[0]:
                pulses.append((began[0], row[0]))
            elif row[1] == 6:
                dispatches.append((began[0], began[4]))
    # Merge possible nested/adjacent pulse spans before binary-searching them.
    occupied = []
    for first, last in sorted(pulses):
        if occupied and first <= occupied[-1][1]:
            occupied[-1] = (occupied[-1][0], max(last, occupied[-1][1]))
        else:
            occupied.append((first, last))
    starts = [span[0] for span in occupied]
    coverage = (snapshot['records'][0][0], snapshot['records'][-1][0])
    groups = {name: [] for name in ('during_pulse_work', 'between_pulses', 'outside_capture')}
    unavailable = 0
    for sent, deadline in dispatches:
        if deadline == 0:
            unavailable += 1
            continue
        index = bisect_right(starts, deadline) - 1
        if not coverage[0] <= deadline <= coverage[1]:
            name = 'outside_capture'
        elif index >= 0 and deadline < occupied[index][1]:
            name = 'during_pulse_work'
        else:
            name = 'between_pulses'
        groups[name].append(sent - deadline)
    classes = {name: {'count': len(values), 'lateness_seconds': _distribution(values) if values else None}
               for name, values in groups.items()}
    classes['deadline_unavailable'] = {'count': unavailable, 'lateness_seconds': None}
    return {'diagnostic_only': True, 'classes': classes,
            'limitation': 'Overlap is association only; probe overhead and dispatch-to-wire delay are not removed.'}


def correlate_callback_deadlines(snapshot):
    """Describe core-profile callback deadlines and enclosed write durations.

    The callback records only its first due group deadline.  This remains a
    callback-level dispatch observation, never a group or musical-occurrence
    identity and never evidence that pulse overlap caused lateness.
    """
    from bisect import bisect_right
    summarize_snapshot(snapshot)
    if any(row[1] not in (1, 4, 5) for row in snapshot['records']):
        raise ValueError('callback correlation requires pulse-core-v1 kinds')
    stack, spans, callbacks = [], [], []
    for row in snapshot['records']:
        if row[5] == 1:
            stack.append({'row': row, 'write_durations': []})
        else:
            entry = stack.pop()  # summarize_snapshot already checked pairing.
            began = entry['row']
            span = {'kind': row[1], 'began': began[0], 'ended': row[0],
                    'deadline': began[4], 'duration': row[0] - began[0]}
            spans.append(span)
            if span['kind'] == 4:
                # Timestamps may be equal after capture rounding. The record
                # stack preserves the actual nesting and gives a write to only
                # its innermost callback, even if callbacks nest.
                for parent in reversed(stack):
                    if parent['row'][1] == 5:
                        parent['write_durations'].append(span['duration'])
                        break
            elif span['kind'] == 5:
                span['write_durations'] = entry['write_durations']
                callbacks.append(span)
    pulses = [(span['began'], span['ended']) for span in spans
              if span['kind'] == 1 and span['began'] < span['ended']]
    occupied = []
    for first, last in sorted(pulses):
        if occupied and first <= occupied[-1][1]:
            occupied[-1] = (occupied[-1][0], max(last, occupied[-1][1]))
        else:
            occupied.append((first, last))
    starts = [span[0] for span in occupied]
    coverage = (snapshot['records'][0][0], snapshot['records'][-1][0])
    classes = {name: {'lateness': [], 'write_durations': []}
               for name in ('during_pulse_work', 'between_pulses', 'outside_capture')}
    unavailable = {'count': 0, 'write_durations': []}
    for callback in callbacks:
        enclosed_writes = callback['write_durations']
        deadline = callback['deadline']
        if deadline == 0:
            unavailable['count'] += 1
            unavailable['write_durations'].extend(enclosed_writes)
            continue
        index = bisect_right(starts, deadline) - 1
        if not coverage[0] <= deadline <= coverage[1]:
            name = 'outside_capture'
        elif index >= 0 and deadline < occupied[index][1]:
            name = 'during_pulse_work'
        else:
            name = 'between_pulses'
        classes[name]['lateness'].append(callback['began'] - deadline)
        classes[name]['write_durations'].extend(enclosed_writes)
    result_classes = {
        name: {'count': len(values['lateness']),
               'callback_lateness_seconds': _distribution(values['lateness']) if values['lateness'] else None,
               'write_duration_seconds': _distribution(values['write_durations']) if values['write_durations'] else None}
        for name, values in classes.items()
    }
    result_classes['deadline_unavailable'] = {
        'count': unavailable['count'], 'callback_lateness_seconds': None,
        'write_duration_seconds': _distribution(unavailable['write_durations']) if unavailable['write_durations'] else None,
    }
    return {'diagnostic_only': True, 'classes': result_classes,
            'limitation': 'This is callback-level association only, not a group or musical-occurrence identity; overlap does not establish causation.'}


class PulseProbe:
    def __init__(self, maiden, capacity=65536, mode='pulse-v1'):
        if type(capacity) is not int or not 1 <= capacity <= 262144:
            raise ValueError('Probe capacity must be an integer in 1..262144')
        if mode not in ('pulse-v1', 'pulse-core-v1'):
            raise ValueError('Unknown pulse probe mode')
        self.maiden, self.capacity, self.installed = maiden, capacity, False
        self.mode = mode
        self.owner = uuid.uuid4().hex
        self.raw_replies = []

    def _eval(self, source):
        output = self.maiden.eval(source)
        if output:self.raw_replies.append(output)
        return output

    def install(self):
        # Arm ownership before eval: a lost reply must still trigger cleanup.
        self.installed = True
        try:
            kinds = ',kinds={[1]=true,[4]=true,[5]=true}' if self.mode == 'pulse-core-v1' else ''
            self._eval("assert(not _G.mosaic_pulse_probe,'pulse probe already installed'); "
                             "_G.mosaic_pulse_probe=include('mosaic/lib/clock/timing_probe').new({capacity=%d,now=util.time%s}); "
                             "_G.mosaic_pulse_probe.owner='%s'" % (self.capacity, kinds, self.owner))
        except Exception:
            # Also handles a lost response after installation; never remove another owner.
            self.remove()
            raise
        return self

    def reset(self):
        if not self.installed:
            raise RuntimeError('Pulse probe not installed')
        self._eval("assert(_G.mosaic_pulse_probe,'pulse probe missing'); _G.mosaic_pulse_probe:reset()")

    def snapshot(self):
        if not self.installed:
            raise RuntimeError('Pulse probe not installed')
        output = self._eval("assert(_G.mosaic_pulse_probe,'pulse probe missing'); _G.mosaic_pulse_probe:pause(); local s=_G.mosaic_pulse_probe:snapshot(1,0); print(string.format('__MOSAIC_PULSE_PROBE_META__%d|%d|%d|%d',s.schema_version,s.capacity,s.count,s.dropped))")
        match = re.search(r'__MOSAIC_PULSE_PROBE_META__(\d+)\|(\d+)\|(\d+)\|(\d+)', output)
        if not match:
            raise RuntimeError('Pulse probe snapshot missing')
        version, capacity, count, dropped = map(int, match.groups())
        if version != 1 or capacity != self.capacity or count > capacity:
            raise RuntimeError('Invalid pulse probe snapshot')
        records = []
        for first in range(1, count+1, 128):
            output = self._eval("local s=_G.mosaic_pulse_probe:snapshot(%d,128); for _,r in ipairs(s.records) do print(string.format('__MOSAIC_PULSE_PROBE_ROW__%%.0f|%%d|%%d|%%d|%%.0f|%%d|%%d|%%d',r[1]*1000000,r[2],r[3],r[4],r[5]*1000000,r[6],r[7],r[8])) end" % first)
            rows = re.findall(r'__MOSAIC_PULSE_PROBE_ROW__([^\r\n]*)', output)
            if len(rows) != min(128, count-first+1):
                raise RuntimeError('Pulse probe row count mismatch')
            for row in rows:
                if not re.fullmatch(r'-?\d+(?:\|-?\d+){7}', row):
                    raise RuntimeError('Pulse probe invalid row')
                values = list(map(int, row.split('|')))
                values[0] /= 1_000_000
                values[4] /= 1_000_000
                records.append(values)
        return dict(schema_version=version,capacity=capacity,count=count,dropped=dropped,records=records)

    def remove(self):
        if self.installed:
            self._eval("if _G.mosaic_pulse_probe and _G.mosaic_pulse_probe.owner=='%s' then _G.mosaic_pulse_probe=nil end" % self.owner)
            self.installed = False

    def __enter__(self):
        return self.install()

    def __exit__(self, *exc):
        self.remove()

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


class PulseProbe:
    def __init__(self, maiden, capacity=65536):
        if type(capacity) is not int or not 1 <= capacity <= 262144:
            raise ValueError('Probe capacity must be an integer in 1..262144')
        self.maiden, self.capacity, self.installed = maiden, capacity, False
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
            self._eval("assert(not _G.mosaic_pulse_probe,'pulse probe already installed'); "
                             "_G.mosaic_pulse_probe=include('mosaic/lib/clock/timing_probe').new({capacity=%d,now=util.time}); "
                             "_G.mosaic_pulse_probe.owner='%s'" % (self.capacity, self.owner))
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

"""PERF-004 constrained input pressure against actual Mosaic.

This is deliberately a separate recipe from PERF-002/003.  It drives the
native MIDI scheduler to its documented 512-event boundary while Mosaic follows
a 100 BPM external clock, then sends 216 physical grid/key/encoder events during
that transport.  The oracles do not inspect Mosaic state: native MIDI emission,
the scheduler's delivery ledger, native action acknowledgements, and raw screen
and grid revisions must all agree.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import traceback
from pathlib import Path

BEHAVIOUR = Path(__file__).resolve().parent
REPO = BEHAVIOUR.parents[1]
sys.path.insert(0, str(BEHAVIOUR))

TICK_NS = 25_000_000  # 100 BPM external MIDI clock, 24 PPQN.
WARM_TICKS = 49
PLAY_TICKS = 200
VALID_SCHEDULE_EVENTS = 512
INPUT_ACTIONS = 216
ACK_LIMIT_NS = 100_000_000
MIDI_TOLERANCE_NS = 10_000_000
STEP_NOTES = ([60, 127], [62, 117], [64, 107], [65, 97])


def nearest_rank(values, percent):
    ordered = sorted(values)
    return ordered[(percent * len(ordered) + 99) // 100 - 1]

def assert_timing_profile(errors):
    absolute = [abs(error) for error in errors]
    assert nearest_rank(absolute, 99) <= MIDI_TOLERANCE_NS, ('p99', nearest_rank(absolute, 99))
    assert max(absolute) <= 50_000_000, ('maximum', max(absolute))
    assert abs(errors[-1]) <= 20_000_000, ('final phase', errors[-1])

def correlate_external_clock(timing_errors, delivered, origin, pulse_stride=6,
                             threshold_ns=10_000_000, residual_limit_ns=10_000_000):
    """Pair every emitted step with the external pulse that triggered it.

    This uses the scheduler ledger's intended and actual native input times. It
    does not infer a clock origin from Mosaic output, so a shared late input and
    late note cannot be mistaken for application drift.
    """
    ticks = [row for row in delivered
             if row['bytes'] == [248] and row['intended_monotonic_ns'] >= origin]
    pairs = []
    for index, output_error in enumerate(timing_errors):
        tick = ticks[index * pulse_stride]
        expected_deadline = origin + index * pulse_stride * TICK_NS
        assert tick['intended_monotonic_ns'] == expected_deadline, (
            'trigger deadline', index, tick['intended_monotonic_ns'], expected_deadline)
        input_error = tick['actual_monotonic_ns'] - tick['intended_monotonic_ns']
        pairs.append(dict(step=index, output_error_ns=output_error,
                          trigger_input_error_ns=input_error,
                          trigger_intended_monotonic_ns=tick['intended_monotonic_ns'],
                          trigger_actual_monotonic_ns=tick['actual_monotonic_ns'],
                          residual_ns=output_error - input_error))
    late = [row for row in pairs if abs(row['output_error_ns']) > threshold_ns]
    shared = [row for row in late if abs(row['residual_ns']) <= residual_limit_ns]
    return dict(pairs=pairs, late_output_count=len(late),
                shared_late_trigger_count=len(shared),
                all_late_outputs_follow_late_trigger=len(shared) == len(late))

def correlate_cgroup_throttling(clock_correlation, samples, window_ns=10_000_000):
    """Match late trigger deliveries to observed cgroup throttle-counter edges."""
    changes = []
    for previous, current in zip(samples, samples[1:]):
        if (current['throttled_periods'] > previous['throttled_periods'] or
                current['throttled_ns'] > previous['throttled_ns']):
            changes.append(current['monotonic_ns'])
    late = [row for row in clock_correlation['pairs']
            if abs(row['output_error_ns']) > MIDI_TOLERANCE_NS]
    matches = []
    for row in late:
        if changes:
            distance = min(abs(sample - row['trigger_actual_monotonic_ns']) for sample in changes)
            if distance <= window_ns:
                matches.append(dict(step=row['step'], distance_ns=distance))
    return dict(throttle_counter_edges=len(changes), late_trigger_count=len(late),
                matched_late_trigger_count=len(matches), matches=matches,
                all_late_triggers_near_throttle_edge=len(matches) == len(late))


def assert_delivery(expected, delivered):
    """Independent input oracle: every accepted packet arrives once, ordered and late."""
    assert len(delivered) == len(expected), (len(delivered), len(expected))
    lateness = []
    for index, (wanted, actual) in enumerate(zip(expected, delivered)):
        assert actual['port'] == wanted['port'], (index, wanted, actual)
        assert actual['bytes'] == wanted['bytes'], (index, wanted, actual)
        assert actual['intended_monotonic_ns'] == wanted['at_monotonic_ns'], (index, wanted, actual)
        delay = actual['actual_monotonic_ns'] - wanted['at_monotonic_ns']
        assert delay >= 0, (index, delay)
        lateness.append(delay)
    return lateness


def assert_external_phrase(emitted, origin, steps):
    """Independent score: C D E F repeats exactly on every sixth external pulse."""
    onsets = [row for row in emitted
              if row['port'] == 1 and row['bytes'][0] == 144 and row['bytes'][2] > 0 and row['bytes'][1] in (60, 62, 64, 65)]
    expected = 1 + (PLAY_TICKS - 1) // 6
    assert len(onsets) == expected, ('onset count', len(onsets), expected)
    errors = []
    for index, onset in enumerate(onsets):
        target = origin + index * 6 * TICK_NS
        wanted = [144, *STEP_NOTES[index % len(STEP_NOTES)]]
        assert onset['bytes'] == wanted, (index, onset['bytes'], wanted)
        error = onset['monotonic_ns'] - target
        errors.append(error)
    releases = [row for row in emitted
                if row['port'] == 1 and len(row['bytes']) > 1 and row['bytes'][1] in (60, 62, 64, 65) and (row['bytes'][0] == 128 or
                                          (row['bytes'][0] == 144 and row['bytes'][2] == 0))]
    assert len(releases) == len(onsets), ('release count', len(releases), len(onsets))
    return errors


def docker(*args, timeout=60, check=True):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError('docker %s: %s' % (args[0], result.stderr[-800:]))
    return result


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


class Http:
    def __init__(self, port, token, session_id):
        self.port, self.token, self.id, self.sequence = port, token, session_id, 0

    def request(self, path, payload=None, timeout=10):
        data = json.dumps(payload).encode() if payload is not None else None
        call = urllib.request.Request('http://127.0.0.1:%d%s' % (self.port, path), data=data,
            headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(call, timeout=timeout) as response:
            return json.load(response)

    def action(self, value):
        self.sequence += 1
        return self.request('/action', dict(schema_version=1, session_id=self.id,
            action_id=uuid.uuid4().hex, sequence=self.sequence, action=value))


class Controls:
    """Public, physical-style input only; no model mutation or runtime probes."""
    def __init__(self, http):
        self.http = http
        self.action_latencies_ns = []
        self.trace = []

    def action(self, value):
        started = time.monotonic_ns()
        response = self.http.action(value)
        elapsed = time.monotonic_ns() - started
        self.action_latencies_ns.append(elapsed)
        self.trace.append(value)
        return response

    def tap(self, x, y):
        self.action(dict(type='grid', x=x, y=y, state=1))
        self.action(dict(type='grid', x=x, y=y, state=0))
        time.sleep(.06)

    def key(self, n):
        self.action(dict(type='key', n=n, state=1))
        self.action(dict(type='key', n=n, state=0))
        time.sleep(.06)

    def enc(self, n, delta):
        self.action(dict(type='enc', n=n, delta=delta))
        time.sleep(.03)

    def configure_pattern(self):
        # Same documented grid/menu path used by the normal behaviour driver:
        # four trigs in pattern 1 routed to configured MIDI channel 1.
        self.tap(3, 8)
        for _ in range(4):
            self.enc(1, 2)
        self.enc(3, 2); self.key(3); self.tap(5, 8)
        for x in range(1, 5):
            self.tap(x, 4)
        self.tap(5, 8)
        for x, y in ((1, 7), (2, 6), (3, 5), (4, 4)):
            self.tap(x, y)
        self.tap(5, 8)
        for x, y in ((1, 1), (2, 2), (3, 3), (4, 4)):
            self.tap(x, y)
        self.tap(3, 8); self.tap(1, 2)
        self.action(dict(type='grid', x=1, y=4, state=1))
        self.tap(4, 4)
        self.action(dict(type='grid', x=1, y=4, state=0))

    def external_clock_port_one(self, diagnostics):
        # Actual norns parameter menu traversal.  The root position is queried
        # only to find the public CLOCK item; it does not inspect Mosaic data.
        self.key(1)
        for _ in range(4):
            self.enc(1, 2)
        self.key(3)
        roots = diagnostics['parameter_roots']
        position = next(index for index, root in enumerate(roots) if root['name'] == 'CLOCK')
        for _ in range(position):
            self.enc(2, 2)
        self.key(3)                 # CLOCK >, source = internal
        self.enc(3, 2)              # midi
        for _ in range(11):
            self.enc(2, 2)
        self.enc(3, 2)              # selected input: Emulator MIDI

    def playback_pressure(self):
        # 160 encoder, 40 grid and 16 key events.  Grid taps/combos occur in
        # even pairs, restoring the edited cells before transport ends.
        pressure_start = len(self.action_latencies_ns)
        for index in range(80):
            self.action(dict(type='enc', n=1, delta=1))
            self.action(dict(type='enc', n=1, delta=-1))
        for _ in range(12):
            self.action(dict(type='grid', x=16, y=4, state=1))
            self.action(dict(type='grid', x=16, y=4, state=0))
        for _ in range(4):
            self.action(dict(type='grid', x=15, y=4, state=1))
            self.action(dict(type='grid', x=16, y=4, state=1))
            self.action(dict(type='grid', x=16, y=4, state=0))
            self.action(dict(type='grid', x=15, y=4, state=0))
        for _ in range(8):
            self.action(dict(type='key', n=1, state=1))
            self.action(dict(type='key', n=1, state=0))
        pressure_latencies = self.action_latencies_ns[pressure_start:]
        assert len(pressure_latencies) == INPUT_ACTIONS, len(pressure_latencies)
        return pressure_latencies


def stimulus(origin):
    warm = origin - 1_250_000_000
    events = [dict(port=1, bytes=[248], at_monotonic_ns=warm + index * TICK_NS)
              for index in range(1, WARM_TICKS + 1)]
    events.append(dict(port=1, bytes=[250], at_monotonic_ns=origin))
    events += [dict(port=1, bytes=[248], at_monotonic_ns=origin + index * TICK_NS)
               for index in range(PLAY_TICKS)]
    # Chord, CC and a program message represent normal supported live traffic.
    events += [dict(port=1, bytes=message, at_monotonic_ns=origin + offset)
               for offset, message in ((40_000_000, [144, 72, 100]),
                                       (45_000_000, [144, 76, 90]),
                                       (50_000_000, [144, 79, 80]),
                                       (180_000_000, [128, 72, 0]),
                                       (185_000_000, [128, 76, 0]),
                                       (190_000_000, [128, 79, 0]),
                                       (210_000_000, [192, 5]))]
    stop = origin + PLAY_TICKS * TICK_NS + TICK_NS // 2
    events.append(dict(port=1, bytes=[252], at_monotonic_ns=stop))
    # Fill to the public 512-event ceiling with ordinary CC 1 changes, spread
    # across active transport so this is input pressure rather than one packet.
    for index in range(VALID_SCHEDULE_EVENTS - len(events)):
        events.append(dict(port=1, bytes=[176, 1, index % 128],
                           at_monotonic_ns=origin + 70_000_000 + index * 17_000_000))
    priority = {250: 0, 248: 1}
    events.sort(key=lambda row: (row['at_monotonic_ns'], priority.get(row['bytes'][0], 2)))
    assert len(events) == VALID_SCHEDULE_EVENTS
    return events, stop


def overflow(events):
    value = list(events)
    value.append(dict(events[-1], at_monotonic_ns=events[-1]['at_monotonic_ns'] + TICK_NS))
    assert len(value) == VALID_SCHEDULE_EVENTS + 1
    return value


def wait_ready(name):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        for line in docker('logs', name, check=False).stdout.splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if value.get('status') == 'ready':
                return value
        time.sleep(.25)
    raise RuntimeError('container did not become ready')


def complete_log(name, session_id, output):
    found = docker('exec', name, 'find', '/opt/emulator/.runtime/sessions/' + session_id,
                   '-name', 'native-events.jsonl').stdout.split()
    assert len(found) == 1, found
    docker('cp', name + ':' + found[0], str(output / 'native-events.jsonl'))
    rows = [json.loads(line) for line in (output / 'native-events.jsonl').read_text().splitlines()]
    emitted = [row for row in rows if row.get('kind') == 3 and 'index' in row and 'bytes' in row]
    assert [row['index'] for row in emitted] == list(range(1, len(emitted) + 1))
    return emitted


def run_one(image, output):
    output.mkdir(parents=True, exist_ok=False)
    data = Path(tempfile.mkdtemp(prefix='perf-input-data-'))
    name = 'mosaic-perf-input-' + uuid.uuid4().hex[:10]
    image_id = docker('image', 'inspect', image, '--format', '{{.Id}}').stdout.strip()
    assert image_id.startswith('sha256:'), image_id
    result = dict(schema_version=1, workload='PERF-004', passed=False, image=image, image_id=image_id,
                  valid_schedule_events=VALID_SCHEDULE_EVENTS, physical_actions=INPUT_ACTIONS)
    started = False
    try:
        docker('run', '-d', '--name', name, '--cpus', '0.5', '--memory', '768m',
               '--memory-swap', '768m', '--cpuset-cpus', '0', '--shm-size', '256m',
               '-p', '127.0.0.1::8765', '--mount', 'type=bind,source=%s,target=/data' % data,
               '--mount', 'type=bind,source=%s,target=/code/mosaic,readonly' % REPO,
               image_id, '--script', '/code/mosaic/mosaic.lua', '--code-root', '/code')
        started = True
        ready = wait_ready(name)
        port = int(docker('port', name, '8765/tcp').stdout.strip().rsplit(':', 1)[1])
        http = Http(port, ready['token'], ready['session_id'])
        controls = Controls(http)
        controls.configure_pattern()
        controls.external_clock_port_one(http.request('/snapshot')['state']['diagnostics'])
        controls.tap(5, 8)  # trig editor: physical edits now affect real grid/frame output.
        before = http.request('/snapshot')
        recording = http.request('/performance/start', dict(period_ms=10, maximum_seconds=25))
        time.sleep(1.0)
        origin = time.monotonic_ns() + 1_750_000_000
        events, stop = stimulus(origin)
        http.action(dict(type='midi_schedule', schedule_id=4004, events=events))
        time.sleep(max(0, (origin + 600_000_000 - time.monotonic_ns()) / 1e9))
        pressure_latencies = controls.playback_pressure()
        after_controls = http.request('/snapshot')
        assert after_controls['frame_revision'] > before['frame_revision'], 'No screen propagation under input pressure'
        assert after_controls['grid_revision'] > before['grid_revision'], 'No grid propagation under input pressure'
        deadline = time.monotonic() + 12
        state = None
        while time.monotonic() < deadline:
            snapshot = http.request('/snapshot')
            state = snapshot['state']
            if (len(state['midi_input_schedule']['delivered']) == len(events) and
                    not state['midi_capture']['outstanding']):
                break
            time.sleep(.02)
        assert state is not None and len(state['midi_input_schedule']['delivered']) == len(events), 'Scheduled input did not drain'
        assert state['held'] == [], state['held']
        delivery_lateness = assert_delivery(events, state['midi_input_schedule']['delivered'])
        try:
            http.action(dict(type='midi_schedule', schedule_id=4005, events=overflow(events)))
            raise AssertionError('513-event schedule was accepted')
        except urllib.error.HTTPError as error:
            rejected = json.load(error)
            assert rejected['code'] == 'schema', rejected
        stopped = http.request('/performance/stop', {})
        samples = []
        cursor = 0
        while True:
            page = http.request('/performance/read', dict(after=cursor, limit=1000))
            samples += page['samples']; cursor = page['cursor']
            if not page['has_more']:
                break
        emitted = complete_log(name, ready['session_id'], output)
        timing_errors = assert_external_phrase(emitted, origin, PLAY_TICKS)
        p95_ack = nearest_rank(pressure_latencies, 95)
        correlation = correlate_external_clock(timing_errors,
                                                state['midi_input_schedule']['delivered'], origin)
        throttle_correlation = correlate_cgroup_throttling(correlation, samples)
        # Persist complete diagnostic evidence before applying any performance
        # gate. A failed run is the evidence that needs these artifacts most.
        write(output / 'samples.json', dict(recording=recording, status=stopped, samples=samples))
        write(output / 'recipe.json', dict(schedule=events, physical_actions=controls.trace))
        result.update(session_id=ready['session_id'], limits=recording['limits'],
                      p95_input_ack_ns=p95_ack, delivery_lateness_ns=delivery_lateness,
                      timing_errors_ns=timing_errors, external_clock_correlation=correlation,
                      cgroup_throttle_correlation=throttle_correlation,
                      frame_revisions=[before['frame_revision'], after_controls['frame_revision']],
                      grid_revisions=[before['grid_revision'], after_controls['grid_revision']],
                      rejected_flood_code=rejected['code'], sample_count=len(samples),
                      midi_messages=len(emitted))
        assert p95_ack <= ACK_LIMIT_NS, ('p95 acknowledgement', p95_ack)
        assert_timing_profile(timing_errors)
        result['passed'] = True
    except Exception as error:
        result['error'] = traceback.format_exc()
    finally:
        if started:
            (output / 'container.log').write_text(docker('logs', name, check=False).stdout)
            docker('stop', '--time', '40', name, timeout=60, check=False)
            docker('rm', name, check=False)
        shutil.rmtree(data)
        result['temporary_data_removed'] = not data.exists()
        assert result['temporary_data_removed'], data
        write(output / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='monome-emulator:perf-recorder-02')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    dirty = subprocess.check_output(['git', 'diff', 'HEAD'], cwd=REPO)
    run = run_one(args.image, output)
    report = dict(schema_version=1, workload='PERF-004', mosaic_revision=revision,
                  dirty_patch_sha256=hashlib.sha256(dirty).hexdigest() if dirty else None,
                  image=args.image, image_id=run["image_id"], run=run)
    report['passed'] = report['run']['passed']
    write(output / 'report.json', report)
    print(output / 'report.json')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

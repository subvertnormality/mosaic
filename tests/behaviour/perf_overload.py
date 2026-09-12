"""PERF-008 constrained overload and musical recovery against actual Mosaic.

The workload runs a 16-channel, 16-step project under the internal clock in the
0.5-CPU/768-MiB norns-class proxy. Four competing processes consume the same
cgroup quota for 1.5 seconds. The independent oracle requires exact per-step
MIDI groups and release ownership, phase recovery within one bar, visible grid
and screen response after overload, and resource evidence that the cgroup was
actually throttled. A constrained x86 result is not physical-norns evidence.
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
import traceback
import uuid
from collections import Counter
from pathlib import Path

BEHAVIOUR = Path(__file__).resolve().parent
REPO = BEHAVIOUR.parents[1]
sys.path.insert(0, str(BEHAVIOUR))

STEP_NS = 166_666_667                 # 90 BPM, sixteenth-note step.
CHANNELS = 16
ONE_BAR_NS = STEP_NS * 16
OVERLOAD_SECONDS = 1.5
POST_RECOVERY_SECONDS = 4.0
PHASE_P99_NS = 10_000_000
PHASE_MAX_NS = 50_000_000
PHASE_FINAL_NS = 20_000_000
FINGERPRINT = (60, 62, 64, 65)


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def docker(*args, timeout=60, check=True):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError('docker %s: %s' % (args[0], result.stderr[-800:]))
    return result


def runtime_dependencies():
    if 'MONOME_EMULATOR' not in os.environ:
        raise RuntimeError('MONOME_EMULATOR must identify the performance-capable emulator checkout')
    emulator = Path(os.environ['MONOME_EMULATOR']).resolve()
    sys.path.insert(0, str(emulator / 'src'))
    from automation.performance import (bracketing_samples, performance_metrics,
                                        throttling_deltas)
    from perf_dense import ContainerDriver, Http, build_project
    return emulator, bracketing_samples, performance_metrics, throttling_deltas, ContainerDriver, Http, build_project


def configure_fingerprint(driver):
    """Give channel 1 a C/D/E/F fingerprint through the physical note editor."""
    driver.tap(5, 8)                  # trig editor
    driver.tap(5, 8)                  # note editor
    for step in range(1, 17):
        driver.tap(step, (7, 6, 5, 4)[(step - 1) % 4])
    driver.tap(3, 8)                  # channel editor


def note_groups(events, channels=CHANNELS):
    """Require complete ordered per-step groups and exact release ownership."""
    ons = [row for row in events if len(row['bytes']) == 3 and
           row['bytes'][0] & 240 == 144 and row['bytes'][2] > 0]
    offs = [row for row in events if len(row['bytes']) == 3 and
            (row['bytes'][0] & 240 == 128 or
             (row['bytes'][0] & 240 == 144 and row['bytes'][2] == 0))]
    assert ons and len(ons) % channels == 0, ('incomplete onset group', len(ons))
    groups = [ons[index:index + channels] for index in range(0, len(ons), channels)]
    for index, group in enumerate(groups):
        statuses = [row['bytes'][0] for row in group]
        assert sorted(statuses) == list(range(144, 144 + channels)), (index, statuses)
        assert all(row['port'] == 1 and row['bytes'][2] == 100 for row in group), (index, group)
        pitches = {row['bytes'][1] for row in group}
        assert len(pitches) == 1 and next(iter(pitches)) in FINGERPRINT, (index, pitches)
    on_owners = Counter((row['port'], row['bytes'][0] & 15, row['bytes'][1]) for row in ons)
    off_owners = Counter((row['port'], row['bytes'][0] & 15, row['bytes'][1]) for row in offs)
    assert on_owners == off_owners, ('unbalanced note ownership', on_owners - off_owners,
                                     off_owners - on_owners)
    return groups


def assert_recovery(groups, overload_start_ns, overload_end_ns,
                    step_ns=STEP_NS, one_bar_ns=ONE_BAR_NS, enforce=True):
    """Anchor before overload; require exact timeline/pitch after one recovery bar."""
    assert len(groups) >= 24, len(groups)
    at = lambda group: min(row['monotonic_ns'] for row in group)
    channel_one = lambda group: next(row for row in group if row['bytes'][0] == 144)
    before = [group for group in groups if at(group) < overload_start_ns]
    assert len(before) >= 8, ('insufficient warm groups', len(before))
    origin = at(before[0])
    warm_errors = [at(group) - (origin + index * step_ns)
                   for index, group in enumerate(before)]
    assert max(map(abs, warm_errors)) <= PHASE_MAX_NS, ('warm phase', warm_errors)
    recovery_due = overload_end_ns + one_bar_ns
    recovered = []
    issues = []
    previous_ordinal = None
    for group in groups:
        onset = at(group)
        if onset < recovery_due:
            continue
        ordinal = round((onset - origin) / step_ns)
        error = onset - (origin + ordinal * step_ns)
        contiguous = previous_ordinal is None or ordinal == previous_ordinal + 1
        if not contiguous:
            issues.append(dict(kind='missing-or-duplicate-step', previous=previous_ordinal,
                               actual=ordinal))
            if enforce:
                raise AssertionError(('missing/duplicate post-recovery step',
                                      previous_ordinal, ordinal))
        expected_note = FINGERPRINT[ordinal % len(FINGERPRINT)]
        actual = channel_one(group)['bytes']
        if actual[1] != expected_note:
            issues.append(dict(kind='timeline-pitch-mismatch', ordinal=ordinal,
                               actual=actual, expected_note=expected_note))
            if enforce:
                raise AssertionError(('timeline/pitch mismatch', ordinal, actual,
                                      expected_note))
        recovered.append((ordinal, error))
        previous_ordinal = ordinal
    assert len(recovered) >= 8, ('insufficient recovered groups', len(recovered))
    errors = [error for _, error in recovered]
    ordered = sorted(abs(error) for error in errors)
    p99 = ordered[(99 * len(ordered) + 99) // 100 - 1]
    gates = dict(p99=p99 <= PHASE_P99_NS,
                 maximum=max(ordered) <= PHASE_MAX_NS,
                 final=abs(errors[-1]) <= PHASE_FINAL_NS,
                 exact_timeline=not issues)
    if enforce:
        assert gates['p99'], ('post-recovery p99', p99)
        assert gates['maximum'], ('post-recovery maximum', max(ordered))
        assert gates['final'], ('post-recovery final phase', errors[-1])
    return dict(origin_ns=origin, warm_errors_ns=warm_errors,
                recovery_due_ns=recovery_due,
                recovered_ordinals=[value for value, _ in recovered],
                recovered_errors_ns=errors, issues=issues,
                gates=gates, passed=all(gates.values()))


def assert_visual_recovery(before, changed):
    """A physical page input after overload must visibly reach grid and screen."""
    assert changed['grid_revision'] > before['grid_revision'], 'grid revision did not advance'
    assert changed['frame_revision'] > before['frame_revision'], 'frame revision did not advance'
    assert changed['state']['grid'] != before['state']['grid'], 'grid image did not change'
    assert changed['state']['frame']['sha256'] != before['state']['frame']['sha256'], \
        'screen image did not change'
    return dict(grid_revisions=[before['grid_revision'], changed['grid_revision']],
                frame_revisions=[before['frame_revision'], changed['frame_revision']],
                frame_hashes=[before['state']['frame']['sha256'],
                              changed['state']['frame']['sha256']])


def cpu_pressure(name, seconds=OVERLOAD_SECONDS, workers=4):
    code = ("import multiprocessing,time\n"
            "def burn(deadline):\n"
            " x=1\n"
            " while time.monotonic()<deadline: x=(x*1103515245+12345)&0x7fffffff\n"
            "deadline=time.monotonic()+%r\n"
            "ps=[multiprocessing.Process(target=burn,args=(deadline,)) for _ in range(%d)]\n"
            "[p.start() for p in ps]\n"
            "[p.join() for p in ps]\n" % (seconds, workers))
    return docker('exec', name, 'python3', '-c', code, timeout=seconds + 15)


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
    (_, bracketing_samples, performance_metrics, throttling_deltas,
     ContainerDriver, Http, build_project) = runtime_dependencies()
    output.mkdir(parents=True, exist_ok=False)
    data = Path(tempfile.mkdtemp(prefix='perf-overload-data-'))
    name = 'mosaic-perf-overload-' + uuid.uuid4().hex[:10]
    image_id = docker('image', 'inspect', image, '--format', '{{.Id}}').stdout.strip()
    assert image_id.startswith('sha256:'), image_id
    result = dict(schema_version=1, workload='PERF-008', passed=False,
                  image=image, image_id=image_id, channels=CHANNELS,
                  overload_seconds=OVERLOAD_SECONDS)
    started = False
    try:
        docker('run', '-d', '--name', name, '--cpus', '0.5', '--memory', '768m',
               '--memory-swap', '768m', '--cpuset-cpus', '0', '--shm-size', '256m',
               '-p', '127.0.0.1::8765', '--mount', 'type=bind,source=%s,target=/data' % data,
               '--mount', 'type=bind,source=%s,target=/code/mosaic,readonly' % REPO,
               image_id, '--script', '/code/mosaic/mosaic.lua', '--code-root', '/code')
        started = True
        deadline = time.monotonic() + 120
        ready = None
        while ready is None and time.monotonic() < deadline:
            for line in docker('logs', name, check=False).stdout.splitlines():
                try:
                    value = json.loads(line)
                except ValueError:
                    continue
                if value.get('status') == 'ready':
                    ready = value
            if ready is None:
                time.sleep(.25)
        if ready is None:
            raise RuntimeError('container did not become ready')
        port = int(docker('port', name, '8765/tcp').stdout.strip().rsplit(':', 1)[1])
        http = Http(port, ready['token'], ready['session_id'])
        driver = ContainerDriver(output, http)
        build_project(driver, CHANNELS)
        configure_fingerprint(driver)
        recording = http.request('/performance/start', dict(period_ms=10, maximum_seconds=25))
        time.sleep(1)
        marker = http.observe()['state']['midi_count']
        http.action(dict(type='grid', x=1, y=8, state=1))
        http.action(dict(type='grid', x=1, y=8, state=0))
        time.sleep(2.5)
        overload_start = time.monotonic_ns()
        cpu_pressure(name)
        overload_end = time.monotonic_ns()
        before_visual = http.request('/snapshot')
        http.action(dict(type='grid', x=5, y=8, state=1))
        http.action(dict(type='grid', x=5, y=8, state=0))
        time.sleep(.15)
        changed_visual = http.request('/snapshot')
        visual = assert_visual_recovery(before_visual, changed_visual)
        http.action(dict(type='grid', x=3, y=8, state=1))
        http.action(dict(type='grid', x=3, y=8, state=0))
        time.sleep(POST_RECOVERY_SECONDS)
        http.action(dict(type='grid', x=1, y=8, state=1))
        http.action(dict(type='grid', x=1, y=8, state=0))
        time.sleep(1)
        final = http.observe()['state']
        assert not final['midi_capture']['outstanding'], final['midi_capture']['outstanding']
        http.request('/performance/stop', {})
        samples = []
        cursor = 0
        while True:
            page = http.request('/performance/read', dict(after=cursor, limit=1000))
            samples += page['samples']
            cursor = page['cursor']
            if not page['has_more']:
                break
        emitted = [row for row in complete_log(name, ready['session_id'], output)
                   if row['index'] > marker]
        groups = note_groups(emitted)
        recovery = assert_recovery(groups, overload_start, overload_end, enforce=False)
        errors = recovery['recovered_errors_ns']
        service = [group[-1]['monotonic_ns'] - group[0]['monotonic_ns'] for group in groups]
        metrics = performance_metrics(samples, errors, service, len(emitted), STEP_NS,
                                      quiet_queue_depth=0, overload_end_ns=overload_end,
                                      one_bar_ns=ONE_BAR_NS)
        overload_samples = bracketing_samples(samples, overload_start, overload_end)
        overload_throttle = throttling_deltas(overload_samples)
        assert overload_throttle['available'] and overload_throttle['periods_delta'] > 0, \
            ('overload not demonstrated', overload_throttle)
        write(output / 'samples.json', dict(recording=recording, samples=samples))
        result.update(passed=bool(metrics['passed'] and recovery['passed']), session_id=ready['session_id'],
                      limits=recording['limits'], onset_groups=len(groups),
                      midi_messages=len(emitted), overload_start_ns=overload_start,
                      overload_end_ns=overload_end, overload_elapsed_ns=overload_end-overload_start,
                      overload_throttling=overload_throttle, recovery=recovery,
                      visual_recovery=visual, metrics=metrics)
    except Exception:
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
    report = dict(schema_version=1, workload='PERF-008', mosaic_revision=revision,
                  dirty_patch_sha256=hashlib.sha256(dirty).hexdigest() if dirty else None,
                  runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  source_status=subprocess.check_output(
                      ['git', 'status', '--porcelain', '--untracked-files=all'], cwd=REPO,
                      text=True).splitlines(),
                  image=args.image, image_id=run['image_id'], run=run, passed=run['passed'])
    write(output / 'report.json', report)
    print(output / 'report.json')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

"""PERF-006 partial: constrained normal-storage named save/load evidence.
This runs one ordinary named-save/load recipe in the same 0.5-CPU, 768-MiB
norns-class proxy as the other performance diagnostics. It is not slow-storage
fault injection or the full PERF-006 matrix, and defines no speed threshold.

    MONOME_EMULATOR=/path/to/performance-integration python3 \
      tests/behaviour/perf_storage.py --image sha256:<immutable-image-id> \
      --output ../mosaic-behaviour-runs/perf-storage-<name>
"""
import argparse
import hashlib
import json
import os
import sys
import subprocess
import time
import traceback
import urllib.error
import uuid
from pathlib import Path

BEHAVIOUR = Path(__file__).resolve().parent
REPO = BEHAVIOUR.parents[1]
EMULATOR = Path(os.environ['MONOME_EMULATOR']).resolve()
sys.path.insert(0, str(EMULATOR / 'src'))
sys.path.insert(0, str(BEHAVIOUR))

from automation.identity import application_identity, source_identity
from automation.performance import throttling_deltas
from named_save import named_save_load
from perf_dense import ContainerDriver, Http, docker

MIB = 1024 * 1024


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host_identity():
    current = EMULATOR / '.runtime/current.json'
    if not current.is_file():
        raise RuntimeError('Missing runtime identity: ' + str(current))
    # application_identity includes untracked files, including this runner.
    return dict(mosaic_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
                emulator_source=source_identity(),
                runtime_current_sha256=sha256(current),
                runtime_current=json.loads(current.read_text()),
                mosaic_application=application_identity(REPO))


def assert_limits(limits):
    assert limits['cpu_quota_us'] * 2 == limits['cpu_period_us'], limits
    assert limits['memory_limit_bytes'] == 768 * MIB, limits
    assert limits['cpuset_cpus'] == '0', limits


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


def read_samples(http):
    samples, cursor = [], 0
    while True:
        page = http.request('/performance/read', dict(after=cursor, limit=1000))
        samples += page['samples']
        cursor = page['cursor']
        if not page['has_more']:
            assert page['status'] == 'stopped' and page['error'] is None, page
            assert [row['sequence'] for row in samples] == list(range(1, len(samples) + 1)), samples
            assert len(samples) >= 2, 'Too few resource samples'
            assert all(b['monotonic_ns'] > a['monotonic_ns'] for a, b in zip(samples, samples[1:])), samples
            return samples


def export_native(name, session_id, output):
    """Retain non-secret native logs/exports before owned cleanup."""
    session = '/opt/emulator/.runtime/sessions/' + session_id
    native = output / 'native'
    native.mkdir()
    found = docker('exec', name, 'find', session, '-maxdepth', '1', '-type', 'f',
                   '(', '-name', '*.log', '-o', '-name', '*.jsonl', '-o',
                   '-name', 'cleanup.json', '-o', '-name', 'cleanup-error.json',
                   '-o', '-name', 'native-config.json', '-o', '-name', 'stopped.json', ')').stdout.splitlines()
    if not found:
        raise RuntimeError('No native exports found for session ' + session_id)
    for source in found:
        docker('cp', name + ':' + source, str(native / Path(source).name))
    events = native / 'native-events.jsonl'
    if not events.is_file():
        raise RuntimeError('Native event export missing')
    return dict(files=sorted(path.name for path in native.iterdir()),
                native_events_sha256=sha256(events))


def run_one(image, output):
    output.mkdir(parents=True, exist_ok=False)
    data_root = output / 'data'
    data_root.mkdir()
    name = 'mosaic-perf-storage-' + uuid.uuid4().hex[:10]
    image_id = docker('image', 'inspect', image, '--format', '{{.Id}}').stdout.strip()
    if not image_id.startswith('sha256:'):
        raise RuntimeError('Image inspection returned no immutable ID: ' + image_id)
    identity_before = host_identity()
    result = dict(
        schema_version=1, workload='PERF-006-partial-normal-storage-save-load',
        scope='One normal bind-mounted named save/load recipe; not slow-storage fault injection or the full PERF-006 matrix.',
        performance_gates='None: samples are retained measurements, not storage-speed thresholds.',
        passed=False, image=image, image_id=image_id, container_name=name,
        limits_requested=dict(cpus='0.5', memory='768m', memory_swap='768m', cpuset_cpus='0'),
        source_identity_before=identity_before)
    started = recorder_started = False
    driver = http = ready = None
    try:
        docker('run', '-d', '--name', name, '--cpus', '0.5', '--memory', '768m',
               '--memory-swap', '768m', '--cpuset-cpus', '0', '--shm-size', '256m',
               '-p', '127.0.0.1::8765', '--mount', 'type=bind,source=%s,target=/data' % data_root,
               '--mount', 'type=bind,source=%s,target=/code/mosaic,readonly' % REPO,
               image_id, '--script', '/code/mosaic/mosaic.lua', '--code-root', '/code')
        started = True
        ready = wait_ready(name)
        session_data = Path(ready['data'])
        try:
            relative = session_data.relative_to('/data')
        except ValueError as error:
            raise RuntimeError('Ready data path escapes /data: ' + str(session_data)) from error
        host_data = data_root / relative
        assert host_data.is_dir() and host_data.name == ready['session_id'], (ready['data'], str(host_data))
        result['data_mapping'] = dict(container_data=ready['data'], host_data=str(host_data),
                                      session_id=ready['session_id'])
        port = int(docker('port', name, '8765/tcp').stdout.strip().rsplit(':', 1)[1])
        http = Http(port, ready['token'], ready['session_id'])
        driver = ContainerDriver(output, http)
        driver.data_directory = host_data / 'mosaic'
        assert driver.data_directory.is_dir(), ('Mosaic data directory missing', str(driver.data_directory))
        write(output / 'setup-snapshot.json', http.observe())
        recording = http.request('/performance/start', dict(period_ms=10, maximum_seconds=600))
        assert_limits(recording['limits'])
        result['recording'] = recording
        recorder_started = True
        recipe_started_ns = time.monotonic_ns()
        named_save_load(driver)
        recipe_finished_ns = time.monotonic_ns()
        final_snapshot = http.observe()
        write(output / 'final-snapshot.json', final_snapshot)
        assert not final_snapshot['state']['midi_capture']['outstanding'], final_snapshot['state']['midi_capture']['outstanding']
        stopped = http.request('/performance/stop', {})
        recorder_started = False
        assert stopped['status'] == 'stopped' and stopped['error'] is None, stopped
        assert stopped['finished_ns'] >= recipe_finished_ns, (stopped, recipe_finished_ns)
        samples = read_samples(http)
        write(output / 'samples.json', dict(recording=recording, stopped=stopped, samples=samples))
        result.update(recipe_window_ns=dict(started=recipe_started_ns, finished=recipe_finished_ns,
                                            elapsed=recipe_finished_ns - recipe_started_ns),
                      recorder_stopped=stopped, recipe_results=driver.results,
                      resource_samples=len(samples), throttling=throttling_deltas(samples),
                      passed=True)
    except Exception as error:
        result['error'] = repr(error)[:4000]
        result['traceback'] = traceback.format_exc(limit=12)[-8000:]
        if isinstance(error, urllib.error.HTTPError):
            result['http_error_body'] = error.read().decode('utf-8', errors='replace')[:4000]
    finally:
        if recorder_started and http is not None:
            try:
                stopped = http.request('/performance/stop', {})
                result['recorder_stop_after_error'] = stopped
                samples = read_samples(http)
                write(output / 'samples.json', dict(recording=result.get('recording'), stopped=stopped, samples=samples))
            except Exception as error:
                result['recorder_cleanup_error'] = repr(error)[:2000]
        if ready is not None and started:
            try:
                result['native_exports'] = export_native(name, ready['session_id'], output)
            except Exception as error:
                result['native_export_error'] = repr(error)[:2000]
        if driver is not None:
            driver.finish()
            write(output / 'observations.json', driver.observations)
        if started:
            (output / 'container.log').write_text(docker('logs', name, check=False).stdout)
            stop_result = docker('stop', '--time', '40', name, timeout=60, check=False)
            remove_result = docker('rm', name, check=False)
            result['container_cleanup'] = dict(stop_exit=stop_result.returncode, remove_exit=remove_result.returncode)
            if stop_result.returncode or remove_result.returncode:
                result['passed'] = False
        try:
            identity_after = host_identity()
            result['source_identity_after'] = identity_after
            result['source_identity_unchanged'] = identity_after == identity_before
            assert result['source_identity_unchanged'], 'Source or default runtime identity changed during run'
        except Exception as error:
            result['source_identity_error'] = repr(error)[:2000]
        result['passed'] = bool(result.get('passed') and result.get('source_identity_unchanged') and
                                not result.get('native_export_error') and not result.get('source_identity_error'))
        write(output / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--image', required=True, help='Immutable performance-recorder image reference or ID')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = run_one(args.image, Path(args.output).resolve())
    print(Path(args.output).resolve() / 'result.json')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())

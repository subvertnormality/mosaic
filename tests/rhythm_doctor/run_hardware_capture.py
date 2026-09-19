"""Run the owned JACK capture probe on Norns without replacing its application.

Follow docs/testing/real-norns-runner.md for access and exclusive ownership.
This is capture component evidence, not an ADC or end-to-end Rhythm Doctor test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
FILES = ('tools/rhythm_doctor/rd_capture.c',
         'tests/rhythm_doctor/test_capture_injector.c',
         'tests/behaviour/rhythm_doctor_capture_hardware.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True)
    parser.add_argument('--control-path', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('evidence output must be new')
    run_id = 'mosaic-rd-capture-' + uuid.uuid4().hex
    remote = '/tmp/' + run_id
    ssh = ['ssh', '-S', args.control_path, '-o', 'BatchMode=yes',
           '-o', 'ConnectTimeout=5', args.host]

    def command(value, check=True):
        return subprocess.run(ssh + [value], text=True, capture_output=True,
                              timeout=60, check=check)

    command('test ! -e /home/we/.cache/mosaic-real-norns/active')
    device = command('uname -sm').stdout.strip()
    command('mkdir ' + shlex.quote(remote))
    identities, report, failure, cleanup = {}, None, None, None
    command_result = None
    try:
        with tempfile.TemporaryDirectory(prefix=run_id) as temporary:
            for relative in FILES:
                frozen = Path(temporary) / Path(relative).name
                frozen.write_bytes((ROOT / relative).read_bytes())
                expected = hashlib.sha256(frozen.read_bytes()).hexdigest()
                identities[relative] = expected
                subprocess.run(['scp', '-o', 'ControlPath=' + args.control_path,
                                str(frozen), args.host + ':' + remote + '/' + frozen.name],
                               check=True, capture_output=True, timeout=30)
                actual = command('sha256sum ' + shlex.quote(remote + '/' + frozen.name)).stdout.split()[0]
                if actual != expected:
                    raise RuntimeError('deployed source hash differs: ' + relative)
            result = command('cd ' + shlex.quote(remote) + ' && '
                'gcc -shared -fPIC -std=c11 -O2 -Wall -Wextra -Werror rd_capture.c -o librd_capture.so -ljack && '
                'gcc -std=c11 -O2 -Wall -Wextra -Werror test_capture_injector.c -o injector -ljack && '
                'python3 rhythm_doctor_capture_hardware.py --library ' + shlex.quote(remote + '/librd_capture.so') +
                ' --injector ' + shlex.quote(remote + '/injector') + ' --output report.json', check=False)
            command_result = dict(exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr)
            report = json.loads(command('cat ' + shlex.quote(remote + '/report.json')).stdout)
            report['command_exit_code'] = result.returncode
            report['command_stderr'] = result.stderr
            report['passed'] = report['passed'] and result.returncode == 0
    except Exception as error:
        failure = str(error)
    finally:
        names = [Path(name).name for name in FILES] + ['librd_capture.so', 'injector', 'report.json']
        try:
            command('rm -f ' + ' '.join(shlex.quote(remote + '/' + name) for name in names))
            command('rmdir ' + shlex.quote(remote))
        except Exception as error:
            cleanup = str(error)
    evidence = dict(run_id=run_id, device=device, source_sha256=identities,
                    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    probe=report, command_result=command_result, failure=failure, cleanup_failure=cleanup,
                    passed=bool(report and report['passed'] and not failure and not cleanup),
                    full_feature_acceptance=False,
                    scope='physical Norns owned JACK capture component only')
    with args.output.open('x') as stream:
        json.dump(evidence, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(passed=evidence['passed'], output=str(args.output),
                          failure=failure, cleanup_failure=cleanup)))
    return int(not evidence['passed'])


if __name__ == '__main__':
    raise SystemExit(main())

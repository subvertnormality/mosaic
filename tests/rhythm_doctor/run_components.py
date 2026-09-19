"""Run RD component tests with immutable source identity and per-command logs.

This deliberately does not claim application, transcription or Norns acceptance.
Run from Linux/WSL with Lua 5.3; --native also requires GCC/JACK/aubio.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
LUA_TESTS = ('core', 'integration', 'lifecycle', 'journal', 'bank_schema', 'paint_boundaries', 'paint_transactions',
             'capture_transitions', 'assets', 'capture_controller', 'analysis_controller', 'analysis_runtime', 'analysis_transport', 'runtime',
             'runtime_paint', 'runtime_persistence', 'bank_persistence', 'project_lifecycle_runtime',
             'ui_adapter', 'worker_host', 'app_surface')
PYTHON_TESTS = ('quality', 'quality_report', 'performance', 'corpus', 'rendered_corpus_audit',
                'acquisition_quality', 'grid_quality', 'native_transport', 'analysis_worker_ipc',
                'pretrained_bass_backend', 'hardware_core_runner', 'documentation')
NATIVE_TESTS = ('capture_contract', 'capture_native', 'tempo_candidate', 'tempo_native')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--detector', action='store_true')
    parser.add_argument('--analysis-python', default=sys.executable,
                        help='interpreter with pinned detector dependencies')
    parser.add_argument('--tempo-corpus', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    paths = list((ROOT/'lib/rhythm_doctor').glob('*.lua'))
    paths += list((ROOT/'tests/rhythm_doctor').glob('*.py'))
    paths += list((ROOT/'tests/rhythm_doctor').glob('*.lua'))
    paths += list((ROOT/'tests/rhythm_doctor').glob('*.c'))
    for folder in ('rhythm_doctor', 'rhythm_doctor_tempo', 'rhythm_doctor_analysis'):
        paths += [p for p in (ROOT/'tools'/folder).glob('*') if p.is_file()]
    identities = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in paths}
    commands = [(name, ['lua', 'tests/rhythm_doctor/test_' + name + '.lua']) for name in LUA_TESTS]
    selected = list(PYTHON_TESTS) + (list(NATIVE_TESTS) if args.native else [])
    if args.detector:
        selected.extend(('detector', 'nmf_template', 'adtof_evaluate', 'basic_pitch_adapter',
                        'audio_frontend', 'capture_worker_ipc', 'omnizart_onnx',
                         'omnizart_onnx_backend', 'pretrained_bass_runtime', 'pretrained_runtime_factory',
                         'pretrained_composite_backend', 'dsp_drum_backend', 'build_scheduled',
                         'pretrained_corpus_evaluate'))
    if args.tempo_corpus:
        selected.append('tempo_corpus')
    detector_tests = {'detector', 'nmf_template', 'adtof_evaluate', 'basic_pitch_adapter', 'audio_frontend',
                      'omnizart_onnx', 'omnizart_onnx_backend', 'pretrained_bass_runtime', 'pretrained_runtime_factory',
                      'pretrained_composite_backend', 'dsp_drum_backend', 'build_scheduled', 'pretrained_corpus_evaluate'}
    commands += [(name, [args.analysis_python if name in detector_tests else sys.executable,
                         '-m', 'unittest', 'discover', '-s',
                        'tests/rhythm_doctor', '-p', 'test_' + name + '.py', '-v'])
                 for name in selected]
    results = []
    for name, command in commands:
        start = time.monotonic()
        try:
            process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=180)
            output = process.stdout + process.stderr
            code = process.returncode
        except (OSError, subprocess.TimeoutExpired) as error:
            output, code = str(error), -1
        (args.output/(name+'.log')).write_text(output)
        skipped = 'skipped=' in output or 'Ran 0 tests' in output
        results.append(dict(name=name, command=command, exit_code=code, skipped=skipped,
                            elapsed_seconds=time.monotonic()-start, passed=code == 0 and not skipped))
        print(name + ': ' + ('PASS' if results[-1]['passed'] else 'FAIL'), flush=True)
    changed = [name for name, digest in identities.items()
               if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest]
    report = dict(passed=all(r['passed'] for r in results) and not changed,
                  source_sha256=identities, changed_during_run=changed, results=results,
                  native_selected=args.native, detector_selected=args.detector,
                  tempo_corpus_selected=args.tempo_corpus,
                  full_feature_acceptance=False, scope='component tests only')
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return int(not report['passed'])


if __name__ == '__main__':
    raise SystemExit(main())

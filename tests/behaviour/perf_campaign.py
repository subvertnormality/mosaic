"""A/B performance campaign on the emulator's norns performance profile.

    MONOME_EMULATOR=/path/to/monome-emulator python3 tests/behaviour/perf_campaign.py \
        --baseline <revision-or-tree> --candidate <revision-or-tree> \
        --install <performance-profile installation.json> --profile <profile.json> \
        --cases PERF-002-HW-16,PERF-003-HW-16 --repeats 3 --output <new dir> [--lua-profile 1000]

Method (the default evidence standard for a Mosaic performance change):
* Both trees are measured with this harness (--app-root), so a baseline need not
  contain the campaign scripts.
* One Lua factor is calibrated for this host at the start (median of three
  sessions) and pinned for every run, removing per-session calibration noise.
* Repeats alternate A/B and B/A to cancel slow host drift.
* A timing change is claimed only when the per-repeat medians do not overlap.
* --lua-profile adds one instruction-sampled session per tree and case; sample
  counts are deterministic Lua work and pinpoint hot functions and lines.
Emulator results are screening evidence; confirm an accepted win on hardware
with real_norns.py performance.
"""
import argparse, json, os, re, shutil, statistics, subprocess, sys, tempfile, time
from pathlib import Path

BEHAVIOUR = Path(__file__).resolve().parent
REPO = BEHAVIOUR.parents[1]
LANE = BEHAVIOUR / 'perf_calibration_emulator.py'


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, capture_output=True, **kwargs).stdout


def resolve_tree(value, out, label):
    path = Path(value)
    if path.is_dir():
        tree = path.resolve()
    else:
        tree = out / 'trees' / label
        run(['git', 'worktree', 'add', '--detach', str(tree), value], cwd=REPO)
        if (REPO / '.gitmodules').exists():
            run(['git', '-c', 'protocol.file.allow=always', 'submodule', 'update', '--init', '--reference', str(REPO / 'lib/nb'), 'lib/nb'], cwd=tree)
    revision = run(['git', 'rev-parse', 'HEAD'], cwd=tree).strip()
    dirty = run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=tree).splitlines()
    return dict(label=label, tree=str(tree), revision=revision, dirty=dirty, worktree_created=not path.is_dir())


def pin_factor(emulator, install, profile_parameters, out):
    sys.path.insert(0, str(emulator / 'src'))
    from automation.client import Session
    from automation.performance_profile import cost_profile_string
    cost = cost_profile_string(profile_parameters)
    factors = []
    for index in range(3):
        directory = out / 'pin' / ('session-%d' % (index + 1))
        live = Session(script=emulator / 'fixtures/probes/probe-a/probe-a.lua', code_root=emulator / 'fixtures/probes',
                       experimental_install=str(install), cost_profile=cost)
        try:
            time.sleep(4)
        finally:
            live.close(directory)
        text = '\n'.join(p.read_text(errors='replace') for p in directory.rglob('matron.log'))
        match = re.search(r'emu_cost: calibrated lua_factor=([0-9.]+)', text)
        if not match:
            raise RuntimeError('host calibration did not complete; see ' + str(directory))
        factors.append(float(match.group(1)))
    pinned = statistics.median(factors)
    parameters = {k: v for k, v in profile_parameters.items()
                  if k not in ('lua_targets_us', 'reference_host_us', 'lua_kernel_weights', 'reference_lua_factor', 'calibration_bias', 'calibration_repeats')}
    parameters['lua_factor'] = round(pinned, 4)
    return dict(session_factors=factors, pinned_lua_factor=pinned, cost_parameters=parameters)


def normalise_location(key):
    """Remove per-session runtime paths so the same function matches across trees."""
    match = re.search(r'(?:^|/)code/(.+)$', key) or re.search(r'(?:^|/)(norns/lua/.+)$', key)
    if match:
        return match.group(1)
    return re.sub(r'^\.\.\.[^/]*/(?:dust/)?', '', key)


def merge_counts(rows):
    merged = {}
    for key, value in rows:
        name = normalise_location(key)
        merged[name] = merged.get(name, 0) + value
    return merged


def verdict(a, b, minimum=3):
    if len(a) < minimum or len(b) < minimum:
        return 'no-claim (fewer than %d repeats)' % minimum
    return 'improved' if max(b) < min(a) else 'regressed' if min(b) > max(a) else 'no-claim (ranges overlap)'


def window_metrics(document):
    rows = [w for w in document.get('windows', []) if w['window'] > 1 and w.get('oracle')]
    if not rows:
        return None
    pick = lambda f: statistics.median(f(w['oracle']) for w in rows)
    return dict(windows=len(rows), passed=sum(bool(w['passed']) for w in rows),
                onset_p99_ms=pick(lambda o: o['timing']['p99_ns'] / 1e6),
                final_phase_ms=pick(lambda o: abs(o['final_phase_error_ns'] or 0) / 1e6),
                service_p50_ms=pick(lambda o: o['service'].get('p50_ns', 0) / 1e6),
                service_p99_ms=pick(lambda o: o['service']['p99_ns'] / 1e6))


def lane(emulator, tree, case, output, install, extra):
    argv = [sys.executable, str(LANE), '--case', case, '--output', str(output), '--windows', '4', '--app-root', tree,
            '--experimental-install', str(install)] + extra
    result = subprocess.run(argv, env=dict(os.environ, MONOME_EMULATOR=str(emulator)), text=True, capture_output=True, timeout=1800)
    (output.parent / (output.name + '.log')).write_text(result.stdout + result.stderr)
    document = json.loads((output / 'performance.json').read_text()) if (output / 'performance.json').exists() else {'error': 'no report'}
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--install', required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--cases', default='PERF-002-HW-16,PERF-003-HW-16')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--pin-factor', type=float, help='skip host calibration and use this Lua factor')
    parser.add_argument('--lua-profile', type=int, help='instructions per sample for one profiled session per tree and case')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    emulator = Path(os.environ['MONOME_EMULATOR']).resolve()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    install = Path(args.install).resolve()
    profile = json.loads(Path(args.profile).read_text())
    trees = dict(A=resolve_tree(args.baseline, out, 'baseline'), B=resolve_tree(args.candidate, out, 'candidate'))
    if args.pin_factor:
        pin = dict(session_factors=[], pinned_lua_factor=args.pin_factor,
                   cost_parameters={**{k: v for k, v in profile['runtime']['cost_parameters'].items() if k.endswith('_call_us')}, 'lua_factor': args.pin_factor})
    else:
        pin = pin_factor(emulator, install, profile['runtime']['cost_parameters'], out)
    report = dict(schema_version=1, profile_id=profile['profile_id'], profile_version=profile['version'], emulator=str(emulator),
                  emulator_revision=run(['git', 'rev-parse', 'HEAD'], cwd=emulator).strip(), install=str(install), pin=pin,
                  harness_revision=run(['git', 'rev-parse', 'HEAD'], cwd=REPO).strip(), trees=trees, repeats=args.repeats,
                  host_loadavg_before=os.getloadavg(), cases={})
    cost = json.dumps(pin['cost_parameters'])
    for case in args.cases.split(','):
        entry = report['cases'][case] = dict(A=[], B=[])
        for repeat in range(1, args.repeats + 1):
            for label in (('A', 'B') if repeat % 2 else ('B', 'A')):
                output = out / 'runs' / case.lower() / ('%s-repeat-%d' % (label, repeat))
                output.parent.mkdir(parents=True, exist_ok=True)
                document = lane(emulator, trees[label]['tree'], case, output, install, ['--cost-parameters', cost])
                entry[label].append(dict(repeat=repeat, error=document.get('error'), metrics=window_metrics(document), path=str(output)))
        summary = {}
        for metric in ('onset_p99_ms', 'final_phase_ms', 'service_p50_ms', 'service_p99_ms'):
            a = [r['metrics'][metric] for r in entry['A'] if r['metrics']]
            b = [r['metrics'][metric] for r in entry['B'] if r['metrics']]
            if len(a) == args.repeats and len(b) == args.repeats:
                change = (statistics.median(b) / statistics.median(a) - 1) if statistics.median(a) else None
                summary[metric] = dict(A=a, B=b, median_change=change, verdict=verdict(a, b))
        entry['summary'] = summary
        entry['pass_counts'] = {label: [r['metrics']['passed'] if r['metrics'] else None for r in entry[label]] for label in 'AB'}
        if args.lua_profile:
            profiles = {}
            for label in 'AB':
                output = out / 'profiles' / case.lower() / label
                output.parent.mkdir(parents=True, exist_ok=True)
                lane(emulator, trees[label]['tree'], case, output, install, ['--lua-profile', str(args.lua_profile)])
                path = output / 'lua-profile-windows.json'
                profiles[label] = json.loads(path.read_text()) if path.exists() else None
            if profiles['A'] and profiles['B']:
                a_functions, b_functions = merge_counts(profiles['A']['functions']), merge_counts(profiles['B']['functions'])
                keys = sorted(set(a_functions) | set(b_functions), key=lambda k: -max(a_functions.get(k, 0), b_functions.get(k, 0)))[:25]
                entry['lua_profile'] = dict(instructions_per_sample=args.lua_profile, samples=dict(A=profiles['A']['samples'], B=profiles['B']['samples']),
                                            sample_change=profiles['B']['samples'] / profiles['A']['samples'] - 1 if profiles['A']['samples'] else None,
                                            hot_functions=[dict(function=k, A=a_functions.get(k, 0), B=b_functions.get(k, 0)) for k in keys],
                                            hot_lines_B=sorted(merge_counts(profiles['B']['lines']).items(), key=lambda kv: -kv[1])[:25])
    report['host_loadavg_after'] = os.getloadavg()
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Performance campaign', '', 'Profile %s %s; pinned Lua factor %.3f (sessions %s).' % (report['profile_id'], report['profile_version'], pin['pinned_lua_factor'], pin['session_factors']),
             'Baseline %s, candidate %s.' % (trees['A']['revision'][:10], trees['B']['revision'][:10]), '']
    for case, entry in report['cases'].items():
        lines.append('## ' + case)
        lines.append('pass counts A %s, B %s' % (entry['pass_counts']['A'], entry['pass_counts']['B']))
        for metric, row in entry.get('summary', {}).items():
            lines.append('- %s: A %s B %s change %s -> %s' % (metric, ['%.2f' % v for v in row['A']], ['%.2f' % v for v in row['B']],
                                                            '%+.1f%%' % (100 * row['median_change']) if row['median_change'] is not None else 'n/a', row['verdict']))
        if entry.get('lua_profile'):
            p = entry['lua_profile']
            lines.append('- Lua instruction samples A %d B %d (%+.1f%%)' % (p['samples']['A'], p['samples']['B'], 100 * (p['sample_change'] or 0)))
            for row in p['hot_functions'][:10]:
                lines.append('  - %s: A %d B %d' % (row['function'], row['A'], row['B']))
        lines.append('')
    (out / 'report.md').write_text('\n'.join(lines) + '\n')
    print(out / 'report.md')
    return 0


if __name__ == '__main__':
    sys.exit(main())

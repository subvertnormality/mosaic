"""Lua mutation campaign over Mosaic's unit suite.

Generates single-token mutants of lib/**/*.lua (relational, arithmetic, logical, boolean and
integer-literal changes; strings and comments are never touched), runs the Lua unit suite
against each mutant in an isolated hard-linked copy, and records killed / survived /
timeout / invalid per mutant. Only lines the unit suite executes are mutated when a
coverage file is given (a mutant on an unexecuted line survives trivially and says nothing
new); unexecuted lines are reported separately.

    python3 tests/lua_mutation.py --out DIR [--coverage cov.tsv] [--workers 20] [module ...]

The unit copy is built like the suite's lua-units layer (tracked + untracked files, pinned
norns Lua from the emulator). Mutants are written by replacing the file, never in place, so
the hard-linked base copy is not modified.
"""
import argparse, concurrent.futures, json, os, re, shutil, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SWAPS = {'==': ['~='], '~=': ['=='], '<': ['<='], '<=': ['<'], '>': ['>='], '>=': ['>'],
         '+': ['-'], '*': ['/'], '/': ['*'], '//': ['/'], 'and': ['or'], 'or': ['and'],
         'true': ['false'], 'false': ['true']}
# Known load-sensitive unit (2 ms limit); excluded so host load cannot fake a kill.
EXCLUDE = ['test_live_slide_admission_all_channel_parameter_slots']


def tokens(src):
    """Yield (kind, start, end, text) for code tokens, skipping strings and comments."""
    i, n = 0, len(src)
    long_bracket = re.compile(r'\[(=*)\[')
    while i < n:
        c = src[i]
        if src.startswith('--', i):
            m = long_bracket.match(src, i + 2)
            if m:
                close = ']' + m.group(1) + ']'
                j = src.find(close, m.end()); i = n if j < 0 else j + len(close)
            else:
                j = src.find('\n', i); i = n if j < 0 else j
            continue
        m = long_bracket.match(src, i)
        if m:
            close = ']' + m.group(1) + ']'
            j = src.find(close, m.end()); i = n if j < 0 else j + len(close); continue
        if c in '"\'':
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == '\\' else 1
            i = j + 1; continue
        m = re.compile(r'[A-Za-z_][A-Za-z0-9_]*').match(src, i)
        if m:
            yield ('name', i, m.end(), m.group()); i = m.end(); continue
        m = re.compile(r'0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?').match(src, i)
        if m:
            yield ('number', i, m.end(), m.group()); i = m.end(); continue
        for op in ('...', '==', '~=', '<=', '>=', '//', '..', '::', '<<', '>>'):
            if src.startswith(op, i):
                yield ('op', i, i + len(op), op); i += len(op); break
        else:
            if not c.isspace():
                yield ('op', i, i + 1, c)
            i += 1


def mutants(path, lines=None):
    src = path.read_text()
    toks = list(tokens(src))
    out = []
    for k, (kind, a, b, text) in enumerate(toks):
        line = src.count('\n', 0, a) + 1
        if lines is not None and line not in lines:
            continue
        prev = toks[k - 1] if k else None
        replacements = []
        if kind == 'op' and text == '-':
            # binary minus only: after a value (name, number, closing bracket)
            if prev and (prev[0] in ('name', 'number') and prev[3] not in ('return', 'and', 'or', 'not', 'then', 'do', 'else', 'in', 'local') or prev[3] in (')', ']', '}')):
                replacements = ['+']
        elif kind in ('op', 'name') and text in SWAPS:
            replacements = SWAPS[text]
        elif kind == 'number' and re.fullmatch(r'\d+', text):
            replacements = [str(int(text) + 1)]
        for r in replacements:
            out.append(dict(file=str(path.relative_to(REPO)), line=line, col=a - src.rfind('\n', 0, a),
                            original=text, mutant=r, start=a, end=b))
    return out


def build_base(base):
    shutil.rmtree(base, ignore_errors=True)
    names = subprocess.run(['git', 'ls-files', '-z'], cwd=REPO, capture_output=True, text=True).stdout.split('\0')
    names += subprocess.run(['git', 'ls-files', '-z', '--others', '--exclude-standard'], cwd=REPO, capture_output=True, text=True).stdout.split('\0')
    for name in sorted(set(names) - {''}):
        s = REPO / name
        if s.is_file() and not name.startswith('lib/tests/test_artefacts/'):
            t = base / 'mosaic' / name; t.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(s, t)
    norns = Path(os.environ.get('MONOME_EMULATOR', '/home/andy/projects/monome-emulator-midi-clock')) / '.runtime/deps/norns/lua'
    shutil.copytree(norns, base / 'mosaic/lib/tests/test_artefacts/norns_test_artefact/lua')


def run_units(root, timeout):
    args = ['lua5.3', './run_tests.lua', '-f']
    for name in EXCLUDE: args += ['-x', name]
    try:
        r = subprocess.run(args, cwd=root / 'mosaic/lib/tests', capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 'timeout', ''
    tail = (r.stdout + r.stderr)[-600:]
    m = re.findall(r'Ran (\d+) tests in [\d.]+ seconds, (\d+) successes, (\d+) failures(?:, (\d+) errors)?', r.stdout)
    if r.returncode == 0 and m:
        return 'survived', tail
    if not m:
        return ('invalid' if ('syntax error' in tail or 'unexpected symbol' in tail) else 'killed'), tail
    return 'killed', tail


def one(job):
    mutant, base, work, timeout = job
    root = work / ('m%06d' % mutant['id'])
    subprocess.run(['cp', '-al', str(base), str(root)], check=True)
    try:
        target = root / 'mosaic' / mutant['file']
        src = target.read_text(); target.unlink()
        target.write_text(src[:mutant['start']] + mutant['mutant'] + src[mutant['end']:])
        started = time.monotonic(); status, tail = run_units(root, timeout)
        return dict(mutant, status=status, seconds=round(time.monotonic() - started, 1), tail=tail if status != 'killed' else '')
    finally:
        shutil.rmtree(root, ignore_errors=True)


def load_coverage(path):
    hits = {}
    for line in Path(path).read_text().splitlines():
        src, ls = line.split('\t'); i = src.find('/lib/')
        hits.setdefault('lib/' + src[i + 5:], set()).update(int(x) for x in ls.split(',') if x)
    return hits


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', required=True); p.add_argument('--coverage')
    p.add_argument('--workers', type=int, default=20); p.add_argument('--timeout', type=int, default=180)
    p.add_argument('--limit', type=int); p.add_argument('modules', nargs='*')
    a = p.parse_args(); out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    cov = load_coverage(a.coverage) if a.coverage else None
    files = [REPO / m for m in a.modules] if a.modules else sorted(
        f for f in (REPO / 'lib').rglob('*.lua') if not str(f.relative_to(REPO)).startswith(('lib/tests/', 'lib/nb/')))
    all_mutants, uncovered = [], {}
    for f in files:
        rel = str(f.relative_to(REPO)); lines = cov.get(rel, set()) if cov is not None else None
        found = mutants(f, lines); all_mutants += found
        if cov is not None: uncovered[rel] = len(mutants(f)) - len(found)
    for i, m in enumerate(all_mutants): m['id'] = i
    if a.limit: all_mutants = all_mutants[:a.limit]
    base = out / 'base'; build_base(base)
    status, _ = run_units(base, a.timeout)
    if status != 'survived':
        raise SystemExit('Unit suite is not green on the unmutated copy: ' + status)
    work = out / 'work'; work.mkdir(exist_ok=True)
    results = []
    with open(out / 'mutants.jsonl', 'w') as log, concurrent.futures.ThreadPoolExecutor(a.workers) as pool:
        for r in pool.map(one, [(m, base, work, a.timeout) for m in all_mutants]):
            results.append(r); log.write(json.dumps(r) + '\n'); log.flush()
            if len(results) % 100 == 0: print(json.dumps(dict(done=len(results), of=len(all_mutants))), flush=True)
    by = {}
    for r in results: by.setdefault(r['file'], {}).setdefault(r['status'], 0); by[r['file']][r['status']] += 1
    summary = dict(mutants=len(results), killed=sum(r['status'] == 'killed' for r in results),
                   survived=sum(r['status'] == 'survived' for r in results), timeout=sum(r['status'] == 'timeout' for r in results),
                   invalid=sum(r['status'] == 'invalid' for r in results), by_file=by, uncovered_mutants=uncovered)
    (out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n'); print(json.dumps({k: v for k, v in summary.items() if k not in ('by_file', 'uncovered_mutants')}))
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()

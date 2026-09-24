"""Import verified BEFORE pairs from downloaded behaviour.yml shard artifacts.

This is a provenance-preserving copy, not an acceptance or campaign-completion gate.
Only original suite.json rows are used; serial reruns cannot replace failed attempts.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath

LANES = {'controlled-experimental': 'controlled', 'real-time': 'real-time'}
EVIDENCE_NAMES = {'recipe.json', 'results.json'}
CASE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def registered_case_id(value, registry):
    require(isinstance(value, str) and CASE_ID.fullmatch(value),
            'unsafe case ID: %r' % value)
    require(value in registry, 'unregistered case ID: %r' % value)
    return value


def safe_relative(value):
    require(isinstance(value, str) and bool(value), 'unsafe path: %r' % value)
    require(not any(c in value for c in ('\\', ':', '\x00')), 'unsafe path: %r' % value)
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(p not in ('', '.', '..') for p in value.split('/')),
            'unsafe path: %r' % value)
    return Path(*path.parts)


def no_symlink(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        require(not item.is_symlink(), 'symlink is not allowed: %s' % item)
    return path


def files_under(root):
    """Do not traverse links, including links in otherwise ignored download files."""
    no_symlink(root)
    require(root.is_dir(), 'missing artifact directory: %s' % root)
    result = []
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            item = Path(folder) / name
            require(not item.is_symlink(), 'symlink is not allowed: %s' % item)
        result.extend(Path(folder) / name for name in files)
    return sorted(result)


def read_bytes(path):
    no_symlink(path)
    require(path.is_file(), 'missing evidence file: %s' % path)
    return path.read_bytes()


def decode(data, label):
    try:
        return json.loads(data)
    except (ValueError, UnicodeError) as error:
        raise ValueError('invalid JSON %s: %s' % (label, error)) from error


def object_json(data, label):
    value = decode(data, label)
    require(isinstance(value, dict), 'expected JSON object: %s' % label)
    return value


def verified_pair_files(manifest, run):
    entries = manifest.get('artifacts')
    require(isinstance(entries, list), 'missing manifest artifact list')
    listed = {}
    for entry in entries:
        require(isinstance(entry, dict), 'invalid manifest artifact entry')
        path = safe_relative(entry.get('path'))
        require(path not in listed, 'duplicate artifact path: %s' % path)
        listed[path] = entry
    evidence = {path: entry for path, entry in listed.items() if path.name in EVIDENCE_NAMES}
    recipes = {p.parent for p in evidence if p.name == 'recipe.json'}
    results = {p.parent for p in evidence if p.name == 'results.json'}
    require(recipes == results, 'unmatched recipe/results sessions in manifest')
    require(Path('.') in recipes, 'missing root recipe/results pair')
    actual = {p.relative_to(run) for p in files_under(run) if p.name in EVIDENCE_NAMES}
    require(not actual - set(evidence), 'unlisted recipe/results evidence')
    payload = {}
    for path, entry in sorted(evidence.items()):
        raw = read_bytes(run / path)
        require(type(entry.get('size')) is int and len(raw) == entry['size'],
                'evidence size mismatch: %s' % path)
        require(sha(raw) == entry.get('sha256'), 'evidence hash mismatch: %s' % path)
        value = decode(raw, path)
        require(isinstance(value, list), 'evidence must be a list: %s' % path)
        key = 'kind' if path.name == 'results.json' else 'type'
        require(all(isinstance(v, dict) and isinstance(v.get(key), str) and v[key] for v in value),
                'evidence entry missing %s: %s' % (key, path))
        payload[path] = raw
    return payload


def import_baselines(download, output, revision, source_run, cases=None, dry_run=False, registered_cases=None):
    """Validate every selected lane before writes; never merge an existing before/.

    Input must be a quiescent local artifact download, with one original suite per
    shard. The supplied run URL is an attribution label, not authenticated by this
    offline tool. No missing/failed lane becomes a baseline or a completion claim.
    """
    require(isinstance(revision, str) and re.fullmatch(r'[0-9a-f]{40}', revision),
            'source revision must be the exact full 40-character commit SHA')
    require(isinstance(source_run, str) and source_run.strip(), 'source run is required')
    download, output = no_symlink(download), no_symlink(output)
    require(download != output and download not in output.parents and output not in download.parents,
            'download and output directories must be disjoint')
    if registered_cases is None:
        from cases import CASES
        registered_cases = CASES
    registered_cases = set(registered_cases)
    requested = set(cases or [])
    for case in requested:
        registered_case_id(case, registered_cases)
    reports = [p for p in files_under(download) if p.name == 'suite.json']
    require(reports, 'no original suite.json reports found')
    planned, skipped, seen, found = [], [], set(), set()
    for report_path in reports:
        report_raw = read_bytes(report_path)
        report = object_json(report_raw, report_path)
        require(report.get('schema_version') == 1 and report.get('status') == 'finished',
                'suite report must be finished schema 1: %s' % report_path)
        identity, summary = report.get('identity'), report.get('summary')
        require(isinstance(identity, dict) and isinstance(summary, dict), 'missing suite source identity/summary')
        source = identity.get('mosaic')
        require(isinstance(source, dict), 'missing Mosaic source identity')
        require(source.get('revision') == revision, 'suite source revision mismatch: %s' % report_path)
        require(source.get('dirty_patch_sha256') == sha(b'') and source.get('untracked') == [],
                'suite source was not clean: %s' % report_path)
        require(summary.get('sources_stable') is True,
                'suite source was not stable: %s' % report_path)
        rows = report.get('cases')
        require(isinstance(rows, list), 'suite cases must be a list')
        for row in rows:
            require(isinstance(row, dict), 'invalid suite case row')
            case, clock_mode = row.get('case'), row.get('lane')
            registered_case_id(case, registered_cases)
            if requested and case not in requested:
                continue
            found.add(case)
            require(clock_mode in LANES, 'unknown lane: %r' % clock_mode)
            lane = LANES[clock_mode]
            key = (case, lane)
            require(key not in seen, 'duplicate case/lane: %s/%s' % key)
            seen.add(key)
            if row.get('passed') is not True:
                skipped.append(dict(case=case, lane=lane, reason='original suite row did not pass',
                                    suite=report_path.relative_to(download).as_posix()))
                continue
            require(row.get('returncode') == 0, 'passing row has nonzero returncode')
            # CI's absolute /tmp path is not a local path. Reconstruct only its
            # documented runs/<clock-mode>/<session>/manifest.json suffix.
            remote = row.get('manifest')
            require(isinstance(remote, str), 'missing manifest path')
            safe_relative(remote.lstrip('/'))
            parts = PurePosixPath(remote).parts
            require(parts.count('runs') == 1, 'manifest must reference original runs directory')
            relative = safe_relative('/'.join(parts[parts.index('runs'):]))
            require(len(relative.parts) == 4 and relative.parts[1] == clock_mode
                    and relative.name == 'manifest.json', 'unexpected manifest layout')
            manifest_path = report_path.parent / relative
            manifest_raw = read_bytes(manifest_path)
            require(sha(manifest_raw) == row.get('manifest_sha256'), 'manifest hash mismatch: %s' % manifest_path)
            manifest = object_json(manifest_raw, manifest_path)
            require(manifest.get('schema_version') == 1, 'unknown manifest schema')
            require(manifest.get('mosaic_revision') == revision, 'manifest source revision mismatch')
            require(manifest.get('case') == case and manifest.get('clock_mode') == clock_mode
                    and manifest.get('profile') == row.get('profile'), 'manifest case/lane/profile mismatch')
            require(manifest.get('passed') is True and manifest.get('failure') is None,
                    'manifest did not pass')
            payload = verified_pair_files(manifest, manifest_path.parent)
            target = no_symlink(output / case / lane / 'before')
            require(not target.exists(), 'existing baseline will not be overwritten: %s' % target)
            provenance = dict(schema_version=1, source_run=source_run, source_revision=revision,
                              case=case, lane=lane, clock_mode=clock_mode, profile=row.get('profile'),
                              suite=report_path.relative_to(download).as_posix(),
                              suite_sha256=sha(report_raw),
                              manifest=manifest_path.relative_to(download).as_posix(),
                              manifest_sha256=sha(manifest_raw),
                              evidence_sha256={p.as_posix(): sha(raw) for p, raw in payload.items()},
                              complete_regression_run=False)
            payload[Path('source-manifest.json')] = manifest_raw
            payload[Path('source-suite.json')] = report_raw
            payload[Path('provenance.json')] = (json.dumps(provenance, indent=2) + '\n').encode()
            planned.append((target, payload, dict(case=case, lane=lane, target=str(target))))
    require(not requested - found, 'requested case absent from reports: %s' % sorted(requested - found))
    if not dry_run:
        for target, payload, _ in planned:
            no_symlink(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            # Exclusive mkdir protects even an empty baseline. An I/O failure leaves
            # an explicit partial directory to inspect, never a replacement/retry.
            target.mkdir(exist_ok=False)
            for path, raw in payload.items():
                destination = no_symlink(target / path)
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as handle:
                    handle.write(raw)
    return dict(dry_run=dry_run, source_revision=revision, source_run=source_run,
                imported=[item for _, _, item in planned], skipped=skipped,
                complete_regression_run=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('download', type=Path, help='download directory containing shard suite.json files')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2] /
                        'docs/testing/ui-migration-baselines')
    parser.add_argument('--revision', required=True, help='full source commit SHA, never a branch or prefix')
    parser.add_argument('--source-run', required=True, help='original GitHub Actions run URL for provenance')
    parser.add_argument('--case', action='append', dest='cases', help='import only this case (repeatable)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = import_baselines(args.download, args.output, args.revision, args.source_run,
                                  cases=args.cases, dry_run=args.dry_run)
    except (ValueError, OSError) as error:
        parser.exit(1, 'Baseline import refused: %s\n' % error)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

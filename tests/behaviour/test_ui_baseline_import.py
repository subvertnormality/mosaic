"""Harness characterisation outside the manual: migration plan section 6 provenance."""
import hashlib
import json
import tempfile
import unittest
import subprocess
import sys
from pathlib import Path
import ui_baseline_import as importer

REVISION = 'a' * 40


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.download = self.root / 'download'
        self.output = self.root / 'baselines'

    def fixture(self, shard='behaviour-base-0', case='M-TEST-001',
                lane='controlled-experimental', sessions=('.',), passed=True):
        folder = self.download / shard
        run = folder / 'runs' / lane / case
        artifacts = []
        for session in sessions:
            for name, value in [('recipe.json', [{'type': 'advance', 'nanoseconds': 42}]),
                                ('results.json', [{'kind': 'notes', 'notes': [60]}])]:
                path = run / session / name
                write_json(path, value)
                artifacts.append(dict(path=path.relative_to(run).as_posix(),
                                      sha256=digest(path.read_bytes()), size=path.stat().st_size))
        manifest = run / 'manifest.json'
        write_json(manifest, dict(schema_version=1, case=case, clock_mode=lane,
                   passed=passed, failure=None if passed else {'type': 'AssertionError'},
                   mosaic_revision=REVISION, profile='base-midi', artifacts=artifacts))
        row = dict(case=case, lane=lane, profile='base-midi', passed=passed,
                   returncode=0 if passed else 1,
                   manifest='/tmp/ci/' + manifest.relative_to(folder).as_posix(),
                   manifest_sha256=digest(manifest.read_bytes()))
        report = folder / 'suite.json'
        write_json(report, dict(schema_version=1, status='finished', passed=passed,
                   complete_regression_run=False, identity={'mosaic': dict(
                       revision=REVISION, dirty_patch_sha256=digest(b''), untracked=[])},
                   summary={'sources_stable': True}, cases=[row]))
        return report, manifest

    def change_manifest(self, report, manifest, change):
        value = json.loads(manifest.read_text())
        change(value)
        write_json(manifest, value)
        suite = json.loads(report.read_text())
        suite['cases'][0]['manifest_sha256'] = digest(manifest.read_bytes())
        write_json(report, suite)

    def run_import(self, **kwargs):
        return importer.import_baselines(self.download, self.output, REVISION,
                                         'https://github.com/example/mosaic/actions/runs/123', **kwargs)

    def test_nested_sessions_and_provenance_preserved(self):
        report, manifest = self.fixture(sessions=('.', 'restarted', 'restarted/reload'))
        result = self.run_import()
        target = self.output / 'M-TEST-001/controlled/before'
        for path in manifest.parent.rglob('*.json'):
            if path.name != 'manifest.json':
                self.assertEqual((target / path.relative_to(manifest.parent)).read_bytes(), path.read_bytes())
        provenance = json.loads((target / 'provenance.json').read_text())
        self.assertEqual(provenance['source_revision'], REVISION)
        self.assertEqual(provenance['manifest_sha256'], digest(manifest.read_bytes()))
        self.assertEqual((target / 'source-manifest.json').read_bytes(), manifest.read_bytes())
        self.assertEqual((target / 'source-suite.json').read_bytes(), report.read_bytes())
        self.assertEqual(len(result['imported']), 1)
        self.assertFalse(result['complete_regression_run'])

    def test_dry_run(self):
        self.fixture()
        self.assertEqual(len(self.run_import(dry_run=True)['imported']), 1)
        self.assertFalse(self.output.exists())

    def test_failed_rows_skipped(self):
        self.fixture(passed=False)
        result = self.run_import()
        self.assertEqual(result['imported'], [])
        self.assertEqual(len(result['skipped']), 1)
        self.assertFalse(self.output.exists())

    def test_missing_or_corrupt_pair(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt):
                _, manifest = self.fixture()
                path = manifest.parent / 'results.json'
                if corrupt:
                    path.write_text('[]')
                else:
                    path.unlink()
                with self.assertRaisesRegex(ValueError, 'missing|hash|size'):
                    self.run_import()
                self.assertFalse(self.output.exists())

    def test_unmatched_manifest_session(self):
        report, manifest = self.fixture(sessions=('.', 'restarted'))
        self.change_manifest(report, manifest, lambda m: m['artifacts'].pop())
        with self.assertRaisesRegex(ValueError, 'unmatched|unlisted'):
            self.run_import()

    def test_wrong_revision(self):
        for in_manifest in (False, True):
            with self.subTest(in_manifest=in_manifest):
                report, manifest = self.fixture()
                if in_manifest:
                    self.change_manifest(report, manifest, lambda m: m.update(mosaic_revision='b' * 40))
                else:
                    value = json.loads(report.read_text())
                    value['identity']['mosaic']['revision'] = 'b' * 40
                    write_json(report, value)
                with self.assertRaisesRegex(ValueError, 'revision'):
                    self.run_import()

    def test_duplicate_case_lane(self):
        self.fixture()
        self.fixture(shard='behaviour-base-1')
        with self.assertRaisesRegex(ValueError, 'duplicate case/lane'):
            self.run_import()
        self.assertFalse(self.output.exists())

    def test_existing_baseline_even_empty(self):
        self.fixture()
        target = self.output / 'M-TEST-001/controlled/before'
        target.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'existing baseline'):
            self.run_import()
        self.assertEqual(list(target.iterdir()), [])

    def test_explicit_selection(self):
        self.fixture()
        self.fixture(shard='behaviour-base-1', case='M-OTHER-001', lane='real-time')
        target = self.output / 'M-TEST-001/controlled/before'
        target.mkdir(parents=True)
        result = self.run_import(cases=['M-OTHER-001'])
        self.assertEqual(result['imported'][0]['case'], 'M-OTHER-001')
        self.assertEqual(list(target.iterdir()), [])

    def test_manifest_hash(self):
        _, manifest = self.fixture()
        manifest.write_text(manifest.read_text() + '\n')
        with self.assertRaisesRegex(ValueError, 'manifest.*hash'):
            self.run_import()

    def test_dirty_unstable_running_report(self):
        for field in ('dirty', 'untracked', 'unstable', 'running'):
            with self.subTest(field=field):
                report, _ = self.fixture()
                value = json.loads(report.read_text())
                if field == 'dirty':
                    value['identity']['mosaic']['dirty_patch_sha256'] = 'c' * 64
                elif field == 'untracked':
                    value['identity']['mosaic']['untracked'] = ['unexpected.py']
                elif field == 'unstable':
                    value['summary']['sources_stable'] = False
                else:
                    value['status'] = 'running'
                write_json(report, value)
                with self.assertRaises(ValueError):
                    self.run_import()

    def test_unsafe_paths(self):
        for path in ('../recipe.json', '/tmp/recipe.json', 'C:/recipe.json',
                     'nested\\recipe.json', 'nested/../recipe.json', 'nested//recipe.json'):
            with self.subTest(path=path):
                report, manifest = self.fixture()
                self.change_manifest(report, manifest, lambda m: m['artifacts'][0].update(path=path))
                with self.assertRaisesRegex(ValueError, 'unsafe path'):
                    self.run_import()

    def test_source_and_destination_symlinks(self):
        _, manifest = self.fixture()
        path = manifest.parent / 'recipe.json'
        saved = self.root / 'saved.json'
        path.rename(saved)
        path.symlink_to(saved)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.run_import()
        path.unlink()
        saved.rename(path)
        outside = self.root / 'outside'
        outside.mkdir()
        self.output.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.run_import()
        self.assertEqual(list(outside.iterdir()), [])

    def test_malformed_results(self):
        for value in ({'not': 'a list'}, [{}]):
            with self.subTest(value=value):
                report, manifest = self.fixture()
                path = manifest.parent / 'results.json'
                write_json(path, value)
                self.change_manifest(report, manifest, lambda m: m['artifacts'][1].update(
                    sha256=digest(path.read_bytes()), size=path.stat().st_size))
                with self.assertRaisesRegex(ValueError, 'list|kind'):
                    self.run_import()

    def test_absent_requested_case(self):
        self.fixture()
        with self.assertRaisesRegex(ValueError, 'requested case'):
            self.run_import(cases=['M-MISSING-001'])

    def test_all_selected_lanes_validated_before_writes(self):
        self.fixture()
        _, manifest = self.fixture(shard='behaviour-base-1', case='M-OTHER-001')
        (manifest.parent / 'results.json').unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.run_import()
        self.assertFalse(self.output.exists())

    def test_profiles_and_both_lanes(self):
        self.fixture()
        for index, profile in enumerate(('base-midi', 'midi-modulation', 'nb-audio', 'crow-jf')):
            report, manifest = self.fixture(shard='profile-' + str(index),
                                            case='M-PROFILE-' + str(index), lane='real-time')
            self.change_manifest(report, manifest, lambda m: m.update(profile=profile))
            value = json.loads(report.read_text())
            value['cases'][0]['profile'] = profile
            write_json(report, value)
        result = self.run_import()
        self.assertEqual(len(result['imported']), 5)
        self.assertEqual({row['lane'] for row in result['imported']}, {'controlled', 'real-time'})

    def test_effective_retry_cannot_replace_original_failure(self):
        report, _ = self.fixture(passed=False)
        effective = json.loads(report.read_text())
        effective['cases'][0]['passed'] = True
        write_json(report.with_name('suite-effective.json'), effective)
        self.assertEqual(self.run_import()['imported'], [])
        self.assertFalse(self.output.exists())

    def test_manifest_must_independently_pass_and_identify_row(self):
        for change in ({'passed': False}, {'failure': {'type': 'error'}},
                       {'case': 'M-OTHER-001'}, {'clock_mode': 'real-time'},
                       {'profile': 'nb-audio'}):
            with self.subTest(change=change):
                report, manifest = self.fixture()
                self.change_manifest(report, manifest, lambda m: m.update(change))
                with self.assertRaisesRegex(ValueError, 'did not pass|mismatch'):
                    self.run_import()

    def test_duplicate_manifest_path_and_unlisted_pair(self):
        report, manifest = self.fixture()
        self.change_manifest(report, manifest, lambda m: m['artifacts'].append(m['artifacts'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate artifact'):
            self.run_import()
        report, manifest = self.fixture()
        write_json(manifest.parent / 'hidden/results.json', [])
        with self.assertRaisesRegex(ValueError, 'unlisted'):
            self.run_import()

    def test_cli_dry_run_and_error_exit(self):
        self.fixture()
        command = [sys.executable, importer.__file__, str(self.download), '--output', str(self.output),
                   '--revision', REVISION, '--source-run', 'https://github.com/example/mosaic/actions/runs/123']
        result = subprocess.run(command + ['--dry-run'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['dry_run'])
        self.assertFalse(self.output.exists())
        result = subprocess.run(command + ['--case', 'M-MISSING-001'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('Baseline import refused:', result.stderr)

    def test_full_revision_required_and_output_cannot_overlap_download(self):
        self.fixture()
        with self.assertRaisesRegex(ValueError, 'full 40-character'):
            importer.import_baselines(self.download, self.output, REVISION[:8], 'run')
        with self.assertRaisesRegex(ValueError, 'disjoint'):
            importer.import_baselines(self.download, self.download / 'output', REVISION, 'run')


if __name__ == '__main__':
    unittest.main()

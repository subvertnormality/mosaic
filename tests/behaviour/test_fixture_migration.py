"""Characterisation outside the manual: proposed fixture lead-identity migration."""
import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from hardware_performance import prepare_fixture
from real_norns import main as real_norns_main


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_fixture(root, *, include_legacy_lead=False, corrupt_hash=False, omit=None):
    root.mkdir()
    files = {
        'autosave.ptn': b'PTN\x00unchanged\n',
        'autosave.pset': (b'"other_parameter": 7\n'
                          + (b'"midi_lock_lead_time": 0\n' if include_legacy_lead else b'')
                          + b'"last_parameter": 9\n'),
    }
    for name, contents in files.items():
        if name != omit:
            (root / name).write_bytes(contents)
    manifest = {
        'case': 'PERF-009-HW-16',
        'files': {name: hashlib.sha256(contents).hexdigest() for name, contents in files.items()},
        'fixture_label': 'legacy input remains verbatim',
        'nested': {'keep': ['this', 2]},
    }
    if corrupt_hash:
        manifest['files']['autosave.ptn'] = '0' * 64
    if omit == 'files':
        manifest.pop('files')
    raw = json.dumps(manifest, indent=2).encode() + b'\n'
    (root / 'fixture.json').write_bytes(raw)
    return files, manifest, raw


class FixtureMigrationTests(unittest.TestCase):
    def test_migration_preserves_source_and_rebinds_only_the_requested_lead(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary); source = temporary / 'legacy'; destination = temporary / 'lead-25'
            files, original_manifest, original_manifest_bytes = make_fixture(source)
            source_before = {name: (source / name).read_bytes() for name in ('autosave.ptn', 'autosave.pset', 'fixture.json')}

            manifest = prepare_fixture(source, destination, lead_ms=25, seed=17, probe_mode='pulse-v1')

            self.assertEqual({name: (source / name).read_bytes() for name in source_before}, source_before)
            self.assertEqual((source / 'fixture.json').read_bytes(), original_manifest_bytes)
            self.assertEqual((destination / 'autosave.ptn').read_bytes(), files['autosave.ptn'])
            pset = (destination / 'autosave.pset').read_text()
            lead_lines = [line for line in pset.splitlines() if line.strip().startswith('"midi_lock_lead_time"')]
            self.assertEqual(lead_lines, ['"midi_lock_lead_time": 25'])
            self.assertEqual(manifest['midi_lock_lead_time'], 25)
            self.assertEqual(manifest['seed'], 17)
            self.assertEqual(manifest['probe_mode'], 'pulse-v1')
            self.assertEqual(manifest['migrated_from'], original_manifest)
            self.assertEqual(manifest['files'], {name: digest(destination / name) for name in ('autosave.ptn', 'autosave.pset')})
            self.assertEqual(json.loads((destination / 'fixture.json').read_text()), manifest)

    def test_existing_legacy_lead_is_replaced_not_duplicated(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary); source = temporary / 'legacy'; destination = temporary / 'lead-50'
            make_fixture(source, include_legacy_lead=True)
            prepare_fixture(source, destination, lead_ms=50)
            lines = (destination / 'autosave.pset').read_text().splitlines()
            self.assertEqual([line for line in lines if line.strip().startswith('"midi_lock_lead_time"')],
                             ['"midi_lock_lead_time": 50'])

    def test_migration_preserves_the_reduced_probe_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary); source = temporary / 'legacy'; destination = temporary / 'core-probe'
            make_fixture(source)
            manifest = prepare_fixture(source, destination, probe_mode='pulse-core-v1')
            self.assertEqual(manifest['probe_mode'], 'pulse-core-v1')

    def test_source_integrity_and_destination_boundaries_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary)
            with self.subTest('bad original hash'):
                source = temporary / 'bad-hash'; destination = temporary / 'out-hash'
                make_fixture(source, corrupt_hash=True)
                with self.assertRaises(ValueError): prepare_fixture(source, destination)
                self.assertFalse(destination.exists())
            with self.subTest('missing pset'):
                source = temporary / 'missing-pset'; destination = temporary / 'out-missing'
                make_fixture(source, omit='autosave.pset')
                with self.assertRaises(ValueError): prepare_fixture(source, destination)
            with self.subTest('manifest missing files'):
                source = temporary / 'no-files'; destination = temporary / 'out-no-files'
                make_fixture(source, omit='files')
                with self.assertRaises(ValueError): prepare_fixture(source, destination)
            with self.subTest('destination exists'):
                source = temporary / 'exists-source'; destination = temporary / 'exists-destination'
                make_fixture(source); destination.mkdir()
                with self.assertRaises(OSError): prepare_fixture(source, destination)
            with self.subTest('destination nested in source'):
                source = temporary / 'nested-source'; make_fixture(source)
                with self.assertRaises(ValueError): prepare_fixture(source, source / 'migration')

    def test_only_integer_leads_in_the_supported_range_are_accepted(self):
        for lead in (-1, 51, 25.0, True, '25'):
            with self.subTest(lead=lead), tempfile.TemporaryDirectory() as temporary:
                temporary = Path(temporary); source = temporary / 'source'; destination = temporary / 'destination'
                make_fixture(source)
                with self.assertRaises(ValueError): prepare_fixture(source, destination, lead_ms=lead)
                self.assertFalse(destination.exists())

    def test_prepare_fixture_cli_needs_no_device_or_host_and_preserves_the_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            temporary = Path(temporary); source = temporary / 'source'; destination = temporary / 'destination'
            _, _, source_manifest = make_fixture(source)
            source_pset = (source / 'autosave.pset').read_bytes()
            output = io.StringIO()
            with redirect_stdout(output):
                status = real_norns_main(['prepare-fixture', '--project-fixture', str(source),
                                          '--fixture-destination', str(destination), '--lock-lead-ms', '25'])
            self.assertEqual(status, 0)
            self.assertEqual((source / 'fixture.json').read_bytes(), source_manifest)
            self.assertEqual((source / 'autosave.pset').read_bytes(), source_pset)
            self.assertEqual(json.loads(output.getvalue())['midi_lock_lead_time'], 25)


if __name__ == '__main__':
    unittest.main()

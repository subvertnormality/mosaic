import importlib.util
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from perf_provenance import git_identity, installation_identity


class PerformanceProvenanceTests(unittest.TestCase):
    def test_git_identity_records_commit_and_all_dirty_paths(self):
        def output(command, **kwargs):
            if command[1] == 'rev-parse':
                return 'a' * 40 + '\n'
            if command[1] == 'status':
                return ' M tracked.py\n?? new.py\n'
            if command[1] == 'ls-files' and '--others' in command:
                return 'new.py\0'
            if command[1] == 'ls-files':
                return 'tracked.py\0'
            raise AssertionError(command)

        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'tracked.py').write_text('tracked')
            (root/'new.py').write_text('untracked')
            with patch('perf_provenance.subprocess.check_output', side_effect=output):
                identity=git_identity(root)
        self.assertEqual(identity['revision'], 'a' * 40)
        self.assertEqual(identity['status'], [' M tracked.py', '?? new.py'])
        self.assertEqual(identity['file_count'],2)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'tracked.py').write_text('tracked')
            (root/'new.py').write_text('untracked')
            with patch('perf_provenance.subprocess.check_output', side_effect=output):
                before=git_identity(root)
            (root/'new.py').write_text('changed')
            with patch('perf_provenance.subprocess.check_output', side_effect=output):
                after=git_identity(root)
        self.assertNotEqual(before['files_sha256'],after['files_sha256'])

    def load_perf_dense(self):
        behavior=Path(__file__).resolve().parent
        fake_package=ModuleType('automation');fake_package.__path__=[]
        fake_performance=ModuleType('automation.performance')
        fake_performance.performance_metrics=lambda *args: {}
        fake_performance.throttling_deltas=lambda *args: {}
        fake_performance.bracketing_samples=lambda *args: []
        fake_client=ModuleType('automation.client')
        fake_client.Session=object
        with patch.dict(os.environ,{'MONOME_EMULATOR':'C:/perf-provenance-test-emulator'}), \
             patch.dict(sys.modules,{'automation':fake_package,'automation.performance':fake_performance,'automation.client':fake_client}):
            spec=importlib.util.spec_from_file_location('perf_dense_provenance_test',behavior/'perf_dense.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def test_perf_dense_report_binds_source_installation_and_image(self):
        module=self.load_perf_dense()
        source=dict(revision='a'*40,status=[],files_sha256='1'*64,file_count=10)
        emulator=dict(revision='b'*40,status=[],files_sha256='2'*64,file_count=20)
        install=dict(manifest_sha256='3'*64,lock_sha256='4'*64)
        identities=[source,emulator,source,emulator]
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(module.subprocess,'check_output',return_value=b''), \
             patch.object(module,'git_identity',side_effect=identities), \
             patch.object(module,'installation_identity',return_value=install), \
             patch.object(module,'docker',return_value=SimpleNamespace(stdout='sha256:image-id')), \
             patch.object(module,'run_one',return_value={'passed':True}), \
             patch.object(sys,'argv',['perf_dense.py','--output',str(Path(directory)/'out'),
                                      '--channels','1','--repeats','1','--installation-manifest','/runtime/installation.json']):
            self.assertEqual(module.main(),0)
            report=json.loads((Path(directory)/'out/result.json').read_text())
        self.assertEqual(report['source_git'],source)
        self.assertEqual(report['source_git_after'],source)
        self.assertEqual(report['emulator_git'],emulator)
        self.assertEqual(report['emulator_git_after'],emulator)
        self.assertEqual(report['native_installation'],install)
        self.assertEqual(report['image_id'],'sha256:image-id')
        self.assertTrue(report['provenance_stable'])
        self.assertTrue(report['passed'])

    def test_perf_dense_marks_report_failed_when_source_changes(self):
        module=self.load_perf_dense()
        source=dict(revision='a'*40,status=[],files_sha256='1'*64,file_count=10)
        changed=dict(revision='a'*40,status=[' M x'],files_sha256='9'*64,file_count=10)
        emulator=dict(revision='b'*40,status=[],files_sha256='2'*64,file_count=20)
        identities=[source,emulator,changed,emulator]
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(module.subprocess,'check_output',return_value=b''), \
             patch.object(module,'git_identity',side_effect=identities), \
             patch.object(module,'installation_identity',return_value=None), \
             patch.object(module,'docker',return_value=SimpleNamespace(stdout='sha256:image-id')), \
             patch.object(module,'run_one',return_value={'passed':True}), \
             patch.object(sys,'argv',['perf_dense.py','--output',str(Path(directory)/'out'),
                                      '--channels','1','--repeats','1']):
            self.assertEqual(module.main(),1)
            report=json.loads((Path(directory)/'out/result.json').read_text())
        self.assertFalse(report['provenance_stable'])
        self.assertFalse(report['passed'])
        self.assertIn('identity changed',report['provenance_error'])

    def test_installation_identity_verifies_manifest_runtime_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'norns'
            script = source / 'lua/core/init.lua'
            script.parent.mkdir(parents=True)
            script.write_bytes(b'print(1)')
            binary = root / 'matron'
            binary.write_bytes(b'ELF-test')
            digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = root / 'installation.json'
            value = {
                'lock_sha256': 'a' * 64,
                'build_inputs_sha256': 'b' * 64,
                'norns_revision': 'c' * 40,
                'source': str(source),
                'binaries': {'matron': {'path': str(binary), 'sha256': digest(binary)}},
                'interpreted_files': {'lua/core/init.lua': digest(script)},
            }
            manifest.write_text(json.dumps(value))
            identity = installation_identity(manifest)
            self.assertEqual(identity['manifest_sha256'], digest(manifest))
            self.assertEqual(identity['norns_revision'], 'c' * 40)
            script.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'interpreted runtime file'):
                installation_identity(manifest)
            script.write_bytes(b'print(1)')
            binary.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'binary runtime file'):
                installation_identity(manifest)

    def test_missing_or_unsafe_installation_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                installation_identity(root / 'missing.json')
            manifest = root / 'installation.json'
            manifest.write_text(json.dumps({
                'lock_sha256': 'a' * 64,
                'build_inputs_sha256': 'b' * 64,
                'norns_revision': 'c' * 40,
                'source': str(root),
                'binaries': {},
                'interpreted_files': {'../escape.lua': 'd' * 64},
            }))
            with self.assertRaises(ValueError):
                installation_identity(manifest)


if __name__ == '__main__':
    unittest.main()

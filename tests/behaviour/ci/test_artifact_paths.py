"""Harness characterisation outside the manual: CI upload evidence boundaries."""
import glob
import re
import tempfile
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[3] / '.github/workflows/behaviour.yml'


def upload_patterns():
    blocks = re.findall(r'          path: \|\n((?:            .+\n)+)', WORKFLOW.read_text())
    return [[line.strip() for line in block.splitlines()]
            for block in blocks if '/runs/**/recipe.json' in block]


def selected_files(patterns, root):
    # upload-artifact@v4 follows symlinks, as does recursive glob.glob.
    selected = set()
    for pattern in patterns:
        exclude = pattern.startswith('!')
        suffix = pattern.lstrip('!').split('/', 3)[3]
        matches = {Path(p).relative_to(root).as_posix()
                   for p in glob.glob(str(root / suffix), recursive=True)
                   if Path(p).is_file()}
        if exclude:
            selected.difference_update(matches)
        else:
            selected.update(matches)
    return selected


class Tests(unittest.TestCase):
    def test_targeted_upload_retains_native_shutdown_diagnostics(self):
        blocks = re.findall(r'          path: \|\n((?:            .+\n)+)',
                            WORKFLOW.read_text())
        selected = [block for block in blocks
                    if '/tmp/mosaic-ui-targeted/targeted-ui-migration.json' in block]
        self.assertEqual(len(selected), 1)
        patterns = [line.strip() for line in selected[0].splitlines()
                    if 'mosaic-ui-targeted' in line]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run = root / 'mosaic-ui-targeted/M-TEST-001/real-time/after/session'
            native = run / 'native'
            native.mkdir(parents=True)
            for name in ('matron.log', 'crone.log', 'cleanup.json',
                         'native-events.jsonl'):
                (native / name).write_text(name)
            for folder in ('code', 'data'):
                path = run / folder
                path.mkdir()
                (path / 'private.json').write_text('private')
            for folder in ('generated-project', 'pre-policy-seed'):
                path = run / folder
                path.mkdir()
                (path / 'autosave.ptn').write_text('generated fixture')
                (path / 'autosave.pset').write_text('generated numeric fixture')
            actual = selected_files(patterns, root)
            prefix = 'mosaic-ui-targeted/M-TEST-001/real-time/after/session/'
            self.assertTrue({prefix + 'native/' + name for name in
                             ('matron.log', 'crone.log', 'cleanup.json',
                              'native-events.jsonl')} <= actual)
            self.assertEqual({name for name in actual if name.endswith('autosave.ptn')},
                             {prefix + 'generated-project/autosave.ptn',
                              prefix + 'pre-policy-seed/autosave.ptn'})
            self.assertFalse(any(name.endswith('autosave.pset') for name in actual))
            self.assertFalse(any('/code/' in name or '/data/' in name
                                 for name in actual))

    def test_uploads_root_and_nested_evidence_without_code_or_data(self):
        patterns = upload_patterns()
        self.assertEqual(len(patterns), 3)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'suite'
            source = Path(directory) / 'checkout'
            source.mkdir()
            for name in ('recipe.json', 'results.json', 'manifest.json'):
                (source / name).write_text('[]')
            expected = {'suite.json'}
            root.mkdir()
            (root / 'suite.json').write_text('{}')
            for lane in ('real-time', 'controlled-experimental'):
                run = root / 'runs' / lane / ('a' * 32)
                for session in (run, run / 'restarted/reload'):
                    session.mkdir(parents=True)
                    for name in ('recipe.json', 'results.json', 'manifest.json'):
                        path = session / name
                        path.write_text('[]')
                        expected.add(path.relative_to(root).as_posix())
                    (session / 'code').mkdir()
                    (session / 'code/mosaic').symlink_to(source, target_is_directory=True)
                    (session / 'data').mkdir()
                    for name in ('recipe.json', 'results.json', 'manifest.json'):
                        (session / 'data' / name).write_text('[]')
            for pattern in patterns:
                with self.subTest(root=pattern[0]):
                    self.assertEqual(selected_files(pattern, root), expected)


if __name__ == '__main__':
    unittest.main()

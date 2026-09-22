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

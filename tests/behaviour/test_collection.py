"""Collection must not silently select an overwritten case registration."""
import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run

class CollectionTests(unittest.TestCase):
    def test_behaviour_source_hashes_include_nested_contract_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            behaviour = root / 'tests' / 'behaviour'
            contract = behaviour / 'contract'
            contract.mkdir(parents=True)
            top_level = behaviour / 'cases.py'
            nested = contract / 'song_divisions.py'
            top_level.write_text('CASES = {}\\n')
            nested.write_text('def song_tempo_divisions(c): pass\\n')
            self.assertEqual(
                run.behaviour_source_hashes(root),
                {
                    'tests/behaviour/cases.py': run.digest(top_level),
                    'tests/behaviour/contract/song_divisions.py': run.digest(nested),
                },
            )

    def test_unique_duration_case_and_duplicate_rejection(self):
        with patch.object(sys,'argv',['run.py','--list']),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run.main(),0)
        self.assertEqual(json.loads(output.getvalue())['M-PAT-003']['requirements'],['PAT-DURATION'])
        source=(run.REPO/'tests/behaviour/cases.py').read_text()
        self.assertEqual(source.count("'M-PAT-003':dict(run=pattern_duration_domain"),1)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'tests/behaviour';path.mkdir(parents=True)
            (path/'cases.py').write_text(source.replace("'M-PAT-003':dict(run=pattern_duration_domain","'M-PAT-002':dict(run=pattern_duration_domain"))
            with patch.object(run,'REPO',root),patch.object(sys,'argv',['run.py','--list']):
                with self.assertRaisesRegex(AssertionError,'Duplicate case IDs'):
                    run.main()

if __name__=='__main__':unittest.main()

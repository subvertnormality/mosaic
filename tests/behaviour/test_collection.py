"""Collection must not silently select an overwritten case registration."""
import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import run

class CollectionTests(unittest.TestCase):
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

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

def repository_root():
 for root in (Path.cwd(),*Path(__file__).resolve().parents):
  if (root/'tools/manual_publication_verify.py').is_file() and (root/'manual/voices.lock.json').is_file():return root
 raise RuntimeError('Run this operator check from a Mosaic repository checkout')
REPO=repository_root();CANDIDATE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'tools'),str(REPO/'tests/behaviour')]
VERIFY_PATH=CANDIDATE/'source/tools/manual_publication_verify.py'
if not VERIFY_PATH.is_file():VERIFY_PATH=REPO/'tools/manual_publication_verify.py'
spec=importlib.util.spec_from_file_location('candidate_publication_verify_native',VERIFY_PATH)
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)

class PreservedNativePublicationIntegration(unittest.TestCase):
 def test_optional_preserved_native_report(self):
  report_value=os.environ.get('MOSAIC_PLAYER_APPLY_REPORT')
  if not report_value:self.skipTest('Operator-only cached check; set MOSAIC_PLAYER_APPLY_REPORT when explicitly requested')
  document=json.loads(Path(report_value).read_text())
  self.assertEqual(verify.audit_reference(document),12)

if __name__=='__main__':unittest.main(verbosity=2)

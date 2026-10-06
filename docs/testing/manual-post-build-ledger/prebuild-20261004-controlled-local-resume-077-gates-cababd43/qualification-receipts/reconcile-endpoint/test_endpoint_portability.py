import os,subprocess,unittest
from pathlib import Path
STAGE=Path(__file__).parent/'candidate'
class EndpointPortabilityTests(unittest.TestCase):
 def run_code(self,source):
  return subprocess.run(['python3','-c',source],cwd=STAGE/'tools',env=dict(os.environ,PYTHONPATH=str(STAGE/'tools')),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 def test_endpoint_imports_without_documentation_helper_path_injection(self):
  p=self.run_code("import manual_reconcile_build; print('imported')")
  self.assertEqual(p.returncode,0,p.stdout)
 def test_endpoint_root_is_parent_of_root_tools(self):
  p=self.run_code("import manual_reconcile_build as m; from pathlib import Path; assert m.ROOT==Path(m.__file__).resolve().parents[1],m.ROOT")
  self.assertEqual(p.returncode,0,p.stdout)

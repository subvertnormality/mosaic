import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
spec=importlib.util.spec_from_file_location('candidate_manual_build',ROOT/'tools/manual_build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
class BuildRegistration(unittest.TestCase):
 def test_gap_and_modulation_cases_register_exact_local_helpers(self):
  opts=SimpleNamespace(emulator='/base',audio_emulator='/audio',controlled_install='/control',audio_install='/audio-install',mod_code_root='/voices',ffmpeg='/ffmpeg',readability_real_install='/real-readability',real_install='/real',modulation_code_root='/matrix',modulation_emulator='/matrix-emulator',modulation_controlled_install='/matrix-control',browser_tests=False)
  stages=build.plan(opts,['scene-plans-native-public-gaps.yaml','scene-plans-modulation-macro.yaml'],controlled_local=True)
  gap=next(x for x in stages if x['name']=='reference-controlled-scene-plans-native-public-gaps-base-midi')
  mod=next(x for x in stages if x['name']=='reference-controlled-scene-plans-modulation-macro-midi-modulation')
  self.assertIn(str(ROOT/'tools/manual_native_public_gap_cases.py'),gap['command'])
  self.assertIn(str(ROOT/'tools/manual_extra_matrix_macro_modest.py'),mod['command'])
  self.assertIn('--mod-code-root',mod['command']);self.assertIn('/matrix',mod['command'])
  self.assertIn('--mod-patches',mod['command'])
 def test_book_registers_both_canonical_sources(self):
  text=(ROOT/'manual/book.yaml').read_text()
  self.assertIn('- scene-plans-native-public-gaps.yaml',text)
  self.assertIn('- scene-plans-modulation-macro.yaml',text)
if __name__=='__main__':unittest.main()

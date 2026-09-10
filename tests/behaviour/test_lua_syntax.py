"""Every production Lua file compiles. The Lua units load only some modules (pages are
not loaded), so a syntax error there would first surface at boot in a native session."""
import subprocess,unittest
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]

def production_lua():
    files=[REPO/'mosaic.lua']+sorted((REPO/'lib').rglob('*.lua'))
    return [f for f in files if not any(part in ('tests','nb') for part in f.relative_to(REPO).parts[:2])]

class LuaSyntaxTests(unittest.TestCase):
    def test_every_production_lua_file_compiles(self):
        files=production_lua()
        self.assertGreater(len(files),50)
        self.assertFalse(any('lib/tests/' in str(f) or '/lib/nb/' in str(f) for f in files))
        failures={}
        for f in files:
            result=subprocess.run(['luac5.3','-p',str(f)],capture_output=True,text=True)
            if result.returncode:failures[str(f.relative_to(REPO))]=result.stderr.strip()
        self.assertEqual(failures,{})
    def test_detector_reports_a_syntax_error(self):
        import tempfile
        with tempfile.NamedTemporaryFile('w',suffix='.lua',delete=False) as handle:handle.write('local x = t[1)\n')
        self.assertNotEqual(subprocess.run(['luac5.3','-p',handle.name],capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()

"""Lua unit tests are global functions: a repeated name silently replaces the earlier test."""
import collections,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'lib/tests/lib'
PATTERN=re.compile(r'\s*(?:function\s+(test_\w+)\s*\(|(test_\w+)\s*=\s*function)')

def definitions(root=ROOT):
    found=collections.defaultdict(list)
    for path in sorted(root.rglob('*.lua')):
        for number,line in enumerate(path.read_text().splitlines(),1):
            match=PATTERN.match(line)
            if match:found[match.group(1) or match.group(2)].append('%s:%d'%(path.relative_to(root),number))
    return found

class LuaTestNameTests(unittest.TestCase):
    def test_every_lua_test_name_is_defined_once(self):
        found=definitions()
        self.assertGreater(len(found),500)
        self.assertEqual({k:v for k,v in found.items() if len(v)>1},{})
    def test_detector_reports_a_repeated_name(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'a.lua').write_text('function test_x()\nend\ntest_y = function() end\n')
            (Path(directory)/'b.lua').write_text('  function test_x()\nend\n')
            found=definitions(Path(directory))
        self.assertEqual(found['test_x'],['a.lua:1','b.lua:1']);self.assertEqual(found['test_y'],['a.lua:3'])
if __name__=='__main__':unittest.main()

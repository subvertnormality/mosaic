"""Characterisation outside README: complete, order-independent saved-content oracle."""
import hashlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from persisted_digest import project_digest


@unittest.skipUnless(shutil.which('lua5.3'), 'requires Lua 5.3')
class PersistedDigestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        lib = self.root / 'lua' / 'lib'
        lib.mkdir(parents=True)
        (lib / 'tabutil.lua').write_text('return {load=function(path) return dofile(path) end}')

    def digest(self, body):
        path = self.root / 'project.ptn'
        path.write_text('return ' + body)
        return project_digest(path, str(self.root))

    def test_order_is_not_content(self):
        first = '{[1]={note=60, velocity=100}, name="test", enabled=false}'
        second = '{enabled=false, name="test", [1]={velocity=100, note=60}}'
        self.assertNotEqual(hashlib.sha256(first.encode()).digest(), hashlib.sha256(second.encode()).digest())
        self.assertEqual(self.digest(first), self.digest(second))

    def test_every_key_type_value_and_nested_value_matters(self):
        original = self.digest('{[1]={note=60}, name="test", enabled=false}')
        for changed in ('{[1]={note=61}, name="test", enabled=false}',
                        '{["1"]={note=60}, name="test", enabled=false}',
                        '{[1]={note="60"}, name="test", enabled=false}',
                        '{[1]={note=60}, name="test", enabled=true}',
                        '{[1]={note=60}, name="test", enabled=false, extra={}}'):
            with self.subTest(changed=changed):
                self.assertNotEqual(original, self.digest(changed))

    def test_large_integer_values_are_exact(self):
        self.assertNotEqual(self.digest('{value=9007199254740992}'),
                            self.digest('{value=9007199254740993}'))

    def test_corrupt_content_is_rejected(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.digest('invalid Lua')

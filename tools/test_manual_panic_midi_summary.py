"""Characterisation: fresh and retained Panic captures share reader prose."""
import pathlib
import subprocess
import unittest


class PanicReaderSummary(unittest.TestCase):
    def test_fresh_and_retained_summary_without_changing_packets(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        script = r'''
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync('manual/manual.js', 'utf8');
const fn = source.slice(source.indexOf('function midiText('), source.indexOf('function panicTargetResult('));
const context = {noteName:n=>'C', sameJson:(a,b)=>JSON.stringify(a)===JSON.stringify(b)};
vm.createContext(context); vm.runInContext(fn, context);
for (const kind of ['retained-panic-original-full-window-v1','fresh-native-panic-full-window-v1']) {
  const midi = {truncated:false,events:[{port:1,bytes:[128,0,0],ms:0}],provenance:{kind}};
  const before = JSON.stringify(midi);
  assert.equal(context.midiText(midi), 'Panic sends Note Off messages to the connected MIDI outputs. This capture starts silent.');
  assert.equal(JSON.stringify(midi), before);
}
assert.match(context.midiText({events:[{bytes:[128,60,0],ms:0}],provenance:{kind:'fresh-native-panic-sounding-note-target-window-v1'}}), /Note off/);
'''
        result = subprocess.run(['node', '-e', script], cwd=root,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()

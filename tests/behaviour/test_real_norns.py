import hashlib,tempfile,unittest
from pathlib import Path
from real_norns import Runner
class S:
 def __init__(self):self.scripts=[];self.synced=[]
 def run(self,x):self.scripts.append(x);return type('R',(),{'stdout':'/usr/bin/oscsend\nclient MIDI\n'})()
 def rsync(self,a,b):self.synced.append((a,b))
 def fetch(self,a,b):b.write_bytes(b'png');self.fetched=(a,b)
class M:
 def __init__(self):self.commands=[]
 def eval(self,x):self.commands.append(x);return 'ok'
class Tests(unittest.TestCase):
 def r(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);s=S();m=M();return Runner(s,m,Path(t.name),'safe-run'),s,m
 def test_backup_precedes_deploy_and_exact_load(self):
  r,s,m=self.r();r.deploy(Path('/candidate'));self.assertIn('recovery required',s.scripts[0]);self.assertEqual(s.synced,[(Path('/candidate'),'/home/we/dust/code/.mosaic-safe-run.staging')]);self.assertEqual(m.commands[0],'norns.script.clear()');self.assertIn("/home/we/dust/code/mosaic/mosaic.lua",m.commands[1])
 def test_restore_requires_owner_and_restores_three_paths(self):
  r,s,m=self.r();r.restore();x=s.scripts[-1];self.assertIn('cat /home/we/.cache/mosaic-real-norns/active',x);self.assertIn('code-mosaic /home/we/dust/code/mosaic',x);self.assertIn('data-mosaic /home/we/dust/data/mosaic',x);self.assertIn('system.state /home/we/dust/data/system.state',x);self.assertIn("dofile('/home/we/dust/data/system.state')",m.commands[-1])
 def test_only_stock_remote_key_encoder(self):
  r,s,_=self.r();r.action('key',2,1);r.action('enc',1,-2);self.assertIn('/remote/key ii 2 1',s.scripts[-2]);self.assertIn('/remote/enc ii 1 -2',s.scripts[-1]);self.assertRaises(ValueError,r.action,'grid',1,1)
 def test_screenshot_public_export_and_digest(self):
  r,s,m=self.r();x=r.screenshot('after-controls');self.assertIn('screen.export_screenshot',m.commands[0]);self.assertEqual(x['sha256'],hashlib.sha256(b'png').hexdigest())
 def test_probe_names_grid_limit(self):
  r,_,_=self.r();x=r.probe();self.assertTrue(x['alsa_available']);self.assertIn('unsupported',x['grid_input'])
if __name__=='__main__':unittest.main()

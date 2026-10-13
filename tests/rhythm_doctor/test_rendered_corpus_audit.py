import hashlib,json,tempfile,unittest,wave,subprocess,sys
from pathlib import Path
from audit_rendered_corpus import main

LANES=("BD","SD","CHH","OHH","BASS")
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
class RenderedAuditTests(unittest.TestCase):
 def setUp(self): self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.r=Path(self.t.name);self.clips=[]
 def add(self,name,frames,tags,events=None):
  p=self.r/(name+".wav")
  with wave.open(str(p),"wb")as w:w.setparams((2,2,16000,16000,"NONE","not compressed"));w.writeframes(frames)
  a=self.r/(name+".json");a.write_text(json.dumps({"events":events or {x:[]for x in LANES}}))
  self.clips.append({"id":name,"split":"held_out","stratum":"full_mix","audio":{"path":p.name,"sha256":digest(p)},"annotation":{"path":a.name},"duration_seconds":1,"tags":tags})
 def report(self):
  m=self.r/"m.json";m.write_text(json.dumps({"clips":self.clips}));return main(self.r,m,self.r/"out.json")
 def fixture(self,residual=0,gains=(100,200)):
  phase=b"".join(int(1000).to_bytes(2,"little",signed=True)+int(-1000+residual).to_bytes(2,"little",signed=True)for _ in range(16000));self.add("phase",phase,["phase_inverted_stereo"])
  raw=[]
  for i in range(16000):
   amp=gains[0] if i<8000 else gains[1];raw.extend((amp,amp))
  e={x:[]for x in LANES};e["BD"]=[{"time_seconds":0,"velocity":10},{"time_seconds":.5,"velocity":20}]
  self.add("gain",b"".join(int(x).to_bytes(2,"little",signed=True)for x in raw),["gain_ladder"],e)
 def test_correct_interleaved_stereo_fixture_passes(self): self.fixture();self.assertTrue(self.report()["passed"])
 def test_hash_tampering_rejected(self): self.fixture();self.clips[0]["audio"]["sha256"]="0"*64;self.assertIn("audio_hash:phase",self.report()["failures"])
 def test_one_bit_phase_residual_rejected(self): self.fixture(1);self.assertIn("phase_not_exact",self.report()["failures"])
 def test_nonproportional_gain_rejected(self): self.fixture(gains=(100,100));self.assertIn("gain_not_proportional:gain",self.report()["failures"])
 def test_cli_fails_for_rejected_report(self):
  self.fixture(1);m=self.r/"m.json";m.write_text(json.dumps({"clips":self.clips}))
  result=subprocess.run([sys.executable,"tests/rhythm_doctor/audit_rendered_corpus.py",str(self.r),str(m),"--output",str(self.r/"cli.json")],capture_output=True)
  self.assertEqual(result.returncode,1)
if __name__=="__main__":unittest.main()

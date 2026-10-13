import importlib.util, tempfile, unittest, wave, struct, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class DoctorStimulusTests(unittest.TestCase):
    def test_stereo_input_has_exact_geometry_and_non_silent_distinct_pulses(self):
        import sys
        sys.path.insert(0,str(ROOT/'tools'))
        import manual_doctor_capture as doctor
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'input.wav';identity=doctor.stimulus(path,seconds=3)
            with wave.open(str(path)) as wav:
                self.assertEqual((wav.getframerate(),wav.getnchannels(),wav.getnframes()),(48000,2,144000))
                samples=struct.unpack('<'+'h'*288000,wav.readframes(144000))
            self.assertEqual(samples[::2],samples[1::2])
            self.assertTrue(all(v==0 for v in samples[:48000*2]))
            self.assertGreater(max(abs(v) for v in samples),10000)
            self.assertLess(max(abs(v) for v in samples),32767)
            self.assertEqual(identity['onsets_seconds'],[1.0,1.5,2.0])
            self.assertEqual(identity['sha256'],doctor.digest(path))
    def test_softcut_pcm24_reader_preserves_signed_extremes_and_rejects_pcm16(self):
        import sys
        sys.path.insert(0,str(ROOT/'tools'))
        import manual_doctor_audit as audit
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'capture.wav'
            values=[-8388608,8388607,-1,0,4194304,-4194304]
            raw=b''.join((value & 0xffffff).to_bytes(3,'little') for value in values)
            with wave.open(str(path),'wb') as wav:
                wav.setnchannels(2);wav.setsampwidth(3);wav.setframerate(48000);wav.writeframes(raw)
            rate,channels=audit.read_softcut_pcm(path)
            self.assertEqual(rate,48000)
            self.assertEqual(channels,[[-1,-1/8388608,.5],[8388607/8388608,0,-.5]])
            with wave.open(str(path),'wb') as wav:
                wav.setnchannels(2);wav.setsampwidth(2);wav.setframerate(48000);wav.writeframes(b'\x00'*4)
            with self.assertRaises(AssertionError):audit.read_softcut_pcm(path)
    def test_source_schema_accepts_public_workflow_and_rejects_private_mutation(self):
        import copy,json,yaml,jsonschema
        source=yaml.safe_load((ROOT/'manual/doctor-scene.yaml').read_text())
        schema=json.loads((ROOT/'manual/doctor-scene.schema.json').read_text())
        jsonschema.Draft7Validator(schema).validate(source)
        bad=copy.deepcopy(source);bad['steps'][0]['inputs'][0]['method']='private_seed_ready_bank'
        with self.assertRaises(jsonschema.ValidationError):jsonschema.Draft7Validator(schema).validate(bad)
        self.assertEqual([s['id'] for s in source['steps']],['setup','record','analyse','ready','preview','paint','play'])
    def test_failed_native_report_cannot_be_published_as_audio_evidence(self):
        import sys,json
        sys.path.insert(0,str(ROOT/'tools'))
        import manual_doctor_audit as audit
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'report.json'
            path.write_text(json.dumps(dict(publication_kind='doctor-native-audio',passed=False)))
            with self.assertRaises(AssertionError):audit.audit_publication(path)
if __name__=='__main__':unittest.main()

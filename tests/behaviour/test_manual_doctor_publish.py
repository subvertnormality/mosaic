import importlib, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
class DoctorPublicationTests(unittest.TestCase):
    def fixture(self,folder,mode):
        directory=Path(folder)/mode;directory.mkdir()
        path=directory/'report.json'
        source='manual/doctor-scene.yaml' if mode=='manual' else 'manual/doctor-auto-probe.yaml'
        scene={'id':'doctor-'+mode,'title':mode,'behaviour_case':'MA-DOCTOR-AUDIO-001','steps':[]}
        value={'publication_kind':'doctor-native-audio','passed':True,'clock_mode':'real-time',
            'complete_regression_run':False,'hardware_timing_equivalent':False,
            'controlled_time':{'applicable':False,'reason':'Public ADC requires real audio time'},
            'source':{'yaml_path':source},'scenes':[scene]}
        path.write_text(json.dumps(value));return path,value
    def test_dry_run_preserves_exact_immutable_scenes_without_writing(self):
        doctor=importlib.import_module('manual_doctor_publish')
        with tempfile.TemporaryDirectory() as folder:
            manual,m=self.fixture(folder,'manual');auto,a=self.fixture(folder,'auto');destination=Path(folder)/'publication'
            with patch.object(doctor,'audit_doctor',return_value={'passed':True}) as audit:
                result=doctor.publish_reports(manual,auto,destination,publish=False)
            self.assertEqual(result['document']['scenes'],m['scenes']+a['scenes'])
            self.assertEqual([r['report_sha256'] for r in result['document']['evidence']['runs']],[doctor.digest(manual),doctor.digest(auto)])
            audit.assert_called_once_with(result['document']);self.assertFalse(destination.exists())
    def test_independent_refusal_cannot_replace_publication(self):
        doctor=importlib.import_module('manual_doctor_publish')
        with tempfile.TemporaryDirectory() as folder:
            manual,_=self.fixture(folder,'manual');auto,_=self.fixture(folder,'auto');destination=Path(folder)/'publication'
            destination.mkdir();original=destination/'generated';original.mkdir();target=original/'doctor-scenes.json';target.write_text('preserved')
            with patch.object(doctor,'audit_doctor',side_effect=ValueError('source mismatch')):
                with self.assertRaisesRegex(ValueError,'source mismatch'):doctor.publish_reports(manual,auto,destination,publish=True)
            self.assertEqual(target.read_text(),'preserved')

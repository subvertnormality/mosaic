import importlib.util,json,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('verify_full',HERE/'verify-full.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Tests(unittest.TestCase):
    def reports(self,root):
        registry=module.suite.case_registry()
        jobs,_=module.suite.plan_jobs(sorted(registry),module.suite.LANES,
            {'base-midi','midi-modulation','nb-audio','crow-jf'},
            module.suite.controlled_only_cases(),real_time_only=module.suite.real_time_only_cases())
        ident={'mosaic':{'revision':'m','tree_sha256':'t'},'emulator':{'revision':'e'},
               'norns_source':{'lua_tree_sha256':'n'}}
        paths=[]
        for i in range(10):
            rows=[{'case':c,'lane':l,'profile':p,'passed':True} for n,(c,l,p) in enumerate(jobs) if n%10==i]
            data={'status':'finished','passed':True,'identity':ident,'summary':{
                'sources_stable':True,'required_not_run':0},'cases':rows,
                'layers':{'python':[{'name':'guard','passed':True}]} if i==0 else {}}
            path=root/f'{i}.json';path.write_text(json.dumps(data));paths.append(path)
        return paths
    def test_accepts_exact_complete_union(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);paths=self.reports(root);out=root/'out.json'
            result=module.verify(paths,out)
            self.assertEqual(805,result['registered_cases'])
            self.assertEqual(1595,result['applicable_case_lane_runs'])
            self.assertTrue(result['complete_behaviour_run'])
    def test_rejects_missing_pair(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);paths=self.reports(root)
            data=json.loads(paths[0].read_text());data['cases'].pop();paths[0].write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'coverage mismatch'):module.verify(paths,root/'out.json')
if __name__=='__main__':unittest.main()

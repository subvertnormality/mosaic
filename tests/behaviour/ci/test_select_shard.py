"""Harness characterisation outside the manual: exhaustive deterministic scheduling."""
import importlib.util,json,subprocess,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('select_shard',HERE/'select-shard.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Tests(unittest.TestCase):
    def test_pinned_duration_tail_is_balanced_without_dropping_cases(self):
        # Red on 08421266 before partition implementation: 4,493,500 ms was
        # not below 3,100,000 ms. This is a prediction, not a CI timing claim.
        timing=json.loads((HERE/'shard-durations.json').read_text())
        weights=timing['cases_ms']
        current=set(module.select('base-midi',0,1))
        selected=[module.select('base-midi',i,16) for i in range(16)]
        self.assertEqual(set(c for group in selected for c in group),current)
        self.assertLessEqual(set(weights),current)
        shards=module.partition(sorted(weights),16,weights,timing['shard_zero_overhead_ms'])
        def tail(groups):
            return max(max(sum(weights[c][lane] for c in group) for lane in range(2))+
                       (timing['shard_zero_overhead_ms'] if i==0 else 0)
                       for i,group in enumerate(groups))
        original=[sorted(weights)[i::16] for i in range(16)]
        self.assertGreater(tail(original),4400000)
        self.assertLess(tail(shards),3100000)
        self.assertEqual(sorted(c for group in shards for c in group),sorted(weights))
        self.assertEqual(timing['source_revision'],'edafd97baa308082b1f0b97202dbfd9b531219c6')
        self.assertEqual(len(timing['reports_sha256']),19)

    def test_partition_is_independent_of_case_and_timing_row_order(self):
        ids=['A','B','C','D']
        weights={'A':[100,0],'B':[90,0],'C':[0,100],'D':[0,90]}
        expected=module.partition(ids,2,weights)
        self.assertEqual(expected,[['A','D'],['B','C']])
        self.assertEqual(expected,module.partition(ids[::-1],2,dict(reversed(list(weights.items())))))

    def test_new_and_stale_cases_do_not_change_selection(self):
        weights={'A':[10,20],'STALE':[999999,999999]}
        ids=['A','NEW']
        expected=module.partition(ids,2,dict(weights,NEW=list(module.UNKNOWN_MS)))
        self.assertEqual(module.partition(ids,2,weights),expected)
        self.assertEqual(sorted(c for group in expected for c in group),sorted(ids))

    def test_shard_zero_fast_layers_are_reserved_on_both_lanes(self):
        weights={c:[100,0] for c in 'ABCD'}
        self.assertEqual(module.partition(list(weights),2,weights,100),[['C'],['A','B','D']])

    def test_invalid_weights_fail_closed(self):
        for pair in ([-1,1],[0,0],[True,1],[1.5,1],[float('nan'),1],
                     [float('inf'),1],[1],[1,2,3],'12',None):
            with self.subTest(pair=pair),self.assertRaises(ValueError):
                module.partition(['A'],2,{'A':pair})
        for overhead in (-1,True,1.5):
            with self.subTest(overhead=overhead),self.assertRaises(ValueError):
                module.partition(['A'],2,{'A':[1,1]},overhead)
        with self.assertRaises(ValueError):module.partition(['A','A'],2,{})
        with self.assertRaises(ValueError):module.partition(['A'],0,{})

    def test_single_shard_and_more_shards_than_cases_preserve_inventory(self):
        for count in (1,2,8):
            shards=module.partition(['B','A'],count,{})
            self.assertEqual(len(shards),count)
            self.assertEqual(sorted(c for group in shards for c in group),['A','B'])

    def test_cli_uses_same_weighted_selection(self):
        result=subprocess.run([sys.executable,str(HERE/'select-shard.py'),'--profile','base-midi',
                               '--index','2','--count','16','--json'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),module.select('base-midi',2,16))

    def test_base_shards_are_disjoint_and_exhaustive(self):
        shards=[module.select('base-midi',i,16) for i in range(16)]
        flat=[case for shard in shards for case in shard]
        self.assertEqual(len(flat),len(set(flat)))
        self.assertEqual(set(flat),set(module.select('base-midi',0,1)))
    def test_special_profiles_are_selected_exactly(self):
        self.assertEqual(4,len(module.select('midi-modulation',0,1)))
        self.assertEqual(3,len(module.select('nb-audio',0,1)))
        self.assertEqual(4,len(module.select('crow-jf',0,1)))
    def test_rejects_invalid_shard(self):
        with self.assertRaises(ValueError):module.select('base-midi',16,16)
if __name__=='__main__':unittest.main()

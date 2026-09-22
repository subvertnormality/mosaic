import importlib.util,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('select_shard',HERE/'select-shard.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class Tests(unittest.TestCase):
    def test_base_shards_are_disjoint_and_exhaustive(self):
        shards=[module.select('base-midi',i,16) for i in range(16)]
        flat=[case for shard in shards for case in shard]
        self.assertEqual(len(flat),len(set(flat)))
        self.assertEqual(set(flat),set(module.select('base-midi',0,1)))
        self.assertEqual(826,len(flat))
    def test_special_profiles_are_selected_exactly(self):
        self.assertEqual(4,len(module.select('midi-modulation',0,1)))
        self.assertEqual(3,len(module.select('nb-audio',0,1)))
        self.assertEqual(4,len(module.select('crow-jf',0,1)))
    def test_rejects_invalid_shard(self):
        with self.assertRaises(ValueError):module.select('base-midi',16,16)
if __name__=='__main__':unittest.main()

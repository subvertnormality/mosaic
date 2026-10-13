"""Characterisation: immutable pre-apply native Device projection contracts."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from manual_player_routes import choose_frame
class RouteProjection(unittest.TestCase):
    def test_canonical_authoring_source_exists(self):
        source=Path(__file__).resolve().parents[2]/"manual/player-routes.yaml"
        self.assertTrue(source.is_file(),"Indexed canonical player-route authoring source is missing")
    def fixture(self):
        observations=[{"monotonic_ns":10,"state":{"selected":"Voice","channel":1}}]
        results=[{"kind":"device-picker-frame","label":"Voice","matched":True}]
        actions=[{"request":{"sequence":1,"action":{"type":"enc","n":3,"delta":2}},"ack":{"status":"applied","monotonic_ns":9}},
                 {"request":{"sequence":2,"action":{"type":"key","n":3,"state":1}},"ack":{"status":"applied","monotonic_ns":11}},
                 {"request":{"sequence":3,"action":{"type":"key","n":3,"state":0}},"ack":{"status":"applied","monotonic_ns":12}}]
        return observations,results,actions
    def matcher(self,state,voice,ch):return state.get("selected")==voice and state.get("channel")==ch
    def test_preapply_frame_and_actual_trace(self):
        obs,results,actions=self.fixture()
        selected=choose_frame(obs,results,actions,"Voice",1,self.matcher)
        self.assertEqual(selected["observation_index"],0)
        self.assertEqual(selected["assertion_index"],0)
        self.assertEqual(selected["following_actions"],actions[1:])
        self.assertEqual(selected["public_actions"],actions[:1])
    def test_other_channel_frame_rejected(self):
        obs,results,actions=self.fixture()
        with self.assertRaisesRegex(ValueError,"pre-apply"):choose_frame(obs,results,actions,"Voice",2,self.matcher)
    def test_missing_semantics_rejected(self):
        obs,results,actions=self.fixture()
        with self.assertRaisesRegex(ValueError,"assertion"):choose_frame(obs,[],actions,"Voice",1,self.matcher)
    def test_apply_frame_not_substituted(self):
        obs,results,actions=self.fixture();obs[0]["monotonic_ns"]=13
        with self.assertRaisesRegex(ValueError,"pre-apply"):choose_frame(obs,results,actions,"Voice",1,self.matcher)
    def test_unapplied_key_rejected(self):
        obs,results,actions=self.fixture();actions[1]["ack"]["status"]="rejected"
        with self.assertRaisesRegex(ValueError,"pre-apply"):choose_frame(obs,results,actions,"Voice",1,self.matcher)
if __name__=="__main__":unittest.main()

import base64,unittest
from contract.mini_header_ui import atlas as v1,literal_pixels
from contract.mini_header_animation_ui import atlas,poses,require_icon,expected_pose,overlay,exact_header_matches
from frame_oracle import live_header

def state(data):return {"frame":{"pixels_base64":base64.b64encode(data).decode()}}

class V2MiniHeaderOracleTests(unittest.TestCase):
    def test_all744_literal_poses_and_rest_footprints_are_frozen(self):
        old=v1();new=atlas();self.assertEqual(set(old),set(new));self.assertEqual(sum(len(s["frames"]) for s in new.values()),744)
        for key,spec in new.items():
            self.assertEqual(spec["frames"][0],old[key]["frames"][0])
            for field in ("width","height","origin"):self.assertEqual(spec[field],old[key][field])
            self.assertEqual(len(spec["frames"]),8)
            for frame in spec["frames"]:literal_pixels(spec,frame)
    def test_every_eighth_pose_and_loop_boundary(self):
        for page in ("C04","C07","S01","C01","C02"):
            spec=atlas()[page];period=spec["loop_quarter_beats"]/8
            for i in range(8):self.assertEqual(expected_pose((i+.25)*period,page),i)
            self.assertEqual(expected_pose(spec["loop_quarter_beats"],page),0)
            for invalid in (None,-1,float("nan"),float("inf"),"1",True):self.assertEqual(expected_pose(invalid,page),0)
            self.assertEqual(expected_pose(.75,page,False),0)
    def test_all_real_authored_clock_frames_match_exactly(self):
        spec=atlas()["C04"]
        for i,f in enumerate(spec["frames"]):self.assertIn(i,poses(state(literal_pixels(spec,f)),"C04"))
    def test_motion_off_rejects_richer_nonrest_frame(self):
        spec=atlas()["C04"]
        f=next(f for f in spec["frames"] if f!=spec["frames"][0])
        with self.assertRaises(AssertionError):require_icon(state(literal_pixels(spec,f)),"C04",False)
    def test_exact_header_keeps_title_scope_and_full_bounded_bitmap(self):
        spec=atlas()["C04"];base,rows=live_header("CLOCK","CH01","vertical_list");e=overlay(base,spec,spec["frames"][4])
        self.assertTrue(exact_header_matches(state(e),"CLOCK","CH01","vertical_list",base,rows))
        for x,y in ((1,1),(1,12),(96,0),(125,7)):
            wrong=bytearray(e);wrong[(y*128+x)*4]^=1
            self.assertFalse(exact_header_matches(state(wrong),"CLOCK","CH01","vertical_list",base,rows))

    def test_shared_header_accepts_only_exact_new_sprite_with_exact_text(self):
        from frame_oracle import live_header_matches
        spec=atlas()["C04"];base,rows=live_header("CLOCK","CH01","vertical_list")
        e=overlay(base,spec,spec["frames"][4])
        self.assertTrue(live_header_matches(state(e),"CLOCK","CH01","vertical_list"))
        self.assertFalse(live_header_matches(state(base),"CLOCK","CH01","vertical_list"))

class FooterBaselineGuardTests(unittest.TestCase):
    def test_actual_transient_footer_cannot_seed_animation_body_baseline(self):
        import json
        from pathlib import Path
        from contract.mini_header_animation_ui import sample
        fixture=json.loads((Path(__file__).parent/"fixtures/readability-scale-footer-native-frames.json").read_text())
        class StopSampling(Exception):pass
        class Driver:
            settled=False
            def wait(self,predicate,timeout):
                self_test.assertFalse(predicate(fixture["transient"]))
                self_test.assertTrue(predicate(fixture["settled"]))
                self.settled=True
            def snapshot(self):
                self_test.assertTrue(self.settled,"Cannot seed fixed body before exact normal footer")
                raise StopSampling()
        self_test=self
        with self.assertRaises(StopSampling):sample(Driver(),"S01",False,.125,tempo=90)

if __name__=="__main__":unittest.main()

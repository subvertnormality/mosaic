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



class PinnedDocumentationMiniFrameTests(unittest.TestCase):
    @staticmethod
    def _driver(top):
        class Driver:
            def __init__(self):
                self.results=[]
            def wait(self, predicate):
                state_value=state(top + bytes(128*64*4-len(top)))
                if not predicate(state_value):
                    raise AssertionError("frame did not match an authored documented pose")
        return Driver()

    def test_preserved_native_obs44_frame_matches_the_authored_pose(self):
        import base64,json,hashlib
        from pathlib import Path
        from contract.harmony_merge_visual import documentation_frame
        fixture=json.loads((Path(__file__).parent/"fixtures/harmony-no-voicing-native-obs44.json").read_text())
        self.assertEqual(fixture["source_run_id"],"b947eb81fea448e2970c47a333adcd37")
        self.assertEqual(fixture["source_case"],"M-HARMONY-FAILURE-001-base-midi")
        self.assertEqual(fixture["source_observation_index"],44)
        self.assertEqual(fixture["source_observations_sha256"],"3a9f1747df3c90887d10b0b107d3b92102349ad9f616523365a8b99608ac467b")
        raw=base64.b64decode(fixture["pixels_base64"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),"d493f76a057f2969bb8779315367736220ccd328cb8b0a22f51fed84baae88c3")
        self.assertEqual(hashlib.sha256(raw).hexdigest(),fixture["frame_sha256"])
        top=raw[:128*55*4]
        self.assertEqual(hashlib.sha256(top).hexdigest(),fixture["top55_sha256"])
        self.assertEqual(fixture["top55_sha256"],"dbb0d576f1c694285fbe2ef40aa74a6215b68d336a0f3dc0ebf97074e149a7a5")
        driver=self._driver(top)
        documentation_frame(driver,"52c9016ad80d1d7c92a9e6d8b97109f21b5450f6453cff5758774e552b5eeef2","images/harmony-no-voicing.png",stable_rows=55)
        result=driver.results[-1]
        self.assertEqual(result["sha256"],fixture["top55_sha256"])
        self.assertEqual(result["baseline_sha256"],"52c9016ad80d1d7c92a9e6d8b97109f21b5450f6453cff5758774e552b5eeef2")
        self.assertEqual(result["matching_poses"],[4])

    def test_all_pinned_documentation_bodies_accept_only_their_v2_atlas_poses(self):
        from contract.harmony_merge_visual import _MINI_DOCUMENTATION_FRAMES, _documented_mini_variants, documentation_frame
        for name, (_, baseline_sha, _) in _MINI_DOCUMENTATION_FRAMES.items():
            _, page, variants = _documented_mini_variants(baseline_sha, name)
            for pose, expected in variants:
                driver=self._driver(expected)
                documentation_frame(driver, baseline_sha, name, stable_rows=55)
                result=driver.results[-1]
                self.assertEqual(result["validation"],"pinned-v2-mini-pose")
                self.assertEqual(result["page"],page)
                self.assertEqual(result["baseline_sha256"],baseline_sha)
                self.assertEqual(result["sha256"],__import__("hashlib").sha256(expected).hexdigest())
                self.assertIn(pose,result["matching_poses"])

    def test_changed_body_and_unlisted_icon_are_rejected(self):
        from contract.harmony_merge_visual import _MINI_DOCUMENTATION_FRAMES, _documented_mini_variants, documentation_frame
        name='images/harmony-no-voicing.png'
        _,baseline_sha, page=_MINI_DOCUMENTATION_FRAMES[name]
        _,_,variants=_documented_mini_variants(baseline_sha,name)
        spec=atlas()[page]
        for label,x,y in (("title",1,2),("value",8,31),("body",4,20)):
            with self.subTest(region=label):
                candidate=bytearray(variants[4][1])
                candidate[(y*128+x)*4] ^= 1
                with self.assertRaises(AssertionError):
                    documentation_frame(self._driver(bytes(candidate)),baseline_sha,name,stable_rows=55)
        candidate=bytearray(variants[4][1])
        x,y=spec["origin"]
        for yy in range(y,y+8):
            for xx in range(x,128):
                i=(yy*128+xx)*4
                candidate[i:i+4]=b"\x5a\x5a\x5a\x00"
        with self.assertRaises(AssertionError):
            documentation_frame(self._driver(bytes(candidate)),baseline_sha,name,stable_rows=55)

    def test_baseline_mismatch_fails_before_observed_pose_can_be_adopted(self):
        from contract.harmony_merge_visual import _documented_mini_variants
        with self.assertRaises(AssertionError):
            _documented_mini_variants("0"*64,"images/harmony-no-voicing.png")
        baseline_sha,_,variants=_documented_mini_variants(
            "52c9016ad80d1d7c92a9e6d8b97109f21b5450f6453cff5758774e552b5eeef2",
            "images/harmony-no-voicing.png")
        self.assertNotEqual(__import__("hashlib").sha256(variants[4][1]).hexdigest(),baseline_sha)


if __name__=="__main__":
    unittest.main()

import base64,unittest
from contract.mini_header_ui import atlas,literal_pixels,matching_poses,require_icon

def state(data):return {"frame":{"pixels_base64":base64.b64encode(data).decode()}}

class LiteralMiniHeaderOracleTests(unittest.TestCase):
    def test_all_authored_frames_are_bounded_and_literal(self):
        scenes=atlas();self.assertEqual(len(scenes),93)
        for spec in scenes.values():
            self.assertEqual(len(spec["frames"]),4)
            self.assertIn(spec["loop_quarter_beats"],(2,4))
            for frame in spec["frames"]:self.assertEqual(len(literal_pixels(spec,frame)),128*64*4)
    def test_exact_rest_and_animated_clock_poses(self):
        spec=atlas()["C04"]
        for i,frame in enumerate(spec["frames"]):
            self.assertIn(i,matching_poses(state(literal_pixels(spec,frame)),"C04"))
        require_icon(state(literal_pixels(spec,spec["frames"][0])),"C04",False)
    def test_motion_off_rejects_nonrest_pose(self):
        spec=atlas()["C04"]
        with self.assertRaises(AssertionError):require_icon(state(literal_pixels(spec,spec["frames"][1])),"C04",False)
    def test_missing_icon_cannot_pass(self):
        with self.assertRaises(AssertionError):require_icon(state(bytes(128*64*4)),"C04",True)
    def test_wrong_pixel_or_ghost_in_reserved_background_cannot_pass(self):
        spec=atlas()["C04"];expected=literal_pixels(spec,spec["frames"][0])
        for x,y in ((118,1),(96,0)):
            wrong=bytearray(expected);wrong[(y*128+x)*4]^=1
            self.assertEqual(matching_poses(state(wrong),"C04"),[])
    def test_compact_masks_contract_owns_only_original_mark_slot(self):
        spec=atlas()["C01"]
        self.assertEqual(spec["origin"],[121,0]);self.assertEqual(spec["width"],7)
        self.assertGreater(len(set(tuple(f) for f in spec["frames"])),1)

if __name__=="__main__":unittest.main()

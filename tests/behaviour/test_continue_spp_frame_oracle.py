"""Exact-footprint framebuffer comparison keeps nearby header pixels observable."""
import unittest
from contract.continue_spp_frame_oracle import assert_same_outside_mini


class ContinueSppFrameOracle(unittest.TestCase):
    def test_adjacent_header_pixel_outside_mini_is_rejected(self):
        spec={"origin":[106,0],"width":22,"height":8}
        control=bytearray(128*64*4)
        adjacent=bytearray(control)
        # x=105 is immediately beside C05's declared x=106..127 footprint.
        adjacent[(3*128+105)*4] = 1
        with self.assertRaisesRegex(AssertionError,"outside the authored mini-header"):
            assert_same_outside_mini(adjacent,control,spec)

    def test_change_inside_exact_mini_footprint_is_scoped_for_pose_oracle(self):
        spec={"origin":[106,0],"width":22,"height":8}
        control=bytearray(128*64*4)
        mini=bytearray(control)
        mini[(3*128+106)*4] = 1
        assert_same_outside_mini(mini,control,spec)


if __name__=="__main__":
    unittest.main()

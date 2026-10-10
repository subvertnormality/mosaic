"""Exact-footprint framebuffer comparison keeps nearby header pixels observable."""
import unittest
from contract.continue_spp_frame_oracle import assert_same_outside_mini
from contract.continue_spp import assert_stopped_snapshot


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


    def test_clock_admission_metadata_is_lane_specific_and_independent_of_stopped_output(self):
        stopped={"grid":[0]*128,"midi_count":34}
        realtime=dict(stopped,clock={"mode":"real-time","admitted":True})
        controlled=dict(stopped,clock={"mode":"controlled-experimental","admitted":False})
        assert_stopped_snapshot(realtime,stopped["grid"],34,"real-time")
        assert_stopped_snapshot(controlled,stopped["grid"],34,"controlled-experimental")

        with self.assertRaises(AssertionError):
            assert_stopped_snapshot(realtime,stopped["grid"],34,"controlled-experimental")

        for mode,admitted in (("real-time",False),("controlled-experimental",True)):
            with self.subTest(mode=mode,admitted=admitted):
                wrong=dict(stopped,clock={"mode":mode,"admitted":admitted})
                with self.assertRaises(AssertionError):
                    assert_stopped_snapshot(wrong,stopped["grid"],34,mode)

        # Realtime admission is metadata, not permission for musical output to resume.
        changed_grid=dict(realtime,grid=[1]+[0]*127)
        changed_midi=dict(realtime,midi_count=35)
        with self.assertRaises(AssertionError):
            assert_stopped_snapshot(changed_grid,stopped["grid"],34,"real-time")
        with self.assertRaises(AssertionError):
            assert_stopped_snapshot(changed_midi,stopped["grid"],34,"real-time")



if __name__=="__main__":
    unittest.main()

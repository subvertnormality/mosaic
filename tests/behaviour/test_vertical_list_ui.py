"""Independent screen-oracle regressions for native vertical editor evidence."""
import base64, os, unittest
os.environ.setdefault('MONOME_EMULATOR','/home/andy/projects/monome-emulator-ci-combined')
from frame_oracle import render, vertical_selected_field_matches, selected_field_matches
from ui import Ui, UiMapError
from ui_map import PAGE_RINGS

def state(commands):
    return {'frame':{'pixels_base64':base64.b64encode(render(commands)).decode()}}

class VerticalListOracle(unittest.TestCase):
    def test_song_slot_setup_ring_uses_current_vertical_layout(self):
        self.assertEqual(PAGE_RINGS["Song"][0],("A01","SLOT SETUP","vertical_list","slot_setup"))
    def test_retired_layout_tag_fails_closed(self):
        s=state([(0,27,15,'>'),(7,27,15,'Rate'),((None,126),27,15,'/1')])
        with self.assertRaisesRegex(ValueError,'retired.*focused'):
            selected_field_matches(s,'focused','Rate','/1')
    def test_ui_verb_rejects_stale_layout_before_observation(self):
        class Driver:
            results=[]
            def wait(self,predicate):
                raise AssertionError('stale tag must be rejected before observing')
        with self.assertRaisesRegex(UiMapError,'retired.*focused'):
            Ui(Driver()).expect_selected_field('focused','Rate','/1')
    def test_current_ui_verb_preserves_exact_layout_metadata(self):
        snapshot=state([(0,27,15,'>'),(7,27,15,'Rate'),((None,126),27,15,'/1')])
        class Driver:
            def __init__(self):self.results=[]
            def wait(self,predicate):
                assert predicate(snapshot)
                return snapshot
        driver=Driver();Ui(driver).expect_selected_field('vertical_list','Rate','/1')
        self.assertEqual(driver.results[-1],dict(kind='selected-field',layout='vertical_list',label='Rate',value='/1',matched=True))
    def test_exact_short_selected_label_and_value(self):
        s=state([(0,27,15,'>'),(7,27,15,'Rate'),((None,126),27,15,'/1')])
        self.assertTrue(vertical_selected_field_matches(s,'Rate','/1'))
        self.assertFalse(vertical_selected_field_matches(s,'Rate','/2'))
        self.assertFalse(vertical_selected_field_matches(s,'Swing','/1'))
    def test_neighbor_is_not_selection(self):
        s=state([(7,36,7,'Swing type'),((None,126),36,10,'X')])
        self.assertFalse(vertical_selected_field_matches(s,'Swing type','X'))
    def test_wide_label_kept_with_whole_value_on_next_line(self):
        value='NO VOICING RANGE'
        s=state([(0,27,15,'>'),(7,27,15,'Register policy'),((None,126),36,15,value)])
        self.assertTrue(vertical_selected_field_matches(s,'Register policy',value))
        self.assertFalse(vertical_selected_field_matches(s,'Register policy','NO VOICING'))
    def test_retired_focused_carousel_is_rejected(self):
        s=state([(1,28,10,'Rate'),(1,48,15,'/1',23)])
        self.assertFalse(vertical_selected_field_matches(s,'Rate','/1'))
if __name__=='__main__':unittest.main()

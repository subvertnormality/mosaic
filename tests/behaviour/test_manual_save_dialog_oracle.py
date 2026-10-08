"""Focused oracle tests; these render expectations, never documentation assets."""
import base64, unittest
from manual_save_dialog_oracle import expected,matches,specification,verify_frame

def state(blob):return {'frame':{'pixels_base64':base64.b64encode(blob).decode()}}

class SaveDialogOracleTest(unittest.TestCase):
    def test_literal_states(self):
        for stage in ['entry','delete','empty','first-character','name-entered','confirm']:
            self.assertTrue(matches(state(expected(stage)),stage))
    def test_del_ok_selection_is_not_interchangeable(self):
        self.assertFalse(matches(state(expected('entry')),'delete'))
        self.assertFalse(matches(state(expected('name-entered')),'confirm'))
    def test_name_and_character_state_are_not_interchangeable(self):
        self.assertFalse(matches(state(expected('first-character')),'name-entered'))
        self.assertFalse(matches(state(expected('empty')),'first-character'))
    def test_alpha_only_is_ignored(self):
        blob=bytearray(expected('confirm'));blob[3::4]=bytes([93])*8192
        self.assertTrue(matches(state(blob),'confirm'))
    def test_incorrect_name_metadata_rejected(self):
        text,row,delok,pos=specification('confirm')
        value=dict(stage='confirm',text='Four note',row=row,delok=delok,position=pos,citation='manual:save-and-load')
        with self.assertRaisesRegex(ValueError,'Changed literal'):
            verify_frame(value,state(expected('confirm')))
    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):expected('invented')

if __name__=='__main__':unittest.main()

import copy,unittest
from jf_oracle import verify_packets,verify_unplayed,verify_session_export

class JFWireOracleTests(unittest.TestCase):
    def setUp(self):
        self.expected=[[8,1,6,102,31,255],[8,2,6,102,31,255],[1,1,0],[1,2,0]]
        self.records=[dict(sequence=i+1,monotonic_ns=1000+i*100,address=0x70,bytes=list(command)) for i,command in enumerate(self.expected)]
    def test_declared_recipe(self):
        self.assertEqual(verify_packets(self.records,self.expected)['commands'],4)
    def test_missing_extra_and_reordered(self):
        for records in (self.records[:-1],self.records+[self.records[-1]],self.records[::-1]):
            with self.subTest(records=records),self.assertRaises(AssertionError):verify_packets(records,self.expected)
    def test_wrong_voice_pitch_level_release(self):
        for row,column,value in ((0,1,2),(0,2,7),(0,5,254),(2,1,2),(3,2,1)):
            rows=copy.deepcopy(self.records);rows[row]['bytes'][column]=value
            with self.subTest(row=row,column=column),self.assertRaises(AssertionError):verify_packets(rows,self.expected)
    def test_wrong_address_gap_duplicate_and_clock_reversal(self):
        for row,key,value in ((0,'address',0x71),(0,'sequence',2),(1,'sequence',1),(2,'monotonic_ns',900)):
            rows=copy.deepcopy(self.records);rows[row][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(AssertionError):verify_packets(rows,self.expected)
    def test_explicit_page_origin(self):
        for row in self.records:row['sequence']+=256
        verify_packets(self.records,self.expected,first_sequence=257)
        with self.assertRaises(AssertionError):verify_packets(self.records,self.expected)
    def test_byte_domain(self):
        for value in (-1,256,True,1.0):
            rows=copy.deepcopy(self.records);rows[0]['bytes'][0]=value
            with self.subTest(value=value),self.assertRaises(AssertionError):verify_packets(rows,self.expected)

class JFScenarioIntervals(unittest.TestCase):
    def packet(self,sequence,command):
        return dict(sequence=sequence,monotonic_ns=sequence*100,address=0x70,bytes=command)
    def test_setup_and_cleanup_contract(self):
        for phase in ('startup','selection'):
            verify_unplayed([self.packet(1,[1,0,0]),self.packet(2,[6,1])],phase)
        observed=[self.packet(1,[8,1,6,102,31,255]),self.packet(2,[1,1,0])]
        verify_session_export(observed+[self.packet(3,[1,0,0])],observed)
        verify_session_export(observed,observed)
    def test_extra_transition_packet_fails_scenario_boundary(self):
        for command in ([8,1,6,102,31,255],[1,2,0],[6,0]):
            transition=[self.packet(3,[6,1]),self.packet(4,command)]
            # Valid sequence/timestamps: must fail the quiet musical contract.
            with self.subTest(command=command),self.assertRaisesRegex(AssertionError,'Unexpected selection JF command'):
                verify_unplayed(transition,'selection')
    def test_extra_final_packet_fails_scenario_export(self):
        observed=[self.packet(1,[8,1,6,102,31,255]),self.packet(2,[1,1,0])]
        for command in ([8,1,6,102,31,255],[1,2,0],[6,1]):
            with self.subTest(command=command),self.assertRaisesRegex(AssertionError,'Unexpected cleanup JF command'):
                verify_session_export(observed+[self.packet(3,command)],observed)

if __name__=='__main__':unittest.main()

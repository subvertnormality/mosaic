import unittest,copy
from panic_repeat_trace import verify_restarted_sweeps
def fixture(repeats=2):
    sweep=[[128+channel,note,0] for note in range(128) for channel in range(16)]
    return [dict(port=port,bytes=data) for size in ([480]*(repeats-1)+[2048]) for data in sweep[:size] for port in (1,2,3)]
class RepeatOracleTests(unittest.TestCase):
    def test_two_and_three_restarts(self):
        for repeats in (2,3):self.assertTrue(verify_restarted_sweeps(fixture(repeats),repeats)['passed'])
    def test_missing_extra_or_reordered_data(self):
        base=fixture()
        mutations=[base[:20]+base[21:],base+[base[-1]],base[:15]+[base[18]]+base[16:18]+[base[15]]+base[19:]]
        for data in mutations:
            with self.assertRaises(AssertionError):verify_restarted_sweeps(data,2)
    def test_wrong_bytes_and_ports(self):
        for field,value in [('port',4),('bytes',[144,24,100]),('bytes',[128,24,1])]:
            data=copy.deepcopy(fixture());data[20][field]=value
            with self.assertRaises(AssertionError):verify_restarted_sweeps(data,2)
    def test_missing_restart_or_completed_previous_sweep(self):
        for data in (fixture(2),fixture(3)):
            with self.assertRaises(AssertionError):verify_restarted_sweeps(data,5-len([e for e in data if e['port']==1 and e['bytes']==[128,0,0]]))
        sweep=fixture()[480*3:]
        with self.assertRaises(AssertionError):verify_restarted_sweeps(sweep+sweep,2)
if __name__=='__main__':unittest.main()

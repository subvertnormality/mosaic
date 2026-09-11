import unittest,copy
from panic_transport import verify_panic_transport
def fixture():return [dict(port=p,bytes=[status],monotonic_ns=t) for status,t in ((250,105),(252,405)) for p in (1,2,3)]
def check(events):return verify_panic_transport(events,field='monotonic_ns',start_bounds=(100,110),stop_bounds=(400,410))
class PanicTransportTests(unittest.TestCase):
    def test_control_boundaries(self):self.assertTrue(check(fixture())['passed'])
    def test_extra_stop_during_panic(self):
        data=fixture();data.insert(3,dict(port=1,bytes=[252],monotonic_ns=250))
        with self.assertRaises(AssertionError):check(data)
    def test_stop_moved_into_panic(self):
        data=fixture();data[3]['monotonic_ns']=250
        with self.assertRaises(AssertionError):check(data)
    def test_startup_stop_from_a_fresh_project_is_unexpected(self):
        data=[dict(port=p,bytes=[252],monotonic_ns=0) for p in (1,2,3)]+fixture()
        with self.assertRaises(AssertionError):check(data)
    def test_missing_reordered_wrong_port_or_late(self):
        base=fixture();mutations=[base[:-1],base[:3]+[base[4],base[3]]+base[5:]]
        for field,value in [('port',4),('monotonic_ns',411),('bytes',[248])]:
            data=copy.deepcopy(base);data[-1][field]=value;mutations.append(data)
        for data in mutations:
            with self.assertRaises(AssertionError):check(data)
if __name__=='__main__':unittest.main()

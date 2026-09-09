import copy,unittest
from forwarded_clock import assert_forwarded_receiver

class ForwardedReceiverTests(unittest.TestCase):
    def fixture(self):
        first=1_000_000_000;events=[dict(index=0,port=2,bytes=[250],logical_ns=first)]
        index=1
        for tick in range(60):
            at=first+tick*25_000_000
            events.append(dict(index=index,port=2,bytes=[248],logical_ns=at));index+=1
            if tick%6==0 and tick<=54:
                events.append(dict(index=index,port=1,bytes=[144,60,100],logical_ns=at));index+=1
        events.append(dict(index=index,port=2,bytes=[252],logical_ns=first+1_487_500_000))
        return first,events
    def test_complete_receiver_trace_passes(self):
        first,events=self.fixture()
        result=assert_forwarded_receiver(events,'logical_ns',first,2e-9)
        self.assertEqual(result['clock_ticks'],60)
    def test_missing_tail_clock_fails(self):
        first,events=self.fixture()
        tail=max(i for i,e in enumerate(events) if e['port']==2 and e['bytes']==[248])
        del events[tail]
        with self.assertRaises(AssertionError):
            assert_forwarded_receiver(events,'logical_ns',first,2e-9)
    def test_missing_stop_fails(self):
        first,events=self.fixture();events.pop()
        with self.assertRaises(AssertionError):
            assert_forwarded_receiver(events,'logical_ns',first,2e-9)

if __name__=='__main__':unittest.main()

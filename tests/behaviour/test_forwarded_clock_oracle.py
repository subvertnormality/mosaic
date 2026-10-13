import copy,unittest
from forwarded_clock import assert_forwarded_receiver
from contract.forwarded_clock import forwarded_clock_diagnostic

class ForwardedReceiverTests(unittest.TestCase):
    def test_forwarded_diagnostic_keeps_stimulus_and_delivery_while_stabilising_capture(self):
        events=[dict(port=2,bytes=[248],logical_ns=123,monotonic_ns=456)]
        stimulus=[dict(port=1,bytes=[248],at_logical_ns=123)]
        delivered=[dict(port=1,bytes=[248],logical_ns=123)]
        result=forwarded_clock_diagnostic(49,123,events,stimulus,delivered,
                                          'controlled-experimental')
        self.assertEqual(result,dict(kind='forwarded-clock-diagnostic',warm_ticks=49,
                                     first_clock_deadline_ns=123,
                                     events=[dict(port=2,bytes=[248],logical_ns=123)],
                                     stimulus=stimulus,delivered=delivered))
        self.assertEqual(events[0]['monotonic_ns'],456)
        self.assertEqual(forwarded_clock_diagnostic(49,123,events,stimulus,delivered,
                                                    'real-time')['events'],events)

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

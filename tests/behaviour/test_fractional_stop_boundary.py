"""Stop uncertainty does not excuse missing required notes or timing violations."""
import copy,os,sys,unittest
from pathlib import Path
from fractions import Fraction as F
sys.path.insert(0,str(Path(os.environ['MONOME_EMULATOR'])/'src'))
from automation.protocol import ContractError
from fractional_deadlines import note_plan,check_segment

class StopBoundary(unittest.TestCase):
    def fixture(self,count=None,period=F(3,2),stop=3_000_000_000,applied=None,controlled=False):
        origin=1_000_000_000;applied=stop if applied is None else applied
        full,onsets=note_plan(period,origin,applied+1_000_000_000)
        if count is None:count=sum(n['deadline_ns']<stop for n in onsets)
        selected=full[:2*count-1];field='logical_ns' if controlled else 'monotonic_ns'
        events=[dict(port=e['port'],bytes=e['bytes'].copy(),**{field:e['deadline_ns']}) for e in selected]
        events.append(dict(port=1,bytes=[128,60,0],**{field:applied}))
        return events,dict(period=period,origin=origin,stop=stop,applied=applied,controlled=controlled)

    def test_boundary_equality_permits_both_cancellation_outcomes(self):
        for count in (1,2):
            events,args=self.fixture(count,period=F(144),stop=2_050_000_000)
            report=check_segment(events,**args)['realtime_stop_boundary']
            self.assertEqual(report['required_onsets'],1)
            self.assertEqual(report['emitted_onsets'],count)
            self.assertEqual(report['permitted_prefix_lengths'],[1,2])
        events,args=self.fixture(1,period=F(144),stop=2_050_000_001)
        with self.assertRaises(AssertionError):check_segment(events,**args)

    def test_controlled_lane_remains_exact(self):
        events,args=self.fixture(1,period=F(144),stop=2_050_000_000,controlled=True)
        with self.assertRaises(AssertionError):check_segment(events,**args)
        events,args=self.fixture(2,period=F(144),stop=2_050_000_000,controlled=True)
        self.assertIsNone(check_segment(events,**args)['realtime_stop_boundary'])
        events[0]['logical_ns']+=3
        with self.assertRaises(AssertionError):check_segment(events,**args)

    def test_onset_during_stop_handling_is_fully_accounted(self):
        events,args=self.fixture(9,stop=1_083_000_000,applied=1_090_000_000)
        self.assertGreater(events[-2]['monotonic_ns'],args['stop'])
        self.assertTrue(check_segment(events,**args)['passed'])
        events[-2]['monotonic_ns']=events[-1]['monotonic_ns']+1
        with self.assertRaises(AssertionError):check_segment(events,**args)

    def test_guaranteed_events_and_all_observed_events_are_checked(self):
        events,args=self.fixture();self.assertTrue(check_segment(events,**args)['passed'])
        changes=[]
        for begin,end in ((0,1),(0,2),(20,22),(20,28),(-1,None)):
            changed=copy.deepcopy(events);del changed[begin:end];changes.append(changed)
        changed=copy.deepcopy(events);changed[20]['bytes'][1]=61;changes.append(changed)
        changed=copy.deepcopy(events);changed[20]['port']=2;changes.append(changed)
        changed=copy.deepcopy(events);changed[20]['monotonic_ns']+=60_000_000;changes.append(changed)
        changed=copy.deepcopy(events);changed[-1]['bytes'][2]=3;changes.append(changed)
        for index,changed in enumerate(changes):
            with self.subTest(index=index),self.assertRaises((AssertionError,ContractError)):
                check_segment(changed,**args)
        required=check_segment(events,**args)['realtime_stop_boundary']['required_onsets']
        changed,_=self.fixture(required-1)
        with self.assertRaises(AssertionError):check_segment(changed,**args)

    def test_start_latency_and_extra_prefix_limits(self):
        events,args=self.fixture()
        for offset in (-1,50_000_001):
            changed=copy.deepcopy(events);changed[0]['monotonic_ns']=args['origin']+offset
            with self.assertRaises(AssertionError):check_segment(changed,**args)
        changed,args=self.fixture(100,stop=1_083_000_000)
        with self.assertRaises(AssertionError):check_segment(changed,**args)

if __name__=='__main__':unittest.main()

"""Fault sensitivity of the external application's fractional timing oracle."""
import copy
from fractions import Fraction
import os
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(os.environ['MONOME_EMULATOR'])/'src'))
from automation.protocol import ContractError
from fractional_deadlines import note_plan, quantised_pulse, check_segment, preview_residual, reconcile_note_stream


class FractionalDeadlineContract(unittest.TestCase):
    def test_literal_startup_quantisation(self):
        self.assertEqual([quantised_pulse(Fraction(3,2),n) for n in range(8)], [0,2,3,5,6,8,9,11])
        self.assertEqual([quantised_pulse(Fraction(240,53),n) for n in range(8)], [0,4,9,13,18,22,27,31])
        for period in (Fraction(3,2),Fraction(240,53),Fraction(24,5),Fraction(120,13),Fraction(240,13),Fraction(312,5),Fraction(636,5)):
            for n in range(100):
                self.assertEqual(quantised_pulse(period,n+period.denominator)-quantised_pulse(period,n),period.numerator)

    def test_stopped_rate_edit_history(self):
        self.assertEqual(preview_residual(Fraction(3,2)), Fraction(1))
        period=Fraction(240,53)
        self.assertEqual([quantised_pulse(period,n,Fraction(1)) for n in range(6)], [0,5,9,14,18,23])
        self.assertNotEqual(quantised_pulse(period,1), quantised_pulse(period,1,Fraction(1)))

    def fixture(self, controlled):
        origin=1_000_000_000;stop=1_083_000_000
        planned,_=note_plan(Fraction(3,2),origin,stop)
        field='logical_ns' if controlled else 'monotonic_ns'
        events=[dict(port=e['port'],bytes=e['bytes'].copy(),**{field:e['deadline_ns']}) for e in planned]
        events.append(dict(port=1,bytes=[128,60,0],**{field:stop}))
        return events,dict(period=Fraction(3,2),origin=origin,stop=stop,applied=stop,controlled=controlled)

    def test_exact_plans_and_all_releases(self):
        for controlled in (False,True):
            events,args=self.fixture(controlled)
            self.assertTrue(check_segment(events,**args)['passed'])
            for i in range(len(events)):
                for mutation in ('missing','channel','port','late'):
                    changed=copy.deepcopy(events)
                    if mutation=='missing':changed.pop(i)
                    elif mutation=='channel':changed[i]['bytes'][0]+=1
                    elif mutation=='port':changed[i]['port']=2
                    else:changed[i]['logical_ns' if controlled else 'monotonic_ns']+=60_000_000
                    with self.assertRaises((AssertionError,ContractError),msg=str((controlled,i,mutation))):
                        check_segment(changed,**args)

    def test_wrong_tempo_and_origin_do_not_fit(self):
        for controlled in (False,True):
            events,args=self.fixture(controlled)
            for replacement in (dict(period=Fraction(24,5)),dict(origin=args['origin']+21_000_000)):
                with self.assertRaises((AssertionError,ContractError)):
                    check_segment(events,**dict(args,**replacement))


    def test_complete_stream_rejects_notes_outside_windows(self):
        segments = [dict(after=2,cursor=4), dict(after=7,cursor=9)]
        for kind in (3,11):
            notes = [dict(kind=kind,sequence=n,port=1,bytes=[144 if n%2 else 128,60,100])
                     for n in (3,4,8,9)]
            self.assertEqual(reconcile_note_stream(notes,segments,kind)['note_events'],4)
            for sequence in (1,2,5,7,10):
                for messages in ([ [128,60,0] ], [ [144,60,100],[128,60,0] ], [ [144,60,0] ]):
                    extras = [dict(kind=kind,sequence=sequence+i,port=2,bytes=message)
                              for i,message in enumerate(messages)]
                    with self.assertRaises(AssertionError):
                        reconcile_note_stream(notes+extras,segments,kind)
            with self.assertRaises(AssertionError):
                reconcile_note_stream(notes,[dict(after=2,cursor=8),dict(after=7,cursor=9)],kind)
            with self.assertRaises(AssertionError):
                reconcile_note_stream([],segments,kind)


if __name__=='__main__':unittest.main()

"""Case-owned controlled playback chunking; harness timing characterization only."""
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from trig_parameter_interactions import _playback_with_bounded_controlled_settle, fixed_note_domain


class ControlledPlaybackChunkTests(unittest.TestCase):
    def test_long_controlled_settle_keeps_exact_total_and_bounds_each_advance(self):
        advances=[]
        def elapse(seconds):
            advances.append(round(seconds*1_000_000_000))
        case=SimpleNamespace(clock_mode="controlled-experimental",elapse=elapse)
        def playback(expected,cycles,timeout,settle_seconds):
            case.elapse(.06)  # Driver.playback's start-tap settle remains unchanged.
            case.elapse(settle_seconds)
            case.elapse(.01)  # A later normal wait quantum remains unchanged.
            return "same native-playback result"
        case.playback=playback
        original=case.elapse
        result=_playback_with_bounded_controlled_settle(case,[(1,[144,60,127])],2,36,30)
        self.assertEqual(result,"same native-playback result")
        self.assertEqual(advances[0],60_000_000)
        self.assertEqual(advances[-1],10_000_000)
        settle=advances[1:-1]
        self.assertEqual(sum(settle),30_000_000_000)
        self.assertTrue(all(0<value<=60_000_000 for value in settle))
        self.assertEqual(len(settle),500)
        self.assertIs(case.elapse,original)

    def test_real_time_keeps_the_existing_single_playback_path(self):
        seen=[]
        original=lambda seconds: seen.append(seconds)
        case=SimpleNamespace(clock_mode="real-time",elapse=original)
        case.playback=lambda expected,cycles,timeout,settle_seconds: (seen.append(settle_seconds),"result")[1]
        result=_playback_with_bounded_controlled_settle(case,[],2,36,30)
        self.assertEqual(result,"result")
        self.assertEqual(seen,[30])
        self.assertIs(case.elapse,original)

    def test_controlled_playback_restores_elapse_after_error(self):
        case=SimpleNamespace(clock_mode="controlled-experimental",elapse=lambda seconds: None)
        original=case.elapse
        case.playback=lambda *args,**kwargs: (_ for _ in ()).throw(RuntimeError("sentinel"))
        with self.assertRaisesRegex(RuntimeError,"sentinel"):
            _playback_with_bounded_controlled_settle(case,[],2,36,30)
        self.assertIs(case.elapse,original)


class FixedNoteObservationTests(unittest.TestCase):
    def case(self,late_note=False):
        calls=[];advances=[]
        ui=SimpleNamespace(**{name:lambda *args,**kwargs:None for name in
            ('configure','channel_page','assign_trig_parameter_key','turn','set_value','encoder_event')})
        case=SimpleNamespace(ui=ui,clock_mode='controlled-experimental',results=[],elapse=advances.append)
        def playback(expected,cycles=3,timeout=5,settle_seconds=0):
            calls.append(dict(expected=expected,cycles=cycles,timeout=timeout,settle_seconds=settle_seconds))
            case.elapse(settle_seconds)
            return [{'logical_ns':round(index*1e9/6)+(63_000_000 if late_note and index==5 else 0)}
                    for index in range(9)]
        case.playback=playback
        return case,calls,advances

    def run_case(self,case):
        cases=ModuleType('cases');cases.assert_durations=lambda *args:None
        with patch.dict(sys.modules,{'cases':cases}):fixed_note_domain(case,start=16,count=1)

    def test_fixed_note_capture_has_a_quiet_full_phrase_window(self):
        # Characterisation of acquisition only: continuous native MIDI capture
        # replaces diagnostic polling during the two four-step fixture phrases.
        case,calls,advances=self.case();self.run_case(case)
        self.assertEqual(len(calls),2)
        for call in calls:
            self.assertEqual((call['cycles'],call['timeout'],call['settle_seconds']),(2,5,4/3))
            self.assertEqual([packet[1][2] for packet in call['expected']],[127,117,107,97])
        self.assertEqual(calls[0]['expected'][0][1][1],16)
        self.assertEqual([packet[1][1] for packet in calls[1]['expected']],[60,62,64,65])
        self.assertEqual(len(case.results),2)

    def test_quiet_capture_still_rejects_a_late_mandatory_note(self):
        case,calls,advances=self.case(late_note=True)
        with self.assertRaises(AssertionError):self.run_case(case)
        self.assertEqual(case.results,[])


if __name__=="__main__":
    unittest.main()

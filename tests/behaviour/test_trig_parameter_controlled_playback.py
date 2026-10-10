"""Case-owned controlled playback chunking; harness timing characterization only."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from trig_parameter_interactions import _playback_with_bounded_controlled_settle


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


if __name__=="__main__":
    unittest.main()

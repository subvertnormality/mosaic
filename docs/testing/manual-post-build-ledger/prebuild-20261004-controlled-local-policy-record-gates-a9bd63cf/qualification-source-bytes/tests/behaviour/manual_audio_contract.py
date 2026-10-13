"""Audio authoring acceptance: characterisation outside README (asset integrity)."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from manual_audio import validate, expand, metrics, verify_midi_packets, mapped_score, lesson_pcm
from unittest.mock import patch
import copy
class AudioAuthoring(unittest.TestCase):
    def setUp(self):
        self.data={"schema_version":1,"examples":[{"id":"example","title":"Example","feature_ids":["masks"],"description":"Example.","bars":4,"bpm":90,"profile":"manual-trio","tracks":[{"channel":1,"voice":"Polyperc 1","note":48,"velocity":42,"length_detents":8,"phrase":[[1,48],[9,55]],"final_bar":[[1,60]]}]}]}
    def test_real_midi_witness_forwards_explicit_install_to_actual_driver(self):
        import manual_audio
        from types import SimpleNamespace
        options=SimpleNamespace(midi_real_install='/qualified/real.json',midi_controlled_install='/qualified/control.json',app_root='/frozen')
        with patch('manual_audio.tracked_driver',side_effect=RuntimeError('driver sentinel')) as driver:
            with self.assertRaisesRegex(RuntimeError,'driver sentinel'):manual_audio.midi_acceptance({},'/evidence',options,'real-time')
            self.assertEqual(driver.call_args.kwargs['experimental_install'],'/qualified/real.json')
            self.assertEqual(driver.call_args.kwargs['clock_mode'],'real-time')
    def test_midi_worker_command_retains_both_explicit_lane_installations(self):
        import manual_audio
        from types import SimpleNamespace
        options=SimpleNamespace(mod_code_root='/voices',audio_install='/audio.json',midi_real_install='/qualified/real.json',midi_controlled_install='/qualified/control.json')
        command=manual_audio.midi_worker_command(Path('/run'),'piece',Path('/out'),Path('/frozen'),options,'real-time')
        self.assertEqual(command[command.index('--midi-real-install')+1],'/qualified/real.json')
        self.assertEqual(command[command.index('--midi-controlled-install')+1],'/qualified/control.json')
        self.assertEqual(command[command.index('--audio-install')+1],'/audio.json')
        self.assertEqual(command[command.index('--clock-mode')+1],'real-time')
    def test_final_bar_replaces_not_overlays(self):
        value=expand(validate(self.data)["examples"][0]["tracks"][0],4)
        self.assertEqual(value[-1],[49,60])
        self.assertEqual(len(value),7)
    def test_player_cannot_be_assigned_twice(self):
        self.data["examples"][0]["tracks"].append(dict(self.data["examples"][0]["tracks"][0],channel=2))
        with self.assertRaisesRegex(ValueError,"player"):
            validate(self.data)
    def test_authored_step_bounds(self):
        self.data["examples"][0]["tracks"][0]["phrase"]=[[17,48]]
        with self.assertRaisesRegex(ValueError,"phrase"):
            validate(self.data)
    def test_velocity_90_and_35_are_authored(self):
        track=self.data["examples"][0]["tracks"][0]
        track["velocity"]=90;track["velocity_overrides"]=[[44,35],[60,35]]
        self.assertEqual(validate(self.data)["examples"][0]["tracks"][0]["velocity"],90)
    def test_bar_phrases_retain_first_two_bars(self):
        track=self.data["examples"][0]["tracks"][0]
        track["bar_phrases"]=[[[1,48]],[[1,48]],[[1,48],[12,55]],[[1,48],[12,55]]]
        self.assertEqual(expand(track,4),[[1,48],[17,48],[33,48],[44,55],[49,48],[60,55]])
    def test_invalid_step_velocity_rejected(self):
        self.data["examples"][0]["tracks"][0]["velocity_overrides"]=[[44,-1]]
        with self.assertRaisesRegex(ValueError,"velocity"):
            validate(self.data)
    def test_relative_pattern_keeps_note_mask_unset(self):
        example=self.data["examples"][0];example["mode"]="relative-scale-slots"
        track=example["tracks"][0];track.pop("note");track.pop("final_bar");track.update(pattern=1,octave=0,phrase=[[1,0],[9,4]])
        example["scale_slots"]=[{"slot":1,"root":"C","root_detents":0},{"slot":2,"root":"D","root_detents":2}]
        example["phase_changes"]=[{"at_step":32,"scale_slot":2,"root":"D"}]
        example["midi_contract"]={"cycle_steps":64,"notes":[{"port":1,"status":144,"note":60,"velocity":42,"step":0,"length":.5}]}
        self.assertNotIn("note",validate(self.data)["examples"][0]["tracks"][0])
    def test_duplicate_channel_rejected(self):
        self.data["examples"][0]["tracks"].append(dict(self.data["examples"][0]["tracks"][0],voice="Oilcan 1"))
        with self.assertRaisesRegex(ValueError,"channel"):
            validate(self.data)
class DigitalIntegrity(unittest.TestCase):
    def check(self,signal):
        with patch("manual_audio.read_wav",return_value=(100,[signal,signal])):
            return metrics(Path("native.wav"),1)
    def test_quiet_signal_with_settled_tail(self):
        result=self.check([.01]*100+[0.0]*200)
        self.assertEqual(result["clipped_samples"],0)
        self.assertEqual(result["tail_rms"],0)
    def test_silent_player_rejected(self):
        with self.assertRaisesRegex(ValueError,"silent"):
            self.check([0.0]*300)
    def test_headroom_failure_rejected(self):
        with self.assertRaisesRegex(ValueError,"headroom"):
            self.check([1.0]*100+[0.0]*200)
    def test_unsettled_tail_rejected(self):
        with self.assertRaisesRegex(ValueError,"tail"):
            self.check([.02]*300)
class LiteralMusicalOutput(unittest.TestCase):
    """README Masks and Scale Editor: literal notes, velocity and length."""
    def score(self):
        return [dict(port=1,status=144,note=60,velocity=90,step=0,length=.5),
                dict(port=1,status=144,note=62,velocity=35,step=32,length=.5)]
    def packets(self):
        rows=[]
        for note in self.score():
            for status,when in ((note["status"],note["step"]),(note["status"]-16,note["step"]+note["length"])):
                rows.append(dict(index=len(rows)+1,port=1,bytes=[status,note["note"],note["velocity"]],
                                 monotonic_ns=round(when/6*1e9),logical_ns=round(when/6*1e9)))
        return rows
    def test_both_lanes_check_literal_velocity_and_pitch(self):
        for lane in ("real-time","controlled-experimental"):
            self.assertTrue(verify_midi_packets(self.packets(),self.score(),0,lane)["passed"])
    def test_equal_velocity_cannot_qualify_ghost_note(self):
        rows=self.packets();rows[2]["bytes"][2]=90
        with self.assertRaises(AssertionError):verify_midi_packets(rows,self.score(),0,"real-time")
    def test_fixed_c_cannot_qualify_scale_change(self):
        rows=self.packets();rows[2]["bytes"][1]=60
        with self.assertRaises(AssertionError):verify_midi_packets(rows,self.score(),0,"real-time")
    def test_incorrect_gate_cannot_qualify(self):
        rows=self.packets();rows[1]["monotonic_ns"]+=20000000
        with self.assertRaises(AssertionError):verify_midi_packets(rows,self.score(),0,"real-time")
    def test_extra_early_onset_is_not_a_closing_boundary(self):
        rows=self.packets()+[dict(index=5,port=1,bytes=[144,60,90],monotonic_ns=9000000000)]
        with self.assertRaisesRegex(AssertionError,"64-step boundary"):
            verify_midi_packets(rows,self.score(),0,"real-time",allow_boundary=True)
    def test_witness_mapping_keeps_literal_musical_values(self):
        example={"midi_contract":{"notes":self.score()}}
        wanted=mapped_score(example,[{"channel":1}],witness=True)
        self.assertEqual(wanted,[dict(v,status=158) for v in self.score()])

class LessonPcmRejections(unittest.TestCase):
    """Characterisation: independent declared interior acceptance boundaries."""
    @patch("manual_audio.read_wav")
    def test_no_added_ghost_activity_is_rejected(self,read):
        read.return_value=(1000,[[0.0]*14000])
        with self.assertRaisesRegex(ValueError,"audible PCM"):
            lesson_pcm({"id":"ghost-note-comparison"},[],None,{"origin_ns":0,"capture_epoch":0})
    @patch("pcm_oracle.analyse")
    @patch("manual_audio.read_wav")
    def test_fixed_c_pitch_after_slot_change_is_rejected(self,read,analyse):
        read.return_value=(1000,[[0.01]*14000])
        notes=[dict(port=2,status=145,note=n,velocity=60,step=i*8,length=.5)
               for i,n in enumerate([48,55,48,55,50,57,50,57])]
        analyse.side_effect=[([dict(note=n,time=j*.01) for j in range(9)],.02,.01)
                             for n in [48,55,48,55,48,55,48,55]]
        with self.assertRaisesRegex(ValueError,"Relative scale PCM pitch"):
            lesson_pcm({"id":"scale-slot-comparison","midi_contract":{"notes":notes}},
                       [{"channel":2,"voice":"Polyperc 1"}],None,{"origin_ns":0,"capture_epoch":0})

class ControlledLocalGeneration(unittest.TestCase):
    def test_controlled_audio_midi_command_does_not_require_or_forward_real_install(self):
        import manual_audio
        from types import SimpleNamespace
        options=SimpleNamespace(controlled_local=True,midi_real_install=None,midi_controlled_install='/qualified/control.json',
                                mod_code_root='/voices',audio_install='/audio.json')
        command=manual_audio.midi_worker_command(Path('/run'),'piece',Path('/out'),Path('/frozen'),options,'controlled-experimental')
        self.assertEqual(command[command.index('--midi-controlled-install')+1],'/qualified/control.json')
        self.assertNotIn('--midi-real-install',command)
        options.controlled_local=False
        with self.assertRaisesRegex(ValueError,'Full MIDI qualification'):
            manual_audio.midi_worker_command(Path('/run'),'piece',Path('/out'),Path('/frozen'),options,'real-time')

    def test_scoped_audio_lesson_accepts_only_the_controlled_midi_lane(self):
        import manual_publication_verify as publication
        example=dict(id='ghost-note-comparison',purpose='lesson-comparison',evidence=dict(path='/capture/mix'),
                     solo_contributions=[],musical_evidence=[dict(clock_mode='controlled-experimental',passed=True,path='/capture/midi')],
                     midi_witness=dict(passed=True),phase_observations=[],
                     lesson_pcm=dict(kind='ghost-note-interiors',passed=True))
        authored=dict(examples=[dict(id='ghost-note-comparison',purpose='lesson-comparison',tracks=[],phase_changes=[])])
        sessions=publication.check_audio_capture_scope(dict(examples=[example]),authored,controlled_local=True)
        self.assertEqual(len(sessions),2)
        with self.assertRaisesRegex(ValueError,'both MIDI lanes'):
            publication.check_audio_capture_scope(dict(examples=[example]),authored,controlled_local=False)

if __name__=="__main__":unittest.main()


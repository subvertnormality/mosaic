"""Course case helpers: the running-transport frame; characterisation outside the manual.

``musical`` must record a frame of the playing screen before it stops the transport, so a
listening step can show what a player sees while hearing the notes (README.md#typical-workflow).
These are double-driver checks of the helper's ordering and failure path; the emulator-backed
capture of the same rows is M-MANUAL-COURSE-001.
"""
import types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def load():
    namespace={};exec(compile((ROOT/'tools/manual_course_cases.py').read_text(),'course-helper','exec'),namespace)
    return namespace

class Double:
    """A driver whose MIDI follows the authored contract; the Play pad lights once play starts."""
    def __init__(self,namespace,stage,lit=True,clock_mode='controlled-experimental'):
        period,expected=namespace['CONTRACTS'][stage];self.period=period;self.events=[];self.results=[]
        # observations/logical_ns/elapse: manual_course_cases.course_audition_wait (course-v10 install, 2026-10-06)
        # polls controlled-time waits by bounded logical advances and trims retained observations.
        self.clock_mode=clock_mode;self.lit=lit;self.playing=False
        self.observations=[];self.logical_ns=0;self.elapsed=[]
        self.ui=types.SimpleNamespace(play=self.play,stop=self.stop)
        self.midi=[];index=0
        steps=sorted([(r['step']+cycle*period,r) for cycle in range(2) for r in expected]+[(2*period,expected[0])],key=lambda item:item[0])
        for step,row in steps:
            index+=1;self.midi.append(dict(index=index,port=row['port'],bytes=[row['status'],row['note'],row['velocity']],logical_ns=round(step/6*1e9)))
            index+=1;self.midi.append(dict(index=index,port=row['port'],bytes=[row['status']-16,row['note'],row['velocity']],logical_ns=round((step+row['length'])/6*1e9)))
        self.midi.sort(key=lambda m:m['logical_ns'])
        for number,m in enumerate(self.midi,1):m['index']=number
    def play(self):self.events.append('play');self.playing=True
    def stop(self):self.events.append('stop');self.playing=False
    def state(self):
        grid=[0]*128;grid[7*16]=15 if self.playing and self.lit else 2
        return dict(midi=list(self.midi) if self.playing else [],midi_count=0,grid=grid,midi_capture=dict(outstanding=0))
    def snapshot(self):return self.state()
    def elapse(self,seconds):
        self.elapsed.append(seconds);self.logical_ns+=round(seconds*1_000_000_000)
    def wait(self,predicate,timeout=3):
        state=self.state()
        if not predicate(state):raise TimeoutError('predicate never held')
        return state

class CoursePlayingFrame(unittest.TestCase):
    def setUp(self):
        self.namespace=load();self.frames=[]
        def checkpoint(c,stage,page,params=None,mask_fields=(),selected=None,leds=(),dashboard_rows=()):
            c.events.append('frame:'+stage);self.frames.append(dict(stage=stage,page=page,params=params,leds=list(leds),mask_fields=list(mask_fields)))
        self.namespace['checkpoint']=checkpoint

    def test_playing_frame_precedes_stop_and_the_midi_row(self):
        c=Double(self.namespace,'first-sound-hear')
        self.namespace['musical'](c,'first-sound-hear')
        # The planned first-sound-stopped checkpoint (manual/scene-plans-course.yaml) follows the stop and shows the authored Mask fields.
        self.assertEqual(c.events,['play','frame:first-sound-hear-playing','stop','frame:first-sound-stopped'])
        self.assertEqual([f['stage'] for f in self.frames],['first-sound-hear-playing','first-sound-stopped'])
        self.assertEqual(self.frames[1]['mask_fields'],[('note','C3'),('velocity','80'),('length','1/2')])
        self.assertEqual([r['kind'] for r in c.results],['manual-course-midi'])
        self.assertEqual(self.frames[0]['page'],'masks');self.assertEqual(self.frames[0]['params'],{'channel':1})
        self.assertEqual(self.frames[0]['leds'],[(1,8,15)],'Play pad shows its playing level, not the stopped level 2')

    def test_page_and_params_are_forwarded(self):
        c=Double(self.namespace,'first-sound-hear')
        self.namespace['musical'](c,'first-sound-hear','scale',{'slot':2})
        self.assertEqual((self.frames[0]['page'],self.frames[0]['params']),('scale',{'slot':2}))

    def test_two_section_song_records_both_sections_before_stop(self):
        c=Double(self.namespace,'song-composition-transition')
        self.namespace['musical'](c,'song-composition-transition','song_setup',{'song_slot':1},later=('song_setup',{'song_slot':2}))
        self.assertEqual(c.events,['play','frame:song-composition-transition-playing','frame:song-composition-transition-playing-slot2','stop'])
        self.assertEqual([f['params'] for f in self.frames],[{'song_slot':1},{'song_slot':2}])

    def test_unlit_play_pad_fails_instead_of_recording_a_stopped_frame(self):
        c=Double(self.namespace,'first-sound-hear',lit=False)
        with self.assertRaises(TimeoutError):self.namespace['musical'](c,'first-sound-hear')
        self.assertEqual(self.frames,[]);self.assertEqual(c.results,[]);self.assertNotIn('stop',c.events)

    def test_controlled_midi_wait_that_never_holds_fails_loudly_in_bounded_logical_steps(self):
        c=Double(self.namespace,'first-sound-hear')
        with self.assertRaisesRegex(AssertionError,'Required observable output did not arrive'):self.namespace['course_audition_wait'](c,lambda s:False,1)
        self.assertTrue(c.elapsed and all(0<step<=.1 for step in c.elapsed),'controlled waits advance logical time in bounded steps')
        self.assertGreaterEqual(c.logical_ns,1_000_000_000)

    def test_controlled_wait_observation_retention_is_bounded(self):
        c=Double(self.namespace,'first-sound-hear');c.wait_observation_limit=4096
        with self.assertRaisesRegex(ValueError,'bounded'):self.namespace['course_audition_wait'](c,lambda s:True,1)

    def test_merge_only_contract_is_the_readme_literal(self):
        """README.md#trig-merge-modes: Only plays steps trigged in more than one selected pattern (1 and 9)."""
        contract=self.namespace['CONTRACTS']['sequence-composition-merge-only']
        port1=[r['step'] for r in contract[1] if r['port']==1]
        self.assertEqual((contract[0],port1),(16,[0,8]))
        self.assertTrue(all(r['note']==60 and r['velocity']==80 for r in contract[1] if r['port']==1))

if __name__=='__main__':unittest.main()

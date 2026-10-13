import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
from manual_closure_cases import song_levels,phrase_prefix,motion_marker_changed,queued_blink_levels,mark_pixels
class SongClosureOracleTests(unittest.TestCase):
    def test_populated_is_seven_not_generic_medium(self):
        self.assertEqual(song_levels({"grid":[7,15,2]},[7,15,2]),[7,15,2])
        with self.assertRaises(AssertionError):song_levels({"grid":[8,15,2]},[7,15,2])
    def test_playback_requires_exact_pitch_velocity_and_port(self):
        notes=[dict(port=1,bytes=row) for row in [[144,60,127],[144,62,117],[144,64,107],[144,65,97]]]
        self.assertEqual(len(phrase_prefix(notes)),4)
        notes[2]["bytes"][1]=60
        with self.assertRaises(AssertionError):phrase_prefix(notes)
    def test_second_port_cannot_establish_selected_slot_output(self):
        notes=[dict(port=2,bytes=row) for row in [[144,60,127],[144,62,117],[144,64,107],[144,65,97]]]
        with self.assertRaises(AssertionError):phrase_prefix(notes)
class MotionClosureOracleTests(unittest.TestCase):
    def test_enabled_requires_observable_decoration_change(self):
        samples=[{"mark_sha256":str(i)} for i in range(6)]
        self.assertTrue(motion_marker_changed(True,samples))
        with self.assertRaises(AssertionError):motion_marker_changed(False,samples)
    def test_disabled_requires_all_sampled_marks_still(self):
        samples=[{"mark_sha256":"same"} for _ in range(6)]
        self.assertFalse(motion_marker_changed(False,samples))
        with self.assertRaises(AssertionError):motion_marker_changed(True,samples)
    def test_missing_sample_cannot_establish_still_decoration(self):
        with self.assertRaises(AssertionError):motion_marker_changed(False,[{"mark_sha256":"same"}])
    def test_clock_full_authored_motif_moves_outside_obsolete_corner(self):
        import json,base64,hashlib
        atlas=json.loads((Path(__file__).resolve().parents[2]/'manual/proposals/mini-header-atlas-v2.json').read_text())
        spec=next(x for x in atlas['screens'] if x['id']=='C04')
        hashes=[]
        for rows in spec['frames']:
            pixels=bytearray(128*64*4)
            for y,line in enumerate(rows):
                for x,char in enumerate(line):
                    value={'.':0,'a':7,'b':11,'c':15}[char]*17
                    offset=(y*128+spec['origin'][0]+x)*4
                    pixels[offset:offset+4]=bytes([value,value,value,255])
            state=dict(frame=dict(pixels_base64=base64.b64encode(pixels).decode()))
            hashes.append(hashlib.sha256(mark_pixels(state)).hexdigest())
        self.assertGreater(len(set(hashes)),1,'Clock authored motif changes outside old corner crop')
    def test_motion_public_recipe_reaches_slow_rate_and_restores_through_actual_owner(self):
        import ast,inspect,subprocess,json
        from manual_closure_cases import motion_controls
        tree=ast.parse(inspect.getsource(motion_controls))
        calls=sorted([n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='encoder_event'],key=lambda n:n.lineno)
        deltas=[ast.literal_eval(n.args[1]) for n in calls]
        root=Path(__file__).resolve().parents[2]
        source=str(root/'lib/pages/channel_edit_page/channel_edit_clock_controls.lua')
        code="""local selector={position=13};function selector:is_selected()return true end
function selector:increment()self.position=self.position+1 end
function selector:decrement()self.position=self.position-1 end
local off={is_selected=function()return false end}
local controls={clock_mod_list_selector=selector,swing_shuffle_type_selector=off,swing_selector=off,shuffle_feel_selector=off,shuffle_basis_selector=off,shuffle_amount_selector=off}
save_confirm={set_save=function()end,set_cancel=function()end}
local controller=dofile(%s).new(controls,{},{});
for _,delta in ipairs({%s})do if delta>0 then controller.handle_increment()else controller.handle_decrement()end;print(selector.position)end
"""%(json.dumps(source),','.join(map(str,deltas)))
        result=subprocess.run(['lua5.3','-e',code],capture_output=True,text=True,check=True)
        # Production division table: /1 index13; /1.5 index14; x1.3 index12.
        self.assertEqual(list(map(int,result.stdout.split())),[14,13])
class QueueBlinkOracleTests(unittest.TestCase):
    def samples(self):
        return [{"levels":[level,15,2],"logical_ns":i*400000000} for i,level in enumerate([1,7,1,7,1,7,1])]
    def test_queue_requires_temporal_blink_and_current_slot_stays_bright(self):
        samples=self.samples();self.assertEqual(queued_blink_levels(samples,True),[1,7,1,7,1,7,1])
        samples[3]["levels"][0]=15
        with self.assertRaises(AssertionError):queued_blink_levels(samples,True)
    def test_controlled_phase_samples_are_exact_not_toleranced(self):
        samples=self.samples();samples[2]["logical_ns"]+=1
        with self.assertRaises(AssertionError):queued_blink_levels(samples,True)
    def test_blink_does_not_allow_active_slot_or_empty_slot_change(self):
        samples=self.samples();samples[1]["levels"][1]=7
        with self.assertRaises(AssertionError):queued_blink_levels(samples,False)

    def real_fixture(self):
        native=[dict(kind=2,id=3,monotonic_ns=i*400000000,leds=[1 if i%2==0 else 7,15,2]) for i in range(9)]
        samples=[dict(levels=[1 if (i*30000000//400000000)%2==0 else 7,15,2],monotonic_ns=i*30000000) for i in range(109)]
        return samples,native
    def test_real_cannot_accept_stuck_native_waveform_from_alternating_snapshots(self):
        samples,native=self.real_fixture()
        for row in native:row['leds'][0]=1
        with self.assertRaises(AssertionError):queued_blink_levels(samples,False,native)
    def test_real_consumes_native_edges_without_assuming_snapshot_phase(self):
        samples,native=self.real_fixture()
        self.assertEqual(queued_blink_levels(samples,False,native),[1,7,1,7,1,7,1])
    def test_real_cannot_accept_slow_sampling_or_wrong_neighbors(self):
        samples,native=self.real_fixture();samples[1]['monotonic_ns']=350000000
        with self.assertRaises(AssertionError):queued_blink_levels(samples,False,native)
    def test_real_rejects_wrong_level_neighbors_skipped_and_overbound_edges(self):
        samples,native=self.real_fixture()
        import copy
        mutations=[]
        wrong=copy.deepcopy(native);wrong[3]['leds'][0]=8;mutations.append(wrong)
        neighbor=copy.deepcopy(native);neighbor[3]['leds'][1]=7;mutations.append(neighbor)
        missed=copy.deepcopy(native);del missed[2:4];mutations.append(missed)
        irregular=copy.deepcopy(native);irregular[3]['monotonic_ns']+=61000000;mutations.append(irregular)
        fast=copy.deepcopy(native)
        for i,row in enumerate(fast):row['monotonic_ns']=i*300000000
        mutations.append(fast)
        for events in mutations:
            with self.subTest(events=events):
                with self.assertRaises(AssertionError):queued_blink_levels(samples,False,events)

if __name__=="__main__":unittest.main()

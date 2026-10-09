"""Independent native clock/bitmap evidence characterization; no hardware timing claim."""
import base64,copy,hashlib,unittest
from pathlib import Path
import mini_phase_oracle as phase
class NativeMiniPhaseIntegrity(unittest.TestCase):
 def test_compatibility_import_uses_unchanged_contract_owned_functions(self):
  from contract import mini_phase_oracle as owner
  from ui_layer_guard import raw_sites
  for name in ('require','finite','observed_phases','native_frame','clock_receipt','phase_interval','check_stopped_phase','check_playing_phases'):
   self.assertIs(getattr(phase,name),getattr(owner,name))
   self.assertEqual(Path(getattr(phase,name).__code__.co_filename).parent,Path(__file__).parent/'contract')
  self.assertEqual(raw_sites(Path(__file__).parent/'mini_phase_oracle.py'),[])
 def fixture(self,enabled=True,tempo=90,low=.251,high=.35,pose=1):
  frames=[['a' if i%2 else 'b']*8 for i in range(8)];frames[1]=['c']*8;spec=dict(frames=frames,origin=[127,0],layout='vertical_list',loop_quarter_beats=2)
  pixels=bytearray(32768)
  for y,line in enumerate(frames[pose]):pixels[(y*128+127)*4:(y*128+127)*4+3]=bytes([17*{'.':0,'a':7,'b':11,'c':15}[line]])*3
  sha=hashlib.sha256(pixels).hexdigest();observations=[]
  for index,beat in enumerate((low,high)):
   diag=dict(beats=beat,tempo=tempo,monotonic_ns=index*100000000+100000000,clock_epoch=0)
   state=dict(frame=dict(sha256=sha,pixels_base64=base64.b64encode(pixels).decode()),grid=[0]*128,midi_count=0,midi_capture=dict(outstanding=[]),clock=dict(mode='controlled-experimental',logical_ns=index*125000000),diagnostics=diag)
   observations.append(dict(frame_revision=7,monotonic_ns=index*100000000+110000000,state=state))
  sample=dict(observation_index=1,clock_before_observation_index=0,clock_after_observation_index=1,frame_sha256=sha,frame_revision=7,monotonic_ns=210000000,clock_before=copy.deepcopy(observations[0]['state']['diagnostics']),clock_after=copy.deepcopy(observations[1]['state']['diagnostics']),native_clock=copy.deepcopy(observations[1]['state']['diagnostics']))
  event=dict(kind=1,revision=7,sha256=sha,monotonic_ns=150000000)
  return sample,observations,[event],spec,enabled,tempo,'controlled-experimental'
 def test_correct_pose_uses_native_beat_bounds_not_wall_time(self):
  args=self.fixture();result=phase.check_stopped_phase(*args);self.assertEqual(result['allowed_phases'],[1])
  sample,obs,events,spec,enabled,tempo,clock=args;events[0]['monotonic_ns']=199999999
  self.assertEqual(phase.check_stopped_phase(*args)['allowed_phases'],[1])
 def test_stopped_phase_accepts_native_tempo_change_inside_input_frame_bracket(self):
  args=list(self.fixture(low=.251,high=.35))
  args[5]=None
  args[1][0]['state']['diagnostics']['tempo']=100
  args[1][1]['state']['diagnostics']['tempo']=85.106383
  args[0]['clock_before']['tempo']=100
  args[0]['clock_after']['tempo']=85.106383
  args[0]['native_clock']['tempo']=85.106383
  result=phase.check_stopped_phase(*args)
  self.assertEqual(result['allowed_phases'],[1])
 def test_wrong_phase_real_revision_and_changed_clock_receipt_are_refused(self):
  args=self.fixture(low=.751,high=.85)
  with self.assertRaisesRegex(ValueError,'pose phase'):phase.check_stopped_phase(*args)
  args=self.fixture();args[2][0]['revision']=8
  with self.assertRaisesRegex(ValueError,'frame revision'):phase.check_stopped_phase(*args)
  args=self.fixture();args[0]['clock_before']['beats']=0
  with self.assertRaisesRegex(ValueError,'clock receipt'):phase.check_stopped_phase(*args)
 def test_stale_frame_whole_loop_epoch_and_missing_source_clock_cannot_pass(self):
  args=self.fixture();args[2][0]['monotonic_ns']=90000000
  with self.assertRaisesRegex(ValueError,'bracket'):phase.check_stopped_phase(*args)
  args=self.fixture(low=0,high=2)
  with self.assertRaisesRegex(ValueError,'bounded'):phase.check_stopped_phase(*args)
  args=self.fixture();args[1][-1]['state']['diagnostics']['clock_epoch']=1;args[0]['clock_after']['clock_epoch']=1;args[0]['native_clock']['clock_epoch']=1
  with self.assertRaisesRegex(ValueError,'epoch'):phase.check_stopped_phase(*args)
 def test_240_can_skip_displayed_phases_but_wrong_shift_is_not_free(self):
  args=self.fixture(tempo=240,low=.1,high=.6);result=phase.check_stopped_phase(*args);self.assertEqual(result['allowed_phases'],[0,1,2])
  args=self.fixture(tempo=240,low=1.1,high=1.6)
  with self.assertRaisesRegex(ValueError,'pose phase'):phase.check_stopped_phase(*args)
 def test_240_sampler_keeps_native_receipts_within_strict_phase_limit(self):
  import base64,hashlib,importlib
  sampling=importlib.import_module("contract.mini_header_animation_ui")
  spec={"frames":[],"origin":[120,0],"layout":"vertical_list","loop_quarter_beats":2}
  for pose in range(8):
   row="."*pose+"c"+"."*(7-pose)
   spec["frames"].append([row]*8)
  palette={".":0,"a":7,"b":11,"c":15}
  captured=((296.208537153,297.355370486),(270.79205625,271.640722917))
  for low,high in captured:
   with self.subTest(low=low),self.assertRaisesRegex(ValueError,"bounded"):
    phase.phase_interval(low,high,spec,3)
  class Driver:
   clock_mode="real-time"
   def __init__(self):
    self.now=0;self.revision=0;self.observations=[];self.events=[];self.results=[];self.overhead=87166667
   def elapse(self,seconds):self.now+=round(seconds*1e9)
   def snapshot(self):
    self.revision+=1;draw=self.now;pose=int(draw*240/60*4/1e9)%8
    pixels=bytearray(32768)
    for y,line in enumerate(spec["frames"][pose]):
     for x,char in enumerate(line):
      i=(y*128+120+x)*4;pixels[i:i+3]=bytes([17*palette[char]])*3
    raw=bytes(pixels);sha=hashlib.sha256(raw).hexdigest()
    beats=self.now*240/60/1e9
    diag={"beats":beats,"tempo":240.0,"monotonic_ns":self.now,"clock_epoch":0}
    state={"frame":{"sha256":sha,"pixels_base64":base64.b64encode(raw).decode(),"width":128,"height":64},
           "pose":pose,"grid":[0]*128,"midi_count":0,"midi_capture":{"outstanding":[]},
           "clock":{"mode":"real-time","logical_ns":None},"diagnostics":diag}
    self.observations.append({"frame_revision":self.revision,"monotonic_ns":self.now,"state":state})
    self.events.append({"kind":1,"revision":self.revision,"sha256":sha,"monotonic_ns":draw})
    self.now+=self.overhead
    return state
   def wait(self,predicate,timeout=1):
    state=self.snapshot()
    if not predicate(state):raise AssertionError("mock wait did not reach a newer native clock/frame")
    return state
  old={name:getattr(sampling,name) for name in ("atlas","wait_normal_footer","require_icon","outside_icon","native_events")}
  sampling.atlas=lambda:{"C04":spec}
  sampling.wait_normal_footer=lambda *args:None
  sampling.require_icon=lambda state,page,enabled:[state["pose"]]
  sampling.outside_icon=lambda data,spec:b"unchanged body"
  sampling.native_events=lambda c:c.events
  try:
   driver=Driver()
   proof=sampling.sample(driver,"C04",True,5,tempo=240)
   self.assertEqual(len(driver.results),1)
   self.assertEqual(len(driver.results[0]["samples"]),40)
   self.assertTrue(all(row["phase_check"]["passed"] for row in driver.results[0]["samples"]))
   self.assertGreater(len(set(driver.results[0]["observed_poses"])),1)
   if hasattr(sampling,"sample_delays"):
    self.assertEqual(sampling.sample_delays(240),(.115,.010))
    self.assertEqual(sum(sampling.sample_delays(240)),.125)
  finally:
   for name,value in old.items():setattr(sampling,name,value)
 def test_cached_frame_is_reacquired_only_inside_new_clock_bracket(self):
  import importlib
  sampling=importlib.import_module("contract.mini_header_animation_ui")
  helper=getattr(sampling,"_frame_after_clock_receipt",None)
  self.assertTrue(callable(helper),"sampler must validate cached-frame receipts")
  if not callable(helper):return
  class Driver:
   def __init__(self):
    self.observations=[{"frame_revision":7}]
    self.pending=[{"frame_revision":7,"frame":{"sha256":"old"},"diagnostics":{"monotonic_ns":130}},
                  {"frame_revision":8,"frame":{"sha256":"new"},"diagnostics":{"monotonic_ns":180}}]
    self.events=[{"kind":1,"revision":7,"sha256":"old","monotonic_ns":90}]
   def snapshot(self):
    state=self.pending.pop(0);self.observations.append({"frame_revision":state["frame_revision"]});return state
   def wait(self,predicate,timeout=1):
    state=self.pending.pop(0);self.observations.append({"frame_revision":state["frame_revision"]})
    self.events.append({"kind":1,"revision":8,"sha256":"new","monotonic_ns":150})
    self.asserted=predicate(state)
    if not self.asserted:raise AssertionError("waited frame did not advance")
    return state
  c=Driver();old_events=sampling.native_events;old_icon=sampling.require_icon
  sampling.native_events=lambda driver:driver.events
  sampling.require_icon=lambda state,page,enabled:[0]
  try:
   before={"diagnostics":{"monotonic_ns":100}}
   stale={"frame_revision":7,"frame":{"sha256":"old"},"diagnostics":{"monotonic_ns":100}}
   result=helper(c,"C04",before,0,before["diagnostics"],stale)
   lower,lower_index,clock,frame,events=result
   draw=next(e["monotonic_ns"] for e in events if e["revision"]==frame["frame_revision"])
   self.assertGreater(lower_index,0)
   self.assertLess(clock["monotonic_ns"],draw)
   self.assertLess(draw,frame["diagnostics"]["monotonic_ns"])
   self.assertEqual(frame["frame_revision"],8)
  finally:
   sampling.native_events=old_events;sampling.require_icon=old_icon
 def test_reanchor_snapshot_revision_is_not_mistaken_for_a_fresh_frame(self):
  import importlib
  sampling=importlib.import_module("contract.mini_header_animation_ui")
  helper=sampling._frame_after_clock_receipt
  class Driver:
   def __init__(self):
    self.observations=[{"frame_revision":7}];self.events=[];self.revision=7
    stale={"frame_revision":7,"frame":{"sha256":"sha7"},"diagnostics":{"monotonic_ns":95}}
    self.events.append(dict(kind=1,revision=7,sha256="sha7",monotonic_ns=90))
    self.last_state=stale;self.lower_ns=100
   def state(self,revision,draw_ns,clock_ns):
    frame={"sha256":f"sha{revision}"};diag={"monotonic_ns":clock_ns}
    state={"frame":frame,"diagnostics":diag,"revision":revision}
    self.events.append(dict(kind=1,revision=revision,sha256=frame["sha256"],monotonic_ns=draw_ns))
    return state
   def observe(self,state):self.observations.append({"frame_revision":state["revision"]})
   def snapshot(self):
    self.revision+=1;draw=self.lower_ns+50;clock=draw+50
    self.last_state=self.state(self.revision,draw,clock);self.lower_ns=clock
    self.observe(self.last_state);return self.last_state
   def wait(self,predicate,timeout=1):
    # The first poll exposes the frame already present in the baseline snapshot.
    self.observe(self.last_state)
    if predicate(self.last_state):return self.last_state
    # Only the next native draw is strictly after that baseline clock receipt.
    self.revision+=1;draw=self.lower_ns+10;clock=draw+10
    self.last_state=self.state(self.revision,draw,clock);self.lower_ns=clock
    self.observe(self.last_state)
    if not predicate(self.last_state):raise AssertionError("wait did not reach a fresh native frame")
    return self.last_state
  driver=Driver();old_events=sampling.native_events;old_icon=sampling.require_icon
  sampling.native_events=lambda c:c.events
  sampling.require_icon=lambda state,page,enabled:[0]
  try:
   before={"diagnostics":{"monotonic_ns":100}}
   stale=driver.last_state
   lower,index,clock,frame,events=helper(driver,"C04",before,0,before["diagnostics"],stale)
   draw=next(event["monotonic_ns"] for event in events if event.get("revision")==frame["revision"] and event.get("sha256")==frame["frame"]["sha256"])
   self.assertGreater(index,0)
   self.assertEqual(frame["revision"],9)
   self.assertGreater(draw,clock["monotonic_ns"])
  finally:
   sampling.native_events=old_events;sampling.require_icon=old_icon
 def test_off_keeps_native_rest_identity_without_fabricated_fresh_redraw(self):
  args=self.fixture(enabled=False,pose=0);args[2][0]['monotonic_ns']=1
  result=phase.check_stopped_phase(*args);self.assertEqual(result['clock_applicable'],False)
  args=self.fixture(enabled=False,pose=1)
  with self.assertRaisesRegex(ValueError,'rest'):phase.check_stopped_phase(*args)
 def test_real_lane_uses_same_native_beats_without_logical_time_substitution(self):
  args=list(self.fixture());args[-1]='real-time'
  for observation in args[1]:observation['state']['clock']=dict(mode='real-time',logical_ns=None)
  self.assertEqual(phase.check_stopped_phase(*args)['allowed_phases'],[1])
class NativePlayingMiniPhaseIntegrity(unittest.TestCase):
 def fixture(self,clock='controlled-experimental'):
  builder=NativeMiniPhaseIntegrity();samples=[];observations=[];events=[]
  for index,pose in enumerate((0,1)):
   sample,obs,frames,spec,*unused=builder.fixture(pose=pose);sample['observation_index']=index*2+1;sample['frame_revision']=7+index;sample['monotonic_ns']=210000000+index*100000000
   for observation in obs:observation['frame_revision']=7+index;observation['state']['clock']['mode']=clock
   obs[-1]['monotonic_ns']=sample['monotonic_ns'];frames[0]['revision']=7+index;frames[0]['monotonic_ns']=150000000+index*120000000
   sample['matching_poses']=[i for i,frame in enumerate(spec['frames']) if frame==spec['frames'][pose]]
   observations.extend(obs);samples.append(sample);events.extend(frames)
  kind=11 if clock=='controlled-experimental' else 3
  events.append(dict(kind=kind,index=1,port=1,bytes=[250],monotonic_ns=80000000,logical_ns=80000000))
  for index in range(13):
   ns=100000000+round(index/36*1e9);events.append(dict(kind=kind,index=index+2,port=1,bytes=[248],monotonic_ns=ns,logical_ns=ns))
  events.append(dict(kind=kind,index=15,port=1,bytes=[252],monotonic_ns=500000000,logical_ns=500000000));events.sort(key=lambda item:item['monotonic_ns'])
  return samples,observations,events,spec,0,15,clock,90
 def test_real_and_controlled_playing_use_actual_f8_ticks_and_multiple_poses(self):
  for clock in ('real-time','controlled-experimental'):
   proof=phase.check_playing_phases(*self.fixture(clock));self.assertEqual(proof['active_frames'],2);self.assertEqual(proof['clock_ticks'],13)
 def test_missing_clock_start_bad_cadence_or_wrong_phase_refused(self):
  args=self.fixture();args[2][:]=[event for event in args[2] if event.get('bytes')!=[250]]
  with self.assertRaisesRegex(ValueError,'Start/Stop'):phase.check_playing_phases(*args)
  args=self.fixture();next(event for event in args[2] if event.get('bytes')==[248])['logical_ns']+=20000000
  with self.assertRaisesRegex(ValueError,'cadence'):phase.check_playing_phases(*args)
  args=self.fixture();args[0][-1]['monotonic_ns']=480000000;args[1][-1]['monotonic_ns']=480000000;next(event for event in args[2] if event.get('revision')==8)['monotonic_ns']=450000000
  with self.assertRaisesRegex(ValueError,'pose phase'):phase.check_playing_phases(*args)
 def test_pre_start_post_stop_frames_are_literal_only_and_do_not_fake_diversity(self):
  args=self.fixture();args[0][0]['monotonic_ns']=70000000;args[1][1]['monotonic_ns']=70000000;next(event for event in args[2] if event.get('revision')==7)['monotonic_ns']=50000000
  with self.assertRaisesRegex(ValueError,'distinct playing'):phase.check_playing_phases(*args)
if __name__=='__main__':unittest.main()

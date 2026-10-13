"""Independent native clock/bitmap evidence characterization; no hardware timing claim."""
import base64,copy,hashlib,unittest
from pathlib import Path
import mini_phase_oracle as phase
class NativeMiniPhaseIntegrity(unittest.TestCase):
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

"""Independent native musical phase and literal authored bitmap acceptance.

Native beat/F8 intervals bound the draw; elapsed host time never creates a beat.
Phase ambiguity of identical authored bitmaps and skipped12Hz display frames is
reported explicitly. This is emulator evidence, never hardware scheduling proof.
"""
import base64,hashlib,math

def require(condition,message):
 if not condition:raise ValueError(message)
def finite(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)
def observed_phases(state,spec):
 data=base64.b64decode(state['frame']['pixels_base64']);require(len(data)==32768 and hashlib.sha256(data).hexdigest()==state['frame']['sha256'],'Mini actual frame bytes/hash differ')
 left=121 if spec['layout'] in ('overview_masks','overview_params','dashboard') else 96;origin=spec['origin'];palette={'.':0,'a':7,'b':11,'c':15}
 require(len(origin)==2 and origin[1]==0 and left<=origin[0]<128,'Invalid literal mini footprint')
 def band(pixels):return bytes(pixels[(y*128+x)*4+k] for y in range(8) for x in range(left,128) for k in range(3))
 targets=[]
 for frame in spec['frames']:
  require(len(frame)==8 and all(len(line)==128-origin[0] and set(line)<=set(palette) for line in frame),'Invalid literal mini bitmap')
  pixels=bytearray(32768)
  for y,line in enumerate(frame):
   for x,letter in enumerate(line):
    i=(y*128+origin[0]+x)*4;pixels[i:i+3]=bytes([17*palette[letter]])*3
  targets.append(band(pixels))
 phases=[i for i,target in enumerate(targets) if band(data)==target];require(phases,'Mini literal native bitmap absent');return phases

def native_frame(sample,observations,events):
 index=sample.get('observation_index');require(type(index)is int and 0<=index<len(observations),'Missing native mini frame observation')
 observation=observations[index];state=observation['state'];require(sample.get('frame_sha256')==state['frame']['sha256'] and sample.get('frame_revision')==observation['frame_revision'] and sample.get('monotonic_ns')==observation['monotonic_ns'],'Changed native mini frame revision receipt')
 matches=[event for event in events if event.get('kind')==1 and event.get('revision')==observation['frame_revision'] and event.get('sha256')==state['frame']['sha256']]
 require(len(matches)==1 and type(matches[0].get('monotonic_ns'))is int,'Missing exact actual native frame revision');return observation,state,matches[0]
def clock_receipt(item,name,observations):
 index=item.get('clock_'+name+'_observation_index');require(type(index)is int and 0<=index<len(observations),'Missing native clock bracket observation')
 observation=observations[index];diag=observation['state'].get('diagnostics',{});clock={key:diag.get(key) for key in ('beats','tempo','monotonic_ns','clock_epoch')}
 require(item.get('clock_'+name)==clock,'Changed raw native clock receipt')
 require(finite(clock['beats']) and clock['beats']>=0 and finite(clock['tempo']) and clock['tempo']>0 and type(clock['monotonic_ns'])is int and type(clock['clock_epoch'])is int,'Invalid native selected musical clock')
 return index,observation,clock

def phase_interval(low,high,spec,max_pose_widths,precision_beats=1e-9):
 count=len(spec['frames']);loop=spec['loop_quarter_beats'];require(count>=2 and finite(loop) and loop>0 and finite(low) and finite(high) and 0<=low<=high,'Invalid native phase beat interval')
 width=(high-low)*count/loop;require(width<=max_pose_widths+1e-8,'Native phase bracket is not bounded below a whole loop')
 # Native beat diagnostics serialize nine decimal places. Expand by1e-9 beat
 # only at exact phase boundaries, never by host time or a redraw tolerance.
 first=math.floor(max(0,low-precision_beats)*count/loop);last=math.floor((high+precision_beats)*count/loop)
 return sorted({index%count for index in range(first,last+1)})
def check_stopped_phase(sample,observations,native_events,spec,enabled,tempo,clock_mode):
 require(type(enabled)is bool and tempo in (40,90,240),'Unsupported authored stopped mini tempo/source')
 image,state,event=native_frame(sample,observations,native_events);phases=observed_phases(state,spec)
 before_index,before,low=clock_receipt(sample,'before',observations);after_index,after,high=clock_receipt(sample,'after',observations);image_index=sample['observation_index']
 require(before_index<image_index<=after_index and before['state']['clock']['mode']==state['clock']['mode']==after['state']['clock']['mode']==clock_mode,'Native clock/frame observation order or mode differs')
 require(low['clock_epoch']==high['clock_epoch'] and low['tempo']==high['tempo']==tempo,'Native clock epoch/tempo changed across frame')
 require(low['beats']<=high['beats'] and low['monotonic_ns']<=high['monotonic_ns'],'Native selected clock moved backwards')
 diag=state.get('diagnostics',{});require(sample.get('native_clock')=={key:diag.get(key) for key in ('beats','tempo','monotonic_ns','clock_epoch')},'Changed selected-frame native clock receipt')
 require(state['midi_capture']['outstanding']==[] and before['state']['midi_count']==state['midi_count']==after['state']['midi_count'] and before['state']['grid']==state['grid']==after['state']['grid'],'Stopped native phase emitted music or changed grid')
 if not enabled:
  require(0 in phases,'Motion Off must preserve authored native rest pose')
  return dict(passed=True,clock_applicable=False,reason='Motion Off retains actual native rest; a cached rest frame need not redraw',matching_phases=phases,allowed_phases=[0],frame_revision=event['revision'])
 require(low['monotonic_ns']<=event['monotonic_ns']<=high['monotonic_ns'],'Actual native draw is outside musical clock bracket')
 allowed=phase_interval(low['beats'],high['beats'],spec,3 if tempo==240 else 2);require(bool(set(phases)&set(allowed)),'Literal mini pose phase differs from native musical clock bracket')
 return dict(passed=True,clock_applicable=True,source='native-selected-norns-clock',transport='stopped',clock_mode=clock_mode,clock_epoch=low['clock_epoch'],tempo=tempo,beat_bounds=[low['beats'],high['beats']],allowed_phases=allowed,matching_phases=phases,frame_revision=event['revision'],native_draw_ns=event['monotonic_ns'],precision='bounded native beat interval; identical bitmap phases remain ambiguous',skipped_display_poses_allowed=tempo==240,hardware_timing_equivalent=False)

def check_playing_phases(samples,observations,native_events,spec,midi_start_index,midi_end_index,clock_mode,tempo=90):
 require(type(midi_start_index)is int and type(midi_end_index)is int and 0<=midi_start_index<midi_end_index and tempo==90,'Invalid authored playing phase clock/packet scope')
 kind=11 if clock_mode=='controlled-experimental' else 3;key='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns';tolerance=2e-9 if clock_mode=='controlled-experimental' else .01
 packets=[event for event in native_events if event.get('kind')==kind and event.get('port')==1 and midi_start_index<event.get('index',0)<=midi_end_index];packets.sort(key=lambda event:event['index'])
 starts=[event for event in packets if event.get('bytes')==[250]];stops=[event for event in packets if event.get('bytes')==[252]]
 require(len(starts)==len(stops)==1 and starts[0]['index']<stops[0]['index'],'Playing phase needs one actual public MIDI Start/Stop')
 start,stop=starts[0],stops[0];ticks=[event for event in packets if event.get('bytes')==[248] and start['index']<event['index']<stop['index']]
 require(len(ticks)>=2 and all(ticks[i]['index']<ticks[i+1]['index'] for i in range(len(ticks)-1)),'Playing phase lacks actual emitted MIDI clock pulses')
 require(all(key in event and abs((event[key]-ticks[0][key])/1e9-i/36)<=tolerance for i,event in enumerate(ticks)),'Playing emitted24-PPQN clock cadence differs')
 notes=[event for event in packets if len(event.get('bytes',[]))==3 and 144<=event['bytes'][0]<=159 and event['bytes'][2]>0]
 for i,note in enumerate(notes):
  preceding=[j for j,tick in enumerate(ticks) if tick['index']<note['index']]
  require(preceding and preceding[-1]==6*i and abs((note[key]-ticks[0][key])/1e9-i/6)<=tolerance,'Playing native note/F8 transport origin differs')
 frames=[];distinct=set()
 for sample in samples:
  observation,state,event=native_frame(sample,observations,native_events);phases=observed_phases(state,spec);require(sample.get('matching_poses')==phases,'Playing stored bitmap phases differ')
  require(event['monotonic_ns']<=observation['monotonic_ns'],'Playing native frame was not yet drawn at observation')
  if not start['monotonic_ns']<=observation['monotonic_ns']<stop['monotonic_ns'] or not start['monotonic_ns']<=event['monotonic_ns']<stop['monotonic_ns']:
   frames.append(dict(applicable=False,reason='Actual observation/draw outside public playing Start/Stop',frame_revision=event['revision'],matching_phases=phases));continue
  preceding=[i for i,tick in enumerate(ticks) if tick['monotonic_ns']<=event['monotonic_ns']];tick=preceding[-1] if preceding else -1
  low=max(tick,0)/24;high=max(tick+1,0)/24;allowed=phase_interval(low,high,spec,1,precision_beats=0)
  require(bool(set(allowed)&set(phases)),'Playing literal mini pose phase differs from actual emitted F8 transport')
  distinct.add(tuple(spec['frames'][phases[0]]));frames.append(dict(applicable=True,frame_revision=event['revision'],native_draw_ns=event['monotonic_ns'],clock_tick=tick,beat_bounds=[low,high],allowed_phases=allowed,matching_phases=phases))
 require(len(distinct)>1,'Need multiple distinct playing native mini poses')
 return dict(passed=True,source='public-midi-clock-output',transport='playing',clock_mode=clock_mode,tempo=90,clock_ticks=len(ticks),active_frames=sum(frame['applicable'] for frame in frames),distinct_poses=len(distinct),frames=frames,precision='actual MIDI24-PPQN pulse interval; no elapsed-time beat estimate',complete_pose_coverage=False,hardware_timing_equivalent=False)

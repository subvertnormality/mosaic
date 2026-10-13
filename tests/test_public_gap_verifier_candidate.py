import importlib.util, json, tempfile, unittest, sys
from pathlib import Path
CANDIDATE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CANDIDATE/'tools'))
spec=importlib.util.spec_from_file_location('gapverify',CANDIDATE/'tools/manual_native_public_gap_verify.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)

class PublicGapCachedVerifier(unittest.TestCase):
 def make(self,kind,reset=False):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
  path=Path(temp.name);(path/'native').mkdir();events=[];rows=[]
  def add(data,ns):
   i=len(rows)+1;rows.append(dict(index=i,port=1,bytes=data,logical_ns=ns));events.append(dict(kind=11,index=i,port=1,bytes=data,logical_ns=ns))
  if kind=='manual-repeat-reset-public-midi':
   expected=[]
   for tick in range(1549):
    origin=(tick//1536)*1536 if reset else 0
    if (tick-origin)%216==0:
     n=(tick-origin)//216%3;expected.append((tick,[144,[60,62,64][n],[127,117,107][n]]))
   for tick,msg in expected:
    add(msg,round(tick*1e9/144));add([128,msg[1],msg[2]],round((tick+24)*1e9/144))
   row=dict(kind=kind,passed=True,citation='manual:reset-at-pattern-repeat',repeat_reset=reset,option_value='On' if reset else 'Off',expected_ticks=[t for t,_ in expected],exact_note_ons=[dict(port=1,bytes=m) for _,m in expected],complete_channel_midi_count=len(rows),complete_note_pair_count=len(expected),note_on_count=len(expected),complete_midi_stream=True,dropped=0,timing_tolerance_ns=2,complete_channel_midi=rows)
   supporting=[dict(kind='selected-menu-option-row',label='Reset on pattern repeat',value=row['option_value'],citation=row['citation'],matched=True)]
  else:
   pitches=[60,62,65,69];phrase=[(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])];expected=phrase*2+[phrase[0]]
   for port,msg in expected:
    add(msg,(len(rows)//2)*166666667);add([128,msg[1],msg[2]],(len(rows)//2)*166666667+166666667)
   row=dict(kind=kind,passed=True,citation='manual:snap-note-masks-to-scale',snap=True,option_value='On',authored_masks=['C#3','D#3','F#3','A#3'],output_pitches=pitches,dropped=0,exact_note_ons=[dict(port=p,bytes=m) for p,m in expected],complete_channel_midi=rows)
   supporting=[dict(kind='selected-menu-option-row',label='Snap note masks to scale',value='On',citation=row['citation'],matched=True)]
   supporting += [dict(kind='selected-mask',citation=row['citation'],held_step=i,value=n) for i,n in enumerate(row['authored_masks'],1)]
  (path/'native/native-events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
  results=[row]+supporting;step=dict(output=dict(binding=dict(assertion_index=0,assertion=row)))
  return path,row,results,step
 def test_repeat_reset_accepts_exact_complete_stream_including_boundary_notes(self):
  path,row,results,step=self.make('manual-repeat-reset-public-midi',True)
  verify.verify(step,[],path,'controlled-experimental',results)
  self.assertEqual(row['expected_ticks'][-2:],[1512,1536])
  bad=dict(row);bad['expected_ticks']=bad['expected_ticks'][:-2]+[1536]
  results[0]=bad;step['output']['binding']['assertion']=bad
  with self.assertRaisesRegex(ValueError,'schedule|result'):verify.verify(step,[],path,'controlled-experimental',results)
 def test_snap_rejects_missing_or_changed_native_midi_event(self):
  path,row,results,step=self.make('manual-snap-mask-public-midi')
  verify.verify(step,[],path,'controlled-experimental',results)
  events=[json.loads(line) for line in (path/'native/native-events.jsonl').read_text().splitlines()]
  events[2]['bytes'][1]=63
  (path/'native/native-events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
  with self.assertRaisesRegex(ValueError,'native packet'):verify.verify(step,[],path,'controlled-experimental',results)
 def test_new_custom_kinds_are_fail_closed_whitelist_entries(self):
  from importlib.util import spec_from_file_location,module_from_spec
  sys.path.insert(0,str(CANDIDATE/'tools')); pub=module_from_spec(spec_from_file_location('manual_publication_verify',CANDIDATE/'tools/manual_publication_verify.py'));pub.__spec__.loader.exec_module(pub)
  for kind in ('manual-repeat-reset-public-midi','manual-snap-mask-public-midi','manual-ui-motion-public-frames','manual-ui-motion-public-midi','manual-ui-motion-midi-pair'):pub.check_custom_kind(kind)
  with self.assertRaisesRegex(ValueError,'Unsupported'):pub.check_custom_kind('manual-fabricated-public-gap')
if __name__=='__main__':unittest.main()

class PublicMotionFrameCachedVerifier(unittest.TestCase):
 def frame_fixture(self):
  import base64,hashlib
  atlas=json.loads((Path('/home/andy/mosaic-manual-1.4.0/tests/behaviour/contract/mini_header_atlas_v2.json')).read_text())
  spec=next(s for s in atlas['screens'] if s['id']=='C04')
  levels={'.':0,'a':119,'b':187,'c':255};pixels=[];samples=[];frames=[];hashes=[];times=[]
  for j in range(19):
   rgba=bytearray(128*64*4)
   for i in range(0,len(rgba),4):rgba[i+3]=255
   for y,line in enumerate(spec['frames'][0]):
    for x,ch in enumerate(line):
     value=levels[ch];i=(y*128+(108+x))*4;rgba[i:i+4]=bytes([value,value,value,255])
   b=bytes(rgba);sha=hashlib.sha256(b).hexdigest();roi=[b[(y*128+x)*4] for y in range(8) for x in range(108,128)]
   times.append(j*83333333);frames.append(roi);hashes.append(sha)
   samples.append({'backend':'native','fidelity':'native-norns','state':{'frame':{'pixels_base64':base64.b64encode(b).decode(),'sha256':sha},'clock':{'logical_ns':times[-1]}}})
  other=bytearray()
  b=base64.b64decode(samples[0]['state']['frame']['pixels_base64'])
  for y in range(64):
   for x in range(128):
    if not (108<=x<128 and y<8):
     i=(y*128+x)*4;other.extend(b[i:i+4])
  outside=hashlib.sha256(other).hexdigest()
  rasters=[]
  for frame in spec['frames']:
   rasters.append(bytes(levels[ch] for line in frame for ch in line))
  uniq=[]
  for x in rasters:
   if x not in uniq:uniq.append(x)
  row={'kind':'manual-ui-motion-public-frames','passed':True,'citation':'manual:ui-motion','enabled':False,'screen':'C04','region':{'x0':108,'y0':0,'x1':128,'y1':8},'sample_count':19,'clock_sample_period_ns':83333333,'source_clock_tempo_bpm':90,'atlas_frame_count':8,'atlas_loop_beats':2,'atlas_unique_pose_count':5,'atlas_pose_raster_sha256':[hashlib.sha256(x).hexdigest() for x in uniq],'observation_indices':list(range(19)),'clock_logical_ns':times,'frame_sha256s':hashes,'frames':frames,'outside_roi_sha256':outside,'source_pose_coverage':[0]}
  return samples,row
 def test_off_frame_proof_uses_actual_frame_and_source_default_pixels(self):
  samples,row=self.frame_fixture();counter=dict(row,enabled=True);option={'kind':'selected-menu-option-row','label':'UI motion','value':'Off','citation':'manual:ui-motion','matched':True};results=[row,counter,option];step={'output':{'binding':{'assertion_index':0,'assertion':row}}}
  with tempfile.TemporaryDirectory() as d:
   Path(d,'native').mkdir();Path(d,'native/native-events.jsonl').write_text('')
   verify.verify(step,samples,d,'controlled-experimental',results)
   changed=json.loads(json.dumps(row));changed['frames'][3][0]=1
   results[0]=changed;step['output']['binding']['assertion']=changed
   with self.assertRaisesRegex(ValueError,'ROI pixels'):verify.verify(step,samples,d,'controlled-experimental',results)

 def test_on_frames_follow_all_ordered_atlas_phases_and_reject_phase_mutation(self):
  import base64,hashlib
  samples,row=self.frame_fixture()
  spec=next(x for x in json.loads(Path('/home/andy/mosaic-manual-1.4.0/tests/behaviour/contract/mini_header_atlas_v2.json').read_text())['screens'] if x['id']=='C04')
  levels={'.':0,'a':119,'b':187,'c':255};rasters=[bytes(levels[ch] for line in f for ch in line) for f in spec['frames']]
  poses=[int(j*83333333/1e9*6+1e-7)%8 for j in range(19)]
  row.update(enabled=True,distinct_public_frames=5,source_pose_coverage=list(range(8)),source_pose_indices=poses,source_phase_consistent=True)
  row['frames']=[];row['frame_sha256s']=[]
  for j,(sample,pose) in enumerate(zip(samples,poses)):
   rgba=bytearray(base64.b64decode(sample['state']['frame']['pixels_base64']))
   for y in range(8):
    for x in range(20):
     value=rasters[pose][y*20+x];i=(y*128+108+x)*4;rgba[i:i+4]=bytes([value,value,value,255])
   raw=bytes(rgba);sha=hashlib.sha256(raw).hexdigest();sample['state']['frame']={'pixels_base64':base64.b64encode(raw).decode(),'sha256':sha}
   row['frame_sha256s'].append(sha);row['frames'].append([raw[(y*128+x)*4] for y in range(8) for x in range(108,128)])
  counter=dict(row,enabled=False);option={'kind':'selected-menu-option-row','label':'UI motion','value':'On','citation':'manual:ui-motion','matched':True};results=[row,counter,option];step={'output':{'binding':{'assertion_index':0,'assertion':row}}}
  with tempfile.TemporaryDirectory() as d:
   Path(d,'native').mkdir();Path(d,'native/native-events.jsonl').write_text('')
   verify.verify(step,samples,d,'controlled-experimental',results)
   bad=json.loads(json.dumps(row));bad['source_pose_indices'][1],bad['source_pose_indices'][2]=bad['source_pose_indices'][2],bad['source_pose_indices'][1]
   results[0]=bad;step['output']['binding']['assertion']=bad
   with self.assertRaisesRegex(ValueError,'source poses|source clock phase'):verify.verify(step,samples,d,'controlled-experimental',results)

class PublicMotionMidiCachedVerifier(unittest.TestCase):
 def fixture(self):
  temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);path=Path(temp.name);(path/'native').mkdir()
  expected=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]*2+[(60,127)]]
  entries=[];events=[];idx=0
  for i,(port,on) in enumerate(expected):
   attack=round(i*24*1e9/144);release=round((i+1)*24*1e9/144) if i<8 else attack+1000000
   for data,when in ((on,attack),([128,on[1],on[2]],release)):
    idx+=1;entries.append({'port':port,'bytes':data,'logical_ns':when})
    events.append({'kind':11,'index':idx,'port':port,'bytes':data,'logical_ns':when})
  idx+=1;events.append({'kind':11,'index':idx,'port':1,'bytes':[252],'logical_ns':entries[-1]['logical_ns']})
  (path/'native/native-events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
  row={'kind':'manual-ui-motion-public-midi','passed':True,'citation':'manual:ui-motion','enabled':True,'timing_tolerance_ns':2,'complete_midi_stream':True,'dropped':0,'gate_ticks':[24]*8,'exact_note_ons':[{'port':p,'bytes':b} for p,b in expected],'note_on_count':9,'complete_note_pair_count':9,'natural_gate_count':8,'relative_channel_midi':entries,'final_gate_policy':'stopped-after-extra-onset','final_gate_matches_stop_logical_ns':True,'stop_grid_press_count':2,'final_gate_duration_ns':1000000,'final_gate_duration_less_than_one_tick':True}
  return path,row,[row],{'output':{'binding':{'assertion_index':0,'assertion':row}}}
 def test_exact_motion_gates_and_stop_truncated_last_gate(self):
  path,row,results,step=self.fixture();verify.verify(step,[],path,'controlled-experimental',results)
  events=[json.loads(x) for x in (path/'native/native-events.jsonl').read_text().splitlines()]
  events[-1]['logical_ns']+=1;(path/'native/native-events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
  with self.assertRaisesRegex(ValueError,'Stop'):verify.verify(step,[],path,'controlled-experimental',results)

 def test_self_consistent_gate_between_one_and_24_ticks_is_rejected(self):
  path,row,results,step=self.fixture()
  events=[json.loads(x) for x in (path/'native/native-events.jsonl').read_text().splitlines()]
  release_ns=round(8*24*1e9/144)+10000000
  events[-2]['logical_ns']=release_ns;events[-1]['logical_ns']=release_ns
  row['relative_channel_midi'][-1]['logical_ns']=release_ns
  row['final_gate_duration_ns']=10000000
  (path/'native/native-events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
  with self.assertRaisesRegex(ValueError,'shorter than one source tick'):
   verify.verify(step,[],path,'controlled-experimental',results)

"""Verify manual publications against pinned native evidence and current authoring."""
import copy,hashlib,json,subprocess,tempfile,shutil
from pathlib import Path
import yaml
from manual_book import ROOT,MANUAL,load,compile_book,capture_catalogue
from manual_model import source_hash
from manual_verify import check_frame,digest

def canonical_hash(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def performance_contract(data):
 result=copy.deepcopy({k:v for k,v in data.items() if k!='feature'})
 for field in ('title','description'):result.get('audio',{}).pop(field,None)
 for scene in result.get('scenes',[]):
  scene.pop('title',None)
  for step in scene.get('steps',[]):step.pop('caption',None)
 return result
def check_editorial_overlay(baseline,current):
 if baseline['feature']['id']!=current['feature']['id']:raise ValueError('Changed feature identity')
 # Only human-facing feature text can change. Scene setup, inputs, selectors,
 # audio routing and timing remain exactly the baseline performance contract.
 if performance_contract(baseline)!=performance_contract(current):
  raise ValueError('Changed performance contract in editorial overlay')
 allowed={'title','summary','prose','musical_use','controls','details','recipes','related','category','parent','level'}
 before={k:v for k,v in baseline['feature'].items() if k not in allowed}
 after={k:v for k,v in current['feature'].items() if k not in allowed}
 if before!=after:raise ValueError('Changed non-editorial feature identity')
 return dict(baseline_sha256=source_hash(baseline),current_sha256=source_hash(current),scope='feature editorial fields, scene titles/step captions, and audio title/description only')
def check_custom_kind(kind):
 supported={'manual-reason-dashboard','manual-reason-midi','manual-course-ui','manual-course-midi','manual-course-persistence','manual-song-indicators','manual-song-slot-setting','manual-song-queue-blink','manual-song-queue-transition','manual-motion-stable-rows','manual-motion-music','manual-motion-pose','manual-song-repeat-advance','manual-modulation-cc-phase'}
 supported.update({'manual-save-dialog-frame','manual-save-dialog-cancel','manual-save-dialog-return','manual-save-dialog-persistence'})
 supported.update({'manual-player-apply-start','manual-player-apply-pending','manual-player-apply-applied','manual-player-apply-reopened'})
 supported.update({'manual-repeat-reset-public-midi','manual-snap-mask-public-midi','manual-ui-motion-public-frames','manual-ui-motion-public-midi','manual-ui-motion-midi-pair'})
 supported.update({'merge-strategy-ui','effective-foundation-musical-result','effective-fragments-musical-result','restored-legacy-musical-result','merge-strategy-next-cycle','effective-only-silence','public-assignment-marquee','public-fitting-vertical-text','public-readability-summary','public-mini-header'})
 if kind.startswith(('manual-','merge-strategy-','effective-','restored-legacy-','public-')) and kind not in supported:raise ValueError('Unsupported new manual semantic kind requires independent native verification: '+kind)
def check_assertion(step,results):
 binding=step['output']['binding'];index=binding['assertion_index']
 if type(index)is not int or not 0<=index<len(results):raise ValueError('Invalid assertion index')
 row=results[index]
 if row!=binding['assertion'] or canonical_hash(row)!=binding['assertion_sha256']:raise ValueError('Changed exact assertion row/hash')
 if row.get('passed') is False or row.get('matched') is False:raise ValueError('Semantic checkpoint failed')
 if not all(row.get(k)==v for k,v in step['expect']['assertion'].items()):raise ValueError('Semantic selector mismatch')
 if canonical_hash(step['inputs'])!=binding['trace_sha256']:raise ValueError('Changed public input trace')
def evidence(scene):
 item=scene['evidence'];path=Path(item['path'])
 if digest(path/'results.json')!=item['results_sha256']:raise ValueError('Changed results evidence')
 if digest(path/'native/identity.json')!=item['identity_sha256']:raise ValueError('Changed native identity')
 results=json.loads((path/'results.json').read_text())
 if any(row.get('passed') is False or row.get('matched') is False for row in results):raise ValueError('Failed assertion in native evidence')
 cleanup=json.loads((path/'native/cleanup.json').read_text())
 if not cleanup or any(row.get('returncode') is None for row in cleanup):raise ValueError('Missing native cleanup receipt')
 return results,json.loads((path/'observations.json').read_text())
def check_reference_publication(document,original):
 subset=document.get('publication_subset')
 if subset is None:
  if original!=document:raise ValueError('Published reference differs from immutable capture')
  return
 if original.get('passed') is False or not original.get('scenes') or original.get('complete_regression_run') is not False:raise ValueError('Failed or empty original campaign cannot supply a publication subset')
 fixed={key:value for key,value in document.items() if key not in ('scenes','selected_scene_ids','publication_subset')}
 expected={key:value for key,value in original.items() if key not in ('scenes','selected_scene_ids')}
 if fixed!=expected:raise ValueError('Subset changed campaign metadata')
 selected=document['scenes'];ids=[scene['id'] for scene in selected]
 if not ids or len(set(ids))!=len(ids) or document.get('selected_scene_ids')!=ids:raise ValueError('Invalid exact scene subset selection')
 originals={scene['id']:scene for scene in original['scenes']}
 if any(scene!=originals.get(scene['id']) for scene in selected):raise ValueError('Publication is not an exact scene subset')
def check_authored_assertion(step,authored):
 accepted=json.loads(json.dumps([authored['assertion']]+authored.get('assertion_alternatives',[])))
 if step['expect']['assertion'] not in accepted:raise ValueError('Published assertion differs from exact pinned selector alternatives')
def check_recovery_publication(document,failure,completed):
 receipt=document['publication_recovery'];source=document['source']
 if failure.get('passed') is not False or document.get('complete_regression_run') is not False or document['clock_mode']!=failure['clock_mode']:raise ValueError('Recovery changed original failed campaign scope')
 if receipt.get('source_start_identity_complete') is not True or receipt.get('missing_start_identity_fields')!=[] or source!=failure.get('source') or not all(field in source for field in ('fixture_sources','case_sources','capture_sources','plan_files','start_source_identity_path','start_source_identity_sha256')):raise ValueError('Recovery requires complete start source identity; missing start fields cannot be reconstructed')
 selected=document['scenes'];ids=[scene['id'] for scene in selected];originals={scene['id']:scene for scene in completed}
 if not ids or len(set(ids))!=len(ids) or document.get('selected_scene_ids')!=ids or set(ids)&set(failure['scenes']) or any(scene!=originals.get(scene['id']) for scene in selected):raise ValueError('Recovery changed completed native scenes or selected failed scenes')
def recovery_sources(document):
 receipt=document['publication_recovery'];run=Path(receipt['failed_campaign']);failure_path=run/'failure.json'
 if digest(failure_path)!=receipt['failure_sha256']:raise ValueError('Changed original failure evidence')
 failure=json.loads(failure_path.read_text());completed=[]
 for item in receipt['completed_cases']:
  path=Path(item['path'])
  if path.name!='captured-scenes.json' or run.resolve() not in path.resolve().parents or digest(path)!=item['sha256']:raise ValueError('Changed completed per-case recovery receipt')
  cases=json.loads(path.read_text())
  if any(Path(scene['evidence']['path']).resolve()!=path.parent.resolve() for scene in cases):raise ValueError('Recovered scene refers to foreign case evidence')
  completed.extend(cases)
 check_recovery_publication(document,failure,completed)
 plans={str(path.relative_to(run/'plan-source')):digest(path) for path in (run/'plan-source').rglob('*.yaml')}
 if plans!=document['source']['plan_files']:raise ValueError('Recovery changed frozen plan inventory')
 aggregate=next(iter(plans.values())) if len(plans)==1 else canonical_hash(plans)
 if aggregate!=failure.get('source',failure)['plans_sha256']:raise ValueError('Frozen recovery plans lack recorded start hash')
 return run
def check_start_source_receipt(document,receipt):
 if receipt.get('schema_version')!=1:raise ValueError('Unsupported start source receipt')
 for field in ('plans_sha256','adapter_sha256','plan_files','case_sources','capture_sources','fixture_sources'):
  if document['source'].get(field)!=receipt.get(field):raise ValueError('Changed immutable start source '+field)
 selected=document['selected_scene_ids']
 expected_selection=receipt['selected_scene_ids']
 recovery=document.get('publication_recovery')
 if recovery and recovery.get('source_start_identity_complete') is True:
  failure_path=Path(recovery['failed_campaign'])/'failure.json'
  if digest(failure_path)!=recovery['failure_sha256']:raise ValueError('Changed immutable recovery failure')
  failure=json.loads(failure_path.read_text())
  if failure.get('source')!=document['source'] or recovery.get('missing_start_identity_fields')!=[]:raise ValueError('Incomplete recovery start source identity')
  expected_selection=[identifier for identifier in receipt['selected_scene_ids'] if identifier not in failure['scenes']]
  full=json.loads((Path(document['evidence'])/'reference-scenes.json').read_text())
  if full.get('selected_scene_ids')!=expected_selection:raise ValueError('Recovery selected or omitted inventory differs from immutable failed start')
 if document.get('clock_mode')!=receipt.get('clock_mode') or (selected!=expected_selection and 'publication_subset' not in document):raise ValueError('Changed immutable start selection or clock')
 if not set(selected).issubset(set(receipt['selected_scene_ids'])):raise ValueError('Changed immutable start selection')
 for relative in receipt.get('extra_case_files',[]):
  path=Path(relative)
  if path.is_absolute() or path.parts[0]!='tools' or '..' in path.parts or relative not in receipt['capture_sources']:raise ValueError('Unpinned extra-case helper')
def audit_start_source_receipt(document,run):
 source=document['source'];receipt_path=source.get('start_source_identity_path')
 if receipt_path is None:
  if (run/'start-source-identity.json').exists():raise ValueError('Publication omitted native start source receipt')
  return
 path=Path(receipt_path)
 if path.resolve()!=(run/'start-source-identity.json').resolve() or digest(path)!=source.get('start_source_identity_sha256'):raise ValueError('Changed start source receipt path/hash')
 receipt=json.loads(path.read_text());check_start_source_receipt(document,receipt)
 for relative in receipt.get('extra_case_files',[]):
  if digest(ROOT/relative)!=receipt['capture_sources'][relative]:raise ValueError('Stale registered extra-case helper: '+relative)
 for field,folder in [('plan_files','plan-source'),('case_sources','case-source'),('capture_sources','capture-source'),('fixture_sources','fixture-source')]:
  for relative,expected in receipt[field].items():
   frozen=run/folder/relative
   if Path(relative).is_absolute() or '..' in Path(relative).parts or digest(frozen)!=expected:raise ValueError('Changed frozen start source '+relative)
 return receipt
def audit_reference(document):
 if document.get('complete_regression_run') is not False:raise ValueError('Reference capture scope must remain partial')
 original_path=Path(document['evidence'])/'reference-scenes.json'
 original=json.loads(original_path.read_text())
 subset=document.get('publication_subset')
 if subset and (Path(subset['original_report']).resolve()!=original_path.resolve() or digest(original_path)!=subset['original_report_sha256']):raise ValueError('Changed original campaign subset receipt')
 check_reference_publication(document,original)
 source=document['source'];run=recovery_sources(document) if 'publication_recovery' in document else Path(document['evidence']);authored={};owners={};current_plans={}
 audit_start_source_receipt(document,run)
 for relative,expected in source.get('plan_files',{}).items():
  frozen=run/'plan-source'/relative
  if digest(frozen)!=expected:raise ValueError('Changed pinned scene plan')
  if digest(ROOT/relative)!=expected:raise ValueError('Stale scene authoring: '+relative)
  for current in yaml.safe_load((ROOT/relative).read_text())['scenes']:current_plans[current['id']]=current
  for plan in yaml.safe_load(frozen.read_text())['scenes']:
   if 'publication_recovery' in document and plan['id'] in document['selected_scene_ids'] and plan!=current_plans.get(plan['id']):raise ValueError('Recovered selected plan is stale or changed')
   for step in plan['steps']:
    authored[(plan['id'],step['id'])]=step
    owners[(plan['id'],step['id'])]=step.get('session_ordinal',plan.get('session_ordinal',0))
 for relative,expected in source.get('capture_sources',{}).items():
  if digest(run/'capture-source'/relative)!=expected:raise ValueError('Changed frozen capture tool')
 for relative,expected in source.get('case_sources',{}).items():
  if digest(ROOT/relative)!=expected:raise ValueError('Stale behaviour case source: '+relative)
 frames=0
 for scene in document['scenes']:
  results,observations=evidence(scene)
  audit_participants(scene,document)
  deferred=any(step['output']['binding'].get('capture_stage') for step in scene['steps'])
  if 'publication_recovery' in document and 'capture_trace_sha256' not in scene['evidence']:raise ValueError('Recovered scene lacks complete public/native trace receipts')
  path=audit_deferred_trace(scene) if deferred or 'capture_trace_sha256' in scene['evidence'] else Path(scene['evidence']['path'])
  native_source_identity(path,profile=scene.get('profile','base-midi'))
  for step in scene['steps']:
   check_assertion(step,results)
   check_custom_kind(step['output']['binding']['assertion'].get('kind',''))
   plan=authored.get((scene['id'],step['id']),{})
   if plan and scene.get('session_ordinal',0)!=owners[(scene['id'],step['id'])]:raise ValueError('Scene participant differs from pinned authoring')
   if plan:check_authored_assertion(step,plan)
   check_capture_stage(step,results,plan)
   if step['output']['binding'].get('capture_stage'):
    binding=step['output']['binding'];states=[row['state'] for row in observations if row['state']['frame']['sha256']==binding['sha256'] and row['state']['grid']==step['output']['grid']]
    if not states:raise ValueError('Missing cached before-finish native image')
    verify_cached_ui(states[0],plan['pre_finish_expect'],path)
   verify_reason_checkpoint(step,observations,path,document['clock_mode'])
   verify_vertical_checkpoint(step,observations,path)
   verify_teaching_checkpoint(step,observations,path,document['clock_mode'],results)
   verify_motion_checkpoint(step,observations,path,document['clock_mode'])
   verify_closure_checkpoint(step,observations,path,document['clock_mode'],results)
   verify_new_public_checkpoint(step,observations,path,document['clock_mode'],results,scene.get('session_ordinal',0))
   if step['output']['binding']['assertion'].get('kind')=='parameter-recording-selected-value':
    if not plan:raise ValueError('Recorded-value checkpoint lacks pinned native readout authoring')
    from manual_parameter_recording_readout import verify_parameter_recording_checkpoint
    verify_parameter_recording_checkpoint(step,plan,scene,results,observations,path,document['clock_mode'],verify_cached_ui)
   check_frame(step['output'],scene['behaviour_case'],results,observations);frames+=1
  check_player_apply_scene(scene)
 return frames


def scoped_native_witness(row,observations,recipe,events,clock_mode):
 witness=row.get('witness',{});states=[];indices=[]
 for name in ('start','end'):
  item=witness.get(name,{});index=item.get('observation_index')
  if type(index)is not int or not 0<=index<len(observations):raise ValueError('Missing exact native playback witness')
  observation=observations[index];state=exact_observation(item,observations,events);logical=state['clock']['logical_ns'] if clock_mode=='controlled-experimental' else None
  if item.get('frame_sha256')!=state['frame']['sha256'] or item.get('midi_count')!=state['midi_count'] or item.get('monotonic_ns')!=observation['monotonic_ns'] or item.get('logical_ns')!=logical:raise ValueError('Changed native playback witness')
  if item.get('midi_outstanding')!=state['midi_capture']['outstanding']:raise ValueError('Changed native outstanding-note witness')
  states.append(state);indices.append(index)
 if indices[0]>=indices[1] or states[-1]['midi_capture']['outstanding']:raise ValueError('Unreleased or unordered native playback witness')
 first,last=witness['start'],witness['end'];a,b=first.get('recipe_index'),last.get('recipe_index')
 if type(a)is not int or type(b)is not int or not 0<=a<b<=len(recipe):raise ValueError('Missing native public playback recipe witness')
 transport=[item for item in recipe[a:b] if item.get('type')=='grid' and (item.get('x'),item.get('y'))==(1,8)]
 if transport!=[dict(type='grid',x=1,y=8,state=z) for z in (1,0,1,0)]:raise ValueError('Native playback requires exact public Play and Stop edges')
 start,end=first['midi_count'],last['midi_count'];kind=11 if clock_mode=='controlled-experimental' else 3
 if type(start)is not int or type(end)is not int or not 0<=start<=end:raise ValueError('Invalid scoped native playback MIDI boundaries')
 packets=[item for item in events if item.get('kind')==kind and start<item.get('index',0)<=end and len(item.get('bytes',[]))==3]
 key='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns';elapsed=((last[key]-first[key]) if clock_mode=='controlled-experimental' else last['monotonic_ns']-first['monotonic_ns'])/1e9
 native_edges=[(i,item) for i,item in enumerate(events) if item.get('kind')=='input' and item.get('type')==3 and item.get('args',[])[:2]==[0,7] and first['monotonic_ns']<=item['monotonic_ns']<=last['monotonic_ns']]
 if [item['args'] for i,item in native_edges]!=[[0,7,z] for z in (1,0,1,0)]:raise ValueError('Missing exact actual native public Play and Stop witness')
 start_i,play=native_edges[0];stop_i,stop=native_edges[2]
 actual_elapsed=sum(item['args'][0]+item['args'][1]/1e9 for item in events[start_i+1:stop_i] if item.get('kind')=='input' and item.get('type')==8) if clock_mode=='controlled-experimental' else (stop['monotonic_ns']-play['monotonic_ns'])/1e9
 if actual_elapsed<0 or elapsed+2e-9<actual_elapsed:raise ValueError('Native playback observation clock differs from actual public transport')
 return packets,actual_elapsed,states

def canonical_merge_witness_hash(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def resolve_scoped_witness(assertion_index,results,*,expected_session_ordinal=None):
 """Resolve only an exact, unique documentation-frame snapshot for a reentrant result."""
 kinds={"effective-foundation-musical-result","effective-fragments-musical-result","restored-legacy-musical-result"}
 if type(assertion_index) is not int or not 0<=assertion_index<len(results):raise ValueError("Invalid musical assertion index")
 row=results[assertion_index]
 if row.get("kind") not in kinds:raise ValueError("Witness resolution requested for a non-musical assertion")
 if "witness" in row:return copy.deepcopy(row)
 linked=[item for item in results if item.get("kind")=="documentation-frame" and item.get("assertion_index")==assertion_index]
 if len(linked)!=1:raise ValueError("Musical assertion requires one unique linked documentation frame")
 frame=linked[0]
 if frame.get("assertion")!=row:raise ValueError("Documentation frame assertion snapshot changed")
 if frame.get("assertion_sha256")!=canonical_merge_witness_hash(row):raise ValueError("Documentation frame assertion hash changed")
 if expected_session_ordinal is not None and frame.get("session_ordinal")!=expected_session_ordinal:raise ValueError("Documentation frame belongs to another native session")
 witness=frame.get("witness")
 if not isinstance(witness,dict) or not all(key in witness for key in ("start","end")):raise ValueError("Linked documentation frame lacks exact start/end witness")
 start,end=witness["start"],witness["end"];start_count=frame.get("midi_start_exclusive");end_count=frame.get("midi_end_inclusive")
 if type(start_count)is not int or type(end_count)is not int or start.get("midi_count")!=start_count or end.get("midi_count")!=end_count:raise ValueError("Documentation frame MIDI boundaries differ from linked witness counts")
 if (("midi_start_exclusive" in row and row["midi_start_exclusive"]!=start_count) or ("midi_end_inclusive" in row and row["midi_end_inclusive"]!=end_count)):raise ValueError("Documentation frame MIDI boundaries differ from assertion")
 result=copy.deepcopy(row);result.update(witness=copy.deepcopy(witness),midi_start_exclusive=start_count,midi_end_inclusive=end_count)
 return result

def check_merge_music(row,observations,recipe,events,clock_mode):
 packets,elapsed,states=scoped_native_witness(row,observations,recipe,events,clock_mode)
 notes=[item for item in packets if 144<=item['bytes'][0]<=159 and item['bytes'][2]>0];kind=row['kind'];allowed=2e-9 if clock_mode=='controlled-experimental' else .02
 if kind=='effective-only-silence':
  if (row.get('loops'),row.get('loop_steps'),row.get('expected'),row.get('actual'))!=(2,8,[],[]) or notes or elapsed<16/6-allowed or any(states[0]['grid'][i] in (12,15) for i in range(48,56)):raise ValueError('Only native silence requires two complete empty channel cycles')
  return
 foundation=[(1,1,60,127),(2,1,62,117),(3,1,64,107),(4,1,65,97),(5,1,60,70),(7,1,60,70)];legacy=[(1,1,60,127),(2,1,62,117),(3,1,64,107),(4,1,65,97),(5,1,60,100),(7,1,60,100)];fragments=[(5,1,60,100),(7,1,60,100)]
 phrase={'effective-foundation-musical-result':foundation,'effective-fragments-musical-result':fragments,'restored-legacy-musical-result':legacy}.get(kind)
 if phrase is None and kind!='merge-strategy-next-cycle':raise ValueError('Unsupported merge musical acceptance')
 phrases=[legacy,foundation,foundation] if kind=='merge-strategy-next-cycle' else [phrase]*3
 wanted=[list((cycle,)+item) for cycle,items in enumerate(phrases) for item in (items if cycle<2 else items[:1])]
 if row.get('expected')!=wanted or row.get('tolerance_seconds')!=allowed or len(notes)!=len(wanted):raise ValueError('Merge literal full native phrase differs')
 if kind!='merge-strategy-next-cycle' and (row.get('loops'),row.get('loop_steps'))!=(2,8):raise ValueError('Merge authored loop count differs')
 if kind=='effective-fragments-musical-result' and (row.get('size'),row.get('seed'))!=(8,0):raise ValueError('Merge fragment deterministic configuration differs')
 key='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns';firststep=wanted[0][1]
 for note,(cycle,step,channel,pitch,velocity) in zip(notes,wanted):
  if note['port']!=1 or note['bytes']!=[143+channel,pitch,velocity] or abs((note[key]-notes[0][key])/1e9-(cycle*8+step-firststep)/6)>allowed:raise ValueError('Merge exact native pitch/velocity/channel/pulse differs')
  if not any(packet['index']>note['index'] and packet['port']==1 and packet['bytes']==[127+channel,pitch,velocity] for packet in packets):raise ValueError('Merge missing exact native note release')
 if row.get('actual',wanted)!=wanted:raise ValueError('Merge stored observed phrase differs')


def check_mini_samples(row,observations,events):
 import base64
 samples=row.get('samples',[]);indices=[item.get('observation_index') for item in samples]
 if len(samples)<2 or any(type(i)is not int or not 0<=i<len(observations) for i in indices) or indices!=sorted(set(indices)):raise ValueError('Mini readability requires exact native sample receipts')
 path=ROOT/'tests/behaviour/contract/mini_header_atlas_v2.json';sha='4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46'
 if digest(path)!=sha or row.get('atlas_sha256')!=sha:raise ValueError('Mini literal v2 atlas identity changed')
 atlas=json.loads(path.read_text());spec=next((item for item in atlas['screens'] if item['id']==row.get('page')),None)
 if spec is None or type(row.get('enabled'))is not bool or row.get('pose_count')!=len(spec['frames']) or row.get('loop_quarter_beats')!=spec['loop_quarter_beats'] or type(row.get('all_distinct_poses_required'))is not bool:raise ValueError('Mini literal animation configuration changed')
 palette={'.':0,'a':7,'b':11,'c':15};left=121 if spec['layout'] in ('overview_masks','overview_params','dashboard') else 96;origin=spec['origin'];seen=set();fixed=grid=count=None;nativeframes={item.get('sha256') for item in events if item.get('kind')==1};times=[]
 def icon(data):return bytes(data[(y*128+x)*4+k] for y in range(8) for x in range(left,128) for k in range(3))
 expected=[]
 for frame in spec['frames']:
  pixels=bytearray(32768)
  for y,letters in enumerate(frame):
   for x,letter in enumerate(letters):
    i=((origin[1]+y)*128+origin[0]+x)*4;pixels[i:i+3]=bytes([17*palette[letter]])*3
  expected.append(icon(pixels))
 for item in samples:
  observation=observations[item['observation_index']];state=observation['state'];data=base64.b64decode(state['frame']['pixels_base64']);frame_sha=hashlib.sha256(data).hexdigest()
  if len(data)!=32768 or frame_sha!=item.get('frame_sha256') or frame_sha!=state['frame']['sha256'] or frame_sha not in nativeframes:raise ValueError('Mini sample differs from actual native framebuffer')
  matches=[i for i,target in enumerate(expected) if icon(data)==target]
  if not matches or matches!=item.get('matching_poses') or not row['enabled'] and 0 not in matches:raise ValueError('Mini exact authored native bitmap pose differs')
  body=bytes(data[(y*128+x)*4+k] for y in range(64) for x in range(128) for k in range(3) if not(y<8 and x>=left))
  if fixed is None:fixed=body;grid=state['grid'];count=state['midi_count']
  if body!=fixed or grid!=state['grid'] or count!=state['midi_count']:raise ValueError('Mini animation changed stationary controls/grid/MIDI')
  if not any(event.get('kind')==2 and event.get('leds')==state['grid'] for event in events):raise ValueError('Mini sample grid differs from actual native grid')
  seen.update(matches);times.append(state['clock']['logical_ns'] if state['clock']['mode']=='controlled-experimental' else observation['monotonic_ns'])
 if any(b-a<125000000 for a,b in zip(times,times[1:])):raise ValueError('Mini samples omit admitted native cadence')
 poses={tuple(spec['frames'][i]) for i in seen};allposes={tuple(frame) for frame in spec['frames']}
 if row.get('observed_poses')!=sorted(seen) or (row['enabled'] and (len(poses)<2 or row['all_distinct_poses_required'] and poses!=allposes)) or (not row['enabled'] and poses!={tuple(spec['frames'][0])}):raise ValueError('Mini native distinct pose coverage differs')
 from mini_phase_oracle import check_stopped_phase
 if row.get('clock_source')!='native-selected-norns-clock' or row.get('transport')!='stopped':raise ValueError('Mini phase requires explicit native stopped clock source')
 clock_mode=observations[samples[0]['observation_index']]['state']['clock']['mode']
 proofs=[check_stopped_phase(item,observations,events,spec,row['enabled'],row.get('tempo'),clock_mode) for item in samples]
 if any(item.get('phase_check')!=proof for item,proof in zip(samples,proofs)):raise ValueError('Mini live phase receipt differs from independently reconstructed native phase')
 return proofs

def check_readability_samples(row,observations,events,path):
 import base64,frame_oracle
 samples=row.get('samples',[]);count=32 if row['kind']=='public-assignment-marquee' else 6;indices=[item.get('observation_index') for item in samples]
 if len(samples)!=count or any(type(i)is not int or not 0<=i<len(observations) for i in indices) or indices!=sorted(set(indices)):raise ValueError('Readability requires exact distinct native sample receipts')
 nativeframes={item.get('sha256') for item in events if item.get('kind')==1};states=[]
 for item in samples:
  state=observations[item['observation_index']]['state'];pixels=base64.b64decode(state['frame']['pixels_base64'])
  if len(pixels)!=32768 or hashlib.sha256(pixels).hexdigest()!=item.get('frame_sha256') or item['frame_sha256']!=state['frame']['sha256'] or item['frame_sha256'] not in nativeframes:raise ValueError('Readability sample differs from actual native framebuffer')
  if not any(event.get('kind')==2 and event.get('leds')==state['grid'] for event in events):raise ValueError('Readability sample grid differs from actual native grid')
  states.append(state)
 identity=json.loads((path/'native/identity.json').read_text())
 with tempfile.TemporaryDirectory(prefix='readability-font-oracle-') as directory:
  runtime=Path(directory)/'.runtime';runtime.mkdir();(runtime/'current.json').write_text(json.dumps(dict(source=identity['runtime_identity']['source'])));previous=frame_oracle.ROOT;frame_oracle.ROOT=Path(directory)
  try:
   # V2 detail/vertical mini sprites extend left of the historical x120.
   # Verify exact authored literal art before excluding only its own rectangle.
   from mini_phase_oracle import observed_phases
   mini_page='C07' if row['kind']=='public-assignment-marquee' else {'clock':'C04','scale':'S01'}.get(row.get('page'))
   atlas_path=ROOT/'tests/behaviour/contract/mini_header_atlas_v2.json'
   if digest(atlas_path)!='4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46':raise ValueError('Readability exact mini atlas changed')
   spec=next((item for item in json.loads(atlas_path.read_text())['screens'] if item['id']==mini_page),None)
   if spec is None or type(row.get('enabled'))is not bool:raise ValueError('Unsupported readability authored mini page')
   for state in states:
    phases=observed_phases(state,spec)
    if not row['enabled'] and 0 not in phases:raise ValueError('Readability Motion Off must preserve authored rest mini')
   icon_x,icon_y=spec['origin'];icon_width=len(spec['frames'][0][0]);icon_height=len(spec['frames'][0])
   def band(state,excluded):
    data=base64.b64decode(state['frame']['pixels_base64']);return bytes(data[(y*128+x)*4+k] for y in range(64) for x in range(128) for k in range(3) if y not in excluded and not(icon_y<=y<icon_y+icon_height and icon_x<=x<icon_x+icon_width))
   if row['kind']=='public-assignment-marquee':
    if (row.get('label'),row.get('value'))!=('Quantised Fixed Note','CURRENT') or type(row.get('enabled'))is not bool:raise ValueError('Changed literal Assignment readability contract')
    expected=frame_oracle.variants(lambda:frame_oracle.render([(0,36,15,'>'),(7,36,15,frame_oracle.fit(row['label'],72)),((None,126),36,15,'CURRENT')]))
    from contract.live_ui_sweep import footer_render,hints
    footer=footer_render(hints('C07'));neighbors=frame_oracle.render([(7,27,6,'Fixed Note'),(7,45,6,'Random Note')]);phases=set()
    for item,state in zip(samples,states):
     data=base64.b64decode(state['frame']['pixels_base64']);matches=[i for i,image in enumerate(expected) if frame_oracle._region_matches(data,image,29,38)]
     if not frame_oracle.live_header_matches(state,'ASSIGN PARAM','CH01','detail') or matches!=[item.get('expected_phase')] or not frame_oracle._region_matches(data,neighbors,20,29) or not frame_oracle._region_matches(data,neighbors,38,47) or not frame_oracle._region_matches(data,footer,57,64):raise ValueError('Readability native literal Assignment phase differs')
     phases.update(matches)
    if row.get('expected_phases')!=len(expected) or row.get('observed_phases')!=sorted(phases) or (not row['enabled'] and phases!={0}) or (row['enabled'] and not {0,len(expected)-1}<=phases):raise ValueError('Readability Off/On native phase coverage differs')
    excluded=range(29,38)
   else:
    wanted={'clock':('Rate','/1','CLOCK','CH01'),'scale':('Scale','Major','SCALE','SLOT 01')}.get(row.get('page'))
    if wanted is None or (row.get('label'),row.get('value'))!=wanted[:2] or type(row.get('enabled'))is not bool:raise ValueError('Changed literal fitting readability contract')
    for state in states:
     if not frame_oracle.live_header_matches(state,*wanted[2:],'vertical_list') or not frame_oracle.vertical_selected_field_matches(state,*wanted[:2]):raise ValueError('Fitting native vertical label/value differs')
    excluded=()
   if any(band(state,excluded)!=band(states[0],excluded) or state['grid']!=states[0]['grid'] or state['midi_count']!=states[0]['midi_count'] for state in states):raise ValueError('Readability samples changed unaffected UI/grid/MIDI')
  finally:frame_oracle.ROOT=previous


def exact_observation(receipt,observations,events):
 import base64
 index=receipt.get('observation_index')
 if type(index)is not int or not 0<=index<len(observations):raise ValueError('Missing exact native UI observation receipt')
 observation=observations[index];state=observation['state'];pixels=base64.b64decode(state['frame']['pixels_base64']);sha=hashlib.sha256(pixels).hexdigest()
 if len(pixels)!=32768 or sha!=state['frame']['sha256'] or sha!=receipt.get('frame_sha256') or not any(event.get('kind')==1 and event.get('sha256')==sha for event in events):raise ValueError('Native UI receipt frame/hash differs')
 if not any(event.get('kind')==2 and event.get('leds')==state['grid'] for event in events):raise ValueError('Native UI receipt differs from actual native grid')
 if 'grid_sha256' in receipt and receipt['grid_sha256']!=canonical_hash(state['grid']):raise ValueError('Native UI receipt grid hash differs')
 return state

def check_merge_ui(row,observations,events,path,results,assertion_index):
 wanted={
 'foundation-active':dict(strategy='FOUNDATION',active='FOUNDATION'),
 'fragments-inactive':dict(strategy='FRAGMENTS',active='FRAGMENTS',saved_modes=['AVERAGE']*3),
 'legacy-restored':dict(strategy='SKIP',saved_modes=['AVERAGE']*3),
 'unset-anchor-refusal':dict(selected='FOUNDATION',active='ALL',pending='NONE',request='NEEDS ANCHOR'),
 'unassigned-anchor-refusal':dict(selected='FOUNDATION',active='ALL',pending='NONE',request='NEEDS ANCHOR'),
 'pending-cycle':dict(active='ALL',pending='FOUNDATION',boundary='NEXT CYCLE'),
 'm02-readonly':dict(strategy='FOUNDATION'),
 'draft-discarded':dict(label='Add amount',value='100')}.get(row.get('checkpoint'))
 if wanted is None or any(row.get(key)!=value for key,value in wanted.items()):raise ValueError('Unknown or changed literal merge UI checkpoint')
 exact_observation(row.get('witness',{}),observations,events);fields=row.get('fields',[])
 if not fields:raise ValueError('Merge UI checkpoint lacks exact selected-field receipts')
 observed=[]
 for field in fields:
  if not any(result.get('kind')=='selected-field' and all(result.get(key)==field.get(key) for key in ('layout','label','value','observation_index','frame_sha256')) for result in results[:assertion_index]):raise ValueError('Merge UI field receipt is not an original earlier assertion')
  state=exact_observation(field,observations,events);verify_cached_ui(state,dict(field=dict(layout=field['layout'],label=field['label'],value=field['value'])),path);observed.append((field['label'],field['value']))
 required={
 'foundation-active':[('Strategy','FOUNDATION'),('Active','FOUNDATION')],
 'fragments-inactive':[('Strategy','FRAGMENTS'),('Active','FRAGMENTS')]+[(label,'AVERAGE SAVED') for label in ('Note mode inactive','Velocity mode inactive','Length mode inactive') for _ in range(2)],
 'legacy-restored':[('Strategy','SKIP')]*2+[(label,'AVERAGE') for label in ('Note mode','Velocity mode','Length mode')],
 'unset-anchor-refusal':[('Anchor','NONE'),('Strategy','FOUNDATION'),('Active','ALL'),('Pending','NONE'),('Request','NEEDS ANCHOR')],
 'unassigned-anchor-refusal':[('Anchor','1'),('Strategy','FOUNDATION'),('Active','ALL'),('Pending','NONE'),('Request','NEEDS ANCHOR')],
 'pending-cycle':[('Pending','FOUNDATION'),('Boundary','NEXT CYCLE')],
 'm02-readonly':[('Strategy','FOUNDATION')]*2,
 'draft-discarded':[('Add amount','99'),('Add amount','100')]}
 from collections import Counter
 counts=Counter(observed)
 if any(counts[field]<count for field,count in Counter(required[row['checkpoint']]).items()):raise ValueError('Merge literal native field/refusal/read-only coverage missing')

def check_readability_summary(row,observations,recipe,events,clock_mode,path=None):
 import base64
 from mini_phase_oracle import check_playing_phases
 if row.get('clock_source')!='public-midi-clock-output' or row.get('transport')!='playing':raise ValueError('Readability playing phase lacks explicit actual emitted clock source')
 start_count=row.get('midi_start_exclusive');end_count=row.get('midi_end_inclusive')
 if start_count!=row.get('witness',{}).get('start',{}).get('midi_count') or end_count!=row.get('witness',{}).get('end',{}).get('midi_count'):raise ValueError('Readability playing phase MIDI scope differs from native witnesses')
 phase_atlas=ROOT/'tests/behaviour/contract/mini_header_atlas_v2.json';phase_sha='4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46'
 if digest(phase_atlas)!=phase_sha or row.get('atlas_sha256')!=phase_sha:raise ValueError('Readability playing phase atlas changed')
 phase_spec=next(item for item in json.loads(phase_atlas.read_text())['screens'] if item['id']=='C01')
 phase_proof=check_playing_phases(row.get('playing_mini_frames',[]),observations,events,phase_spec,start_count,end_count,clock_mode,90)
 if row.get('phase_check')!=phase_proof:raise ValueError('Readability live playing-phase receipt differs from independent native proof')
 setup=exact_observation(row.get('clock_output_setup',{}),observations,events);setup_pixels=base64.b64decode(setup['frame']['pixels_base64'])
 if not all(setup_pixels[(y*128+x)*4+k]==255 for y in range(26,29) for x in range(124,127) for k in range(3)):raise ValueError('Readability actual native MIDI clock output is not enabled')
 if path is None:raise ValueError('Readability playing phase lacks captured native font source')
 verify_cached_ui(setup,dict(menu_label=dict(label='1. Emulator MIDI',top=24,x=0,width=70)),path)
 overviews=row.get('overviews',[])
 if [(item.get('page'),item.get('enabled')) for item in overviews]!=[('C02',False),('C01',False),('C02',True),('C01',True)]:raise ValueError('Readability exact Off/On overview receipts missing')
 bodies={}
 for item in overviews:
  state=exact_observation(item,observations,events);pixels=base64.b64decode(state['frame']['pixels_base64']);body=pixels[8*128*4:]
  if item['page'] in bodies and bodies[item['page']]!=body:raise ValueError('Readability motion changed Masks/Trig Params overview')
  bodies[item['page']]=body
 packets,elapsed,states=scoped_native_witness(row,observations,recipe,events,clock_mode);notes=[packet for packet in packets if 144<=packet['bytes'][0]<=159 and packet['bytes'][2]>0]
 phrase=[[144,60,127],[144,62,117],[144,64,107],[144,65,97]];allowed=2e-9 if clock_mode=='controlled-experimental' else .02;key='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns'
 if len(notes)<9 or any(note['port']!=1 or note['bytes']!=phrase[i%4] or abs((note[key]-notes[0][key])/1e9-i/6)>allowed for i,note in enumerate(notes)):raise ValueError('Readability exact native complete repeated phrase differs')
 for note in notes:
  if not any(packet['index']>note['index'] and packet['port']==1 and len(packet['bytes'])==3 and packet['bytes'][:2]==[128,note['bytes'][1]] for packet in packets):raise ValueError('Readability native note release missing')
 start,end=row['witness']['start']['observation_index'],row['witness']['end']['observation_index'];samples=row.get('playing_mini_frames',[])
 if [item.get('observation_index') for item in samples]!=list(range(start,end+1)):raise ValueError('Readability all native playing mini samples missing')
 atlas_path=ROOT/'tests/behaviour/contract/mini_header_atlas_v2.json';sha='4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46'
 if row.get('atlas_sha256')!=sha or digest(atlas_path)!=sha:raise ValueError('Readability playing atlas changed')
 spec=next(item for item in json.loads(atlas_path.read_text())['screens'] if item['id']=='C01');origin=spec['origin'];expected=[]
 for frame in spec['frames']:
  pixels=bytearray(32768)
  for y,line in enumerate(frame):
   for x,char in enumerate(line):
    i=(y*128+origin[0]+x)*4;pixels[i:i+3]=bytes([17*{'.':0,'a':7,'b':11,'c':15}[char]])*3
  expected.append(bytes(pixels[(y*128+x)*4+k] for y in range(8) for x in range(121,128) for k in range(3)))
 for item in samples:
  state=exact_observation(item,observations,events);pixels=base64.b64decode(state['frame']['pixels_base64']);band=bytes(pixels[(y*128+x)*4+k] for y in range(8) for x in range(121,128) for k in range(3));matching=[i for i,target in enumerate(expected) if band==target]
  if not matching or item.get('matching_poses')!=matching:raise ValueError('Readability playing native mini bitmap differs')

def verify_new_public_checkpoint(step,observations,path,clock_mode,results,expected_session_ordinal=None):
 row=step['output']['binding']['assertion'];kind=row.get('kind','')
 if kind.startswith('manual-player-apply-'):
  check_player_apply_checkpoint(step,results,observations,path);return
 if kind in {'manual-repeat-reset-public-midi','manual-snap-mask-public-midi','manual-ui-motion-public-frames','manual-ui-motion-public-midi','manual-ui-motion-midi-pair'}:
  from manual_native_public_gap_verify import verify
  verify(step,observations,path,clock_mode,results);return
 if kind not in {'merge-strategy-ui','effective-foundation-musical-result','effective-fragments-musical-result','restored-legacy-musical-result','merge-strategy-next-cycle','effective-only-silence','public-assignment-marquee','public-fitting-vertical-text','public-readability-summary','public-mini-header'}:return
 events=[json.loads(line) for line in (path/'native/native-events.jsonl').read_text().splitlines()];recipe=json.loads((path/'recipe.json').read_text())
 if kind=='merge-strategy-ui':check_merge_ui(row,observations,events,path,results,step['output']['binding']['assertion_index'])
 elif kind.startswith(('effective-','merge-strategy-','restored-legacy-')):
  if kind in {'effective-foundation-musical-result','effective-fragments-musical-result','restored-legacy-musical-result'} and 'witness' not in row:
   row=resolve_scoped_witness(step['output']['binding'].get('assertion_index'),results,expected_session_ordinal=expected_session_ordinal)
  check_merge_music(row,observations,recipe,events,clock_mode)
 elif kind=='public-readability-summary':check_readability_summary(row,observations,recipe,events,clock_mode,path)
 elif kind=='public-mini-header':check_mini_samples(row,observations,events)
 else:check_readability_samples(row,observations,events,path)

def check_player_apply_checkpoint(step,results,observations,path):
  """Verify the checkpoint from raw result, native pixels and public inputs."""
  binding=step['output']['binding'];index=binding.get('assertion_index')
  if type(index)is not int or index<=0 or index>=len(results):raise ValueError('Player Apply assertion lacks adjacent Device result')
  row=results[index];kind=row.get('kind','')
  if not kind.startswith('manual-player-apply-'):return
  selected=results[index-1]
  if (selected.get('kind')!='selected-field' or selected.get('layout')!='detail' or selected.get('label')!='Device' or selected.get('matched') is not True):raise ValueError('Player Apply checkpoint is not immediately preceded by a matched Device field')
  if row.get('citation')!='manual:mods-and-software-devices' or row.get('field')!='Device' or type(row.get('channel')) is not int or not 1<=row['channel']<=16:raise ValueError('Player Apply checkpoint lacks stable citation or channel scope')
  value=None if kind=='manual-player-apply-start' else row.get('value')
  if selected.get('value')!=value:raise ValueError('Player Apply Device differs from selected-field result')
  oi=selected.get('observation_index')
  if type(oi)is not int or not 0<=oi<len(observations):raise ValueError('Player Apply field lacks exact native observation')
  observation=observations[oi];state=observation.get('state',{});frame=state.get('frame',{})
  identity=json.loads((path/'native/identity.json').read_text())
  if observation.get('backend')!='native' or observation.get('fidelity')!='native-norns' or observation.get('session_id')!=identity.get('session_id'):raise ValueError('Player Apply observation is not from the selected native session')
  if not frame or frame.get('sha256')!=selected.get('frame_sha256') or frame.get('sha256')!=binding.get('sha256'):raise ValueError('Player Apply frame differs across result, observation and publication binding')
  if state.get('grid')!=step['output'].get('grid'):raise ValueError('Player Apply grid differs from its native observation')
  expected={'header':{'page':'midi_config','params':{'channel':row['channel']}},'field':{'layout':'detail','label':'Device','value':value}}
  if kind=='manual-player-apply-pending':
   if row.get('confirmation_prompt')!='Press K3 to confirm':raise ValueError('Pending confirmation prompt changed')
   expected['footer']={'text':row['confirmation_prompt'],'present':True}
  elif kind in ('manual-player-apply-applied','manual-player-apply-reopened'):
   if row.get('confirmation_prompt_absent') is not True:raise ValueError('Completed checkpoint lacks prompt-absence assertion')
   expected['footer']={'text':'Press K3 to confirm','present':False}
  elif kind!='manual-player-apply-start':raise ValueError('Unsupported Player Apply checkpoint')
  verify_cached_ui(state,expected,path)
  key3=[item.get('state') for item in step.get('inputs',[]) if item.get('type')=='key' and item.get('n')==3]
  if kind=='manual-player-apply-pending' and 1 in key3:raise ValueError('Pending checkpoint already contains K3 confirmation')
  if kind in ('manual-player-apply-applied','manual-player-apply-reopened') and key3!=[1,0]:raise ValueError('Completed checkpoint lacks exact public K3 press/release')

def check_player_apply_scene(scene):
  if scene.get('behaviour_case')!='M-MANUAL-PLAYER-APPLY-001':return
  if scene.get('profile')!='manual-player-ui':raise ValueError('Player Apply scene uses the wrong profile')
  steps=scene.get('steps',[]);kinds=tuple(step['output']['binding']['assertion'].get('kind') for step in steps)
  expected=('manual-player-apply-start','manual-player-apply-pending','manual-player-apply-applied','manual-player-apply-reopened')
  if len(steps)!=4 or kinds!=expected:raise ValueError('Player Apply states are missing or out of order')
  rows=[step['output']['binding']['assertion'] for step in steps]
  if len({row.get('channel') for row in rows})!=1 or any(row.get('citation')!='manual:mods-and-software-devices' or row.get('field')!='Device' for row in rows):raise ValueError('Player Apply channel or manual citation changed')
  value=rows[1].get('value')
  if not isinstance(value,str) or not value.strip() or any(row.get('value')!=value for row in rows[2:]):raise ValueError('Device value does not persist from pending through reopening')
  pending=[i for i in steps[1]['inputs'] if i.get('type')=='key' and i.get('n')==3 and i.get('state')==1]
  applied=[i.get('state') for i in steps[2]['inputs'] if i.get('type')=='key' and i.get('n')==3]
  if pending or applied!=[1,0]:raise ValueError('K3 input does not distinguish pending from applied state')

def check_reason_midi(row,events,clock_mode):
 allowed=2e-9 if clock_mode=='controlled-experimental' else .02
 if row.get('tolerance_seconds')!=allowed:raise ValueError('Reason MIDI lane tolerance changed')
 start=row.get('midi_start_index')
 if type(start)is not int or start<0:raise ValueError('Reason MIDI lacks explicit native start index')
 notes=[];key='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns'
 for packet in events:
  if packet.get('kind')!=(11 if clock_mode=='controlled-experimental' else 3) or packet.get('index',0)<=start or packet.get('port')!=1:continue
  for message in packet.get('decoded',[]):
   if message.get('type')=='note_on' and message.get('channel')==row['channel'] and message['data'][1]>0:notes.append((packet[key],message['data']))
 expected=row['expected']
 if len(notes)<len(expected):raise ValueError('Reason MIDI has missing native attacks')
 origin=notes[0][0]
 for (timestamp,data),(pulse,pitch,velocity) in zip(notes,expected):
  if data!=[pitch,velocity] or abs((timestamp-origin)/1e9-pulse/144)>allowed:raise ValueError('Reason MIDI exact native pulse/pitch/velocity mismatch')
 absent=row['absent_pulse']/144
 if any(abs((timestamp-origin)/1e9-absent)<=allowed for timestamp,data in notes):raise ValueError('Reason MIDI emitted suppressed native step')
def verify_reason_checkpoint(step,observations,path,clock_mode):
 row=step['output']['binding']['assertion'];kind=row.get('kind')
 if kind=='manual-reason-midi':
  events=[json.loads(line) for line in (path/'native/native-events.jsonl').read_text().splitlines()]
  check_reason_midi(row,events,clock_mode)
 elif kind=='manual-reason-dashboard':
  binding=step['output']['binding'];states=[item['state'] for item in observations if item['state']['frame']['sha256']==binding['sha256'] and item['state']['grid']==step['output']['grid']]
  if not states or len(row.get('rows',[]))!=6:raise ValueError('Missing exact Reason dashboard native frame/rows')
  verify_cached_ui(states[0],dict(reason_rows=row['rows']),path)
def vertical_checkpoint_contract(row):
 checkpoint=row.get('checkpoint');wanted={
  'clock-neighbors':dict(rows=['Rate','Feel source','Swing type']),
  'inherit-sentinel':dict(label='Swing type',value='X'),
  'scroll-end':dict(label='Shuffle amount',value='0'),
  'masks-unchanged':dict(layout='overview_masks'),
  'single-field':dict(label='Tresillo amount',value='x8')}
 if checkpoint not in wanted:raise ValueError('Unsupported vertical-list checkpoint')
 if any(row.get(key)!=value for key,value in wanted[checkpoint].items()):raise ValueError('Changed literal vertical-list checkpoint')
 if checkpoint=='clock-neighbors':return dict(field=dict(layout='vertical_list',label='Rate',value='/1'),vertical_labels=[['Rate',27,True],['Feel source',36,False],['Swing type',45,False]])
 if checkpoint=='masks-unchanged':return dict(mask_overview=True)
 return dict(field=dict(layout='vertical_list',label=row['label'],value=row['value']))
def check_vertical_public_inputs(row,inputs):
 if row['checkpoint']=='scroll-end' and not any(value.get('type')=='enc' and value.get('n')==2 and value.get('delta')==126 for value in inputs):raise ValueError('Vertical scroll boundary lacks exact public encoder delta')
def verify_vertical_checkpoint(step,observations,path):
 row=step['output']['binding']['assertion']
 if row.get('kind')!='vertical-list-ui':return
 expected=vertical_checkpoint_contract(row);check_vertical_public_inputs(row,step['inputs']);binding=step['output']['binding']
 from ui_map import header_parts
 page={'masks-unchanged':'masks','single-field':'trigger_editor_confirmation'}.get(row['checkpoint'],'clock_mods');expected['literal_header']=list(header_parts(page,channel=1))
 states=[item['state'] for item in observations if item['state']['frame']['sha256']==binding['sha256'] and item['state']['grid']==step['output']['grid']]
 if not states:raise ValueError('Missing bound native vertical-list image')
 verify_cached_ui(states[0],expected,path)
def check_course_midi(row,events,clock_mode):
 from collections import Counter
 allowed=2e-9 if clock_mode=='controlled-experimental' else .01;key='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns';kind=11 if clock_mode=='controlled-experimental' else 3
 if row.get('bpm')!=90 or row.get('cycles')!=2 or row.get('timing_tolerance_seconds')!=allowed:raise ValueError('Course exact tempo/cycle/lane tolerance changed')
 period=row['cycle_steps'];start=row['midi_start_index'];end=row['midi_end_index']
 if type(period)is not int or period<1 or type(start)is not int or type(end)is not int or not 0<=start<end or row.get('next_cycle_index')!=end+1:raise ValueError('Course native packet window changed')
 expected=row['expected']
 if not expected or any(set(item)!={'port','status','note','velocity','step','length'} or item['status']<144 or item['status']>159 or item['velocity']<=0 or not 0<=item['step']<period or item['length']<=0 for item in expected):raise ValueError('Invalid exact Course phrase')
 wanted=[dict(item,step=item['step']+cycle*period) for cycle in range(2) for item in expected]
 packets=[item for item in events if item.get('kind')==kind and start<item.get('index',0)<=end and len(item.get('bytes',[]))==3 and 128<=item['bytes'][0]<=159]
 required=Counter((item['port'],item['status'],item['note'],item['velocity']) for item in wanted);required.update((item['port'],item['status']-16,item['note'],item['velocity']) for item in wanted)
 if Counter((item['port'],*item['bytes']) for item in packets)!=required:raise ValueError('Course exact native packet inventory differs')
 notes=[item for item in packets if 144<=item['bytes'][0]<=159 and item['bytes'][2]>0];origin=min(item[key] for item in notes)
 boundary=[item for item in events if item.get('kind')==kind and item.get('index')==end+1]
 if len(boundary)!=1 or not 144<=boundary[0]['bytes'][0]<=159 or boundary[0]['bytes'][2]<=0 or abs((boundary[0][key]-origin)/1e9-period*2/6)>allowed:raise ValueError('Course next-cycle native boundary differs')
 for port in {item['port'] for item in wanted}:
  actual=[item for item in notes if item['port']==port];literal=sorted([item for item in wanted if item['port']==port],key=lambda item:item['step'])
  if [item['bytes'] for item in actual]!=[[item['status'],item['note'],item['velocity']] for item in literal]:raise ValueError('Course exact native note order differs')
  for note,item in zip(actual,literal):
   if abs((note[key]-origin)/1e9-item['step']/6)>allowed:raise ValueError('Course exact native onset differs')
   releases=[packet for packet in packets if packet['index']>note['index'] and packet['port']==port and packet['bytes']==[item['status']-16,item['note'],item['velocity']]]
   if not releases or abs((releases[0][key]-note[key])/1e9-item['length']/6)>allowed:raise ValueError('Course exact native gate differs')
def check_song_indicators(row,state,events,clock_mode):
 expected={'copied-selected':[7,15,2],'playing':[7,15,2],'empty-copy-erases':[15,2,2]}.get(row.get('stage'))
 if expected is None or row.get('levels')!=expected or state['grid'][:3]!=expected:raise ValueError('Song native LED indicators differ from literal stage')
 if row['stage']!='playing':return
 phrase=[[144,60,127],[144,62,117],[144,64,107],[144,65,97]];allowed=2e-9 if clock_mode=='controlled-experimental' else .01;key='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns';kind=11 if clock_mode=='controlled-experimental' else 3
 if row.get('phrase')!=phrase or row.get('tolerance_seconds')!=allowed or type(row.get('midi_start_index'))is not int:raise ValueError('Song native phrase metadata changed')
 notes=[item for item in events if item.get('kind')==kind and item.get('index',0)>row['midi_start_index'] and len(item.get('bytes',[]))==3 and 144<=item['bytes'][0]<=159 and item['bytes'][2]>0][:4]
 if len(notes)!=4 or [item['bytes'] for item in notes]!=phrase or any(item['port']!=1 for item in notes):raise ValueError('Song exact native phrase differs')
 if any(abs((item[key]-notes[0][key])/1e9-index/6)>allowed for index,item in enumerate(notes)):raise ValueError('Song exact native phrase pulse differs')
def check_real_song_queue_waveform(row,observations,events,intervals):
 # Visual callback/flush bound, independent of all musical onset/gate tolerances.
 timing=dict(blink_period_ns=400000000,grid_flush_period_ns=50000000,real_clock_allowance_ns=10000000,min_transition_ns=340000000,max_transition_ns=460000000,observation_poll_ns=30000000,window_ns=3330000000,source='mosaic.lua blink clock.sleep(0.4); grid_redraw clock.sleep(1/20); existing real musical allowance0.01s')
 if row.get('timing_contract')!=timing:raise ValueError('Changed source-derived real visual waveform timing contract')
 samples=row['samples'];first,last=samples[0]['monotonic_ns'],samples[-1]['monotonic_ns'];span=last-first
 if any(not 0<delta<timing['min_transition_ns'] for delta in intervals) or not span>=timing['window_ns'] or span-intervals[-1]>=timing['window_ns']:raise ValueError('Real queue waveform observation period/window aliases or changed')
 grids=[(i,event) for i,event in enumerate(events) if event.get('kind')==2]
 frame_hashes={event.get('sha256') for event in events if event.get('kind')==1}
 for sample in samples:
  observation=observations[sample['observation_index']];revision=observation.get('grid_revision')
  if type(revision)is not int or not 1<=revision<=len(grids) or sample.get('grid_revision')!=revision:raise ValueError('Missing exact native queue sample grid revision')
  event=grids[revision-1][1]
  if event['leds']!=observation['state']['grid'] or event['monotonic_ns']>sample['monotonic_ns'] or sample['frame_sha256'] not in frame_hashes:raise ValueError('Queue sample does not bind actual native grid/frame revision')
 rows=[];previous=samples[0]['levels'][0]
 for index,event in grids:
  if not first<event['monotonic_ns']<=last:continue
  levels=event['leds'][:3]
  if levels[0] not in (1,7) or levels[1:]!=[15,2]:raise ValueError('Native real queue waveform changed literal levels/neighbors')
  if levels[0]!=previous:
   rows.append(dict(native_event_index=index,id=event['id'],monotonic_ns=event['monotonic_ns'],leds_sha256=canonical_hash(event['leds']),levels=levels));previous=levels[0]
 if row.get('native_grid_transitions')!=rows:raise ValueError('Real queue waveform receipt differs from complete actual native transitions')
 if len(rows)<7:raise ValueError('Need seven native queue changes and six complete visual dwells')
 dwells=[b['monotonic_ns']-a['monotonic_ns'] for a,b in zip(rows,rows[1:])]
 if any(not timing['min_transition_ns']<=delta<=timing['max_transition_ns'] for delta in dwells) or rows[0]['monotonic_ns']-first>timing['max_transition_ns'] or last-rows[-1]['monotonic_ns']>timing['max_transition_ns']:raise ValueError('Real native queue waveform dwell/dropout differs from source bound')
 return dict(transitions=len(rows),complete_dwells=len(dwells),dwell_intervals_ns=dwells,source_timing=timing,initial_phase_censored=True)

def check_applied_native_input(event,native,events,clock_mode):
 if event.get('sequence')!=native.get('sequence'):raise ValueError('Native input sequence differs from applied receipt')
 applied=[e for e in events if e.get('kind')==4 and e.get('id')==native['sequence']]
 timing=[e for e in events if e.get('kind')=='input_timing' and e.get('sequence')==native['sequence']]
 if len(applied)!=1 or len(timing)!=1:raise ValueError('Missing unique native applied input/timing record')
 t=timing[0];completed=native['monotonic_ns']
 if applied[0]['monotonic_ns']!=completed or t.get('native_ack_ns')!=completed or not event['monotonic_ns']<=t['submission_start_ns']<=t['submitted_ns']<=t['monotonic_ns'] or not event['monotonic_ns']<=completed<=t['monotonic_ns']:raise ValueError('Native received/submitted/applied input ordering differs')

def check_song_queue_blink(row,observations,recipe,events,actions,clock_mode):
 import base64
 if (row.get('queued_slot'),row.get('playing_slot'),row.get('period_ns'))!=(1,2,400000000):raise ValueError('Changed literal Song queue blink contract')
 samples=row.get('samples',[]);indices=[item.get('observation_index') for item in samples]
 controlled=clock_mode=='controlled-experimental'
 if (len(samples)!=7 if controlled else len(samples)<7) or any(type(index)is not int or not 0<=index<len(observations) for index in indices) or indices!=sorted(set(indices)):raise ValueError('Song queue requires seven distinct native samples')
 times=[]
 for index,item in enumerate(samples):
  observation=observations[item['observation_index']];state=observation['state'];pixels=base64.b64decode(state['frame']['pixels_base64']);levels=[1 if index%2==0 else 7,15,2] if controlled else [state['grid'][0],15,2]
  if not controlled and levels[0] not in (1,7):raise ValueError('Changed literal real queued blink level')
  if len(pixels)!=32768 or hashlib.sha256(pixels).hexdigest()!=state['frame']['sha256'] or item['frame_sha256']!=state['frame']['sha256'] or item['grid_sha256']!=canonical_hash(state['grid']) or item['monotonic_ns']!=observation['monotonic_ns'] or item['levels']!=state['grid'][:3] or item['levels']!=levels:raise ValueError('Changed exact native queue sample')
  logical=state['clock']['logical_ns'] if clock_mode=='controlled-experimental' else None
  if item['logical_ns']!=logical:raise ValueError('Changed native queue sample clock')
  times.append(logical if logical is not None else observation['monotonic_ns'])
 if any(b['monotonic_ns']<=a['monotonic_ns'] for a,b in zip(samples,samples[1:])):raise ValueError('Song queue native sample timestamps do not advance')
 intervals=[after-before for before,after in zip(times,times[1:])]
 if controlled and any(delta!=400000000 for delta in intervals):raise ValueError('Changed native queue sample period')
 waveform=check_real_song_queue_waveform(row,observations,events,intervals) if not controlled else None
 if controlled and (row.get('timing_contract') is not None or row.get('native_grid_transitions',[])!=[]):raise ValueError('Controlled queue timing contract changed')
 start=row.get('recipe_start_index');end=row.get('recipe_end_index');expected=[dict(type='grid',x=1,y=1,state=value) for value in (1,0)]
 if type(start)is not int or type(end)is not int or not 0<=start<end<=len(recipe) or recipe[start:end]!=expected:raise ValueError('Song queue differs from exact public grid edges')
 matched=[index for index,action in enumerate(actions) if action['request']['sequence']==row.get('input_sequence')]
 if len(matched)!=1:raise ValueError('Missing unique native queue input acknowledgment')
 edge_actions=actions[matched[0]:matched[0]+2]
 if len(edge_actions)!=2 or edge_actions[0]['ack']['native']!=row.get('native') or edge_actions[1]['request']['sequence']!=row['input_sequence']+1:raise ValueError('Changed native queue input acknowledgment')
 for action,required in zip(edge_actions,expected):
  ack=action['ack'];native=ack['native'];actual=[event for event in events if event.get('kind')=='input' and event.get('sequence')==native['sequence']]
  if action['request']['action']!=required or ack['status']!='applied' or len(actual)!=1 or actual[0]['type']!=3 or actual[0]['args']!=[0,0,required['state']] or native['monotonic_ns']>observations[indices[0]]['monotonic_ns']:raise ValueError('Missing exact applied native queue input edge')
  check_applied_native_input(actual[0],native,events,clock_mode)
 return dict(sample_span_ns=times[-1]-times[0],sample_intervals_ns=intervals,clock_mode=clock_mode,real_waveform=waveform,hardware_timing_verified=False)
def check_song_queue_transition(row,state,events,clock_mode):
 allowed=2e-9 if clock_mode=='controlled-experimental' else .01;kind=11 if clock_mode=='controlled-experimental' else 3;key='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns'
 wanted=dict(from_slot=2,to_slot=1,transition_index=32,old_phrase=[60,62,64,65],new_phrase=[72,74,76,77],velocities=[127,117,107,97],onset_spacing_seconds=1/6,tolerance_seconds=allowed,levels=[15,7,2])
 if any(row.get(field)!=value for field,value in wanted.items()) or type(row.get('midi_start_index'))is not int:raise ValueError('Changed literal Song queued transition contract')
 if state['grid'][:3]!=wanted['levels'] or state['grid'][112]!=2 or state['midi_capture']['outstanding']!=[]:raise ValueError('Song queue transport/notes not stopped at destination')
 packets=[event for event in events if event.get('kind')==kind and row['midi_start_index']<event.get('index',0)<=state['midi_count'] and len(event.get('bytes',[]))==3];notes=[event for event in packets if 144<=event['bytes'][0]<=159 and event['bytes'][2]>0]
 if len(notes)<37 or row.get('onsets')!=len(notes):raise ValueError('Song queue lacks complete old cycles and destination phrase')
 releases=[]
 for index,note in enumerate(notes):
  phrase=wanted['old_phrase'] if index<32 else wanted['new_phrase'];expected=[144,phrase[index%4],wanted['velocities'][index%4]]
  if note['port']!=1 or note['bytes']!=expected or abs((note[key]-notes[0][key])/1e9-index/6)>allowed:raise ValueError('Song queue wire phrase or exact transition pulse differs')
  matching=[event for event in packets if event['index']>note['index'] and event['port']==1 and event['bytes']==[128,expected[1],expected[2]]]
  if not matching:raise ValueError('Missing exact native Song queue gate release')
  release=matching[0];duration=(release[key]-note[key])/1e9
  if release['index'] in releases or (abs(duration-1/6)>allowed if index<len(notes)-1 else not 0<=duration<=1/6+allowed):raise ValueError('Song queue gate differs from exact musical length')
  releases.append(release['index'])
 if len(packets)!=2*len(notes) or len(set(releases))!=len(notes):raise ValueError('Song queue contains extra or unbalanced wire packets')
def check_queue_documentation(row,binding,grid,observations,events):
 last=row['samples'][-1]['observation_index'];start=observations[last]['monotonic_ns']
 next_inputs=[e['monotonic_ns'] for e in events if e.get('kind')=='input' and e.get('type') in (1,2,3) and e['monotonic_ns']>start]
 if not next_inputs:raise ValueError('Missing next public gesture boundary for queue documentation')
 end=min(next_inputs)
 if not any(start<=item['monotonic_ns']<=end and item['state']['frame']['sha256']==binding['sha256'] and item['state']['grid']==grid for item in observations[last:]):raise ValueError('Song queue documentation frame precedes sampled blink or follows next public gesture')

def check_course_dashboard(row,observations,binding,grid):
 import base64,frame_oracle
 slot=row.get('params',{}).get('song_slot')
 if type(slot)is not int or slot not in (1,2) or row.get('stage')!='song-composition-global-length-slot%d'%slot or row.get('page')!='song' or row.get('header')!=dict(title='SONG PLAYBACK',scope='SONG %02d'%slot,layout='dashboard') or row.get('dashboard_rows')!=[dict(row=4,label='Global length',value='16')]:raise ValueError('Unsupported exact course Song dashboard contract')
 index=row.get('native_observation_index')
 if type(index)is not int or not 0<=index<len(observations):raise ValueError('Missing exact course dashboard native observation')
 state=observations[index]['state'];pixels=base64.b64decode(state['frame']['pixels_base64'])
 if len(pixels)!=32768 or hashlib.sha256(pixels).hexdigest()!=state['frame']['sha256'] or state['frame']['sha256']!=binding['sha256'] or state['grid']!=grid:raise ValueError('Course dashboard differs from bound native frame/grid')
 if not frame_oracle.dashboard_row_matches(state,4,'Global length','16'):raise ValueError('Course native dashboard Global length is not16')
 return state

def verify_teaching_checkpoint(step,observations,path,clock_mode,results):
 row=step['output']['binding']['assertion'];kind=row.get('kind','')
 if kind.startswith('manual-save-dialog-'):
  import importlib.util
  receipt=json.loads((Path(path).parent/'start-source-identity.json').read_text())
  sources=receipt.get('case_sources',{})
  shim='tests/behaviour/manual_save_dialog_oracle.py'
  implementation='tests/behaviour/contract/manual_save_dialog_oracle.py'
  if implementation in sources:
   for relative in (shim,implementation):
    cached_source=Path(path).parent/'case-source'/relative
    if sources.get(relative)!=digest(cached_source):raise ValueError('Unhashed or changed dialog source cache')
   cached=Path(path).parent/'case-source'/implementation
  else:
   cached=Path(path).parent/'case-source'/shim
   if sources.get(shim)!='f65bf1a840e9060d6acfff8c6d8db8abc05487957c81b8b3fc148aad6470aa4a':raise ValueError('Missing contract-owned dialog implementation hash')
   if digest(cached)!='f65bf1a840e9060d6acfff8c6d8db8abc05487957c81b8b3fc148aad6470aa4a':raise ValueError('Unrecognized or changed legacy flat dialog source cache')
  spec=importlib.util.spec_from_file_location('_native_save_dialog_audit',cached)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  module.verify_checkpoint(step,observations,path)
  return
 if not kind.startswith(('manual-course-','manual-song-')):return
 supported={'manual-course-ui','manual-course-midi','manual-course-persistence','manual-song-indicators','manual-song-slot-setting','manual-song-queue-blink','manual-song-queue-transition','manual-song-repeat-advance'}
 if kind not in supported:raise ValueError('Unsupported new manual semantic kind requires independent native verification')
 binding=step['output']['binding'];states=[item['state'] for item in observations if item['state']['frame']['sha256']==binding['sha256'] and item['state']['grid']==step['output']['grid']]
 if not states:raise ValueError('Missing bound native teaching image')
 state=states[0];events=[json.loads(line) for line in (path/'native/native-events.jsonl').read_text().splitlines()]
 if kind=='manual-song-indicators':check_song_indicators(row,state,events,clock_mode)
 elif kind=='manual-song-queue-transition':check_song_queue_transition(row,state,events,clock_mode)
 elif kind=='manual-song-queue-blink':
  recipe=json.loads((path/'recipe.json').read_text());actions=[json.loads(line) for line in (path/'native/actions.jsonl').read_text().splitlines()]
  check_song_queue_blink(row,observations,recipe,events,actions,clock_mode)
  check_queue_documentation(row,binding,step['output']['grid'],observations,events)
 elif kind=='manual-song-slot-setting':
  if row.get('field')!='Repeats' or row.get('value') not in (1,16,2):raise ValueError('Unsupported literal Song slot value')
  verify_cached_ui(state,dict(field=dict(layout='vertical_list',label='Repeats',value=str(row['value']))),path)
 elif kind=='manual-course-midi':
  import importlib.util
  specification=importlib.util.spec_from_file_location('manual_course_authored_contract',ROOT/'tools/manual_course_cases.py');module=importlib.util.module_from_spec(specification);specification.loader.exec_module(module)
  if row.get('stage') not in module.CONTRACTS or (row['cycle_steps'],row['expected'])!=module.CONTRACTS[row['stage']]:raise ValueError('Course MIDI differs from pinned authored literal phrase')
  check_course_midi(row,events,clock_mode)
 elif kind=='manual-course-ui':
  if 'dashboard_rows' in row or row.get('stage') in ('song-composition-global-length-slot1','song-composition-global-length-slot2'):state=check_course_dashboard(row,observations,binding,step['output']['grid'])
  from ui_map import header_parts
  if row['page'] in ('song_setup','song_global_settings'):
   title='SLOT SETUP' if row['page']=='song_setup' else 'GLOBAL FEEL';header=[title,'SONG %02d'%row['params'].get('song_slot',1),'vertical_list']
  else:header=list(header_parts(row['page'],**row['params']))
  if row['header']!=dict(zip(('title','scope','layout'),header)):raise ValueError('Course UI header differs from literal page contract')
  expected=dict(literal_header=header,mask_fields=row['mask_fields'])
  if row.get('selected_field'):expected['field']=row['selected_field']
  verify_cached_ui(state,expected,path)
  for cell in row['leds']:
   if type(cell['x'])is not int or type(cell['y'])is not int or not 1<=cell['x']<=16 or not 1<=cell['y']<=8 or state['grid'][(cell['y']-1)*16+cell['x']-1]!=cell['level']:raise ValueError('Course native grid LED differs')
 elif kind=='manual-course-persistence':
  if row.get('stage') not in ('keep-your-work-save','keep-your-work-loaded-files') or row.get('name')!='Four notes' or set(row['files'])!={'Four notes.ptn','Four notes.pset'} or Path(row['evidence_directory']).resolve()!=(path/'course-project-evidence').resolve():raise ValueError('Unsupported named course persistence receipt')
  pair=[item for item in results if item.get('kind')=='manual-course-persistence']
  if len(pair)!=2 or {item['stage'] for item in pair}!={'keep-your-work-save','keep-your-work-loaded-files'} or any(item['files']!=row['files'] for item in pair):raise ValueError('Course saved and loaded native files differ')
  for receipt in pair:
   for filename,sha in receipt['files'].items():
    if digest(path/'course-project-evidence'/(receipt['stage']+'-'+filename))!=sha:raise ValueError('Changed named course native project copy')
  replay=[item for item in results if item.get('kind')=='manual-course-midi' and item.get('stage')=='keep-your-work-perform']
  if len(replay)!=1:raise ValueError('Named course load lacks native replay acceptance')
  check_course_midi(replay[0],events,clock_mode)
def check_motion_samples(row,observations,clock_mode,events,results,assertion_index):
 import base64
 mini=row.get('public_mini_header_assertion')
 if not isinstance(mini,dict) or mini.get('kind')!='public-mini-header' or mini.get('page')!='C04' or mini.get('enabled')!=row.get('enabled') or mini.get('tempo')!=90 or mini.get('all_distinct_poses_required') is not row.get('enabled'):raise ValueError('Motion requires complete original C04 native mini proof')
 if type(assertion_index)is not int or not 0<=assertion_index<len(results) or results[assertion_index]!=row or assertion_index<5 or results[assertion_index-5]!=mini or [(r.get('kind'),r.get('enabled'),r.get('phase')) for r in results[assertion_index-4:assertion_index]]!=[('manual-motion-pose',row.get('enabled'),'rest'),('documentation-frame',None,None),('manual-motion-pose',row.get('enabled'),'moved'),('documentation-frame',None,None)]:raise ValueError('Motion mini proof is not its exact preceding native result')
 check_mini_samples(mini,observations,events)
 spec=next(item for item in json.loads((ROOT/'tests/behaviour/contract/mini_header_atlas_v2.json').read_text())['screens'] if item['id']=='C04')
 x,y=spec['origin'];height=len(spec['frames'][0]);width=len(spec['frames'][0][0]);samples=row.get('samples',[])
 if len(samples)!=len(mini['samples']):raise ValueError('Motion samples differ from original native mini proof')
 states=[];marks=[]
 for item,original in zip(samples,mini['samples']):
  if {key:value for key,value in item.items() if key not in ('grid_sha256','logical_ns','mark_sha256')}!=original:raise ValueError('Motion changed original exact native mini sample')
  observation=observations[item['observation_index']];state=observation['state'];pixels=base64.b64decode(state['frame']['pixels_base64'])
  logical=state['clock']['logical_ns'] if clock_mode=='controlled-experimental' else None
  if state['clock']['mode']!=clock_mode or item.get('logical_ns')!=logical or item.get('grid_sha256')!=canonical_hash(state['grid']):raise ValueError('Motion changed native sample clock/grid')
  mark=bytes(pixels[(yy*128+xx)*4+channel] for yy in range(8) for xx in range(96,128) for channel in range(3));sha=hashlib.sha256(mark).hexdigest()
  if item.get('mark_sha256')!=sha:raise ValueError('Motion marker differs from full admitted C04 mini window')
  marks.append(sha);states.append(state)
 changed=len(set(marks))>1
 if type(row.get('enabled'))is not bool or changed!=row['enabled'] or row.get('decorative_mark_changed')!=changed:raise ValueError('Motion native marker variation differs from Off/On')
 return states
def check_motion_feedback(row,observations,recipe,events,actions):
 receipts=row.get('response_receipts',[])
 if row.get('public_feedback_bound_seconds')!=.25 or [item.get('stage') for item in receipts]!=['edit','restore']:raise ValueError('Missing exact motion response receipts')
 for item,delta in zip(receipts,[-2,2]):
  before=item['before_observation_index'];after=item['response_observation_index'];start=item['recipe_start_index'];end=item['recipe_end_index']
  if any(type(index)is not int for index in (before,after,start,end)) or not 0<=before<after<len(observations) or not 0<=start<end<=len(recipe):raise ValueError('Invalid native motion response boundary')
  expected=[dict(type='enc',n=3,delta=delta),dict(type='key',n=3,state=1),dict(type='key',n=3,state=0)]
  if recipe[start:end]!=expected:raise ValueError('Motion feedback differs from exact public encoder/key edges')
  match=[index for index,action in enumerate(actions) if action['request']['sequence']==item['input_sequence']]
  if len(match)!=1:raise ValueError('Missing unique motion input acknowledgment')
  index=match[0];native=actions[index]['ack']['native']
  if native!=item['native'] or actions[index]['ack']['status']!='applied' or [value['request']['action'] for value in actions[index:index+3]]!=expected:raise ValueError('Changed acknowledged motion native input edges')
  actual=[value for value in events if value.get('kind')=='input' and value.get('sequence')==native['sequence']]
  if len(actual)!=1 or actual[0]['type']!=2 or actual[0]['args']!=[3,delta]:raise ValueError('Changed actual motion encoder receipt')
  check_applied_native_input(actual[0],native,events,observations[before]['state']['clock']['mode'])
  earlier=observations[before];later=observations[after];controlled=earlier['state']['clock']['mode']=='controlled-experimental';t0=earlier['state']['clock']['logical_ns'] if controlled else earlier['monotonic_ns'];t1=later['state']['clock']['logical_ns'] if controlled else later['monotonic_ns']
  if not 0<=t1-t0<=250000000:raise ValueError('Native motion UI feedback exceeds admitted quarter-second bound')
  if not earlier['monotonic_ns']<=actual[0]['monotonic_ns']<=later['monotonic_ns']:raise ValueError('Motion encoder acknowledgment lies outside native response observations')
  for action,expected_edge in zip(actions[index:index+3],expected):
   ack=action['ack'];edge=ack['native'];native_edges=[event for event in events if event.get('kind')=='input' and event.get('sequence')==edge['sequence']]
   required_type=2 if expected_edge['type']=='enc' else 1;required_args=[expected_edge['n'],expected_edge.get('delta',expected_edge.get('state'))]
   if ack['status']!='applied' or len(native_edges)!=1 or native_edges[0]['type']!=required_type or native_edges[0]['args']!=required_args or not earlier['monotonic_ns']<=edge['monotonic_ns']<=later['monotonic_ns']:raise ValueError('Motion response lacks exact applied native input edge')
   check_applied_native_input(native_edges[0],edge,events,earlier['state']['clock']['mode'])
 return receipts
def check_motion_music(row,state,events,clock_mode):
 allowed=2e-9 if clock_mode=='controlled-experimental' else .01;kind=11 if clock_mode=='controlled-experimental' else 3;key='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns'
 if row.get('pitches')!=[60,62,64,65] or row.get('velocities')!=[127,117,107,97] or row.get('onset_spacing_seconds')!=1/6 or row.get('tolerance_seconds')!=allowed or row.get('stopped') is not True or type(row.get('midi_start_index'))is not int:raise ValueError('Changed literal motion musical contract')
 if state['grid'][112]!=2 or state['midi_capture']['outstanding']!=[]:raise ValueError('Motion native transport/notes not stopped')
 packets=[item for item in events if item.get('kind')==kind and row['midi_start_index']<item.get('index',0)<=state['midi_count'] and len(item.get('bytes',[]))==3];notes=[item for item in packets if 144<=item['bytes'][0]<=159 and item['bytes'][2]>0]
 if len(notes)<9:raise ValueError('Motion native music lacks two complete cycles and next onset')
 for index,note in enumerate(notes):
  offset=index%4;expected=[144,row['pitches'][offset],row['velocities'][offset]]
  if note['port']!=1 or note['bytes']!=expected or abs((note[key]-notes[0][key])/1e9-index/6)>allowed:raise ValueError('Motion exact native wire phrase/pulse differs')
  if index<8:
   releases=[item for item in packets if item['index']>note['index'] and item['port']==1 and item['bytes']==[128,expected[1],expected[2]]]
   if not releases or abs((releases[0][key]-note[key])/1e9-1/6)>allowed:raise ValueError('Motion exact native musical gate differs')
def verify_motion_checkpoint(step,observations,path,clock_mode):
 row=step['output']['binding']['assertion'];kind=row.get('kind')
 if kind not in ('manual-motion-stable-rows','manual-motion-music'):return
 binding=step['output']['binding'];state=next(item['state'] for item in observations if item['state']['frame']['sha256']==binding['sha256'] and item['state']['grid']==step['output']['grid']);events=[json.loads(line) for line in (path/'native/native-events.jsonl').read_text().splitlines()]
 if kind=='manual-motion-music':check_motion_music(row,state,events,clock_mode);return
 if row.get('rows')!=['Rate','Feel source','Swing type'] or row.get('clock_value')!='/1' or row.get('sample_selected_row')!=0 or row.get('sample_clock_value')!='/1.5':raise ValueError('Changed literal essential motion rows')
 actions=[json.loads(line) for line in (path/'native/actions.jsonl').read_text().splitlines()];receipts=check_motion_feedback(row,observations,json.loads((path/'recipe.json').read_text()),events,actions);results=json.loads((path/'results.json').read_text());states=check_motion_samples(row,observations,clock_mode,events,results,binding['assertion_index'])
 labels=[['Rate',27,True],['Feel source',36,False],['Swing type',45,False]]
 for sample in states:verify_cached_ui(sample,dict(literal_header=['CLOCK','CH01','vertical_list'],vertical_labels=labels,vertical_values=[['/1.5',27,True],['GLOBAL',36,False],['X',45,False]]),path)
 verify_cached_ui(state,dict(literal_header=['CLOCK','CH01','vertical_list'],vertical_labels=labels,vertical_values=[['/1',27,True],['GLOBAL',36,False],['X',45,False]]),path)
 if receipts[0]['response_observation_index']>=row['samples'][0]['observation_index'] or receipts[1]['before_observation_index']<=row['samples'][-1]['observation_index']:raise ValueError('Motion sample sequence lies outside acknowledged edit/restore')
 for receipt,value in zip(receipts,['/1.5','/1']):verify_cached_ui(observations[receipt['response_observation_index']]['state'],dict(literal_header=['CLOCK','CH01','vertical_list'],field=dict(layout='vertical_list',label='Rate',value=value)),path)
CLOSURE_REPEAT_STAGES={'slot-1':([15,7,2],'1 / 1',[60,62,64,65],4),'slot-2-pass-1':([7,15,2],'1 / 2',[72,74,76,77],12),'slot-2-pass-2':([7,15,2],'2 / 2',[72,74,76,77],20),'wrapped':([15,7,2],'1 / 1',[60,62,64,65],28)}
def check_motion_pose(row,state,results):
 # README UI Motion: the Clock mark moves only with UI motion On. Recompute the mark from the bound native frame.
 import base64
 from contract.mini_header_animation_ui import atlas,left_edge
 spec=atlas()['C04'];pixels=base64.b64decode(state['frame']['pixels_base64'])
 mark=hashlib.sha256(bytes(pixels[(y*128+x)*4+k] for y in range(8) for x in range(left_edge(spec),128) for k in range(3))).hexdigest()
 if row.get('clock_value')!='/1.5' or type(row.get('enabled'))is not bool or row.get('phase')not in('rest','moved') or row.get('mark_sha256')!=mark:raise ValueError('Motion pose mark differs from its bound native frame')
 rest=[r for r in results if r.get('kind')=='manual-motion-pose' and r.get('enabled')is row['enabled'] and r.get('phase')=='rest']
 if len(rest)!=1 or rest[0]['mark_sha256']!=row['rest_mark_sha256'] or row['at_rest']is not (mark==row['rest_mark_sha256']):raise ValueError('Motion pose rest comparison differs')
 if (not row['enabled'] or row['phase']=='rest') != row['at_rest']:raise ValueError('UI motion Off must stay at rest; On must have moved')
def native_midi_events(events,clock_mode):
 kind=11 if clock_mode=='controlled-experimental' else 3
 return [e for e in events if e.get('kind')==kind and e.get('bytes')]
def check_song_repeat_advance(row,state,events,clock_mode):
 expected=CLOSURE_REPEAT_STAGES.get(row.get('stage'))
 if not expected or [row.get(k) for k in('levels','pass_text','latest_pitches','onsets_so_far')]!=[expected[0],expected[1],expected[2],expected[3]]:raise ValueError('Changed literal Song repeat contract')
 if state['grid'][:3]!=row['levels']:raise ValueError('Song repeat grid levels differ from native state')
 low=[60,62,64,65];high=[72,74,76,77];velocity=[127,117,107,97]
 sequence=[low[i%4] for i in range(8)]+[high[i%4] for i in range(16)]+[low[i%4] for i in range(4)]
 notes=[e for e in native_midi_events(events,clock_mode) if e['index']<=state['midi_count'] and e.get('port')==1 and 144<=e['bytes'][0]<=159 and e['bytes'][2]>0]
 count=row['onsets_so_far']
 if len(notes)<count:raise ValueError('Song repeat lacks native onsets')
 window=notes[len(notes)-count:]
 if [e['bytes'][1] for e in window]!=sequence[:count] or [e['bytes'][2] for e in window]!=[velocity[i%4] for i in range(count)]:raise ValueError('Song repeat native wire sequence differs from Repeats contract')
def check_modulation_cc_phase(row,events,clock_mode):
 import math
 phase=row.get('phase');depth=row.get('depth');source=row.get('source');cc=row.get('cc')
 if phase not in('route-depth','zero-source','halfway','cleared-depth','clear-baseline','returned-to-source-baseline'):raise ValueError('Unknown modulation phase')
 if cc!=(math.floor(32+128*depth*source+.5) if depth is not None else 32):raise ValueError('Modulation CC differs from Matrix formula')
 if phase not in('zero-source','halfway','clear-baseline'):return
 if row.get('notes')!=9 or row.get('late_window_onsets')!=0:raise ValueError('Changed literal modulation phrase contract')
 midi=native_midi_events(events,clock_mode);field='logical_ns' if clock_mode=='controlled-experimental' else 'monotonic_ns';allowed=2e-9 if clock_mode=='controlled-experimental' else .01
 phrase=[(60,127),(62,117),(64,107),(65,97)]
 for start in (e for e in midi if e['bytes']==[250]):
  before=[e for e in midi if e['index']<start['index'] and e['bytes'][0]&240==176]
  after=[e for e in midi if e['index']>start['index']]
  notes=[e for e in after if e.get('port')==1 and e['bytes'][0]==144 and e['bytes'][2]>0][:9]
  if not before or before[-1]['bytes']!=[176,1,cc] or before[-1].get('port')!=1 or len(notes)<9:continue
  if all(e['port']==1 and e['bytes']==[144,*phrase[i%4]] and abs((e[field]-notes[0][field])/1e9-i/6)<=allowed for i,e in enumerate(notes)):return
 raise ValueError('No native playback matches the modulation phase CC and phrase')
def verify_closure_checkpoint(step,observations,path,clock_mode,results):
 row=step['output']['binding']['assertion'];kind=row.get('kind')
 if kind not in('manual-motion-pose','manual-song-repeat-advance','manual-modulation-cc-phase'):return
 binding=step['output']['binding'];events=[json.loads(line) for line in (path/'native/native-events.jsonl').read_text().splitlines()]
 if kind=='manual-modulation-cc-phase':return check_modulation_cc_phase(row,events,clock_mode)
 states=[item['state'] for item in observations if item['state']['frame']['sha256']==binding['sha256'] and item['state']['grid']==step['output']['grid']]
 if not states:raise ValueError('Missing bound native image for closure checkpoint')
 if kind=='manual-motion-pose':check_motion_pose(row,states[0],results)
 else:check_song_repeat_advance(row,states[0],events,clock_mode)
def pre_finish_rows(expected):
 if not expected or set(expected)-{'header','field','menu','menu_label','menu_value'}:raise ValueError('Missing or unsupported pre-finish UI expectation')
 rows=[]
 if 'header' in expected:
  from ui_map import header_text
  header=expected['header'];rows.append(dict(kind='screen-header',expected=header_text(header['page'],**header.get('params',{})),matched=True))
 if 'field' in expected:
  field=expected['field'];rows.append(dict(kind='selected-field',layout=field['layout'],label=field.get('label'),value=field.get('value'),matched=True))
 if 'menu' in expected:
  menu=expected['menu'];rows.append(dict(kind='selected-menu-option-row',label=menu['label'],value=menu['value'],matched=True))
 if 'menu_label' in expected:rows.append(dict(kind='selected-menu-label',text=expected['menu_label']['label']))
 if 'menu_value' in expected:rows.append(dict(kind='selected-menu-value',text=expected['menu_value']['value']))
 return rows
def check_capture_stage(step,results,authored):
 binding=step['output']['binding'];docs=[index for index,row in enumerate(results) if row==binding]
 if len(docs)!=1:raise ValueError('Missing unique documentation capture row')
 document_index=docs[0];assertion_index=binding['assertion_index'];stage=binding.get('capture_stage')
 if stage is None:
  if document_index<=assertion_index:raise ValueError('Image precedes semantic oracle without an authorised capture stage')
  return
 if stage!='before-finish' or authored.get('capture_stage')!=stage:raise ValueError('Before-finish capture not authorised by pinned plan')
 expected=authored.get('pre_finish_expect')
 if binding.get('pre_finish_expect')!=expected or step.get('expect',{}).get('pre_finish_expect',expected)!=expected:raise ValueError('Changed pre-finish expectation')
 wanted=pre_finish_rows(expected);indices=binding.get('pre_finish_assertion_indices',[])
 if len(indices)!=len(wanted) or len(set(indices))!=len(indices):raise ValueError('Missing exact pre-finish assertion indices')
 if document_index>=assertion_index:raise ValueError('Before-finish frame does not precede later oracle')
 for index,row in zip(indices,wanted):
  if type(index)is not int or not 0<=index<document_index or results[index]!=row:raise ValueError('Invalid pre-finish UI assertion')
 if binding['semantic_assertions']<=max(indices):raise ValueError('Image predates pre-finish UI verification')
def verify_cached_ui(state,expected,path):
 import base64,frame_oracle
 from ui_map import header_parts,SCREEN
 identity=json.loads((path/'native/identity.json').read_text())
 # Render the independent UI oracle with the captured norns source's font.
 # The temporary descriptor selects a font only; no emulator session is started.
 with tempfile.TemporaryDirectory(prefix='manual-font-oracle-') as directory:
  runtime=Path(directory)/'.runtime';runtime.mkdir();(runtime/'current.json').write_text(json.dumps(dict(source=identity['runtime_identity']['source'])))
  previous=frame_oracle.ROOT;frame_oracle.ROOT=Path(directory)
  try:
   if 'literal_header' in expected:
    if not frame_oracle.live_header_matches(state,*expected['literal_header']):raise ValueError('Native literal screen header mismatch')
   if 'doctor_tooltip' in expected:
    actual=base64.b64decode(state['frame']['pixels_base64']);rendered=frame_oracle.render([(1,63,9,frame_oracle.fit(expected['doctor_tooltip'],126))])
    if not frame_oracle._region_matches(actual,rendered,56,64,0,128):raise ValueError('Native Doctor tooltip mismatch')
   if 'vertical_values' in expected:
    actual=base64.b64decode(state['frame']['pixels_base64'])
    for value,y,selected in expected['vertical_values']:
     left=max(7,126-int(frame_oracle.text_width(value))-2);rendered=frame_oracle.render([((None,126),y,15 if selected else 10,value)])
     if not frame_oracle._region_matches(actual,rendered,y-7,y+2,left,127):raise ValueError('Native essential vertical-list value changed')
   if 'mask_fields' in expected:
    from ui_map import OVERVIEW_CELLS
    for field in expected['mask_fields']:
     if field.get('layout')!='overview_masks' or field['field'] not in OVERVIEW_CELLS:raise ValueError('Unsupported course Masks field')
     index,label=OVERVIEW_CELLS[field['field']]
     if not frame_oracle.overview_cell_matches(state,'overview_masks',index,label,field['value']):raise ValueError('Course native Masks cell differs')
   if 'vertical_labels' in expected:
    actual=base64.b64decode(state['frame']['pixels_base64'])
    for label,y,selected in expected['vertical_labels']:
     commands=[(7,y,15 if selected else 7,label)]+([(0,y,15,'>')] if selected else [])
     if not frame_oracle._region_matches(actual,frame_oracle.render(commands),y-7,y+2,0,8+int(frame_oracle.text_width(label))):raise ValueError('Native vertical-list neighbor label/selection mismatch')
   if expected.get('mask_overview'):
    if not frame_oracle.overview_selected_cell_matches(state,'overview_masks',2,'Note','X','Note') or not frame_oracle.overview_cell_matches(state,'overview_masks',3,'Vel','X') or not frame_oracle.overview_cell_matches(state,'overview_masks',4,'Len','X'):raise ValueError('Native Masks overview changed')
   if 'reason_rows' in expected:
    if not all(frame_oracle.dashboard_row_matches(state,index,label,value) for index,(label,value) in enumerate(expected['reason_rows'],1)):raise ValueError('Reason dashboard native rows differ from exact expected labels/values')
   if 'header' in expected:
    header=expected['header'];title,scope,layout=header_parts(header['page'],**header.get('params',{}))
    if not frame_oracle.live_header_matches(state,title,scope,layout):raise ValueError('Cached image does not show pre-finish header')
   if 'footer' in expected:
    footer=expected['footer']
    if type(footer.get('present')) is not bool:raise ValueError('Invalid cached footer expectation')
    matches=frame_oracle.footer_matches(state,footer.get('text',''))
    if matches!=footer['present']:raise ValueError('Cached image footer differs from expected confirmation state')
   if 'field' in expected:
    if not frame_oracle.selected_field_matches(state,**expected['field']):raise ValueError('Cached image does not show pre-finish selected field')
   if 'parameter_readout' in expected:
    from frame_oracle import _selected_overview_index,overview_cell_matches,overview_cell_marker
    value=expected['parameter_readout'];slot=value.get('slot')
    if value.get('layout')!='overview_params' or type(slot)is not int or not 1<=slot<=64:raise ValueError('Unsupported Trig Params public readout')
    if _selected_overview_index(base64.b64decode(state['frame']['pixels_base64']),'overview_params')!=slot:raise ValueError('Native Trig Params selected slot differs')
    if not overview_cell_matches(state,'overview_params',slot,value['label'],value['value'],value['marker']):raise ValueError('Native Trig Params visible label/value/marker differs')
    if overview_cell_marker(state,'overview_params',slot)!=value['marker']:raise ValueError('Native Trig Params lock/slide marker differs')
   if 'menu_label' in expected:
    label=dict(expected['menu_label']);text=label.pop('label');geometry=SCREEN['menu_label']
    if not frame_oracle.selected_line(state,text,x=label.get('x',geometry['x']),width=label.get('width',geometry['width']),top=label.get('top',geometry['top'])):raise ValueError('Cached image does not show pre-finish menu label')
   if 'menu_value' in expected:
    if not frame_oracle.selected_value(state,expected['menu_value']['value']):raise ValueError('Cached image does not show pre-finish menu value')
   if 'menu' in expected:
    menu=expected['menu'];region=dict(SCREEN['menu_option_row']);region['top']=menu.get('top',region['top']);selected=SCREEN['selected_row']
    frames=frame_oracle.variants(lambda:frame_oracle.render([(0,selected['baseline'],selected['level'],menu['label']),(None,selected['baseline'],selected['level'],menu['value'])]))
    actual=base64.b64decode(state['frame']['pixels_base64']);indices=[(y*128+x)*4+c for y in range(region['top'],region['bottom']) for x in range(region['left'],region['right']) for c in range(3)]
    if not any(all(actual[index]==frame[index] for index in indices) for frame in frames):raise ValueError('Cached image does not show pre-finish menu row')
  finally:frame_oracle.ROOT=previous
def check_native_input_trace(recipe,events):
 native=[]
 for event in events:
  if event['kind']!='input' or event['type'] not in (1,2,3,6,7,8,9,10,11,12,13,28):continue
  kind=event['type'];args=event['args']
  if kind==6:native.append(dict(type='grid_connection',connected=bool(args[0])))
  elif kind==12:native.append(dict(type='midi_connection',port=args[0],connected=bool(args[1])))
  elif kind==13:native.append(dict(type='runtime_stall',milliseconds=args[0]))
  elif kind==28:native.append(dict(type='runtime_lua_load',iterations=args[0]))
  elif kind in (9,10,11):native.append(args[0])
  elif kind==7:native.append(dict(type='midi',port=args[0],bytes=args[1]))
  elif kind==8:native.append(dict(type='advance',nanoseconds=args[0]*1000000000+args[1]))
  elif kind==1:native.append(dict(type='key',n=args[0],state=args[1]))
  elif kind==2:native.append(dict(type='enc',n=args[0],delta=args[1]))
  else:native.append(dict(type='grid',x=args[0]+1,y=args[1]+1,state=args[2]))
 expected=[];held={}
 for value in recipe:
  action={key:value for key,value in value.items() if key!='at_monotonic_ns'}
  if action['type']=='grid':
   key=(action['x'],action['y']);expected.append(action)
   if action['state']:held[key]=action
   else:held.pop(key,None)
  elif action['type']=='grid_connection':
   if not action['connected']:
    expected.extend(dict(type='grid',x=item['x'],y=item['y'],state=0) for item in held.values());held.clear()
   expected.append(action)
  elif action['type']=='native_input_schedule':
   for item in action['events']:
    item={key:value for key,value in item.items() if key!='at_monotonic_ns'};expected.append(item)
    if item['type']=='grid':
     key=(item['x'],item['y'])
     if item['state']:held[key]=item
     else:held.pop(key,None)
  else:expected.append(action)
 if native!=expected:raise ValueError('Native full-session inputs differ from public recipe')
def audit_deferred_trace(scene):
 item=scene['evidence'];path=Path(item['path'])
 for filename,key in [('recipe.json','recipe_sha256'),('native/native-events.jsonl','native_events_sha256'),('capture-trace.json','capture_trace_sha256')]:
  if key not in item or digest(path/filename)!=item[key]:raise ValueError('Missing or changed full-session trace evidence')
 recipe=json.loads((path/'recipe.json').read_text());events=[json.loads(line) for line in (path/'native/native-events.jsonl').read_text().splitlines()]
 check_native_input_trace(recipe,events)
 trace=json.loads((path/'capture-trace.json').read_text());inputs=[value for step in scene['steps'] for value in step['inputs']]
 if trace[:len(inputs)]!=inputs:raise ValueError('Deferred scene trace does not match full public session')
 actions=[value for value in trace if value['type'] not in ('wait','advance')]
 public=[{key:value for key,value in value.items() if key!='at_monotonic_ns'} for value in recipe if value['type'] not in ('wait','advance')]
 if actions and public[-len(actions):]!=actions:raise ValueError('Capture trace differs from native verified public recipe')
 native_source_identity(path,profile=scene.get('profile','base-midi'))
 return path
def capture_application_root(path):
 for ancestor in [path]+list(path.parents):
  if len(ancestor.name)==32 and all(letter in '0123456789abcdef' for letter in ancestor.name) and (ancestor/'application').is_dir():return (ancestor/'application').resolve()
 return (path.parent/'application').resolve()
def mosaic_file_map(identity):return {item['path']:item['sha256'] for item in identity['application_identity']['files'] if item['path'].startswith('mosaic/')}
def check_participant_context(context,identity,config,clock_mode,profile,ordinal,app_root):
 if context['session_ordinal']!=ordinal or context['clock_mode']!=clock_mode or context['profile']!=profile or Path(context['app_root']).resolve()!=Path(app_root).resolve():raise ValueError('Participant declared capture context differs')
 if config['clock_mode']!=clock_mode:raise ValueError('Participant native clock differs from requested lane')
 if context['session_id']!=identity['session_id']:raise ValueError('Participant session identity differs')
 if context['runtime_identity_sha256']!=canonical_hash(identity['runtime_identity']):raise ValueError('Participant runtime identity differs')
 if context['application_identity_sha256']!=canonical_hash(mosaic_file_map(identity)):raise ValueError('Participant application identity differs')
 if context.get('finished') is not True or context.get('held_inputs')!=[] or context.get('cleanup_verified') is not True:raise ValueError('Participant cleanup context incomplete')
def check_participant_binding(scene,ordinal):
 if scene.get('session_ordinal',0)!=ordinal or any(step['output']['binding'].get('session_ordinal')!=ordinal for step in scene['steps']):raise ValueError('Frame/assertion participant namespace differs')
def audit_participants(scene,document):
 item=scene['evidence'];participants=item.get('case_participants')
 if participants is None:
  if scene.get('session_ordinal',0)!=0:raise ValueError('Child scene lacks participant evidence')
  return
 manifest=Path(item['case_participants_path'])
 if digest(manifest)!=item['case_participants_sha256'] or json.loads(manifest.read_text())!=participants:raise ValueError('Changed complete participant manifest')
 if not participants:raise ValueError('Empty participant manifest')
 actual=[]
 for ordinal,participant in enumerate(participants):
  path=Path(participant['path'])
  if path.resolve()!=manifest.parent.resolve() and manifest.parent.resolve() not in path.resolve().parents:raise ValueError('Participant lies outside original case capture')
  for filename,key in [('results.json','results_sha256'),('native/identity.json','identity_sha256'),('recipe.json','recipe_sha256'),('native/native-events.jsonl','native_events_sha256'),('capture-trace.json','capture_trace_sha256'),('session-context.json','session_context_sha256'),('native/native-config.json','native_config_sha256'),('native/cleanup.json','cleanup_sha256')]:
   if digest(path/filename)!=participant[key]:raise ValueError('Changed participant '+filename)
  context=json.loads((path/'session-context.json').read_text());identity=json.loads((path/'native/identity.json').read_text());config=json.loads((path/'native/native-config.json').read_text())
  if context!=participant['session_context']:raise ValueError('Changed participant context')
  check_participant_context(context,identity,config,document['clock_mode'],scene.get('profile','base-midi'),ordinal,capture_application_root(path))
  if context.get('experimental_install'):
   if digest(Path(context['experimental_install']))!=context['installation_sha256']:raise ValueError('Changed controlled participant installation')
  elif context.get('installation_sha256') is not None:raise ValueError('Unexpected participant installation receipt')
  results=json.loads((path/'results.json').read_text());cleanup=json.loads((path/'native/cleanup.json').read_text())
  if any(row.get('passed') is False or row.get('matched') is False for row in results):raise ValueError('Failed participant assertion')
  if not cleanup or any(row.get('returncode') not in ((0,-15) if row.get('service') in ('sclang','crow') else (0,)) for row in cleanup):raise ValueError('Participant cleanup failed')
  recipe=json.loads((path/'recipe.json').read_text());events=[json.loads(line) for line in (path/'native/native-events.jsonl').read_text().splitlines()]
  check_native_input_trace(recipe,events);native_source_identity(path,profile=scene.get('profile','base-midi'))
  actual.append(identity)
 if any(identity['runtime_identity']!=actual[0]['runtime_identity'] or mosaic_file_map(identity)!=mosaic_file_map(actual[0]) for identity in actual):raise ValueError('Parent and child native contexts differ')
 ordinal=scene.get('session_ordinal',0)
 if type(ordinal)is not int or not 0<=ordinal<len(participants):raise ValueError('Invalid selected participant')
 selected=participants[ordinal]
 if any(item.get(key)!=value for key,value in selected.items()):raise ValueError('Scene binds foreign participant evidence')
 check_participant_binding(scene,ordinal)
def refresh_pilot_editorial(ffmpeg=None):
 path=MANUAL/'generated/pilot.json';data=json.loads(path.read_text())
 current=yaml.safe_load((MANUAL/'features/masks.yaml').read_text())
 if data.get('validation',{}).get('validation_scope')=='controlled-manual-generation':
  # The controlled Masks capture re-records the pilot audio, so accept the new compressed bytes only after
  # reproducing their decoded signal from the immutable native WAV; pilot_complete stays False until CI.
  refresh_compression_receipt(data,ffmpeg)
  return dict(overlay_required=False,verified=audit_controlled_pilot(),validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',
              scope='Controlled masks publication verified with its decoded-signal audio receipt refreshed')
 if data['source_sha256']==source_hash(current):
  verified=audit_fresh_pilot(data,current,check_receipt=False)
  refresh_compression_receipt(data,ffmpeg)
  return dict(overlay_required=False,verified=verified,scope='Current authoring and immutable native publication match; publication bytes unchanged')
 # This immutable committed publication supplies every original output and binding.
 revisions=subprocess.check_output(['git','log','--format=%H','--','manual/generated/pilot.json'],cwd=ROOT,text=True).splitlines()
 baseline=None;baseline_revision=None
 for revision in revisions:
  candidate=json.loads(subprocess.check_output(['git','show',revision+':manual/generated/pilot.json'],cwd=ROOT,text=True))
  if candidate['source_sha256']==data['source_sha256'] and candidate['validation']==data['validation']:
   baseline=candidate;baseline_revision=revision;break
 if baseline is None:raise ValueError('Cannot identify immutable pilot publication')
 current=yaml.safe_load((MANUAL/'features/masks.yaml').read_text())
 authoring_baseline=None
 revisions=subprocess.check_output(['git','log','--format=%H','--','manual/features/masks.yaml'],cwd=ROOT,text=True).splitlines()
 for revision in revisions:
  candidate=yaml.safe_load(subprocess.check_output(['git','show',revision+':manual/features/masks.yaml'],cwd=ROOT,text=True))
  if source_hash(candidate)==baseline['source_sha256']:authoring_baseline=candidate;break
 if authoring_baseline is None:raise ValueError('Cannot identify immutable pilot authoring')
 check_editorial_overlay(authoring_baseline,current)
 authored_scenes={scene['id']:scene for scene in current['scenes']}
 updated=copy.deepcopy(baseline)
 for scene in updated['scenes']:
  authored=authored_scenes[scene['id']];scene['title']=authored['title']
  captions={step['id']:step['caption'] for step in authored['steps']}
  for step in scene['steps']:step['caption']=captions[step['id']]
 for field in ('title','description'):
  if field in current['audio']:updated['audio'][field]=current['audio'][field]
 updated['editorial_overlay']=dict(baseline_revision=baseline_revision,baseline_publication_sha256=canonical_hash(baseline),current_authoring_sha256=source_hash(current),scope='scene.title, step.caption and audio.title/description only')
 # Existing publication may differ solely by the same approved fields.
 def strip(value):
  value=copy.deepcopy(value);value.pop('editorial_overlay',None)
  for field in ('title','description'):value['audio'].pop(field,None)
  for scene in value['scenes']:
   scene.pop('title',None)
   for step in scene['steps']:step.pop('caption',None)
  return value
 if strip(data)!=strip(baseline):raise ValueError('Pilot publication changed beyond editorial overlay')
 temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(updated,separators=(',',':'))+'\n');temp.replace(path)
 return updated['editorial_overlay']
def audit_controlled_pilot():
 """Verify complete controlled Masks visuals and same-run audio provenance."""
 data=json.loads((MANUAL/'generated/pilot.json').read_text())
 authored=yaml.safe_load((MANUAL/'features/masks.yaml').read_text())
 report=data.get('validation',{})
 if report.get('validation_scope')!='controlled-manual-generation' or report.get('realtime_qualification')!='pending-ci' or report.get('clock_mode')!='controlled-experimental' or report.get('complete_regression_run') is not False or report.get('scene_build_complete') is not True or report.get('pilot_complete') is not False:
  raise ValueError('Controlled masks publication scope changed')
 if data.get('source_sha256')!=source_hash(authored):raise ValueError('Controlled masks publication is stale')
 preserved=report.get('preserved_audio');audio=data.get('audio',{})
 if 'preserved_audio' in report:
  if not isinstance(preserved,dict) or preserved.get('source_sha256')!=data['source_sha256'] or Path(preserved.get('publication_path','')).resolve()!=(MANUAL/'generated/pilot.json').resolve():raise ValueError('Controlled masks lacks exact preserved audio source receipt')
  expected_files={name:digest(MANUAL/name) for name in audio.get('files',[]) if (MANUAL/name).is_file()}
  if not expected_files or expected_files!=preserved.get('file_sha256'):raise ValueError('Controlled masks preserved audio files changed')
 else:
  _audit_fresh_controlled_audio_run(data,report,audio)
 scenes=audit_generic(data,('features/masks.yaml',authored))
 audio_frames=audit_pilot_audio(data,authored,check_receipt=True)
 return dict(frames=scenes['frames']+audio_frames,baseline_cases=scenes['baseline_cases'],current_source_sha256=data['source_sha256'],validation_scope='controlled-manual-generation',realtime_qualification='pending-ci')

def _audit_fresh_controlled_audio_run(data,report,audio):
 """Require fresh visuals, cases and audio to belong to one immutable capture run."""
 import re
 run_id=report.get('run_id')
 if not isinstance(run_id,str) or re.fullmatch(r'[0-9a-f]{32}',run_id) is None:
  raise ValueError('Fresh controlled masks audio lacks an exact capture run id')
 source_sha=data.get('source_sha256')
 if report.get('source_sha256')!=source_sha:
  raise ValueError('Fresh controlled masks audio source identity changed')
 run_root=(ROOT.parent/'mosaic-manual-runs'/run_id).resolve()
 def require_inside(label,path_value):
  if not isinstance(path_value,str) or not path_value:
   raise ValueError('Fresh controlled masks lacks '+label+' evidence path')
  path=Path(path_value).resolve()
  try:path.relative_to(run_root)
  except ValueError:raise ValueError('Fresh controlled masks '+label+' is outside its capture run')
  if not path.exists():raise ValueError('Fresh controlled masks '+label+' evidence is missing')
 for scene in data.get('scenes',[]):
  evidence=scene.get('evidence',{})
  require_inside('scene',evidence.get('path'))
 cases=report.get('behaviour_cases')
 if not isinstance(cases,list) or not cases:
  raise ValueError('Fresh controlled masks lacks same-run behaviour case evidence')
 for case in cases:
  if not isinstance(case,dict) or case.get('passed') is not True or not isinstance(case.get('case'),str) or not case['case']:
   raise ValueError('Fresh controlled masks behaviour case receipt is not successful')
  require_inside('behaviour case',case.get('path') if isinstance(case,dict) else None)
 evidence=audio.get('evidence',{})
 if not isinstance(evidence,dict) or Path(evidence.get('path','')).resolve()!=(run_root/'audio').resolve():
  raise ValueError('Fresh controlled masks audio is not from the exact visual capture run')
 if not (run_root/'audio').is_dir():
  raise ValueError('Fresh controlled masks audio evidence is missing')

def audit_pilot():
 data=json.loads((MANUAL/'generated/pilot.json').read_text())
 current=yaml.safe_load((MANUAL/'features/masks.yaml').read_text())
 if data['source_sha256']==source_hash(current):return audit_fresh_pilot(data,current)
 revisions=subprocess.check_output(['git','log','--format=%H','--','manual/features/masks.yaml'],cwd=ROOT,text=True).splitlines()
 baseline=None;baseline_revision=None
 for revision in revisions:
  candidate=yaml.safe_load(subprocess.check_output(['git','show',revision+':manual/features/masks.yaml'],cwd=ROOT,text=True))
  if source_hash(candidate)==data['source_sha256']:baseline=candidate;baseline_revision=revision;break
 if baseline is None:raise ValueError('Pilot baseline authoring identity mismatch')
 current=yaml.safe_load((MANUAL/'features/masks.yaml').read_text())
 overlay=check_editorial_overlay(baseline,current);overlay['baseline_revision']=baseline_revision
 receipt=data.get('editorial_overlay')
 if receipt:
  original=json.loads(subprocess.check_output(['git','show',receipt['baseline_revision']+':manual/generated/pilot.json'],cwd=ROOT,text=True))
  if canonical_hash(original)!=receipt['baseline_publication_sha256'] or source_hash(current)!=receipt['current_authoring_sha256']:raise ValueError('Stale pilot editorial overlay receipt')
  wanted={scene['id']:scene for scene in current['scenes']}
  for scene in data['scenes']:
   if scene['title']!=wanted[scene['id']]['title']:raise ValueError('Stale scene title overlay')
   captions={step['id']:step['caption'] for step in wanted[scene['id']]['steps']}
   if any(step['caption']!=captions[step['id']] for step in scene['steps']):raise ValueError('Stale step caption overlay')
 if data['validation']['complete_regression_run'] is not False or not data['validation']['pilot_complete']:raise ValueError('Incorrect pilot evidence scope')
 captured=[];frames=0
 for scene in data['scenes']:
  results,observations=evidence(scene)
  native_source_identity(Path(scene['evidence']['path']))
  original={k:v for k,v in scene.items() if k!='evidence'}
  original['steps']=[{k:v for k,v in step.items() if k!='output'} for step in scene['steps']]
  captured.append(original)
  for step in scene['steps']:
   semantics=[row for row in results if row.get('kind')=='manual-semantic' and row.get('step')==step['id'] and row.get('passed')]
   if len(semantics)!=1 or semantics[0]['expected']!=step['expect']:raise ValueError('Missing exact pilot semantic assertion')
   check_frame(step['output'],scene['behaviour_case'],results,observations);frames+=1
 if performance_contract(dict(scenes=captured))!=performance_contract(dict(scenes=baseline['scenes'])):raise ValueError('Pilot scenes differ from immutable authoring')
 frames+=audit_pilot_audio(data,baseline)
 return dict(frames=frames,editorial_overlay=overlay)
def audit_pilot_audio(data,authored,check_receipt=True):
 frames=0
 audio=data['audio']
 if performance_contract(dict(audio={k:audio[k] for k in authored['audio']}))!=performance_contract(dict(audio=authored['audio'])):raise ValueError('Changed pilot audio performance contract')
 path=Path(audio['evidence']['path']);results=json.loads((path/'results.json').read_text());observations=json.loads((path/'observations.json').read_text())
 cleanup=json.loads((path/'native/cleanup.json').read_text())
 if not cleanup or any(row.get('returncode') is None for row in cleanup):raise ValueError('Missing pilot audio cleanup')
 if any(row.get('passed') is False or row.get('matched') is False for row in results):raise ValueError('Failed pilot audio acceptance')
 native_source_identity(path,voice_roots=True)
 if not any(row.get('kind')=='manual-audio-PCM' and row.get('passed') for row in results):raise ValueError('Missing pilot PCM acceptance')
 if len([row for row in results if row.get('kind')=='manual-audio-track' and row.get('passed')])!=len(audio['tracks']):raise ValueError('Missing pilot voice assertions')
 if digest(path/'native/audio-captures'/audio['evidence']['job']['job_id']/'output.wav')!=audio['evidence']['wav_sha256']:raise ValueError('Changed pilot native WAV')
 for frame in audio['timeline']:check_frame(frame['output'],'manual-audio',results,observations);frames+=1
 if check_receipt:
  hashes=json.loads((MANUAL/'evidence/audio-files.json').read_text())
  for filename in audio['files']:
   if digest(MANUAL/filename)!=hashes[filename]:raise ValueError('Changed pilot compressed audio')
 return frames
def check_doctor_scope(data):
 if data.get('publication_kind')!='doctor-native-audio' or data.get('passed') is not True or data.get('diagnostic_only') or data.get('failure') or data.get('cleanup_failure'):raise ValueError('Doctor acceptance failed or diagnostic only')
 if data.get('clock_mode')!='real-time' or data.get('controlled_time',{}).get('applicable') is not False or not data['controlled_time'].get('reason') or data.get('complete_regression_run') is not False or data.get('hardware_timing_equivalent') is not False:raise ValueError('Doctor acceptance scope changed')
def check_doctor_grids(steps):
 by_id={step['id']:step for step in steps};setup=by_id['setup']['output']['grid'][48:112]
 if any(level in (12,15) for level in setup):raise ValueError('Doctor setup native pattern is not empty')
 preview=by_id['preview'];grid=preview['output']['grid'][48:112];hits=[index+1 for index,level in enumerate(grid) if level in preview['expect']['levels']]
 if len(hits)<preview['expect']['minimum_trigs'] or hits!=preview['expect']['grid_steps']:raise ValueError('Doctor preview native grid differs from detected attacks')
 painted=by_id['paint'];grid=painted['output']['grid'][48:112];committed=[index+1 for index,level in enumerate(grid) if level==painted['expect']['level']]
 if committed!=hits or committed!=painted['expect']['grid_steps'] or any(grid[index-1]!=15 for index in hits):raise ValueError('Doctor committed native grid differs from preview')
def check_doctor_midi(expected,events,state):
 start=expected.get('midi_start_index');end=expected.get('midi_end_index')
 if type(start)is not int or type(end)is not int or not 0<=start<end:raise ValueError('Doctor playback lacks explicit native packet boundaries')
 packets=[item for item in events if item.get('kind')==3 and start<item.get('index',0)<=end]
 notes=[item for item in packets if len(item.get('bytes',[]))>=3 and 144<=item['bytes'][0]<=159 and item['bytes'][2]>0]
 if len(notes)<expected['midi_minimum_attacks'] or any(item['port']!=expected['port'] for item in notes):raise ValueError('Doctor painted native playback attacks missing or on wrong port')
 public_keys={'bytes','decoded','device_id','index','monotonic_ns','port','port_name'}
 if [{key:value for key,value in item.items() if key in public_keys} for item in notes]!=expected['notes']:raise ValueError('Doctor published notes differ from exact native playback packets')
 if state['midi_capture']['outstanding']!=expected['outstanding_notes'] or expected['outstanding_notes']!=[]:raise ValueError('Doctor playback has outstanding native notes')
def doctor_authoring_path(value):
 path=Path(value);resolved=(path if path.is_absolute() else ROOT/path).resolve()
 if resolved not in {(MANUAL/'doctor-scene.yaml').resolve(),(MANUAL/'doctor-auto-probe.yaml').resolve()}:raise ValueError('Source is not an owned Doctor authoring file')
 return resolved
def check_doctor_identity(application,native):
 if application!=native.get('application_identity'):raise ValueError('Changed Doctor native application source identity')
def check_doctor_collection(document,reports):
 check_doctor_scope(document)
 if document.get('schema_version')!=1 or len(reports)!=2 or {doctor_authoring_path(report['source']['yaml_path']) for report in reports}!={(MANUAL/'doctor-scene.yaml').resolve(),(MANUAL/'doctor-auto-probe.yaml').resolve()}:raise ValueError('Doctor collection requires both Manual and Auto native reports')
 scenes=[scene for report in reports for scene in report['scenes']]
 if document['scenes']!=scenes or len({scene['id'] for scene in scenes})!=len(scenes):raise ValueError('Doctor collection differs from exact native scenes or has duplicate identities')
 maps=[{item['path']:item['sha256'] for item in report['source_identity']['files'] if item['path'].startswith('mosaic/')} for report in reports]
 if not maps[0] or maps[0]!=maps[1]:raise ValueError('Doctor modes have different Mosaic source identities')
def audit_doctor_collection(document):
 check_doctor_scope(document);receipts=document.get('evidence',{}).get('runs',[])
 if len(receipts)!=2:raise ValueError('Doctor collection requires both Manual and Auto native reports')
 reports=[];audits=[];identities=[];paths=[]
 for receipt in receipts:
  path=Path(receipt['report'])
  if not path.is_absolute() or path.name!='report.json' or digest(path)!=receipt['report_sha256'] or path.resolve() in paths:raise ValueError('Changed or duplicated Doctor collection immutable report')
  paths.append(path.resolve());report=json.loads(path.read_text())
  if report.get('evidence',{}).get('runs'):raise ValueError('Doctor collection cannot use another collection as native evidence')
  audits.append(audit_doctor(path));reports.append(report);identities.append(json.loads((path.parent/'native/identity.json').read_text()))
 check_doctor_collection(document,reports)
 if identities[0]['runtime_identity']!=identities[1]['runtime_identity']:raise ValueError('Doctor modes have different native runtime identity')
 return dict(passed=True,frames=sum(item['frames'] for item in audits),clock_mode='real-time',controlled_time_applicable=False,complete_regression_run=False,hardware_timing_verified=False,runs=audits)
def audit_doctor(value):
 data=json.loads(Path(value).read_text()) if isinstance(value,(str,Path)) else copy.deepcopy(value)
 if data.get('evidence',{}).get('runs') is not None:return audit_doctor_collection(data)
 check_doctor_scope(data)
 receipt=data.get('evidence',{});report_path=Path(receipt['report']) if receipt.get('report') else (Path(value) if isinstance(value,(str,Path)) else None)
 if report_path is None or report_path.name!='report.json':raise ValueError('Doctor lacks immutable native report path')
 run=report_path.parent
 if (run/'diagnostic-only.json').exists():raise ValueError('Doctor acceptance is diagnostic only')
 original=json.loads(report_path.read_text());published={key:item for key,item in data.items() if key!='evidence'}
 if published!=original:raise ValueError('Doctor publication differs from immutable native report')
 if receipt and receipt.get('report_sha256')!=digest(report_path):raise ValueError('Changed Doctor immutable report hash')
 source=data['source'];authored_path=doctor_authoring_path(source['yaml_path'])
 if digest(authored_path)!=source['yaml_sha256'] or digest(run/'doctor-scene.yaml')!=source['yaml_sha256']:raise ValueError('Stale Doctor authoritative YAML')
 if digest(ROOT/'tools/manual_doctor_capture.py')!=source['recipe_sha256'] or digest(run/'capture-recipe.py')!=source['recipe_sha256']:raise ValueError('Stale Doctor public-input fixture')
 authored=yaml.safe_load(authored_path.read_text());scenes=data['scenes']
 if len(scenes)!=1 or scenes[0]['id']!=authored['scene_id'] or scenes[0]['behaviour_case']!=authored['case'] or scenes[0]['title']!=authored['title']:raise ValueError('Changed Doctor scene identity')
 scene=scenes[0];steps=scene['steps']
 if [step['id'] for step in steps]!=[step['id'] for step in authored['steps']]:raise ValueError('Incomplete Doctor native checkpoints')
 identity=json.loads((run/'native/identity.json').read_text())
 check_doctor_identity(data['source_identity'],identity)
 native_source_identity(run)
 config=json.loads((run/'native/native-config.json').read_text())
 if config['clock_mode']!='real-time':raise ValueError('Doctor native lane is not real audio time')
 results=json.loads((run/'results.json').read_text());observations=json.loads((run/'observations.json').read_text());recipe=json.loads((run/'recipe.json').read_text());events=[json.loads(line) for line in (run/'native/native-events.jsonl').read_text().splitlines()]
 if any(row.get('passed') is False or row.get('matched') is False for row in results):raise ValueError('Failed Doctor native assertion')
 cleanup=json.loads((run/'native/cleanup.json').read_text())
 if not cleanup or any(row.get('returncode') not in ((0,-15) if row.get('service') in ('sclang','crow') else (0,)) for row in cleanup):raise ValueError('Doctor native cleanup failed')
 check_native_input_trace(recipe,events)
 inputs=[item for step in steps for item in step['inputs']]
 if recipe[:len(inputs)]!=inputs:raise ValueError('Doctor delivered step inputs differ from full native recipe')
 from ui_map import RHYTHM_DOCTOR_SCREEN
 for step,authoring in zip(steps,authored['steps']):
  if step['caption']!=authoring['caption'] or step['citation']!=authoring['citation'] or step['authoring_operations']!=authoring['inputs']:raise ValueError('Changed Doctor authoring/input operations')
  expected={key:item for key,item in step['expect'].items() if key not in ('grid_steps','notes','midi_start_index','midi_end_index')}
  if expected!=authoring['expect']:raise ValueError('Changed Doctor literal expectations')
  matches=[row for row in results if row.get('kind')=='manual-doctor-semantic' and row.get('step')==step['id']]
  if len(matches)!=1 or matches[0].get('expected')!=step['expect'] or matches[0].get('citation')!=step['citation'] or matches[0].get('passed') is not True:raise ValueError('Missing exact Doctor semantic assertion')
  output=step['output'];binding=output['binding']
  if binding['semantic_assertions']<=results.index(matches[0]) or results.index(binding)<=results.index(matches[0]):raise ValueError('Doctor image predates semantic acceptance')
  check_frame(output,scene['behaviour_case'],results,observations)
  state=next(item['state'] for item in observations if item['state']['frame']['sha256']==binding['sha256'] and item['state']['grid']==output['grid'])
  ui={}
  if 'route' in step['expect']:
   title,layout=RHYTHM_DOCTOR_SCREEN['screens'][step['expect']['route']];ui['literal_header']=[title,'CH01',layout]
  if 'tooltip' in step['expect']:ui['doctor_tooltip']=step['expect']['tooltip']
  if ui:verify_cached_ui(state,ui,run)
  if 'midi_minimum_attacks' in step['expect']:check_doctor_midi(step['expect'],events,state)
 check_doctor_grids(steps)
 from manual_doctor_audit import audit_publication as audit_signal
 signal=audit_signal(report_path)
 return dict(passed=True,frames=len(steps),clock_mode='real-time',controlled_time_applicable=False,complete_regression_run=False,hardware_timing_verified=False,report_sha256=digest(report_path),results_sha256=digest(run/'results.json'),recipe_sha256=digest(run/'recipe.json'),native_events_sha256=digest(run/'native/native-events.jsonl'),audio=signal)
def scene_format(document):
 if document.get('publication_kind') in ('audio-route-projection','doctor-native-audio'):
  if not isinstance(document.get('scenes'),list) or not document['scenes']:raise ValueError('Incomplete specialized native publication')
  return document['publication_kind']
 if 'scenes' not in document:return None
 if 'validation' in document and 'feature' in document:return 'generic'
 if 'source' in document and 'clock_mode' in document:return 'reference'
 raise ValueError('Unrecognised scene publication')
def check_generic_scene_contract(scene,source):
 captured={key:value for key,value in scene.items() if key!='evidence'}
 captured['steps']=[{key:value for key,value in step.items() if key!='output'} for step in scene['steps']]
 if captured!=source:raise ValueError('Changed generic scene contract')
def check_generic_scope(report,scenes):
 if not report.get('passed') or not report.get('scene_build_complete') or report.get('complete_regression_run') is not False:raise ValueError('Incomplete generic capture scope')
 cases=report.get('behaviour_cases',[])
 if {row['case'] for row in cases}!={scene['behaviour_case'] for scene in scenes} or any(not row.get('passed') for row in cases):raise ValueError('Missing full baseline cases')
def check_module_pin(name,pins,origin,revision):
 if name not in pins or origin!=pins[name]['url'] or revision!=pins[name]['commit']:raise ValueError('External module pin differs')
def modulation_source_roots(path,app):
 root=Path(app['code_root']).resolve();pins=json.loads((ROOT/'tests/behaviour/mods.lock.json').read_text())['mods']
 config=json.loads((path/'native/native-config.json').read_text())
 if set(config['enabled_mods'])!=set(pins):raise ValueError('Native modulation modules differ from profile pins')
 external={name:(root/name).resolve() for name in pins if root not in (root/name).resolve().parents}
 if not external:raise ValueError('Missing pinned modulation clone context')
 parents={clone.parent for clone in external.values()}
 if len(parents)!=1:raise ValueError('Modulation clones do not share declared source root')
 parent=next(iter(parents));clones={}
 for name in pins:
  clone=parent/name;origin=subprocess.check_output(['git','remote','get-url','origin'],cwd=clone,text=True).strip();revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=clone,text=True).strip()
  check_module_pin(name,pins,origin,revision)
  if subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=clone,text=True).strip():raise ValueError('Pinned modulation clone is dirty')
  clones[name]=clone
 patches=json.loads((ROOT/'tests/behaviour/mod-patches/manifest.json').read_text())
 for item in app['files']:
  relative=Path(item['path']);name=relative.parts[0]
  if name not in pins:continue
  local=Path(*relative.parts[1:]);patch=patches.get(name);source=clones[name]/local
  if root in (root/name).resolve().parents and patch and local.as_posix()==patch['file']:
   if digest(ROOT/'tests/behaviour/mod-patches'/patch['patch'])!=patch['sha256'] or digest(source)!=patch['before_sha256'] or item['sha256']!=patch['after_sha256']:raise ValueError('Native modulation patch differs from manifest')
  elif not source.is_file() or digest(source)!=item['sha256']:raise ValueError('Native modulation source differs from pinned clone')
 return list(external.values())
def player_source_roots(path,app):
  import ast
  root=Path(app['code_root']).resolve();pins=json.loads((MANUAL/'voices.lock.json').read_text())
  driver=ast.parse((ROOT/'tests/behaviour/driver.py').read_text())
  profile_node=next((node for node in driver.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='MANUAL_PLAYER_UI_PROFILE' for target in node.targets)),None)
  if profile_node is None:raise ValueError('Manual player profile pins are missing from the behaviour driver')
  profile=ast.literal_eval(profile_node.value);profile_mods=profile.get('mods')
  if profile.get('controlled_ui_only') is not True or not isinstance(profile_mods,dict) or not profile_mods:raise ValueError('Manual player profile declaration is invalid')
  for name,pin in profile_mods.items():
   if name not in pins or pins[name].get('url')!=pin.get('url') or pins[name].get('commit')!=pin.get('commit'):raise ValueError('Manual player profile differs from manual/voices.lock.json: '+name)
  config=json.loads((path/'native/native-config.json').read_text());mods=config.get('enabled_mods')
  if not isinstance(mods,list) or len(mods)!=len(set(mods)) or set(mods)!=set(profile_mods):raise ValueError('Manual player enabled-mod inventory differs from the exact profile declaration')
  files={Path(item['path']).parts[0] for item in app['files'] if Path(item['path']).parts[0]!='mosaic'}
  if files!=set(mods):raise ValueError('Manual player source inventory differs from enabled mods')
  clones={}
  for name in mods:
   pin=pins.get(name)
   if not pin:raise ValueError('Unpinned native manual player: '+name)
   clone=(root/name).resolve()
   origin=subprocess.check_output(['git','remote','get-url','origin'],cwd=clone,text=True).strip()
   revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=clone,text=True).strip()
   if origin!=pin['url'] or revision!=pin['commit']:raise ValueError('Native manual player origin or revision changed: '+name)
   if subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=clone,text=True).strip():raise ValueError('Native manual player source is dirty: '+name)
   ignored=subprocess.check_output(['git','ls-files','--others','--ignored','--exclude-standard','--','*.lua','*.sc','*.so','*.scx'],cwd=clone,text=True)
   if ignored:raise ValueError('Ignored runtime source outside native manual player pin: '+name)
   for item in app['files']:
    relative=Path(item['path'])
    if relative.parts[0]==name:
     source=clone.joinpath(*relative.parts[1:])
     if not source.is_file() or digest(source)!=item['sha256']:raise ValueError('Native manual player file differs from pinned clone: '+relative.as_posix())
   clones[name]=clone
  return list(clones.values())
def native_source_identity(path,voice_roots=False,profile='base-midi',application_root=None):
 identity=json.loads((path/'native/identity.json').read_text())
 app=identity['application_identity'];root=Path(app['code_root']).resolve();allowed=[root,capture_application_root(path)]
 if application_root is not None:
  application_root=Path(application_root).resolve(strict=True)
  if not application_root.is_dir():raise ValueError('Invalid frozen application root')
  allowed.append(application_root)
 if profile=='midi-modulation':allowed.extend(modulation_source_roots(path,app))
 if profile=='manual-player-ui':allowed.extend(player_source_roots(path,app))
 if voice_roots:
  pins=json.loads((MANUAL/'voices.lock.json').read_text())
  for player in {Path(item['path']).parts[0] for item in app['files']} - {'mosaic'}:
   if player not in pins:raise ValueError('Unpinned native audio player')
   clone=(root/player).resolve()
   revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=clone,text=True).strip()
   if revision!=pins[player]['commit']:raise ValueError('Native audio player revision changed')
   allowed.append(clone)
 if not app.get('files') or not app.get('digest'):raise ValueError('Missing native application identity')
 metadata_transition=None
 for item in app['files']:
  file=(root/item['path']).resolve()
  relative=Path(item['path'])
  if relative.is_absolute() or '..' in relative.parts or not any(parent in file.parents for parent in allowed):raise ValueError('Unsafe native application path')
  if application_root is not None and relative.parts[0]=='mosaic':
   expected=application_root.joinpath(*relative.parts[1:]).resolve(strict=True)
   if file!=expected:raise ValueError('Unsafe native application path')
  if digest(file)!=item['sha256'] or file.stat().st_size!=item['size']:raise ValueError('Changed native application source')
  if relative.parts[0]=='mosaic':
   current=ROOT.joinpath(*relative.parts[1:])
   if not current.is_file() or digest(current)!=item['sha256']:
    from manual_metadata_transition import METADATA,validate_identity_from_context
    if Path(*relative.parts[1:]).as_posix() not in METADATA:raise ValueError('Stale native Mosaic source: '+relative.as_posix())
    metadata_transition=validate_identity_from_context(ROOT,path/'native/identity.json')
    if metadata_transition is None:raise ValueError('Stale native Mosaic source: '+relative.as_posix())
 result=dict(identity_sha256=digest(path/'native/identity.json'),application_digest=app['digest'])
 if metadata_transition is not None:result['reviewed_metadata_transition']=metadata_transition
 return result
def generic_authoring(document):
 config=yaml.safe_load((MANUAL/'book.yaml').read_text());matches=[]
 for name in dict.fromkeys(config.get('sources',[])+config.get('scene_sources',[])):
  candidate=yaml.safe_load((MANUAL/name).read_text())
  if candidate.get('schema_version')==2 and candidate.get('feature',{}).get('id')==document['feature']['id'] and 'scenes' in candidate:matches.append((name,candidate))
 if len(matches)!=1:raise ValueError('Generic publication requires one indexed version-2 source')
 name,authored=matches[0]
 if source_hash(authored)!=document['source_sha256'] or authored['feature']!=document['feature']:raise ValueError('Stale generic authoring')
 return name,authored
def audit_generic(document,source=None):
 name,authored=source if source is not None else generic_authoring(document);report=document['validation']
 if source_hash(authored)!=document['source_sha256'] or authored['feature']!=document['feature']:raise ValueError('Stale generic authoring')
 check_generic_scope(report,authored['scenes'])
 if report['source_sha256']!=document['source_sha256']:raise ValueError('Generic report source identity mismatch')
 if len(document['scenes'])!=len(authored['scenes']):raise ValueError('Missing generic captured scenes')
 run=Path(document['scenes'][0]['evidence']['path']).parent
 if run.name!=report['run_id'] or json.loads((run/'report.json').read_text())!=report:raise ValueError('Changed generic immutable report')
 if json.loads((run/'pilot.json').read_text())!=document:raise ValueError('Changed generic immutable publication')
 if digest(ROOT/'tools/manual_capture.py')!=report['capture_tool_sha256'] or digest(ROOT/'tests/behaviour/driver.py')!=report['driver_sha256']:raise ValueError('Stale generic capture tool/driver identity')
 if report.get('voice_lock_sha256')!=digest(MANUAL/'voices.lock.json'):raise ValueError('Stale generic player pin identity')
 baseline=[]
 for case in report['behaviour_cases']:
  path=Path(case['path'])
  if path.parent!=run or digest(path/'results.json')!=case['results_sha256']:raise ValueError('Changed baseline case results')
  results=json.loads((path/'results.json').read_text())
  if not results or any(row.get('passed') is False or row.get('matched') is False for row in results):raise ValueError('Failed baseline case acceptance')
  cleanup=json.loads((path/'native/cleanup.json').read_text())
  if not cleanup or any(row.get('returncode') is None for row in cleanup):raise ValueError('Missing baseline cleanup')
  baseline.append(dict(case=case['case'],**native_source_identity(path)))
 frames=0
 for scene,source in zip(document['scenes'],authored['scenes']):
  check_generic_scene_contract(scene,source)
  results,observations=evidence(scene)
  identity=native_source_identity(Path(scene['evidence']['path']))
  if identity['application_digest']!={row['application_digest'] for row in baseline if row['case']==scene['behaviour_case']}.pop():raise ValueError('Baseline and scene application identities differ')
  for step in scene['steps']:
   semantics=[row for row in results if row.get('kind')=='manual-semantic' and row.get('step')==step['id'] and row.get('passed')]
   if len(semantics)!=1 or semantics[0]['expected']!=step['expect'] or semantics[0]['citation']!=step['citation']:raise ValueError('Missing exact generic semantic assertion/citation')
   binding=step['output']['binding']
   if binding['semantic_assertions']<results.index(semantics[0])+1:raise ValueError('Frame predates semantic acceptance')
   check_frame(step['output'],scene['behaviour_case'],results,observations);frames+=1
 return dict(source=name,scenes=len(document['scenes']),frames=frames,clock_mode=report['clock_mode'],baseline_cases=baseline)
def audit_fresh_pilot(document,authored,check_receipt=True):
 if source_hash(authored)!=document['source_sha256']:raise ValueError('Fresh pilot source identity mismatch')
 if not document['validation'].get('pilot_complete'):raise ValueError('Fresh pilot incomplete')
 report=audit_generic(document,('features/masks.yaml',authored))
 audio_frames=audit_pilot_audio(document,authored,check_receipt=check_receipt)
 return dict(frames=report['frames']+audio_frames,baseline_cases=report['baseline_cases'],current_source_sha256=document['source_sha256'],overlay_required=False)
def refresh_compression_receipt(document,ffmpeg=None):
 # Accept newly encoded bytes only after reproducing their decoded signal from
 # the immutable native WAV using the capture tool's exact encoding contract.
 audio=document['audio'];out=Path(audio['evidence']['path'])
 wav=out/'native/audio-captures'/audio['evidence']['job']['job_id']/'output.wav'
 if digest(wav)!=audio['evidence']['wav_sha256']:raise ValueError('Changed native PCM before compression receipt')
 ffmpeg=ffmpeg or shutil.which('ffmpeg') or '/home/andy/mosaic-manual-tools/imageio_ffmpeg/binaries/ffmpeg-linux64-v4.2.2'
 seconds=audio['bars']*4*60/audio['bpm'];hashes={}
 with tempfile.TemporaryDirectory(prefix='manual-compression-audit-') as directory:
  for filename in audio['files']:
   published=MANUAL/filename;suffix=published.suffix
   codec={'.ogg':'libopus','.mp3':'libmp3lame'}.get(suffix)
   if codec is None:raise ValueError('Unknown pilot compression format')
   reproduced=Path(directory)/published.name
   subprocess.run([ffmpeg,'-y','-loglevel','error','-i',str(wav),'-af','afade=t=in:d=0.015,afade=t=out:st='+str(seconds+1.8)+':d=0.2','-c:a',codec,'-b:a','128k',str(reproduced)],check=True)
   def decoded_hash(file):
    pcm=subprocess.check_output([ffmpeg,'-loglevel','error','-i',str(file),'-f','f32le','-'])
    if not pcm:raise ValueError('Empty decoded pilot audio')
    return hashlib.sha256(pcm).hexdigest()
   if decoded_hash(published)!=decoded_hash(reproduced):raise ValueError('Compressed audio differs from native encoding contract')
   hashes[filename]=digest(published)
 receipt=MANUAL/'evidence/audio-files.json';prior=json.loads(receipt.read_text()) if receipt.exists() else {}
 if prior==hashes:return hashes
 history=MANUAL/'evidence/compression-history';history.mkdir(exist_ok=True)
 if prior:(history/(canonical_hash(prior)+'.json')).write_text(json.dumps(prior,indent=2)+'\n')
 proof=dict(native_wav_sha256=audio['evidence']['wav_sha256'],source_sha256=document['source_sha256'],files=hashes,decoded_signal_verified=True,complete_regression_run=False)
 (history/(canonical_hash(proof)+'.json')).write_text(json.dumps(proof,indent=2)+'\n')
 temp=receipt.with_suffix('.json.tmp');temp.write_text(json.dumps(hashes,indent=2)+'\n');temp.replace(receipt)
 return hashes
def text_digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()
def scene_contract(scene):
 value=copy.deepcopy(scene);value.pop('title',None);value.pop('data_path',None);value.pop('starting_state',None)
 for step in value.get('steps',[]):step.pop('caption',None);step.pop('caption_overlay',None)
 return value
def scene_contract_digest(scene):return text_digest(json.dumps(scene_contract(scene),sort_keys=True,separators=(',',':'),ensure_ascii=False))
def check_compiled_scene_contract(raw,compiled):
 if scene_contract(raw)!=scene_contract(compiled):raise ValueError('Compiled caption changed native contract')
 for original,revised in zip(raw.get('steps',[]),compiled.get('steps',[])):
  receipt=revised.get('caption_overlay')
  if original.get('caption')==revised.get('caption'):
   if receipt is not None:raise ValueError('Unneeded historic caption receipt on fresh wording')
   continue
  wanted=dict(original_caption_sha256=text_digest(original['caption']),caption_sha256=text_digest(revised['caption']),contract_sha256=scene_contract_digest(raw))
  if receipt!=wanted:raise ValueError('Missing or changed compiled caption receipt')
# Reviewed audio lessons: each needs independent acceptance before it may publish.
# contract_sha256 is canonical_hash(authored midi_contract); pcm_solo_voice limits the
# PCM proof to that single-voice solo session (None: every session of the lesson).
CANONICAL_AUDIO_LESSONS={
 'ghost-note-comparison':dict(setup=None,pcm_kind='ghost-note-interiors',pcm_solo_voice=None,
  contract_sha256='aec0ea3979f584d5dfb9764b707858808c9861072b3a373f0e3fa3a37d49f34c'),
 'scale-slot-comparison':dict(setup=None,pcm_kind='relative-scale-pitch-interiors',pcm_solo_voice='Polyperc 1',
  contract_sha256='4561961c69a54d7acbfdf9ad68acc46379d062e330599bdc44126e8d2bcaedde'),
 # 1.4.0 comparisons: MIDI-contract lessons only (no PCM proof). Their contracts are derived by hand from the
 # README (tools/test_manual_audio_lessons.py holds the independent models) and proved in the controlled MIDI lane.
 'swing-comparison':dict(setup='swing-comparison',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='526b650233ea32ecdc4ecf8384eeeaab8ed417ff86c32cb6f974da5f01a14bdf'),
 'note-merge-modes':dict(setup='note-merge-modes',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='bc9c51c9651332d4a59c639f9ab64326b75747f6caeb3ab3a4a4edac50261ff0'),
 'polymeter':dict(setup=None,pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='507203d0d95546d20263e22db8cf129b32da0c1bada55030b88ef8431bd2be7e'),
 'song-sections':dict(setup='song-sections',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='93f4d125d8e7cd298479cbb127977675f08b25b957ab2f1734fbc065649dda05'),
 # Chord articulation by step trig locks (notes) and a CC lock witness (notes and controllers in the contract).
 'harmony-strum-arp':dict(setup='harmony-strum-arp',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='6638a7ef7f50a289b57fcdcb17ca5ed47eb9b5642989ce7e79c4d6f8135d6e48'),
 'param-lock-comparison':dict(setup='param-lock-comparison',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='41e49730507f030869244fc2425b0aa4f39ab57ed2822ce0243d55bbd5bbaadf'),
 # Harmony Revoice by invariants (README.md#harmony): slot 1 literal, slot 2 checked against stated rules, not notes.
 'voice-leading-revoice':dict(setup='voice-leading-revoice',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='13d0eebb1203b2c336f1fb072a57681a2d80dbb21845d5fbac7fca8ce5fafcbd'),
 # Course listening clips: the course's own state (setup course-stage) judged by its CONTRACTS entry, tiled.
 'course-first-sound-hear':dict(setup='course-stage',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='1a5b62c8005d3814c4ccbcc2267c0b9e8aa28a0d19a63df1cbe8a23b9554095d'),
 'course-build-a-phrase-compare':dict(setup='course-stage',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='e9270efc530db0c38460a3510a90b1c9472c9555f98e9817cbdaf6b7d9f16461'),
 'course-masks-listen':dict(setup='course-stage',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='25986edc83e58d4bb74f4833e04ce2681e1a5e47551173ac15d27d0f77160816'),
 'course-masks-keep':dict(setup='course-stage',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='ce12437c3e822b57f5b2e800a5c6b74c9a808693c017daef93bce493a9bd01a2'),
 'course-sequence-composition-both':dict(setup='course-stage',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='211361a734e7290a84f107eb27f1301ff8e7846419a29fcf8c30c5b48916ffcd'),
 'course-harmony-design-apply':dict(setup='course-stage',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='50404544295da7a9e3fe215efe7d68916e27938595cde38c3af0efde72912348'),
 'course-modulation-movement-and-interest-level':dict(setup='course-stage',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='b57298c2d4c7edbaa96d02c1a613f7b73d424c7a11ab287f49dffb6c21caffa0'),
 'course-song-composition-transition':dict(setup='course-stage',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='ab7d62be1e3de3a20f5b6a7f307079c6f53b5ed56959bca1102353aefc52dd25'),
 'course-keep-your-work-perform':dict(setup='course-stage',pcm_kind=None,pcm_solo_voice=None,
  contract_sha256='ab7d62be1e3de3a20f5b6a7f307079c6f53b5ed56959bca1102353aefc52dd25'),
}
def check_canonical_audio_lessons(authored):
 lessons=set()
 for source in authored['examples']:
  if source.get('purpose')!='lesson-comparison':continue
  canonical=CANONICAL_AUDIO_LESSONS.get(source['id'])
  if canonical is None:raise ValueError('Unsupported new audio lesson requires independent acceptance')
  if canonical_hash(source.get('midi_contract'))!=canonical['contract_sha256']:raise ValueError('Changed canonical audio lesson contract '+source['id'])
  if source.get('setup')!=canonical['setup']:raise ValueError('Changed canonical audio lesson setup '+source['id'])
  lessons.add(source['id'])
 return lessons
def audio_session_examples(report):
 sessions={}
 for example in report['examples']:
  for record in [example]+example.get('solo_contributions',[]):sessions[Path(record['evidence']['path']).resolve()]=example['id']
  for lane in example.get('musical_evidence',[]):sessions[Path(lane['path']).resolve()]=example['id']
 return sessions
def audio_scale_phase_rows(example_id,results):
 rows=[row for row in results if row.get('kind')=='manual-audio-scale-phase']
 if rows and example_id!='scale-slot-comparison':raise ValueError('Unreviewed scale phase in audio example '+example_id)
 for phase in rows:
  if (phase.get('at_step'),phase.get('scale_slot'),phase.get('root'))!=(32,2,'D') or not phase.get('output'):raise ValueError('Missing literal native Root D phase frame')
 return rows
def check_audio_capture_scope(report,authored,controlled_local=False):
 examples=report.get('examples',[]);wanted={value['id']:value for value in authored['examples']}
 if len(examples)!=len(wanted) or len({value['id'] for value in examples})!=len(examples) or {value['id'] for value in examples}!=set(wanted):raise ValueError('Missing or duplicate unique audio inventory')
 sessions=[]
 for example in examples:
  source=wanted[example['id']];tracks=source['tracks'];solos=example.get('solo_contributions',[])
  if len(solos)!=len(tracks) or {(value['channel'],value['voice']) for value in solos}!={(value['channel'],value['voice']) for value in tracks}:raise ValueError('Missing exact independent audio solo inventory')
  records=[(example,tracks)]+[(solo,[next(track for track in tracks if track['channel']==solo['channel'])]) for solo in solos]
  for record,selected in records:sessions.append((Path(record['evidence']['path']).resolve(),'real-time',True))
  if source.get('purpose')!='lesson-comparison':
   if any(field in example for field in ('musical_evidence','midi_witness','phase_observations','lesson_pcm','course_before_after')):raise ValueError('Unreviewed new audio musical evidence requires a canonical lesson')
   continue
  canonical=CANONICAL_AUDIO_LESSONS.get(source['id'])
  if canonical is None:raise ValueError('Unsupported new audio lesson requires independent acceptance')
  if source.get('setup')!=canonical['setup']:raise ValueError('Changed canonical audio lesson setup '+source['id'])
  lanes=example.get('musical_evidence',[])
  expected_lanes={'controlled-experimental'} if controlled_local else {'real-time','controlled-experimental'}
  if len(lanes)!=len(expected_lanes) or {value.get('clock_mode') for value in lanes}!=expected_lanes or any(value.get('passed') is not True for value in lanes):
   raise ValueError('Controlled audio lesson requires its exact controlled MIDI lane' if controlled_local else 'Audio lesson requires both MIDI lanes')
  for lane in lanes:sessions.append((Path(lane['path']).resolve(),lane['clock_mode'],False))
  for record,selected in records:
   if source.get('setup')=='course-stage':
    # A course stage cannot carry witness channels: its take is voice-routed and proved on MIDI before and after.
    row=record.get('course_before_after')
    if 'midi_witness' in record or 'lesson_pcm' in record or record.get('phase_observations'):raise ValueError('Course audio carries before/after MIDI proofs, not witness evidence')
    if isinstance(row,dict) and 'stand_in_port' in row:raise ValueError('Course before/after row is a MIDI-port rehearsal, not a voice take')
    if not isinstance(row,dict) or row.get('kind')!='manual-audio-course-before-after' or row.get('passed') is not True or any(not isinstance(row.get(name),dict) for name in ('before','route_to_voices','take','route_to_midi','after')):raise ValueError('Course audio lacks its before/after MIDI check')
    continue
   if not isinstance(record.get('midi_witness'),dict) or record['midi_witness'].get('passed') is not True:raise ValueError('Audio lesson lacks same-session MIDI witness')
   phases=record.get('phase_observations')
   if not isinstance(phases,list) or len(phases)!=len(source.get('phase_changes',[])):raise ValueError('Audio lesson lacks authored continuous phase observations')
   pcm_kind=canonical['pcm_kind'] if canonical['pcm_solo_voice'] is None or (len(selected)==1 and selected[0]['voice']==canonical['pcm_solo_voice']) else None
   if pcm_kind and (not isinstance(record.get('lesson_pcm'),dict) or record['lesson_pcm'].get('kind')!=pcm_kind or record['lesson_pcm'].get('passed') is not True):raise ValueError('Missing exact audio lesson PCM proof')
   if not pcm_kind and 'lesson_pcm' in record:raise ValueError('Unsupported new audio lesson PCM proof')
 if len({path for path,clock,voices in sessions})!=len(sessions):raise ValueError('Expected distinct native audio sessions')
 return sessions
def check_audio_native_session(path,clock_mode,voices):
 native_source_identity(path,voice_roots=voices)
 config=json.loads((path/'native/native-config.json').read_text());observations=json.loads((path/'observations.json').read_text())
 if config.get('clock_mode')!=clock_mode or not observations or any(value['state']['clock']['mode']!=clock_mode for value in observations):raise ValueError('Changed actual native audio clock')
 final=observations[-1]['state']
 if final.get('held')!=[] or final['midi_capture']['outstanding']!=[]:raise ValueError('Missing released native audio session state')
 rows=json.loads((path/'results.json').read_text());cleanup=json.loads((path/'native/cleanup.json').read_text())
 if any(row.get('passed') is False or row.get('matched') is False for row in rows):raise ValueError('Failed native audio session assertion')
 if not cleanup or any(row.get('returncode') not in ((0,-15) if row.get('service') in ('sclang','crow') else (0,)) for row in cleanup):raise ValueError('Native audio session cleanup failed')
 events=[json.loads(line) for line in (path/'native/native-events.jsonl').read_text().splitlines()];recipe=json.loads((path/'recipe.json').read_text());check_native_input_trace(recipe,events)
 return mosaic_file_map(json.loads((path/'native/identity.json').read_text()))
def check_scale_phase_frame(phase,results,observations):
 # manual_audio.apply_phase captures this frame as case MA-AUDIO-SCALE-PHASE.
 check_frame(phase['output'],'MA-AUDIO-SCALE-PHASE',results,observations)
def verify_audio_retake_receipts(report,run):
 """Verify bounded real-time retries and their preserved failure evidence."""
 root=Path(run).resolve(strict=True)
 referenced=set()
 expected_attempt_names=set()
 required_attempt_names=set()
 successful_attempt_names=set()
 lane_count=retake_count=0
 def reject(condition,message):
  if not condition:raise ValueError("Audio retake receipt: "+message)
 def verify_successful_lane(lane_path):
  reject(lane_path.parent==root and lane_path.is_dir(),"successful lane escaped its run")
  failure_path=lane_path/'lesson-failure.json'
  receipt_path=lane_path/'retake-receipt.json'
  reject(not failure_path.exists() and not failure_path.is_symlink() and not receipt_path.exists() and not receipt_path.is_symlink(),"successful lane retains failed-attempt records")
  result_path=lane_path/'lesson-result.json'
  reject(result_path.is_file() and result_path.stat().st_size<=1024*1024 and result_path.resolve(strict=True).parent==lane_path,"successful lane result is missing, escaped, or oversized")
  result=json.loads(result_path.read_text())
  reject(result.get('passed') is True and result.get('clock_mode')=='real-time' and Path(result.get('path','')).resolve()==lane_path,"successful lane result identity mismatch")
 for example in report.get('examples',[]):
  for lane in example.get('musical_evidence',[]):
   lane_count+=1
   case=str(example.get('id',''))+'-midi-real-time'
   if lane.get('clock_mode')=='real-time' and Path(case).name==case and case not in ('','.','..'):
    expected_attempt_names.update((case,case+'-retake-1',case+'-retake-2'))
    lane_path_value=lane.get('path')
    lane_name=Path(lane_path_value).name if isinstance(lane_path_value,str) else None
    retry_prefix=case+'-retake-'
    if lane_name==case:implied_attempts=0
    elif lane_name is not None and lane_name.startswith(retry_prefix) and lane_name[len(retry_prefix):] in ('1','2'):
     implied_attempts=int(lane_name[len(retry_prefix):])
    else:implied_attempts=None
    if implied_attempts is not None:
     required_attempt_names.update(case if index==1 else case+'-retake-'+str(index-1) for index in range(1,implied_attempts+1))
   else:
    lane_name=None
    implied_attempts=None
   if 'retakes' not in lane:
    if lane_name in expected_attempt_names:
     lane_path=Path(lane['path']).resolve(strict=True)
     verify_successful_lane(lane_path)
     successful_attempt_names.add(lane_name)
    continue  # historical single-attempt sessions remain valid
   retakes=lane.get('retakes')
   reject(isinstance(retakes,list) and 1<=len(retakes)<=2,"invalid retry count")
   reject(lane.get('clock_mode')=='real-time',"retries are allowed only for real-time lanes")
   reject(Path(case).name==case and case not in ('','.','..'),"invalid case identity")
   reject(isinstance(lane.get('path'),str),'successful lane path is missing')
   lane_path=Path(lane['path']).resolve(strict=True)
   verify_successful_lane(lane_path)
   successful_attempt_names.add(lane_path.name)
   reject(implied_attempts==len(retakes),"successful lane path does not identify the reported retry sequence")
   required_attempt_names.update(case if index==1 else case+'-retake-'+str(index-1) for index in range(1,len(retakes)+1))
   for index,row in enumerate(retakes,1):
    reject(isinstance(row,dict),"receipt row is not an object")
    expected_name=case if index==1 else case+'-retake-'+str(index-1)
    reject(row.get('case')==case and row.get('clock_mode')=='real-time',"case or lane mismatch")
    reject(row.get('attempt')==index and type(row.get('attempt')) is int and row.get('max_attempts')==3 and type(row.get('max_attempts')) is int,"attempt sequence or limit mismatch")
    reject(row.get('retake_eligible') is True and row.get('error_type')=='AssertionError',"failed take was not an eligible timing assertion")
    reject(isinstance(row.get('path'),str),'failed attempt path is missing')
    attempt=Path(row['path']).resolve(strict=True)
    reject(attempt.parent==root and attempt.is_dir() and attempt.name==expected_name,"failed attempt escaped or has wrong path")
    receipt_path=attempt/'retake-receipt.json'
    reject(receipt_path.is_file() and receipt_path.stat().st_size<=1024*1024 and receipt_path.resolve(strict=True).parent==attempt,"missing, escaped, or oversized retake receipt")
    receipt_data=json.loads(receipt_path.read_text())
    receipt_hash=row.get('receipt_sha256')
    public_row=dict(row);public_row.pop('receipt_sha256',None)
    reject(isinstance(receipt_hash,str) and digest(receipt_path)==receipt_hash and receipt_data==public_row,"retake receipt hash/content mismatch")
    failure_path=attempt/'lesson-failure.json'
    reject(failure_path.is_file() and failure_path.stat().st_size<=1024*1024 and failure_path.resolve(strict=True).parent==attempt,"missing, escaped, or oversized worker failure record")
    failure=json.loads(failure_path.read_text())
    reject(isinstance(row.get('worker_failure'),dict) and row.get('worker_failure')==failure,"worker failure differs from receipt")
    reject(row.get('worker_failure_sha256')==digest(failure_path),"worker failure hash mismatch")
    packet=failure.get('packet');timing_row=failure.get('row');kind=failure.get('kind')
    reject(failure.get('category')=='timing' and failure.get('clock_mode')=='real-time' and kind in ('Musical onset','Musical gate'),"worker failure is not an authorized real-time timing miss")
    reject(isinstance(packet,dict) and type(packet.get('monotonic_ns')) is int and not isinstance(packet.get('monotonic_ns'),bool),"timing packet has no real-time timestamp")
    reject(isinstance(timing_row,dict) and type(timing_row.get('step')) in (int,float) and not isinstance(timing_row.get('step'),bool),"timing assertion row is malformed")
    if kind=='Musical gate':reject(type(timing_row.get('length')) in (int,float) and not isinstance(timing_row.get('length'),bool),"gate assertion row has no length")
    referenced.add(attempt.resolve())
    retake_count+=1
   expected_final=case+'-retake-'+str(len(retakes))
   reject(lane_path.name==expected_final,"successful lane does not follow the retry sequence")
 discovered=set()
 for name in required_attempt_names:
  attempt=root/name
  reject(attempt.is_dir() and attempt.resolve(strict=True).parent==root,"missing or escaped generated prior-attempt directory")
  receipt_path=attempt/'retake-receipt.json'
  failure_path=attempt/'lesson-failure.json'
  reject(receipt_path.is_file() and receipt_path.resolve(strict=True).parent==attempt.resolve(strict=True),"generated prior attempt is missing its receipt")
  reject(failure_path.is_file() and failure_path.resolve(strict=True).parent==attempt.resolve(strict=True),"generated prior attempt is missing its worker failure")
 for child in root.iterdir():
  if child.name in expected_attempt_names and child.is_dir() and child.name not in successful_attempt_names:discovered.add(child.resolve())
 reject(discovered==referenced,"unreported or missing preserved retry attempt")
 return dict(lanes=lane_count,retakes=retake_count,passed=True)

def audit_audio_session_integrity(path=None,controlled_local=False):
 path=Path(path) if path is not None else MANUAL/'generated/audio-scenes.json';report=json.loads(path.read_text());authored=yaml.safe_load((MANUAL/'audio-scenes.yaml').read_text());check_canonical_audio_lessons(authored);sessions=check_audio_capture_scope(report,authored,controlled_local=controlled_local);session_examples=audio_session_examples(report)
 if controlled_local:
  if report.get('validation_scope')!='controlled-manual-generation' or report.get('realtime_qualification')!='pending-ci' or report.get('clock_mode')!='controlled-experimental' or report.get('audio_capture_clock_mode')!='real-time' or report.get('complete_regression_run') is not False or not str(report.get('controlled_lane','')).startswith('inapplicable:'):raise ValueError('Missing controlled-manual audio scope')
 elif report.get('clock_mode')!='real-time' or report.get('complete_regression_run') is not False or not str(report.get('controlled_lane','')).startswith('inapplicable:'):raise ValueError('Missing native audio real-time scope')
 run=Path(report['examples'][0]['evidence']['path']).parent
 verify_audio_retake_receipts(report,run)
 import manual_audio_resume
 if manual_audio_resume.require_resume_provenance(report,run):
  import manual_audio
  resume_audit=manual_audio_resume.audit_resume_provenance(manual_audio,report,run,ROOT)
  from manual_audio_origin_audit import audit_resumed_audio_sessions
  import sys
  return audit_resumed_audio_sessions(sys.modules[__name__],report,authored,sessions,session_examples,run,resume_audit)
 for current,frozen,key in [(ROOT/'tools/manual_audio.py',run/'capture-tool.py','tool_sha256'),(ROOT/'tools/manual_capture.py',run/'capture-helpers.py','helper_sha256')]:
  if report.get(key)!=digest(current) or digest(frozen)!=report[key]:raise ValueError('Stale native audio capture source '+key)
 if report.get('setups_sha256') is None or digest(ROOT/'tools/manual_audio_setups.py')!=report['setups_sha256'] or not (run/'capture-setups.py').is_file() or digest(run/'capture-setups.py')!=report['setups_sha256']:raise ValueError('Audio setups identity')
 if any(out.parent!=run.resolve() for out,clock,voices in sessions):raise ValueError('Audio session lies outside original frozen campaign')
 original=json.loads((run/'audio-scenes.json').read_text());originals={value['id']:value for value in original['examples']}
 for example in report['examples']:
  for field in ('musical_evidence','midi_witness','phase_observations','lesson_pcm','course_before_after'):
   baseline=originals[example['id']]
   if (field in example)!=(field in baseline) or example.get(field)!=baseline.get(field):raise ValueError('Changed immutable audio musical evidence')
 for out,clock,voices in sessions:
  check_audio_native_session(out,clock,voices)
  identity=json.loads((out/'native/identity.json').read_text());application=identity['application_identity'];code_root=Path(application['code_root'])
  if capture_application_root(out)!=(run/'application').resolve():raise ValueError('Audio participant frozen application root differs')
  for item in application['files']:
   relative=Path(item['path'])
   if relative.parts[0]=='mosaic' and (code_root/relative).resolve()!=(run/'application').joinpath(*relative.parts[1:]).resolve():raise ValueError('Audio participant did not load the frozen campaign application')
  results=json.loads((out/'results.json').read_text());observations=json.loads((out/'observations.json').read_text())
  for phase in audio_scale_phase_rows(session_examples[out],results):
   check_scale_phase_frame(phase,results,observations)
   binding=phase['output']['binding'];state=next(value['state'] for value in observations if value['state']['frame']['sha256']==binding['sha256'] and value['state']['grid']==phase['output']['grid'])
   verify_cached_ui(state,dict(literal_header=['SCALE','SLOT 02','vertical_list'],field=dict(layout='vertical_list',label='Root',value='D')),out)
 return dict(passed=True,dsp_sessions=sum(voices for out,clock,voices in sessions),midi_sessions=sum(not voices for out,clock,voices in sessions),complete_regression_run=False,hardware_timing_verified=False)
def audit_raw_publications(controlled_local=False):
 """Audit every raw native publication before editorial rebinding or compilation.

 Uses the same immutable evidence and current-source checks as the full audit.
 This intentionally does not grant compiled-book or editorial-overlay acceptance.
 """
 pilot=audit_controlled_pilot() if controlled_local else audit_pilot();references=[];generic=[];specialized=[]
 for path in sorted((MANUAL/'generated').glob('*.json')):
  if path.name in ('pilot.json','book.json','reader-index.json'):continue
  document=json.loads(path.read_text());kind=scene_format(document)
  if kind=='reference':references.append(dict(file=path.name,scenes=len(document['scenes']),frames=audit_reference(document),clock_mode=document['clock_mode']))
  elif kind=='generic':generic.append(dict(file=path.name,**audit_generic(document)))
  elif kind=='audio-route-projection':
   from manual_player_routes import audit as audit_routes
   specialized.append(dict(file=path.name,kind=kind,**audit_routes(path)))
  elif kind=='doctor-native-audio':specialized.append(dict(file=path.name,kind=kind,**audit_doctor(path)))
 from manual_audio import audit_publication as audit_audio
 audio_audit=audit_audio(MANUAL/'generated/audio-scenes.json',controlled_local=True) if controlled_local else audit_audio()
 audio=dict(audio_audit,native_session_integrity=audit_audio_session_integrity(controlled_local=controlled_local))
 return dict(passed=True,complete_regression_run=False,hardware_timing_verified=False,pilot=pilot,references=references,generic=generic,specialized=specialized,audio=audio)

def audit_inventory_source_hashes(root,inventory_path,expected_sources):
 root=Path(root).resolve()
 inventory=json.loads(Path(inventory_path).read_text())
 sources=inventory.get('source_files')
 if not isinstance(sources,dict) or set(sources)!=set(expected_sources):raise ValueError('Manual inventory source identity set changed')
 for relative in expected_sources:
  path=Path(relative)
  if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe manual inventory source path')
  source=root/path
  if not source.is_file() or digest(source)!=sources.get(relative):raise ValueError('Manual inventory source hash is stale: '+relative)
 return dict(passed=True,sources=len(sources))

def captured_scene_order(scenes):
 """Scene ids in manual_case_capture's capture order: grouped by (behaviour case, profile), first appearance first."""
 groups={}
 for scene in scenes:groups.setdefault((scene['behaviour_case'],scene.get('profile','base-midi')),[]).append(scene['id'])
 return [identifier for group in groups.values() for identifier in group]
def audit_controlled_stage_adoptions(build,manifest,root):
 """Recheck adopted checkpoint and audio stages independently at final audit."""
 stages=manifest.get('stages',[])
 adopted_rows=[row for row in stages if row.get('execution_status')=='adopted-verified' and row.get('name')!='musical-audio-assets']
 checkpoint=None
 if adopted_rows:
  from resume_adoption import audit_resume_lineage
  checkpoint=audit_resume_lineage(build,manifest,root)
 audio_claimed=('audio_adoption' in manifest or any(row.get('name')=='musical-audio-assets' and row.get('execution_status')=='adopted-verified' for row in stages))
 audio=None
 if audio_claimed:
  from audio_report_adoption import audit_build_audio_adoption
  audio=audit_build_audio_adoption(build,manifest,root)
 return {'checkpoint':checkpoint,'audio':audio}

def audit_reader_projection(retained=None,fresh_target_midi_manifest=None,fresh_target_midi_sha256=None,fresh_build_root=None):
 from manual_reader_projection import validate_projection
 generated=MANUAL/'generated'
 report=validate_projection(generated/'reader-index.json',generated/'reader-chunks',
     generated/'book.json',generated/'audio-scenes.json',project_root=ROOT,
     retained_midi_admissions=ROOT/retained['relative_path'] if retained else None,
     retained_midi_admissions_sha256=retained['sha256'] if retained else None,
     fresh_target_midi_manifest=fresh_target_midi_manifest,
     fresh_target_midi_sha256=fresh_target_midi_sha256,
     fresh_build_root=fresh_build_root)
 report['producer_sha256']=digest(ROOT/'tools/manual_reader_projection.py')
 if fresh_target_midi_manifest is not None:
  manifest_path=Path(fresh_target_midi_manifest).resolve()
  build_root=Path(fresh_build_root).resolve()
  if manifest_path!=build_root/'fresh-target-midi-manifest.json':raise ValueError('Fresh target MIDI manifest is outside its build receipt')
  producer=build_root/'fresh-target-midi-producer.json'
  if not producer.is_file():raise ValueError('Fresh target MIDI producer stage receipt is missing')
  stage=json.loads(producer.read_text());expected={'path':str(manifest_path),'sha256':fresh_target_midi_sha256}
  if stage.get('name')!='fresh-target-midi-producer' or stage.get('passed') is not True or stage.get('returncode')!=0 or stage.get('fresh_target_midi_manifest',{}).get('path')!=expected['path'] or stage.get('fresh_target_midi_manifest',{}).get('sha256')!=expected['sha256'] or stage.get('fresh_target_midi_producer_sha256')!=digest(ROOT/'tools/manual_fresh_target_midi.py'):
   raise ValueError('Fresh target MIDI producer receipt differs from the projected manifest')
  log=build_root/'fresh-target-midi-producer.log'
  if not log.is_file() or stage.get('log_sha256')!=digest(log):raise ValueError('Fresh target MIDI producer log changed')
  data=json.loads(manifest_path.read_text())
  report['fresh_target_midi_qualification']=data.get('qualification')
  report['fresh_target_midi_producer_sha256']=digest(ROOT/'tools/manual_fresh_target_midi.py')
  report['fresh_target_midi_manifest_sha256']=fresh_target_midi_sha256
 return report

def _audit_controlled_manual_generation(build_evidence,require_manual_generation_complete=True):
 """Audit controlled manual-generation receipts; REAL qualification remains pending CI."""
 build=Path(build_evidence).resolve();manifest_path=build/'manifest.json';context_path=build/'generation-context.json'
 if not build.is_dir():raise ValueError('Missing controlled manual build directory')
 manifest=json.loads(manifest_path.read_text()) if manifest_path.is_file() else None
 if manifest is None and require_manual_generation_complete:raise ValueError('Missing final controlled manual build manifest')
 if manifest is not None:
  if manifest.get('schema_version')!=1 or manifest.get('passed') is not True or manifest.get('build_complete') is not False:raise ValueError('Controlled manual build must remain separate from full REAL build qualification')
  if manifest.get('validation_scope')!='controlled-manual-generation' or manifest.get('realtime_qualification')!='pending-ci' or manifest.get('clock_mode')!='controlled-experimental' or manifest.get('complete_regression_run') is not False:raise ValueError('Controlled manual completion scope changed')
  if require_manual_generation_complete and manifest.get('manual_generation_complete') is not True:raise ValueError('Controlled manual completion marker is missing')
  if manifest.get('controlled_time_admitted') is not False or manifest.get('renderer_validated') is not True:raise ValueError('Controlled manual completion or renderer validation missing')
  audit_controlled_stage_adoptions(build,manifest,ROOT)
 if not context_path.is_file():raise ValueError('Missing immutable controlled generation context')
 context=json.loads(context_path.read_text())
 if context.get('schema_version')!=1 or context.get('validation_scope')!='controlled-manual-generation' or context.get('realtime_qualification')!='pending-ci' or context.get('clock_mode')!='controlled-experimental' or context.get('complete_regression_run') is not False:raise ValueError('Controlled generation context scope changed')
 plans=sorted(MANUAL.glob('scene-plans*.yaml'));required_plans=[path.name for path in plans]
 expected_rows={};captured_orders={};expected_scene_ids=[]
 for path in plans:
  data=yaml.safe_load(path.read_text()) or {};profiles=sorted({scene.get('profile','base-midi') for scene in data.get('scenes',[])}) or ['base-midi']
  for profile in profiles:
   if profile not in ('base-midi','midi-modulation','manual-player-ui'):raise ValueError('Unsupported required scene profile')
   name='reference-controlled-'+path.stem+'-'+profile
   scenes=[scene for scene in data.get('scenes',[]) if scene.get('profile','base-midi')==profile]
   expected_rows[name]=[scene['id'] for scene in scenes];captured_orders[name]=captured_scene_order(scenes);expected_scene_ids.extend(expected_rows[name])
 if len(expected_scene_ids)!=len(set(expected_scene_ids)):raise ValueError('Duplicate scene IDs across required controlled plans')
 expected_scene_ids=sorted(expected_scene_ids)
 if not required_plans or context.get('required_plans')!=required_plans or context.get('selected_plans')!=required_plans or context.get('required_scene_ids')!=expected_scene_ids or context.get('selected_scene_ids')!=expected_scene_ids:raise ValueError('Controlled generation context omits required plan/profile inventory')
 if manifest is not None and (manifest.get('required_plans')!=required_plans or manifest.get('selected_plans')!=required_plans or manifest.get('required_scene_ids')!=expected_scene_ids or manifest.get('selected_scene_ids')!=expected_scene_ids):raise ValueError('Controlled build omitted required authored plan/profile inventory')
 current={str(path.relative_to(ROOT)):digest(path) for path in sorted(MANUAL.rglob('*.yaml'))}
 archived_root=build/'authoring-before';archived={str(path.relative_to(archived_root)):digest(path) for path in sorted(archived_root.rglob('*.yaml'))} if archived_root.is_dir() else None
 if archived is None:raise ValueError('Missing immutable controlled-build authoring-before snapshot')
 before=context.get('source_files_before')
 if not isinstance(before,dict) or before!=archived:raise ValueError('Controlled generation context differs from archived before sources')
 if manifest is not None:
  if manifest.get('source_files_before')!=archived or manifest.get('source_files_after')!=current:raise ValueError('Controlled build source snapshots differ from archived before/current after')
 for plan in required_plans:
  relative='manual/'+plan
  if archived.get(relative)!=current.get(relative):raise ValueError('Controlled scene plan source changed during build: '+plan)
 rows=manifest.get('stages',[]) if manifest is not None else []
 if manifest is None:
  for name in expected_rows:
   receipt=build/(name+'.json')
   if receipt.is_file():rows.append(json.loads(receipt.read_text()))
 by_name={row.get('name'):row for row in rows}
 if len(by_name)!=len(rows) or {name for name in by_name if name.startswith('reference-controlled-')}!=set(expected_rows):raise ValueError('Controlled stage inventory differs from required plan/profile inventory')
 audited=[]
 for name,scene_ids in expected_rows.items():
  row=by_name[name]
  if row.get('passed') is not True or row.get('returncode')!=0:raise ValueError('Controlled scene stage failed: '+name)
  log=build/(name+'.log')
  if not log.is_file() or digest(log)!=row.get('log_sha256'):raise ValueError('Changed controlled stage log: '+name)
  receipt=row.get('native_report',{});path=Path(receipt.get('path',''))
  if not path.is_absolute() or path.name!='reference-scenes.json' or not path.is_file() or digest(path)!=receipt.get('sha256'):raise ValueError('Changed controlled native report: '+name)
  document=json.loads(path.read_text())
  if document.get('validation_scope')!='controlled-manual-generation' or document.get('realtime_qualification')!='pending-ci' or document.get('clock_mode')!='controlled-experimental' or document.get('complete_regression_run') is not False or 'manual_generation_complete' in document:raise ValueError('Controlled native report scope changed: '+name)
  if document.get('selected_scene_ids')!=scene_ids or [scene['id'] for scene in document.get('scenes',[]) or []]!=captured_orders[name]:raise ValueError('Controlled native report scene inventory changed: '+name)
  audited.append(dict(name=name,report_sha256=receipt['sha256'],frames=audit_reference(document)))
 # Before final assembly the compiled book and course feature bindings are
 # intentionally not authoritative yet. The controlled raw inventory, current
 # source, native cleanup, masks/audio assets and encoded files are still audited.
 publication=audit_raw_publications(controlled_local=True)
 if not require_manual_generation_complete:
  return dict(passed=True,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',clock_mode='controlled-experimental',manual_generation_complete=False,complete_regression_run=False,controlled_stages=audited,current_publication=publication)
 book_source=load()
 inventory_sources={'manual/'+book_source['legacy_source'],'cheat_sheet.html','tests/behaviour/manual-inventory.json'}
 inventory_identity=audit_inventory_source_hashes(ROOT,MANUAL/'inventory.json',inventory_sources)
 expected=compile_book(book_source);actual=json.loads((MANUAL/'generated/book.json').read_text())
 if expected!=actual:raise ValueError('Stale compiled book after controlled generation')
 reader_projection=audit_reader_projection(manifest.get('retained_midi_admission'))
 projection_rows=[row for row in rows if row.get('name')=='reader-projection']
 if len(projection_rows)!=1 or projection_rows[0].get('passed') is not True:raise ValueError('Reader projection stage receipt is missing or failed')
 if projection_rows[0].get('reader_projection')!=reader_projection:raise ValueError('Reader projection stage report differs from current source-bound files')
 raw=capture_catalogue()
 for identifier,scene in actual['scenes'].items():
  if identifier not in raw:raise ValueError('Compiled scene lacks current raw catalogue evidence: '+identifier)
  check_compiled_scene_contract(raw[identifier],scene)
 course=None
 if actual.get('project',{}).get('capture_status')=='controlled-verified':
  from manual_course_bind import verify_publication as verify_course
  course=verify_course(root=ROOT,controlled_local=True)
  if course.get('passed') is not True or course.get('validation_scope')!='controlled-manual-generation':raise ValueError('Controlled course publication proof did not pass')
 return dict(passed=True,validation_scope='controlled-manual-generation',realtime_qualification='pending-ci',clock_mode='controlled-experimental',manual_generation_complete=True,complete_regression_run=False,controlled_stages=audited,current_publication=publication,inventory_sources=inventory_identity,course=course,features=len(actual['features']),reader_projection=reader_projection)

def audit_controlled_manual_generation(build_evidence,require_manual_generation_complete=True,metadata_transition_proof=None):
 """Strict generation audit; a reviewed metadata proof is explicit and post-build only."""
 if metadata_transition_proof is None:
  return _audit_controlled_manual_generation(build_evidence,require_manual_generation_complete)
 if not require_manual_generation_complete:raise ValueError('Metadata transition proof requires the complete post-build audit')
 from manual_metadata_transition import transition_scope
 with transition_scope(ROOT,metadata_transition_proof):
  result=_audit_controlled_manual_generation(build_evidence,True)
 result['reviewed_metadata_proof']={'path':str(Path(metadata_transition_proof).resolve()),'sha256':digest(Path(metadata_transition_proof)),'source_scope':'243 exact Mosaic application files and 3 verified review metadata transitions'}
 return result

def audit_publication(retained=None,fresh_target_midi_manifest=None,fresh_target_midi_sha256=None,fresh_build_root=None):
 expected=compile_book(load());actual=json.loads((MANUAL/'generated/book.json').read_text())
 if expected!=actual:raise ValueError('Stale compiled book; rebuild after authoring changes')
 target_ids={'doctor-local-capture-and-paint','doctor-local-auto-capture-and-paint','panic-from-song-channel','panic-from-song-pattern'}
 if any(scene.get('id') in target_ids for scene in actual.get('scenes',{}).values()) and not retained and not fresh_target_midi_manifest:
  raise ValueError('Full publication requires a fresh native or explicit retained target MIDI receipt')
 reader_projection=audit_reader_projection(retained,fresh_target_midi_manifest,fresh_target_midi_sha256,fresh_build_root)
 course=None
 if actual.get('project',{}).get('capture_status')=='verified':
  from manual_course_bind import verify_publication as verify_course
  course=verify_course(root=ROOT)
  if course.get('passed') is not True:raise ValueError('Course publication proof did not pass')
 raw=capture_catalogue()
 for identifier,scene in actual['scenes'].items():
  if identifier not in raw:raise ValueError('Compiled scene lacks original native publication')
  check_compiled_scene_contract(raw[identifier],scene)
 report=audit_raw_publications()
 if course is not None:report=dict(report,course=course)
 return dict(report,features=len(actual['features']),reader_projection=reader_projection)
def main():
 import argparse
 parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group();mode.add_argument('--refresh-editorial',action='store_true');mode.add_argument('--raw-only',action='store_true');parser.add_argument('--controlled-local',action='store_true');parser.add_argument('--build-evidence',type=Path);parser.add_argument('--ffmpeg');parser.add_argument('--retained-midi-admissions',type=Path);parser.add_argument('--retained-midi-admissions-sha256');parser.add_argument('--fresh-target-midi-manifest',type=Path);parser.add_argument('--fresh-target-midi-sha256');parser.add_argument('--fresh-build-root',type=Path);options=parser.parse_args()
 if bool(options.fresh_target_midi_manifest)!=bool(options.fresh_target_midi_sha256) or bool(options.fresh_target_midi_manifest)!=bool(options.fresh_build_root):parser.error('fresh target MIDI manifest, SHA256 and build root must be supplied together')
 if options.retained_midi_admissions and options.fresh_target_midi_manifest:parser.error('retained and fresh target MIDI routes are mutually exclusive')
 from manual_retained_midi_caller import retained_call
 retained=retained_call(ROOT,options.retained_midi_admissions,options.retained_midi_admissions_sha256,mode='retained-standalone' if options.retained_midi_admissions else 'fresh')
 if options.refresh_editorial:print(json.dumps(refresh_pilot_editorial(options.ffmpeg),indent=2));return
 if options.controlled_local:
  if options.raw_only:report=audit_raw_publications(controlled_local=True)
  elif options.build_evidence:report=audit_controlled_manual_generation(options.build_evidence,require_manual_generation_complete=False)
  else:parser.error('--controlled-local publication audit requires --build-evidence; use --raw-only for current raw publications')
 else:
  if options.build_evidence:parser.error('--build-evidence requires --controlled-local')
  report=audit_raw_publications() if options.raw_only else audit_publication(retained,options.fresh_target_midi_manifest,options.fresh_target_midi_sha256,options.fresh_build_root)
 print(json.dumps(report,indent=2))

if __name__=='__main__':main()

"""Independent seven-gate Doctor acceptance audit; never launches native sessions.

README.md#rhythm-doctor supplies musical/UI acceptance. Source/receipt guards are
publication-integrity characterisation, not hardware scheduling evidence.
"""
import argparse,base64,hashlib,json,math,struct,sys,tempfile,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/behaviour'))
from manual_publication_verify import native_source_identity,check_native_input_trace,check_doctor_identity,verify_cached_ui,canonical_hash
from manual_verify import check_frame
from manual_doctor_audit import read_softcut_pcm
ROLES={'manual_stereo':('manual_stereo','real-time'),'auto_left':('auto_left','real-time'),'manual_right':('manual_right','real-time'),'setup_real':('setup_options','real-time'),'setup_controlled':('setup_options','controlled-experimental'),'ready_real':('ready_options','real-time'),'ready_controlled':('ready_options','controlled-experimental')}
ORIGIN='application-autosave-after-public-adc'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def require(condition,message):
 if not condition:raise ValueError(message)
def bounded(root,name):
 name=Path(name);require(not name.is_absolute() and '..' not in name.parts,'Unsafe Doctor evidence relative path');p=(root/name).resolve();require(root.resolve() in p.parents,'Doctor evidence path escapes');return p
def check_roles(reports):
 require(set(reports)==set(ROLES),'Doctor qualification requires all seven exact roles')
 require(len({Path(value).resolve() for value in reports.values()})==7,'Doctor roles require distinct native reports')
def check_scope(report,case,clock):
 require(report.get('publication_kind')=='doctor-options-qualification' and report.get('case')==case,'Doctor qualification role differs')
 require(report.get('passed') is True and report.get('failure') is None and report.get('cleanup_failure') is None,'Doctor qualification failed')
 require(report.get('complete_regression_run') is False and report.get('hardware_timing_equivalent') is False,'Doctor qualification scope differs')
 require(report.get('clock_mode')==clock,'Doctor qualification clock differs')
 audio=case not in ('setup_options','ready_options');controlled=report.get('controlled_time',{})
 require(controlled.get('applicable') is (not audio) and bool(controlled.get('reason')),'Doctor ADC/UI controlled applicability missing')
 require(not audio or clock=='real-time','Doctor ADC requires real time')
 require(report.get('source')=='source.json' and report.get('results')=='results.json','Doctor report evidence filenames differ')
def native_midi_window(events,start,end,clock):
 require(type(start)is int and type(end)is int and 0<=start<=end,'Invalid explicit Doctor MIDI boundary')
 kind=11 if clock=='controlled-experimental' else 3
 packets=[value for value in events if value.get('kind')==kind and start<value.get('index',0)<=end and len(value.get('bytes',[]))==3]
 require(len({value['index'] for value in packets})==len(packets),'Duplicate native Doctor MIDI packet index')
 return packets
def check_phrase(packets,steps,expected,clock,cycles=1,closing=False,stop_time_ns=None):
 require(steps and sorted(set(steps))==steps and all(type(s)is int and 1<=s<=64 for s in steps),'Invalid Doctor phrase step mask')
 require(len(expected)==len(steps) and all(port==1 and len(data)==3 and data[0]==144 and data[1]==60 and 1<=data[2]<=127 for port,data in expected),'Invalid literal Doctor MIDI phrase')
 notes=[value for value in packets if 144<=value['bytes'][0]<=159 and value['bytes'][2]>0]
 minimum=len(expected)*cycles+int(closing);require(len(notes)>=minimum,'Missing complete Doctor musical cycles/closing attack')
 key='logical_ns' if clock=='controlled-experimental' else 'monotonic_ns';tolerance=2e-9 if clock=='controlled-experimental' else .01
 used=set()
 for index,note in enumerate(notes):
  port,data=expected[index%len(expected)];require(note['port']==port and note['bytes']==data,'Doctor exact native phrase differs')
  cell=(index//len(expected))*64+steps[index%len(expected)]-steps[0]
  require(abs((note[key]-notes[0][key])/1e9-cell/6)<=tolerance,'Doctor musical phrase timing differs')
  releases=[value for value in packets if value['index']>note['index'] and value['port']==port and (value['bytes']==[128,data[1],data[2]] or index==len(notes)-1 and type(stop_time_ns)is int and value['bytes']==[128,data[1],0])]
  require(bool(releases),'Missing Doctor note gate release');off=releases[0];length=(off[key]-note[key])/1e9
  musical_gate=off['bytes']==[128,data[1],data[2]] and abs(length-1/6)<=tolerance
  stopped_gate=index==len(notes)-1 and type(stop_time_ns)is int and 0<=length<=1/6+tolerance and note[key]<=stop_time_ns<=off[key]+round(tolerance*1e9) and abs((off[key]-stop_time_ns)/1e9)<=tolerance
  require(off['index'] not in used and (musical_gate or stopped_gate),'Doctor musical gate differs')
  used.add(off['index'])
 musical=[p for p in packets if 128<=p['bytes'][0]<=159];require(len(musical)==2*len(notes),'Extra or unbalanced Doctor musical packets')
 return dict(onsets=len(notes),complete_cycles=cycles,closing_attack=closing,tolerance_seconds=tolerance)
def bind_public_stop(events,packets,clock):
 notes=[value for value in packets if 144<=value['bytes'][0]<=159 and value['bytes'][2]>0];require(bool(notes),'Stop binding lacks musical attacks')
 last=notes[-1];releases=[value for value in packets if value['index']>last['index'] and value['port']==last['port'] and value['bytes'] in ([128,last['bytes'][1],last['bytes'][2]],[128,last['bytes'][1],0])];require(bool(releases),'Stop binding lacks exact release')
 off=releases[0];stops=[(index,value) for index,value in enumerate(events) if value.get('kind')=='input' and value.get('type')==3 and value.get('args')==[0,7,1] and value['monotonic_ns']>=last['monotonic_ns']]
 require(bool(stops),'Missing actual native public Stop');index,event=min(stops,key=lambda item:item[1]['monotonic_ns'])
 stop_ns=event['monotonic_ns']
 if clock=='controlled-experimental':stop_ns=sum(value['args'][0]*1000000000+value['args'][1] for value in events[:index] if value.get('kind')=='input' and value.get('type')==8)
 key='logical_ns' if clock=='controlled-experimental' else 'monotonic_ns';tolerance=2e-9 if clock=='controlled-experimental' else .01
 length=(off[key]-last[key])/1e9
 require(off['bytes'][2]==last['bytes'][2] and abs(length-1/6)<=tolerance or last[key]<=stop_ns<=off[key]+round(tolerance*1e9) and abs((off[key]-stop_ns)/1e9)<=tolerance,'Native public Stop release time differs')
 return dict(stop_time_ns=stop_ns,input_sequence=event['sequence'],native_event_sha256=canonical_hash(event),clock_mode=clock)
def check_adc_playback_horizon(events,packets):
 notes=[row for row in packets if 144<=row['bytes'][0]<=159 and row['bytes'][2]>0];require(bool(notes),'Missing actual ADC musical attacks')
 edges=[row for row in events if row.get('kind')=='input' and row.get('type')==3 and row.get('args')==[0,7,1]]
 pairs=list(zip(edges[::2],edges[1::2]));matches=[(play,stop) for play,stop in pairs if play['monotonic_ns']<=notes[0]['monotonic_ns']<=notes[-1]['monotonic_ns']<=stop['monotonic_ns']]
 require(len(matches)==1,'ADC MIDI witness lacks one exact native public playback window');play,stop=matches[0]
 elapsed=(stop['monotonic_ns']-play['monotonic_ns'])/1e9;require(elapsed>=12-.01,'ADC requires actual authored 12-second public playback horizon')
 actual=[row for row in events if row.get('kind')==3 and len(row.get('bytes',[]))==3 and 128<=row['bytes'][0]<=159 and play['monotonic_ns']<=row['monotonic_ns']<=stop['monotonic_ns']+10000000]
 require(actual==[row for row in packets if 128<=row['bytes'][0]<=159],'ADC packet boundary omits native public playback music')
 return dict(elapsed_seconds=elapsed,play_sequence=play['sequence'],stop_sequence=stop['sequence'],play_native_sha256=canonical_hash(play),stop_native_sha256=canonical_hash(stop),minimum_seconds=12,tolerance_seconds=.01)
def band_energy(samples,rate,hz):
 stride=20;size=rate//10;energy=0.0
 # Fixed 100ms interiors, averaged energies avoid phase cancellation between
 # independently restarted input kicks. No signal or output is synthesized.
 weights=[(math.cos(2*math.pi*hz*j/rate),math.sin(2*math.pi*hz*j/rate)) for j in range(0,size,stride)]
 for start in range(0,len(samples)-size+1,size):
  real=imag=0.0
  for (cosine,sine),value in zip(weights,samples[start:start+size:stride]):real+=value*cosine;imag+=value*sine
  energy+=real*real+imag*imag
 return energy
def check_selected_channels(channels,rate,selection):
 require(rate==48000 and len(channels)==2 and len(channels[0])==len(channels[1]),'Doctor captured PCM geometry differs')
 require(selection in ('stereo','left','right'),'Unsupported selected ADC input')
 require((channels[0]!=channels[1]) if selection=='stereo' else (channels[0]==channels[1]),'Stereo requires distinct ADC sources' if selection=='stereo' else 'Selected mono must duplicate its own ADC')
 checked=[]
 for channel,values in enumerate(channels):
  rms=math.sqrt(sum(v*v for v in values)/len(values));require(rms>.001,'Silent Doctor selected ADC input')
  selected=60 if selection=='left' or selection=='stereo' and channel==0 else 90;other=90 if selected==60 else 60
  energy=band_energy(values,rate,selected);alternate=band_energy(values,rate,other)
  require(energy>2*alternate and energy>0,'Captured selected ADC spectrum differs from public input')
  checked.append(dict(channel=channel,rms=rms,selected_hz=selected,energy=energy,other_energy=alternate))
 return checked
def check_fixture_contract(fixture):
 require(fixture.get('project_seed_origin')==ORIGIN,'READY needs real application autosave provenance')
 require(fixture.get('retained_audio') is False,'READY reload must have no retained audio')
 require(fixture.get('bank_bpm')==120 and type(fixture.get('window_max'))is int and fixture['window_max']>=64 and fixture.get('beat_count',0)>1,'READY bank geometry differs from confirmed ManualRight120')
 masks=fixture.get('masks_by_sensitivity',{});require(set(masks)=={'0','0.5','1'},'Missing READY sensitivity masks')
 for values in masks.values():require(isinstance(values,list) and sorted(set(values))==values and all(type(s)is int and 1<=s<=64 for s in values),'Invalid READY mask')
 require(bool(masks['0.5']) and len(masks['0.5'])<64,'READY requires a populated bounded lane')
 expected=fixture.get('midi_expected');require(isinstance(expected,list) and len(expected)==len(masks['0.5']),'READY MIDI phrase/mask mismatch')
def seed_files(root):
 root=Path(root).resolve();require(root.is_dir(),'Missing saved project seed')
 paths=list(root.rglob('*'));require(not any(path.is_symlink() for path in paths),'Symlink in READY seed')
 files={str(path.relative_to(root)):digest(path) for path in paths if path.is_file()}
 require('autosave.ptn' in files and all(name=='autosave.ptn' or name.startswith('config/') for name in files),'READY seed contains unqualified files')
 return files

REQUIRED_HARNESS={'tests/behaviour/driver.py','tests/behaviour/ui.py','tests/behaviour/ui_map.py','tests/behaviour/frame_oracle.py','tools/manual_capture.py','tools/manual_doctor_capture.py','tools/manual_doctor_audit.py','tools/doctor_ready_fixture.py','tools/doctor_options_capture.py','docs/ui-reimplementation/spec.json'}
def check_harness_inventory(harness):
 require(REQUIRED_HARNESS<=set(harness),'Incomplete Doctor harness provenance')
def check_production_inventory(files,root=ROOT):
 root=Path(root);required={'mosaic.lua'}
 for directory in ('lib','docs/ui-reimplementation/code','tools/rhythm_doctor'):
  for path in (root/directory).rglob('*'):
   if path.is_file() and path.suffix in ('.lua','.json','.py','.c','.h','.sh','.bin','.npz') and not any(part in ('tests','__pycache__','.git') for part in path.relative_to(root).parts):required.add(str(path.relative_to(root)))
 missing=required-set(files);require(not missing,'Incomplete Doctor production inventory: '+','.join(sorted(missing)))
def check_sources(out,report):
 source=read(out/'source.json');app=Path(source['app']).resolve();require(app==(out/'frozen-app').resolve(),'Frozen Doctor app path differs')
 files=source.get('files',{});require(bool(files),'Missing frozen Doctor source inventory')
 check_production_inventory(files)
 for name,value in files.items():
  frozen=bounded(app,name);require(digest(frozen)==value,'Changed frozen Doctor source '+name)
  if name=='mosaic.lua' or name.startswith(('lib/','docs/ui-reimplementation/code/','tools/rhythm_doctor/')):
   require((ROOT/name).is_file() and digest(ROOT/name)==value,'Stale Doctor production source '+name)
 recipe='tests/behaviour/contract/rhythm_doctor_capture_options.py' if report['case'] not in ('setup_options','ready_options') else 'tests/behaviour/contract/rhythm_doctor_options.py'
 require(digest(ROOT/recipe)==source.get('recipe_sha256')==digest(out/'acceptance-recipe.py'),'Stale Doctor acceptance recipe')
 require(digest(ROOT/'tools/doctor_options_capture.py')==source.get('runner_sha256')==digest(out/'capture-runner.py'),'Stale Doctor qualification runner')
 harness=source.get('harness_files',{});snapshot=Path(source.get('harness_snapshot','')).resolve();require(snapshot==(out/'harness').resolve() and bool(harness),'Missing Doctor prelaunch harness snapshot')
 check_harness_inventory(harness)
 for name,value in harness.items():require(digest(bounded(snapshot,name))==value and (ROOT/name).is_file() and digest(ROOT/name)==value,'Stale Doctor harness source '+name)
 require({str(p.relative_to(ROOT)) for p in (ROOT/'tests/behaviour').rglob('*.py')}<=set(harness),'Doctor harness omits current Python sources')
 native_source_identity(out,application_root=app);native=read(out/'native/identity.json');check_doctor_identity(report['source_identity'],native)
 return source

def visible_sequence(out,observations,contracts):
 from ui_map import RHYTHM_DOCTOR_SCREEN
 cursor=0;cache={}
 for route,label,value in contracts:
  title,layout=RHYTHM_DOCTOR_SCREEN['screens'][route];expected=dict(literal_header=[title,'CH01',layout])
  if label is not None:expected['field']=dict(layout=layout,label=label,value=str(value),art=True)
  found=False
  for index in range(cursor,len(observations)):
   state=observations[index]['state'];key=(state['frame']['sha256'],canonical_hash(expected))
   if key not in cache:
    try:verify_cached_ui(state,expected,out);cache[key]=True
    except ValueError:cache[key]=False
   if cache[key]:cursor=index+1;found=True;break
  require(found,'Missing ordered native Doctor UI: '+str((route,label,value)))
 return cursor

def audit_ui(out,report,results,observations,fixture=None):
 fields=[(row['route'],row['label'],row['value']) for row in results if row.get('kind')=='doctor-options' and row.get('check')=='field']
 if report['case']=='setup_options':
  wanted=[('R01','Tempo',v) for v in ('AUTO','MANUAL','AUTO')]+[('R01','Manual BPM',v) for v in ('120','40','40','240','240')]+[('R01','Input',v) for v in ('STEREO','L','R','STEREO','R')]+[('R01',k,v) for k,v in [('Tempo','AUTO'),('Manual BPM','120'),('Input','STEREO'),('Tempo','MANUAL'),('Manual BPM','127'),('Input','R'),('Input','R')]]
  require(fields==wanted,'Doctor setup option boundaries/draft contract differs')
  require(any(row.get('check')=='setup-complete' and row.get('backend_bpm_input_claim') is False for row in results),'Missing UI-only setup acceptance')
  visible_sequence(out,observations,fields);visible_sequence(out,observations,[('R11',None,None)])
  return dict(fields=len(fields),audio_applicable=False)
 require(fixture is not None,'READY qualification lacks verified fixture')
 visible_sequence(out,observations,fields)
 for landmark in [('R06','Exact BPM','40'),('R06','Exact BPM','240'),('R06','Start beat','1'),('R06','Start beat',str(fixture['beat_count'])),('R06','Fine start','-1ms'),('R06','Fine start','1ms'),('R05','Sensitivity','0'),('R05','Sensitivity','1'),('R05','Sensitivity','0.5')]:require(landmark in fields,'Missing READY option boundary '+str(landmark))
 visible_sequence(out,observations,[('R10',None,None),('R05',None,None)]);visible_sequence(out,observations,[('R07',None,None)])
 require(any(row.get('check')=='clear-keeps-painted-pattern' and row.get('bank_cleared') is True for row in results),'Missing READY clear preservation')
 masks=[row for row in results if row.get('kind')=='doctor-options' and row.get('check')=='exact-grid-mask'];cursor=0
 for row in masks:
  wanted=row['steps'];require(sorted(set(wanted))==wanted,'Invalid Doctor option mask receipt')
  found=False
  for index in range(cursor,len(observations)):
   levels=observations[index]['state']['grid'][48:112];actual=[i+1 for i,v in enumerate(levels) if v in ((12,15) if row['preview'] else (15,))]
   if actual==wanted:cursor=index+1;found=True;break
  require(found,'Missing ordered exact READY native grid mask')
 lane=set(fixture['masks_by_sensitivity']['0.5']);baseline={min(lane),next(s for s in range(1,65) if s not in lane)}
 committed=[set(row['steps']) for row in masks if not row['preview']]
 require(all(value in committed for value in [baseline^lane,baseline|lane,lane]),'READY paint policy algebra not observed')
 musical=[row for row in results if row.get('kind')=='midi'];require(len(musical)==3 and all(row.get('complete_cycles')==2 for row in musical),'READY requires three full two-cycle MIDI checks')
 events=[json.loads(line) for line in (out/'native/native-events.jsonl').read_text().splitlines()];windows=play_windows(events,report['clock_mode']);accepted=[]
 for packets in windows:
  try:accepted.append(check_phrase(packets,sorted(lane),fixture['midi_expected'],report['clock_mode'],cycles=2,closing=True,stop_time_ns=bind_public_stop(events,packets,report['clock_mode'])['stop_time_ns']))
  except ValueError:pass
 require(len(accepted)==3,'READY exact native full phrases not bound to three public playback windows')
 return dict(fields=len(fields),grid_masks=len(masks),musical_phrases=accepted,audio_applicable=False)
def play_windows(events,clock):
 kind=11 if clock=='controlled-experimental' else 3;windows=[];active=False;current=[]
 for event in events:
  if event.get('kind')=='input' and event.get('type')==3 and event.get('args')==[0,7,1]:
   if active:active=False;windows.append(current)
   else:active=True;current=[]
  elif event.get('kind')==kind and len(event.get('bytes',[]))==3:
   if active:current.append(event)
   elif windows and 128<=event['bytes'][0]<=143:windows[-1].append(event)
 return windows

def check_qualification_registration(out,report,source,results):
 name='tools/doctor-qualification-inventory.json';start_id='MA-DOCTOR-MANUAL-START-BEAT-001';setup_id='MA-DOCTOR-SETUP-OPTIONS-001';citation='manual:rhythm-doctor'
 checkpoints=['start-beat-original1','start-beat-next2','start-beat-next-ready','start-beat-restore1','start-beat-restored-ready']
 current=ROOT/name;registration=dict(file='qualification-registration.json',source_path=name,sha256=digest(current))
 require(report.get('qualification_manifest')==source.get('qualification_manifest')==registration,'Missing/stale exact Doctor qualification manifest receipt')
 require(digest(out/registration['file'])==registration['sha256'],'Doctor qualification manifest frozen report copy differs')
 harness=source.get('harness_files',{});snapshot=Path(source.get('harness_snapshot',''));require(snapshot.resolve()==(out/'harness').resolve(),'Doctor qualification harness snapshot differs')
 for dependency in (name,'tools/doctor_options_capture.py','tests/behaviour/contract/rhythm_doctor_start_beat.py','tests/behaviour/contract/rhythm_doctor_options.py'):
  require(dependency in harness and harness[dependency]==digest(ROOT/dependency)==digest(bounded(snapshot,dependency)),'Doctor qualification manifest/procedure lacks frozen harness provenance')
 manifest=read(current);entries=manifest.get('qualifications',[]);by_id={entry.get('id'):entry for entry in entries}
 require(manifest.get('schema_version')==1 and manifest.get('publication_kind')=='doctor-options-qualification' and bool(manifest.get('scope')) and len(entries)==2 and set(by_id)=={start_id,setup_id},'Unsupported specialized Doctor inventory')
 entry=by_id[start_id]
 require(entry.get('citation')==citation and entry.get('feature_id')=='rhythm-doctor' and entry.get('required_for_manual_build') is True and entry.get('global_inventory_member') is False,'Doctor Start Beat membership differs')
 require(entry.get('runner')==dict(path='tools/doctor_options_capture.py',role='manual_right',clock_mode='real-time') and entry.get('procedure')==dict(path='tests/behaviour/contract/rhythm_doctor_start_beat.py',callable='next_beat_apply_restore') and entry.get('checkpoint_ids')==checkpoints and bool(entry.get('scope')),'Doctor Start Beat procedure/checkpoint inventory differs')
 controlled=entry.get('controlled_time',{});require(controlled.get('applicable') is False and bool(controlled.get('reason')),'Doctor ADC controlled inapplicability differs')
 ui=entry.get('ui_only_witness',{});require(ui.get('role')=='ready_options' and ui.get('procedure')=='draft_next_cancel' and ui.get('clock_modes')==['real-time','controlled-experimental'] and ui.get('backend_regression') is False and ui.get('successful_reanalysis_claim') is False and bool(ui.get('requires')),'READY UI cannot claim full backend regression')
 setup_entry=by_id[setup_id];expected_roles=[
  dict(role='setup_real',clock_mode='real-time',installation_profile='audio'),
  dict(role='setup_controlled',clock_mode='controlled-experimental',installation_profile='controlled')]
 require(setup_entry.get('citation')==citation and setup_entry.get('feature_id')=='rhythm-doctor' and setup_entry.get('required_for_manual_build') is True and setup_entry.get('global_inventory_member') is False,'Setup options membership differs')
 require(setup_entry.get('registration_only') is True and setup_entry.get('native_run_required') is True and not any(key in setup_entry for key in ('passed','report','report_sha256','qualified_at')),'Staged setup registration claims a run')
 require(setup_entry.get('runner')==dict(path='tools/doctor_options_capture.py',roles=expected_roles) and setup_entry.get('procedure')==dict(path='tests/behaviour/contract/rhythm_doctor_options.py',callable='setup_options') and setup_entry.get('result_ids')==['setup-complete'] and bool(setup_entry.get('scope')),'Setup options procedure/role registration differs')
 setup_clock=setup_entry.get('controlled_time',{});require(setup_clock.get('applicable') is True and bool(setup_clock.get('reason')),'Setup UI controlled applicability differs')
 required=[]
 if report['case']=='manual_right':required=[dict(id=start_id,citation=citation)]
 elif report['case']=='setup_options':required=[dict(id=setup_id,citation=citation)]
 require(report.get('specialized_qualifications')==required,'Doctor report specialized role membership differs')
 if report['case']=='manual_right':
  require(report['clock_mode']=='real-time','Specialized Doctor backend requires real-time ADC')
  rows=[row for row in results if row.get('kind') in ('doctor-manual-start-beat','doctor-start-beat-checkpoint')]
  require(len(rows)==6 and sum(row.get('kind')=='doctor-manual-start-beat' for row in rows)==1 and [row.get('id') for row in rows if row.get('kind')=='doctor-start-beat-checkpoint']==checkpoints,'Missing exact registered Start Beat subprocedure rows')
  require(all(row.get('case_id')==start_id and row.get('citation')==citation for row in rows),'Doctor Start Beat row registered identity/citation differs')
 if report['case']=='setup_options':
  require(report['clock_mode'] in ('real-time','controlled-experimental'),'Setup UI lane differs')
  all_setup_rows=[row for row in results if row.get('kind')=='doctor-options']
  require(bool(all_setup_rows) and all(row.get('case_id')==setup_id and row.get('citation')==citation for row in all_setup_rows),'Doctor setup UI records lack specialized context identity/citation')
  rows=[row for row in all_setup_rows if row.get('check')=='setup-complete']
  require(len(rows)==1 and rows[0].get('backend_bpm_input_claim') is False,'Missing exact UI-only staged setup semantic receipt')
 return dict(manifest_sha256=registration['sha256'],specialized_qualifications=required,global_inventory_member=False)

def check_manual_start_beat(envelopes,results,captured_sha256):
 require(len(envelopes)==4,'ManualRight needs exactly four completed retained analyses')
 rows=[row for row in results if row.get('kind')=='doctor-manual-start-beat'];require(len(rows)==1,'Missing exact Manual Start Beat semantic receipt');row=rows[0]
 require(row.get('passed') is True and row.get('captured_sha256')==captured_sha256 and row.get('origins')==[0,24000,0] and row.get('bpm')==120 and row.get('candidate_absolute_positions_unchanged') is True and row.get('controlled_time',{}).get('applicable') is False and bool(row['controlled_time'].get('reason')),'Changed Manual Start Beat contract')
 require([row.get(name) for name in ('original','advanced','restored')]==envelopes[1:],'Manual Start Beat receipt differs from exact completed native envelopes')
 require(envelopes[0]['analysis_revision']==0 and len({e['job_id'] for e in envelopes})==4,'Retained corrections need distinct actual backend jobs')
 first=envelopes[0]
 for i,envelope in enumerate(envelopes):
  require(envelope.get('status')=='COMPLETED' and envelope.get('command')=='ANALYSE' and envelope.get('wav_sha256')==captured_sha256,'Manual correction lacks completed same-WAV analysis')
  require(type(envelope.get('analysis_revision'))is int and envelope['analysis_revision']==first['analysis_revision']+i,'Manual correction analysis revision chain differs')
  require(all(envelope.get(key)==first.get(key) and key in first for key in ('wav_sha256','frames','sample_rate','project_id','generation')),'Manual correction recording/project identity changed')
  require(type(envelope['frames'])is int and envelope['frames']>0 and envelope['sample_rate']==48000,'Manual correction recording geometry differs')
  if i==0:continue
  analysis=envelope['analysis'];origin=[0,24000,0][i-1]
  require(analysis.get('tempo_mode')=='manual' and analysis.get('bpm')==120 and analysis.get('origin_sample')==origin and analysis.get('phrase_start_sample')==origin,'Manual Start Beat origin/tempo differs')
  # Half-open whole-recording regular grid, including beats preceding origin.
  wanted=list(range(origin%24000,envelope['frames'],24000));require(len(wanted)>1 and analysis.get('beat_positions')==wanted,'Manual Start Beat full-capture regular grid differs')
  require(analysis.get('candidates')==envelopes[1]['analysis'].get('candidates') and analysis.get('detector')==envelopes[1]['analysis'].get('detector'),'Manual Start Beat changed absolute candidates/detector')
 return envelopes[-1]['analysis']

def audit_adc(out,report,results,observations,source):
 backend=[row for row in results if row.get('kind')=='doctor-backend-options'];require(len(backend)==1 and backend[0].get('passed') is True,'Missing exact actual ADC acceptance');row=backend[0]
 mode,selection=report['case'].split('_');require((row.get('mode'),row.get('input_source'),row.get('manual_bpm'))==(mode,selection,100),'ADC authored mode/input/BPM differs')
 from contract.rhythm_doctor_capture_options import asymmetric_stimulus
 with tempfile.TemporaryDirectory(prefix='doctor-options-input-audit-') as directory:expected=asymmetric_stimulus(Path(directory)/'input.wav')
 input_wav=out/'doctor-asymmetric-input.wav';require(digest(input_wav)==row['stimulus_sha256']==expected,'Public asymmetric ADC input changed')
 job=read(out/'audio-result.json');require(job.get('status')=='complete' and job.get('seconds')==29 and job.get('input_sha256')==expected,'Actual native ADC job differs')
 frozen_job=out/'native/audio-captures'/job['job_id'];require(read(frozen_job/'result.json')==job and digest(frozen_job/'input.wav')==expected,'ADC native input/result binding differs')
 require(job['finished']['frames']==job['finished']['expected_frames']==29*48000 and all(job['finished'].get(k)==0 for k in ('xruns','nonfinite','server_dead')),'Native ADC frame/quality failure')
 require(digest(frozen_job/'output.wav')==job['sha256'],'Native ADC output hash differs')
 wavs=list((out/'rhythm-doctor-captures').glob('*.wav'));require(len(wavs)==1 and digest(wavs[0])==row['captured_sha256'],'Doctor must use exact owned softcut capture')
 rate,channels=read_softcut_pcm(wavs[0]);require(len(channels[0])>=24*rate,'Short actual Doctor recording');signal=check_selected_channels(channels,rate,selection)
 envelopes=[read(path) for path in (out/'rhythm-doctor-analysis-runtime/results').glob('*.json')];envelopes=sorted((v for v in envelopes if v.get('status')=='COMPLETED'),key=lambda v:v['analysis_revision'])
 require(len(envelopes)==(4 if report['case']=='manual_right' else 1),'Unexpected local analysis revision inventory')
 for envelope in envelopes:
  require(envelope.get('command')=='ANALYSE' and envelope.get('wav_sha256')==row['captured_sha256'] and envelope.get('frames')==len(channels[0]) and envelope.get('sample_rate')==rate,'Analysis does not bind the same actual PCM')
  detector=envelope['analysis']['detector'];require(detector.get('backend_id')=='nmf-pfnmf-drums-v1','Analysis is not the default local backend')
  for name,file in [('backend_sha256','tools/rhythm_doctor/rd_analysis_backend.c'),('template_sha256','tools/rhythm_doctor/data/nmf_drum_templates.bin')]:require(detector.get(name)==digest(Path(source['app'])/file)==digest(ROOT/file),'Local detector source/template differs')
 require(row['analysis']==envelopes[0]['analysis'],'Changed original ADC analysis acceptance')
 analysis=row['analysis'];require(analysis.get('tempo_mode')==mode,'Analysis tempo mode differs')
 if mode=='manual':require(analysis.get('bpm')==100 and analysis.get('origin_sample')==0,'Manual tempo/origin differs')
 else:require(analysis.get('tempo_detected') is True and 40<=analysis.get('bpm',0)<=240,'Auto ignored actual tempo detection')
 if report['case']=='manual_right':
  retained=[v for v in results if v.get('kind')=='doctor-retained-alignment'];require(len(retained)==1 and retained[0].get('passed') is True and retained[0].get('initial_bpm')==100 and retained[0].get('confirmed_bpm')==120,'Missing retained alignment acceptance')
  require(envelopes[1]['analysis_revision']==envelopes[0]['analysis_revision']+1 and envelopes[1]['analysis']['bpm']==120 and envelopes[1]['analysis']['tempo_mode']=='manual' and retained[0]['analysis']==envelopes[1]['analysis'] and retained[0]['captured_sha256']==row['captured_sha256'],'Retained correction did not analyse same WAV at120')
  check_manual_start_beat(envelopes,results,row['captured_sha256'])
  visible_sequence(out,observations,[('R06','Exact BPM','120'),('R06','Half tempo','100'),('R06','Exact BPM','120'),('R06','Half tempo','120')])
 steps=row['preview_steps'];require(len(steps)>=2 and sorted(set(steps))==steps,'Missing actual preview gates')
 preview=next((i for i,o in enumerate(observations) if [j+1 for j,v in enumerate(o['state']['grid'][48:112]) if v in (12,15)]==steps),None);require(preview is not None,'Missing exact native Doctor preview')
 require(any([j+1 for j,v in enumerate(o['state']['grid'][48:112]) if v==15]==steps for o in observations[preview:]),'Paint commit differs from exact preview')
 events=[json.loads(line) for line in (out/'native/native-events.jsonl').read_text().splitlines()];packets=native_midi_window(events,row['midi_start_index'],row['midi_end_index'],'real-time');notes=[p for p in packets if 144<=p['bytes'][0]<=159 and p['bytes'][2]>0]
 keys=('index','device_id','port','port_name','monotonic_ns','bytes','decoded');require([{key:p[key] for key in keys} for p in notes]==row['notes'],'ADC accepted notes differ from exact native packet window')
 transport=check_adc_playback_horizon(events,packets)
 expected_phrase=[[p['port'],p['bytes']] for p in notes[:len(steps)]];phrase=check_phrase(packets,steps,expected_phrase,'real-time',stop_time_ns=bind_public_stop(events,packets,'real-time')['stop_time_ns'])
 return dict(input_selection=selection,mode=mode,pcm_frames=len(channels[0]),signal=signal,analysis_revisions=len(envelopes),phrase=phrase,transport=transport,captured_sha256=row['captured_sha256'])


def check_native_observations(events,observations):
 frame_hashes={value['sha256'] for value in events if value.get('kind')==1};grids={tuple(value['leds']) for value in events if value.get('kind')==2}
 require(bool(frame_hashes) and bool(grids),'Missing actual native framebuffer/grid events')
 for item in observations:
  state=item['state'];pixels=base64.b64decode(state['frame']['pixels_base64'])
  require(len(pixels)==32768 and hashlib.sha256(pixels).hexdigest()==state['frame']['sha256'] and state['frame']['sha256'] in frame_hashes and tuple(state['grid']) in grids,'Doctor observation lacks exact native frame/grid event')

def check_playing_record_refusal(results,observations,recipe,events,fixture,clock,out):
 rows=[row for row in results if row.get('kind')=='doctor-options' and row.get('check')=='playing-record-refused'];require(len(rows)==1,'Missing exact playing Record refusal');row=rows[0]
 require(row.get('route')=='R05' and row.get('released') is True and row.get('bank_bpm')==fixture['bank_bpm'] and row.get('steps')==fixture['masks_by_sensitivity']['0.5'],'Playing Record changed original bank tempo/mask')
 names=['pre_play','held_record','released_record','post_stop_mask','stopped_bpm','end'];receipts=row.get('witnesses',{});require(set(receipts)==set(names),'Missing exact playing Record refusal witnesses');states={};stamps=[];indices=[];prefixes=[]
 for name in names:
  receipt=receipts[name];index=receipt.get('observation_index');prefix=receipt.get('recipe_index');require(type(index)is int and 0<=index<len(observations) and type(prefix)is int and 0<=prefix<=len(recipe),'Invalid refusal observation/public recipe index')
  observation=observations[index];state=observation['state'];require(receipt.get('state_sha256')==canonical_hash(state) and receipt.get('frame_sha256')==state['frame']['sha256'],'Changed exact refusal native state/frame receipt')
  pixels=base64.b64decode(state['frame']['pixels_base64']);require(len(pixels)==32768 and hashlib.sha256(pixels).hexdigest()==receipt['frame_sha256'] and any(e.get('kind')==1 and e.get('sha256')==receipt['frame_sha256'] for e in events) and any(e.get('kind')==2 and e.get('leds')==state['grid'] for e in events),'Refusal lacks actual native frame/grid')
  states[name]=state;stamps.append(observation['monotonic_ns']);indices.append(index);prefixes.append(prefix)
 require(indices==sorted(set(indices)) and all(a<b for a,b in zip(stamps,stamps[1:])) and prefixes==sorted(prefixes),'Unordered refusal observation/input witnesses')
 # Only actual public edges establish held/running state; cached Play LED art
 # and state.held (which does not expose grid holds) are not transport oracles.
 wanted=[dict(type='grid',x=1,y=y,state=z) for y,z in [(8,1),(8,0),(2,1),(2,0),(8,1),(8,0)]]
 actual=[r for r in recipe[prefixes[0]:prefixes[3]] if r.get('type')=='grid' and (r.get('x'),r.get('y')) in ((1,8),(1,2))];require(actual==wanted,'Missing exact public Play/Record/Stop recipe edges')
 edges=[e for e in events if e.get('kind')=='input' and e.get('type')==3 and e.get('args',[])[:2] in ([0,7],[0,1]) and stamps[0]<e['monotonic_ns']<=stamps[3]]
 require([e['args'] for e in edges]==[[0,y-1,z] for y,z in [(8,1),(8,0),(2,1),(2,0),(8,1),(8,0)]],'Missing exact native public Play/Record/Stop edges')
 require(edges[2]['monotonic_ns']<=stamps[1]<edges[3]['monotonic_ns']<=stamps[2]<edges[4]['monotonic_ns']<=edges[5]['monotonic_ns']<=stamps[3],'Record held/released frames do not bracket actual native input edges')
 for i,end,state in [(1,3,1),(2,4,0)]:
  record=[r for r in recipe[prefixes[0]:prefixes[i]] if r.get('type')=='grid' and (r.get('x'),r.get('y'))==(1,2)];require(record==[dict(type='grid',x=1,y=2,state=z) for z in ([1] if state else [1,0])],'Refusal frame public prefix differs from held/released Record')
 kind=11 if clock=='controlled-experimental' else 3
 require(any(e.get('kind')==kind and e.get('port')==1 and len(e.get('bytes',[]))==3 and 144<=e['bytes'][0]<=159 and e['bytes'][2]>0 and edges[0]['monotonic_ns']<=e['monotonic_ns']<edges[4]['monotonic_ns'] for e in events),'Refusal lacks actual running musical output')
 from ui_map import RHYTHM_DOCTOR_SCREEN
 for name,route,label,value in [('held_record','R05','Alignment','OPEN >'),('released_record','R05','Alignment','OPEN >'),('stopped_bpm','R06','Half tempo',str(fixture['bank_bpm']))]:
  title,layout=RHYTHM_DOCTOR_SCREEN['screens'][route];verify_cached_ui(states[name],dict(literal_header=[title,'CH01',layout],field=dict(layout=layout,label=label,value=value,art=True)),out)
 for name in ('pre_play','post_stop_mask','end'):
  require([i+1 for i,v in enumerate(states[name]['grid'][48:112]) if v==15]==row['steps'] and states[name]['midi_capture']['outstanding']==[] and states[name]['held']==[],'Record refusal changed original stopped mask or left active inputs/notes')
 return dict(passed=True,bank_bpm=fixture['bank_bpm'],steps=row['steps'],native_edges=6,held_released_frames=True,musical_transport=True)

def audit_ready_witnesses(out,report,results,observations,fixture):
 rows=[row for row in results if row.get('kind')=='doctor-ready-playback'];require([row.get('id') for row in rows]==['replace-policy','live-preview-commit','clear-keeps-pattern'],'READY needs three exact scoped playback witnesses')
 events=[json.loads(line) for line in (out/'native/native-events.jsonl').read_text().splitlines()];checked=[]
 for row in rows:
  require(row.get('passed') is True and row.get('complete_cycles')==2 and row.get('outstanding_notes')==[] and row.get('expectedphrase')==fixture['midi_expected'],'Changed READY playback witness contract')
  packets=native_midi_window(events,row['midi_start_index'],row['midi_end_index'],report['clock_mode']);notes=[p for p in packets if 144<=p['bytes'][0]<=159 and p['bytes'][2]>0]
  keys=('index','device_id','port','port_name','monotonic_ns','bytes','decoded')+(('logical_ns',) if report['clock_mode']=='controlled-experimental' else ())
  require([{key:p[key] for key in keys} for p in notes]==[{key:p[key] for key in keys} for p in row['attacks']],'READY witness differs from exact native attacks')
  checked.append(check_phrase(packets,fixture['masks_by_sensitivity']['0.5'],fixture['midi_expected'],report['clock_mode'],cycles=2,closing=True,stop_time_ns=bind_public_stop(events,packets,report['clock_mode'])['stop_time_ns']))
 isolation=[row for row in results if row.get('kind')=='doctor-options' and row.get('check')=='lane-sensitivity-isolation'];require(len(isolation)==1 and isolation[0].get('selected_lane')=='BD' and isolation[0].get('bd_sensitivity')==.5 and isolation[0].get('sd_sensitivity')==1 and isolation[0].get('detector_quality_claim') is False,'Missing independent lane sensitivity acceptance')
 browse=[row for row in results if row.get('kind')=='doctor-options' and row.get('check')=='browse-gesture'];require(len(browse)>=8,'Missing Doctor tap/held/boundary browse coverage')
 for row in browse:
  require(type(row.get('held'))is bool and 0<=row['window_start']<=fixture['window_max'] and bool(row.get('tooltip')),'Invalid Doctor browse receipt')
  visible_sequence(out,observations,[('R05','Window step',str(row['window_start']+1))])
  require(any(doctor_tooltip_matches(observation['state'],row['tooltip'],out) for observation in observations),'Missing actual Doctor browse feedback')
 refusal=check_playing_record_refusal(results,observations,read(out/'recipe.json'),events,fixture,report['clock_mode'],out)
 return dict(scoped_phrases=checked,browse_gestures=len(browse),lane_isolation=True,playing_record_refusal=refusal)
def doctor_tooltip_matches(state,text,out):
 try:verify_cached_ui(state,dict(doctor_tooltip=text),out);return True
 except ValueError:return False

def adc_checkpoint_contract(case):
 require(case in ('manual_stereo','auto_left','manual_right'),'Unsupported ADC documentation role')
 selection={'manual_stereo':'STEREO','auto_left':'L','manual_right':'R'}[case]
 expected=[('setup-manual-bpm',dict(route='R01',label='Manual BPM',value='100')),('setup-input-source',dict(route='R01',label='Input',value=selection)),('window-lower-row',dict(route='R05',label='Alignment',value='OPEN >')),('alignment-lower-row',dict(route='R06',label='Fine start',value='0ms'))]
 if case=='manual_right':expected +=[(key,dict(route='R06',label=label,value=value)) for key,label,value in [('alignment-edited-then-cancelled','Exact BPM','120'),('alignment-confirmed-draft','Exact BPM','120'),('alignment-reanalysis-ready','Half tempo','120')]]
 if case=='manual_right':expected +=[(key,dict(route=route,label=label,value=value)) for key,route,label,value in [('start-beat-original1','R06','Start beat','1'),('start-beat-next2','R06','Start beat','2'),('start-beat-next-ready','R05',None,None),('start-beat-restore1','R06','Start beat','1'),('start-beat-restored-ready','R05',None,None)]]
 return expected

def check_checkpoint_pixels(frame,observations,out):
 from ui_map import RHYTHM_DOCTOR_SCREEN
 contract=frame['expect'];title,layout=RHYTHM_DOCTOR_SCREEN['screens'][contract['route']];expected=dict(literal_header=[title,'CH01',layout])
 if contract['label'] is not None:expected['field']=dict(layout=layout,label=contract['label'],value=str(contract['value']),art=True)
 for observation in observations:
  state=observation['state']
  if state['frame']['sha256']!=frame['output']['binding']['sha256'] or state['grid']!=frame['output']['grid']:continue
  try:verify_cached_ui(state,expected,out);return
  except ValueError:pass
 raise ValueError('Doctor checkpoint selector differs from its own bound native frame')

def audit_report(path,case,clock,fixture=None):
 path=Path(path).resolve();require(path.name=='report.json','Doctor report must be explicit original report.json');out=path.parent;report=read(path);check_scope(report,case,clock)
 require(not (out/'diagnostic-only.json').exists(),'Diagnostic Doctor report cannot qualify');require(report.get('harness_changed')==[],'Doctor harness mutation/missing final source guard')
 source=check_sources(out,report);require(read(out/'native/native-config.json').get('clock_mode')==clock,'Actual native Doctor clock differs')
 results=read(out/'results.json');observations=read(out/'observations.json');check_qualification_registration(out,report,source,results);require(observations and not any(row.get('passed') is False or row.get('matched') is False for row in results),'Missing/failed Doctor semantic results')
 cleanup=read(out/'native/cleanup.json');require(cleanup and all(row.get('returncode') in ((0,-15) if row.get('service') in ('sclang','crow') else (0,)) for row in cleanup),'Doctor native cleanup failed')
 final=observations[-1]['state'];require(final.get('held')==[] and final['midi_capture']['outstanding']==[],'Doctor cleanup left held inputs/notes')
 events=[json.loads(line) for line in (out/'native/native-events.jsonl').read_text().splitlines()];check_native_input_trace(read(out/'recipe.json'),events);check_native_observations(events,observations)
 require(all(item['state']['clock']['mode']==clock for item in observations),'Doctor observed clock differs')
 frames=report.get('checkpoints',[])
 if case not in ('setup_options','ready_options'):
  expected=adc_checkpoint_contract(case)
  require([(frame['id'],frame['expect']) for frame in frames]==expected,'Missing exact Doctor lower-row/alignment checkpoints')
 for frame in frames:
  start_beat=frame['id'].startswith('start-beat-');semantic_kind='doctor-start-beat-checkpoint' if start_beat else 'doctor-options-checkpoint'
  semantic=[row for row in results if row.get('kind')==semantic_kind and row.get('id')==frame['id']];require(len(semantic)==1 and semantic[0].get('expected')==frame['expect'] and semantic[0].get('passed') is True,'Doctor documentation semantic binding differs')
  check_frame(frame['output'],'DOCTOR-START-BEAT' if start_beat else 'DOCTOR-OPTIONS',results,observations);require(results.index(semantic[0])<results.index(frame['output']['binding']),'Doctor frame precedes semantic assertion')
  check_checkpoint_pixels(frame,observations,out)
  visible_sequence(out,observations,[(frame['expect']['route'],frame['expect']['label'],frame['expect']['value'])])
 if case=='ready_options':
  require(isinstance(fixture,tuple) and len(fixture)==3,'READY audit requires explicit fixture/pathSHA/ManualRight report')
  qualified,proof=audit_fixture(*fixture)
  require(report.get('ready_fixture')==dict(path=qualified['_path'],sha256=qualified['_sha256']),'READY report fixture pointer differs');prelaunch=read(out/'fixture-prelaunch.json');seed=out/'frozen-project-seed'
  require(prelaunch.get('passed') is True and prelaunch.get('phase')=='before-native-startup' and prelaunch.get('fixture')==qualified['_path'] and prelaunch.get('fixture_sha256')==qualified['_sha256'],'Missing READY prelaunch qualification receipt')
  for key in ('acquisition_report','acquisition_report_sha256','geometry_receipt','geometry_receipt_sha256','saved_project_sha256'):require(prelaunch.get(key)==qualified[key],'READY prelaunch provenance differs '+key)
  require(Path(prelaunch['project_seed']).resolve()==seed.resolve() and prelaunch['project_seed_files']==source['project_seed_files']==qualified['project_seed_files']==seed_files(seed),'READY frozen seed bytes differ')
  require(read(out/'session.json').get('data_seeds')==[dict(source=str(seed),destination='mosaic')],'Actual native session did not use qualified seed')
  detail=audit_ui(out,report,results,observations,qualified);detail['scoped']=audit_ready_witnesses(out,report,results,observations,qualified)
 elif case=='setup_options':detail=audit_ui(out,report,results,observations)
 else:detail=audit_adc(out,report,results,observations,source)
 return dict(passed=True,case=case,clock_mode=clock,report=str(path),report_sha256=digest(path),source_sha256=digest(out/'source.json'),results_sha256=digest(out/'results.json'),native_identity_sha256=digest(out/'native/identity.json'),native_events_sha256=digest(out/'native/native-events.jsonl'),frames=len(frames),detail=detail,complete_regression_run=False,hardware_timing_equivalent=False)

def audit_fixture(path,sha,parent_report):
 path=Path(path).resolve();parent_report=Path(parent_report).resolve();require(digest(path)==sha,'READY fixture SHA differs');fixture=read(path);check_fixture_contract(fixture)
 require(path==parent_report.parent/'ready-fixture/fixture.json' and Path(fixture['acquisition_report']).resolve()==parent_report and fixture['acquisition_report_sha256']==digest(parent_report),'READY fixture lacks exact ManualRight parent')
 parent_audit=audit_report(parent_report,'manual_right','real-time')
 source=read(parent_report.parent/'source.json');require(source['harness_files']['tools/doctor_ready_fixture.py']==digest(ROOT/'tools/doctor_ready_fixture.py'),'Stale READY fixture exporter')
 receipt_path=Path(fixture['geometry_receipt']).resolve();require(receipt_path==path.parent/'geometry-receipt.json' and digest(receipt_path)==fixture['geometry_receipt_sha256'],'READY geometry receipt differs');receipt=read(receipt_path);draft_path=path.parent/'acquisition.json';draft=read(draft_path)
 require(receipt.get('passed') is True and receipt.get('kind')=='doctor-saved-project-geometry' and receipt.get('acquisition_report_sha256')==digest(parent_report) and receipt.get('acquisition_receipt_sha256')==digest(draft_path),'READY geometry provenance differs')
 seed=path.parent/'project-seed';require(Path(fixture['project_seed']).resolve()==seed.resolve() and Path(fixture['saved_project']).resolve()==seed/'autosave.ptn','READY autosave path differs')
 files=seed_files(seed);require(files==fixture['project_seed_files']==receipt['project_seed_files']==draft['project_seed_files'] and files['autosave.ptn']==fixture['saved_project_sha256']==receipt['saved_project_sha256']==draft['saved_project_sha256'],'READY saved seed/config bytes changed')
 from doctor_ready_fixture import saved_geometry
 geometry=saved_geometry(seed/'autosave.ptn');require(geometry==receipt['geometry']==draft['geometry'],'READY geometry not derived from actual saved graph')
 for key in ('bank_bpm','window_max','beat_count'):require(fixture[key]==geometry[key],'READY scalar geometry differs '+key)
 require(receipt['observations']==draft['observations']==dict(masks_by_sensitivity=fixture['masks_by_sensitivity'],midi_expected=fixture['midi_expected']),'READY observed masks/MIDI changed')
 require(draft.get('kind')=='doctor-ready-fixture-acquisition' and draft.get('passed') is True and draft.get('project_seed_origin')==receipt.get('project_seed_origin')==ORIGIN and draft.get('retained_audio') is False and draft.get('recipe_sha256')==receipt.get('recipe_sha256')==digest(ROOT/'tools/doctor_ready_fixture.py'),'READY exporter/acquisition contract differs')
 results=read(parent_report.parent/'results.json');observations=read(parent_report.parent/'observations.json');events=[json.loads(line) for line in (parent_report.parent/'native/native-events.jsonl').read_text().splitlines()]
 bindings=[row for row in results if row.get('kind')=='doctor-ready-fixture-acquisition'];require(len(bindings)==1 and bindings[0].get('passed') is True and bindings[0]['receipt_sha256']==digest(draft_path),'READY acquisition result binding differs')
 backend=next(row for row in results if row.get('kind')=='doctor-backend-options');alignment=next(row for row in results if row.get('kind')=='doctor-retained-alignment');envelopes=sorted((read(path) for path in (parent_report.parent/'rhythm-doctor-analysis-runtime/results').glob('*.json') if read(path).get('status')=='COMPLETED'),key=lambda value:value['analysis_revision']);analysis=check_manual_start_beat(envelopes,results,backend['captured_sha256']);require(draft['captured_sha256']==backend['captured_sha256']==alignment['captured_sha256'],'READY fixture lost retained actual WAV')
 require(geometry['bank_bpm']==analysis['bpm'] and geometry['origin_sample']==analysis['origin_sample'] and geometry['beat_count']==len(analysis['beat_positions']) and geometry['window_start']==0 and geometry['sample_rate']==48000 and geometry['samples_per_cell']==48000*60/geometry['bank_bpm']/4,'READY bank alignment differs from recorded analysis')
 originals=list((parent_report.parent/'data').rglob('autosave.ptn'));require(len(originals)==1 and digest(originals[0])==files['autosave.ptn'],'Seed is not actual application autosave export')
 frame_map={frame['id']:frame for frame in draft['frames']};required={'window-low','preview-0','preview-0.5','preview-1','paint-p3','full64-midi','full64-midi-release','blank-destinations','window-high-confirmed'};require(set(frame_map)==required and len(frame_map)==len(draft['frames']),'Incomplete or duplicate READY acquisition frames')
 for frame in draft['frames']:check_frame(frame['output'],'DOCTOR-READY-FIXTURE',results,observations)
 for level in ('0','0.5','1'):
  frame=frame_map['preview-'+level];require(frame['expected']['steps']==fixture['masks_by_sensitivity'][level] and [i+1 for i,v in enumerate(frame['output']['grid'][48:112]) if v in (12,15)]==fixture['masks_by_sensitivity'][level],'READY sensitivity mask not actually observed')
 require([i+1 for i,v in enumerate(frame_map['paint-p3']['output']['grid'][48:112]) if v==15]==fixture['masks_by_sensitivity']['0.5'],'READY fixture paint differs from preview')
 high=frame_map['window-high-confirmed'];visible_sequence(parent_report.parent,observations,[('R05','Window step',str(geometry['window_max']+1))]);require(high['expected']['window_max']==geometry['window_max'],'READY public bound differs')
 full=frame_map['full64-midi']['expected'];require(full['expected']==fixture['midi_expected'] and full['steps']==fixture['masks_by_sensitivity']['0.5'],'READY full phrase expectation changed')
 # The original pre-Stop frame stays immutable. The NEW endpoint records the
 # real post-Stop release. No open-closing exception or packet-count reduction.
 endpoint=draft['playback_release'];require(endpoint==receipt['playback_release']==frame_map['full64-midi-release']['expected'] and endpoint['outstanding_notes']==[] and endpoint['midi_start_index']==full['midi_start_index'] and endpoint['midi_end_index']>=full['midi_end_index'],'READY release endpoint provenance differs')
 packet_rows=native_midi_window(events,endpoint['midi_start_index'],endpoint['midi_end_index'],'real-time');keys=('index','device_id','port','port_name','monotonic_ns','bytes','decoded')
 recorded=[{key:value[key] for key in keys} for value in endpoint['packets'] if len(value.get('bytes',[]))==3];require([{key:value[key] for key in keys} for value in packet_rows]==recorded,'READY release endpoint differs from actual native packets')
 attacks=[value for value in packet_rows if value['bytes'][0]==144 and value['bytes'][2]>0];closing=attacks[-1];require(endpoint['closing_attack_index']==closing['index'] and {key:endpoint['closing_attack'][key] for key in keys}=={key:closing[key] for key in keys},'READY closing attack differs')
 release_rows=[value for value in packet_rows if value['index']>closing['index'] and value['port']==closing['port'] and value['bytes'] in ([128,closing['bytes'][1],closing['bytes'][2]],[128,closing['bytes'][1],0])]
 require(release_rows and [{key:value[key] for key in keys} for value in release_rows]==[{key:value[key] for key in keys} for value in endpoint['closing_releases']],'Missing exact native closing note-off')
 release_semantic=[row for row in results if row.get('kind')=='doctor-ready-fixture-playback-release'];require(len(release_semantic)==1 and release_semantic[0].get('passed') is True and all(release_semantic[0].get(key)==value for key,value in endpoint.items()),'READY release semantic row differs')
 phrase=check_phrase(packet_rows,full['steps'],full['expected'],'real-time',cycles=2,closing=True,stop_time_ns=bind_public_stop(events,packet_rows,'real-time')['stop_time_ns'])
 fixture.update(_path=str(path),_sha256=sha)
 return fixture,dict(passed=True,fixture=str(path),fixture_sha256=sha,parent_report_sha256=parent_audit['report_sha256'],saved_project_sha256=files['autosave.ptn'],geometry=geometry,phrase=phrase)

def audit_qualification(reports,fixture,fixture_sha256):
 check_roles(reports);report_checks={}
 for role in ('manual_stereo','auto_left','manual_right','setup_real','setup_controlled'):
  case,clock=ROLES[role];report_checks[role]=audit_report(reports[role],case,clock)
 qualified,fixture_check=audit_fixture(fixture,fixture_sha256,reports['manual_right'])
 for role in ('ready_real','ready_controlled'):
  case,clock=ROLES[role];report_checks[role]=audit_report(reports[role],case,clock,(Path(fixture),fixture_sha256,Path(reports['manual_right'])))
 for role,checked in report_checks.items():require(digest(reports[role])==checked['report_sha256'],'Doctor report changed during whole qualification')
 require(digest(fixture)==fixture_sha256,'READY fixture changed during qualification')
 return dict(passed=True,roles=report_checks,fixture=fixture_check,real_adc_sessions=3,ui_sessions=4,complete_regression_run=False,hardware_timing_equivalent=False,controlled_audio=dict(applicable=False,reason='Actual ADC/softcut acquisition requires real-time audio'))
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 for role in ROLES:parser.add_argument('--'+role.replace('_','-')+'-report',required=True,type=Path)
 parser.add_argument('--fixture',required=True,type=Path);parser.add_argument('--fixture-sha256',required=True);parser.add_argument('--output',type=Path);options=parser.parse_args()
 reports={role:getattr(options,role+'_report') for role in ROLES};report=audit_qualification(reports,options.fixture,options.fixture_sha256)
 if options.output:
  with options.output.open('x') as target:target.write(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())

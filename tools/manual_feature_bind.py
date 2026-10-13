"""Bind reviewed manual features to audited, freshly built native publications.

Only scene_refs and review metadata may change. This is scoped documentation
evidence; it never establishes exhaustive behaviour or hardware acceptance.
"""
import argparse,copy,hashlib,json,os,sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
MAPPINGS={
 'merge-modes':['shared-merge-strategy-workflow','note-merge-numeric-output','velocity-merge-numeric-output','length-merge-numeric-output'],
 'trig-merge-modes':['shared-merge-strategy-workflow','workflow-compose-two-channels','merge-shape-skip-shared-step'],
 'musical-merge-and-voice-leading':['shared-merge-strategy-workflow','foundation-protected-and-added','harmony-revoice-two-voices'],
 'merge-shape':['shared-merge-strategy-workflow','foundation-protected-and-added','foundation-two-cycle-build','merge-shape-owns-trigs','merge-shape-skip-shared-step'],
 'fragments':['shared-merge-strategy-workflow','fragments-seed-source-choice'],
 'lock-lead-time':['lock-lead-menu-values'],
 'midi-panic':['panic-from-song-channel','panic-from-song-pattern','panic-stops-sounding-note'],
 'arm-live-record':['record-keyboard-steps'],
 'rhythm-doctor':['doctor-local-capture-and-paint','doctor-local-auto-capture-and-paint'],
 'clocks-swing-and-shuffle':['swing-interlock-pulse-times','vertical-clock-neighbors','shuffle-smooth-amount-boundaries'],
 'button-indicators':['song-slot-light-states'],
 'navigating-the-norns-display':['public-display-readability','song-slot-repeat-values','song-repeats-advance','song-tempo-across-slots','song-global-length','vertical-clock-neighbors'],
 'save-and-load':['named-project-roundtrip'],
 'reset-at-song-editor-pattern-change':['song-change-reset-policies','polymeter-song-reset'],
 'reset-at-pattern-repeat':['repeat-reset-policies','repeat-reset-first-boundary-public'],
 'snap-note-masks-to-scale':['snap-note-masks-public-pair'],
 'lfos-and-modulation':['matrix-macro-route-clear','toolkit-clocked-lfo-menu','matrix-macro-modest-cc'],
 'trigless-locks':['trigless-locks-on','trigless-locks-off'],
 'lock-all-to-pentatonic':['pentatonic-snap-all'],
 'lock-random-to-pentatonic':['random-pentatonic-on','random-pentatonic-off'],
 'lock-merged-to-pentatonic':['merged-pentatonic-on','merged-pentatonic-off'],
 'honor-scale-rotations':['keyboard-honour-degree-rotation'],
 'honor-scale-degree':['keyboard-honour-degree'],
 'honour-scale-transpose':['keyboard-honour-all'],
 'screen-options':['screen-motion-on-and-off','public-display-readability'],
 'ui-motion':['screen-motion-on-and-off','public-display-readability','ui-motion-public-frames'],
 'result-and-reason':['reason-ordered-rejections'],
 'build-a-phrase':['workflow-patterns-and-scale','workflow-second-channel','workflow-song-chain'],
 'chord-acceleration':['chord-acceleration-termination','chord-acceleration-slowing'],
 'fully-quantise-mask':['full-quantisation-precedence','full-quantisation-inherit-and-step-off','full-quantisation-channel-beats-global'],
 'loops-that-meet':['loops-four-against-three','loops-sixteen-against-five'],
 'note-dashboard':['output-dashboard-readout','output-channel-selection','output-latest-event'],
 'pocket-rhythm':['pocket-ghost-bar'],
 'scale-editor':['scale-edit-versus-apply','scale-save-d-and-apply'],
 'scale-locks':['scale-lock-scope-and-lifetime','scale-lock-skipped-trig','scale-lock-replacement'],
 'song-mode-operations':['song-mode-groups-and-selection','song-build-two-groups'],
 'structure':['structure-anchor-chord-and-delete','structure-every-4-markers'],
 'transposition':['transpose-next-onset','transpose-song-slot-copy'],
 'transposition-locks':['transpose-explicit-zero-and-clear','transpose-lock-direct-taps'],
 'mods-and-software-devices':['player-apply-oilcan','player-apply-polyperc','player-apply-doubledecker'],
}
EXPECTED_CASES={'public-display-readability':'M-UI-READABILITY-001','shared-merge-strategy-workflow':'M-MERGE-STRATEGY-001','foundation-protected-and-added':'M-MERGE-FOUNDATION-001','foundation-two-cycle-build':'M-MERGE-PHRASE-001','fragments-seed-source-choice':'M-MERGE-FRAGMENTS-001','harmony-revoice-two-voices':'M-HARMONY-REVOICE-001','workflow-compose-two-channels':'M-WORKFLOW-001','note-merge-numeric-output':'M-MERGE-009','velocity-merge-numeric-output':'M-MERGE-020','length-merge-numeric-output':'M-MERGE-025','lock-lead-menu-values': 'M-SYNC-LEAD-002', 'panic-from-song-channel': 'M-PANIC-001', 'panic-from-song-pattern': 'M-PANIC-002', 'record-keyboard-steps': 'M-REC-001', 'doctor-local-capture-and-paint': 'MA-DOCTOR-AUDIO-001', 'doctor-local-auto-capture-and-paint': 'MA-DOCTOR-AUDIO-001', 'swing-interlock-pulse-times': 'M-MANUAL-SWING-001', 'vertical-clock-neighbors': 'M-UI-VERTICAL-001', 'shuffle-smooth-amount-boundaries': 'M-SHUFFLE-002', 'song-slot-light-states': 'M-MANUAL-CLOSURE-SONG-001', 'song-slot-repeat-values': 'M-MANUAL-CLOSURE-SONG-001', 'song-repeats-advance': 'M-MANUAL-CLOSURE-SONG-002', 'panic-stops-sounding-note': 'M-MANUAL-CLOSURE-PANIC-001', 'song-tempo-across-slots': 'M-SONG-SETTINGS-002', 'song-global-length': 'M-LIVEUI-FOCUS-001', 'named-project-roundtrip': 'M-SAVE-NAMED-001', 'song-change-reset-policies': 'M-TIME-005', 'repeat-reset-policies': 'M-TIME-003', 'trigless-locks-on': 'M-PARAM-022', 'trigless-locks-off': 'M-PARAM-023', 'pentatonic-snap-all': 'M-OPT-PENT-ALL-001', 'random-pentatonic-on': 'M-PARAM-039', 'random-pentatonic-off': 'M-PARAM-037', 'merged-pentatonic-on': 'M-MERGE-011', 'merged-pentatonic-off': 'M-MERGE-010', 'keyboard-honour-degree-rotation': 'M-OPT-KEYS-001', 'keyboard-honour-degree': 'M-OPT-KEYS-001', 'keyboard-honour-all': 'M-OPT-KEYS-001', 'screen-motion-on-and-off': 'M-MANUAL-CLOSURE-MOTION-001', 'reason-ordered-rejections': 'M-MANUAL-REASON-001'}
EXPECTED_CASES.update({
 'workflow-patterns-and-scale':'M-WORKFLOW-001','workflow-second-channel':'M-WORKFLOW-001','workflow-song-chain':'M-WORKFLOW-001',
 'chord-acceleration-termination':'M-CHORDSHAPE-257','chord-acceleration-slowing':'M-CHORDSHAPE-260',
 'full-quantisation-precedence':'M-MASK-021','full-quantisation-inherit-and-step-off':'M-MASK-021','full-quantisation-channel-beats-global':'M-MASK-021',
 'loops-four-against-three':'M-RANGE-REJECT-006','loops-sixteen-against-five':'M-RANGE-LCM-001',
 'merge-shape-owns-trigs':'M-LIVEUI-SHAPETRIG-001','merge-shape-skip-shared-step':'M-LIVEUI-SHAPETRIG-002',
 'output-dashboard-readout':'M-LIVEUI-DASH-001','output-channel-selection':'M-DASHBOARD-SELECT-001','output-latest-event':'M-UIACC-A19-001',
 'pocket-ghost-bar':'M-MANUAL-CLOSURE-GHOST-001','polymeter-song-reset':'M-MANUAL-CLOSURE-RESET-001',
 'scale-edit-versus-apply':'M-SCALE-001','scale-save-d-and-apply':'M-SCALE-001',
 'scale-lock-scope-and-lifetime':'M-SCALE-LOCK-003','scale-lock-skipped-trig':'M-SCALE-LOCK-003','scale-lock-replacement':'M-SCALE-LOCK-003',
 'song-mode-groups-and-selection':'M-SONG-FLOW-001','song-build-two-groups':'M-SONG-FLOW-001',
 'structure-anchor-chord-and-delete':'M-MERGE-STRUCTURE-001','structure-every-4-markers':'M-MERGE-STRUCTURE-004',
 'transpose-next-onset':'M-TRANS-009','transpose-song-slot-copy':'M-TRANS-010',
 'transpose-explicit-zero-and-clear':'M-TRANS-001','transpose-lock-direct-taps':'M-TRANS-011',
 'player-apply-oilcan':'M-MANUAL-PLAYER-APPLY-001','player-apply-polyperc':'M-MANUAL-PLAYER-APPLY-001','player-apply-doubledecker':'M-MANUAL-PLAYER-APPLY-001',
 'matrix-macro-modest-cc':'M-MANUAL-MODULATION-001',
 'repeat-reset-first-boundary-public':'M-MANUAL-RESET-REPEAT-PUBLIC-001',
 'snap-note-masks-public-pair':'M-MANUAL-SNAP-MASK-PUBLIC-001',
 'ui-motion-public-frames':'M-MANUAL-UI-MOTION-FRAME-001',
})
SCOPES={
 'merge-modes':'Shared Strategy grid/encoder selection, accepted/pending/refused state, retained inactive attribute modes and exact current note/velocity/length arithmetic.',
 'trig-merge-modes':'Shared five-choice Strategy navigation, legacy Skip/All composition and exact Foundation/Fragments/current-to-next-cycle output; Only emits exact silence for disjoint sources.',
 'musical-merge-and-voice-leading':'Shared Strategy ownership, parameter-draft discard, Foundation controls and exact musical output, plus Harmony revoicing through current public UI.',
 'merge-shape':'Shared Strategy ownership/refusal/cycle handoff, read-only Merge Shape summary and parameter-draft discard, Foundation accent and two-cycle Build output.',
 'fragments':'Shared Fragments selection, inactive retained merge settings/restoration, seed-specific fragment source output and native current editor workflow.', 
 'lock-lead-time':'Selected native lead-time values and independently asserted lock/output scheduling.',
 'midi-panic':'Both Song-page panic gestures, retained page, complete Note Off output accounting and a sounding long note silenced by panic.',
 'arm-live-record':'Live keyboard capture through public inputs with exact recorded notes and playback.',
 'rhythm-doctor':'Manual and Auto real-audio capture, analysis, ready bank, preview and committed painting.',
 'clocks-swing-and-shuffle':'Exact swing/Interlock timing, shuffle amount boundaries and native vertical Clock row/scroll behavior.',
 'button-indicators':'Song-slot copied/selected, playing and erased-copy light states; not every grid indicator.',
 'navigating-the-norns-display':'Native Slot setup repeats, audible Repeats advancing the song, applied Song tempo, Playback global length, Clock list navigation and actual assignment-detail overflow/fitting vertical text readability.',
 'save-and-load':'Named-project round trip and case-defined cancel/rejected-load outcomes.',
 'reset-at-song-editor-pattern-change':'Exact channel reset policies at arrangement changes.',
 'reset-at-pattern-repeat':'Exact channel reset policies at repeat boundaries.',
 'trigless-locks':'On/off automation behavior at rests.',
 'lock-all-to-pentatonic':'Configured all-note pentatonic restriction and exact resulting notes.',
 'lock-random-to-pentatonic':'On/off random-note pentatonic restriction with seeded output.',
 'lock-merged-to-pentatonic':'On/off merged-note pentatonic restriction and exact output.',
 'honor-scale-rotations':'Live keyboard degree/rotation mapping.',
 'honor-scale-degree':'Live keyboard scale-degree mapping.',
 'honour-scale-transpose':'Live keyboard degree/rotation/transpose mapping.',
 'screen-options':'Native UI motion On/Off option, actual assignment-detail marquee, fitting vertical text stability and independently audited unchanged musical output.',
 'ui-motion':'Native UI motion On/Off option, actual assignment-detail marquee, fitting vertical text stability and independently audited unchanged musical output.',
 'result-and-reason':'Exact ordered Reason readouts and associated emitted/suppressed MIDI outcomes.',
}
SCOPES.update({
 'build-a-phrase':'Three current public-input composing workflows: pattern and scale, a second channel and a song chain.',
 'chord-acceleration':'Chord acceleration termination and slowing controls with exact authored output.',
 'fully-quantise-mask':'Precedence, inheritance and channel/global beat-mask behavior for Fully Quantise.',
 'loops-that-meet':'The 4:3 and 16:5 loop relationship scenes with exact authored alignment output.',
 'note-dashboard':'Dashboard output readout, channel selection and latest-event feedback.',
 'pocket-rhythm':'The pocket-rhythm teaching placement, including its ghost-bar grid and MIDI feedback.',
 'scale-editor':'Saved scale creation and the distinction between editing and applying a scale.',
 'scale-locks':'Scale-lock scope, skipped-trig behavior and replacement lifetime.',
 'song-mode-operations':'Song grouping and the authored two-group build workflow.',
 'structure':'Structure anchor selection/deletion and marker cadence.',
 'transposition':'Next-onset transposition and song-slot copy behavior.',
 'transposition-locks':'Explicit zero/clear and direct-tap transposition-lock behavior.',
 'mods-and-software-devices':'Public Device selection, pending K3 confirmation, applied player value, and persistence after reopening the Device page; external mod installation is setup, not captured behavior.',
 'lfos-and-modulation':'Current Matrix source/target/depth and Toolkit Macro 1 setup, exact CC 32-to-38 movement at a modest depth with unchanged four-note phrase, then route-clear restoration to CC 32.',
 'reset-at-pattern-repeat':'Selected Off/On row values and exact MIDI through the first song-repeat boundary, including the expected restart note only when repeat reset is On.',
 'snap-note-masks-to-scale':'Selected Snap option, held-step chromatic mask values, exact C-major snapped pitches when On, and unchanged chromatic pitches when Off.',
 'ui-motion':'Current public UI-motion frames with exact native pixels and unchanged musical output; other motion and hardware claims remain scoped by their own evidence.',
})
STRATEGY_CHECKPOINTS={
 'foundation-active':('merge-strategy-ui','foundation-active'),
 'foundation-phrase':('effective-foundation-musical-result',None),
 'fragments-inactive':('merge-strategy-ui','fragments-inactive'),
 'fragments-phrase':('effective-fragments-musical-result',None),
 'legacy-restored':('merge-strategy-ui','legacy-restored'),
 'only-silence':('effective-only-silence',None),
 'legacy-phrase':('restored-legacy-musical-result',None),
 'unset-anchor-refusal':('merge-strategy-ui','unset-anchor-refusal'),
 'unassigned-anchor-refusal':('merge-strategy-ui','unassigned-anchor-refusal'),
 'pending-cycle':('merge-strategy-ui','pending-cycle'),
 'cycle-handoff':('merge-strategy-next-cycle',None),
 'm02-readonly':('merge-strategy-ui','m02-readonly'),
 'draft-discarded':('merge-strategy-ui','draft-discarded'),
}
READABILITY_ATLAS_SHA256='4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46'
READABILITY_CHECKPOINTS={}
for enabled,suffix in ((False,'off'),(True,'on')):
 READABILITY_CHECKPOINTS['assignment-'+suffix]=dict(kind='public-assignment-marquee',enabled=enabled,label='Quantised Fixed Note',value='CURRENT',passed=True)
 for page,label,value in (('clock','Rate','/1'),('scale','Scale','Major')):
  READABILITY_CHECKPOINTS[page+'-'+suffix]=dict(kind='public-fitting-vertical-text',page=page,enabled=enabled,label=label,value=value,passed=True)
 for page in ('C02','C04','S01','C01'):
  READABILITY_CHECKPOINTS['mini-'+page.lower()+'-'+suffix+'-90']=dict(kind='public-mini-header',page=page,enabled=enabled,tempo=90,pose_count=8,loop_quarter_beats=4 if page=='S01' else 2,all_distinct_poses_required=enabled,atlas_sha256=READABILITY_ATLAS_SHA256,passed=True)
for tempo,allposes in ((40,True),(240,False)):
 READABILITY_CHECKPOINTS['mini-c04-on-'+str(tempo)]=dict(kind='public-mini-header',page='C04',enabled=True,tempo=tempo,pose_count=8,loop_quarter_beats=2,all_distinct_poses_required=allposes,atlas_sha256=READABILITY_ATLAS_SHA256,passed=True)
READABILITY_CHECKPOINTS['stable-overviews-and-music']=dict(kind='public-readability-summary',passed=True)
def verify_readability_scene(scene):
 if scene.get('behaviour_case')!='M-UI-READABILITY-001':raise ValueError('Reviewed readability semantic case changed')
 steps=scene.get('steps',[])
 ids=[step['id'] for step in steps]
 if len(ids)!=len(set(ids)) or not set(READABILITY_CHECKPOINTS)<=set(ids):raise ValueError('Readability requires all seventeen acceptance checkpoints')
 for step in steps:
  assertion=step.get('output',{}).get('binding',{}).get('assertion',{})
  if step['id'] not in READABILITY_CHECKPOINTS:
   # Added teaching checkpoint (e.g. prepared starting point): must bind a passed row.
   if assertion.get('passed') is False or assertion.get('matched') is False or not assertion.get('kind'):raise ValueError('Readability teaching checkpoint must bind a passed row')
   continue
  if any(assertion.get(key)!=value for key,value in READABILITY_CHECKPOINTS[step['id']].items()):raise ValueError('Readability checkpoint literal selector changed')

def verify_reviewed_scene(scene):
 if scene["id"]=="public-display-readability":return verify_readability_scene(scene)
 if scene['id']!='shared-merge-strategy-workflow':return
 if scene.get('behaviour_case')!='M-MERGE-STRATEGY-001':raise ValueError('Reviewed shared Strategy semantic case changed')
 steps=scene.get('steps',[])
 ids=[step['id'] for step in steps]
 if len(ids)!=len(set(ids)) or not set(STRATEGY_CHECKPOINTS)<=set(ids):raise ValueError('Shared Strategy requires all thirteen acceptance checkpoints')
 for step in steps:
  assertion=step.get('output',{}).get('binding',{}).get('assertion',{})
  if step['id'] not in STRATEGY_CHECKPOINTS:
   if assertion.get('passed') is False or assertion.get('matched') is False or not assertion.get('kind'):raise ValueError('Shared Strategy teaching checkpoint must bind a passed row')
   continue
  kind,checkpoint=STRATEGY_CHECKPOINTS[step['id']]
  if assertion.get('kind')!=kind or checkpoint is not None and assertion.get('checkpoint')!=checkpoint or assertion.get('passed') is not True:raise ValueError('Shared Strategy checkpoint semantic selector changed')
  if step['id']=='only-silence' and (assertion.get('loops'),assertion.get('loop_steps'),assertion.get('expected'),assertion.get('actual'))!=(2,8,[],[]):raise ValueError('Shared Strategy Only silence fixture changed')
  if step['id']=='fragments-phrase' and (assertion.get('size'),assertion.get('seed'))!=(8,0):raise ValueError('Shared Strategy fragment literal fixture changed')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def value_sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write_new(path,value):
 with Path(path).open('x') as handle:json.dump(value,handle,indent=2);handle.write('\n')
def auditors():
 from manual_publication_verify import audit_raw_publications,audit_reference,native_source_identity
 return audit_raw_publications,audit_reference,native_source_identity
def stage_reports(build,controlled_local=False):
 if not build.is_dir():raise ValueError('Missing build evidence directory')
 rows=[]
 for path in sorted(build.glob('*.json')):
  record=read(path)
  if not record.get('name','').startswith(('reference-real-','reference-controlled-','doctor-')):continue
  if controlled_local and record.get('name','').startswith('reference-real-'):continue
  if record.get('action') or record.get('name')=='doctor-publish':continue
  if record.get('passed') is not True or record.get('returncode')!=0:raise ValueError('Failed native stage: '+path.name)
  log=build/(record['name']+'.log')
  if not log.is_file() or sha(log)!=record.get('log_sha256'):raise ValueError('Changed native stage log')
  native=record.get('native_report',{});report=Path(native.get('path',''))
  if not report.is_file() or sha(report)!=native.get('sha256'):raise ValueError('Missing or changed native report')
  command=record.get('executed_command',[])
  mode='real-time' if record['name'].startswith(('reference-real-','doctor-')) else 'controlled-experimental'
  if record.get('execution_status')=='adopted-verified':
   # Adopted stages keep a stub log; their parent report is proven through resume-adoption.json.
   import resume_adoption
   prove=resume_adoption.verify_adopted_reference_stage if record['name'].startswith('reference-') else resume_adoption.verify_adopted_doctor_stage
   if record['name'].startswith('reference-') and ('--clock-mode' not in command or command[command.index('--clock-mode')+1]!=mode):raise ValueError('Native stage clock mismatch')
   if prove(build,record['name'],record,ROOT)!=str(report):raise ValueError('Native report differs from adoption proof')
  elif record['name'].startswith('reference-'):
   if '--clock-mode' not in command or command[command.index('--clock-mode')+1]!=mode:raise ValueError('Native stage clock mismatch')
   if report.name!='reference-scenes.json' or log.read_text().splitlines()[-1].strip()!=str(report.parent):raise ValueError('Native report differs from final stage output')
  else:
   try:summary=json.loads(log.read_text().splitlines()[-1])
   except (IndexError,json.JSONDecodeError) as error:raise ValueError('Missing final Doctor result') from error
   if summary.get('passed') is not True or summary.get('report')!=str(report):raise ValueError('Doctor report differs from final stage output')
  document=read(report)
  if document.get('passed') is False or document.get('clock_mode')!=mode or not document.get('scenes'):raise ValueError('Native report failed or clock mismatch')
  if record['name'].startswith('doctor-') and document.get('passed') is not True:raise ValueError('Doctor report failed')
  if document.get('complete_regression_run') is not False:raise ValueError('Native stage claimed exhaustive campaign')
  rows.append(dict(stage=record['name'],stage_path=str(path),stage_sha256=sha(path),log=str(log),log_sha256=sha(log),report=str(report),report_sha256=sha(report),clock_mode=mode,document=document))
 return rows
def catalogue(root):
 scenes={}
 for path in sorted((root/'manual/generated').glob('*.json')):
  if path.name in ('book.json','reader-index.json'):continue
  document=read(path)
  for scene in document.get('scenes',[]):
   identifier=scene['id']
   if identifier in scenes:raise ValueError('Duplicate native scene: '+identifier)
   scenes[identifier]=(path,document,scene)
 return scenes
def owners(root,mappings):
 result={};documents={};before={}
 for path in sorted((root/'manual/features').glob('*.yaml')):
  raw=path.read_bytes();document=yaml.safe_load(raw)
  if not isinstance(document,dict):continue
  for feature in document.get('features',[]):
   if feature['id'] not in mappings:continue
   if feature['id'] in result:raise ValueError('Duplicate feature identity')
   result[feature['id']]=(path,feature);documents[path]=document;before[path]=raw
 missing=set(mappings)-set(result)
 if missing:raise ValueError('Unknown feature IDs: '+','.join(sorted(missing)))
 return result,documents,before
def assertions(scene,doctor=False):
 if not scene.get('behaviour_case') or not scene.get('steps'):raise ValueError('Missing case or scene contract')
 result=[]
 for step in scene['steps']:
  binding=step.get('output',{}).get('binding',{})
  row=binding.get('assertion',dict(kind='audited-doctor-semantic-contract',expected=step.get('expect')) if doctor else None)
  if binding.get('passed') is not True or not isinstance(row,dict) or row.get('passed') is False or row.get('matched') is False:raise ValueError('Missing or failed semantic scene binding')
  if binding.get('semantic_assertions',0)<=0 or not binding.get('sha256') or not binding.get('grid_sha256'):raise ValueError('Missing native frame/grid/semantic binding')
  result.append(row)
 return result
def strip_receipt(row):return {key:value for key,value in row.items() if key!='document'}
def source_pair(real,controlled):
 keys=('plans_sha256','plan_files','adapter_sha256','case_sources','capture_sources','fixture_sources')
 for key in keys:
  if not real.get('source',{}).get(key) or real['source'][key]!=controlled.get('source',{}).get(key):raise ValueError('Two-lane native source mismatch: '+key)
def match_scene(identifier,scene,document,rows,audit_lane,identity):
 matching={}
 for row in rows:
  mode=row['clock_mode']
  if row['stage'].startswith('doctor-'):continue
  native=next((s for s in row['document'].get('scenes',[]) if s['id']==identifier),None)
  if native is None:continue
  if mode in matching:raise ValueError('Ambiguous build scene/lane: '+identifier)
  if native['behaviour_case']!=scene['behaviour_case'] or [s['id'] for s in native['steps']]!=[s['id'] for s in scene['steps']]:raise ValueError('Two-lane scene/case contract mismatch')
  audit_lane(row['document'])
  assertions(native)
  verify_reviewed_scene(native)
  matching[mode]=(row,native)
 if set(matching)!={'real-time','controlled-experimental'}:raise ValueError('Missing successful two-lane build scene: '+identifier)
 real,rs=matching['real-time'];controlled,cs=matching['controlled-experimental']
 if document['clock_mode']!='real-time' or rs!=scene:raise ValueError('Publication is not exact current real build scene')
 source_pair(real['document'],controlled['document'])
 ri=identity(Path(rs['evidence']['path']),profile=rs.get('profile','base-midi'))
 ci=identity(Path(cs['evidence']['path']),profile=cs.get('profile','base-midi'))
 if ri['application_digest']!=ci['application_digest']:raise ValueError('Two-lane application identity mismatch')
 return [dict(strip_receipt(row),application_identity=native_identity) for row,native_identity in [(real,ri),(controlled,ci)]]
def controlled_manual_audit(build):
 from manual_publication_verify import audit_controlled_manual_generation
 return audit_controlled_manual_generation(build,require_manual_generation_complete=False)

def match_controlled_scene(identifier,scene,document,rows,audit_lane,identity):
 matches=[]
 for row in rows:
  if row["clock_mode"]!="controlled-experimental" or row["stage"].startswith("doctor-"):continue
  native=next((candidate for candidate in row["document"].get("scenes",[]) if candidate["id"]==identifier),None)
  if native is None:continue
  if native["behaviour_case"]!=scene["behaviour_case"] or [step["id"] for step in native["steps"]]!=[step["id"] for step in scene["steps"]]:raise ValueError("Controlled scene/case contract mismatch: "+identifier)
  audit_lane(row["document"]);assertions(native);verify_reviewed_scene(native)
  if document.get("clock_mode")!="controlled-experimental" or native!=scene:raise ValueError("Publication is not exact current controlled build scene")
  native_identity=identity(Path(native["evidence"]["path"]),profile=native.get("profile","base-midi"))
  matches.append((row,native,native_identity))
 if len(matches)!=1:raise ValueError("Missing or ambiguous controlled build scene: "+identifier)
 row,native,native_identity=matches[0]
 return [dict(strip_receipt(row),application_identity=native_identity)]

def doctor_proof(document,rows):
 exception=document.get('controlled_time',{})
 if exception.get('applicable') is not False or not exception.get('reason'):raise ValueError('Missing Doctor audio-lane inapplicability')
 expected={(item['report'],item['report_sha256']) for item in document.get('evidence',{}).get('runs',[])}
 selected=[row for row in rows if row['stage'] in ('doctor-manual-real','doctor-auto-real')]
 actual={(row['report'],row['report_sha256']) for row in selected}
 if len(selected)!=2 or actual!=expected:raise ValueError('Doctor publication lacks both fresh build receipts')
 return [strip_receipt(row) for row in selected],copy.deepcopy(exception)



NB_ROUTE_IDS=['software-player-oilcan','software-player-polyperc','software-player-doubledecker']
def verify_nb_route_bindings(root=ROOT,audit_projection=None):
 root=Path(root)
 owned,_,_=owners(root,{'norns-sound-sources-with-n-b':NB_ROUTE_IDS})
 feature=owned['norns-sound-sources-with-n-b'][1]
 if any(identifier not in feature.get('scene_refs',[]) for identifier in NB_ROUTE_IDS) or 'generated/player-routes.json' not in feature.get('review',{}).get('native_evidence_catalogues',[]):raise ValueError('n.b. parent requires canonical player route replay bindings')
 path=root/'manual/generated/player-routes.json';document=read(path)
 case='MA-AUDIO-three-voice-conversation'
 if document.get('publication_kind')!='audio-route-projection' or document.get('passed') is not True or document.get('complete_regression_run') is not False or document.get('parent_publication',{}).get('acceptance_case')!=case:raise ValueError('Player route provenance or publication scope changed')
 scenes=document.get('scenes',[])
 if len(scenes)!=3 or [scene.get('id') for scene in scenes]!=NB_ROUTE_IDS:raise ValueError('Player route provenance inventory changed')
 for scene,voice,channel in zip(scenes,('Oilcan 1','Polyperc 1','Doubledecker'),(1,2,3)):
  if scene.get('feature_id')!='mods-and-software-devices' or scene.get('behaviour_case')!=case or len(scene.get('steps',[]))!=1:raise ValueError('Player route provenance ownership/case changed')
  binding=scene['steps'][0].get('output',{}).get('binding',{});assertion=binding.get('assertion',{});frame=binding.get('frame_oracle',{})
  if binding.get('passed') is not True or binding.get('capture_stage')!='before-apply' or assertion!={'kind':'device-picker-frame','label':voice,'matched':True} or frame!={'page':'midi_config','channel':channel,'selected_label':'Device','selected_value':voice,'matched':True} or not binding.get('following_apply'):raise ValueError('Player route provenance selection/apply contract changed')
 if audit_projection is None:
  from manual_player_routes import audit
  audit_projection=audit
 proof=audit_projection(path)
 if proof.get('passed') is not True or proof.get('scenes')!=3 or proof.get('frames')!=3:raise ValueError('Player route provenance audit failed')
 return dict(passed=True,scene_ids=list(NB_ROUTE_IDS),catalogue=str(path),catalogue_sha256=sha(path),case=case,audit=proof,complete_regression_run=False,scope='Real-audio native Device selection before K3; subsequent public apply and parent DSP acceptance. No controlled-audio or hardware claim.')


def bind(build,evidence,root=ROOT,mappings=None,audit_functions=None,controlled_local=False):
 default_mappings=mappings is None
 mappings=MAPPINGS if default_mappings else mappings
 build=Path(build).resolve();evidence=Path(evidence).resolve()
 if evidence.exists():raise ValueError('Binding evidence directory must be new')
 evidence.mkdir(parents=True)
 receipt=dict(schema_version=1,tool_sha256=sha(Path(__file__)),passed=False,complete_regression_run=False,hardware_timing_verified=False,build_evidence=str(build),feature_ids=list(mappings),mappings=[])
 if controlled_local:receipt.update(validation_scope="controlled-manual-generation",realtime_qualification="pending-ci",clock_mode="controlled-experimental")
 originals={};changed=[]
 try:
  audit_raw,audit_lane,identity=auditors() if audit_functions is None else audit_functions
  if controlled_local:
   scoped=controlled_manual_audit(build)
   if scoped.get('passed') is not True or scoped.get('validation_scope')!='controlled-manual-generation' or scoped.get('realtime_qualification')!='pending-ci' or scoped.get('complete_regression_run') is not False:raise ValueError('Controlled manual generation audit failed or changed scope')
   write_new(evidence/'controlled-audit.json',scoped)
   receipt['controlled_audit_sha256']=sha(evidence/'controlled-audit.json')
   receipt['controlled_audit']=scoped
  else:
   audit=audit_raw()
   if audit.get('passed') is not True or audit.get('complete_regression_run') is not False:raise ValueError('Raw publication audit failed or changed campaign scope')
   write_new(evidence/'raw-audit.json',audit)
   receipt['raw_audit_sha256']=sha(evidence/'raw-audit.json')
  if default_mappings:receipt['nb_player_routes']=verify_nb_route_bindings(root)
  rows=stage_reports(build,controlled_local=controlled_local);scenes=catalogue(root)
  feature_owners,documents,originals=owners(root,mappings)
  proof_cache={};audited_lanes=set()
  def cached_lane_audit(document):
   if id(document) not in audited_lanes:
    audit_lane(document);audited_lanes.add(id(document))
  for fid,identifiers in mappings.items():
   path,feature=feature_owners[fid]
   if feature.get('review',{}).get('status') not in ('pending','verified','controlled-verified'):raise ValueError('Unsupported feature review state: '+fid)
   refs=[];lanes=[];cases=[];exception=None
   for identifier in identifiers:
    if identifier not in scenes:raise ValueError('Missing audited scene: '+identifier)
    pub,document,scene=scenes[identifier]
    if identifier in EXPECTED_CASES and scene.get('behaviour_case')!=EXPECTED_CASES[identifier]:raise ValueError('Reviewed semantic case changed: '+identifier)
    is_doctor=document.get('publication_kind')=='doctor-native-audio'
    semantic=assertions(scene,doctor=is_doctor)
    verify_reviewed_scene(scene)
    if identifier not in proof_cache:
     if is_doctor:proof_cache[identifier]=doctor_proof(document,rows)
     else:proof_cache[identifier]=((match_controlled_scene(identifier,scene,document,rows,cached_lane_audit,identity) if controlled_local else match_scene(identifier,scene,document,rows,cached_lane_audit,identity)),None)
    proofs,exception=proof_cache[identifier]
    refs.append(dict(scene=identifier,data=pub.name,data_sha256=sha(pub),clock_mode=('controlled-experimental' if controlled_local and not is_doctor else 'real-time'),case=scene['behaviour_case'],assertions=semantic,scope=SCOPES.get(fid,'Exact audited native scene contract only.'),build_lane_proofs=proofs))
    lanes.extend(proofs);cases.append(scene['behaviour_case'])
   prior=copy.deepcopy(feature.get('review',{}))
   history=prior.get('historical_native_evidence',[])+[dict(review=copy.deepcopy({k:v for k,v in prior.items() if k!='historical_native_evidence'}),scene_refs=copy.deepcopy(feature.get('scene_refs',[])))]
   revised=copy.deepcopy(prior)
   revised.update(status=('controlled-verified' if controlled_local else 'verified'),cases=list(dict.fromkeys(prior.get('cases',[])+cases)),native_evidence=refs,historical_native_evidence=history,native_gap=None,rationale=SCOPES.get(fid,'Exact audited native scene contract only.'),scope=SCOPES.get(fid,'Exact audited native scene contract only.'),
    binding_receipt=str(evidence/'manifest.json'),complete_regression_run=False,
    note='Current raw publications independently audited; exact current-build timing-lane receipts are retained. Verification is scoped to the listed native contracts; exhaustive behavior and hardware acceptance remain separate.')
   if controlled_local:
    revised['validation_scope']='controlled-manual-generation';revised['realtime_qualification']='pending-ci'
   revised['controlled_baselines']=[row for row in lanes if row['clock_mode']=='controlled-experimental']
   if exception:revised['controlled_time']=exception
   feature['review']=revised
   feature['scene_refs']=list(dict.fromkeys(feature.get('scene_refs',[])+identifiers))
   receipt['mappings'].append(dict(feature=fid,source=str(path.relative_to(root)),claims_sha256=value_sha({k:v for k,v in feature.items() if k not in ('review','scene_refs')}),scene_ids=identifiers,cases=list(dict.fromkeys(cases)),scope=revised['scope'],controlled_time=exception or dict(applicable=True,verified=True),prior_review_sha256=value_sha(prior),current_review_sha256=value_sha(revised)))
  updates={path:yaml.safe_dump(document,sort_keys=False,allow_unicode=True).encode() for path,document in documents.items()}
  for path,raw in originals.items():
   if path.read_bytes()!=raw:raise ValueError('Authoring changed during audit: '+str(path))
   relative=path.relative_to(root)
   for folder,payload in [('before',raw),('after',updates[path])]:
    target=evidence/folder/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as handle:handle.write(payload)
   def content(doc):
    out=copy.deepcopy(doc)
    for item in out.get('features',[]):
     if item['id'] in mappings:item.pop('review',None);item.pop('scene_refs',None)
    return out
   if content(yaml.safe_load(raw))!=content(documents[path]):raise ValueError('Binding changed prose/source/history outside review metadata')
  receipt['files']=[dict(path=str(path.relative_to(root)),before_sha256=hashlib.sha256(originals[path]).hexdigest(),after_sha256=hashlib.sha256(updates[path]).hexdigest()) for path in updates]
  temporaries={}
  try:
   for path,payload in updates.items():
    temp=path.with_name('.'+path.name+'.feature-bind-'+evidence.name)
    with temp.open('xb') as handle:handle.write(payload);handle.flush();os.fsync(handle.fileno())
    temporaries[path]=temp
   for path,temp in temporaries.items():
    if path.read_bytes()!=originals[path]:raise ValueError('Concurrent authoring change before binding')
    os.replace(temp,path);changed.append(path)
   receipt['passed']=True
   ready=evidence/'manifest.ready'
   with ready.open('x') as handle:
    json.dump(receipt,handle,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
   os.replace(ready,evidence/'manifest.json')
  except BaseException:
   for path in changed:path.write_bytes(originals[path])
   raise
  finally:
   for temp in temporaries.values():
    if temp.exists():temp.unlink()
  receipt['passed']=True
 except BaseException as error:
  receipt['passed']=False
  receipt['failure']=repr(error)
  raise
 finally:
  if not (evidence/'manifest.json').exists():write_new(evidence/'manifest.json',receipt)
 return receipt
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--build-evidence',required=True)
 parser.add_argument('--evidence',required=True);parser.add_argument('--controlled-local',action='store_true')
 options=parser.parse_args()
 print(json.dumps(bind(options.build_evidence,options.evidence,controlled_local=options.controlled_local),indent=2))
if __name__=='__main__':main()


"""Fresh-run Doctor/Panic native MIDI producer; no retained-source admission."""
import base64
import copy
import hashlib
import json
from pathlib import Path

class FreshMidiError(ValueError):
    pass

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode('utf-8')

def _require(condition, message):
    if not condition:
        raise FreshMidiError(message)

def _read(root, name, pin=None):
    raw=(root/name).read_bytes()
    _require(pin is None or _sha(raw)==pin,'changed retained source: '+name)
    return raw

def _native(root, pins, complete_snapshots, allow_equal_timestamps=False):
    names=('results.json','observations.json','native/identity.json','native/native-events.jsonl')
    files={n:_read(root,n,pins.get(n)) for n in names}
    results=json.loads(files['results.json']); obs=json.loads(files['observations.json'])
    identity=json.loads(files['native/identity.json'])
    rows=[json.loads(v) for v in files['native/native-events.jsonl'].splitlines() if v.strip()]
    midi=[v for v in rows if v.get('kind') in (3,11)]
    _require(bool(midi) and all(type(v.get('index')) is int and v['index']==i for i,v in enumerate(midi,1)),'missing, invalid, or unordered native MIDI index')
    _require(all(type(v.get('sequence')) is int and v['sequence']==i for i,v in enumerate(midi,1)),'native MIDI sequence changed or invalid')
    times=[v.get('monotonic_ns') for v in midi]
    _require(all(isinstance(t,int) and not isinstance(t,bool) and t>0 for t in times),'native MIDI monotonic timestamp missing or invalid')
    _require(all(a<=b for a,b in zip(times,times[1:])) if allow_equal_timestamps else all(a<b for a,b in zip(times,times[1:])),
        'native MIDI timestamps are duplicate or out of order')
    _require(not any(r.get('passed') is False or r.get('matched') is False for r in results),'failed original assertion')
    seen={}
    for o in obs:
        _require(o.get('session_id')==identity['session_id'],'foreign native session')
        state=o['state']; cap=state['midi_capture']
        _require(cap['dropped']==0 and cap['count']==state['midi_count'],'dropped or inconsistent capture')
        for p in state['midi']:
            _require(p['index'] not in seen or seen[p['index']]==p,'snapshot conflict')
            seen[p['index']]=p
    _require(obs[-1]['state']['midi_count']==len(midi),'truncated native journal')
    _require(set(seen)<=set(range(1,len(midi)+1)),'foreign snapshot packet')
    if complete_snapshots:
        _require(set(seen)==set(range(1,len(midi)+1)),'incomplete snapshot cross-check')
    for p in midi:
        if p['index'] in seen:
            _require(all(p.get(k)==seen[p['index']].get(k) for k in ('port','bytes','monotonic_ns','logical_ns','device_id','port_name')),'raw packet differs from snapshot')
    return results,obs,identity,rows,midi,seen,{k:_sha(v) for k,v in files.items()}

def _pixel_observations(output, observations, count):
    levels=[v for v,n in output['screen_rle'] for _ in range(n)]
    grid=output['grid']; binding=output['binding']
    _require(len(levels)==8192 and len(grid)==128 and all(isinstance(v,int) and 0<=v<=15 for v in levels+grid),'invalid pixel/grid extent')
    _require(_sha(bytes(grid))==binding['grid_sha256'],'changed bound grid')
    found=[]
    for i,o in enumerate(observations):
        st=o['state']
        if st['midi_count']==count and st['frame']['sha256']==binding['sha256'] and st['grid']==grid:
            rgba=base64.b64decode(st['frame']['pixels_base64'])
            _require(len(rgba)==32768 and _sha(rgba)==binding['sha256'] and _sha(rgba[:128*55*4])==binding['stable_sha256'],'frame hash/pixels differ')
            _require(all(v%17==0 for v in rgba[::4]) and [v//17 for v in rgba[::4]]==levels,'changed bound pixels')
            found.append(i)
    _require(bool(found),'target frame is not observed at actual window end')
    return found

def _receipt(window, midi, identity, hashes, binding, witness, kind, coverage, pixel_indices):
    return {'events':window,'total':len(window),'truncated':False,
        'provenance':{'kind':kind,'session_id':identity['session_id'],'source_sha256':hashes,
          'window_start_index':window[0]['index'],'window_end_index':window[-1]['index'],
          'complete_native_event_count':len(midi),'window_sha256':_sha(_canonical(window)),
          'start_monotonic_ns':window[0]['monotonic_ns'],'end_monotonic_ns':window[-1]['monotonic_ns'],
          'snapshot_cross_checked_packet_count':coverage,'snapshot_cross_check_complete':coverage==len(midi),
          'target_frame_sha256':binding['sha256'],'target_grid_sha256':binding['grid_sha256'],
          'target_pixel_observation_indices':pixel_indices,'original_witness':witness}}

def _same_original(step, original):
    for k in ('inputs','expect','output'):
        _require(step[k]==original[k],'current target differs from original '+k)

def _doctor(scene, project_root):
    path=(project_root/'manual'/scene['data_path']).resolve()
    _require(project_root.resolve() in path.parents and path.name=='doctor-scenes.json','unsafe Doctor publication path')
    pub=json.loads(path.read_bytes())
    _require(pub.get('publication_kind')=='doctor-native-audio' and pub.get('passed') is True,'unqualified Doctor publication')
    matches=[]
    for record in pub['evidence']['runs']:
        report_path=Path(record['report']);raw=_read(report_path.parent,'report.json',record['report_sha256']);report=json.loads(raw)
        originals=[v for v in report['scenes'] if v['id']==scene['id']]
        if originals:matches.append((report_path.parent,report,originals[0],record['report_sha256']))
    _require(len(matches)==1,'Doctor report binding is not unique')
    root,report,original,report_sha=matches[0]
    _require(report.get('passed') is True and not report.get('failure') and not report.get('cleanup_failure') and report.get('clock_mode')=='real-time','Doctor report failed or wrong lane')
    results,obs,identity,rows,midi,seen,hashes=_native(root,{},False)
    _require(identity['application_identity']['digest']==report['source_identity']['digest'],'foreign Doctor source identity')
    published=[v for v in pub['scenes'] if v['id']==scene['id']]
    _require(len(published)==1,'Doctor publication scene is not unique')
    out=copy.deepcopy(scene)
    steps=[s for s in out['steps'] if s['id']=='play'];_require(len(steps)==1,'Doctor play target missing')
    step=steps[0];old=[s for s in original['steps'] if s['id']=='play'];_require(len(old)==1,'Doctor original play missing');_same_original(step,old[0])
    _same_original(step,next(v for v in published[0]['steps'] if v['id']=='play'))
    binding=step['output']['binding'];i=binding['semantic_assertions']
    _require(results[i]==binding and results[i-1].get('kind')=='manual-doctor-semantic' and results[i-1].get('step')=='play' and results[i-1]['expected']==step['expect'],'Doctor semantic/frame adjacency changed')
    witness=results[i-1];expected=witness['expected'];lo=expected['midi_start_index'];hi=expected['midi_end_index']
    _require(isinstance(lo,int) and isinstance(hi,int) and 0<=lo<hi<=len(midi),'invalid original Doctor window')
    window=midi[lo:hi];ons=[v for v in window if 144<=v['bytes'][0]<=159 and v['bytes'][2]>0]
    _require([seen[v['index']] for v in ons]==expected['notes'] and len(ons)>=expected['midi_minimum_attacks'] and all(v['port']==expected['port'] for v in ons),'Doctor actual onset witness changed')
    _require(any(o['state']['midi_count']==lo for o in obs),'Doctor baseline not observed')
    pi=_pixel_observations(step['output'],obs,hi);hashes.update({'report.json':report_sha,'publication.json':_sha(path.read_bytes())})
    receipt=_receipt(window,midi,identity,hashes,binding,witness,'fresh-native-doctor-play-window-v1',len(seen),pi)
    receipt['provenance'].update(source_classification='fresh-current-run',window_lower_bound_exclusive=lo,window_upper_bound_inclusive=hi,scope='complete fresh native Doctor play stage, including transport and releases')
    step['output']['midi']=receipt
    return out

def _panic(scene):
    ev=scene['evidence'];root=Path(ev['path'])
    pins={'results.json':ev['results_sha256'],'native/identity.json':ev['identity_sha256'],'native/native-events.jsonl':ev['native_events_sha256']}
    results,obs,identity,rows,midi,seen,hashes=_native(root,pins,False)
    context=json.loads(_read(root,'session-context.json',ev['session_context_sha256']))
    _require(context==ev['session_context'] and context['session_id']==identity['session_id'] and context.get('finished') is True and context.get('cleanup_verified') is True and not context.get('held_inputs'),'foreign or incomplete panic participant')
    trace_raw=_read(root,'capture-trace.json',ev['capture_trace_sha256']);trace=json.loads(trace_raw)
    originals=json.loads(_read(root,'captured-scenes.json'))
    original=[v for v in originals if v['id']==scene['id']];_require(len(original)==1,'original panic scene missing')
    out=copy.deepcopy(scene);step=next(v for v in out['steps'] if v['id']=='hold-and-release');_same_original(step,next(v for v in original[0]['steps'] if v['id']=='hold-and-release'))
    binding=step['output']['binding'];_require(binding in results and binding.get('capture_stage')=='before-finish','panic deferred frame changed')
    i=binding['assertion_index'];witness=results[i]
    _require(witness==binding['assertion'] and _sha(_canonical(witness))==binding['assertion_sha256'] and witness=={'kind':'panic-full-stream-accounting','note_events':6144,'windows':1,'unaccounted':0,'passed':True},'panic original full accounting changed')
    _require(_sha(_canonical(step['inputs']))==binding['trace_sha256'],'panic target input trace changed')
    windows_raw=_read(root,'panic-windows.json');windows=json.loads(windows_raw)
    _require(len(windows)==1 and windows[0]['type']=='panic','panic original window is not unique');w=windows[0]
    _require(w['press_ack']['session_id']==identity['session_id'] and w['press_ack']['status']=='applied','foreign panic press receipt')
    _require(w['press_ack']['action_id']==w['input_origin']['action_id'] and w['press_ack']['native']['sequence']==w['input_origin']['native_sequence'],'panic input origin changed')
    press=[v for v in rows if v.get('kind')=='input' and v.get('sequence')==w['input_origin']['native_sequence']]
    timings=[v for v in rows if v.get('kind')=='input_timing' and v.get('sequence')==w['input_origin']['native_sequence']]
    _require(len(press)==1 and press[0]['type']==3 and press[0]['args']==[w['button']-1,7,1] and press[0]['monotonic_ns']==w['input_origin']['origin_ns'],'panic native public press differs')
    _require(len(timings)==1 and timings[0]['native_ack_ns']==w['input_origin']['applied_ns'],'panic native acknowledgement differs')
    _require(any(step['inputs']==trace[j:j+len(step['inputs'])] for j in range(len(trace)-len(step['inputs'])+1)),'panic target trace not retained')
    lo=w['after'];hi=w['cursor'];_require(isinstance(lo,int) and isinstance(hi,int) and 0<=lo<hi<=len(midi),'invalid original panic bounds')
    window=midi[lo:hi]
    _require(len(window)==6144 and hi==len(midi),'panic actual full window count changed')
    _require(all(v['monotonic_ns']>=w['input_origin']['applied_ns'] and v['logical_ns']>=w['minimum_ns'] for v in window),'panic packets precede original hold boundary')
    actual={(p,c,n):0 for p in (1,2,3) for c in range(16) for n in range(128)}
    for packet in window:
        b=packet['bytes'];_require(len(b)==3 and 128<=b[0]<=143 and b[2]==0,'panic packet is not actual note off');key=(packet['port'],b[0]-128,b[1]);_require(key in actual,'panic foreign port/note');actual[key]+=1
    _require(all(v==1 for v in actual.values()),'panic actual channel/note accounting changed')
    counts=[r for r in results if r.get('kind')=='panic-port-counts'];_require(len(counts)==1 and counts[0]['counts']=={'1':2048,'2':2048,'3':2048} and counts[0]['button']==w['button'] and counts[0]['source']==w['source'],'panic original per-port receipt changed')
    _require(any(o['state']['midi_count']==lo for o in obs),'panic baseline not observed');pi=_pixel_observations(step['output'],obs,hi)
    hashes.update({'panic-windows.json':_sha(windows_raw),'capture-trace.json':_sha(trace_raw),'session-context.json':_sha(_read(root,'session-context.json')),'captured-scenes.json':_sha(_read(root,'captured-scenes.json'))})
    receipt=_receipt(window,midi,identity,hashes,binding,witness,'fresh-native-panic-full-window-v1',len(seen),pi)
    receipt['provenance'].update(source_classification='fresh-current-run',original_window_receipt=w,window_lower_bound_exclusive=lo,window_upper_bound_inclusive=hi,scope='complete fresh native 6144-packet Panic sweep, with partial snapshot cross-check explicitly recorded')
    step['output']['midi']=receipt
    return out


def _documented_frame_count(scene, step, results, observations, session_id):
    binding=step.get('output',{}).get('binding',{})
    i=binding.get('assertion_index')
    _require(type(i) is int and 0<=i<len(results) and results[i]==binding.get('assertion'),
        'Panic frame assertion is not bound to its source result')
    _require(binding.get('assertion_sha256')==_sha(_canonical(binding['assertion'])),
        'Panic frame assertion digest changed')
    _require(binding.get('trace_sha256')==_sha(_canonical(step.get('inputs',[]))),
        'Panic frame input trace digest changed')
    doc=results[i+1] if i+1<len(results) else None
    expected='manual/'+scene.get('behaviour_case','')+'/'+scene['id']+'/'+step['id']
    _require(isinstance(doc,dict) and doc.get('kind')=='documentation-frame' and doc.get('name')==expected
        and doc.get('passed') is True and doc.get('assertion_index')==i and doc.get('assertion')==binding['assertion']
        and binding.get('sha256')==doc.get('sha256'), 'Panic source frame is not adjacent to its assertion')
    output=step.get('output',{});grid=output.get('grid');
    _require(isinstance(grid,list) and len(grid)==128 and _sha(bytes(grid))==doc.get('grid_sha256')
        and binding.get('grid_sha256')==doc.get('grid_sha256'), 'Panic source grid differs from its documented frame')
    from manual_screen_codec import encode_native_frame
    matching=[]
    for i,row in enumerate(observations):
        if row.get('session_id')!=session_id or row.get('backend')!='native' or row.get('fidelity')!='native-norns':
            continue
        state=row.get('state',{});frame=state.get('frame',{})
        if state.get('grid')!=grid or frame.get('sha256')!=doc.get('sha256'):
            continue
        pixels=base64.b64decode(frame.get('pixels_base64',''),validate=True)
        _require((frame.get('width'),frame.get('height'),frame.get('format'))==(128,64,'BGRA8')
            and len(pixels)==32768 and _sha(pixels)==doc['sha256'], 'Panic source observation pixels changed')
        _require(encode_native_frame(pixels)=={'screen_rle':output.get('screen_rle')},
            'Panic source screen RLE differs from its native frame')
        matching.append((i,state.get('midi_count')))
    _require(matching and all(type(count) is int and count==matching[0][1] for _,count in matching),
        'Panic source frame lacks a stable same-session MIDI count')
    return matching[-1][0],matching[-1][1],doc

def _panic_sounding_note(scene, project_root, build_root, manifest, record):
    from manual_panic_release_readout import validate_fresh_panic_release_readout
    out=copy.deepcopy(scene); step=_target_step(out); ev=out['evidence']; root=Path(record['source_root'])
    pins=record['source_sha256']
    results,obs,identity,rows,midi,seen,hashes=_native(root,pins,False)
    proof=validate_fresh_panic_release_readout(out,step['id'],[{'port':1,'bytes':[128,60,0]}],
        Path(project_root),build_root,manifest,record)
    _require(len(out['steps'])>=3 and out['steps'][-2]['id']=='note-sounding' and out['steps'][-1]['id']=='panic-released',
        'Panic target does not follow its recorded sounding-note baseline')
    before=out['steps'][-2]
    before_index,before_count,before_doc=_documented_frame_count(out,before,results,obs,identity['session_id'])
    target_index,target_count,_=_documented_frame_count(out,step,results,obs,identity['session_id'])
    _require(type(before_count) is int and type(target_count) is int and 0<=before_count<target_count<=len(midi),
        'Panic at-target MIDI bounds are invalid')
    cutoff_index=proof.get('native_event_index')
    _require(type(cutoff_index) is int and before_count<cutoff_index<=target_count,
        'Panic note-off is outside the documented target-frame window')
    window=midi[before_count:target_count]
    _require(window and len(window)==target_count-before_count
        and [row.get('index') for row in window]==list(range(before_count+1,target_count+1)),
        'Panic target MIDI window is missing, unordered, or includes data beyond its frame')
    proof['target_midi_start_exclusive']=before_count
    proof['target_midi_end_inclusive']=target_count
    proof['target_documentation_observation_index']=target_index
    proof['baseline_documentation_observation_index']=before_index
    proof['baseline_frame_sha256']=before_doc['sha256']
    proof['complete_native_event_count']=len(midi)
    receipt=_receipt(window,midi,identity,hashes,step['output']['binding'],
        step['output']['binding']['assertion'],'fresh-native-panic-sounding-note-target-window-v1',len(seen),[target_index])
    receipt['provenance'].update(source_classification='fresh-current-run',
        fresh_run_id=record['run_id'],fresh_build_id=manifest['build_id'],
        fresh_manifest_qualification=manifest['qualification'],fresh_source_sha256=record['source_sha256'],
        fresh_record_sha256=_sha(_canonical(record)),panic_release_readout=proof,
        scope='complete MIDI packets after the documented sounding-note frame through the exact Panic target frame; later playback is excluded')
    step['output']['midi']=receipt
    return out

TARGET_DOCTOR = {'doctor-local-capture-and-paint','doctor-local-auto-capture-and-paint'}
TARGET_PANIC = {'panic-from-song-channel','panic-from-song-pattern'}
TARGET_PANIC_RELEASE = {'panic-stops-sounding-note'}
TARGET_MASKS = {'mask-precedence','mask-ghost-note','mask-melody-ending','mask-chords'}
MASK_TRANSITIONS = {'mask-precedence':('route','default'),'mask-ghost-note':('accent','ghost'),'mask-melody-ending':('step-four','ending-d'),'mask-chords':('chord','thirds')}
MANIFEST_KIND = 'fresh-native-target-midi-v1'
def _target_step(scene):
    wanted = ('play' if scene['id'] in TARGET_DOCTOR else
              'panic-released' if scene['id'] in TARGET_PANIC_RELEASE else
              MASK_TRANSITIONS[scene['id']][1] if scene['id'] in TARGET_MASKS else 'hold-and-release')
    steps = [step for step in scene.get('steps',[]) if step.get('id') == wanted]
    _require(len(steps)==1,'fresh target step is missing or duplicated')
    return steps[0]
def _target_root(scene, project_root):
    sid=scene['id']
    if sid in TARGET_PANIC | TARGET_PANIC_RELEASE | TARGET_MASKS:
        return Path(scene['evidence']['path']).resolve()
    pub_path=(Path(project_root)/'manual'/scene['data_path']).resolve()
    _require(Path(project_root).resolve() in pub_path.parents and pub_path.name=='doctor-scenes.json','unsafe Doctor publication path')
    pub=json.loads(pub_path.read_bytes())
    _require(pub.get('publication_kind')=='doctor-native-audio' and pub.get('passed') is True,'unqualified fresh Doctor publication')
    matches=[]
    for record in pub.get('evidence',{}).get('runs',[]):
        report_path=Path(record['report']).resolve()
        report=json.loads(report_path.read_bytes())
        if any(row.get('id')==sid for row in report.get('scenes',[])):
            matches.append(report_path.parent)
    _require(len(matches)==1,'fresh Doctor report binding is not unique')
    return matches[0]
def _required_sources(sid):
    common={'results.json','observations.json','native/identity.json','native/native-events.jsonl'}
    return common|({'report.json'} if sid in TARGET_DOCTOR else
        {'captured-scenes.json','capture-trace.json','session-context.json','panic-windows.json'} if sid in TARGET_PANIC else
        {'capture-trace.json','session-context.json','native/cleanup.json','recipe.json'} if sid in TARGET_PANIC_RELEASE else
        {'results.json','observations.json','native/identity.json','native/native-events.jsonl','native/cleanup.json'} if sid in TARGET_MASKS else
        {'results.json','observations.json','native/identity.json','native/native-events.jsonl','native/cleanup.json'})
def _masks_stage_proof(build_root, project_root, scenes):
    """Admit Masks only from this build's sealed live stage receipt, never from scene paths alone."""
    build_root=Path(build_root).resolve();project_root=Path(project_root).resolve()
    sidecar=build_root/'masks-controlled.json';log=build_root/'masks-controlled.log';context_path=build_root/'generation-context.json'
    for path in (sidecar,log,context_path):
        _require(path.is_file() and not path.is_symlink() and build_root in path.resolve().parents,
            'current Masks stage receipt is missing or unsafe: '+path.name)
    stage_raw=sidecar.read_bytes();log_raw=log.read_bytes();context_raw=context_path.read_bytes()
    stage=json.loads(stage_raw);context=json.loads(context_raw);log_text=log_raw.decode('utf-8')
    _require(stage.get('name')=='masks-controlled' and stage.get('passed') is True
        and stage.get('returncode')==0 and stage.get('exclusive_lock') is True and stage.get('action') is None,
        'Masks controlled stage is not a successful exclusive fresh capture')
    command=stage.get('command');executed=stage.get('executed_command')
    _require(isinstance(command,list) and command and command==executed,'Masks executed command differs from its stage plan')
    _require(len(command)>=2 and Path(command[1]).resolve()==(project_root/'tools/manual_capture.py').resolve(),
        'Masks stage did not invoke the current checkout capture producer')
    _require('--clock-mode' in command and command.index('--clock-mode')+1<len(command)
        and command[command.index('--clock-mode')+1]=='controlled-experimental'
        and '--experimental-install' in command and command.index('--experimental-install')+1<len(command)
        and bool(command[command.index('--experimental-install')+1]) and '--controlled-local' in command,
        'Masks stage lacks controlled clock/install qualification')
    _require('--source' not in command,'Masks stage uses an unsupported alternate source')
    _require('--visuals-only' not in command and '--verify-only' not in command,
        'Masks stage uses an unsupported nonfresh capture mode')
    _require(not any(any(word in str(arg).lower() for word in ('resume','adopt','reuse')) for arg in command),
        'Masks stage uses an unsupported resumed/adopted evidence mode')
    start=stage.get('started_utc');finish=stage.get('finished_utc')
    _require(isinstance(start,str) and isinstance(finish,str) and start<finish,'Masks stage timing receipt is invalid')
    _require(context.get('validation_scope')=='controlled-manual-generation'
        and context.get('clock_mode')=='controlled-experimental'
        and context.get('complete_regression_run') is False,'Masks generation context is not controlled/pending')
    producer_pins=context.get('producer_source_sha256')
    required_tools={'tools/manual_capture.py','tools/manual_build.py'}
    _require(isinstance(producer_pins,dict) and set(producer_pins)==required_tools,
        'pre-stage producer source pins are missing')
    for rel,pin in producer_pins.items():
        path=project_root/rel
        _require(path.is_file() and not path.is_symlink() and _sha(path.read_bytes())==pin,
            'producer source differs from pre-stage pin: '+rel)
    source_before=context.get('source_files_before')
    _require(isinstance(source_before,dict) and source_before
        and all(isinstance(rel,str) and isinstance(pin,str) and len(pin)==64 for rel,pin in source_before.items()),
        'generation source snapshot is missing or malformed')
    mask_source='manual/features/masks.yaml';mask_pin=source_before.get(mask_source)
    _require(isinstance(mask_pin,str) and _sha((project_root/mask_source).read_bytes())==mask_pin,
        'Masks capture source differs from its pre-stage pin')
    _require(stage.get('log_sha256')==_sha(log_raw),'Masks stage log differs from its sidecar hash')
    roots=[]
    for line in log_text.splitlines():
        if line.startswith('Evidence '):roots.append(line[len('Evidence '):].strip())
    _require(len(roots)==1 and roots[0],'Masks stage log has no unique evidence root')
    evidence_root=Path(roots[0]).resolve()
    target_scenes=[v for v in scenes if v.get('id') in TARGET_MASKS]
    _require({v['id'] for v in target_scenes}==TARGET_MASKS,'Masks target scene inventory differs')
    identities=[]
    for scene in target_scenes:
        root=Path(scene.get('evidence',{}).get('path','')).resolve()
        _require(root==evidence_root/scene['id'],'Masks scene root does not match the live stage log')
        identity=json.loads((root/'native/identity.json').read_bytes())
        app=identity.get('application_identity',{});entries=app.get('files')
        _require(isinstance(entries,list) and entries and app.get('digest'),'Masks application identity is incomplete')
        paths=[entry.get('path') for entry in entries]
        _require(all(isinstance(v,str) and v for v in paths) and paths==sorted(paths) and len(paths)==len(set(paths)),
            'Masks application identity file list is not canonical')
        _require(hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()==app['digest'],
            'Masks application identity digest does not bind its file list')
        seen={}
        for entry in entries:
            rel=entry.get('path','')
            _require(rel.startswith('mosaic/'),'Masks identity path is outside the Mosaic tree')
            normalized=rel[len('mosaic/'):]
            _require(normalized not in seen,'Masks application identity has duplicate paths')
            src=(project_root/normalized).resolve()
            _require(project_root in src.parents and src.is_file() and not src.is_symlink()
                and src.stat().st_size==entry.get('size') and _sha(src.read_bytes())==entry.get('sha256'),
                'Masks captured application source differs from current checkout: '+normalized)
            seen[normalized]=entry['sha256']
        identities.append((identity['session_id'],app['digest'],_sha(_canonical(seen))))
    _require(len({v[1:] for v in identities})==1,'Masks scenes have inconsistent application source identities')
    return {'stage_name':'masks-controlled','stage_sidecar_sha256':_sha(stage_raw),
        'stage_log_sha256':_sha(log_raw),'generation_context_sha256':_sha(context_raw),
        'producer_source_sha256':producer_pins,'evidence_root':str(evidence_root),
        'application_digest':identities[0][1],'application_file_map_sha256':identities[0][2],
        'scene_sessions':{v['id']:next(i[0] for i,scene in zip(identities,target_scenes) if scene['id']==v['id']) for v in target_scenes}}

def _masks_frame(scene,step,results,observations,session_id):
    binding=step.get('output',{}).get('binding',{});i=binding.get('semantic_assertions')
    _require(type(i) is int and 1<=i<len(results),'Masks target has no captured semantic/frame association')
    semantic,doc=results[i-1],results[i]
    _require(semantic.get('kind')=='manual-semantic' and semantic.get('step')==step.get('id')
        and semantic.get('passed') is True and semantic.get('expected')==step.get('expect'),
        'Masks semantic result is not the authored target result')
    _require(doc.get('kind')=='documentation-frame' and doc.get('name')==binding.get('name')
        and doc.get('passed') is True and binding.get('sha256')==doc.get('sha256'),
        'Masks frame result is not adjacent to its semantic checkpoint')
    grid=step.get('output',{}).get('grid');_require(isinstance(grid,list) and len(grid)==128
        and _sha(bytes(grid))==doc.get('grid_sha256')==binding.get('grid_sha256'),'Masks frame grid differs')
    from manual_screen_codec import encode_native_frame
    matching=[]
    for oi,row in enumerate(observations):
        if row.get('session_id')!=session_id or row.get('backend')!='native' or row.get('fidelity')!='native-norns':continue
        state=row.get('state',{});frame=state.get('frame',{})
        if frame.get('sha256')!=doc.get('sha256') or state.get('grid')!=grid:continue
        pixels=base64.b64decode(frame.get('pixels_base64',''),validate=True)
        _require((frame.get('width'),frame.get('height'),frame.get('format'))==(128,64,'BGRA8')
            and len(pixels)==32768 and _sha(pixels)==doc['sha256'],'Masks native frame pixels differ')
        _require(encode_native_frame(pixels)=={'screen_rle':step['output'].get('screen_rle')},
            'Masks screen RLE differs from the native frame')
        matching.append((oi,state.get('midi_count')))
    _require(matching and all(type(n) is int for _,n in matching),'Masks frame lacks native MIDI count')
    return i,doc,matching

def _masks(scene,project_root,build_root,manifest,record,stage_proof):
    sid=scene['id'];source_root=Path(record['source_root']);pins=record['source_sha256']
    results,observations,identity,rows,midi,seen,hashes=_native(source_root,pins,False,allow_equal_timestamps=True)
    cleanup=json.loads(_read(source_root,'native/cleanup.json',pins['native/cleanup.json']))
    _require(cleanup and all(item.get('returncode') in (0,-15) for item in cleanup),
        'Masks source cleanup failed')
    session=identity.get('session_id');_require(session==stage_proof['scene_sessions'][sid],'Masks session differs from live stage receipt')
    from_id,to_id=MASK_TRANSITIONS[sid];out=copy.deepcopy(scene)
    before=next((v for v in out['steps'] if v.get('id')==from_id),None);target=_target_step(out)
    _require(before is not None,'Masks source step is missing')
    before_index,before_doc,before_matches=_masks_frame(out,before,results,observations,session)
    target_index,target_doc,target_matches=_masks_frame(out,target,results,observations,session)
    ordered_counts=[row.get('state',{}).get('midi_count') for row in observations]
    _require(all(type(n) is int for n in ordered_counts)
        and all(a<=b for a,b in zip(ordered_counts,ordered_counts[1:])),
        'Masks native observation MIDI counts are not ordered')
    before_counts={n for _,n in before_matches}
    _require(len(before_counts)==1,'Masks source frame MIDI count is ambiguous')
    start=next(iter(before_counts));baseline_observation=max(i for i,n in before_matches)
    target_candidates=[(i,n) for i,n in target_matches if i>baseline_observation and n>start]
    target_counts={n for _,n in target_candidates}
    _require(len(target_counts)==1,'Masks target frame MIDI count is ambiguous')
    end=next(iter(target_counts));end_matches=[i for i,n in target_candidates if n==end]
    _require(end_matches,'Masks target documentation frame has no observation after its source frame')
    target_observation=min(end_matches)
    _require(0<=start<end<=len(midi),'Masks target MIDI window bounds are invalid')
    window=midi[start:end]
    _require(window and [v.get('index') for v in window]==list(range(start+1,end+1)),
        'Masks MIDI target window is missing or noncontiguous')
    midi_result=results[target_index-2] if target_index>=2 else {}
    _require(midi_result.get('kind')=='midi' and midi_result.get('expected')==midi_result.get('actual'),
        'Masks target MIDI result is not adjacent to its semantic/frame proof')
    expected=midi_result.get('expected',[])
    actual=[[v['port'],v['bytes']] for v in window if len(v.get('bytes',[]))==3
        and 144<=v['bytes'][0]<=159 and v['bytes'][2]>0]
    phrase=target.get('expect',{}).get('midi_phrase')
    _require(expected and actual==expected,'Masks complete native MIDI window differs from passed MIDI result')
    normalized=[{'port':p,'bytes':b} for p,b in actual]
    cursor=0
    for wanted in phrase or []:
        try:cursor=next(i+1 for i in range(cursor,len(normalized)) if normalized[i]==wanted)
        except StopIteration:raise FreshMidiError('Masks authored MIDI phrase is not in the captured target window')
    proof={'from_step_id':from_id,'to_step_id':to_id,'baseline_midi_count':start,
        'target_midi_count':end,'target_documentation_observation_index':target_observation,
        'target_equivalent_observation_indices':end_matches,
        'baseline_documentation_observation_index':baseline_observation,
        'baseline_frame_sha256':before_doc['sha256'],'target_frame_sha256':target_doc['sha256'],
        'complete_native_event_count':len(midi),'captured_note_on_count':len(actual),
        'passed_midi_result_sha256':_sha(_canonical(midi_result))}
    receipt=_receipt(window,midi,identity,hashes,target['output']['binding'],proof,
        'fresh-native-masks-transition-target-window-v1',len(seen),end_matches)
    receipt['provenance'].update(source_classification='fresh-current-run',fresh_run_id=record['run_id'],
        fresh_build_id=manifest['build_id'],fresh_manifest_qualification=manifest['qualification'],
        fresh_source_sha256=record['source_sha256'],fresh_record_sha256=_sha(_canonical(record)),
        masks_stage=stage_proof,transition=proof,
        scope='complete raw MIDI window after the source frame through the exact captured target frame')
    target['output']['midi']=receipt
    return out

def build_fresh_target_midi_manifest(scenes, project_root, build_root, qualification='fresh-candidate-pending-ci'):
    """Seal only target evidence produced beneath this build's evidence directory."""
    build_root=Path(build_root).resolve()
    _require(qualification in ('fresh-candidate-pending-ci','derived-unit-fixture'),'invalid fresh qualification label')
    targets=[scene for scene in scenes if scene.get('id') in TARGET_DOCTOR|TARGET_PANIC|TARGET_PANIC_RELEASE|TARGET_MASKS]
    expected={scene['id'] for scene in targets}
    _require(expected and len(expected)==len(targets),'fresh target scene inventory is empty or duplicated')
    records={}
    masks_stage=_masks_stage_proof(build_root,project_root,scenes) if expected & TARGET_MASKS else None
    for scene in targets:
        sid=scene['id'];root=_target_root(scene,project_root).resolve()
        if sid not in TARGET_MASKS:
            _require(build_root in root.parents,'fresh native run is outside this build evidence root')
        names=_required_sources(sid);hashes={}
        for name in names:
            file=root/name
            _require(root in file.resolve().parents and file.is_file() and not file.is_symlink(),'missing or unsafe fresh source: '+name)
            hashes[name]=_sha(file.read_bytes())
        identity=json.loads((root/'native/identity.json').read_bytes())
        step=_target_step(scene)
        records[sid]={'scene_id':sid,'source_root':str(root),'run_id':root.name,
            'session_id':identity.get('session_id'),
            'application_digest':identity.get('application_identity',{}).get('digest'),
            'step_id':step['id'],'target_sha256':_sha(_canonical({k:step[k] for k in ('inputs','expect','output')})),
            'source_sha256':hashes}
    return {'schema_version':1,'kind':MANIFEST_KIND,'qualification':qualification,
        'validation_scope':'fresh-native-target-midi-source-receipt','realtime_qualification':'pending-ci',
        'complete_regression_run':False,'build_root':str(build_root),'build_id':build_root.name,'masks_stage':masks_stage,'scenes':records}
def validate_fresh_target_midi_manifest(scenes, project_root, build_root, manifest):
    _require(isinstance(manifest,dict) and manifest.get('schema_version')==1 and manifest.get('kind')==MANIFEST_KIND,'fresh native target manifest is required')
    _require(manifest.get('qualification') in ('fresh-candidate-pending-ci','derived-unit-fixture'),'invalid fresh evidence qualification')
    build_root=Path(build_root).resolve()
    _require(Path(manifest.get('build_root','')).resolve()==build_root and manifest.get('build_id')==build_root.name,'foreign fresh build root')
    expected={scene['id'] for scene in scenes if scene.get('id') in TARGET_DOCTOR|TARGET_PANIC|TARGET_PANIC_RELEASE|TARGET_MASKS}
    records=manifest.get('scenes',{})
    stage_proof=_masks_stage_proof(build_root,project_root,scenes) if expected & TARGET_MASKS else None
    _require(manifest.get('masks_stage')==stage_proof,'current Masks stage receipt changed or is missing')
    _require(set(records)==expected,'fresh target scene inventory differs')
    by_id={scene['id']:scene for scene in scenes}
    for sid,record in records.items():
        scene=by_id[sid];root=Path(record.get('source_root','')).resolve()
        if sid in TARGET_MASKS:
            _require(root==Path(by_id[sid].get('evidence',{}).get('path','')).resolve()
                and root.name==sid,'Masks run root does not match its source scene')
        else:
            _require(build_root in root.parents and root.name==record.get('run_id'),'foreign fresh run root')
        _require(record.get('scene_id')==sid and record.get('session_id') and record.get('application_digest'),'fresh session identity missing')
        step=_target_step(scene)
        _require(record.get('step_id')==step['id'] and record.get('target_sha256')==_sha(_canonical({k:step[k] for k in ('inputs','expect','output')})),'fresh scene target changed')
        names=_required_sources(sid);pins=record.get('source_sha256',{})
        _require(set(pins)==names,'fresh source inventory differs')
        for name,pin in pins.items():
            path=root/name
            _require(root in path.resolve().parents and not path.is_symlink() and _sha(path.read_bytes())==pin,'fresh source changed: '+name)
        identity=json.loads((root/'native/identity.json').read_bytes())
        _require(identity.get('session_id')==record['session_id'] and identity.get('application_identity',{}).get('digest')==record['application_digest'],'fresh native identity changed')
        if sid in TARGET_PANIC | TARGET_PANIC_RELEASE | TARGET_MASKS:
            _require(Path(scene.get('evidence',{}).get('path','')).resolve()==root,'current scene does not name admitted fresh run')
        else:
            _require(_target_root(scene,project_root)==root,'current Doctor publication does not name fresh run')
    return records
def project_fresh_target_midi(scene, project_root, build_root, manifest, records=None):
    sid=scene.get('id')
    if sid not in TARGET_DOCTOR|TARGET_PANIC|TARGET_PANIC_RELEASE|TARGET_MASKS:
        return scene
    records=records or validate_fresh_target_midi_manifest([scene],project_root,build_root,manifest)
    record=records[sid];out_scene=copy.deepcopy(scene);root=Path(record['source_root'])
    if sid in TARGET_PANIC:
        ev=out_scene['evidence'];ev['path']=str(root)
        for name,key in [('results.json','results_sha256'),('native/identity.json','identity_sha256'),('native/native-events.jsonl','native_events_sha256'),('capture-trace.json','capture_trace_sha256'),('session-context.json','session_context_sha256')]:
            if name in record['source_sha256']:ev[key]=record['source_sha256'][name]
    result=(_doctor(out_scene,Path(project_root)) if sid in TARGET_DOCTOR else
        _panic_sounding_note(out_scene,project_root,build_root,manifest,record) if sid in TARGET_PANIC_RELEASE else
        _masks(out_scene,project_root,build_root,manifest,record,manifest['masks_stage']) if sid in TARGET_MASKS else _panic(out_scene))
    step=_target_step(result);receipt=step['output']['midi']
    receipt['provenance'].update(fresh_run_id=record['run_id'],fresh_build_id=manifest['build_id'],
        fresh_manifest_qualification=manifest['qualification'],fresh_source_sha256=record['source_sha256'],
        fresh_record_sha256=_sha(_canonical(record)))
    return result
def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--book',required=True,type=Path)
    parser.add_argument('--project-root',required=True,type=Path)
    parser.add_argument('--build-root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--qualification',choices=('fresh-candidate-pending-ci','derived-unit-fixture'),default='fresh-candidate-pending-ci')
    args=parser.parse_args()
    build_root=args.build_root.resolve()
    output=args.output.resolve()
    _require(build_root in output.parents,'fresh manifest output must be inside current build root')
    output.parent.mkdir(parents=True,exist_ok=True)
    book=json.loads(args.book.read_text())
    manifest=build_fresh_target_midi_manifest(list(book.get('scenes',{}).values()),args.project_root,build_root,args.qualification)
    output.write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n')
    print(json.dumps({'passed':True,'kind':MANIFEST_KIND,'qualification':manifest['qualification'],'scenes':len(manifest['scenes'])},sort_keys=True))
if __name__=='__main__':main()

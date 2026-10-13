"""Explicit retained Doctor/panic MIDI adapters; original observations only."""
import base64
import copy
import hashlib
import json
from pathlib import Path

class RetainedMidiError(ValueError):
    pass

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()

def _canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=False).encode('utf-8')

def _require(condition, message):
    if not condition:
        raise RetainedMidiError(message)

def _read(root, name, pin=None):
    raw=(root/name).read_bytes()
    _require(pin is None or _sha(raw)==pin,'changed retained source: '+name)
    return raw

def _native(root, pins, complete_snapshots):
    names=('results.json','observations.json','native/identity.json','native/native-events.jsonl')
    files={n:_read(root,n,pins.get(n)) for n in names}
    results=json.loads(files['results.json']); obs=json.loads(files['observations.json'])
    identity=json.loads(files['native/identity.json'])
    rows=[json.loads(v) for v in files['native/native-events.jsonl'].splitlines() if v.strip()]
    midi=[v for v in rows if v.get('kind') in (3,11)]
    _require(bool(midi) and [v['index'] for v in midi]==list(range(1,len(midi)+1)),'missing or unordered native MIDI')
    if midi[0]['kind']==11:
        _require([v.get('sequence') for v in midi]==list(range(1,len(midi)+1)),'native MIDI sequence changed')
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
    results,obs,identity,rows,midi,seen,hashes=_native(root,{},True)
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
    receipt=_receipt(window,midi,identity,hashes,binding,witness,'retained-doctor-original-play-window-v1',len(seen),pi)
    receipt['provenance'].update(historically_pinned_sources=['report.json'],newly_sealed_retained_sources=['results.json','observations.json','native/identity.json','native/native-events.jsonl'],window_lower_bound_exclusive=lo,window_upper_bound_inclusive=hi,scope='complete original observed Doctor play stage, including transport and releases')
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
    receipt=_receipt(window,midi,identity,hashes,binding,witness,'retained-panic-original-full-window-v1',len(seen),pi)
    receipt['provenance'].update(historically_pinned_sources=['results.json','native/identity.json','native/native-events.jsonl','capture-trace.json','session-context.json'],newly_sealed_retained_sources=['observations.json','panic-windows.json','captured-scenes.json'],original_window_receipt=w,window_lower_bound_exclusive=lo,window_upper_bound_inclusive=hi,scope='complete original observed 6144-packet panic sweep, with partial snapshot cross-check explicitly recorded')
    step['output']['midi']=receipt
    return out

def _validate_retained_target_admission(scene, project_root=None, admissions=None):
    sid=scene.get('id')
    doctor=sid in ('doctor-local-capture-and-paint','doctor-local-auto-capture-and-paint')
    panic=sid in ('panic-from-song-channel','panic-from-song-pattern')
    if not doctor and not panic:
        return None
    _require(isinstance(admissions,dict) and admissions.get('schema_version')==1 and admissions.get('kind')=='retained-target-midi-admission-v1','explicit retained MIDI admission required')
    _require(admissions.get('qualification') in ('retained-source-audit','derived-unit-fixture'),'unclassified admission')
    record=admissions.get('scenes',{}).get(sid)
    _require(isinstance(record,dict) and record.get('scene_id')==sid,'missing or foreign scene admission')
    root=Path(record['source_root'])
    _require(root.name==record['run_id'],'foreign run admission')
    if panic:
        _require(root.resolve()==Path(scene['evidence']['path']).resolve(),'foreign panic source root')
    else:
        _require(project_root is not None,'Doctor original publication root required')
        pub=json.loads((Path(project_root)/'manual'/scene['data_path']).read_bytes())
        _require(pub.get('publication_kind')=='doctor-native-audio','misclassified Doctor publication')
        matched=[r for r in pub['evidence']['runs'] if Path(r['report']).parent.resolve()==root.resolve() and r['report_sha256']==record['source_sha256'].get('report.json')]
        _require(len(matched)==1,'foreign Doctor report admission')
    required={'results.json','observations.json','native/identity.json','native/native-events.jsonl'}
    required |= {'report.json'} if doctor else {'captured-scenes.json','capture-trace.json','session-context.json','panic-windows.json'}
    _require(set(record['source_sha256'])==required,'retained source admission inventory differs')
    historical=record.get('historical_source_pins',{});sealed=record.get('newly_sealed_source_pins',{})
    _require(not set(historical)&set(sealed) and {**historical,**sealed}==record['source_sha256'],'source admission seal classification differs')
    needed={'report.json'} if doctor else {'results.json','native/identity.json','native/native-events.jsonl','capture-trace.json','session-context.json'}
    _require(needed<=set(historical),'historical source pins missing')
    for name,pin in record['source_sha256'].items():
        _read(root,name,pin)
    identity=json.loads((root/'native/identity.json').read_bytes())
    _require(identity['session_id']==record['session_id'] and identity['application_identity']['digest']==record['application_digest'],'foreign source/session admission')
    step=next(v for v in scene['steps'] if v['id']==record['step_id'])
    _require(record['step_id']==('play' if doctor else 'hold-and-release'),'foreign target admission')
    _require(_sha(_canonical({k:step[k] for k in ('inputs','expect','output')}))==record['target_sha256'],'changed target/frame admission')
    return doctor,record

def validate_retained_target_admissions(scenes, project_root, admissions):
    expected={s['id'] for s in scenes if s['id'] in ('doctor-local-capture-and-paint','doctor-local-auto-capture-and-paint','panic-from-song-channel','panic-from-song-pattern')}
    _require(isinstance(admissions,dict) and set(admissions.get('scenes',{}))==expected,'admission scene inventory differs from retained projection')
    for scene in scenes:
        _validate_retained_target_admission(scene,project_root,admissions)

def project_retained_target_midi(scene, project_root=None, admissions=None):
    admitted=_validate_retained_target_admission(scene,project_root,admissions)
    if admitted is None:
        return scene
    doctor,record=admitted
    output=_doctor(scene,Path(project_root)) if doctor else _panic(scene)
    receipt=next(v for v in output['steps'] if v['id']==record['step_id'])['output']['midi']
    receipt['provenance']['admission_qualification']=admissions['qualification']
    receipt['provenance']['admission_record_sha256']=_sha(_canonical(record))
    receipt['provenance']['historical_source_pins']=record['historical_source_pins']
    receipt['provenance']['newly_sealed_source_pins']=record['newly_sealed_source_pins']
    return output
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

def _native(root, pins, complete_snapshots):
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
    _require(all(a<b for a,b in zip(times,times[1:])),'native MIDI timestamps are duplicate or out of order')
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


TARGET_DOCTOR = {'doctor-local-capture-and-paint','doctor-local-auto-capture-and-paint'}
TARGET_PANIC = {'panic-from-song-channel','panic-from-song-pattern'}
MANIFEST_KIND = 'fresh-native-target-midi-v1'
def _target_step(scene):
    wanted = 'play' if scene['id'] in TARGET_DOCTOR else 'hold-and-release'
    steps = [step for step in scene.get('steps',[]) if step.get('id') == wanted]
    _require(len(steps)==1,'fresh target step is missing or duplicated')
    return steps[0]
def _target_root(scene, project_root):
    sid=scene['id']
    if sid in TARGET_PANIC:
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
        {'captured-scenes.json','capture-trace.json','session-context.json','panic-windows.json'})
def build_fresh_target_midi_manifest(scenes, project_root, build_root, qualification='fresh-candidate-pending-ci'):
    """Seal only target evidence produced beneath this build's evidence directory."""
    build_root=Path(build_root).resolve()
    _require(qualification in ('fresh-candidate-pending-ci','derived-unit-fixture'),'invalid fresh qualification label')
    targets=[scene for scene in scenes if scene.get('id') in TARGET_DOCTOR|TARGET_PANIC]
    expected={scene['id'] for scene in targets}
    _require(expected and len(expected)==len(targets),'fresh target scene inventory is empty or duplicated')
    records={}
    for scene in targets:
        sid=scene['id'];root=_target_root(scene,project_root).resolve()
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
        'complete_regression_run':False,'build_root':str(build_root),'build_id':build_root.name,'scenes':records}
def validate_fresh_target_midi_manifest(scenes, project_root, build_root, manifest):
    _require(isinstance(manifest,dict) and manifest.get('schema_version')==1 and manifest.get('kind')==MANIFEST_KIND,'fresh native target manifest is required')
    _require(manifest.get('qualification') in ('fresh-candidate-pending-ci','derived-unit-fixture'),'invalid fresh evidence qualification')
    build_root=Path(build_root).resolve()
    _require(Path(manifest.get('build_root','')).resolve()==build_root and manifest.get('build_id')==build_root.name,'foreign fresh build root')
    expected={scene['id'] for scene in scenes if scene.get('id') in TARGET_DOCTOR|TARGET_PANIC}
    records=manifest.get('scenes',{})
    _require(set(records)==expected,'fresh target scene inventory differs')
    by_id={scene['id']:scene for scene in scenes}
    for sid,record in records.items():
        scene=by_id[sid];root=Path(record.get('source_root','')).resolve()
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
        if sid in TARGET_PANIC:
            _require(Path(scene.get('evidence',{}).get('path','')).resolve()==root,'current Panic scene does not name fresh run')
        else:
            _require(_target_root(scene,project_root)==root,'current Doctor publication does not name fresh run')
    return records
def project_fresh_target_midi(scene, project_root, build_root, manifest, records=None):
    sid=scene.get('id')
    if sid not in TARGET_DOCTOR|TARGET_PANIC:
        return scene
    records=records or validate_fresh_target_midi_manifest([scene],project_root,build_root,manifest)
    record=records[sid];out_scene=copy.deepcopy(scene);root=Path(record['source_root'])
    if sid in TARGET_PANIC:
        ev=out_scene['evidence'];ev['path']=str(root)
        for name,key in [('results.json','results_sha256'),('native/identity.json','identity_sha256'),('native/native-events.jsonl','native_events_sha256'),('capture-trace.json','capture_trace_sha256'),('session-context.json','session_context_sha256')]:
            if name in record['source_sha256']:ev[key]=record['source_sha256'][name]
    result=_doctor(out_scene,Path(project_root)) if sid in TARGET_DOCTOR else _panic(out_scene)
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

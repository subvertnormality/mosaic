#!/usr/bin/env python3
"""Fail-closed staged qualification and optional transactional install.

Manifest contract matches combined-teaching-candidate: `files` pins before/after
hashes, `parsed_allowlist` lists {file,path,before,after,origin}, and candidate
copies live below --candidate-root. Exactly one caption row may append at
manual/scene-captions.yaml/overlays[106], targeting the approved chord-strum
step with its raw contract pin. A no-flag run is read-only outside --work;
installation requires --install and --reviewed-manifest-sha256 equal to the
manifest hash.
"""
import argparse, copy, hashlib, importlib.util, json, shutil, subprocess, sys, tempfile
from pathlib import Path
import yaml

ROOT=Path('/home/andy/mosaic-manual-1.4.0')
PUB=Path('/home/andy/mosaic-manual-build-operators/final-publication-source-snapshot-20261008-01/checkout')
RETAINED='8a5aca9c52ed89de06df6361b236a0b937c91045788c2c18c97c0b5ecca8446a'
CAPTION_TARGET=('chord-strum-a-timed-chord','assign-strum')
GEN='manual/generated'

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest_bytes(raw): return hashlib.sha256(raw).hexdigest()
def clone(value): return copy.deepcopy(value)
def jbytes(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def get_at(obj,path):
    for key in path: obj=obj[key]
    return obj
def set_at(obj,path,value):
    cur=obj
    for key in path[:-1]: cur=cur[key]
    cur[path[-1]]=value
def read_yaml(path): return yaml.load(Path(path).read_text(encoding='utf-8'), Loader=yaml.CSafeLoader)

def read_manifest(path):
    raw=Path(path).read_bytes(); m=json.loads(raw); allow=m.get('parsed_allowlist'); file_rows=m.get('files')
    if not isinstance(allow,list) or not allow or not isinstance(file_rows,list): raise ValueError('manifest requires parsed_allowlist and per-file before/after pins')
    files={row['path']:{'before_sha256':row['before_sha256'],'after_sha256':row['after_sha256']} for row in file_rows}
    rows=[]; caption_rows=[]
    for row in allow:
        if row.get('file')=='manual/scene-captions.yaml': caption_rows.append(row)
        else: rows.append({k:row[k] for k in ('file','path','before','after')})
    if len(caption_rows)!=1: raise ValueError('manifest must allow exactly one appended caption entry')
    caprow=caption_rows[0]; cap=caprow.get('after')
    if caprow.get('path')!=['overlays',106] or caprow.get('before') is not None: raise ValueError('caption manifest row must be a new overlay at the exact appended index')
    if not isinstance(cap,dict) or (cap.get('scene_id'),cap.get('step_id'))!=CAPTION_TARGET or set(cap)!={'scene_id','step_id','baseline_caption','caption','contract_sha256'}: raise ValueError('caption overlay must be the exact approved target and fields')
    seen=set(); changed=set()
    for r in rows:
        if not isinstance(r,dict) or set(r)!={'file','path','before','after'}: raise ValueError('source change rows must be {file,path,before,after}')
        f,p=r['file'],r['path']
        if not isinstance(f,str) or not f.startswith('manual/') or f=='manual/scene-captions.yaml' or '..' in Path(f).parts or not f.endswith('.yaml'): raise ValueError('unsafe or disallowed source file')
        if not isinstance(p,list) or not p or any(not isinstance(x,(int,str)) for x in p): raise ValueError('source path must be a nonempty key/index array')
        if not all(isinstance(r[k],str) for k in ('before','after')) or r['before']==r['after']: raise ValueError('only changed text scalar leaves are allowed')
        key=(f,tuple(p))
        if key in seen: raise ValueError('duplicate leaf allowlist')
        seen.add(key); changed.add(f)
    if set(files)!=changed|{'manual/scene-captions.yaml'}: raise ValueError('manifest files must name exactly changed YAML plus caption YAML')
    if len(m.get('parsed_allowlist',[]))!=len(rows)+1: raise ValueError('allowlist contains unsupported entries')
    m['_file_pins']=files; m['_caption_overlay']=cap
    return m,raw,rows,cap

def verify_sources(candidate,m,rows):
    grouped={}
    for r in rows: grouped.setdefault(r['file'],[]).append(r)
    for rel,items in grouped.items():
        before=read_yaml(ROOT/rel); after=read_yaml(candidate/rel); expected=clone(before)
        for r in items:
            if get_at(before,r['path'])!=r['before'] or get_at(after,r['path'])!=r['after']: raise ValueError('source leaf does not match pinned before/after: '+rel)
            set_at(expected,r['path'],r['after'])
        if expected!=after: raise ValueError('unlisted YAML change: '+rel)
        if digest(candidate/rel)!=m['_file_pins'][rel]['after_sha256']: raise ValueError('candidate hash mismatch: '+rel)
        if digest(ROOT/rel)!=m['_file_pins'][rel]['before_sha256']: raise ValueError('source preimage hash mismatch: '+rel)
    rel='manual/scene-captions.yaml'; before=read_yaml(ROOT/rel); after=read_yaml(candidate/rel)
    if before.get('schema_version')!=1 or after.get('schema_version')!=1: raise ValueError('caption schema changed')
    old=before.get('overlays',[]); new=after.get('overlays',[])
    if len(new)!=len(old)+1 or new[:-1]!=old: raise ValueError('caption source must append exactly one entry and preserve all old entries')
    entry=new[-1]
    if entry!=m['_caption_overlay']: raise ValueError('appended caption entry differs from manifest')
    if digest(candidate/rel)!=m['_file_pins'][rel]['after_sha256']: raise ValueError('caption source candidate hash mismatch')
    if digest(ROOT/rel)!=m['_file_pins'][rel]['before_sha256']: raise ValueError('caption source preimage hash mismatch')
    return sorted(grouped)+[rel]

def authoring_identity(root):
    sys.path[:0]=[str(root/'tools'),str(root/'tests/behaviour')]
    from manual_authority import authoring_identity as get_identity
    return get_identity(root)

def catalog_guard(root):
    raw={p.relative_to(root).as_posix():digest(p) for p in sorted((root/GEN).glob('*.json')) if p.name not in ('book.json','reader-index.json')}
    plans={p.relative_to(root).as_posix():digest(p) for p in sorted((root/'manual').glob('scene-plans*.yaml'))}
    return {'raw_catalogues':raw,'scene_plans':plans}

def preimage_guard():
    ri=authoring_identity(ROOT); pi=authoring_identity(PUB)
    if ri!=pi: raise ValueError('root/publication authored source identities differ')
    for rel in ('manual/generated/book.json','manual/generated/reader-index.json'):
        if digest(ROOT/rel)!=digest(PUB/rel): raise ValueError('generated preimage differs: '+rel)
    rchunks={p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/GEN/'reader-chunks').rglob('*') if p.is_file()}
    pchunks={p.relative_to(PUB).as_posix():digest(p) for p in (PUB/GEN/'reader-chunks').rglob('*') if p.is_file()}
    if rchunks!=pchunks: raise ValueError('root/publication reader-chunk preimages differ')
    return {'authoring_identity':ri,'book_sha256':digest(ROOT/GEN/'book.json'),'index_sha256':digest(ROOT/GEN/'reader-index.json'),'chunk_sha256':rchunks}

def stage_root(candidate,files,dest):
    dest.mkdir(parents=True)
    shutil.copytree(ROOT/'manual',dest/'manual',ignore=shutil.ignore_patterns('generated','evidence','images','audio'))
    (dest/'manual/generated').symlink_to(ROOT/'manual/generated',target_is_directory=True)
    if (ROOT/'manual/evidence').exists(): (dest/'manual/evidence').symlink_to(ROOT/'manual/evidence',target_is_directory=True)
    if (ROOT/'manual/audio').exists(): (dest/'manual/audio').symlink_to(ROOT/'manual/audio',target_is_directory=True)
    for rel in files:
        target=dest/rel; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(candidate/rel,target)
    # The compiler requires source references to resolve inside its own ROOT.
    # Copy only the actual referenced files, preserving the independent guard.
    required=set()
    for source in (dest/'manual/features').glob('*.yaml'):
        doc=read_yaml(source)
        features=doc.get('features',[])+([doc['feature']] if 'feature' in doc else [])
        for feature in features:
            required.update(feature.get('sources',{}).get('code',[]))
    reserved={Path(rel).parts[0] for rel in required}|{'.git','manual'}
    for item in ROOT.iterdir():
        if item.name in reserved or item.name.startswith('.pytest_cache'): continue
        (dest/item.name).symlink_to(item,target_is_directory=item.is_dir())
    for rel in sorted(required):
        source=(ROOT/rel).resolve()
        if ROOT not in source.parents or not source.is_file():
            raise ValueError('invalid source reference: '+rel)
        target=dest/rel
        if target.exists() and target.is_file() and digest(target)==digest(source): continue
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)

def compile_staged(stage):
    sys.path[:0]=[str(stage/'tools'),str(stage/'tests/behaviour')]
    spec=importlib.util.spec_from_file_location('staged_manual_book',ROOT/'tools/manual_book.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.ROOT=stage; mod.MANUAL=stage/'manual'
    mod.read=lambda path: yaml.load(Path(path).read_text(encoding='utf-8'),Loader=yaml.CSafeLoader)
    return mod.compile_book(mod.load())

def leaf_diffs(a,b,path=()):
    if type(a)!=type(b): return [path]
    if isinstance(a,dict):
        out=[]
        for key in set(a)|set(b):
            if key not in a or key not in b: out.append(path+(key,))
            else: out.extend(leaf_diffs(a[key],b[key],path+(key,)))
        return out
    if isinstance(a,list):
        if len(a)!=len(b): return [path+('<length>',)]
        return sum((leaf_diffs(x,y,path+(i,)) for i,(x,y) in enumerate(zip(a,b))),[])
    return [] if a==b else [path]

def book_allowlist(rows,book):
    ids={f['id']:i for i,f in enumerate(book['features'])}; out=set()
    for r in rows:
        p=r['path']
        if p and p[0]=='feature':
            source_doc=read_yaml(ROOT/r['file']); feature_id=source_doc['feature']['id']
            if feature_id not in ids: raise ValueError('source feature absent from compiled book: '+feature_id)
            out.add(('features',ids[feature_id],*p[1:]))
        elif len(p)>=2 and p[0]=='features' and isinstance(p[1],int):
            source_doc=read_yaml(ROOT/r['file'])
            feature_id=source_doc['features'][p[1]]['id']
            if feature_id not in ids: raise ValueError('source feature absent from compiled book: '+feature_id)
            out.add(('features',ids[feature_id],*p[2:]))
        elif len(p)>=2 and p[0]=='features' and p[1] in ids: out.add(('features',ids[p[1]],*p[2:]))
        elif p and p[0]=='course':
            key={'title':'course_title','summary':'course_summary'}.get(p[1],p[1])
            out.add((key,*p[2:]))
        elif len(p)>=2 and p[0]=='recordings' and isinstance(p[1],int):
            # recording context is compiled to a dict keyed by the stable audio ID.
            source_path=next(r['file'] for r in rows if r['path'][:2]==p[:2])
            recording_id=get_at(read_yaml(ROOT/source_path),p[:2])['id']
            out.add(('recordings_context','recordings',recording_id,*p[2:]))
            out.add(('recordings_context','source','sha256'))
        elif p and p[0]=='recordings': out.add(('recordings_context',*p[1:]))
        else: raise ValueError('unrecognized parsed source path: '+str(p))
    return out

def assert_only_diffs(old,new,allowed,label):
    diffs=leaf_diffs(old,new); extra=[p for p in diffs if p not in allowed]
    if extra: raise ValueError(f'{label} has unapproved changes: {extra[:10]}')
    if allowed-set(diffs): raise ValueError(f'{label} has unchanged allowlisted leaves: {list(allowed-set(diffs))[:10]}')

def check_scenes(old,new,cap):
    a=old['scenes']; b=new['scenes']; sid,stepid=CAPTION_TARGET
    if set(a)!=set(b) or len(b)!=146: raise ValueError('scene ID inventory differs from 146-scene baseline')
    for key in a:
        if key!=sid:
            if a[key]!=b[key]: raise ValueError('non-target scene changed: '+key)
            continue
        x=clone(a[key]); y=clone(b[key]); xs=[s for s in x['steps'] if s.get('id')==stepid]; ys=[s for s in y['steps'] if s.get('id')==stepid]
        if len(xs)!=1 or len(ys)!=1: raise ValueError('target step missing or duplicated')
        if xs[0].get('caption')!=cap['baseline_caption'] or ys[0].get('caption')!=cap['caption']: raise ValueError('caption baseline/text mismatch')
        expected={'original_caption_sha256':digest_bytes(cap['baseline_caption'].encode()),'caption_sha256':digest_bytes(cap['caption'].encode()),'contract_sha256':cap['contract_sha256']}
        if ys[0].get('caption_overlay')!=expected: raise ValueError('caption receipt mismatch')
        xs[0].pop('caption_overlay',None); ys[0].pop('caption_overlay',None); xs[0]['caption']=ys[0]['caption']
        if x!=y: raise ValueError('target scene native semantic diff outside caption and receipt')

def make_projection(book,work,label):
    from manual_reader_projection import build_projection,validate_projection,_canonical_bytes
    receipt=ROOT/'manual/evidence/retained-midi/retained-target-midi-admission-v1.json'
    if digest(receipt)!=RETAINED: raise ValueError('retained MIDI admission pin mismatch')
    bp=work/(label+'-book.json'); bp.write_text(json.dumps(book,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
    idx,chunks=build_projection(bp,ROOT/GEN/'audio-scenes.json',project_root=ROOT,retained_midi_admissions=receipt,retained_midi_admissions_sha256=RETAINED)
    if len(chunks)!=167: raise ValueError(f'projection has {len(chunks)} chunks, expected 167')
    out=work/(label+'-projection'); out.mkdir()
    for rel,raw in chunks.items():
        dest=out/rel; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(raw)
    ip=out/'reader-index.json'; ip.write_bytes(_canonical_bytes(idx))
    validate_projection(ip,out/'reader-chunks',bp,ROOT/GEN/'audio-scenes.json',project_root=ROOT,retained_midi_admissions=receipt,retained_midi_admissions_sha256=RETAINED)
    return idx,chunks,bp,ip

def checked_in_projection():
    root=ROOT/GEN; idx=json.loads((root/'reader-index.json').read_text(encoding='utf-8'))
    chunks={}
    for p in (root/'reader-chunks').rglob('*'):
        if p.is_file(): chunks[p.relative_to(root).as_posix()]=p.read_bytes()
    return idx,chunks

def native_contract_with_live_receipt(book,feature_id,lesson_id,receipt_key):
    sys.path.insert(0,str(ROOT/'tools'))
    import manual_teaching_v8 as producer
    features={f['id']:f for f in book['features']}; feature=features[feature_id]
    lesson=next(row for row in feature['teaching_bindings'] if row.get('id')==lesson_id)
    target=lesson['binding']; scene=book['scenes'][target['scene']]
    authored=lesson['teaching_binding']; req=authored['semantic_requires']
    native=producer._native(scene,authored['from_step_id'],target['step'],authored.get('transition_scope','adjacent'))
    if receipt_key=='player_device_readout_receipts':
        from manual_player_device_readout import validate_player_device_readout
        device=req['public_readout_equals']['device_configuration']
        native[receipt_key]=[validate_player_device_readout(scene,target['step'],device,ROOT)]
    elif receipt_key=='panic_release_receipts':
        from manual_panic_release_readout import validate_panic_release_readout
        native[receipt_key]=[validate_panic_release_readout(scene,target['step'],req['midi_events_at_target'],ROOT)]
    else: raise ValueError('unexpected current producer receipt kind')
    return native,producer.native_transition_hash(native)

def assert_current_index_rebase(checked,fresh,book):
    cases=(
        ('mods-and-software-devices','play-polyperc-apply-confirm','player_device_readout_receipts','manual_player_device_readout.py'),
        ('midi-panic','play-panic-stops-sounding-note-note-sounding','panic_release_receipts','manual_panic_release_readout.py'),
    )
    expected_paths=set(); producer_hashes={}
    for fid,lid,receipt_key,adapter_file in cases:
        feature_i=next(i for i,row in enumerate(fresh['features']) if row.get('id')==fid)
        lesson_i=next(i for i,row in enumerate(fresh['features'][feature_i]['teaching_bindings']) if row.get('id')==lid)
        contract_id=f'feature:{fid}:{lid}'
        feature_path=('features',feature_i,'teaching_bindings',lesson_i)
        contract_path=('teaching_contracts',contract_id)
        paths=(feature_path+('native_transition_contract_sha256',),
               feature_path+(receipt_key,0,'adapter_source_sha256'),
               contract_path+('native_transition_contract_sha256',),
               contract_path+(receipt_key,0,'adapter_source_sha256'))
        expected_paths.update(paths)
        old_receipt=get_at(checked,feature_path+(receipt_key,0)); new_receipt=get_at(fresh,feature_path+(receipt_key,0))
        old_without=clone(old_receipt); new_without=clone(new_receipt)
        old_adapter=old_without.pop('adapter_source_sha256'); new_adapter=new_without.pop('adapter_source_sha256')
        if old_without!=new_without: raise ValueError('current-producer receipt differs beyond its source hash: '+contract_id)
        sys.path.insert(0,str(ROOT/'tools'))
        module=__import__(adapter_file[:-3])
        actual_adapter=module._sha(ROOT/'tools'/adapter_file)
        if new_adapter!=actual_adapter: raise ValueError('live adapter hash does not equal the producer receipt: '+contract_id)
        native,current_native_hash=native_contract_with_live_receipt(book,fid,lid,receipt_key)
        if current_native_hash!=get_at(fresh,feature_path+('native_transition_contract_sha256',)):
            raise ValueError('native contract hash does not reproduce through the current producer: '+contract_id)
        prior_native=clone(native)
        prior_native[receipt_key][0]['adapter_source_sha256']=old_adapter
        prior_native_hash=__import__('manual_teaching_v8').native_transition_hash(prior_native)
        if prior_native_hash!=get_at(checked,feature_path+('native_transition_contract_sha256',)):
            raise ValueError('checked-in native hash is not explained solely by its previous adapter receipt: '+contract_id)
        producer_hashes[contract_id]={
            'adapter_file':'tools/'+adapter_file,'checked_in_adapter_source_sha256':old_adapter,
            'live_adapter_source_sha256':actual_adapter,'checked_in_native_transition_sha256':prior_native_hash,
            'live_native_transition_sha256':current_native_hash,
        }
        # The two duplicated projection locations must carry the same generated receipt values.
        for path in paths:
            if get_at(checked,path)==get_at(fresh,path): raise ValueError('expected current-producer rebase field did not change: '+str(path))
    actual_diffs=set(leaf_diffs(checked,fresh))
    if actual_diffs!=expected_paths:
        raise ValueError('checked-in/current-producer index diff differs from the exact eight receipt leaves: '+str(sorted(actual_diffs^expected_paths,key=str)))
    return {'difference_count':len(expected_paths),'changed_paths':[list(path) for path in sorted(expected_paths,key=str)],'producer_hashes':producer_hashes}

def exact_save_outcome_derivatives(rows,book,candidate_index):
    matches=[r for r in rows if r['path'][-2:]==['teaching_binding','human_outcome']]
    if len(matches)!=1: raise ValueError('expected the one save-and-load human_outcome source leaf')
    row=matches[0]; p=row['path']
    if row['file']!='manual/features/reference-locks.yaml' or p[0]!='features' or len(p)!=6 or p[2]!='teaching_bindings' or p[4:]!=['teaching_binding','human_outcome']:
        raise ValueError('human_outcome source leaf is outside the exact save-and-load lesson path')
    source_doc=read_yaml(ROOT/row['file']); fid=source_doc['features'][p[1]]['id']; source_lesson=source_doc['features'][p[1]]['teaching_bindings'][p[3]]['id']
    if (fid,source_lesson)!=('save-and-load','save-named-arrangement'):
        raise ValueError('human_outcome leaf owner changed from save-and-load/save-named-arrangement')
    feature_i=next(i for i,f in enumerate(book['features']) if f.get('id')==fid)
    book_lesson_i=next(i for i,l in enumerate(book['features'][feature_i].get('teaching_bindings',[])) if l.get('id')==source_lesson)
    lesson=book['features'][feature_i]['teaching_bindings'][book_lesson_i]
    if lesson.get('teaching_binding',{}).get('human_outcome')!=row['after']:
        raise ValueError('compiled source human_outcome differs from the manifest after-value')
    sys.path.insert(0,str(ROOT/'tools'))
    import manual_teaching_v8 as producer
    source,metadata,identity=producer.feature_presentation(fid,lesson)
    if source!={'feature_id':fid,'lesson_id':source_lesson} or metadata.get('human_outcome')!=row['after']:
        raise ValueError('feature_presentation did not derive the exact authored save outcome')
    if hashlib.sha256(json.dumps({'source':source,'metadata':metadata},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()!=identity:
        raise ValueError('presentation metadata hash does not reproduce through producer')
    projected_feature_i=next(i for i,f in enumerate(candidate_index['features']) if f.get('id')==fid)
    projected_lesson_i=next(i for i,l in enumerate(candidate_index['features'][projected_feature_i].get('teaching_bindings',[])) if l.get('id')==source_lesson)
    contract_id=f'feature:{fid}:{source_lesson}'
    projected=candidate_index['features'][projected_feature_i]['teaching_bindings'][projected_lesson_i]
    contract=candidate_index['teaching_contracts'][contract_id]
    for label,value in (('feature binding',projected),('teaching contract',contract)):
        if value.get('human_outcome')!=row['after'] or value.get('presentation_metadata')!=metadata or value.get('presentation_metadata_sha256')!=identity:
            raise ValueError(label+' does not match the actual feature_presentation result')
    feature_prefix=('features',projected_feature_i,'teaching_bindings',projected_lesson_i)
    contract_prefix=('teaching_contracts',contract_id)
    values={
      feature_prefix+('human_outcome',):row['after'],
      feature_prefix+('presentation_metadata','human_outcome'):row['after'],
      feature_prefix+('presentation_metadata_sha256',):identity,
      contract_prefix+('human_outcome',):row['after'],
      contract_prefix+('presentation_metadata','human_outcome'):row['after'],
      contract_prefix+('presentation_metadata_sha256',):identity,
    }
    return values,{'source_path':row['file'],'source_leaf':p,'feature_id':fid,'lesson_id':source_lesson,'presentation_metadata_sha256':identity,'derived_paths':[list(path) for path in values]}

def check_chunk_scene_semantics(oldidx,oldchunks,newidx,newchunks):
    old=oldidx['scene_chunks']; new=newidx['scene_chunks']; sid,stepid=CAPTION_TARGET
    if set(old)!=set(new) or len(new)!=146: raise ValueError('scene chunk index inventory differs')
    for scene in old:
        a=json.loads(oldchunks[old[scene]['path']]); b=json.loads(newchunks[new[scene]['path']])
        if scene!=sid:
            if a!=b: raise ValueError('non-target projected scene chunk changed: '+scene)
            continue
        aa=clone(a); bb=clone(b); x=next(s for s in aa['steps'] if s['id']==stepid); y=next(s for s in bb['steps'] if s['id']==stepid)
        x.pop('caption_overlay',None); y.pop('caption_overlay',None); x['caption']=y['caption']
        if aa!=bb: raise ValueError('target scene chunk has semantic changes beyond caption receipt')
    old_audio={k:v for k,v in oldchunks.items() if '/audio/' in k}; new_audio={k:v for k,v in newchunks.items() if '/audio/' in k}
    if old_audio!=new_audio: raise ValueError('audio chunks changed in text-only batch')

def check_projection_index(old,new,book_paths,cap,rows,candidate_book):
    a=clone(old); b=clone(new); sid,stepid=CAPTION_TARGET
    # Authored human text leaves are the only feature/course/recording content changes.
    for p in book_paths:
        if p[0]=='features':
            # Index feature rows have the same stable ordering as compiled book features.
            set_at(a,p,get_at(b,p))
        else:
            set_at(a,p,get_at(b,p))
    outcome_values,_=exact_save_outcome_derivatives(rows,candidate_book,b)
    for path,value in outcome_values.items(): set_at(a,path,value)
    if any(p[:1]==('recordings_context',) for p in book_paths):
        a['recordings_context']['source']['sha256']=b['recordings_context']['source']['sha256']
    # Expected provenance changes identify the staged authored bytes.
    for p in [('authoring_identity',),('source_sha256',),('canonical_inputs','book_json_sha256')]: set_at(a,p,get_at(b,p))
    # One caption and its content-addressed scene chunk reference may change.
    scene_a=a['scenes'][sid]; scene_b=b['scenes'][sid]
    sa=next(i for i,s in enumerate(scene_a['steps']) if s['id']==stepid); sb=next(i for i,s in enumerate(scene_b['steps']) if s['id']==stepid)
    if scene_a['steps'][sa].get('caption')!=cap['baseline_caption'] or scene_b['steps'][sb].get('caption')!=cap['caption']: raise ValueError('reader index caption does not match overlay')
    scene_a['steps'][sa]['caption']=scene_b['steps'][sb]['caption']
    for key in ('path','sha256'):
        a['scene_chunks'][sid][key]=b['scene_chunks'][sid][key]
    # Native contract remains the same; only the content-addressed scene receipt may change.
    for contract_id, new_contract in b.get('teaching_contracts',{}).items():
        if new_contract.get('scene_id')==sid:
            old_contract=a['teaching_contracts'][contract_id]
            old_contract['scene_chunk_sha256']=new_contract['scene_chunk_sha256']
    for i, feature in enumerate(b['features']):
        for j, lesson in enumerate(feature.get('teaching_bindings',[])):
            if lesson.get('scene_id')==sid:
                a['features'][i]['teaching_bindings'][j]['scene_chunk_sha256']=lesson['scene_chunk_sha256']
    if a!=b:
        extra=leaf_diffs(a,b)
        raise ValueError('reader index has changes outside allowlisted text/caption/provenance/receipt paths: '+str(extra[:12]))

def rollback(records,roots):
    for rootix,rel,existed,backup,oldsha in reversed(records):
        path=roots[rootix]/rel
        if existed:
            path.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(backup,path)
            if digest(path)!=oldsha: raise RuntimeError('rollback hash mismatch: '+str(path))
        elif path.exists(): path.unlink()

def transactional_install(candidate,files,bookpath,indexpath,chunks,work,guard):
    roots=[ROOT,PUB]
    if preimage_guard()!=guard['preimage']: raise ValueError('root/publication source or generated-output preimage drift before installation')
    if catalog_guard(ROOT)!=guard['root_catalogues'] or catalog_guard(PUB)!=guard['publication_catalogues']: raise ValueError('raw catalogue or scene-plan drift before installation')
    rels=set(files)|{GEN+'/book.json',GEN+'/reader-index.json'}
    expected_chunks={GEN+'/'+rel for rel in chunks}; existing={p.relative_to(ROOT).as_posix() for p in (ROOT/GEN/'reader-chunks').rglob('*') if p.is_file()}
    rels|=existing|expected_chunks
    if GEN+'/audio-scenes.json' in rels: raise ValueError('refusing to mutate audio-scenes')
    backuproot=work/'preimage-backup'; records=[]
    for i,r in enumerate(roots):
        for rel in sorted(rels):
            p=r/rel; existed=p.is_file(); backup=backuproot/str(i)/rel if existed else None
            oldsha=digest(p) if existed else None
            if existed: backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(p,backup)
            records.append((i,rel,existed,backup,oldsha))
    try:
        for r in roots:
            for rel in files:
                dest=r/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(candidate/rel,dest)
            shutil.copy2(bookpath,r/GEN/'book.json'); shutil.copy2(indexpath,r/GEN/'reader-index.json')
            chunkroot=r/GEN/'reader-chunks'
            for p in chunkroot.rglob('*'):
                if p.is_file() and p.relative_to(r).as_posix() not in expected_chunks: p.unlink()
            for rel,raw in chunks.items():
                dest=r/GEN/rel; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(raw)
        from manual_reader_projection import validate_projection
        receipt=ROOT/'manual/evidence/retained-midi/retained-target-midi-admission-v1.json'
        kwargs=dict(project_root=ROOT,retained_midi_admissions=receipt,retained_midi_admissions_sha256=RETAINED)
        for r in roots: validate_projection(r/GEN/'reader-index.json',r/GEN/'reader-chunks',r/GEN/'book.json',ROOT/GEN/'audio-scenes.json',**kwargs)
        from manual_authority import authoring_identity
        book=json.loads((ROOT/GEN/'book.json').read_text())
        if authoring_identity(ROOT)!=book['authoring_identity'] or authoring_identity(PUB)!=book['authoring_identity']: raise ValueError('post-install authoring identity mismatch')
        if catalog_guard(ROOT)!=guard['root_catalogues'] or catalog_guard(PUB)!=guard['publication_catalogues']: raise ValueError('catalogue/scene-plan changed during install')
        return {'installed':True,'rollback_files_per_root':len(rels),'publication_audio_scenes_used':False}
    except BaseException:
        rollback(records,roots)
        raise

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',required=True,type=Path); ap.add_argument('--candidate-root',required=True,type=Path); ap.add_argument('--work',required=True,type=Path); ap.add_argument('--install',action='store_true'); ap.add_argument('--reviewed-manifest-sha256')
    args=ap.parse_args(); manifest_path=args.manifest.resolve(); candidate=args.candidate_root.resolve(); work=args.work.resolve()
    manifest,raw,rows,cap=read_manifest(manifest_path); mh=digest_bytes(raw)
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    if manifest.get('source_commit')!=head: raise SystemExit('candidate source_commit does not match authoritative checkout HEAD')
    scene_plan=ROOT/'manual/scene-plans.yaml'
    if digest(scene_plan)!=manifest.get('scene_plan_sha256_unchanged'): raise SystemExit('authoritative scene-plan source pin mismatch')
    if args.install and args.reviewed_manifest_sha256!=mh: raise SystemExit('install requires the exact reviewed manifest SHA-256')
    if work.exists() or not work.parent.is_dir(): raise SystemExit('work path must be a fresh child of an existing external directory')
    pre=preimage_guard(); guard={'root_catalogues':catalog_guard(ROOT),'publication_catalogues':catalog_guard(PUB)}
    files=verify_sources(candidate,manifest,rows); listed=set(manifest['_file_pins']); actual={p.relative_to(candidate).as_posix() for p in candidate.rglob('*') if p.is_file()}
    if actual!=listed: raise SystemExit(f'candidate file set mismatch: extra={sorted(actual-listed)} missing={sorted(listed-actual)}')
    work.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='mosaic-text-stage-',dir=str(work.parent)) as temp:
        stage=Path(temp)/'root'; stage_root(candidate,files,stage); book=compile_staged(stage)
        old=json.loads((ROOT/GEN/'book.json').read_text(encoding='utf-8')); allowed=book_allowlist(rows,book)
        a=clone(old); b=clone(book)
        for item in (a,b): item.pop('authoring_identity',None); item.pop('source_sha256',None); item.pop('scenes',None)
        assert_only_diffs(a,b,allowed,'compiled book'); check_scenes(old,book,cap)
        checked_idx,checked_chunks=checked_in_projection()
        base_idx,base_chunks,base_bookpath,base_indexpath=make_projection(old,work,'current-base')
        producer_rebase=assert_current_index_rebase(checked_idx,base_idx,old)
        if checked_chunks!=base_chunks: raise ValueError('current-producer base chunks are not byte-identical to the checked-in native/audio chunks')
        old_index_raw=(ROOT/GEN/'reader-index.json').read_bytes(); base_index_raw=base_indexpath.read_bytes()
        rebase_paths=[]
        for path in producer_rebase['changed_paths']:
            p=tuple(path); rebase_paths.append({'path':path,'checked_in_value':get_at(checked_idx,p),'current_producer_value':get_at(base_idx,p)})
        rebase_report={'checked_in_book_sha256':digest(ROOT/GEN/'book.json'),'checked_in_index_sha256':digest_bytes(old_index_raw),'current_base_book_sha256':digest(base_bookpath),'current_base_index_sha256':digest_bytes(base_index_raw),'retained_midi_admission_sha256':RETAINED,'root_audio_scenes_sha256':digest(ROOT/GEN/'audio-scenes.json'),'current_base_projection_chunks':len(base_chunks),'full_validate_projection_passed':True,'all_167_current_base_chunks_byte_identical_to_checked_in':True,'native_scene_and_audio_chunk_semantics_unchanged':True,'exact_rebase_leaf_count':producer_rebase['difference_count'],'exact_rebase_leaves':rebase_paths,'producer_recomputed_receipts':producer_rebase['producer_hashes']}
        (work/'current-base-rebase.json').write_text(json.dumps(rebase_report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        idx,chunks,bp,ip=make_projection(book,work,'candidate')
        check_chunk_scene_semantics(base_idx,base_chunks,idx,chunks); outcome_derivatives,save_outcome_proof=exact_save_outcome_derivatives(rows,book,idx); check_projection_index(base_idx,idx,allowed,cap,rows,book)
        if catalog_guard(ROOT)!=guard['root_catalogues'] or catalog_guard(PUB)!=guard['publication_catalogues']: raise ValueError('raw catalog/scene-plan drift during qualification')
        report={'manifest_sha256':mh,'candidate_files':manifest['_file_pins'],'authored_leaf_changes':len(rows),'preimage_authoring_identity':pre['authoring_identity']['sha256'],'staged_authoring_identity':book['authoring_identity']['sha256'],'scene_count':len(book['scenes']),'scene_native_semantic_parity':True,'projection_chunks':len(chunks),'full_validate_projection':True,'retained_midi_admission_sha256':RETAINED,'raw_catalogues_and_scene_plans_unchanged':True,'root_audio_scenes_sha256':digest(ROOT/GEN/'audio-scenes.json'),'current_base_rebase_report':'current-base-rebase.json','save_outcome_derivative_proof':save_outcome_proof,'save_outcome_derived_leaf_count':len(outcome_derivatives),'publication_audio_scenes_used':False,'audio_scenes_copied':False,'install_requested':args.install}
        (work/'qualification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        if args.install:
            result=transactional_install(candidate,files,bp,ip,chunks,work,{'preimage':pre,**guard}); report['installation']=result
            report['postinstall_identity_root']=authoring_identity(ROOT)['sha256']; report['postinstall_identity_publication']=authoring_identity(PUB)['sha256']
            (work/'qualification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__': main()

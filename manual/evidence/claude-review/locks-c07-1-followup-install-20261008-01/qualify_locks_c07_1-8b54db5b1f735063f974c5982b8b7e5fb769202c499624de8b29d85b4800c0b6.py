#!/usr/bin/env python3
"""Narrow staged compiler/projection gate and optional rollback-safe install for C07-1.

Unlike qualify_text_batch.py, this contract accepts exactly three authored text
leaves and no caption rows. The staged gate is strict: only the three allowlisted recipe text leaves
and derived authoring/source hashes may change in book/index output; all 146 scenes
and all 167 generated chunks must remain identical. Installation requires the
exact reviewed manifest SHA and writes to both roots with backups and rollback.
"""
import argparse,copy,hashlib,importlib.util,json,shutil,subprocess,tempfile
from pathlib import Path
import yaml

ROOT=Path('/home/andy/mosaic-manual-1.4.0')
PUB=Path('/home/andy/mosaic-manual-build-operators/final-publication-source-snapshot-20261008-01/checkout')
VIS=Path('/mnt/c/Users/andy/.codex/visualizations/2026/10/03/01a100e0-e188-7c11-b2f0-748214517bb6')
HELPER=VIS/'qualify_text_batch.py'
GEN='manual/generated'
EXPECTED_HEAD='1867886ca2f39e3aff99cea19133e83b9c0cdd44'
EXPECTED_BOOK='38beead5d88faa3a5aa1a5a0fc27c25796308c4d84bd831060035fe5085ef89f'
EXPECTED_INDEX='73dc1ddb8952ca590cb9d670ee3a145ee460a68ec27f3259c1a08e28283323ca'
EXPECTED_AUDIO_SOURCE='ffc775971ce1fa3bfca8ba55c1059798519cd4a82241eb8827e9852afeebcd74'
EXPECTED_AUDIO_SCENES={str(ROOT):'3396e9e75f11dd66482fb85c3dc58997efdcb591801c37622dcd49a1ff1fe0bd',str(PUB):'22d4fe42d42e100d219f14f935234ab81e66cfd7551caad89a7a42e041003a7e'}
EXPECTED_AUTHORING='9d5e81b8776366aae0f9460d59bfe3d5f0d02e337d3188e965a143491d88e053'
EXPECTED_HELPER='7752cf769fa71e8b1566039fb89b7b2af1b454ca61aafbd984b8264e117c92dd'
TARGET_FILE='manual/features/reference-locks.yaml'
TARGET_PATH=['features',0,'recipes',4,'text']

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read_yaml(path): return yaml.load(Path(path).read_text(encoding='utf-8'),Loader=yaml.CSafeLoader)
def at(value,path):
    for part in path: value=value[part]
    return value
def load_helper():
    if digest(HELPER)!=EXPECTED_HELPER: raise ValueError('staged helper source hash changed')
    spec=importlib.util.spec_from_file_location('guarded_text_batch',HELPER)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
def sha_bytes(raw): return hashlib.sha256(raw).hexdigest()
def verify_manifest(manifest_path,candidate):
    raw=manifest_path.read_bytes(); m=json.loads(raw)
    if m.get('source_commit')!=EXPECTED_HEAD: raise ValueError('source commit is not the reviewed C07 baseline')
    if m.get('scene_plan_sha256_unchanged')!=digest(ROOT/'manual/scene-plans.yaml'): raise ValueError('scene-plan source changed')
    rows=m.get('parsed_allowlist'); files=m.get('files')
    if not isinstance(rows,list) or len(rows)!=3: raise ValueError('expected exactly three text leaf rows')
    if not isinstance(files,list) or {x['path'] for x in files}!={TARGET_FILE,'manual/features/cookbook.yaml'}: raise ValueError('candidate must contain only the two authorized YAML files')
    expected={(TARGET_FILE,tuple(TARGET_PATH)),('manual/features/cookbook.yaml',('features',0,'recipes',1,'text')),('manual/features/cookbook.yaml',('features',0,'recipes',2,'text'))}
    actual={(r.get('file'),tuple(r.get('path',[]))) for r in rows}
    if actual!=expected: raise ValueError(f'allowlist differs from the exact 3-leaf contract: {actual ^ expected}')
    if any('manual/scene-captions.yaml' in row.get('file','') for row in rows): raise ValueError('caption changes are not allowed')
    for record in files:
        rel=record['path']; src=ROOT/rel; dst=candidate/rel
        if digest(src)!=record['before_sha256'] or digest(dst)!=record['after_sha256']: raise ValueError('source/candidate file hash mismatch: '+rel)
    for row in rows:
        if row['before']==row['after']: raise ValueError('unchanged leaf in allowlist')
        if at(read_yaml(ROOT/row['file']),row['path'])!=row['before']: raise ValueError('source leaf preimage mismatch')
        if at(read_yaml(candidate/row['file']),row['path'])!=row['after']: raise ValueError('candidate leaf value mismatch')
    for rel in sorted({r['file'] for r in rows}):
        before=read_yaml(ROOT/rel); after=read_yaml(candidate/rel); expected_doc=copy.deepcopy(before)
        for row in rows:
            if row['file']==rel:
                cur=expected_doc
                for part in row['path'][:-1]: cur=cur[part]
                cur[row['path'][-1]]=row['after']
        if expected_doc!=after: raise ValueError('unlisted YAML semantic change: '+rel)
    listed={x['path'] for x in files}
    present={p.relative_to(candidate).as_posix() for p in candidate.rglob('*') if p.is_file()}
    if present!=listed: raise ValueError(f'candidate file inventory mismatch: {present ^ listed}')
    return m,raw,rows,files

def find_feature(index):
    ids=[f.get('id') for f in index.get('features',[])]
    if ids.count('locks')!=1: raise ValueError('compiled locks feature missing or duplicated')
    return ids.index('locks')
def source_feature_id(row):
    doc=read_yaml(ROOT/row['file']); path=row['path']
    if len(path)<4 or path[0]!='features': raise ValueError('expected feature recipe leaf')
    return doc['features'][path[1]]['id']
def compiled_path(row,doc):
    fid=source_feature_id(row); ids=[f.get('id') for f in doc.get('features',[])]
    if ids.count(fid)!=1: raise ValueError('compiled feature missing/duplicated: '+fid)
    return ['features',ids.index(fid)]+row['path'][2:]
def strict_index_compare(base,candidate,rows,changed_file_hashes,old_book_sha,new_book_sha):
    bi=copy.deepcopy(base); ci=copy.deepcopy(candidate)
    for i,row in enumerate(rows):
        bp=compiled_path(row,bi); cp=compiled_path(row,ci)
        if at(bi,bp)!=row['before'] or at(ci,cp)!=row['after']: raise ValueError('projected recipe leaf pre/postimage mismatch')
        for obj,path in ((bi,bp),(ci,cp)):
            cur=obj
            for part in path[:-1]: cur=cur[part]
            cur[path[-1]]='__AUTHORIZED_RECIPE_TEXT_%d__'%i
    for key in ('source_sha256',):
        if key not in bi or key not in ci or bi[key]==ci[key]: raise ValueError('expected derived source hash did not change: '+key)
        ci[key]=bi[key]
    ba=bi.get('authoring_identity'); ca=ci.get('authoring_identity')
    if not isinstance(ba,dict) or not isinstance(ca,dict): raise ValueError('index authoring identity missing')
    changed=set(changed_file_hashes)
    if changed!={'manual/features/reference-locks.yaml','manual/features/cookbook.yaml'}: raise ValueError('unexpected authoring input set')
    if ba.get('files',{}).keys()!=ca.get('files',{}).keys(): raise ValueError('authoring identity file set changed')
    for key,old_hash in ba['files'].items():
        if key in changed:
            if ca['files'].get(key)!=changed_file_hashes[key] or ca['files'].get(key)==old_hash: raise ValueError('changed authoring source hash mismatch: '+key)
        elif ca['files'][key]!=old_hash: raise ValueError('unrelated authoring source hash changed: '+key)
    if ba.get('sha256')==ca.get('sha256'): raise ValueError('authoring identity digest did not change')
    for key in changed: ca['files'][key]=ba['files'][key]
    ca['sha256']=ba['sha256']
    bc=bi.get('canonical_inputs'); cc=ci.get('canonical_inputs')
    if not isinstance(bc,dict) or not isinstance(cc,dict) or bc.keys()!=cc.keys(): raise ValueError('canonical input set changed')
    if bc.get('book_json_sha256')!=old_book_sha or cc.get('book_json_sha256')!=new_book_sha or bc['book_json_sha256']==cc['book_json_sha256']:
        raise ValueError('canonical_inputs.book_json_sha256 is not the exact baseline/candidate book hash')
    cc['book_json_sha256']=bc['book_json_sha256']
    if bi!=ci: raise ValueError('reader index contains unapproved differences beyond the three recipe leaves and derived source/authoring/book hashes')
def qualify(manifest_path,candidate,work,install,reviewed_sha):
    manifest_path=manifest_path.resolve(); candidate=candidate.resolve(); work=work.resolve()
    m,raw,rows,file_records=verify_manifest(manifest_path,candidate); mh=sha_bytes(raw)
    if install and reviewed_sha!=mh: raise ValueError('install requires exact reviewed manifest SHA-256')
    if work.exists() or not work.parent.is_dir(): raise ValueError('work path must be a fresh external child')
    head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    if head!=EXPECTED_HEAD: raise ValueError('authoritative HEAD changed')
    for root in (ROOT,PUB):
        for rec in file_records:
            if digest(root/rec['path'])!=rec['before_sha256']: raise ValueError('root/publication source preimage differs: '+str(root/rec['path']))
        if digest(root/(GEN+'/book.json'))!=EXPECTED_BOOK or digest(root/(GEN+'/reader-index.json'))!=EXPECTED_INDEX: raise ValueError('root/publication generated preimage differs')
        if digest(root/'manual/audio-scenes.yaml')!=EXPECTED_AUDIO_SOURCE or digest(root/(GEN+'/audio-scenes.json'))!=EXPECTED_AUDIO_SCENES[str(root)] or digest(root/'manual/scene-plans.yaml')!=m['scene_plan_sha256_unchanged']: raise ValueError('root/publication audio source/generated output or scene-plan pin differs')
        book=json.loads((root/(GEN+'/book.json')).read_text(encoding='utf-8'))
        if book['authoring_identity']['sha256']!=EXPECTED_AUTHORING or len(book['scenes'])!=146: raise ValueError('root/publication authoring identity or scene inventory differs')
        index=json.loads((root/(GEN+'/reader-index.json')).read_text(encoding='utf-8'))
        chunks={p.relative_to(root/(GEN+'/reader-chunks')).as_posix():digest(p) for p in (root/(GEN+'/reader-chunks')).rglob('*') if p.is_file()}
        if len(chunks)!=167: raise ValueError('root/publication must have exactly 167 existing chunks')
        if chunks!=m['generated_preimage_both_roots']['chunk_sha256']: raise ValueError('root/publication chunk hashes differ from sealed current preimage')
        if root==ROOT: root_chunks=chunks
        elif chunks!=root_chunks: raise ValueError('root/publication chunk preimages differ')
        if index.get('authoring_identity',{}).get('sha256')!=EXPECTED_AUTHORING: raise ValueError('index authoring identity preimage differs')
    work.mkdir(parents=True)
    helper=load_helper()
    preimage=helper.preimage_guard(); guard={'preimage':preimage,'root_catalogues':helper.catalog_guard(ROOT),'publication_catalogues':helper.catalog_guard(PUB)}
    with tempfile.TemporaryDirectory(prefix='locks-c07-1-stage-',dir=str(work.parent)) as td:
        stage=Path(td)/'stage'; helper.stage_root(candidate,[r['path'] for r in file_records],stage)
        compiled=helper.compile_staged(stage)
        old=json.loads((ROOT/(GEN+'/book.json')).read_text(encoding='utf-8'))
        lock_i=find_feature(old)
        if at(old,['features',lock_i,'recipes',4,'text'])!=rows[0]['before']: raise ValueError('compiled-book source preimage differs')
        if at(compiled,['features',lock_i,'recipes',4,'text'])!=rows[0]['after']: raise ValueError('compiled book did not include the recipe update')
        if len(compiled.get('scenes',{}))!=146 or compiled['scenes']!=old['scenes']: raise ValueError('scene/native semantics changed')
        if compiled.get('authoring_identity',{}).get('files',{}).get(TARGET_FILE)!=file_records[0]['after_sha256']: raise ValueError('compiled authoring source hash mismatch')
        # Only the two edited authoring inputs may change in the identity file map; all other input hashes remain pinned.
        before_identity=old['authoring_identity']; after_identity=compiled['authoring_identity']; changed_input_hashes={r['path']:r['after_sha256'] for r in file_records}
        if before_identity['files'].keys()!=after_identity['files'].keys(): raise ValueError('authoring identity input set changed')
        for key,old_hash in before_identity['files'].items():
            if key in changed_input_hashes:
                if after_identity['files'][key]!=changed_input_hashes[key] or after_identity['files'][key]==old_hash: raise ValueError('authoring identity changed input does not match candidate: '+key)
            elif after_identity['files'][key]!=old_hash: raise ValueError('unrelated authoring input hash changed: '+key)
        if before_identity['sha256']==after_identity['sha256']: raise ValueError('derived authoring identity did not change')
        # Normalize only the three authored text leaves and exact derived source/authoring hashes.
        old_n=copy.deepcopy(old); new_n=copy.deepcopy(compiled)
        changed_hashes={r['path']:r['after_sha256'] for r in file_records}
        if set(changed_hashes)!={'manual/features/reference-locks.yaml','manual/features/cookbook.yaml'}: raise ValueError('unexpected compiled source file set')
        before_identity=old['authoring_identity']; after_identity=compiled['authoring_identity']
        if before_identity['files'].keys()!=after_identity['files'].keys(): raise ValueError('authoring identity input set changed')
        for key,old_hash in before_identity['files'].items():
            if key in changed_hashes:
                if after_identity['files'][key]!=changed_hashes[key] or after_identity['files'][key]==old_hash: raise ValueError('changed authoring identity hash mismatch: '+key)
            elif after_identity['files'][key]!=old_hash: raise ValueError('unrelated authoring identity file hash changed: '+key)
        if before_identity['sha256']==after_identity['sha256']: raise ValueError('derived authoring identity did not change')
        for row in rows:
            old_path=compiled_path(row,old_n); new_path=compiled_path(row,new_n)
            if at(old_n,old_path)!=row['before'] or at(new_n,new_path)!=row['after']: raise ValueError('compiled-book recipe leaf mismatch')
            cur=old_n
            for part in old_path[:-1]: cur=cur[part]
            cur[old_path[-1]]=row['after']
        for obj in (old_n,new_n):
            obj.pop('authoring_identity',None); obj.pop('source_sha256',None)
        if old_n!=new_n: raise ValueError('compiled book has unapproved semantic differences')        # Use the producer's real projection builder and validator for baseline and candidate.
        old_idx,old_chunks,old_bp,old_ip=helper.make_projection(old,work,'current-base')
        checked_idx,checked_chunks=helper.checked_in_projection()
        if old_idx!=checked_idx or old_chunks!=checked_chunks: raise ValueError('current producer base differs from checked-in index/chunks')
        new_idx,new_chunks,new_bp,new_ip=helper.make_projection(compiled,work,'candidate')
        if len(new_chunks)!=167 or new_chunks!=old_chunks: raise ValueError('candidate changes native/audio chunk bytes or inventory')
        strict_index_compare(old_idx,new_idx,rows,{r['path']:r['after_sha256'] for r in file_records},digest(old_bp),digest(new_bp))
        if new_idx.get('authoring_identity')!=compiled.get('authoring_identity') or new_idx.get('source_sha256')!=compiled.get('source_sha256'): raise ValueError('projection identity/source hash differs from compiled book')
        report={'manifest_sha256':mh,'source_commit':head,'changed_text_leaves':3,'candidate_files':[{'path':x['path'],'before_sha256':x['before_sha256'],'after_sha256':x['after_sha256']} for x in file_records],'compiled_book_semantic_diff':'exact three recipe text leaves plus derived authoring_identity/source_sha256 only','scene_count':146,'all_scenes_exact':True,'chunk_count':167,'all_chunks_byte_identical':True,'index_diff':'exact three recipe text leaves plus derived authoring_identity/source_sha256/canonical_inputs.book_json_sha256 only','caption_changes':0,'native_audio_runs':0,'install_requested':install}
        (work/'qualification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        if install:
            helper.transactional_install(candidate,[r['path'] for r in file_records],new_bp,new_ip,new_chunks,work,guard)
            report['installation']={'installed_to':[str(ROOT),str(PUB)],'rollback_backup':str(work/'preimage-backup')}
            (work/'qualification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2,ensure_ascii=False))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--manifest',required=True,type=Path); ap.add_argument('--candidate-root',required=True,type=Path); ap.add_argument('--work',required=True,type=Path)
    ap.add_argument('--install',action='store_true'); ap.add_argument('--reviewed-manifest-sha256')
    a=ap.parse_args(); qualify(a.manifest,a.candidate_root,a.work,a.install,a.reviewed_manifest_sha256)
if __name__=='__main__': main()

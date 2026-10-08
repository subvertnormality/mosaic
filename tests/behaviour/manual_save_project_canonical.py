"""Complete stock decoded-content equality; no field/value normalization."""
from pathlib import Path
import hashlib,json,subprocess
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(path, fixture, oracle):
    fixture=Path(fixture);oracle=Path(oracle)
    if digest(oracle)!='1704dd05df57a472b3351abd0e01a8361d9d2538df988bc64668792de5fe32f7':raise ValueError('Changed stock decoded-content oracle')
    runtime=json.loads((fixture/'CANONICAL-RUNTIME.json').read_text())
    for item in [runtime['binary']]+runtime['libraries']:
        if digest(item['path'])!=item['sha256']:raise ValueError('Changed invoked Lua runtime identity')
    tab=fixture/runtime['tabutil']['relative']
    if digest(tab)!=runtime['tabutil']['sha256']:raise ValueError('Changed invoked cached tabutil source')
    return subprocess.check_output([runtime['binary']['path'],str(oracle),str(fixture/'canonical-runtime'),str(path)])
def prove(saved, original, fixture, oracle):
    before=canonical(original,fixture,oracle);after=canonical(saved,fixture,oracle)
    if before!=after:raise ValueError('Changed complete decoded project content')
    return dict(original_byte_sha256=digest(original),observed_byte_sha256=digest(saved),decoded_sha256=hashlib.sha256(before).hexdigest(),decoded_bytes=len(before),oracle_sha256=digest(oracle),runtime_manifest_sha256=digest(Path(fixture)/'CANONICAL-RUNTIME.json'))

"""Explicit retained projection caller inputs and exact producer/source fence."""
import hashlib
import json
from pathlib import Path

RECEIPT_RELATIVE_PATH='manual/evidence/retained-midi/retained-target-midi-admission-v1.json'
REQUIRED_RETAINED_PRODUCERS={'tools/manual_reader_projection.py','tools/manual_retained_target_midi.py','tools/manual_retained_midi_caller.py'}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def required_producer_inventory(root, retained=None):
    root=Path(root)
    required={p.relative_to(root).as_posix() for p in (root/'tools').glob('manual_*.py')}
    required.update(('tools/resume_adoption.py','tools/manual_reconcile_build.py'))
    if retained:
        required.update(REQUIRED_RETAINED_PRODUCERS)
        required.add(retained['relative_path'])
    return required

def validate_producer_sources(root, producer_hashes, retained=None):
    root=Path(root)
    required=required_producer_inventory(root,retained)
    if set(producer_hashes)!=required:
        raise ValueError('Producer source fence inventory differs')
    for name,pin in producer_hashes.items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or not (root/path).is_file() or sha(root/path)!=pin:
            raise ValueError('Producer source fence changed: '+name)
    if retained and producer_hashes[retained['relative_path']]!=retained['sha256']:
        raise ValueError('Retained receipt differs from producer source fence')

def retained_call(root, receipt=None, receipt_sha256=None, *, mode='fresh'):
    root=Path(root).resolve()
    if bool(receipt)!=bool(receipt_sha256):
        raise ValueError('Retained receipt and literal SHA must be supplied together')
    if mode not in ('fresh','retained-resume','retained-standalone'):
        raise ValueError('Unknown projection source mode')
    if mode=='fresh':
        if receipt:raise ValueError('Fresh native generation cannot adopt retained MIDI runs')
        return None
    if not receipt:raise ValueError('Retained projection mode requires explicit receipt and SHA')
    path=Path(receipt);path=path if path.is_absolute() else root/path
    path=path.resolve()
    if path!=root/RECEIPT_RELATIVE_PATH or not path.is_file():
        raise ValueError('Retained receipt must be the tracked reviewed receipt path')
    if sha(path)!=receipt_sha256:
        raise ValueError('Retained caller receipt changed')
    data=json.loads(path.read_text())
    if data.get('schema_version')!=1 or data.get('kind')!='retained-target-midi-admission-v1' or data.get('qualification')!='retained-source-audit':
        raise ValueError('Caller receipt is not a reviewed retained-source audit')
    return {'mode':mode,'relative_path':RECEIPT_RELATIVE_PATH,'sha256':receipt_sha256}

def projection_arguments(root, retained):
    if not retained:return []
    path=Path(root)/retained['relative_path']
    if not path.is_file() or sha(path)!=retained['sha256']:
        raise ValueError('Retained projection receipt changed after planning')
    return ['--retained-midi-admissions',str(path),'--retained-midi-admissions-sha256',retained['sha256']]

def archive_retained_call(root,evidence,retained,producer_hashes):
    if not retained:return None
    validate_producer_sources(root,producer_hashes,retained)
    raw=(Path(root)/retained['relative_path']).read_bytes()
    target=Path(evidence)/'producer-inputs'/retained['relative_path'];target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as f:f.write(raw)
    return dict(retained,archive_relative_path=target.relative_to(evidence).as_posix())

def audit_retained_call(root,evidence,retained,producer_hashes):
    if not retained:return
    checked=retained_call(root,retained['relative_path'],retained['sha256'],mode=retained['mode'])
    if any(checked[k]!=retained[k] for k in checked):raise ValueError('Retained caller identity changed')
    validate_producer_sources(root,producer_hashes,retained)
    expected='producer-inputs/'+retained['relative_path']
    archive=Path(evidence)/expected
    if retained.get('archive_relative_path')!=expected or not archive.is_file() or sha(archive)!=retained['sha256']:
        raise ValueError('Retained caller archived receipt changed or missing')

"""Run explicitly selected real-input cases; full inventory fails closed."""
import argparse,hashlib,json,os,platform,subprocess,sys,traceback,uuid
from pathlib import Path
from driver import Driver,REPO,EMULATOR_ROOT,write,digest
from cases import CASES

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--list',action='store_true')
    parser.add_argument('--case',action='append');parser.add_argument('--require-all',action='store_true')
    parser.add_argument('--artifacts',default=str(REPO.parent/'mosaic-behaviour-runs'))
    args=parser.parse_args();inventory=json.loads((REPO/'tests/behaviour/manual-inventory.json').read_text())
    assert digest(REPO/inventory['manual'])==inventory['manual_sha256'],'Manual changed: reconcile inventory'
    for source in inventory['manual_sources']:
        if 'path' in source:
            assert digest(REPO/source['path'])==source['sha256'],'Manual source changed: '+source['path']
    requirements={r['id'] for r in inventory['requirements']}
    assert all(set(case['requirements'])<=requirements for case in CASES.values()),'Dangling case requirement ID'
    if args.list:
        print(json.dumps({k:{n:v for n,v in case.items() if n!='run'} for k,case in CASES.items()},indent=2));return 0
    if args.require_all:
        pending=[s['id'] for s in inventory['sections'] if s['status']!='complete']
        if pending:raise ValueError('Manual coverage incomplete: '+','.join(pending))
        raise ValueError('Full campaign gate not implemented; cannot claim suite complete')
    selected=args.case or []
    if not selected or any(name not in CASES for name in selected) or len(selected)!=len(set(selected)):
        raise ValueError('Select known, unique --case IDs, or use --list; no empty/implicit acceptance')
    failed=False
    for name in selected:
        out=Path(args.artifacts).resolve()/uuid.uuid4().hex;out.mkdir(parents=True,exist_ok=False)
        c=None;failure=None
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
        try:c=Driver(out);CASES[name]['run'](c)
        except Exception as error:failure=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
        finally:
            if c:
                try:c.finish()
                except Exception as error:failure=failure or dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
        result=dict(schema_version=1,case=name,requirements=CASES[name]['requirements'],passed=failure is None,
            campaign_complete=False,clock_mode='real-time',seed=42,mosaic_revision=revision,
            manual_sha256=inventory['manual_sha256'],platform=platform.platform(),failure=failure,
            artifacts=[dict(path=p.relative_to(out).as_posix(),sha256=digest(p),size=p.stat().st_size) for p in sorted(out.rglob('*')) if p.is_file() and 'code' not in p.relative_to(out).parts and 'data' not in p.relative_to(out).parts])
        write(out/'manifest.json',result);print(json.dumps(dict(case=name,passed=result['passed'],manifest=str(out/'manifest.json'))),flush=True)
        failed|=failure is not None
    return int(failed)

if __name__=='__main__':sys.exit(main())

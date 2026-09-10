"""Run explicitly selected real-input cases; full inventory fails closed."""
import ast,argparse,hashlib,json,os,platform,subprocess,sys,traceback,uuid,time
from pathlib import Path
from driver import Driver,REPO,EMULATOR_ROOT,write,digest
from cases import CASES

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--list',action='store_true')
    parser.add_argument('--case',action='append');parser.add_argument('--require-all',action='store_true')
    parser.add_argument('--artifacts',default=str(REPO.parent/'mosaic-behaviour-runs'))
    parser.add_argument('--clock-mode',choices=['real-time','controlled-experimental'],default='real-time')
    parser.add_argument('--experimental-install')
    parser.add_argument('--profile',choices=['base-midi','midi-modulation','nb-audio','crow-jf','mixed-outputs'],default='base-midi')
    parser.add_argument('--mod-code-root')
    parser.add_argument('--mod-patches',action='store_true',help='Apply the recorded isolated dependency candidate; original checkouts stay unchanged')
    args=parser.parse_args()
    if (args.profile!='base-midi') != bool(args.mod_code_root):
        parser.error('Mod profiles require --mod-code-root; base profile takes no mod source')
    if args.profile in ('nb-audio','crow-jf','mixed-outputs') and args.clock_mode!='real-time':
        parser.error('Audio/Crow profiles require real time')
    if args.clock_mode=='controlled-experimental' and not args.experimental_install:
        parser.error('Experimental diagnostics require both --clock-mode controlled-experimental and --experimental-install')
    # Python dict literals silently replace duplicate keys. Reject duplicate
    # case IDs from source before any selection can earn misleading credit.
    tree=ast.parse((REPO/'tests/behaviour/cases.py').read_text())
    registries=[n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CASES' for t in n.targets)]
    assert len(registries)==1 and isinstance(registries[0],ast.Dict),'Expected one explicit CASES registry'
    keys=registries[0].keys
    assert all(isinstance(k,ast.Constant) and isinstance(k.value,str) for k in keys),'Case IDs must be literal strings'
    ids=[k.value for k in keys]
    assert len(ids)==len(set(ids)),'Duplicate case IDs in source registry'
    inventory=json.loads((REPO/'tests/behaviour/manual-inventory.json').read_text())
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
        c=None;failure=None;started=time.monotonic()
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
        try:c=Driver(out,clock_mode=args.clock_mode,experimental_install=args.experimental_install,profile=args.profile,mod_code_root=args.mod_code_root,mod_patches=args.mod_patches);CASES[name]['run'](c)
        except Exception as error:failure=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
        finally:
            if c:
                try:c.finish()
                except Exception as error:failure=failure or dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
        result=dict(schema_version=1,case=name,requirements=CASES[name]['requirements'],expansion_families=CASES[name].get('expansion_families',[]),passed=failure is None,
            campaign_complete=False,clock_mode=args.clock_mode,diagnostic_only=bool(args.experimental_install),
            controlled_time_admitted=False,profile=args.profile,mod_revisions=c.mod_revisions if c else {},mod_patches=c.applied_mod_patches if c else {},seed=42,mosaic_revision=revision,
            wall_elapsed_seconds=time.monotonic()-started,
            logical_advanced_seconds=(sum(a['nanoseconds'] for p in out.rglob('recipe.json') if not {'code','data'} & set(p.relative_to(out).parts) for a in json.loads(p.read_text()) if a['type']=='advance')/1e9 if args.clock_mode!='real-time' else None),
            manual_sha256=inventory['manual_sha256'],
            behaviour_source_sha256={p.relative_to(REPO).as_posix():digest(p) for p in sorted((REPO/'tests/behaviour').glob('*.py'))},
            platform=platform.platform(),failure=failure,
            artifacts=[dict(path=p.relative_to(out).as_posix(),sha256=digest(p),size=p.stat().st_size) for p in sorted(out.rglob('*')) if p.is_file() and 'code' not in p.relative_to(out).parts and 'data' not in p.relative_to(out).parts])
        write(out/'manifest.json',result);print(json.dumps(dict(case=name,passed=result['passed'],manifest=str(out/'manifest.json'))),flush=True)
        failed|=failure is not None
    return int(failed)

if __name__=='__main__':sys.exit(main())

"""Three fresh-process D repeats; compare logical outputs and input recipes."""
import argparse,json,os,subprocess,sys,uuid
from pathlib import Path
from driver import REPO,write,digest

def normalized(root):
    result={}
    for path in sorted(root.rglob('observations.json')):
        if {'code','data'} & set(path.relative_to(root).parts):continue
        state=json.loads(path.read_text())[-1]['state']
        result[path.parent.relative_to(root).as_posix()]=dict(
            recipe=json.loads((path.parent/'recipe.json').read_text()),
            midi=[(m['port'],m['bytes'],m['logical_ns']) for m in state['midi']],
            grid=state['grid'],frame=state['frame']['sha256'],clock=state['clock'],
            outstanding=state['midi_capture']['outstanding'])
    assert result,'No observable segments collected'
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--case',required=True)
    parser.add_argument('--experimental-install',required=True)
    parser.add_argument('--profile',choices=['base-midi','midi-modulation'],default='base-midi')
    parser.add_argument('--mod-code-root')
    args=parser.parse_args();out=REPO.parent/'mosaic-behaviour-runs'/('repeat-'+uuid.uuid4().hex);out.mkdir()
    command=[sys.executable,str(REPO/'tests/behaviour/run.py'),'--case',args.case,
             '--clock-mode','controlled-experimental','--experimental-install',args.experimental_install,
             '--profile',args.profile]
    if args.mod_code_root:command+=['--mod-code-root',args.mod_code_root]
    runs=[];values=[];failure=None
    try:
        for _ in range(3):
            completed=subprocess.run(command,cwd=REPO,text=True,capture_output=True)
            write(out/('process-'+str(len(runs))+'.json'),dict(returncode=completed.returncode,stdout=completed.stdout,stderr=completed.stderr))
            assert completed.returncode==0,completed.stdout+completed.stderr
            summary=json.loads(completed.stdout.strip().splitlines()[-1]);manifest=Path(summary['manifest'])
            item=json.loads(manifest.read_text());assert item['passed'] and item['diagnostic_only']
            runs.append(dict(manifest=str(manifest),sha256=digest(manifest),wall_elapsed_seconds=item['wall_elapsed_seconds'],logical_advanced_seconds=item['logical_advanced_seconds']))
            values.append(normalized(manifest.parent))
        assert values[0]==values[1]==values[2],'Fresh processes produced different logical traces or final output'
    except Exception as error:failure=dict(type=type(error).__name__,message=str(error))
    write(out/'normalized.json',values)
    write(out/'manifest.json',dict(case=args.case,profile=args.profile,passed=failure is None,failure=failure,
        diagnostic_only=True,controlled_time_admitted=False,runs=runs,normalized_sha256=digest(out/'normalized.json')))
    print(out/'manifest.json',flush=True)
    return int(failure is not None)
if __name__=='__main__':sys.exit(main())

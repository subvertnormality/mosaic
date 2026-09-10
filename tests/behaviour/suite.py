"""Full Mosaic regression suite: every declared test layer, fail-closed.

    MONOME_EMULATOR=/path/to/emulator python3 tests/behaviour/suite.py run \\
        --output ../mosaic-behaviour-runs/suite-<name> \\
        --experimental-install /path/to/installation.json
    python3 tests/behaviour/suite.py compare BASELINE/suite.json CANDIDATE/suite.json

Layers: Lua contracts, Python oracle tests, script tests, the isolated Lua unit
suite seeded with the pinned norns Lua tree, and every registered native case in
each requested clock lane. Profiles other than base-midi need their own sources
and are reported NOT RUN (never passed) unless requested. A suite passes only if
every selected item ran and passed and the tested sources did not change during
the run. The emulator checkout and installs are configuration, recorded in the
report; they are not part of Mosaic's acceptance oracle.
"""
import argparse,concurrent.futures,hashlib,json,os,re,shutil,subprocess,sys,time
from pathlib import Path

REPO=Path(__file__).resolve().parents[2]
BEHAVIOUR=REPO/'tests/behaviour'
# Declared invocation for every Lua file in tests/behaviour; an unlisted file fails collection.
LUA_ARGUMENT={'panic_live_note_contract.lua':'mosaic-root','test_native_control_endpoint.lua':'norns-root',
              'test_patch_param_domain.lua':'norns-root'}
# Python test modules run under unittest, each with the environment it needs.
PYTHON_UNITTEST={'test_acquisition_oracle','test_collection','test_duration_routes','test_external_clock_fault_oracle',
    'test_forwarded_clock_oracle','test_fractional_stop_boundary','test_jf_oracle','test_master_clock_oracle',
    'test_midi_window','test_note_accounting','test_note_schedule','test_output_profiles','test_panic_hotplug_trace',
    'test_inventory','test_lua_test_names','test_panic_repeat_trace','test_panic_trace','test_panic_transport','test_pcm_oracle','test_suite'}
PYTHON_NEEDS_OUTPUT_MODS={'test_output_profiles'}
PYTHON_SCRIPT={'test_nrpn_legacy_serializer':'norns-source-and-artifact-directory'}
# Cases whose code asserts a non-base profile. Base cases are everything else.
CASE_PROFILE={'M-MOD-001':'midi-modulation','M-MOD-002':'midi-modulation','M-MOD-003':'midi-modulation',
    'M-MOD-004':'midi-modulation','M-XA-001-JF':'crow-jf','M-XA-002-AUDIO':'nb-audio',
    'M-XA-003-JF-OWNERSHIP':'crow-jf','M-XA-004-JF-OVERLAP':'crow-jf'}
LANES=('real-time','controlled-experimental')

def sha(data):return hashlib.sha256(data).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=1)+'\n')
def git(*args,cwd=REPO,binary=False):
    return subprocess.run(['git',*args],cwd=cwd,check=True,capture_output=True,text=not binary).stdout

RUNNER='tests/behaviour/suite.py'

def source_state(root=REPO,exclude_runner=False):
    """Digest every tracked and untracked, non-ignored file: the tree under test.

    The Mosaic tree excludes this runner, which only selects and invokes tests;
    its own digest is recorded separately so harness fixes can rerun a baseline.
    """
    names=sorted(set(git('ls-files','-z',cwd=root).split('\0')+
                     git('ls-files','-z','--others','--exclude-standard',cwd=root).split('\0'))-{''})
    files={n:sha((root/n).read_bytes()) for n in names if (root/n).is_file() and not (root/n).is_symlink()
           and not (exclude_runner and n==RUNNER)}
    state=dict(revision=git('rev-parse','HEAD',cwd=root).strip(),
               dirty_patch_sha256=sha(git('diff','HEAD',cwd=root,binary=True)),
               untracked=sorted(git('ls-files','--others','--exclude-standard',cwd=root).split()),
               tree_sha256=sha(json.dumps(files,sort_keys=True).encode()),file_count=len(files))
    if exclude_runner:state.update(files=files,runner_sha256=sha((root/RUNNER).read_bytes()))
    return state

def same_tested_tree(recorded):
    """True if this checkout is the tree a suite report tested, runner aside."""
    if 'files' in recorded:return source_state(exclude_runner=True)['files']==recorded['files']
    # Reports before per-file digests: same commit, nothing untracked, and any
    # working-tree change confined to the runner.
    changed=set(git('diff','--name-only','HEAD').split())
    return (git('rev-parse','HEAD').strip()==recorded['revision'] and not recorded['untracked'] and
            recorded['dirty_patch_sha256']==sha(b'') and changed<={RUNNER} and
            not git('ls-files','--others','--exclude-standard').split())

def collect(case_ids):
    """Classify every test file; unclassified or stale declarations fail closed."""
    lua=sorted(p.name for p in BEHAVIOUR.glob('*.lua'))
    python=sorted(p.stem for p in BEHAVIOUR.glob('test_*.py'))
    unknown=sorted(set(python)-PYTHON_UNITTEST-set(PYTHON_SCRIPT))
    stale=sorted((PYTHON_UNITTEST|set(PYTHON_SCRIPT))-set(python))+sorted(set(LUA_ARGUMENT)-set(lua))
    stale+=sorted(set(CASE_PROFILE)-set(case_ids))
    if unknown or stale:raise SystemExit('Unclassified tests %r; stale declarations %r'%(unknown,stale))
    if not lua or not python or not case_ids:raise SystemExit('Empty test collection')
    return lua,python

def run_command(name,command,cwd,env=None,timeout=900,log=None):
    started=time.monotonic()
    try:
        result=subprocess.run(command,cwd=cwd,env=env,capture_output=True,text=True,timeout=timeout)
        code,output=result.returncode,result.stdout+result.stderr
    except subprocess.TimeoutExpired as error:
        code,output=None,'TIMEOUT after %ss\n'%timeout+((error.stdout or b'').decode(errors='replace') if isinstance(error.stdout,bytes) else (error.stdout or ''))
    if log:log.write_text(output)
    return dict(name=name,command=command,returncode=code,passed=code==0,seconds=round(time.monotonic()-started,3),
                tail=output.strip().splitlines()[-1][:300] if output.strip() else '',log=str(log) if log else None)

def lua_layer(files,norns,out):
    logs=out/'logs/lua';logs.mkdir(parents=True)
    rows=[]
    for name in files:
        kind=LUA_ARGUMENT.get(name)
        args=[] if kind is None else [str(REPO) if kind=='mosaic-root' else str(norns)]
        rows.append(run_command(name,['lua5.3','tests/behaviour/'+name,*args],REPO,log=logs/(name+'.log')))
    return rows

def python_layer(modules,env,norns,out):
    logs=out/'logs/python';logs.mkdir(parents=True)
    rows=[]
    for module in modules:
        if module in PYTHON_SCRIPT:
            target=out/'script-artifacts'/module
            rows.append(run_command(module,[sys.executable,module+'.py',str(norns),str(target)],BEHAVIOUR,env,log=logs/(module+'.log')))
        elif module in PYTHON_NEEDS_OUTPUT_MODS and not env.get('MOSAIC_OUTPUT_MOD_ROOT'):
            rows.append(dict(name=module,passed=None,not_run='MOSAIC_OUTPUT_MOD_ROOT not supplied'))
        else:
            row=run_command(module,[sys.executable,'-m','unittest','-v',module],BEHAVIOUR,env,log=logs/(module+'.log'))
            text=Path(row['log']).read_text()
            ran=re.findall(r'^Ran (\d+) tests?',text,re.M)
            row['tests']=int(ran[-1]) if ran else 0
            if row['passed'] and not row['tests']:row.update(passed=False,tail='No tests collected')
            rows.append(row)
    return rows

def lua_units(norns,out):
    """Unchanged Mosaic Lua units in an isolated copy seeded with pinned norns Lua."""
    copy=out/'units/mosaic'
    names=set(git('ls-files','-z').split('\0')+git('ls-files','-z','--others','--exclude-standard').split('\0'))-{''}
    for name in sorted(names):
        source=REPO/name
        if source.is_file() and not name.startswith('lib/tests/test_artefacts/'):
            target=copy/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    seeded=copy/'lib/tests/test_artefacts/norns_test_artefact'
    shutil.copytree(norns/'lua',seeded/'lua')
    log=out/'logs/lua-units.log'
    row=run_command('lua-units',['lua5.3','./run_tests.lua'],copy/'lib/tests',timeout=1800,log=log)
    text=log.read_text()
    match=re.findall(r'Ran (\d+) tests in [\d.]+ seconds, (\d+) successes, (\d+) failures',text)
    fetched='Skipping download' not in text or 'Fetching latest release' in text
    row.update(collected=int(match[-1][0]) if match else 0,successes=int(match[-1][1]) if match else 0,
               failures=int(match[-1][2]) if match else None,network_fetch_attempted=fetched,
               norns_lua_tree_sha256=tree_digest(norns/'lua'))
    row['passed']=bool(row['passed'] and match and row['collected']>0 and row['failures']==0 and
                       row['successes']==row['collected'] and not fetched)
    shutil.rmtree(copy)
    return row

def tree_digest(root):
    return sha(json.dumps({p.relative_to(root).as_posix():sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()},sort_keys=True).encode())

class StartGate:
    """Space case launches: concurrent native startups race on JACK's shared registry.

    Measured in the emulator (R22): six simultaneous starts failed 15 of 18 times.
    Startup is not under test, so spacing launches changes no case result.
    """
    def __init__(self,interval):
        import threading
        self.interval=interval;self.lock=threading.Lock();self.last=None
    def wait(self):
        with self.lock:
            if self.last is not None:
                delay=self.interval-(time.monotonic()-self.last)
                if delay>0:time.sleep(delay)
            self.last=time.monotonic()

def run_case(case,lane,profile,args,artifacts,env,gate=None):
    if gate:gate.wait()
    command=[sys.executable,str(BEHAVIOUR/'run.py'),'--case',case,'--artifacts',str(artifacts),'--clock-mode',lane]
    if args.experimental_install:command+=['--experimental-install',args.experimental_install]
    if profile!='base-midi':command+=['--profile',profile,'--mod-code-root',args.mod_code_root[profile]]
    started=time.monotonic()
    try:
        result=subprocess.run(command,cwd=REPO,env=env,capture_output=True,text=True,timeout=args.case_timeout)
        lines=[json.loads(l) for l in result.stdout.splitlines() if l.startswith('{"case"')]
        row=dict(case=case,lane=lane,profile=profile,returncode=result.returncode,seconds=round(time.monotonic()-started,1))
        if len(lines)!=1 or lines[0]['case']!=case:
            row.update(passed=False,error='No case manifest reported',stderr=result.stderr[-2000:]);return row
        manifest=Path(lines[0]['manifest']);data=json.loads(manifest.read_text())
        row.update(passed=bool(data['passed']) and result.returncode==0,manifest=str(manifest),manifest_sha256=sha(manifest.read_bytes()),
                   wall_elapsed_seconds=data.get('wall_elapsed_seconds'),
                   failure=(data['failure']['type']+': '+data['failure']['message'][:400]) if data.get('failure') else None)
        return row
    except subprocess.TimeoutExpired:
        return dict(case=case,lane=lane,profile=profile,passed=False,error='TIMEOUT after %ss'%args.case_timeout,
                    seconds=round(time.monotonic()-started,1))

def case_registry():
    sys.path.insert(0,str(BEHAVIOUR))
    from cases import CASES
    return {name:list(case['requirements']) for name,case in CASES.items()}

def run(args):
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,MONOME_EMULATOR=str(Path(args.emulator).resolve()))
    if args.output_mod_root:env['MOSAIC_OUTPUT_MOD_ROOT']=str(Path(args.output_mod_root).resolve())
    norns=Path(args.norns_source).resolve()
    registry=case_registry()
    lua,python=collect(set(registry))
    selected=[c for c in registry if not args.case_pattern or re.search(args.case_pattern,c)]
    if not selected:raise SystemExit('Case selection is empty')
    before=source_state(exclude_runner=True)
    identity=dict(mosaic=before,emulator=source_state(Path(args.emulator).resolve()),
        norns_source=dict(path=str(norns),revision=git('rev-parse','HEAD',cwd=norns).strip(),lua_tree_sha256=tree_digest(norns/'lua')),
        experimental_install=dict(path=args.experimental_install,sha256=sha(Path(args.experimental_install).read_bytes()),
            lock_sha256=json.loads(Path(args.experimental_install).read_text()).get('lock_sha256')) if args.experimental_install else None,
        argv=sys.argv[1:],python=sys.version.split()[0])
    report=dict(schema_version=1,started=time.strftime('%Y-%m-%dT%H:%M:%S%z'),identity=identity,lanes=args.lanes,
                profiles=sorted(args.profiles),case_pattern=args.case_pattern)
    write(out/'suite.json',dict(report,status='running'))
    layers={}
    if not args.skip_fast_layers:
        layers['lua_contracts']=lua_layer(lua,norns,out)
        layers['python']=python_layer(python,env,norns,out)
        layers['lua_units']=lua_units(norns,out)
        write(out/'suite.json',dict(report,status='running',layers=layers))
    jobs=[];not_run=[]
    for lane in args.lanes:
        for case in selected:
            profile=CASE_PROFILE.get(case,'base-midi')
            if profile not in args.profiles:not_run.append(dict(case=case,lane=lane,profile=profile,reason='profile not requested'))
            elif profile in ('crow-jf','nb-audio') and lane!='real-time':
                not_run.append(dict(case=case,lane=lane,profile=profile,reason='audio/Crow profiles are real-time only',applicable=False))
            else:jobs.append((case,lane,profile))
    results=[]
    for lane in args.lanes:
        artifacts=out/'runs'/lane;artifacts.mkdir(parents=True)
        workers=args.real_time_workers if lane=='real-time' else args.controlled_workers
        lane_jobs=[j for j in jobs if j[1]==lane]
        gate=StartGate(args.start_interval)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(run_case,case,lane,profile,args,artifacts,env,gate) for case,lane,profile in lane_jobs]
            for done,future in enumerate(concurrent.futures.as_completed(futures),1):
                row=future.result();results.append(row)
                print(json.dumps(dict(done=done,of=len(lane_jobs),lane=lane,case=row['case'],passed=row['passed'],seconds=row['seconds'])),flush=True)
                if done%10==0:write(out/'suite.json',dict(report,status='running',layers=layers,cases=results,not_run=not_run))
    after=source_state(exclude_runner=True)
    stable=after['files']==before['files'] and after['runner_sha256']==before['runner_sha256']
    results.sort(key=lambda r:(args.lanes.index(r['lane']),r['case']))
    layer_rows=[r for rows in layers.values() for r in (rows if isinstance(rows,list) else [rows])]
    requirements={}
    for row in results:
        for requirement in registry[row['case']]:
            entry=requirements.setdefault(requirement,{})
            entry.setdefault(row['lane'],dict(passed=0,failed=0))['passed' if row['passed'] else 'failed']+=1
    required_not_run=[r for r in not_run if r.get('applicable',True)]
    summary=dict(cases_selected=len(selected),case_runs=len(results),case_runs_passed=sum(r['passed'] for r in results),
        case_runs_failed=[dict(case=r['case'],lane=r['lane']) for r in results if not r['passed']],
        layer_items=len(layer_rows),layer_items_failed=[r['name'] for r in layer_rows if r['passed'] is False],
        layer_items_not_run=[r['name'] for r in layer_rows if r['passed'] is None],
        not_run=len(not_run),required_not_run=len(required_not_run),fast_layers_skipped=args.skip_fast_layers,
        sources_stable=stable)
    passed=(stable and not summary['case_runs_failed'] and not summary['layer_items_failed'] and results and
            len(results)==len(jobs))
    complete=(passed and not summary['layer_items_not_run'] and not required_not_run and not args.case_pattern and
              not args.skip_fast_layers and set(args.lanes)==set(LANES))
    write(out/'suite.json',dict(report,status='finished',finished=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        passed=bool(passed),complete_regression_run=bool(complete),summary=summary,layers=layers,cases=results,
        not_run=not_run,requirements=requirements,sources_after={k:v for k,v in after.items() if k!='files'}))
    print(json.dumps(dict(suite=str(out/'suite.json'),passed=bool(passed),complete=bool(complete),
        failed_case_runs=len(summary['case_runs_failed']),failed_layer_items=summary['layer_items_failed'])))
    return 0 if passed else 1

STARTUP_FAILURE=re.compile(r'^ContractError: (?:(?:jack|crone|sclang|matron) exited|.* did not reach )')

def failure_class(row):
    """Separate native startup failures from failures of the case itself."""
    return 'native-startup' if STARTUP_FAILURE.search(row.get('failure') or '') else 'case'

def rerun(args):
    """Serially rerun every failed case run; the original report is untouched.

    A first-attempt failure that passes serially is marked load_sensitive, never
    silently green. The effective report is what compare should read.
    """
    source=Path(args.suite).resolve();report=json.loads(source.read_text())
    if report.get('status')!='finished':raise SystemExit('Suite has not finished')
    if not same_tested_tree(report['identity']['mosaic']):
        raise SystemExit('Tested tree differs from the suite run; rerun from the same tree')
    env=dict(os.environ,MONOME_EMULATOR=str(Path(args.emulator).resolve()))
    artifacts=source.parent/'serial-rerun';artifacts.mkdir(exist_ok=False)
    rows=[]
    for row in report['cases']:
        if row['passed']:rows.append(row);continue
        again=run_case(row['case'],row['lane'],row['profile'],args,artifacts,env)
        print(json.dumps(dict(case=row['case'],lane=row['lane'],serial_passed=again['passed'])),flush=True)
        kind=failure_class(row)
        rows.append(dict(again,first_attempt=row,first_attempt_class=kind,
                         load_sensitive=bool(again['passed']) and kind=='case',
                         startup_retry=bool(again['passed']) and kind=='native-startup'))
    summary=dict(report['summary'],case_runs_passed=sum(r['passed'] for r in rows),
                 case_runs_failed=[dict(case=r['case'],lane=r['lane']) for r in rows if not r['passed']],
                 load_sensitive=[dict(case=r['case'],lane=r['lane']) for r in rows if r.get('load_sensitive')],
                 startup_retries=[dict(case=r['case'],lane=r['lane']) for r in rows if r.get('startup_retry')],
                 serial_rerun_sources_stable=same_tested_tree(report['identity']['mosaic']))
    passed=(report['summary']['sources_stable'] and summary['serial_rerun_sources_stable'] and
            not summary['case_runs_failed'] and not summary['layer_items_failed'] and len(rows)==len(report['cases']))
    effective=dict(report,cases=rows,summary=summary,passed=bool(passed),
                   complete_regression_run=bool(passed and report.get('complete_regression_run') is not None and
                       not summary['layer_items_not_run'] and not summary['required_not_run'] and not report.get('case_pattern')
                       and not summary['fast_layers_skipped'] and set(report['lanes'])==set(LANES)),
                   serial_rerun=dict(of=str(source),sha256=sha(source.read_bytes()),argv=sys.argv[1:],
                                     runner_sha256=sha((REPO/RUNNER).read_bytes())))
    write(source.parent/'suite-effective.json',effective)
    print(json.dumps(dict(effective=str(source.parent/'suite-effective.json'),passed=effective['passed'],
        still_failing=len(summary['case_runs_failed']),load_sensitive=len(summary['load_sensitive']))))
    return 0 if passed else 1

def compare(args):
    base=json.loads(Path(args.baseline).read_text());new=json.loads(Path(args.candidate).read_text())
    def index(report):
        rows={('case',r['case'],r['lane']):r['passed'] for r in report.get('cases',[])}
        for layer,items in report.get('layers',{}).items():
            for r in (items if isinstance(items,list) else [items]):rows[('layer',layer,r['name'])]=r['passed']
        return rows
    b,n=index(base),index(new)
    regressions=sorted('/'.join(k) for k in b if b[k] is True and n.get(k) is not True)
    fixed=sorted('/'.join(k) for k in n if n[k] is True and b.get(k) is False)
    added=sorted('/'.join(k) for k in n if k not in b)
    result=dict(baseline=args.baseline,candidate=args.candidate,regressions=regressions,fixed=fixed,added=added,
                still_failing=sorted('/'.join(k) for k in n if n[k] is False and b.get(k) is False),
                candidate_passed=new.get('passed'),candidate_complete=new.get('complete_regression_run'))
    print(json.dumps(result,indent=1))
    return 1 if regressions or not new.get('passed') else 0

def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    commands=parser.add_subparsers(dest='command',required=True)
    r=commands.add_parser('run')
    r.add_argument('--output',required=True)
    r.add_argument('--emulator',default=os.environ.get('MONOME_EMULATOR'),required='MONOME_EMULATOR' not in os.environ)
    r.add_argument('--experimental-install',help='Runtime installation for both lanes (controlled lane requires one)')
    r.add_argument('--norns-source',help='Pinned norns checkout for Lua units and norns-root contracts; default EMULATOR/.runtime/deps/norns')
    r.add_argument('--lanes',default=','.join(LANES),type=lambda v:[x for x in v.split(',') if x])
    r.add_argument('--profiles',default='base-midi',type=lambda v:set(v.split(',')))
    r.add_argument('--mod-code-root',action='append',default=[],help='PROFILE=PATH for non-base profiles')
    r.add_argument('--output-mod-root',default=os.environ.get('MOSAIC_OUTPUT_MOD_ROOT'))
    r.add_argument('--case-pattern',help='Regex selection (a partial run is never a complete regression run)')
    r.add_argument('--real-time-workers',type=int,default=2)
    r.add_argument('--controlled-workers',type=int,default=6)
    r.add_argument('--case-timeout',type=int,default=3600)
    r.add_argument('--start-interval',type=float,default=10,help='Minimum seconds between case launches (native startup race, emulator R22)')
    r.add_argument('--skip-fast-layers',action='store_true')
    c=commands.add_parser('compare');c.add_argument('baseline');c.add_argument('candidate')
    s=commands.add_parser('rerun',help='Serially rerun failed case runs into suite-effective.json')
    s.add_argument('suite')
    s.add_argument('--emulator',default=os.environ.get('MONOME_EMULATOR'),required='MONOME_EMULATOR' not in os.environ)
    s.add_argument('--experimental-install')
    s.add_argument('--mod-code-root',action='append',default=[])
    s.add_argument('--case-timeout',type=int,default=3600)
    args=parser.parse_args()
    if args.command=='compare':return compare(args)
    if args.command=='rerun':
        args.mod_code_root=dict(v.split('=',1) for v in args.mod_code_root);return rerun(args)
    if any(l not in LANES for l in args.lanes) or len(set(args.lanes))!=len(args.lanes) or not args.lanes:
        parser.error('Lanes must be unique values from '+','.join(LANES))
    if 'controlled-experimental' in args.lanes and not args.experimental_install:
        parser.error('The controlled lane requires --experimental-install')
    args.mod_code_root=dict(v.split('=',1) for v in args.mod_code_root)
    missing=[p for p in args.profiles if p!='base-midi' and p not in args.mod_code_root]
    if missing:parser.error('Missing --mod-code-root for '+','.join(missing))
    args.norns_source=args.norns_source or str(Path(args.emulator)/'.runtime/deps/norns')
    return run(args)

if __name__=='__main__':sys.exit(main())

"""Focused existing public-input music/UI regressions; no exhaustive claim."""
import os,sys,json,hashlib,subprocess,fcntl
from pathlib import Path
ROOT=Path('/home/andy/mosaic-manual-1.4.0')
OUT=ROOT/'docs/testing/vertical-list-ui'
lane=sys.argv[1]
paths=sorted(set(list((ROOT/'lib').rglob('*.lua'))+list((ROOT/'docs/ui-reimplementation').rglob('*'))+list((ROOT/'tests/behaviour').rglob('*.py'))+list((ROOT/'tests/behaviour/config').rglob('*'))))
paths=[p for p in paths if p.is_file() and '__pycache__' not in p.parts]
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
start={str(p.relative_to(ROOT)):digest(p) for p in paths}
cases=['M-UIACC-A01-001','M-UIACC-A02-001','M-UIACC-A03-001','M-UIACC-A18-001']
(OUT/(lane+'-affected-start.json')).write_text(json.dumps(dict(clock_mode=lane,selected_cases=cases,complete_regression_run=False,source_hashes=start),indent=2)+'\n')
args=['python3',str(ROOT/'tests/behaviour/run.py'),'--clock-mode',lane,'--artifacts','/home/andy/mosaic-behaviour-runs/vertical-list-'+lane]
if lane=='controlled-experimental':args+=['--experimental-install','/home/andy/projects/monome-runtime-candidates/final-qualification-controlled-01/installation.json']
for name in cases:args+=['--case',name]
with open('/tmp/mosaic-manual-native.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 with (OUT/(lane+'-affected.log')).open('w') as output:
  proc=subprocess.Popen(args,env=dict(os.environ,MONOME_EMULATOR='/home/andy/projects/monome-emulator-ci-combined'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
  for line in proc.stdout:print(line,end='',flush=True);output.write(line);output.flush()
  code=proc.wait()
 changed=[name for name,sha in start.items() if digest(ROOT/name)!=sha]
 (OUT/(lane+'-affected-finish.json')).write_text(json.dumps(dict(clock_mode=lane,selected_cases=cases,complete_regression_run=False,returncode=code,source_unchanged=not changed,changed=changed),indent=2)+'\n')
 assert not changed,changed
 sys.exit(code)

"""Run the corrected literal acceptance against the immutable unfixed application."""
import sys,os,json,hashlib,uuid,fcntl,types
from pathlib import Path
ROOT=Path('/home/andy/mosaic-manual-1.4.0')
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tests/behaviour')]
import manual_case_capture as capture
from contract import vertical_list_ui as added
import yaml
lane=sys.argv[1]; original=Path('/home/andy/mosaic-manual-runs/feec37b4b9c84b269f981322c292f7bc')
run=Path('/home/andy/mosaic-manual-runs')/uuid.uuid4().hex;run.mkdir()
plan=ROOT/'manual/scene-plans-vertical-list.yaml'; plans=yaml.safe_load(plan.read_text())['scenes']
plans[0]['steps']=plans[0]['steps'][:1]
blobs={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'tests/behaviour').rglob('*.py') if not p.name.startswith('test_') and p.name not in ('suite.py','run.py')}
helper=ROOT/'tools/manual_vertical_list_cases.py'
start=capture.persist_start_sources(run,dict(plan_files={str(plan.relative_to(ROOT)):plan.read_bytes()},case_sources=blobs,fixture_sources={str(p.relative_to(ROOT)):p.read_bytes() for p in (ROOT/'tests/behaviour/config').rglob('*') if p.is_file()},capture_sources={str(helper.relative_to(ROOT)):helper.read_bytes()}),dict(schema_version=1,clock_mode=lane,selected_scene_ids=['vertical-clock-neighbors'],plans_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),original_application=str(original/'application'),original_start_identity_sha256=hashlib.sha256((original/'start-source-identity.json').read_bytes()).hexdigest()))
options=types.SimpleNamespace(clock_mode=lane,experimental_install='/home/andy/projects/monome-runtime-candidates/final-qualification-controlled-01/installation.json' if lane=='controlled-experimental' else None,app_root=original/'application',mod_code_root=None,mod_patches=False,case_registry=added.CASES,extra_case_files=[str(helper)])
folder=run/'M-UI-VERTICAL-001-base-midi';folder.mkdir()
with open('/tmp/mosaic-manual-native.lock','a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 try:capture.capture_group(plans,folder,options)
 except AssertionError as error:
  assert str(error).startswith('vertical-list acceptance:'),repr(error)
  (run/'failure.json').write_text(json.dumps(dict(passed=False,expected_failure=True,error=repr(error),clock_mode=lane,original_application=str(options.app_root),source=start),indent=2)+'\n')
  print('EXPECTED RED',run,flush=True)
 else:raise AssertionError('Unfixed application unexpectedly passed new vertical list acceptance')

"""Negative typed-audit tests using explicitly synthetic unit fixtures.

No emulated framebuffer or native acceptance report is claimed by these tests.
Stock source snapshot machinery supplies the source-cache test fixture.
"""
import base64,copy,hashlib,json,tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
sys.path.insert(0,str(ROOT/"tests/behaviour"))
import manual_save_dialog_oracle as oracle
import manual_save_dialog_cases as save_case
from manual_case_capture import persist_start_sources
from manual_publication_verify import check_custom_kind,verify_teaching_checkpoint
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class SaveDialogAuditTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.run=Path(self.tmp.name);self.case=self.run/'M-MANUAL-SAVE-DIALOG-001-base-midi';self.case.mkdir()
  self.fixture=ROOT/'tests/behaviour/config/manual-save-dialog'
  cases={name:(ROOT/name).read_bytes() for name in ['tests/behaviour/manual_save_dialog_oracle.py','tests/behaviour/contract/manual_save_dialog_oracle.py','tests/behaviour/frame_oracle.py','tests/behaviour/driver.py','tests/behaviour/ui_map.py','tests/behaviour/manual_save_project_canonical.py','tests/behaviour/persisted_digest.lua']}
  fixtures={str(p.relative_to(ROOT)):p.read_bytes() for p in self.fixture.rglob('*') if p.is_file()}
  receipt=persist_start_sources(self.run,dict(case_sources=cases,fixture_sources=fixtures,capture_sources={},plan_files={}))
  self.assertEqual(receipt['case_sources'],{k:hashlib.sha256(v).hexdigest() for k,v in cases.items()})
  self.assertEqual(receipt['fixture_sources'],{k:hashlib.sha256(v).hexdigest() for k,v in fixtures.items()})
  blob=oracle.expected('confirm');self.sha=hashlib.sha256(blob).hexdigest()
  self.state=dict(frame=dict(sha256=self.sha,pixels_base64=base64.b64encode(blob).decode()),grid=[0]*128,held=[],midi_capture=dict(outstanding=[]))
  text,line,delok,pos=oracle.specification('confirm')
  row=dict(kind='manual-save-dialog-frame',stage='confirm',text=text,row=line,delok=delok,position=pos,native_observation_index=0,frame_sha256=self.sha,citation='manual:save-and-load')
  self.step=dict(inputs=[],output=dict(grid=[0]*128,binding=dict(sha256=self.sha,assertion=row)))
  self.observations=[dict(state=self.state)]
 def audit(self):oracle.verify_checkpoint(self.step,self.observations,self.case)
 def test_original_fixture_path_is_resolved_from_fixture_root(self):
  manifest=json.loads((self.fixture/'DERIVATION.json').read_text())
  for origin in manifest['origins']:
   relative=Path(origin['path'])
   self.assertFalse(relative.is_file(),'fixture-relative path must not depend on the process cwd')
   resolved=save_case.fixture_origin_path(origin)
   self.assertEqual(resolved,self.fixture/relative)
   self.assertEqual(digest(resolved),origin['sha256'])
   self.assertEqual(digest(resolved),manifest['original_files'][origin['original_name']])
  for unsafe in ('../outside.ptn','/tmp/outside.ptn'):
   with self.subTest(path=unsafe),self.assertRaisesRegex(ValueError,'stay within'):
    save_case.fixture_origin_path(dict(path=unsafe))
 def test_stock_source_cache_inventory_and_valid_literal_frame(self):self.audit()
 def test_stock_verifier_typed_branch(self):
  verify_teaching_checkpoint(self.step,self.observations,self.case,'controlled-experimental',[])
 def test_unhashed_cache_cannot_execute(self):
  p=self.run/'case-source/tests/behaviour/manual_save_dialog_oracle.py'
  p.write_text("raise AssertionError('UNHASHED CODE EXECUTED')\n")
  with self.assertRaisesRegex(ValueError,'Unhashed or changed'):
   verify_teaching_checkpoint(self.step,self.observations,self.case,'controlled-experimental',[])
 def test_changed_contract_cached_oracle_rejected_before_execution(self):
  p=self.run/'case-source/tests/behaviour/contract/manual_save_dialog_oracle.py'
  p.write_text(p.read_text()+'\\n# changed\\n')
  with self.assertRaisesRegex(ValueError,'Unhashed or changed'):self.audit()
 def test_missing_contract_oracle_source_hash_rejected(self):
  p=self.run/'start-source-identity.json';d=json.loads(p.read_text())
  del d['case_sources']['tests/behaviour/contract/manual_save_dialog_oracle.py'];p.write_text(json.dumps(d))
  with self.assertRaisesRegex(ValueError,'Missing contract-owned dialog implementation hash'):self.audit()
 def _legacy_snapshot(self,changed=False):
  legacy_run=self.run/'legacy-run';legacy_run.mkdir(exist_ok=True)
  files={name:(ROOT/name).read_bytes() for name in ['tests/behaviour/frame_oracle.py','tests/behaviour/driver.py','tests/behaviour/ui_map.py','tests/behaviour/manual_save_project_canonical.py','tests/behaviour/persisted_digest.lua']}
  old=ROOT/'tests/behaviour/testdata/legacy_manual_save_dialog_oracle.py'
  blob=old.read_bytes()+(b'\\n# changed\\n' if changed else b'')
  files['tests/behaviour/manual_save_dialog_oracle.py']=blob
  fixtures={str(p.relative_to(ROOT)):p.read_bytes() for p in self.fixture.rglob('*') if p.is_file()}
  persist_start_sources(legacy_run,dict(case_sources=files,fixture_sources=fixtures,capture_sources={},plan_files={}))
  case=legacy_run/'legacy-case';case.mkdir()
  return case
 def test_legacy_flat_source_snapshot_remains_verifiable(self):
  case=self._legacy_snapshot()
  self.assertEqual(hashlib.sha256((case.parent/'case-source/tests/behaviour/manual_save_dialog_oracle.py').read_bytes()).hexdigest(),'f65bf1a840e9060d6acfff8c6d8db8abc05487957c81b8b3fc148aad6470aa4a')
  verify_teaching_checkpoint(self.step,self.observations,case,'controlled-experimental',[])
 def test_modified_legacy_flat_source_snapshot_is_rejected(self):
  case=self._legacy_snapshot(changed=True)
  with self.assertRaisesRegex(ValueError,'Missing contract-owned dialog implementation hash'):
   verify_teaching_checkpoint(self.step,self.observations,case,'controlled-experimental',[])
 def test_wrong_kind_rejected(self):
  self.step['output']['binding']['assertion']['kind']='manual-save-dialog-invented'
  with self.assertRaisesRegex(ValueError,'Unsupported'):self.audit()
  with self.assertRaisesRegex(ValueError,'Unsupported'):check_custom_kind('manual-save-dialog-invented')
 def test_wrong_native_observation_rejected(self):
  self.step['output']['binding']['assertion']['native_observation_index']=1
  with self.assertRaisesRegex(ValueError,'observation'):self.audit()
 def test_wrong_binding_sha_rejected(self):
  self.step['output']['binding']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'Missing actual'):self.audit()
 def test_changed_cached_oracle_rejected_before_execution(self):
  p=self.run/'case-source/tests/behaviour/manual_save_dialog_oracle.py';p.write_text(p.read_text()+'\n# changed\n')
  with self.assertRaisesRegex(ValueError,'Unhashed or changed'):self.audit()
 def test_missing_source_hash_rejected(self):
  p=self.run/'start-source-identity.json';d=json.loads(p.read_text());del d['case_sources']['tests/behaviour/manual_save_dialog_oracle.py'];p.write_text(json.dumps(d))
  with self.assertRaisesRegex(ValueError,'Unhashed or changed'):self.audit()
 def test_changed_derived_fixture_rejected(self):
  p=self.run/'fixture-source/tests/behaviour/config/manual-save-dialog/Course seed.ptn';p.write_bytes(p.read_bytes()+b'changed')
  with self.assertRaisesRegex(ValueError,'Unhashed or changed'):self.audit()
 def persistence(self,picker=True):
  f=json.loads((self.fixture/'DERIVATION.json').read_text());w=self.case/'save-dialog-evidence';w.mkdir()
  for name,origin in zip(['Four notes.ptn','Four notes.pset'],f['origins']):
   source=Path(origin['path']);source=source if source.is_absolute() else self.fixture/source
   (w/name).write_bytes(source.read_bytes())
  (self.case/'results.json').write_text(json.dumps([dict(kind='selected-menu-label',text='Four notes.ptn')] if picker else []))
  original=Path(f['origins'][0]['path'])
  if not original.is_absolute():original=self.fixture/original
  content=__import__('manual_save_project_canonical').prove(w/'Four notes.ptn',original,self.fixture,ROOT/'tests/behaviour/persisted_digest.lua')
  self.step['output']['binding']['assertion']=dict(kind='manual-save-dialog-persistence',stage='saved',name='Four notes',files=dict(f['original_files']),original_files=f['original_files'],content=content,picker_confirmed=True,held_controls=[],outstanding_notes=False,fixture_sha256=digest(self.fixture/'DERIVATION.json'),citation='manual:save-and-load')
 def test_missing_public_picker_witness_rejected(self):
  self.persistence(False)
  with self.assertRaisesRegex(ValueError,'picker witness'):self.audit()
 def test_wrong_original_arrangement_hash_rejected(self):
  self.persistence();self.step['output']['binding']['assertion']['files']['Four notes.ptn']='0'*64
  with self.assertRaisesRegex(ValueError,'saved project copy'):self.audit()
 def test_cancel_produced_named_file_rejected(self):
  # Replace only the unit state with a synthetic selected-menu raster.
  from frame_oracle import render
  blob=render([(0,30,15,'< Save project')]);sha=hashlib.sha256(blob).hexdigest()
  self.state['frame']=dict(sha256=sha,pixels_base64=base64.b64encode(blob).decode());self.step['output']['binding']['sha256']=sha
  w=self.case/'save-dialog-evidence';w.mkdir();f=json.loads((self.fixture/'DERIVATION.json').read_text())
  value=dict(stage='cancel',files=dict(f['derived_files'],**{'Four notes.ptn':'0'*64}),named_files_absent=True,fixture_sha256=digest(self.fixture/'DERIVATION.json'))
  q=w/'cancel.json';q.write_text(json.dumps(value));self.step['inputs']=[dict(type='key',n=2,state=0)]
  self.step['output']['binding']['assertion']=dict(kind='manual-save-dialog-cancel',stage='cancel',receipt_sha256=digest(q),fixture_sha256=value['fixture_sha256'],citation='manual:save-and-load')
  with self.assertRaisesRegex(ValueError,'Cancelled save produced'):self.audit()

 def test_valid_full_decoded_persistence(self):
  self.persistence();self.audit()
 def test_missing_cached_lua_source_rejected(self):
  p=self.run/'start-source-identity.json';d=json.loads(p.read_text());del d['case_sources']['tests/behaviour/persisted_digest.lua'];p.write_text(json.dumps(d))
  with self.assertRaisesRegex(ValueError,'Unhashed or changed'):self.audit()
 def test_tampered_lua_source_rejected(self):
  p=self.run/'case-source/tests/behaviour/persisted_digest.lua';p.write_text(p.read_text()+'-- mutation\n')
  with self.assertRaisesRegex(ValueError,'Unhashed or changed'):self.audit()
 def test_changed_runtime_identity_rejected(self):
  self.persistence();p=self.run/'fixture-source/tests/behaviour/config/manual-save-dialog/CANONICAL-RUNTIME.json';d=json.loads(p.read_text());d['binary']['sha256']='0'*64;p.write_text(json.dumps(d))
  # Authentic source map alone cannot override the invoked runtime check.
  q=self.run/'start-source-identity.json';identity=json.loads(q.read_text());identity['fixture_sources'][str(p.relative_to(self.run/'fixture-source'))]=digest(p);q.write_text(json.dumps(identity))
  with self.assertRaisesRegex(ValueError,'runtime identity'):self.audit()
 
 def _tamper_bundled_runtime(self, relative):
  self.persistence();cached=self.run/'fixture-source/tests/behaviour/config/manual-save-dialog'/relative
  cached.write_bytes(cached.read_bytes()+b'\0mutation')
  q=self.run/'start-source-identity.json';identity=json.loads(q.read_text())
  fixture_relative='tests/behaviour/config/manual-save-dialog/'+relative
  identity['fixture_sources'][fixture_relative]=digest(cached);q.write_text(json.dumps(identity))
  with self.assertRaisesRegex(ValueError,'runtime identity'):
   self.audit()
 def test_tampered_bundled_binary_rejected(self):
  self._tamper_bundled_runtime('canonical-runtime/bin/lua5.3')
 def test_tampered_bundled_loader_rejected(self):
  self._tamper_bundled_runtime('canonical-runtime/lib64/ld-linux-x86-64.so.2')
 def test_tampered_bundled_library_rejected(self):
  self._tamper_bundled_runtime('canonical-runtime/lib/x86_64-linux-gnu/libreadline.so.8')
 def test_bundled_loader_resolves_every_runtime_library(self):
  import subprocess
  from manual_save_project_canonical import runtime_command
  fixture=self.fixture.resolve();runtime=json.loads((fixture/'CANONICAL-RUNTIME.json').read_text())
  command=runtime_command(fixture,runtime)
  loader=command[0];library_dir=command[3];binary=command[4]
  output=subprocess.check_output([loader,'--inhibit-cache','--library-path',library_dir,'--list',binary],text=True)
  resolved=[line.split('=>',1)[1].split('(',1)[0].strip() for line in output.splitlines() if '=>' in line]
  self.assertTrue(resolved)
  self.assertEqual(len(resolved),len(runtime['libraries'])+1)
  expected={str((fixture/item['path']).resolve()) for item in runtime['libraries']}|{str((fixture/runtime['loader']['path']).resolve())}
  self.assertEqual(set(resolved),expected)
  self.assertIn(str((fixture/runtime['loader']['path']).resolve()),output)
 def test_relocated_runtime_ignores_host_search_paths(self):
  import os,shutil,subprocess
  moved=Path(self.tmp.name)/'relocated-fixture';shutil.copytree(self.fixture,moved)
  runtime=json.loads((moved/'CANONICAL-RUNTIME.json').read_text())
  from manual_save_project_canonical import runtime_command
  env=dict(os.environ,LD_LIBRARY_PATH='/not/a/host/library/path',PATH='/not/a/host/bin/path')
  out=subprocess.check_output(runtime_command(moved,runtime,'-v'),env=env,text=True).strip()
  self.assertEqual(out,'Lua 5.3.3  Copyright (C) 1994-2016 Lua.org, PUC-Rio')
  q=self.run/'portable-runtime-smoke.ptn';q.write_text('return { { value=1 } }')
  oracle=ROOT/'tests/behaviour/persisted_digest.lua'
  from manual_save_project_canonical import canonical
  portable=subprocess.check_output(runtime_command(moved,runtime,str(oracle),str(moved/'canonical-runtime'),str(q)),env=env)
  self.assertEqual(portable,canonical(q,self.fixture,oracle))

 def test_every_musical_mutant_rejected_by_typed_audit(self):
  import subprocess
  self.persistence();w=self.case/'save-dialog-evidence';original=(w/'Four notes.ptn').read_bytes()
  runtime=json.loads((self.fixture/'CANONICAL-RUNTIME.json').read_text())
  # Mutate actual retained fields, retaining valid tab.save serialization.
  script="""local tab=dofile(arg[1]); local data=assert(tab.load(arg[2])); local visited={};local found=false
local function walk(t) if visited[t] then return end;visited[t]=true
local function alter(target) for k,v in pairs(target) do if type(v)=='number' then target[k]=v+1;return true elseif type(v)=='table' and alter(v) then return true end end return false end
for k,v in pairs(t) do if k==arg[4] and not found then if type(v)=='number' then t[k]=v+1;found=true elseif type(v)=='table' then found=alter(v) end end;if type(v)=='table' then walk(v) end end end
if arg[4]=='__extra' then data.extra_decoded_field=true;found=true else walk(data) end
assert(found,'Mutant did not touch an actual decoded field');tab.save(data,arg[3])"""
  tool=self.run/'mutate.lua';tool.write_text(script)
  for field in ['note_value','velocity_value','length','midi_channel','midi_device','transpose','repeats','start_trig','end_trig','global_pattern_length','selected_song_pattern','__extra']:
   with self.subTest(field=field):
    q=w/'Four notes.ptn';q.write_bytes(original)
    from manual_save_project_canonical import runtime_command
    subprocess.check_call(runtime_command(self.fixture,runtime,str(tool),str(self.fixture/runtime['tabutil']['relative']),str(q),str(q),field))
    self.step['output']['binding']['assertion']['files']['Four notes.ptn']=digest(q)
    with self.assertRaisesRegex(ValueError,'complete decoded'):self.audit()

 def test_stock_alias_and_cycle_contract(self):
  from manual_save_project_canonical import canonical
  import subprocess
  q=self.run/'synthetic.ptn';oracle=ROOT/'tests/behaviour/persisted_digest.lua'
  # tab.load expands references; repeated aliases compare by complete value.
  q.write_text('return { { {2}, {2} }, { x=1 } }')
  alias=canonical(q,self.fixture,oracle)
  q.write_text('return { { {2}, {3} }, { x=1 }, { x=1 } }')
  self.assertEqual(alias,canonical(q,self.fixture,oracle))
  q.write_text('return { { self={1} } }')
  with self.assertRaises(subprocess.CalledProcessError):canonical(q,self.fixture,oracle)
 def test_stock_retains_scalar_types_and_every_field(self):
  from manual_save_project_canonical import canonical
  q=self.run/'synthetic.ptn';oracle=ROOT/'tests/behaviour/persisted_digest.lua'
  q.write_text('return { { value=1 } }');baseline=canonical(q,self.fixture,oracle)
  for literal in ['"1"','true','1.0']:
   with self.subTest(literal=literal):
    q.write_text('return { { value='+literal+' } }');self.assertNotEqual(baseline,canonical(q,self.fixture,oracle))

 def test_actual_selected_case_source_inventory_contains_lua(self):
  from manual_case_capture import case_source_paths
  lua=ROOT/'tests/behaviour/persisted_digest.lua'
  self.assertIn(lua,case_source_paths(ROOT,[dict(behaviour_case='M-MANUAL-SAVE-DIALOG-001')]))
  self.assertNotIn(lua,case_source_paths(ROOT,[dict(behaviour_case='M-MANUAL-COURSE-001')]))

if __name__=='__main__':unittest.main()

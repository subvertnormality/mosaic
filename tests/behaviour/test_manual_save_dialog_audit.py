"""Negative typed-audit tests using explicitly synthetic unit fixtures.

No emulated framebuffer or native acceptance report is claimed by these tests.
Stock source snapshot machinery supplies the source-cache test fixture.
"""
import base64,copy,hashlib,json,tempfile,unittest
from pathlib import Path
import manual_save_dialog_oracle as oracle
from manual_case_capture import persist_start_sources
from manual_publication_verify import check_custom_kind,verify_teaching_checkpoint

ROOT=Path(__file__).resolve().parents[2]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class SaveDialogAuditTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.run=Path(self.tmp.name);self.case=self.run/'M-MANUAL-SAVE-DIALOG-001-base-midi';self.case.mkdir()
  self.fixture=ROOT/'tests/behaviour/config/manual-save-dialog'
  cases={name:(ROOT/name).read_bytes() for name in ['tests/behaviour/manual_save_dialog_oracle.py','tests/behaviour/frame_oracle.py','tests/behaviour/driver.py','tests/behaviour/ui_map.py','tests/behaviour/manual_save_project_canonical.py','tests/behaviour/persisted_digest.lua']}
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
 def test_stock_source_cache_inventory_and_valid_literal_frame(self):self.audit()
 def test_stock_verifier_typed_branch(self):
  verify_teaching_checkpoint(self.step,self.observations,self.case,'controlled-experimental',[])
 def test_unhashed_cache_cannot_execute(self):
  p=self.run/'case-source/tests/behaviour/manual_save_dialog_oracle.py'
  p.write_text("raise AssertionError('UNHASHED CODE EXECUTED')\n")
  with self.assertRaisesRegex(ValueError,'Unhashed or changed'):
   verify_teaching_checkpoint(self.step,self.observations,self.case,'controlled-experimental',[])
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
  for name,origin in zip(['Four notes.ptn','Four notes.pset'],f['origins']):(w/name).write_bytes(Path(origin['path']).read_bytes())
  (self.case/'results.json').write_text(json.dumps([dict(kind='selected-menu-label',text='Four notes.ptn')] if picker else []))
  self.step['output']['binding']['assertion']=dict(kind='manual-save-dialog-persistence',stage='saved',name='Four notes',files=dict(f['original_files']),original_files=f['original_files'],content=__import__('manual_save_project_canonical').prove(w/'Four notes.ptn',Path(f['origins'][0]['path']),self.fixture,ROOT/'tests/behaviour/persisted_digest.lua'),picker_confirmed=True,held_controls=[],outstanding_notes=False,fixture_sha256=digest(self.fixture/'DERIVATION.json'),citation='manual:save-and-load')
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
    subprocess.check_call([runtime['binary']['path'],str(tool),str(self.fixture/runtime['tabutil']['relative']),str(q),str(q),field])
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

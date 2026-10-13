"""The coordinated authority switch preserves historical evidence and fails closed."""
import contextlib,copy,hashlib,io,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
import yaml
import reconcile_manual as rec
from manual_authority import authoring_identity,verify_authority,verify_manual_sources

class AuthorityTransitionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name)
  for folder in ['manual/legacy','manual/features','manual/generated','tools','tests/behaviour','docs/testing']:
   (self.root/folder).mkdir(parents=True)
  original='\n'.join(['## Getting Started','Original controls']+['### H'+str(i)+'\nText '+str(i) for i in range(1,125)])+'\n'
  self.legacy=self.root/'manual/legacy/README-1.4.0.md';self.legacy.write_text(original)
  self.cheat_legacy=self.root/'manual/legacy/cheat-sheet-1.4.0.html'
  cheat='\n'.join('<div class="command-text">Control '+str(i)+'</div>' for i in range(77))+'\n'
  self.cheat_legacy.write_text(cheat);(self.root/'cheat_sheet.html').write_text(cheat)
  (self.root/'README.md').write_text(original.replace('Original controls','Original controls; current vertical UI'))
  sections=[dict(s,id='MAN-%03d'%(i+1),status='in_progress',requirements=[]) for i,s in enumerate(rec.manual_sections((self.root/'README.md').read_text()))]
  requirements=[dict(id='R'+str(i),cases=[]) for i in range(178)]
  for i in range(876):requirements[i%178]['cases'].append('C'+str(i))
  requirements[0]['cases'].append('M-UI-VERTICAL-001')
  self.inventory=dict(manual='README.md',manual_sha256=rec.digest(self.root/'README.md'),sections=sections,requirements=requirements,manual_sources=[dict(path='README.md',sha256=rec.digest(self.root/'README.md')),dict(path='cheat_sheet.html',sha256=rec.digest(self.root/'cheat_sheet.html'))],image_references=[],statement_mappings=[])
  for i,line in enumerate(cheat.splitlines()):
   self.inventory['statement_mappings'].append(dict(id='S'+str(i),source=dict(path='cheat_sheet.html',line=i+1,text='Control '+str(i),sha256=hashlib.sha256(line.encode()).hexdigest()),proposed_requirements=['R'+str(i%178)],status='in_progress'))
  self.data=dict(features=[dict(id='f'+str(i),scene_refs=['scene'],review={'status':'verified'}) for i in range(125)],aliases={})
  (self.root/'manual/book.yaml').write_text('sources: [features/a.yaml]\n')
  (self.root/'manual/features/a.yaml').write_text(yaml.safe_dump({'features':self.data['features']}))
  cross={'features':[dict(id='f'+str(i),readme={'section_ids':['MAN-%03d'%(i+1)]}) for i in range(125)]}
  (self.root/'manual/inventory.json').write_text(json.dumps(cross))
  self.book=dict(self.data,complete_manual=True,source_sha256=hashlib.sha256(json.dumps(self.data,sort_keys=True,separators=(',',':')).encode()).hexdigest(),authoring_identity=authoring_identity(self.root),scenes={'scene':dict(behaviour_case='CASE',steps=[dict(output={'binding':dict(passed=True,semantic_assertions=1,sha256='frame',grid_sha256='grid')})])})
  (self.root/'manual/generated/book.json').write_text(json.dumps(self.book))
  (self.root/'tools/manual_book.py').write_text('def load(): return '+repr(self.data)+'\ndef compile_book(data): return '+repr(self.book)+'\n')
  self.patches=[patch.object(rec,'REPO',self.root),patch.object(rec,'ORIGINAL_README_SHA256',rec.digest(self.legacy)),patch.object(rec,'ORIGINAL_CHEAT_SHA256',rec.digest(self.cheat_legacy))]
  for item in self.patches:item.start();self.addCleanup(item.stop)
 def plan(self,**options):return rec.plan_transition(self.inventory,{},**options)
 def install(self,planned):
  updated,matrix,snapshots=planned
  for relative,raw in snapshots.items():
   path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  return updated
 def test_prepare_is_inactive_and_does_not_bind_mutable_authoring(self):
  updated,_,_=self.plan(prepare=True)
  self.assertEqual(updated['manual_authority']['status'],'inactive')
  self.assertNotIn('identity',updated['manual_authority'])
  (self.root/'manual/features/a.yaml').write_text('changed after preparation')
  self.assertIsNone(verify_authority(self.root,updated))
 def test_freeze_routes_all_77_original_cheat_records(self):
  updated=self.install(self.plan(freeze=True,prepare=True))
  self.assertEqual(len(updated['legacy_cheat_history']['rows']),77)
  self.assertEqual(len(updated['statement_mappings']),77)
  for old,new in zip(self.inventory['statement_mappings'],updated['statement_mappings']):
   self.assertEqual(new['historical_source'],old['source']);self.assertNotEqual(new['source']['path'],'cheat_sheet.html')
  (self.root/'README.md').write_text('# Overview\n## Install\n')
  (self.root/'cheat_sheet.html').write_text('Generated new table')
  verify_manual_sources(self.root,updated)
 def test_activation_after_edited_readme_uses_original_archive_identity(self):
  self.inventory=self.install(self.plan(freeze=True,prepare=True))
  (self.root/'README.md').write_text('# Overview only\n')
  updated,_,_=self.plan(activate=True)
  self.assertEqual(updated['historical_manual']['sha256'],rec.digest(self.legacy))
  self.assertNotEqual(updated['historical_manual']['sha256'],self.inventory['manual_sha256'])
  self.assertEqual(updated['manual'],'manual/book.yaml')
  verify_manual_sources(self.root,updated)
 def test_transition_preserves_125_sections_178_requirements_876_original_cases_and_extension(self):
  baseline=copy.deepcopy(self.inventory)
  self.inventory=self.install(self.plan(freeze=True,prepare=True))
  updated,_,_=self.plan(activate=True)
  self.assertEqual([s['id'] for s in updated['sections']],[s['id'] for s in baseline['sections']])
  self.assertEqual(updated['requirements'],baseline['requirements'])
  self.assertEqual(len(updated['sections']),125);self.assertEqual(len(updated['requirements']),178)
  self.assertEqual(len({c for r in updated['requirements'] for c in r['cases']}),877)
 def test_incomplete_activation_fails_without_source_writes(self):
  self.book['complete_manual']=False;(self.root/'manual/generated/book.json').write_text(json.dumps(self.book))
  before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
  with self.assertRaisesRegex(ValueError,'incomplete'):self.plan(activate=True)
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
 def test_missing_book_activation_fails_without_snapshot_writes(self):
  (self.root/'manual/generated/book.json').unlink()
  with self.assertRaisesRegex(ValueError,'Missing compiled'):self.plan(activate=True)
  self.assertEqual(len(list((self.root/'manual/legacy').iterdir())),2)
 def test_stale_book_activation_fails_without_snapshot_writes(self):
  self.book['source_sha256']='stale';(self.root/'manual/generated/book.json').write_text(json.dumps(self.book))
  with self.assertRaisesRegex(ValueError,'Compiled manual source changed'):self.plan(activate=True)
  self.assertEqual(len(list((self.root/'manual/legacy').iterdir())),2)
 def test_claim_must_have_exact_historical_line_hash_to_archive(self):
  self.inventory['statement_mappings'][0]['source']['sha256']='fabricated'
  with self.assertRaisesRegex(ValueError,'exact historical'):self.plan(freeze=True)
 def test_changed_original_archive_is_rejected(self):
  self.legacy.write_text('Changed original')
  with self.assertRaisesRegex(ValueError,'Original README'):self.plan(freeze=True)
 def test_cli_help_has_no_gate_or_snapshot_side_effect(self):
  before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
  with contextlib.redirect_stdout(io.StringIO()):
   with self.assertRaises(SystemExit) as exited:rec.main(['--help'])
  self.assertEqual(exited.exception.code,0)
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
 def test_cli_plan_freeze_has_no_gate_or_snapshot_writes(self):
  inv=self.root/'tests/behaviour/manual-inventory.json';inv.write_text(json.dumps(self.inventory))
  matrix=self.root/'docs/testing/unit-integration-hardening-matrix.json';matrix.write_text('{}')
  before_inv=inv.read_bytes();before_matrix=matrix.read_bytes()
  with patch.object(rec,'INVENTORY',inv),patch.object(rec,'MATRIX',matrix),contextlib.redirect_stdout(io.StringIO()) as output:
   rec.main(['--freeze-manual-sources','--prepare-authority','--plan'])
  planned=json.loads(output.getvalue());self.assertFalse(planned['writes_performed'])
  self.assertEqual(inv.read_bytes(),before_inv);self.assertEqual(matrix.read_bytes(),before_matrix)
  self.assertEqual(len(list((self.root/'manual/legacy').iterdir())),2)
 def test_cli_incomplete_activation_leaves_inventory_matrix_and_archives_unchanged(self):
  inv=self.root/'tests/behaviour/manual-inventory.json';inv.write_text(json.dumps(self.inventory))
  matrix=self.root/'docs/testing/unit-integration-hardening-matrix.json';matrix.write_text('{}')
  self.book['complete_manual']=False;(self.root/'manual/generated/book.json').write_text(json.dumps(self.book))
  before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
  with patch.object(rec,'INVENTORY',inv),patch.object(rec,'MATRIX',matrix):
   with self.assertRaisesRegex(ValueError,'incomplete'):rec.main(['--activate-authority'])
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
 def test_missing_semantic_contract_cannot_activate_or_create_snapshots(self):
  self.book['scenes']={};(self.root/'manual/generated/book.json').write_text(json.dumps(self.book))
  with self.assertRaisesRegex(ValueError,'Missing scene contract'):self.plan(activate=True)
  self.assertEqual(len(list((self.root/'manual/legacy').iterdir())),2)
 def test_frozen_alias_cannot_escape_workspace(self):
  updated=self.install(self.plan(freeze=True,prepare=True))
  updated['manual_source_aliases']['README.md']['path']='../../outside'
  with self.assertRaisesRegex(ValueError,'Unsafe manual source'):verify_manual_sources(self.root,updated)
 def test_complete_flag_cannot_override_actual_compiler_incompleteness(self):
  actual=dict(self.book,complete_manual=False)
  (self.root/'tools/manual_book.py').write_text('def load(): return '+repr(self.data)+'\ndef compile_book(data): return '+repr(actual)+'\n')
  with self.assertRaisesRegex(ValueError,'incomplete'):self.plan(activate=True)
  self.assertEqual(len(list((self.root/'manual/legacy').iterdir())),2)
 def test_preparing_active_authority_cannot_silently_downgrade_gate(self):
  self.inventory=self.install(self.plan(freeze=True,prepare=True))
  self.inventory=self.plan(activate=True)[0]
  updated,_,_=self.plan(prepare=True)
  self.assertEqual(updated['manual_authority']['status'],'active')
  self.assertIn('identity',updated['manual_authority'])
 def test_additive_registered_case_links_each_requirement_without_rewriting_history(self):
  baseline=copy.deepcopy(self.inventory)
  registry={'M-MERGE-STRATEGY-001':{'requirements':['R0','R1'],'description':'Shared Strategy selector acceptance'}}
  revised=rec.add_registered_cases(self.inventory,registry,{'path':'tests/behaviour/cases.py','sha256':'candidate'})
  for index,row in enumerate(revised['requirements']):
   expected=baseline['requirements'][index]['cases']+(['M-MERGE-STRATEGY-001'] if row['id'] in ['R0','R1'] else [])
   self.assertEqual(row['cases'],expected)
   self.assertEqual({k:v for k,v in row.items() if k!='cases'},{k:v for k,v in baseline['requirements'][index].items() if k!='cases'})
  self.assertEqual(self.inventory,baseline)
  self.assertFalse(revised['inventory_extensions'][-1]['complete_regression_run'])
 def test_unknown_requirement_registration_fails_without_inventory_mutation(self):
  baseline=copy.deepcopy(self.inventory)
  with self.assertRaisesRegex(ValueError,'Unknown canonical requirement'):
   rec.add_registered_cases(self.inventory,{'NEW':{'requirements':['missing']}},{})
  self.assertEqual(self.inventory,baseline)
 def test_transition_plan_includes_new_current_canonical_case_extension(self):
  registry={'M-MERGE-STRATEGY-001':{'requirements':['R0','R1']}}
  with patch.object(rec,'canonical_registry',return_value=(registry,{'path':'cases.py','sha256':'new'})):
   revised,_,_=self.plan(prepare=True)
  cases={c for row in revised['requirements'] for c in row['cases']}
  self.assertEqual(len(cases),878)
  self.assertIn('M-UI-VERTICAL-001',cases)
  self.assertIn('M-MERGE-STRATEGY-001',cases)
 def test_matrix_links_only_additive_extensions_without_claiming_acceptance(self):
  registry={'M-MERGE-STRATEGY-001':{'requirements':['R0','R1']}}
  revised=rec.add_registered_cases(self.inventory,registry,{'sha256':'new'})
  matrix={'counts':{'requirements':177},'domains':[{'id':'H16','requirement_ids':['R0','R1'],'linked_behaviour_cases':['HISTORICAL'],'status':'partial'}]}
  linked=rec.link_case_extensions(matrix,revised)
  self.assertEqual(matrix['domains'][0]['linked_behaviour_cases'],['HISTORICAL'])
  self.assertEqual(linked['domains'][0]['linked_behaviour_cases'],['HISTORICAL','M-MERGE-STRATEGY-001'])
  self.assertEqual(linked['domains'][0]['status'],'partial');self.assertEqual(linked['counts'],matrix['counts'])
  self.assertFalse(linked['case_registration_extensions'][0]['complete_regression_run'])
  self.assertEqual(rec.link_case_extensions(linked,revised),linked)
 def test_frozen_snapshot_drift_is_rejected(self):
  self.inventory=self.install(self.plan(freeze=True,prepare=True))
  (self.root/self.inventory['section_manual']['path']).write_text('changed')
  with self.assertRaisesRegex(ValueError,'Frozen manual'):self.plan()
if __name__=='__main__':unittest.main()


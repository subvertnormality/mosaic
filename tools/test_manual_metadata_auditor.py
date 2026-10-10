"""Native auditor integration: metadata transition never excuses source drift."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import manual_metadata_transition as transition
import manual_publication_verify as auditor

class NativeMetadataAuditorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.top=Path(self.tmp.name)
  self.current=self.top/'repo';self.captured=self.top/'captured';self.run=self.top/'run'
  files=list(transition.METADATA)+['lib/example.lua','docs/ui-reimplementation/tools/helper.py']+[f'lib/source-{i}.lua' for i in range(241)]
  entries=[]
  for relative in files:
   raw=('original:'+relative).encode()
   for base in (self.current,self.captured/'mosaic'):
    p=base/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
   entries.append({'path':'mosaic/'+relative,'sha256':hashlib.sha256(raw).hexdigest(),'size':len(raw)})
  self.identity=self.run/'native/identity.json';self.identity.parent.mkdir(parents=True)
  self.identity.write_text(json.dumps({'application_identity':{'code_root':str(self.captured),'files':entries,'digest':'original-capture-digest'}}))
  self.proof={'schema_version':1,'kind':'post-reconcile-metadata-transition','metadata_paths':list(transition.METADATA),'before':{},'after':{}}
  for relative in transition.METADATA:
   p=self.current/relative;original=p.read_bytes();p.write_bytes(original+b' reviewed')
   self.proof['before'][relative]={'sha256':hashlib.sha256(original).hexdigest(),'size':len(original)}
   self.proof['after'][relative]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size}
 def tearDown(self):self.tmp.cleanup()
 def invoke(self,context=False):
  token=transition._TRANSITION_CONTEXT.set(self.proof if context else None)
  try:
   with patch.object(auditor,'ROOT',self.current),patch.object(auditor,'capture_application_root',return_value=self.captured/'mosaic'):
    return auditor.native_source_identity(self.run)
  finally:transition._TRANSITION_CONTEXT.reset(token)
 def test_default_still_rejects_reviewed_metadata(self):
  with self.assertRaisesRegex(ValueError,'Stale native Mosaic source'):self.invoke()
 def test_explicit_context_accepts_only_three_metadata_paths(self):
  result=self.invoke(True)
  self.assertEqual(result['reviewed_metadata_transition'],{'exact_application_files':243,'transitioned_metadata_files':3})
  self.assertEqual(result['application_digest'],'original-capture-digest')
  with self.assertRaisesRegex(ValueError,'Stale native Mosaic source'):self.invoke()
 def test_context_does_not_excuse_lua_drift(self):
  (self.current/'lib/example.lua').write_bytes(b'changed behaviour')
  with self.assertRaisesRegex(ValueError,'Stale native Mosaic source: mosaic/lib/example.lua'):self.invoke(True)
 def test_context_does_not_excuse_documentation_helper_drift(self):
  (self.current/'docs/ui-reimplementation/tools/helper.py').write_bytes(b'changed capture helper')
  with self.assertRaisesRegex(ValueError,'Stale native Mosaic source: mosaic/docs/ui-reimplementation/tools/helper.py'):self.invoke(True)
 def test_context_never_excuses_modified_capture(self):
  (self.captured/'mosaic'/transition.METADATA[0]).write_bytes(b'tampered original')
  with self.assertRaisesRegex(ValueError,'Changed native application source'):self.invoke(True)
 def test_context_requires_correct_recorded_after_bytes(self):
  (self.current/transition.METADATA[1]).write_bytes(b'forged final ledger')
  with self.assertRaisesRegex(ValueError,'post-reconcile bytes not pinned'):self.invoke(True)

class ReconciliationRollbackTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.top=Path(self.tmp.name);self.root=self.top/'repo';self.evidence=self.top/'evidence';self.proof=self.top/'transition.json'
  self.originals={}
  inventory={'files':{},'manual_sections':[],'grid_registrations':[],'controller_units':[]}
  for relative,data in zip(transition.METADATA,({},inventory,{})):
   p=self.root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));self.originals[p]=p.read_bytes()
  self.review={'baseline_inventory':'baseline.json','post_build_review':{'changes':[],'validation_scope':'controlled-manual-generation'}}
  self.inventory=inventory
 def tearDown(self):self.tmp.cleanup()
 def invoke(self,proof_creator):
  import manual_reconcile_build as reconciler
  from contextlib import ExitStack
  with ExitStack() as stack:
   stack.enter_context(patch.object(reconciler,'ROOT',self.root))
   stack.enter_context(patch.object(reconciler,'prepare',return_value=self.review))
   stack.enter_context(patch.object(reconciler.refresher,'refresh',return_value=(self.inventory,{'branches':[]})))
   stack.enter_context(patch('validate.validate',return_value=[]))
   stack.enter_context(patch.object(transition,'create_proof',side_effect=proof_creator))
   stack.enter_context(patch.object(auditor,'audit_controlled_manual_generation',side_effect=ValueError('final native audit rejected')))
   return reconciler.reconcile(self.top/'build','pinned',self.top/'snapshot',self.evidence,self.top/'overlay','overlaypin',self.proof,self.top/'native/identity.json')
 def test_proof_failure_restores_all_original_metadata(self):
  def fail(*args):raise ValueError('proof replay rejected')
  with self.assertRaisesRegex(ValueError,'proof replay rejected'):self.invoke(fail)
  self.assertTrue(all(p.read_bytes()==raw for p,raw in self.originals.items()))
  self.assertFalse(self.proof.exists())
 def test_final_audit_failure_restores_metadata_and_preserves_failed_proof(self):
  def create(*args):self.proof.write_text('saved rejected proof')
  with self.assertRaisesRegex(ValueError,'final native audit rejected'):self.invoke(create)
  self.assertTrue(all(p.read_bytes()==raw for p,raw in self.originals.items()))
  self.assertFalse(self.proof.exists())
  self.assertEqual((self.evidence/'failed-metadata-transition-proof.json').read_text(),'saved rejected proof')
 def test_partial_transition_options_rejected_before_mutation(self):
  import manual_reconcile_build as reconciler
  with patch.object(reconciler,'ROOT',self.root):
   with self.assertRaisesRegex(ValueError,'supplied together'):
    reconciler.reconcile(self.top/'build','pin',self.top/'snapshot',self.evidence,self.top/'overlay')
  self.assertFalse(self.evidence.exists())
  self.assertTrue(all(p.read_bytes()==raw for p,raw in self.originals.items()))

if __name__=='__main__':unittest.main()

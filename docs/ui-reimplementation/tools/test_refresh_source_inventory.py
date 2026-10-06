"""Fail-closed source-review contracts; fixtures are temporary, never production files."""
import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import refresh_source_inventory as tool

class SourceReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.source="function owner()\n press:register(\n if gate then\n run()\n end\n )\nend\n"
  self.manual="## Topic\n\nOriginal guidance.\n"
  (self.root/'owner.lua').write_text(self.source);(self.root/'README.md').write_text(self.manual)
  blobs={'owner.lua':self.source.encode(),'README.md':self.manual.encode()}
  self.blobs=blobs
  self.old={'head':'abc','files':{k:tool.digest(v) for k,v in blobs.items()},'grid_registrations':[{'id':'callback','source':'owner.lua','ordinal':1,'line':2,'branches':[{'id':'branch','lines':'3-5'}]}],'controller_units':[{'id':'owner','source':'owner.lua','line':1}],'manual_sections':[{'id':'MAN.001','heading':'Topic','text':'Original guidance.','line':1}]}
  self.baseline=self.root/'baseline.json';self.baseline.write_text(json.dumps(self.old))
  self.review={'files':{k:{'sha256':tool.digest(v),'meaning':'Reviewed fixture semantics'} for k,v in blobs.items()},'new_manual_sections':{},'read_on':'2026-10-03','head':'candidate','identity':'fixture'}
 def tearDown(self):self.tmp.cleanup()
 def invoke(self):
  # Historical bytes come from the fixture, mimicking immutable git-show data.
  with patch.object(tool,'REPO',self.root),patch.object(tool,'ROOT',self.root),patch.object(tool.subprocess,'check_output',side_effect=lambda args,**kw:self.blobs[args[-1].split(':',1)[1]]):
   return tool.refresh(self.baseline,self.review)
 def test_retains_branch_and_manual_identity_with_inserted_comment(self):
  current='-- inserted context\n'+self.source;(self.root/'owner.lua').write_text(current);self.review['files']['owner.lua']['sha256']=tool.digest(current.encode())
  out,receipt=self.invoke()
  self.assertEqual(out['grid_registrations'][0]['line'],3)
  self.assertEqual(out['grid_registrations'][0]['branches'][0]['lines'],'4-6')
  self.assertEqual(out['manual_sections'][0]['id'],'MAN.001')
  self.assertTrue(receipt['branches'][0]['review'].startswith('original source lines retained in order'))
 def test_rejects_current_bytes_that_were_not_reviewed(self):
  (self.root/'owner.lua').write_text(self.source+'-- unexpected change\n')
  with self.assertRaisesRegex(AssertionError,'unreviewed source bytes'):self.invoke()
 def test_rejects_hash_only_review_without_meaning(self):
  self.review['files']['owner.lua'].pop('meaning')
  with self.assertRaisesRegex(AssertionError,'missing semantic review'):self.invoke()
 def test_rejects_changed_branch_action_despite_reviewed_hash(self):
  current=self.source.replace('run()','corrupt()');(self.root/'owner.lua').write_text(current);self.review['files']['owner.lua']['sha256']=tool.digest(current.encode())
  with self.assertRaisesRegex(AssertionError,'branch body changed'):self.invoke()
 def test_rejects_changed_callback_kind_despite_reviewed_hash(self):
  current=self.source.replace('press:register(','press:register_long(');(self.root/'owner.lua').write_text(current);self.review['files']['owner.lua']['sha256']=tool.digest(current.encode())
  with self.assertRaisesRegex(AssertionError,'callback kind changed'):self.invoke()
 def test_rejects_inserted_branch_action_even_if_original_lines_survive(self):
  current=self.source.replace(' run()', ' corrupt()\n run()');(self.root/'owner.lua').write_text(current);self.review['files']['owner.lua']['sha256']=tool.digest(current.encode())
  with self.assertRaisesRegex(AssertionError,'unreviewed branch addition'):self.invoke()
 def test_rejects_historical_identity_mismatch(self):
  self.blobs['owner.lua']=b'unrelated baseline'
  with self.assertRaisesRegex(AssertionError,'historical source does not match ledger'):self.invoke()

 def replacement(self):
  current=self.source.replace('if gate then\n run()','if replacement_gate then\n accept()')
  (self.root/'owner.lua').write_text(current);self.review['files']['owner.lua']['sha256']=tool.digest(current.encode())
  old='\n'.join(self.source.splitlines()[2:5]);new='\n'.join(current.splitlines()[2:5])
  self.review['branch_transformations']={'branch':{'old_sha256':tool.digest(old.encode()),'source':'owner.lua','replacement':new,'meaning':'Authorized new fixture branch, separately evidenced','dependencies':{'owner.lua':tool.digest(current.encode())}}}
  return current
 def test_explicit_exact_replacement_keeps_historical_identity(self):
  self.replacement();out,receipt=self.invoke()
  self.assertEqual(out['grid_registrations'][0]['branches'][0]['id'],'branch')
  self.assertEqual(out['grid_registrations'][0]['branches'][0]['lines'],'3-5')
  self.assertIn('explicit reviewed behavior replacement',receipt['branches'][0]['review'])
 def test_explicit_replacement_rejects_wrong_historical_body(self):
  self.replacement();self.review['branch_transformations']['branch']['old_sha256']='wrong'
  with self.assertRaisesRegex(AssertionError,'historical branch replacement identity'):self.invoke()
 def test_explicit_replacement_rejects_unreviewed_dependency(self):
  self.replacement();self.review['branch_transformations']['branch']['dependencies']['owner.lua']='wrong'
  with self.assertRaisesRegex(AssertionError,'replacement dependency identity'):self.invoke()
 def test_explicit_replacement_rejects_missing_meaning(self):
  self.replacement();self.review['branch_transformations']['branch'].pop('meaning')
  with self.assertRaisesRegex(AssertionError,'replacement semantic review'):self.invoke()


 def test_frozen_full_manual_keeps_MAN_ids_when_root_becomes_overview(self):
  archive='manual/legacy/full-ui-manual.md';(self.root/archive).parent.mkdir(parents=True)
  (self.root/archive).write_text(self.manual)
  overview="## Overview\n\nThe interactive YAML manual is authoritative.\n"
  (self.root/'README.md').write_text(overview)
  self.review['files']['README.md']={'sha256':tool.digest(overview.encode()),'meaning':'Current root overview, separately reviewed'}
  self.review['files'][archive]={'sha256':tool.digest(self.manual.encode()),'meaning':'Exact frozen full UI manual with historical section identities'}
  self.review['manual_source']={'file':archive,'sha256':tool.digest(self.manual.encode()),'meaning':'Keep historical MAN slices bound to frozen full manual, not overview'}
  out,receipt=self.invoke()
  self.assertEqual(out['manual_sections'][0]['id'],'MAN.001')
  self.assertEqual(out['manual_sections'][0]['heading'],'Topic')
  self.assertEqual(out['manual_source']['file'],archive)
  self.assertEqual(receipt['manual_source']['sha256'],tool.digest(self.manual.encode()))


 def archive_reference(self):
  path='manual/legacy/frozen.md';(self.root/path).parent.mkdir(parents=True)
  (self.root/path).write_text(self.manual)
  self.review['files'][path]={'sha256':tool.digest(self.manual.encode()),'meaning':'Frozen reference source'}
  self.review['manual_source']={'file':path,'sha256':tool.digest(self.manual.encode()),'meaning':'Historical section reference, separate from overview/YAML authority'}
 def test_frozen_manual_rejects_fingerprint_reset_without_exact_bytes(self):
  self.archive_reference();self.review['manual_source']['sha256']='wrong'
  with self.assertRaisesRegex(AssertionError,'unreviewed manual source identity'):self.invoke()
 def test_frozen_manual_rejects_missing_semantic_review(self):
  self.archive_reference();self.review['manual_source'].pop('meaning')
  with self.assertRaisesRegex(AssertionError,'missing manual source semantic review'):self.invoke()
 def test_frozen_manual_rejects_source_outside_repository(self):
  self.archive_reference();self.review['manual_source']['file']='../outside.md'
  with self.assertRaisesRegex(AssertionError,'manual source outside repository'):self.invoke()
 def test_frozen_manual_rejects_unreviewed_archive(self):
  self.archive_reference();self.review['files'].pop(self.review['manual_source']['file'])
  with self.assertRaisesRegex(AssertionError,'unreviewed manual source identity'):self.invoke()

if __name__=='__main__':unittest.main()

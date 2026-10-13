"""Characterisation outside the legacy manual: citation migration and evidence identity."""
import copy, hashlib, json, tempfile, unittest
from unittest import mock
import reconcile_manual
from pathlib import Path
from manual_authority import authoring_identity, resolve_feature, verify_authority, feature_links

class ManualAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/"manual/features").mkdir(parents=True)
        (self.root/"manual/generated").mkdir()
        (self.root/"manual/book.yaml").write_text("sources: [features/a.yaml]\naliases: {old-a: a}\n")
        (self.root/"manual/features/a.yaml").write_text("features:\n- id: a\n  scene_refs: [scene-a]\n  sources: {readme: 'manual/legacy/README-1.4.0.md#a'}\n")
        self.book = {"features":[{"id":"a","scene_refs":["scene-a"]}], "aliases":{"old-a":"a"},
                     "scenes":{"scene-a":{"behaviour_case":"CASE-A","steps":[{"output":{"binding":{"passed":True,"semantic_assertions":1,"sha256":"frame","grid_sha256":"grid"}}}]}}}
        self.book["authoring_identity"]=authoring_identity(self.root)
        self.inventory = {"manual":"README.md","manual_sha256":"historical",
                          "requirements":[{"id":"REQ","cases":["CASE-A"]}],
                          "sections":[{"id":"MAN-001","requirements":["REQ"],"title":"A"}],
                          "statement_mappings":[{"source":{"path":"README.md","line":12,"sha256":"old"}}]}
    def test_alias_and_stable_feature_citations_resolve(self):
        self.assertEqual(resolve_feature(self.book,"manual:a")["id"],"a")
        self.assertEqual(resolve_feature(self.book,"manual/#old-a")["id"],"a")
    def test_unknown_feature_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unknown manual feature"):
            resolve_feature(self.book,"missing")
    def test_all_authoring_files_are_hashed_and_change_invalidates_identity(self):
        before=authoring_identity(self.root)
        self.assertEqual(set(before["files"]),{"manual/book.yaml","manual/features/a.yaml"})
        (self.root/"manual/features/a.yaml").write_text("features: []\n")
        self.assertNotEqual(before,authoring_identity(self.root))
    def test_missing_authoring_source_fails_closed(self):
        (self.root/"manual/features/a.yaml").unlink()
        with self.assertRaisesRegex(ValueError,"Missing authoring"):
            authoring_identity(self.root)
    def test_unknown_or_missing_feature_link_cannot_earn_migration_credit(self):
        inv=copy.deepcopy(self.inventory)
        inv["manual_authority"]={"identity":authoring_identity(self.root),"feature_links":{"MAN-001":["missing"]}}
        with self.assertRaisesRegex(ValueError,"Unknown manual feature"):
            verify_authority(self.root,inv,self.book)
        inv["manual_authority"]["feature_links"]={}
        with self.assertRaisesRegex(ValueError,"Missing feature"):
            verify_authority(self.root,inv,self.book)
    def test_stale_authoring_and_absent_scene_contract_are_rejected(self):
        inv=copy.deepcopy(self.inventory)
        inv["manual_authority"]={"identity":authoring_identity(self.root),"feature_links":{"MAN-001":["a"]}}
        verify_authority(self.root,inv,self.book)
        inv["manual_authority"]["identity"]["sha256"]="stale"
        with self.assertRaisesRegex(ValueError,"authoring changed"):
            verify_authority(self.root,inv,self.book)
        inv["manual_authority"]["identity"]=authoring_identity(self.root)
        book=copy.deepcopy(self.book);book["scenes"]={}
        with self.assertRaisesRegex(ValueError,"Missing scene contract"):
            verify_authority(self.root,inv,book)
    def test_compiled_manual_must_be_bound_to_current_authoring(self):
        inv=copy.deepcopy(self.inventory)
        inv["manual_authority"]={"identity":authoring_identity(self.root),"feature_links":{"MAN-001":["a"]}}
        self.book.pop("authoring_identity")
        with self.assertRaisesRegex(ValueError,"Compiled manual authoring changed"):
            verify_authority(self.root,inv,self.book)
    def test_unlisted_yaml_cannot_escape_authority_identity(self):
        (self.root/"manual/features/forgotten.yaml").write_text("features: []")
        with self.assertRaisesRegex(ValueError,"Unlisted authoring"):
            authoring_identity(self.root)
    def test_scene_pixels_alone_cannot_replace_semantic_acceptance(self):
        inv=copy.deepcopy(self.inventory)
        inv["manual_authority"]={"identity":authoring_identity(self.root),"feature_links":{"MAN-001":["a"]}}
        self.book["scenes"]["scene-a"]["steps"][0]["output"]={"grid":[0]*128}
        with self.assertRaisesRegex(ValueError,"Missing semantic scene binding"):
            verify_authority(self.root,inv,self.book)
    def test_scene_audio_and_schema_sources_participate_in_identity(self):
        config=self.root/"manual/book.yaml"
        config.write_text(config.read_text()+"scene_sources: [scene-plans.yaml]\naudio_sources: [audio-scenes.yaml]\nschema_sources: [schema.json]\n")
        for name in ["scene-plans.yaml","audio-scenes.yaml","schema.json"]:
            (self.root/"manual"/name).write_text("{}")
        identity=authoring_identity(self.root)
        for name in ["scene-plans.yaml","audio-scenes.yaml","schema.json"]:
            self.assertIn("manual/"+name,identity["files"])
    def test_runtime_gate_rejects_stale_compiled_catalogue(self):
        (self.root/"tools").mkdir()
        (self.root/"tools/manual_book.py").write_text("def load(): return {'current': True}")
        inv=copy.deepcopy(self.inventory)
        inv["manual_authority"]={"identity":authoring_identity(self.root),"feature_links":{"MAN-001":["a"]}}
        self.book["source_sha256"]="stale"
        (self.root/"manual/generated/book.json").write_text(json.dumps(self.book))
        with self.assertRaisesRegex(ValueError,"Compiled manual source changed"):
            verify_authority(self.root,inv)
    def test_archived_readme_mappings_keep_original_paths_and_line_hashes(self):
        (self.root/"manual/legacy").mkdir()
        line="A documented behaviour."
        (self.root/"manual/legacy/README-1.4.0.md").write_text("Header\n"+line+"\n")
        (self.root/"README.md").write_text("New overview without that historical statement.")
        mapping={"id":"statement","source":{"path":"README.md","line":2,"text":line,
            "sha256":hashlib.sha256(line.encode()).hexdigest()},"requirements":["REQ"]}
        with mock.patch.object(reconcile_manual,"REPO",self.root):
            result=reconcile_manual.relocate_statements([mapping],{"path":"manual/legacy/README-1.4.0.md"})
        self.assertEqual(result,[mapping])
    def test_compiled_feature_tamper_cannot_keep_a_valid_source_hash(self):
        (self.root/"tools").mkdir()
        authored={"features":[],"aliases":{}}
        (self.root/"tools/manual_book.py").write_text("def load(): return "+repr(authored))
        inv=copy.deepcopy(self.inventory)
        inv["manual_authority"]={"identity":authoring_identity(self.root),"feature_links":{"MAN-001":["a"]}}
        self.book["source_sha256"]=hashlib.sha256(json.dumps(authored,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        (self.root/"manual/generated/book.json").write_text(json.dumps(self.book))
        with self.assertRaisesRegex(ValueError,"Compiled manual contents changed"):
            verify_authority(self.root,inv)
    def test_course_source_is_pinned_and_edit_invalidates_identity(self):
        config=self.root/"manual/book.yaml"
        config.write_text(config.read_text()+"course_source: course.yaml\n")
        course=self.root/"manual/course.yaml";course.write_text("learning_path: []\n")
        before=authoring_identity(self.root)
        self.assertIn("manual/course.yaml",before["files"])
        course.write_text("learning_path: [{id: a}]\n")
        self.assertNotEqual(before,authoring_identity(self.root))
    def test_course_source_escape_is_rejected(self):
        config=self.root/"manual/book.yaml"
        config.write_text(config.read_text()+"course_source: ../../outside.yaml\n")
        with self.assertRaisesRegex(ValueError,"Unsafe authoring"):
            authoring_identity(self.root)
    def test_feature_links_preserve_historical_requirements_and_sources(self):
        baseline=copy.deepcopy(self.inventory)
        features=[{"id":"a","sources":{"readme":"manual/legacy/README-1.4.0.md#a"}}]
        links=feature_links(self.inventory,features,{"MAN-001":"a"})
        self.assertEqual(links,{"MAN-001":["a"]})
        self.assertEqual(self.inventory,baseline)
class ControlledAuthorityTests(unittest.TestCase):
    setUp=ManualAuthorityTests.setUp
    def active(self,status='controlled-verified',scope=True):
        self.book['complete_manual']=True
        self.book['features'][0]['review']={'status':status}
        self.inventory['manual_authority']={'status':'active','identity':authoring_identity(self.root),'feature_links':{'MAN-001':['a']}}
        if scope:
            for target in (self.book,self.inventory['manual_authority']):
                target.update(validation_scope='controlled-manual-generation',realtime_qualification='pending-ci')
    def verify_active(self):
        compiler=mock.Mock();compiler.compile_book.return_value=copy.deepcopy(self.book)
        with mock.patch('manual_authority.compiler_module',return_value=compiler):
            return verify_authority(self.root,self.inventory,self.book)
    def test_explicit_controlled_complete_authority_accepts_without_real_claim(self):
        self.active();self.assertEqual(self.verify_active(),authoring_identity(self.root))
    def test_default_authority_does_not_admit_controlled_status(self):
        self.active(scope=False)
        with self.assertRaisesRegex(ValueError,'incomplete'):self.verify_active()
    def test_full_default_verified_still_accepts(self):
        self.active(status='verified',scope=False);self.assertEqual(self.verify_active(),authoring_identity(self.root))
    def test_controlled_authority_requires_pending_ci_on_both_sources(self):
        for target in ('book','authority'):
            self.active();(self.book if target=='book' else self.inventory['manual_authority'])['realtime_qualification']='passed'
            with self.assertRaisesRegex(ValueError,'qualification'):self.verify_active()
    def test_controlled_authority_still_rejects_incomplete_content(self):
        self.active();self.book['complete_manual']=False
        with self.assertRaisesRegex(ValueError,'incomplete'):self.verify_active()
    def test_controlled_authority_requires_compiled_scope(self):
        self.active();self.book.pop('validation_scope')
        with self.assertRaisesRegex(ValueError,'scope'):self.verify_active()

if __name__=="__main__":unittest.main()

"""Characterisation: generated quick reference matches the validated public book."""
import copy, importlib.util, unittest, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("manual_quick_reference",ROOT/"tools/manual_quick_reference.py")
quick=importlib.util.module_from_spec(spec);spec.loader.exec_module(quick)

def generated_book():
    """Use the checked-in generated book, avoiding the slow authoring compiler."""
    return json.loads((ROOT/"manual/generated/book.json").read_text())

class QuickReferenceTests(unittest.TestCase):
    def setUp(self):
        self.data={"title":"Mosaic","edition":"1.4.0","features":[
            {"id":"test-feature","title":"Test","summary":"A short reference.",
             "controls":[{"gesture":"Hold K1 & press <step>","result":"Write \"note\""}],
             "scene_refs":[]}],"aliases":{}}
    def test_text_and_attributes_are_escaped(self):
        self.data["features"][0]["title"]="<script>alert(1)</script>"
        text=quick.render(self.data)
        self.assertNotIn("<script>alert(1)</script>",text)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;",text)
        self.assertIn("Hold K1 &amp; press &lt;step&gt;",text)
    def test_every_public_feature_and_control_is_present(self):
        data=generated_book()
        public=quick.public_features(data)
        self.assertGreaterEqual(len(public), 130)
        text=quick.render(data)
        self.assertEqual(text.count('<article id='),len(public))
        for feature in public:
            fid=feature["id"]
            self.assertIn('id="'+fid+'"',text)
            self.assertIn('href="manual/#'+fid+'"',text)
            self.assertIn(quick.escape(feature["title"]),text)
            self.assertIn(quick.escape(feature.get("summary","")),text)
            for control in feature.get("controls",[]):
                self.assertIn(quick.escape(control["gesture"]),text,(fid,control))
                self.assertIn(quick.escape(control.get("result","")),text,(fid,control))
    def test_public_filter_excludes_only_developer_records(self):
        data=copy.deepcopy(self.data)
        data["features"].extend([
            {"id":"development","title":"Development","audience":"developer","category":"developer","controls":[]},
            {"id":"interesting-components-for-norns-script-developers","title":"Developer components","audience":"developer","category":"developer","controls":[]},
            {"id":"roadmap","title":"Roadmap","audience":"developer","category":"developer","controls":[]},
            {"id":"public-feature","title":"Player feature","audience":"all","category":"workflow","controls":[{"gesture":"Press K3","result":"Open the page"}]},
        ])
        text=quick.render(data)
        self.assertIn('id="test-feature"',text)
        self.assertIn('id="public-feature"',text)
        for feature_id in ("development","interesting-components-for-norns-script-developers","roadmap"):
            self.assertNotIn('id="'+feature_id+'"',text)
    def test_changed_gesture_regenerates_without_editing_renderer(self):
        before=quick.render(self.data)
        self.data["features"][0]["controls"][0]["gesture"]="Turn E3 while holding step 2"
        after=quick.render(self.data)
        self.assertNotEqual(before,after)
        self.assertIn("Turn E3 while holding step 2",after)
    def test_scene_names_do_not_invent_visual_verification(self):
        self.data["features"][0]["scene_refs"]=["not-a-real-scene"]
        text=quick.render(self.data)
        self.assertNotIn("not-a-real-scene",text)
        self.assertNotIn("verified",text.lower())
    def test_keyboard_navigation_and_legacy_reference_remain_accessible(self):
        text=quick.render(self.data)
        self.assertIn('href="#reference"',text)
        self.assertIn('<label for="find">',text)
        self.assertIn("prefers-color-scheme",text)
        self.assertIn("Interactive manual",text)
        self.assertIn("1.4.0 / quick reference",text)
        self.assertLess(text.index("Interactive manual"),text.index("Switch light / dark"))
        self.assertNotIn("Original quick reference",text)
        self.assertNotIn("historical wording",text)
        self.assertNotIn("same authoring",text)
    def test_legacy_coverage_review_accounts_for_every_gesture_and_result(self):
        report=json.loads((ROOT/"manual/evidence/quick-reference-coverage.json").read_text())
        original=quick.legacy_rows(ROOT/report["legacy_path"])
        self.assertEqual(len(original),77)
        self.assertEqual([(r["legacy_line"],r["legacy_statement"]) for r in report["rows"]],
                         [(r["line"],r["text"]) for r in original])
        features={f["id"]:f for f in quick.book.load()["features"]}
        self.assertFalse(report["complete_regression_run"])
        for row in report["rows"]:
            self.assertIn(row["status"],("preserved","clarified"))
            feature=features[row["feature_id"]]
            excerpts=[feature.get("prose","")]
            excerpts += [c["gesture"]+" → "+c.get("result","") for c in feature.get("controls",[])]
            excerpts += [d.get("title","")+" "+d.get("text",d.get("body","")) for d in feature.get("details",[]) if isinstance(d,dict)]
            self.assertTrue(row["authored_evidence"],row["legacy_line"])
            for evidence in row["authored_evidence"]:
                self.assertTrue(any(evidence["excerpt"] in text for text in excerpts),row["legacy_line"])
    def test_logo_path_is_relative_to_both_public_outputs(self):
        self.assertEqual(quick.relative_logo_src(ROOT/"cheat_sheet.html"),"images/logo.svg")
        self.assertEqual(quick.relative_logo_src(ROOT/"manual/generated/quick-reference.html"),"../../images/logo.svg")
        self.assertIn('src="images/logo.svg"',quick.render(self.data,logo_src="images/logo.svg"))
    def test_invalid_destination_is_rejected(self):
        self.data["features"][0]["id"]='bad" onclick="run'
        with self.assertRaisesRegex(ValueError,"feature ID"):quick.render(self.data)
if __name__=="__main__":unittest.main()

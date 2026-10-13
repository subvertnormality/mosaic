"""Regression for metadata-based selectors over the pinned v2 mini-header poses."""
import copy
import glob
import hashlib
import json
import pathlib
import sys
import unittest

import yaml

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tools"))
sys.path.insert(0,str(ROOT/"tests/behaviour"))
from manual_case_capture import Selector
from contract.harmony_merge_visual import _MINI_DOCUMENTATION_FRAMES

ATLAS_SHA256="4b1623dd87cabd4a98b3ed5d2e47b32455221c360054f1eb5dd8783eb5278c46"
CAPTURED_RESULTS_SHA256="82f17bee8aa2c98d86388b2ed727d22e3997d592d133cfd05e01a4ed1b15abbc"
CAPTURED_NATIVE_IDENTITY_SHA256="4b220eb6d1ddee37189c8b1f8315ca26c159f0d1674e6ed99e0fa92816fe6c0e"
CAPTURED_CASE_SOURCE_SHA256="1fe0b023d69fca4d9cac99129ac3bdcfd7aeac044bfede13fe1c149dcaadc138"
CAPTURED_HELPER_SOURCE_SHA256="600a95ff080d8e3b03cdacbabb13b635e18c6861336c131e3d1b656663999296"
CAPTURED_PLAN_SOURCE_SHA256="779d537e108bc21180542e94aa2b476f4c5d523dcb212c2bd57ae04167d02df0"
CAPTURED_ROW_SHA256="a158f7071130a906402dd0191836ae446d17d163c533f4c97010d5305ee0003d"
CAPTURED_PROVENANCE={
 "run":"630f2a5078824322998691fce24e4a37",
 "case":"M-MERGE-FOUNDATION-001-base-midi",
 "results_path":"/home/andy/mosaic-manual-runs/630f2a5078824322998691fce24e4a37/M-MERGE-FOUNDATION-001-base-midi/results.json",
 "results_sha256":CAPTURED_RESULTS_SHA256,
 "native_identity_sha256":CAPTURED_NATIVE_IDENTITY_SHA256,
 "cleanup_sha256":"0171a6db90105679e06945831735ca66bf49d0e4e8e7a2ff3452ffed368b519b",
 "foundation_case_source_sha256":CAPTURED_CASE_SOURCE_SHA256,
 "helper_source_sha256":CAPTURED_HELPER_SOURCE_SHA256,
 "scene_plan_sha256":CAPTURED_PLAN_SOURCE_SHA256,
 "actual_result_sha256":CAPTURED_ROW_SHA256,
}
CAPTURED_PROVENANCE_SHA256="7f619ee1a2d32a7b8b2aab62d391ea1cd1bb1bd23befa653dc46305bf1f738fc"

# This exact result row was emitted by the preserved controlled Foundation case
# in run 630f2a5078824322998691fce24e4a37. The complete results.json and native
# identity are archived externally with the source plan and case-source snapshots.
CAPTURED_FOUNDATION_RESULT={
 "kind":"documentation-frame",
 "name":"images/merge-shape-foundation.png",
 "sha256":"bfef1e487a4d957d65587e682bdeeaf60f793603c5d7f56cbf2edb472e6baca4",
 "passed":True,
 "validation":"pinned-v2-mini-pose",
 "page":"M03",
 "baseline_sha256":"49ddaad6ba1a77775be8ce7e8d32ff61670f25bacd664560166d019787970463",
 "atlas_sha256":ATLAS_SHA256,
 "matching_poses":[0],
}

LEGACY={
 ("foundation-protected-and-added","accent-setting"):dict(
  kind="documentation-frame",name="images/merge-shape-foundation.png",
  sha256="49ddaad6ba1a77775be8ce7e8d32ff61670f25bacd664560166d019787970463",passed=True),
 ("fragments-seed-source-choice","seed-one-editor"):dict(
  kind="documentation-frame",name="images/merge-shape-fragments.png",
  sha256="760b9f276791a959a98a73441d88f534d9f77730fad051d93dd890841581689b",passed=True),
}
EXPECTED_SCOPE={
 ("foundation-protected-and-added","accent-setting"):dict(
  kind="documentation-frame",name="images/merge-shape-foundation.png",
  baseline_sha256="49ddaad6ba1a77775be8ce7e8d32ff61670f25bacd664560166d019787970463",
  validation="pinned-v2-mini-pose",page="M03",atlas_sha256=ATLAS_SHA256,passed=True),
 ("fragments-seed-source-choice","seed-one-editor"):dict(
  kind="documentation-frame",name="images/merge-shape-fragments.png",
  baseline_sha256="760b9f276791a959a98a73441d88f534d9f77730fad051d93dd890841581689b",
  validation="pinned-v2-mini-pose",page="M15",atlas_sha256=ATLAS_SHA256,passed=True),
}
EXPECTED_IMAGES={
 "images/harmony-tone-map.png":("9ada7d5dfae6b9d849e19f4228b1475459595d3f9eefe57af08ef87904e6f823","c6d2c5bba8503166a2abeb5f728091e01227f397e6656cee555625433824227b","H11"),
 "images/harmony-no-voicing.png":("f55f4b3fb68a92d1721a928b3e587ba0716dc174ab05a9cf1e4bb6d094eac7ea","52c9016ad80d1d7c92a9e6d8b97109f21b5450f6453cff5758774e552b5eeef2","H05"),
 "images/merge-shape-foundation.png":("1dac205f0379af973f62703cc49507cddacea68d019fcac9a172d46ec7ea9850","49ddaad6ba1a77775be8ce7e8d32ff61670f25bacd664560166d019787970463","M03"),
 "images/merge-shape-fragments.png":("7984c43100cc0c290f1f9639d32ed0aae7102f10c0d7efa03e8c3f3afa6f014a","760b9f276791a959a98a73441d88f534d9f77730fad051d93dd890841581689b","M15"),
 "images/merge-shape-interlock.png":("533d8bbbb5553040db390a0dd79c89873fd58a37b1f8d8a1a218c62bbbb5f4e2","de6e77eb93ebd84d696def4c0862dd49140f3447b745fd92d445ab3c014615a7","M16"),
 "images/merge-shape-structure.png":("4fbf43e3e5a53b6ba8a92116f3e006432b7a1329e2f2437565b649ffce7bb223","f2250df79def76419e0054c5295e2183b3f889513bc2bce77bed46af702f8095","M18"),
}

def canonical_sha(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def plan_selectors():
 rows={}
 for path in sorted(glob.glob(str(ROOT/"manual"/"scene-plans*.yaml"))):
  document=yaml.safe_load(pathlib.Path(path).read_text())
  for scene in document.get("scenes",[]):
   for step in scene.get("steps",[]):
    assertion=step.get("assertion",{})
    if assertion.get("kind")=="documentation-frame":
     rows[(scene["id"],step["id"])]=assertion
 return rows

class DocumentationFrameSelectorTests(unittest.TestCase):
 def test_captured_foundation_result_matches_scoped_selector_not_legacy_sha(self):
  self.assertEqual(canonical_sha(CAPTURED_PROVENANCE),CAPTURED_PROVENANCE_SHA256)
  self.assertEqual(canonical_sha(CAPTURED_FOUNDATION_RESULT),CAPTURED_ROW_SHA256)
  plan=plan_selectors()
  legacy=LEGACY[("foundation-protected-and-added","accent-setting")]
  current=plan[("foundation-protected-and-added","accent-setting")]
  self.assertFalse(Selector(legacy).accept(CAPTURED_FOUNDATION_RESULT))
  adapter=Selector(current)
  self.assertTrue(adapter.accept(CAPTURED_FOUNDATION_RESULT))
  self.assertEqual(adapter.matched,current)

 def test_wrong_baseline_page_or_atlas_is_rejected_by_actual_adapter(self):
  actual=CAPTURED_FOUNDATION_RESULT
  expected=EXPECTED_SCOPE[("foundation-protected-and-added","accent-setting")]
  for key,value in (("baseline_sha256","wrong"),("page","M15"),("atlas_sha256","wrong")):
   candidate=dict(expected);candidate[key]=value
   with self.subTest(key=key):self.assertFalse(Selector(candidate).accept(actual))

 def test_all_scene_plan_selectors_use_the_exact_six_image_scope_contract(self):
  self.assertEqual(_MINI_DOCUMENTATION_FRAMES,EXPECTED_IMAGES)
  plan=plan_selectors()
  self.assertEqual(set(plan),set(EXPECTED_SCOPE))
  self.assertEqual(plan,EXPECTED_SCOPE)
  self.assertTrue(all("sha256" not in row for row in plan.values()))

 def test_musical_plan_matches_reviewed_teaching_and_selector_scope(self):
  path=ROOT/"manual/scene-plans-musical.yaml"
  document=yaml.safe_load(path.read_text())
  for scene in document["scenes"]:
   for step in scene.get("steps",[]):
    key=(scene["id"],step["id"])
    if key in LEGACY:step["assertion"]=copy.deepcopy(LEGACY[key])
  # Reviewed round-3 teaching/checkpoint additions; full-document guard remains strict.
  original_semantic_sha="ebe76e6880a537aba2504cb710f127b68daf5b5e6e93927c59741e682745c8d4"
  self.assertEqual(canonical_sha(document),original_semantic_sha)

if __name__=="__main__":unittest.main()

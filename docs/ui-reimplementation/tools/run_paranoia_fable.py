"""Run the requested Paranoia Fable plan review and proposal, when Fable CLI is available."""
from pathlib import Path
import json,sys
from paranoia_local.server import dispatch
ROOT=Path(__file__).resolve().parents[3]
PACKAGE=ROOT/'docs/ui-reimplementation'
OUT=PACKAGE/'reviews'
OUT.mkdir(exist_ok=True)
args={
 'repo_path':str(ROOT),
 'plan_path':str(PACKAGE/'IMPLEMENTATION.md'),
 'context':('Review the complete Mosaic UI migration contract, not an implementation. '
  'Read docs/ui-reimplementation/README.md and spec.json, including source_route_map, '
  'feature_action_edges, input_algebra, grid ownership, view_model, acceptance_matrix '
  'and source-inventory.json. Inspect actual README.md and current Lua owners. '
  'Assume docs/testing/ui-abstraction-plan.md has already been completed, as the user directed. '
  'Focus on functions silently lost, wrong source route translations, invalid input priority, '
  'grid-first fidelity, native ownership, dynamic fields, scope/return behavior, overlap '
  'and the feasibility of implementing screens from proto-code. Every material finding '
  'should have a minimal suggested patch to the plan/spec, with source evidence. '
  'Do not modify files.'),
 'stakes':'Grid-first norns sequencer. This is a planning review. A lower-power executor should be able to implement without musical regressions or missing UI functions. No production UI changes are authorized in this review.',
 'engine':'claude',
 'model':'claude-fable-5-1',
 'effort':'high',
 'lineage':'mosaic-ui-reimplementation-20260924',
 'round':1,
 'class_closure':True,
 'propose_patch':True,
}
(OUT/'request.json').write_text(json.dumps(args,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def progress(message):print(message,flush=True)
try:
 result=dispatch('critique_plan',args,default_engine_name='claude',log_dir=OUT/'logs',on_progress=progress)
except Exception as exc:
 print(f'PARANOIA DID NOT RUN: {type(exc).__name__}: {exc}',file=sys.stderr,flush=True)
 raise SystemExit(2)
if result.lstrip().startswith('[paranoia-local error]'):
 print('PARANOIA DID NOT RUN: '+result.strip(),file=sys.stderr,flush=True)
 raise SystemExit(2)
(OUT/'fable-plan-round1.md').write_text(result,encoding='utf8')
print('Saved '+str(OUT/'fable-plan-round1.md'),flush=True)

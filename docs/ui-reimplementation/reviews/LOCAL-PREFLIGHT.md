# Local preflight findings; this is not a Paranoia or Fable result.

The requested Paranoia `critique_plan` call was prepared with
`engine=claude`, `model=claude-fable-5-1`, `class_closure=true`,
`round=1` and `propose_patch=true`. Its Windows attempt returned
`[paranoia-local error] FileNotFoundError: [WinError 2]`; the Claude
CLI is absent from Windows. WSL failed to enumerate/start before the
Linux reviewer could run. No Fable review or patch proposal exists.
`request.json` and `../tools/run_paranoia_fable.py` preserve the exact call.

These are independently reproduced local findings, for triage and later
Fable review. They are not a substitute for it.

1. **MAJOR: grid page outcomes leave the router in the prior context.**
   `tools/model.py:52-63` changes `screen` in `outcome.follow` but not `context`.
   Reproduction: from `P01`/Trig, `G03` with `page=Note` returns
   `screen=P03, context=Trig`; `screens.P03.context` is `Note`. The actual
   `lib/m_grid.lua` menu callback cycles Trig → Note → Velocity. The next
   context task or grid geometry can therefore use the wrong owner.
   Suggested patch: make one resolved grid outcome atomically set its page
   context, screen and captured target; invalidate returns once. Specify
   whether `grid.context` is a separate event or merely the page-change
   form of that outcome, and add tests for G01–G04 and both G03 cycle edges.

2. **MAJOR: numeric values can be abbreviated in the coded live layouts.**
   `code/screen.lua:37` applies `fit` to every overview compact value;
   line 54 applies it to every detail value. `fit` appends `~` after dropping
   characters. Only the focused path at lines 61–64 asserts that a full
   numeric value fits. The stated overflow contract says numeric data must
   not silently truncate. A five-digit parameter value may exceed the
   20-pixel overview cell and no guaranteed full-value route is encoded.
   Suggested patch: require a full-width selected-value line or focused
   fallback in overview/detail when the native font reports overflow.
   Test maximum numeric domains with native `screen.text_extents`, including
   assigned device parameters, and assert the complete value is visible.

3. **MAJOR: registration retention is weaker than branch migration proof.**
   `tools/validate.py:40-44,59` checks that each of 63 registrations has at
   least one valid flow and that source registration positions match. It
   does not establish that each conditional branch, modifier and release
   edge emits a declared outcome. The plan asks the executor to exercise
   these branches later, but it does not give a machine-readable branch
   list or a case-to-outcome matrix. A lower-power executor could satisfy
   the validator while leaving a rare grid gesture without a new UI flow.
   Suggested patch: enumerate branch-level outcome IDs under each callback,
   including guard, edge and source line; require a behavior case for each
   reachable branch and an explicit retain-without-navigation disposition.
   Have validation reject unmapped branches, not merely unmapped callback
   registrations.

No production files or canonical contract fields were changed in this
preflight; suggested patches remain reviewable.

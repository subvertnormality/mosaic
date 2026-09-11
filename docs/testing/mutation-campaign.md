# Lua mutation campaign

Tool: `tests/lua_mutation.py`. Single-token mutants of `lib/**/*.lua` (relational
`== ~= < <= > >=`, arithmetic `+ - * / //`, logical `and or`, `true`/`false`, integer literal
`n -> n+1`; strings and comments untouched), restricted to lines the Lua unit suite executes
(line-hook coverage file). Each mutant runs the whole unit suite (`run_tests.lua -f`) in its own
hard-linked copy; a failing or erroring suite kills it. Two units with wall-clock limits
(`test_live_slide_admission_all_channel_parameter_slots`,
`test_massive_concurrent_automation_with_param_slides`, 1-2 ms per pulse via `os.clock`) are
excluded because host load would fake kills; timing is covered by the emulator lanes. It
measures the **unit suite only**: mutants the emulator behaviour cases would catch still
count as survivors here.

## Baseline campaign at bc0570c (2026-09-11)

1218 units; 7,122 mutants on executed lines (of 9,488 in all of lib, excluding lib/tests and
lib/nb); 20 workers; about 2.5 h. Results in
`mosaic-behaviour-runs/mutation-bc0570c/` (`mutants.jsonl`, `summary.json`, per-file
`survivors/`).

| | Killed (incl. 21 timeouts) | Survived | Kill rate |
|---|---|---|---|
| All mutants | 4,904 | 2,218 | 68.9% |
| Logic mutants | 4,775 | 1,326 | 78.3% |
| Data-table element mutants | 129 | 892 | 12.6% |

"Data-table element" mutants change one number inside a literal table of six or more numbers
(the 64-entry pattern defaults in `pattern.lua:25-28`, the shuffle feel tables in
`m_lattice.lua`, division tables). Many cannot change behaviour (a default overwritten
before use); the rest need a golden table to kill.

Weakest logic kill rates (the refactor and performance-sweep hot path):

| File | Logic killed / total | Kill rate |
|---|---|---|
| `pages/channel_edit_page/channel_edit_page_ui.lua` | 282 / 678 | 41.6% |
| `clock/midi_output_transport.lua` | 12 / 25 | 48% |
| `clock/m_clock.lua` | 195 / 390 | 50.0% |
| `clock/m_lattice.lua` | 207 / 350 | 59.1% |
| `memory.lua` | 120 / 194 | 61.9% |
| `quantiser.lua` | 186 / 291 | 63.9% |
| `step.lua` | 322 / 468 | 68.8% |
| `scheduler.lua` | 23 / 33 | 69.7% |
| `pattern.lua` | 88 / 118 | 74.6% |

Files at 90% or more logic kill: `m_midi`, `divisions`, `program`, `param_manager`,
`device_map`, `json`, `m_grid`, `functions`, the NRPN codec, value domain, patch recall,
recorder, press, controls and UI components.

Follow-up: survivors are being triaged per module (equivalent / unreachable / real gap) and
real gaps killed with new units; results are appended below.

## Survivor triage and final campaign at 18a317f + delta units (2026-09-11)

**Wave 3.** The baseline survivors were grouped by module and triaged as GAP (a realistic input
tells the mutant apart), EQUIVALENT (no input can) or UNREACHABLE (only inputs production never
produces). Every GAP got a killer unit in `lib/tests/lib/*_mutation_killers_tests.lua`
(12 files, commit 9f7bebb). The largest single gap was in `m_lattice`. The existing
`create_sprocket` helper never passed `shuffle_amount`, so every shuffle test ran straight and all
528 shuffle-table mutants survived. They are now killed by a characterisation golden table
plus derived properties (an 8-step cycle spans exactly 768 pulses, amount 0 is straight, amount 50
is halfway).

**Wave 4 (delta).** Coverage was regenerated after wave 3. The 563 lines only the new units
executed produced 342 new mutants (223 killed, 119 survived). Those survivors were triaged the
same way and killed with `*_delta_killers_tests.lua` (commits 18a317f, 383d473). Differential
fuzzing backs the equivalence calls on the clock and lattice retime paths: 3,000 seeds for
`m_clock` and 1,000 for `m_lattice`.

**Final campaign.** Coverage was regenerated again (1464 units; 9,903 executed production
lines), giving 7,518 mutants. 4,733 earlier kills on unchanged source were reused, because an
added test cannot revive a killed mutant. `channel_edit_page_ui.lua` changed in 18a317f, so all
of its mutants were re-run. Results are in
`mosaic-behaviour-runs/mutation-final-383d473/` (`mutants.jsonl`, `summary.json`,
`survivors.json`).

| | Baseline (bc0570c) | Final |
|---|---|---|
| Mutants | 7,122 | 7,518 |
| Killed (incl. 21 timeouts) | 4,904 | 6,655 |
| Survived | 2,218 | 863 |
| Kill rate | 68.9% | 88.5% |
| Kill rate excluding the 256 `pattern.lua:25-28` default-table survivors | 71.4% | 91.6% |

The 863 survivors are each classified EQUIVALENT or UNREACHABLE by the per-module triage. The
exception is six survivors on lines first executed by the delta units; they were classified
while this report was written. Two were real gaps (`dirty_screen(true)` after an E1 page change)
and were killed by `test_w4c_encoder_one_page_changes_leave_a_redraw_requested`; the other four
are equivalent or unreachable. The `pattern.lua` default tables are overwritten by every merge
mode before any read, so no single-element change is observable.

Weakest files after triage (kill rate, killed / total):

| File | Baseline | Final |
|---|---|---|
| `pattern.lua` (default tables, see above) | 34.7% (152 / 438) | 38.8% (170 / 438) |
| `scheduler.lua` | 69.7% | 72.7% (24 / 33) |
| `clock/m_clock.lua` | 50.0% | 77.0% (339 / 440) |
| `pages/channel_edit_page/channel_edit_page_ui.lua` | 41.2% | 81.4% (732 / 899) |
| `step.lua` | 64.4% | 83.1% (424 / 510) |
| `clock/midi_output_transport.lua` | 48.0% | 84.8% (28 / 33) |
| `quantiser.lua` | 51.5% | 87.5% (321 / 367) |
| `memory.lua` | 61.9% | 87.7% (171 / 195) |
| `clock/m_lattice.lua` | 27.5% | 94.9% (968 / 1,020) |

These baseline rates count all mutants, so they differ from the logic-only table above. The
remaining survivors in these files are dominated by dead stores, double clamps, fields
nothing reads, and fallbacks production never takes. They are refactor candidates, not test
gaps.

**Limits.** The operators do not delete statements, remove call arguments or change string
literals, and lines the units never execute are not mutated. The kill rate is therefore an
upper bound on the units' sensitivity, and the emulator behaviour cases remain the net for
cross-module and timing behaviour.

**Defects found.** Writing the killers pinned 17 suspected defects (S38-S54 in
`suspected-defects.md`). One was reproduced in the emulator and fixed (S50, Note Dashboard
showed Vel -1 / Len -1.0; bugs.json `dashboard-absent-velocity-length`). One was ruled out by
code reading (S49). The rest went to human review on 2026-09-11.

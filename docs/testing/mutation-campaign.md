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

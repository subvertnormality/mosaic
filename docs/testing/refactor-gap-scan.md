# Refactor and performance-sweep regression gap scan — 2026-09-10

User direction (2026-09-10): finish the behaviour and unit/integration suites, then
find and fill tests whose absence would let a broad refactor or performance sweep
regress Mosaic. Gap tests use Lua units for pure logic and emulator behaviour
cases for user-visible contracts. Oracles cite README lines; anything else is
labelled characterisation. Isolated defect fixes follow the defect rule (minimal
real-input regression, baseline evidence, bug-ledger entry).

Scan method: every production module's public functions against direct Lua unit
calls, behaviour-case coverage and README statements; hot spots for persistence,
caches, capacity limits, boundary arithmetic, event order and nil handling. Each
item below was checked against the code before being accepted.

Status: `open`, `done` (test landed), `defect` (test found a defect), `decision`.

| # | Gap | Layer | Status |
|---|---|---|---|
| U1 | Seven Lua unit tests shadowed by repeated global names (merge_mode x2, param_tests x2, pattern_and_song, scale_and_quantiser, memory) | unit + guard | done: renamed; one stale expectation corrected to README 785 (ties choose the lower pitch); `test_lua_test_names` guards |
| D1 | Memory ring buffer: after wrapping, truncate then push writes an absolute slot (`memory.lua` `push`), so history after undo+edit is wrong | unit + behaviour | open (verified in code) |
| D2 | Quantiser scale cache: entries get a timestamp only on a hit; the 101st distinct key sorts nil timestamps and raises (`quantiser.lua` `cleanup_old_cache_entries`) | unit + behaviour | open (verified in code) |
| D3 | `step.process_params` norns/nb parameter step locks index an undefined global `c`; `get_original_param_state(nil,i).value` raises | unit + behaviour (nb-audio) | open (verified in code) |
| D4 | `step.sinfonian_sync(s)` reads the `step` module table instead of `s` as the step number | unit | open (verified in code) |
| G1 | No frozen project saved by an earlier release is loaded; all persistence cases write with current code | behaviour fixture | open |
| G2 | No Lua round trip of real `program.prepare_for_save` -> serialise -> load | unit | open |
| G3 | New/load does not reset memory history (`memory.lua` keeps the module-load table) | behaviour | open (to verify) |
| G4 | Slide ring (1024) saturation: a full ring drops a new slide after cancelling the old one | unit | open |
| G5 | Division table consistency (`divisions.lua` parallel arrays, float index keys) | unit | open |
| G6 | CC-before-note order not observable in unit mocks (separate note/CC logs) | unit mock | open |
| G7 | Picker-loaded project referencing a missing device config (nil device) | behaviour | open (to verify) |
| G8 | 14-bit CC MSB/LSB split in real `m_midi.cc` | unit | open |
| G9 | `device_map.get_params` cached table shared with callers | unit | open |
| G10 | Elektron program changes with two devices on different ports | behaviour | open |
| G11 | Global scale channel 17 versus channel scale lock on a coincident step; processing order | unit + behaviour | open |
| G12 | Autosave with unwritable storage then recovery | behaviour | open |
| G13 | Song slot bound 90 (README) versus validation accepting 96 | decision | open |
| G14 | `mosaic.lua` load tests reach locals through `debug.getupvalue` | unit seam | open (refactor-fragile; note only unless a seam exists) |
| G15 | PERF-003..008 canonical constrained runs | performance | open (measurement only; no fixes) |

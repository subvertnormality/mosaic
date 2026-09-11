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
| U1 | Seven Lua unit tests shadowed by repeated global names | unit + guard | done: renamed; one stale expectation corrected to README 785; `test_lua_test_names` guards |
| U2 | Page modules are never loaded by the Lua units, so a syntax error there surfaces only at boot | guard | done: `test_lua_syntax` compiles all 65 production Lua files |
| D1 | Memory history after wrapping: undo then a new action writes an absolute slot | unit + M-MEMORY-004 | defect fixed (`memory-wrap-logical-slot`) |
| D2 | Quantiser cache: the 101st distinct key sorts nil timestamps and raises at Play | unit + M-SCALE-CACHE-001 | defect fixed (`quantiser-cache-timestamp`) |
| D3 | norns/nb parameter step locks index an undefined global `c` and raise at Play | unit + M-XA-005-NB-LOCK (nb-audio) | defect fixed (`norns-param-lock-channel`) |
| D4 | `step.sinfonian_sync(s)` passes the `step` module as the step number | unit | latent: masked by the persistent global scale set just before; observable path pinned by `sinfonion_sync_tests.lua`; not changed |
| D5 | Fractional length masks (1/24, 1/12, 1/6, 1/3, 2/3, 5/6) reload as 14-digit floats; the length selector shows X | unit + M-SAVE-LENGTH-001 | defect fixed (`length-index-after-reload`) |
| D6 | Slide ring: replaced slides behind one long slide exhaust the 1024 slots and new slides are dropped | unit + M-SLIDE-CAPACITY-001 | defect fixed (`slide-ring-compaction`) |
| D7 | `+ New` keeps the previous project's memory history (E3 replays it) | unit + M-MEMORY-005 | defect fixed (`new-project-memory`) |
| G1 | No project saved by an earlier version is loaded | fixtures + M-PERSIST-FIXTURE-CURRENT/1.2.12 | done: frozen current and 1.2.12 autosaves; 1.2.12 plays exactly as the current version's own save |
| G2 | No Lua round trip of real `program.prepare_for_save` -> tabutil -> load | unit | done: `persistence_round_trip_tests.lua` (memory binding caveat: the memory module keeps its own state table) |
| G5 | Division tables are parallel arrays | unit | done: `divisions_tests.lua` |
| G6 | CC-before-note order not observable in unit mocks | behaviour | covered by patch_ten_slot_slides and live_parameter_recording ordering asserts |
| G8 | 14-bit CC MSB/LSB split | unit | done (characterisation, MIDI 1.0 convention) |
| G9 | `device_map.get_params` cached table shared with callers | code reading | safe today: `safe_set_param` deep-copies; no test |
| G10 | Elektron program changes with two devices on different ports | behaviour | done: M-OPT-ELEK-004 (defect D8 fixed) |
| G11 | Global scale track versus channel scale lock on a coincident step | behaviour | done: M-SCALE-ORDER-001 (processing order and precedence) |
| G12 | Failed saves and autosave suspension | behaviour | done: M-SAVE-FAIL-001 (README 1054 read in context: a failed save does not end a rejected-load suspension) |
| G13 | Song slot bound versus validation | check | no conflict: README 884 states 96 slots (six rows of 16), as validation and the song page use; the plan's F12 row says 90 |
| G14 | `mosaic.lua` load tests reach locals through `debug.getupvalue` | unit seam | refactor-fragile; note only |
| G15 | PERF-003..008 canonical constrained runs | performance | open (measurement only; no fixes) |

### Second pass (UI state, MIDI input, algorithms, hot loops, shared state)

| # | Gap | Layer | Status |
|---|---|---|---|
| D9 | Tooltip frees metro slot `i` (list position) instead of `m.id`; the tooltip timer aliases the autosave metro and "Autosaved" never clears | M-TOOLTIP-002 | defect fixed (`tooltip-metro-id`) |
| D10 | Song slot / global length queued during playback survive Stop and apply at the next Play | M-SONG-QUEUE-STOP-001 | defect fixed (`song-queue-discard-on-stop`, arbitrated SEM-015) |
| D11 | Two-key gestures resolved by release order: releasing the copy source first erased it | M-SONG-COPY-001 | defect fixed for slot copy (`song-slot-copy-press-order`, arbitrated SEM-016); other gestures unchanged by decision |
| C | Real scheduler: a job cancelled earlier in the same update pass still runs one slice; `active_count` can go negative | unit | latent (visible effect at most one stale UI refresh); semantics that hold pinned by `scheduler_tests.lua`; not changed |
| D12 | `pattern.lua` checks `lengths_mask ~= -1` (typo for `length_mask`) | code reading | latent: no version writes -1 (1.2.12 and current write nil); not changed |
| E | Incoming MIDI recomputes the selected channel's step transpose (shared persistent state) | differential probe | not reproduced; a CC-path mutation that clears the state left playback unchanged, so no case kept |
| 9 | MIDI map targets beyond velocity | M-MAP-003 | done: mapped note/length masks, trig param and memory equal their page encoders (equivalence characterisation) |
| 14 | Keyboard chord state (`chord_states`, `midi_off_store`) is never reset, so a Note Off lost with a removed device leaves a stale chord at that step | behaviour | open: README 239 does not say what a lost release should record; needs a decision before an oracle |
| 8 | Held grid key surviving a grid disconnect as a phantom hold | probe | not reproduced: hold step 1, disconnect, reconnect, tap step 24 left the phrase unchanged (no range gesture); the driver's recipe check does not yet model grid_connection, so no case |
| G, 5-7, 11-12, 15-18 | Prime/paint race, stuck held keys, UI asymmetries, per-call debouncers (merge order checked: merged values are order-independent) | behaviour/unit | open |
| 13 | Numeric Repetitor full domain | unit | done: drum_ops_tests.lua golden checksum (characterisation) |
| F | Pattern edit within a few ms of a song boundary is not heard at the next pass of its slot | M-PAT-BOUNDARY-001 | open defect (`pattern-edit-before-song-boundary`), deferred to the refactor: controlled red at 1 ms (3 of 3), green at 10-80 ms and in real time (80 ms) |
| — | Reset with a sounding note across a song transition; memory truncation isolation and save/reload; scale-lock release order | M-TIME-013, M-MEMORY-007, M-GESTURE-ORDER-001 | done (E and D, 3 fresh D repeats each); release order is characterisation kept by SEM-016 |
| D13 | Fixed-channel mask map while a selected-channel step is held wrote the other channel's step mask from the selected channel's value | M-MAP-004 | defect fixed (`fixed-map-held-steps`, arbitrated SEM-017) |
| — | MIDI transport at startup: fresh boot sends none, an autosave-loaded boot sends Stop per port (the M-PANIC-007..010 reds bisected to `b1afcc5`) | M-STARTUP-TRANSPORT-001, panic oracle | done (arbitrated SEM-018: current behaviour kept, oracle corrected) |
| — | Suite lane applicability: six controlled-only fixtures assert on the clock mode and always failed in the real-time lane | suite.py + test_suite | done: declared `controlled_only` in cases.py and recorded as not applicable in real time, with the case's reason |

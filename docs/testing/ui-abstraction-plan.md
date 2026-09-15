# Plan: a UI layer that makes the behaviour cases robust to UI change

Status: proposal (revision 13, after Opus plan review rounds 1-14), not started. Test-side only:
no change to Mosaic (repo root `mosaic.lua`, `lib/`) and none to the emulator checkout.
`tests/behaviour/driver.py` is this suite's own driver over the emulator's public client, so
it is in scope.

## Problem

The 773 behaviour cases (104 case files; `tests/behaviour/cases.py` is ~4,000 lines and holds
the `CASES` registry, shared helpers and many case bodies) drive Mosaic through the driver's
input primitives and exact screen/LED oracles. Measured on 2026-09-11 at `bc0570c` with
`grep -o PATTERN tests/behaviour/*.py | wc -l` (occurrences, all receivers):

| Coupling | Occurrences |
|---|---|
| `.tap(` | 1,333 in 72 files; `tap(1,8)` Play/Stop 195, `tap(3,8)` channel editor 175, `tap(5,8)` pattern editor 158 |
| raw `action(type='grid'|'key'|'enc')` (held gestures) | 503 lines in 54 files |
| `hold_tap(` (hold one key, tap another) | 158 lines in 39 files (156 in 38 case modules) |
| encoder moves `enc(1,` / `enc(2,` / `enc(3,` | 281 / 331 / 527, mostly relative counts from a known page or field |
| `.key(` | 478 |
| exact LED checks `led_values` | 174 in 20 files; direct `['grid']` reads 11 in 8 files |
| pixel oracles `pixels_base64` / `render([` | 48 / 44 in ~31 files; `screen_header` 63 in 24 files |
| frame access `['frame']` (pixels, whole-frame `sha256`) | 54 in 34 files; `frame_oracle` imported by 35 files |

Musical outcomes are asserted on MIDI (`playback`, `['midi']`, logical and monotonic
timestamps) and do not depend on layout. The choreography that reaches a state does:
moving a grid menu button, inserting a channel-editor page, changing header style or
replacing a gesture would fail hundreds of cases whose musical oracle is unchanged.

## Goal, measure and non-goals

Goal: after a UI change that keeps Mosaic's musical behaviour, the files that must change
are the UI layer (`ui.py`, `ui_map.py`, `frame_oracle.py` for rendering changes) and the
interaction-contract modules, and no other case module.

Measure: the contract set is decided by the predicate in section 5, enumerated in the
committed file `tests/behaviour/contract_cases.json` produced in step 0, and bounded by the
ceiling recorded there; `test_ui_layer.py` fails if the set of `CASES` entries defined in
contract modules differs from that file or exceeds the ceiling.

Non-goals: no weakening of any oracle (enforced by the results gate in section 6); no
change to which cases exist or what they claim; no Mosaic observability hooks.

## 1. `ui_map.py`: the single authority for UI facts

Data only. For the UI layer and every non-contract case it is the only file stating each fact
below. `ui.py` and `frame_oracle.py` take every coordinate, level, span and title from it
(checked by `test_ui.py`: no numeric literal appears in a render command, pixel region or grid
cell argument in those two modules). Contract modules (section 5) may keep their own copies:
they are expected to change with the UI and are listed in the cost table.

- **Grid menu row** (y = 8): x of the channel editor, scale editor, pattern editor (repeated
  taps cycle trigger → note → velocity, `lib/m_grid.lua` 95-130), song editor, Play/Stop,
  record and panic buttons.
- **Channel-editor pages**: each page has a stable key (today's `index_to_channel_page`
  identifiers, `channel_edit_page_ui.lua:113`: `Masks`, `Trig Locks`, `Memory`, `Clock Mods`,
  `Midi Config`, `Note Dashboard`), an order, and, as a separate field, the rendered title
  (each page's `page:new` name, `channel_edit_page_ui.lua:211-278`, prefixed `Ch. <n> `: Note
  Masks, Trig Locks, Memory, Clocks, Device Config, Note Dashboard). A rename and a reorder
  are independent edits to the map. The header tab count and each page's tab index derive
  from the order.
- **Fields per page**: a list per page, each field with a stable key, its rendered label, its
  label-plus-value screen region, its value vocabulary, and the visibility predicate it
  depends on
  (Clocks: swing/shuffle type; Device Config: device defaults and MIDI connectivity; Trig
  Locks: sub-page state — sources `channel_edit_page_ui.lua` and
  `channel_edit_page_ui_handlers.lua`). Fields whose position depends on run-time state are
  reachable only by label seek (section 3, kind C), never by offset.
- **Grid geometry per page, keyed by control**: on every page the whole 16 × 8 grid is
  partitioned into named controls, so every cell belongs to exactly one control — steps on rows 4-7 (`step n -> ((n-1) % 16 + 1,
  (n-1) // 16 + 4)`, `fn.calc_grid_count`), the grid menu buttons (y = 8), the channel row
  (y = 1 on the channel editor), the pattern, song and scale slot rows (y = 2, 3 where the page
  uses them), the note-mask and pattern degree cells (rows 1-7 on the mask and pattern
  pages, sharing coordinates with those rows) and the faders. Row 1 and the slot rows are page-dependent, so geometry is keyed
  by page and control.
- **LED vocabulary per control** (section 4).
- **Screen geometry**: header band rows, tab pitch and baseline, title position and level,
  selected-menu-row baseline, level and span, value-field span.
- **Menu parameters and list entries**: stable keys (the norns parameter id, the device id)
  with their rendered labels, for the kind C seeks; per parameter, its option-value
  vocabulary (value key → rendered string, e.g. the clock source's `internal`) for
  enumerated options, and its formatter for numeric values.

**Verb domains are derived from evidence, not enumerated by hand.** Step 0 first makes every
frame and LED oracle's result entry record all the arguments that determine what it renders
or compares (header: title, selected tab, tab count; menu label/value and option row: text
and row; field value: field and value; list label: text; `led_values`: cells and levels) — a
harness change that emits no action — and then captures every case's baseline. From those
entries it derives the map's domains: the set of header families (for the channel-editor
family the tab count is `len(order)` and each page's selected index is its position in the
order, as above — the captured entries only confirm these derived values and are never
stored; other families such as `Trig editor options` with 2 tabs, or `Scale slot <n> ` with 3,
store their template, tab count and selected index explicitly), every menu, field and list value vocabulary (value
key → rendered string, e.g. a length field's `X`, `1/2`, `2`, `64`, `128`, with a formatter
for numeric values), and every LED level set per control. Coverage of what the suite asserts
is therefore by construction; a value that appears later extends the map.

Verbs take keys, never rendered strings: `ui.py` resolves every title, field label and menu
label from the map. A non-contract case module therefore names no rendered UI string, so a
rename is a map edit only.

Sites that state these facts today are found, not listed: after migration no non-contract
module may touch `frame_oracle`, `['frame']`, `['grid']` or raw inputs (section 5 guard), so
every surviving copy of a fact is in `ui.py`/`frame_oracle.py` (which must read it from the
map, above) or in a contract module. Known examples: `frame_oracle.header`,
`selected_line`, `selected_value` (`frame_oracle.py:55-78`), `cases.menu_option_row` and its
per-label row tops (`cases.py:1179-1204`), the device-picker / parameter-list row
(`cases.py:1424-1425`, `elektron_program_changes.py:16-17`, `device_picker_names.py:26-27`,
`nb_param_lock.py:16-17`, `output_cases.py:9-10, 68-69, 116-117`); each moves into `ui.py`
reading the map, or stays in the contract module that owns it.

## 2. `ui.py`: verbs over the driver

`c.ui` wraps the driver. Inputs:

- transport and pages: `play()`, `stop()`, `menu(button)`, `channel_page(page, from_page)`,
  `pattern_editor(view, from_view)`, `song_editor()`, `scale_editor()`;
- selection: `select_channel(n)`, `select_field(name, **path)`, `select_song_slot(n)`;
- norns keys and encoders: `press_key(n)` (press, release, 0.06 s, as `Driver.key`,
  `driver.py:111-112`), `turn(encoder, detents)` for E1-E3 moves not covered by a navigation
  kind, and `set_value(delta)` (E3);
- grid: `tap_control(control, index)` for any mapped control cell (steps, slot rows, mask and
  keyboard cells, menu buttons — symmetric with `expect_leds`), `tap_step(n)` as its shorthand;
- steps and holds: `step(n)` → coordinates, `hold_step(n)` and `hold_keys(*keys)` context
  managers inside which `c.elapse`, MIDI input and other verbs may run, `gesture(presses,
  releases)` for an explicit press and release order that need not nest (e.g. releasing the
  first-pressed step before the slot, `gesture_release_order.py:19-22`),
  `set_range(first, last)` (the hold-step-then-tap-step range gesture), `copy_slot(src, dst)`,
  `record_key(step, note, velocity)`. Together they subsume `tap`, `key`, `hold_tap` (158
  lines) and the 503 raw `action` lines, emitting the same primitives, order and elapses;
- setup: `configure()` (today `Driver.configure`, `driver.py:129-137`, moves here and
  `Driver.configure` becomes a call to it).

Observations: `expect_leds({(control, index): state_name})` (`expect_steps({step: state})` is
its shorthand for the step control), `expect_header(page, **params)` (a page key from any
header family; `params` fill its title template, e.g. `channel=2` or `slot=3`) (the
channel is explicit at the call site, as the origin is for `channel_page`; the map renders
the full title from its `Ch. <n> ` template, so the channel number asserted today is still
asserted), `expect_menu_label(param, row=None)`, `expect_menu_value(param, value)` (a value
key for enumerated options, a number for numeric ones, rendered through the map) and
`expect_menu_option_row(param, value)` (the composite label-plus-value row today's
`cases.menu_option_row` asserts, `cases.py:1179-1189`), `expect_field_value(field, value)`
(a channel-editor field's label-plus-value region, today `cases.length_mask_display`,
`cases.py:1365-1372`), `expect_list_label(entry)` (the
device-picker / parameter-list row), all taking keys or
numbers, never rendered strings; section 4 defines their semantics. Each `ui-confirm`
result entry records the page key and channel it confirmed.

## 3. Navigation kinds

Every navigation idiom in the suite is one of three kinds:

- **A. Map offset.** `channel_page(page, from_page)` emits `enc(1, index(page) -
  index(from_page))`; the origin is explicit at the call site (no hidden tracked
  position, so a raw-primitive contract case or an unmigrated helper cannot desynchronise
  it). The emitted count equals today's relative count, so recipes are unchanged.
- **B. Path-faithful.** Idioms whose path matters are expressed with the path as an
  argument: saturate-then-step (`enc(2, -10)` then `enc(2, 1)`) becomes
  `select_field('velocity', saturate=-10, then=1)`, emitting exactly those detents. Because the
  path is preserved, a case whose subject is the saturating move itself (e.g. the lower
  channel clamp, `cases.py:577-578`) still exercises it through the verb and is not a
  contract case on that account.
- **C. Observed-state seek.** Any idiom whose emitted inputs depend on what is observed: a
  loop emitting detents until an observation predicate holds, or an offset computed from an
  observed state such as `diagnostics.parameter_roots`. Examples: `set_mosaic_options`
  (`cases.py:1191-1206`, including its diagnostics-derived `enc(2, position)` prefix),
  `set_mosaic_number` (`elektron_program_changes.py:27-39`, the same shape),
  `assign_trig_parameter` (`cases.py:1433-1439`), `pick_device`
  (`elektron_program_changes.py:14-25`) and the seek loops in `output_cases.py:114-128` and
  `patch_params.py:86-89`, `output_cases.py:14-17, 73-76`. Their detent count is a function
  of the observed state, so they are exempt from the map-offset rule; they move into `ui.py`
  with their loop and emitted sequence unchanged (their geometry read from the map), so
  recipes are unchanged. They are the kind that survives reordering without a map edit. The
  list is illustrative: kind C is defined by the rule, so an unnamed seek loop is kind C.

Confirmation after navigation is observation-only (one `snapshot()`, no advance). It is valid
only after a primitive that already elapsed at least one redraw period (Mosaic redraws on a
1/30 s poll when dirty, `mosaic.lua:292-301`): true after `tap`/`key` (0.06 s) and `enc`
(0.15 s tail), not after `hold_tap`, whose release has no following elapse. Verbs ending in a
release do not confirm; they keep the case's existing waiting oracle if it has one. No verb
inserts an advance to make a confirmation work. In the real-time lane the confirmation is a
bounded wait (wall-clock, no recipe effect); in the controlled lane it is the single
snapshot. The real-time wait polls every 0.03 s (the driver's own real-time poll,
`driver.py:107`) with a 1 s timeout, 30 redraw periods; on expiry it raises `UiMapError`
naming the expected and observed title, as in the controlled lane.

## 4. Observations preserve the oracle exactly

- **LED vocabulary.** Per control, a bijection between names and exactly one integer level,
  covering every level asserted on that control in the captured baseline results (step 0).
  Because each distinct asserted level gets its own name, the mapping is injective by
  construction; a level that appears later adds a name. `ui_map.py` is the only place it is defined.
- **`expect_leds`** takes a mapping over any number of cells of any mapped controls and calls
  `Driver.led_values` once with the mapped cells and levels: the same single wait until the whole vector holds,
  the same advances emitted, the same result entry recorded. Per-cell queries are never
  substituted for a multi-cell check.
- **Sequences.** A multi-sample sequence, including a blink sampled at level 4 then 2
  (`cases.py:122`) or a re-check separated only by elapsed time (`cases.py:797-802`,
  `channel_scale_display.py:22, 35`), is a sequence of `expect_leds` calls, one per
  `led_values` call today, in the same order with the same waits; nothing is merged or split.
- **Frame oracles.** `expect_header`, `expect_menu_label`, `expect_menu_value`,
  `expect_menu_option_row`, `expect_field_value` and `expect_list_label` call the same
  `Driver.wait` over the same region and render command as today's `screen_header`,
  `menu_label`, `menu_value`, `menu_option_row`, `length_mask_display` and list-label checks (the rendered
  string is resolved from the keys, channel or number, so it is the same string today's
  call passes)
  (`driver.py:125-128`, `cases.py:1730-1736, 1421-1428`), with geometry from the map; they
  emit the same advances and record the same result entry. A label, value or region these
  verbs cannot express (any other pixel region, or a whole-frame `sha256` comparison such as
  `continue_spp.py:32-39`) keeps the raw oracle in a contract case.
- **Input catch-all.** Every grid cell is a mapped control, every norns key and encoder has
  a verb, and `gesture` emits any press/release order, so every input idiom is expressible;
  should one appear that no verb emits exactly, its case keeps the raw primitives and is a
  contract case, symmetric with the assertion catch-all below.
- **Catch-all.** Any assertion made through an API the section 5 guard forbids that no verb
  above expresses exactly — whatever its shape: a predicate over a set of levels (e.g.
  `numeric_merging.py:15`), a comparison with an earlier raw grid or frame sample, a
  whole-frame hash, or any other pixel region — keeps its raw oracle, and its case is a
  contract case. Such assertions all read `['grid']`/`['frame']` or `frame_oracle` directly
  in case code outside the verb sources (section 5), which is what the section 5 scan
  detects. No forbidden assertion can fall outside both a verb and this rule.

## 5. Contract cases and the guard

**Predicate (mechanical, applied in step 0).** A case is a contract case if and only if
(a) it carries a `NAV-*` requirement, or (b) its run callable, or a `tests/behaviour` helper
it reaches (excluding `driver.py`, `ui.py` and `frame_oracle.py`), contains a frame or grid
access that no verb reproduces. The test is on the shape of the call, wherever it is written:

- calls to `frame_oracle.header`/`matches`, `selected_line` and `selected_value`, and to
  `Driver.screen_header` and `Driver.led_values`, are reproducible by verbs and never make a
  case contract, inline or in a helper (their arguments are in the captured entries that
  built the verb domains, section 1);
- `render` plus region comparisons are reproducible only inside the helpers listed in the
  committed `tests/behaviour/ui_verb_sources.json` (helper → verb), written in step 0 from
  the region shapes the verbs cover — `cases.menu_option_row`, `parameter_list_label`,
  `length_mask_display`, `elektron_program_changes.pick_device` and the kind C seeks, among
  others; the file records each site as module and function;
- any other `render` call, direct `['grid']`/`['frame']` read or `pixels_base64` decoding makes
  the case contract (the section 4 catch-all).

A case that fails at baseline is classified contract, fail-closed, and recorded as such.
Step 0 writes the list and its size to `contract_cases.json`; that size plus 10% is the
ceiling. The predicate is recomputed after step 1 and after each step that moves a listed
helper into `ui.py`; the moved helper's entry in `ui_verb_sources.json` is updated to its
new home in the same commit, the excluded code is the same, and the list must be identical
(a difference fails the guard). A migration that would add a contract case updates the file
in the same commit.

**Unit: the module.** In step 0 every contract case body, in any case module, moves into
`tests/behaviour/contract/*.py` (from `cases.py`, and from mixed modules such as
`patch_params.py`, whose `patch_slide_live_division` is contract while `patch_nrpn_bytes` is
not); helpers used by both halves move into `ui.py` if non-contract code needs them, and are
duplicated into `contract/` otherwise. No module then holds both contract and non-contract
bodies, so every allowlisted module can become clean and the allowlist can empty. Raw primitives — `tap`, `key`, `enc`, `hold_tap`,
`action(type='grid'|'key'|'enc')`, `led_values`, `screen_header`, direct `['grid']` or
`['frame']` access (including `['frame']['sha256']`), `pixels_base64` decoding and any call into
`frame_oracle` (`render`, `header`, `selected_line`, `selected_value`, `matches`) — are
allowed only in `driver.py`, `ui.py`, `frame_oracle.py`,
`contract/*.py`, and modules listed in the migration allowlist. A helper belongs to the
module that defines it; shared helpers used by non-contract cases live in `ui.py` (or are
migrated before any caller leaves the allowlist).

**Guard.** `test_ui_layer.py` (added to `suite.py` `PYTHON_UNITTEST`) scans the case
modules — those defining a `CASES` run callable and the `tests/behaviour` helpers they
import — and not the harness (`run.py`, `repeat.py`, `suite.py`, `driver.py`, the gate
script), which reads observation state by design. It asserts: no raw primitive outside the
allowed modules; every `CASES` run callable (lambdas resolved to their
defining function) is defined in a contract module iff its ID is in `contract_cases.json`;
the contract count is within the ceiling; and for the allowlist
(`tests/behaviour/ui_migration_allowlist.json`): every entry exists, none is duplicated,
and no entry is clean (a listed module with no raw primitive fails the test, forcing its
removal in the same commit). The allowlist file and its test are deleted in the step that
empties it.

## 6. Migration gate (fail-closed)

Evidence lives in `docs/testing/ui-migration-baselines/<case>/<lane>/{before,after}/`, where
`<lane>` is `controlled` or `real-time`, committed with the migration. For every case in a
module being migrated, in every lane the suite runs it in (`controlled_only` cases:
controlled only; `crow-jf`/`nb-audio` cases: real-time only; all others: both):

1. Before any edit, run the case at the current commit and copy its `recipe.json` and
   `results.json` to `<case>/<lane>/before/`. A missing `before/` fails the gate.
2. After the edit, run it again and copy the same two files to `<case>/<lane>/after/`.
   `tests/behaviour/ui_migration_gate.py <case>/<lane>` exits non-zero unless the normalized
   recipes are identical (same actions, order and, in the controlled lane, advances) and the
   results match, per lane: in the controlled lane `after/results.json` equals
   `before/results.json` except for added entries of kind `ui-confirm`; in the real-time lane
   entries carry per-run measurements (jitter, durations, capture paths, and `expected`
   values some cases derive from what was observed), so the compared projection is the
   ordered list of entry `kind`s, again ignoring added `ui-confirm` entries, and the run must
   pass. A missing or unparsable file or an entry without `kind` fails the gate.
   `observations.json` is not compared (confirmation snapshots add observations). For cases
   that also run in the controlled lane, the controlled comparison is what proves no oracle
   was weakened; for real-time-only modules (`output_cases.py`, `nb_param_lock.py`) the kind
   projection proves no oracle was dropped, and item 5's side-by-side review is required for
   every changed assertion line.
3. Normalization (both lanes, implemented in the gate script, unit-tested in `test_ui.py`
   with a nested schedule): remove every `at_monotonic_ns` field recursively, at any depth.
   The driver's own native-trace comparison (`driver.py:186`) strips it only from an
   action's top level, while `midi_schedule` actions carry it inside each element of their
   `events` list (`cases.py:1864-1870`, `continue_spp.py:17-20`, `forwarded_clock.py:41-43`).
4. Repeatability, per migrated module: if it has a controlled-lane base-midi or
   midi-modulation case, one such case passes `repeat.py`; otherwise (only
   `crow-jf`/`nb-audio` cases, e.g. `output_cases.py`, `nb_param_lock.py`) one case is run three
   times fresh in real time and its three normalized recipes must be identical and all three
   runs pass.
5. Where an assertion is deliberately re-expressed, the commit shows the old and new
   `results.json` entries side by side; if the old entry cannot be reproduced, the case
   becomes a contract case instead.

## 7. Steps

0. Classify: make every oracle entry record its rendering arguments (section 1); capture
   every case's `before/` evidence in each lane it runs in (section 6 item 1); build
   `ui_map.py`'s grid partition and derive its domains (header families, value
   vocabularies, level sets) from the captured entries; write `ui_verb_sources.json`; run the
   section 5 predicate, write `contract_cases.json` with the ceiling, move
   contract bodies into `contract/`, add the guard with the full allowlist, and document the
   layer, the contract rule and the allowlist in `tests/behaviour/README.md` (correcting its
   "raw screen/LED" sentence to distinguish contract from migrated cases).
1. Complete `ui_map.py` (stable keys, field regions and visibility predicates, over the
   step 0 domains) and build `ui.py` and the gate script, with unit tests in
   `tests/behaviour/test_ui.py` (added to `suite.py` `PYTHON_UNITTEST` with
   `test_ui_layer.py`; no emulator) that the
   verbs emit the expected primitive sequences, the LED vocabulary is injective and
   `expect_steps` makes one `led_values` call, and confirmations accept the right frame,
   reject a wrong header, and do not run after a release.
2. Make `frame_oracle`, `menu_option_row` and `parameter_list_label` derive from the map;
   move `configure` and the shared helpers into `ui.py`; gate every case (section 6).
3. Migrate case modules family by family through the gate; each empties its allowlist
   entries.
4. Drift drill: on a scratch branch, swap the order of two channel-editor pages in
   `ui_map.py` only. The drill set is every migrated case whose
   `<case>/controlled/after/results.json` has a `ui-confirm` entry for either swapped page
   (real-time-only cases are outside it: they reach the same `ui.py` confirmation code, and
   the drill tests that code, not the lane). Each case in the set must fail with `UiMapError`
   in the controlled lane, and one base-midi or midi-modulation member must also fail that
   way under `repeat.py`; a member that passes, or fails any other way, fails the drill. The
   outcome (case, status, first error) is written to `docs/testing/ui-migration-drill.json`
   and committed with the final step.

## 8. Cost of a later UI change

| Change | Files that change |
|---|---|
| grid menu button moved | `ui_map.py`; contract cases for the menu |
| channel-editor page inserted, reordered or renamed | `ui_map.py` (order or title field; tab count and indices derive); contract cases for page navigation |
| header or font style | `ui_map.py` screen geometry and/or `frame_oracle.py` rendering; contract modules that pin pixels with their own geometry |
| a gesture replaced (e.g. hold step + E3 becomes another gesture) | that verb in `ui.py`; its contract case |
| a UI paradigm change | `ui.py`, `ui_map.py`; contract cases; musical cases only if musical behaviour changed |

## Risks

- Recipe identity is strict: re-ordering two harmless primitives breaks it. That is
  intended; the gate is not relaxed.
- The contract set may be larger than hoped where cases interleave LED stories with musical
  ones; the ceiling makes that visible at step 0 rather than at the end.
- Effort: the surface is ~1,300 taps, ~1,140 encoder moves, ~480 key presses, 156
  `hold_tap` gestures (38 modules) and 503 held raw actions across 104 files. Migration runs family by family; the suite stays green
  throughout via the allowlist.

Every case, contract or not, follows the repository's existing rule: it cites the README lines
for what it pins or is labelled characterisation, with its arbitration reference where one
exists (e.g. M-GESTURE-ORDER-001, a release-order characterisation kept by SEM-016, which is
non-contract under the section 5 predicate and uses `gesture`); a contract case pinning a
documented gesture while characterising its exact rendering carries both.

## Review record

Reviewed with `paranoia` `critique_plan` (engine claude, model claude-opus-5, lineage
`mosaic-behaviour-tests~ui-abstraction~plan`), 14 rounds on 2026-09-11. Nine classes were
raised and closed: executable fail-closed gate (92ea13d6), navigation kinds (9642d663), exact
observation verbs (98111157, replaced by 43e26b14), single authority for UI facts (5c1d23a6),
guard unit (15ea0621), premises about the tree (c2ba9f85), census and verb coverage of input
APIs (3ebc3349), a decidable contract set (b7fcfa98), and confirmation timing (fd0a420b).
Round 14, the cold final regression, reopened 3ebc3349 (no verb for a bare key press, a tap
on non-step controls, or a non-nesting release order); revision 13 adds `press_key`, `turn`,
`tap_control`, `gesture` and an input catch-all for it. By the maintainer's decision the loop
stopped there: revision 13 has not been re-reviewed, so the lineage's last computed state is
BLOCKED on that one class.

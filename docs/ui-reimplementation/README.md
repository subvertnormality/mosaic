# Mosaic UI reimplementation contract

This is the canonical specification for migrating the UI on `codex/1.4.0`.
Read `../../README.md` as the musical manual. It was read in full against
commit `56a9ba23` on 24 September 2026; its fingerprint and section-by-section
text are recorded in `source-inventory.json`, and the validator checks each
section against the README itself. The baseline is that commit, never a working
tree: uncommitted copies of inventoried sources invalidate the contract. Assume `../testing/ui-abstraction-plan.md`
has been completed before beginning implementation.

## Authority and reading order

1. `spec.json`: machine-readable screen registry, input precedence and emission,
   effect contracts, source-route translation, physical grid ownership (including
   the Rhythm Doctor overlay and `doctor_routes`), task navigators, providers,
   field domains, migration slices and acceptance matrix.
2. `source-inventory.json`: source fingerprints, every registered grid callback
   with its branch ledger, retained controller/native-setting units and
   manual-to-screen mappings.
3. `code/screen.lua`: executable data-bound layout proto-code. Feed it a
   `ViewModel` following `spec.json#/view_model`; never feed it application state.
4. `code/atlas.lua`, `code/characters.lua`, `code/visuals.lua` and `fixtures.json`:
   coded accepted visual examples, including the doctor, garden and choir.
   Their example values are not bindings. `characters.draw_art` exports the
   decorative characters without titles, state or controls.
5. `tools/model.py`: executable presentation transition reference;
   `tests/test_contract.py`: specification regressions and mutation checks.
6. `IMPLEMENTATION.md`: executor procedure and evidence requirements.

The HTML acceptance library is generated at `generated/index.html`. It has no
independent authority. Changes begin in the JSON/Lua contract, then regenerate
the library. No screenshots are needed to interpret or implement a screen.
The older `monome-emulator/docs/proposals/mosaic-ux-harmony` HTML and Markdown
remain historical design references; this package supersedes them for execution.

## Small context bundles

An executor should load one slice and the relevant screen/flow bundle at a time:

```text
python -X utf8 docs/ui-reimplementation/tools/query.py slice UI02
python -X utf8 docs/ui-reimplementation/tools/query.py screen M13
python -X utf8 docs/ui-reimplementation/tools/query.py flow G13
python -X utf8 docs/ui-reimplementation/tools/query.py manual MAN.115
```

Each screen bundle includes its owner, field contract, applicable input rules,
feature edges, manual references and acceptance groups. `schema.json` supplies
editor tooling; `validate.py` adds cross-reference and source checks.

## Product rules

Mosaic is grid first. Preserve the existing grid callback and its timing, musical
mutation, modifier precedence and release behavior. After it resolves, emit one
read-only outcome. Norns follows that outcome; it must not execute it again.
The grid's existing renderer continues to own musical LED state.

Channel E1 progresses Masks → Trig parameters → Tasks, one stop per input;
negative movement reverses and clamps. E2 selects a field; E3 edits through its
original owner. Held steps establish the exact edit scope and override a feature
draft before clear/slide/edit. Native menus own norns controls while open.
Playback, MIDI and queue updates change displayed data without stealing focus.

The feature editors share the same scope, field, value, status and footer layout.
Rhythm Doctor has a recognisable physician with head mirror, shades, coat and
stethoscope. Merge's garden and Harmony's choir are decorative: their positions
must never be mistaken for live counts or emitted notes. Live diagrams read an
explicit immutable snapshot; absent data stays absent. Active, queued and draft
values remain distinguishable.

An old gesture may acquire a better flow, but its function must have an explicit
replacement and unchanged musical acceptance. A screen fixture's short field
list cannot remove a conditional or generated owner field. Native parameters,
device controls, NRPN compatibility, MIDI mapping and lock lead time are retained.

## Validate and regenerate

From the repository root, with Python 3 and Lua available:

```text
python -X utf8 docs/ui-reimplementation/tools/validate.py
python -X utf8 -m unittest discover -s docs/ui-reimplementation/tests -v
python -X utf8 docs/ui-reimplementation/tools/compile.py
lua docs/ui-reimplementation/tools/replay.lua
python -X utf8 docs/ui-reimplementation/tools/build_html.py
node docs/ui-reimplementation/tools/check_html.cjs
```

Windows Lua 5.3 is installed and the plain `lua` command above works. An optional WSL invocation is:

```text
wsl -d Ubuntu-20.04 --cd /mnt/c/Users/andy/Documents/ChatGPT/mosaic /usr/bin/lua docs/ui-reimplementation/tools/replay.lua
```

A source fingerprint failure requires reviewing the actual change and updating
its mappings and baseline intentionally. Do not automatically refresh hashes to
make validation green. `--skip-source-fingerprints` is for isolated specification
mutation tests, never the implementation readiness gate.

## What validation establishes

The validator checks declared references, input ownership ambiguity, source
identity, manual sections against the README, field identity, route maps, the
branch ledger, the Doctor overlay and route table, and the 128-cell partition for
every context. Transition tests exercise
navigation, held scope, native ownership, read-only protection and invalidation.
Lua replay executes every accepted fixture and its data-bound counterpart, plus
empty states. Synthetic text metrics permit offline execution; they do **not**
certify native font bounds, visual overlap, real-time behavior or hardware timing.

Implementation completion requires the emulator and Lua gates in the contract.
No specification can prove that arbitrary future code is bug-free. The purpose of
this package is to make missing functions, routing conflicts and evidence gaps
visible before implementation, then require actual player-visible evidence for
each migrated slice. There are no production UI changes in this deliverable.

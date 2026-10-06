# Mosaic manual expansion report

The approved Masks pilot is now expanding into a complete manual. There are
**133 stable feature destinations**, rewritten reference text, guided workflows,
a musical cookbook and additional native interaction scenes. Final native
capture and publication gates are still in progress. The YAML model is now the
documentation authority; final acceptance activation has not happened.

Work uses the freshly fetched `origin/codex/1.4.0` baseline
`54d7b871358fcc68b7166847603cc9fb1461d0b6`, in
`/home/andy/mosaic-manual-1.4.0`, branch `manual/1.4.0-interactive`.
The current committed revision is
`69df623e06efd6721e1cc53e961a1dd845d2a48c`; expansion changes are being
integrated locally. The older Windows checkout and its existing edits were
preserved.

A temporary public preview was published after explicit approval at
[the remote manual preview](https://karen-diy-clarity-status.trycloudflare.com/manual/).
It depends on the local preview service and tunnel. This is separate from a
GitHub Pages deployment. No Git push or PR has been made.

## Completed authoring and interface work

- A 133-feature YAML catalogue with stable anchors, source references,
  procedures, control/result tables, musical uses and related routes. Newcomers
  have First sound, No sound, Build a phrase and Save your work paths; experts
  have search, dense lookup and quick reference.
- Mosaic's four-tile mark, restrained instrument colours, compact control
  labels and a grid-oriented layout. Reference prose uses literal operation
  names and numbered instructions. `RESEARCH.md` and `STYLE.md` identify the
  adopted patterns and exactly which primary-manual sections were reviewed.
- Actual norns framebuffer and grid brightness data, shown together through
  plain HTML/CSS/JS. Scene controls support stepping, replay, clickable keys and
  pads, draggable encoders, keyboard focus and reduced motion. Textual controls
  remain available alongside the devices.
- An independently authored First sound scene matching the guide: an empty
  project, four attacks, MIDI 60, velocity 80 and half-step length. It checks its
  own screen/grid/MIDI expectations and the full existing M-PAT-001 baseline.
- Three additional four-bar audio examples and the original Masks example,
  with compressed Opus/MP3 files and native captured playhead timelines.
- A generated quick reference prepared from the same feature model. Independent
  review accounts for all **77** old cheat-sheet gesture/result rows:
  **54 preserved, 23 clarified**. The report cites current authored excerpts,
  code and cases; the old sheet is also archived unchanged.
- One-command orchestration for independent capture lanes, musical audio,
  source indexing, compilation, native publication audit and browser checks.
  `--plan-only` inspects the full command list without starting native sessions.
  See [BUILD.md](BUILD.md).

The rendering model contains no invented framebuffer states. Frames remain
bound to semantic assertions and immutable native evidence. Editorial overlays
change only permitted text fields and retain the original performance source
identity; publication auditing rejects changed inputs or expectations.

## Latest readiness checkpoint

The current authored catalogue retains **133 destinations**, with declared
editorial statuses of **107 verified, 25 pending and one pilot-reviewed**. These
are authoring statuses, not final acceptance of every workflow. The earlier
[read-only gap inventory](evidence/readiness-gap-inventory.json) records an
intermediate 101-scene publication checkpoint and its exact source hashes; it
must not be read as the final candidate inventory.

Original source preservation remains **125 README section IDs, 178 requirements
and 77 cheat-sheet rows**. The original **876 case IDs** remain unchanged.
Three additive canonical registrations bring the current inventory to **879**:
vertical-list UI, shared Merge Strategy, and readability. Registration alone
does not promote a requirement, domain or native acceptance status. The
inventory and matrix retain that distinction explicitly.

The user has authorized the interactive YAML manual as documentation authority
and a shorter root README. Exact original documents remain archived, and an
initial pre-authority full-document snapshot is also preserved. The final
normative UI instructions are now frozen in content-addressed full README and
cheat-sheet archives. The overview, AGENTS and generated quick-reference
replacements are now applied. Root README is an overview, AGENTS identifies the
YAML authority, and the root quick reference is generated from that model.
Post-replacement verification passed all 53 focused authority, inventory,
collection and quick-reference checks; all 55 historical statement mappings
resolve without relying on the shortened root README. UI source-ledger rebasing
uses the explicit full-manual archive, with overview and YAML identities kept
separate. The [replacement verification receipt](evidence/authority-document-replacement-verified.json)
records the exact root hashes and preserved source aliases.
Acceptance authority is prepared but **inactive**; there is no final mutable
authoring identity or complete-book claim yet.

The 25 entries awaiting final binding cover Lead, Record, Panic, Doctor,
shared merge strategies, clocks/swing, button indicators, norns navigation,
Save/Load, both reset options, Trigless Locks, the three pentatonic options,
the three keyboard scale options, Screen options, UI Motion, Merge/Harmony
navigation, Foundation, Fragments and Result/Reason. Earlier native publications
exist for parts of that scope, including Record and the two Doctor workflows.
They are historical progress evidence. The final build must independently audit
fresh scenes, matching controlled lanes where applicable, explicit audio-only
exceptions, all chapter contracts, and their exact current bindings before
those pending entries can be promoted.

The original Mosaic logo and its colours are retained in the manual. Newly
approved miniature screen graphics and readability changes reopen the native
candidate: earlier passing UI/Doctor evidence remains preserved and cannot be
relabeled as acceptance of the new graphics. No source badge was promoted by
this reporting or inventory update.

## Earlier durable native evidence

The following real-time scene families have passed and have preserved native
reports. Their controlled-time evidence is separate.

| Published reference family | Scenes | Semantic capture checkpoints |
| --- | ---: | ---: |
| Core navigation, algorithms, merge, scale and song | 9 | 39 |
| Composition workflow | 2 | 5 |
| Musical merge and harmony | 16 | 42 |
| Parameters, articulation and quantisation | 25 | 74 |
| Remaining independent options/navigation | 11 | 28 |
| Device handling | 3 | 3 |
| Locks | 3 | 14 |

These **69 reference scenes and 205 checkpoints** are a progress inventory,
not a complete manual or exhaustive campaign claim. The original four Masks
scenes contain 22 authored steps. The independent First sound scene adds six
checkpoints and has passed in both real and controlled lanes; its audit receipt
is [first-sound-independent-audit.json](evidence/first-sound-independent-audit.json).

Additional Masks boundary cases M-MASK-017 and M-MASK-021 passed in both lanes.
The authoring regression changed velocity 50 to 51 in temporary YAML and
observed different native pixels and exact MIDI velocity 51, while preserving
the published source and baseline.

The pilot publication audit checked **123 native screen/grid captures**,
including its recorded audio timeline. Later reference families have their own
source, assertion, frame, trace and participant identities; final combined
publication auditing is pending completion of the remaining runs.

## Audio evidence

All three expansion clips are four bars at 90 BPM. Each has 68 sampled timeline
frames, an MP3 fallback and independently captured solo contributions.

| Example | Actual voices | Peak / RMS | Clipped samples |
| --- | --- | --- | ---: |
| Three sounds, one pocket | Oilcan 1, three percussion note selections | 0.404 / 0.0639 | 0 |
| Bass and intervals | Polyperc bass + Doubledecker harmony | 0.088 / 0.0127 | 0 |
| Three-voice conversation | Oilcan + Polyperc + Doubledecker | 0.358 / 0.0524 | 0 |

Oilcan now has actual native WAV and encoded-audio evidence; it is not merely
researched. Exact pins and voice guidance are in [VOICES.md](VOICES.md), and
[audio-report.json](evidence/audio-report.json) identifies the immutable native
run, metrics, solos and file hashes. Emplaitress remains researched/pinned;
MiPlaits availability limits native evidence, so no Emplaitress recording is
claimed.

The original Masks recording uses Polyperc and Doubledecker on separate
channels. Mosaic reserves an assigned player for its channel; a second channel
cannot reuse that same player instance. The separately researched
`nb_plyprc` variant is outside Mosaic's admitted names; the supported
`nb_polyperc` implementation is used.

## Verification and remaining integration

The complete existing Lua suite passed again during expansion:
**2,398 successes, zero failures**. Its log and production-source hashes are
[lua-expansion.log](evidence/lua-expansion.log) and
[lua-expansion-source.json](evidence/lua-expansion-source.json).
An unchanged staging copy named `mosaic` accommodates the suite's relative
include convention. The initial pilot staging failure remains separately
recorded.

Focused regression checks cover rejecting schemas, source identities, inventory
preservation, stable citations, case grouping, child-session participants,
publication bindings, quick-reference coverage, build planning, markup and
audio selection races. Failed red evidence and passing results are retained
separately. A final consolidated Python result will be recorded after the
authoring and capture integration settles.

Earlier browser checks passed at 1440, 768 and 390 pixels for all 133 anchors,
the then-published scenes, native brightness/LED rendering, search, themes,
reader routes and all three additional audio examples. Remote frontend
verification also fetched the clips through the approved public preview.
The audio race regression verifies that a late response from the previously
selected example cannot replace the selected audio. These checks must run
again against the final combined publication.

Remaining work is the residual readiness scope listed above, final UI candidate
recapture, full publication/browser gates and the coordinated documentation
integration. Navigation, Stop, options, modulation, polymeter and nested-session
real-time batches have since passed; their receipts are preserved separately.
The earlier 69-scene table is an intermediate checkpoint, not the final total.

The README/AGENTS documentation switch is authorized; final acceptance activation remains gated. Earlier cleanup receipts
prove their completed sessions closed; new candidate campaigns require fresh
cleanup receipts. Final source identities, consolidated test totals and the
complete workflow/case closure map will be recorded after the candidate settles.

Every report leaves `complete_regression_run` false. Content migration and
manual capture coverage do not substitute for the existing exhaustive sharded
campaign or real-norns evidence.

## Findings and limits

[DISCREPANCIES.md](DISCREPANCIES.md) retains source-line evidence, including
ambiguous channel-default terminology, historical task navigation, chord
interval explanation, the stale script version header and later scale/song
clarifications. The quick-reference audit also corrected channel-octave scope,
algorithm fader availability, parameter-specific fine control and plain MIDI
audition. A continuous-hold edit/clear boundary remains an observed discrepancy,
not a diagnosed production fix; its failed and passing recipes stay distinct.

Octave labels are **control-specific**. Masks calls norns
`musicutil.note_num_to_name`, displaying MIDI 60 as C3. The stock Fixed Note
parameter has another label table and displays MIDI 60 as C5. These names refer
to the same numeric MIDI pitch; the reference uses MIDI numbers when comparing
them. It does not claim that every norns or Mosaic control calls MIDI 60 C3.

The playhead is sampled against host recording time, not calibrated to sample
accuracy or physical norns. Controlled time establishes logical semantics,
not DSP or hardware scheduling. Signal metrics and browser checks establish
captured audio integrity and playback; they do not establish physical-device
performance or artistic quality.

Research attribution remains bounded: current targeted Syntakt and Polyend
Play sections were retrieved, while older Digitakt/Octatrack/Tracker links are
historical references rather than newly verified complete reviews. Inaccessible
Lines discussions are not presented as read.

Local commits are unsigned because the configured signing key could not be
unlocked in this session. Signing configuration was not changed.

## Complete source mapping, separate from acceptance

The [machine-readable preservation receipt](evidence/source-coverage.json) records
all counts, source hashes, mappings and retained requirement/case IDs.

All **125 original MAN section IDs** map to current stable feature destinations;
all **178 original requirement IDs** remain in the behaviour inventory. The
eight additional destinations provide tutorials and cookbook material. No
original section was dropped when the README text was archived. The table below
lists every original section mapping; the machine-readable inventory retains
its original excerpts, requirement and case links.

All **77 old cheat-sheet rows** are separately mapped in
[QUICK_REFERENCE_COVERAGE.md](QUICK_REFERENCE_COVERAGE.md) and
[the detailed row evidence](evidence/quick-reference-coverage.json). They include
gesture and result preservation or an explicit source-backed clarification.

These are content/citation coverage claims. A linked introductory scene or a
verified editorial badge does not accept an entire workflow, all interactions,
all original case IDs, or the exhaustive campaign. Every comprehensive workflow
still needs its complete applicable case/native scope and final coverage gates.
The inventory's new current_review records actual bound and missing scene
references separately from the frozen source_review baseline; current evidence
cannot rewrite a historical source review.

| Original section ID | Current feature destination | Bound scene references, not full-case acceptance |
| --- | --- | --- |
| MAN-001 | [getting-started](./#getting-started) | 5 bound |
| MAN-002 | [install](./#install) | Explicit non-native scope |
| MAN-003 | [setup](./#setup) | 2 bound |
| MAN-004 | [hardware](./#hardware) | Explicit non-native scope |
| MAN-005 | [midi-device-configuration](./#midi-device-configuration) | 1 bound |
| MAN-006 | [stock-devices](./#stock-devices) | 1 bound |
| MAN-007 | [adding-custom-devices](./#adding-custom-devices) | 1 bound |
| MAN-116 | [lock-lead-time](./#lock-lead-time) | 0 bound |
| MAN-008 | [mods-and-software-devices](./#mods-and-software-devices) | 0 bound |
| MAN-009 | [midi-keyboard-input](./#midi-keyboard-input) | 3 bound |
| MAN-010 | [midi-controller-mapping](./#midi-controller-mapping) | 0 bound |
| MAN-011 | [getting-around-mosaic](./#getting-around-mosaic) | 4 bound |
| MAN-012 | [sequencer-start-and-stop](./#sequencer-start-and-stop) | 1 bound |
| MAN-013 | [arm-live-record](./#arm-live-record) | 0 bound |
| MAN-014 | [grid-menu-navigation](./#grid-menu-navigation) | 4 bound |
| MAN-015 | [norns-menu-navigation](./#norns-menu-navigation) | 1 bound |
| MAN-016 | [tooltips](./#tooltips) | 1 bound |
| MAN-114 | [external-midi-transport](./#external-midi-transport) | 0 bound |
| MAN-017 | [midi-panic](./#midi-panic) | 0 bound |
| MAN-018 | [cheat-sheet](./#cheat-sheet) | Explicit non-native scope |
| MAN-019 | [typical-workflow](./#typical-workflow) | 5 bound |
| MAN-020 | [sound-design](./#sound-design) | 1 bound |
| MAN-021 | [rhythm-section-design](./#rhythm-section-design) | 4 bound |
| MAN-022 | [harmony-design](./#harmony-design) | 3 bound |
| MAN-023 | [sequence-composition](./#sequence-composition) | 2 bound |
| MAN-024 | [using-merge-modes](./#using-merge-modes) | 3 bound |
| MAN-025 | [melody-composition](./#melody-composition) | 3 bound |
| MAN-026 | [modulation-movement-and-interest](./#modulation-movement-and-interest) | 5 bound |
| MAN-027 | [song-composition](./#song-composition) | 3 bound |
| MAN-028 | [dig-deeper](./#dig-deeper) | 4 bound |
| MAN-029 | [pattern-editor](./#pattern-editor) | 4 bound |
| MAN-030 | [adding-trigs](./#adding-trigs) | 2 bound |
| MAN-115 | [rhythm-doctor](./#rhythm-doctor) | 0 bound |
| MAN-031 | [adding-notes](./#adding-notes) | 2 bound |
| MAN-032 | [adding-velocity](./#adding-velocity) | 2 bound |
| MAN-033 | [channel-editor](./#channel-editor) | 4 bound |
| MAN-034 | [devices](./#devices) | 1 bound |
| MAN-035 | [midi-sound-sources](./#midi-sound-sources) | 1 bound |
| MAN-036 | [norns-sound-sources-with-n-b](./#norns-sound-sources-with-n-b) | 0 bound |
| MAN-037 | [device-parameters](./#device-parameters) | 2 bound |
| MAN-038 | [adding-patterns-to-channels](./#adding-patterns-to-channels) | 1 bound |
| MAN-039 | [masks](./#masks) | 4 bound |
| MAN-040 | [adding-trig-masks](./#adding-trig-masks) | 1 bound |
| MAN-041 | [adding-melodic-notes-over-harmony-and-drums](./#adding-melodic-notes-over-harmony-and-drums) | 1 bound |
| MAN-042 | [adding-chords](./#adding-chords) | 3 bound |
| MAN-043 | [removing-masks](./#removing-masks) | 3 bound |
| MAN-044 | [merge-modes](./#merge-modes) | 1 bound |
| MAN-045 | [trig-merge-modes](./#trig-merge-modes) | 2 bound |
| MAN-046 | [note-merge-modes](./#note-merge-modes) | 2 bound |
| MAN-047 | [velocity-merge-modes](./#velocity-merge-modes) | 0 bound |
| MAN-048 | [length-merge-modes](./#length-merge-modes) | 0 bound |
| MAN-049 | [note-dashboard](./#note-dashboard) | 0 bound |
| MAN-050 | [clocks-swing-and-shuffle](./#clocks-swing-and-shuffle) | 1 bound |
| MAN-051 | [memory-undo-and-redo](./#memory-undo-and-redo) | 0 bound |
| MAN-052 | [channel-length](./#channel-length) | 1 bound |
| MAN-053 | [muting-channels](./#muting-channels) | 1 bound |
| MAN-054 | [trig-parameters](./#trig-parameters) | 3 bound |
| MAN-055 | [sequencer-params](./#sequencer-params) | 3 bound |
| MAN-056 | [trig-probability](./#trig-probability) | 1 bound |
| MAN-057 | [fixed-note](./#fixed-note) | 1 bound |
| MAN-058 | [quantised-fixed-note](./#quantised-fixed-note) | 1 bound |
| MAN-059 | [random-note](./#random-note) | 1 bound |
| MAN-060 | [random-twos-note](./#random-twos-note) | 1 bound |
| MAN-061 | [chord-strum](./#chord-strum) | 3 bound |
| MAN-062 | [chord-arpeggio](./#chord-arpeggio) | 2 bound |
| MAN-063 | [chord-acceleration](./#chord-acceleration) | 1 bound |
| MAN-064 | [chord-spread](./#chord-spread) | 2 bound |
| MAN-065 | [chord-velocity-modifier](./#chord-velocity-modifier) | 1 bound |
| MAN-066 | [chord-shape-modifier](./#chord-shape-modifier) | 3 bound |
| MAN-067 | [mute-root-note](./#mute-root-note) | 1 bound |
| MAN-068 | [fully-quantise-mask](./#fully-quantise-mask) | 1 bound |
| MAN-069 | [scale-editor](./#scale-editor) | 1 bound |
| MAN-070 | [transposition](./#transposition) | 1 bound |
| MAN-071 | [song-editor](./#song-editor) | 3 bound |
| MAN-072 | [button-indicators](./#button-indicators) | 0 bound |
| MAN-073 | [interacting-with-slots](./#interacting-with-slots) | 2 bound |
| MAN-074 | [song-mode-operations](./#song-mode-operations) | 1 bound |
| MAN-075 | [adjusting-song-sequence-length](./#adjusting-song-sequence-length) | 1 bound |
| MAN-076 | [navigating-the-norns-display](./#navigating-the-norns-display) | 1 bound |
| MAN-077 | [locks](./#locks) | 7 bound |
| MAN-078 | [trig-param-locks](./#trig-param-locks) | 2 bound |
| MAN-079 | [param-slides](./#param-slides) | 2 bound |
| MAN-080 | [mask-locks](./#mask-locks) | 4 bound |
| MAN-081 | [scale-locks](./#scale-locks) | 0 bound |
| MAN-082 | [transposition-locks](./#transposition-locks) | 0 bound |
| MAN-083 | [octave-locks](./#octave-locks) | 0 bound |
| MAN-084 | [save-and-load](./#save-and-load) | 0 bound |
| MAN-085 | [options](./#options) | 0 bound |
| MAN-086 | [sequencer-options](./#sequencer-options) | 0 bound |
| MAN-087 | [shift-press-stop](./#shift-press-stop) | 0 bound |
| MAN-088 | [song-mode](./#song-mode) | 1 bound |
| MAN-089 | [reset-at-song-editor-pattern-change](./#reset-at-song-editor-pattern-change) | 0 bound |
| MAN-090 | [reset-at-pattern-repeat](./#reset-at-pattern-repeat) | 0 bound |
| MAN-091 | [parameter-slides-wrap](./#parameter-slides-wrap) | 1 bound |
| MAN-092 | [elektron-program-changes](./#elektron-program-changes) | 0 bound |
| MAN-093 | [elektron-program-change-channel](./#elektron-program-change-channel) | 0 bound |
| MAN-094 | [parameter-lock-options](./#parameter-lock-options) | 2 bound |
| MAN-095 | [trigless-locks](./#trigless-locks) | 0 bound |
| MAN-096 | [quantiser-options](./#quantiser-options) | 1 bound |
| MAN-097 | [snap-note-masks-to-scale](./#snap-note-masks-to-scale) | 1 bound |
| MAN-098 | [quantise-note-masks](./#quantise-note-masks) | 1 bound |
| MAN-099 | [scales-lock-until-pattern-end](./#scales-lock-until-pattern-end) | 0 bound |
| MAN-100 | [lock-all-to-pentatonic](./#lock-all-to-pentatonic) | 0 bound |
| MAN-101 | [lock-random-to-pentatonic](./#lock-random-to-pentatonic) | 0 bound |
| MAN-102 | [lock-merged-to-pentatonic](./#lock-merged-to-pentatonic) | 0 bound |
| MAN-103 | [midi-controller-options](./#midi-controller-options) | 0 bound |
| MAN-104 | [map-scale-to-white-keys](./#map-scale-to-white-keys) | 1 bound |
| MAN-105 | [honor-scale-rotations](./#honor-scale-rotations) | 0 bound |
| MAN-106 | [honor-scale-degree](./#honor-scale-degree) | 0 bound |
| MAN-107 | [honour-scale-transpose](./#honour-scale-transpose) | 0 bound |
| MAN-117 | [screen-options](./#screen-options) | 0 bound |
| MAN-118 | [ui-motion](./#ui-motion) | 0 bound |
| MAN-108 | [sinfonion-connect](./#sinfonion-connect) | Explicit non-native scope |
| MAN-109 | [lfos-and-modulation](./#lfos-and-modulation) | 0 bound |
| MAN-119 | [musical-merge-and-voice-leading](./#musical-merge-and-voice-leading) | 2 bound |
| MAN-120 | [merge-shape](./#merge-shape) | 3 bound |
| MAN-122 | [fragments](./#fragments) | 1 bound |
| MAN-123 | [interlock](./#interlock) | 1 bound |
| MAN-124 | [structure](./#structure) | 1 bound |
| MAN-125 | [result-and-reason](./#result-and-reason) | 2 bound |
| MAN-121 | [harmony](./#harmony) | 3 bound |
| MAN-110 | [performance-management](./#performance-management) | Explicit non-native scope |
| MAN-111 | [development](./#development) | 0 bound |
| MAN-112 | [roadmap](./#roadmap) | Explicit non-native scope |
| MAN-113 | [interesting-components-for-norns-script-developers](./#interesting-components-for-norns-script-developers) | Explicit non-native scope |


## Miniature header qualification status

The README, cheat sheet and UI Motion authoring now give normative instructions for the implemented miniature header and selected-overflow exception. Temporary qualification notes are recorded here rather than in the player-facing procedure. Component and affected-UI checks passed; root reports the settled full Lua suite at 2,444 of 2,444. Actual-app miniature acceptance remains pending, so the feature's native review status stays pending. Design previews, prior captures and the 93 registered identity inventory are not evidence that 93 screens are publicly reachable. Native norns PARAMS remains excluded.

`docs/testing/vertical-list-ui/mini-header-documentary-review.json` preserves the preceding full source hashes, content-addressed archives and UI Motion excerpt separately from the normative candidate hashes. This documentation adjustment does not relabel a preview or historical framebuffer as current native evidence.

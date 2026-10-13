# Doctor UI coverage inventory

Read-only source inventory, fresh WSL `/home/andy/mosaic-manual-1.4.0`,
2026-10-03. This document adds no acceptance claims or native runs.
Current native receipts are in `manual/DOCTOR-EVIDENCE.md`.

## Current limitation and authorized next work

Manual BPM and Input are currently presentation-only: the adapter retains
draft values but Record calls `runtime:start_capture(self.capture_mode)`
without those values (`lib/rhythm_doctor/ui_adapter.lua:233,612`). README
explicitly documents this limitation. Root has since authorized full
functionality; new acceptance must fail on the old implementation, then prove
backend consumption with real PCM. The existing Manual-labelled scene proves
mode selection, not analysis at displayed manual BPM or L/R routing.

## Route/control matrix

C = canonical cases.py actual-app coverage; S = standalone actual-app recipe;
A = manual real-time public ADC acceptance; U = component/integration tests.

| Route/control | Existing actual-app evidence | Component pointers | Player-visible gap |
|---|---|---|---|
| R01 RHYTHM DR, algorithm grid/picker K3 | C M-LIVEUI-ALGO-001, M-UIACC-A18-001; S RD-UI-001; A setup | ui_adapter, app_surface, lib/tests/lib/ui_adapters_doctor_tests.lua | Canonical lane matrix |
| Setup Auto/Manual, BPM40–240, Stereo/L/R, K2/K3 | S RD-UI-002 edits Manual/127/L and discard/commit; A Manual commit | ui_adapter setup/bounds | Canonical extrema/cycle/discard/commit/transport interruption; functional BPM/Input real PCM |
| Local lane selection/reserved/inert cells | S RD-UI-001/002; A BD | bank_schema, ui_adapter, app_surface | Canonical matrix; SD/CYM musical fixtures |
| R02 CAPTURE, Record down/release | S lane retention; A direct header/K3 Finish | capture_transitions, ui_adapter, app_surface | Held release, no premature K3, second Record Finish |
| Early Finish/R03 CANCEL TAKE? | None complete | runtime duration/preflight; ui_adapter modal | MORE AUDIO NEEDED, K3 refusal, Record abandon question, K2 keep/K3 abandon |
| R04 ANALYSIS/async R05 WINDOW | A both modes | analysis_controller/runtime/transport/worker_host; route-refresh regression | Silence/failure/retry, cancel/interruption |
| R05 bar/step/R15 BROWSE, row8 press/hold/reset | S empty NOT_READY only | ui_adapter/app_surface phrase tests | Genuine READY exact increments/bounds/tooltip/reset and preview following |
| R05 sensitivity | A default BD only | runtime/ui_adapter/grid_quality | Public 0/1 bounds and selected-lane isolation |
| R05 policy/R08/R09 PAINT | A default Toggle empty destination | paint_boundaries/transactions/runtime_paint/app_surface | Add union, Replace removal, Toggle existing gates, Cancel/destination/lane/browse changes, live painting |
| R06 ALIGNMENT fields | S RD-UI-003 E3/K3 open then half-tempo refusal | ui_adapter/runtime/backend correction | Half/Double/Exact/Start Beat/Fine bounds, successful retained-audio reanalysis |
| R07 refusal | S visible refusal/retained draft/edit-dismiss/K2 | app_surface/runtime | Canonical genuine-bank reload/Save As refusal |
| R10 CLEAR BANK?/R16 CANCEL CORRECTION? | None | capture_transitions/lifecycle/ui_adapter | Held Record safety, cancel/confirm, painted patterns preserved |
| R11 STOP SEQUENCER | S same-CYM retention only | ui_adapter running gate/READY allowed | Genuine public capture/setup/alignment gate; READY remains usable |
| Transport during drafts/take/analysis | None | ui_adapter/capture/runtime lifecycle | Draft/take cancellation, cleanup, retained preview commit |
| R12 NO BANK | S empty phrase NOT_READY | core/ui_adapter/app_surface | Empty Paint/failure/retry |
| R13 BANK LANES/remote ten lanes | None | ui_adapter/app_surface/bank_schema | Native last lane reachable without fader collision/order |
| R14 SETUP LIMITS/server/fallback | None remote | remote_backend/server | Public configuration/real remote/fallback; functional BPM/Input proof |
| Save/reload/Save As/project isolation | S fabricated persisted bank reload | bank_persistence/runtime_persistence/project_lifecycle_runtime | Genuine captured-bank persistence/replayed MIDI/project isolation |

## Canonical versus standalone versus ADC

`tests/behaviour/cases.py` has general Doctor entry/navigation cases, not a
dedicated completed Doctor workflow. `rhythm_doctor.py` (RD-UI-001),
`rhythm_doctor_surface.py` (RD-UI-002), and
`rhythm_doctor_correction.py` (RD-UI-003) are standalone Driver recipes outside
the canonical exhaustive campaign.

RD-UI-003 lets Mosaic autosave, shuts down, then uses
`fixtures/inject_ready_bank.lua` to insert a fabricated bank. Its public
reload/refusal assertions are valid for that fixture, but do not prove ADC,
classification or genuine bank persistence.

`tools/manual_doctor_capture.py` and its Manual/Auto YAML sources implement
MA-DOCTOR-AUDIO-001: genuine public ADC, production softcut PCM24, local analysis,
seven strict checkpoints, exact preview/paint LEDs and MIDI/cleanup.
Both modes have native publication receipts. This is real-time deterministic
kick PCM acceptance, not general classification or physical-norns equivalence.
Controlled-time public audio capture is explicitly unsupported.

## Executable inventory

61 `test_*` files in `tests/rhythm_doctor/`, plus 3 server files:

* Lua model: core, integration, lifecycle, journal, bank_schema, bank_persistence,
  paint_boundaries, paint_transactions, assets.
* Lua runtime: capture_controller, capture_transitions, softcut_recorder,
  file_mailbox, analysis_controller, analysis_runtime, analysis_transport,
  analysis_worker_host, runtime, runtime_paint, runtime_persistence,
  project_lifecycle_runtime.
* Lua surface: ui_adapter, app_surface, dancing_doctor.
* Python infrastructure: acquisition_quality, quality, quality_report,
  grid_quality, performance, corpus, rendered_corpus_audit, analysis_worker_ipc,
  runtime_dependencies, matron_compatibility, launch_analysis_worker,
  hardware_core_runner, documentation.
* Python signal/backend: tempo_candidate, tempo_native, tempo_corpus, detector,
  nmf_template, adtof_evaluate, basic_pitch_adapter, audio_frontend,
  omnizart_onnx, omnizart_onnx_backend, pretrained_bass_backend,
  pretrained_bass_runtime, pretrained_runtime_factory,
  pretrained_composite_backend, dsp_drum_backend, native_backend,
  build_scheduled, pretrained_corpus_evaluate, remote_backend,
  bass_calibration, bass_harmonic_rf, bass_precision_operating_point,
  v11_adtof_priority_transfer, v11_priority_rf.
* Server: onsets, phrase, server.

`run_components.py` selects 24 Lua and 15 default Python suites, with optional
native/detector/corpus/server groups. Even all flags omit bass_calibration,
bass_harmonic_rf, bass_precision_operating_point, v11_adtof_priority_transfer
and v11_priority_rf.

`lib/tests/lib/ui_live_doctor_route_refresh_tests.lua` tests isolated owner
routes. Other descriptor/router tests supplement it. `test_app_surface.lua`
runs real page modules with outer doubles; `test_softcut_recorder.lua` uses
fake softcut/files including PCM16. These are not actual PCM24 capture.
Manual fixture/publisher/build/binding/audit unit tests validate evidence
machinery, not additional player workflows.

## Proposed canonical cases, not launched

* **M-RD-SETUP-001:** public setup Auto/Manual, BPM40/240 clamps, Stereo/L/R,
  atomic discard/commit and transport gate. Both UI lanes apply.
* **M-RD-READY-001:** produce/save a genuine public-ADC bank, freeze saved
  project and acquisition receipts, then copy through Driver `project_seed`
  (driver.py:32,79) into isolated sessions. No bank injection. Assert all READY
  options, bounded bar/step/phrase navigation, sensitivity0/1, policy cycle,
  preview follows browsing. Both UI lanes apply after real-only acquisition.
* **M-RD-PAINT-001:** genuine bank plus grid-entered sentinel gates; exact Toggle
  symmetric difference/Add union/Replace mask, Cancel, destination change,
  armed preview start/live commit, balanced MIDI. Both UI lanes apply.
* **M-RD-MODAL-001:** held Record prevents K3 before release, K2 clear cancellation,
  later K3 clear; bank gone, painted patterns still play. Both UI lanes apply.
* **M-RD-REFUSAL-001:** genuine bank reload with retained audio absent; Half tempo
  refusal/retained draft/edit-dismiss/K2; Save As and project isolation.
  Both UI lanes apply.
* **M-RD-CAPTURE-BOUNDARY-001:** genuine ADC earlyFinish, abandon question,
  K2 continue, held-release safety, Record Finish when enough, retry/cleanup.
  Real-time audio only; isolated UI timing supplements it.
* **M-RD-ALIGN-001:** in the same live captured-audio session, Half/Double/Exact/
  Start Beat/Fine edits then actual reanalysis; visible BPM/window/grid and
  exact MIDI changes. Reload cannot prove success because retained audio is
  deliberately dropped. Real-time only; draft-only UI can run both lanes.
* **M-RD-INPUT-001:** authorized new BPM/Input functionality: asymmetrical L/R
  PCM and requested manual BPM different from actual signal tempo. Preserve
  old-code red results, then assert captured channels/result grid/MIDI.
  Real-time only.

Every assertion cites current README or is explicit characterisation; preserve
source identities and unfixed evidence. Cleanup must leave no session, held
key, active note or changed user project.

## Discrepancies and likely defects

The original display-only Manual BPM/Input limitation has preserved native reds.
The candidate now consumes the confirmed settings: Manual uses capture-start
origin and the chosen BPM; Stereo retains separate ADC channels, while L/R
duplicates the selected ADC. Focused component tests pass. Native ManualStereo
and AutoLeft checks have passed separately; the complete seven-role current
qualification, saved READY fixture and independent audit remain pending.

The latest ManualRight run passed actual right-channel PCM, Manual100 analysis
and full-phrase MIDI, then failed at retained-alignment reentry. Reselecting
algorithm 5 is explicitly inert when it is already selected. The recipe now
reopens the existing bank through Trig Tasks > Rhythm Doctor. This corrects the
fixture gesture and preserves the original failure; it is not a production fix.

Prior confirmed route-reconciliation and 96-byte mailbox defects are fixed and
qualified in `docs/testing/doctor-route-refresh/`; historical failures do not
show a new current production defect.

Likely coverage/documentation defects:

* RD-UI-002 taps CYM when CYM is selected; retention cannot prove gating. No READY
  bank is present. Current README permits READY lane selection while playing.
* app_surface “transport-gated lane selection” stubs refusal; it proves rendering,
  not that the actual READY adapter should refuse.
* manual-inventory RD-LANES globally says three lanes/columns6–7 inert, conflicting
  with remote ten lanes; empty canonical case lists omit external evidence.
* rhythm_doctor.py still says proposed/intentionally red; surface says Four lanes.
* documentation.py literal unconfigured-backend wording is not runtime evidence.
* **Historical ledger labels:** DOCTOR-EVIDENCE.md sentences “remain unverified”,
  “stays red”, “No successful Doctor scene” and “three tests” describe attempts
  before its final Complete native qualification section. Its leading status
  and final receipts supersede those historical pending statements. This
  document labels their time scope without editing the ledger.
* MA-DOCTOR-AUDIO-001 cites frozen legacy README; it does not certify every later
  current READY or remote control.

No other current production failure is proven by this inventory.



## Authored READY fixture/recipe gesture-route audit

The staged source explicitly follows ordinary task entry after routes that
leave the Doctor. This audit does not claim native qualification.

| Block/gesture | Declared route | Next Doctor action |
|---|---|---|
| Global Channel G01, pattern assignments, range | C01/C02 or merge feedback | No Doctor fields during channel playback |
| Global Pattern G03 from Channel | P01 Trig, selected PAT/CH | Assert exact P01; Pattern tasks > Rhythm Doctor opens R05 |
| READY destination top row G20 | P01 on selected pattern; cancels stale preview | _destination records P01 frame, then explicit task opens strict R05 |
| Grid step edits G21: policy sentinels | Hold temporarily follows P01; hold.end restores original R05 | Exact returned R05/frame; no task reopen |
| Grid step edits G21: clearing acquired P3 | Hold temporarily follows P01; release restores R05 | Exact returned R05; subsequent G20 destination has its separate explicit task reopen |
| Play/Stop G38 | Retain current workspace | READY playback retains R05; clear-bank playback retains EMPTY R01; channel fixture playback stays Channel |
| Transport owner reconciliation G43 | READY R05 or armed preview R08; EMPTY playing R11 | Fields checked on their declared owner routes; no implicit task gesture |
| Lane G41, no preview | READY R05 | Public E2 selects Sensitivity on R05 |
| Browse tap/hold/reset | Browse feedback, then owner WINDOW R05 | Tooltip asserted before selecting Window step; no painting is armed in browse block |
| Paint arm/commit/cancel G42 | Armed R08; committed/cancelled READY R05 | Strict R05 field selections; destination changes explicitly route through P01 |
| Record occupied modal/K2 | R10 then READY R05 | Held-release assertion and explicit R05 after cancel |
| Alignment open/refuse/edit/K2 | R06 / R07 / R06 / R05 | Exact route/value checks, no generic fallback |
| Confirm clear | EMPTY R01 | Painted grid/MIDI remain; no READY field selection follows |

Same-algorithm 5-to-5 is deliberately inert in ui_grid_outcomes.lua. Only initial
1-to-5 entry is used to enter Doctor; returns from other pages use its public
Pattern task. _select never silently reopens a Doctor route.


### Held-step lifetime correction

The first route audit above originally omitted global held-step return lifetime.
Immutable native run 6a86 reached full64 MIDI/release then exposed that omission.
The independent executable presentation model confirms R05 -> hold.begin(R05)
-> G21(P01, invalidates_return=false) -> hold.end(R05). G20 without a step-hold
frame remains P01. Durable test_doctor_ready_routes reproduces the old observer
failure and verifies the corrected exact return without additional navigation.
Red/green source identities are preserved under docs/testing/doctor-held-return/.
Other held gestures were rechecked: row8 phrase holds are not sequencer-step
holds and have no step return frame; Record claims its pre-press and has its
own modal/release lifecycle; range setting on Channel returns to its original
Channel workspace; destination top row is never a sequencer-step hold.

# Rhythm Doctor evidence

Current status: Manual and stock Auto capture workflows each pass seven strict
native checkpoints and independent publication audit. The published collection
contains fourteen actual native frames, exact preview-to-paint grid checks,
bounded MIDI playback and cleanup. Both diagnosed Mosaic fixes have preserved
red evidence and passing regressions. The independent emulator is unchanged.
This evidence covers the stated deterministic software audio fixture; it does
not establish physical-norns timing or general recording classification quality.

The stock analysis path is local. `mosaic.lua` creates the softcut recorder and
analysis worker; `lib/rhythm_doctor/analysis_worker_host.lua` builds the shipped
C backend and uses its pinned drum templates when no alternative is configured.
The server is an optional advanced setting. No server is required for this fixture.

`tools/manual_doctor_capture.py` exercises the actual application through public
grid, norns key/encoder and emulator audio-input APIs. A deterministic stereo
kick pulse train is test input, rather than a musical guide audio asset. The
fixture records through production softcut, finishes recording with K3, waits
for local analysis, previews the BD lane, commits it to pattern 1 and plays that
pattern through a selected MIDI output. It asserts the Listening, Analysing,
Window and Paint screens, exact preview/committed trig locations, and emitted
MIDI attacks. It preserves the actual input WAV, captured WAV, local backend
result, application/runtime identities, public input trace and cleanup report.
A passing result is required before the workflow is marked verified.

The real-time audio lane is applicable. The public identified audio helper feeds
crone ADC inputs 1 and 2; the production softcut recorder reads those inputs.
This demonstrates software capture and processing with seeded PCM. It does not
measure microphone/interface hardware, acoustic classification quality, or
physical-norns scheduling.

The controlled-time audio lane is inapplicable: the emulator public capture API
rejects controlled-time sessions, and softcut and local PCM processing depend on
real audio time. Controlled-time UI entry/setup remains independently applicable.
Existing pure Lua tests cover state-machine boundaries, stale analysis replies,
paint transactions, persistence and cleanup. Existing native-backend tests cover
signal detection and source/template identity. These component checks supplement
the real-time actual-app workflow and do not replace it.

Native runs use `/tmp/mosaic-manual-native.lock` for the whole session. The
fixture copies its application sources before starting the runtime, preserves
failed runs separately, releases input and active notes, and closes its native
session. `tools/manual_doctor_audit.py` independently verifies input PCM,
production captured PCM and local backend identities. The publication auditor
also verifies framebuffer/grid bindings, public input delivery and cleanup.

## Preserved failed acceptance

The first Manual-tempo actual-app attempt is
`/home/andy/mosaic-manual-runs/8388eab2017e48fda54e811f8758af55/report.json`.
The paced key/Record retry is
`/home/andy/mosaic-manual-runs/0e3580d2f5244560bb6aa5c81eb4f738/report.json`.
Both reached the setup screen, then failed the expected CAPTURE header after
Record. Both shut down cleanly. Their failing results and frozen source/YAML
remain immutable. They do not verify capture, analysis or painting.

Source review identifies a display reconciliation gap. `ui_live.lua` reconciles
Doctor-owned routes before and after input dispatch, but `view_model()` and
redraw do not reconcile them. Doctor Record claims its grid press in
`m_grid.pre_press`; that path removes the claimed key and skips the ordinary
short-press grid outcome. Asynchronous completion also changes the owner without
an input dispatch. A stale displayed route can therefore explain the failed
header. The separately labelled diagnostic below tests the Recording part of this
inference. The later asynchronous Ready-display part has not been reached in
valid acceptance.

The diagnostic wrapper adds status logging only to an isolated copied
entrypoint. It is outside unchanged-application acceptance, is labelled with
`diagnostic-only.json`, and is refused by the independent audio publication
auditor. The separate stock Auto-tempo actual-app attempt below distinguishes
setup confirmation from the capture path. No extra refresh gesture has been
added to satisfy a failed header expectation; the direct Record checkpoint
remains required.

## Diagnostic outcome

The read-only diagnostic finished in
`/home/andy/mosaic-manual-runs/bbde80eae2584ef9aa1b80058c2d4e90/`.
Its preserved matron log shows `state=RECORDING`, `setup=false` and
`controller=true` after Record. The visible CAPTURE header still failed, and
shutdown succeeded. This confirms that the owner advanced while the displayed
route remained stale; it rules out an unconfirmed setup draft as the cause of
this attempt. The status logging changed an isolated copied entrypoint, so it
remains diagnostic evidence and is explicitly refused as feature acceptance.

This evidence does not establish completed PCM capture, local classification,
a READY bank, painting, or emitted MIDI. Those checkpoints remain unverified.
The direct visible Record-status assertion stays red. A display-refresh gesture
has not been added solely to obtain a passing result. The source-level
asynchronous Ready-display reconciliation gap remains a separately identified
inference until that stage is reached through valid acceptance.

## Stock Auto outcome

The unchanged-application Auto attempt finished in
`/home/andy/mosaic-manual-runs/ac19906c83cd457eae1f0804bca4c2a6/`.
It also reached setup, then failed the direct CAPTURE header after Record,
with clean shutdown. The native Record LED stayed at level 15, which the
production page defines as `worker_ready`; level 4 means not ready. This
supports recorder availability while preserving the visible-status failure.
No successful Doctor scene has been published or marked verified.

The helper/schema-focused checks pass three tests: exact deterministic stereo
input geometry/headroom/pulses, source schema acceptance with private-state
operation rejection, and rejection of failed reports by the publication auditor.
These checks validate the fixture boundary rather than the user workflow.
The next implementation decision concerns the existing live UI's route
reconciliation; it is outside this documentation-only evidence pass. Teaching
review may also identify a legitimate natural lane-selection step, but that
cannot erase or relabel the separate direct Record-status failure.

## UI conversion candidate and mailbox boundary

The candidate Manual attempt is
`/home/andy/mosaic-manual-runs/bb4c17d52a43490698a1d066aeef8cfb/report.json`.
Its setup, Record-to-CAPTURE and finish-to-ANALYSIS assertions passed. The READY
header timed out, and cleanup succeeded. The original report, frozen source and
actual softcut recording remain preserved; this is partial evidence and cannot
be published as a complete workflow.

The worker published the 99-byte absolute file-mailbox root
`/tmp/norns_emu_9f715791ca8b4169b697d0579a4fa751/dust/data/mosaic/rhythm-doctor-analysis-runtime/ipc`.
Mosaic's file-mailbox validator rejected roots longer than 96 bytes. The worker
therefore remained unclaimed and exited after its claim timeout. This is a
Mosaic path-compatibility failure; it does not establish a remote-service
requirement or an emulator audio-input limitation.

The live UI now reconciles owner routes before building the screen model, so
claimed grid presses and analysis callbacks do not require another gesture.
Two isolated owner-route regressions fail against the frozen original source
and pass after that change; a non-Doctor screen remains unaffected. Native
CAPTURE and ANALYSIS corroborate the capture-route correction. The asynchronous
READY stage still requires a fresh full native pass.

The file-mailbox fix checks the complete temporary message filenames against
Linux's 4095-byte pathname budget (4096 including the terminating NUL), using
both actual direction names and the nine-digit message plus `.msg.part` suffix.
Absolute-root, trailing-slash, control-byte and direction-layout checks remain.
The observed native root, exact full-filename boundary and longer direction
boundary all fail on the frozen unfixed source and pass on the candidate;
invalid-path controls pass in both. Existing mailbox coverage passes 34 checks.
Affected transport, host, analysis-controller and runtime checks also pass.

Component source inventories and red/green logs are under
`docs/testing/doctor-route-refresh/`. No Auto candidate follows until Manual
passes its complete strict native workflow. Controlled-time audio capture stays
inapplicable for the public API reason recorded above.

## Complete native qualification and publication

Manual:
`/home/andy/mosaic-manual-runs/ea67eb71b9f94235b71220fe63ed0be2/report.json`
(report SHA256 `387696b6248a46f1a98540fef3c134c5ded6ad95edd8f47d348d694afaab13d3`).

Stock Auto:
`/home/andy/mosaic-manual-runs/7141a7813c384e79aaba01111624c6e6/report.json`
(report SHA256 `104770e1f996faba2703df3cd1f2a4062da9521c8cece862f6a0b2fa0b6cf6a6`).

Both original reports pass setup, direct CAPTURE, ANALYSIS, asynchronous WINDOW,
BD preview, exact committed trig locations and painted MIDI playback assertions.
Each native session closes cleanly. The independent audit verifies current and
frozen application/recipe/YAML identities, full delivered public input traces,
semantic assertion ordering before frames, exact rendered route/footer feedback,
empty/preview/committed grids, bounded native MIDI packets and zero outstanding
notes. Both local analysis artifacts contain 48 BD candidates with pinned native
source/template identities. Production softcut recordings are stereo 48 kHz
signed PCM24, over 25 seconds, with nonzero RMS; completed analysis envelopes bind
the exact recording SHA256 and frame count. Detached workers are inactive.

`manual/generated/doctor-scenes.json` is an exact concatenation of those immutable
reports' distinct authored Manual and Auto scenes. Its receipts preserve both raw
report hashes. `manual/features/scenes-doctor-scenes.yaml` provides derived scene
bindings to the two authoritative input sources. It validates against
`manual/doctor-bindings.schema.json`. The publisher passes its independent native
collection audit before writing either file; failed qualification cannot replace
a publication. `tools/manual_doctor_publish.py` is dry by default and requires
`--publish` for writes. It is separate from the capture recipe, so qualification
identities remain unchanged.

Rebuild each mode with `tools/manual_doctor_capture.py --source
manual/doctor-scene.yaml` or `--source manual/doctor-auto-probe.yaml`, passing the
identified audio installation and output root. Each command owns the whole-run
native lock and prints its immutable report path. Then run
`tools/manual_doctor_publish.py --manual-report <Manual/report.json> --auto-report
<Auto/report.json> --publish`. The publisher refuses stale source identities.
Controlled-time PCM acceptance remains inapplicable for the public API reason
above; no controlled or physical-hardware audio result is implied.

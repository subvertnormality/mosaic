# Rhythm Doctor implementation checkpoint

Base: `codex/behaviour-validation`, `8c08cb93d9f5a4cc36488e90517043531446a4f7`.
Work branch: `codex/rhythm-doctor`.
The user authorized implementation on 2026-09-19, superseding the planning-only
status in the preserved proposal. PLAN.md is an unchanged copy of the proposal
from the adjacent monome-emulator workspace.

## User scope amendment (2026-09-19)

The user prioritised BD, SD, HH and BASS and explicitly allowed TOM to be
deprioritised if it is not working. These four lanes are required for this
implementation; TOM is optional and must not block their delivery. An unreliable
TOM detector must not be presented as a working lane. The preserved PLAN.md and
historical five-lane reports remain unchanged. The four required lanes retain
every existing accuracy, negative-control, velocity, timing, persistence and
physical-Norns acceptance requirement. Dropping TOM alone does not make the
current candidates pass. New score reports must explicitly name their scope.

## Status

RD-01/RD-02 in progress. No delivery card is complete. No product UI or standalone
transcription capability is claimed. Source bank foundations can be developed
independently but must not bypass the RD-02 empirical gate for integration.

The baseline full Lua suite completed with 1,701 successes, zero failures, in
27.589 seconds. Its log is evidence/lua-baseline.log. The surrounding shell
wrapper returned 1 because its exit-status forwarding was empty; this is a
harness error after the Lua runner printed OK, not a Lua test failure. Do not
present the wrapper as a successful command. Later runs must use reliable exit
propagation. No production changes existed at this baseline.

## Source integration map (RD-01 audit, not acceptance)

- `lib/pages/trigger_edit_page/trigger_edit_page.lua`: four algorithm IDs use
  fader x=12..15,y=2. Add a separate enum-5 button at x=16,y=2; expanding the
  proportional fader would change existing IDs. Existing paint writes trigs and
  lengths but no velocities; source update fans out to referencing channels.
- `lib/m_grid.lua`: key-down registers the held key and long-press timer;
  ordinary short presses dispatch on release. Claim only RD Record before this
  path, keep release ownership across page changes, and clear ownership on
  disconnect. Transport controls remain outside RD modal ownership.
- `lib/ui.lua`: trigger UI receives encoders but its key dispatch is commented
  out. RD K2/K3 dispatch requires explicit routing while preserving K1 semantics.
- `lib/project_lifecycle.lua`: save stops and resets transport before serialization.
  Capture inhibition must occur before this call; autosave needs one deferred
  flag and project replacement must discard the old flag.
- `lib/pattern.lua`: `update_source_working_patterns` propagates source data.
  Journal revisions must cover all source edits, including note/velocity edits,
  copies and history, not only this trig editor.
- `lib/clock/m_clock.lua`: transport preparation is the synchronous invalidation
  boundary; worker cleanup must not block Start.

## Environment and hardware observations

Commit `eb979ec` was exercised on physical Norns (`Linux armv7l`, Lua 5.1.5).
The first isolated core run preserved a red report after exposing dependencies
omitted by the hardware runner. After adding those files and disabling the
device-global `include` path for isolated tests, all 17 component groups passed
with exact deployed hashes in `hardware-core-eb979ec-v2.json`. The production
capture launcher/AF_UNIX transport and the three-trial JACK capture probe also
passed with cleanup and route restoration in
`hardware-launch-worker-eb979ec-v2.json` and
`hardware-capture-eb979ec.json`. The first launcher attempt remains in
`hardware-launch-worker-eb979ec.json`: the long-running JACK process had lost
its shared-memory socket. Restarting JACK and its dependent norns services
restored client connectivity before the passing retry. These runs do not supply
pretrained-model quality, latency, RSS, or full-feature acceptance.

The same production revision passed the basic and ownership/setup application
recipes in both real-time and controlled emulator lanes. Their four manifests
are named `mosaic-rhythm-doctor-{ui,surface}-eb979ec-{realtime,controlled}.json`.

Ubuntu-20.04 WSL has Lua, Python, GCC, JACK and libsndfile; Ubuntu is a separate,
less-equipped distribution. Norns was reachable through an existing authenticated
SSH control socket. Its architecture is armv7l; JACK 1.9.17 and libsndfile 1.0.31
are installed. No active test ownership marker was observed. A read-only JACK
port inspection found physical capture_1/2 connected to crone input_1/2. No
connections, scripts, device files or runtime settings were changed by this audit.
An independent input-only client will be tested before selecting capture ownership.

Device observations are not capture performance or transcription-quality evidence.

## Native UI baseline evidence

`RD-UI-001` starts the actual frozen Mosaic base, presses the four existing
algorithm positions and then (16,2), and requires the literal RHYTHM DOCTOR
framebuffer header. Both real-time and controlled-time baseline runs failed at
that missing user-visible output. Both completed cleanup without an error.
Source identities and recipe hashes are preserved in:

- evidence/mosaic-rhythm-doctor-ui-red-realtime-02.json
- evidence/mosaic-rhythm-doctor-ui-red-controlled.json

The first real-time attempt had an oracle setup KeyError because the shared
header helper recognizes only existing titles. It remains separately preserved
at /tmp/mosaic-rhythm-doctor-ui-red-realtime and is not counted as feature-red
acceptance. The corrected recipe renders the proposed literal title directly
using the independent norns font primitive. No oracle was weakened.

Current pure metric tests: 6 onset/velocity, 8 performance, 5 per-domain quality.
Their green results prove the evaluators, not transcription quality or hardware
performance. The performance report explicitly does not authenticate raw device
evidence; the release campaign must verify that separately.

## Component hardware results and source-revision integration

The frozen native capture passed three physical-Norns owned-JACK-injection
trials; see evidence/hardware-capture-mosaic-rd-probe-d02976ca26f44569a0a6d2f22ab752e6.json.
Each preserved stereo sample continuity and the original JACK routing. PCM buffers
were memory-locked. Native preflight cost 148–163 ms (mode-entry work); arm to first
observed PCM was 1.26–1.49 ms using polling, not a grid-key timestamp. ADC ingress,
Mosaic UI integration, transcription, and full-feature performance are untested.
The measured process peak RSS includes Python/JACK/shared runtime overhead and
is not the feature's incremental-RSS acceptance measurement.

The optimized immutable-bank scroll benchmark was also run on physical Norns:
22,500 candidates, 720 timeline cells, 100 five-lane scrolls per trial. Across three
trials, CPU p95 was 3.97–4.39 ms; maximum 14.78–15.47 ms. Building that largest bank
cost 653–662 ms of Lua CPU, so app integration must not call it synchronously on
the UI event thread. These timings do not measure screen response or model work.

The source revision module and its integration into `pattern.lua` have 6 passing
new unit/integration tests, with missing-module/missing-hook failures preserved.
The complete Lua suite after this production hook passes: 1,707 successes,
zero failures, 31.485 seconds. Evidence: lua-source-revision-candidate.log.
Revisions are session-only, do not alter saved project fields, and change on
explicit source edits and replacement source/song identity. Full input-path
coverage for every editor remains required before paint integration.

## Feasibility review cautions

The first detector pilot result is not reliable quality evidence: it compared
20-second predictions with whole-song references and emitted framewise positives
as duplicate onsets. It must remain labelled an invalid evaluation harness;
corrected runs must retain separate identities. It does not establish that the
architecture fails the quality gates.

The first tempo pilot candidate logic similarly cannot establish detector
feasibility: it incorrectly required three consecutive beat callbacks to span
four seconds and treated 15 beat intervals as a 16-beat region. Corrections need
acceptance fixtures for valid acquisition as well as uncertainty cases. Passing
characterisation tests of an always-uncertain prototype are not Auto acceptance.

## Further component checks (2026-09-19)

All four legacy algorithm tooltips now have exact actual-framebuffer assertions
before the fifth-mode assertion. Both time lanes passed the legacy checks and
failed at the expected missing fifth title; cleanup succeeded. The separate
`mosaic-rhythm-doctor-ui-red-legacy-*` manifests preserve these runs.

Nine focused source-revision tests now cover actual trigger tap/length/legacy
paint, note and velocity editor callbacks, including parallel edits, plus copy
and identity boundaries. Source-revision-only tests do not substitute for the
future undo UI/MIDI acceptance.

The resource lifecycle now inhibits saves until release acknowledgement, preserves
an in-flight release token through project replacement, and refuses destructive
modal confirmation without explicit stopped transport. Four failing regressions
were preserved before the fix. Pure core/integration/lifecycle tests also passed
on physical Norns with deployed hashes in hardware-core-lifecycle-v1.json. That
report predates the subsequent journal/schema/paint hardening; it does not certify
those later changes.

The journal now starts a fresh stack when ordinary editing occurred before a new
paint, preventing a second Undo from jumping over that edit. Fourteen malformed
bank cases are rejected before READY. The paint matrix checks each of 64 cells,
all policies, numeric/boolean adapters and shifts; its current measured result is
5,433 assertions. Independent performance validation now rejects buffers too
short for four bars and requires both short/full-buffer measurements, scoring
latency percentiles separately so one duration class cannot hide another's failure.

The full-development spectral classifier pilot used all nine development songs
(182–314 seconds each) with 420 TOM references, then fixed 60-second diagnostic
holdouts. F1 was BD 0.7283, SD 0.5457, HH 0.7034, TOM 0, BASS 0.5610. All fail the
0.80 onset gate. This is evidence against that frozen candidate, not proof that
all possible local architectures fail. It is not pristine final acceptance data.
No UI, persistence, standalone transcription or complete release is claimed.


The global paint-history bound is now enforced across all targets, with a
session-wide token generation preventing reuse after eviction. The new regression
failed before the change; all six pure suites pass on physical Norns in
`hardware-core-global-journal-v4.json`. The actual-application existing
`M-PAT-BOUNDARY-001` passes in both timing lanes on frozen commit `6dff846`;
this covers the source-revision hook without claiming a Rhythm Doctor UI pass.

The corrected frozen corpus v11 passes inventory/provenance and independent PCM
fixture audits (40 development, 66 held, seven acquisition clips). No detector
has been scored on it. Two diagnostic transcription candidates miss the quality
gates; pretrained drum/bass architectures are still under investigation. Total
Windows process working set is not incremental RSS or ARM device evidence.


Checkpoint component runner: 16 selected groups pass, with unchanged source hashes
through the run (`component-checkpoint-v2.json`). Detector unit tests are separate
Windows checks: three classifier tests, three NMF selection tests and one ADTOF
label-adapter test pass. The ADTOF and UMXHQ pretrained diagnostics remain in
progress and are not shipping classifiers. The official UMXHQ Zenodo weight
record explicitly declares MIT (`umxhq-official-license.json`), resolving the
earlier research note's license uncertainty.

The original acquisition evaluator draft's abbreviated red/green report is not
reliable acceptance evidence. Independent audit reproduced four failures and
three errors, retained with actual source hashes and raw output in
`acquisition-independent-audit-red.json`. The corrected ten-test evaluator checks
16 complete intervals, full-span beat phase, control failures, explicit eligible
identities, uncertainty labels and numeric bounds. It is an independent scoring
component, not measured acquisition success.


Draft PR #97 is open against `codex/behaviour-validation`. At commit `5b4bf10`,
local full Lua tests pass (1,710 tests, zero failures); CI run 35418429234 also
passes all 1,710 Lua tests and 19 component/native groups. The application feature
remains incomplete. A repeat physical-Norns capture probe verifies the committed
native source bytes, three contiguous stereo acquisitions, restored routing and
successful cleanup (`hardware-capture-checkpoint-5b4bf10-v2.json`). The first new
launcher attempt failed because relative library paths were resolved incorrectly;
its failed report is preserved, and it is not capture-quality evidence.

## Project-save guard integration groundwork

`project_lifecycle.new` now accepts an optional capture-machine guard. It checks
manual/autosave permission before ordinary save can stop/reset transport or
serialize the project. Three integration regressions execute the actual Mosaic
entrypoint closures with the real capture state machine: all four active states,
coalesced requests until asynchronous release, release during playback, and
old-project deferred-request discard. Transport and IO are observed test doubles;
this is not sounding-n.b., contiguous-PCM, or public-input acceptance. The
application controller still needs to supply this guard and wire release/Stop
callbacks. The following checkpoint extends the optional guard to load/new;
production controller wiring and project identity assignment remain outstanding.

The failing pre-hook source and test hashes and actual output are preserved in
`evidence/project-save-inhibition-red.json`; the three focused regressions pass
after the hook. This does not complete RD-03.

The complete local Lua suite now passes 1,713 tests with zero failures and an
observed subprocess exit code of 0. `evidence/full-lua-lifecycle-v2.json` freezes
all tracked Lua source hashes and confirms no source changed during the run.
An earlier run printed 1,713 passes but its shell wrapper lost the exit status;
it is not counted as a successful command. The direct subprocess rerun fixes
that evidence gap. Seven quality-profile and four NMF-isolation tests also pass.

## Project replacement release checkpoint

The optional lifecycle guard now validates a load before cancelling capture,
then defers load/new side effects until owned resources are released. It keeps
only the latest valid replacement request, discards the old project's deferred
autosave, and drops the continuation on cleanup. Synchronous release and
reentrant state/release callbacks cannot run an obsolete continuation; throwing
continuations are removed before invocation and cannot replay.

Three actual-lifecycle integration regressions demonstrate these boundaries;
`evidence/project-replace-release-red.json` preserves two expected pre-fix
failures and the already-passing invalid-load case. The complete local Lua suite
passes 1,716 tests with exit code 0 and unchanged source hashes
(`evidence/full-lua-project-release-v1.json`). All six pure core groups pass on
physical Norns, including seven lifecycle cases
(`evidence/hardware-core-project-release-v1.json`); deployed hashes match and
runner cleanup completed. This evidence covers the protocol, not public PCM/UI
acceptance. `mosaic.lua` does not yet construct a capture controller or supply
this guard. Controller wiring, release timeout handling and new/loaded project
identity assignment remain required before RD-03 can be accepted.


## Priority-lane and compatibility checkpoint

BD, SD, HH and BASS remain required; TOM is optional. The corrected BASS
random-forest diagnostic excludes declared stems whose MIDI is missing instead
of labelling them as negatives. Its validation-only threshold achieved 0.8469
validation onset F1 and 0.7511 on the reused diagnostic held set, below the 0.80
gate. These are not final corpus or device acceptance results. The prior models
remain identified as trained with incomplete label provenance.

At commit 6176544, CI run 35421547048 passed. The actual application pattern
boundary regression also passed in real time and controlled time on a frozen
6176544 source snapshot, with literal emitted MIDI expectations, unchanged
source hashes and successful session cleanup. See
`evidence/project-release-boundary-checkpoint.json`. This is compatibility
evidence; it does not exercise the unfinished Rhythm Doctor interface.


## Capture completion protocol checkpoint

The state machine now rejects stale capture failure/timeout notifications,
invalidates pending modals, and moves failed acquisitions to FAILED while
waiting for actual resource release. A timeout without a valid span enters
ALIGNMENT_REQUIRED; later analysis waits for release and takes a new resource
lease. A valid timeout starts analysis only while its original token still
owns the state, including when a state callback synchronously starts transport.
Nine focused cases and all seven pure Lua groups pass on physical Norns with
matching source hashes (`evidence/hardware-capture-transitions-v1.json`).
The missing-method and reentrant-cancellation failures are preserved separately.
These transitions still require the asynchronous controller and actual capture
worker integration; they are not end-to-end audio acceptance.

## Owned capture worker and first clean held evaluation

The controller now uses complete project/generation/analysis identities and a
nonblocking transport contract. A native worker owns its private Unix seqpacket
socket and JACK input ports, rejects malformed or stale commands, publishes a
fixed owned WAV name atomically, acknowledges release only after destroying the
capture client, and removes its exact temporary root on disconnect or exit. An
isolated JACK integration executes the real state machine, LuaJIT transport,
controller and worker from Manual capture through contiguous stereo PCM,
publish, injected analysis failure, resource release and cleanup. This is host
integration evidence; `mosaic.lua` still needs to launch and schedule the
controller, bind controls, and persist the worker WAV as a project asset.

The first untouched v11 held evaluation froze its development-selected epoch,
thresholds and phase-safe frontend before opening the 66 held clips. Independent
hash-checked scoring reports onset F1 of 0.499 BD, 0.469 SD and 0.774 HH; grid F1
is 0.499, 0.469 and 0.775 respectively. All miss the required gates except the
silence controls, which emit zero false positives. The corrected audit is
`evidence/candidate_b_adtof_v11_independent_v3.json`. Earlier v1/v2 grid
derivations are identified as invalid or unverified configurations and are not
acceptance evidence. No held threshold tuning was performed.

Project-owned WAV storage now validates the native float32-stereo format,
content address, project binding and complete 45-second bound. It uses exclusive
staging/publication and file/parent durability barriers, rejects partial or
corrupt assets, and never resumes a partial capture. The production filesystem
adapter and lifecycle serialization wiring remain required.

## Frozen v12 pretrained quality result (2026-09-19)

Branch rebased onto `main` (`5384d0b`); the previous base `codex/behaviour-validation`
`8c08cb93` merged through PR #94 and `origin/main` has a byte-identical tree, so the
rebase changed no file content. PR #97 already targets `main`.

**The pinned pretrained candidate fails RD-02 and is not a shipping detector.**
Fourteen of fifteen lane/stratum domains miss both the 0.80 onset and 0.85
quantized-cell gates; only CHH/full_mix passes at 0.8874. Velocity MAE fails for
every lane and the gain ladders are not monotonic. See
`evidence/pretrained-v12-quality-2026-09-19.json` and
`evidence/pretrained-v12-failure-diagnosis-2026-09-19.json`, and DETECTOR.md for
the per-domain table.

Held-out recall/precision: BD 0.667/0.643, SD 0.657/0.600, CHH 0.899/0.727,
OHH 0.339/0.176, BASS 0.314/0.502. The dominant cause is cross-lane leakage:
the share of false positives arising on clips where the lane is absent is
CHH 62.1%, SD 49.4%, BD 45.1%, OHH 21.2%, BASS 0.9%. OHH collapses outright at
189 true positives against 884 false positives.

Three alternative explanations were tested and rejected, so the failure is not
an evaluation artefact. There is no systematic timing offset (a -10 ms
difference well inside the 50 ms tolerance). Gate selection is not at fault: an
oracle threshold fitted directly on held-out data, used only as a diagnostic and
never for a reported score, still leaves BD at 0.6684, SD 0.6367, OHH 0.2886 and
BASS 0.4863. Beat tracking is not degraded on the worst strata either: derived
bpm is correct on 10/10 isolated and 41/41 full-mix held-out clips.

No gate was weakened, no class relabelled, no held-out tuning fed a reported
score, and no model was trained or replaced.

### Production defects found and fixed by this evaluation

The run aborted twice on real defects, each fixed red-green with a preserved
failing regression.

1. A digitally silent capture crashed the drum frontend. madmom's tempo estimate
   degenerates on an all-zero buffer, escaping as `OMNIZART_FRONTEND_FAILED` and
   leaving the absent-lane controls unscorable.
2. The guard then had to move from the interleaved buffer to the mono downmix,
   because the frontend loads audio with `mono=True` and an exactly
   phase-inverted stereo capture cancels to silence. Held-out clip `v12-phase`
   peaks at 7964 interleaved and is exactly zero in mono.

Across all 113 clips exactly four take the silent path — the three silence
controls and `v12-phase`, all held out — so development gate selection is
unaffected and no audible mono signal is suppressed. The pinned drum weight is
still verified on that path so silence cannot bypass the artifact pin.

### Physical Norns

All 17 Lua component groups pass on the device at the rebased commit with
verified deployed hashes (`evidence/hardware-core-silence-guard-892a3ad.json`).

The device cannot currently run the pretrained chain at all. It has no numpy,
no pip, no onnxruntime and no torch, and no internet: its only route is an
isolated 10.42.0.0/24 hotspot, so every dependency must be staged from a host.
numpy 1.19.5 from the official Debian armhf package and an UNOFFICIAL community
armv7l onnxruntime 1.16.0 wheel were both loaded from a removable /tmp tree, the
latter reporting `CPUExecutionProvider`. That is the first direct evidence an
ONNX Runtime binary loads on this Norns; it is not evidence that any pinned
graph runs. See `evidence/norns-onnxruntime-runtime-probe-2026-09-19.json` and
`evidence/armv7-onnxruntime-availability-2026-09-19.json`.

Microsoft has never published an armv7l ONNX Runtime binary for any version, and
cp39 wheels stop at 1.19.2. Desktop peak RSS was 383,268 KiB for eight seconds of
audio and 891,800 KiB for the corpus process, against roughly 469 MB available
and zero swap on the device for a 45-second target. Norns inference memory,
latency, xruns and cancellation remain UNMEASURED and must not be inferred from
x86 numbers.

## Scope and constraint decisions (2026-09-19)

The user set these after reading the v12 result. They change what RD-02 must
deliver and should be treated as current scope.

**Norns must work standalone.** Off-device or host-assisted analysis is
rejected. Analysis must run on the device, within roughly 470 MB of available
RAM and no swap, on armv7l.

**OHH is descoped**, following TOM. BASS is explicitly a higher priority than
OHH and is required.

**BD 0.702, SD 0.687 and CHH 0.887 are acceptable** as measured on the held-out
full-mix stratum, which is the stratum that resembles a real capture. Better is
wanted, but these do not block delivery. This is a user scope decision, not a
weakened gate: `quality_report.py` still applies 0.80/0.85 and still reports the
candidate as failing.

**Training is permitted** if it beats the pretrained alternatives. It remains
contraindicated on currently available rendered data — see CORPUS.md.

**Rhythm Doctor targets real music**, not isolated drum parts or drum-machine
patterns. See the domain-mismatch section in CORPUS.md: v12 is not a sufficient
acceptance gate for that target, and a real-music evaluation set is required
before the next candidate decision.

### Consequence for the architecture

Separation-first was the natural answer to the measured cross-lane leakage, and
for real music it remains the right architecture. It is blocked on device
footprint rather than on quality or licence: every drum separator found is
320–562 MB of weights before runtime, and LarsNet is additionally unusable
(CC BY-NC 4.0 weights, and no licence file at all on the code).

One avenue was dismissed too early and is not yet measured. Demucs is MIT,
including its weights, and is materially stronger than UMXHQ on bass. Its widely
quoted 3–7 GB requirement is for whole-track processing, but it processes in
segments and the hybrid-transformer models cap the segment at 7.8 s, so peak
memory should scale with segment length rather than capture length. On a Norns,
analysis time is cheap and memory is not: a 45-second capture may take minutes
without harming a stop-transport capture-and-paint workflow. **Measuring peak
RSS for segment-bounded Demucs is therefore the next experiment**, and it is the
most direct route to the required BASS lane.

### BASS is recoverable

The lane fails on discrimination, not blindness. With the decoder floor at zero,
596 of 732 held-out BASS references are matched, a recall ceiling of 0.8142
against an actual 0.314, while the detector offers 2842 candidates — roughly
fourfold over-generation whose confidence does not separate true from false.

Kick bleed is not the dominant cause: of 3041 false positives, 39.5% coincide
with an annotated drum onset and 60.5% with nothing annotated. Note that v12
deliberately leaves toms and pedal hats audible but unlabelled, and toms are low
and pitched, so some of those are scored as BASS errors by construction. See
`evidence/bass-lane-ceiling-analysis-2026-09-19.json`.

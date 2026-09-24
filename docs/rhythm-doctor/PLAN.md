# Rhythm Doctor — audio to five paintable rhythm lanes

Status: design proposal, 2026-09-18. Third musical feature plan alongside Musical
Merge and Harmony. Implementation is not authorized by this planning request.
Target: the existing Mosaic pattern/trigger editor and official norns runtime.
User amendment: Rhythm Doctor operates only while Mosaic's sequencer is stopped.
Incoming audio may continue playing from an external source during capture.
Automatic tempo acquisition and a scrollable four-bar window over a longer
captured rhythm timeline are the default,
following the user's subsequent amendment. The previous Paranoia review predates
this amendment; see the review record for its exact coverage.
Review evidence and dispositions: `evidence/rhythm-doctor/` and
[RHYTHM-DOCTOR-REVIEW.md](RHYTHM-DOCTOR-REVIEW.md).

## Scope amendment — 2026-09-19

The active Rhythm Doctor lanes are **BD, SD, CHH, OHH and BASS**: bass drum,
snare drum, closed hi-hat, open hi-hat and pitched bass attacks. This amendment
supersedes every unqualified earlier PLAN lane list and coordinate assignment.
`HH` is no longer an acceptance lane: it may appear only in preserved historical
evidence or diagnostics. `TOM` is out of the active feature scope. No combined-hat
result, TOM result, macro average, or remapping of historical labels can stand in
for an independently labelled and scored CHH or OHH result.

The active lane coordinates are fixed: BD `x=3,y=2`, SD `x=4,y=2`, CHH
`x=5,y=2`, OHH `x=6,y=2`, and BASS `x=7,y=2`. RD-01/RD-04 must exercise these
exact controls through the public grid path. RD-02/RD-06 acceptance requires all
five active lanes to meet every per-lane, per-stratum, negative-control,
quantised-cell and velocity gate below; a missing CHH or OHH gate blocks release.

## Feasibility and evidence

Capturing audio and painting 64 steps are feasible engineering tasks. Accurate,
fast classification of kick, snare, closed hi-hat, open hi-hat and bass attacks
from arbitrary mixed music on norns is an unverified premise, not a shipped capability. Bass
means pitched bass-instrument attacks, distinct from bass drum. Pitch transcription
is outside this request. Velocity is estimated attack strength; compression,
mixing and overlapping instruments prevent exact original MIDI-velocity recovery.

Official [softcut documentation](https://monome.org/docs/norns/softcut/) describes
input routing, recording and file export. It establishes capture facilities,
not a transcription engine. [Norns specifications](https://monome.org/docs/norns/)
include a quad-core 1.2 GHz/1 GB platform: desktop inference speed is not a norns
benchmark. [ADTOF](https://github.com/MZehren/ADTOF) and the
[drum-separation/transcription paper](https://arxiv.org/abs/2509.24853) provide
research candidates for drum attacks. Their drum-class vocabulary does not supply
the requested bass-instrument lane. [Demucs](https://github.com/facebookresearch/demucs)
offers drum/bass separation but requires independent latency/memory validation.
[Basic Pitch](https://github.com/spotify/basic-pitch) is a candidate for pitched
onsets on an isolated bass signal, not an assumed mixed-audio instrument classifier.
The proposed pretrained chain is described in `DETECTOR.md`: Omnizart raw heads
for BD/SD/CHH/OHH and Open-Unmix plus Basic Pitch for BASS. It remains
gate-blocked rather than delivery-selected: freeze the exact checkpoint manifests,
hashes, licences and dependencies before any installation or redistribution.

[Aubio's tempo interface](https://aubio.org/doc/0.4.4/tempo_8h.html) provides
streaming beat positions, BPM and confidence and is a candidate for the acquisition
stage. Its confidence scale needs calibration against fixtures. Tempo estimation
does not itself identify meter or the first beat of a bar; four-beat grouping
remains an explicit 4/4 interpretation with user-correctable start position.

Expected practical distinction: isolated or sparse rhythmic sources are easier
than mastered full mixes. Kick versus bass, closed versus open hats, hats versus
other noisy material, and simultaneous events need explicit error measurement.
Five frequency-band threshold detectors alone cannot establish instrument identity.
All five lanes remain required; no three-lane fallback may be labelled complete.

Source grounding: frozen audit source at
`audit/sweep-20260909-162423/source/lib/pages/trigger_edit_page/trigger_edit_page.lua`
and read-only live inspection at Mosaic HEAD
`b5901c1b72f81dfc80f638526a493e4c307a6495` (working changes not assumed absent).
Both show four algorithm buttons at x=12..15,y=2, a 64-step sequencer and Paint
at x=16,y=8. Current painting toggles admitted trigs and lengths; it does not
copy detected velocity. RD-01 must record exact implementation source hashes and
revalidate these anchors before adapting the current paint path.

Latest plan-review grounding, per user direction: clean worktree
`/home/andy/projects/perfdev/confirm/mosaic`, branch
`codex/perf-candidate-batch`, commit
`b5dffa00caacce63dc4abb4f66fb175f7c0e1b03` (2026-09-17). This commit contains
the earlier `b5901c1...` inspection revision. Review evidence must record this
path and identity; an older behavior-validation checkout cannot substitute.

## User contract and coordinate convention

User-facing pairs below are **row,column** on the existing 8-row/16-column grid.
Native grid callbacks use **x=column,y=row**; never transpose this silently.

| Grid row,column | Native x,y | Action in Rhythm Doctor |
|---|---|---|
| 2,16 | 16,2 | Select fifth algorithm, Rhythm Doctor |
| 2,1 | 1,2 | Empty bank: capture; occupied bank: request confirmed clear; active capture: cancel prompt |
| 2,2 | 2,2 | Reserved, no action; never an old numeric-fader side effect |
| 2,3 | 3,2 | Select BD (bass drum) |
| 2,4 | 4,2 | Select SD (snare drum) |
| 2,5 | 5,2 | Select CHH (closed hi-hat) |
| 2,6 | 6,2 | Select OHH (open hi-hat) |
| 2,7 | 7,2 | Select BASS (pitched bass attacks, no pitch extraction) |
| 8,16 | 16,8 | Existing Paint: first press previews, second commits |
| 8,14 | 14,8 | Existing Cancel: discard paint preview |
| 8,10 / 8,11 / 8,12 | 10,8 / 11,8 / 12,8 | Shift left / reset / right for selected lane preview |

The first four algorithms keep their IDs and controls. In algorithm 5, replace
the old row-2 parameter fader with these controls, disable unused old parameter
and bank-fader handlers/draws, and dispatch each press/release exactly once.
The fifth button must set enum 5 directly; extending a proportional fader must
not remap algorithms 1..4. Top-row pattern selection and the step area remain.

Record acts on key-down (z=1), not Mosaic's ordinary release-triggered short
press. Only this mode/control claims the gesture; consume its release, long-press
timer and dual-press participation without suppressing unrelated keys. A held
Record cannot retrigger, and disconnect clears its ownership. Preflight the
capture resource when entering the mode and show NOT READY until it can start;
do not spend the first beat loading a model. RD-01 measures key-down-to-first-PCM
latency (target <=10 ms), captures its timestamps and tests 20/100/500 ms hold
durations against identical injected audio origins. Any excess start latency is
reported explicitly; hold duration must never shift the buffer origin. The final
four-bar region is selected within that buffer, so Record need not land on a
downbeat. Preserve native dispatch behavior outside this exact control.

Existing norns screen shows RHYTHM DOCTOR, state, selected lane, hit count,
tempo/source, listening confidence, acquired beats or analysis progress. E2 selects setup fields,
E3 edits them; K3 confirms setup, K2 cancels/returns, K1 retains system semantics.
Setup: Tempo Auto (default)/Manual; Manual BPM; Input Stereo/L/R; selected-lane sensitivity;
Paint Toggle/Add/Replace. Default paint is Toggle to preserve the current gesture.
In the READY browser, E2 selects Window bar or Window step and E3 scrolls by
16 steps or one step respectively. Both edit the same bounded window-start index;
show START bar.beat.step and the four-bar end. K3 has no paint side effect on
these rows: commit remains the existing grid Paint control. Display total captured
bars/steps and the selected lane. During acquisition, K3 is labelled FINISH once
at least four usable bars are buffered; before that it is disabled with MORE AUDIO
NEEDED. While any confirmation modal is open, K2/K3 belong to that modal only.
No new task navigator. Clear confirmation is a modal on the existing screen:
`CLEAR CAPTURE BANK? / ALL 5 LANES / PAINTED PATTERNS KEPT`;
K2 cancels, K3 confirms. The initiating grid release cannot confirm the modal.
Every destructive modal captures project ID, capture generation, analysis
revision, operation kind and the state in which it opened. Dismiss it immediately
on project load/new, generation invalidation, capture completion/timeout, failure,
clear, or any incompatible state transition. K3 revalidates the complete token
before acting; a stale response closes with STALE REQUEST and changes nothing.
Refresh callbacks are not trusted to provide this safety. Test project replacement
and automatic completion/timeout while CLEAR CAPTURE, CANCEL CAPTURE and CANCEL
CORRECTION are open, including late K3/key-release events.

Alignment editor: detected BPM, Half tempo, Double tempo, exact BPM override,
Start beat and Fine start (milliseconds), with the proposed four-bar interval
and retained-audio bounds visible. E2 selects, E3 drafts, K3 applies, K2 cancels.
Half/double are explicit action rows activated by K3. These settings change the
capture interpretation only, never Mosaic's global tempo. Start beat moves among
detected beat positions; Fine start adjusts that position within buffered bounds.
Expose Alignment from READY as well as when the estimate is uncertain.

While transport is running, algorithm 5 displays STOP SEQUENCER; capture,
analysis initiation, clear, lane editing and painting are disabled. No action
silently stops or starts transport. A transport Start during capture/analysis
cancels and invalidates that unfinished job; Start during a paint/clear/setup
modal dismisses it without applying. A completed READY bank is preserved and
becomes usable again after Stop. Standard transport and native system controls
remain reachable; the modal must not swallow Start. Cancellation must not delay
normal transport Start: invalidate synchronously and signal bounded background
cleanup rather than blocking the event thread waiting for inference to finish.

## Four bars, clock and quantisation

Release 1 interpretation: 4/4 and sixteenth-note resolution, with a four-bar,
64-cell paint window per lane over a longer timeline. Display this before capture. In Auto, Record immediately
starts a bounded audio buffer and streaming beat/tempo estimation. Show LISTENING,
then ESTIMATED BPM and confidence. No pre-entered tempo or downbeat press is
required. Use elapsed samples independently of the stopped sequencer clock;
global tempo edits cannot change the captured interpretation.

At BPM B a four-bar window lasts T=960/B seconds: 8 seconds at 120 BPM.
Supported interpretation range is initially 40..240 BPM (24..4 seconds), subject
to RD-01/02 validation. Retain at most 45 seconds of input per capture; never
overwrite its beginning in a rolling buffer. Once a stable candidate and four
complete bars are available, show ENOUGH AUDIO / K3 FINISH and continue capturing
until K3 or the 45-second limit. This permits longer passages and fills without
forcing every capture to last the maximum. At the limit, stop input automatically
and analyse a valid timeline, or show the alignment/uncertainty state below.
Recorded earlier samples count toward the timeline. At 120 BPM, 24 seconds of
aligned material supplies twelve bars and nine bar-aligned four-bar windows.

Initial lock rule: at least eight detected beat positions and three estimates
spanning at least four seconds whose BPMs differ by at most 2%, confidence above
the detector-specific threshold frozen in RD-02, and acceptable beat-phase fit
over the proposed region. Eight beats alone do not qualify a region: its entire
16-beat duration must be buffered and validated. Consider half/double hypotheses;
if their scores cannot be distinguished at the frozen confidence margin, show
TEMPO UNCERTAIN with candidates rather than silently picking an octave. Freeze
the accepted BPM and origin on Finish/timeout; do not chase estimates
while classifying or painting. Validate the complete retained musical span, not
just its first four bars. Nonstationary tempo that fails the fit is uncertain,
not an excuse to force the audio onto a regular grid. RD-02 measures acquisition
success and latency; these initial rules are testable design targets.

Choose the earliest complete four-bar window in the stable-tempo span, starting at a
credible downbeat candidate if one is available. Otherwise choose a detected beat
and label START ASSUMED: BPM/beat confidence cannot certify bar-one position.
Automatic READY is allowed with that visible warning and an Alignment action;
the user can shift start to the intended bar. Never claim automatic meter inference.
The timeline and selected window must contain actual buffered audio for their full duration; do not
pad, repeat or time-stretch missing music to manufacture four bars.

On timeout with no valid span stop input acquisition and retain the buffer. Show
TEMPO UNCERTAIN or NOT ENOUGH ALIGNED AUDIO; open Alignment for BPM, half/double
and start correction. A valid in-bounds interpretation proceeds to analysis without recapturing.
If a correction needs unavailable audio, show NEED MORE AUDIO / RECAPTURE; require
the existing confirmed-clear flow followed by a new Record, rather than silently
resuming a discontinuous recording. Silence in Auto cannot establish BPM and
therefore follows the uncertainty path. Manual mode supplies a fixed BPM and a
Record-origin start; K3 Finish becomes available after T and capture continues
until Finish or the same 45-second limit. It remains useful for unrhythmic input
or a known-tempo source. Manual BPM defaults to the current Mosaic tempo but
does not change it. Unsupported BPM values are rejected visibly.

Alignment changes in READY are draft transactions. K3 validates bounds, disables
painting, invalidates the prior preview, and rebuilds all five timelines against the
same retained audio with a new analysis revision. Publish the result atomically;
on failure preserve the last READY interpretation with a visible correction-failed
message. Reset the window to the first complete four bars after alignment changes;
ordinary window scrolling needs no reanalysis. K2 leaves that original bank unchanged. Changes affect future painting
only; already painted patterns are never rewritten. A Start cancels acquisition
or reanalysis; in the latter case preserve the prior completed bank.

Capture sample indices, sample rate and start/end timestamps are authoritative.
After alignment let d=15/B seconds per sixteenth and N=floor((end-origin)/d).
Keep N complete timeline cells; require N>=64 to paint. Exclude leading audio
before origin and the incomplete trailing cell with visible duration information.
For each onset in [origin,origin+N*d), quantise once to zero-based timeline cell
min(N-1,floor((time-origin)/d+0.5)). Ties go to the later cell and near-final
events clamp to the last complete timeline cell. Store that cell identity before
window selection, so overlapping windows cannot quantise the same event differently.
Window start w displays cells w..w+63 mapped to pattern steps 1..64; scrolling
does not reclassify, renormalise velocity, or move an event relative to the timeline.
Preserve original buffer timestamps/confidence in the bank to diagnose quantisation.
Multiple events in one lane/cell collapse to one
trig with maximum estimated velocity; simultaneous events in different lanes
survive. Report collision count. Triplets, flams and swing finer than this grid
are lossy; source audio never supplies automatic microtiming or note lengths.

## Capture and analysis architecture

Default source is the norns physical audio input, stereo; L and R are selectable.
Do not mistake master-output tape capture for input capture. Internal engine,
tape or softcut-output sampling is a future explicit source option, not implicit
monitor feedback. Recording must not change input monitoring or audible output.

RD-01 compares a reserved softcut region/voice and an app-owned input capture
helper connected to the official audio graph. Choose a proven option that
coexists with Mosaic's n.b. engines, mods and softcut users. No global
softcut.reset, engine replacement, buffer erasure or commandeering active tape
recording. Snapshot/restore only resources owned by the capture lease. If no
safe route is available, display INPUT RESOURCE BUSY rather than disrupt music.
Completed PCM chunks may feed streaming tempo/features; final file completion
must be acknowledged before offline classification, with sample-count checks;
waveform thumbnail data is not full-band PCM suitable for classification.

Prefer a bounded native local worker with streaming feature extraction while
recording, then short final inference/decoding of the retained musical timeline.
All five complete timelines must be ready before READY is shown; browsing is
instant array slicing, not another separation/model job per window. Keep model work and file I/O
outside Lua's UI/event thread and audio callback. The audio callback only
copies into bounded owned buffers; overflow is a visible failure. Buffer size,
lookahead, cold/warm model loading, thread count and RAM must be benchmarked.
The 45-second maximum is about 17.3 MB at 48 kHz stereo float32 before feature,
model and duplicate-buffer costs. Include all those costs in the memory gate.
Tempo acquisition should run on the input mix in parallel with buffering;
full stem separation must not delay the first tempo estimate. Benchmark whether
cheap percussion features improve acquisition without requiring that separation.
Stereo preprocessing uses per-channel features or energy combination; avoid
blind L+R cancellation of opposite-phase inputs.

Use a pretrained-first architecture.  Do not train, fine-tune, transfer-learn or
learn a classifier/output head for Rhythm Doctor.  The candidate worker takes
immutable captured PCM and runs the published Omnizart `drum_keras` ONNX
candidate. Its raw heads may map 0/1/4/6 to BD/SD/CHH/OHH only after a fixed-audio
parity test establishes that its tensor order matches the source Keras model;
the stock writer's combined-HH output is insufficient. A separate frozen
Open-Unmix UMXHQ BASS separator feeds frozen Basic Pitch TFLite, constrained to
the bass range, for BASS attacks. This has a source-defined target label mapping
but is not yet a standalone-norns selection: the drum checkpoint's licence/hash,
Keras/ONNX parity and every ARM runtime measurement remain release blockers.
`DETECTOR.md` records the exact model comparison, source links, sizes, licence
status, adapter mapping and gates.

Run all model work in a bounded owned worker after capture; Lua's UI/event thread
and audio callback only manage bounded PCM and state. Overlapping instruments
require multilabel output. Detector probabilities are not velocities. Estimate
velocity from attributed attack energy using a versioned mapping to 1..127,
calibrated across the capture/lane rather than normalised independently per window;
keep confidence separate. Silence produces empty lanes without invented hits.
Clipping/no input and uncertain results are visible. Per-lane sensitivity changes
filter retained candidates and regenerate previews without recapturing; thresholds
and velocity mapping are selected on development data then frozen before held-out
acceptance; they may not be retuned per capture or on acceptance clips.

Local norns operation is the primary product objective. A local-computer worker
is a separately named optional profile if useful: explicitly paired, opt-in,
same result schema and no silent cloud upload. If only that profile passes,
report local norns performance unproven and require a scope decision before
claiming the requested standalone feature delivered.

## Bank lifecycle, races and persistence

One capture bank per project contains all five lanes, accessible while choosing
different destination patterns/song slots. It is independent of a selected lane
or a destination pattern. Store version, generation ID, analysis revision,
tempo mode/candidates/confidence, accepted tempo/meter, timeline origin/end,
window-start index, source/sample timing, detector identity/settings, candidates,
five variable-length trig/velocity timelines and quality warnings. A 64-step
window is a view, not the bank's storage limit. No bank is shared between projects.

States: EMPTY → LISTENING (Auto) or RECORDING (Manual) → ANALYSING → READY.
ENOUGH AUDIO is a capture substate enabling K3 Finish, not automatic termination.
Auto may go from LISTENING to ALIGNMENT REQUIRED at timeout, then to ANALYSING
after valid user correction. READY can enter REANALYSING with a retained prior
READY snapshot. FAILED is retryable with its diagnostic retained. Manual silence
can yield READY with zero hits; Auto silence requires manual alignment first.
An occupied buffer awaiting alignment is not EMPTY. Starting capture never
alters any pattern.

Record on EMPTY captures while transport is stopped. Record on READY or ALIGNMENT REQUIRED opens the all-lane clear modal;
cancel preserves the complete bank, confirm invalidates its generation and
returns EMPTY. It does not immediately record: the next Record press captures
new audio. Painted patterns remain intact. During LISTENING/RECORDING/ANALYSING,
Record offers CANCEL CAPTURE?; K3 cancels the job to EMPTY, K2 continues. During
REANALYSING it offers CANCEL CORRECTION?, restoring the previous READY snapshot.
Record
on FAILED retries after clearing only that job's partial owned artifacts.

Leaving the editor or switching algorithm may allow capture to finish in the
background but never paints automatically or steals screen focus. Project load,
new project and script cleanup cancel owned jobs and invalidate callbacks. Worker
responses must match project ID, capture generation and analysis revision; late results cannot
repopulate a cleared bank. Clear cancels any bank-derived paint preview first.
Only one capture job runs; repeated presses cannot spawn duplicate jobs.

Save READY banks, their bounded audio buffer and alignment metadata atomically
with the project; no transient workers. LISTENING, RECORDING, ANALYSING and
REANALYSING are save-inhibition states because Mosaic's existing project save
stops/resets transport and n.b. voices. During them, defer autosave by setting one
pending-save flag; do not enter project serialization or its audio/transport side
effects. Coalesce further autosave requests. A manual Save reports CAPTURE ACTIVE
/ FINISH OR CANCEL and changes neither disk nor audio; it never silently saves an
EMPTY or prior bank. On successful completion, cancellation or failure, clear
the inhibition and service one pending autosave through the ordinary lifecycle
only after capture resources and input routing are released. Project load/new
still cancels the job first, waits for bounded resource release, then continues
its explicit lifecycle; it does not run the deferred autosave for the old project.
Script cleanup discards a pending autosave and follows ordinary shutdown. Test
autosave and manual Save during each active state with sounding n.b. audio and
injected input: PCM must remain contiguous, monitoring/output unchanged, no
transport/audio lifecycle call may run, and exactly one deferred autosave must
occur after a terminal state where applicable. Reload never resumes input capture. Retaining
the buffer permits half/double and start correction after analysis and reload.
Use project-owned content-addressed audio assets; a failed save cannot delete the
previous asset. Clear removes the active reference and exactly owned temporary
files, never audio referenced by another saved project. Saved-file reclamation
must follow explicit reference ownership. Derived candidates permit sensitivity
changes; alignment reanalysis uses the retained PCM. Existing projects with no bank load EMPTY; reject
unknown schemas visibly without corrupting existing pattern data.

## Painting into the current pattern

Select a READY lane, scroll its four-bar window to the desired passage, choose
destination pattern on the existing top row, press Paint to preview that window's
64 cells and detected velocities, then Paint again to
commit through ordinary Mosaic mutation/history hooks. Selection or preview
alone never writes. Cancel discards only the preview, not the bank.

Freeze target project/song-slot/pattern ID, target revision, lane/capture generation,
analysis revision, window start, thresholds, shift and paint policy at preview. Changing target or underlying data
invalidates it visibly; confirm cannot apply a stale preview to a newly selected
pattern. Scrolling or changing lane during Paint preview rebuilds the preview
explicitly against the same pinned target and a new window revision; a confirmation
must use the displayed revision, never an earlier asynchronously rendered window.
Changing target cancels preview rather than following a new destination.
No delayed analysis callback may commit a pattern. Shift applies to trigs
and velocities together modulo 64, only in the preview; bank timings remain intact.
Scrolling selects different source events and does not wrap at the bank ends;
Shift rotates events inside the selected 64-step window. All five lanes share
one window start so switching BD/SD/CHH/OHH/BASS keeps the same musical passage.
Successive windows can be painted into different patterns; selecting a destination
does not move the window. A window can start on any sixteenth, with bar jumps
as a convenience. Require 64 complete cells, clamp scrolling to [0,N-64], and
show AT START/AT END; never loop or zero-pad a short tail without user knowledge.

Paint policies:

- Toggle (default): detected occupied cells toggle existing trigs. Turning a cell
  on copies the detected velocity and sets length=1; turning it off follows the
  existing trig/length clear behavior. Other cells remain unchanged.
- Add: detected cells become on with detected velocity; an already-on cell keeps
  its existing length, a newly-on cell gets length=1. Other cells remain unchanged.
- Replace: explicit norns confirmation names the destination and 64-step trig/
  velocity scope. Set all trigs to the lane mask, detected-hit velocities to the
  estimates and hit lengths to 1; absent cells have trig/length cleared but their
  stored velocity retained. Notes and unrelated pattern fields stay unchanged.

One commit is one undoable source-pattern edit including every affected trig,
velocity and length; redo restores it exactly. Add a bounded source-paint journal
owned by project/song-slot/pattern ID, separate from channel-mask history.
Each entry stores before/after values and a source revision; reproject every
channel referencing that shared pattern after apply/undo/redo. Expose explicit
Undo paint and Redo paint rows on the existing Rhythm Doctor norns screen,
using E2 then K3 while stopped. The rows name the current target and are disabled
if its stack has no applicable entry. Do not route these actions through channel
mask undo controls. New paint truncates that target's redo branch. Any intervening
ordinary edit to that source invalidates its paint undo/redo journal; stale undo
refuses visibly (PATTERN CHANGED) instead of overwriting newer edits. Other
patterns/channels do not invalidate it. Journal is session-only: project reload
preserves painted values and bank but clears undo/redo with a displayed notice.
RD-01 binds revision updates to every source mutation path, including ordinary
grid edits, copy and existing history; missing coverage blocks paint integration.
Painting an empty lane with Toggle/Add is a no-op;
Replace still requires the explicit clear-pattern confirmation. Short playback
ranges do not crop the bank: paint all 64 source steps, show that only the current
range plays, and never resize channel clocks/ranges automatically.

Rhythm Doctor authors source data deliberately. The existing Channel merge,
Musical Merge and Harmony overlays subsequently interpret it. It is not another
continuously running Channel overlay. BASS paints rhythm/velocity only; the user
authors its pitches with existing note tools and can then map them in Harmony.

## Performance and acceptance

Separate listening/tempo-lock latency, selected region duration, alignment wait,
model warm-up, transfer, analysis tail and
time to paintable READY. Initial engineering targets, not measured promises:
for four bars, local warm analysis tail p95 <=2 seconds and cold tail <=5 seconds;
for a full 45-second buffer, initial targets are <=5 seconds warm / <=10 seconds
cold. Window-scroll response p95 <=100 ms with no model rerun; general UI response p95
<=100 ms, incremental peak RSS <=256 MiB; no capture-induced audio xruns are
allowed. Measure analysis tail from Finish/automatic acquisition stop or confirmed
alignment, excluding explicit
user alignment wait but including all automatic processing thereafter. Record
at least 30 warm and 5 cold acquisitions across the BPM envelope
with Mosaic stopped and incoming audio active. Verify Start invalidates jobs
without delaying transport and cleanup does not breach existing playback timing
limits. If these fail, retain the result and revise architecture or
explicitly publish slower numerical latency limits; no fake READY before all five
lanes finish. Capture-induced xruns, audible routing/monitor changes, blocked or
delayed transport Start, and interference with normal post-cancel playback are
unconditional release blockers and cannot be converted into published limits.
Desktop timing cannot certify ARM norns performance. No manual or real-hardware
test is required for software acceptance: automated native-runtime audio injection
is mandatory; unavailable matching hardware performance remains an explicit
unverified claim, never inferred from throttled desktop runs.

RD-02 freezes a licensed, independently labelled corpus before detector tuning:
at least 40 development and 40 held-out four-bar clips, with source songs/kits
disjoint (never adjacent segments of one recording). In the held-out partition,
each active lane (BD, SD, CHH, OHH and BASS) must have at least 10 positive
clips and 50 annotated events, including at least 5 full-mixture clips, 2 sparse-mixture clips and 2
isolated clips; the remaining positive clip may be any of those strata. Counts
can overlap across lanes. Each lane must span electronic and acoustic timbres.
Also include at least 5 absent-lane negatives per lane, 3 silence clips, and
declared clipping, phase-inverted stereo and kick+bass-unison cases. Report
quality separately per lane and per isolated/sparse/full-mixture stratum;
missing strata cannot pass by an overall score. Each such lane/stratum must
meet the same onset gate. Require held-out per-lane onset F1 >=0.80 at
one-to-one 50 ms matching and quantised-cell F1 >=0.85 on straight-sixteenth
aligned fixtures; no macro average can conceal a missing active lane. Negative
controls must have zero painted events at default threshold. On labelled controlled
gain ladders, relative velocity must be monotonic; on independently rendered
velocity fixtures report per-lane MAE with initial gate <=16 MIDI units. Real mixes
receive relative-dynamics evaluation, not an exact-MIDI-velocity claim. If these
initial gates fail, report the failed lane/domain rather than relabel its output.

Add independently annotated longer acquisition fixtures (up to 45 seconds),
not just already cropped four-bar files: random Record phase, silence/intro before
rhythm, 40/60/120/180/240 BPM, syncopation, half/double ambiguity, changing tempo
and uncertain downbeats. Initial Auto gate: >=90% of steady-tempo eligible held-out
clips select an in-bounds 16-beat region within the timeout at BPM error <=2%;
report every octave error separately, never score half/double as correct. Beat
phase error must be <=50 ms on accepted aligned fixtures. Ambiguous/silent or
unstable cases must expose uncertainty. Score bar-start accuracy separately from
tempo and beat phase; assumed starts must be labelled. Verify half/double and
start corrections, insufficient-buffer refusal, reanalysis cancellation/revision
races, saved audio round trips and no change to already painted patterns.
Test K3 Finish eligibility, the 45-second cap and the Record-cancel modal's K3
ownership. Use a twelve-bar fixture with distinct middle/end fills: scroll by
bar and by step, compare all overlapping windows against one independently
annotated timeline, preserve velocities across overlaps, switch all five lanes
at the same window, and paint two distinct passages into two patterns. Verify
nonwrapping bounds and partial-tail exclusion, window-preview revision checks,
unchanged bank after painting, and playback through ordinary Channel overlays.

End-to-end tests inject actual PCM through the norns input route, operate the
real Mosaic grid/key path, capture bank display/LED evidence, paint to disposable
patterns, and play through actual MIDI output. Reference events come from fixture
annotations or independent render metadata, never the classifier's own results.
Mocks are allowed for race/error unit tests, not transcription acceptance.

Mosaic's own AGENTS.md remains binding at delivery: write externally observable
acceptance before implementing each feature, then run affected unit/integration,
relevant emulator behavior tests and the existing full Lua suite after the change
settles. Use controlled-time musical expectations where applicable and real-time
checks; explicitly document controlled-time inapplicability for PCM capture and
wall-clock inference rather than simulate successful audio analysis. Update the
Mosaic README and cheat_sheet.html, with durable actual grid/norns captures under
images/ and accompanying semantic assertions. Missing required evidence blocks
RD-06. No manually operated hardware or listening certification is introduced.

## Delivery cards and checkpoints

| Card | Work and dependencies | Exit evidence |
|---|---|---|
| RD-01 Source and capture spike | Freeze live code hashes, native coordinates/dispatch, paint/history, clock/sample alignment, official capture route and resource ownership. | PCM injected and captured intact without disturbing engine/softcut/tape; fifth-button mapping and all four legacy algorithm baselines; exact insertion table. |
| RD-02 Tempo and five-lane feasibility | RD-01; freeze independent acquisition/transcription corpora for BD/SD/CHH/OHH/BASS; evaluate the pinned pretrained-only raw-head drum and BASS-separation/onset worker, tempo stability/confidence, half/double candidates and region selection; record code, checkpoint manifests, hashes, licences and runtime artifacts. No training or fine-tuning. | Tempo/phase/uncertainty gates, all five active per-lane quality results, listening/tail/RSS benchmarks and supported platform envelope; missing exact checkpoint terms, a combined-HH result, failed BASS chain, or failed norns premise blocks standalone claim. |
| RD-03 Capture bank | RD-01/02; implement bounded audio/timeline storage, Finish eligibility, bank schema, state machine, save inhibition/deferred autosave, project assets/save/load and late-result rejection. | No input, silence, full/disk error, 45-second cap, overflow, cancel/clear, duplicate press, manual/autosave under active jobs with sounding n.b. and contiguous PCM, project switch/reload and interrupted-save tests; asset references safe. |
| RD-04 Fifth algorithm UI | RD-03; native grid/norns controls, Auto/Manual listening, Finish, timeout/alignment editor, half/double/start correction, shared window scrolling, lane selection, confirmed clear and stopped-only operation; preserve algorithms 1..4. | Every mapping/modal, transport gate/Start cancellation, in-bounds correction/reanalysis, nonwrapping bar/step scrolling, release ownership and all 64 displayed cells; no redraw mutations. |
| RD-05 Paint and velocities | RD-04; versioned window preview, shifts, Toggle/Add/Replace, source-paint journal and complete source revision checks. | Five lanes and multiple distinct/overlapping windows painted to disposable patterns, exact trig/velocity/length MIDI expectations; reachable undo/redo, stale refusal, shared-channel playback, save/reload window/values and journal reset. |
| RD-06 Integrated release | RD-05; corpus rerun through actual input path while stopped, Start/Stop cancellation races, subsequent playback verification, optional Musical Merge/Harmony integration, README/cheat-sheet and durable images. | Full five-lane evidence, affected unit/integration and relevant runtime behavior tests plus existing full Lua suite; controlled/real-time coverage or documented inapplicability; unchanged first four algorithms, latency/quality limits, no orphan resources, clean optional-asset installation. One bounded Codex Paranoia review. |

Planning checkpoint: one Codex-only Paranoia `critique_plan`, medium effort,
10-minute limit, class_closure=false, claim_verification=false. External premises
are assigned empirical gates above. Retain request, plan hash, full raw reply,
session ID and disposition; at most one focused follow-up for substantive fixes.
Missing/error review is not acceptance. No mandatory multi-vendor convergence.
Emulator changes, if needed, stay generic audio-input capabilities; Mosaic's
classifier, fixtures and model assets never become core emulator dependencies.

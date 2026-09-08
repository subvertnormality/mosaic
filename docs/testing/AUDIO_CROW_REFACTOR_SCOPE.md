# Audio and Crow behaviour expansion for the Mosaic refactor

Status: scope reviewed and amended; execution planned, no new coverage is claimed. Requested 2026-09-08 against emulator
`f301e7644746f699fa769b6ab7cf3bb678f3c228`. This revision records integration;
implementation is `a7dd08c` plus `f66bb22`, admitted by `4b7ab6b`.

This amendment extends BEHAVIOUR_PLAN.md. Actual PCM, virtual Crow voltages/input
and Just Friends wire output are now required for the supported profiles below.
It supersedes the earlier audio/n.b. DSP exclusion only for these profiles.
The entire existing MIDI/manual campaign remains required. The broad refactor
must wait for both that campaign and this expansion's admission gate.

## Boundaries and evidence already available

Use the current authorised Mosaic worktree, its dirty-source digest and actual
entry point. Emulator `tests/mosaic_audio.py` and `tests/mosaic_jf.py` are migration
references: they pin old Mosaic `160d1ea`, use an emulator-private Slice, and prove
only a four-note audio phrase/stop tail and mono JF phrase/release respectively.
Do not transfer their pass status to this branch. Generic `tests/nb_audio.py`
proves player behaviour, not Mosaic routing, lock or recording behaviour.

The added platform supplies native engines/JACK/SuperCollider; bounded stereo WAV
capture/injection; browser PCM; identified DoubleDecker/n.b. mods; pinned Crow
ASL/CASL CV with none/change/stream input and Crow-source clock; JF ii writes.
Generic boundaries stay owned by emulator tests. Mosaic owns user recipes and
independent musical expectations. Use public Session capture/input/ii methods;
never import emulator-private test drivers or mutate Mosaic globals.

Audio and Crow run in real time. Controlled Lua time is not DSP/Crow time.
Requesting unsupported D capture must fail explicitly; MIDI D evidence cannot
certify PCM, CV or ii timing. Record separate native MIDI monotonic timestamps,
WAV sample positions/rate, Crow sample epoch and ii monotonic timestamps. Establish
and test mappings before cross-clock assertions; no subtraction of unrelated
epochs, fitted origin, or sample-accurate claim from a capture-start ACK.

Pin runtime composition, norns/Crow sources, n.b., DoubleDecker and nb_jf separately.
The candidate path in emulator A01-tranche1.md is a local reference, not a portable
dependency lock. Integrate audio/Crow with MIDI-hotplug in an isolated candidate
and prove generic conformance before using it; neither capability may disappear.
Do not replace the user's default runtime or modify another task's session.

Physical DAC/ADC, speakers, downstream JF synthesis, ii reads/followers, Ansible,
unsupported Crow modes, arbitrary engines, arc and cheat codes 2 remain explicit
capability gaps or other emulator work. Missing Mosaic-relevant support is tracked,
not counted as a pass. Broader scripts/desktop/Maiden/Docker retain their separate
delivery order. No hardware, listening or manual screenshot approval is required.

## Independent output oracles

PCM checks need an event-level time/frequency envelope: expected notes in their
windows, missing/unexpected tones, rests, releases, stereo routing, finite samples,
clipping and capture integrity. Whole-recording RMS or presence of four frequencies
cannot prove ordering, duration or absence of extra notes. Use simple pinned player
settings with declared envelopes/effects; independently calculate equal-tempered
frequencies and expected envelopes. Calibrate detector sensitivity using generated
PCM fixtures with wrong pitch, missing note, extra tail, reordered notes, globally
shifted phrase, wrong duration, swapped channels and discontinuity faults.
Freeze frequency/amplitude/onset tolerances before candidate runs. Where timbre
prevents reliable event discrimination, pair a generic boundary probe with actual
Mosaic PCM and declare precisely which property each establishes.

CV checks use volts, full channel traces and source-bound timestamps: pitch ratios,
gate edges/duration, slew trajectories, unused-output silence and finite values.
ii checks use independently decoded complete packets: address, voice, signed pitch,
level, setup, order, release and sequence continuity through pagination. Establish
the n.b. velocity mapping against manual/player contracts; do not copy step.lua's
formula merely because it produced the earlier passing fixture. MIDI, PCM and JF
may legitimately encode the same musical velocity differently.

Maintain one semantic event table (pitch, velocity intent, onset, duration, route)
with backend-specific expected outputs. Do not demand byte-identical waveforms
from an asynchronous synth. Refactor comparisons supplement independent oracles;
a before/after match cannot bless an existing bug. Retain visible selected-device,
screen parameter and grid edit assertions alongside sounding/wire output.

## Staged cards and selected regression cases

Every case below is a planned family. Expand the named small finite choices fully;
use min/min+1/interior/max-1/max and discontinuities for larger domains. Cases list
the high-value minimum, not an exemption from remaining manual requirements.
All run real-time; selected logical input recipes additionally retain MIDI D/R
coverage. Each card records commands, identities, artifacts, failures and gaps.

### X00 — Capability composition and trustworthy observations (first)

Depends: existing runner and admitted emulator tranche. Add opt-in profiles
`nb-audio`, `crow-cv`, `crow-jf`, `mixed-outputs` to the Mosaic runner with explicit
capability preflight. Acquire mods externally; inventory actual selectable players
and their supported functions before generating player cases. Capture complete
WAV/CV/ii evidence on success and failure; bounded polling and strict cleanup.

| Case | Recipe and observable guard | Edges / required negative |
|---|---|---|
| XA-001 | Boot current Mosaic with each supported mod profile; select by verified displayed name, author a note, observe its intended output and no other route | Cold/warm load, mod absent/disabled, changed engine/Crow Lua identity, failed engine readiness; no fallback to MIDI or silent success |
| XA-002 | Capture while grid/key/MIDI actions run; export and independently verify samples, sequence, hashes and terminal job status | Short/long bounds, cancel, backend death, truncation, missing file, nonfinite samples and overflow must fail; emulator contracts reused, one composed Mosaic fault guard |
| XA-003 | Run two isolated sessions with distinct pitches/ports; stop one and continue the other | No OSC/audio/CV/ii crossover, held input or capture leakage; three fresh restarts; run serially except this bounded isolation case |

Done: profiles load the current worktree using public APIs; measurement faults fail
the intended assertion, not an unrelated timeout. Generic app-free controls/grid/
MIDI/hotplug/audio/Crow contracts pass on the composed candidate. No new source
hashes may be learned from edited dependency files during composition.

### X01 — Voice selection, ownership and release (highest priority)

Depends X00. Primary refactor seams: device lookup, nb dispatch, per-note ownership,
channel selection, MIDI/n.b. translation, stop/retrigger and scheduled callbacks.

| Case | Recipe and observable guard | Edges / required negative |
|---|---|---|
| XA-004 | Author full phrases on channels1/16; assign MIDI, DoubleDecker and each supported JF voice mode via controls | Confirm/cancel; assigned unique n.b. player excluded from other channels, freed player becomes selectable again; distinct compatible JF voices/mixed players; route switch stopped/playing; old releases retain ownership |
| XA-005 | Play distinct pitches and velocities through each supported player | Pitch low/middle/high legal values, octave boundaries; velocity minimum, midpoint, maximum, zero only where UI supports it; no hard-coded shared gain formula |
| XA-006 | Retrigger same pitch with shorter/equal/longer durations; overlapping chords and repeated notes on two channels | Old release must not cut a newly owned voice; missing release, wrong voice and duplicate onset fault fixtures fail |
| XA-007 | Stop/restart during held notes, strums and arps; mute/unmute and route changes | Final owned releases, bounded declared effect tail, no ghost restart notes; test MIDI panic separately—manual promises a MIDI sweep, not universal nb.stop_all |
| XA-008 | Exercise supported mono/poly/kit/MPE/unison JF selections | Independently specified setup, voice allocation, pitch/level packets and final releases; all finite voices, repeated/overlapping notes, allocation exhaustion/stealing, mode switch with pending notes/slew, parameter limits; unsupported functions explicit |

JF selectors share a module: distinct player IDs do not prove independent mode
or release ownership. Inventory mode/setup and all-voice release effects from the
pinned player; specify compatible combinations and observable conflict handling
before testing. Do not require simultaneous incompatible kit/mono modes or invent
shared-player support. Establish intended behaviour through contracts and focused
arbitration where current code/manual disagree.

Done: complete phrase and release accounting on each route with screen/grid proof.
An empty inherited nb.stop_all is not accepted as working; distinguish Mosaic,
player and emulator defects with a generic player reproducer and isolated fix.

### X02 — Musical transformations, locks and modulation

Depends X01 and existing T04/T05 editing primitives. Prioritise shared sequencer
logic whose correctness on MIDI does not prove correctness through nb dispatch.

| Case | Recipe and observable guard | Edges / required negative |
|---|---|---|
| XA-009 | Reuse independent scale/transposition/octave/chord recipes on audio and JF | Signed pitch boundaries, root mute, duplicate pitches, strum/arp order and rests; full phrase, no missing voice hidden by aggregate spectrum |
| XA-010 | Apply player parameter defaults, locks, trigless locks and slides through controls | Off/zero/bounds; lock→unlocked-trig restoration including original zero, manual edit during lock, device/parameter reassignment with queued slide; non-1 range/wrap/descending chains/song change/stop; no stale target writes or NRPN waiver |
| XA-011 | Configure each supported matrix/toolkit path to a player parameter, then manual edit and lock it | Depth/rate boundaries, enable/disable, channel switch, competing lock/mod/manual precedence; sound/voltage/wire trajectory and displayed parameter must agree |
| XA-012 | Change tempo/division/swing while notes or parameter motion remain pending | Duration/phase continuity and ordered releases; no D-only acceptance and no broadened timing tolerance to excuse musical error |

For n.b. locks, declare the original-value restoration contract independently
before execution: when restoration occurs, whether manual edits update the saved
value, and which target owns queued work after reassignment. Inspect source only
to find discrepancies, not to manufacture expected values.

Done: independent expected musical events and parameter trajectories pass through
new outputs. Start with sparse dry phrases, then combine features; do not duplicate
the full existing MIDI Cartesian matrix for every synth setting.

### X03 — Keyboard recording and persistence across backends

Depends X01 and T05/T06. Reuse the agreed recording contract: active processed step,
first press to final release; disarmed held notes finish, fresh notes do not record.

| Case | Recipe and observable guard | Edges / required negative |
|---|---|---|
| XA-013 | Record keyboard notes/chords assigned to audio/JF; replay and inspect grid, duration and output route | Disarmed live audition; held key across selected-channel/device changes; live/sequenced same-pitch overlap with exact release ownership; before/on/after boundary, unequal rates, first-press/final-release, arm/disarm |
| XA-014 | Save/autosave, fresh-process reload and replay mixed-output song | Mod/player identity, per-channel selection, parameters, locks/slides, song slots and routes preserved; dirty source identity bound per run |
| XA-015 | Load with missing/disabled player or incompatible capability; cancel then recover with correct profile | Explicit diagnostic, prior project preserved, no silently substituted voice; failed/truncated save and unknown player ID |

Done: reconstructed output and visible edits survive cold restart; failure paths
preserve valid project data. No WAV/audio recording workflow is invented for Mosaic
merely because generic audio injection exists; map any such requirement to actual
manual functionality before adding it.

### X04 — Crow CV/input/clock and Just Friends integration

Depends X00 plus pinned Mosaic-usable CV player/capability evidence. JF can proceed
independently; generic Crow support does not itself prove a Mosaic CV voice exists.

| Case | Recipe and observable guard | Edges / required negative |
|---|---|---|
| XA-016 | Select the supported CV player; author pitch/gate/velocity or slew gestures actually exposed by that player | All supported output mappings, min/max/signed voltages, rests, legato/retrigger, stop/restart; no crosstalk or stale gate; preserve output units |
| XA-017 | Feed Crow clock pulses via public input and run Mosaic phrase; switch internal→Crow→internal | Missing/extra pulses, tempo change, stopped/started source, source handoff with held note; prove clock lock/origin before measuring onset and release; no fabricated sample-level timing |
| XA-018 | Feed supported voltage change/stream inputs to an actual documented Mosaic/player consumer | Threshold equality/hysteresis, repeated identical voltage, both inputs, callback burst and stream stop; if no consumer exists, retain generic conformance ownership and explicit not-applicable rationale |
| XA-019 | Capture JF setup/note/release across pages, simultaneous voices and lifecycle | Exact commands/order/addresses, page boundary256 records, tail drain, no unrelated packets; dropped/reordered/repeated/partial record negative guards |

Done: application-level pitch/gate/clock/JF behaviour has measured outputs; pinned
firmware and wire tests independently support encoding. Unsupported Ansible/ii
reads are capability gaps, not simulated answers or a claim of hardware support.

### X05 — Mixed-output stress and browser regression guards

Depends X01–X04. Use a small intentional interaction matrix instead of exhaustive
cross-products: routing×release, clock×recording, locks×modulation, persistence×
player identity, session shutdown×capture, browser disconnect×held input.

| Case | Recipe and observable guard | Edges / required negative |
|---|---|---|
| XA-020 | Ten-minute mixed MIDI/audio/JF/CV workload with editing, autosave, chords and clock changes | Complete MIDI/ii trace integrity plus bounded PCM/CV windows around transitions/final release; no stuck voices/gates in observed windows or growing clocks/process leaks; preserve MIDI limits and predeclare audio/Crow measurement limits |
| XA-021 | Automate browser controls over Mosaic during audio monitoring; compare actual framebuffer/grid and rendered PCM | Focus loss while held, monitor enable/disable, disconnect/reconnect, capture concurrent with monitoring; mute monitor must not stop sequencer or capture |
| XA-022 | Ten reload/stop/reset cycles including one failed engine/Crow session | Owned cleanup, retained failure evidence, no orphan service or other-session interruption; unexpected exit fails and captures native stack on recurrence |

The delivered capture APIs allow at most eight jobs of at most30 seconds each
per session. XA-020 therefore schedules bounded observation windows within that
budget around chosen transitions and final release, while running the full
ten-minute workload and retaining complete MIDI/ii traces. Intervening PCM/CV
samples remain explicitly unverified. If continuous ten-minute PCM/CV evidence
becomes necessary to diagnose a defect, add a named emulator capture capability
dependency; do not silently relaunch sessions or splice windows into a continuous
claim. Timing checks distinguish relative musical intervals from absolute
input-to-output latency; the latter remains unverified without an independently
bounded mapping across the native, DSP and Crow clocks.

Keep detailed sample-rate/block conversion tests in generic browser suite; run
one composed Mosaic browser guard per relevant renderer change. Existing two-minute
sampled continuity evidence is not an every-sample no-click guarantee. Use a known
steady signal for discontinuity sensitivity and a sparse Mosaic phrase for routing.

### X06 — Refactor admission and economical regression tiers

Depends all applicable X00–X05 and original T00–T08 gates. Every XA family must have
atomic cases, manual/player contract references, observable oracles, explicit
domain choices, source-bound real-time evidence and resolved major defects.
Platform-only/not-applicable rows need concrete source evidence and owner; missing
capabilities for required behaviours remain blocking, never skip/xfail green.

Fast development tier: one dry phrase, same-pitch retrigger/release, mixed-route
ownership, one parameter lock, one JF packet/release, and a cold-load smoke. Target
under three minutes after build; measure rather than promise. Pull-request tier:
affected card suites plus shared routing/clock/lifecycle guards. Refactor admission:
full original campaign and all expansion cases once on the exact baseline; run
all again on refactor plus changed-boundary negatives. Endurance only at admission
or after relevant changes/failures. One bounded Codex scope review plus at most one
focused follow-up, then evidence-based implementation; no per-case review ritual.

Do not start the refactor while XA families remain planned, unsupported-required,
failed or indirectly verified. The scope ledger is `audio-crow-scope.json`; it is
a planning ledger, not executable coverage. Register executable cases in the
actual runner and wire them into require-all before declaring this gate complete.

## Scope review disposition

Codex session `01a08200-2e90-75f1-a9c1-ca7aff78686f` completed one bounded
read-only scope critique. All six findings are incorporated: unique-player
selection rules (XA-004), bounded endurance observation (XA-020), n.b. restoration
and stale targets (XA-010), live keyboard ownership (XA-013), JF unison/shared-module
constraints (XA-008), and temporal/channel negative fixtures (X00 oracle admission).
Raw response: `reviews/audio-crow-scope-review.json`. These are plan corrections
and additional guards, not evidence that execution or runtime composition passes.
A second review is reserved for a substantive implementation/gate dispute.

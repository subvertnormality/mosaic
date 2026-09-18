# Parameter-lock foundations implementation status

The implementation is staged against `docs/parameter-lock-lead-foundations-plan.md`.
Step nudge remains a separate delivery. This checkpoint does not change the existing
delayed-note lead contract or claim working parameter lookahead.

## Implemented scaffolding

- Default-off preallocated numeric probe for pulse, parameter resolution, note
  production, delayed callback/group dispatch and MIDI write spans.
- Bounded single-line Maiden readout, raw replies, ownership-aware removal and
  dropped-record rejection. Probe snapshots stop recording before copying rows.
- Explicit lead, seed, timing-contract and probe identity in hardware fixtures and
  reports; public parameter setter/readback before each window.
- Non-destructive fixture migration with verified input hashes. Historical fixtures
  remain preserved and cannot silently acquire an inferred lead identity.
- Independent synthetic absolute-time/lock-gap oracle; stock device dispatch traces
  are explicitly diagnostic and cannot qualify receiver timing.
- Configurable measured-step windows, without changing acceptance thresholds.
- Pure next-step selection extracted with existing wrap/first-run semantics.

Probe schema 1 rows contain timestamp seconds, kind, pulse, context, deadline
seconds, boundary (1 begin / 2 end), bytes and batches. Context is a channel,
sprocket ID, batch index or queue serial depending on kind. It is **not yet** an
immutable musical occurrence ID. Zero deadlines mean that no deadline was supplied.
Do not interpret those rows as an independently anchored intended timeline.

The earlier probe was recovered read-only from
`/home/andy/projects/perfdev/pulseprobe/mosaic`. Its uncommitted lattice diff
preallocated 40,000 arrival/duration entries at module load, always installed the
global and silently stopped recording at capacity. The new adapter installs only
on request, records overflow explicitly and avoids calling `util.time()` at module
load (the unit stub cannot supply it).

## Evidence so far

Terra ran the original baseline `b5901c1b72f81dfc80f638526a493e4c307a6495`
in `/tmp/mosaic-baseline-b5901c1/mosaic`: 1,618/1,618 Lua tests passed.
The isolated candidate `/tmp/mosaic-candidate-checkpoint/mosaic` passed
1,627/1,627. Logs and the candidate runtime SHA manifest are in their respective
parent directories. These results establish the tested checkpoint only.

Durable copies are in
`tests/behaviour/candidates/parameter-lock-foundations-checkpoint/`. The committed
checkpoint is `e7edad3`; all 181 files in the tested runtime Lua manifest match the
workspace checkpoint bytes. Terra also passed 252 configured Python harness tests
on that commit. `test_output_profiles` was not run because its optional output-mod
source is unavailable. Existing cases M-SYNC-LEAD-002, -016 and -018 passed in both
controlled and real-time lanes. This is focused checkpoint evidence, not the
exhaustive release campaign or a test of new lookahead behaviour.

After the optional diagnostic-kind filter, Terra preserved its expected failing
baseline, passed the focused regression, and passed the full Lua suite again:
1,629/1,629. The later filter applies only when explicitly requested by the probe
adapter. The six emulator runs and hardware smoke above identify the earlier
checkpoint; they are not relabelled as executions of the reduced profile.

## Harness use

Create a new fixture variant locally before any device deployment:

```sh
python3 tests/behaviour/real_norns.py prepare-fixture \
  --project-fixture /path/to/original/locks-16 \
  --fixture-destination /path/to/new/locks-16-lead25 \
  --lock-lead-ms 25 --seed 20260918 --pulse-probe
```

For a run using the test runbook's hardware arguments, add
`--lock-lead-ms 25 --seed 20260918 --measured-steps 80 --pulse-probe` and the new
fixture path. Omit `--pulse-probe` for an uninstrumented window and identify that
fixture variant accordingly. `--measured-steps` adjusts the window duration from
the configured tempo and workload stride; it does not relax the oracle. Restore
after every run, even a failed one. Exit status alone is never a passing gate.

## Outstanding gates

Checkpoint A remains incomplete: controlled probe identity coverage, calibrated
input/receiver capture integration, interleaved hardware diagnostics and probe
overhead qualification are still required. The pure parameter preview, base onset
projection, occurrence/generation ledger, cancellable value queue and lookahead
arbitration are not implemented. Neither are Timing feedback, product migration,
the complete behaviour matrix or release hardware qualification.

The user confirmed on 2026-09-18 that no calibrated receiver capture rig exists.
The hardware shim timestamps in Lua immediately before `_norns.midi_send` calls
the original C binding. It observes dispatch; subsequent driver queues, USB and
wire serialization are outside that measurement. The existing hardware thresholds
remain unchanged and describe dispatch timing. Controlled emulator capture checks
virtual-time correctness, not physical delivery. Pulse arrival/work spans can
investigate thread contention without inventing a receiver timestamp. Receiver
qualification is unavailable, not a failed timing result, and does not itself
authorize the plan's nonzero-lead-disabled fallback. Building a physical capture
rig is outside this implementation checkpoint.

The first hardware smoke (locks-16, 130 BPM, lead 25, two 80-step windows per mode)
completed with successful restoration after each run. All four windows passed the
existing dispatch gates. The full probe nevertheless has an unresolved overhead
problem: p95 step jitter was 0.87–1.21 ms off and 2.48–2.52 ms on. These are
off/off/on/on observations, not the required interleaved campaign. No causality or
probe-overhead acceptance is claimed. The results and restoration journal are in
the checkpoint evidence directory; raw artifacts are under
`tests/behaviour/artifacts/lock-lead/e7edad3/legacy-delay-v1/smoke-20260918`.

`--pulse-probe-core` selects a reduced experimental scope (pulse, MIDI write and
delay callback spans; kinds 1/4/5). It suppresses per-channel and per-group clock
reads/records. Use the same flag when preparing its fixture. It cannot be combined
with `--pulse-probe`, and its reduced scope is recorded in run identity. It still
requires hardware overhead qualification before using it as causal evidence.
The full-trace offline `correlate_deadlines()` helper classifies delayed-group
deadlines by recorded pulse occupancy; it explicitly makes no causal inference.

Follow the test runbook before device work, restore after each run and preserve all
failed evidence. The runner in this checkout uses `git archive HEAD` for deployment;
uncommitted files are **not deployed**, unlike the runner variant described in the
supplied appendix. Freeze and identify a committed source before hardware trials.

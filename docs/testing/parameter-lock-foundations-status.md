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

## Outstanding gates

Checkpoint A remains incomplete: controlled probe identity coverage, calibrated
input/receiver capture integration, interleaved hardware diagnostics and probe
overhead qualification are still required. The pure parameter preview, base onset
projection, occurrence/generation ledger, cancellable value queue and lookahead
arbitration are not implemented. Neither are Timing feedback, product migration,
the complete behaviour matrix or release hardware qualification.

Follow the test runbook before device work, restore after each run and preserve all
failed evidence. The runner in this checkout uses `git archive HEAD` for deployment;
uncommitted files are **not deployed**, unlike the runner variant described in the
supplied appendix. Freeze and identify a committed source before hardware trials.

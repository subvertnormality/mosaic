## Appendix A — how to actually run the tests

The sections above say *what* to measure. This says *how*. None of it is guessable
from the repo.

### A.1 Local unit tests

```
cd <worktree>/mosaic && ./test.sh
```

- The worktree directory **must be named `mosaic`** or `test.sh` fails.
- Expect **1618 tests**. Two are known flaky and fail intermittently on an
  unmodified tree: `test_live_slide_admission_all_channel_parameter_slots` and
  `test_dense_live_slide_replacements_keep_all_final_slots_running_after_ring_wrap`.
  Always confirm a suspected regression against an unmodified tree before believing
  it — run the control three times.
- `util.time()` is **not callable** in the unit-test stub (`util.get_time` is nil).
  Code that calls it at module load must degrade gracefully or ~400 tests error.

### A.2 Local behaviour cases (the emulator lane)

```
MONOME_EMULATOR=$EMU python3 tests/behaviour/run.py --case M-SYNC-LEAD-002 \
  --experimental-install $EMU/.runtime/ci-qualified/runtime/installation.json \
  --clock-mode controlled-experimental --artifacts <dir>
```

- Lanes: `controlled-experimental` (virtual time, µs tolerances) and `real-time`
  (10 ms tolerance). The lead matrix is judged in `controlled-experimental`.
- Each case prints a JSON blob whose `manifest` path holds `passed` and `failure`.
- A full 19-case sweep takes roughly 30–40 minutes. Run it detached and block on a
  sentinel rather than polling.
- **Manual/inventory reconciliation:** editing `README.md` invalidates
  `tests/behaviour/manual-inventory.json` and
  `docs/testing/unit-integration-hardening-matrix.json`. Every case then errors with
  "Manual changed: reconcile inventory". Rebind both hashes in the same commit as
  any README edit.

### A.3 The device

Address `we@10.42.0.1` over a wifi hotspot. **Password auth only — no SSH key.**
The password is the public norns default, `sleep` (the owner confirmed it may be
documented).

Still keep it off command lines and out of logs and artifacts, so it never lands in
process listings or evidence. The sanctioned method is a temporary askpass file for
an SSH ControlMaster, deleted immediately:

```
A=$SCRATCH/.ap$$; umask 077; printf '#!/bin/sh\necho sleep\n' > $A; chmod 700 $A
SSH_ASKPASS=$A SSH_ASKPASS_REQUIRE=force DISPLAY=:0 \
  ssh -MNf -o StrictHostKeyChecking=no -o ControlPersist=yes -S $SOCK we@10.42.0.1 </dev/null
rm -f $A
```

- `$SOCK` must be a short path: a Unix socket path over 108 bytes fails silently
  and the next command reports "Control socket connect ... No such file".
- Do not pipe the master's output (e.g. into `grep`): the backgrounded master holds
  the pipe open and the command never returns, so the `rm` never runs.

All later commands reuse `-S $SOCK`. **The master dies periodically** (it did twice
in one session) and every device operation fails with ssh exit 255 until it is
re-established. Check with `ssh -S $SOCK -O check`.

### A.4 Running one hardware case

```
python3 tests/behaviour/real_norns.py performance \
  --performance-case PERF-002-HW-16 \
  --config-source tests/behaviour/config --device-map-id cc_device \
  --host we@10.42.0.1 --ssh-option=-S --ssh-option=$SOCK \
  --maiden-url ws://10.42.0.1:5555 --osc-host 10.42.0.1 \
  --maiden-input --synthetic-grid --source <worktree> --run-id <id> \
  --artifacts <dir> --project-fixture <fixture-dir> \
  --stock-clock-errors record --maiden-timeout 900 --measured-windows 6
```

Case ids: `PERF-009-HW-16` locks, `PERF-002-HW-16` dense, `PERF-003-HW-16` slides,
`PERF-010-HW-16` extreme. Results land in `<dir>/**/performance.json` under
`oracle.gates`, `oracle.step_jitter`, `oracle.timing`, `resources`.

**A run exiting 0 does not mean the gates passed.** Exit 0 means the run completed.
Always read `oracle.gates`. (This was misreported once in this project.)

Durations vary widely — 3 to 19 minutes for the same case on different days, and one
run took 96 minutes when the link degraded.

### A.5 Fixtures

Under `perf-campaign-20260915/final-25/qualified/fixtures/{locks,dense,slides,extreme}-16`.
Each holds `autosave.ptn`, `autosave.pset` and a `fixture.json` carrying **sha256 of
both files**. The lead is stored in the `.pset` as `midi_lock_lead_time`. To make a
variant, edit the pset, then recompute both hashes into `fixture.json` or the run is
rejected.

### A.6 Restore — mandatory after every run

```
python3 <campaign>/final-deadline/qualified/restore_with_stock_errors.py restore \
  --host we@10.42.0.1 --ssh-option=-S --ssh-option=$SOCK \
  --maiden-url ws://10.42.0.1:5555 --osc-host 10.42.0.1 \
  --run-id <id> --artifacts <dir>
```

A run installs its own build over the user's. The user's copy is stashed under
`/home/we/.cache/mosaic-real-norns/<run-id>/` (`code-mosaic`, `data-mosaic`,
`had-code`, `had-data`, `had-state`). Verify afterwards, all four:

1. `/home/we/.cache/mosaic-real-norns/active` is **absent**
2. `systemctl is-active` on norns-jack / crone / matron / maiden → all `active`
3. `/home/we/dust/code/mosaic` is the user's copy (check mtime)
4. Five stock bindings via `maiden_eval.py binding_probe.lua`: four `C [C]:-1 []`
   plus `midi.event Lua /home/we/norns/lua/core/midi.lua:<line>`

The restore is **idempotent** — safe to re-run if it fails.

### A.7 Device hazards (all encountered)

- **Never power-cycle the device.** If a restore has not run, the `active` marker is
  still set and a reboot brings the device up on the *test* build, not the user's.
- **Never interrupt a measurement.** Stop between queue items with a
  `STOP-AFTER-CURRENT` sentinel the queue checks.
- **Never edit a worktree that is the `--source` of a running run.** `real_norns`
  uploads HEAD **plus the uncommitted diff**, so an edit mid-run corrupts it. Keep
  development and run trees separate.
- `pkill -f` / `pgrep -f` **match the invoking shell**. Use PIDs.
- The **restore can wedge** on the maiden websocket, polling forever (33 minutes
  once). The device is healthy in that state; the fix is host-side — kill the client
  and re-run the restore.
- The **wifi link collapses** occasionally (66% loss, 2.3 s RTT observed). Symptoms:
  ssh timeouts, an install phase that never finishes, and the device unresponsive to
  its own encoders (expected during install, since matron is restarted).
- **`kept-<run-id>` collisions**: move any pre-existing directory aside before a run.
- Record every persistent device change in `DEVICE-CHANGES.md` and every anomaly in
  `INCIDENTS.md`. Never delete or rewrite existing evidence.

### A.8 Instrumenting the device (the pulse probe)

An instrumented `Lattice:pulse()` records per-pulse arrival and work duration into a
preallocated `_G.mosaic_pulse_probe` (see `perfdev/pulseprobe`). Reading it back:

- `maiden_eval.py` feeds the file to maiden's REPL **line by line**. A multi-line
  script is torn into fragments evaluated in separate contexts — this silently
  produced nonsense twice. **The probe script must be a single line.**
  `binding_probe.lua` is the working example.
- **`io.open` returns nil in that eval context**, so the probe cannot write a file.
  Print the data instead, in rows, as integers.
- Probe state is lost at restore, so a readout must happen after the measurement
  window closes and before the restore.
- Keep the whole eval reply. Grepping for a success marker throws away the reason
  for a failure.

### A.9 Statistical discipline

**One repeat cannot distinguish these designs.** Identical repeats of `locks-16`
measured 1.20 and 4.86 ms p95. Run at least 2 repeats of all four cases, report the
range, and treat a single favourable run as noise. Several early conclusions in this
project were wrong for exactly this reason.
Shell cwd was reset to /home/andy/norns-emulator
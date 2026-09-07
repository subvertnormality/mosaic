# Native Mosaic behaviour tests

Run from this worktree with an explicitly selected emulator checkout:

```sh
export MONOME_EMULATOR=/path/to/monome-emulator
python3 tests/behaviour/run.py --list
python3 tests/behaviour/run.py --case M-PAT-001
python3 tests/behaviour/run.py --case M-LEN-001
python3 tests/behaviour/run.py --require-all
```

The final command intentionally fails until all manual requirements and the full
campaign gate are implemented. A focused case passing is not complete coverage.
The length case initially reproduces a known baseline defect; it is never xfailed.
Runtime inputs use the public emulator Session client, with physical encoders,
buttons and grid events. Results assert raw screen/LED and native MIDI outputs.
No Mosaic model functions are invoked to manufacture expected results.

Runs use sibling mosaic-behaviour-runs storage, away from the source tree and
user project data. Each run links the actual worktree under its required code/mosaic
name, seeds a declared MIDI config, records loaded source identities and complete
native inputs/MIDI, and preserves failure evidence. Test source must remain stable
during an execution. The default native lane uses wall time. An explicit experimental diagnostic
lane now uses logical time; it is not admitted campaign D evidence.

Initial four-note and length recipes and Cairo header oracle adapted from the
monome-emulator project's tests, with independent literal musical expectations.

Initial public client revision: ce812e7 in subvertnormality/monome-emulator.
Full acceptance rejection verified after requirement-ID and both-manual-hash checks; all114 indexed source sections remain incomplete.

Experimental timing diagnostics (requires the separately built emulator C16
candidate, not the default runtime installation):

```sh
python3 tests/behaviour/run.py --clock-mode controlled-experimental \
  --experimental-install /path/to/candidate/installation.json --case M-LEN-001
```

This lane records `diagnostic_only: true` and `controlled_time_admitted: false`.
Control pacing and observation waits advance the real native runtime through the
public input API. Recipes include every advance and are checked against the full
native input trace. MIDI assertions use native logical emission timestamps with
a two-nanosecond rounding allowance; real-time assertions retain the existing
10ms jitter allowance. An exact-time failure remains a nonzero exit.


The optional modulation profile uses independently supplied, clean checkouts at
the exact revisions in mods.lock.json; no mod is a default test dependency:

```sh
python3 tests/behaviour/run.py --case M-PAT-001 --profile midi-modulation \
  --mod-code-root /path/to/code-containing-matrix-and-toolkit
python3 tests/behaviour/run.py --case M-SAVE-001
python3 tests/behaviour/repeat.py --case M-SAVE-001 \
  --experimental-install /path/to/candidate/installation.json
```

repeat.py runs three fresh controlled cases and compares physical input recipes,
ordered logical MIDI, final grid/frame/clock and outstanding notes for every
process segment. Only host timestamps and process/source-location identities are
omitted. It preserves failures and never converts incomplete campaign coverage
into acceptance. Per-case manifests record end-to-end wall time and total logical
time advanced. M-SAVE-001 retains both native process segments under its run
directory; its second process reads the actual first process's saved data.

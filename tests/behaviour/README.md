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


Modulation output cases are M-MOD-001 (macro routing/clear) and M-MOD-002 (clocked
pulse LFO with MIDI pitch and timing assertions). The former exposes a confirmed
bug in the pinned matrix dependency. To select the isolated correction explicitly:

```sh
python3 tests/behaviour/run.py --case M-MOD-001 --profile midi-modulation \
  --mod-code-root /path/to/code-containing-matrix-and-toolkit --mod-patches
```

The patch manifest pins original/modified file hashes and patch bytes. Only the
run's own matrix copy is patched; supplied checkouts remain untouched. The flag
also works with repeat.py and controlled mode. Omitting it preserves the failing
baseline. Candidate selection is recorded in each case manifest and is not a
claim that the full dependency or Mosaic suite passes.

## Full regression suite

`suite.py` runs every declared layer and every registered case, fail-closed:

```sh
export MONOME_EMULATOR=/path/to/monome-emulator
python3 tests/behaviour/suite.py run --output ../mosaic-behaviour-runs/suite-<name> \
  --experimental-install /path/to/candidate/installation.json \
  --output-mod-root /path/to/mosaic-output-mods
python3 tests/behaviour/suite.py compare BASELINE/suite.json CANDIDATE/suite.json
```

Layers: all `tests/behaviour/*.lua` contracts (each with its declared argument),
every `test_*.py` oracle module (unittest or declared script), the unchanged Lua
units in an isolated copy seeded with the emulator's pinned norns Lua tree (a
network fetch fails the layer), and each case in the real-time and controlled
lanes. A test file the suite does not classify fails collection. Non-base
profiles are reported NOT RUN unless requested with `--profiles` and
`--mod-code-root PROFILE=PATH`; audio/Crow profiles are real-time only. The
report binds the Mosaic tree digest (tracked, dirty and untracked files), the
emulator checkout and the installation, and fails if the tested tree changes
during the run; run it from a clean worktree of the commit under test when
editing continues elsewhere. `compare` exits nonzero on any item that passed in
the baseline and does not pass in the candidate: this is the refactor guard.
`complete_regression_run` is true only for an unfiltered run of every layer in
both lanes with no required item left unrun. It is not manual coverage closure.

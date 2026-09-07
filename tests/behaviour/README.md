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
during an execution. Current native lane uses wall time; controlled time is T02.

Initial four-note and length recipes and Cairo header oracle adapted from the
monome-emulator project's tests, with independent literal musical expectations.

Initial public client revision: ce812e7 in subvertnormality/monome-emulator.
Full acceptance rejection verified after requirement-ID and both-manual-hash checks; all114 indexed source sections remain incomplete.

# R03 parameter registration extraction

Base: `915d937`. `mosaic.lua` now delegates its MOSAIC parameter declarations to
`lib/application_parameters.lua`. The native init entrypoint retains startup order,
project/autosave closures and all other initialization. Three project actions are
passed explicitly; no general dependency container or new parameter semantics.

Validation: all 1514 Lua tests passed; six inventory/naming/syntax guards passed.
Controlled M-SAVE-001 passed with native autosave and cold restoration:
`/home/andy/projects/mosaic-behaviour-runs/d1895bf05de0435eb71d41c194780511/manifest.json`.
Real-time M-SAVE-001 passed:
`/home/andy/projects/mosaic-behaviour-runs/aad7a1c57d954877ae849973905f7534/manifest.json`.
An exact comparison with the old registration block passed after reversing only
the three project callback forwards. Lua syntax and diff checks passed. One WSL
connection timeout preceded a successful retry of that read-only comparison.
This is a structural slice, not completion of R03 or the overall delivery.

Prior slide-index exploratory measurement at `915d937`:
`/home/andy/projects/mosaic-behaviour-runs/perf-003-slide-index-915d937-exploratory/result.json`.
PERF-003, 16 channels, 8 seconds, one repeat passed: p99 3.737327 ms,
maximum 6.369230 ms, final phase 1.044063 ms, 48 checked slide cycles, 784 note-ons,
2786 MIDI messages. Limits were 0.5 CPU, 768 MiB, CPU0. Shared-host load and a single
repeat prevent a causal speedup or final acceptance claim. Existing reds are retained.

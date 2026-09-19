# R03 project/autosave ownership

Base `413d69b`. `lib/project_lifecycle.lua` owns load, save, new-project and
autosave operations, inhibition state and timer replacement. `mosaic.lua` retains
native callbacks and initial timer allocation order, passes the existing parameter
manager/validator and a splash-state callback, and delegates autosave_reset.
The existing native globals remain external boundaries; this is not a new framework.

The project integration fixture now loads the actual module in its existing IO and
transport environment and captures the constructed instance. Private upvalue paths
were replaced as follows: init/load_project -> load; init/load_new_project -> new;
autosave_reset/prime_autosave -> prime_autosave; prime/do_autosave -> autosave;
do_autosave/save_project -> save. All existing assertion and scenario bodies,
including the queued-callback helper, are unchanged by exact comparison.

Moved production function bodies match the previous code except the explicit splash
callback. Rejection-before-Stop, IO restoration, saved shape and autosave policy are
preserved. No new behaviour or timing tolerance was introduced.

Validation: 1514/1514 Lua tests, six inventory/naming/syntax guards, Lua syntax and
diff checks passed. Controlled native manifests under
`/home/andy/projects/mosaic-behaviour-runs/`:

- M-RANGE-SAVED-002: `90fb61abcda34273a1d8adc6b2951fa1/manifest.json`.
- M-SAVE-002: `ee04712c217543fdb90603fe89331efb/manifest.json`.
- M-RANGE-SAVED-003 (named save and reload):
  `55ac6b2a43714196898a3a831d958fb9/manifest.json`.

The first real-time launch failed at the WSL service connection before test startup;
no process remained. The next run, `eff2a22816bd454ab368d588fa66e094`, failed in
Python fixture setup because this case requires an explicit experimental-install
path even in real-time mode. It did not reach rejected-load execution. The corrected
invocation supplies the same pinned installation as the controlled run and passed:
`c8efd9b4456b41f5963833ac93e5182e/manifest.json`. Neither setup failure counts as an
application pass.

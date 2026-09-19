# Rhythm Doctor core contracts

These modules are pure Lua foundations for the Rhythm Doctor UI integration. They
do not capture PCM, select a transcription model, touch norns state, mutate a
Mosaic pattern, or save projects. RD-02 remains the empirical tempo/classifier
gate; callers pass already-detected candidates to `bank.build`.

`bank.build(args)` accepts authoritative `sample_rate`, capture/origin sample
indices, 40–240 BPM and five-lane candidates with `sample_index`, `velocity` and
`confidence`. It returns a serializable bank with retained candidates and one
quantised timeline cell per candidate. `bank.with_sensitivity`, `window`,
`move_window` and `with_window_start` are copy-returning view operations. A view
always represents exactly 64 cells; use `cell_count` rather than Lua's `#` on its
sparse `cells` table.

`state_machine.new(callbacks)` has `start_capture`, `finish_capture`,
`begin_reanalysis`, `receive_analysis`, `request_record_action`,
`confirm_modal`, `transport_started`, `autosave`, `manual_save`,
`replace_project` and `cleanup`. It returns result tables with stable `code`
values. `finish_capture` requires a confirmed `enough_audio` flag. Pass the
actual stopped status into stopped-only entry points. Worker responses must echo
`job_token()` exactly and include `bank.valid_ready`'s complete five-lane schema.
Resource release is asynchronous: `on_release` only starts bounded cleanup; the
host must call `resources_released(owner_token, transport_stopped)` before one
deferred autosave can run. Callbacks are optional and injected:
`on_capture_start`, `on_analyse`, `on_reanalyse`, `on_cancel`, `on_release`,
`on_deferred_save`, and `on_state`.

`paint.preview(spec)` pins bank, lane, window start/revision, thresholds, shift,
policy and target identity and rotates a 64-cell source view; `valid_preview`
checks every pin; `apply(source, preview, adapter)` returns a copied
source snapshot. The integration must call the normal Mosaic mutation/history and
channel-reprojection hooks only after pin validation and any Replace confirmation.
The default adapter is boolean `trigs`/`velocities`/`lengths`; numeric
Mosaic-style data must pass an explicit whole-source adapter such as
`{ trig_field, velocity_field, length_field, on = 1, off = 0 }`.

`paint_journal` is session-only. `record` takes the source's resulting revision and its revision before paint;
an intervening ordinary edit starts a fresh stack, preserving only the new paint.
`prepare_undo`/`prepare_redo` return a snapshot for the host to apply, then
`complete_undo`/`complete_redo` records the host's new revision. A mismatch
returns `PATTERN_CHANGED` and never overwrites the source.

`with_window_start` returns a new small bank header that shares immutable
candidate/timeline storage with the prior bank. Do not mutate those shared arrays.

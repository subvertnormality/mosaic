# R04 model mutation map

Source snapshot: `2a8727f` on `codex/behaviour-validation`.

Migration labels: **Explicit** means the writer receives or captures song/channel
identity before mutation, including across deferred work. **Partial** means an
explicit core exists but wrappers or sibling callers still use ambient selection.
**Deferred** means the writer still resolves a meaningful target from global
selection or mutates an escaped model table directly.

## State ownership

| Class | Data and owner | Save/lifetime and invalidation |
|---|---|---|
| Persisted source | `song_patterns[*].patterns[*]`: trig, length, note, note-mask and velocity arrays; owned by `program_store` in `lib/models/program.lua` | Saved in `.ptn`. Any edit invalidates the affected song/channel `working_pattern`. |
| Persisted source | Per-song scales, transpose, global length, repeats and active; per-channel selected patterns, merge modes, masks, locks, slides, octave, scale, range, mute and timing overrides | Saved in `.ptn`. Pattern/merge/mask edits invalidate `working_pattern`; scale changes invalidate quantised results; length/timing changes affect clock and song boundaries; assignment/lock changes may retire slides. |
| Persisted source | `channel.trig_lock_params` and top-level `devices` routes | Saved in `.ptn`. Configuration rebuilds native params, clears dirty recording, cancels old-assignment callbacks, and refreshes device/lock UI. Routes are top-level per channel while assignments are per song/channel. |
| Persisted history | Rings, cursors, original/prior/result states and event song IDs in `program_store.memory` | Bound by `memory.bind_project()` and serialized by `prepare_for_save()`. History and model must always refer to the same replacement project. |
| Separate native state | Device parameter defaults and Mosaic options in companion `.pset` | Native `params`, not the `.ptn` target. Actions may emit output, update clocks, enqueue edits, or reset autosave. |
| Derived but currently saved | `channel.working_pattern`; generated scale/pentatonic arrays and scale `version`; `trig_lock_calculator_ids`; legacy `memory.pattern_states` | `prepare_for_save()` returns the whole store, so these are copied/saved today. Treat working patterns as rebuildable output. Keep `pattern_states` only for compatibility. Calculator IDs are callback generations, not musical source data. |
| Module caches | Quantiser caches, device-map merged-param cache, pattern scratch arrays and weak per-song debouncers | Cache keys must contain complete source identity. Replacement/copy must not allow old deferred publication into a new song. |
| Transient fields mixed into the project | Selected page/song/pattern/channel/scale, current channel steps, global accumulator, repeat count and blink | Currently included in the returned project store. Selection is a cursor, never a delayed writer target. Clock/reset owns step and repeat cursors. |
| Transient module state | Recorder portions/dirty values; clock voices, delayed IDs, slides and sprockets; step queues; MIDI held-note/chord ownership; grid presses; UI controls; autosave timers | Stop, panic, disconnect, assignment change, song transition and project replacement define their lifetimes. Do not copy these into songs or edit commands. |

## Writer families

| Family and source anchors | Target identity | Invalidation/lifetime implication | Status / action |
|---|---|---|---|
| Project construct/replace: `program.init/set`, `project_lifecycle.load/new` | Whole replacement project; memory is rebound before history deserialization | Stop/reset playback, rebuild native params, refresh UI/grid, and prevent old recorder/clock/debounce work publishing afterward | **Explicit** for project-memory binding. Cleanup of other transient owners remains lifecycle work. |
| Defaults/migration/lazy repair: `model_defaults.migrate`, `program.get_song_pattern`, `device_map.validate_devices` | Explicit replacement tree or song ID; device repair writes top-level route by channel | Defaults must produce complete source state; route repair needs parameter/UI rebuild | **Partial**. Keep migration centralized; move route repair behind an explicit project/device operation when touched. |
| Song copy: `program.set_song_pattern(source,destination)`, `song_edit_page.lua` | Source and destination IDs are explicit; deep copy includes derived channel fields | Destination working patterns, dynamic params, timing and view state are replaced; history is not copied | **Partial**. Publish a complete destination and later stop copying derived/runtime-shaped fields. |
| Selection/runtime cursors: program setters plus direct page and clock assignments | Ambient cursor or explicit channel number | Refresh view/clock configuration; never retarget pending edits, held notes or callbacks | **Deferred** as model separation. Capture edit/playback target before deferral. |
| Pattern editors: `trigger_edit_page.lua`, `note_edit_page.lua`, `velocity_edit_page.lua`, sequencer controls | Repeated selected-song/selected-pattern lookup; controls can mutate referenced pattern tables | One targeted working-pattern rebuild and active flag after a gesture | **Deferred**. First edit command should capture song, pattern and affected steps once. |
| Channel composition UI: selected-pattern set, merge modes, octave, range, mute in `channel_edit_page.lua` | Mostly direct selected-channel writes | Selected-pattern/merge changes rebuild one channel; octave affects playback; range/timing update clock bounds; mute is immediate runtime behavior | **Deferred**. Separate musical edits from transport/view actions. |
| Channel/step masks: `channel_edit_page_ui.handle_*_mask_change`; mask operations in `program.lua` | Channel-wide handlers receive an object. Selected-step toggle/clear resolves the channel once. Per-field number wrappers still read selected song | Invalidate one channel working pattern and refresh mask/lock UI | **Partial**. Selected-step toggle/clear is explicit; migrate remaining wrappers with the command that needs them. |
| Octave/scale/transpose/parameter locks and slides: page gestures and `program.add_*/clear_*/toggle_*` | Parameter-lock core has explicit-channel add/clear. Octave/scale/transpose APIs still use selection; slide APIs receive channel objects | Refresh lock UI; cancel assignment-owned slides when needed; scale/transpose invalidate quantiser results. Ordinary parameter locks do not invalidate working pattern | **Partial**. Add explicit song/channel variants incrementally and retain compatibility wrappers. |
| Held-step recorder: `recorder.add_*_event_portion/record_stored_*` | Trig-lock portions capture song and commit through `memory.record_event_for_target`. MIDI-note mask data carries song, but encoder mask portions keep it only at the event top level and `record_stored_note_mask_events` discards that target | Portion lives to grid release; commit must update history and the captured model target | **Partial**. Trig locks are explicit at `2a8727f`; make note-mask commit use `event.song_pattern` through the same explicit memory core. |
| MIDI note/chord recording: `handle_midi_event_data`, `recorder.handle_note_midi_message` | Note-on captures channel/device ownership and note portions capture song. Note-off length recording still reads current selected song | Release must use onset song/channel/device and survive selection changes; Stop retires chord ownership | **Partial**. Store onset song in MIDI held-note/chord state and use it for release-time length commit. |
| Live parameter recording: `recorder.trig_lock_dirty/record_trig_event`, `step.process_recording_params` | Dirty state is channel/slot keyed; clock commit uses compatibility memory ingress, deriving song from current selection | Assignment/disarm/Stop clear dirty state. Song transition must follow an explicit playback target | **Deferred**. Pass playback song into the record commit. |
| Memory ingress: `memory.record_event_for_target` and `record_event` | Explicit song + channel in core; wrapper uses `data.song_pattern` or selection | Truncate redo, capture prior/result, advance ring, apply exactly one target event | **Partial**. New deferred writers use explicit core; retain wrapper for synchronous/legacy callers until audited. |
| Memory apply/undo/redo/all: `memory.lua`, `memory/event_handlers.lua` | Stored event song ID + channel; handlers receive channel object | Mask events update masks and working step; page navigator rebuilds after undo/redo. Trig locks change lock banks/slides only | **Explicit** for replay identity. A command seam may later own rebuild, preserving event shape and ring floors. |
| Memory bind/reset/load: `bind_project/init/deserialize_state/clear` | Bound project-memory object or explicit channel history | Replace rings/cursors/original states together; new/load cannot retain old references | **Explicit**. Do not promote legacy `pattern_states` into cache authority. |
| MIDI mapping params: `m_midi.set_up_midi_mapping_params` | Selected-channel actions resolve at action time. Fixed-channel actions hold channel number but still resolve current song. Memory replay follows stored event song | Same rebuild/refresh as delegated handler; mapping controls reset silently | **Deferred** for song identity. Resolve song + channel once and pass explicit target, preserving fixed-map held-step behavior. |
| Device configuration/assignment: `update_channel_config`, `param_manager.update_param/update_default_params` | Selected channel object plus top-level route by channel number | Reinstall dynamic actions, increment calculator generation, clear dirty record, cancel old spread action, refresh UI | **Partial**. Make route target and per-song channel target separate explicit arguments. |
| Native param/application actions: `application_parameters.lua`, `param_manager.add_device_params`, UI `params:set` | Param ID; installed closures capture channel/device route. Global options have no song target | Device changes reinstall actions; timing changes update lattice; device values may emit MIDI and autosave | **Partial**. Params are adapters around explicit edits/output, not canonical project writers. |
| Pattern rebuild/publication: `pattern.update_working_pattern(s)` | Single rebuild takes channel + song. Bulk rebuild takes optional song and has weak per-song debounce; many callers omit target | Every pattern/selection/merge/mask edit must schedule its song; copy/replacement cannot accept stale publication | **Partial**. Convert ambient callers with each writer migration. Add revisions only after all invalidators use this path. |
| Clock/song transitions: `m_clock.lua`, `step.process_song_song_patterns/reset*` | Explicit runtime channels; transition writes selected song then configures/rebuilds it | Retire song-owned slides, align timing, reset step/repeat under options, rebuild target song | **Partial**. Carry playback song into recording and delayed callbacks instead of reading editor selection. |
| Modulation/player output: native modulation reaches installed params actions; `nb/lib/player.lua` `modulate*` emits to live players | Param ID or player/note handle; NB output has no project target | Parameter modulation inherits action route/assignment lifetime. Player modulation ends with voice/device | **Deferred** where it enters Mosaic mapping params. Output-only NB modulation remains outside model mutation. |
| Device/quantiser cache writers: `device_map.get_params/invalidate_*`, `quantiser.process*` | Device ID; quantiser key uses scale content/version and processing options | Device definition changes clear matching cache; scale edit must change complete key/version | Device invalidation API is **Explicit**; quantiser identity is **Partial**. Keep cache invalidation downstream of model operations. |

## Near-term migration order

1. Make note-mask pending commit honor the already captured top-level song, then
   store onset song identity in MIDI held-note/chord ownership for release-time length
   recording.
2. Add one small pattern edit operation for one page family. It should carry song,
   pattern and affected steps, then publish one targeted working-pattern rebuild.
3. Route the corresponding selected and fixed MIDI-map actions through that operation,
   proving grid/encoder/MIDI entry points share target and invalidation behavior.
4. Add a per-song/channel source revision only after every writer that can affect
   that working pattern increments it. Until then, targeted rebuilds are safer.

### Pending note-mask ownership closure

M-MASK-032 now proves captured-song commit, second-song isolation and undo/redo
in both timing lanes; candidate `0114-pending-note-mask-song-target.patch`.
All 1534 Lua tests and six guards pass, with three identical controlled repeats.
Earlier delta-1 runs were invalid evidence: native encoder sensitivity requires
two counts per detent. Only the corrected baselines in the candidate record count.
Next: MIDI held-note/chord release-time length ownership across a song transition.

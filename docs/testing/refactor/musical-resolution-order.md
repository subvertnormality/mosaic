# Musical resolution order

Verified against Mosaic commit `38385b7`. This document records observable ordering that an R06 extraction must preserve. It separates two scopes that are easy to conflate:

1. **Same-pulse runtime order**: which lattice sprocket runs first when several sprockets are due on one lattice pulse.
2. **`step.handle` inner order**: how one accepted or rejected trig resolves probability, pitch, velocity, routing, and delayed notes inside the channel sprocket.

The order numbers below are lattice order groups. They do not imply that every action happens on every pulse.

## Source anchors

- `lib/clock/m_lattice.lua`: `Lattice:pulse`, `Lattice:order_sprockets`
- `lib/clock/m_clock.lua`: `m_clock.init`, local `sprocket_action`, local `end_of_clock_action`, local `process_ring_buffer`
- `lib/step.lua`: `process_stock_params`, `process_recording_params`, `process_params`, `calculate_step_scale_number`, `calculate_step_transpose`, `handle`, local `handle_note`, local `handle_arp`, local `play_note_internal`
- `lib/helpers/functions.lua`: `transform_random_value`, `transform_twos_random_value`
- `lib/recorder.lua`: `record_trig_event`, `record_stored_note_mask_events`
- `lib/musical_resolution/chord_order.lua`: `index`

## Same-pulse runtime order

`Lattice:pulse` visits order groups 1 through 5. Within a group, `Lattice:order_sprockets` sorts sprocket IDs ascending. Pending `before_onset` actions that are due run before their owner sprocket; due zero-length actions created by an onset run after that onset. Equal delayed-action deadlines retain insertion order.

| Order | Source anchor | Operation when due | Ordering that must remain |
| --- | --- | --- | --- |
| 1 | `m_clock.init` master clock | For global lengths at least 3, optionally preannounces an Elektron program change. On later runs, applies `step.process_song_song_patterns()` and refreshes the selected song. Then advances and wraps the global step. | A due song transition is applied before any channel resolves its song/channel for this pulse. |
| 2 | `m_clock.init` channel `sprocket_action` | Advances one channel step, handles wrap bookkeeping, resolves scale and locks, runs the trig, then records after-step parameter events. | Coincident channel clocks run track 17 first, then channels 16 down to 1, because they were created in that order and IDs are sorted ascending. |
| 3 | `end_of_clock_action` | For regular channels, records stored note-mask events for the just-finished step and schedules the memory UI refresh. | This is the delayed end-of-clock recording phase, after the corresponding order-2 work when both are due on one lattice pulse. |
| 4 | short-global-length sprocket | For global lengths 1 or 2, optionally sends the Elektron program change after the master and channel work. | Keep this separate from the order-1 preannouncement path. |
| 5 | `process_ring_buffer` | Advances active parameter-slide callbacks at 1/48 resolution. | On a coincident pulse, slides run after orders 1 through 4. |

Within an order-2 regular-channel action, the preserved sequence is:

1. Resolve the currently selected song, channel, working pattern, and pattern range.
2. Advance, clamp, or wrap the channel step.
3. On wrap while recording, clear all ten dirty recorder trig-lock values.
4. Publish the channel step scale with `calculate_step_scale_number`.
5. For an active trig, or any step when trigless recording is enabled, run `process_recording_params`.
6. For an active trig, or a trigless step that contains a parameter lock, run `process_params`.
7. For an active trig, call `step.handle`.
8. For an active trig, or any step when trigless recording is enabled, call `recorder.record_trig_event` for slots 1 through 10 when this is the selected recording channel.
9. Update the clock's first-run and next-step state, then mark the applicable grid view dirty.

Track 17 takes a different order-2 branch: it publishes `current_scale_channel_step`, applies `process_global_step_scale_trig_lock`, then calls `sinfonian_sync`. The normal clock path does not call `step.handle` for track 17.

## `step.handle` inner order

This sequence starts only after order-2 parameter recording and lock processing described above.

1. Resolve the selected-song channel, working pattern, route, source note or note mask, velocity, length, and channel octave.
2. Apply a step octave lock when present. Lua treats `0` as true, so octave zero is an explicit override.
3. Resolve trig probability. The existing expression calls `process_stock_params` once when the first result is `-1`, and twice for other first results.
4. If probability is below 100, draw `random(0, 99)`. A rejected trig stops note construction, but does not stop the outer channel action's later recorder calls.
5. For an accepted trig with quantiser hold enabled, clear the persistent channel step scale.
6. For both accepted and rejected trigs, republish the channel step scale and calculate transpose.
7. For an accepted trig, resolve pitch randomness in this order: bipolar random shift, then twos random shift.
8. Resolve the note-mask/full-quantise branch and calculate the base pitch.
9. Resolve random velocity.
10. Resolve quantised fixed note, then fixed note. A valid fixed note wins last over both quantised fixed note and the calculated pitch.
11. Resolve the output device. Stop if the route is disabled.
12. If the channel is not muted and the note exists, call `handle_note`, which sends or schedules root, chord, strum, or arp notes.

Chord order selection is delegated to `lib/musical_resolution/chord_order.lua:index`. The extraction preserves the four existing index sequences: input order, reverse order, alternating low/high, and alternating high/low. It must not change when the sequence is consulted.

## Sentinel and truthiness invariants

`process_stock_params` scans slots 1 through 10 and stops at the first matching assignment. Its return values are semantic:

- A step lock equal to that parameter's `off_value` returns `nil` before the assigned parameter value is read.
- A present lock returns unchanged. Lua makes both `0` and `-1` truthy.
- With no present lock, the assigned parameter value is returned with `or nil`; an assigned value equal to `off_value` is not filtered here.
- With no matching assignment, a stock fallback is returned only when it differs from the parameter default.
- Callers interpret `nil`, `-1`, and `0` independently. An extraction must not coerce them to one disabled state.

Concrete consequences in `step.handle`:

- Probability `-1` means 100. Probability `0` remains active, consumes a probability draw, and rejects.
- A note-mask value of `0` enters the mask branch; only `nil` or a value at most `-1` selects the source-note branch.
- The full-quantise-mask expression distinguishes `nil`, `-1`, and `0` when the global option is enabled.
- Quantised fixed-note and fixed-note value `0` are valid and playable. Fixed note is applied last.
- Note `0` is truthy in Lua and may be scheduled.
- In `process_params`, `0` is a present lock. The effective off value is parameter-specific, with `-1` used only when `param.off_value` is absent.

Preserve the existing number conversion, rounding, constrain operations, and their position relative to these checks.

## RNG invariants

Mosaic uses the global `math.random` binding in `step.lua` and in the transform helpers. Seeded behavior therefore depends on draw count and order.

- Probability below 100 consumes exactly one draw. Probability 100 consumes none.
- A rejected trig consumes no pitch-random or velocity-random draws.
- On an accepted trig, optional draws occur in this order: bipolar pitch, twos pitch, random velocity.
- `transform_random_value` and `transform_twos_random_value` consume no draw when their amount is below 1; otherwise each consumes one draw.
- Chord-order indexing and delayed chord/arp scheduling introduce no additional random draws.
- Preserve repeated `process_stock_params` evaluation where current short-circuit expressions perform it. Lookup-call count can be observable even where RNG count is unchanged.

## Scheduling-time and callback-time values

`handle_note` resolves and captures the parent event's route, MIDI channel/device or player, root source note, octave, transpose, random shift, velocity, length, mute-root setting, chord definition, strum/arp settings, and chord ordering when the trig is scheduled.

Values intentionally read later are narrower:

- A delayed strum note and a delayed reverse-strum root quantise their captured pitch inputs using the channel's **live `step_scale_number` at callback time**.
- Later arp callbacks also use the channel's live `step_scale_number`; the initial arp note is quantised at scheduling time.
- Delayed strum and arp velocity calculations use the captured parent velocity and captured modifiers.
- Output routing remains the captured parent route/player/device. A later song or channel selection must not retarget an already scheduled note.
- Current selected-channel state consulted by delayed callbacks is presentation state used for dashboard updates, not the note destination.
- `play_note_internal` sends Note On, then schedules Note Off with the captured note, velocity, MIDI channel/device, and player. Nonpositive ordinary gates clamp to zero and release on the same pulse after onset.
- Parameter-slide ring entries capture their parameter descriptor, MIDI channel, NRPN mode, and the current devices table. A MIDI slide callback reads `devices[channel.number].midi_device` when it runs, so an in-place device reassignment is callback-time state. A norns slide callback uses the captured parameter descriptor. Each order-5 callback applies the interpolation value supplied for that callback.

The existing unit anchor `test_delayed_strum_uses_live_scale_but_parent_output_device` in `lib/tests/lib/step_test.lua` characterizes the key mixed-time contract: live scale, captured output route.

## After-step recording

There are two distinct recording points:

- `process_recording_params` runs before `process_params` and before `step.handle`. It emits dirty live-control values for the current step before stored locks are applied.
- `recorder.record_trig_event` runs after `step.handle` in the same order-2 channel action. It still runs for an active trig that probability rejected, because probability rejection returns only from `step.handle`.
- `recorder.record_stored_note_mask_events` runs later in the order-3 end-of-clock action for the just-finished step.

An R06 transition table or extracted resolver must keep these recorder calls outside the probability-accepted note path and retain their current song/channel target resolution.

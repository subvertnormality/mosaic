-- Mutation killers for lib/memory.lua (wave 3 over mutation-bc0570c survivors).
-- README "Memory (undo and redo)": every mask and trig lock action is remembered per
-- channel and can be stepped through; the navigator shows the current position
-- (get_event_count) within the retained history (get_total_event_count).

local mem = include("mosaic/lib/memory")

local function fresh_channel()
  program.init()
  mem.init()
  return program.get_channel(1, 1)
end

-- Records one note mask edit on step 2 of a fresh channel; reports whether memory took it.
local function note_mask_accepted(fields)
  local channel = fresh_channel()
  local data = {step = 2, song_pattern = 1}
  for key, value in pairs(fields) do data[key] = value end
  mem.record_event(1, "note_mask", data)
  return mem.get_total_event_count(1) == 1, channel
end

function test_memory_killer_note_and_velocity_accept_exactly_the_midi_range()
  for _, field in ipairs({"note", "velocity"}) do
    local masks = field == "note" and "step_note_masks" or "step_velocity_masks"
    for _, value in ipairs({0, 1, 64, 126, 127}) do
      local accepted, channel = note_mask_accepted({[field] = value})
      luaunit.assert_true(accepted, field .. " " .. value)
      luaunit.assert_equals(channel[masks][2], value)
    end
    -- -1 is refused for a note; for a velocity it clears the lock (human decision S24)
    for _, value in ipairs(field == "note" and {-1, 128, 200} or {-2, 128, 200}) do
      local accepted, channel = note_mask_accepted({[field] = value})
      luaunit.assert_false(accepted, field .. " " .. value)
      luaunit.assert_nil(channel[masks][2])
    end
  end
end

-- characterisation: a length of 0 is accepted; only negative lengths are refused.
function test_memory_killer_length_accepts_zero_and_refuses_negative()
  local accepted, channel = note_mask_accepted({length = 0})
  luaunit.assert_true(accepted)
  luaunit.assert_equals(channel.step_length_masks[2], 0)
  accepted, channel = note_mask_accepted({length = 16})
  luaunit.assert_true(accepted)
  luaunit.assert_equals(channel.step_length_masks[2], 16)
  accepted, channel = note_mask_accepted({length = -1})
  luaunit.assert_false(accepted)
  luaunit.assert_nil(channel.step_length_masks[2])
end

-- Chord degrees span -14..14 (the range m_midi.lua keeps when recording chords), each at
-- most once; anything else refuses the whole edit.
function test_memory_killer_chord_degrees_accept_distinct_degrees_within_two_octaves()
  local accepted, channel = note_mask_accepted({chord_degrees = {-14, 14, 1, -1}})
  luaunit.assert_true(accepted)
  luaunit.assert_equals(channel.step_chord_masks[2], {-14, 14, 1, -1})
  for _, degrees in ipairs({{-15}, {15}, {1, 1}, {3, -2, 3}, {"x"}, {1, 14, 15}}) do
    accepted, channel = note_mask_accepted({note = 60, chord_degrees = degrees})
    luaunit.assert_false(accepted)
    luaunit.assert_nil(channel.step_chord_masks[2])
    luaunit.assert_nil(channel.step_note_masks[2])
  end
  accepted, channel = note_mask_accepted({note = 60, chord_degrees = 5})
  luaunit.assert_false(accepted)
  luaunit.assert_nil(channel.step_note_masks[2])
end

function test_memory_killer_explicit_record_target_does_not_follow_selection()
  program.init()
  mem.init()
  program.set_selected_song_pattern(1)
  local selected = program.get_channel(1, 1)
  local target = program.get_channel(2, 1)

  mem.record_event_for_target(2, 1, "note_mask", {step = 6, note = 73})

  luaunit.assert_nil(selected.step_note_masks[6])
  luaunit.assert_equals(target.step_note_masks[6], 73)
  luaunit.assert_equals(program.get().selected_song_pattern, 1)
  luaunit.assert_equals(mem.get_total_event_count(1), 1)
  mem.undo(1)
  luaunit.assert_nil(target.step_note_masks[6])
  luaunit.assert_equals(program.get().selected_song_pattern, 1)
end

function test_memory_killer_trig_lock_without_a_parameter_is_not_remembered()
  local channel = fresh_channel()
  mem.record_event(1, "trig_lock", {step = 1, value = 5, song_pattern = 1})
  luaunit.assert_equals(mem.get_total_event_count(1), 0)
  luaunit.assert_equals(mem.get_event_count(1), 0)
  mem.record_event(1, "trig_lock", {step = 1, parameter = 3, value = 5, song_pattern = 1})
  luaunit.assert_equals(mem.get_total_event_count(1), 1)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel, 1, 3), 5)
end

function test_memory_killer_record_without_channel_or_known_type_is_ignored()
  local channel = fresh_channel()
  mem.record_event(nil, "note_mask", {step = 1, note = 60, song_pattern = 1})
  mem.record_event(1, "velocity_lock", {step = 1, note = 60, song_pattern = 1})
  mem.record_event(1, nil, {step = 1, note = 60, song_pattern = 1})
  luaunit.assert_equals(mem.get_total_event_count(1), 0)
  luaunit.assert_nil(channel.step_note_masks[1])
end

-- README "Chords": up to four additional voices. A recorded chord of six keys carries a
-- fifth degree (recorder.lua sets chord[voice - 1]); only the first four are kept.
function test_memory_killer_chord_masks_keep_four_voices()
  local channel = fresh_channel()
  mem.record_event(1, "note_mask", {step = 1, note = 60, chord_degrees = {1, 2, 3, 4, 5}, song_pattern = 1})
  luaunit.assert_equals(channel.step_chord_masks[1], {1, 2, 3, 4})

  channel = fresh_channel()
  mem.record_event(1, "note_mask", {step = 1, note = 60, chord_degrees = {[5] = 3}, song_pattern = 1})
  luaunit.assert_nil(channel.step_chord_masks[1])
  luaunit.assert_equals(mem.get_total_event_count(1), 1)

  mem.record_event(1, "note_mask", {step = 1, chord_degrees = {1, nil, 3}, song_pattern = 1})
  mem.record_event(1, "note_mask", {step = 1, chord_degrees = {[5] = 3}, song_pattern = 1})
  luaunit.assert_equals(channel.step_chord_masks[1], {1, nil, 3})
end

-- characterisation: memory writes the working pattern for the edited step from the
-- event's own fields, else the step's masks, else fixed fallbacks (trig 0, note 0,
-- velocity 100, length 1). The channel edit page rebuilds the working pattern after
-- mask edits and undo/redo (channel_edit_page_ui.lua), which overwrites these values.
function test_memory_killer_working_pattern_takes_event_then_mask_then_fallback_values()
  local channel = fresh_channel()
  local working = channel.working_pattern
  working.trig_values[3] = 1
  working.velocity_values[3] = 80
  working.lengths[3] = 4
  mem.record_event(1, "note_mask", {step = 3, song_pattern = 1})
  luaunit.assert_equals({working.trig_values[3], working.note_mask_values[3], working.velocity_values[3], working.lengths[3]},
    {0, 0, 100, 1})

  mem.record_event(1, "note_mask", {step = 4, trig = 1, note = 62, velocity = 90, length = 6, song_pattern = 1})
  luaunit.assert_equals({working.trig_values[4], working.note_mask_values[4], working.velocity_values[4], working.lengths[4]},
    {1, 62, 90, 6})
  working.trig_values[4], working.note_mask_values[4], working.velocity_values[4], working.lengths[4] = 0, -1, 100, 1
  mem.record_event(1, "note_mask", {step = 4, song_pattern = 1})
  luaunit.assert_equals({working.trig_values[4], working.note_mask_values[4], working.velocity_values[4], working.lengths[4]},
    {1, 62, 90, 6})
end

-- README: "Press K3 to jump directly to the latest action." Redo at the latest action
-- changes nothing and keeps the navigator where it is.
function test_memory_killer_redo_at_the_latest_action_is_a_no_op()
  local channel = fresh_channel()
  mem.record_event(1, "note_mask", {step = 1, note = 60, song_pattern = 1})
  mem.record_event(1, "note_mask", {step = 1, note = 62, song_pattern = 1})
  mem.redo(1)
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {2, 2})
  luaunit.assert_equals(channel.step_note_masks[1], 62)
  mem.undo(1)
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {1, 2})
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  mem.redo(1)
  mem.redo(1)
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {2, 2})
  luaunit.assert_equals(channel.step_note_masks[1], 62)
end

-- A channel with no remembered actions: every navigation is a no-op, both counts are 0,
-- and another channel's history is untouched.
function test_memory_killer_channel_without_history_navigates_as_empty()
  local channel = fresh_channel()
  local other = program.get_channel(1, 2)
  mem.record_event(1, "note_mask", {step = 1, note = 60, song_pattern = 1})
  for _, action in ipairs({mem.undo_all, mem.redo_all, mem.undo, mem.redo, mem.clear}) do
    action(2)
  end
  luaunit.assert_equals({mem.get_event_count(2), mem.get_total_event_count(2)}, {0, 0})
  luaunit.assert_equals(#mem.get_recent_events(2, 5), 0)
  luaunit.assert_nil(other.step_note_masks[1])
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {1, 1})
  luaunit.assert_equals(channel.step_note_masks[1], 60)
end

-- Clearing a channel's memory leaves nothing to redo and a navigator at 0 of 0.
function test_memory_killer_clear_leaves_nothing_to_redo()
  local channel = fresh_channel()
  mem.record_event(1, "note_mask", {step = 1, note = 60, song_pattern = 1})
  mem.record_event(1, "note_mask", {step = 2, note = 62, song_pattern = 1})
  mem.undo(1)
  mem.clear(1)
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {0, 0})
  mem.redo(1)
  mem.redo_all(1)
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {0, 0})
  luaunit.assert_nil(channel.step_note_masks[2])
  luaunit.assert_equals(channel.step_note_masks[1], 60)

  mem.record_event(1, "note_mask", {step = 3, note = 64, song_pattern = 1})
  mem.undo(1)
  mem.reset()
  mem.redo(1)
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {0, 0})
  luaunit.assert_nil(channel.step_note_masks[3])
end

-- A saved and reloaded memory keeps its position and its redo tail.
function test_memory_killer_serialised_memory_keeps_position_and_redo_tail()
  local channel = fresh_channel()
  for i = 1, 3 do
    mem.record_event(1, "note_mask", {step = i, note = 60 + i, song_pattern = 1})
  end
  mem.undo(1)
  local saved = mem.serialize_state()
  mem.init()
  luaunit.assert_equals(mem.get_total_event_count(1), 0)
  mem.deserialize_state(saved)
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {2, 3})
  luaunit.assert_nil(channel.step_note_masks[3])
  mem.redo(1)
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {3, 3})
  luaunit.assert_equals(channel.step_note_masks[3], 63)
end

-- Redo-all re-applies every trig lock parameter edited on one step, not only the last.
function test_memory_killer_redo_all_restores_each_trig_lock_parameter_of_a_step()
  local channel = fresh_channel()
  mem.record_event(1, "trig_lock", {step = 1, parameter = 1, value = 5, song_pattern = 1})
  mem.record_event(1, "trig_lock", {step = 1, parameter = 2, value = 7, song_pattern = 1})
  mem.record_event(1, "trig_lock", {step = 1, parameter = 3, value = 9, song_pattern = 1})
  mem.undo_all(1)
  luaunit.assert_equals({program.get_step_param_trig_lock(channel, 1, 1), program.get_step_param_trig_lock(channel, 1, 2),
    program.get_step_param_trig_lock(channel, 1, 3)}, {})
  mem.redo_all(1)
  luaunit.assert_equals({program.get_step_param_trig_lock(channel, 1, 1), program.get_step_param_trig_lock(channel, 1, 2),
    program.get_step_param_trig_lock(channel, 1, 3)}, {5, 7, 9})
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {3, 3})
end

-- characterisation: a channel remembers its 5000 most recent actions.
function test_memory_killer_history_keeps_the_most_recent_5000_actions()
  fresh_channel()
  for i = 1, 5001 do
    mem.record_event(1, "note_mask", {step = (i - 1) % 64 + 1, note = i % 128, song_pattern = 1})
  end
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {5000, 5000})
  local recent = mem.get_recent_events(1, 1)
  luaunit.assert_equals(recent[1].data.event_data.note, 5001 % 128)
end

-- Undo restores the full prior state of the step: a field the undone event changed but the
-- previous event on the step did not carry is reverted too (bugs.json
-- memory-undo-full-step-state; formerly characterised as suspected defect S42).
function test_memory_killer_undo_reverts_a_field_the_previous_event_did_not_carry()
  local channel = fresh_channel()
  mem.record_event(1, "note_mask", {step = 1, note = 60, song_pattern = 1})
  mem.record_event(1, "note_mask", {step = 1, velocity = 30, song_pattern = 1})
  mem.record_event(1, "note_mask", {step = 1, note = 64, song_pattern = 1})
  mem.undo(1)
  luaunit.assert_equals(mem.get_event_count(1), 2)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 30)
  mem.undo(1)
  luaunit.assert_equals({channel.step_note_masks[1], channel.step_velocity_masks[1]}, {60, nil})
  mem.redo(1)
  mem.redo(1)
  luaunit.assert_equals({channel.step_note_masks[1], channel.step_velocity_masks[1]}, {64, 30})
end

-- Undo keeps a chord set by an earlier edit of the step when the previous edit carried no
-- chord degrees, and redo_all from there keeps it (bugs.json memory-undo-full-step-state;
-- formerly characterised as suspected defect S43).
function test_memory_killer_undo_keeps_an_earlier_chord_and_redo_all_keeps_it()
  local channel = fresh_channel()
  mem.record_event(1, "note_mask", {step = 1, chord_degrees = {1, 3}, song_pattern = 1})
  mem.record_event(1, "note_mask", {step = 1, note = 60, song_pattern = 1})
  mem.record_event(1, "note_mask", {step = 1, note = 62, song_pattern = 1})
  mem.undo(1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_chord_masks[1], {1, 3})
  mem.redo_all(1)
  luaunit.assert_equals(channel.step_note_masks[1], 62)
  luaunit.assert_equals(channel.step_chord_masks[1], {1, 3})
  luaunit.assert_equals({mem.get_event_count(1), mem.get_total_event_count(1)}, {3, 3})
  mem.undo(1)
  mem.undo(1)
  mem.undo(1)
  luaunit.assert_equals({channel.step_note_masks[1], channel.step_chord_masks[1]}, {nil, nil})
end

-- Undo of a trig lock restores only that lock's prior value, whatever edit of another type or
-- trig lock parameter precedes it on the step (bugs.json memory-undo-full-step-state;
-- formerly characterised as suspected defect S44).
function test_memory_killer_undo_of_a_trig_lock_after_another_edit_of_its_step_drops_the_lock()
  local channel = fresh_channel()
  mem.record_event(1, "trig_lock", {step = 1, parameter = 1, value = 5, song_pattern = 1})
  mem.record_event(1, "trig_lock", {step = 1, parameter = 2, value = 7, song_pattern = 1})
  mem.undo(1)
  luaunit.assert_equals(mem.get_event_count(1), 1)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel, 1, 1), 5)
  luaunit.assert_nil(program.get_step_param_trig_lock(channel, 1, 2))

  channel = fresh_channel()
  mem.record_event(1, "note_mask", {step = 1, note = 60, song_pattern = 1})
  mem.record_event(1, "trig_lock", {step = 1, parameter = 2, value = 7, song_pattern = 1})
  mem.undo(1)
  luaunit.assert_equals(mem.get_event_count(1), 1)
  luaunit.assert_nil(program.get_step_param_trig_lock(channel, 1, 2))
  luaunit.assert_equals(channel.step_note_masks[1], 60)

  channel = fresh_channel()
  mem.record_event(1, "trig_lock", {step = 1, parameter = 2, value = 7, song_pattern = 1})
  mem.record_event(1, "trig_lock", {step = 1, parameter = 2, value = 9, song_pattern = 1})
  mem.record_event(1, "note_mask", {step = 1, note = 60, song_pattern = 1})
  mem.undo(1)
  luaunit.assert_equals({program.get_step_param_trig_lock(channel, 1, 2), channel.step_note_masks[1]}, {9, nil})
  mem.undo(1)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel, 1, 2), 7)
end

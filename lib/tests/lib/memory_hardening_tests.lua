-- Deterministic integration hardening for lib/memory.lua.
-- README.md:698-707: every mask and trig-lock action is remembered per channel;
-- undo/redo navigates that history and a new edit after undo truncates the redo tail.

local hardening_memory = include("mosaic/lib/memory")

local function fresh()
  program.init()
  hardening_memory.init()
end

local function assert_position(current, total)
  luaunit.assert_equals(
    {hardening_memory.get_event_count(1), hardening_memory.get_total_event_count(1)},
    {current, total})
end

local MASK_FIELDS = {
  {event = "trig", table_name = "step_trig_masks", values = {0, 1, 0}},
  {event = "note", table_name = "step_note_masks", values = {0, 127, 64}},
  {event = "velocity", table_name = "step_velocity_masks", values = {0, 127, 63}},
  {event = "length", table_name = "step_length_masks", values = {0, 96, 1}}
}

function test_hardening_memory_mask_fields_cross_song_bounds_undo_redo_branch_and_serialisation()
  for song_pattern = 1, 16 do
    for field_index, field in ipairs(MASK_FIELDS) do
      fresh()
      local step = (song_pattern + field_index) % 2 == 0 and 1 or 64
      local channel = program.get_channel(song_pattern, 1)
      local data1 = {step = step, song_pattern = song_pattern}
      local data2 = {step = step, song_pattern = song_pattern}
      local data3 = {step = step, song_pattern = song_pattern}
      data1[field.event] = field.values[1]
      data2[field.event] = field.values[2]
      data3[field.event] = field.values[3]

      hardening_memory.record_event(1, "note_mask", data1)
      hardening_memory.record_event(1, "note_mask", data2)
      assert_position(2, 2)
      luaunit.assert_equals(channel[field.table_name][step], field.values[2])

      hardening_memory.undo(1)
      assert_position(1, 2)
      luaunit.assert_equals(channel[field.table_name][step], field.values[1])
      local saved = hardening_memory.serialize_state()
      hardening_memory.init()
      hardening_memory.deserialize_state(saved)
      assert_position(1, 2)
      hardening_memory.redo_all(1)
      luaunit.assert_equals(channel[field.table_name][step], field.values[2])

      hardening_memory.undo(1)
      hardening_memory.record_event(1, "note_mask", data3)
      assert_position(2, 2)
      luaunit.assert_equals(channel[field.table_name][step], field.values[3])
      hardening_memory.redo(1)
      hardening_memory.redo_all(1)
      assert_position(2, 2)
      luaunit.assert_equals(channel[field.table_name][step], field.values[3])

      local other_song = song_pattern == 16 and 15 or 16
      luaunit.assert_nil(program.get_channel(other_song, 1)[field.table_name][step])
    end
  end
end

function test_hardening_memory_every_chord_voice_survives_navigation_branch_and_reload()
  for voice = 1, 4 do
    fresh()
    local channel = program.get_channel(16, 1)
    local base = {1, 3, 5, 7}
    local changed = {[voice] = 8 + voice}
    local branch = {[voice] = -voice}
    hardening_memory.record_event(1, "note_mask", {
      step = 64, chord_degrees = base, song_pattern = 16})
    hardening_memory.record_event(1, "note_mask", {
      step = 64, chord_degrees = changed, song_pattern = 16})
    local expected = {1, 3, 5, 7}; expected[voice] = 8 + voice
    luaunit.assert_equals(channel.step_chord_masks[64], expected)

    hardening_memory.undo(1)
    luaunit.assert_equals(channel.step_chord_masks[64], base)
    local saved = hardening_memory.serialize_state()
    hardening_memory.init(); hardening_memory.deserialize_state(saved)
    hardening_memory.redo(1)
    luaunit.assert_equals(channel.step_chord_masks[64], expected)

    hardening_memory.undo(1)
    hardening_memory.record_event(1, "note_mask", {
      step = 64, chord_degrees = branch, song_pattern = 16})
    local branched = {1, 3, 5, 7}; branched[voice] = -voice
    luaunit.assert_equals(channel.step_chord_masks[64], branched)
    hardening_memory.redo_all(1)
    luaunit.assert_equals(channel.step_chord_masks[64], branched)
    assert_position(2, 2)
  end
end

function test_hardening_memory_all_ten_lock_slots_cross_song_bounds_branch_and_reload()
  for slot = 1, 10 do
    fresh()
    local song_pattern = slot % 2 == 0 and 1 or 16
    local step = slot % 2 == 0 and 1 or 64
    local channel = program.get_channel(song_pattern, 1)
    hardening_memory.record_event(1, "trig_lock", {
      step = step, parameter = slot, value = slot, song_pattern = song_pattern})
    hardening_memory.record_event(1, "trig_lock", {
      step = step, parameter = slot, value = 100 + slot, song_pattern = song_pattern})
    luaunit.assert_equals(program.get_step_param_trig_lock(channel, step, slot), 100 + slot)

    hardening_memory.undo(1)
    luaunit.assert_equals(program.get_step_param_trig_lock(channel, step, slot), slot)
    local saved = hardening_memory.serialize_state()
    hardening_memory.init(); hardening_memory.deserialize_state(saved)
    hardening_memory.redo_all(1)
    luaunit.assert_equals(program.get_step_param_trig_lock(channel, step, slot), 100 + slot)

    hardening_memory.undo(1)
    hardening_memory.record_event(1, "trig_lock", {
      step = step, parameter = slot, value = 50 + slot, song_pattern = song_pattern})
    hardening_memory.redo_all(1)
    luaunit.assert_equals(program.get_step_param_trig_lock(channel, step, slot), 50 + slot)
    assert_position(2, 2)
    local other_slot = slot == 10 and 9 or 10
    luaunit.assert_nil(program.get_step_param_trig_lock(channel, step, other_slot))
  end
end

-- README.md:698-705: K2 returns to the beginning of Memory. When bounded history has
-- wrapped, that beginning is the state immediately before its oldest retained action.
-- S58's production-capacity behavior baseline is M-MEMORY-014.
function test_hardening_memory_wrap_retains_exact_floor_for_undo_and_undo_all()
  local original_max = hardening_memory.max_history_size
  hardening_memory.max_history_size = 3
  fresh()
  local channel = program.get_channel(1, 1)
  for note = 60, 63 do
    hardening_memory.record_event(1, "note_mask", {step = 1, note = note, song_pattern = 1})
  end
  hardening_memory.undo(1); luaunit.assert_equals(channel.step_note_masks[1], 62)
  hardening_memory.undo(1); luaunit.assert_equals(channel.step_note_masks[1], 61)
  hardening_memory.undo(1); luaunit.assert_equals(channel.step_note_masks[1], 60)

  fresh()
  for note = 60, 63 do
    hardening_memory.record_event(1, "note_mask", {step = 1, note = note, song_pattern = 1})
  end
  local saved = hardening_memory.serialize_state()
  hardening_memory.init(); hardening_memory.deserialize_state(saved)
  hardening_memory.undo_all(1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  hardening_memory.max_history_size = original_max
end


function test_hardening_memory_legacy_serialisation_without_prior_state_still_undoes()
  fresh()
  local channel = program.get_channel(1, 1)
  hardening_memory.record_event(1, "note_mask", {step = 1, note = 60, song_pattern = 1})
  hardening_memory.record_event(1, "note_mask", {step = 1, note = 62, song_pattern = 1})
  local saved = hardening_memory.serialize_state()
  for _, event in pairs(saved.channels[1].buffer) do event.data.prior_state = nil end
  hardening_memory.init(); hardening_memory.deserialize_state(saved)
  hardening_memory.undo(1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  hardening_memory.undo(1)
  luaunit.assert_nil(channel.step_note_masks[1])
end

function test_hardening_memory_wrap_retains_independent_floors_for_interleaved_keys()
  local original_max = hardening_memory.max_history_size
  hardening_memory.max_history_size = 3
  fresh()
  local channel = program.get_channel(1, 1)
  for _, event in ipairs({{1, 60}, {2, 70}, {1, 61}, {2, 71}}) do
    hardening_memory.record_event(1, "note_mask", {step = event[1], note = event[2], song_pattern = 1})
  end
  hardening_memory.undo_all(1)
  luaunit.assert_equals(channel.step_note_masks[1], 60, "floor of key whose older edit rolled out")
  luaunit.assert_nil(channel.step_note_masks[2], "floor of key whose first edit is retained")
  hardening_memory.max_history_size = original_max
end

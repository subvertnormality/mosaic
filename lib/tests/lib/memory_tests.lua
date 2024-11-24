local memory = include("mosaic/lib/memory")

function test_memory_init_should_create_empty_event_store_for_each_channel()
  memory.init()
  program.init()

  for i = 1, 16 do
    local state = memory.get_state(i)
  
    luaunit.assert_equals(#state.event_history, 0)
    luaunit.assert_equals(state.current_event_index, 0)
  end

end

function test_memory_should_add_single_note()
  memory.init()
  program.init()

  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)

  memory.record_event(channel_number, "note_mask", {
    trig = 1,
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
end

function test_memory_should_add_note_mask()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)

  memory.record_event(channel_number, "note_mask", {
    trig = 1,
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5},
    song_pattern = song_pattern_number
  })

  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end



function test_memory_should_undo_last_note()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.undo(channel_number)
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
end

function test_memory_should_redo_undone_note()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.undo(channel_number)
  memory.redo(channel_number)
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 64)
end

function test_memory_should_clear_redo_history_after_new_note()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.undo(channel_number)
  memory.record_event(channel_number, "note_mask", {
    step = 2,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  local state = memory.get_state(channel_number)
  luaunit.assert_equals(state.event_history.size, 2)
  luaunit.assert_equals(channel.step_note_masks[2], 67)
end

function test_memory_should_maintain_separate_channels()
  memory.init()
  program.init()
  local channel_number_1 = 1
  local channel_number_2 = 2
  local song_pattern_number = 1
  local channel1 = program.get_channel(song_pattern_number, channel_number_1)
  local channel2 = program.get_channel(song_pattern_number, channel_number_2)
  
  memory.record_event(channel_number_1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number_2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_channel_history_should_remain_intact_when_another_channel_history_is_wiped_after_new_event_added_in_middle_of_history()
  memory.init()
  program.init()
  
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Add events in specific order
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(1, "note_mask", {
    step = 2,
    note = 61,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  
  memory.record_event(2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(2, "note_mask", {
    step = 2,
    note = 66,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })

  memory.undo(1)

  memory.record_event(1, "note_mask", {
    step = 2,
    note = 61,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  

  luaunit.assert_equals(memory.get_event_count(1), 2)
  luaunit.assert_equals(#memory.get_recent_events(1), 2)
end

function test_memory_should_handle_undo_when_empty()
  memory.init()
  program.init()

  local channel2 = program.get_channel(1, 2)
  
  memory.undo(channel2.number)
  
  local channel2_state = memory.get_state(channel2.number)
  luaunit.assert_equals(channel2_state.current_event_index, 0)
  luaunit.assert_equals(#channel2_state.event_history, 0)
end

function test_memory_should_handle_redo_when_empty()
  memory.init()
  program.init()

  local channel_number = 16
  local song_pattern_number = 1
  local channel16 = program.get_channel(channel_number, song_pattern_number)

  memory.redo(channel_number)
  
  local channel16_state = memory.get_state(channel16.number)
  luaunit.assert_equals(channel16_state.current_event_index, 0)
  luaunit.assert_equals(#channel16_state.event_history, 0)
end

function test_memory_should_handle_chord_after_note_on_same_step()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    chord_degrees = {1, 3, 5},
    song_pattern = song_pattern_number
  })
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  memory.undo(channel_number)
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_memory_should_maintain_correct_velocities_during_undo_redo()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 2
  local channel = program.get_channel(song_pattern_number, channel_number)
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 80,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  
  memory.undo(channel_number)
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  memory.redo(channel_number)
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
end

function test_memory_should_handle_empty_chord_degrees()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {},
    song_pattern = song_pattern_number
  })
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_memory_should_preserve_original_state()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Set up initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  channel.step_length_masks[1] = 2
  
  -- Record new note
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  -- Verify state changed
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  -- Undo should restore original state
  memory.undo(channel_number)
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
end

function test_memory_should_store_deep_copies_of_chord_masks()
  memory.init()
  program.init()
  
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Set up initial chord
  if not channel.step_chord_masks then channel.step_chord_masks = {} end
  channel.step_chord_masks[1] = {1, 3, 5}
  
  -- Add new chord
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {2, 4, 6},
    song_pattern = 1
  })
  
  -- Modify original chord array
  channel.step_chord_masks[1][1] = 7
  
  -- Undo should restore original values, not modified ones
  memory.undo(channel_number)
  
  luaunit.assert_equals(channel.step_chord_masks[1][1], 1)
  luaunit.assert_equals(channel.step_chord_masks[1][2], 3)
  luaunit.assert_equals(channel.step_chord_masks[1][3], 5)
end

function test_memory_should_preserve_event_order_during_undo()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(song_pattern_number, channel_number)
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 2,
    note = 62,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })

  memory.record_event(channel_number, "note_mask", {
    step = 3,
    note = 64,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  -- Get initial event order
  local state = memory.get_state(channel_number)
  local initial_events = {}
  for i, event in ipairs(state.event_history) do
    initial_events[i] = event.data.event_data.note
  end
  
  -- Undo everything
  memory.undo(channel_number)
  memory.undo(channel_number)
  memory.undo(channel_number)
  
  -- Redo everything
  memory.redo(channel_number)
  memory.redo(channel_number)
  memory.redo(channel_number)
  
  -- Check event order is preserved
  state = memory.get_state(channel_number)
  for i, event in ipairs(state.event_history) do
    luaunit.assert_equals(event.data.event_data.note, initial_events[i])
  end
end

function test_memory_should_handle_nil_chord_degrees_correctly()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = nil,
    song_pattern = 1
  })
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 62,
    velocity = 95,
    length = 1,
    chord_degrees = {},
    song_pattern = 1
  })
  
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_memory_should_update_working_pattern()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  memory.record_event(channel_number, "note_mask", {
    trig = 1,
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  -- Check masks are set
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  -- Check working pattern is updated
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 1)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 1)
end

function test_memory_should_restore_working_pattern_on_undo()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Add two steps
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })
  
  -- Undo last step
  memory.undo(channel_number)
  
  -- Check working pattern reflects first step
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
end

function test_memory_should_clear_working_pattern_on_full_undo()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Add and undo a step
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.undo(channel_number)
  
  -- Check working pattern is cleared
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 1)
end

function test_memory_should_handle_multiple_channels_working_pattern()
  memory.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Add notes to different patterns
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })
  
  -- Check working patterns are independent
  luaunit.assert_equals(channel1.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel2.working_pattern.note_mask_values[1], 64)
end

function test_memory_should_preserve_working_pattern_original_state()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Set up initial working pattern state
  channel.working_pattern.trig_values[1] = 1
  channel.working_pattern.note_mask_values[1] = 48
  channel.working_pattern.velocity_values[1] = 70
  channel.working_pattern.lengths[1] = 2
  
  -- Add new note
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  -- Verify working pattern changed
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  -- Undo should restore original working pattern
  memory.undo(channel_number)
  
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 1)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 48)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 70)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end

function test_memory_should_handle_working_pattern_multiple_edits()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Add series of edits
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  -- Verify final working pattern state
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 67)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 80)
  
  -- Undo each edit and verify working pattern
  memory.undo(channel_number)  -- Back to second edit
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
  
  memory.undo(channel_number)  -- Back to first edit
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  memory.undo(channel_number)  -- Back to original
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
end

function test_memory_should_preserve_working_pattern_during_redo()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Add and undo some steps
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })

  memory.undo(channel_number)
  memory.undo(channel_number)
  
  -- Verify back to initial state
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
  
  -- Redo and verify working pattern restored
  memory.redo(channel_number)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  memory.redo(channel_number)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
end

function test_memory_should_preserve_original_chord_state()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Set up initial chord state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  channel.step_length_masks[1] = 2
  if not channel.step_chord_masks then channel.step_chord_masks = {} end
  channel.step_chord_masks[1] = {1, 4, 7}
  
  -- Record new note (should not affect chord)
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  -- Verify chord preserved
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 4)
  luaunit.assert_equals(chord_mask[3], 7)
  
  -- Explicitly clear chord
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = nil,
    chord_degrees = {},
    song_pattern = song_pattern_number
  })
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_memory_should_handle_multiple_edits_to_same_step()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Set up initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  
  -- Make multiple edits
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 67)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  
  -- Undo should go back through the history one step at a time
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
end

function test_memory_should_preserve_nil_states()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Record new note in empty step
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  -- Verify note was added
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Undo should restore nil state
  memory.undo(channel_number)
  
  luaunit.assert_equals(channel.step_trig_masks[1], nil)
  luaunit.assert_equals(channel.step_note_masks[1], nil)
  luaunit.assert_equals(channel.step_velocity_masks[1], nil)
  luaunit.assert_equals(channel.step_length_masks[1], nil)
end

function test_memory_should_handle_mixed_note_and_chord_edits_on_same_step()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Set initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  
  -- Series of mixed edits - chords should remain unless explicitly changed
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    chord_degrees = {1, 3, 5},
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 72,
    velocity = 110,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  luaunit.assert_equals(channel.step_velocity_masks[1], 110)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Explicitly clear chord
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = nil,
    chord_degrees = {},
    song_pattern = song_pattern_number
  })

  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_memory_should_handle_interleaved_step_edits()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Set initial states
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_trig_masks[2] = 1
  channel.step_note_masks[2] = 50
  
  -- Interleaved edits
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 2,
    note = 62,
    velocity = 90,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 110,
    length = 1,
    song_pattern = song_pattern_number
  })

  memory.record_event(channel_number, "note_mask", {
    step = 2,
    note = 65,
    velocity = 95,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_note_masks[2], 65)
  
  -- Undo should affect steps independently
  memory.undo(channel_number)  -- Undo step 2 second edit
  luaunit.assert_equals(channel.step_note_masks[1], 64)  -- Step 1 unchanged
  luaunit.assert_equals(channel.step_note_masks[2], 62)  -- Step 2 back one
  
  memory.undo(channel_number)  -- Undo step 1 second edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 62)
  
  memory.undo(channel_number)  -- Undo step 2 first edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 50)
  
  memory.undo(channel_number)  -- Undo step 1 first edit
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_note_masks[2], 50)
end

function test_memory_should_handle_partial_undo_with_new_edits()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  
  -- First series of edits
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  -- Partial undo
  memory.undo(channel_number)
  memory.undo(channel_number)
  
  -- Should be back to first edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Add new edits
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 72,
    velocity = 110,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 74,
    velocity = 115,
    length = 1,
    song_pattern = 1
  })
  
  -- Verify new state
  luaunit.assert_equals(channel.step_note_masks[1], 74)
  
  -- Undo through new edits
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Back to original
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
end

function test_memory_should_preserve_original_state_across_multiple_edits_and_song_patterns()
  memory.init()
  program.init()
  local s1_channel1 = program.get_channel(1, 1)
  local s1_channel2 = program.get_channel(1, 2)
  local s2_channel1 = program.get_channel(2, 1)
  local s2_channel2 = program.get_channel(2, 2) 


  
  -- Set up complex initial state
  s1_channel1.step_trig_masks[1] = 1
  s1_channel1.step_note_masks[1] = 40
  s1_channel1.step_velocity_masks[1] = 70
  if not s1_channel1.step_chord_masks then s1_channel1.step_chord_masks = {} end
  s1_channel1.step_chord_masks[1] = {1, 4, 7}

  -- Set up complex initial state
  s1_channel2.step_trig_masks[1] = 1
  s1_channel2.step_note_masks[1] = 41
  s1_channel2.step_velocity_masks[1] = 71
  if not s1_channel2.step_chord_masks then s1_channel2.step_chord_masks = {} end
  s1_channel2.step_chord_masks[1] = {2, 5, 8}

  -- Set up complex initial state
  s2_channel1.step_trig_masks[1] = 1
  s2_channel1.step_note_masks[1] = 42
  s2_channel1.step_velocity_masks[1] = 72
  if not s2_channel1.step_chord_masks then s2_channel1.step_chord_masks = {} end
  s2_channel1.step_chord_masks[1] = {3, 6, 9}

  -- Set up complex initial state
  s2_channel2.step_trig_masks[1] = 1
  s2_channel2.step_note_masks[1] = 43
  s2_channel2.step_velocity_masks[1] = 73
  if not s2_channel2.step_chord_masks then s2_channel2.step_chord_masks = {} end
  s2_channel2.step_chord_masks[1] = {4, 7, 10}
  
  -- Multiple edits of different types
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    chord_degrees = {1, 3, 5},
    song_pattern = 2
  })

  memory.record_event(1, "note_mask", {
    step = 1,
    note = 72,
    velocity = 110,
    length = 1,
    song_pattern = 2
  })

  memory.record_event(2, "note_mask", {
    step = 1,
    note = 76,
    velocity = 95,
    length = 1,
    chord_degrees = {1, 3, 5},
    song_pattern = 2 -- note: different song pattern
  })
  
  -- Undo all the way back
  memory.undo(2)
  memory.undo(1)
  memory.undo(2)
  memory.undo(1)
  
  -- Verify original state is perfectly preserved
  luaunit.assert_equals(s1_channel1.step_trig_masks[1], 1)
  luaunit.assert_equals(s1_channel1.step_note_masks[1], 40)
  luaunit.assert_equals(s1_channel1.step_velocity_masks[1], 70)
  local original_chord = s1_channel1.step_chord_masks[1]
  luaunit.assert_equals(original_chord[1], 1)
  luaunit.assert_equals(original_chord[2], 4)
  luaunit.assert_equals(original_chord[3], 7)

  luaunit.assert_equals(s1_channel2.step_trig_masks[1], 1)
  luaunit.assert_equals(s1_channel2.step_note_masks[1], 41)
  luaunit.assert_equals(s1_channel2.step_velocity_masks[1], 71)
  local original_chord = s1_channel2.step_chord_masks[1]
  luaunit.assert_equals(original_chord[1], 2)
  luaunit.assert_equals(original_chord[2], 5)
  luaunit.assert_equals(original_chord[3], 8)

  luaunit.assert_equals(s2_channel1.step_trig_masks[1], 1)
  luaunit.assert_equals(s2_channel1.step_note_masks[1], 42)
  luaunit.assert_equals(s2_channel1.step_velocity_masks[1], 72)
  local original_chord = s2_channel1.step_chord_masks[1]
  luaunit.assert_equals(original_chord[1], 3)
  luaunit.assert_equals(original_chord[2], 6)
  luaunit.assert_equals(original_chord[3], 9)

  luaunit.assert_equals(s2_channel2.step_trig_masks[1], 1)
  luaunit.assert_equals(s2_channel2.step_note_masks[1], 43)
  luaunit.assert_equals(s2_channel2.step_velocity_masks[1], 73)
  local original_chord = s2_channel2.step_chord_masks[1]
  luaunit.assert_equals(original_chord[1], 4)
  luaunit.assert_equals(original_chord[2], 7)
  luaunit.assert_equals(original_chord[3], 10)

end

function test_memory_should_preserve_working_pattern_when_clearing_redo_history()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Create some history
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })

  memory.undo(channel_number)
  
  -- Working pattern should show first note
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  
  -- Add new note (clearing redo history)
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  -- Working pattern should show new note
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 67)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 80)
  
  -- Undo should restore to first note
  memory.undo(channel_number)
  
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
end

function test_memory_should_maintain_working_pattern_across_multiple_patterns()
  memory.init()
  program.init()
  
  -- Set up two patterns
  program.set_selected_song_pattern(1)
  local channel1 = program.get_channel(1, 1)
  
  program.set_selected_song_pattern(2)
  local channel2 = program.get_channel(2, 2)
  
  -- Add notes to different patterns

  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  -- Verify working patterns are independent
  luaunit.assert_equals(channel1.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel2.working_pattern.note_mask_values[1], 64)
  
  -- Undo second pattern
  memory.undo(2)
  
  -- Pattern 1 should be unchanged, pattern 2 cleared
  luaunit.assert_equals(channel1.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel2.working_pattern.note_mask_values[1], 0)
  luaunit.assert_equals(channel2.working_pattern.trig_values[1], 0)
end

function test_memory_should_handle_working_pattern_with_chords()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Add chord
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5},
    song_pattern = song_pattern_number
  })
  
  -- Verify working pattern values
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  -- Add normal note (clearing chord)
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  -- Verify working pattern updated
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
  
  -- Undo should restore chord state in working pattern
  memory.undo(channel_number)
  
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
end

function test_memory_should_handle_invalid_step_numbers()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Test negative step
  memory.record_event(channel_number, "note_mask", {
    step = -1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  luaunit.assert_equals(channel.step_note_masks[-1], nil)
  
  -- Test zero step
  memory.record_event(channel_number, "note_mask", {
    step = 0,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })

  luaunit.assert_equals(channel.step_note_masks[0], nil)
  
  -- Test non-numeric step
  memory.record_event(channel_number, "note_mask", {
    step = "invalid",
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  luaunit.assert_equals(channel.step_note_masks["invalid"], nil)
  
  local state = memory.get_state(channel_number)
  luaunit.assert_equals(#state.event_history, 0)
end

function test_memory_should_persist_state_across_pattern_switches()
  memory.init()
  program.init()
  
  -- Add notes to pattern 1
  local channel_number = 1
  local song_pattern_1 = 1
  local song_pattern_2 = 2
  local channel = program.get_channel(song_pattern_1, channel_number)
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_1
  })
  
  -- Switch to pattern 2 and add notes
  program.set_selected_song_pattern(song_pattern_2)
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = song_pattern_2
  })
  
  -- Switch back to pattern 1 and verify state
  program.set_selected_song_pattern(song_pattern_1)
  channel = program.get_channel(song_pattern_1, channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Switch to pattern 2 and verify state
  program.set_selected_song_pattern(song_pattern_2)
  channel = program.get_channel(song_pattern_2, channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  
  -- Undo in pattern 2
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], nil)
  
  -- Switch to pattern 1 and verify unaffected
  program.set_selected_song_pattern(song_pattern_1)
  channel = program.get_channel(song_pattern_1, channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
end

function test_memory_should_respect_song_pattern_value_across_pattern_switches()
  memory.init()
  program.init()
  
  -- Add notes to pattern 1 channel 1 
  program.set_selected_song_pattern(1)
  local s1_channel1 = program.get_channel(1, 1)
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  -- Switch to pattern 2 and add notes
  program.set_selected_song_pattern(2)
  local s2_channel1 = program.get_channel(2, 1)

  memory.record_event(2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })

  local s2_channel2 = program.get_channel(2, 2)
  
  -- Switch back to pattern 1 and verify state
  program.set_selected_song_pattern(1)
  luaunit.assert_equals(s1_channel1.step_note_masks[1], 60)
  
  -- Switch to pattern 2 and verify state
  program.set_selected_song_pattern(2)
  luaunit.assert_equals(s2_channel2.step_note_masks[1], 64)
  
  -- Undo in channel 2
  memory.undo(2)
  luaunit.assert_equals(s2_channel2.step_note_masks[1], nil)
  luaunit.assert_equals(s2_channel1.step_note_masks[1], nil)
  
  -- Switch to pattern 1 and verify unaffected
  program.set_selected_song_pattern(1)
  luaunit.assert_equals(s1_channel1.step_note_masks[1], 60)
end



function test_memory_should_count_events_per_channel()
  memory.init()
  program.init()
  
  -- Add notes to different patterns/channels
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(1, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  memory.record_event(2, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = 3
  })
  
  luaunit.assert_equals(memory.get_event_count(1), 2)
  luaunit.assert_equals(memory.get_event_count(2), 1)
  -- Test after undo
  memory.undo(1)
  luaunit.assert_equals(memory.get_event_count(1), 1)
end


function test_memory_should_handle_custom_length()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2,
    song_pattern = 1
  })
  
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end


function test_memory_should_preserve_length_during_undo_redo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2,
    song_pattern = 1
  })

  memory.record_event(1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 3,
    song_pattern = 1
  })
  
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  
  memory.undo(1)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  memory.redo(1)
  luaunit.assert_equals(channel.step_length_masks[1], 3)
end



function test_memory_should_maintain_length_in_working_pattern()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 3,
    song_pattern = 1
  })
  
  -- Verify length in both masks and working pattern
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 3)
  
  memory.undo(1)
  
  -- Verify length cleared from both
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 1)  -- Default value
end


function test_memory_should_preserve_original_length_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  channel.step_length_masks[1] = 4
  channel.working_pattern.lengths[1] = 4
  
  -- Record new note with different length
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2,
    song_pattern = 1
  })
  
  -- Verify state changed
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
  
  -- Undo should restore original length
  memory.undo(1)
  luaunit.assert_equals(channel.step_length_masks[1], 4)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 4)
end


function test_memory_should_preserve_chord_when_only_changing_length()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state with chord
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2,
    chord_degrees = {1, 3, 5},
    song_pattern = 1
  })
  
  -- Modify only length
  memory.record_event(1, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 3,
    chord_degrees = nil,
    song_pattern = 1
  })
  
  -- Verify chord is preserved
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Verify other values
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 3)
end


function test_memory_should_handle_partial_updates()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  -- Update only velocity and length
  memory.record_event(1, "note_mask", {
    step = 1,
    note = nil,
    velocity = 80,
    length = 2,
    song_pattern = 1
  })
  
  -- Note should be preserved, velocity and length updated
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  -- Update only note and length
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 64,
    velocity = nil,
    length = 3,
    song_pattern = 1
  })
  
  -- Note and length should be updated, velocity preserved
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  luaunit.assert_equals(channel.step_length_masks[1], 3)
end



function test_memory_should_handle_undo_redo_with_partial_updates()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5},
    song_pattern = 1
  })
  
  -- Update only length
  memory.record_event(1, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 2,
    song_pattern = 1
  })
  
  -- Verify only length changed
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  
  -- Undo should restore original length only
  memory.undo(1)
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  
  -- Redo should restore only length change
  memory.redo(1)
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
end


function test_memory_should_allow_all_nil_values_except_step()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2,
    chord_degrees = {1, 3, 5},
    song_pattern = 1
  })
  
  -- Should preserve all values when using nil
  memory.record_event(1, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = nil,
    chord_degrees = nil,
    song_pattern = 1
  })
  
  -- Verify all original values preserved
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end



function test_memory_should_validate_partial_updates()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test various partial update combinations
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = nil,
    length = nil,
    chord_degrees = nil,
    song_pattern = 1
  })
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  memory.record_event(1, "note_mask", {
    step = 1,
    note = nil,
    velocity = 100,
    length = nil,
    chord_degrees = nil,
    song_pattern = 1
  })
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  memory.record_event(1, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 2,
    chord_degrees = nil,
    song_pattern = 1
  })
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  memory.record_event(1, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = nil,
    chord_degrees = {1, 3},
    song_pattern = 1
  })
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  
  -- Mixed combinations
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = nil,
    chord_degrees = nil,
    song_pattern = 1
  })
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  memory.record_event(1, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 3,
    chord_degrees = {1, 4},
    song_pattern = 1
  })
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 4)
end


function test_memory_should_respect_max_history_size()
  memory.init()

  memory.max_history_size = 1000

  program.init()
  local channel_number = 1
  local channel = program.get_channel(1, channel_number)
  
  -- Add more than MAX_HISTORY_SIZE events
  for i = 1, 1001 do  -- MAX_HISTORY_SIZE is 1000
    memory.record_event(1, "note_mask", {
      step = i % 16 + 1,
      note = 60 + (i % 12),
      velocity = 100,
      length = 1,
      song_pattern = 1
    })
  end
  
  local state = memory.get_state(channel_number)
  
  -- Should be limited to MAX_HISTORY_SIZE
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- First event should be second event since first was pushed out
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.event_data.note, 62)
  
  -- Last event should be the most recent one
  local last_event = state.event_history:get(1000)
  luaunit.assert_equals(last_event.data.event_data.note, 60 + (1001 % 12))
end



function test_memory_should_handle_ring_buffer_wrapping()
  memory.init()

  memory.max_history_size = 1000

  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Create predictable sequence using modulo to keep notes in valid MIDI range
  for i = 1, 1000 do
    memory.record_event(1, "note_mask", {
      step = i % 16 + 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  -- Add one more to cause wrap
  memory.record_event(1, "note_mask", {
    step = 1,
    note = (1001 % 128),
    velocity = 100,
    length = 1
  })
  
  local state = memory.get_state(1)
  
  -- Buffer should still be at max size
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- First event should be note value (2 % 128) (since 1 was pushed out)
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.event_data.note, (2 % 128))
  
  -- Last event should be (1001 % 128)
  local last_event = state.event_history:get(1000)
  luaunit.assert_equals(last_event.data.event_data.note, (1001 % 128))
end



function test_ring_buffer_should_maintain_correct_order_during_wrap()
  memory.init()

  memory.max_history_size = 1000

  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Fill buffer
  for i = 1, 998 do
    memory.record_event(1, "note_mask", {
      step = 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state(1)
  local initial_size = state.event_history:get_size()
  luaunit.assert_equals(initial_size, 998)
  
  -- Add wrap boundary notes
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(1, "note_mask", {
    step = 1,
    note = 62,
    velocity = 100,
    length = 1
  })

  memory.record_event(1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 100,
    length = 1
  })
  
  state = memory.get_state(1)
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- First event should be the second one after wrap
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.event_data.note, 2)
end


function test_ring_buffer_should_handle_edge_case_at_max_size()
  memory.init()

  memory.max_history_size = 1000

  program.init()
  local channel = program.get_channel(1, 16)
  
  -- Fill buffer exactly to max size
  for i = 1, 1000 do
    memory.record_event(16, "note_mask", {
      step = 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state(16)
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- other channel states remain empty
  luaunit.assert_equals(memory.get_state(1).event_history:get_size(), 0)

  -- Add one more event
  memory.record_event(16, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Verify size hasn't changed but content has
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.event_data.note, (2 % 128))
end

function test_ring_buffer_truncation_should_respect_wrap_point()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 2)
  
  -- Add 100 events
  for i = 1, 100 do
    memory.record_event(2, "note_mask", {
      step = 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state(2)
  luaunit.assert_equals(state.current_event_index, 100)
  
  -- Undo 25 events
  for _ = 1, 25 do
    memory.undo(2)
  end
  
  state = memory.get_state(2)
  luaunit.assert_equals(state.current_event_index, 75)
  
  -- Add new event
  memory.record_event(2, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  state = memory.get_state(2)
  luaunit.assert_equals(state.current_event_index, 76)
end



function test_memory_should_undo_all_in_single_channel_across_all_song_patterns()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Set initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  
  channel.step_trig_masks[3] = 1
  channel.step_note_masks[3] = 50
  channel.step_velocity_masks[3] = 80
  if not channel.step_chord_masks then channel.step_chord_masks = {} end
  channel.step_chord_masks[3] = {1, 3, 5}
  
  -- Add multiple steps
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(1, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(2, "note_mask", { -- note channel 2
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })


  memory.record_event(1, "note_mask", {
    step = 3,
    note = 67,
    velocity = 85,
    length = 1,
    chord_degrees = {2, 4, 6},
    song_pattern = 20
  })
  
  -- Undo all channel 1 events at once
  memory.undo_all(1)
  
  -- Verify original states restored
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
  
  -- Step 2 had no original state
  luaunit.assert_equals(channel.step_trig_masks[2], nil)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
  luaunit.assert_equals(channel.step_velocity_masks[2], nil)
  
  -- Step 3 should restore original state including chord
  luaunit.assert_equals(channel.step_trig_masks[3], 1)
  luaunit.assert_equals(channel.step_note_masks[3], 50)
  luaunit.assert_equals(channel.step_velocity_masks[3], 80)
  luaunit.assert_equals(channel.step_chord_masks[3][1], 1)
  luaunit.assert_equals(channel.step_chord_masks[3][2], 3)
  luaunit.assert_equals(channel.step_chord_masks[3][3], 5)
  
  -- Verify index reset
  local state = memory.get_state(1)
  luaunit.assert_equals(state.current_event_index, 0)

  -- Verify channel 2 was unaffected
  luaunit.assert_equals(channel2.step_note_masks[1], 60)

end



function test_memory_should_handle_undo_all_with_no_original_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- All steps start with nil state
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(1, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })
  
  memory.undo_all(1)
  
  -- Verify steps return to nil state
  luaunit.assert_equals(channel.step_trig_masks[1], nil)
  luaunit.assert_equals(channel.step_note_masks[1], nil)
  luaunit.assert_equals(channel.step_velocity_masks[1], nil)
  
  luaunit.assert_equals(channel.step_trig_masks[2], nil)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
  luaunit.assert_equals(channel.step_velocity_masks[2], nil)
end


function test_memory_should_handle_undo_all_with_mixed_original_states()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state for step 1 only
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  
  -- Record events for both steps
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(1, "note_mask", {
    step = 2,  -- No initial state
    note = 64,
    velocity = 90,
    length = 1
  })
  
  memory.undo_all(1)
  
  -- Step 1 should restore to original state
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
  
  -- Step 2 should restore to nil
  luaunit.assert_equals(channel.step_trig_masks[2], nil)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
  luaunit.assert_equals(channel.step_velocity_masks[2], nil)
end


function test_memory_should_preserve_working_pattern_after_undo_all()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial working pattern state
  channel.working_pattern.trig_values[1] = 1
  channel.working_pattern.note_mask_values[1] = 48
  channel.working_pattern.velocity_values[1] = 70
  channel.working_pattern.lengths[1] = 2
  
  -- Record some events
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  memory.undo_all(1)
  
  -- Working pattern should restore to initial state
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 1)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 48)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 70)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end



function test_memory_should_redo_all_across_all_song_patterns_in_channel()
  memory.init()
  program.init()
  
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(2, 2)
  
  -- Record events in different patterns
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  -- Undo all patterns
  memory.undo_all(2)
  
  -- Verify undone state in channel 2 only
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], nil)
  
  -- Redo all patterns
  memory.redo_all(2)
  
  -- Channel 1 is unaffected
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_velocity_masks[1], 100)
  
-- Verify restored state
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  luaunit.assert_equals(channel2.step_velocity_masks[1], 90)
end


function test_memory_should_handle_partial_redo_all()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Record multiple events
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(1, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  -- Undo twice (leaving one event)
  memory.undo(1)
  memory.undo(1)
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Redo all
  memory.redo_all(1)
  
  -- Should restore final state
  luaunit.assert_equals(channel.step_note_masks[1], 67)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
end


function test_memory_should_handle_empty_redo_all()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Call redo_all with no events
  memory.redo_all(1)
  
  -- Should not error and state should remain empty
  local state = memory.get_state(1)
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(next(state.pattern_channels), nil)
end


function test_memory_should_handle_redo_all_with_working_pattern()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 2)
  
  -- Record events
  memory.record_event(2, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 2,
    song_pattern = 1
  })
  
  -- Undo all
  memory.undo_all(2)
  
  -- Verify working pattern cleared
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
  
  -- Redo all
  memory.redo_all(2)
  
  -- Working pattern should show final state
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end


function test_memory_reset_should_clear_histories_but_preserve_current_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial state
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  -- Modify state without recording
  channel.step_note_masks[1] = 64
  channel.step_velocity_masks[1] = 90
  
  memory.reset()
  
  -- Current state should be preserved
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  -- Event history should be cleared
  local state = memory.get_state(1)
  luaunit.assert_equals(state.event_history:get_size(), 0)
  luaunit.assert_equals(state.current_event_index, 0)
end



function test_memory_reset_should_treat_current_state_as_new_baseline()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial state and record
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  -- Modify state without recording
  channel.step_note_masks[1] = 64
  channel.step_velocity_masks[1] = 90
  
  memory.reset()
  
  -- Record new event
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  -- Undo should go back to state at reset (64, 90), not original state (60, 100)
  memory.undo(1)
  
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
end


function test_memory_reset_should_handle_working_pattern()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up state
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  -- Modify working pattern directly
  channel.working_pattern.note_mask_values[1] = 64
  channel.working_pattern.velocity_values[1] = 90
  
  memory.reset()
  
  -- Record new event
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  -- Undo should restore working pattern to state at reset
  memory.undo(1)
  
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
end


function test_memory_reset_should_keep_chord_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up state with chord
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Modify chord manually
  channel.step_chord_masks[1] = {1, 4, 5}
  
  memory.reset()
  
  -- Record new event
  memory.record_event(1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Undo should restore modified chord
  memory.undo(1)
  
  local chord = channel.step_chord_masks[1]
  luaunit.assert_equals(chord[1], 1)
  luaunit.assert_equals(chord[2], 4)
  luaunit.assert_equals(chord[3], 5)
end


function test_memory_should_handle_undo_redo_with_partial_chord_updates()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Initial chord
  memory.record_event(1, "note_mask", {
    step = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Partial update
  memory.record_event(1, "note_mask", {
    step = 1,
    chord_degrees = {2, nil, nil}
  })
  
  -- Verify state before undo
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 2)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Undo partial update
  memory.undo(1)
  
  -- Verify original state restored
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Redo partial update
  memory.redo(1)
  
  -- Verify partial update reapplied
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 2)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end


function test_memory_should_handle_clearing_individual_chord_degrees()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial chord
  memory.record_event(1, "note_mask", {
    step = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Clear middle degree by setting to nil
  memory.record_event(1, "note_mask", {
    step = 1,
    chord_degrees = {nil, nil, nil}
  })
  
  -- Verify chord was cleared since all degrees nil
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end


function test_memory_should_count_events()
  memory.init()
  program.init()
  
  local channel_1_number = 1
  local channel_2_number = 2

  local channel1_p1 = program.get_channel(1, channel_1_number)
  local channel2_p1 = program.get_channel(1, channel_2_number)
  local channel1_p2 = program.get_channel(2, channel_1_number)
  local channel2_p2 = program.get_channel(2, channel_2_number)

  -- Test empty state
  luaunit.assert_equals(memory.get_event_count(channel_1_number), 0)
  luaunit.assert_equals(memory.get_event_count(channel_2_number), 0)

  -- Add events across patterns and channels
  memory.record_event(channel_1_number, "note_mask", {step = 1, note = 60, song_pattern = 1})
  memory.record_event(channel_2_number, "note_mask", {step = 1, note = 62, song_pattern = 1})
  memory.record_event(channel_1_number, "note_mask", {step = 1, note = 64, song_pattern = 2})
  memory.record_event(channel_2_number, "note_mask", {step = 1, note = 66, song_pattern = 2})
  memory.record_event(channel_2_number, "note_mask", {step = 1, note = 66, song_pattern = 3})


  -- Test channel-specific counts
  luaunit.assert_equals(memory.get_event_count(channel_1_number), 2, "Should count channel 1 events")
  luaunit.assert_equals(memory.get_event_count(channel_2_number), 3, "Should count channel 2 events")
  
  -- Test after undo
  memory.undo(1)
  luaunit.assert_equals(memory.get_event_count(channel_1_number), 1, "Should count channel 1 events")
  luaunit.assert_equals(memory.get_event_count(channel_2_number), 3, "Should count channel 2 events")

end


function test_memory_get_recent_events_should_return_most_recent_events_for_channel()
  memory.init()
  program.init()

  local channel_number = 1
  local channel = program.get_channel(1, channel_number)
  
  -- Add a series of events
  for i = 1, 7 do
    memory.record_event(channel_number, "note_mask", {
      step = i,
      note = 60 + i,
      velocity = 100,
      length = 1, 
      song_pattern = 1
    })
  end

  memory.record_event(2, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1, 
    song_pattern = 1
  })

  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 68,
    velocity = 100,
    length = 1, 
    song_pattern = 2
  })
  
  -- Get recent events with default count
  local events = memory.get_recent_events(channel_number)
  
  -- Should return 5 most recent events by default
  luaunit.assert_equals(#events, 5)

  -- Get all events by giving a count higher than total number of events added
  events = memory.get_recent_events(channel_number, 20)

  -- we dont count the event we added to channel 2
  luaunit.assert_equals(#events, 8)
  
  -- Events should be in reverse chronological order
  luaunit.assert_equals(events[1].data.event_data.note, 68)
  luaunit.assert_equals(events[2].data.event_data.note, 67)
  luaunit.assert_equals(events[3].data.event_data.note, 66)
  luaunit.assert_equals(events[4].data.event_data.note, 65)
  luaunit.assert_equals(events[5].data.event_data.note, 64)
  luaunit.assert_equals(events[6].data.event_data.note, 63)
  luaunit.assert_equals(events[7].data.event_data.note, 62)
  luaunit.assert_equals(events[8].data.event_data.note, 61)
end


function test_memory_get_recent_events_should_handle_empty_history()
  memory.init()
  program.init()
  
  -- Test all query types with empty history
  local channel_events = memory.get_recent_events(1)
  luaunit.assert_equals(#channel_events, 0)
  
  local channel_events = memory.get_recent_events(2)
  luaunit.assert_equals(#channel_events, 0)
  
  local channel_events = memory.get_recent_events(3)
  luaunit.assert_equals(#channel_events, 0)
  
  local channel_events = memory.get_recent_events(4)
  luaunit.assert_equals(#channel_events, 0)
end


function test_memory_get_recent_events_should_maintain_order_after_undo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add events
  for i = 1, 5 do
    memory.record_event(1, "note_mask", {
      step = i,
      note = 60 + i,
      velocity = 100,
      length = 1, 
      song_pattern = 1
    })
  end
  
  -- Undo last event
  memory.undo(1)
  
  -- Get recent events
  local events = memory.get_recent_events(1)
  
  -- Should return 4 events in correct order
  luaunit.assert_equals(#events, 4)
  -- Most recent event should be note 64 (60 + 4), then counting down
  for i = 1, 4 do
    luaunit.assert_equals(events[i].data.event_data.note, 64 - (i - 1))
  end
end

function test_memory_get_recent_events_should_maintain_context_after_reset()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 7)
  
  -- Add events and reset
  memory.record_event(7, "note_mask", {
    step = 1,
    note = 60, 
    song_pattern = 1
  })
  
  memory.reset()
  
  -- Add new event
  memory.record_event(7, "note_mask", {
    step = 2,
    note = 62, 
    song_pattern = 1
  })
  
  -- Get recent events
  local events = memory.get_recent_events(7)
  
  -- Should only include post-reset events
  luaunit.assert_equals(#events, 1)
  luaunit.assert_equals(events[1].data.event_data.note, 62)
end


function test_memory_get_total_event_count_should_count_all_events_in_a_given_channel()
  memory.init()
  program.init()

  local channel_number = 1
  local channel = program.get_channel(1, channel_number)
  
  for i = 1, 5 do
    memory.record_event(channel_number, "note_mask", {
      step = i,
      note = 60 + i, 
      song_pattern = 1 + i
    })
  end
  
  -- Should include all events including undone ones
  memory.undo(1)
  memory.undo(1)
  
  luaunit.assert_equals(memory.get_total_event_count(channel_number), 5)
end

function test_memory_should_handle_concurrent_step_modifications()
  memory.init()
  program.init()
  local channel_number = 1
  local song_pattern_number = 1
  local channel = program.get_channel(channel_number, song_pattern_number)
  
  -- Simulate rapid concurrent modifications to same step
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = song_pattern_number
  })
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 62,
    velocity = 90,
    song_pattern = song_pattern_number
  })
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    length = 2,
    song_pattern = song_pattern_number
  })
  
  -- Verify final state combines all modifications
  luaunit.assert_equals(channel.step_note_masks[1], 62)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  -- Verify undo restores states in correct order
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_length_masks[1], 2) -- Length remains unchanged as it's preserved
  
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
end

function test_memory_should_handle_events_during_pattern_changes()
  memory.init()
  program.init()
  local channel_number = 1
  
  -- Record events in different patterns
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    song_pattern = 1
  })
  
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    song_pattern = 2
  })
  
  -- Verify states are preserved per pattern
  local channel1 = program.get_channel(1, channel_number)
  local channel2 = program.get_channel(2, channel_number)
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_velocity_masks[1], 100)
  
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  luaunit.assert_equals(channel2.step_velocity_masks[1], 90)
  
  -- Verify undo affects correct pattern
  memory.undo(channel_number)
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], nil)
end

-- Resource Management Tests
function test_memory_should_handle_maximum_history_size()
  memory.init()
  program.init()
  
  -- Temporarily reduce max history size for testing
  local original_max = memory.max_history_size
  memory.max_history_size = 5
  
  local channel_number = 1
  local channel = program.get_channel(1, channel_number)
  
  -- Add more than max events
  for i = 1, 10 do
    memory.record_event(channel_number, "note_mask", {
      step = i,
      note = 60 + i,
      velocity = 100,
      song_pattern = 1
    })
  end
  
  -- Verify only most recent events are kept
  local state = memory.get_state(channel_number)
  luaunit.assert_equals(state.event_history:get_size(), 5)
  
  -- Verify oldest events are properly removed
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.event_data.note, 66)
  
  -- Restore original max size
  memory.max_history_size = original_max
end

-- Stress Tests
function test_memory_under_rapid_event_load()
  memory.init()
  program.init()
  local channel_number = 1
  local channel = program.get_channel(1, channel_number)
  
  -- Record many events rapidly
  for i = 1, 100 do
    memory.record_event(channel_number, "note_mask", {
      step = i % 16 + 1,
      note = 60 + (i % 12),
      velocity = 100 - (i % 30),
      length = 1 + (i % 4),
      song_pattern = 1
    })
  end
  
  -- Verify system remains stable
  local state = memory.get_state(channel_number)
  luaunit.assert_equals(state.event_history.size, 100)
  
  -- Test rapid undo/redo
  for _ = 1, 50 do
    memory.undo(channel_number)
  end
  
  for _ = 1, 25 do
    memory.redo(channel_number)
  end
  
  -- Verify correct event count after operations
  luaunit.assert_equals(memory.get_event_count(channel_number), 75)
end

function test_memory_should_handle_error_recovery()
  memory.init()
  program.init()
  local channel_number = 1
  local channel = program.get_channel(1, channel_number)
  
  -- Set up initial state
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  -- Simulate error by manually corrupting state
  channel.step_note_masks[1] = nil
  channel.step_velocity_masks[1] = nil
  
  -- Record new event
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 2,
    song_pattern = 1
  })
  
  -- Verify system recovers and maintains consistency
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  -- Verify undo still works
  memory.undo(channel_number)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
end

function test_memory_should_cleanup_temporary_states()
  memory.init()
  program.init()
  local channel_number = 1
  local channel = program.get_channel(1, channel_number)
  
  -- Create complex state with multiple types of data
  memory.record_event(channel_number, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5},
    song_pattern = 1
  })
  
  -- Simulate cleanup
  memory.reset()
  
  -- Verify all temporary states are cleared
  local state = memory.get_state(channel_number)
  luaunit.assert_equals(state.event_history:get_size(), 0)
  luaunit.assert_equals(state.current_event_index, 0)
  
  -- Verify channel state remains intact
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

-- Timing Sensitive Tests
function test_memory_should_maintain_event_order_under_rapid_changes()
  memory.init()
  program.init()
  local channel_number = 1
  local channel = program.get_channel(1, channel_number)
  
  -- Record rapid sequence of events
  local expected_sequence = {}
  for i = 1, 20 do
    local note = 60 + i
    table.insert(expected_sequence, note)
    memory.record_event(channel_number, "note_mask", {
      step = 1,
      note = note,
      velocity = 100,
      song_pattern = 1
    })
  end
  
  -- Rapidly undo all events
  for _ = 1, 20 do
    memory.undo(channel_number)
  end
  
  -- Rapidly redo all events
  for _ = 1, 20 do
    memory.redo(channel_number)
  end
  
  -- Verify final state matches expected sequence
  luaunit.assert_equals(channel.step_note_masks[1], expected_sequence[#expected_sequence])
  
  -- Verify events are in correct order
  local state = memory.get_state(channel_number)
  for i = 1, #expected_sequence do
    local event = state.event_history:get(i)
    luaunit.assert_equals(event.data.event_data.note, expected_sequence[i])
  end
end
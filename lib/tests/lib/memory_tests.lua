local memory = include("mosaic/lib/memory")

function test_memory_init_should_create_empty_event_store()
  memory.init()
  program.init()
  local state = memory.get_state()
  
  luaunit.assert_equals(#state.event_history, 0)
  luaunit.assert_equals(state.current_event_index, 0)
end

function test_memory_should_add_single_note()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)

  memory.record_event(channel, "note_mask", {
    trig = 1,
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
end

function test_memory_should_add_note_mask()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)

  memory.record_event(channel, "note_mask", {
    trig = 1,
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5}
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
  local channel = program.get_channel(1, 1)

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
end

function test_memory_should_redo_undone_note()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.undo()
  memory.redo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 64)
end

function test_memory_should_clear_redo_history_after_new_note()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.undo()
  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  local state = memory.get_state()
  luaunit.assert_equals(state.event_history.size, 2)
  luaunit.assert_equals(channel.step_note_masks[2], 67)
end

function test_memory_should_maintain_separate_channels()
  memory.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_memory_should_maintain_event_history()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  local state = memory.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1)
  luaunit.assert_equals(state.current_event_index, 1)
  local first_event = state.event_history:get(1)
  luaunit.assert_not_nil(first_event)
  luaunit.assert_equals(first_event.data.event_data.note, 60)
end


function test_memory_should_maintain_event_index_during_undo_redo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.undo()
  
  local state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 1)
  luaunit.assert_equals(state.event_history.size, 2)
end

function test_memory_undo_should_clear_notes_from_channel()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add two notes
  memory.record_event(channel, "note_mask", {
    trig = 1,
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    trig = 1,
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Verify both notes are present
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_trig_masks[2], 1)
  luaunit.assert_equals(channel.step_note_masks[2], 64)
  
  -- Undo the second note
  memory.undo()
  
  -- Verify first note remains but second note is fully cleared
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_trig_masks[2], nil)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
  luaunit.assert_equals(channel.step_velocity_masks[2], nil)
  luaunit.assert_equals(channel.step_length_masks[2], nil)
  
  -- Undo the first note
  memory.undo()
  
  -- Verify both notes are fully cleared
  luaunit.assert_equals(channel.step_trig_masks[1], nil)
  luaunit.assert_equals(channel.step_note_masks[1], nil)
  luaunit.assert_equals(channel.step_velocity_masks[1], nil)
  luaunit.assert_equals(channel.step_length_masks[1], nil)
end

function test_memory_should_handle_undo_when_empty()
  memory.init()
  program.init()
  
  memory.undo()
  
  local state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(#state.event_history, 0)
end

function test_memory_should_handle_redo_when_empty()
  memory.init()
  program.init()
  
  memory.redo()
  
  local state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(#state.event_history, 0)
end

function test_memory_should_handle_multiple_notes_on_same_step()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  memory.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
end

function test_memory_should_handle_chord_after_note_on_same_step()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    chord_degrees = {1, 3, 5}
  })
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  memory.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_memory_should_handle_note_after_chord_on_same_step()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5}
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 71,
    velocity = 70,
    length = 1
  })
  
  -- Verify chord remains
  luaunit.assert_equals(channel.step_note_masks[1], 71)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  memory.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_memory_should_handle_undo_redo_at_boundaries()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test undo at start
  memory.undo()
  local state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  
  -- Add and undo all notes
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.undo()
  memory.undo()
  
  -- Test undo past beginning
  memory.undo()
  state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  
  -- Redo all notes
  memory.redo()
  memory.redo()
  
  -- Test redo past end
  memory.redo()
  state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 2)
end

function test_memory_should_maintain_correct_velocities_during_undo_redo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 80,
    length = 1
  })
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  
  memory.undo()
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  memory.redo()
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
end

function test_memory_should_handle_empty_chord_degrees()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {}
  })
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_memory_should_preserve_event_history_during_clear()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  program.init()  -- Should not affect memory state
  
  local state = memory.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1)
  luaunit.assert_equals(state.current_event_index, 1)
  local first_event = state.event_history:get(1)
  luaunit.assert_not_nil(first_event)
  luaunit.assert_equals(first_event.data.event_data.note, 60)
end

function test_memory_should_preserve_original_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  channel.step_length_masks[1] = 2
  
  -- Record new note
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Verify state changed
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  -- Undo should restore original state
  memory.undo()
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
end

function test_memory_should_preserve_original_chord_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial chord state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  channel.step_length_masks[1] = 2
  if not channel.step_chord_masks then channel.step_chord_masks = {} end
  channel.step_chord_masks[1] = {1, 4, 7}
  
  -- Record new note (should not affect chord)
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Verify chord preserved
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 4)
  luaunit.assert_equals(chord_mask[3], 7)
  
  -- Explicitly clear chord
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = nil,
    chord_degrees = {}
  })
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

-- Update the test to match the expected behavior:
function test_memory_should_handle_multiple_edits_to_same_step()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  
  -- Make multiple edits
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 67)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  
  -- Undo should go back through the history one step at a time
  memory.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  memory.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  memory.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
end

function test_memory_should_preserve_nil_states()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Record new note in empty step
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Verify note was added
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Undo should restore nil state
  memory.undo()
  
  luaunit.assert_equals(channel.step_trig_masks[1], nil)
  luaunit.assert_equals(channel.step_note_masks[1], nil)
  luaunit.assert_equals(channel.step_velocity_masks[1], nil)
  luaunit.assert_equals(channel.step_length_masks[1], nil)
end


function test_memory_should_handle_mixed_note_and_chord_edits_on_same_step()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  
  -- Series of mixed edits - chords should remain unless explicitly changed
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    chord_degrees = {1, 3, 5}
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 72,
    velocity = 110,
    length = 1
  })
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  luaunit.assert_equals(channel.step_velocity_masks[1], 110)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Explicitly clear chord
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = nil,
    chord_degrees = {}
  })

  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_memory_should_handle_interleaved_step_edits()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial states
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_trig_masks[2] = 1
  channel.step_note_masks[2] = 50
  
  -- Interleaved edits
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 62,
    velocity = 90,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 110,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 65,
    velocity = 95,
    length = 1
  })
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_note_masks[2], 65)
  
  -- Undo should affect steps independently
  memory.undo()  -- Undo step 2 second edit
  luaunit.assert_equals(channel.step_note_masks[1], 64)  -- Step 1 unchanged
  luaunit.assert_equals(channel.step_note_masks[2], 62)  -- Step 2 back one
  
  memory.undo()  -- Undo step 1 second edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 62)
  
  memory.undo()  -- Undo step 2 first edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 50)
  
  memory.undo()  -- Undo step 1 first edit
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_note_masks[2], 50)
end

function test_memory_should_handle_partial_undo_with_new_edits()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  
  -- First series of edits
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  -- Partial undo
  memory.undo()
  memory.undo()
  
  -- Should be back to first edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Add new edits
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 72,
    velocity = 110,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 74,
    velocity = 115,
    length = 1
  })
  
  -- Verify new state
  luaunit.assert_equals(channel.step_note_masks[1], 74)
  
  -- Undo through new edits
  memory.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  
  memory.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Back to original
  memory.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 48)
end

function test_memory_should_handle_redo_after_multiple_undos()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  
  -- Build up history
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    chord_degrees = {1, 3, 5}
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 72,
    velocity = 110,
    length = 1
  })
  
  -- Undo everything
  memory.undo()
  memory.undo()
  memory.undo()
  
  -- Verify back to original
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  
  -- Redo everything
  memory.redo()
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  memory.redo()
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  memory.redo()
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  luaunit.assert_equals(channel.step_velocity_masks[1], 110)
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_memory_should_preserve_original_state_across_multiple_edits()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up complex initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  if not channel.step_chord_masks then channel.step_chord_masks = {} end
  channel.step_chord_masks[1] = {1, 4, 7}
  
  -- Multiple edits of different types
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    chord_degrees = {1, 3, 5}
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 72,
    velocity = 110,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 76,
    velocity = 95,
    length = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Undo all the way back
  memory.undo()
  memory.undo()
  memory.undo()
  memory.undo()
  
  -- Verify original state is perfectly preserved
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
  local original_chord = channel.step_chord_masks[1]
  luaunit.assert_equals(original_chord[1], 1)
  luaunit.assert_equals(original_chord[2], 4)
  luaunit.assert_equals(original_chord[3], 7)
end

function test_memory_should_preserve_states_across_patterns()
  memory.init()
  program.init()
  
  -- Set up channels in different patterns
  program.set_selected_sequencer_pattern(1)
  local channel_pattern1 = program.get_channel(1, 1)
  channel_pattern1.step_trig_masks[1] = 1
  channel_pattern1.step_note_masks[1] = 48
  channel_pattern1.step_velocity_masks[1] = 70
  
  program.set_selected_sequencer_pattern(2)
  local channel_pattern2 = program.get_channel(2, 1)
  channel_pattern2.step_trig_masks[1] = 1
  channel_pattern2.step_note_masks[1] = 48
  channel_pattern2.step_velocity_masks[1] = 70
  
  -- Make edits specifying different patterns
  memory.record_event(channel_pattern1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel_pattern2, "note_mask", {
    step = 1,
    note = 62,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  -- Verify each pattern tracked separately
  memory.undo()  -- Undo pattern 2 edit
  luaunit.assert_equals(channel_pattern2.step_note_masks[1], 48)  -- Pattern 2 back to original
  luaunit.assert_equals(channel_pattern1.step_note_masks[1], 60)  -- Pattern 1 unchanged
  
  memory.undo()  -- Undo pattern 1 edit
  luaunit.assert_equals(channel_pattern1.step_note_masks[1], 48)  -- Pattern 1 back to original
end

function test_memory_should_undo_redo_in_correct_pattern()
  memory.init()
  program.init()
  
  -- Set up two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1_pattern1 = program.get_channel(1, 1)
  channel1_pattern1.step_note_masks[1] = 48
  
  program.set_selected_sequencer_pattern(2)
  local channel1_pattern2 = program.get_channel(2, 1)
  channel1_pattern2.step_note_masks[1] = 50
  
  -- Add notes to both patterns, explicitly passing song pattern
  memory.record_event(channel1_pattern1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel1_pattern2, "note_mask", {
    step = 1,
    note = 62,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  -- Undo should restore correct pattern
  memory.undo()  -- Should affect pattern 2
  luaunit.assert_equals(channel1_pattern2.step_note_masks[1], 50)  -- Back to original
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 60)  -- Pattern 1 unchanged
  
  memory.undo()  -- Should affect pattern 1
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 48)  -- Back to original
  
  -- Redo should also respect patterns
  memory.redo()  -- Should affect pattern 1
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1_pattern2.step_note_masks[1], 50)
  
  memory.redo()  -- Should affect pattern 2
  luaunit.assert_equals(channel1_pattern2.step_note_masks[1], 62)
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 60)
end

function test_memory_should_find_previous_events_in_same_pattern()
  memory.init()
  program.init()
  
  -- Set up two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1_pattern1 = program.get_channel(1, 1)
  
  program.set_selected_sequencer_pattern(2)
  local channel1_pattern2 = program.get_channel(2, 1)
  
  -- Create sequence of events across patterns
  memory.record_event(channel1_pattern1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel1_pattern2, "note_mask", {
    step = 1,
    note = 62,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })

  memory.record_event(channel1_pattern1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  -- Undo should find previous event in same pattern
  memory.undo()  -- Undo last note in pattern 1
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 60)  -- Back to first note
  luaunit.assert_equals(channel1_pattern2.step_note_masks[1], 62)  -- Pattern 2 unchanged
end

function test_memory_should_not_modify_step_key_when_same_channel_number_in_different_patterns()
  memory.init()
  program.init()

  -- Set up two channels with same number but in different patterns
  program.set_selected_sequencer_pattern(1)
  local channel1_pattern1 = program.get_channel(1, 1)
  channel1_pattern1.step_note_masks[1] = 48

  program.set_selected_sequencer_pattern(2)
  local channel1_pattern2 = program.get_channel(2, 1)  -- Same channel number (1)
  channel1_pattern2.step_note_masks[1] = 50

  -- Add note to first pattern
  memory.record_event(channel1_pattern1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  -- Access pc_state1 after adding step to pattern 1
  local state = memory.get_state()
  local key1 = "1_1"
  local step_key = "1"
  local pc_state1 = state.pattern_channels[key1]
  luaunit.assert_equals(pc_state1.original_states[step_key].note_mask, 48)

  -- Add note to second pattern
  memory.record_event(channel1_pattern2, "note_mask", {
    step = 1,
    note = 62,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })

  -- Access pc_state2 after adding step to pattern 2
  local key2 = "2_1"
  local pc_state2 = state.pattern_channels[key2]
  luaunit.assert_equals(pc_state2.original_states[step_key].note_mask, 50)
end


function test_memory_should_store_deep_copies_of_chord_masks()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial chord
  if not channel.step_chord_masks then channel.step_chord_masks = {} end
  channel.step_chord_masks[1] = {1, 3, 5}
  
  -- Add new chord
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {2, 4, 6}
  })
  
  -- Modify original chord array
  channel.step_chord_masks[1][1] = 7
  
  -- Undo should restore original values, not modified ones
  memory.undo()
  
  luaunit.assert_equals(channel.step_chord_masks[1][1], 1)
  luaunit.assert_equals(channel.step_chord_masks[1][2], 3)
  luaunit.assert_equals(channel.step_chord_masks[1][3], 5)
end

function test_memory_should_handle_deleted_recreated_channels()
  memory.init()
  program.init()
  
  -- Add note to channel
  local channel = program.get_channel(1, 1)
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Simulate channel deletion/recreation
  program.init()
  channel = program.get_channel(1, 1)
  
  -- Verify memory state preserved
  local state = memory.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1)
  local first_event = state.event_history:get(1)
  luaunit.assert_not_nil(first_event)
  luaunit.assert_equals(first_event.data.event_data.note, 60)
  
  -- Verify undo still works
  memory.undo()
  luaunit.assert_equals(channel.step_note_masks[1], nil)
end

function test_memory_should_preserve_event_order_during_undo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 62,
    velocity = 90,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 3,
    note = 64,
    velocity = 80,
    length = 1
  })
  
  -- Get initial event order
  local state = memory.get_state()
  local initial_events = {}
  for i, event in ipairs(state.event_history) do
    initial_events[i] = event.data.event_data.note
  end
  
  -- Undo everything
  memory.undo()
  memory.undo()
  memory.undo()
  
  -- Redo everything
  memory.redo()
  memory.redo()
  memory.redo()
  
  -- Check event order is preserved
  state = memory.get_state()
  for i, event in ipairs(state.event_history) do
    luaunit.assert_equals(event.data.event_data.note, initial_events[i])
  end
end

function test_memory_should_handle_nil_chord_degrees_correctly()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = nil
  })
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 62,
    velocity = 95,
    length = 1,
    chord_degrees = {}
  })
  
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end


function test_memory_should_update_working_pattern()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    trig = 1,
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
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
  local channel = program.get_channel(1, 1)
  
  -- Add two steps
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Undo last step
  memory.undo()
  
  -- Check working pattern reflects first step
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
end

function test_memory_should_clear_working_pattern_on_full_undo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add and undo a step
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.undo()
  
  -- Check working pattern is cleared
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 1)
end

function test_memory_should_handle_multiple_patterns_working_pattern()
  memory.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(2, 1)
  
  -- Add notes to different patterns
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Check working patterns are independent
  luaunit.assert_equals(channel1.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel2.working_pattern.note_mask_values[1], 64)
end


function test_memory_should_preserve_working_pattern_original_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial working pattern state
  channel.working_pattern.trig_values[1] = 1
  channel.working_pattern.note_mask_values[1] = 48
  channel.working_pattern.velocity_values[1] = 70
  channel.working_pattern.lengths[1] = 2
  
  -- Add new note
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Verify working pattern changed
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  -- Undo should restore original working pattern
  memory.undo()
  
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 1)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 48)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 70)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end

function test_memory_should_handle_working_pattern_multiple_edits()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add series of edits
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  -- Verify final working pattern state
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 67)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 80)
  
  -- Undo each edit and verify working pattern
  memory.undo()  -- Back to second edit
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
  
  memory.undo()  -- Back to first edit
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  memory.undo()  -- Back to original
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
end

function test_memory_should_preserve_working_pattern_during_redo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add and undo some steps
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.undo()
  memory.undo()
  
  -- Verify back to initial state
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
  
  -- Redo and verify working pattern restored
  memory.redo()
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  memory.redo()
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
end

function test_memory_should_handle_working_pattern_across_different_steps()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add notes to different steps
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Verify both steps in working pattern
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[2], 64)
  
  -- Undo second step
  memory.undo()
  
  -- First step should remain unchanged, second step cleared
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[2], 0)
  luaunit.assert_equals(channel.working_pattern.trig_values[2], 0)
end

function test_memory_should_handle_working_pattern_with_chords()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add chord
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Verify working pattern values
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  -- Add normal note (clearing chord)
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Verify working pattern updated
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
  
  -- Undo should restore chord state in working pattern
  memory.undo()
  
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
end

function test_memory_should_preserve_working_pattern_when_clearing_redo_history()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Create some history
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.undo()
  
  -- Working pattern should show first note
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  
  -- Add new note (clearing redo history)
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  -- Working pattern should show new note
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 67)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 80)
  
  -- Undo should restore to first note
  memory.undo()
  
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
end

function test_memory_should_maintain_working_pattern_across_multiple_patterns()
  memory.init()
  program.init()
  
  -- Set up two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)
  
  -- Add notes to different patterns

  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel2, "note_mask", {
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
  memory.undo()
  
  -- Pattern 1 should be unchanged, pattern 2 cleared
  luaunit.assert_equals(channel1.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel2.working_pattern.note_mask_values[1], 0)
  luaunit.assert_equals(channel2.working_pattern.trig_values[1], 0)
end

function test_memory_should_handle_nil_channel()
  memory.init()
  program.init()
  
  -- Attempt to add step with nil channel
  memory.record_event(nil, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  local state = memory.get_state()
  luaunit.assert_equals(#state.event_history, 0)
  luaunit.assert_equals(state.current_event_index, 0)
end

function test_memory_should_handle_invalid_step_numbers()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test negative step
  memory.record_event(channel, "note_mask", {
    step = -1,
    note = 60,
    velocity = 100,
    length = 1
  })

  luaunit.assert_equals(channel.step_note_masks[-1], nil)
  
  -- Test zero step
  memory.record_event(channel, "note_mask", {
    step = 0,
    note = 60,
    velocity = 100,
    length = 1
  })

  luaunit.assert_equals(channel.step_note_masks[0], nil)
  
  -- Test non-numeric step
  memory.record_event(channel, "note_mask", {
    step = "invalid",
    note = 60,
    velocity = 100,
    length = 1
  })
  luaunit.assert_equals(channel.step_note_masks["invalid"], nil)
  
  local state = memory.get_state()
  luaunit.assert_equals(#state.event_history, 0)
end

function test_memory_should_handle_invalid_note_velocity_values()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test invalid note values
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = -1,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 128,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = "C4",
    velocity = 100,
    length = 1
  })
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = -1,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 128,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = "ff",
    length = 1
  })
  
  local state = memory.get_state()
  luaunit.assert_equals(#state.event_history, 0)
  luaunit.assert_equals(channel.step_note_masks[1], nil)
end

function test_memory_should_persist_state_across_pattern_switches()
  memory.init()
  program.init()
  
  -- Add notes to pattern 1
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Switch to pattern 2 and add notes
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)

  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Switch back to pattern 1 and verify state
  program.set_selected_sequencer_pattern(1)
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  
  -- Switch to pattern 2 and verify state
  program.set_selected_sequencer_pattern(2)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  
  -- Undo in pattern 2
  memory.undo()
  luaunit.assert_equals(channel2.step_note_masks[1], nil)
  
  -- Switch to pattern 1 and verify unaffected
  program.set_selected_sequencer_pattern(1)
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
end

function test_memory_should_clear_redo_history_on_cross_pattern_edits()
  memory.init()
  program.init()
  
  -- Build up history in pattern 1
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.undo()
  
  -- Add note in pattern 2 
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)

  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  -- Try to redo pattern 1 edit
  program.set_selected_sequencer_pattern(1)
  memory.redo()
  
  -- Verify redo was cleared
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  
  local state = memory.get_state()
  local pattern1_state = state.pattern_channels["1_1"]
  luaunit.assert_equals(pattern1_state.current_index, 1)
end

function test_memory_should_validate_chord_degrees()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {"1", "3", "5"}
  })

  -- Verify invalid chords weren't recorded
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  local state = memory.get_state()
  luaunit.assert_equals(#state.event_history, 0)
end

function test_memory_undo_should_be_isolated_to_pattern()
  memory.init()
  program.init()
  
  -- Add notes to two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel1, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })

  memory.record_event(channel2, "note_mask", {
    step = 2,
    note = 71,
    velocity = 70,
    length = 1
  })
  
  -- Undo in pattern 2
  memory.undo(2, 1)
  
  -- Pattern 2 should have last note undone
  luaunit.assert_equals(channel2.step_note_masks[2], nil)
  luaunit.assert_equals(channel2.step_note_masks[1], 67)
  
  -- Pattern 1 should be unchanged
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_note_masks[2], 64)
end

function test_memory_redo_should_be_isolated_to_pattern()
  memory.init()
  program.init()
  
  -- Add and undo notes in two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)

  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel1, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.undo(1, 1)
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)

  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })

  memory.record_event(channel2, "note_mask", {
    step = 2,
    note = 71,
    velocity = 70,
    length = 1
  })

  memory.undo(2, 1)
  
  -- Redo in pattern 2
  memory.redo(2, 1)
  
  -- Pattern 2 should have note redone
  luaunit.assert_equals(channel2.step_note_masks[2], 71)
  
  -- Pattern 1 should still have last note undone
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_note_masks[2], nil)
end

function test_memory_should_track_separate_histories_per_pattern()
  memory.init()
  program.init()
  
  -- Add notes alternating between patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)

  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)

  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  program.set_selected_sequencer_pattern(1)
  memory.record_event(channel1, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  program.set_selected_sequencer_pattern(2)
  memory.record_event(channel2, "note_mask", {
    step = 2,
    note = 71,
    velocity = 70,
    length = 1
  })
  
  -- Verify separate histories tracked
  local state = memory.get_state()
  local pattern1_history = state.pattern_channels["1_1"].event_history
  local pattern2_history = state.pattern_channels["2_1"].event_history
  
  luaunit.assert_equals(pattern1_history:get_size(), 2)
  luaunit.assert_equals(pattern1_history:get(1).data.event_data.note, 60)
  luaunit.assert_equals(pattern1_history:get(2).data.event_data.note, 64)
  
  luaunit.assert_equals(pattern2_history:get_size(), 2)
  luaunit.assert_equals(pattern2_history:get(1).data.event_data.note, 67)
  luaunit.assert_equals(pattern2_history:get(2).data.event_data.note, 71)
end

function test_memory_should_count_events_per_channel()
  memory.init()
  program.init()
  
  -- Add notes to different patterns/channels
  local channel1 = program.get_channel(1, 1) 
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel1, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  local channel2 = program.get_channel(1, 2)
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  luaunit.assert_equals(memory.get_event_count(1, 1), 2)
  luaunit.assert_equals(memory.get_event_count(1, 2), 1)
  luaunit.assert_equals(memory.get_event_count(2, 1), 0)
  
  -- Test after undo
  memory.undo()
  luaunit.assert_equals(memory.get_event_count(1, 2), 0)
  luaunit.assert_equals(memory.get_event_count(1, 1), 2)
end


function test_memory_should_count_events_across_patterns()
  memory.init()
  program.init()
  
  -- Add notes to different patterns/channels
  program.set_selected_sequencer_pattern(1)
  local channel1_p1 = program.get_channel(1, 1)
  local channel2_p1 = program.get_channel(1, 2)
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel2_p1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  program.set_selected_sequencer_pattern(2)
  local channel1_p2 = program.get_channel(2, 1)
  local channel2_p2 = program.get_channel(2, 2)
  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })

  memory.record_event(channel2_p2, "note_mask", {
    step = 1,
    note = 71,
    velocity = 70,
    length = 1
  })

  memory.record_event(channel1_p2, "note_mask", {
    step = 2,
    note = 72,
    velocity = 85,
    length = 1
  })
  
  -- Check counts across patterns and channels
  luaunit.assert_equals(memory.get_event_count(1, 1), 1)
  luaunit.assert_equals(memory.get_event_count(1, 2), 1)
  luaunit.assert_equals(memory.get_event_count(2, 1), 2)
  luaunit.assert_equals(memory.get_event_count(2, 2), 1)
  
  -- Test undo in specific pattern/channel
  memory.undo(2, 1) -- Undo last note in pattern 2, channel 1
  luaunit.assert_equals(memory.get_event_count(2, 1), 1)
  luaunit.assert_equals(memory.get_event_count(2, 2), 1)
  
  -- Test redo in specific pattern/channel
  memory.redo(2, 1)
  luaunit.assert_equals(memory.get_event_count(2, 1), 2)
end

function test_memory_should_handle_custom_length()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2
  })
  
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end

function test_memory_should_validate_length()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test invalid lengths
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 0
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = "2"
  })
  
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  
  local state = memory.get_state()
  luaunit.assert_equals(#state.event_history, 0)
end

function test_memory_should_preserve_length_during_undo_redo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 3
  })
  
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  
  memory.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  memory.redo()
  luaunit.assert_equals(channel.step_length_masks[1], 3)
end

function test_memory_should_handle_multiple_length_edits_to_same_step()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Series of length edits
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 4
  })
  
  luaunit.assert_equals(channel.step_length_masks[1], 4)
  
  -- Undo should restore previous lengths
  memory.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  memory.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 1)
end

function test_memory_should_preserve_length_across_patterns()
  memory.init()
  program.init()
  
  -- Set up channels in different patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2
  })
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)

  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 3
  })
  
  -- Verify lengths are independent
  luaunit.assert_equals(channel1.step_length_masks[1], 2)
  luaunit.assert_equals(channel2.step_length_masks[1], 3)
  
  -- Undo in pattern 2 shouldn't affect pattern 1
  memory.undo()
  luaunit.assert_equals(channel1.step_length_masks[1], 2)
  luaunit.assert_equals(channel2.step_length_masks[1], nil)
end

function test_memory_should_maintain_length_in_working_pattern()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 3
  })
  
  -- Verify length in both masks and working pattern
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 3)
  
  memory.undo()
  
  -- Verify length cleared from both
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 1)  -- Default value
end

function test_memory_should_handle_interleaved_length_edits()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add steps with different lengths
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 3
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 4
  })
  
  -- Verify final state
  luaunit.assert_equals(channel.step_length_masks[1], 4)
  luaunit.assert_equals(channel.step_length_masks[2], 3)
  
  -- Undo last edit
  memory.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  luaunit.assert_equals(channel.step_length_masks[2], 3)
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
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2
  })
  
  -- Verify state changed
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
  
  -- Undo should restore original length
  memory.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 4)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 4)
end

function test_memory_should_persist_length_through_redo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add and undo a series of edits
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 3
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 4
  })

  memory.undo()
  memory.undo()
  memory.undo()
  
  -- Verify all undone
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  
  -- Redo should restore lengths in order
  memory.redo()
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  memory.redo()
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  
  memory.redo()
  luaunit.assert_equals(channel.step_length_masks[1], 4)
end

function test_memory_should_validate_length_with_chord()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test invalid length with chord
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = -1,
    chord_degrees = {1, 3, 5}
  })
  
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  -- Test valid length with chord
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2,
    chord_degrees = {1, 3, 5}
  })
  
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_memory_should_handle_nil_note_and_velocity()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Modify only length
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 3
  })
  
  -- Original note and velocity should be preserved
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  -- Length should be updated
  luaunit.assert_equals(channel.step_length_masks[1], 3)
end

function test_memory_should_preserve_chord_when_only_changing_length()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state with chord
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2,
    chord_degrees = {1, 3, 5}
  })
  
  -- Modify only length
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 3,
    chord_degrees = nil
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
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Update only velocity and length
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = 80,
    length = 2
  })
  
  -- Note should be preserved, velocity and length updated
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  -- Update only note and length
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = nil,
    length = 3
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
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Update only length
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 2
  })
  
  -- Verify only length changed
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  
  -- Undo should restore original length only
  memory.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  
  -- Redo should restore only length change
  memory.redo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
end

function test_memory_should_validate_nil_values()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2,
    chord_degrees = {1, 3, 5}
  })
  
  -- Update only individual values
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = 90,
    length = nil,
    chord_degrees = nil
  })

  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = nil,
    length = nil,
    chord_degrees = nil
  })

  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 3,
    chord_degrees = nil
  })

  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  
  -- Invalid values should still be caught
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = -1,
    velocity = nil,
    length = nil,
    chord_degrees = nil
  })

  luaunit.assert_equals(channel.step_note_masks[1], 64)  -- Should not change
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = 128,
    length = nil,
    chord_degrees = nil
  })

  luaunit.assert_equals(channel.step_velocity_masks[1], 90)  -- Should not change
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = -6,
    chord_degrees = nil
  })

  luaunit.assert_equals(channel.step_length_masks[1], 3)  -- Should not change
  
end

function test_memory_should_allow_all_nil_values_except_step()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 2,
    chord_degrees = {1, 3, 5}
  })
  
  -- Should preserve all values when using nil
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = nil,
    chord_degrees = nil
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
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = nil,
    length = nil,
    chord_degrees = nil
  })
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = 100,
    length = nil,
    chord_degrees = nil
  })
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 2,
    chord_degrees = nil
  })
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = nil,
    chord_degrees = {1, 3}
  })
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  
  -- Mixed combinations
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = nil,
    chord_degrees = nil
  })
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = nil,
    velocity = nil,
    length = 3,
    chord_degrees = {1, 4}
  })
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 4)
end

function test_memory_should_preserve_indices_after_wrap()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Fill buffer and cause wrap
  for i = 1, 1001 do
    memory.record_event(channel, "note_mask", {
      step = i % 16 + 1,
      note = 60 + i,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state()
  
  -- Check step indices are maintained
  for i = 1, 16 do
    -- Get last event for each step
    local step_events = state.global_index.step_to_events[i]
    luaunit.assert_not_nil(step_events, "Step events should exist for step " .. i)
    
    -- Verify the events are accessible and in correct order
    for j, event_idx in ipairs(step_events) do
      local event = state.event_history:get(event_idx)
      luaunit.assert_not_nil(event, "Event should exist at index " .. event_idx)
      luaunit.assert_equals(event.data.step, i)
    end
  end
end

function test_memory_should_respect_max_history_size()
  memory.init()

  memory.max_history_size = 1000

  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add more than MAX_HISTORY_SIZE events
  for i = 1, 1001 do  -- MAX_HISTORY_SIZE is 1000
    memory.record_event(channel, "note_mask", {
      step = i % 16 + 1,
      note = 60 + (i % 12),
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state()
  
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
    memory.record_event(channel, "note_mask", {
      step = i % 16 + 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  -- Add one more to cause wrap
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = (1001 % 128),
    velocity = 100,
    length = 1
  })
  
  local state = memory.get_state()
  
  -- Buffer should still be at max size
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- First event should be note value (2 % 128) (since 1 was pushed out)
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.event_data.note, (2 % 128))
  
  -- Last event should be (1001 % 128)
  local last_event = state.event_history:get(1000)
  luaunit.assert_equals(last_event.data.event_data.note, (1001 % 128))
end

function test_memory_should_handle_pattern_channel_buffer_wrapping()
  memory.init()

  memory.max_history_size = 1000

  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Fill first channel with predictable sequence
  for i = 1, 800 do
    memory.record_event(channel1, "note_mask", {
      step = 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  -- Add to second channel
  for i = 1, 300 do
    memory.record_event(channel2, "note_mask", {
      step = 1,
      note = (1000 + i) % 128,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state()
  local pc1 = state.pattern_channels["1_1"]
  local pc2 = state.pattern_channels["1_2"]
  
  -- Verify initial counts
  luaunit.assert_equals(pc1.event_history:get_size(), 800)
  luaunit.assert_equals(pc2.event_history:get_size(), 300)
  
  -- Add enough to cause wrap in first channel
  for i = 801, 1100 do
    memory.record_event(channel1, "note_mask", {
      step = 1,
      note = (i % 128),
      velocity = 100,
      length = 1
    })
  end
  
  -- First channel should be at MAX_HISTORY_SIZE
  luaunit.assert_equals(pc1.event_history:get_size(), 1000)
  
  -- Second channel should be unaffected
  luaunit.assert_equals(pc2.event_history:get_size(), 300)
  
  -- First event in channel 1 should be (101 % 128)
  local first_ch1_event = pc1.event_history:get(1)
  luaunit.assert_equals(first_ch1_event.data.event_data.note, (101 % 128))
  
  -- Last event in channel 1 should be (1100 % 128)
  local last_ch1_event = pc1.event_history:get(1000)
  luaunit.assert_equals(last_ch1_event.data.event_data.note, (1100 % 128))
end

function test_ring_buffer_should_maintain_correct_order_during_wrap()
  memory.init()

  memory.max_history_size = 1000

  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Fill buffer
  for i = 1, 998 do
    memory.record_event(channel, "note_mask", {
      step = 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state()
  local initial_size = state.event_history:get_size()
  luaunit.assert_equals(initial_size, 998)
  
  -- Add wrap boundary notes
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 62,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 100,
    length = 1
  })
  
  state = memory.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- First event should be the second one after wrap
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.event_data.note, 2)
end


function test_ring_buffer_should_handle_rapid_wrap_multiple_times()
  memory.init()

  memory.max_history_size = 1000

  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Fill buffer multiple times
  local final_batch_start = 2001
  for i = 1, 3000 do
    memory.record_event(channel, "note_mask", {
      step = 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state()
  
  -- Verify size remains at max
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- Get events from different positions
  local first = state.event_history:get(1)
  local last = state.event_history:get(1000)
  
  luaunit.assert_not_nil(first, "First event should exist")
  luaunit.assert_not_nil(last, "Last event should exist")
  
  -- Verify the sequence wraps correctly
  luaunit.assert_equals(first.data.event_data.note, (2001 % 128))
  luaunit.assert_equals(last.data.event_data.note, (3000 % 128))
end

function test_ring_buffer_should_handle_concurrent_pattern_wraps()
  memory.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Alternate between channels while exceeding buffer size
  for i = 1, 2000 do
    local note = i % 128
    if i % 2 == 0 then
      memory.record_event(channel1, "note_mask", {
        step = 1,
        note = note,
        velocity = 100,
        length = 1
      })
    else
      memory.record_event(channel2, "note_mask", {
        step = 1,
        note = note,
        velocity = 100,
        length = 1
      })
    end
  end
  
  local state = memory.get_state()
  local pc1 = state.pattern_channels["1_1"]
  local pc2 = state.pattern_channels["1_2"]
  
  -- Verify pattern channels exist
  luaunit.assert_not_nil(pc1, "Pattern channel 1 should exist")
  luaunit.assert_not_nil(pc2, "Pattern channel 2 should exist")
  
  -- Verify we can get events from each channel
  local pc1_first = pc1.event_history:get(1)
  local pc2_first = pc2.event_history:get(1)
  
  luaunit.assert_not_nil(pc1_first, "First event in channel 1 should exist")
  luaunit.assert_not_nil(pc2_first, "First event in channel 2 should exist")
  
  -- Verify events are in valid range
  luaunit.assert_true(pc1_first.data.event_data.note >= 0 and pc1_first.data.event_data.note <= 127)
  luaunit.assert_true(pc2_first.data.event_data.note >= 0 and pc2_first.data.event_data.note <= 127)
end

function test_ring_buffer_should_maintain_indices_after_multiple_wraps()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Create a sequence that will wrap multiple times
  for i = 1, 2500 do
    memory.record_event(channel, "note_mask", {
      step = (i % 16) + 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state()
  
  -- Test that step indices are maintained for recent events
  for step = 1, 16 do
    local step_events = state.global_index.step_to_events[step]
    luaunit.assert_not_nil(step_events, "Step events missing for step " .. step)
    
    -- Verify last few events for each step are accessible and in order
    local last_events = {}
    for i = #step_events - 2, #step_events do
      if i > 0 then
        local event = state.event_history:get(step_events[i])
        luaunit.assert_not_nil(event, "Event missing at index " .. step_events[i])
        table.insert(last_events, event.data.event_data.note)
      end
    end
    
    -- Verify events are in ascending order
    for i = 2, #last_events do
      luaunit.assert_true(last_events[i] >= last_events[i-1], 
        "Events out of order for step " .. step)
    end
  end
end

function test_ring_buffer_should_handle_edge_case_at_max_size()
  memory.init()

  memory.max_history_size = 1000

  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Fill buffer exactly to max size
  for i = 1, 1000 do
    memory.record_event(channel, "note_mask", {
      step = 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- Add one more event
  memory.record_event(channel, "note_mask", {
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
  local channel = program.get_channel(1, 1)
  
  -- Add 100 events
  for i = 1, 100 do
    memory.record_event(channel, "note_mask", {
      step = 1,
      note = i % 128,
      velocity = 100,
      length = 1
    })
  end
  
  local state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 100)
  
  -- Undo 25 events
  for _ = 1, 25 do
    memory.undo()
  end
  
  state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 75)
  
  -- Add new event
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 76)
end

function test_memory_should_undo_all_in_single_pattern()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
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
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 3,
    note = 67,
    velocity = 85,
    length = 1,
    chord_degrees = {2, 4, 6}
  })
  
  -- Undo all at once
  memory.undo_all(1, 1)
  
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
  local state = memory.get_state()
  local pc_state = state.pattern_channels["1_1"]
  luaunit.assert_equals(pc_state.current_index, 0)
end

function test_memory_should_undo_all_across_patterns()
  memory.init()
  program.init()
  
  -- Set up initial state for both patterns first
  local channel1 = program.get_channel(1, 1)
  channel1.step_trig_masks[1] = 1
  channel1.step_note_masks[1] = 48
  channel1.step_velocity_masks[1] = 70
  
  local channel2 = program.get_channel(2, 1)
  channel2.step_trig_masks[1] = 1
  channel2.step_note_masks[1] = 50
  channel2.step_velocity_masks[1] = 80
  
  -- Now add events
  -- First pattern
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1  -- Explicitly specify pattern
  })
  
  -- Second pattern
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2  -- Explicitly specify pattern
  })
  
  -- Undo all patterns
  memory.undo_all()
  
  -- Verify original states restored for both patterns
  luaunit.assert_equals(channel1.step_trig_masks[1], 1)
  luaunit.assert_equals(channel1.step_note_masks[1], 48)
  luaunit.assert_equals(channel1.step_velocity_masks[1], 70)
  
  luaunit.assert_equals(channel2.step_trig_masks[1], 1)
  luaunit.assert_equals(channel2.step_note_masks[1], 50)
  luaunit.assert_equals(channel2.step_velocity_masks[1], 80)
  
  -- Verify indices reset
  local state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(state.pattern_channels["1_1"].current_index, 0)
  luaunit.assert_equals(state.pattern_channels["2_1"].current_index, 0)
end

function test_memory_should_preserve_original_states_after_undo_all()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial states
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  channel.step_length_masks[1] = 2
  
  channel.step_trig_masks[2] = 1  -- Step 2 has initial state too
  channel.step_note_masks[2] = 52
  channel.step_velocity_masks[2] = 75
  channel.step_length_masks[2] = 3
  
  -- Add multiple edits
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Undo all at once
  memory.undo_all(1, 1)
  
  -- Verify original states restored
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  luaunit.assert_equals(channel.step_trig_masks[2], 1)
  luaunit.assert_equals(channel.step_note_masks[2], 52)
  luaunit.assert_equals(channel.step_velocity_masks[2], 75)
  luaunit.assert_equals(channel.step_length_masks[2], 3)
end


function test_memory_should_handle_undo_all_with_no_original_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- All steps start with nil state
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  memory.undo_all(1, 1)
  
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
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,  -- No initial state
    note = 64,
    velocity = 90,
    length = 1
  })
  
  memory.undo_all(1, 1)
  
  -- Step 1 should restore to original state
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
  
  -- Step 2 should restore to nil
  luaunit.assert_equals(channel.step_trig_masks[2], nil)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
  luaunit.assert_equals(channel.step_velocity_masks[2], nil)
end

function test_memory_should_handle_undo_all_with_multiple_events_on_same_step()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  
  -- Multiple events on same step
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 67,
    velocity = 85,
    length = 1
  })
  
  memory.undo_all(1, 1)
  
  -- Should restore to original state, ignoring intermediate values
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
end

function test_memory_should_handle_undo_all_with_complex_pattern_interactions()
  memory.init()
  program.init()
  
  -- Set up initial states
  local channel1 = program.get_channel(1, 1)
  channel1.step_trig_masks[1] = 1
  channel1.step_note_masks[1] = 48
  if not channel1.step_chord_masks then channel1.step_chord_masks = {} end
  channel1.step_chord_masks[1] = {1, 3, 5}
  
  local channel2 = program.get_channel(2, 1)
  channel2.step_trig_masks[1] = 1
  channel2.step_note_masks[1] = 50
  
  -- Interleaved events across patterns
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 67,
    velocity = 85,
    length = 1,
    song_pattern = 1,
    chord_degrees = {2, 4, 6}
  })
  
  memory.undo_all()
  
  -- Pattern 1 should restore chord
  luaunit.assert_equals(channel1.step_trig_masks[1], 1)
  luaunit.assert_equals(channel1.step_note_masks[1], 48)
  luaunit.assert_equals(channel1.step_chord_masks[1][1], 1)
  luaunit.assert_equals(channel1.step_chord_masks[1][2], 3)
  luaunit.assert_equals(channel1.step_chord_masks[1][3], 5)
  
  -- Pattern 2 should restore simple state
  luaunit.assert_equals(channel2.step_trig_masks[1], 1)
  luaunit.assert_equals(channel2.step_note_masks[1], 50)
end

function test_memory_should_handle_undo_all_with_empty_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Call undo_all with no events
  memory.undo_all(1, 1)
  
  -- Should not error and state should remain empty
  local state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(next(state.pattern_channels), nil)
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
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  memory.undo_all(1, 1)
  
  -- Working pattern should restore to initial state
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 1)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 48)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 70)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end

function test_memory_should_redo_all_in_single_pattern()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Record series of events
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 3,
    note = 67,
    velocity = 80,
    length = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Undo everything
  memory.undo_all(1, 1)
  
  -- Verify initial state
  luaunit.assert_equals(channel.step_note_masks[1], nil)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
  luaunit.assert_equals(channel.step_note_masks[3], nil)
  
  -- Redo all at once
  memory.redo_all(1, 1)
  
  -- Verify final state restored
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  luaunit.assert_equals(channel.step_note_masks[2], 64)
  luaunit.assert_equals(channel.step_velocity_masks[2], 90)
  
  luaunit.assert_equals(channel.step_note_masks[3], 67)
  luaunit.assert_equals(channel.step_velocity_masks[3], 80)
  local chord_mask = channel.step_chord_masks[3]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_memory_should_redo_all_across_patterns()
  memory.init()
  program.init()
  
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(2, 1)
  
  -- Record events in different patterns
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  -- Undo all patterns
  memory.undo_all()
  
  -- Verify undone state
  luaunit.assert_equals(channel1.step_note_masks[1], nil)
  luaunit.assert_equals(channel2.step_note_masks[1], nil)
  
  -- Redo all patterns
  memory.redo_all()
  
  -- Verify restored state
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_velocity_masks[1], 100)
  
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  luaunit.assert_equals(channel2.step_velocity_masks[1], 90)
end

function test_memory_should_handle_partial_redo_all()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Record multiple events
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  -- Undo twice (leaving one event)
  memory.undo()
  memory.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Redo all
  memory.redo_all(1, 1)
  
  -- Should restore final state
  luaunit.assert_equals(channel.step_note_masks[1], 67)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
end

function test_memory_should_handle_empty_redo_all()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Call redo_all with no events
  memory.redo_all(1, 1)
  
  -- Should not error and state should remain empty
  local state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(next(state.pattern_channels), nil)
end

function test_memory_should_handle_redo_all_with_working_pattern()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Record events
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 2
  })
  
  -- Undo all
  memory.undo_all(1, 1)
  
  -- Verify working pattern cleared
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
  
  -- Redo all
  memory.redo_all(1, 1)
  
  -- Working pattern should show final state
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end

function test_memory_should_handle_mixed_undo_redo_all()
  memory.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(2, 1)
  
  -- Record events in both patterns
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  -- Undo all in pattern 1 only
  memory.undo_all(1, 1)
  
  -- Verify pattern 1 undone but pattern 2 unchanged
  luaunit.assert_equals(channel1.step_note_masks[1], nil)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  
  -- Redo all in pattern 1
  memory.redo_all(1, 1)
  
  -- Both patterns should have their events
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_memory_reset_should_clear_histories_but_preserve_current_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial state
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Modify state without recording
  channel.step_note_masks[1] = 64
  channel.step_velocity_masks[1] = 90
  
  memory.reset()
  
  -- Current state should be preserved
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  -- Event history should be cleared
  local state = memory.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 0)
  luaunit.assert_equals(state.current_event_index, 0)
end

function test_memory_reset_should_treat_current_state_as_new_baseline()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial state and record
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Modify state without recording
  channel.step_note_masks[1] = 64
  channel.step_velocity_masks[1] = 90
  
  memory.reset()
  
  -- Record new event
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  -- Undo should go back to state at reset (64, 90), not original state (60, 100)
  memory.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
end

function test_memory_reset_should_preserve_pattern_channels()
  memory.init()
  program.init()
  
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(2, 1)
  
  -- Set up states in different patterns
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  -- Modify states
  channel1.step_note_masks[1] = 67
  channel2.step_note_masks[1] = 71
  
  memory.reset()
  
  -- Pattern channels should exist but have clear histories
  local state = memory.get_state()
  luaunit.assert_not_nil(state.pattern_channels["1_1"])
  luaunit.assert_not_nil(state.pattern_channels["2_1"])
  luaunit.assert_equals(state.pattern_channels["1_1"].event_history:get_size(), 0)
  luaunit.assert_equals(state.pattern_channels["2_1"].event_history:get_size(), 0)
  
  -- Current states should be preserved
  luaunit.assert_equals(channel1.step_note_masks[1], 67)
  luaunit.assert_equals(channel2.step_note_masks[1], 71)
end

function test_memory_reset_should_handle_working_pattern()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up state
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Modify working pattern directly
  channel.working_pattern.note_mask_values[1] = 64
  channel.working_pattern.velocity_values[1] = 90
  
  memory.reset()
  
  -- Record new event
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1
  })
  
  -- Undo should restore working pattern to state at reset
  memory.undo()
  
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
end

function test_memory_reset_should_allow_recording_new_steps()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up state with step 1
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  memory.reset()
  
  -- Record new step
  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Should create new original state for step 2
  luaunit.assert_equals(channel.step_note_masks[2], 64)
  
  -- Undo should clear step 2
  memory.undo()
  luaunit.assert_equals(channel.step_note_masks[2], nil)
end

function test_memory_reset_should_keep_chord_state()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up state with chord
  memory.record_event(channel, "note_mask", {
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
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Undo should restore modified chord
  memory.undo()
  
  local chord = channel.step_chord_masks[1]
  luaunit.assert_equals(chord[1], 1)
  luaunit.assert_equals(chord[2], 4)
  luaunit.assert_equals(chord[3], 5)
end


function test_memory_should_handle_trig_only_note_mask()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Record event with only step and trig
  memory.record_event(channel, "note_mask", {
    step = 1,
    trig = 1
    -- No note, velocity, or length specified
  })
  
  -- Verify trig was set but other values remain default/nil
  luaunit.assert_equals(channel.step_trig_masks[1], 1)  -- Default trig value should be 1
  luaunit.assert_equals(channel.step_note_masks[1], nil)
  luaunit.assert_equals(channel.step_velocity_masks[1], nil)
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  luaunit.assert_equals(channel.step_chord_masks, {})
  
  -- Verify working pattern reflects trig-only state
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 1)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)  -- Default note value
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)  -- Default velocity
  luaunit.assert_equals(channel.working_pattern.lengths[1], 1)  -- Default length
end


function test_memory_should_support_partial_chord_updates()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial chord state
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Verify initial state
  luaunit.assert_not_nil(channel.step_chord_masks, "Chord masks table should exist")
  luaunit.assert_not_nil(channel.step_chord_masks[1], "Initial chord should be set")
  luaunit.assert_equals(channel.step_chord_masks[1][1], 1)
  luaunit.assert_equals(channel.step_chord_masks[1][2], 3)
  luaunit.assert_equals(channel.step_chord_masks[1][3], 5)
  
  -- Update just the middle degree
  memory.record_event(channel, "note_mask", {
    step = 1,
    chord_degrees = {nil, 4, nil}
  })
  
  -- Verify only the middle degree changed
  luaunit.assert_not_nil(channel.step_chord_masks, "Chord masks table should still exist")
  luaunit.assert_not_nil(channel.step_chord_masks[1], "Chord mask should still exist after partial update")
  luaunit.assert_equals(channel.step_chord_masks[1][1], 1, "First degree should remain unchanged")
  luaunit.assert_equals(channel.step_chord_masks[1][2], 4, "Second degree should be updated")
  luaunit.assert_equals(channel.step_chord_masks[1][3], 5, "Third degree should remain unchanged")
  
  -- Update just the first degree
  memory.record_event(channel, "note_mask", {
    step = 1,
    chord_degrees = {2, nil, nil}
  })
  
  -- Verify only first degree changed
  luaunit.assert_not_nil(channel.step_chord_masks[1], "Chord mask should still exist after second update")
  luaunit.assert_equals(channel.step_chord_masks[1][1], 2, "First degree should be updated")
  luaunit.assert_equals(channel.step_chord_masks[1][2], 4, "Second degree should remain from previous update")
  luaunit.assert_equals(channel.step_chord_masks[1][3], 5, "Third degree should remain from initial state")
end

function test_memory_should_handle_undo_redo_with_partial_chord_updates()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Initial chord
  memory.record_event(channel, "note_mask", {
    step = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Partial update
  memory.record_event(channel, "note_mask", {
    step = 1,
    chord_degrees = {2, nil, nil}
  })
  
  -- Verify state before undo
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 2)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Undo partial update
  memory.undo()
  
  -- Verify original state restored
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Redo partial update
  memory.redo()
  
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
  memory.record_event(channel, "note_mask", {
    step = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Clear middle degree by setting to nil
  memory.record_event(channel, "note_mask", {
    step = 1,
    chord_degrees = {nil, nil, nil}
  })
  
  -- Verify chord was cleared since all degrees nil
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_memory_should_preserve_partial_chord_updates_after_reset()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Initial chord
  memory.record_event(channel, "note_mask", {
    step = 1,
    chord_degrees = {1, 3, 5}
  })
  
  -- Partial update
  memory.record_event(channel, "note_mask", {
    step = 1,
    chord_degrees = {2, nil, nil}
  })
  
  -- Reset memory
  memory.reset()
  
  -- Record new partial update 
  memory.record_event(channel, "note_mask", {
    step = 1,
    chord_degrees = {nil, 4, nil}
  })
  
  -- Undo should restore state at reset time
  memory.undo()
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 2)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_memory_should_undo_most_recent_event_across_patterns()
  memory.init()
  program.init()
  
  -- Set up channels in different patterns
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  -- Add events in chronological order
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  -- Undo most recent event for channel 1
  memory.undo(nil, 1)
  
  -- Pattern 2 event should be undone, Pattern 1 unchanged
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
end

function test_memory_should_redo_earliest_available_event_across_patterns()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  -- Add and undo events
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })
  
  memory.undo_all(nil, 1)
  
  -- Verify undone state
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
  
  -- Redo earliest event
  memory.redo(nil, 1)
  
  -- Pattern 1 event should be redone first
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
end

function test_memory_should_undo_all_events_across_patterns_for_channel()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  local channel2_p1 = program.get_channel(1, 2)  -- Different channel
  
  -- Add events to multiple patterns/channels
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })

  memory.record_event(channel2_p1, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  -- Undo all events for channel 1
  memory.undo_all(nil, 1)
  
  -- Channel 1 events should be undone in all patterns
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
  
  -- Channel 2 should be unaffected
  luaunit.assert_equals(channel2_p1.step_note_masks[1], 67)
end

function test_memory_should_redo_all_events_across_patterns_for_channel()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  local channel2_p1 = program.get_channel(1, 2)
  
  -- Add and undo events
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })

  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })

  memory.record_event(channel2_p1, "note_mask", {
    step = 1,
    note = 67,
    velocity = 80,
    length = 1,
    song_pattern = 1
  })
  
  memory.undo_all()
  
  -- Redo all events for channel 1 only
  memory.redo_all(nil, 1)
  
  -- Channel 1 events should be redone in all patterns
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], 64)
  
  -- Channel 2 should remain undone
  luaunit.assert_equals(channel2_p1.step_note_masks[1], nil)
end

function test_memory_should_handle_empty_channel_undo_redo()
  memory.init()
  program.init()
  
  -- Attempt operations on empty state
  memory.undo(nil, 1)
  memory.redo(nil, 1)
  memory.undo_all(nil, 1)
  memory.redo_all(nil, 1)
  
  -- Should not error and state should remain empty
  local state = memory.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(next(state.pattern_channels), nil)
end

function test_memory_should_maintain_channel_independence()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel2_p1 = program.get_channel(1, 2)
  
  -- Add events to different channels
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel2_p1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Undo channel 1 events
  memory.undo(nil, 1)
  
  -- Channel 1 should be undone, Channel 2 unchanged
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  luaunit.assert_equals(channel2_p1.step_note_masks[1], 64)
  
  -- Redo channel 1 events
  memory.redo(nil, 1)
  
  -- Both channels should have their events
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2_p1.step_note_masks[1], 64)
end

function test_memory_should_preserve_working_pattern_across_patterns()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    song_pattern = 1
  })

  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    song_pattern = 2  
  })

  memory.undo(nil, 1)
  
  -- Verify working pattern state maintained independently
  luaunit.assert_equals(channel1_p1.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel1_p2.working_pattern.note_mask_values[1], 0)
end

function test_memory_should_preserve_chord_state_across_patterns()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    chord_degrees = {1, 3, 5},
    song_pattern = 1
  })

  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    chord_degrees = {1, 4, 5},
    song_pattern = 2
  })

  memory.undo(nil, 1) -- Undo most recent event for channel 1
  
  -- Verify chord state maintained independently
  luaunit.assert_equals(channel1_p1.step_chord_masks[1][1], 1)
  luaunit.assert_equals(channel1_p1.step_chord_masks[1][2], 3)
  luaunit.assert_equals(channel1_p2.step_chord_masks[1], nil)
end

function test_memory_should_handle_multiple_undo_redo_cycles_across_patterns()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  -- Add events in different order
  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 2
  })

  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  -- Multiple undo/redo cycles
  memory.undo(nil, 1)  -- Should undo pattern 1
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], 64)
  
  memory.undo(nil, 1)  -- Should undo pattern 2
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
  
  memory.redo(nil, 1)  -- Should redo pattern 2 first (earliest)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], 64)
  
  memory.redo(nil, 1)  -- Should redo pattern 1
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], 64)
end

function test_memory_should_handle_interleaved_channel_events_across_patterns()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  local channel2_p1 = program.get_channel(1, 2)
  
  -- Interleaved events across channels and patterns
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    song_pattern = 1
  })

  memory.record_event(channel2_p1, "note_mask", {
    step = 1,
    note = 62,
    song_pattern = 1
  })

  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 64,
    song_pattern = 2
  })
  
  -- Undo channel 1 events
  memory.undo(nil, 1)  -- Most recent channel 1 event (pattern 2)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2_p1.step_note_masks[1], 62)
  
  memory.undo(nil, 1)  -- Earlier channel 1 event (pattern 1)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
  luaunit.assert_equals(channel2_p1.step_note_masks[1], 62)
end

function test_memory_should_handle_edge_cases_in_cross_pattern_operations()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  -- Edge case: Pattern with no events
  memory.undo(nil, 1)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  
  -- Edge case: Single event
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    song_pattern = 1
  })
  
  memory.undo(nil, 1)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  
  memory.redo(nil, 1)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
  
  -- Edge case: Multiple undo beyond available events
  memory.undo(nil, 1)
  memory.undo(nil, 1)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  
  -- Edge case: Multiple redo beyond available events
  memory.redo(nil, 1)
  memory.redo(nil, 1)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
end

 function test_memory_should_count_events()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel2_p1 = program.get_channel(1, 2)
  local channel1_p2 = program.get_channel(2, 1)
  local channel2_p2 = program.get_channel(2, 2)

  -- Test empty state
  luaunit.assert_equals(memory.get_event_count(), 0)
  luaunit.assert_equals(memory.get_event_count(1), 0)
  luaunit.assert_equals(memory.get_event_count(nil, 1), 0)
  luaunit.assert_equals(memory.get_event_count(1, 1), 0)

  -- Add events across patterns and channels
  memory.record_event(channel1_p1, "note_mask", {step = 1, note = 60, song_pattern = 1})
  memory.record_event(channel2_p1, "note_mask", {step = 1, note = 62, song_pattern = 1})
  memory.record_event(channel1_p2, "note_mask", {step = 1, note = 64, song_pattern = 2})
  memory.record_event(channel2_p2, "note_mask", {step = 1, note = 66, song_pattern = 2})

  -- Test total counts
  luaunit.assert_equals(memory.get_event_count(), 4, "Should count all events")
  
  -- Test pattern-specific counts
  luaunit.assert_equals(memory.get_event_count(1), 2, "Should count pattern 1 events")
  luaunit.assert_equals(memory.get_event_count(2), 2, "Should count pattern 2 events")
  
  -- Test channel-specific counts
  luaunit.assert_equals(memory.get_event_count(nil, 1), 2, "Should count channel 1 events")
  luaunit.assert_equals(memory.get_event_count(nil, 2), 2, "Should count channel 2 events")
  
  -- Test pattern-channel specific counts
  luaunit.assert_equals(memory.get_event_count(1, 1), 1, "Should count pattern 1 channel 1")
  luaunit.assert_equals(memory.get_event_count(1, 2), 1, "Should count pattern 1 channel 2")
  luaunit.assert_equals(memory.get_event_count(2, 1), 1, "Should count pattern 2 channel 1")
  luaunit.assert_equals(memory.get_event_count(2, 2), 1, "Should count pattern 2 channel 2")

  -- Test after undo
  memory.undo()
  luaunit.assert_equals(memory.get_event_count(), 3, "Should count after undo")
  luaunit.assert_equals(memory.get_event_count(2), 1, "Should count pattern after undo")
  luaunit.assert_equals(memory.get_event_count(nil, 2), 1, "Should count channel after undo")
  
  -- Test non-existent pattern/channel
  luaunit.assert_equals(memory.get_event_count(3), 0, "Should handle non-existent pattern")
  luaunit.assert_equals(memory.get_event_count(nil, 3), 0, "Should handle non-existent channel")
  luaunit.assert_equals(memory.get_event_count(3, 3), 0, "Should handle non-existent pattern-channel")
end


function test_memory_get_recent_events_should_return_most_recent_global_events()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add a series of events
  for i = 1, 7 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 60 + i,
      velocity = 100,
      length = 1
    })
  end
  
  -- Get recent events with default count
  local events = memory.get_recent_events()
  
  -- Should return 5 most recent events by default
  luaunit.assert_equals(#events, 5)
  
  -- Events should be in reverse chronological order
  for i = 1, 5 do
    luaunit.assert_equals(events[i].data.event_data.note, 67 - (i - 1))
  end
end

function test_memory_get_recent_events_should_handle_specific_count()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add events
  for i = 1, 5 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 60 + i,
      velocity = 100,
      length = 1
    })
  end
  
  -- Request specific counts
  local events_3 = memory.get_recent_events(nil, nil, 3)
  luaunit.assert_equals(#events_3, 3)
  
  local events_all = memory.get_recent_events(nil, nil, 10)
  luaunit.assert_equals(#events_all, 5)  -- Only 5 exist
end

function test_memory_get_recent_events_should_return_channel_specific_events()
  memory.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Add events alternating between channels
  memory.record_event(channel1, "note_mask", {
    step = 1, 
    note = 60,
    song_pattern = 1,
    channel_number = 1  -- Explicitly set channel number
  })
  memory.record_event(channel2, "note_mask", {
    step = 1, 
    note = 62,
    song_pattern = 1,
    channel_number = 2
  })
  memory.record_event(channel1, "note_mask", {
    step = 2, 
    note = 64,
    song_pattern = 1,
    channel_number = 1
  })
  memory.record_event(channel2, "note_mask", {
    step = 2, 
    note = 66,
    song_pattern = 1,
    channel_number = 2
  })
  
  -- Get events for channel 1
  local events = memory.get_recent_events(nil, 1, 2)  -- Explicitly request 2 events
  
  -- Should only include channel 1 events
  luaunit.assert_equals(#events, 2)
  luaunit.assert_equals(events[1].data.event_data.note, 64)
  luaunit.assert_equals(events[2].data.event_data.note, 60)
end

function test_memory_get_recent_events_should_return_pattern_specific_events()
  memory.init()
  program.init()
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  -- Add events in different patterns
  memory.record_event(channel1_p1, "note_mask", {
    step = 1, 
    note = 60,
    song_pattern = 1,
    channel_number = 1
  })
  
  memory.record_event(channel1_p2, "note_mask", {
    step = 1, 
    note = 62,
    song_pattern = 2,
    channel_number = 1
  })
  
  -- Get events for pattern 1, specify count of 1
  local events = memory.get_recent_events(1, nil, 1)
  
  -- Should only include pattern 1 events
  luaunit.assert_equals(#events, 1)
  luaunit.assert_equals(events[1].data.event_data.note, 60)
end

function test_memory_get_recent_events_should_return_pattern_and_channel_specific_events()
  memory.init()
  program.init()
  
  -- Set up channels in different patterns
  local channel1_p1 = program.get_channel(1, 1)
  local channel2_p1 = program.get_channel(1, 2)
  local channel1_p2 = program.get_channel(2, 1)
  
  -- Add events across patterns and channels
  memory.record_event(channel1_p1, "note_mask", {
    step = 1, 
    note = 60,
    song_pattern = 1
  })
  
  memory.record_event(channel2_p1, "note_mask", {
    step = 1, 
    note = 62,
    song_pattern = 1
  })
  
  memory.record_event(channel1_p2, "note_mask", {
    step = 1, 
    note = 64,
    song_pattern = 2
  })
  
  -- Get events for pattern 1, channel 1
  local events = memory.get_recent_events(1, 1)
  
  -- Should only include events for specified pattern and channel
  luaunit.assert_equals(#events, 1)
  luaunit.assert_equals(events[1].data.event_data.note, 60)
end

function test_memory_get_recent_events_should_handle_empty_history()
  memory.init()
  program.init()
  
  -- Test all query types with empty history
  local global_events = memory.get_recent_events()
  luaunit.assert_equals(#global_events, 0)
  
  local channel_events = memory.get_recent_events(nil, 1)
  luaunit.assert_equals(#channel_events, 0)
  
  local pattern_events = memory.get_recent_events(1)
  luaunit.assert_equals(#pattern_events, 0)
  
  local specific_events = memory.get_recent_events(1, 1)
  luaunit.assert_equals(#specific_events, 0)
end

function test_memory_get_recent_events_should_maintain_order_after_undo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add events
  for i = 1, 5 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 60 + i,
      velocity = 100,
      length = 1
    })
  end
  
  -- Undo last event
  memory.undo()
  
  -- Get recent events
  local events = memory.get_recent_events()
  
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
  local channel = program.get_channel(1, 1)
  
  -- Add events and reset
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60
  })
  
  memory.reset()
  
  -- Add new event
  memory.record_event(channel, "note_mask", {
    step = 2,
    note = 62
  })
  
  -- Get recent events
  local events = memory.get_recent_events()
  
  -- Should only include post-reset events
  luaunit.assert_equals(#events, 1)
  luaunit.assert_equals(events[1].data.event_data.note, 62)
end

function test_memory_get_recent_events_should_respect_current_event_index()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add events
  for i = 1, 3 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 60 + i,
      velocity = 100,
      length = 1
    })
  end
  
  -- Save events at current state
  local original_events = memory.get_recent_events()
  
  -- Add more events and undo
  memory.record_event(channel, "note_mask", {
    step = 4,
    note = 64
  })
  
  memory.undo()
  
  -- Get events again
  local current_events = memory.get_recent_events()
  
  -- Should match original events
  luaunit.assert_equals(#current_events, #original_events)
  for i = 1, #original_events do
    luaunit.assert_equals(
      current_events[i].data.event_data.note,
      original_events[i].data.event_data.note
    )
  end
end

function test_memory_get_recent_events_should_handle_cross_pattern_events()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  -- Add events alternating between patterns
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    song_pattern = 1
  })
  
  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 62,
    song_pattern = 2
  })
  
  -- Get events for channel 1 across patterns
  local events = memory.get_recent_events(nil, 1)
  
  -- Should include both events in reverse chronological order
  luaunit.assert_equals(#events, 2)
  luaunit.assert_equals(events[1].data.event_data.note, 62)
  luaunit.assert_equals(events[2].data.event_data.note, 60)
end

function test_memory_get_recent_events_should_handle_large_history()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add 1000 events
  for i = 1, 1000 do
    memory.record_event(channel, "note_mask", {
      step = i % 16 + 1,
      note = 60 + (i % 12),
      velocity = 100,
      length = 1
    })
  end
  
  -- Get recent events with different counts
  local events_5 = memory.get_recent_events(nil, nil, 5)
  luaunit.assert_equals(#events_5, 5)
  for i = 1, 5 do
    -- Verify reverse chronological order
    luaunit.assert_equals(events_5[i].data.event_data.note, 60 + ((1000 - i + 1) % 12))
  end
  
  local events_100 = memory.get_recent_events(nil, nil, 100)
  luaunit.assert_equals(#events_100, 100)
end

function test_memory_get_recent_events_should_handle_invalid_inputs()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add some events
  memory.record_event(channel, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  -- Test with invalid pattern/channel numbers
  local events_invalid_pattern = memory.get_recent_events(999, nil)
  luaunit.assert_equals(#events_invalid_pattern, 0)
  
  local events_invalid_channel = memory.get_recent_events(nil, 999)
  luaunit.assert_equals(#events_invalid_channel, 0)
  
  -- Test with negative count
  local events_negative_count = memory.get_recent_events(nil, nil, -1)
  luaunit.assert_equals(#events_negative_count, 0)
  
  -- Test with zero count
  local events_zero_count = memory.get_recent_events(nil, nil, 0)
  luaunit.assert_equals(#events_zero_count, 0)
end

function test_memory_get_recent_events_should_handle_mixed_pattern_channel_combinations()
  memory.init()
  program.init()
  
  -- Set up channels in different patterns
  local channel1_p1 = program.get_channel(1, 1)
  local channel2_p1 = program.get_channel(1, 2)
  local channel1_p2 = program.get_channel(2, 1)
  local channel2_p2 = program.get_channel(2, 2)
  
  -- Add events in specific order
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(channel2_p1, "note_mask", {
    step = 1,
    note = 62,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 100,
    length = 1,
    song_pattern = 2
  })
  
  memory.record_event(channel2_p2, "note_mask", {
    step = 1,
    note = 66,
    velocity = 100,
    length = 1,
    song_pattern = 2
  })
  
  -- Test various combinations
  -- All events for channel 1 across patterns
  local channel1_events = memory.get_recent_events(nil, 1, 2)
  luaunit.assert_equals(#channel1_events, 2)
  luaunit.assert_equals(channel1_events[1].data.event_data.note, 64)
  luaunit.assert_equals(channel1_events[2].data.event_data.note, 60)
  
  -- All events for pattern 1 across channels
  local pattern1_events = memory.get_recent_events(1, nil, 2)
  luaunit.assert_equals(#pattern1_events, 2)
  luaunit.assert_equals(pattern1_events[1].data.event_data.note, 62)
  luaunit.assert_equals(pattern1_events[2].data.event_data.note, 60)
  
  -- Events for specific pattern/channel combination
  local specific_events = memory.get_recent_events(2, 2, 1)
  luaunit.assert_equals(#specific_events, 1)
  luaunit.assert_equals(specific_events[1].data.event_data.note, 66)
end

function test_memory_get_recent_events_should_handle_undo_redo()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add series of events
  for i = 1, 5 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 60 + i,
      velocity = 100,
      length = 1
    })
  end
  
  -- Get initial events
  local initial_events = memory.get_recent_events()
  luaunit.assert_equals(#initial_events, 5)
  luaunit.assert_equals(initial_events[1].data.event_data.note, 65)
  
  -- Undo some events
  memory.undo()
  memory.undo()
  
  -- Get events after undo
  local after_undo = memory.get_recent_events()
  luaunit.assert_equals(#after_undo, 3)
  luaunit.assert_equals(after_undo[1].data.event_data.note, 63)
  
  -- Redo events
  memory.redo()
  
  -- Get events after redo
  local after_redo = memory.get_recent_events()
  luaunit.assert_equals(#after_redo, 4)
  luaunit.assert_equals(after_redo[1].data.event_data.note, 64)
end

function test_memory_get_recent_events_should_preserve_order_after_reset()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add initial events
  for i = 1, 3 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 60 + i,
      velocity = 100,
      length = 1
    })
  end
  
  memory.reset()
  
  -- Add new events
  for i = 1, 2 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 70 + i,
      velocity = 100,
      length = 1
    })
  end
  
  -- Verify only post-reset events are returned in correct order
  local events = memory.get_recent_events()
  luaunit.assert_equals(#events, 2)
  luaunit.assert_equals(events[1].data.event_data.note, 72)
  luaunit.assert_equals(events[2].data.event_data.note, 71)
end


function test_memory_get_total_event_count_should_handle_empty_state()
  memory.init()
  program.init()
  
  luaunit.assert_equals(memory.get_total_event_count(), 0)
  luaunit.assert_equals(memory.get_total_event_count(1), 0)
  luaunit.assert_equals(memory.get_total_event_count(nil, 1), 0)
  luaunit.assert_equals(memory.get_total_event_count(1, 1), 0)
end

function test_memory_get_total_event_count_should_count_all_events()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  for i = 1, 5 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 60 + i
    })
  end
  
  -- Should include all events including undone ones
  memory.undo()
  memory.undo()
  
  luaunit.assert_equals(memory.get_total_event_count(), 5)
end

function test_memory_get_total_event_count_should_count_pattern_specific_events()
  memory.init()
  program.init()
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    song_pattern = 1
  })
  
  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 62,
    song_pattern = 2
  })
  
  luaunit.assert_equals(memory.get_total_event_count(1), 1)
  luaunit.assert_equals(memory.get_total_event_count(2), 1)
end

function test_memory_get_total_event_count_should_count_channel_specific_events()
  memory.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 62
  })
  
  luaunit.assert_equals(memory.get_total_event_count(nil, 1), 1)
  luaunit.assert_equals(memory.get_total_event_count(nil, 2), 1)
end

function test_memory_get_total_event_count_should_count_pattern_channel_specific_events()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel2_p1 = program.get_channel(1, 2)
  local channel1_p2 = program.get_channel(2, 1)
  
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    song_pattern = 1
  })
  
  memory.record_event(channel2_p1, "note_mask", {
    step = 1,
    note = 62,
    song_pattern = 1
  })
  
  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 64,
    song_pattern = 2
  })
  
  luaunit.assert_equals(memory.get_total_event_count(1, 1), 1)
  luaunit.assert_equals(memory.get_total_event_count(1, 2), 1)
  luaunit.assert_equals(memory.get_total_event_count(2, 1), 1)
end

function test_memory_get_total_event_count_should_include_undone_events()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add events and undo some
  for i = 1, 3 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 60 + i
    })
  end
  
  memory.undo()
  memory.undo()
  
  -- Should still count undone events
  luaunit.assert_equals(memory.get_total_event_count(), 3)
  luaunit.assert_equals(memory.get_total_event_count(1, 1), 3)
end

function test_memory_get_total_event_count_should_handle_pattern_switching()
  memory.init()
  program.init()
  
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  
  program.set_selected_sequencer_pattern(1)
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    song_pattern = 1
  })
  
  program.set_selected_sequencer_pattern(2)
  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 62,
    song_pattern = 2
  })
  
  luaunit.assert_equals(memory.get_total_event_count(nil, 1), 2)
  luaunit.assert_equals(memory.get_total_event_count(1, 1), 1)
  luaunit.assert_equals(memory.get_total_event_count(2, 1), 1)
end

function test_memory_get_total_event_count_should_handle_reset()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add events and reset
  for i = 1, 3 do
    memory.record_event(channel, "note_mask", {
      step = i,
      note = 60 + i
    })
  end
  
  memory.reset()
  
  -- Should start fresh count after reset
  luaunit.assert_equals(memory.get_total_event_count(), 0)
  luaunit.assert_equals(memory.get_total_event_count(1, 1), 0)
end

function test_memory_get_total_event_count_should_handle_large_histories()
  memory.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add many events
  for i = 1, 1000 do
    memory.record_event(channel, "note_mask", {
      step = i % 16 + 1,
      note = 60 + (i % 12)
    })
  end
  
  luaunit.assert_equals(memory.get_total_event_count(), 1000)
  luaunit.assert_equals(memory.get_total_event_count(1, 1), 1000)
end

-- Add these new tests to your existing test suite:

function test_memory_should_preserve_channel_histories_during_interleaved_operations()
  memory.init()
  program.init()
  
  -- Set up channels
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Add events alternating between channels
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  memory.record_event(channel1, "note_mask", {
    step = 2,
    note = 62,
    velocity = 95,
    length = 1
  })
  
  -- Verify initial state
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_note_masks[2], 62)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  
  -- Undo last event from channel 1
  memory.undo(nil, 1)
  
  -- Channel 1's second note should be undone, but channel 2 unchanged
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_note_masks[2], nil)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  
  -- Add new event to channel 1
  memory.record_event(channel1, "note_mask", {
    step = 2,
    note = 67,
    velocity = 85,
    length = 1
  })
  
  -- Channel 2's history should still be intact
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_note_masks[2], 67)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  
  -- Undo channel 2's event
  memory.undo(nil, 2)
  
  -- Only channel 2's event should be undone
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_note_masks[2], 67)
  luaunit.assert_equals(channel2.step_note_masks[1], nil)
  
  -- Redo channel 2's event
  memory.redo(nil, 2)
  
  -- Channel 2's event should be restored
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  
  -- Both channels should maintain correct event counts
  luaunit.assert_equals(memory.get_event_count(nil, 1), 2)
  luaunit.assert_equals(memory.get_event_count(nil, 2), 1)
end

function test_memory_should_handle_channel_specific_redo_after_new_events()
  memory.init()
  program.init()
  
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Add and undo events in both channels
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  memory.undo(nil, 1)
  memory.undo(nil, 2)
  
  -- Add new event to channel 1
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 67,
    velocity = 85,
    length = 1
  })
  
  -- Channel 2 should still be able to redo its event
  memory.redo(nil, 2)
  
  luaunit.assert_equals(channel1.step_note_masks[1], 67)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_memory_should_maintain_correct_event_order_per_channel()
  memory.init()
  program.init()
  
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Add events in specific order
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  memory.record_event(channel1, "note_mask", {
    step = 2,
    note = 62,
    velocity = 95,
    length = 1
  })
  
  -- Undo all events from channel 1
  memory.undo(nil, 1)
  memory.undo(nil, 1)
  
  -- Redo channel 1 events - should maintain original order
  memory.redo(nil, 1)
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  
  memory.redo(nil, 1)
  luaunit.assert_equals(channel1.step_note_masks[2], 62)
end

function test_memory_should_handle_pattern_and_channel_specific_operations()
  memory.init()
  program.init()
  
  -- Set up channels in different patterns
  local channel1_p1 = program.get_channel(1, 1)
  local channel1_p2 = program.get_channel(2, 1)
  local channel2_p1 = program.get_channel(1, 2)
  
  -- Add events across patterns and channels
  memory.record_event(channel1_p1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(channel2_p1, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1,
    song_pattern = 1
  })
  
  memory.record_event(channel1_p2, "note_mask", {
    step = 1,
    note = 67,
    velocity = 85,
    length = 1,
    song_pattern = 2
  })
  
  -- Undo channel 1 events across all patterns
  memory.undo(nil, 1)
  
  -- Should undo most recent channel 1 event (in pattern 2)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
  luaunit.assert_equals(channel2_p1.step_note_masks[1], 64)
  
  memory.undo(nil, 1)
  
  -- Should undo channel 1 pattern 1 event
  luaunit.assert_equals(channel1_p1.step_note_masks[1], nil)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
  luaunit.assert_equals(channel2_p1.step_note_masks[1], 64)
  
  -- Redo should maintain pattern-specific state
  memory.redo(nil, 1)
  luaunit.assert_equals(channel1_p1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1_p2.step_note_masks[1], nil)
end

function test_memory_should_clear_redo_history_per_channel()
  memory.init()
  program.init()
  
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Add initial events
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  -- Undo both channels
  memory.undo(nil, 1)
  memory.undo(nil, 2)
  
  -- Add new event to channel 1
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 67,
    velocity = 85,
    length = 1
  })
  
  -- Channel 1 redo should not be possible
  memory.redo(nil, 1)
  luaunit.assert_equals(channel1.step_note_masks[1], 67)
  
  -- Channel 2 redo should still work
  memory.redo(nil, 2)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end


function test_channel_history_should_remain_intact_when_another_channel_history_is_wiped_after_new_event_added_in_middle_of_history()
  memory.init()
  program.init()
  
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Add events in specific order
  memory.record_event(channel1, "note_mask", {
    step = 1,
    note = 60,
    velocity = 100,
    length = 1
  })

  memory.record_event(channel1, "note_mask", {
    step = 2,
    note = 61,
    velocity = 100,
    length = 1
  })
  
  
  memory.record_event(channel2, "note_mask", {
    step = 1,
    note = 64,
    velocity = 90,
    length = 1
  })
  
  memory.record_event(channel2, "note_mask", {
    step = 2,
    note = 66,
    velocity = 90,
    length = 1
  })

  print(#memory.get_recent_events(nil, 2, 25))

  memory.undo(nil, 1)

  print(#memory.get_recent_events(nil, 2, 25))

  memory.record_event(channel1, "note_mask", {
    step = 2,
    note = 61,
    velocity = 100,
    length = 1
  })
  

  luaunit.assert_equals(memory.get_event_count(nil, 2), 2)
  luaunit.assert_equals(#memory.get_recent_events(nil, 2, 25), 2)
end
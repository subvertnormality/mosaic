local recorder = include("mosaic/lib/recorder")

function test_recorder_init_should_create_empty_event_store()
  recorder.init()
  program.init()
  local state = recorder.get_state()
  
  luaunit.assert_equals(#state.event_history, 0)
  luaunit.assert_equals(state.current_event_index, 0)
end

function test_recorder_should_add_single_note()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_note(channel, 1, 60, 100)
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
end

function test_recorder_should_add_chord()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_chord(channel, 1, {60, 64, 67}, {100, 90, 80}, {1, 3, 5})
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_recorder_should_undo_last_note()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 2, 64, 90)
  recorder.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
end

function test_recorder_should_redo_undone_note()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 2, 64, 90)
  recorder.undo()
  recorder.redo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 64)
end

function test_recorder_should_clear_redo_history_after_new_note()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 2, 64, 90)
  recorder.undo()
  recorder.add_note(channel, 2, 67, 80)
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 2)
  luaunit.assert_equals(channel.step_note_masks[2], 67)
end

function test_recorder_should_maintain_separate_channels()
  recorder.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  recorder.add_note(channel1, 1, 60, 100)
  recorder.add_note(channel2, 1, 64, 90)
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_recorder_should_maintain_event_history()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_note(channel, 1, 60, 100)
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 1)
  luaunit.assert_equals(state.current_event_index, 1)
  luaunit.assert_equals(state.event_history[1].type, "note_added")
  luaunit.assert_equals(state.event_history[1].data.note, 60)
end


function test_recorder_should_maintain_event_index_during_undo_redo()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 2, 64, 90)
  recorder.undo()
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 1)
  luaunit.assert_equals(#state.event_history, 2)
end

function test_recorder_undo_should_clear_notes_from_channel()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add two notes
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 2, 64, 90)
  
  -- Verify both notes are present
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_trig_masks[2], 1)
  luaunit.assert_equals(channel.step_note_masks[2], 64)
  
  -- Undo the second note
  recorder.undo()
  
  -- Verify first note remains but second note is fully cleared
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_trig_masks[2], nil)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
  luaunit.assert_equals(channel.step_velocity_masks[2], nil)
  luaunit.assert_equals(channel.step_length_masks[2], nil)
  
  -- Undo the first note
  recorder.undo()
  
  -- Verify both notes are fully cleared
  luaunit.assert_equals(channel.step_trig_masks[1], nil)
  luaunit.assert_equals(channel.step_note_masks[1], nil)
  luaunit.assert_equals(channel.step_velocity_masks[1], nil)
  luaunit.assert_equals(channel.step_length_masks[1], nil)
end

function test_recorder_should_handle_undo_when_empty()
  recorder.init()
  program.init()
  
  recorder.undo()
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(#state.event_history, 0)
end

function test_recorder_should_handle_redo_when_empty()
  recorder.init()
  program.init()
  
  recorder.redo()
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(#state.event_history, 0)
end

function test_recorder_should_handle_multiple_notes_on_same_step()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 1, 64, 90)  -- Overwrites previous note
  
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  recorder.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
end

function test_recorder_should_handle_chord_after_note_on_same_step()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_chord(channel, 1, {64, 67, 71}, {90, 80, 70}, {1, 3, 5})
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  recorder.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_recorder_should_handle_note_after_chord_on_same_step()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_chord(channel, 1, {60, 64, 67}, {100, 90, 80}, {1, 3, 5})
  recorder.add_note(channel, 1, 71, 70)
  
  luaunit.assert_equals(channel.step_note_masks[1], 71)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  recorder.undo()
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_recorder_should_handle_undo_redo_at_boundaries()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test undo at start
  recorder.undo()
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  
  -- Add and undo all notes
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 2, 64, 90)
  recorder.undo()
  recorder.undo()
  
  -- Test undo past beginning
  recorder.undo()
  state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  
  -- Redo all notes
  recorder.redo()
  recorder.redo()
  
  -- Test redo past end
  recorder.redo()
  state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 2)
end

function test_recorder_should_maintain_correct_velocities_during_undo_redo()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 1, 60, 80)
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  
  recorder.undo()
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  recorder.redo()
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
end

function test_recorder_should_handle_empty_chord_degrees()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_chord(channel, 1, {60, 64}, {100, 90}, {})
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_recorder_should_preserve_event_history_during_clear()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_note(channel, 1, 60, 100)
  program.init()  -- Should not affect recorder state
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 1)
  luaunit.assert_equals(state.current_event_index, 1)
  luaunit.assert_equals(state.event_history[1].data.note, 60)
end



function test_recorder_should_preserve_original_state()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  channel.step_length_masks[1] = 2
  
  -- Record new note
  recorder.add_note(channel, 1, 60, 100)
  
  -- Verify state changed
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  -- Undo should restore original state
  recorder.undo()
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
end

function test_recorder_should_preserve_original_chord_state()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial chord state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  channel.step_length_masks[1] = 2
  if not channel.step_chord_masks then channel.step_chord_masks = {} end
  channel.step_chord_masks[1] = {1, 4, 7}
  
  -- Record new note (which should clear chord)
  recorder.add_note(channel, 1, 60, 100)
  
  -- Verify chord was cleared
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  -- Undo should restore original chord
  recorder.undo()
  
  luaunit.assert_equals(channel.step_chord_masks[1][1], 1)
  luaunit.assert_equals(channel.step_chord_masks[1][2], 4)
  luaunit.assert_equals(channel.step_chord_masks[1][3], 7)
end

-- Update the test to match the expected behavior:
function test_recorder_should_handle_multiple_edits_to_same_step()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  
  -- Make multiple edits
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 1, 64, 90)
  recorder.add_note(channel, 1, 67, 80)
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 67)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  
  -- Undo should go back through the history one step at a time
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
end

function test_recorder_should_preserve_nil_states()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Record new note in empty step
  recorder.add_note(channel, 1, 60, 100)
  
  -- Verify note was added
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Undo should restore nil state
  recorder.undo()
  
  luaunit.assert_equals(channel.step_trig_masks[1], nil)
  luaunit.assert_equals(channel.step_note_masks[1], nil)
  luaunit.assert_equals(channel.step_velocity_masks[1], nil)
  luaunit.assert_equals(channel.step_length_masks[1], nil)
end


function test_recorder_should_handle_mixed_note_and_chord_edits_on_same_step()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  
  -- Series of mixed edits
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_chord(channel, 1, {64, 67, 71}, {90, 85, 80}, {1, 3, 5})
  recorder.add_note(channel, 1, 72, 110)
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  luaunit.assert_equals(channel.step_velocity_masks[1], 110)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  -- Undo to chord
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Undo to note
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  -- Undo to original
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
end

function test_recorder_should_handle_interleaved_step_edits()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial states
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_trig_masks[2] = 1
  channel.step_note_masks[2] = 50
  
  -- Interleaved edits
  recorder.add_note(channel, 1, 60, 100)  -- Edit step 1
  recorder.add_note(channel, 2, 62, 90)   -- Edit step 2
  recorder.add_note(channel, 1, 64, 110)  -- Edit step 1 again
  recorder.add_note(channel, 2, 65, 95)   -- Edit step 2 again
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_note_masks[2], 65)
  
  -- Undo should affect steps independently
  recorder.undo()  -- Undo step 2 second edit
  luaunit.assert_equals(channel.step_note_masks[1], 64)  -- Step 1 unchanged
  luaunit.assert_equals(channel.step_note_masks[2], 62)  -- Step 2 back one
  
  recorder.undo()  -- Undo step 1 second edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 62)
  
  recorder.undo()  -- Undo step 2 first edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 50)
  
  recorder.undo()  -- Undo step 1 first edit
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_note_masks[2], 50)
end

function test_recorder_should_handle_partial_undo_with_new_edits()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  
  -- First series of edits
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_note(channel, 1, 64, 90)
  recorder.add_note(channel, 1, 67, 80)
  
  -- Partial undo
  recorder.undo()
  recorder.undo()
  
  -- Should be back to first edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Add new edits
  recorder.add_note(channel, 1, 72, 110)
  recorder.add_note(channel, 1, 74, 115)
  
  -- Verify new state
  luaunit.assert_equals(channel.step_note_masks[1], 74)
  
  -- Undo through new edits
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Back to original
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], 48)
end

function test_recorder_should_handle_redo_after_multiple_undos()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  
  -- Build up history
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_chord(channel, 1, {64, 67, 71}, {90, 85, 80}, {1, 3, 5})
  recorder.add_note(channel, 1, 72, 110)
  
  -- Undo everything
  recorder.undo()
  recorder.undo()
  recorder.undo()
  
  -- Verify back to original
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  
  -- Redo everything
  recorder.redo()
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  recorder.redo()
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  recorder.redo()
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  luaunit.assert_equals(channel.step_velocity_masks[1], 110)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_recorder_should_preserve_original_state_across_multiple_edits()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up complex initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  if not channel.step_chord_masks then channel.step_chord_masks = {} end
  channel.step_chord_masks[1] = {1, 4, 7}
  
  -- Multiple edits of different types
  recorder.add_note(channel, 1, 60, 100)
  recorder.add_chord(channel, 1, {64, 67, 71}, {90, 85, 80}, {1, 3, 5})
  recorder.add_note(channel, 1, 72, 110)
  recorder.add_chord(channel, 1, {76, 79, 83}, {95, 90, 85}, {1, 3, 5})
  
  -- Undo all the way back
  recorder.undo()
  recorder.undo()
  recorder.undo()
  recorder.undo()
  
  -- Verify original state is perfectly preserved
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 48)
  luaunit.assert_equals(channel.step_velocity_masks[1], 70)
  local original_chord = channel.step_chord_masks[1]
  luaunit.assert_equals(original_chord[1], 1)
  luaunit.assert_equals(original_chord[2], 4)
  luaunit.assert_equals(original_chord[3], 7)
end
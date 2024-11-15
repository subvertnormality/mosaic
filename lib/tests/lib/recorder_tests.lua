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
  recorder.add_step(channel, 1, 60, 100, 1)
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
end

function test_recorder_should_add_step()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_step(channel, 1, 60, 100, 1, {1, 3, 5})
  
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
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 2, 64, 90, 1)
  recorder.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], nil)
end

function test_recorder_should_redo_undone_note()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 2, 64, 90, 1)
  recorder.undo()
  recorder.redo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 64)
end

function test_recorder_should_clear_redo_history_after_new_note()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 2, 64, 90, 1)
  recorder.undo()
  recorder.add_step(channel, 2, 67, 80, 1)
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.event_history.size, 2)
  luaunit.assert_equals(channel.step_note_masks[2], 67)
end

function test_recorder_should_maintain_separate_channels()
  recorder.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  recorder.add_step(channel1, 1, 60, 100, 1)
  recorder.add_step(channel2, 1, 64, 90, 1)
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_recorder_should_maintain_event_history()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_step(channel, 1, 60, 100, 1)
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1)
  luaunit.assert_equals(state.current_event_index, 1)
  local first_event = state.event_history:get(1)
  luaunit.assert_not_nil(first_event)
  luaunit.assert_equals(first_event.data.note, 60)
end


function test_recorder_should_maintain_event_index_during_undo_redo()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 2, 64, 90, 1)
  recorder.undo()
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 1)
  luaunit.assert_equals(state.event_history.size, 2)
end

function test_recorder_undo_should_clear_notes_from_channel()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add two notes
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 2, 64, 90, 1)
  
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
  
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1)  -- Overwrites previous note
  
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
  
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1, {1, 3, 5})
  
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
  
  recorder.add_step(channel, 1, 60, 100, 1, {1, 3, 5})
  recorder.add_step(channel, 1, 71, 70, 1)   -- Should not affect chord
  
  -- Verify chord remains
  luaunit.assert_equals(channel.step_note_masks[1], 71)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  recorder.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  chord_mask = channel.step_chord_masks[1]
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
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 2, 64, 90, 1)
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
  
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 60, 80, 1)
  
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
  
  recorder.add_step(channel, 1, 60, 100, 1, {})
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end

function test_recorder_should_preserve_event_history_during_clear()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_step(channel, 1, 60, 100, 1)
  program.init()  -- Should not affect recorder state
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1)
  luaunit.assert_equals(state.current_event_index, 1)
  local first_event = state.event_history:get(1)
  luaunit.assert_not_nil(first_event)
  luaunit.assert_equals(first_event.data.note, 60)
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
  recorder.add_step(channel, 1, 60, 100, 1)
  
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
  
  -- Record new note (should not affect chord)
  recorder.add_step(channel, 1, 60, 100, 1)
  
  -- Verify chord preserved
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 4)
  luaunit.assert_equals(chord_mask[3], 7)
  
  -- Explicitly clear chord
  recorder.add_step(channel, 1, nil, nil, nil, {})
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
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
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1)
  recorder.add_step(channel, 1, 67, 80, 1)
  
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
  recorder.add_step(channel, 1, 60, 100, 1)
  
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
  
  -- Series of mixed edits - chords should remain unless explicitly changed
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1, {1, 3, 5})
  recorder.add_step(channel, 1, 72, 110, 1)  -- Should not affect chord
  
  -- Verify final state
  luaunit.assert_equals(channel.step_note_masks[1], 72)
  luaunit.assert_equals(channel.step_velocity_masks[1], 110)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Explicitly clear chord
  recorder.add_step(channel, 1, nil, nil, nil, {})
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
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
  recorder.add_step(channel, 1, 60, 100, 1)  -- Edit step 1
  recorder.add_step(channel, 2, 62, 90, 1)   -- Edit step 2
  recorder.add_step(channel, 1, 64, 110, 1)  -- Edit step 1 again
  recorder.add_step(channel, 2, 65, 95, 1)   -- Edit step 2 again
  
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
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1)
  recorder.add_step(channel, 1, 67, 80, 1)
  
  -- Partial undo
  recorder.undo()
  recorder.undo()
  
  -- Should be back to first edit
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  -- Add new edits
  recorder.add_step(channel, 1, 72, 110, 1)
  recorder.add_step(channel, 1, 74, 115, 1)
  
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
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1, {1, 3, 5})
  recorder.add_step(channel, 1, 72, 110, 1)
  
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
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
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
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1, {1, 3, 5})
  recorder.add_step(channel, 1, 72, 110, 1)
  recorder.add_step(channel, 1, 76, 95, 1, {1, 3, 5})
  
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

function test_recorder_should_preserve_states_across_patterns()
  recorder.init()
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
  recorder.add_step(channel_pattern1, 1, 60, 100, 1, {}, 1)  -- Pattern 1
  recorder.add_step(channel_pattern2, 1, 62, 90, 1, {}, 2)   -- Pattern 2
  
  -- Verify each pattern tracked separately
  recorder.undo()  -- Undo pattern 2 edit
  luaunit.assert_equals(channel_pattern2.step_note_masks[1], 48)  -- Pattern 2 back to original
  luaunit.assert_equals(channel_pattern1.step_note_masks[1], 60)  -- Pattern 1 unchanged
  
  recorder.undo()  -- Undo pattern 1 edit
  luaunit.assert_equals(channel_pattern1.step_note_masks[1], 48)  -- Pattern 1 back to original
end

function test_recorder_should_undo_redo_in_correct_pattern()
  recorder.init()
  program.init()
  
  -- Set up two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1_pattern1 = program.get_channel(1, 1)
  channel1_pattern1.step_note_masks[1] = 48
  
  program.set_selected_sequencer_pattern(2)
  local channel1_pattern2 = program.get_channel(2, 1)
  channel1_pattern2.step_note_masks[1] = 50
  
  -- Add notes to both patterns, explicitly passing song pattern
  recorder.add_step(channel1_pattern1, 1, 60, 100, 1, {}, 1)  -- Pattern 1
  recorder.add_step(channel1_pattern2, 1, 62, 90, 1, {}, 2)   -- Pattern 2
  
  -- Undo should restore correct pattern
  recorder.undo()  -- Should affect pattern 2
  luaunit.assert_equals(channel1_pattern2.step_note_masks[1], 50)  -- Back to original
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 60)  -- Pattern 1 unchanged
  
  recorder.undo()  -- Should affect pattern 1
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 48)  -- Back to original
  
  -- Redo should also respect patterns
  recorder.redo()  -- Should affect pattern 1
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1_pattern2.step_note_masks[1], 50)
  
  recorder.redo()  -- Should affect pattern 2
  luaunit.assert_equals(channel1_pattern2.step_note_masks[1], 62)
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 60)
end

function test_recorder_should_find_previous_events_in_same_pattern()
  recorder.init()
  program.init()
  
  -- Set up two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1_pattern1 = program.get_channel(1, 1)
  
  program.set_selected_sequencer_pattern(2)
  local channel1_pattern2 = program.get_channel(2, 1)
  
  -- Create sequence of events across patterns
  recorder.add_step(channel1_pattern1, 1, 60, 100, 1, {}, 1)  -- Pattern 1
  recorder.add_step(channel1_pattern2, 1, 62, 90, 1, {}, 2)   -- Pattern 2
  recorder.add_step(channel1_pattern1, 1, 64, 80, 1, {}, 1)   -- Pattern 1
  
  -- Undo should find previous event in same pattern
  recorder.undo()  -- Undo last note in pattern 1
  luaunit.assert_equals(channel1_pattern1.step_note_masks[1], 60)  -- Back to first note
  luaunit.assert_equals(channel1_pattern2.step_note_masks[1], 62)  -- Pattern 2 unchanged
end

function test_recorder_should_not_modify_step_key_when_same_channel_number_in_different_patterns()
  recorder.init()
  program.init()

  -- Set up two channels with same number but in different patterns
  program.set_selected_sequencer_pattern(1)
  local channel1_pattern1 = program.get_channel(1, 1)
  channel1_pattern1.step_note_masks[1] = 48

  program.set_selected_sequencer_pattern(2)
  local channel1_pattern2 = program.get_channel(2, 1)  -- Same channel number (1)
  channel1_pattern2.step_note_masks[1] = 50

  -- Add note to first pattern
  recorder.add_step(channel1_pattern1, 1, 60, 100, 1, {}, 1)

  -- Access pc_state1 after adding step to pattern 1
  local state = recorder.get_state()
  local key1 = "1_1"
  local step_key = "1"
  local pc_state1 = state.pattern_channels[key1]
  luaunit.assert_equals(pc_state1.original_states[step_key].note_mask, 48)

  -- Add note to second pattern
  recorder.add_step(channel1_pattern2, 1, 62, 90, 1, {}, 2)

  -- Access pc_state2 after adding step to pattern 2
  local key2 = "2_1"
  local pc_state2 = state.pattern_channels[key2]
  luaunit.assert_equals(pc_state2.original_states[step_key].note_mask, 50)
end


function test_recorder_should_store_deep_copies_of_chord_masks()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial chord
  if not channel.step_chord_masks then channel.step_chord_masks = {} end
  channel.step_chord_masks[1] = {1, 3, 5}
  
  -- Add new chord
  recorder.add_step(channel, 1, 60, 100, 1, {2, 4, 6})
  
  -- Modify original chord array
  channel.step_chord_masks[1][1] = 7
  
  -- Undo should restore original values, not modified ones
  recorder.undo()
  
  luaunit.assert_equals(channel.step_chord_masks[1][1], 1)
  luaunit.assert_equals(channel.step_chord_masks[1][2], 3)
  luaunit.assert_equals(channel.step_chord_masks[1][3], 5)
end

function test_recorder_should_handle_deleted_recreated_channels()
  recorder.init()
  program.init()
  
  -- Add note to channel
  local channel = program.get_channel(1, 1)
  recorder.add_step(channel, 1, 60, 100, 1)
  
  -- Simulate channel deletion/recreation
  program.init()
  channel = program.get_channel(1, 1)
  
  -- Verify recorder state preserved
  local state = recorder.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1)
  local first_event = state.event_history:get(1)
  luaunit.assert_not_nil(first_event)
  luaunit.assert_equals(first_event.data.note, 60)
  
  -- Verify undo still works
  recorder.undo()
  luaunit.assert_equals(channel.step_note_masks[1], nil)
end

function test_recorder_should_preserve_event_order_during_undo()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 2, 62, 90, 1)
  recorder.add_step(channel, 3, 64, 80, 1)
  
  -- Get initial event order
  local state = recorder.get_state()
  local initial_events = {}
  for i, event in ipairs(state.event_history) do
    initial_events[i] = event.data.note
  end
  
  -- Undo everything
  recorder.undo()
  recorder.undo()
  recorder.undo()
  
  -- Redo everything
  recorder.redo()
  recorder.redo()
  recorder.redo()
  
  -- Check event order is preserved
  state = recorder.get_state()
  for i, event in ipairs(state.event_history) do
    luaunit.assert_equals(event.data.note, initial_events[i])
  end
end

function test_recorder_should_handle_nil_chord_degrees_correctly()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_step(channel, 1, 60, 100, 1, nil)
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  recorder.add_step(channel, 1, 62, 95, 1, {})
  
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
end


function test_recorder_should_update_working_pattern()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_step(channel, 1, 60, 100, 1)
  
  -- Check masks are set
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  -- Check working pattern is updated
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 1)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 1)
end

function test_recorder_should_restore_working_pattern_on_undo()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add two steps
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1)
  
  -- Undo last step
  recorder.undo()
  
  -- Check working pattern reflects first step
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
end

function test_recorder_should_clear_working_pattern_on_full_undo()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add and undo a step
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.undo()
  
  -- Check working pattern is cleared
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 1)
end

function test_recorder_should_handle_multiple_patterns_working_pattern()
  recorder.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(2, 1)
  
  -- Add notes to different patterns
  recorder.add_step(channel1, 1, 60, 100, 1)
  recorder.add_step(channel2, 1, 64, 90, 1)
  
  -- Check working patterns are independent
  luaunit.assert_equals(channel1.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel2.working_pattern.note_mask_values[1], 64)
end


function test_recorder_should_preserve_working_pattern_original_state()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set up initial working pattern state
  channel.working_pattern.trig_values[1] = 1
  channel.working_pattern.note_mask_values[1] = 48
  channel.working_pattern.velocity_values[1] = 70
  channel.working_pattern.lengths[1] = 2
  
  -- Add new note
  recorder.add_step(channel, 1, 60, 100, 1)
  
  -- Verify working pattern changed
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  -- Undo should restore original working pattern
  recorder.undo()
  
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 1)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 48)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 70)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end

function test_recorder_should_handle_working_pattern_multiple_edits()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add series of edits
  recorder.add_step(channel, 1, 60, 100, 1)  -- First edit
  recorder.add_step(channel, 1, 64, 90, 1)   -- Second edit
  recorder.add_step(channel, 1, 67, 80, 1)   -- Third edit
  
  -- Verify final working pattern state
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 67)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 80)
  
  -- Undo each edit and verify working pattern
  recorder.undo()  -- Back to second edit
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
  
  recorder.undo()  -- Back to first edit
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  recorder.undo()  -- Back to original
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
end

function test_recorder_should_preserve_working_pattern_during_redo()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add and undo some steps
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1)
  recorder.undo()
  recorder.undo()
  
  -- Verify back to initial state
  luaunit.assert_equals(channel.working_pattern.trig_values[1], 0)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 0)
  
  -- Redo and verify working pattern restored
  recorder.redo()
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  recorder.redo()
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
end

function test_recorder_should_handle_working_pattern_across_different_steps()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add notes to different steps
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 2, 64, 90, 1)
  
  -- Verify both steps in working pattern
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[2], 64)
  
  -- Undo second step
  recorder.undo()
  
  -- First step should remain unchanged, second step cleared
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.note_mask_values[2], 0)
  luaunit.assert_equals(channel.working_pattern.trig_values[2], 0)
end

function test_recorder_should_handle_working_pattern_with_chords()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add chord
  recorder.add_step(channel, 1, 60, 100, 1, {1, 3, 5})
  
  -- Verify working pattern values
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
  
  -- Add normal note (clearing chord)
  recorder.add_step(channel, 1, 64, 90, 1)
  
  -- Verify working pattern updated
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 64)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 90)
  
  -- Undo should restore chord state in working pattern
  recorder.undo()
  
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
end

function test_recorder_should_preserve_working_pattern_when_clearing_redo_history()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Create some history
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 64, 90, 1)
  recorder.undo()
  
  -- Working pattern should show first note
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  
  -- Add new note (clearing redo history)
  recorder.add_step(channel, 1, 67, 80, 1)
  
  -- Working pattern should show new note
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 67)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 80)
  
  -- Undo should restore to first note
  recorder.undo()
  
  luaunit.assert_equals(channel.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel.working_pattern.velocity_values[1], 100)
end

function test_recorder_should_maintain_working_pattern_across_multiple_patterns()
  recorder.init()
  program.init()
  
  -- Set up two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)
  
  -- Add notes to different patterns
  recorder.add_step(channel1, 1, 60, 100, 1, {}, 1)
  recorder.add_step(channel2, 1, 64, 90, 1, {}, 2)
  
  -- Verify working patterns are independent
  luaunit.assert_equals(channel1.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel2.working_pattern.note_mask_values[1], 64)
  
  -- Undo second pattern
  recorder.undo()
  
  -- Pattern 1 should be unchanged, pattern 2 cleared
  luaunit.assert_equals(channel1.working_pattern.note_mask_values[1], 60)
  luaunit.assert_equals(channel2.working_pattern.note_mask_values[1], 0)
  luaunit.assert_equals(channel2.working_pattern.trig_values[1], 0)
end

function test_recorder_should_handle_nil_channel()
  recorder.init()
  program.init()
  
  -- Attempt to add step with nil channel
  recorder.add_step(nil, 1, 60, 100, 1)
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 0)
  luaunit.assert_equals(state.current_event_index, 0)
end

function test_recorder_should_handle_invalid_step_numbers()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test negative step
  recorder.add_step(channel, -1, 60, 100, 1)
  luaunit.assert_equals(channel.step_note_masks[-1], nil)
  
  -- Test zero step
  recorder.add_step(channel, 0, 60, 100, 1)
  luaunit.assert_equals(channel.step_note_masks[0], nil)
  
  -- Test non-numeric step
  recorder.add_step(channel, "invalid", 60, 100, 1)
  luaunit.assert_equals(channel.step_note_masks["invalid"], nil)
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 0)
end

function test_recorder_should_handle_invalid_note_velocity_values()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test invalid note values
  recorder.add_step(channel, 1, -1, 100, 1)  -- Negative note
  recorder.add_step(channel, 1, 128, 100, 1) -- Note too high
  recorder.add_step(channel, 1, "C4", 100, 1) -- Non-numeric note
  
  -- Test invalid velocity values  
  recorder.add_step(channel, 1, 60, -1, 1)    -- Negative velocity
  recorder.add_step(channel, 1, 60, 128, 1)   -- Velocity too high
  recorder.add_step(channel, 1, 60, "ff", 1)  -- Non-numeric velocity
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 0)
  luaunit.assert_equals(channel.step_note_masks[1], nil)
end

function test_recorder_should_persist_state_across_pattern_switches()
  recorder.init()
  program.init()
  
  -- Add notes to pattern 1
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  recorder.add_step(channel1, 1, 60, 100, 1)
  
  -- Switch to pattern 2 and add notes
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)
  recorder.add_step(channel2, 1, 64, 90, 1)
  
  -- Switch back to pattern 1 and verify state
  program.set_selected_sequencer_pattern(1)
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  
  -- Switch to pattern 2 and verify state
  program.set_selected_sequencer_pattern(2)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
  
  -- Undo in pattern 2
  recorder.undo()
  luaunit.assert_equals(channel2.step_note_masks[1], nil)
  
  -- Switch to pattern 1 and verify unaffected
  program.set_selected_sequencer_pattern(1)
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
end

function test_recorder_should_clear_redo_history_on_cross_pattern_edits()
  recorder.init()
  program.init()
  
  -- Build up history in pattern 1
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  recorder.add_step(channel1, 1, 60, 100, 1)
  recorder.add_step(channel1, 1, 64, 90, 1)
  recorder.undo()
  
  -- Add note in pattern 2 
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)
  recorder.add_step(channel2, 1, 67, 80, 1)
  
  -- Try to redo pattern 1 edit
  program.set_selected_sequencer_pattern(1)
  recorder.redo()
  
  -- Verify redo was cleared
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  
  local state = recorder.get_state()
  local pattern1_state = state.pattern_channels["1_1"]
  luaunit.assert_equals(pattern1_state.current_index, 1)
end

function test_recorder_should_validate_chord_degrees()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test invalid chord degrees
  recorder.add_step(channel, 1, 60, 100, 1, {-1, 3, 5})     -- Negative degree
  recorder.add_step(channel, 1, 60, 100, 1, {1, 8, 5})      -- Degree too high
  recorder.add_step(channel, 1, 60, 100, 1, {"1", "3", "5"}) -- Non-numeric degrees
  recorder.add_step(channel, 1, 60, 100, 1, {1, 1, 1})      -- Duplicate degrees
  
  -- Verify invalid chords weren't recorded
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 0)
end

function test_recorder_undo_should_be_isolated_to_pattern()
  recorder.init()
  program.init()
  
  -- Add notes to two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  recorder.add_step(channel1, 1, 60, 100, 1)
  recorder.add_step(channel1, 2, 64, 90, 1)
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)
  recorder.add_step(channel2, 1, 67, 80, 1)
  recorder.add_step(channel2, 2, 71, 70, 1)
  
  -- Undo in pattern 2
  recorder.undo(2, 1)
  
  -- Pattern 2 should have last note undone
  luaunit.assert_equals(channel2.step_note_masks[2], nil)
  luaunit.assert_equals(channel2.step_note_masks[1], 67)
  
  -- Pattern 1 should be unchanged
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_note_masks[2], 64)
end

function test_recorder_redo_should_be_isolated_to_pattern()
  recorder.init()
  program.init()
  
  -- Add and undo notes in two patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  recorder.add_step(channel1, 1, 60, 100, 1)
  recorder.add_step(channel1, 2, 64, 90, 1)
  recorder.undo(1, 1)
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)
  recorder.add_step(channel2, 1, 67, 80, 1)
  recorder.add_step(channel2, 2, 71, 70, 1)
  recorder.undo(2, 1)
  
  -- Redo in pattern 2
  recorder.redo(2, 1)
  
  -- Pattern 2 should have note redone
  luaunit.assert_equals(channel2.step_note_masks[2], 71)
  
  -- Pattern 1 should still have last note undone
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel1.step_note_masks[2], nil)
end

function test_recorder_should_track_separate_histories_per_pattern()
  recorder.init()
  program.init()
  
  -- Add notes alternating between patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  recorder.add_step(channel1, 1, 60, 100, 1)
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)
  recorder.add_step(channel2, 1, 67, 80, 1)
  
  program.set_selected_sequencer_pattern(1)
  recorder.add_step(channel1, 2, 64, 90, 1)
  
  program.set_selected_sequencer_pattern(2)
  recorder.add_step(channel2, 2, 71, 70, 1)
  
  -- Verify separate histories tracked
  local state = recorder.get_state()
  local pattern1_history = state.pattern_channels["1_1"].event_history
  local pattern2_history = state.pattern_channels["2_1"].event_history
  
  luaunit.assert_equals(pattern1_history:get_size(), 2)
  luaunit.assert_equals(pattern1_history:get(1).data.note, 60)
  luaunit.assert_equals(pattern1_history:get(2).data.note, 64)
  
  luaunit.assert_equals(pattern2_history:get_size(), 2)
  luaunit.assert_equals(pattern2_history:get(1).data.note, 67)
  luaunit.assert_equals(pattern2_history:get(2).data.note, 71)
end

function test_recorder_should_count_events_per_channel()
  recorder.init()
  program.init()
  
  -- Add notes to different patterns/channels
  local channel1 = program.get_channel(1, 1) 
  recorder.add_step(channel1, 1, 60, 100, 1)
  recorder.add_step(channel1, 2, 64, 90, 1)
  
  local channel2 = program.get_channel(1, 2)
  recorder.add_step(channel2, 1, 67, 80, 1)
  
  luaunit.assert_equals(recorder.get_event_count(1, 1), 2)
  luaunit.assert_equals(recorder.get_event_count(1, 2), 1)
  luaunit.assert_equals(recorder.get_event_count(2, 1), 0)
  
  -- Test after undo
  recorder.undo()
  luaunit.assert_equals(recorder.get_event_count(1, 2), 0)
  luaunit.assert_equals(recorder.get_event_count(1, 1), 2)
end


function test_recorder_should_count_events_across_patterns()
  recorder.init()
  program.init()
  
  -- Add notes to different patterns/channels
  program.set_selected_sequencer_pattern(1)
  local channel1_p1 = program.get_channel(1, 1)
  local channel2_p1 = program.get_channel(1, 2)
  recorder.add_step(channel1_p1, 1, 60, 100, 1)
  recorder.add_step(channel2_p1, 1, 64, 90, 1)
  
  program.set_selected_sequencer_pattern(2)
  local channel1_p2 = program.get_channel(2, 1)
  local channel2_p2 = program.get_channel(2, 2)
  recorder.add_step(channel1_p2, 1, 67, 80, 1)
  recorder.add_step(channel2_p2, 1, 71, 70, 1)
  recorder.add_step(channel1_p2, 2, 72, 85, 1)
  
  -- Check counts across patterns and channels
  luaunit.assert_equals(recorder.get_event_count(1, 1), 1)
  luaunit.assert_equals(recorder.get_event_count(1, 2), 1)
  luaunit.assert_equals(recorder.get_event_count(2, 1), 2)
  luaunit.assert_equals(recorder.get_event_count(2, 2), 1)
  
  -- Test undo in specific pattern/channel
  recorder.undo(2, 1) -- Undo last note in pattern 2, channel 1
  luaunit.assert_equals(recorder.get_event_count(2, 1), 1)
  luaunit.assert_equals(recorder.get_event_count(2, 2), 1)
  
  -- Test redo in specific pattern/channel
  recorder.redo(2, 1)
  luaunit.assert_equals(recorder.get_event_count(2, 1), 2)
end

function test_recorder_should_handle_custom_length()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_step(channel, 1, 60, 100, 2)
  
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
end

function test_recorder_should_validate_length()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test invalid lengths
  recorder.add_step(channel, 1, 60, 100, -1)      -- Negative length
  recorder.add_step(channel, 1, 60, 100, "2")     -- Non-numeric length
  
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 0)
end

function test_recorder_should_preserve_length_during_undo_redo()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_step(channel, 1, 60, 100, 2)
  recorder.add_step(channel, 1, 64, 90, 3)
  
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  
  recorder.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  recorder.redo()
  luaunit.assert_equals(channel.step_length_masks[1], 3)
end

function test_recorder_should_handle_multiple_length_edits_to_same_step()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Series of length edits
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 60, 100, 2)
  recorder.add_step(channel, 1, 60, 100, 4)
  
  luaunit.assert_equals(channel.step_length_masks[1], 4)
  
  -- Undo should restore previous lengths
  recorder.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  recorder.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 1)
end

function test_recorder_should_preserve_length_across_patterns()
  recorder.init()
  program.init()
  
  -- Set up channels in different patterns
  program.set_selected_sequencer_pattern(1)
  local channel1 = program.get_channel(1, 1)
  recorder.add_step(channel1, 1, 60, 100, 2)
  
  program.set_selected_sequencer_pattern(2)
  local channel2 = program.get_channel(2, 1)
  recorder.add_step(channel2, 1, 64, 90, 3)
  
  -- Verify lengths are independent
  luaunit.assert_equals(channel1.step_length_masks[1], 2)
  luaunit.assert_equals(channel2.step_length_masks[1], 3)
  
  -- Undo in pattern 2 shouldn't affect pattern 1
  recorder.undo()
  luaunit.assert_equals(channel1.step_length_masks[1], 2)
  luaunit.assert_equals(channel2.step_length_masks[1], nil)
end

function test_recorder_should_maintain_length_in_working_pattern()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  recorder.add_step(channel, 1, 60, 100, 3)
  
  -- Verify length in both masks and working pattern
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 3)
  
  recorder.undo()
  
  -- Verify length cleared from both
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 1)  -- Default value
end

function test_recorder_should_handle_interleaved_length_edits()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add steps with different lengths
  recorder.add_step(channel, 1, 60, 100, 2)
  recorder.add_step(channel, 2, 64, 90, 3)
  recorder.add_step(channel, 1, 60, 100, 4)  -- Change step 1 length
  
  -- Verify final state
  luaunit.assert_equals(channel.step_length_masks[1], 4)
  luaunit.assert_equals(channel.step_length_masks[2], 3)
  
  -- Undo last edit
  recorder.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  luaunit.assert_equals(channel.step_length_masks[2], 3)
end

function test_recorder_should_preserve_original_length_state()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  channel.step_trig_masks[1] = 1
  channel.step_note_masks[1] = 48
  channel.step_velocity_masks[1] = 70
  channel.step_length_masks[1] = 4
  channel.working_pattern.lengths[1] = 4
  
  -- Record new note with different length
  recorder.add_step(channel, 1, 60, 100, 2)
  
  -- Verify state changed
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 2)
  
  -- Undo should restore original length
  recorder.undo()
  luaunit.assert_equals(channel.step_length_masks[1], 4)
  luaunit.assert_equals(channel.working_pattern.lengths[1], 4)
end

function test_recorder_should_persist_length_through_redo()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add and undo a series of edits
  recorder.add_step(channel, 1, 60, 100, 2)
  recorder.add_step(channel, 1, 60, 100, 3)
  recorder.add_step(channel, 1, 60, 100, 4)
  recorder.undo()
  recorder.undo()
  recorder.undo()
  
  -- Verify all undone
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  
  -- Redo should restore lengths in order
  recorder.redo()
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  recorder.redo()
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  
  recorder.redo()
  luaunit.assert_equals(channel.step_length_masks[1], 4)
end

function test_recorder_should_validate_length_with_chord()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test invalid length with chord
  recorder.add_step(channel, 1, 60, 100, -1, {1, 3, 5})
  
  luaunit.assert_equals(channel.step_length_masks[1], nil)
  luaunit.assert_equals(channel.step_chord_masks[1], nil)
  
  -- Test valid length with chord
  recorder.add_step(channel, 1, 60, 100, 2, {1, 3, 5})
  
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_recorder_should_handle_nil_note_and_velocity()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  recorder.add_step(channel, 1, 60, 100, 1)
  
  -- Modify only length
  recorder.add_step(channel, 1, nil, nil, 2)
  
  -- Original note and velocity should be preserved
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  -- Length should be updated
  luaunit.assert_equals(channel.step_length_masks[1], 2)
end

function test_recorder_should_preserve_chord_when_only_changing_length()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state with chord
  recorder.add_step(channel, 1, 60, 100, 1, {1, 3, 5})
  
  -- Modify only length
  recorder.add_step(channel, 1, nil, nil, 2)
  
  -- Verify chord is preserved
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  -- Verify other values
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
end

function test_recorder_should_handle_partial_updates()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  recorder.add_step(channel, 1, 60, 100, 1)
  
  -- Update only velocity and length
  recorder.add_step(channel, 1, nil, 80, 2)
  
  -- Note should be preserved, velocity and length updated
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  -- Update only note and length
  recorder.add_step(channel, 1, 64, nil, 3)
  
  -- Note and length should be updated, velocity preserved
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)
  luaunit.assert_equals(channel.step_length_masks[1], 3)
end

function test_recorder_should_handle_undo_redo_with_partial_updates()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  recorder.add_step(channel, 1, 60, 100, 1, {1, 3, 5})
  
  -- Update only length
  recorder.add_step(channel, 1, nil, nil, 2)
  
  -- Verify only length changed
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  
  -- Undo should restore original length only
  recorder.undo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 1)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  
  -- Redo should restore only length change
  recorder.redo()
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
end

function test_recorder_should_validate_nil_values()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  recorder.add_step(channel, 1, 60, 100, 2, {1, 3, 5})
  
  -- Update only individual values
  recorder.add_step(channel, 1, nil, 90, nil, nil)     -- Update just velocity
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  recorder.add_step(channel, 1, 64, nil, nil, nil)     -- Update just note
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  recorder.add_step(channel, 1, nil, nil, 3, nil)      -- Update just length
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  
  -- Invalid values should still be caught
  recorder.add_step(channel, 1, -1, nil, nil, nil)    -- Invalid note
  luaunit.assert_equals(channel.step_note_masks[1], 64)  -- Should not change
  
  recorder.add_step(channel, 1, nil, 128, nil, nil)   -- Invalid velocity
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)  -- Should not change
  
  recorder.add_step(channel, 1, nil, nil, -6, nil)     -- Invalid length
  luaunit.assert_equals(channel.step_length_masks[1], 3)  -- Should not change
  
  recorder.add_step(channel, 1, nil, nil, nil, {0})   -- Invalid chord degree
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)  -- Should not change
end

function test_recorder_should_allow_all_nil_values_except_step()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Set initial state
  recorder.add_step(channel, 1, 60, 100, 2, {1, 3, 5})
  
  -- Should preserve all values when using nil
  recorder.add_step(channel, 1, nil, nil, nil, nil)
  
  -- Verify all original values preserved
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_recorder_should_validate_partial_updates()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Test various partial update combinations
  recorder.add_step(channel, 1, 60, nil, nil, nil)    -- Just note
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  
  recorder.add_step(channel, 1, nil, 100, nil, nil)   -- Just velocity
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  
  recorder.add_step(channel, 1, nil, nil, 2, nil)     -- Just length
  luaunit.assert_equals(channel.step_length_masks[1], 2)
  
  recorder.add_step(channel, 1, nil, nil, nil, {1, 3}) -- Just chord
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  
  -- Mixed combinations
  recorder.add_step(channel, 1, 64, 90, nil, nil)     -- Note + velocity
  luaunit.assert_equals(channel.step_note_masks[1], 64)
  luaunit.assert_equals(channel.step_velocity_masks[1], 90)
  
  recorder.add_step(channel, 1, nil, nil, 3, {1, 4})  -- Length + chord
  luaunit.assert_equals(channel.step_length_masks[1], 3)
  chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 4)
end

function test_recorder_should_preserve_indices_after_wrap()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Fill buffer and cause wrap
  for i = 1, 1001 do
    recorder.add_step(channel, i % 16 + 1, 60 + i, 100, 1)  -- Use 16 different steps
  end
  
  local state = recorder.get_state()
  
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

function test_recorder_should_respect_max_history_size()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add more than MAX_HISTORY_SIZE events
  for i = 1, 1001 do  -- MAX_HISTORY_SIZE is 1000
    recorder.add_step(channel, 1, 60 + (i % 12), 100, 1)
  end
  
  local state = recorder.get_state()
  
  -- Should be limited to MAX_HISTORY_SIZE
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- First event should be second event since first was pushed out
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.note, 62)
  
  -- Last event should be the most recent one
  local last_event = state.event_history:get(1000)
  luaunit.assert_equals(last_event.data.note, 60 + (1001 % 12))
end

function test_recorder_should_handle_ring_buffer_wrapping()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Create predictable sequence using modulo to keep notes in valid MIDI range
  for i = 1, 1000 do
    recorder.add_step(channel, 1, (i % 128), 100, 1)  -- Keep notes 0-127
  end
  
  -- Add one more to cause wrap
  recorder.add_step(channel, 1, (1001 % 128), 100, 1)
  
  local state = recorder.get_state()
  
  -- Buffer should still be at max size
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- First event should be note value (2 % 128) (since 1 was pushed out)
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.note, (2 % 128))
  
  -- Last event should be (1001 % 128)
  local last_event = state.event_history:get(1000)
  luaunit.assert_equals(last_event.data.note, (1001 % 128))
end

function test_recorder_should_handle_pattern_channel_buffer_wrapping()
  recorder.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Fill first channel with predictable sequence
  for i = 1, 800 do
    recorder.add_step(channel1, 1, (i % 128), 100, 1)  -- Keep notes 0-127
  end
  
  -- Add to second channel
  for i = 1, 300 do
    recorder.add_step(channel2, 1, ((1000 + i) % 128), 100, 1)
  end
  
  local state = recorder.get_state()
  local pc1 = state.pattern_channels["1_1"]
  local pc2 = state.pattern_channels["1_2"]
  
  -- Verify initial counts
  luaunit.assert_equals(pc1.event_history:get_size(), 800)
  luaunit.assert_equals(pc2.event_history:get_size(), 300)
  
  -- Add enough to cause wrap in first channel
  for i = 801, 1100 do
    recorder.add_step(channel1, 1, (i % 128), 100, 1)
  end
  
  -- First channel should be at MAX_HISTORY_SIZE
  luaunit.assert_equals(pc1.event_history:get_size(), 1000)
  
  -- Second channel should be unaffected
  luaunit.assert_equals(pc2.event_history:get_size(), 300)
  
  -- First event in channel 1 should be (101 % 128)
  local first_ch1_event = pc1.event_history:get(1)
  luaunit.assert_equals(first_ch1_event.data.note, (101 % 128))
  
  -- Last event in channel 1 should be (1100 % 128)
  local last_ch1_event = pc1.event_history:get(1000)
  luaunit.assert_equals(last_ch1_event.data.note, (1100 % 128))
end

function test_ring_buffer_should_maintain_correct_order_during_wrap()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Fill buffer
  for i = 1, 998 do
    recorder.add_step(channel, 1, i % 128, 100, 1)
  end
  
  local state = recorder.get_state()
  local initial_size = state.event_history:get_size()
  luaunit.assert_equals(initial_size, 998)
  
  -- Add wrap boundary notes
  recorder.add_step(channel, 1, 60, 100, 1)
  recorder.add_step(channel, 1, 62, 100, 1)
  recorder.add_step(channel, 1, 64, 100, 1)
  
  state = recorder.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- First event should be the second one after wrap
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.note, 2)
end


function test_ring_buffer_should_handle_rapid_wrap_multiple_times()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Fill buffer multiple times
  local final_batch_start = 2001
  for i = 1, 3000 do
    recorder.add_step(channel, 1, i % 128, 100, 1)
  end
  
  local state = recorder.get_state()
  
  -- Verify size remains at max
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- Get events from different positions
  local first = state.event_history:get(1)
  local last = state.event_history:get(1000)
  
  luaunit.assert_not_nil(first, "First event should exist")
  luaunit.assert_not_nil(last, "Last event should exist")
  
  -- Verify the sequence wraps correctly
  luaunit.assert_equals(first.data.note, (2001 % 128))
  luaunit.assert_equals(last.data.note, (3000 % 128))
end

function test_ring_buffer_should_handle_concurrent_pattern_wraps()
  recorder.init()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  -- Alternate between channels while exceeding buffer size
  for i = 1, 2000 do
    local note = i % 128
    if i % 2 == 0 then
      recorder.add_step(channel1, 1, note, 100, 1)
    else
      recorder.add_step(channel2, 1, note, 100, 1)
    end
  end
  
  local state = recorder.get_state()
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
  luaunit.assert_true(pc1_first.data.note >= 0 and pc1_first.data.note <= 127)
  luaunit.assert_true(pc2_first.data.note >= 0 and pc2_first.data.note <= 127)
end

function test_ring_buffer_should_maintain_indices_after_multiple_wraps()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Create a sequence that will wrap multiple times
  for i = 1, 2500 do
    recorder.add_step(channel, (i % 16) + 1, i % 128, 100, 1)
  end
  
  local state = recorder.get_state()
  
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
        table.insert(last_events, event.data.note)
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
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Fill buffer exactly to max size
  for i = 1, 1000 do
    recorder.add_step(channel, 1, i % 128, 100, 1)
  end
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  
  -- Add one more event
  recorder.add_step(channel, 1, 60, 100, 1)
  
  -- Verify size hasn't changed but content has
  luaunit.assert_equals(state.event_history:get_size(), 1000)
  local first_event = state.event_history:get(1)
  luaunit.assert_equals(first_event.data.note, (2 % 128))
end

function test_ring_buffer_truncation_should_respect_wrap_point()
  recorder.init()
  program.init()
  local channel = program.get_channel(1, 1)
  
  -- Add 100 events
  for i = 1, 100 do
    recorder.add_step(channel, 1, i % 128, 100, 1)
  end
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 100)
  
  -- Undo 25 events
  for _ = 1, 25 do
    recorder.undo()
  end
  
  state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 75)
  
  -- Add new event
  recorder.add_step(channel, 1, 60, 100, 1)
  
  state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 76)
end
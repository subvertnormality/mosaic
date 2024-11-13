local recorder = include("mosaic/lib/recorder")

function test_recorder_init_should_create_empty_event_store()
  recorder.init()
  record.init()
  local state = recorder.get_state()
  
  luaunit.assert_equals(#state.event_history, 0)
  luaunit.assert_equals(state.current_event_index, 0)
end

function test_recorder_should_add_single_note()
  recorder.init()
  record.init()
  recorder.add_note(1, 1, 1, 60, 100)
  
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 1), 1)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), 100)
  luaunit.assert_equals(record.get_step_length_mask(1, 1, 1), 1)
end

function test_recorder_should_add_chord()
  recorder.init()
  record.init()
  recorder.add_chord(1, 1, 1, {60, 64, 67}, {100, 90, 80}, {1, 3, 5})
  
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 1), 1)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), 100)
  luaunit.assert_equals(record.get_step_length_mask(1, 1, 1), 1)
  
  local chord_mask = record.get_step_chord_mask(1, 1, 1)
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_recorder_should_undo_last_note()
  recorder.init()
  record.init()
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_note(1, 1, 2, 64, 90)
  recorder.undo()
  
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 2), nil)
end

function test_recorder_should_redo_undone_note()
  recorder.init()
  record.init()
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_note(1, 1, 2, 64, 90)
  recorder.undo()
  recorder.redo()
  
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 2), 64)
end

function test_recorder_should_clear_redo_history_after_new_note()
  recorder.init()
  record.init()
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_note(1, 1, 2, 64, 90)
  recorder.undo()
  recorder.add_note(1, 1, 2, 67, 80)
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 2)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 2), 67)
end

function test_recorder_should_maintain_separate_channels_and_patterns()
  recorder.init()
  record.init()
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_note(1, 2, 1, 64, 90)
  recorder.add_note(2, 1, 1, 67, 80)
  
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_note_mask(1, 2, 1), 64)
  luaunit.assert_equals(record.get_step_note_mask(2, 1, 1), 67)
end

function test_recorder_should_maintain_event_history()
  recorder.init()
  record.init()
  recorder.add_note(1, 1, 1, 60, 100)
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 1)
  luaunit.assert_equals(state.current_event_index, 1)
  luaunit.assert_equals(state.event_history[1].type, "note_added")
  luaunit.assert_equals(state.event_history[1].data.note, 60)
end

function test_recorder_should_maintain_event_index_during_undo_redo()
  recorder.init()
  record.init()
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_note(1, 1, 2, 64, 90)
  recorder.undo()
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 1)
  luaunit.assert_equals(#state.event_history, 2)
end

function test_recorder_undo_should_clear_notes_from_record_model()
  recorder.init()
  record.init()
  
  -- Add two notes
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_note(1, 1, 2, 64, 90)
  
  -- Verify both notes are present
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 1), 1)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 2), 1)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 2), 64)
  
  -- Undo the second note
  recorder.undo()
  
  -- Verify first note remains but second note is fully cleared
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 1), 1)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 2), nil)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 2), nil)
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 2), nil)
  luaunit.assert_equals(record.get_step_length_mask(1, 1, 2), nil)
  
  -- Undo the first note
  recorder.undo()
  
  -- Verify both notes are fully cleared
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 1), nil)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), nil)
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), nil)
  luaunit.assert_equals(record.get_step_length_mask(1, 1, 1), nil)
end

function test_recorder_should_handle_undo_when_empty()
  recorder.init()
  record.init()
  
  recorder.undo()
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(#state.event_history, 0)
end

function test_recorder_should_handle_redo_when_empty()
  recorder.init()
  record.init()
  
  recorder.redo()
  
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  luaunit.assert_equals(#state.event_history, 0)
end

function test_recorder_should_handle_multiple_notes_on_same_step()
  recorder.init()
  record.init()
  
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_note(1, 1, 1, 64, 90)  -- Overwrites previous note
  
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 64)
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), 90)
  
  recorder.undo()
  
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), 100)
end

function test_recorder_should_handle_chord_after_note_on_same_step()
  recorder.init()
  record.init()
  
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_chord(1, 1, 1, {64, 67, 71}, {90, 80, 70}, {1, 3, 5})
  
  local chord_mask = record.get_step_chord_mask(1, 1, 1)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 64)
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
  
  recorder.undo()
  
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_chord_mask(1, 1, 1), nil)
end

function test_recorder_should_handle_note_after_chord_on_same_step()
  recorder.init()
  record.init()
  
  recorder.add_chord(1, 1, 1, {60, 64, 67}, {100, 90, 80}, {1, 3, 5})
  recorder.add_note(1, 1, 1, 71, 70)
  
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 71)
  luaunit.assert_equals(record.get_step_chord_mask(1, 1, 1), nil)
  
  recorder.undo()
  
  local chord_mask = record.get_step_chord_mask(1, 1, 1)
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_recorder_should_handle_undo_redo_at_boundaries()
  recorder.init()
  record.init()
  
  -- Test undo at start
  recorder.undo()
  local state = recorder.get_state()
  luaunit.assert_equals(state.current_event_index, 0)
  
  -- Add and undo all notes
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_note(1, 1, 2, 64, 90)
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
  record.init()
  
  recorder.add_note(1, 1, 1, 60, 100)
  recorder.add_note(1, 1, 1, 60, 80)
  
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), 80)
  
  recorder.undo()
  
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), 100)
  
  recorder.redo()
  
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), 80)
end

function test_recorder_should_handle_empty_chord_degrees()
  recorder.init()
  record.init()
  
  recorder.add_chord(1, 1, 1, {60, 64}, {100, 90}, {})
  
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), 100)
  luaunit.assert_equals(record.get_step_chord_mask(1, 1, 1), nil)
end

function test_recorder_should_preserve_event_history_during_clear()
  recorder.init()
  record.init()
  
  recorder.add_note(1, 1, 1, 60, 100)
  record.init()  -- Should not affect recorder state
  
  local state = recorder.get_state()
  luaunit.assert_equals(#state.event_history, 1)
  luaunit.assert_equals(state.current_event_index, 1)
  luaunit.assert_equals(state.event_history[1].data.note, 60)
end
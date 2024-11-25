function test_recorder_init()
  local recorder = include("mosaic/lib/recorder")
  
  -- Verify initial state
  luaunit.assert_not_nil(recorder.mask_events)
  luaunit.assert_not_nil(recorder.trig_lock_events)
  luaunit.assert_not_nil(recorder.trig_lock_dirty)
  
  -- Verify trig_lock_dirty initialization
  for i = 1, 16 do
    luaunit.assert_not_nil(recorder.trig_lock_dirty[i])
    for j = 1, 10 do
      luaunit.assert_equals(recorder.trig_lock_dirty[i][j], false)
    end
  end
end

function test_recorder_add_note_mask_event_portion()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  
  local channel = 1
  local step = 1
  local event_portion = {
    
    data = {
      song_pattern = 1,
      trig = 1,
      note = 60,
      velocity = 100,
      length = 1,
      step = 1
    }
  }
  
  -- Add event portion
  recorder.add_note_mask_event_portion(channel, step, event_portion)
  
  -- Verify event was stored
  luaunit.assert_not_nil(recorder.mask_events[channel])
  luaunit.assert_not_nil(recorder.mask_events[channel][step])
  luaunit.assert_equals(recorder.mask_events[channel][step].data.song_pattern, 1)
  luaunit.assert_equals(recorder.mask_events[channel][step].data.note, 60)
  luaunit.assert_equals(recorder.mask_events[channel][step].data.velocity, 100)
end

function test_recorder_add_multiple_note_mask_event_portions()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  
  local channel = 1
  local step = 1
  
  -- Add first portion
  recorder.add_note_mask_event_portion(channel, step, {
    
    data = {
      song_pattern = 1,
      trig = 1,
      note = 60,
      step = 1
    }
  })
  
  -- Add second portion (should merge)
  recorder.add_note_mask_event_portion(channel, step, {
    
    data = {
      song_pattern = 1,
      velocity = 100,
      length = 1,
      step = 1
    }
  })
  
  -- Verify merged data
  local event = recorder.mask_events[channel][step]
  luaunit.assert_equals(event.data.note, 60)
  luaunit.assert_equals(event.data.velocity, 100)
  luaunit.assert_equals(event.data.length, 1)
end

function test_recorder_record_stored_note_mask_events()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  local channel = 1
  local step = 1
  
  -- Add event portion
  recorder.add_note_mask_event_portion(channel, step, {
    data = {
      song_pattern = 1,
      trig = 1,
      note = 60,
      velocity = 100,
      length = 1,
      step = 1
    }
  })
  
  -- Record stored events
  recorder.record_stored_note_mask_events(channel, step)
  
  -- Verify event was recorded and cleared
  luaunit.assert_nil(recorder.mask_events[channel][step])
  
  -- Verify event was recorded to memory
  local channel_obj = program.get_channel(1, channel)
  luaunit.assert_equals(channel_obj.step_note_masks[step], 60)
  luaunit.assert_equals(channel_obj.step_velocity_masks[step], 100)
end

function test_recorder_add_trig_lock_event_portion()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  
  local channel = 1
  local step = 1
  local event_portion = {
    data = {
      song_pattern = 1,
      parameter = 1,
      value = 100,
      step = 1
    }
  }
  
  -- Add event portion
  recorder.add_trig_lock_event_portion(channel, step, event_portion)
  
  -- Verify event was stored
  luaunit.assert_not_nil(recorder.trig_lock_events[channel])
  luaunit.assert_not_nil(recorder.trig_lock_events[channel][step])
  luaunit.assert_equals(recorder.trig_lock_events[channel][step].data.value, 100)
end

function test_recorder_record_stored_trig_lock_events()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  local channel = 1
  local step = 1
  
  -- Add event portion
  recorder.add_trig_lock_event_portion(channel, step, {
    data = {
      song_pattern = 1,
      parameter = 1,
      value = 100,
      step = 1
    }
  })
  
  -- Record stored events
  recorder.record_stored_trig_lock_events(channel, step)
  
  -- Verify event was recorded and cleared
  luaunit.assert_nil(recorder.trig_lock_events[channel][step])
  
  -- Verify event was recorded to memory
  local channel_obj = program.get_channel(1, channel)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel_obj, step, 1), 100)
end

function test_recorder_trig_lock_dirty_state()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  
  local channel = 1
  local parameter = 1
  
  -- Test initial state
  luaunit.assert_false(recorder.trig_lock_is_dirty(channel, parameter))
  
  -- Set dirty
  recorder.set_trig_lock_dirty(channel, parameter, true)
  luaunit.assert_true(recorder.trig_lock_is_dirty(channel, parameter))
  
  -- Clear dirty
  recorder.clear_trig_lock_dirty(channel, parameter)
  luaunit.assert_nil(recorder.trig_lock_is_dirty(channel, parameter))
end

function test_recorder_record_trig_event()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  local channel = 1
  local step = 1
  local parameter = 1
  
  -- Set dirty state
  recorder.set_trig_lock_dirty(channel, parameter, 100)
  
  -- Record event
  recorder.record_trig_event(channel, step, parameter)
  
  -- Verify event was recorded
  local channel_obj = program.get_channel(1, channel)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel_obj, step, parameter), 100)
end


function test_recorder_clear_stored_events()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  
  -- Add some events
  recorder.add_note_mask_event_portion(1, 1, {
    data = {song_pattern = 1, note = 60 }
  })
  
  recorder.add_trig_lock_event_portion(1, 1, {
    data = {song_pattern = 1, parameter = 1, value = 100 }
  })
  
  -- Record events (should clear storage)
  recorder.record_stored_note_mask_events(1, 1)
  recorder.record_stored_trig_lock_events(1, 1)
  
  -- Verify storages are empty
  luaunit.assert_nil(recorder.mask_events[1][1])
  luaunit.assert_nil(recorder.trig_lock_events[1][1])
end


function test_recorder_merge_chord_degrees()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  
  local channel = 1
  local step = 1
  
  -- Add chord degrees one at a time
  recorder.add_note_mask_event_portion(channel, step, {
    
    data = {
      chord_degrees = {3, nil, nil}, song_pattern = 1,
    }
  })
  
  recorder.add_note_mask_event_portion(channel, step, {
    data = {
      chord_degrees = {nil, 5, nil}, song_pattern = 1,
    }
  })
  
  recorder.add_note_mask_event_portion(channel, step, {
    data = {
      chord_degrees = {nil, nil, 7}, song_pattern = 1,
    }
  })
  
  -- Verify merged chord degrees
  local event = recorder.mask_events[channel][step]
  luaunit.assert_equals(event.data.chord_degrees[1], 3)
  luaunit.assert_equals(event.data.chord_degrees[2], 5)
  luaunit.assert_equals(event.data.chord_degrees[3], 7)
end

function test_recorder_handle_multiple_channels()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  
  -- Add events to different channels
  recorder.add_note_mask_event_portion(1, 1, {
    data = { 
      note = 60,
      step = 1,
      song_pattern = 1,
    }
  })
  
  recorder.add_note_mask_event_portion(2, 1, {
    song_pattern = 1,
    data = { 
      note = 64,
      step = 1,
      song_pattern = 1,
    },
  })
  
  -- Verify events are stored separately
  luaunit.assert_equals(recorder.mask_events[1][1].data.note, 60)
  luaunit.assert_equals(recorder.mask_events[2][1].data.note, 64)
  
  -- Record events
  recorder.record_stored_note_mask_events(1, 1)
  recorder.record_stored_note_mask_events(2, 1)
  
  -- Verify channels remain independent
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end


function test_recorder_handle_multiple_steps()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  -- Add events to different steps
  recorder.add_note_mask_event_portion(1, 1, {
    
    data = { note = 60, step = 1, song_pattern = 1,}
  })
  
  recorder.add_note_mask_event_portion(1, 2, {
    
    data = { note = 64, step = 2, song_pattern = 1 }
  })
  
  -- Verify events are stored separately
  luaunit.assert_equals(recorder.mask_events[1][1].data.note, 60)
  luaunit.assert_equals(recorder.mask_events[1][2].data.note, 64)
  
  -- Record events
  recorder.record_stored_note_mask_events(1, 1)
  recorder.record_stored_note_mask_events(1, 2)
  
  -- Verify steps remain independent
  local channel = program.get_channel(1, 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 64)
end

function test_recorder_handle_empty_event_data()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  -- Add event without data
  recorder.add_note_mask_event_portion(1, 1, {
    song_pattern = 1
  })
  
  -- Record event
  recorder.record_stored_note_mask_events(1, 1)
  
  -- Verify nothing was recorded
  local channel = program.get_channel(1, 1)
  luaunit.assert_nil(channel.step_note_masks[1])
end

function test_recorder_handle_multiple_song_patterns()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  -- Add events to different song patterns
  recorder.add_note_mask_event_portion(1, 1, {
    data = { 
      note = 60, 
      step = 1,
      song_pattern = 1,
    }
  })
  
  recorder.add_note_mask_event_portion(2, 11, {
    data = { 
      note = 64, 
      step = 11,
      song_pattern = 2,
    }
  })
  
  -- Record events
  recorder.record_stored_note_mask_events(1, 1)
  recorder.record_stored_note_mask_events(2, 11)
  
  -- Verify patterns remain independent
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(2, 2)
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[11], 64)
end

function test_recorder_trig_lock_events_with_multiple_parameters()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  -- Set multiple parameters as dirty
  recorder.set_trig_lock_dirty(1, 1, 100)
  recorder.set_trig_lock_dirty(1, 2, 80)
  recorder.set_trig_lock_dirty(1, 3, 60)
  
  -- Record events
  recorder.record_trig_event(1, 1, 1)
  recorder.record_trig_event(1, 1, 2)
  recorder.record_trig_event(1, 1, 3)
  
  -- Verify all parameters were recorded
  local channel = program.get_channel(1, 1)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel, 1, 1), 100)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel, 1, 2), 80)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel, 1, 3), 60)
end

function test_recorder_handle_nil_trig_lock_values()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  -- Set a trig lock value
  recorder.set_trig_lock_dirty(1, 1, 100)
  recorder.record_trig_event(1, 1, 1)
  
  -- Clear it by setting to nil
  recorder.set_trig_lock_dirty(1, 1, nil)
  recorder.record_trig_event(1, 1, 1)
  
  -- Verify trig lock was cleared
  local channel = program.get_channel(1, 1)
  luaunit.assert_nil(program.get_step_param_trig_lock(channel, 1, 1))
end

function test_recorder_merge_partial_note_mask_events()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  -- Add note data in portions
  recorder.add_note_mask_event_portion(1, 1, {
    
    data = { song_pattern = 1,note = 60, step = 1 }
  })
  
  recorder.add_note_mask_event_portion(1, 1, {
    
    data = { song_pattern = 1,velocity = 100, step = 1 }
  })
  
  recorder.add_note_mask_event_portion(1, 1, {
    
    data = { song_pattern = 1,length = 2, step = 1 }
  })
  
  -- Record merged event
  recorder.record_stored_note_mask_events(1, 1)
  
  -- Verify all portions were merged and recorded
  local channel = program.get_channel(1, 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
  luaunit.assert_equals(channel.step_length_masks[1], 2)
end

function test_recorder_handle_overlapping_note_mask_events()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  -- Add initial complete note
  recorder.add_note_mask_event_portion(1, 1, {
    
    data = {
      song_pattern = 1,
      note = 60,
      velocity = 100,
      length = 1,
      step = 1
    }
  })
  
  -- Overlay with partial update
  recorder.add_note_mask_event_portion(1, 1, {
    
    data = {
      song_pattern = 1,
      velocity = 80,
      step = 1
    }
  })
  
  -- Record event
  recorder.record_stored_note_mask_events(1, 1)
  
  -- Verify merge behavior
  local channel = program.get_channel(1, 1)
  luaunit.assert_equals(channel.step_note_masks[1], 60)  -- Preserved
  luaunit.assert_equals(channel.step_velocity_masks[1], 80)  -- Updated
  luaunit.assert_equals(channel.step_length_masks[1], 1)  -- Preserved
end

function test_recorder_handle_trig_lock_events_across_steps()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  -- Set trig locks for multiple steps
  recorder.set_trig_lock_dirty(1, 1, 100)
  recorder.record_trig_event(1, 1, 1)
  
  recorder.set_trig_lock_dirty(1, 1, 80)
  recorder.record_trig_event(1, 2, 1)
  
  -- Verify independent step values
  local channel = program.get_channel(1, 1)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel, 1, 1), 100)
  luaunit.assert_equals(program.get_step_param_trig_lock(channel, 2, 1), 80)
end

function test_recorder_trig_lock_dirty_state_independence()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  
  -- Set dirty states for different channels/parameters
  recorder.set_trig_lock_dirty(1, 1, 100)
  recorder.set_trig_lock_dirty(1, 2, 80)
  recorder.set_trig_lock_dirty(2, 1, 60)
  
  -- Verify independence
  luaunit.assert_equals(recorder.trig_lock_is_dirty(1, 1), 100)
  luaunit.assert_equals(recorder.trig_lock_is_dirty(1, 2), 80)
  luaunit.assert_equals(recorder.trig_lock_is_dirty(2, 1), 60)
  
  -- Clear individual states
  recorder.clear_trig_lock_dirty(1, 1)
  
  luaunit.assert_nil(recorder.trig_lock_is_dirty(1, 1))
  luaunit.assert_equals(recorder.trig_lock_is_dirty(1, 2), 80)
  luaunit.assert_equals(recorder.trig_lock_is_dirty(2, 1), 60)
end

-- Revised tests removing m_grid dependency

function test_recorder_handle_midi_message_with_record_mode_changes()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  local channel_number = 1
  local step = 1
  program.set_current_step_for_channel(channel_number, step)
  
  -- Test with record off
  params:set("record", 1)
  recorder.handle_note_midi_message(60, 100, 1, nil)
  
  -- Verify no recording happened
  luaunit.assert_nil(recorder.mask_events[channel_number])
  
  -- Test with record on
  params:set("record", 2)
  recorder.handle_note_midi_message(60, 100, 1, nil)
  
  -- Verify recording happened
  luaunit.assert_not_nil(recorder.mask_events[channel_number])
  luaunit.assert_not_nil(recorder.mask_events[channel_number][step])
  luaunit.assert_equals(recorder.mask_events[channel_number][step].data.note, 60)
  luaunit.assert_equals(recorder.mask_events[channel_number][step].data.velocity, 100)
end

function test_recorder_handle_note_midi_message_direct_recording()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  local channel_number = 1
  local step = 1
  program.set_current_step_for_channel(channel_number, step)
  params:set("record", 2)
  
  -- Test basic note recording
  recorder.handle_note_midi_message(60, 100, 1, nil)
  
  -- Verify event was stored correctly
  luaunit.assert_not_nil(recorder.mask_events[channel_number])
  luaunit.assert_not_nil(recorder.mask_events[channel_number][step])
  luaunit.assert_equals(recorder.mask_events[channel_number][step].data.note, 60)
  luaunit.assert_equals(recorder.mask_events[channel_number][step].data.velocity, 100)
end

function test_recorder_handle_chord_note_recording()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  local channel_number = 1
  local step = 1
  program.set_current_step_for_channel(channel_number, step)
  params:set("record", 2)
  
  -- Record chord notes
  recorder.handle_note_midi_message(60, 100, 2, 3) -- Second chord note, degree 3
  recorder.handle_note_midi_message(64, 100, 3, 5) -- Third chord note, degree 5
  
  -- Verify chord data was stored correctly
  local event = recorder.mask_events[channel_number][step]
  luaunit.assert_equals(event.data.chord_degrees[1], 3)
  luaunit.assert_equals(event.data.chord_degrees[2], 5)
end

function test_recorder_handle_complete_chord_recording()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  local channel_number = 1
  local step = 1
  program.set_current_step_for_channel(channel_number, step)
  params:set("record", 2)
  
  -- Record base note
  recorder.handle_note_midi_message(60, 100, 1, nil)
  
  -- Record chord notes in different order
  recorder.handle_note_midi_message(64, 100, 3, 5)  -- Third position, degree 5
  recorder.handle_note_midi_message(62, 100, 2, 3)  -- Second position, degree 3
  recorder.handle_note_midi_message(65, 100, 4, 7)  -- Fourth position, degree 7
  
  -- Verify chord data was stored in correct order
  local event = recorder.mask_events[channel_number][step]
  luaunit.assert_equals(event.data.note, 60)  -- Base note
  luaunit.assert_equals(event.data.chord_degrees[1], 3)
  luaunit.assert_equals(event.data.chord_degrees[2], 5)
  luaunit.assert_equals(event.data.chord_degrees[3], 7)
end

function test_recorder_handle_recording_to_different_steps()
  local recorder = include("mosaic/lib/recorder")
  program.init()
  memory.init()
  
  local channel_number = 1
  params:set("record", 2)
  
  -- Record to step 1
  program.set_current_step_for_channel(channel_number, 1)
  recorder.handle_note_midi_message(60, 100, 1, nil)
  
  -- Record to step 2
  program.set_current_step_for_channel(channel_number, 2)
  recorder.handle_note_midi_message(64, 100, 1, nil)
  
  -- Verify notes were recorded to correct steps
  luaunit.assert_equals(recorder.mask_events[channel_number][1].data.note, 60)
  luaunit.assert_equals(recorder.mask_events[channel_number][2].data.note, 64)
end
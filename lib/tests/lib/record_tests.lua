local record = include("mosaic/lib/record")

function test_record_init_should_create_empty_store()
  record.init()
  local store = record.get()
  luaunit.assert_equals(type(store.sequencer_patterns), "table")
  luaunit.assert_not_nil(store.sequencer_patterns[1])
end

function test_get_sequencer_pattern_should_initialize_if_not_exists()
  record.init()
  local pattern = record.get_sequencer_pattern(1)
  
  luaunit.assert_not_nil(pattern)
  luaunit.assert_equals(type(pattern.channels), "table")
end

function test_get_channel_should_initialize_if_not_exists()
  record.init()
  local channel = record.get_channel(1, 1)  -- Add song_pattern parameter
  
  luaunit.assert_not_nil(channel)
  luaunit.assert_equals(channel.number, 1)
  luaunit.assert_equals(type(channel.step_trig_masks), "table")
  luaunit.assert_equals(type(channel.step_note_masks), "table")
  luaunit.assert_equals(type(channel.step_velocity_masks), "table")
  luaunit.assert_equals(type(channel.step_length_masks), "table")
  luaunit.assert_equals(type(channel.step_chord_masks), "table")
end

function test_step_trig_mask_getters_and_setters()
  record.init()
  record.set_step_trig_mask(1, 1, 1, 1)  -- Add song_pattern parameter
  
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 1), 1)
end

function test_step_note_mask_getters_and_setters()
  record.init()
  record.set_step_note_mask(1, 1, 1, 60)  -- Add song_pattern parameter
  
  luaunit.assert_equals(record.get_step_note_mask(1, 1, 1), 60)
end

function test_step_velocity_mask_getters_and_setters()
  record.init()
  record.set_step_velocity_mask(1, 1, 1, 100)  -- Add song_pattern parameter
  
  luaunit.assert_equals(record.get_step_velocity_mask(1, 1, 1), 100)
end

function test_step_length_mask_getters_and_setters()
  record.init()
  record.set_step_length_mask(1, 1, 1, 4)  -- Add song_pattern parameter
  
  luaunit.assert_equals(record.get_step_length_mask(1, 1, 1), 4)
end

function test_step_chord_mask_getters_and_setters()
  record.init()
  record.set_step_chord_mask(1, 1, 1, {1, 3, 5})  -- Add song_pattern parameter
  
  luaunit.assert_equals(record.get_step_chord_mask(1, 1, 1)[1], 1)
  luaunit.assert_equals(record.get_step_chord_mask(1, 1, 1)[2], 3)
  luaunit.assert_equals(record.get_step_chord_mask(1, 1, 1)[3], 5)
end

function test_multiple_channels_should_maintain_separate_masks()
  record.init()
  record.set_step_trig_mask(1, 1, 1, 1)  -- Add song_pattern parameter
  record.set_step_trig_mask(1, 2, 1, 0)  -- Add song_pattern parameter
  
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 1), 1)
  luaunit.assert_equals(record.get_step_trig_mask(1, 2, 1), 0)
end

function test_multiple_patterns_should_maintain_separate_channels()
  record.init()
  record.get_sequencer_pattern(1)
  record.get_sequencer_pattern(2)
  
  record.set_step_trig_mask(1, 1, 1, 1)  -- Add song_pattern parameter
  
  -- Check first pattern
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 1), 1)
  
  -- Set different value in second pattern
  record.set_step_trig_mask(2, 1, 1, 0)  -- Add song_pattern parameter
  
  -- Check second pattern
  luaunit.assert_equals(record.get_step_trig_mask(2, 1, 1), 0)
  
  -- Check first pattern maintains its value
  luaunit.assert_equals(record.get_step_trig_mask(1, 1, 1), 1)
end
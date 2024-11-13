function test_program_should_get_and_set_step_trig_mask()
  program.init()
  local channel = program.get_channel(1, 1)
  channel.step_trig_masks[1] = 1
  
  luaunit.assert_equals(channel.step_trig_masks[1], 1)
end

function test_program_should_get_and_set_step_note_mask()
  program.init()
  local channel = program.get_channel(1, 1)
  channel.step_note_masks[1] = 60
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
end

function test_program_should_get_and_set_step_velocity_mask()
  program.init()
  local channel = program.get_channel(1, 1)
  channel.step_velocity_masks[1] = 100
  
  luaunit.assert_equals(channel.step_velocity_masks[1], 100)
end

function test_program_should_get_and_set_step_length_mask()
  program.init()
  local channel = program.get_channel(1, 1)
  channel.step_length_masks[1] = 4
  
  luaunit.assert_equals(channel.step_length_masks[1], 4)
end

function test_program_should_get_and_set_step_chord_mask()
  program.init()
  local channel = program.get_channel(1, 1)
  if not channel.step_chord_masks then
    channel.step_chord_masks = {}
  end
  channel.step_chord_masks[1] = {1, 3, 5}
  
  local chord_mask = channel.step_chord_masks[1]
  luaunit.assert_equals(chord_mask[1], 1)
  luaunit.assert_equals(chord_mask[2], 3)
  luaunit.assert_equals(chord_mask[3], 5)
end

function test_program_should_handle_multiple_song_patterns()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(2, 1)
  
  channel1.step_note_masks[1] = 60
  channel2.step_note_masks[1] = 64
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_program_should_handle_multiple_channels()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  channel1.step_note_masks[1] = 60
  channel2.step_note_masks[1] = 64
  
  luaunit.assert_equals(channel1.step_note_masks[1], 60)
  luaunit.assert_equals(channel2.step_note_masks[1], 64)
end

function test_program_should_handle_multiple_steps()
  program.init()
  local channel = program.get_channel(1, 1)
  
  channel.step_note_masks[1] = 60
  channel.step_note_masks[2] = 64
  
  luaunit.assert_equals(channel.step_note_masks[1], 60)
  luaunit.assert_equals(channel.step_note_masks[2], 64)
end

function test_program_should_handle_nil_masks()
  program.init()
  local channel = program.get_channel(1, 1)
  channel.step_note_masks[1] = nil
  
  luaunit.assert_equals(channel.step_note_masks[1], nil)
end

function test_program_should_initialize_chord_masks_table()
  program.init()
  local channel = program.get_channel(1, 1)
  if not channel.step_chord_masks then
    channel.step_chord_masks = {}
  end
  channel.step_chord_masks[1] = {1, 3, 5}
  
  luaunit.assert_not_nil(channel.step_chord_masks)
  luaunit.assert_equals(type(channel.step_chord_masks), "table")
end

function test_program_should_maintain_channel_numbers()
  program.init()
  local channel1 = program.get_channel(1, 1)
  local channel2 = program.get_channel(1, 2)
  
  luaunit.assert_equals(channel1.number, 1)
  luaunit.assert_equals(channel2.number, 2)
end
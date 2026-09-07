-- Supplementary regression; actual UI/MIDI evidence remains mandatory.
function test_emulator_partial_note_mask_preserves_pattern_on_record_and_redo()
  memory.init();program.init()
  local channel=program.get_channel(1,1)
  channel.working_pattern.trig_values[3]=1
  channel.working_pattern.velocity_values[3]=107
  channel.working_pattern.lengths[3]=2
  memory.record_event(1,'note_mask',{step=3,note=69,song_pattern=1})
  luaunit.assertEquals(channel.working_pattern.trig_values[3],1)
  luaunit.assertEquals(channel.working_pattern.velocity_values[3],107)
  luaunit.assertEquals(channel.working_pattern.lengths[3],2)
  memory.undo(1);memory.redo(1)
  luaunit.assertEquals(channel.working_pattern.trig_values[3],1)
  luaunit.assertEquals(channel.working_pattern.note_mask_values[3],69)
  luaunit.assertEquals(channel.working_pattern.velocity_values[3],107)
  luaunit.assertEquals(channel.working_pattern.lengths[3],2)
end

function test_emulator_trig_only_mask_does_not_invent_note_mask()
  memory.init();program.init()
  local channel=program.get_channel(1,1)
  memory.record_event(1,'note_mask',{step=1,trig=1,song_pattern=1})
  luaunit.assertNil(channel.working_pattern.note_mask_values[1])
  luaunit.assertEquals(channel.working_pattern.trig_values[1],1)
end

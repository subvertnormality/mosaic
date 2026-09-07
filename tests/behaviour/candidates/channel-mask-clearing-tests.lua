-- Supplements the real UI regression; no runtime acceptance is inferred here.
function test_emulator_clear_all_masks_removes_defaults_and_preserves_other_channel()
  program.init()
  local channel=program.get_channel(1,1)
  local other=program.get_channel(1,2)
  local defaults={'trig_mask','note_mask','velocity_mask','length_mask',
    'chord_one_mask','chord_two_mask','chord_three_mask','chord_four_mask'}
  for _,name in ipairs(defaults) do channel[name]=2;other[name]=3 end
  channel.step_note_masks[3]=69
  channel.working_pattern.trig_values[1]=1
  program.clear_masks_for_channel(channel)
  for _,name in ipairs(defaults) do
    luaunit.assertNil(channel[name]);luaunit.assertEquals(other[name],3)
  end
  luaunit.assertEquals(channel.step_note_masks,{})
  luaunit.assertEquals(channel.working_pattern.trig_values[1],1)
end

local midi_output = include("mosaic/lib/m_midi")

local function with_output_spy(run)
  local original_devices=midi_devices
  local sent={}
  midi_devices={{
    note_on=function(_,note,velocity,channel) sent[#sent+1]={"on",note,velocity,channel} end,
    note_off=function(_,note,velocity,channel) sent[#sent+1]={"off",note,velocity,channel} end
  }}
  midi_output:reset_note_counts()
  local ok,err=pcall(run,sent)
  midi_output:reset_note_counts();midi_devices=original_devices
  if not ok then error(err,0) end
end

function test_midi_output_clamps_composed_note_domain_and_preserves_ownership()
  with_output_spy(function(sent)
    midi_output:note_on(-17,100,1,1)
    midi_output:note_on(0,101,1,1)
    midi_output:note_off(-17,100,1,1)
    midi_output:note_off(0,101,1,1)
    midi_output:note_on(148,102,1,1)
    midi_output:note_on(127,103,1,1)
    midi_output:note_off(148,102,1,1)
    midi_output:note_off(127,103,1,1)
    luaunit.assert_equals(sent,{
      {"on",0,100,1},{"on",0,101,1},{"off",0,100,1},{"off",0,101,1},
      {"on",127,102,1},{"on",127,103,1},{"off",127,102,1},{"off",127,103,1}})
    luaunit.assert_equals(midi_output.note_counts[1][1],{})
  end)
end

function test_unmatched_midi_release_is_clamped_before_safety_send()
  with_output_spy(function(sent)
    midi_output:note_off(200,77,4,1)
    luaunit.assert_equals(sent,{{"off",127,77,4}})
  end)
end


function test_all_notes_off_preserves_every_clamped_endpoint_owner()
  with_output_spy(function(sent)
    midi_output:note_on(-17,100,2,1)
    midi_output:note_on(0,101,2,1)
    midi_output:note_on(148,102,2,1)
    midi_output:note_on(127,103,2,1)
    midi_output:all_notes_off()
    luaunit.assert_equals({sent[1],sent[2],sent[3],sent[4]},
      {{"on",0,100,2},{"on",0,101,2},{"on",127,102,2},{"on",127,103,2}})
    local released={sent[5][2],sent[6][2],sent[7][2],sent[8][2]};table.sort(released)
    luaunit.assert_equals(released,{0,0,127,127})
    for i=5,8 do luaunit.assert_equals({sent[i][1],sent[i][3],sent[i][4]},{"off",0,2}) end
    luaunit.assert_equals(midi_output.note_counts,{})
  end)
end

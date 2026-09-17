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

-- Characterisation (not README text; MIDI 1.0 convention): a 14-bit controller sends
-- its MSB (value // 128) before its LSB (value % 128) on the same channel; a 7-bit
-- controller sends the value unchanged; an absent output device sends nothing.
function test_cc_sends_seven_bit_values_and_splits_fourteen_bit_values_msb_first()
  local original_devices = midi_devices
  local sent = {}
  midi_devices = {{cc = function(_, number, value, channel) sent[#sent + 1] = {number, value, channel} end}}
  local ok, err = pcall(function()
    midi_output.cc(74, nil, 127, 3, 1)
    midi_output.cc(1, 33, 16383, 2, 1)
    midi_output.cc(1, 33, 8191, 2, 1)
    midi_output.cc(7, 39, 0, 16, 1)
    midi_output.cc(1, nil, 64, 1, 2)
  end)
  midi_devices = original_devices
  if not ok then error(err, 0) end
  luaunit.assert_equals(sent, {{74, 127, 3}, {1, 127, 2}, {33, 127, 2}, {1, 63, 2}, {33, 127, 2}, {7, 0, 16}, {39, 0, 16}})
end

-- A port with a norns MIDI device behind it receives each message as its
-- three wire bytes in a single send, the same bytes norns' note_on, note_off
-- and cc build; the byte table is reused, so each send is copied as it arrives.
function test_midi_output_sends_wire_bytes_straight_to_a_norns_device()
  local original_devices=midi_devices
  local writes={}
  local Device={}
  Device.__index=Device
  function Device:send(bytes) writes[#writes+1]={bytes[1],bytes[2],bytes[3],#bytes} end
  local called={}
  midi_devices={{device=setmetatable({},Device),
    note_on=function() called[#called+1]="note_on" end,
    note_off=function() called[#called+1]="note_off" end,
    cc=function() called[#called+1]="cc" end}}
  midi_output:reset_note_counts()
  local ok,err=pcall(function()
    midi_output:note_on(60,100,2,1)
    midi_output:note_off(60,nil,2,1)
    midi_output.cc(7,nil,64,16,1)
    midi_output.cc(1,33,1000,1,1)
  end)
  midi_output:reset_note_counts();midi_devices=original_devices
  if not ok then error(err,0) end
  luaunit.assert_equals(writes,{{0x91,60,100,3},{0x81,60,100,3},{0xBF,7,64,3},{0xB0,1,7,3},{0xB0,33,1000%128,3}})
  luaunit.assert_equals(called,{},"A norns device port is not sent through its message methods")
end

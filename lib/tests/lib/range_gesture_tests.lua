local sequencer_control = include("mosaic/lib/controls/sequencer")
local function coords(step) return ((step-1)%16)+1, math.floor((step-1)/16)+4 end

function test_channel_range_gesture_all_endpoint_pairs()
  program.init();globals.reset();params.reset()
  local control = sequencer_control:new(4, "channel")
  for _, number in ipairs({1,17}) do
    program.get().selected_channel = number
    local channel = program.get_selected_channel()
    for first = 1,64 do
      for last = 1,64 do
        channel.start_trig = {2,4};channel.end_trig = {8,4}
        local x,y = coords(first);local x2,y2 = coords(last)
        local result = control:dual_press(x,y,x2,y2)
        luaunit.assert_equals(result, last > first)
        luaunit.assert_equals(channel.start_trig, last > first and {x,y} or {2,4})
        luaunit.assert_equals(channel.end_trig, last > first and {x2,y2} or {8,4})
      end
    end
    channel.start_trig={2,4};channel.end_trig={8,4}
    luaunit.assert_nil(control:dual_press(2,4,1,3))
    luaunit.assert_equals(channel.start_trig,{2,4});luaunit.assert_equals(channel.end_trig,{8,4})
  end
end

function test_pattern_note_length_wrap_unchanged_by_channel_range_guard()
  program.init();globals.reset();params.reset()
  local control = sequencer_control:new(4,"pattern")
  local pattern = program.get_selected_pattern()
  for first = 1,64 do
    for last = 1,64 do
      if first ~= last then -- Two distinct physical grid keys.
      pattern.trig_values[first]=1;pattern.lengths[first]=1
      local x,y=coords(first);local x2,y2=coords(last)
      control:dual_press(x,y,x2,y2)
      local expected=((last-first)%64)+1
      luaunit.assert_equals(pattern.lengths[first],expected)
      end
    end
  end
end

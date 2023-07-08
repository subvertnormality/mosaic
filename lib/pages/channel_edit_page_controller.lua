local channel_edit_page_controller = {}

local pattern_buttons = {}
local channel_edit_page_sequencer = Sequencer:new(4, "channel")
local channel_select_fader = Fader:new(1, 1, 16, 16)

function channel_edit_page_controller:init()
  
  for s = 1, 16 do
    pattern_buttons["step"..s.."_pattern_button"] = Button:new(s, 2)
  end

end

function channel_edit_page_controller:merge_patterns(merged_pattern, pattern)

  for s = 1, 64 do

    if pattern[s] == 1 then
      merged_pattern[s] = 1
    end
  end

  return merged_pattern
  
end

function channel_edit_page_controller:get_and_merge_patterns()

  local selected_sequencer_pattern = program.selected_sequencer_pattern
  local merged_pattern = initialise_64_table(0)

  for pattern in pairs(program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].selected_patterns) do
    merged_pattern = channel_edit_page_controller:merge_patterns(merged_pattern, program.sequencer_patterns[selected_sequencer_pattern].patterns[pattern].trig_values)
  end
  
  return merged_pattern
end

function channel_edit_page_controller:merge_lengths(merged_lengths, lengths)

  for s = 1, 64 do

    if lengths[s] >= 1 then
      merged_lengths[s] = lengths[s]
    end
  end

  return merged_lengths
  
end

function channel_edit_page_controller:get_and_merge_lengths()

  local selected_sequencer_pattern = program.selected_sequencer_pattern
  local merged_lengths = initialise_64_table(-1)

  -- TODO: implement merge strategies
  for pattern in pairs(program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].selected_patterns) do
    merged_lengths = channel_edit_page_controller:merge_lengths(merged_lengths, program.sequencer_patterns[selected_sequencer_pattern].patterns[pattern].lengths)
  end
  
  return merged_lengths
end

function channel_edit_page_controller:update_channel_edit_page_ui()
  local selected_sequencer_pattern = program.selected_sequencer_pattern

  for s = 1, 16 do  
    if fn.is_in_set(program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].selected_patterns, s) then
      pattern_buttons["step"..s.."_pattern_button"]:set_state(2)
    else
      pattern_buttons["step"..s.."_pattern_button"]:set_state(1)
    end
  end

end


function channel_edit_page_controller:register_draw_handlers()
  draw_handler:register(
    "channel_edit_page",
    function()

      local trigs = channel_edit_page_controller:get_and_merge_patterns()
      local lengths = channel_edit_page_controller:get_and_merge_lengths()

      -- TODO: Save these in the channel's working pattern

      channel_edit_page_sequencer:draw(trigs, lengths)
    end
  )

  draw_handler:register(
    "channel_edit_page",
    function()

      return channel_select_fader:draw()

    end
  )
  for s = 1, 16 do  
    draw_handler:register(
      "channel_edit_page",
      function()
        pattern_buttons["step"..s.."_pattern_button"]:draw()
      end
    )
  end
end



function channel_edit_page_controller:register_press_handlers()

  press_handler:register(
    "channel_edit_page",
    function(x, y)
      return channel_edit_page_sequencer:press(x, y)
    end
  )
  press_handler:register(
    "channel_edit_page",
    function(x, y)
      local result = channel_select_fader:press(x, y)
      program.selected_channel = channel_select_fader:get_value()
      channel_edit_page_controller:update_channel_edit_page_ui()
      return result
    end
  )
  press_handler:register_dual(
    "channel_edit_page",
    function(x, y, x2, y2)
      return channel_edit_page_sequencer:dual_press(x, y, x2, y2)
    end
  )
  for s = 1, 16 do  
    press_handler:register(
      "channel_edit_page",
      function(x, y)
        local selected_sequencer_pattern = program.selected_sequencer_pattern
        pattern_buttons["step"..s.."_pattern_button"]:press(x, y)
        if pattern_buttons["step"..s.."_pattern_button"]:is_this(x, y) then
          if pattern_buttons["step"..s.."_pattern_button"]:get_state() == 2 then
            fn.add_to_set(program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].selected_patterns, x)
          else
            fn.remove_from_set(program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].selected_patterns, x)
          end
        end
        
      end
    )
  end
end



return channel_edit_page_controller

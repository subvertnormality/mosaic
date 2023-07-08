local channel_edit_page_controller = {}

local pattern_buttons = {}
local channel_edit_page_sequencer = Sequencer:new(4, "channel")
local channel_select_fader = Fader:new(1, 1, 16, 16)

function channel_edit_page_controller:init()
  
  for s = 1, 16 do
    pattern_buttons["step"..s.."_pattern_button"] = Button:new(s, 2)
  end

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

      local selected_sequencer_pattern = program.selected_sequencer_pattern
      local trigs = program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].working_pattern.trig_values
      local lengths = program.sequencer_patterns[selected_sequencer_pattern].channels[program.selected_channel].working_pattern.lengths

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
      pattern_controller:update_working_patterns()
      channel_edit_page_controller:update_channel_edit_page_ui()
      return result
    end
  )
  press_handler:register_dual(
    "channel_edit_page",
    function(x, y, x2, y2)
      channel_edit_page_sequencer:dual_press(x, y, x2, y2)
      pattern_controller:update_working_patterns()
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
        pattern_controller:update_working_patterns()
      end
    )
  end
end



return channel_edit_page_controller


local channel_sequencer_page_controller = {}
local channel_pattern_buttons = {}

local refresh_button = {}

function channel_sequencer_page_controller.init()
  
  for s = 1, 96 do
    channel_pattern_buttons["step"..s.."_sequencer_pattern_button"] = Button:new((s-1) % 16 + 1 , math.floor((s-1) / 16) + 1, {
      {"Sequencer pattern "..s.." off", 2},
      {"Sequencer pattern "..s.." on", 7},
      {"Sequencer pattern "..s.." active", 15},
    })
    refresh_button[s] = true
  end

  channel_pattern_buttons["step"..program.get().selected_sequencer_pattern.."_sequencer_pattern_button"]:set_state(3)
end

function channel_sequencer_page_controller.register_draw_handlers()
  
  draw_handler:register_grid(
    "channel_sequencer_page",
    function()
      for s = 1, 96 do  
        channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:draw()
        if refresh_button[s] then
          if program.get().selected_sequencer_pattern == s then
            channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:set_state(3)
          elseif program.is_sequencer_pattern_active(s) then
            channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:set_state(2)
          else
            channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:set_state(1)
          end
          refresh_button[s] = false
        end
      end
    end
  )

end

function channel_sequencer_page_controller.register_press_handlers()

  press_handler:register(
    "channel_sequencer_page",
    function(x, y)
      local s = fn.calc_grid_count(x, y) + 48
      local previous_selected_pattern = program.get().selected_sequencer_pattern
      if channel_pattern_buttons["step"..s.."_sequencer_pattern_button"] and channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:is_this(x, y) then
        channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:set_state(3)
        program.get().selected_sequencer_pattern = s
        tooltip:show("Sequencer pattern "..s.." selected")
        if program.is_sequencer_pattern_active(previous_selected_pattern) then
          channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:set_state(2)
        else
          channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:set_state(1)
        end
      end

      channel_sequencer_page_controller.refresh()
      refresh_button[previous_selected_pattern] = true
      refresh_button[s] = true
      
    end
  )
  press_handler:register_dual(
    "channel_sequencer_page",
    function(x, y, x2, y2)
      local pattern = fn.calc_grid_count(x, y) + 48
      local target_pattern = fn.calc_grid_count(x2, y2) + 48
      if channel_pattern_buttons["step"..pattern.."_sequencer_pattern_button"] and channel_pattern_buttons["step"..pattern.."_sequencer_pattern_button"]:is_this(x, y) 
      and channel_pattern_buttons["step"..target_pattern.."_sequencer_pattern_button"] and channel_pattern_buttons["step"..target_pattern.."_sequencer_pattern_button"]:is_this(x2, y2) then
        program.set_sequencer_pattern(pattern, target_pattern)
        refresh_button[pattern] = true
        refresh_button[target_pattern] = true
      end
      channel_sequencer_page_controller.refresh()
    end
  )
end

function channel_sequencer_page_controller.refresh()
  channel_sequencer_page_ui_controller.refresh()
  for s = 1, 96 do
    refresh_button[s] = true
  end
end

return channel_sequencer_page_controller
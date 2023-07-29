
local channel_sequencer_page_controller = {}
local channel_pattern_buttons = {}


function channel_sequencer_page_controller.init()
  
  for s = 1, 96 do
    channel_pattern_buttons["step"..s.."_sequencer_pattern_button"] = Button:new((s-1) % 16 + 1 , math.floor((s-1) / 16) + 1, {
      {"Sequencer pattern "..s.." off", 2},
      {"Sequencer pattern "..s.." on", 7},
      {"Sequencer pattern "..s.." active", 15},
    })
  end

  channel_pattern_buttons["step"..program.get().selected_sequencer_pattern.."_sequencer_pattern_button"]:set_state(3)
end

function channel_sequencer_page_controller.register_draw_handlers()
  for s = 1, 96 do  
    draw_handler:register_grid(
      "channel_sequencer_page",
      function()
          channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:draw(trigs, lengths)
          if program.get().selected_sequencer_pattern == s then
            channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:set_state(3)
          elseif program.is_sequencer_pattern_active(s) then
            channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:set_state(2)
          else
            channel_pattern_buttons["step"..s.."_sequencer_pattern_button"]:set_state(1)
          end
      end
    )
  end
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
    end
  )

end

return channel_sequencer_page_controller
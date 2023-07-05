local channel_edit_page_controller = {}


local channel_edit_page_sequencer = Sequencer:new(4, "channel")

function channel_edit_page_controller:init()
  

end

function channel_edit_page_controller:register_draw_handlers()
  draw_handler:register(
    "channel_edit_page",
    function()


      -- This is temporary code. TODO: Implement pattern merging.
      local selected_sequencer_pattern = program.selected_sequencer_pattern
      local selected_pattern = program.selected_pattern
      
      local trigs = program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].trig_values
      local lengths = program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].lengths
      -- End temporary code


      return channel_edit_page_sequencer:draw(trigs, lengths)
    end
  )
end



function channel_edit_page_controller:register_press_handlers()

  press_handler:register(
    "channel_edit_page",
    function(x, y)
      return channel_edit_page_sequencer:press(x, y)
    end
  )
  press_handler:register_dual(
    "channel_edit_page",
    function(x, y, x2, y2)
      return channel_edit_page_sequencer:dual_press(x, y, x2, y2)
    end
  )
end



return channel_edit_page_controller

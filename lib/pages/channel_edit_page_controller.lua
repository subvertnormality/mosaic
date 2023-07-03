local channel_edit_page_controller = {}


local channel_edit_page_sequencer = Sequencer:new(4)

function channel_edit_page_controller:init()
  

end

function channel_edit_page_controller:register_draw_handlers()
  draw_handler:register(
    "channel_edit_page",
    function()
      return channel_edit_page_sequencer:draw()
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

end



return channel_edit_page_controller

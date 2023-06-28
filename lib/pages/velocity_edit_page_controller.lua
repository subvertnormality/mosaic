velocity_edit_page_controller = {}

local VerticalFader = include("sinfcommand/lib/controls/VerticalFader")

local faders = {}

function velocity_edit_page_controller:init()

  for s = 1, 16 do
    faders["step"..s.."_fader"] = VerticalFader:new(s, 1, 7)
  end

end

function velocity_edit_page_controller:register_draw_handlers()
  
  for s = 1, 16 do  
    draw_handler:register(
      "pattern_velocity_edit_page",
      function()
        return faders["step"..s.."_fader"]:draw()
      end
    )
  end
end

function velocity_edit_page_controller:register_press_handlers()
  for s = 1, 16 do   
    press_handler:register(
      "pattern_velocity_edit_page",
      function(x, y)
        faders["step"..s.."_fader"]:press(x, y)
      end
    )
  end
end

return velocity_edit_page_controller

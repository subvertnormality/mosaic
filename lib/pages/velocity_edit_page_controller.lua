velocity_edit_page_controller = {}

local VerticalFader = include("sinfcommand/lib/controls/VerticalFader")

local faders = {}
local vertical_offset = 0
local horizontal_offset = 0

function velocity_edit_page_controller:init()

  for s = 1, 64 do
    faders["step"..s.."_fader"] = VerticalFader:new(s, 1, 14)
  end

end

function velocity_edit_page_controller:register_draw_handlers()
  
  for s = 1, 64 do  
    draw_handler:register(
      "pattern_velocity_edit_page",
      function()

        faders["step"..s.."_fader"]:set_vertical_offset(vertical_offset)
        faders["step"..s.."_fader"]:set_horizontal_offset(horizontal_offset)
        return faders["step"..s.."_fader"]:draw()
      end
    )
  end
end

function velocity_edit_page_controller:register_press_handlers()
  for s = 1, 64 do   
    press_handler:register(
      "pattern_velocity_edit_page",
      function(x, y)
        faders["step"..s.."_fader"]:press(x, y)
      end
    )
  end
end

return velocity_edit_page_controller

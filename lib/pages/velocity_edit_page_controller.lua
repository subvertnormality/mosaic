velocity_edit_page_controller = {}

local VerticalFader = include("sinfcommand/lib/controls/VerticalFader")
local FadeButton = include("sinfcommand/lib/controls/FadeButton")

local faders = {}
local vertical_offset = 0
local horizontal_offset = 0

function reset_buttons()
  step1to16_fade_button:set_value(horizontal_offset)
  step17to32_fade_button:set_value(horizontal_offset)
  step33to48_fade_button:set_value(horizontal_offset)
  step49to64_fade_button:set_value(horizontal_offset)
end

function velocity_edit_page_controller:init()

  for s = 1, 64 do
    faders["step"..s.."_fader"] = VerticalFader:new(s, 1, 14)
  end

  step1to16_fade_button = FadeButton:new(10, 8, 1, 16)
  step17to32_fade_button = FadeButton:new(11, 8, 17, 32)
  step33to48_fade_button = FadeButton:new(12, 8, 33, 48)
  step49to64_fade_button = FadeButton:new(13, 8, 49, 64)
  reset_buttons()
end



function reset_fader(s)
  faders["step"..s.."_fader"]:set_vertical_offset(vertical_offset)
  faders["step"..s.."_fader"]:set_horizontal_offset(horizontal_offset)
end

function reset_all_controls()
  for s = 1, 64 do  
    faders["step"..s.."_fader"]:set_vertical_offset(vertical_offset)
    faders["step"..s.."_fader"]:set_horizontal_offset(horizontal_offset)
  end
  reset_buttons()
end

function velocity_edit_page_controller:register_draw_handlers()
  
  for s = 1, 64 do  
    draw_handler:register(
      "pattern_velocity_edit_page",
      function()
        reset_fader(s)
        return faders["step"..s.."_fader"]:draw()
      end
    )
  end
  draw_handler:register(
    "pattern_velocity_edit_page",
    function()

      return step1to16_fade_button:draw()
    end
  )
  draw_handler:register(
    "pattern_velocity_edit_page",
    function()

      return step17to32_fade_button:draw()
    end
  )
  draw_handler:register(
    "pattern_velocity_edit_page",
    function()

      return step33to48_fade_button:draw()
    end
  )
  draw_handler:register(
    "pattern_velocity_edit_page",
    function()

      return step49to64_fade_button:draw()
    end
  )
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

  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step1to16_fade_button:is_this(x, y)) then
        horizontal_offset = 0
        reset_all_controls()
      end
      return step1to16_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step17to32_fade_button:is_this(x, y)) then
        horizontal_offset = 16
        reset_all_controls()
      end

      return step17to32_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step33to48_fade_button:is_this(x, y)) then
        horizontal_offset = 32
        reset_all_controls()
      end

      return step33to48_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step49to64_fade_button:is_this(x, y)) then
        horizontal_offset = 48
        reset_all_controls()
      end

      return step49to64_fade_button:press(x, y)
    end
  )
end

return velocity_edit_page_controller

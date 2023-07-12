local velocity_edit_page_controller = {}

local VerticalFader = include("sinfcommand/lib/controls/VerticalFader")
local FadeButton = include("sinfcommand/lib/controls/FadeButton")

local faders = {}
local vertical_offset = 0
local horizontal_offset = 0

local step1to16_fade_button = FadeButton:new(9, 8, 1, 16)
local step17to32_fade_button = FadeButton:new(10, 8, 17, 32)
local step33to48_fade_button = FadeButton:new(11, 8, 33, 48)
local step49to64_fade_button = FadeButton:new(12, 8, 49, 64)

local vel1to7_fade_button = FadeButton:new(15, 8, 1, 7)
local vel8to14_fade_button = FadeButton:new(16, 8, 8, 14)

function velocity_edit_page_controller:reset_buttons()
  step1to16_fade_button:set_value(horizontal_offset)
  step17to32_fade_button:set_value(horizontal_offset)
  step33to48_fade_button:set_value(horizontal_offset)
  step49to64_fade_button:set_value(horizontal_offset)
  vel1to7_fade_button:set_value(vertical_offset)
  vel8to14_fade_button:set_value(vertical_offset)
end

function velocity_edit_page_controller:init()

  for s = 1, 64 do
    faders["step"..s.."_fader"] = VerticalFader:new(s, 1, 14)
  end

  velocity_edit_page_controller:reset_buttons()
end


function velocity_edit_page_controller:value_from_velocity(vel)

  if vel == -1 then return 1 end

  local inputStart = 0
  local inputEnd = 127
  local outputStart = 1
  local outputEnd = 14

  local inputRange = inputEnd - inputStart
  local outputRange = outputEnd - outputStart

  local inputValue = (inputEnd - vel) / inputRange
  local outputValue = outputStart + (inputValue * outputRange)

  return math.floor(outputValue)
end

function velocity_edit_page_controller:velocity_from_value(val)

  if val == -1 then return 127 end

  local inputStart = 1
  local inputEnd = 14
  local outputStart = 0
  local outputEnd = 127

  local inputRange = inputEnd - inputStart
  local outputRange = outputEnd - outputStart

  local inputValue = (val - inputStart) / inputRange
  local outputValue = outputEnd - (inputValue * outputRange)

  return math.floor(outputValue)
end


function velocity_edit_page_controller:reset_fader(s)
  local selected_sequencer_pattern = program.selected_sequencer_pattern
  local selected_pattern = program.selected_pattern
  faders["step"..s.."_fader"]:set_vertical_offset(vertical_offset)
  faders["step"..s.."_fader"]:set_horizontal_offset(horizontal_offset)
  local value = velocity_edit_page_controller:value_from_velocity(program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].velocity_values[s])

  if value then 
    faders["step"..s.."_fader"]:set_value(value) 
  end

  if program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].trig_values[s] < 1 then
    faders["step"..s.."_fader"]:set_dark()
  else
    faders["step"..s.."_fader"]:set_light()
  end
end

function velocity_edit_page_controller:reset_all_controls()
  for s = 1, 64 do  
    faders["step"..s.."_fader"]:set_vertical_offset(vertical_offset)
    faders["step"..s.."_fader"]:set_horizontal_offset(horizontal_offset)
  end
  velocity_edit_page_controller:reset_buttons()
end

function velocity_edit_page_controller:register_draw_handlers()
  
  for s = 1, 64 do  
    draw_handler:register(
      "pattern_velocity_edit_page",
      function()
        velocity_edit_page_controller:reset_fader(s)
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
  draw_handler:register(
    "pattern_velocity_edit_page",
    function()

      return vel1to7_fade_button:draw()
    end
  )
  draw_handler:register(
    "pattern_velocity_edit_page",
    function()

      return vel8to14_fade_button:draw()
    end
  )
end


function velocity_edit_page_controller:register_press_handlers()
  for s = 1, 64 do   
    press_handler:register(
      "pattern_velocity_edit_page",
      function(x, y)
        faders["step"..s.."_fader"]:press(x, y)
        if faders["step"..s.."_fader"]:is_this(x, y) then
          local selected_sequencer_pattern = program.selected_sequencer_pattern
          local selected_pattern = program.selected_pattern
          local velocity = velocity_edit_page_controller:velocity_from_value(faders["step"..s.."_fader"]:get_value())
          program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].velocity_values[s] = velocity
          program.sequencer_patterns[program.selected_sequencer_pattern].active = true
        end
      end
    )
  end

  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step1to16_fade_button:is_this(x, y)) then
        horizontal_offset = 0
        velocity_edit_page_controller:reset_all_controls()
      end
      return step1to16_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step17to32_fade_button:is_this(x, y)) then
        horizontal_offset = 16
        velocity_edit_page_controller:reset_all_controls()
      end

      return step17to32_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step33to48_fade_button:is_this(x, y)) then
        horizontal_offset = 32
        velocity_edit_page_controller:reset_all_controls()
      end

      return step33to48_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step49to64_fade_button:is_this(x, y)) then
        horizontal_offset = 48
        velocity_edit_page_controller:reset_all_controls()
      end

      return step49to64_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (vel1to7_fade_button:is_this(x, y)) then
        vertical_offset = 0
        velocity_edit_page_controller:reset_all_controls()
      end

      return vel1to7_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (vel8to14_fade_button:is_this(x, y)) then
        vertical_offset = 7
        velocity_edit_page_controller:reset_all_controls()
      end

      return vel8to14_fade_button:press(x, y)
    end
  )
end

return velocity_edit_page_controller

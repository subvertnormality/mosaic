local velocity_edit_page_controller = {}

local vertical_fader = include("mosaic/lib/controls/vertical_fader")
local fade_button = include("mosaic/lib/controls/fade_button")

local faders = {}
local vertical_offset = 0
local horizontal_offset = 0

local velocity_from_value_results = {}
local value_from_velocity_results = {}

local step1to16_fade_button = fade_button:new(9, 8, 1, 16)
local step17to32_fade_button = fade_button:new(10, 8, 17, 32)
local step33to48_fade_button = fade_button:new(11, 8, 33, 48)
local step49to64_fade_button = fade_button:new(12, 8, 49, 64)

local vel1to7_fade_button = fade_button:new(15, 8, 1, 7)
local vel8to14_fade_button = fade_button:new(16, 8, 8, 14)

local quad_dupe_button = button:new(7, 8)

function velocity_edit_page_controller.init()
  for s = 1, 64 do
    faders["step" .. s .. "_fader"] = vertical_fader:new(s, 1, 14)
  end

  for val = 1, 14 do
    local input_start = 1
    local input_end = 14

    local output_start = 0
    local output_end = 127

    local input_range = input_end - input_start
    local output_range = output_end - output_start

    local input_value = (val - input_start) / input_range
    local output_value = output_end - (input_value * output_range)

    velocity_from_value_results[val] = math.floor(output_value)
  end

  for vel = 0, 127 do
    local input_start = 0
    local input_end = 127

    local output_start = 1
    local output_end = 14

    local input_range = input_end - input_start
    local output_range = output_end - output_start

    local input_value = (input_end - vel) / input_range
    local output_value = output_start + (input_value * output_range)

    value_from_velocity_results[vel] = math.floor(output_value)
  end

  velocity_edit_page_controller.refresh()
end

function velocity_edit_page_controller.register_draw_handlers()
  for s = 1, 64 do
    draw_handler:register_grid(
      "pattern_velocity_edit_page",
      function()
        -- velocity_edit_page_controller.refresh()
        return faders["step" .. s .. "_fader"]:draw()
      end
    )
  end
  draw_handler:register_grid(
    "pattern_velocity_edit_page",
    function()
      return step1to16_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_velocity_edit_page",
    function()
      return step17to32_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_velocity_edit_page",
    function()
      return step33to48_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_velocity_edit_page",
    function()
      return step49to64_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_velocity_edit_page",
    function()
      return vel1to7_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_velocity_edit_page",
    function()
      return vel8to14_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_velocity_edit_page",
    function()
      return quad_dupe_button:draw()
    end
  )
end

function velocity_edit_page_controller.register_press_handlers()
  for s = 1, 64 do
    press_handler:register(
      "pattern_velocity_edit_page",
      function(x, y)
        if faders["step" .. s .. "_fader"]:is_this(x, y) then
          faders["step" .. s .. "_fader"]:press(x, y)
          local selected_sequencer_pattern = program.get().selected_sequencer_pattern
          local selected_pattern = program.get().selected_pattern
          local velocity =
            velocity_edit_page_controller.velocity_from_value(faders["step" .. s .. "_fader"]:get_value())
          local seq_pattern = program.get_selected_sequencer_pattern().patterns[selected_pattern]
          seq_pattern.velocity_values[s] = velocity
          program.get_selected_sequencer_pattern().active = true
          local steps_tip = s .. " "
          tooltip:show("Step " .. s .. " velocity set to " .. velocity)

          if quad_dupe_button:get_state() == 2 then
            local steps = {16, 32, 48, -16, -32, -48}

            for _, step in ipairs(steps) do
              local step_value = s + step
              if step_value > 0 and step_value < 65 then
                seq_pattern.velocity_values[step_value] = velocity
                steps_tip = steps_tip .. step_value .. " "
              end
            end
            tooltip:show("Steps " .. steps_tip .. "set to " .. velocity)
          end

          pattern_controller.ui_throttled_update_working_patterns()
        end
      end
    )
  end
  press_handler:register_long(
    "pattern_velocity_edit_page",
    function(x, y)
      if (y == 1) then
        program.get().selected_pattern = x
        tooltip:show("Pattern " .. x .. " selected")
        velocity_edit_page_controller.refresh()
      end
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step1to16_fade_button:is_this(x, y)) then
        horizontal_offset = 0
        velocity_edit_page_controller.refresh()
        tooltip:show("Steps 1 to 16")
      end
      return step1to16_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step17to32_fade_button:is_this(x, y)) then
        horizontal_offset = 16
        velocity_edit_page_controller.refresh()
        tooltip:show("Steps 17 to 32")
      end

      return step17to32_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step33to48_fade_button:is_this(x, y)) then
        horizontal_offset = 32
        velocity_edit_page_controller.refresh()
        tooltip:show("Steps 33 to 48")
      end

      return step33to48_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (step49to64_fade_button:is_this(x, y)) then
        horizontal_offset = 48
        velocity_edit_page_controller.refresh()
        tooltip:show("Steps 49 to 64")
      end

      return step49to64_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (vel1to7_fade_button:is_this(x, y)) then
        vertical_offset = 0
        velocity_edit_page_controller.refresh()
        tooltip:show("Velocity 68 to 127")
      end

      return vel1to7_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      if (vel8to14_fade_button:is_this(x, y)) then
        vertical_offset = 7
        velocity_edit_page_controller.refresh()
        tooltip:show("Velocity 0 to 58")
      end

      return vel8to14_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_velocity_edit_page",
    function(x, y)
      quad_dupe_button:press(x, y)
      if (quad_dupe_button:is_this(x, y)) then
        if quad_dupe_button:get_state() == 1 then
          tooltip:show("Quad dupe off")
          quad_dupe_button:no_blink()
        else
          tooltip:show("Quad dupe on")
          quad_dupe_button:blink()
        end
      end
    end
  )
end

function velocity_edit_page_controller.value_from_velocity(vel)
  if vel == -1 then
    return 1
  end
  return value_from_velocity_results[vel]
end

function velocity_edit_page_controller.velocity_from_value(val)
  if val == -1 then
    return 100
  end
  return velocity_from_value_results[val]
end

function velocity_edit_page_controller.refresh_buttons()
  step1to16_fade_button:set_value(horizontal_offset)
  step17to32_fade_button:set_value(horizontal_offset)
  step33to48_fade_button:set_value(horizontal_offset)
  step49to64_fade_button:set_value(horizontal_offset)
  vel1to7_fade_button:set_value(vertical_offset)
  vel8to14_fade_button:set_value(vertical_offset)
end

function velocity_edit_page_controller.refresh_fader(s)
  local selected_pattern = program.get_selected_pattern()
  faders["step" .. s .. "_fader"]:set_vertical_offset(vertical_offset)
  faders["step" .. s .. "_fader"]:set_horizontal_offset(horizontal_offset)

  local value = velocity_edit_page_controller.value_from_velocity(selected_pattern.velocity_values[s])

  if value then
    faders["step" .. s .. "_fader"]:set_value(value)
  end

  if selected_pattern.trig_values[s] < 1 then
    faders["step" .. s .. "_fader"]:set_dark()
  else
    faders["step" .. s .. "_fader"]:set_light()
  end
end

function velocity_edit_page_controller.refresh()
  clock.run(
    function()
      for s = 1, 64 do
        velocity_edit_page_controller.refresh_fader(s)
        clock.sleep(0.0001)
      end
      velocity_edit_page_controller.refresh_buttons()
    end
  )
end

return velocity_edit_page_controller

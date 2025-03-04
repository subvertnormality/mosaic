local velocity_edit_page = {}

local vertical_fader = include("mosaic/lib/controls/vertical_fader")
local fade_button = include("mosaic/lib/controls/fade_button")

local faders = {}
local vertical_offset = 0
local horizontal_offset = 0

local velocity_from_value_results = {}
local value_from_velocity_results = {}

local step1to16_button = button:new(9, 8, {{"Inactive", 3}, {"Page 1-16", 15}})
local step17to32_button = button:new(10, 8, {{"Inactive", 3}, {"Page 17-32", 15}})
local step33to48_button = button:new(11, 8, {{"Inactive", 3}, {"Page 33-48", 15}})
local step49to64_button = button:new(12, 8, {{"Inactive", 3}, {"Page 49-64", 15}})

local vel8to14_fade_button = fade_button:new(15, 8, 0, 7, "up")
local vel1to7_fade_button = fade_button:new(16, 8, 0, 7, "down")

function velocity_edit_page.init()
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

  velocity_edit_page.refresh()
end

function velocity_edit_page.register_draws()
  for s = 1, 64 do
    draw:register_grid(
      "velocity_edit_page",
      function()
        -- velocity_edit_page.refresh()
        return faders["step" .. s .. "_fader"]:draw()
      end
    )
  end
  draw:register_grid(
    "velocity_edit_page",
    function()
        return step1to16_button:draw()
    end
  )

  draw:register_grid(
      "velocity_edit_page",
      function()
          return step17to32_button:draw()
      end
  )

  draw:register_grid(
      "velocity_edit_page",
      function()
          return step33to48_button:draw()
      end
  )

  draw:register_grid(
      "velocity_edit_page",
      function()
          return step49to64_button:draw()
      end
  )
  draw:register_grid(
    "velocity_edit_page",
    function()
      return vel1to7_fade_button:draw()
    end
  )
  draw:register_grid(
    "velocity_edit_page",
    function()
      return vel8to14_fade_button:draw()
    end
  )
end

function velocity_edit_page.register_press()
  for s = 1, 64 do
    press:register(
      "velocity_edit_page",
      function(x, y)
        if (y == 1) and is_key1_down then
          program.get().selected_pattern = x
          tooltip:show("Pattern " .. x .. " selected")
          velocity_edit_page.refresh()
        else
          if faders["step" .. s .. "_fader"]:is_this(x, y) then
            faders["step" .. s .. "_fader"]:press(x, y)
            local selected_song_pattern = program.get().selected_song_pattern
            local selected_pattern = program.get().selected_pattern
            local velocity =
              velocity_edit_page.velocity_from_value(faders["step" .. s .. "_fader"]:get_value())
            local seq_pattern = program.get_selected_song_pattern().patterns[selected_pattern]
            seq_pattern.velocity_values[s] = velocity
            program.get_selected_song_pattern().active = true
            local steps_tip = s .. " "
            tooltip:show("Step " .. s .. " velocity set to " .. velocity)

            if is_key1_down then
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

            pattern.update_working_patterns()
          end
        end
      end
    )
  end
  press:register_long(
    "velocity_edit_page",
    function(x, y)
      if (y == 1) then
        program.get().selected_pattern = x
        tooltip:show("Pattern " .. x .. " selected")
        velocity_edit_page.refresh()
      end
    end
  )
  press:register(
    "velocity_edit_page",
    function(x, y)
        if step1to16_button:is_this(x, y) then
            horizontal_offset = 0
            step1to16_button:set_state(2)
            step17to32_button:set_state(1)
            step33to48_button:set_state(1)
            step49to64_button:set_state(1)
            velocity_edit_page.refresh()
            tooltip:show("Steps 1 to 16")
        end
    end
  )

  press:register(
      "velocity_edit_page",
      function(x, y)
          if step17to32_button:is_this(x, y) then
              horizontal_offset = 16
              step1to16_button:set_state(1)
              step17to32_button:set_state(2)
              step33to48_button:set_state(1)
              step49to64_button:set_state(1)
              velocity_edit_page.refresh()
              tooltip:show("Steps 17 to 32")
          end
      end
  )

  press:register(
      "velocity_edit_page",
      function(x, y)
          if step33to48_button:is_this(x, y) then
              horizontal_offset = 32
              step1to16_button:set_state(1)
              step17to32_button:set_state(1)
              step33to48_button:set_state(2)
              step49to64_button:set_state(1)
              velocity_edit_page.refresh()
              tooltip:show("Steps 33 to 48")
          end
      end
  )

  press:register(
      "velocity_edit_page",
      function(x, y)
          if step49to64_button:is_this(x, y) then
              horizontal_offset = 48
              step1to16_button:set_state(1)
              step17to32_button:set_state(1)
              step33to48_button:set_state(1)
              step49to64_button:set_state(2)
              velocity_edit_page.refresh()
              tooltip:show("Steps 49 to 64")
          end
      end
  )
  press:register(
    "velocity_edit_page",
    function(x, y)
        if (vel1to7_fade_button:is_this(x, y)) then
            local new_offset = vel1to7_fade_button:press(x, y)
            if new_offset ~= false then
                vertical_offset = new_offset
                velocity_edit_page.refresh()
                -- Calculate value range for current offset page
                local high_value = new_offset + 1
                local low_value = math.max(1, high_value + 6)  -- Use 6 to show 7 values total
                -- Convert to velocities and swap them since the mapping is inverted
                local high_vel = velocity_edit_page.velocity_from_value(high_value)
                local low_vel = velocity_edit_page.velocity_from_value(low_value)
                tooltip:show("Velocity " .. low_vel .. " to " .. high_vel)
            end
        end
        return vel1to7_fade_button:press(x, y)
    end
  )
  press:register_long(
    "velocity_edit_page",
    function(x, y)
        if (vel1to7_fade_button:is_this(x, y)) then
            vertical_offset = 7  -- Go to full high velocity (0)
            velocity_edit_page.refresh()
            local high_value = 8
            local low_value = 14
            local high_vel = velocity_edit_page.velocity_from_value(high_value)
            local low_vel = velocity_edit_page.velocity_from_value(low_value)
            tooltip:show("Velocity " .. low_vel .. " to " .. high_vel)
        elseif (vel8to14_fade_button:is_this(x, y)) then
            vertical_offset = 0  -- Go to full low velocity (127)
            velocity_edit_page.refresh()
            local high_value = 1
            local low_value = 7
            local high_vel = velocity_edit_page.velocity_from_value(high_value)
            local low_vel = velocity_edit_page.velocity_from_value(low_value)
            tooltip:show("Velocity " .. low_vel .. " to " .. high_vel)
        end
    end
)
  press:register(
      "velocity_edit_page",
      function(x, y)
          if (vel8to14_fade_button:is_this(x, y)) then
              local new_offset = vel8to14_fade_button:press(x, y)
              if new_offset ~= false then
                  vertical_offset = new_offset
                  velocity_edit_page.refresh()
                  -- Calculate value range for current offset page
                  local high_value = new_offset + 1
                  local low_value = math.max(1, high_value + 6)  -- Use 6 to show 7 values total
                  -- Convert to velocities and swap them since the mapping is inverted
                  local high_vel = velocity_edit_page.velocity_from_value(high_value)
                  local low_vel = velocity_edit_page.velocity_from_value(low_value)
                  tooltip:show("Velocity " .. low_vel .. " to " .. high_vel)
              end
          end
          return vel8to14_fade_button:press(x, y)
      end
  )
end

function velocity_edit_page.value_from_velocity(vel)
  if vel == -1 then
    return 1
  end
  return value_from_velocity_results[vel]
end

function velocity_edit_page.velocity_from_value(val)
  if val == -1 then
    return 100
  end
  return velocity_from_value_results[val]
end

function velocity_edit_page.refresh_buttons()
  step1to16_button:set_state(horizontal_offset == 0 and 2 or 1)
  step17to32_button:set_state(horizontal_offset == 16 and 2 or 1)
  step33to48_button:set_state(horizontal_offset == 32 and 2 or 1)
  step49to64_button:set_state(horizontal_offset == 48 and 2 or 1)
  vel1to7_fade_button:set_value(vertical_offset)
  vel8to14_fade_button:set_value(vertical_offset)
end

function velocity_edit_page.refresh_fader(s)
  local selected_pattern = program.get_selected_pattern()
  faders["step" .. s .. "_fader"]:set_vertical_offset(vertical_offset)
  faders["step" .. s .. "_fader"]:set_horizontal_offset(horizontal_offset)

  local value = velocity_edit_page.value_from_velocity(selected_pattern.velocity_values[s])

  if value then
    faders["step" .. s .. "_fader"]:set_value(value)
  end

  if selected_pattern.trig_values[s] < 1 then
    faders["step" .. s .. "_fader"]:set_dark()
  else
    faders["step" .. s .. "_fader"]:set_light()
  end
end

velocity_edit_page.refresh = scheduler.debounce(function()

  velocity_edit_page.refresh_buttons()

  for s = 1, 64, 8 do
    -- Process 8 faders per batch
    for i = 0, 7 do
      local index = s + i
      if index <= 64 then
        velocity_edit_page.refresh_fader(index)
      end
    end
    coroutine.yield()  -- Yield after each batch of 8
  end
 
  fn.grid_dirty = true
 end, 0.01)

return velocity_edit_page

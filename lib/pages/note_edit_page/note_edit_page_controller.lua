local note_edit_page_controller = {}


local vertical_fader = include("mosaic/lib/controls/vertical_fader")
local fade_button = include("mosaic/lib/controls/fade_button")

local faders = {}
local vertical_offset = 7
local horizontal_offset = 0

local step1to16_button = button:new(9, 8, {{"Inactive", 3}, {"Page 1-16", 15}})
local step17to32_button = button:new(10, 8, {{"Inactive", 3}, {"Page 17-32", 15}})
local step33to48_button = button:new(11, 8, {{"Inactive", 3}, {"Page 33-48", 15}})
local step49to64_button = button:new(12, 8, {{"Inactive", 3}, {"Page 49-64", 15}})

local note1to7_fade_button = fade_button:new(16, 8, 0, 14, "up")      -- Bottom button moves up
local note8to14_fade_button = fade_button:new(15, 8, 0, 14, "center") -- Middle button centers
local note15to21_fade_button = fade_button:new(14, 8, 0, 14, "down")  -- Top button moves down



function note_edit_page_controller.init()
  for s = 1, 64 do
    faders["step" .. s .. "_fader"] = vertical_fader:new(s, 1, 21)
  end

  note_edit_page_controller.refresh()
end

function note_edit_page_controller.register_draws()
  for s = 1, 64 do
    draw:register_grid(
      "note_edit_page",
      function()
        return faders["step" .. s .. "_fader"]:draw()
      end
    )
  end
  draw:register_grid(
    "note_edit_page",
    function()
      return step1to16_button:draw()
    end
  )
  draw:register_grid(
    "note_edit_page",
    function()
      return step17to32_button:draw()
    end
  )
  draw:register_grid(
    "note_edit_page",
    function()
      return step33to48_button:draw()
    end
  )
  draw:register_grid(
    "note_edit_page",
    function()
      return step49to64_button:draw()
    end
  )
  draw:register_grid(
    "note_edit_page",
    function()
      return note1to7_fade_button:draw()
    end
  )
  draw:register_grid(
    "note_edit_page",
    function()
      return note8to14_fade_button:draw()
    end
  )
  draw:register_grid(
    "note_edit_page",
    function()
      return note15to21_fade_button:draw()
    end
  )
end

function note_edit_page_controller.register_presss()
  for s = 1, 64 do
    press:register(
      "note_edit_page",
      function(x, y)
        if y == 1 and is_key3_down then
          program.get().selected_pattern = x
          tooltip:show("Pattern " .. x .. " selected")
          note_edit_page_controller.refresh()
          return
        else
          local fader_key = "step" .. s .. "_fader"
          local fader = faders[fader_key]
          fader:press(x, y)

          if not fader:is_this(x, y) then
            return
          end

          local selected_sequencer_pattern = program.get().selected_sequencer_pattern
          local selected_pattern = program.get().selected_pattern
          local note = fn.note_from_value(fader:get_value())
          local seq_pattern = program.get_selected_sequencer_pattern().patterns[selected_pattern]
          local steps_tip = s .. " "

          seq_pattern.note_values[s] = note
          program.get_selected_sequencer_pattern().active = true
          tooltip:show("Step " .. s .. " note set to " .. note)

          if is_key3_down then
            local steps = {16, 32, 48, -16, -32, -48}

            for _, step in ipairs(steps) do
              local step_value = s + step
              if step_value > 0 and step_value < 65 then
                seq_pattern.note_values[step_value] = note
                steps_tip = steps_tip .. step_value .. " "
              end
            end
            tooltip:show("Steps " .. steps_tip .. "set to " .. note)
          end

          pattern.update_working_patterns()
        end
      end
    )
  end
  press:register_long(
    "note_edit_page",
    function(x, y)
      if (y == 1) then
        program.get().selected_pattern = x
        tooltip:show("Pattern " .. x .. " selected")
        note_edit_page_controller.refresh()
      end
    end
  )
  press:register(
    "note_edit_page",
    function(x, y)
        if step1to16_button:is_this(x, y) then
            horizontal_offset = 0
            step1to16_button:set_state(2)
            step17to32_button:set_state(1)
            step33to48_button:set_state(1)
            step49to64_button:set_state(1)
            note_edit_page_controller.refresh()
            tooltip:show("Steps 1 to 16")
        end
    end
  )

  press:register(
      "note_edit_page",
      function(x, y)
          if step17to32_button:is_this(x, y) then
              horizontal_offset = 16
              step1to16_button:set_state(1)
              step17to32_button:set_state(2)
              step33to48_button:set_state(1)
              step49to64_button:set_state(1)
              note_edit_page_controller.refresh()
              tooltip:show("Steps 17 to 32")
          end
      end
  )

  press:register(
      "note_edit_page",
      function(x, y)
          if step33to48_button:is_this(x, y) then
              horizontal_offset = 32
              step1to16_button:set_state(1)
              step17to32_button:set_state(1)
              step33to48_button:set_state(2)
              step49to64_button:set_state(1)
              note_edit_page_controller.refresh()
              tooltip:show("Steps 33 to 48")
          end
      end
  )

  press:register(
      "note_edit_page",
      function(x, y)
          if step49to64_button:is_this(x, y) then
              horizontal_offset = 48
              step1to16_button:set_state(1)
              step17to32_button:set_state(1)
              step33to48_button:set_state(1)
              step49to64_button:set_state(2)
              note_edit_page_controller.refresh()
              tooltip:show("Steps 49 to 64")
          end
      end
  )
  press:register(
    "note_edit_page",
    function(x, y)
        if (note15to21_fade_button:is_this(x, y)) then
            local new_offset = note15to21_fade_button:press(x, y)
            if new_offset ~= false then
                vertical_offset = 14 - new_offset  -- Convert button value to offset
                note_edit_page_controller.refresh()
                local low_value = vertical_offset + 1
                local high_value = math.min(21, low_value + 6)
                local low_note = fn.note_from_value(low_value)
                local high_note = fn.note_from_value(high_value)
                if low_note == 0 then low_note = "Root" end
                if high_note == 0 then high_note = "Root" end
                tooltip:show("Notes " .. high_note .. " to " .. low_note)
            end
        end
        return note15to21_fade_button:press(x, y)
    end
  )

  press:register(
      "note_edit_page",
      function(x, y)
          if (note8to14_fade_button:is_this(x, y)) then
              local new_offset = note8to14_fade_button:press(x, y)
              if new_offset ~= false then
                  vertical_offset = 7  -- Center position
                  note_edit_page_controller.refresh()
                  tooltip:show("Root to 6")
              end
          end
          return note8to14_fade_button:press(x, y)
      end
  )

  press:register(
      "note_edit_page",
      function(x, y)
          if (note1to7_fade_button:is_this(x, y)) then
              local new_offset = note1to7_fade_button:press(x, y)
              if new_offset ~= false then
                  vertical_offset = 14 - new_offset  -- Convert button value to offset
                  note_edit_page_controller.refresh()
                  local low_value = vertical_offset + 1
                  local high_value = math.min(21, low_value + 6)
                  local low_note = fn.note_from_value(low_value)
                  local high_note = fn.note_from_value(high_value)
                  if low_note == 0 then low_note = "Root" end
                  if high_note == 0 then high_note = "Root" end
                  tooltip:show("Notes " .. high_note .. " to " .. low_note)
              end
          end
          return note1to7_fade_button:press(x, y)
      end
  )

  press:register_long(
    "note_edit_page",
    function(x, y)
        if (y == 1) then
            program.get().selected_pattern = x
            tooltip:show("Pattern " .. x .. " selected")
            note_edit_page_controller.refresh()
        elseif (note15to21_fade_button:is_this(x, y)) then
            -- Top button - jump to highest notes
            vertical_offset = 0
            note_edit_page_controller.refresh()
            local low_value = 1
            local high_value = 7
            local low_note = fn.note_from_value(low_value)
            local high_note = fn.note_from_value(high_value)
            if low_note == 0 then low_note = "Root" end
            if high_note == 0 then high_note = "Root" end
            tooltip:show("Notes " .. high_note .. " to " .. low_note)
        elseif (note8to14_fade_button:is_this(x, y)) then
            -- Middle button - jump to root notes
            vertical_offset = 7
            note_edit_page_controller.refresh()
            tooltip:show("Root to 6")
        elseif (note1to7_fade_button:is_this(x, y)) then
            -- Bottom button - jump to lowest notes
            vertical_offset = 14
            note_edit_page_controller.refresh()
            local low_value = 15
            local high_value = 21
            local low_note = fn.note_from_value(low_value)
            local high_note = fn.note_from_value(high_value)
            if low_note == 0 then low_note = "Root" end
            if high_note == 0 then high_note = "Root" end
            tooltip:show("Notes " .. high_note .. " to " .. low_note)
        end
    end
  )
end

function note_edit_page_controller.refresh_buttons()
  step1to16_button:set_state(horizontal_offset == 0 and 2 or 1)
  step17to32_button:set_state(horizontal_offset == 16 and 2 or 1)
  step33to48_button:set_state(horizontal_offset == 32 and 2 or 1)
  step49to64_button:set_state(horizontal_offset == 48 and 2 or 1)
  note1to7_fade_button:set_value(14 - vertical_offset)
  note8to14_fade_button:set_value(vertical_offset)
  note15to21_fade_button:set_value(14 - vertical_offset)
end

function note_edit_page_controller.refresh_fader(s)
  local selected_pattern = program.get().selected_pattern

  faders["step" .. s .. "_fader"]:set_vertical_offset(vertical_offset)
  faders["step" .. s .. "_fader"]:set_horizontal_offset(horizontal_offset)
  local value = fn.value_from_note(program.get_selected_sequencer_pattern().patterns[selected_pattern].note_values[s])

  if value then
    faders["step" .. s .. "_fader"]:set_value(value)
  end

  if program.get_selected_sequencer_pattern().patterns[selected_pattern].trig_values[s] < 1 then
    faders["step" .. s .. "_fader"]:set_dark()
  else
    faders["step" .. s .. "_fader"]:set_light()
  end
end

note_edit_page_controller.refresh = scheduler.debounce(function()

  note_edit_page_controller.refresh_buttons()

  -- Process faders in batches of 8
  for s = 1, 64, 8 do
    -- Update batch of 8 faders
    for i = 0, 7 do
      local index = s + i
      if index <= 64 then  -- Prevent going over bounds
        note_edit_page_controller.refresh_fader(index)
      end
    end
    coroutine.yield()  -- Yield after each batch of 8
  end
 
  fn.grid_dirty = true
 end, 0.01)

return note_edit_page_controller
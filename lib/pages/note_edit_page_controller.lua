local note_edit_page_controller = {}

local VerticalFader = include("sinfcommand/lib/controls/VerticalFader")
local FadeButton = include("sinfcommand/lib/controls/FadeButton")

local faders = {}
local vertical_offset = 7
local horizontal_offset = 0

local step1to16_fade_button = FadeButton:new(9, 8, 1, 16)
local step17to32_fade_button = FadeButton:new(10, 8, 17, 32)
local step33to48_fade_button = FadeButton:new(11, 8, 33, 48)
local step49to64_fade_button = FadeButton:new(12, 8, 49, 64)

local note1to7_fade_button = FadeButton:new(14, 8, 1, 7)
local note8to14_fade_button = FadeButton:new(15, 8, 8, 14)
local note15to21_fade_button = FadeButton:new(16, 8, 15, 21)

local quad_dupe_button = Button:new(7, 8)


function note_edit_page_controller.init()

  for s = 1, 64 do
    faders["step"..s.."_fader"] = VerticalFader:new(s, 1, 21)
  end

  note_edit_page_controller.refresh_buttons()
end


function note_edit_page_controller.register_draw_handlers()
  
  for s = 1, 64 do  
    draw_handler:register_grid(
      "pattern_note_edit_page",
      function()
        note_edit_page_controller.refresh_fader(s)
        return faders["step"..s.."_fader"]:draw()
      end
    )
  end
  draw_handler:register_grid(
    "pattern_note_edit_page",
    function()

      return step1to16_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_note_edit_page",
    function()

      return step17to32_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_note_edit_page",
    function()

      return step33to48_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_note_edit_page",
    function()

      return step49to64_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_note_edit_page",
    function()

      return note1to7_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_note_edit_page",
    function()

      return note8to14_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_note_edit_page",
    function()

      return note15to21_fade_button:draw()
    end
  )
  draw_handler:register_grid(
    "pattern_note_edit_page",
    function()

      return quad_dupe_button:draw()
    end
  )
end


function note_edit_page_controller.register_press_handlers()
  for s = 1, 64 do   
    press_handler:register(
      "pattern_note_edit_page",
      function(x, y)
        local fader_key = "step"..s.."_fader"
        local fader = faders[fader_key]
        fader:press(x, y)
        
        if not fader:is_this(x, y) then
          return
        end
        
        local selected_sequencer_pattern = program.get().selected_sequencer_pattern
        local selected_pattern = program.get().selected_pattern
        local note = fn.note_from_value(fader:get_value())
        local seq_pattern = program.get_selected_sequencer_pattern().patterns[selected_pattern]
        local steps_tip = s.." "

        seq_pattern.note_values[s] = note
        program.get_selected_sequencer_pattern().active = true
        tooltip:show("Step "..s.." note set to "..note)
        
        if quad_dupe_button:get_state() == 2 then
          local steps = {16, 32, 48, -16, -32, -48}
          
          for _, step in ipairs(steps) do
            local step_value = s + step
            if step_value > 0 and step_value < 65 then
              seq_pattern.note_values[step_value] = note
              steps_tip = steps_tip..step_value.." "
            end
          end
          tooltip:show("Steps "..steps_tip.."set to "..note)

        end
        
        pattern_controller.update_working_patterns()
      end
    )
  end
  press_handler:register_long(
    "pattern_note_edit_page",
    function(x, y)
      if (y == 1) then
        program.get().selected_pattern = x
        tooltip:show("Pattern "..x.." selected")
        note_edit_page_controller.refresh()
      end
    end
  )
  press_handler:register(
    "pattern_note_edit_page",
    function(x, y)
      if (step1to16_fade_button:is_this(x, y)) then
        horizontal_offset = 0
        note_edit_page_controller.refresh()
        tooltip:show("Steps 1 to 16")
      end
      return step1to16_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_note_edit_page",
    function(x, y)
      if (step17to32_fade_button:is_this(x, y)) then
        horizontal_offset = 16
        note_edit_page_controller.refresh()
        tooltip:show("Steps 17 to 32")
      end

      return step17to32_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_note_edit_page",
    function(x, y)
      if (step33to48_fade_button:is_this(x, y)) then
        horizontal_offset = 32
        note_edit_page_controller.refresh()
        tooltip:show("Steps 33 to 48")
      end

      return step33to48_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_note_edit_page",
    function(x, y)
      if (step49to64_fade_button:is_this(x, y)) then
        horizontal_offset = 48
        note_edit_page_controller.refresh()
        tooltip:show("Steps 49 to 64")
      end

      return step49to64_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_note_edit_page",
    function(x, y)
      if (note15to21_fade_button:is_this(x, y)) then
        vertical_offset = 0
        note_edit_page_controller.refresh()
        tooltip:show("Notes +6 to +13")
      end

      return note15to21_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_note_edit_page",
    function(x, y)
      if (note8to14_fade_button:is_this(x, y)) then
        vertical_offset = 7
        note_edit_page_controller.refresh()
        tooltip:show("Root to +6")
      end

      return note8to14_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_note_edit_page",
    function(x, y)
      if (note1to7_fade_button:is_this(x, y)) then
        vertical_offset = 14
        note_edit_page_controller.refresh()
        tooltip:show("Notes -1 to -7")
      end

      return note1to7_fade_button:press(x, y)
    end
  )
  press_handler:register(
    "pattern_note_edit_page",
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

function note_edit_page_controller.refresh_buttons()
  step1to16_fade_button:set_value(horizontal_offset)
  step17to32_fade_button:set_value(horizontal_offset)
  step33to48_fade_button:set_value(horizontal_offset)
  step49to64_fade_button:set_value(horizontal_offset)
  note1to7_fade_button:set_value(14 - vertical_offset)
  note8to14_fade_button:set_value(vertical_offset)
  note15to21_fade_button:set_value(14 - vertical_offset)
end

function note_edit_page_controller.refresh_fader(s)
  local selected_sequencer_pattern = program.get().selected_sequencer_pattern
  local selected_pattern = program.get().selected_pattern
  faders["step"..s.."_fader"]:set_vertical_offset(vertical_offset)
  faders["step"..s.."_fader"]:set_horizontal_offset(horizontal_offset)
  local value = fn.value_from_note(program.get_selected_sequencer_pattern().patterns[selected_pattern].note_values[s])

  if value then 
    faders["step"..s.."_fader"]:set_value(value) 
  end

  if program.get_selected_sequencer_pattern().patterns[selected_pattern].trig_values[s] < 1 then
    faders["step"..s.."_fader"]:set_dark()
  else
    faders["step"..s.."_fader"]:set_light()
  end
end

function note_edit_page_controller.refresh()
  for s = 1, 64 do  
    note_edit_page_controller.refresh_fader(s)
  end
  note_edit_page_controller.refresh_buttons()
end


return note_edit_page_controller

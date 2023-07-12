local er = require("er")
local drum_ops = include("sinfcommand/lib/drum_ops")

local trigger_edit_page_controller = {}
local paint_pattern = {}
local shift = 0

local pattern_trigger_edit_page_pattern_select_fader = Fader:new(1, 1, 16, 16)
local pattern_trigger_edit_page_sequencer = Sequencer:new(4, "pattern")
local pattern_trigger_edit_page_pattern1_fader = Fader:new(1, 2, 10, 100)
local pattern_trigger_edit_page_pattern2_fader = Fader:new(1, 3, 10, 100)
local pattern_trigger_edit_page_algorithm_fader = Fader:new(12, 2, 4, 4)
local pattern_trigger_edit_page_bankmask_fader = Fader:new(12, 3, 5, 5)
local pattern_trigger_edit_page_paint_button = Button:new(16, 8, {{"Inactive", 3}, {"Save", 15}})
local pattern_trigger_edit_page_cancel_button = Button:new(14, 8, {{"Inactive", 3}, {"Cancel", 15}})
local pattern_trigger_edit_page_left_button = Button:new(10, 8, {{"Inactive", 3}, {"Shift Left", 15}})
local pattern_trigger_edit_page_centre_button = Button:new(11, 8, {{"Inactive", 3}, {"Reset Shift", 8}})
local pattern_trigger_edit_page_right_button = Button:new(12, 8, {{"Inactive", 3}, {"Shift Right", 15}})


function trigger_edit_page_controller:init()
  
  pattern_trigger_edit_page_pattern_select_fader:set_value(program.selected_pattern)

  trigger_edit_page_controller:update_pattern_trigger_edit_page_ui()
end

function trigger_edit_page_controller:register_draw_handlers()
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_pattern_select_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()

    local selected_sequencer_pattern = program.selected_sequencer_pattern
    local selected_pattern = program.selected_pattern
    
    local trigs = program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].trig_values
    local lengths = program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].lengths
  
    return pattern_trigger_edit_page_sequencer:draw(trigs, lengths)
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_pattern1_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_pattern2_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_algorithm_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_bankmask_fader:draw()
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_paint_button:draw()
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_cancel_button:draw()
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_left_button:draw()
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_centre_button:draw()
  end
  )
  draw_handler:register(
  "pattern_trigger_edit_page",
  function()
    return pattern_trigger_edit_page_right_button:draw()
  end
  )
end

function trigger_edit_page_controller:update_pattern_trigger_edit_page_ui()
  local algorithm = pattern_trigger_edit_page_algorithm_fader:get_value()

  if (algorithm == 1) then
    pattern_trigger_edit_page_bankmask_fader:enabled()
    pattern_trigger_edit_page_bankmask_fader:set_size(5)
    pattern_trigger_edit_page_bankmask_fader:set_length(5)
    pattern_trigger_edit_page_pattern1_fader:set_size(128)
    pattern_trigger_edit_page_pattern2_fader:set_size(128)
    pattern_trigger_edit_page_pattern2_fader:disabled()
  elseif (algorithm == 2) then
    pattern_trigger_edit_page_bankmask_fader:enabled()
    pattern_trigger_edit_page_bankmask_fader:set_size(5)
    pattern_trigger_edit_page_bankmask_fader:set_length(5)
    pattern_trigger_edit_page_pattern1_fader:set_size(128)
    pattern_trigger_edit_page_pattern2_fader:set_size(128)
    pattern_trigger_edit_page_pattern2_fader:enabled()
  elseif (algorithm == 3) then
    pattern_trigger_edit_page_bankmask_fader:disabled()
    pattern_trigger_edit_page_bankmask_fader:set_size(5)
    pattern_trigger_edit_page_bankmask_fader:set_length(5)
    pattern_trigger_edit_page_pattern2_fader:enabled()
    pattern_trigger_edit_page_pattern1_fader:set_size(32)
    pattern_trigger_edit_page_pattern2_fader:set_size(32)
  elseif (algorithm == 4) then
    pattern_trigger_edit_page_bankmask_fader:enabled()
    pattern_trigger_edit_page_bankmask_fader:set_size(4)
    pattern_trigger_edit_page_bankmask_fader:set_length(4)
    pattern_trigger_edit_page_pattern1_fader:set_size(32)
    pattern_trigger_edit_page_pattern2_fader:set_size(16)
    pattern_trigger_edit_page_pattern2_fader:enabled()
  end

  fn.dirty_grid(true)
end

function trigger_edit_page_controller:register_press_handlers()
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    local result = pattern_trigger_edit_page_pattern_select_fader:press(x, y)
    program.selected_pattern = pattern_trigger_edit_page_pattern_select_fader:get_value()
    return result
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    pattern_trigger_edit_page_sequencer:press(x, y)
    if pattern_trigger_edit_page_sequencer:is_this(x, y) then
      pattern_controller:update_working_patterns()
    end
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    load_paint_pattern()
    pattern_trigger_edit_page_pattern1_fader:press(x, y)
    return true
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    load_paint_pattern()
    pattern_trigger_edit_page_pattern2_fader:press(x, y)
    return true
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    pattern_trigger_edit_page_algorithm_fader:press(x, y)
    if pattern_trigger_edit_page_algorithm_fader:is_this(x, y) then
      trigger_edit_page_controller:update_pattern_trigger_edit_page_ui()
    end
    load_paint_pattern()
    return true
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    pattern_trigger_edit_page_bankmask_fader:press(x, y)
    load_paint_pattern()
    return true
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    pattern_trigger_edit_page_paint_button:press(x, y)

    if pattern_trigger_edit_page_paint_button:is_this(x, y) then
      if (pattern_trigger_edit_page_paint_button:get_state() == 2) then
        pattern_trigger_edit_page_cancel_button:set_state(2)
        pattern_trigger_edit_page_left_button:set_state(2)
        pattern_trigger_edit_page_centre_button:set_state(2)
        pattern_trigger_edit_page_right_button:set_state(2)
        load_paint_pattern()
        pattern_trigger_edit_page_paint_button:blink()
      else
        pattern_trigger_edit_page_left_button:set_state(1)
        pattern_trigger_edit_page_centre_button:set_state(1)
        pattern_trigger_edit_page_right_button:set_state(1)
        pattern_trigger_edit_page_cancel_button:set_state(1)
        pattern_trigger_edit_page_sequencer:hide_unsaved_grid()
        save_paint_pattern(paint_pattern)
        pattern_trigger_edit_page_paint_button:no_blink()
      end
    end
    return true
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    pattern_trigger_edit_page_cancel_button:press(x, y)

    if pattern_trigger_edit_page_cancel_button:is_this(x, y) then
      if (pattern_trigger_edit_page_paint_button:get_state() == 2) then
        pattern_trigger_edit_page_sequencer:hide_unsaved_grid()
        pattern_trigger_edit_page_paint_button:set_state(1)
        pattern_trigger_edit_page_paint_button:no_blink()
        pattern_trigger_edit_page_cancel_button:no_blink()
        pattern_trigger_edit_page_left_button:set_state(1)
        pattern_trigger_edit_page_centre_button:set_state(1)
        pattern_trigger_edit_page_right_button:set_state(1)
      else
        pattern_trigger_edit_page_cancel_button:set_state(1)
      end
    end

    return true
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    -- pattern_trigger_edit_page_left_button:press(x, y)

    if pattern_trigger_edit_page_left_button:is_this(x, y) then
      if (pattern_trigger_edit_page_left_button:get_state() == 2) then
        shift = shift - 1

        load_paint_pattern()
        pattern_trigger_edit_page_left_button:set_state(2)
      else
        pattern_trigger_edit_page_left_button:set_state(1)
      end
    end

    return true
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    if pattern_trigger_edit_page_centre_button:is_this(x, y) then
      if (pattern_trigger_edit_page_centre_button:get_state() == 2) then
        shift = 0
        load_paint_pattern()
        pattern_trigger_edit_page_centre_button:set_state(2)
      else
        pattern_trigger_edit_page_centre_button:set_state(1)
      end
    end
    return true
  end
  )
  press_handler:register(
  "pattern_trigger_edit_page",
  function(x, y)
    -- pattern_trigger_edit_page_right_button:press(x, y)

    if pattern_trigger_edit_page_right_button:is_this(x, y) then
      if (pattern_trigger_edit_page_right_button:get_state() == 2) then
        shift = shift + 1

        pattern_trigger_edit_page_right_button:set_state(2)
        load_paint_pattern()
      else
        pattern_trigger_edit_page_right_button:set_state(1)
      end
    end

    return true
  end
  )
  press_handler:register_dual(
    "pattern_trigger_edit_page",
    function(x, y, x2, y2)
      pattern_trigger_edit_page_sequencer:dual_press(x, y, x2, y2)
      if pattern_trigger_edit_page_sequencer:is_this(x2, y2) then
        pattern_controller:update_working_patterns()
      end
    end
  )
end

function save_paint_pattern(p)
  local selected_sequencer_pattern = program.selected_sequencer_pattern
  local selected_pattern = program.selected_pattern
  local trigs = program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].trig_values
  local lengths = program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].lengths

  for x = 1, 64 do
    if (trigs[x] < 1) and p[x] then
      trigs[x] = 1
      lengths[x] = 1
    elseif trigs[x] and p[x] then
      trigs[x] = 0
      lengths[x] = 0
    end
  end
  program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].trig_values = trigs
  program.sequencer_patterns[selected_sequencer_pattern].patterns[selected_pattern].lengths = lengths
  pattern_controller:update_working_patterns()
  program.sequencer_patterns[program.selected_sequencer_pattern].active = true
end

function load_paint_pattern()
  if (pattern_trigger_edit_page_paint_button:get_state() == 2) then
    paint_pattern = {}
    local algorithm = pattern_trigger_edit_page_algorithm_fader:get_value()
    local pattern1 = pattern_trigger_edit_page_pattern1_fader:get_value()
    local pattern2 = pattern_trigger_edit_page_pattern2_fader:get_value()
    local bank = pattern_trigger_edit_page_bankmask_fader:get_value()

    if (algorithm == 3) then
      local erpattern = er.gen(pattern1, pattern2, 0)
      while #paint_pattern < 64 do
        for i = 1, #erpattern do
          table.insert(paint_pattern, erpattern[i])
          if #paint_pattern >= 64 then
            break
          end
        end
      end
    else
      for step = 1, 64 do
        if (algorithm == 1) then
          table.insert(paint_pattern, drum_ops.drum(bank, pattern1, step))
        elseif (algorithm == 2) then
          table.insert(paint_pattern, drum_ops.tresillo(bank, pattern1, pattern2, 24, step)) -- TODO need to make the tressilo length editable
        elseif (algorithm == 4) then
          table.insert(paint_pattern, drum_ops.nr(pattern1, bank, pattern2, step))
        end
      end
    end

    if (shift > 0) then
      for s = 1, shift do
        paint_pattern = fn.shift_table_right(paint_pattern)
      end
    elseif (shift < 0) then
      for s = 1, math.abs(shift) do
        paint_pattern = fn.shift_table_left(paint_pattern)
      end
    end

    pattern_trigger_edit_page_sequencer:show_unsaved_grid(paint_pattern)
  end
end

return trigger_edit_page_controller

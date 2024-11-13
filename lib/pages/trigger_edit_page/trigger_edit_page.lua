local er = require("er")
local drum_ops = include("mosaic/lib/helpers/drum_ops")


local trigger_edit_page = {}
local paint_pattern = {}
local shift = 0

local trigger_edit_page_pattern_select_fader = fader:new(1, 1, 16, 16)
local trigger_edit_page_sequencer = sequencer:new(4, "pattern")
local trigger_edit_page_pattern1_fader = fader:new(1, 2, 10, 100)
local trigger_edit_page_pattern2_fader = fader:new(1, 3, 10, 100)
local trigger_edit_page_algorithm_fader = fader:new(12, 2, 4, 4)
local trigger_edit_page_bankmask_fader = fader:new(12, 3, 5, 5)
local trigger_edit_page_paint_button = button:new(16, 8, {{"Inactive", 3}, {"Save", 15}})
local trigger_edit_page_cancel_button = button:new(14, 8, {{"Inactive", 3}, {"Cancel", 15}})
local trigger_edit_page_left_button = button:new(10, 8, {{"Inactive", 3}, {"Shift Left", 15}})
local trigger_edit_page_centre_button = button:new(11, 8, {{"Inactive", 3}, {"Reset Shift", 8}})
local trigger_edit_page_right_button = button:new(12, 8, {{"Inactive", 3}, {"Shift Right", 15}})

local load_timer = nil
local throttle_time = 0.1

function trigger_edit_page.init()
  trigger_edit_page.refresh_trigger_edit_page_ui()
end

function trigger_edit_page.register_draws()
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_pattern_select_fader:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_sequencer:draw(program.get_selected_channel(), grid_abstraction.led)
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_pattern1_fader:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_pattern2_fader:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_algorithm_fader:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_bankmask_fader:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_paint_button:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_cancel_button:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_left_button:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_centre_button:draw()
    end
  )
  draw:register_grid(
    "trigger_edit_page",
    function()
      return trigger_edit_page_right_button:draw()
    end
  )
end

local function get_bank_name(id)
  if (trigger_edit_page_algorithm_fader:get_value() == 4) then
    return "Prime " .. id
  end

  if (id == 1) then
    return "Random bank"
  elseif (id == 2) then
    return "Bass drum bank"
  elseif (id == 3) then
    return "Snare drum bank"
  elseif (id == 4) then
    return "Closed hi-hat bank"
  elseif (id == 5) then
    return "Open hi-hat bank"
  end
end

local function get_algorithm_name(id)
  if (id == 1) then
    return "Drum algorithm"
  elseif (id == 2) then
    return "Tresillo algorithm"
  elseif (id == 3) then
    return "Euclidean algorithm"
  elseif (id == 4) then
    return "Numeric repetitor"
  end
end

local function shift_table(tbl, n)
  local len = #tbl
  n = n % len
  if n == 0 then return tbl end
  local res = {}
  for i = 1, len do
    res[i] = tbl[(i - n - 1) % len + 1]
  end
  return res
end

local load_paint_pattern = scheduler.debounce(function()
  if (trigger_edit_page_paint_button:get_state() ~= 2) then
    return
  end
 
  -- Get all values up front
  local algorithm = trigger_edit_page_algorithm_fader:get_value()
  local pattern1 = trigger_edit_page_pattern1_fader:get_value()
  local pattern2 = trigger_edit_page_pattern2_fader:get_value() 
  local bank = trigger_edit_page_bankmask_fader:get_value()
  local len = 64
  paint_pattern = {}
  
  coroutine.yield() -- Yield after getting values
  
  -- Handle Euclidean rhythm case
  if (algorithm == 3) then
    local erpattern = er.gen(pattern1, pattern2, 0)
    local er_len = #erpattern
    
    -- Process in batches of 4
    for i = 1, len, 4 do
      for j = 0, 3 do
        local index = i + j
        if index <= len then
          paint_pattern[index] = erpattern[(index - 1) % er_len + 1]
        end
      end
      coroutine.yield() -- Yield after each batch of 4
    end
  
  -- Handle other algorithms
  else
    -- Process in batches of 4
    for step = 1, len, 4 do
      for j = 0, 3 do
        local current_step = step + j
        if current_step <= len then
          if (algorithm == 1) then
            paint_pattern[current_step] = drum_ops.drum(bank, pattern1, current_step)
          elseif (algorithm == 2) then
            paint_pattern[current_step] = drum_ops.tresillo(bank, pattern1, pattern2, params:string("tresillo_amount"), current_step)
          elseif (algorithm == 4) then
            paint_pattern[current_step] = drum_ops.nr(pattern1, bank, pattern2, current_step)
          end
        end
      end
      coroutine.yield() -- Yield after each batch of 4
    end
  end
 
  coroutine.yield() -- Yield before shift operation
  
  if shift ~= 0 then
    paint_pattern = shift_table(paint_pattern, shift)
  end
 
  trigger_edit_page_sequencer:show_unsaved_grid(paint_pattern)
 end, throttle_time)

local function save_paint_pattern(p)
  local selected_sequencer_pattern = program.get().selected_sequencer_pattern
  local selected_pattern = program.get().selected_pattern
  local trigs = program.get_selected_sequencer_pattern().patterns[selected_pattern].trig_values
  local lengths = program.get_selected_sequencer_pattern().patterns[selected_pattern].lengths

  for x = 1, 64 do
    if (trigs[x] < 1) and p[x] then
      trigs[x] = 1
      lengths[x] = 1
    elseif trigs[x] and p[x] then
      trigs[x] = 0
      lengths[x] = 0
    end
  end
  program.get_selected_sequencer_pattern().patterns[selected_pattern].trig_values = trigs
  program.get_selected_sequencer_pattern().patterns[selected_pattern].lengths = lengths
  pattern.update_working_patterns()
  program.get_selected_sequencer_pattern().active = true
end

function trigger_edit_page.register_presss()
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_pattern_select_fader:is_this(x, y) then
        trigger_edit_page_pattern_select_fader:press(x, y)
        program.get().selected_pattern = trigger_edit_page_pattern_select_fader:get_value()
        tooltip:show("Pattern " .. program.get().selected_pattern .. " selected")
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_sequencer:is_this(x, y) then
        trigger_edit_page_sequencer:press(x, y)
        pattern.update_working_patterns()
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_pattern1_fader:is_this(x, y) then
        trigger_edit_page_pattern1_fader:press(x, y)
        load_paint_pattern()
        if (trigger_edit_page_algorithm_fader:get_value() == 3) then
          tooltip:show("Fill - " .. trigger_edit_page_pattern1_fader:get_value() .. " selected")
        else
          tooltip:show("Pattern 1 - " .. trigger_edit_page_pattern1_fader:get_value() .. " selected")
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_pattern2_fader:is_this(x, y) then
        trigger_edit_page_pattern2_fader:press(x, y)
        load_paint_pattern()
        if (trigger_edit_page_algorithm_fader:get_value() == 3) then
          tooltip:show("Length - " .. trigger_edit_page_pattern2_fader:get_value() .. " selected")
        else
          tooltip:show("Pattern 2 - " .. trigger_edit_page_pattern2_fader:get_value() .. " selected")
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      trigger_edit_page_algorithm_fader:press(x, y)
      if trigger_edit_page_algorithm_fader:is_this(x, y) then
        trigger_edit_page.refresh_trigger_edit_page_ui()
        tooltip:show(get_algorithm_name(trigger_edit_page_algorithm_fader:get_value()) .. " selected")
        load_paint_pattern()
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      local algorithm = trigger_edit_page_algorithm_fader:get_value()
      if trigger_edit_page_bankmask_fader:is_this(x, y) and algorithm ~= 3 then
        trigger_edit_page_bankmask_fader:press(x, y)
        load_paint_pattern()
        tooltip:show(get_bank_name(trigger_edit_page_bankmask_fader:get_value()) .. " selected")
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      trigger_edit_page_paint_button:press(x, y)

      if trigger_edit_page_paint_button:is_this(x, y) then
        if (trigger_edit_page_paint_button:get_state() == 2) then
          trigger_edit_page_cancel_button:set_state(2)
          trigger_edit_page_left_button:set_state(2)
          trigger_edit_page_centre_button:set_state(2)
          trigger_edit_page_right_button:set_state(2)
          load_paint_pattern()
          trigger_edit_page_paint_button:blink()
          tooltip:show("Painting pattern")
        else
          trigger_edit_page_left_button:set_state(1)
          trigger_edit_page_centre_button:set_state(1)
          trigger_edit_page_right_button:set_state(1)
          trigger_edit_page_cancel_button:set_state(1)
          trigger_edit_page_sequencer:hide_unsaved_grid()
          save_paint_pattern(paint_pattern)
          trigger_edit_page_paint_button:no_blink()
          tooltip:show("Pattern painted")
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      trigger_edit_page_cancel_button:press(x, y)

      if trigger_edit_page_cancel_button:is_this(x, y) then
        if (trigger_edit_page_paint_button:get_state() == 2) then
          trigger_edit_page_sequencer:hide_unsaved_grid()
          trigger_edit_page_paint_button:set_state(1)
          trigger_edit_page_paint_button:no_blink()
          trigger_edit_page_cancel_button:no_blink()
          trigger_edit_page_left_button:set_state(1)
          trigger_edit_page_centre_button:set_state(1)
          trigger_edit_page_right_button:set_state(1)
          tooltip:show("Painting cancelled")
        else
          trigger_edit_page_cancel_button:set_state(1)
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_left_button:is_this(x, y) then
        if (trigger_edit_page_left_button:get_state() == 2) then
          shift = shift - 1

          load_paint_pattern()
          trigger_edit_page_left_button:set_state(2)
          tooltip:show("Shifting left")
        else
          trigger_edit_page_left_button:set_state(1)
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_centre_button:is_this(x, y) then
        if (trigger_edit_page_centre_button:get_state() == 2) then
          shift = 0
          load_paint_pattern()
          trigger_edit_page_centre_button:set_state(2)
          tooltip:show("Shift reset")
        else
          trigger_edit_page_centre_button:set_state(1)
        end
      end
    end
  )
  press:register(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_right_button:is_this(x, y) then
        if (trigger_edit_page_right_button:get_state() == 2) then
          shift = shift + 1

          trigger_edit_page_right_button:set_state(2)
          load_paint_pattern()
          tooltip:show("Shifting right")
        else
          trigger_edit_page_right_button:set_state(1)
        end
      end
    end
  )
  press:register_dual(
    "trigger_edit_page",
    function(x, y, x2, y2)
      trigger_edit_page_sequencer:dual_press(x, y, x2, y2)
      if trigger_edit_page_sequencer:is_this(x2, y2) then
        pattern.update_working_patterns()
        tooltip:show("Note length set")
      end
    end
  )
  press:register_long(
    "trigger_edit_page",
    function(x, y)
      if trigger_edit_page_sequencer:is_this(x, y) then
        trigger_edit_page_sequencer:long_press(x, y)
        pattern.update_working_patterns()
        tooltip:show("Note length reset")
      end
    end
  )
end

function trigger_edit_page.refresh_trigger_edit_page_ui()
  local algorithm = trigger_edit_page_algorithm_fader:get_value()

  if (algorithm == 1) then
    trigger_edit_page_bankmask_fader:enabled()
    trigger_edit_page_bankmask_fader:set_size(5)
    trigger_edit_page_bankmask_fader:set_length(5)
    trigger_edit_page_pattern1_fader:set_size(128)
    trigger_edit_page_pattern2_fader:set_size(128)
    trigger_edit_page_pattern2_fader:disabled()
  elseif (algorithm == 2) then
    trigger_edit_page_bankmask_fader:enabled()
    trigger_edit_page_bankmask_fader:set_size(5)
    trigger_edit_page_bankmask_fader:set_length(5)
    trigger_edit_page_pattern1_fader:set_size(128)
    trigger_edit_page_pattern2_fader:set_size(128)
    trigger_edit_page_pattern2_fader:enabled()
  elseif (algorithm == 3) then
    trigger_edit_page_bankmask_fader:disabled()
    trigger_edit_page_bankmask_fader:set_size(5)
    trigger_edit_page_bankmask_fader:set_length(5)
    trigger_edit_page_pattern2_fader:enabled()
    trigger_edit_page_pattern1_fader:set_size(32)
    trigger_edit_page_pattern2_fader:set_size(32)
  elseif (algorithm == 4) then
    trigger_edit_page_bankmask_fader:enabled()
    trigger_edit_page_bankmask_fader:set_size(4)
    trigger_edit_page_bankmask_fader:set_length(4)
    trigger_edit_page_pattern1_fader:set_size(32)
    trigger_edit_page_pattern2_fader:set_size(16)
    trigger_edit_page_pattern2_fader:enabled()
  end

  trigger_edit_page_pattern_select_fader:set_value(program.get().selected_pattern)

  fn.dirty_grid(true)
end

function trigger_edit_page.refresh()
  trigger_edit_page.refresh_trigger_edit_page_ui()
end

return trigger_edit_page

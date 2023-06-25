grid_controller = {}

local Fader = include("sinfcommand/lib/controls/Fader")
local Sequencer = include("sinfcommand/lib/controls/Sequencer")
local Button = include("sinfcommand/lib/controls/Button")

local er = require("er")

local drum_ops = include("sinfcommand/lib/drum_ops")
local draw_handler = include("sinfcommand/lib/draw_handler")
local press_handler = include("sinfcommand/lib/press_handler")

local paint_pattern = {}
local shift = 0

g = grid.connect()

pages = {
  channel_edit_page = 1,
  channel_sequencer_page = 2,
  pattern_trigger_edit_page = 3,
  pattern_note_edit_page = 4,
  pattern_velocity_edit_page = 5,
  pattern_probability_edit_page = 6
}

function register_draw_handlers()
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_pattern_select_fader:draw() end)
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_sequencer:draw() end)
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_pattern1_fader:draw() end)
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_pattern2_fader:draw() end)
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_algorithm_fader:draw() end)
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_bankmask_fader:draw() end)
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_paint_button:draw() end)
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_cancel_button:draw() end)
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_left_button:draw() end)
  draw_handler:register("pattern_trigger_edit_page", function() return pattern_trigger_edit_page_right_button:draw() end)
end

function update_pattern_trigger_edit_page_ui()
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
            if #paint_pattern >= 64 then break end
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


function register_press_handlers()
  press_handler:register("pattern_trigger_edit_page", function(x, y) 
    local result = pattern_trigger_edit_page_pattern_select_fader:press(x, y) 
    program.selected_pattern = pattern_trigger_edit_page_pattern_select_fader:get_value()
    return result
  end)
  press_handler:register("pattern_trigger_edit_page", function(x, y) return pattern_trigger_edit_page_sequencer:press(x, y) end)
  press_handler:register("pattern_trigger_edit_page", function(x, y) 
    load_paint_pattern()
    pattern_trigger_edit_page_pattern1_fader:press(x, y)
    return true 
  end)
  press_handler:register("pattern_trigger_edit_page", function(x, y) 
    load_paint_pattern()
    pattern_trigger_edit_page_pattern2_fader:press(x, y)
    return true 
  end)
  press_handler:register("pattern_trigger_edit_page", function(x, y) 
    pattern_trigger_edit_page_algorithm_fader:press(x, y) 
    if pattern_trigger_edit_page_algorithm_fader:is_this(x, y) then
      update_pattern_trigger_edit_page_ui()
    end
    load_paint_pattern()
    return true
  end)
  press_handler:register("pattern_trigger_edit_page", function(x, y) 
    pattern_trigger_edit_page_bankmask_fader:press(x, y) 
    load_paint_pattern()
    return true
  end)
  press_handler:register("pattern_trigger_edit_page", function(x, y) 
    pattern_trigger_edit_page_paint_button:press(x, y)

    if pattern_trigger_edit_page_paint_button:is_this(x, y) then
      if (pattern_trigger_edit_page_paint_button:get_state() == 2) then
      pattern_trigger_edit_page_cancel_button:set_state(2)
        pattern_trigger_edit_page_left_button:set_state(2)
        pattern_trigger_edit_page_right_button:set_state(2)
        load_paint_pattern()
        pattern_trigger_edit_page_paint_button:blink()
      else
        pattern_trigger_edit_page_left_button:set_state(1)
        pattern_trigger_edit_page_right_button:set_state(1)
        pattern_trigger_edit_page_cancel_button:set_state(1)
        pattern_trigger_edit_page_sequencer:hide_unsaved_grid()
        save_paint_pattern(paint_pattern)
        pattern_trigger_edit_page_paint_button:no_blink()
      end
    end
    return true
  end)
  press_handler:register("pattern_trigger_edit_page", function(x, y) 
    pattern_trigger_edit_page_cancel_button:press(x, y)

    if pattern_trigger_edit_page_cancel_button:is_this(x, y) then
      if (pattern_trigger_edit_page_paint_button:get_state() == 2) then
        pattern_trigger_edit_page_sequencer:hide_unsaved_grid()
        pattern_trigger_edit_page_paint_button:set_state(1)
        pattern_trigger_edit_page_paint_button:no_blink()
        pattern_trigger_edit_page_cancel_button:no_blink()
        pattern_trigger_edit_page_left_button:set_state(1)
        pattern_trigger_edit_page_right_button:set_state(1)
      else
        pattern_trigger_edit_page_cancel_button:set_state(1)
      end
    end

    return true
  end)
  press_handler:register("pattern_trigger_edit_page", function(x, y) 
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
  end)
  press_handler:register("pattern_trigger_edit_page", function(x, y) 
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
  end)
end

function grid_controller.init()
  grid_controller.counter = {}
  grid_controller.toggled = {}
  grid_controller.disconnect_dismissed = true
  for x = 1, 16 do
    grid_controller.counter[x] = {}
    for y = 1, 8 do
      grid_controller.counter[x][y] = nil
    end
  end
  
  pattern_trigger_edit_page_pattern_select_fader = Fader:new(1, 1, 16, 16)
  pattern_trigger_edit_page_pattern_select_fader:set_value(program.selected_pattern)

  pattern_trigger_edit_page_sequencer = Sequencer:new(4)
  pattern_trigger_edit_page_pattern1_fader = Fader:new(1, 2, 10, 100)
  pattern_trigger_edit_page_pattern2_fader = Fader:new(1, 3, 10, 100)
  pattern_trigger_edit_page_algorithm_fader = Fader:new(12, 2, 4, 4)
  pattern_trigger_edit_page_bankmask_fader = Fader:new(12, 3, 5, 5)
  pattern_trigger_edit_page_paint_button = Button:new(16, 8, {{"Inactive", 3}, {"Save", 15}})
  pattern_trigger_edit_page_cancel_button = Button:new(14, 8, {{"Inactive", 3}, {"Cancel", 15}})
  pattern_trigger_edit_page_left_button = Button:new(11, 8, {{"Inactive", 3}, {"Shift Left", 15}})
  pattern_trigger_edit_page_right_button = Button:new(12, 8, {{"Inactive", 3}, {"Shift Right", 15}})

  update_pattern_trigger_edit_page_ui()
  register_draw_handlers()
  register_press_handlers()

end



-- little g

function g.key(x, y, z)
  if z == 1 then
    grid_controller.counter[x][y] = clock.run(grid_controller.grid_long_press, g, x, y)
  elseif z == 0 then -- otherwise, if a grid key is released...
    if grid_controller.counter[x][y] then -- and the long press is still waiting...
      clock.cancel(grid_controller.counter[x][y]) -- then cancel the long press clock,
      grid_controller:short_press(x,y) -- and execute a short press instead.
    end
  end
end



function grid_controller:short_press(x, y)
  press_handler:handle(program.selected_page, x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function g.remove()
  grid_controller:alert_disconnect()
end

function grid_controller:alert_disconnect()
  self.disconnect_dismissed = false
end

function grid_controller:dismiss_disconnect()
  self.disconnect_dismissed = true
end

function grid_draw_menu(selected_page)

  for i = 1, 6 do
    g:led(i, 8, 2)
  end

  if pages[selected_page] then
    g:led(pages[selected_page], 8, 15)
  end
  
  fn.dirty_grid(true)

end

function calc_grid_count(x, y)
  return ((y - 4) * 16) + x
end


function grid_controller:grid_redraw()
  g:all(0)

  grid_draw_menu(program.selected_page)
  draw_handler:handle(program.selected_page)

  g:refresh()
end

function grid_controller:grid_long_press(x, y)
  clock.sleep(.5)

  fn.dirty_grid(true)
end

function grid_controller.grid_redraw_clock()
  while true do
    clock.sleep(1 / 30)
    if fn.dirty_grid() == true then
      grid_controller:grid_redraw()
      fn.dirty_grid(false)
    end
  end
end

return grid_controller

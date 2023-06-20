_grid = {}

local Fader = include("sinfcommand/lib/controls/Fader")
local Sequencer = include("sinfcommand/lib/controls/Sequencer")
local Button = include("sinfcommand/lib/controls/Button")


local drum_ops = include("sinfcommand/lib/drum_ops")
local _draw_handler = include("sinfcommand/lib/_draw_handler")
local _press_handler = include("sinfcommand/lib/_press_handler")


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
  _draw_handler:register("pattern_trigger_edit_page", function() return _pattern_trigger_edit_page_pattern_select_fader:draw() end)
  _draw_handler:register("pattern_trigger_edit_page", function() return _pattern_trigger_edit_page_sequencer:draw() end)
  _draw_handler:register("pattern_trigger_edit_page", function() return _pattern_trigger_edit_page_pattern1_fader:draw() end)
  _draw_handler:register("pattern_trigger_edit_page", function() return _pattern_trigger_edit_page_pattern2_fader:draw() end)
  _draw_handler:register("pattern_trigger_edit_page", function() return _pattern_trigger_edit_page_algorithm_fader:draw() end)
  _draw_handler:register("pattern_trigger_edit_page", function() return _pattern_trigger_edit_page_bankmask_fader:draw() end)
  _draw_handler:register("pattern_trigger_edit_page", function() return _pattern_trigger_edit_page_paint_button:draw() end)
end

function register_press_handlers()
  _press_handler:register("pattern_trigger_edit_page", function(x, y) 
    local result = _pattern_trigger_edit_page_pattern_select_fader:press(x, y) 
    program.selected_pattern = _pattern_trigger_edit_page_pattern_select_fader:get_value()
    return result
  end)
  _press_handler:register("pattern_trigger_edit_page", function(x, y) return _pattern_trigger_edit_page_sequencer:press(x, y) end)
  _press_handler:register("pattern_trigger_edit_page", function(x, y) return _pattern_trigger_edit_page_pattern1_fader:press(x, y) end)
  _press_handler:register("pattern_trigger_edit_page", function(x, y) return _pattern_trigger_edit_page_pattern2_fader:press(x, y) end)
  _press_handler:register("pattern_trigger_edit_page", function(x, y) return _pattern_trigger_edit_page_algorithm_fader:press(x, y) end)
  _press_handler:register("pattern_trigger_edit_page", function(x, y) return _pattern_trigger_edit_page_bankmask_fader:press(x, y) end)
  _press_handler:register("pattern_trigger_edit_page", function(x, y) 
    paint_pattern = {}
    for step = 1, 64 do
      table.insert(paint_pattern, drum_ops.drum(1, 50, step))
    end
    
    return _pattern_trigger_edit_page_paint_button:press(x, y)
  end)
end

function _grid.init()
  _grid.counter = {}
  _grid.toggled = {}
  _grid.disconnect_dismissed = true
  for x = 1, 16 do
    _grid.counter[x] = {}
    for y = 1, 8 do
      _grid.counter[x][y] = nil
    end
  end
  
  _pattern_trigger_edit_page_pattern_select_fader = Fader:new(1, 1, 16, 16)
  _pattern_trigger_edit_page_pattern_select_fader:set_value(program.selected_pattern)

  _pattern_trigger_edit_page_sequencer = Sequencer:new(4)
  _pattern_trigger_edit_page_pattern1_fader = Fader:new(1, 2, 10, 100)
  _pattern_trigger_edit_page_pattern2_fader = Fader:new(1, 3, 10, 100)
  _pattern_trigger_edit_page_algorithm_fader = Fader:new(12, 2, 5, 5)
  _pattern_trigger_edit_page_bankmask_fader = Fader:new(12, 3, 5, 5)
  _pattern_trigger_edit_page_paint_button = Button:new(16, 8)
  
  register_draw_handlers()
  register_press_handlers()

end



-- little g

function g.key(x, y, z)
  if z == 1 then
    _grid.counter[x][y] = clock.run(_grid.grid_long_press, g, x, y)
  elseif z == 0 then -- otherwise, if a grid key is released...
    if _grid.counter[x][y] then -- and the long press is still waiting...
      clock.cancel(_grid.counter[x][y]) -- then cancel the long press clock,
      _grid:short_press(x,y) -- and execute a short press instead.
    end
  end
end



function _grid:short_press(x, y)
  _press_handler:handle(program.selected_page, x, y)
  fn.dirty_grid(true)
  fn.dirty_screen(true)
end

function g.remove()
  _grid:alert_disconnect()
end

function _grid:alert_disconnect()
  self.disconnect_dismissed = false
end

function _grid:dismiss_disconnect()
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


function _grid:grid_redraw()
  g:all(0)

  grid_draw_menu(program.selected_page)
  _draw_handler:handle(program.selected_page)

  g:refresh()
end

function _grid:grid_long_press(x, y)
  clock.sleep(.5)

  fn.dirty_grid(true)
end

function _grid.grid_redraw_clock()
  while true do
    clock.sleep(1 / 30)
    if fn.dirty_grid() == true then
      _grid:grid_redraw()
      fn.dirty_grid(false)
    end
  end
end

return _grid

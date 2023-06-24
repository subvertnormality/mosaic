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

function update_pattern_trigger_edit_page_ui()
  local algorithm = _pattern_trigger_edit_page_algorithm_fader:get_value()

  if (algorithm == 1) then
    _pattern_trigger_edit_page_bankmask_fader:set_length(5)
    _pattern_trigger_edit_page_pattern2_fader:disabled()
  elseif (algorithm == 2) then
    _pattern_trigger_edit_page_bankmask_fader:set_length(5)
    _pattern_trigger_edit_page_pattern2_fader:enabled()
  elseif (algorithm == 3) then
    _pattern_trigger_edit_page_bankmask_fader:set_length(5)
    _pattern_trigger_edit_page_pattern2_fader:disabled()
  elseif (algorithm == 4) then
    _pattern_trigger_edit_page_bankmask_fader:set_length(5)
    _pattern_trigger_edit_page_pattern2_fader:disabled()
  
  end
  fn.dirty_grid(true)
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
  _press_handler:register("pattern_trigger_edit_page", function(x, y) 
    _pattern_trigger_edit_page_algorithm_fader:press(x, y) 
    if _pattern_trigger_edit_page_algorithm_fader:is_this(x, y) then
      update_pattern_trigger_edit_page_ui()
    end
    return true
  end)
  _press_handler:register("pattern_trigger_edit_page", function(x, y) return _pattern_trigger_edit_page_bankmask_fader:press(x, y) end)
  _press_handler:register("pattern_trigger_edit_page", function(x, y) 
    _pattern_trigger_edit_page_paint_button:press(x, y)

    if _pattern_trigger_edit_page_paint_button:is_this(x, y) then
      if (_pattern_trigger_edit_page_paint_button:get_state() == 2) then

        paint_pattern = {}
        local algorithm = _pattern_trigger_edit_page_algorithm_fader:get_value()
        local pattern1 = _pattern_trigger_edit_page_pattern1_fader:get_value()
        local pattern2 = _pattern_trigger_edit_page_pattern2_fader:get_value()
        local bank = _pattern_trigger_edit_page_bankmask_fader:get_value()

        for step = 1, 64 do
          if (algorithm == 1) then
            table.insert(paint_pattern, drum_ops.drum(bank, pattern1, step))
          elseif (algorithm == 2) then
            table.insert(paint_pattern, drum_ops.tresillo(bank, pattern1, pattern2, 8, step)) -- TODO need to make the tressilo length editable
          elseif (algorithm == 3) then
            -- TODO Euclid
          elseif (algorithm == 4) then
            -- TODO NR
          end
        end
        -- for key, value in pairs(paint_pattern) do
        --   print(key, value)
        -- end
        _pattern_trigger_edit_page_paint_button:blink()
      else
        _pattern_trigger_edit_page_paint_button:no_blink()
      end
    end
    return true
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
  _pattern_trigger_edit_page_paint_button = Button:new(16, 8, {{"Inactive", 3}, {"Save", 15}})
  update_pattern_trigger_edit_page_ui()
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

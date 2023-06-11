_grid = {}
g = grid.connect()

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

function _grid:grid_draw_menu(selected_page)
  
  local pages = {
    channel_edit_page = 1,
    channel_sequencer_page = 2,
    pattern_trigger_edit_page = 3,
    pattern_note_edit_page = 4,
    pattern_velocity_edit_page = 5,
    pattern_probability_edit_page = 6
  }

  for i = 1, 6 do
    g:led(i, 8, 2)
  end

  if pages[selected_page] then
    g:led(pages[selected_page], 8, 7)
  end
  
  fn.dirty_grid(true)

end

function _grid:grid_draw_sequencer_visualisation(trigs, lengths)

  local length = -1
  local grid_count = -1

  for y = 4, 7 do
    for x = 1, 16 do
      g:led(x, y, 2)
    end
  end

  for y = 4, 7 do
    for x = 1, 16 do    
      grid_count = ((y - 4) * 16) + x
    
      if (trigs[grid_count] > 0) then
        g:led(x, y, 15)
        length = lengths[grid_count]
        
        if (length > 1) then
          for lx = grid_count + 1, grid_count + length - 1 do
            if (trigs[lx] < 1 and lx < 65) then
              g:led((lx % 16), 4 + (lx // 16), 5)
            else
              break
            end
          end
        end
      end
    end
  end

  fn.dirty_grid(true)

end


function _grid:grid_redraw()
  g:all(0)

  _grid:grid_draw_menu(program.selected_page)
  _grid:grid_draw_sequencer_visualisation(program.sequencer_patterns[1].patterns[1].trig_values, program.sequencer_patterns[1].patterns[1].lengths)

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

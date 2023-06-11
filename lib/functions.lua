fn = {}

function fn.init()
  fn.id_prefix = "sinf-"
  fn.id_counter = 1000
end


function fn.cleanup()
  _midi:all_off()
  g.cleanup()
  clock.cancel(redraw_clock_id)
  clock.cancel(grid_clock_id)

end


function fn.dirty_grid(bool)
  if bool == nil then return grid_dirty end
  grid_dirty = bool
  return grid_dirty
end

function fn.dirty_screen(bool)
  if bool == nil then return screen_dirty end
  screen_dirty = bool
  return screen_dirty
end

return fn
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

function fn.table_to_string(tbl)
    local result = "{"
    for k, v in pairs(tbl) do
        -- serialize the key
        if type(k) == "string" then
            result = result .. "[\"" .. k .. "\"]" .. "="
        else
            result = result .. "[" .. k .. "]" .. "="
        end
        -- serialize the value
        if type(v) == "table" then
            result = result .. fn.table_to_string(v) .. ","
        else
            if type(v) == "string" then
            result = result .. "\"" .. v .. "\"" .. ","
            else
            result = result .. v .. ","
            end
        end
    end
    result = result .. "}"
    return result
end

function fn.string_to_table(str)
    return load("return " .. str)()
end

function fn.shift_table_left(t)
  local first_val = table.remove(t, 1)
  table.insert(t, first_val)

  return t
end

function fn.shift_table_right(t)
  local last_val = table.remove(t)
  table.insert(t, 1, last_val)

  return t
end

return fn
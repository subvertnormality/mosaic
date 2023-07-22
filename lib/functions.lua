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

function fn.find_key(tbl, value)
  for k, v in pairs(tbl) do
    if v == value then
      return k
    end
  end
  return nil
end

function fn.scale(num, old_min, old_max, new_min, new_max)
  return ((num - old_min) / (old_max - old_min)) * (new_max - new_min) + new_min
end

function fn.add_to_set(set, value)
  set[value] = true
end

function fn.is_in_set(set, value)
  return set[value] ~= nil
end

function fn.remove_from_set(set, value)
  set[value] = nil
end

function fn.value_from_note(note)
  return 14 - note
end

function fn.note_from_value(val)
  return 14 - val
end

function fn.initialise_64_table(d)
  local table_64 = {}
  for i=1,64 do
    table_64[i] = d
  end
  return table_64
end

function fn.initialise_default_trig_lock_banks()
  local trig_lock_banks = {}
  for i=1,8 do
    trig_lock_banks[i] = fn.initialise_64_table(-1)
  end
  return trig_lock_banks
end

function fn.initialise_default_channels()
  
  local channels = {}
  
  for i=1,16 do
    channels[i] = {
      trig_lock_banks = fn.initialise_default_trig_lock_banks(),
      working_pattern = {
        trig_values = fn.initialise_64_table(0),
        lengths = fn.initialise_64_table(1),
        note_values = fn.initialise_64_table(0),
        velocity_values = fn.initialise_64_table(100)
      },
      start_trig = {1, 4},
      end_trig = {16, 7},
      midi_channel = i,
      midi_device = 1,
      selected_patterns = {},
      default_scale = -1,
      root_note = -1,
      chord = -1,
      step_scales = fn.initialise_64_table(0),
      merge_mode = "skip",
      octave = 0,
      clock_division = 1,
      current_step = 1,
      trig_lock_locations = {
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 }
      }
    }
  end
  
  return channels
end

function fn.initialise_default_pattern()
  
  return {
    trig_values = fn.initialise_64_table(0),
    lengths = fn.initialise_64_table(1),
    note_values = fn.initialise_64_table(0),
    velocity_values = fn.initialise_64_table(100)
  }

end

function fn.initialise_default_patterns()
  
  local patterns = {}

  for i=1,16 do
    patterns[i] = fn.initialise_default_pattern()
  end
  
  return patterns
end


function fn.initialise_default_sequencer_patterns()
  
  local sequencer_patterns = {}
  
  for i=1,96 do 
    
    sequencer_patterns[i] = {
      active = false,
      global_pattern_length = 64,
      scale = 0,
      patterns = fn.initialise_default_patterns(),
      channels = fn.initialise_default_channels()
    }
    
  end

  return sequencer_patterns
end

function fn.round(num) 
  return math.floor(num + 0.5)
end

function fn.calc_grid_count(x, y)
  return ((y - 4) * 16) + x
end

function fn.rotate_table_left(t)
  table.insert(t, table.remove(t, 1))
  return t
end

return fn
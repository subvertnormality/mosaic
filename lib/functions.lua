local fn = {}

function fn.cleanup()
  _midi.all_off()
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

function fn.remove_table_by_id(t, target_id)
  local size = #t
  for i = size, 1, -1 do
    if t[i].id == target_id then
      table.remove(t, i)
    end
  end
end

function fn.id_appears_in_table(t, target_id)
  local size = #t
  for i = size, 1, -1 do
    if t[i].id == target_id then
      return true
    end
  end
end

function fn.get_by_id(t, target_id)
  for i=#t, 1, -1 do 
      if t[i].id == target_id then
          return t[i]
      end
  end
end

function fn.get_index_by_id(t, target_id)
  for i=#t, 1, -1 do 
      if t[i].id == target_id then
          return i
      end
  end
end

function fn.table_to_string(tbl)
  local result = {}
  table.insert(result, "{")
  for k, v in pairs(tbl) do
    table.insert(result, (type(k) == "string" and "[\""..k.."\"]=") or ("["..k.."]="))
    table.insert(result, (type(v) == "table" and fn.table_to_string(v) or (type(v) == "string" and "\""..v.."\"" or v)))
    table.insert(result, ",")
  end
  table.insert(result, "}")
  return table.concat(result)
end


function fn.print_table(t, indent)
  indent = indent or ''
  for k, v in pairs(t) do
      if type(v) == 'table' then
          print(indent .. k .. ' :')
          fn.print_table(v, indent .. '  ')
      else
          print(indent .. k .. ' : ' .. tostring(v))
      end
  end
end

function fn.merge_tables(t1, t2)
  for k, v in pairs(t2) do
      t1[k] = v
  end
  return t1
end

function fn.string_to_table(str)
    return load("return " .. str)()
end

function fn.title_case(str)
  return (str:gsub("(%a)([%w_']*)", function(first, rest)
    return first:upper()..rest:lower()
  end))
end

local function split_words(str)
  local words = {}
  for word in str:gmatch("%w+") do
      table.insert(words, word)
  end
  return words
end

function fn.snake_case(str)
  -- Convert any uppercase letter that has a space or start-of-string before it to lowercase
  local temp = str:gsub("(%s?)(%u)", function(space, letter)
    return (space == " " and "_" or "") .. letter:lower()
  end)
  -- Replace spaces with underscores (if any still remain)
  local snake_case = temp:gsub("%s", "_")
  return snake_case
end

function fn.format_first_descriptor(str)

  local words = split_words(str)
  local first_word = words[1]


  local truncated
  -- Remove first vowel if the string has more than 4 characters
  -- and if there is a consonant before the vowel
  if #first_word > 4 then
      truncated = first_word:gsub("([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ])[aeiouAEIOU]", "%1", 1)
  else
      truncated = first_word
  end

  -- Take first 4 characters
  truncated = string.sub(truncated, 1, 4)

  -- Capitalize the string
  local capitalized = string.upper(truncated)

  return capitalized
end



function fn.format_second_descriptor(str)

  local words = split_words(str)
  local second_word = words[2]

  if second_word == nil then
      return ""
  end

  local truncated

  -- Remove first vowel if the string has more than 4 characters
  -- and if there is a consonant before the vowel
  if #second_word > 4 then
      truncated = second_word:gsub("([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ])[aeiouAEIOU]", "%1", 1)
  else
      truncated = second_word
  end

  -- Take first 4 characters
  truncated = string.sub(truncated, 1, 4)

  -- Capitalize the string
  local capitalized = string.upper(truncated)

  return capitalized
end

function fn.deep_copy(original)
  local copy
  if type(original) == 'table' then
      copy = {}
      for original_key, original_value in pairs(original) do
          copy[original_key] = fn.deep_copy(original_value)
      end
      setmetatable(copy, getmetatable(original))
  else -- number, string, boolean, etc
      copy = original
  end
  return copy
end


function fn.table_count(t)
  local count = 0
  for _ in pairs(t) do count = count + 1 end
  return count
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

function fn.find_index_in_table_by_id(table, object)
  for i, o in ipairs(table) do
    if o.id == object.id then
      return i
    end
  end
  return nil
end

function fn.find_index_in_table_by_value(table, object)
  for i, o in ipairs(table) do
    if o.value == object.value then
      return i
    end
  end
  return nil 
end

function fn.find_key(tbl, value)
  for k, v in pairs(tbl) do
    if v == value then
      return k
    end
  end
  return nil
end

function fn.tables_are_equal(t1, t2)
  if fn.table_count(t1) ~= fn.table_count(t2) then return false end
  for k, v in pairs(t1) do
    if v ~= t2[k] then return false end
  end
  for k, v in pairs(t2) do
    if v ~= t1[k] then return false end
  end
  return true
end

function fn.table_contains(table, value)
  for _, v in ipairs(table) do
      if v == value then
          return true
      end
  end
  return false
end

function fn.remove_table_from_table(t, object)
  for i, v in ipairs(t) do
      if fn.tables_are_equal(v, object) then
          table.remove(t, i)
          return
      end
  end
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


function fn.round(num) 
  return math.floor(num + 0.5)
end

function fn.round_to_decimal_places(num, num_decimal_places)
  local mult = 10^(num_decimal_places or 0)
  return math.floor(num * mult + 0.5) / mult
end


function fn.calc_grid_count(x, y)
  return ((y - 4) * 16) + x
end

function fn.rotate_table_left(t)
  -- Create a new table by copying the original table
  local new_table = {table.unpack(t)}
  
  -- Rotate elements of the new table
  local first_item = table.remove(new_table, 1)
  new_table[7] = first_item
  return new_table
end

return fn
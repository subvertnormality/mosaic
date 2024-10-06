local fn = {}

-- Localize functions for performance
local floor = math.floor
local insert, remove, concat = table.insert, table.remove, table.concat
local string_find, string_gsub, string_match, string_sub, string_upper, string_lower = 
    string.find, string.gsub, string.match, string.sub, string.upper, string.lower

function fn.cleanup()
  _midi.all_off()
  g.cleanup()
  clock.cancel(redraw_clock_id)
  clock.cancel(grid_clock_id)
end

function fn.dirty_grid(bool)
  if bool == nil then
    return grid_dirty
  end
  grid_dirty = bool
  return grid_dirty
end

function fn.dirty_screen(bool)
  if bool == nil then
    return screen_dirty
  end
  screen_dirty = bool
  return screen_dirty
end

function fn.remove_table_by_id(t, target_id)
  local n = #t
  for i = n, 1, -1 do
    if t[i].id == target_id then
      remove(t, i)
    end
  end
end

function fn.id_appears_in_table(t, target_id)
  local n = #t
  for i = n, 1, -1 do
    if t[i].id == target_id then
      return true
    end
  end
  return false
end

function fn.appears_in_table(t, target_id)
  local n = #t
  for i = n, 1, -1 do
    if t[i] == target_id then
      return true
    end
  end
  return false
end

function fn.limit_string(str, max_length)
  if #str > max_length then
    return string.sub(str, 1, max_length)
  else
    return str
  end
end

function fn.string_in_table(tbl, target)
  for _, value in ipairs(tbl) do
    if value == target then
      return true
    end
  end
  return false
end

function fn.get_by_id(t, target_id)
  local n = #t
  for i = n, 1, -1 do
    if t[i].id == target_id then
      return t[i]
    end
  end
end

function fn.get_index_by_id(t, target_id)
  local n = #t
  for i = n, 1, -1 do
    if t[i].id == target_id then
      return i
    end
  end
end

function fn.table_to_string(tbl)
  local result = {}
  insert(result, "{")
  for k, v in pairs(tbl) do
    insert(result, (type(k) == "string" and '["' .. k .. '"]=' or "[" .. k .. "]="))
    insert(result, (type(v) == "table" and fn.table_to_string(v) or (type(v) == "string" and '"' .. v .. '"' or v)))
    insert(result, ",")
  end
  insert(result, "}")
  return concat(result)
end

function fn.print_table(t, indent, current_depth, max_depth)
  indent = indent or ""
  current_depth = current_depth or 0
  max_depth = max_depth or 7

  if current_depth > max_depth then
    print(indent .. "...")
    return
  end

  for k, v in pairs(t) do
    if type(v) == "table" then
      print(indent .. k .. " :")
      fn.print_table(v, indent .. "  ", current_depth + 1, max_depth)
    else
      print(indent .. k .. " : " .. tostring(v))
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
  return string_gsub(str, "(%a)([%w_']*)", function(first, rest) return string_upper(first) .. string_lower(rest) end)
end

local function split_words(str)
  local words = {}
  for word in str:gmatch("%w+") do
    insert(words, word)
  end
  return words
end

function fn.snake_case(str)
  return string_gsub(str, "(%s?)(%u)", function(space, letter) return (space == " " and "_" or "") .. string_lower(letter) end):gsub("%s", "_")
end

local function truncate_word(word)
  if #word > 4 then
    return string_gsub(word, "([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ])[aeiouAEIOU]", "%1", 1):sub(1, 4):upper()
  end
  return string_sub(word, 1, 4):upper()
end

function fn.format_first_descriptor(str)
  local words = split_words(str)
  return truncate_word(words[1])
end

function fn.format_second_descriptor(str)
  local words = split_words(str)
  if words[2] then
    return truncate_word(words[2])
  end
  return ""
end

function fn.deep_copy(original, max_depth, current_depth)
  max_depth = max_depth or 7
  current_depth = current_depth or 0

  if current_depth > max_depth then
    return original
  end

  if type(original) == "table" then
    local copy = {}
    for original_key, original_value in pairs(original) do
      copy[original_key] = fn.deep_copy(original_value, max_depth, current_depth + 1)
    end
    setmetatable(copy, getmetatable(original))
    return copy
  end
  return original
end

function fn.table_count(t)
  local count = 0
  for _ in pairs(t) do
    count = count + 1
  end
  return count
end

function fn.shift_table_left(t)
  local first_val = remove(t, 1)
  insert(t, first_val)
  return t
end

function fn.shift_table_right(t)
  local last_val = remove(t)
  insert(t, 1, last_val)
  return t
end

function fn.find_in_table_by_id(t, id)
  for i, o in ipairs(t) do
    if o.id == id then
      return o
    end
  end
  return nil
end

function fn.find_index_in_table_by_value(t, value)
  for i, o in ipairs(t) do
    if o.value == value then
      return i
    end
  end
  return nil
end

function fn.find_index_by_value(t, value)
  for i, o in ipairs(t) do
    if o == value then
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
  if fn.table_count(t1) ~= fn.table_count(t2) then
    return false
  end
  for k, v in pairs(t1) do
    if v ~= t2[k] then
      return false
    end
  end
  for k, v in pairs(t2) do
    if v ~= t1[k] then
      return false
    end
  end
  return true
end

function fn.table_has_one_item(tbl)
  local count = 0
  for _ in pairs(tbl) do
    count = count + 1
    if count > 1 then
      return false
    end
  end
  return count == 1
end

function fn.table_contains(t, value)
  for _, v in ipairs(t) do
    if v == value then
      return true
    end
  end
  return false
end

function fn.remove_table_from_table(t, object)
  for i, v in ipairs(t) do
    if fn.tables_are_equal(v, object) then
      remove(t, i)
      return
    end
  end
end

function fn.filter_by_type(input_table, filter_type)
  local filtered = {}
  for _, item in ipairs(input_table) do
    if item.type == filter_type then
      insert(filtered, item)
    end
  end
  return filtered
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
  return floor(num + 0.5)
end

function fn.round_to_decimal_places(num, num_decimal_places)
  local mult = 10 ^ (num_decimal_places or 0)
  return floor(num * mult + 0.5) / mult
end

function fn.calc_grid_count(x, y)
  return ((y - 4) * 16) + x
end

function fn.rotate_table_left(t)
  local first_item = remove(t, 1)
  local new_table = {table.unpack(t)}
  insert(new_table, first_item)
  return new_table
end

function fn.transform_random_value(n)
  if n < 1 then
    return 0
  else
    local min, max
    if n % 2 == 0 then
      min = -n / 2
      max = n / 2
    else
      min = -(n - 1) / 2
      max = (n + 1) / 2
    end
    return random(min, max)
  end
end

function fn.transform_twos_random_value(n)
  if n < 1 then
    return 0
  else
    local min = -floor(n / 2) * 2
    return random(0, n) * 2 + min
  end
end

function fn.transpose_scale(scale, transpose)
  local transposed = {}
  for i, note in ipairs(scale) do
    insert(transposed, note + transpose)
  end
  return transposed
end

function fn.signed_inv_mod(a, b)
  if b == 0 then
    return 0
  end
  local mod = a % b
  local inv_mod = b - mod
  if a < 0 then
    return -inv_mod
  else
    return inv_mod
  end
end

function fn.constrain(min, max, value)
  if value < min then
    value = min
  elseif value > max then
    value = max
  end
  return value
end

function fn.average_table_values(tbl)
  local sum, count = 0, 0
  for _, value in pairs(tbl) do
    sum = sum + value
    count = count + 1
  end
  if count == 0 then
    return nil
  else
    return floor((sum / count) + 0.5)
  end
end

function fn.string_trim(self)
  return string_match(self, "^%s*(.-)%s*$")
end

function fn.string_split(self, in_split_pattern, out_results)
  if not out_results then
    out_results = {}
  end
  local the_start = 1
  local the_split_start, the_split_end = string_find(self, in_split_pattern, the_start)
  while the_split_start do
    insert(out_results, string_sub(self, the_start, the_split_start - 1))
    the_start = the_split_end + 1
    the_split_start, the_split_end = string_find(self, in_split_pattern, the_start)
  end
  insert(out_results, string_sub(self, the_start))
  return out_results
end


local param_types = {
  "number",
  "option",
  "control",
  "file",
  "taper",
  "trigger",
  "group",
  "text",
  "binary"
}

function fn.get_param_type_from_id(type_id)
  return param_types[type_id]
end

function fn.clean_number(num)
  -- Check if the number is a whole number
  if num == math.floor(num) then
    return math.floor(num)  -- Return as integer if no decimal places
  else
    return math.floor(num * 1000 + 0.5) / 1000  -- Return the original rounded to 0.001
  end
end

return fn

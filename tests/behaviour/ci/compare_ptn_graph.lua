-- Compare decoded norns tabutil .ptn graphs while preserving alias identity.
-- Raw artifact hashes remain in the run manifests and are verified separately.

local function read_project(path)
  local chunk, err = loadfile(path, "t", {})
  assert(chunk, err)
  local pool = chunk()
  assert(type(pool) == "table", "project must return a table pool")
  for _, table_value in ipairs(pool) do
    assert(type(table_value) == "table", "project pool entry must be a table")
    local entries = {}
    for key, child in pairs(table_value) do
      entries[#entries + 1] = {key, child}
    end
    for key in pairs(table_value) do table_value[key] = nil end
    local function resolve(value)
      if type(value) ~= "table" then return value end
      local count, index = 0, nil
      for ref_key, ref_value in pairs(value) do
        count = count + 1
        if ref_key == 1 then index = ref_value end
      end
      assert(count == 1 and type(index) == "number" and index % 1 == 0,
             "invalid serialized table reference marker")
      return assert(pool[index], "invalid serialized table reference")
    end
    for _, entry in ipairs(entries) do
      table_value[resolve(entry[1])] = resolve(entry[2])
    end
  end
  assert(type(pool[1]) == "table", "project root table is missing")
  return pool[1]
end

local function same(a, b, left_to_right, right_to_left, path)
  if type(a) ~= type(b) then return false, path .. ": type mismatch" end
  if type(a) ~= "table" then
    if a == b then return true end
    return false, path .. ": value mismatch"
  end
  if left_to_right[a] or right_to_left[b] then
    if left_to_right[a] == b and right_to_left[b] == a then return true end
    return false, path .. ": reference/alias mismatch"
  end
  left_to_right[a], right_to_left[b] = b, a
  for key, value in pairs(a) do
    if b[key] == nil then return false, path .. ": missing key " .. tostring(key) end
    local equal, reason = same(value, b[key], left_to_right, right_to_left,
                               path .. "." .. tostring(key))
    if not equal then return false, reason end
  end
  for key in pairs(b) do
    if a[key] == nil then return false, path .. ": extra key " .. tostring(key) end
  end
  return true
end

local ok, reason = same(read_project(arg[1]), read_project(arg[2]), {}, {}, "root")
if not ok then
  io.write("different: " .. reason .. "\n")
  os.exit(1)
end
io.write("equal\n")

-- Characterisation oracle: decoded project content, independent of tab.save order.
local source, path = table.unpack(arg)
local tab = dofile(source .. '/lua/lib/tabutil.lua')
local saved = assert(tab.load(path), 'Cannot decode saved project')
local active = {}
local function canonical(value)
  local kind = type(value)
  if kind == 'string' then return 's' .. #value .. ':' .. value end
  if kind == 'number' then
    local format = math.type(value) == 'integer' and '%d' or '%a'
    return 'n' .. string.format(format, value) .. ';'
  end
  if kind == 'boolean' then return value and 'b1' or 'b0' end
  assert(kind == 'table', 'Unsupported saved value: ' .. kind)
  assert(not active[value], 'Cyclic saved table')
  active[value] = true
  local entries = {}
  for key, child in pairs(value) do
    assert(type(key) ~= 'table', 'Unsupported table key')
    entries[#entries + 1] = {canonical(key), canonical(child)}
  end
  table.sort(entries, function(a, b) return a[1] < b[1] end)
  local parts = {'t', tostring(#entries), ':'}
  for _, entry in ipairs(entries) do
    parts[#parts + 1] = entry[1]
    parts[#parts + 1] = entry[2]
  end
  parts[#parts + 1] = ';'
  active[value] = nil
  return table.concat(parts)
end
io.write(canonical(saved))

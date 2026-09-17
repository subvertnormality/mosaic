-- norns shows exactly the number of parameters a group declares, so a group
-- that is one short silently drops its last entry from the menu. Adding
-- "Resend unchanged locks" without raising the count hid "Honour scale
-- transpose" from the MOSAIC page. Pin the declared size to what is added.
local function group_size_and_entries(path, group_id)
  local source = assert(io.open(path, "r")):read("*a")
  local declared = tonumber(source:match('params:add_group%("' .. group_id .. '",%s*"[^"]*",%s*(%d+)%)'))
  local after = source:match('params:add_group%("' .. group_id .. '".-\n(.*)')
  local entries = 0
  for kind in after:gmatch("params:add_(%a+)%(") do
    if kind ~= "group" then entries = entries + 1 end
  end
  return declared, entries
end

function test_mosaic_parameter_group_declares_every_entry_it_holds()
  local declared, entries = group_size_and_entries("../../lib/application_parameters.lua", "mosaic")
  luaunit.assert_not_nil(declared, "MOSAIC group declaration not found")
  luaunit.assert_equals(declared, entries,
    "The MOSAIC group must declare exactly the parameters added after it, or the last ones leave the menu")
end

-- Test isolation for the UI02 adapter tests that load real page UIs.
--
-- isolated(stubs, body) snapshots _G, installs the stub globals, runs body and
-- then restores every changed global and removes every new one, even when the
-- body fails. include() is dofile, so modules loaded inside start fresh.
local isolation = {}

function isolation.isolated(stubs, body)
  local before = {}
  for k, v in pairs(_G) do before[k] = v end
  local dirty_screen, dirty_grid = fn.dirty_screen, fn.dirty_grid
  local ok, err = pcall(function()
    for k, v in pairs(stubs or {}) do _G[k] = v end
    fn.dirty_screen = function() end
    fn.dirty_grid = function() end
    body()
  end)
  fn.dirty_screen, fn.dirty_grid = dirty_screen, dirty_grid
  local keys = {}
  for k in pairs(_G) do keys[#keys + 1] = k end
  for _, k in ipairs(keys) do
    if before[k] == nil then _G[k] = nil end
  end
  for k, v in pairs(before) do
    if rawget(_G, k) ~= v then _G[k] = v end
  end
  if not ok then error(err, 0) end
end

-- A screen that records every text call as "x,y text".
function isolation.screen(log)
  local x, y = 0, 0
  local function put(text) log[#log + 1] = string.format("%s,%s %s", x, y, tostring(text)) end
  return setmetatable({move = function(nx, ny) x, y = nx, ny end, text = put, text_right = put,
    text_center = put, text_trim = put}, {__index = function() return function() end end})
end

return isolation

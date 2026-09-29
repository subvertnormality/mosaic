-- The script, not just the pacer module: init must pace collection and
-- cleanup must hand the automatic collector back to the next script.

-- Any field is a function returning the same stub, so the script's other
-- collaborators accept whatever init and cleanup ask of them.
local function universal_stub()
  local stub
  stub = setmetatable({}, {
    __index = function() return stub end,
    __call = function() return stub end,
  })
  return stub
end

local function load_script(events)
  local pacer_module = {new = function()
    events[#events + 1] = "new"
    return {
      start = function() events[#events + 1] = "start" end,
      stop = function() events[#events + 1] = "stop" end,
    }
  end}
  local env = setmetatable({}, {__index = function(_, key)
    local value = _G[key]
    if value ~= nil then return value end
    return universal_stub()
  end})
  env.include = function(name)
    if name == "mosaic/lib/gc_pacer" then return pacer_module end
    return universal_stub()
  end
  env.require = function() return universal_stub() end
  assert(loadfile("../../mosaic.lua", "t", env))()
  return env
end

function test_script_init_starts_paced_collection()
  local events = {}
  local env = load_script(events)
  -- The rest of init runs against stubs and may stop early; the pacer must
  -- already be running by then.
  pcall(env.init)
  luaunit.assert_equals(events[1], "new")
  luaunit.assert_equals(events[2], "start")
end

function test_script_cleanup_restores_the_automatic_collector_first()
  local events = {}
  local env = load_script(events)
  pcall(env.init)
  local count = #events
  -- Stopping the pacer comes first so a failure later in cleanup cannot
  -- leave the next script with collection stopped.
  pcall(env.cleanup)
  luaunit.assert_equals(events[count + 1], "stop")
end

function test_script_cleanup_without_init_is_safe()
  local events = {}
  local env = load_script(events)
  pcall(env.cleanup)
  for _, event in ipairs(events) do luaunit.assert_not_equals(event, "stop") end
end

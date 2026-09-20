-- The analysis worker host, and the remote endpoint it may be pointed at.
-- The endpoint is text the player types on a norns and it ends up inside a
-- shell command, so what is NOT accepted matters as much as what is.
package.path = './lib/?.lua;' .. package.path
local Host = dofile('lib/rhythm_doctor/analysis_worker_host.lua')

local failures, checks = {}, 0
local function equal(got, want, label)
  checks = checks + 1
  if got ~= want then
    failures[#failures + 1] = string.format("%s: expected %s, got %s", label, tostring(want), tostring(got))
  end
end
local function truthy(value, label) equal(value and true or false, true, label) end

local function host(extra)
  local commands = {}
  local deps = {
    code_root = "/code", runtime_root = "/run",
    execute = function(command) commands[#commands + 1] = command; return true end,
    read_line = function() return nil end,
    transport_factory = function() return {} end,
  }
  for key, value in pairs(extra or {}) do deps[key] = value end
  return Host.new(deps), commands
end

-- Unconfigured: the stock native backend, no remote anything.
do
  local h, commands = host()
  h:open()
  truthy(commands[1]:find("--native-source", 1, true) ~= nil, "a stock install builds the native backend")
  equal(commands[1]:find("rd_remote_backend", 1, true), nil, "no endpoint means no remote backend")
end

-- Configured: the remote backend wraps the local one as its fallback.
do
  local h, commands = host({ remote_endpoint = "http://192.168.1.50:8420" })
  h:open()
  local command = commands[1]
  truthy(command:find("rd_remote_backend", 1, true) ~= nil, "a configured endpoint uses the remote backend")
  truthy(command:find("'http://192.168.1.50:8420'", 1, true) ~= nil, "the endpoint is passed quoted")
  truthy(command:find("--native-source", 1, true) ~= nil, "the native backend is still built, as the fallback")
end

-- An endpoint that is not a plain http(s) URL is refused. The value is typed
-- on a norns and reaches a shell command; a typo must fail visibly rather than
-- become a strange command.
do
  local bad = {
    "", "   ", "ftp://host", "file:///etc/passwd", "192.168.1.50:8420",
    "http://host; rm -rf /", "http://host'\\''", "http://host$(whoami)",
    "http://host`id`", "http://host\nX", "javascript:alert(1)",
    "http://" .. string.rep("h", 300),
  }
  for _, value in ipairs(bad) do
    local h = host({ remote_endpoint = value })
    local transport, problem = h:open()
    equal(transport, nil, "refused: " .. value)
    truthy(problem ~= nil, "a refusal explains itself: " .. value)
  end
end

-- Accepted shapes.
do
  for _, value in ipairs({ "http://host", "https://host", "http://host:8420",
                           "http://192.168.1.50:8420", "https://studio.local:443",
                           "http://host:8420/" }) do
    local h, commands = host({ remote_endpoint = value })
    h:open()
    truthy(commands[1] ~= nil and commands[1]:find("rd_remote_backend", 1, true) ~= nil,
      "accepted: " .. value)
  end
end

-- A bad endpoint must not silently disable analysis altogether: the player
-- still gets gates from the local backend if they mistype a URL.
do
  local h = host({ remote_endpoint = "not a url" })
  local _, problem = h:open()
  truthy(tostring(problem):lower():find("endpoint") ~= nil, "the refusal names the endpoint")
end

if #failures > 0 then io.stderr:write(table.concat(failures, "\n") .. "\n"); os.exit(1) end
print("analysis worker host: " .. checks .. " checks")

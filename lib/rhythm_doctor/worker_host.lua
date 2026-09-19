-- Norns host adapter for the detached native capture worker.  Startup and C
-- compilation happen in a background Python helper; open() only starts it or
-- reads a short status file, so the Lua/grid thread never waits for gcc/JACK.
local Host = {}
Host.__index = Host

local function shell_quote(value)
  assert(type(value) == "string" and not value:find("%z"), "safe shell value required")
  return "'" .. value:gsub("'", "'\\''") .. "'"
end

local function read_line(path)
  local handle = io.open(path, "r")
  if not handle then return nil end
  local value = handle:read("*l"); handle:close()
  return value
end

local function code_root()
  local source = debug.getinfo(1, "S").source
  local directory = source:match("^@(.+)/lib/rhythm_doctor/worker_host%.lua$")
  return directory
end

function Host.new(deps)
  deps = deps or {}
  local root = deps.code_root or code_root()
  local runtime = deps.runtime_root
  assert(type(root) == "string" and root ~= "", "Mosaic code root is required")
  assert(type(runtime) == "string" and runtime:sub(1, 1) == "/", "absolute runtime root is required")
  return setmetatable({ code_root = root, runtime_root = runtime,
    left = deps.left or "system:capture_1", right = deps.right or "system:capture_2",
    execute = deps.execute or os.execute, read_line = deps.read_line or read_line,
    transport_factory = assert(deps.transport_factory, "transport factory is required"),
    launched = false, closed = false }, Host)
end

function Host:open()
  if self.closed then return nil, "worker host closed" end
  if not self.launched then
    self.launched = true
    local launcher = self.code_root .. "/tools/rhythm_doctor/launch_worker.py"
    local source = self.code_root .. "/tools/rhythm_doctor"
    local command = table.concat({ "mkdir -p", shell_quote(self.runtime_root), "&& rm -f", shell_quote(self.runtime_root .. "/cancel"),
      "&& python3", shell_quote(launcher), "--source", shell_quote(source),
      "--runtime", shell_quote(self.runtime_root), "--left", shell_quote(self.left),
      "--right", shell_quote(self.right), ">/dev/null 2>&1 &" }, " ")
    local ok = self.execute(command)
    if ok ~= true and ok ~= 0 then return nil, "worker launcher failed" end
    return nil, "worker starting"
  end
  local problem = self.read_line(self.runtime_root .. "/error")
  if problem then return nil, problem end
  local socket_path = self.read_line(self.runtime_root .. "/socket")
  if socket_path then return self.transport_factory(socket_path) end
  return nil, "worker starting"
end

function Host:close()
  -- Closing the seqpacket transport makes the native worker observe HUP, destroy
  -- its JACK client and remove its exact owned directory.  Never kill by name.
  self.closed = true
  self.execute("mkdir -p " .. shell_quote(self.runtime_root) .. " && : > " .. shell_quote(self.runtime_root .. "/cancel"))
  local pid = self.read_line(self.runtime_root .. "/pid")
  if pid and pid:match("^[0-9]+$") then self.execute("kill " .. pid .. " 2>/dev/null") end
  self.execute("rm -f " .. shell_quote(self.runtime_root .. "/socket") .. " " ..
    shell_quote(self.runtime_root .. "/pid") .. " " .. shell_quote(self.runtime_root .. "/error"))
end

Host.shell_quote = shell_quote
return Host

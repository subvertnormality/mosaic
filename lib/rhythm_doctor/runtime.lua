-- Application-facing ownership bridge for Rhythm Doctor.
--
-- `worker:open()` must be nonblocking and return a transport implementing
-- send/poll; it is intentionally injected because spawning a local helper is
-- host-specific.  `worker:close()` is called only after the native RELEASE
-- acknowledgement has reached the state machine.
local Machine = require("rhythm_doctor.state_machine")
local Controller = require("rhythm_doctor.capture_controller")

local Runtime = {}
Runtime.__index = Runtime

local function result(code, extra)
  extra = extra or {}
  extra.code, extra.ok = code, code == "OK"
  return extra
end

local function valid_transport(value)
  return type(value) == "table" and type(value.send) == "function" and type(value.poll) == "function"
end

-- Worker protocol IDs cannot contain paths. Keep loaded projects distinct while
-- preserving a stable identity when the same .ptn file is loaded again.
local function project_identity(value)
  assert(type(value) == "string" and value ~= "", "project identity is required")
  local hash = 2166136261
  for index = 1, #value do hash = (hash * 16777619 + value:byte(index)) % 4294967296 end
  local readable = value:gsub("[^A-Za-z0-9_-]", "-"):gsub("-+", "-")
  if #readable > 48 then readable = readable:sub(-48) end
  if readable == "" then readable = "project" end
  return readable .. string.format("-%08x", hash)
end
Runtime.project_identity = project_identity

function Runtime.new(deps)
  assert(type(deps) == "table", "dependencies are required")
  assert(type(deps.project_id) == "string" and deps.project_id ~= "", "project_id is required")
  assert(type(deps.worker) == "table" and type(deps.worker.open) == "function", "nonblocking worker.open is required")
  assert(type(deps.now) == "function", "monotonic now is required")
  assert(type(deps.transport_stopped) == "function", "transport_stopped is required")
  local self = setmetatable({ worker = deps.worker, now = deps.now, transport_stopped = deps.transport_stopped,
    on_status = deps.on_status, on_capture_saved = deps.on_capture_saved, on_analysis_ready = deps.on_analysis_ready,
    seconds = deps.seconds or 45, controller = nil, transport = nil, closing = false, worker_closed = false }, Runtime)
  assert(type(self.seconds) == "number" and self.seconds % 1 == 0 and self.seconds >= 1 and self.seconds <= 45,
    "capture seconds must be 1..45")
  self.machine = Machine.new({ project_id = project_identity(deps.project_id),
    on_capture_start = function(mode, token) self:_capture_start(mode, token) end,
    on_analyse = function(token) self:_analyse(token) end,
    on_reanalyse = function(token) self:_analyse(token) end,
    on_cancel = function(token) self:_cancel(token) end,
    on_release = function(token) self:_release(token) end,
    on_state = function(state, token) if self.on_status then self.on_status(state, token) end end,
  })
  return self
end

function Runtime:_status(code, detail)
  if self.on_status then self.on_status(code, detail) end
end

function Runtime:_open()
  if self.controller then return result("OK") end
  if self.closing then return result("SHUTTING_DOWN") end
  local ok, transport, problem = pcall(self.worker.open, self.worker)
  if not ok or not valid_transport(transport) then
    self:_status("CAPTURE_WORKER_UNAVAILABLE", ok and problem or transport)
    return result("WORKER_UNAVAILABLE")
  end
  self.transport = transport
  self.controller = Controller.new({ machine = self.machine, transport = transport, now = self.now,
    transport_stopped = self.transport_stopped, seconds = self.seconds,
    on_status = function(code, detail) self:_status(code, detail) end,
    on_capture_saved = function(asset, token) if self.on_capture_saved then self.on_capture_saved(asset, token) end end,
    on_analysis_ready = function(asset, token) if self.on_analysis_ready then self.on_analysis_ready(asset, token) end end,
  })
  self:_status("CAPTURE_WORKER_READY")
  return result("OK")
end

-- Called when the fifth algorithm becomes visible. It starts only the host
-- helper connection; actual JACK preflight remains owned by begin/Record.
function Runtime:enter()
  return self:_open()
end

function Runtime:start_capture(mode)
  local opened = self:_open()
  if not opened.ok then return opened end
  return self.machine:start_capture(mode, self.transport_stopped() == true)
end

function Runtime:_capture_start(mode, token)
  local started = self.controller and self.controller:begin(mode, token, self.seconds)
  if not started or started.code ~= "PREFLIGHTING" then
    self.machine:capture_failed(token, "CAPTURE_PREFLIGHT_UNAVAILABLE")
  end
end
function Runtime:_analyse(token)
  if self.controller then self.controller:analyse(token) end
end
function Runtime:_cancel(token)
  if self.controller then self.controller:cancel(token) end
end
function Runtime:_release(token)
  if self.controller then self.controller:release(token)
  else self.machine:resources_released(token, self.transport_stopped() == true) end
end

function Runtime:record_action()
  return self.machine:request_record_action(self.transport_stopped() == true)
end
function Runtime:confirm_modal(token, accepted)
  return self.machine:confirm_modal(token, accepted, self.transport_stopped() == true)
end
function Runtime:finish(enough_audio)
  return self.machine:finish_capture(self.transport_stopped() == true, enough_audio == true)
end
function Runtime:transport_started()
  return self.machine:transport_started()
end
function Runtime:transport_stopped_event()
  return self.machine:transport_stopped()
end

-- Project lifecycle calls prepare before replacing program state and calls
-- project_loaded only after the replacement committed successfully.
function Runtime:prepare_project_change(continuation)
  return self.machine:prepare_project_change(continuation)
end
function Runtime:project_loaded(project_id)
  assert(type(project_id) == "string" and project_id ~= "", "project_id is required")
  self.machine:replace_project(project_identity(project_id))
  return result("OK")
end

function Runtime:_close_if_released()
  if not self.closing or not self.machine.resources_are_released or self.worker_closed then return end
  self.worker_closed = true
  if self.transport and type(self.transport.close) == "function" then self.transport:close() end
  if type(self.worker.close) == "function" then self.worker:close() end
  self:_status("CAPTURE_WORKER_CLOSED")
end

-- One controller poll only. A release timeout deliberately does not kill the
-- helper, since pretending a native release succeeded could race a project load.
function Runtime:poll()
  local event = self.controller and self.controller:poll() or result("NO_EVENT")
  self:_close_if_released()
  return event
end

function Runtime:cleanup()
  self.closing = true
  self.machine:cleanup()
  self:_close_if_released()
  return result(self.worker_closed and "CLOSED" or "RELEASING")
end

return Runtime

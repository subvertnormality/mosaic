-- Application-facing ownership bridge for Rhythm Doctor.
--
-- `worker:open()` must be nonblocking and return a transport implementing
-- send/poll; it is intentionally injected because spawning a local helper is
-- host-specific.  `worker:close()` is called only after the native RELEASE
-- acknowledgement has reached the state machine.
local function dependency(name, path)
  if type(include) == "function" then return include(path) end
  return require(name)
end
local Machine = dependency("rhythm_doctor.state_machine", "mosaic/lib/rhythm_doctor/state_machine")
local Controller = dependency("rhythm_doctor.capture_controller", "mosaic/lib/rhythm_doctor/capture_controller")
local AnalysisController = dependency("rhythm_doctor.analysis_controller", "mosaic/lib/rhythm_doctor/analysis_controller")
local Transactions = dependency("rhythm_doctor.paint_transactions", "mosaic/lib/rhythm_doctor/paint_transactions")
local Persistence = dependency("rhythm_doctor.bank_persistence", "mosaic/lib/rhythm_doctor/bank_persistence")
local Bank = dependency("rhythm_doctor.bank", "mosaic/lib/rhythm_doctor/bank")

local Runtime = {}
Runtime.__index = Runtime

local function result(code, extra)
  extra = extra or {}
  extra.code, extra.ok = code, code == "OK"
  return extra
end

local function copy(value)
  if type(value) ~= "table" then return value end
  local out = {}
  for key, item in pairs(value) do out[key] = copy(item) end
  return out
end

local function valid_transport(value)
  return type(value) == "table" and type(value.send) == "function" and type(value.poll) == "function"
end

local function valid_alignment(value)
  return type(value) == "table" and type(value.bpm) == "number" and value.bpm == value.bpm and
    value.bpm >= Bank.MIN_BPM and value.bpm <= Bank.MAX_BPM and type(value.start_beat) == "number" and
    value.start_beat == math.floor(value.start_beat) and type(value.fine_start_ms) == "number" and
    value.fine_start_ms == value.fine_start_ms and value.fine_start_ms ~= math.huge and value.fine_start_ms ~= -math.huge and
    (value.origin_sample == nil or type(value.origin_sample) == "number")
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
  if deps.analysis_transport ~= nil then
    assert(valid_transport(deps.analysis_transport), "nonblocking analysis_transport is required")
  end
  if deps.analysis_worker ~= nil then
    assert(type(deps.analysis_worker) == "table" and type(deps.analysis_worker.open) == "function",
      "nonblocking analysis_worker.open is required")
  end
  assert(not (deps.analysis_transport and deps.analysis_worker), "choose one analysis transport source")
  if deps.paint ~= nil then
    assert(type(deps.paint) == "table", "paint integration must be a table")
    for _, name in ipairs({ "read_source", "write_source", "reproject" }) do
      assert(type(deps.paint[name]) == "function", "paint." .. name .. " is required")
    end
  end
  local self = setmetatable({ worker = deps.worker, now = deps.now, transport_stopped = deps.transport_stopped,
    on_status = deps.on_status, on_capture_saved = deps.on_capture_saved, on_analysis_ready = deps.on_analysis_ready,
    seconds = deps.seconds or 45, controller = nil, transport = nil, closing = false,
    worker_closed = false, enter_requested = false, analysis_transport = deps.analysis_transport,
    analysis_worker = deps.analysis_worker, analysis_worker_closed = false, analysis_controller = nil,
    paint_context = nil, paint_transactions = nil, alignment = nil,
    retry_seconds = deps.retry_seconds or .25, worker_retry_at = 0, analysis_retry_at = 0 }, Runtime)
  assert(type(self.seconds) == "number" and self.seconds % 1 == 0 and self.seconds >= 1 and self.seconds <= 45,
    "capture seconds must be 1..45")
  self.machine = Machine.new({ project_id = project_identity(deps.project_id),
    on_capture_start = function(mode, token) self:_capture_start(mode, token) end,
    on_analyse = function(token) self:_analyse(token) end,
    on_reanalyse = function(token) self:_analyse(token) end,
    on_cancel = function(token) self:_cancel(token) end,
    on_release = function(token) self:_release(token) end,
    on_state = function(state, token) if self.on_status then self.on_status(state, token) end end,
    -- A save asked for during a capture is deferred, not refused: the autosave
    -- timers stop once it is declined, so without this the save is lost until
    -- some later edit primes them again.
    on_deferred_save = function(project_id)
      if deps.on_deferred_save then deps.on_deferred_save(project_id) end
    end,
  })
  if deps.paint then
    self.paint_transactions = Transactions.new({
      context = function() return self.paint_context end,
      bank = function() return self.machine.bank end,
      transport_stopped = self.transport_stopped,
      read_source = deps.paint.read_source,
      write_source = deps.paint.write_source,
      reproject = deps.paint.reproject,
      adapter = deps.paint.adapter,
      journal_limit = deps.paint.journal_limit,
    })
  end
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
    on_analysis_ready = function(asset, token) self:_analysis_ready(asset, token) end,
  })
  if self.analysis_transport then self:_open_analysis_transport(self.analysis_transport) end
  -- Preflight the detached inference worker while the editor becomes visible.
  -- A published capture must not spend its first analysis poll launching Python
  -- or discovering a missing pinned artifact.
  if self.analysis_worker then self:_open_analysis_worker() end
  self:_status("CAPTURE_WORKER_READY")
  return result("OK")
end

function Runtime:_open_analysis_transport(transport)
  if self.analysis_controller then return result("OK") end
  if not valid_transport(transport) then return result("ANALYSIS_WORKER_UNAVAILABLE") end
  self.analysis_transport = transport
  self.analysis_controller = AnalysisController.new({ machine=self.machine, transport=transport,
    on_status=function(code, detail) self:_status(code, detail) end,
    alignment=function() return copy(self.alignment) end })
  self:_status("ANALYSIS_WORKER_READY")
  return result("OK")
end

function Runtime:_open_analysis_worker()
  if self.analysis_controller then return result("OK") end
  if not self.analysis_worker or self.closing then return result("ANALYSIS_WORKER_UNAVAILABLE") end
  local ok, transport, problem = pcall(self.analysis_worker.open, self.analysis_worker)
  if not ok or not valid_transport(transport) then
    self:_status("ANALYSIS_WORKER_UNAVAILABLE", ok and problem or transport)
    return result("ANALYSIS_WORKER_UNAVAILABLE")
  end
  return self:_open_analysis_transport(transport)
end

-- Called when the fifth algorithm becomes visible. It starts only the host
-- helper connection; actual JACK preflight remains owned by begin/Record.
function Runtime:enter()
  self.enter_requested = true
  local value = self:_open()
  local now = self.now()
  self.worker_retry_at, self.analysis_retry_at = now + self.retry_seconds, now + self.retry_seconds
  return value
end

function Runtime:start_capture(mode)
  local opened = self:_open()
  if not opened.ok then return opened end
  return self.machine:start_capture(mode, self.transport_stopped() == true)
end

-- Finish eligibility is observed, not guessed: the capture's elapsed time is
-- compared against the length a bank actually needs at the tempo the detector
-- assumes when it has not measured one. Without this the adapter's progress
-- stayed empty, enough_audio was never true, and K3 Finish could never
-- complete a recording.
function Runtime:capture_progress()
  local needed = Bank.minimum_capture_seconds(Bank.SLOWEST_SUPPORTED_BPM) or 24
  local started = self.capture_acquiring_at
  if not started then
    return { enough_audio = false, captured_seconds = 0, required_seconds = needed }
  end
  local captured = (self.now() or started) - started
  return { enough_audio = captured >= needed, captured_seconds = captured,
           required_seconds = needed }
end

-- The recorder has reported that it is acquiring audio. Only from here does
-- captured time accrue: worker launch and JACK preflight precede it and record
-- nothing.
function Runtime:capture_acquiring()
  self.capture_acquiring_at = self.now()
end

function Runtime:_capture_start(mode, token)
  self.capture_started_at, self.capture_acquiring_at = self.now(), nil
  local started = self.controller and self.controller:begin(mode, token, self.seconds)
  if not started or started.code ~= "PREFLIGHTING" then
    self.machine:capture_failed(token, "CAPTURE_PREFLIGHT_UNAVAILABLE")
  end
end
function Runtime:_analyse(token)
  if self.controller then self.controller:analyse(token) end
end
function Runtime:_analysis_ready(asset, token)
  if not self.analysis_controller and self.analysis_worker then self:_open_analysis_worker() end
  if self.analysis_controller then
    local dispatched = self.analysis_controller:dispatch(asset, token)
    if dispatched.code ~= "DISPATCHED" then
      -- A missing or malformed invocation is terminal evidence, never a reason
      -- to retain the prior ANALYSING label or manufacture a READY bank.
      self.machine:receive_analysis({ project_id=token.project_id, generation=token.generation,
        analysis_revision=token.analysis_revision, error="ANALYSIS_DISPATCH_FAILED" })
      return dispatched
    end
    return result("OK")
  end
  if self.on_analysis_ready then self.on_analysis_ready(asset, token, copy(self.alignment)) end
  return result("OK")
end
function Runtime:_cancel(token)
  if self.controller then self.controller:cancel(token) end
  if self.analysis_controller then self.analysis_controller:cancel(token) end
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
function Runtime:set_window_start(desired_start)
  if self.transport_stopped() ~= true then return result("STOP_SEQUENCER") end
  if self.machine.state ~= Machine.READY or type(self.machine.bank) ~= "table" then return result("NOT_READY") end
  local bank, problem = Bank.with_window_start(self.machine.bank, desired_start)
  if not bank then return problem or result("INVALID_WINDOW_START") end
  self.machine.bank = bank
  return result("WINDOW_MOVED", { window_start = bank.window_start })
end
function Runtime:set_sensitivity(lane, sensitivity)
  if self.transport_stopped() ~= true then return result("STOP_SEQUENCER") end
  if self.machine.state ~= Machine.READY or type(self.machine.bank) ~= "table" then return result("NOT_READY") end
  local bank, problem = Bank.with_sensitivity(self.machine.bank, lane, sensitivity)
  if not bank then return problem or result("INVALID_SENSITIVITY") end
  self.machine.bank = bank
  return result("SENSITIVITY_UPDATED", { lane = lane, sensitivity = sensitivity })
end
function Runtime:apply_alignment(alignment)
  if not valid_alignment(alignment) then return result("INVALID_ALIGNMENT") end
  if self.transport_stopped() ~= true then return result("STOP_SEQUENCER") end
  if self.machine.state ~= Machine.READY then return result("NOT_READY") end
  self.alignment = copy(alignment)
  return self.machine:begin_reanalysis(true)
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
-- project_lifecycle.save_project calls these two unconditionally once a guard
-- is installed, unlike its other guard hooks, which it probes first. The
-- capture state machine owns the actual permission decision; the runtime only
-- forwards, so an active capture still blocks a save from stopping transport
-- or serializing a partial bank.
function Runtime:autosave()
  return self.machine:autosave()
end

function Runtime:manual_save()
  return self.machine:manual_save()
end

function Runtime:project_loaded(project_id)
  assert(type(project_id) == "string" and project_id ~= "", "project_id is required")
  local identity = project_identity(project_id)
  self.machine:replace_project(identity)
  if self.paint_transactions then self.paint_transactions:project_loaded(identity) end
  return result("OK")
end

-- Project lifecycle calls this only after its capture-save gate returns
-- SAVE_NOW.  Active jobs therefore cannot leak a partial bank into tab.save.
function Runtime:serialize_project(data, project_path)
  if type(data) ~= "table" then return result("INVALID_PROJECT") end
  if self.machine.state ~= Machine.READY or not self.machine.bank then
    data.rhythm_doctor = nil
    return result("OK")
  end
  local identity = type(project_path) == "string" and project_identity(project_path) or self.machine.project_id
  local bank = copy(self.machine.bank)
  bank.project_id = identity
  if not Persistence.encode(bank) then return result("INVALID_BANK") end
  self.machine.project_id, self.machine.bank = identity, bank
  if self.paint_transactions then self.paint_transactions:project_loaded(identity) end
  data.rhythm_doctor = assert(Persistence.encode(bank))
  return result("OK")
end

-- The project validator has already rejected unknown/malformed envelopes before
-- model replacement.  Rebinding the saved bank to this project path gives a
-- loaded copy its own generation/identity and prevents cross-project callbacks.
function Runtime:restore_project(data, project_path)
  if type(data) ~= "table" then return result("INVALID_PROJECT") end
  local bank, problem = Persistence.decode(data.rhythm_doctor)
  if not bank and problem and problem.code == "EMPTY" then return result("OK") end
  if not bank then return result(problem and problem.code or "INVALID_BANK") end
  local identity = project_identity(project_path)
  bank.project_id = identity
  local restored = self.machine:restore_ready_bank(bank)
  if restored.ok and self.paint_transactions then self.paint_transactions:project_loaded(identity) end
  return restored
end

-- The UI owns the currently displayed lane/window/policy values.  It passes a
-- fresh immutable-looking context for each operation; keeping it only for the
-- synchronous transaction prevents a delayed preview from following later UI
-- selection changes.
function Runtime:_with_paint_context(context, operation)
  if not self.paint_transactions then return nil, result("PAINT_UNAVAILABLE") end
  if type(context) ~= "table" then return nil, result("INVALID_CONTEXT") end
  self.paint_context = context
  local values = table.pack(operation(self.paint_transactions))
  self.paint_context = nil
  return table.unpack(values, 1, values.n)
end

function Runtime:paint_preview(context, target)
  return self:_with_paint_context(context, function(transactions) return transactions:preview(target) end)
end
function Runtime:paint_commit(context, preview, replace_confirmed)
  return self:_with_paint_context(context, function(transactions) return transactions:commit(preview, replace_confirmed) end)
end
function Runtime:paint_undo(context, target)
  return self:_with_paint_context(context, function(transactions) return transactions:undo(target) end)
end
function Runtime:paint_redo(context, target)
  return self:_with_paint_context(context, function(transactions) return transactions:redo(target) end)
end

function Runtime:_close_if_released()
  if not self.closing or not self.machine.resources_are_released or self.worker_closed then return end
  self.worker_closed = true
  if self.transport and type(self.transport.close) == "function" then self.transport:close() end
  if type(self.worker.close) == "function" then self.worker:close() end
  if self.analysis_worker and not self.analysis_worker_closed and type(self.analysis_worker.close) == "function" then
    self.analysis_worker_closed = true; self.analysis_worker:close()
  end
  self:_status("CAPTURE_WORKER_CLOSED")
end

-- One controller poll only. A release timeout deliberately does not kill the
-- helper, since pretending a native release succeeded could race a project load.
function Runtime:poll()
  local now = self.now()
  if self.enter_requested and not self.controller and not self.closing and now >= self.worker_retry_at then
    self.worker_retry_at = now + self.retry_seconds
    self:_open()
  end
  if self.enter_requested and self.analysis_worker and not self.analysis_controller and not self.closing and now >= self.analysis_retry_at then
    self.analysis_retry_at = now + self.retry_seconds
    self:_open_analysis_worker()
  end
  local event = self.controller and self.controller:poll() or result("NO_EVENT")
  if event.code == "STARTED" then self:capture_acquiring() end
  local analysis_event = self.analysis_controller and self.analysis_controller:poll() or result("NO_EVENT")
  self:_close_if_released()
  return event.code ~= "NO_EVENT" and event or analysis_event
end

function Runtime:cleanup()
  self.closing = true
  self.machine:cleanup()
  self:_close_if_released()
  return result(self.worker_closed and "CLOSED" or "RELEASING")
end

return Runtime

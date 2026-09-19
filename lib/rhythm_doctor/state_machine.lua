-- Job ownership and lifecycle only.  Host capture/worker/save actions are
-- injected callbacks so UI integration can keep this module deterministic.
local Bank = type(include) == "function" and include("mosaic/lib/rhythm_doctor/bank") or require("rhythm_doctor.bank")
local Machine = {
  EMPTY = "EMPTY", LISTENING = "LISTENING", RECORDING = "RECORDING",
  ANALYSING = "ANALYSING", ALIGNMENT_REQUIRED = "ALIGNMENT_REQUIRED",
  READY = "READY", REANALYSING = "REANALYSING", FAILED = "FAILED",
}

local active = { LISTENING = true, RECORDING = true, ANALYSING = true, REANALYSING = true }
local function result(code, extra)
  extra = extra or {}; extra.code = code; extra.ok = code == "OK"; return extra
end
local function invoke(fn, ...)
  if fn then return fn(...) end
end

function Machine.new(deps)
  deps = deps or {}
  assert(type(deps.project_id) == "string" and deps.project_id ~= "", "project_id is required")
  return setmetatable({ project_id = deps.project_id, state = Machine.EMPTY, generation = 0,
    analysis_revision = 0, deps = deps, pending_save = false, pending_project_change = nil, bank = nil, modal = nil,
    modal_nonce = 0, previous_ready = nil, resources_are_released = true, release_token = nil, last_message = nil }, { __index = Machine })
end

function Machine:is_active() return active[self.state] == true end
function Machine:job_token()
  return { project_id = self.project_id, generation = self.generation, analysis_revision = self.analysis_revision }
end
function Machine:_set_state(state)
  self.state = state; invoke(self.deps.on_state, state, self:job_token())
end
function Machine:_request_resource_release(owner_token)
  if self.resources_are_released or self.release_token then return end
  -- This is a nonblocking request.  The host must call resources_released with
  -- this token after input routing/file handles are actually released.
  self.resources_are_released = false
  self.release_token = owner_token or self:job_token()
  invoke(self.deps.on_release, self.release_token)
end
function Machine:_service_project_change()
  local request = self.pending_project_change
  if request and request.ready and self.resources_are_released and not self:is_active() then
    self.pending_project_change = nil
    self.pending_save = false -- requests made while waiting still belong to the old project
    request.callback()
  end
end
function Machine:prepare_project_change(callback)
  assert(type(callback) == "function", "project continuation is required")
  local completed, value = false, nil
  local request = { ready = false, callback = function()
    completed = true
    value = callback()
  end }
  -- Install ownership before cancellation: callbacks may release synchronously.
  -- A newer request/cleanup replaces this table and invalidates this continuation.
  self.pending_project_change = request
  self:_cancel_job(true)
  if self.pending_project_change ~= request then return result("STALE_REQUEST") end
  self.bank, self.previous_ready = nil, nil
  self:_set_state(Machine.EMPTY)
  if self.pending_project_change ~= request then return result("STALE_REQUEST") end
  request.ready = true
  self:_service_project_change()
  return result(completed and "OK" or "DEFERRED", { value = value })
end
-- A correction that ends without a new bank restores the snapshot taken before
-- it began. That snapshot carries the lease it was analysed under, while the
-- machine has since advanced - cancellation bumps the generation as well as the
-- revision. Rebind it, or every identity-checked use of the restored bank,
-- painting above all, fails INVALID_BANK and the abandoned correction quietly
-- bricks the bank. The machine's own identity is never rolled back, so a late
-- result from the abandoned lease is still rejected as stale.
function Machine:_restore_ready_snapshot()
  local restored = self.previous_ready
  if not restored then return nil end
  restored.generation, restored.analysis_revision = self.generation, self.analysis_revision
  self.previous_ready = nil
  return restored
end
function Machine:_service_pending_save(transport_stopped)
  if self.pending_save and not self.pending_project_change and transport_stopped and self.resources_are_released and not self:is_active() then
    self.pending_save = false
    invoke(self.deps.on_deferred_save, self.project_id)
  end
end
function Machine:resources_released(token, transport_stopped)
  local owner = self.release_token
  if not owner or type(token) ~= "table" or token.project_id ~= owner.project_id or token.generation ~= owner.generation or
      token.analysis_revision ~= owner.analysis_revision then return result("STALE_RELEASE") end
  self.resources_are_released, self.release_token = true, nil
  self:_service_project_change()
  self:_service_pending_save(transport_stopped == true)
  return result("OK")
end
function Machine:_invalidate_modal(message)
  self.modal = nil
  if message then self.last_message = message end
end
function Machine:_cancel_job(discard_deferred)
  local old_token = self:job_token()
  self.generation = self.generation + 1
  self:_invalidate_modal()
  -- Invalidate first.  A worker may synchronously invoke its completion callback
  -- while receiving cancellation, and it must see its old token as stale.
  if self:is_active() then invoke(self.deps.on_cancel, old_token) end
  if discard_deferred then self.pending_save = false end
  self:_request_resource_release(old_token)
end

function Machine:start_capture(mode, transport_stopped)
  if self.pending_project_change then return result("PROJECT_CHANGING") end
  if not transport_stopped then return result("STOP_SEQUENCER") end
  if not self.resources_are_released then return result("RESOURCE_RELEASING") end
  if self.state ~= Machine.EMPTY and self.state ~= Machine.FAILED then return result("BUSY") end
  if mode ~= "auto" and mode ~= "manual" then return result("INVALID_MODE") end
  self.generation = self.generation + 1; self.analysis_revision = 0; self.bank = nil
  self.resources_are_released = false; self:_invalidate_modal()
  self:_set_state(mode == "auto" and Machine.LISTENING or Machine.RECORDING)
  invoke(self.deps.on_capture_start, mode, self:job_token())
  return result("OK", self:job_token())
end

local function owns_capture(self, token)
  return type(token) == "table" and token.project_id == self.project_id and
    token.generation == self.generation and token.analysis_revision == self.analysis_revision and
    (self.state == Machine.LISTENING or self.state == Machine.RECORDING)
end

function Machine:capture_failed(token, message)
  if not owns_capture(self, token) then return result("STALE_RESULT") end
  self:_invalidate_modal()
  self.last_message = type(message) == "string" and message ~= "" and message or "CAPTURE_FAILED"
  self:_set_state(Machine.FAILED)
  self:_request_resource_release(token)
  return result("OK")
end

-- Host calls only after the contiguous input buffer has stopped. Audio retention
-- belongs to the host; releasing the capture lease must not discard that asset.
function Machine:capture_timeout(token, valid_span)
  if not owns_capture(self, token) then return result("STALE_RESULT") end
  self:_invalidate_modal()
  if valid_span == true then
    self:_set_state(Machine.ANALYSING)
    if self.state == Machine.ANALYSING and token.project_id == self.project_id and
        token.generation == self.generation and token.analysis_revision == self.analysis_revision then
      invoke(self.deps.on_analyse, token)
    end
  else
    self.last_message = "TEMPO_UNCERTAIN"
    self:_set_state(Machine.ALIGNMENT_REQUIRED)
    self:_request_resource_release(token)
  end
  return result("OK")
end

function Machine:finish_capture(transport_stopped, enough_audio)
  if not transport_stopped then return result("STOP_SEQUENCER") end
  if self.state ~= Machine.LISTENING and self.state ~= Machine.RECORDING and self.state ~= Machine.ALIGNMENT_REQUIRED then return result("NOT_CAPTURING") end
  if enough_audio ~= true then return result("MORE_AUDIO_NEEDED") end
  if self.release_token then return result("RESOURCE_RELEASING") end
  self.resources_are_released = false
  self:_invalidate_modal(); self:_set_state(Machine.ANALYSING)
  invoke(self.deps.on_analyse, self:job_token())
  return result("OK", self:job_token())
end

function Machine:begin_reanalysis(transport_stopped)
  if self.pending_project_change then return result("PROJECT_CHANGING") end
  if not transport_stopped then return result("STOP_SEQUENCER") end
  if not self.resources_are_released then return result("RESOURCE_RELEASING") end
  if self.state ~= Machine.READY then return result("NOT_READY") end
  self.previous_ready = self.bank; self.analysis_revision = self.analysis_revision + 1
  self.resources_are_released = false; self:_invalidate_modal(); self:_set_state(Machine.REANALYSING)
  invoke(self.deps.on_reanalyse, self:job_token())
  return result("OK", self:job_token())
end

function Machine:receive_analysis(response)
  response = response or {}
  if response.project_id ~= self.project_id or response.generation ~= self.generation or response.analysis_revision ~= self.analysis_revision then
    return result("STALE_RESULT")
  end
  if self.state ~= Machine.ANALYSING and self.state ~= Machine.REANALYSING then return result("STALE_RESULT") end
  self:_invalidate_modal()
  if not response.error and not Bank.valid_ready(response.bank, self:job_token()) then response.error = "INVALID_BANK" end
  if response.error then
    if self.state == Machine.REANALYSING and self.previous_ready then
      -- The snapshot was stamped with the lease it was analysed under, but the
      -- machine has moved to the correction's lease. Rebind it, or every
      -- identity-checked use of the restored bank - painting above all - fails
      -- INVALID_BANK and the failed correction quietly bricks the bank. The
      -- revision itself is not rolled back: a late result from the abandoned
      -- lease must still be rejected as stale.
      self.bank = self:_restore_ready_snapshot(); self:_set_state(Machine.READY)
      self.last_message = "CORRECTION_FAILED"
    else
      self:_set_state(Machine.FAILED); self.last_message = response.error
    end
    self:_request_resource_release(); return result(response.error == "INVALID_BANK" and "INVALID_BANK" or "OK")
  end
  self.bank, self.previous_ready = response.bank, nil
  self:_set_state(Machine.READY); self:_request_resource_release()
  return result("OK")
end

function Machine:request_record_action(transport_stopped)
  if not transport_stopped then return result("STOP_SEQUENCER") end
  local operation
  if self.state == Machine.READY or self.state == Machine.ALIGNMENT_REQUIRED then operation = "clear"
  elseif self.state == Machine.LISTENING or self.state == Machine.RECORDING or self.state == Machine.ANALYSING then operation = "cancel_capture"
  elseif self.state == Machine.REANALYSING then operation = "cancel_correction"
  else return result("NO_ACTION") end
  local token = self:job_token()
  self.modal_nonce = self.modal_nonce + 1
  token.operation, token.state, token.nonce = operation, self.state, self.modal_nonce
  self.modal = token
  return token
end

function Machine:confirm_modal(token, accepted, transport_stopped)
  local modal = self.modal
  self.modal = nil
  if not modal or type(token) ~= "table" or token.project_id ~= self.project_id or token.generation ~= self.generation or
      token.analysis_revision ~= self.analysis_revision or token.state ~= self.state or token.operation ~= modal.operation or token.nonce ~= modal.nonce then
    return result("STALE_REQUEST")
  end
  if transport_stopped ~= true then return result("STOP_SEQUENCER") end
  if not accepted then return result("CANCELLED") end
  if token.operation == "clear" then
    self:_cancel_job(false); self.bank = nil; self:_set_state(Machine.EMPTY); self:_service_pending_save(true); return result("OK")
  elseif token.operation == "cancel_correction" then
    self:_cancel_job(false); self.bank = self:_restore_ready_snapshot(); self:_set_state(Machine.READY); self:_service_pending_save(true); return result("OK")
  elseif token.operation == "cancel_capture" then
    self:_cancel_job(false); self.bank = nil; self:_set_state(Machine.EMPTY); self:_service_pending_save(true); return result("OK")
  end
  return result("STALE_REQUEST")
end

function Machine:autosave()
  if self.pending_project_change or self:is_active() or not self.resources_are_released then self.pending_save = true; return result("DEFERRED") end
  return result("SAVE_NOW")
end
function Machine:manual_save()
  if self.pending_project_change or self:is_active() or not self.resources_are_released then return result("CAPTURE_ACTIVE") end
  return result("SAVE_NOW")
end
function Machine:transport_started()
  if self:is_active() then
    local correcting = self.state == Machine.REANALYSING and self.previous_ready ~= nil
    self:_cancel_job(false)
    self.bank, self.previous_ready = correcting and self:_restore_ready_snapshot() or nil, nil
    self:_set_state(self.bank and Machine.READY or Machine.EMPTY)
  else self:_invalidate_modal() end
  return result("OK")
end
function Machine:transport_stopped()
  self:_service_pending_save(true)
  return result("OK")
end
function Machine:replace_project(project_id)
  assert(type(project_id) == "string" and project_id ~= "", "project_id is required")
  self.pending_project_change = nil
  self:_cancel_job(true); self.project_id, self.bank, self.previous_ready = project_id, nil, nil
  self.analysis_revision = 0; self:_set_state(Machine.EMPTY)
end

-- A project file can restore only a fully validated, completed bank.  Workers,
-- release leases, modals and deferred saves never cross that boundary.
function Machine:restore_ready_bank(bank)
  if self:is_active() or not self.resources_are_released or not Bank.valid_ready(bank) then return result("INVALID_BANK") end
  self.generation, self.analysis_revision = bank.generation, bank.analysis_revision
  self.bank, self.previous_ready, self.pending_save, self.pending_project_change = bank, nil, false, nil
  self:_invalidate_modal(); self.last_message = nil; self:_set_state(Machine.READY)
  return result("OK")
end
function Machine:cleanup()
  self.pending_project_change = nil
  self:_cancel_job(true); self.bank, self.previous_ready = nil, nil; self:_set_state(Machine.EMPTY)
end

return Machine

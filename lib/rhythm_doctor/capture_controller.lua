-- Nonblocking host-side capture controller. This module deliberately has no
-- socket, FFI, JACK, or Mosaic UI dependency: a future native bridge is injected.
local Controller = {}
Controller.__index = Controller

local function result(code, extra)
  extra = extra or {}; extra.code, extra.ok = code, code == 'OK'; return extra
end
local function same_token(a, b)
  return type(a) == 'table' and type(b) == 'table' and a.project_id == b.project_id and
    a.generation == b.generation and a.analysis_revision == b.analysis_revision
end
local function same_capture(a, b)
  return type(a) == 'table' and type(b) == 'table' and a.project_id == b.project_id and a.generation == b.generation
end
-- The recorder adopts one identity at PREFLIGHT and compares every later
-- command against it, analysis revision included. A reanalysis advances the
-- analysis lease over the same retained audio, so the two identities diverge:
-- the recorder must keep being addressed as the identity it adopted, or it
-- answers STALE_JOB and never releases its input.
local function recorder_identity(job)
  return job.capture_token or job.token
end
local function same_identity(job, message, version)
  return type(message) == 'table' and message.protocol_version == version and message.job_id == job.job_id and
    same_token(recorder_identity(job), message)
end
local function copy_identity(job, command)
  local owner = recorder_identity(job)
  return { protocol_version = job.protocol_version, job_id = job.job_id, project_id = owner.project_id,
    generation = owner.generation, analysis_revision = owner.analysis_revision, command = command }
end
local function finite_integer(value, minimum, maximum)
  return type(value) == 'number' and value == value and value ~= math.huge and value ~= -math.huge and
    value == math.floor(value) and value >= minimum and value <= maximum
end
local function valid_asset(message)
  local path, hash = message.wav_path, message.wav_sha256
  return type(path) == 'string' and path:sub(1, 1) == '/' and path:match('%.wav$') and not path:find('%z') and
    not path:find('/%.%./') and path:sub(-3) ~= '/..' and type(hash) == 'string' and #hash == 64 and hash:match('^[%x]+$') and
    finite_integer(message.frames, 0, 45 * 192000) and finite_integer(message.sample_rate, 8000, 192000)
end
local terminal_commands = { START = true, STOP = true, POLL = true, EVENT = true }

function Controller.new(deps)
  assert(type(deps) == 'table', 'dependencies are required')
  assert(type(deps.machine) == 'table', 'machine is required')
  assert(type(deps.transport) == 'table' and type(deps.transport.send) == 'function' and type(deps.transport.poll) == 'function', 'nonblocking transport.send and transport.poll are required')
  assert(type(deps.now) == 'function', 'monotonic now is required')
  assert(type(deps.transport_stopped) == 'function', 'transport_stopped is required')
  local self = setmetatable({ machine = deps.machine, transport = deps.transport, now = deps.now, transport_stopped = deps.transport_stopped,
    on_status = deps.on_status, on_capture_saved = deps.on_capture_saved, on_analysis_ready = deps.on_analysis_ready,
    protocol_version = deps.protocol_version or 1, release_timeout_seconds = deps.release_timeout_seconds or 2,
    job_prefix = deps.job_prefix or 'rhythm-doctor', nonce = 0, job = nil }, Controller)
  assert(finite_integer(self.protocol_version, 1, math.huge), 'protocol_version is required')
  assert(type(self.release_timeout_seconds) == 'number' and self.release_timeout_seconds > 0, 'release timeout is required')
  return self
end
function Controller:_status(code, detail) if self.on_status then self.on_status(code, detail) end end
function Controller:_owns(job) return self.job == job and same_token(job.token, self.machine:job_token()) end
function Controller:_capturing(job)
  return self:_owns(job) and (self.machine.state == 'LISTENING' or self.machine.state == 'RECORDING')
end
function Controller:_lookup(token)
  local job = self.job
  return job and same_token(job.token, token) and job or nil
end
function Controller:_send(job, command, extra)
  local message = copy_identity(job, command)
  for key, value in pairs(extra or {}) do message[key] = value end
  local ok, sent, reason = pcall(self.transport.send, self.transport, message)
  if not ok or sent ~= true then
    self:_status('CAPTURE_TRANSPORT_SEND_FAILED', { command = command, reason = ok and reason or sent, token = job.token })
    return nil
  end
  return message
end
function Controller:_fail(job, message)
  if not self:_owns(job) then return result('STALE_JOB') end
  if self.machine.state == 'LISTENING' or self.machine.state == 'RECORDING' then
    self.machine:capture_failed(job.token, message or 'CAPTURE_PROTOCOL_ERROR')
  elseif self.machine.state == 'ANALYSING' then
    self.machine:receive_analysis({ project_id = job.token.project_id, generation = job.token.generation,
      analysis_revision = job.token.analysis_revision, error = message or 'CAPTURE_PROTOCOL_ERROR' })
  else
    return result('STALE_JOB')
  end
  return result('FAILED')
end
function Controller:_protocol_error(job) return self:_fail(job, 'CAPTURE_PROTOCOL_ERROR') end

-- Called by the state-machine on_capture_start callback. It sends one PREFLIGHT
-- request and returns; readiness is received later through poll/receive.
function Controller:begin(mode, token, seconds)
  if mode ~= 'auto' and mode ~= 'manual' then return result('INVALID_MODE') end
  if not finite_integer(seconds, 1, 45) then return result('INVALID_DURATION') end
  if not same_token(token, self.machine:job_token()) then return result('STALE_JOB') end
  self.nonce = self.nonce + 1
  local job = { token = { project_id = token.project_id, generation = token.generation, analysis_revision = token.analysis_revision },
    capture_token = { project_id = token.project_id, generation = token.generation, analysis_revision = token.analysis_revision },
    protocol_version = self.protocol_version, job_id = self.job_prefix .. '-' .. tostring(self.nonce), mode = mode, seconds = seconds,
    phase = 'PREFLIGHTING', started = false, completed = false, publishing = false, analysis_requested = false,
    analysis_dispatched = false, timeout_valid_span = nil, cancel_sent = false, release_sent = false, release_acked = false,
    release_deadline = nil, release_timeout_reported = false }
  self.job = job
  if not self:_send(job, 'PREFLIGHT', { mode = mode, seconds = seconds }) then return self:_fail(job, 'CAPTURE_PREFLIGHT_SEND_FAILED') end
  return result('PREFLIGHTING', { job_id = job.job_id })
end
function Controller:cancel(token)
  local job = self:_lookup(token)
  if not job then return result('STALE_JOB') end
  if job.cancel_sent then return result('CANCEL_PENDING') end
  job.cancel_sent = true
  self:_send(job, 'CANCEL')
  return result('CANCEL_PENDING')
end
function Controller:release(token)
  local job = self:_lookup(token)
  if not job then return result('STALE_RELEASE') end
  -- A corrected alignment can reuse its retained WAV in a later analysis lease.
  -- The machine calls on_release once per lease, even though its token is unchanged.
  if job.release_acked then
    job.release_sent, job.release_acked, job.release_deadline, job.release_timeout_reported = false, false, nil, false
  end
  if job.release_sent then return result('RELEASE_PENDING') end
  job.release_sent, job.release_deadline = true, self.now() + self.release_timeout_seconds
  self:_send(job, 'RELEASE')
  return result('RELEASE_PENDING')
end
function Controller:_publish(job)
  if job.publishing then return result('PUBLISH_PENDING') end
  if not job.completed then return result('NOT_COMPLETED') end
  job.publishing, job.phase = true, 'PUBLISHING'
  if not self:_send(job, 'PUBLISH') then job.publishing = false; return self:_fail(job, 'CAPTURE_PUBLISH_SEND_FAILED') end
  return result('PUBLISHING')
end
-- A PUBLISHED reply is necessary but not an analysis result. The injected
-- callback owns analysis and must explicitly call Machine:receive_analysis later.
function Controller:analyse(token)
  local job = self:_lookup(token)
  -- Reanalysis deliberately keeps the retained WAV but receives a new analysis
  -- revision.  Adopt that lease before dispatching so the analysis controller,
  -- release acknowledgement and all later replies share the new token.
  if not job then
    job = self.job
    if not job or not same_capture(job.token, token) or type(token.analysis_revision) ~= 'number' or
        token.analysis_revision <= job.token.analysis_revision or not job.asset then return result('STALE_JOB') end
    job.token = { project_id = token.project_id, generation = token.generation, analysis_revision = token.analysis_revision }
    job.asset = { wav_path = job.asset.wav_path, wav_sha256 = job.asset.wav_sha256, frames = job.asset.frames,
      sample_rate = job.asset.sample_rate, job_id = job.asset.job_id, project_id = token.project_id,
      generation = token.generation, analysis_revision = token.analysis_revision }
    job.analysis_dispatched, job.analysis_requested = false, false
  end
  if not job or not self:_owns(job) then return result('STALE_JOB') end
  job.analysis_requested = true
  if job.asset then
    if not job.analysis_dispatched and self.on_analysis_ready then job.analysis_dispatched = true; self.on_analysis_ready(job.asset, job.token) end
    return result('ANALYSIS_READY')
  end
  if job.completed then return self:_publish(job) end
  if job.stop_sent then return result('STOP_PENDING') end
  job.stop_sent, job.phase = true, 'STOPPING'
  if not self:_send(job, 'STOP') then return self:_fail(job, 'CAPTURE_STOP_SEND_FAILED') end
  return result('STOPPING')
end
-- Acquisition supplies valid_span; this controller never invents it from C state.
function Controller:timeout(token, valid_span)
  local job = self:_lookup(token)
  if not job or not self:_capturing(job) then return result('STALE_JOB') end
  if type(valid_span) ~= 'boolean' then return result('INVALID_TIMEOUT') end
  if not job.completed then return result('NOT_COMPLETED') end
  job.timeout_valid_span = valid_span
  if job.asset then self.machine:capture_timeout(job.token, valid_span); return result('TIMEOUT_APPLIED') end
  return self:_publish(job)
end
function Controller:_complete(job)
  if not self:_owns(job) then return result('STALE_JOB') end
  if job.phase ~= 'CAPTURING' and job.phase ~= 'STOPPING' then return self:_protocol_error(job) end
  job.completed, job.phase = true, 'COMPLETED'
  if job.analysis_requested or job.timeout_valid_span ~= nil then return self:_publish(job) end
  return result('COMPLETED')
end
function Controller:_published(job, message)
  if not self:_owns(job) then return result('STALE_JOB') end
  if job.phase ~= 'PUBLISHING' or not job.publishing or not valid_asset(message) then return self:_protocol_error(job) end
  job.publishing, job.phase = false, 'PUBLISHED'
  job.asset = { wav_path = message.wav_path, wav_sha256 = message.wav_sha256, frames = message.frames, sample_rate = message.sample_rate,
    job_id = job.job_id, project_id = job.token.project_id, generation = job.token.generation, analysis_revision = job.token.analysis_revision }
  if self.on_capture_saved then self.on_capture_saved(job.asset, job.token) end
  if job.timeout_valid_span ~= nil then
    local valid_span = job.timeout_valid_span; job.timeout_valid_span = nil
    self.machine:capture_timeout(job.token, valid_span)
    return result('PUBLISHED')
  end
  if job.analysis_requested then self:analyse(job.token) end
  return result('PUBLISHED')
end
function Controller:_released(job)
  if not job.release_sent or job.release_acked then return result('STALE_RELEASE') end
  local released = self.machine:resources_released(job.token, self.transport_stopped() == true)
  if released.code ~= 'OK' then return released end
  job.release_acked, job.release_deadline = true, nil
  return result('RELEASED')
end
function Controller:receive(message)
  local job = self.job
  if not job or not same_identity(job, message, self.protocol_version) then return result('STALE_REPLY') end
  if type(message.command) ~= 'string' or type(message.status) ~= 'string' then return self:_protocol_error(job) end
  if message.status == 'READY' and message.command == 'PREFLIGHT' then
    if not self:_capturing(job) then return result('STALE_JOB') end
    if job.phase ~= 'PREFLIGHTING' then return self:_protocol_error(job) end
    job.phase = 'STARTING'
    if not self:_send(job, 'START', { mode = job.mode }) then return self:_fail(job, 'CAPTURE_START_SEND_FAILED') end
    if not self:_capturing(job) then return result('STALE_JOB') end
    return result('READY')
  elseif message.status == 'STARTED' and message.command == 'START' then
    if not self:_capturing(job) then return result('STALE_JOB') end
    if job.phase ~= 'STARTING' then return self:_protocol_error(job) end
    job.started, job.phase = true, 'CAPTURING'
    return result('STARTED')
  elseif message.status == 'COMPLETED' and terminal_commands[message.command] then
    return self:_complete(job)
  elseif message.status == 'FAILED' and (terminal_commands[message.command] or message.command == 'PREFLIGHT' or message.command == 'PUBLISH') then
    return self:_fail(job, type(message.capture_error) == 'string' and message.capture_error or 'CAPTURE_FAILED')
  elseif message.status == 'PUBLISHED' and message.command == 'PUBLISH' then
    return self:_published(job, message)
  elseif message.status == 'RELEASED' and message.command == 'RELEASE' then
    return self:_released(job)
  end
  return self:_protocol_error(job)
end
function Controller:_release_deadline()
  local job = self.job
  if job and job.release_sent and not job.release_acked and not job.release_timeout_reported and self.now() >= job.release_deadline then
    job.release_timeout_reported = true
    self:_status('CAPTURE_RELEASE_TIMEOUT', { token = job.token, job_id = job.job_id })
    return result('RELEASE_TIMEOUT')
  end
end
-- One worker poll and one deadline comparison only. Callers schedule this method;
-- it contains no blocking or drain loop. Deadline wins over a stale-event flood.
function Controller:poll()
  local message = self.transport:poll()
  local received = message ~= nil and self:receive(message) or nil
  local deadline = self:_release_deadline()
  if deadline then return deadline end
  return received or result('NO_EVENT')
end
return Controller

-- Nonblocking analysis-worker protocol boundary.  A detector implementation is
-- deliberately injected: this module only admits an identified, bounded result
-- whose complete bank schema is valid for the current state-machine job.
local Bank = type(include) == 'function' and include('mosaic/lib/rhythm_doctor/bank') or require('rhythm_doctor.bank')

local Controller = {}
Controller.__index = Controller

local function result(code, extra)
  extra = extra or {}; extra.code, extra.ok = code, code == 'OK'; return extra
end
local function same_token(a, b)
  return type(a) == 'table' and type(b) == 'table' and a.project_id == b.project_id and
    a.generation == b.generation and a.analysis_revision == b.analysis_revision
end
local function finite_integer(value, minimum, maximum)
  return type(value) == 'number' and value == value and value ~= math.huge and value ~= -math.huge and
    value == math.floor(value) and value >= minimum and value <= maximum
end
local function valid_asset(asset)
  return type(asset) == 'table' and type(asset.wav_path) == 'string' and asset.wav_path:sub(1, 1) == '/' and
    asset.wav_path:match('%.wav$') and not asset.wav_path:find('%z') and not asset.wav_path:find('/%.%./') and
    asset.wav_path:sub(-3) ~= '/..' and type(asset.wav_sha256) == 'string' and #asset.wav_sha256 == 64 and
    asset.wav_sha256:match('^[%x]+$') and finite_integer(asset.sample_rate, 8000, 192000) and
    finite_integer(asset.frames, 0, asset.sample_rate * Bank.MAX_CAPTURE_SECONDS)
end
local function valid_error(value)
  return type(value) == 'string' and #value > 0 and #value <= 160 and not value:find('[%c]')
end
local function same_asset(message, asset)
  return message.wav_sha256 == asset.wav_sha256 and message.frames == asset.frames and message.sample_rate == asset.sample_rate
end

function Controller.new(deps)
  assert(type(deps) == 'table', 'dependencies are required')
  assert(type(deps.machine) == 'table' and type(deps.machine.job_token) == 'function' and type(deps.machine.receive_analysis) == 'function',
    'analysis machine is required')
  assert(type(deps.transport) == 'table' and type(deps.transport.send) == 'function' and type(deps.transport.poll) == 'function',
    'nonblocking analysis transport is required')
  local self = setmetatable({ machine = deps.machine, transport = deps.transport, protocol_version = deps.protocol_version or 1,
    job_prefix = deps.job_prefix or 'rhythm-doctor-analysis', nonce = 0, job = nil, on_status = deps.on_status }, Controller)
  assert(finite_integer(self.protocol_version, 1, math.huge), 'protocol version is required')
  return self
end

function Controller:_status(code, detail) if self.on_status then self.on_status(code, detail) end end
function Controller:_owns(job)
  return self.job == job and same_token(job.token, self.machine:job_token()) and
    (self.machine.state == 'ANALYSING' or self.machine.state == 'REANALYSING')
end
function Controller:_send(job, command)
  local message = { protocol_version = job.protocol_version, job_id = job.job_id, project_id = job.token.project_id,
    generation = job.token.generation, analysis_revision = job.token.analysis_revision, command = command }
  if command == 'ANALYSE' then
    message.wav_path, message.wav_sha256, message.frames, message.sample_rate = job.asset.wav_path, job.asset.wav_sha256,
      job.asset.frames, job.asset.sample_rate
    message.result_schema_version, message.max_candidates = Bank.VERSION, Bank.MAX_CANDIDATES
  end
  local ok, sent, reason = pcall(self.transport.send, self.transport, message)
  if not ok or sent ~= true then
    self:_status('ANALYSIS_TRANSPORT_SEND_FAILED', { command = command, reason = ok and reason or sent, token = job.token })
    return nil
  end
  return message
end
function Controller:_protocol_error(job)
  if not self:_owns(job) then return result('STALE_RESULT') end
  job.done = true
  self.machine:receive_analysis({ project_id = job.token.project_id, generation = job.token.generation,
    analysis_revision = job.token.analysis_revision, error = 'ANALYSIS_PROTOCOL_ERROR' })
  return result('ANALYSIS_PROTOCOL_ERROR')
end

-- `asset` originates only from the capture publication callback.  It is copied
-- into the invocation rather than reopened here, so no detector result can
-- silently substitute another capture or extend the 45-second retention bound.
function Controller:dispatch(asset, token)
  if not same_token(token, self.machine:job_token()) or self.machine.state ~= 'ANALYSING' and self.machine.state ~= 'REANALYSING' then
    return result('STALE_RESULT')
  end
  if not valid_asset(asset) or not same_token(asset, token) then return result('INVALID_ASSET') end
  if self.job and not self.job.done and same_token(self.job.token, token) then return result('ANALYSIS_PENDING') end
  self.nonce = self.nonce + 1
  local job = { protocol_version = self.protocol_version, job_id = self.job_prefix .. '-' .. tostring(self.nonce),
    token = { project_id=token.project_id, generation=token.generation, analysis_revision=token.analysis_revision },
    asset = { wav_path=asset.wav_path, wav_sha256=asset.wav_sha256, frames=asset.frames, sample_rate=asset.sample_rate }, done=false, cancel_sent=false }
  self.job = job
  if not self:_send(job, 'ANALYSE') then return self:_protocol_error(job) end
  return result('DISPATCHED', { job_id=job.job_id })
end

function Controller:cancel(token)
  local job = self.job
  if not job or not same_token(job.token, token) or job.done then return result('STALE_RESULT') end
  if job.cancel_sent then return result('CANCEL_PENDING') end
  job.cancel_sent = true
  if not self:_send(job, 'CANCEL') then self:_status('ANALYSIS_CANCEL_SEND_FAILED', { token=job.token, job_id=job.job_id }) end
  return result('CANCEL_PENDING')
end

function Controller:receive(message)
  local job = self.job
  if not job or type(message) ~= 'table' or message.protocol_version ~= job.protocol_version or message.job_id ~= job.job_id or
      not same_token(job.token, message) then return result('STALE_REPLY') end
  if type(message.command) ~= 'string' or type(message.status) ~= 'string' then return self:_protocol_error(job) end
  if message.command == 'CANCEL' and message.status == 'CANCELLED' then
    if not job.cancel_sent then return self:_protocol_error(job) end
    job.done = true; return result('CANCELLED')
  end
  if message.command ~= 'ANALYSE' then return self:_protocol_error(job) end
  if not self:_owns(job) then return result('STALE_RESULT') end
  if job.done then return self:_protocol_error(job) end
  if message.status == 'FAILED' then
    if not valid_error(message.analysis_error) then return self:_protocol_error(job) end
    job.done = true
    self.machine:receive_analysis({ project_id=job.token.project_id, generation=job.token.generation,
      analysis_revision=job.token.analysis_revision, error=message.analysis_error })
    return result('FAILED')
  end
  if message.status ~= 'COMPLETED' then return self:_protocol_error(job) end
  if not same_asset(message, job.asset) or type(message.bank) ~= 'table' or message.bank.sample_rate ~= job.asset.sample_rate or
      not Bank.valid_ready(message.bank, job.token) then
    job.done = true
    self.machine:receive_analysis({ project_id=job.token.project_id, generation=job.token.generation,
      analysis_revision=job.token.analysis_revision, error='INVALID_BANK' })
    return result('INVALID_BANK')
  end
  job.done = true
  local applied = self.machine:receive_analysis({ project_id=job.token.project_id, generation=job.token.generation,
    analysis_revision=job.token.analysis_revision, bank=message.bank })
  return result(applied.code == 'OK' and 'COMPLETED' or applied.code)
end

function Controller:poll()
  local message = self.transport:poll()
  if message == nil then return result('NO_EVENT') end
  return self:receive(message)
end

return Controller

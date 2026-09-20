-- Capture through softcut instead of a JACK client of our own.
--
-- The native worker opened its own JACK client, which is the one thing on a
-- norns that cannot be relied on: systemd removes the user's POSIX shared
-- memory when their last login session ends, taking JACK's registry with it.
-- Existing clients survive on open descriptors -- crone, softcut, the engine --
-- but nothing new can ever join the graph again until jackd restarts. A script
-- that opens its own client is therefore one SSH logout away from silence.
--
-- softcut already lives inside crone, which is already connected, so recording
-- through it needs nothing to join the graph. It also removes the compiled
-- capture worker, its build step and its IPC from a stock install entirely.
--
-- This speaks exactly the protocol capture_controller expects, so it is a
-- straight replacement for the transport that fronted the native worker: the
-- controller, the state machine and the UI above it are unchanged.
local Recorder = {}
Recorder.__index = Recorder

local SAMPLE_RATE = 48000
local MAX_SECONDS = 45
-- softcut's buffers are about 349 seconds each; a capture is at most 45.
local LEFT_VOICE, RIGHT_VOICE = 1, 2
local PUBLISH_TIMEOUT_SECONDS = 20
local HEADER_BYTES = 64

local function safe_id(value)
  return type(value) == 'string' and #value >= 1 and #value <= 64 and value:match('^[A-Za-z0-9_-]+$') ~= nil
end
local function integer(value)
  return type(value) == 'number' and value == math.floor(value) and value >= 0 and value <= 4294967295
end
local function identity(message)
  if type(message) ~= 'table' or message.protocol_version ~= 1 or not safe_id(message.job_id) or
      not safe_id(message.project_id) or not integer(message.generation) or not integer(message.analysis_revision) then return nil end
  return { protocol_version = 1, job_id = message.job_id, project_id = message.project_id,
    generation = message.generation, analysis_revision = message.analysis_revision }
end
local function same_identity(left, right)
  return left ~= nil and right ~= nil and left.job_id == right.job_id and left.project_id == right.project_id and
    left.generation == right.generation and left.analysis_revision == right.analysis_revision
end
local function reply(id, command, status, extra)
  local message = { protocol_version = 1, job_id = id.job_id, project_id = id.project_id,
    generation = id.generation, analysis_revision = id.analysis_revision, command = command, status = status }
  for key, value in pairs(extra or {}) do message[key] = value end
  return message
end

local function shell_quote(value)
  assert(type(value) == 'string' and not value:find('%z'), 'safe shell value required')
  return "'" .. value:gsub("'", "'\\''") .. "'"
end

-- Little-endian integer out of a byte string, so the published frame count and
-- rate are read from the file rather than inferred from a wall clock.
local function le(bytes, offset, width)
  local value = 0
  for i = width, 1, -1 do value = value * 256 + bytes:byte(offset + i) end
  return value
end

local function wav_geometry(header)
  if type(header) ~= 'string' or #header < 44 or header:sub(1, 4) ~= 'RIFF' or header:sub(9, 12) ~= 'WAVE' then return nil end
  local cursor = 13
  local channels, rate, bits, data_bytes
  while cursor + 7 <= #header do
    local id, size = header:sub(cursor, cursor + 3), le(header, cursor + 3, 4)
    if id == 'fmt ' and cursor + 7 + 16 <= #header then
      channels, rate = le(header, cursor + 9, 2), le(header, cursor + 11, 4)
      bits = le(header, cursor + 21, 2)
    elseif id == 'data' then
      data_bytes = size; break
    end
    cursor = cursor + 8 + size + (size % 2)
  end
  if not channels or not rate or not bits or not data_bytes then return nil end
  local block = channels * (bits // 8)
  if channels < 1 or channels > 2 or rate < 8000 or rate > 192000 or block < 1 then return nil end
  return data_bytes // block, rate
end

function Recorder.new(deps)
  deps = deps or {}
  local directory = deps.directory
  assert(type(directory) == 'string' and directory:sub(1, 1) == '/' and directory:sub(-1) ~= '/',
    'an absolute capture directory is required')
  local engine = deps.softcut or softcut
  assert(type(engine) == 'table', 'softcut is required')
  local mixer = deps.audio or audio
  assert(type(mixer) == 'table', 'the audio mixer is required')
  local self = setmetatable({
    directory = directory, softcut = engine, audio = mixer,
    -- The ADC send to softcut is a setting in the player's own AUDIO menu.
    -- Borrow it at unity for a capture and give back whatever they have set,
    -- read when it is handed back rather than remembered from before.
    adc_cut_level = deps.adc_cut_level or function()
      if norns and norns.state and norns.state.mix and util and util.dbamp then
        return util.dbamp(norns.state.mix.cut_input_adc)
      end
      return 0
    end,
    now = deps.now or (util and util.time) or os.clock,
    execute = deps.execute or os.execute,
    open_file = deps.open_file or io.open,
    remove = deps.remove or os.remove,
    left_voice = deps.left_voice or LEFT_VOICE, right_voice = deps.right_voice or RIGHT_VOICE,
    publish_timeout_seconds = deps.publish_timeout_seconds or PUBLISH_TIMEOUT_SECONDS,
    queue = {}, owner = nil, phase = 'IDLE', closed = false,
    seconds = nil, started_at = nil, duration = nil, publish = nil, published_path = nil,
  }, Recorder)
  self.execute('mkdir -p ' .. shell_quote(directory))
  return self
end

function Recorder:_emit(message) self.queue[#self.queue + 1] = message end

-- Softcut is a shared resource: take only what is needed, and hand it back.
-- Every default here is set deliberately, because softcut's own defaults suit
-- a delay line rather than a capture: it loops inside a one-second window per
-- voice, and it lowpasses the record path at 16 kHz.
function Recorder:_arm()
  local sc = self.softcut
  self.audio.level_adc_cut(1.0)
  for channel, voice in ipairs({ self.left_voice, self.right_voice }) do
    sc.enable(voice, 1)
    sc.buffer(voice, channel)
    -- Clear the whole channel rather than the region: softcut keeps crossfade
    -- and record-head guard samples outside the nominal loop, and an earlier
    -- capture must not leak into this one.
    sc.buffer_clear_channel(channel)
    sc.level(voice, 0)                        -- captured, never monitored back out
    sc.pan(voice, 0)
    sc.level_input_cut(channel, voice, 1.0)   -- this input, this voice, nothing else
    sc.level_input_cut(3 - channel, voice, 0)
    sc.rec_level(voice, 1.0)
    sc.pre_level(voice, 0)                    -- overwrite rather than layer
    -- A capture that is about to be analysed must not be coloured on the way in.
    sc.pre_filter_dry(voice, 1.0); sc.pre_filter_lp(voice, 0)
    sc.post_filter_dry(voice, 1.0); sc.post_filter_lp(voice, 0)
    sc.rate(voice, 1.0)
    sc.fade_time(voice, 0.005)
    sc.loop_start(voice, 0)
    sc.loop_end(voice, MAX_SECONDS)
    sc.loop(voice, 0)                         -- run off the end instead of wrapping
    sc.position(voice, 0)
    sc.rec(voice, 0)
    sc.play(voice, 0)
  end
end

-- The record head follows the play head, so a voice has to be moving to record.
function Recorder:_run(recording)
  local sc = self.softcut
  for _, voice in ipairs({ self.left_voice, self.right_voice }) do
    if recording then sc.position(voice, 0) end
    sc.rec(voice, recording and 1 or 0)
    sc.play(voice, recording and 1 or 0)
  end
end

function Recorder:_release_voices()
  local sc = self.softcut
  for channel, voice in ipairs({ self.left_voice, self.right_voice }) do
    sc.rec(voice, 0); sc.play(voice, 0)
    sc.level_input_cut(channel, voice, 0)
    sc.level_input_cut(3 - channel, voice, 0)
    sc.enable(voice, 0)
  end
  self.audio.level_adc_cut(self.adc_cut_level())
end

function Recorder:_reset()
  self:_release_voices()
  self.phase, self.owner, self.seconds = 'IDLE', nil, nil
  self.started_at, self.duration, self.publish = nil, nil, nil
  if self.published_path then self.remove(self.published_path); self.published_path = nil end
end

function Recorder:_preflight(message, id)
  if self.phase ~= 'IDLE' then return self:_emit(reply(id, 'PREFLIGHT', 'FAILED', { capture_error = 'BUSY' })) end
  local seconds = message.seconds
  if not integer(seconds) or seconds < 1 or seconds > MAX_SECONDS or
      (message.mode ~= 'auto' and message.mode ~= 'manual') then
    return self:_emit(reply(id, 'PREFLIGHT', 'FAILED', { capture_error = 'INVALID_DURATION' }))
  end
  local ok = pcall(function() self:_arm() end)
  if not ok then return self:_emit(reply(id, 'PREFLIGHT', 'FAILED', { capture_error = 'INPUT_RESOURCE_BUSY' })) end
  self.owner, self.seconds, self.phase = id, seconds, 'READY'
  self:_emit(reply(id, 'PREFLIGHT', 'READY'))
end

function Recorder:_start(id)
  if self.phase ~= 'READY' then return self:_emit(reply(id, 'START', 'FAILED', { capture_error = 'BAD_STATE' })) end
  self.started_at, self.phase = self.now(), 'RECORDING'
  self:_run(true)
  self:_emit(reply(id, 'START', 'STARTED'))
end

-- Stopping is not an acknowledgement: the controller waits for the terminal
-- event, exactly as it did with the native worker.
function Recorder:_finish()
  if self.phase ~= 'RECORDING' then return end
  self:_run(false)
  self.duration = math.min(self.now() - self.started_at, self.seconds)
  self.phase = 'COMPLETED'
  self:_emit(reply(self.owner, 'EVENT', 'COMPLETED'))
end

function Recorder:_publish_request(id)
  if self.phase ~= 'COMPLETED' or not self.duration or self.duration <= 0 then
    return self:_emit(reply(id, 'PUBLISH', 'FAILED', { capture_error = 'BAD_STATE' }))
  end
  local path = self.directory .. '/' .. id.job_id .. '.wav'
  self.remove(path); self.remove(path .. '.sha256')
  -- softcut writes the file on the audio thread and never answers, so the
  -- write is watched for rather than waited on, and hashing is handed to a
  -- background process: neither may block the Lua thread.
  local ok = pcall(function() self.softcut.buffer_write_stereo(path, 0, self.duration) end)
  if not ok then return self:_emit(reply(id, 'PUBLISH', 'FAILED', { capture_error = 'PUBLISH_FAILED' })) end
  self.phase = 'PUBLISHING'
  self.publish = { path = path, digest_path = path .. '.sha256', deadline = self.now() + self.publish_timeout_seconds,
    size = nil, stable = false, hashing = false }
end

-- A file that is still being written must not be hashed, and softcut gives no
-- completion signal, so the size is watched until it stops changing.
function Recorder:_advance_publish()
  local publish = self.publish
  if not publish then return end
  if self.now() > publish.deadline then
    self.publish, self.phase = nil, 'COMPLETED'
    return self:_emit(reply(self.owner, 'PUBLISH', 'FAILED', { capture_error = 'PUBLISH_TIMEOUT' }))
  end
  if not publish.hashing then
    local handle = self.open_file(publish.path, 'rb')
    if not handle then return end
    local size = handle:seek('end')
    handle:close()
    if size == nil or size < 44 then return end
    if publish.size ~= size then publish.size = size; return end
    publish.hashing = true
    self.execute('sha256sum ' .. shell_quote(publish.path) .. ' > ' .. shell_quote(publish.digest_path) .. ' 2>/dev/null &')
    return
  end
  local handle = self.open_file(publish.digest_path, 'rb')
  if not handle then return end
  local line = handle:read('*l'); handle:close()
  local digest = type(line) == 'string' and line:match('^(%x%x%x%x%x%x%x%x+)') or nil
  if not digest or #digest ~= 64 then return end
  local source = self.open_file(publish.path, 'rb')
  local header = source and source:read(HEADER_BYTES)
  if source then source:close() end
  local frames, rate = wav_geometry(header)
  self.remove(publish.digest_path)
  if not frames or frames < 1 then
    self.publish, self.phase = nil, 'COMPLETED'
    return self:_emit(reply(self.owner, 'PUBLISH', 'FAILED', { capture_error = 'PUBLISH_FAILED' }))
  end
  self.published_path, self.publish, self.phase = publish.path, nil, 'PUBLISHED'
  self:_emit(reply(self.owner, 'PUBLISH', 'PUBLISHED',
    { wav_path = publish.path, wav_sha256 = digest, frames = frames, sample_rate = rate or SAMPLE_RATE }))
end

local handlers = {
  START = function(self, _, id) self:_start(id) end,
  STOP = function(self) self:_finish() end,
  CANCEL = function(self)
    if self.phase == 'RECORDING' then self:_run(false) end
    if self.phase ~= 'PUBLISHED' then self.phase = 'READY'; self.duration, self.publish = nil, nil end
  end,
  PUBLISH = function(self, _, id) self:_publish_request(id) end,
  RELEASE = function(self, _, id) self:_release_voices(); self:_emit(reply(id, 'RELEASE', 'RELEASED')) end,
  EXIT = function(self, _, id) self:_emit(reply(id, 'EXIT', 'BYE')); self:_reset() end,
}

function Recorder:send(message)
  if self.closed then return false, 'closed' end
  local id = identity(message)
  if not id or type(message.command) ~= 'string' then return false, 'INVALID_MESSAGE' end
  if message.command == 'PREFLIGHT' then self:_preflight(message, id); return true end
  local handler = handlers[message.command]
  if not handler then return false, 'INVALID_MESSAGE' end
  if not same_identity(self.owner, id) then
    self:_emit(reply(id, message.command, 'STALE', { capture_error = 'STALE_JOB' }))
    return true
  end
  handler(self, message, id)
  return true
end

function Recorder:poll()
  if self.closed then return nil end
  -- A capture that reaches its own duration completes itself, as the native
  -- worker's process callback did.
  if self.phase == 'RECORDING' and self.now() - self.started_at >= self.seconds then self:_finish() end
  self:_advance_publish()
  if #self.queue == 0 then return nil end
  return table.remove(self.queue, 1)
end

function Recorder:close()
  if self.closed then return end
  self.closed = true
  self:_reset()
end

-- The runtime opens a capture source rather than being handed a transport,
-- because the native worker had to be launched and compiled before it could
-- answer anything. softcut is already running inside crone, so opening is
-- immediate -- but the shape the runtime expects is unchanged.
function Recorder.host(deps)
  local host = { recorder = nil, closed = false }
  function host:open()
    if self.closed then return nil, 'capture host closed' end
    if not self.recorder then self.recorder = Recorder.new(deps) end
    return self.recorder
  end
  function host:close()
    self.closed = true
    if self.recorder then self.recorder:close(); self.recorder = nil end
  end
  return host
end

Recorder.SAMPLE_RATE, Recorder.MAX_SECONDS = SAMPLE_RATE, MAX_SECONDS
Recorder.wav_geometry = wav_geometry
return Recorder

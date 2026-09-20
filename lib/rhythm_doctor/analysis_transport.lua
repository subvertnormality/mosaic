-- Nonblocking boundary to the detached Rhythm Doctor analysis worker, carried
-- by a sequenced file mailbox because matron's Lua 5.3 has no FFI.  Large banks
-- never travel in a message: the worker atomically publishes one owned JSON
-- result file, then sends its small pathname/identity envelope.
local function dependency(name, path)
  if type(include) == "function" then return include(path) end
  return require(name)
end
local json = dependency("helpers.json", "mosaic/lib/helpers/json")
local Bank = dependency("rhythm_doctor.bank", "mosaic/lib/rhythm_doctor/bank")
local Mailbox = dependency("rhythm_doctor.file_mailbox", "mosaic/lib/rhythm_doctor/file_mailbox")

local Transport = {}; Transport.__index = Transport
local MAX_PACKET, MAX_RESULT, MAX_QUEUE = 8192, 4 * 1024 * 1024, 8

local function safe_id(value)
  return type(value) == "string" and #value >= 1 and #value <= 64 and value:match("^[A-Za-z0-9_-]+$") ~= nil
end
local function integer(value) return type(value) == "number" and value == math.floor(value) and value >= 0 and value <= 4294967295 end
local function identity(message)
  if type(message) ~= "table" or message.protocol_version ~= 1 or not safe_id(message.job_id) or not safe_id(message.project_id) or
      not integer(message.generation) or not integer(message.analysis_revision) then return nil end
  return { protocol_version=1, job_id=message.job_id, project_id=message.project_id,
    generation=message.generation, analysis_revision=message.analysis_revision }
end
local function same_identity(left, right)
  return identity(left) and identity(right) and left.job_id == right.job_id and left.project_id == right.project_id and
    left.generation == right.generation and left.analysis_revision == right.analysis_revision
end
local function safe_error(value)
  return type(value) == "string" and #value > 0 and #value <= 160 and not value:find("[%c]")
end
local function safe_asset(message)
  return type(message.wav_path) == "string" and message.wav_path:sub(1, 1) == "/" and not message.wav_path:find("[%z\r\n]") and
    type(message.wav_sha256) == "string" and #message.wav_sha256 == 64 and message.wav_sha256:match("^[%x]+$") and
    integer(message.frames) and integer(message.sample_rate) and message.sample_rate >= 8000 and message.sample_rate <= 192000
end
local function failure(id, code)
  id = id or { protocol_version=1, job_id="invalid", project_id="invalid", generation=0, analysis_revision=0 }
  id.command, id.status, id.analysis_error = "ANALYSE", "FAILED", code
  return id
end
local function read_limited(path)
  local handle = io.open(path, "rb"); if not handle then return nil end
  local value = handle:read(MAX_RESULT + 1); handle:close()
  if not value or #value > MAX_RESULT then return nil end
  return value
end
local function digest(value)
  return type(value) == "string" and #value == 64 and value:match("^[%x]+$") ~= nil
end
-- Two detector identities are supported, and a result must carry exactly one
-- of them whole. The shipped classical-DSP backend pins its own source and the
-- template table it reads; a pretrained chain pins its model artifacts. Half a
-- shape, or both at once, is a configuration error and pins nothing reliably.
local function supported_detector(detector)
  if type(detector) ~= "table" or type(detector.backend_id) ~= "string" or detector.backend_id == "" or
      not digest(detector.backend_sha256) then return false end
  local dsp = digest(detector.template_sha256) and detector.drum_artifact_sha256 == nil and
    detector.bass_artifact_sha256 == nil
  local pretrained = digest(detector.drum_artifact_sha256) and digest(detector.bass_artifact_sha256) and
    detector.template_sha256 == nil
  return (dsp or pretrained) and not (dsp and pretrained)
end
local function complete_lane_gates(value)
  if type(value) ~= "table" then return false end
  for _, lane in ipairs(Bank.LANES) do
    local gate=value[lane]
    if type(gate) ~= "number" or gate ~= gate or gate < 0 or gate > 1 then return false end
  end
  return true
end

function Transport.new(mailbox_root, result_root, deps)
  deps = deps or {}
  if type(result_root) ~= "string" or result_root:sub(1, 1) ~= "/" or result_root:sub(-1) == "/" or result_root:find("[%z\r\n\t]") then
    return nil, { code="INVALID_RESULT_ROOT" }
  end
  local mailbox, problem = (deps.mailbox_factory or Mailbox.open)(mailbox_root, "c2w", "w2c",
    { limit = MAX_PACKET, open_file = deps.open_file, rename = deps.rename, remove = deps.remove,
      now = deps.now, claim = deps.claim })
  if not mailbox then return nil, { code = problem } end
  return setmetatable({ mailbox=mailbox, queue={}, last_identity=nil,
    result_root=result_root, read_file=deps.read_file or read_limited }, Transport)
end

function Transport:send(message)
  local id = identity(message)
  if not self.mailbox or self.mailbox.closed or not id or (message.command ~= "ANALYSE" and message.command ~= "CANCEL") then return false, "invalid message" end
  if message.command == "ANALYSE" and (not safe_asset(message) or message.result_schema_version == nil or message.max_candidates == nil) then
    return false, "invalid analysis request"
  end
  local ok, wire = pcall(json.encode, message)
  if not ok or #wire > MAX_PACKET or #self.queue >= MAX_QUEUE then return false, "message rejected" end
  self.queue[#self.queue + 1], self.last_identity = wire, id
  return self:_flush()
end
function Transport:_flush()
  while #self.queue > 0 do
    local sent, problem = self.mailbox:send(self.queue[1])
    if not sent then return false, problem end
    table.remove(self.queue, 1)
  end
  return true
end
function Transport:_completed(message)
  if type(message.result_path) ~= "string" or message.result_path:sub(1, #self.result_root + 1) ~= self.result_root .. "/" or
      message.result_path:find("[%z\r\n]") then return failure(self.last_identity, "ANALYSIS_PROTOCOL_ERROR") end
  local text = self.read_file(message.result_path); if not text then return failure(message, "ANALYSIS_RESULT_UNREADABLE") end
  local ok, stored = pcall(json.decode, text)
  if not ok or type(stored) ~= "table" or not same_identity(message, stored) or stored.command ~= "ANALYSE" or
      stored.status ~= "COMPLETED" or not safe_asset(stored) or type(stored.analysis) ~= "table" or
      not supported_detector(stored.analysis.detector) or
      not complete_lane_gates(stored.analysis.lane_onset_gates) then
    return failure(message, "ANALYSIS_PROTOCOL_ERROR")
  end
  local analysis=stored.analysis
  analysis.detector.lane_onset_gates=analysis.lane_onset_gates
  local bank, problem=Bank.build({ project_id=stored.project_id, generation=stored.generation,
    analysis_revision=stored.analysis_revision, sample_rate=stored.sample_rate, capture_start_sample=0,
    capture_end_sample=stored.frames, origin_sample=analysis.origin_sample, bpm=analysis.bpm,
    tempo_mode=analysis.tempo_mode, tempo_candidates=analysis.tempo_candidates, tempo_confidence=analysis.tempo_confidence,
    -- The backend says when it found no periodicity and returned its default
    -- tempo. Dropping that here is how a default reached the screen looking
    -- exactly like a measurement.
    tempo_detected=analysis.tempo_detected,
    -- Where the backend believes the four-bar phrase begins, and the beat grid
    -- the alignment editor steps through when the player disagrees. Neither
    -- reached the bank before, so the editor's START BEAT control had an empty
    -- list to step through and did nothing.
    phrase_start_sample=analysis.phrase_start_sample, phrase_confidence=analysis.phrase_confidence,
    beat_positions=analysis.beat_positions,
    sensitivities=analysis.sensitivities, candidates=analysis.candidates, detector=analysis.detector,
    quality_warnings=analysis.quality_warnings })
  if not bank then return failure(message, problem and problem.code or "ANALYSIS_PROTOCOL_ERROR") end
  return { protocol_version=1, job_id=message.job_id, project_id=message.project_id, generation=message.generation,
    analysis_revision=message.analysis_revision, command="ANALYSE", status="COMPLETED", wav_sha256=stored.wav_sha256,
    frames=stored.frames, sample_rate=stored.sample_rate, bank=bank }
end
-- A record already in the mailbox outranks a departed worker, so the envelope
-- is drained before liveness is judged.
function Transport:poll()
  if not self.mailbox or self.mailbox.closed then return nil end
  self.mailbox:heartbeat()
  local flushed = self:_flush(); if not flushed then return failure(self.last_identity, "ANALYSIS_TRANSPORT_ERROR") end
  local wire, problem = self.mailbox:receive()
  if problem then return failure(self.last_identity, "ANALYSIS_PROTOCOL_ERROR") end
  if not wire then
    if not self.mailbox:peer_present() then return failure(self.last_identity, "ANALYSIS_TRANSPORT_ERROR") end
    return nil
  end
  local ok, message = pcall(json.decode, wire)
  if not ok or type(message) ~= "table" or not same_identity(message, self.last_identity) then
    return failure(self.last_identity, "ANALYSIS_PROTOCOL_ERROR")
  end
  if message.status == "COMPLETED" then return self:_completed(message) end
  if message.status == "FAILED" and safe_error(message.analysis_error) then return message end
  if message.status == "CANCELLED" and message.command == "CANCEL" then return message end
  return failure(message, "ANALYSIS_PROTOCOL_ERROR")
end
function Transport:close() if self.mailbox then self.mailbox:close() end end
return Transport

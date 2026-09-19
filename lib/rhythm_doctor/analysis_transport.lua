-- Nonblocking AF_UNIX boundary for the detached Rhythm Doctor analysis worker.
-- Large banks never travel in a socket packet: the worker atomically publishes
-- one owned JSON result file, then sends its small pathname/identity envelope.
local ffi = require("ffi")
local bit = require("bit")
local function dependency(name, path)
  if type(include) == "function" then return include(path) end
  return require(name)
end
local json = dependency("helpers.json", "mosaic/lib/helpers/json")
local Bank = dependency("rhythm_doctor.bank", "mosaic/lib/rhythm_doctor/bank")

ffi.cdef[[
typedef unsigned short sa_family_t;
struct sockaddr { sa_family_t sa_family; char sa_data[14]; };
struct sockaddr_un { sa_family_t sun_family; char sun_path[108]; };
int socket(int domain, int type, int protocol);
int connect(int fd, const struct sockaddr *addr, unsigned int addrlen);
long send(int fd, const void *buf, unsigned long len, int flags);
long recv(int fd, void *buf, unsigned long len, int flags);
int close(int fd); int fcntl(int fd, int command, ...); char *strerror(int errnum);
]]

local C, Transport = ffi.C, {}; Transport.__index = Transport
local AF_UNIX, SOCK_SEQPACKET, SOCK_NONBLOCK = 1, 5, 2048
local F_SETFL, O_NONBLOCK, EAGAIN, EWOULDBLOCK, EINPROGRESS = 4, 2048, 11, 11, 115
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
local function complete_lane_gates(value)
  if type(value) ~= "table" then return false end
  for _, lane in ipairs(Bank.LANES) do
    local gate=value[lane]
    if type(gate) ~= "number" or gate ~= gate or gate < 0 or gate > 1 then return false end
  end
  return true
end

function Transport.new(socket_path, result_root, deps)
  deps = deps or {}
  if type(socket_path) ~= "string" or socket_path:sub(1, 1) ~= "/" or #socket_path > 107 or socket_path:find("[%z\r\n\t]") then
    return nil, { code="INVALID_SOCKET_PATH" }
  end
  if type(result_root) ~= "string" or result_root:sub(1, 1) ~= "/" or result_root:sub(-1) == "/" or result_root:find("[%z\r\n\t]") then
    return nil, { code="INVALID_RESULT_ROOT" }
  end
  local fd = C.socket(AF_UNIX, bit.bor(SOCK_SEQPACKET, SOCK_NONBLOCK), 0)
  if fd < 0 then return nil, { code="SOCKET_FAILED" } end
  local address = ffi.new("struct sockaddr_un"); address.sun_family = AF_UNIX; ffi.copy(address.sun_path, socket_path, #socket_path)
  if C.connect(fd, ffi.cast("const struct sockaddr *", address), ffi.sizeof(address)) ~= 0 and ffi.errno() ~= EINPROGRESS then
    C.close(fd); return nil, { code="CONNECT_FAILED" }
  end
  C.fcntl(fd, F_SETFL, O_NONBLOCK)
  return setmetatable({ fd=fd, queue={}, receive=ffi.new("char[?]", MAX_PACKET + 1), last_identity=nil,
    result_root=result_root, read_file=deps.read_file or read_limited }, Transport)
end

function Transport:send(message)
  local id = identity(message)
  if self.fd < 0 or not id or (message.command ~= "ANALYSE" and message.command ~= "CANCEL") then return false, "invalid message" end
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
    local wire = self.queue[1]; local sent = C.send(self.fd, wire, #wire, 0)
    if sent < 0 then local number=ffi.errno(); if number == EAGAIN or number == EWOULDBLOCK then return true end; return false, "send failed" end
    if sent ~= #wire then return false, "partial seqpacket send" end
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
      type(stored.analysis.detector) ~= "table" or type(stored.analysis.detector.backend_id) ~= "string" or
      stored.analysis.detector.backend_id == "" or type(stored.analysis.detector.backend_sha256) ~= "string" or
      #stored.analysis.detector.backend_sha256 ~= 64 or not stored.analysis.detector.backend_sha256:match("^[%x]+$") or
      type(stored.analysis.detector.drum_artifact_sha256) ~= "string" or #stored.analysis.detector.drum_artifact_sha256 ~= 64 or
      not stored.analysis.detector.drum_artifact_sha256:match("^[%x]+$") or type(stored.analysis.detector.bass_artifact_sha256) ~= "string" or
      #stored.analysis.detector.bass_artifact_sha256 ~= 64 or not stored.analysis.detector.bass_artifact_sha256:match("^[%x]+$") or
      not complete_lane_gates(stored.analysis.lane_onset_gates) then
    return failure(message, "ANALYSIS_PROTOCOL_ERROR")
  end
  local analysis=stored.analysis
  analysis.detector.lane_onset_gates=analysis.lane_onset_gates
  local bank, problem=Bank.build({ project_id=stored.project_id, generation=stored.generation,
    analysis_revision=stored.analysis_revision, sample_rate=stored.sample_rate, capture_start_sample=0,
    capture_end_sample=stored.frames, origin_sample=analysis.origin_sample, bpm=analysis.bpm,
    tempo_mode=analysis.tempo_mode, tempo_candidates=analysis.tempo_candidates, tempo_confidence=analysis.tempo_confidence,
    sensitivities=analysis.sensitivities, candidates=analysis.candidates, detector=analysis.detector,
    quality_warnings=analysis.quality_warnings })
  if not bank then return failure(message, problem and problem.code or "ANALYSIS_PROTOCOL_ERROR") end
  return { protocol_version=1, job_id=message.job_id, project_id=message.project_id, generation=message.generation,
    analysis_revision=message.analysis_revision, command="ANALYSE", status="COMPLETED", wav_sha256=stored.wav_sha256,
    frames=stored.frames, sample_rate=stored.sample_rate, bank=bank }
end
function Transport:poll()
  if self.fd < 0 then return nil end
  local flushed = self:_flush(); if not flushed then return failure(self.last_identity, "ANALYSIS_TRANSPORT_ERROR") end
  local received = C.recv(self.fd, self.receive, MAX_PACKET + 1, 0)
  if received < 0 then local number=ffi.errno(); return (number == EAGAIN or number == EWOULDBLOCK) and nil or failure(self.last_identity, "ANALYSIS_TRANSPORT_ERROR") end
  if received == 0 or received > MAX_PACKET then return failure(self.last_identity, "ANALYSIS_PROTOCOL_ERROR") end
  local ok, message = pcall(json.decode, ffi.string(self.receive, received))
  if not ok or type(message) ~= "table" or not same_identity(message, self.last_identity) then
    return failure(self.last_identity, "ANALYSIS_PROTOCOL_ERROR")
  end
  if message.status == "COMPLETED" then return self:_completed(message) end
  if message.status == "FAILED" and safe_error(message.analysis_error) then return message end
  if message.status == "CANCELLED" and message.command == "CANCEL" then return message end
  return failure(message, "ANALYSIS_PROTOCOL_ERROR")
end
function Transport:close() if self.fd >= 0 then C.close(self.fd); self.fd=-1 end end
return Transport

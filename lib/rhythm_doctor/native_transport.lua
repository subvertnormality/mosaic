-- Nonblocking boundary to rd_capture_worker over a sequenced file mailbox.
-- The RD1 wire record is unchanged; only its carrier is, because matron's
-- Lua 5.3 has no ffi and cannot reach an AF_UNIX socket.  See file_mailbox.
local function dependency(name, path)
  if type(include) == "function" then return include(path) end
  return require(name)
end
local Mailbox = dependency("rhythm_doctor.file_mailbox", "mosaic/lib/rhythm_doctor/file_mailbox")

local Transport = {}
Transport.__index = Transport
local MAX_MESSAGE, MAX_QUEUE = 1023, 8

local function safe_id(value)
  return type(value) == 'string' and #value >= 1 and #value <= 64 and value:match('^[A-Za-z0-9_-]+$') ~= nil
end
local function integer(value)
  return type(value) == 'number' and value == math.floor(value) and value >= 0 and value <= 4294967295
end
local function failure(code, detail) return nil, { code = code, detail = detail } end

local function identity(message)
  if type(message) ~= 'table' or message.protocol_version ~= 1 or not safe_id(message.job_id) or
      not safe_id(message.project_id) or not integer(message.generation) or not integer(message.analysis_revision) then return nil end
  return { protocol_version=1, job_id=message.job_id, project_id=message.project_id,
    generation=message.generation, analysis_revision=message.analysis_revision }
end

local commands = { PREFLIGHT=true, START=true, STOP=true, CANCEL=true, PUBLISH=true, RELEASE=true, EXIT=true }
local function encode(message)
  local id = identity(message)
  if not id or not commands[message.command] then return failure('INVALID_MESSAGE') end
  local argument = ''
  if message.command == 'PREFLIGHT' then
    if not integer(message.seconds) or message.seconds < 1 or message.seconds > 45 or
        (message.mode ~= 'auto' and message.mode ~= 'manual') then return failure('INVALID_MESSAGE') end
    argument = tostring(message.seconds)..','..message.mode
  elseif message.command == 'START' then
    if message.mode ~= nil and message.mode ~= 'auto' and message.mode ~= 'manual' then return failure('INVALID_MESSAGE') end
  end
  local wire = table.concat({'RD1',id.job_id,id.project_id,tostring(id.generation),tostring(id.analysis_revision),message.command,argument}, '\t')
  if #wire > MAX_MESSAGE then return failure('MESSAGE_TOO_LARGE') end
  return wire, id
end

local function split_exact(value, delimiter, count)
  local out, start = {}, 1
  for _ = 1, count - 1 do
    local at = value:find(delimiter, start, true); if not at then return nil end
    out[#out+1] = value:sub(start, at - 1); start = at + #delimiter
  end
  out[#out+1] = value:sub(start)
  if #out ~= count then return nil end
  return out
end

local function decode(wire)
  if type(wire) ~= 'string' or #wire > MAX_MESSAGE or wire:find('[%z\r\n]') then return nil end
  local f=split_exact(wire,'\t',8); if not f or f[1]~='RD1' then return nil end
  local generation,revision=tonumber(f[4]),tonumber(f[5])
  local message={protocol_version=1,job_id=f[2],project_id=f[3],generation=generation,analysis_revision=revision,command=f[6],status=f[7]}
  if not identity(message) or not safe_id(f[6]) or not safe_id(f[7]) then return nil end
  if f[7]=='PUBLISHED' then
    local detail=split_exact(f[8],',',4);if not detail then return nil end
    message.wav_path,message.wav_sha256=detail[1],detail[2]
    message.frames,message.sample_rate=tonumber(detail[3]),tonumber(detail[4])
  elseif f[7]=='FAILED' or f[7]=='ERROR' then message.capture_error=f[8]
  elseif f[8]~='' then return nil end
  return message
end

function Transport.new(mailbox_root, deps)
  deps = deps or {}
  local mailbox, problem = (deps.mailbox_factory or Mailbox.open)(mailbox_root, 'c2w', 'w2c',
    { limit = MAX_MESSAGE, open_file = deps.open_file, rename = deps.rename, remove = deps.remove,
      now = deps.now, claim = deps.claim })
  if not mailbox then return failure(problem) end
  return setmetatable({ mailbox=mailbox, queue={}, last_identity=nil }, Transport)
end

function Transport:_flush()
  while #self.queue>0 do
    local sent,problem=self.mailbox:send(self.queue[1])
    if not sent then return false,problem end
    table.remove(self.queue,1)
  end
  return true
end
function Transport:send(message)
  if not self.mailbox or self.mailbox.closed then return false,'closed' end
  local wire,id_or_error=encode(message);if not wire then return false,id_or_error.code end
  if #self.queue>=MAX_QUEUE then return false,'queue full' end
  self.queue[#self.queue+1]=wire;self.last_identity=id_or_error
  return self:_flush()
end
function Transport:_protocol_failure()
  local id=self.last_identity
  if not id then return {protocol_version=1,job_id='invalid',project_id='invalid',generation=0,analysis_revision=0,command='EVENT',status='FAILED',capture_error='CAPTURE_PROTOCOL_ERROR'} end
  id.command,id.status,id.capture_error='EVENT','FAILED','CAPTURE_PROTOCOL_ERROR';return id
end
-- A record already in the mailbox outranks a departed worker: the worker
-- answers EXIT and only then removes its sentinel, so draining before the
-- liveness check keeps that final reply from being reported as a failure.
function Transport:poll()
  if not self.mailbox or self.mailbox.closed then return nil end
  self.mailbox:heartbeat()
  local flushed=self:_flush();if not flushed then return self:_protocol_failure() end
  local wire,problem=self.mailbox:receive()
  if wire then return decode(wire) or self:_protocol_failure() end
  if problem then return self:_protocol_failure() end
  if not self.mailbox:peer_present() then return self:_protocol_failure() end
  return nil
end
function Transport:close()
  if self.mailbox then self.mailbox:close() end
end
return Transport

-- Linux/LuaJIT nonblocking AF_UNIX transport for rd_capture_worker.
local ffi = require('ffi')
local bit = require('bit')
ffi.cdef[[
typedef unsigned short sa_family_t;
struct sockaddr { sa_family_t sa_family; char sa_data[14]; };
struct sockaddr_un { sa_family_t sun_family; char sun_path[108]; };
int socket(int domain, int type, int protocol);
int connect(int fd, const struct sockaddr *addr, unsigned int addrlen);
long send(int fd, const void *buf, unsigned long len, int flags);
long recv(int fd, void *buf, unsigned long len, int flags);
int close(int fd);
int fcntl(int fd, int command, ...);
char *strerror(int errnum);
]]

local C, Transport = ffi.C, {}
Transport.__index = Transport
local AF_UNIX, SOCK_SEQPACKET, SOCK_NONBLOCK = 1, 5, 2048
local F_SETFL, O_NONBLOCK = 4, 2048
local EAGAIN, EWOULDBLOCK, EINPROGRESS = 11, 11, 115
local MAX_MESSAGE, MAX_QUEUE = 1023, 8

local function safe_id(value)
  return type(value) == 'string' and #value >= 1 and #value <= 64 and value:match('^[A-Za-z0-9_-]+$') ~= nil
end
local function integer(value)
  return type(value) == 'number' and value == math.floor(value) and value >= 0 and value <= 4294967295
end
local function failure(code, detail) return nil, { code = code, detail = detail } end
local function errno_text() local number = ffi.errno(); return number, ffi.string(C.strerror(number)) end

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

function Transport.new(socket_path)
  if type(socket_path)~='string' or socket_path:sub(1,1)~='/' or #socket_path>107 or socket_path:find('[%z\r\n\t]') then
    return failure('INVALID_SOCKET_PATH')
  end
  local fd=C.socket(AF_UNIX,bit.bor(SOCK_SEQPACKET,SOCK_NONBLOCK),0)
  if fd<0 then local _,problem=errno_text();return failure('SOCKET_FAILED',problem) end
  local address=ffi.new('struct sockaddr_un');address.sun_family=AF_UNIX;ffi.copy(address.sun_path,socket_path,#socket_path)
  local connected=C.connect(fd,ffi.cast('const struct sockaddr *',address),ffi.sizeof(address))
  if connected~=0 then
    local number,problem=errno_text();C.close(fd)
    return failure(number==EINPROGRESS and 'CONNECT_PENDING' or 'CONNECT_FAILED',problem)
  end
  C.fcntl(fd,F_SETFL,O_NONBLOCK)
  return setmetatable({fd=fd,queue={},receive=ffi.new('char[?]',MAX_MESSAGE+1),last_identity=nil},Transport)
end

function Transport:_flush()
  while #self.queue>0 do
    local wire=self.queue[1];local sent=C.send(self.fd,wire,#wire,0)
    if sent<0 then local number,problem=errno_text();if number==EAGAIN or number==EWOULDBLOCK then return true end;return false,problem end
    if sent~=#wire then return false,'partial seqpacket send' end
    table.remove(self.queue,1)
  end
  return true
end
function Transport:send(message)
  if self.fd<0 then return false,'closed' end
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
function Transport:poll()
  if self.fd<0 then return nil end
  local ok=self:_flush();if not ok then return self:_protocol_failure() end
  local received=C.recv(self.fd,self.receive,MAX_MESSAGE+1,0)
  if received<0 then local number=ffi.errno();if number==EAGAIN or number==EWOULDBLOCK then return nil end;return self:_protocol_failure() end
  if received==0 or received>MAX_MESSAGE then return self:_protocol_failure() end
  return decode(ffi.string(self.receive,received)) or self:_protocol_failure()
end
function Transport:close()
  if self.fd>=0 then C.close(self.fd);self.fd=-1 end
end
return Transport

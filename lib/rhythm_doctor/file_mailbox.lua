-- Sequenced file mailbox: the IPC carrier shared by the Rhythm Doctor workers
-- and the norns Lua thread.
--
-- matron embeds Lua 5.3 (liblua5.3.so.0), not LuaJIT.  There is no ffi, no
-- luasocket and no posix binding on a stock norns, so AF_UNIX is unreachable
-- from a script and the previous seqpacket transports could never load.  A
-- message is therefore one file: the sender writes it under a temporary name
-- beside its target and renames it into place.  Rename within a directory is
-- atomic, so a reader never observes a partial record and every record arrives
-- whole -- the exact framing guarantee SOCK_SEQPACKET gave.
--
-- Delivery stays ordered and exactly once because both ends agree on the next
-- sequence number: a reader opens precisely that name and unlinks it once it
-- holds the bytes.  Nothing here lists a directory, because Lua 5.3 cannot.
local Mailbox = {}
Mailbox.__index = Mailbox

-- Nine digits outlast any session: a capture spends single-figure messages and
-- the worker is replaced long before a billion of them.
local MAX_SEQUENCE = 999999999
local HEARTBEAT_SECONDS = 1

local function sequence_name(directory, number, suffix)
  return string.format("%s/%09d.msg%s", directory, number, suffix or "")
end

-- The worker owns the root and appends "/c2w/000000001.msg" to it, so a root
-- this long keeps every derived path comfortably inside PATH_MAX.
local function safe_root(value)
  return type(value) == "string" and value:sub(1, 1) == "/" and value:sub(-1) ~= "/" and
    #value <= 96 and value:find("[%z\r\n\t]") == nil
end

local function safe_segment(value)
  return type(value) == "string" and value:match("^[a-z0-9_]+$") ~= nil
end

-- One client at a time, decided atomically.  Lua 5.3 has no O_EXCL, but rename
-- is a test-and-set: the worker leaves "claim" behind at startup and only the
-- rename that moves it wins.  A second transport over the same root fails
-- closed instead of interleaving its sequence numbers with the first.
function Mailbox.open(root, outbound, inbound, options)
  options = options or {}
  local rename = options.rename or os.rename
  local open_file = options.open_file or io.open
  if not safe_root(root) then return nil, "INVALID_MAILBOX_ROOT" end
  if not safe_segment(outbound) or not safe_segment(inbound) or outbound == inbound then
    return nil, "INVALID_MAILBOX_LAYOUT"
  end
  local limit = options.limit
  if type(limit) ~= "number" or limit ~= math.floor(limit) or limit < 1 then return nil, "INVALID_MAILBOX_LIMIT" end
  if options.claim ~= false and not rename(root .. "/claim", root .. "/claimed") then
    return nil, "MAILBOX_UNAVAILABLE"
  end
  return setmetatable({
    root = root, outbound = root .. "/" .. outbound, inbound = root .. "/" .. inbound, limit = limit,
    send_sequence = 1, receive_sequence = 1, closed = false, heartbeat_at = nil,
    open_file = open_file, rename = rename, remove = options.remove or os.remove, now = options.now or os.time,
  }, Mailbox)
end

function Mailbox:send(bytes)
  if self.closed then return false, "MAILBOX_CLOSED" end
  if type(bytes) ~= "string" or #bytes == 0 or #bytes > self.limit then return false, "INVALID_MESSAGE" end
  if self.send_sequence > MAX_SEQUENCE then return false, "MAILBOX_EXHAUSTED" end
  local final = sequence_name(self.outbound, self.send_sequence)
  local partial = sequence_name(self.outbound, self.send_sequence, ".part")
  local handle = self.open_file(partial, "wb")
  if not handle then return false, "MAILBOX_WRITE_FAILED" end
  local written = handle:write(bytes)
  local flushed = handle:close()
  if not written or not flushed or not self.rename(partial, final) then
    self.remove(partial); return false, "MAILBOX_WRITE_FAILED"
  end
  self.send_sequence = self.send_sequence + 1
  return true
end

-- nil with no reason means an empty mailbox, which is the common case and not
-- a fault.  A reason means the record was unusable and the caller must treat
-- it as a protocol failure.
function Mailbox:receive()
  if self.closed then return nil, "MAILBOX_CLOSED" end
  local path = sequence_name(self.inbound, self.receive_sequence)
  local handle = self.open_file(path, "rb")
  if not handle then return nil end
  local bytes = handle:read(self.limit + 1)
  handle:close(); self.remove(path)
  self.receive_sequence = self.receive_sequence + 1
  if type(bytes) ~= "string" or #bytes == 0 or #bytes > self.limit then return nil, "MAILBOX_INVALID_MESSAGE" end
  return bytes
end

-- The worker cannot observe a hung-up peer without a socket, so the client
-- stamps a file the worker stats.  Once a second is ample against a timeout
-- measured in seconds, and keeps the norns thread off the filesystem.
function Mailbox:heartbeat()
  local now = self.now()
  if self.heartbeat_at and now - self.heartbeat_at < HEARTBEAT_SECONDS then return end
  self.heartbeat_at = now
  local handle = self.open_file(self.root .. "/alive", "wb")
  if not handle then return end
  handle:write(tostring(now)); handle:close()
end

-- The worker removes this sentinel as it exits, cleanly or by signal handler.
function Mailbox:peer_present()
  local handle = self.open_file(self.root .. "/up", "rb")
  if not handle then return false end
  handle:close(); return true
end

function Mailbox:close() self.closed = true end

Mailbox.MAX_SEQUENCE = MAX_SEQUENCE
return Mailbox

package.path = './lib/?.lua;' .. package.path
local Mailbox = require('rhythm_doctor.file_mailbox')

-- The mailbox is the carrier both Rhythm Doctor workers now share, because
-- matron's Lua 5.3 has no FFI and cannot hold a socket. What a seqpacket gave
-- for free -- whole records, in order, one peer -- it has to give explicitly.

local passed = 0
local function check(condition, message)
  if not condition then error(message, 2) end
  passed = passed + 1
end

local function shell(command) assert(os.execute(command)) end
local function scratch()
  local root = '/tmp/rd-mailbox-test-' .. tostring(math.random(1, 2 ^ 30))
  shell("rm -rf '" .. root .. "' && mkdir -p '" .. root .. "/c2w' '" .. root .. "/w2c'")
  local handle = assert(io.open(root .. '/claim', 'wb')); handle:close()
  handle = assert(io.open(root .. '/up', 'wb')); handle:close()
  return root
end
local function remove(root) shell("rm -rf '" .. root .. "'") end
local function exists(path)
  local handle = io.open(path, 'rb'); if not handle then return false end
  handle:close(); return true
end

-- A client and the worker facing each other across one root.
local function pair(root)
  local client = assert(Mailbox.open(root, 'c2w', 'w2c', { limit = 64 }))
  local worker = assert(Mailbox.open(root, 'w2c', 'c2w', { limit = 64, claim = false }))
  return client, worker
end

local root = scratch()
do
  local client, worker = pair(root)
  check(client:send('first'), 'send must succeed')
  check(client:send('second'), 'second send must succeed')
  check(worker:receive() == 'first', 'records arrive in order')
  check(worker:receive() == 'second', 'the second record follows the first')
  check(worker:receive() == nil, 'an empty mailbox is not a fault')
  check(worker:send('reply'), 'the worker answers on the other direction')
  check(client:receive() == 'reply', 'the client reads the reply')
end
remove(root)

-- Only one client, decided atomically: the token can be taken exactly once.
root = scratch()
do
  local first = assert(Mailbox.open(root, 'c2w', 'w2c', { limit = 64 }))
  local second, problem = Mailbox.open(root, 'c2w', 'w2c', { limit = 64 })
  check(first ~= nil and second == nil, 'a second client must be refused')
  check(problem == 'MAILBOX_UNAVAILABLE', 'refusal names the claim')
end
remove(root)

-- A reader must never see a record mid-write. The writer builds it under a
-- name the reader does not look at, then renames it into place.
root = scratch()
do
  local client, worker = pair(root)
  local held
  client.rename = function(from, to) held = { from, to }; return true end
  check(client:send('half-written'), 'the write itself reports success')
  check(worker:receive() == nil, 'an unrenamed record is invisible')
  check(exists(held[1]), 'the partial record exists under its own name')
  check(os.rename(held[1], held[2]), 'completing the rename publishes it')
  check(worker:receive() == 'half-written', 'the whole record arrives at once')
end
remove(root)

-- Sequence gaps stall rather than reorder: a reader waiting on record one does
-- not skip ahead to record two.
root = scratch()
do
  local client, worker = pair(root)
  client.send_sequence = 2
  check(client:send('out-of-order'), 'the writer may run ahead')
  check(worker:receive() == nil, 'the missing record is waited for, not skipped')
  client.send_sequence = 1
  check(client:send('first'), 'the gap is filled')
  check(worker:receive() == 'first', 'delivery resumes in order')
  check(worker:receive() == 'out-of-order', 'the later record follows')
end
remove(root)

-- Oversize records are consumed and reported, so a sender cannot wedge the
-- sequence with one bad write.
root = scratch()
do
  local client, worker = pair(root)
  local ok, problem = client:send(string.rep('x', 65))
  check(not ok and problem == 'INVALID_MESSAGE', 'the sender refuses an oversize record')
  local handle = assert(io.open(root .. '/c2w/000000001.msg', 'wb'))
  handle:write(string.rep('x', 65)); handle:close()
  client.send_sequence = 2  -- the injected record occupies sequence one
  local value, reason = worker:receive()
  check(value == nil and reason == 'MAILBOX_INVALID_MESSAGE', 'the reader reports an oversize record')
  check(client:send('after'), 'the sequence continues')
  check(worker:receive() == 'after', 'one bad record does not wedge the mailbox')
end
remove(root)

-- Liveness, in both directions: the sentinel the worker removes as it leaves,
-- and the stamp the client leaves while it polls.
root = scratch()
do
  local client = assert(Mailbox.open(root, 'c2w', 'w2c', { limit = 64 }))
  check(client:peer_present(), 'a running worker is present')
  check(exists(root .. '/claimed'), 'claiming leaves the worker a marker')
  local clock = 100
  client.now = function() return clock end
  client.heartbeat_at = nil
  client:heartbeat()
  check(exists(root .. '/alive'), 'polling stamps liveness')
  shell("rm -f '" .. root .. "/alive'")
  client:heartbeat()
  check(not exists(root .. '/alive'), 'stamping is throttled within the second')
  clock = 102
  client:heartbeat()
  check(exists(root .. '/alive'), 'a later second stamps again')
  shell("rm -f '" .. root .. "/up'")
  check(not client:peer_present(), 'a departed worker is observable')
end
remove(root)

-- Nothing is created before the arguments are known good.
do
  check(Mailbox.open('relative', 'c2w', 'w2c', { limit = 64 }) == nil, 'a relative root is refused')
  check(Mailbox.open('/tmp/rd/', 'c2w', 'w2c', { limit = 64 }) == nil, 'a trailing slash is refused')
  check(Mailbox.open('/tmp/rd', '../c2w', 'w2c', { limit = 64 }) == nil, 'a traversing direction is refused')
  check(Mailbox.open('/tmp/rd', 'c2w', 'c2w', { limit = 64 }) == nil, 'one direction cannot be both')
  check(Mailbox.open('/tmp/rd', 'c2w', 'w2c', { limit = 0 }) == nil, 'a zero limit is refused')
end

print('test_file_mailbox: ' .. passed .. ' tests passed')

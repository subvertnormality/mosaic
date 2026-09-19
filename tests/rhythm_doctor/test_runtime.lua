-- Runtime bridge integration checks, characterisation outside README.
package.path = './lib/?.lua;' .. package.path
local Runtime = require('rhythm_doctor.runtime')
local Bank = require('rhythm_doctor.bank')

local failures, count = {}, 0
local function test(name, body)
  count = count + 1
  local ok, err = pcall(body)
  if not ok then failures[#failures + 1] = name .. ': ' .. tostring(err) end
end
local function equal(actual, expected, message)
  assert(actual == expected, (message or 'values differ') .. ': expected ' .. tostring(expected) .. ', got ' .. tostring(actual))
end
local function check(value, message) assert(value, message or 'expected true') end

local function transport()
  local self = { sent = {}, replies = {}, closed = false }
  function self:send(message) self.sent[#self.sent + 1] = message; return true end
  function self:poll() if #self.replies == 0 then return nil end return table.remove(self.replies, 1) end
  function self:close() self.closed = true end
  return self
end
local function response(request, status)
  return { protocol_version = request.protocol_version, job_id = request.job_id, project_id = request.project_id,
    generation = request.generation, analysis_revision = request.analysis_revision, command = request.command, status = status }
end
local function context()
  local socket, worker, statuses = transport(), { opens = 0, closes = 0 }, {}
  function worker:open() self.opens = self.opens + 1; return socket end
  function worker:close() self.closes = self.closes + 1 end
  local runtime = Runtime.new({ project_id = 'project-a', worker = worker, now = function() return 0 end,
    transport_stopped = function() return true end, on_status = function(code) statuses[#statuses + 1] = code end })
  return runtime, socket, worker, statuses
end

test('enter opens injected nonblocking worker exactly once and record owns controller', function()
  local runtime, socket, worker = context()
  check(runtime:enter().ok)
  check(runtime:enter().ok)
  equal(worker.opens, 1)
  check(runtime:start_capture('manual').ok)
  equal(socket.sent[1].command, 'PREFLIGHT')
end)

test('failed worker startup cannot put the machine into a capture state', function()
  local worker = { open = function() return nil, 'no socket' end }
  local runtime = Runtime.new({ project_id = 'project-a', worker = worker, now = function() return 0 end,
    transport_stopped = function() return true end })
  equal(runtime:start_capture('manual').code, 'WORKER_UNAVAILABLE')
  equal(runtime.machine.state, 'EMPTY')
end)

test('mode entry retries a background worker from bounded polls', function()
  local socket, opens, now = transport(), 0, 0
  local worker = { open = function()
    opens = opens + 1
    if opens < 3 then return nil, 'worker starting' end
    return socket
  end }
  local runtime = Runtime.new({ project_id = 'project-a', worker = worker, now = function() return now end,
    transport_stopped = function() return true end })
  equal(runtime:enter().code, 'WORKER_UNAVAILABLE')
  runtime:poll(); equal(opens, 1, 'rapid polls do not thrash worker connection setup')
  now = .25; runtime:poll(); equal(runtime.machine.state, 'EMPTY')
  now = .50; runtime:poll(); equal(opens, 3)
  check(runtime:start_capture('manual').ok)
end)

test('cleanup waits for native release acknowledgement before closing worker', function()
  local runtime, socket, worker = context()
  runtime:start_capture('manual')
  local preflight = socket.sent[#socket.sent]
  socket.replies[#socket.replies + 1] = response(preflight, 'READY')
  runtime:poll()
  local started = socket.sent[#socket.sent]
  socket.replies[#socket.replies + 1] = response(started, 'STARTED')
  runtime:poll()
  equal(runtime:cleanup().code, 'RELEASING')
  equal(worker.closes, 0)
  local release = socket.sent[#socket.sent]
  equal(release.command, 'RELEASE')
  socket.replies[#socket.replies + 1] = response(release, 'RELEASED')
  runtime:poll()
  equal(worker.closes, 1)
  check(socket.closed)
end)

test('project replacement is deferred by the machine then receives the new identity', function()
  local runtime, socket = context()
  runtime:start_capture('manual')
  local called = false
  equal(runtime:prepare_project_change(function() called = true end).code, 'DEFERRED')
  local release = socket.sent[#socket.sent]
  socket.replies[#socket.replies + 1] = response(release, 'RELEASED')
  runtime:poll()
  check(called)
  check(runtime:project_loaded('project-b').ok)
  equal(runtime.machine.project_id, Runtime.project_identity('project-b'))
end)

test('READY controls clamp the shared window, rebuild one lane sensitivity, and start alignment reanalysis', function()
  local runtime = select(1, context())
  local bank = assert(Bank.build({ project_id = runtime.machine.project_id, generation = 0, analysis_revision = 0,
    sample_rate = 100, capture_start_sample = 0, capture_end_sample = 1000, origin_sample = 0, bpm = 120,
    sensitivities = { BD = .2, SD = .2, CHH = .2, OHH = .2, BASS = .2 },
    candidates = { { lane = 'BD', sample_index = 10, velocity = 80, confidence = .3 } } }))
  runtime.machine.state, runtime.machine.bank = 'READY', bank
  equal(runtime:set_window_start(999).code, 'WINDOW_MOVED')
  equal(runtime.machine.bank.window_start, 16, 'longest 64-cell view is retained')
  equal(runtime:set_sensitivity('BD', .4).code, 'SENSITIVITY_UPDATED')
  equal(runtime.machine.bank.sensitivities.BD, .4); equal(runtime.machine.bank.sensitivities.SD, .2)
  local value = runtime:apply_alignment({ bpm = 60, start_beat = 1, fine_start_ms = 0, origin_sample = 0 })
  check(value.ok); equal(runtime.machine.state, 'REANALYSING')
  equal(runtime.machine.analysis_revision, 1)
end)

if #failures > 0 then io.stderr:write(table.concat(failures, '\n') .. '\n'); os.exit(1) end
print('rhythm_doctor runtime: ' .. count .. ' tests passed')

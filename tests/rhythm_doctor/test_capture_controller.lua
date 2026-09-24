-- Controller contract: injected transport only. No native IPC or app wiring is implied.
package.path = './lib/?.lua;' .. package.path
local Machine = require('rhythm_doctor.state_machine')
local Controller = require('rhythm_doctor.capture_controller')

local errors, count = {}, 0
local function test(name, body)
  count = count + 1
  local ok, err = pcall(body)
  if not ok then errors[#errors + 1] = name .. ': ' .. tostring(err) end
end
local function equal(actual, expected, message)
  assert(actual == expected, (message or 'values differ') .. ': expected ' .. tostring(expected) .. ', got ' .. tostring(actual))
end
local function check(value, message) assert(value, message or 'expected true') end

local function fake_transport()
  local self = { sent = {}, replies = {}, hook = nil }
  function self:send(message)
    self.sent[#self.sent + 1] = message
    if self.hook then self.hook(message) end
    return true
  end
  function self:poll()
    if #self.replies == 0 then return nil end
    return table.remove(self.replies, 1)
  end
  return self
end

local function reply(message, status, extra)
  local response = {
    protocol_version = message.protocol_version,
    job_id = message.job_id,
    project_id = message.project_id,
    generation = message.generation,
    analysis_revision = message.analysis_revision,
    command = message.command,
    status = status,
  }
  for key, value in pairs(extra or {}) do response[key] = value end
  return response
end

local function controller_context()
  local now, statuses, saved, analysed = 0, {}, {}, {}
  local transport = fake_transport()
  local controller, machine
  machine = Machine.new{
    project_id = 'project-a',
    on_capture_start = function(mode, token) controller:begin(mode, token, 45) end,
    on_analyse = function(token) controller:analyse(token) end,
    on_reanalyse = function(token) controller:analyse(token) end,
    on_cancel = function(token) controller:cancel(token) end,
    on_release = function(token) controller:release(token) end,
  }
  controller = Controller.new{
    machine = machine,
    transport = transport,
    now = function() return now end,
    transport_stopped = function() return true end,
    on_status = function(code) statuses[#statuses + 1] = code end,
    on_capture_saved = function(asset) saved[#saved + 1] = asset end,
    on_analysis_ready = function(asset) analysed[#analysed + 1] = asset end,
    job_prefix = 'test',
  }
  return {
    machine = machine, controller = controller, transport = transport,
    statuses = statuses, saved = saved, analysed = analysed,
    set_now = function(value) now = value end,
  }
end

local function start_ready(context)
  check(context.machine:start_capture('manual', true).ok)
  local preflight = context.transport.sent[#context.transport.sent]
  equal(preflight.command, 'PREFLIGHT')
  context.transport.replies[#context.transport.replies + 1] = reply(preflight, 'READY')
  equal(context.controller:poll().code, 'READY')
  local started = context.transport.sent[#context.transport.sent]
  equal(started.command, 'START')
  context.transport.replies[#context.transport.replies + 1] = reply(started, 'STARTED')
  equal(context.controller:poll().code, 'STARTED')
  return context.machine:job_token(), started
end

test('full identity rejects stale reply and only matching reply starts capture', function()
  local c = controller_context()
  check(c.machine:start_capture('manual', true).ok)
  local preflight = c.transport.sent[#c.transport.sent]
  for _, stale in ipairs({
    reply(preflight, 'READY', { job_id = 'other-job' }),
    reply(preflight, 'READY', { project_id = 'other-project' }),
    reply(preflight, 'READY', { generation = preflight.generation + 1 }),
    reply(preflight, 'READY', { analysis_revision = preflight.analysis_revision + 1 }),
  }) do
    c.transport.replies[#c.transport.replies + 1] = stale
    equal(c.controller:poll().code, 'STALE_REPLY')
    equal(#c.transport.sent, 1, 'stale ready cannot start a job')
  end
  c.transport.replies[#c.transport.replies + 1] = reply(preflight, 'READY')
  c.controller:poll()
  equal(c.transport.sent[#c.transport.sent].command, 'START')
end)

test('synchronous Start cancellation leaves no active capture and releases only on acknowledgement', function()
  local c = controller_context()
  c.transport.hook = function(message)
    if message.command == 'START' then c.machine:transport_started() end
  end
  check(c.machine:start_capture('manual', true).ok)
  local preflight = c.transport.sent[#c.transport.sent]
  c.transport.replies[#c.transport.replies + 1] = reply(preflight, 'READY')
  equal(c.controller:poll().code, 'STALE_JOB')
  equal(c.machine.state, 'EMPTY')
  check(not c.machine.resources_are_released, 'cancellation requests release but cannot acknowledge it')
  local release = c.transport.sent[#c.transport.sent]
  equal(release.command, 'RELEASE')
  c.transport.replies[#c.transport.replies + 1] = reply(release, 'RELEASED')
  equal(c.controller:poll().code, 'RELEASED')
  check(c.machine.resources_are_released, 'only matching RELEASED acknowledges release')
end)

test('release deadline is visible and never fabricates an acknowledgement', function()
  local c = controller_context()
  local token = start_ready(c)
  c.machine:transport_started()
  local release = c.transport.sent[#c.transport.sent]
  equal(release.command, 'RELEASE')
  c.set_now(2.0)
  equal(c.controller:poll().code, 'RELEASE_TIMEOUT')
  equal(c.statuses[#c.statuses], 'CAPTURE_RELEASE_TIMEOUT')
  check(not c.machine.resources_are_released)
  c.transport.replies[#c.transport.replies + 1] = reply(release, 'RELEASED', { generation = token.generation + 1 })
  equal(c.controller:poll().code, 'STALE_REPLY')
  check(not c.machine.resources_are_released)
  c.transport.replies[#c.transport.replies + 1] = reply(release, 'RELEASED')
  equal(c.controller:poll().code, 'RELEASED')
  check(c.machine.resources_are_released)
end)

test('matching native failure routes through capture_failed then release', function()
  local c = controller_context()
  local token, started = start_ready(c)
  c.transport.replies[#c.transport.replies + 1] = reply(started, 'FAILED', { capture_error = 'XRUN' })
  equal(c.controller:poll().code, 'FAILED')
  equal(c.machine.state, 'FAILED')
  equal(c.machine.last_message, 'XRUN')
  local release = c.transport.sent[#c.transport.sent]
  equal(release.command, 'RELEASE')
  c.transport.replies[#c.transport.replies + 1] = reply(release, 'RELEASED')
  c.controller:poll()
  check(c.machine.resources_are_released)
end)

test('timeout publishes a same-job asset before invalid and valid machine transitions', function()
  for _, valid_span in ipairs({ false, true }) do
    local c = controller_context()
    local token, started = start_ready(c)
    c.transport.replies[#c.transport.replies + 1] = reply(started, 'COMPLETED')
    equal(c.controller:poll().code, 'COMPLETED')
    equal(c.controller:timeout(token, valid_span).code, 'PUBLISHING')
    local publish = c.transport.sent[#c.transport.sent]
    equal(publish.command, 'PUBLISH')
    c.transport.replies[#c.transport.replies + 1] = reply(publish, 'PUBLISHED', { wav_path = '/tmp/test.wav', wav_sha256 = string.rep('a', 64), frames = 10, sample_rate = 8000 })
    equal(c.controller:poll().code, 'PUBLISHED')
    equal(#c.saved, 1)
    if valid_span then
      equal(c.machine.state, 'ANALYSING')
      equal(#c.analysed, 1, 'valid timeout invokes the injected analysis callback only after publish')
    else
      equal(c.machine.state, 'ALIGNMENT_REQUIRED')
      equal(#c.analysed, 0, 'invalid timeout never starts analysis')
      local release = c.transport.sent[#c.transport.sent]
      equal(release.command, 'RELEASE')
    end
  end
end)

test('manual Finish stops, completes, publishes, and dispatches only after the matching asset', function()
  local c = controller_context()
  local token = start_ready(c)
  check(c.machine:finish_capture(true, true).ok)
  equal(c.machine.state, 'ANALYSING')
  local stop = c.transport.sent[#c.transport.sent]
  equal(stop.command, 'STOP')
  c.transport.replies[#c.transport.replies + 1] = reply(stop, 'COMPLETED')
  equal(c.controller:poll().code, 'PUBLISHING')
  local publish = c.transport.sent[#c.transport.sent]
  equal(publish.command, 'PUBLISH')
  c.transport.replies[#c.transport.replies + 1] = reply(publish, 'PUBLISHED', { wav_path = '/tmp/finish.wav', wav_sha256 = string.rep('b', 64), frames = 10, sample_rate = 8000 })
  equal(c.controller:poll().code, 'PUBLISHED')
  equal(#c.saved, 1)
  equal(#c.analysed, 1)
  equal(c.analysed[1].job_id, c.saved[1].job_id)
end)

test('alignment release acknowledgement can be followed by a new analysis release', function()
  local c = controller_context()
  local token, started = start_ready(c)
  c.transport.replies[#c.transport.replies + 1] = reply(started, 'COMPLETED')
  c.controller:poll(); c.controller:timeout(token, false)
  local publish = c.transport.sent[#c.transport.sent]
  c.transport.replies[#c.transport.replies + 1] = reply(publish, 'PUBLISHED', { wav_path = '/tmp/alignment.wav', wav_sha256 = string.rep('c', 64), frames = 10, sample_rate = 8000 })
  c.controller:poll()
  local first_release = c.transport.sent[#c.transport.sent]
  equal(first_release.command, 'RELEASE')
  c.transport.replies[#c.transport.replies + 1] = reply(first_release, 'RELEASED')
  c.controller:poll(); check(c.machine.resources_are_released)
  check(c.machine:finish_capture(true, true).ok)
  equal(#c.analysed, 1)
  c.machine:receive_analysis({ project_id = token.project_id, generation = token.generation, analysis_revision = token.analysis_revision, error = 'analysis failed' })
  local second_release = c.transport.sent[#c.transport.sent]
  equal(second_release.command, 'RELEASE')
  check(second_release ~= first_release, 'a new release request is required for the new lease')
  c.transport.replies[#c.transport.replies + 1] = reply(second_release, 'RELEASED')
  equal(c.controller:poll().code, 'RELEASED')
  check(c.machine.resources_are_released)
end)

test('duplicate ready is rejected and stale replies cannot starve the release deadline', function()
  local c = controller_context()
  local token, started = start_ready(c)
  c.transport.replies[#c.transport.replies + 1] = reply(c.transport.sent[1], 'READY')
  equal(c.controller:poll().code, 'FAILED')
  equal(c.machine.state, 'FAILED')
  local release = c.transport.sent[#c.transport.sent]
  c.set_now(2.0)
  c.transport.replies[#c.transport.replies + 1] = reply(release, 'RELEASED', { job_id = 'stale' })
  equal(c.controller:poll().code, 'RELEASE_TIMEOUT')
  equal(c.statuses[#c.statuses], 'CAPTURE_RELEASE_TIMEOUT')
  check(not c.machine.resources_are_released)
end)

test('malformed published asset is rejected before any save callback', function()
  local c = controller_context()
  local token, started = start_ready(c)
  c.transport.replies[#c.transport.replies + 1] = reply(started, 'COMPLETED')
  c.controller:poll(); c.controller:timeout(token, true)
  local publish = c.transport.sent[#c.transport.sent]
  c.transport.replies[#c.transport.replies + 1] = reply(publish, 'PUBLISHED', { wav_path = 'relative.wav', wav_sha256 = 'bad', frames = 1.5, sample_rate = 0 })
  equal(c.controller:poll().code, 'FAILED')
  equal(#c.saved, 0)
  equal(#c.analysed, 0)
end)
test('transport send must explicitly return true', function()
  local c = controller_context()
  c.transport.send = function(self, message) self.sent[#self.sent + 1] = message end
  check(c.machine:start_capture('manual', true).ok)
  equal(c.machine.state, 'FAILED')
  equal(c.statuses[#c.statuses], 'CAPTURE_TRANSPORT_SEND_FAILED')
end)

test('late publish after cancellation cannot invoke save or analysis callbacks', function()
  local c = controller_context()
  local token, started = start_ready(c)
  c.machine:transport_started()
  c.transport.replies[#c.transport.replies + 1] = reply(started, 'PUBLISHED', { wav_path = '/tmp/late.wav', wav_sha256 = string.rep('d', 64), frames = 10, sample_rate = 8000 })
  equal(c.controller:poll().code, 'STALE_JOB')
  equal(#c.saved, 0)
  equal(#c.analysed, 0)
end)
test('a reanalysis lease releases under the recorder identity, not the new revision', function()
  -- The recorder adopts one identity at PREFLIGHT and compares every later
  -- command against it, revision included. A confirmed alignment advances the
  -- analysis revision, so RELEASE was sent under an identity the recorder had
  -- never adopted: it answered STALE_JOB, the release was never acknowledged,
  -- and the capture lease, saves and project changes stayed blocked.
  local Bank = require('rhythm_doctor.bank')
  local c = controller_context()
  local token, started = start_ready(c)
  local preflight_revision = c.transport.sent[1].analysis_revision
  equal(c.transport.sent[1].command, 'PREFLIGHT')

  c.transport.replies[#c.transport.replies + 1] = reply(started, 'COMPLETED')
  c.controller:poll(); c.controller:timeout(token, false)
  local publish = c.transport.sent[#c.transport.sent]
  c.transport.replies[#c.transport.replies + 1] = reply(publish, 'PUBLISHED',
    { wav_path = '/tmp/r2.wav', wav_sha256 = string.rep('f', 64), frames = 64000, sample_rate = 8000 })
  c.controller:poll()
  local release = c.transport.sent[#c.transport.sent]
  equal(release.command, 'RELEASE')
  c.transport.replies[#c.transport.replies + 1] = reply(release, 'RELEASED')
  c.controller:poll()

  check(c.machine:finish_capture(true, true).ok)
  local bank = assert(Bank.build{ project_id = token.project_id, generation = token.generation,
    analysis_revision = token.analysis_revision, sample_rate = 8000, capture_start_sample = 0,
    capture_end_sample = 64000, origin_sample = 0, bpm = 120 })
  check(c.machine:receive_analysis({ project_id = token.project_id, generation = token.generation,
    analysis_revision = token.analysis_revision, bank = bank }).ok)
  equal(c.machine.state, 'READY')
  -- Acknowledge the release this lease asked for, through the controller, so
  -- the recorder is not still holding an unanswered request.
  local ready_release = c.transport.sent[#c.transport.sent]
  equal(ready_release.command, 'RELEASE')
  c.transport.replies[#c.transport.replies + 1] = reply(ready_release, 'RELEASED')
  c.controller:poll()
  check(c.machine.resources_are_released)

  -- A confirmed alignment asks for the same audio under a new analysis lease.
  check(c.machine:begin_reanalysis(true).ok)
  local advanced = c.machine:job_token()
  check(advanced.analysis_revision > preflight_revision,
    'reanalysis must advance the analysis revision')

  -- The controller adopts the new lease for the reanalysis dispatch.
  equal(c.controller:analyse(advanced).code, 'ANALYSIS_READY')
  equal(c.analysed[#c.analysed].analysis_revision, advanced.analysis_revision,
    'the analysis lease must carry the new revision')

  -- Failing that reanalysis makes the machine release the lease. The release
  -- must still address the recorder by the identity it adopted at PREFLIGHT,
  -- or it answers STALE_JOB and never lets go of its input.
  local sent_before = #c.transport.sent
  c.machine:receive_analysis({ project_id = advanced.project_id, generation = advanced.generation,
    analysis_revision = advanced.analysis_revision, error = 'analysis failed' })
  check(#c.transport.sent > sent_before, 'the failed reanalysis never asked for a release')
  local reanalysis_release = c.transport.sent[#c.transport.sent]
  equal(reanalysis_release.command, 'RELEASE')
  equal(reanalysis_release.analysis_revision, preflight_revision,
    'RELEASE was sent under a revision the recorder never adopted')

  -- The recorder echoes the identity it adopted; that reply must be accepted
  -- and must release the machine's current lease.
  c.transport.replies[#c.transport.replies + 1] = reply(reanalysis_release, 'RELEASED')
  equal(c.controller:poll().code, 'RELEASED')
  check(c.machine.resources_are_released, 'the lease was never released')
end)

if #errors > 0 then
  io.stderr:write(table.concat(errors, '\n') .. '\n')
  os.exit(1)
end
print('rhythm_doctor capture_controller: ' .. count .. ' tests passed')

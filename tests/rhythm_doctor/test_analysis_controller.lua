-- Analysis-worker protocol contract. This is characterisation outside the
-- README: it proves that a worker result cannot create READY by identity alone.
package.path = './lib/?.lua;' .. package.path
local Bank = require('rhythm_doctor.bank')
local Machine = require('rhythm_doctor.state_machine')
local Controller = require('rhythm_doctor.analysis_controller')

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

local function transport()
  local self = { sent = {}, replies = {} }
  function self:send(message) self.sent[#self.sent + 1] = message; return true end
  function self:poll() if #self.replies == 0 then return nil end return table.remove(self.replies, 1) end
  return self
end
local function response(request, status, extra)
  local message = { protocol_version=request.protocol_version, job_id=request.job_id, project_id=request.project_id,
    generation=request.generation, analysis_revision=request.analysis_revision, command=request.command, status=status }
  for key, value in pairs(extra or {}) do message[key] = value end
  return message
end
local function ready_bank(token)
  return assert(Bank.build({ project_id=token.project_id, generation=token.generation, analysis_revision=token.analysis_revision,
    sample_rate=8000, capture_start_sample=0, capture_end_sample=200000, origin_sample=8000, bpm=100,
    candidates={{lane='BD', sample_index=8000, velocity=100, confidence=1}} }))
end
local function context()
  local machine = Machine.new({project_id='project-a'})
  machine.generation = 3; machine.analysis_revision = 2; machine.resources_are_released = false
  machine:_set_state(Machine.ANALYSING)
  local wire = transport()
  return machine, wire, Controller.new({machine=machine, transport=wire, job_prefix='analysis-test'})
end
local function asset(token)
  return {wav_path='/tmp/rd.wav', wav_sha256=string.rep('a', 64), frames=200000, sample_rate=8000,
    project_id=token.project_id, generation=token.generation, analysis_revision=token.analysis_revision}
end

test('dispatch includes bounded asset and complete job identity', function()
  local machine, wire, controller = context(); local token = machine:job_token()
  equal(controller:dispatch(asset(token), token).code, 'DISPATCHED')
  local request = wire.sent[1]
  equal(request.command, 'ANALYSE'); equal(request.protocol_version, 1)
  equal(request.job_id, 'analysis-test-1'); equal(request.project_id, token.project_id)
  equal(request.generation, token.generation); equal(request.analysis_revision, token.analysis_revision)
  equal(request.result_schema_version, Bank.VERSION); equal(request.max_candidates, Bank.MAX_CANDIDATES)
  equal(request.frames, 200000); equal(request.sample_rate, 8000)
  check(not controller:dispatch(asset(token), token).ok, 'one active analysis token has one invocation')
end)

test('mismatched identity and a late result cannot change the active bank', function()
  local machine, wire, controller = context(); local token = machine:job_token()
  controller:dispatch(asset(token), token); local request = wire.sent[1]
  wire.replies[#wire.replies + 1] = response(request, 'COMPLETED', {job_id='other', bank=ready_bank(token), wav_sha256=request.wav_sha256, frames=request.frames, sample_rate=request.sample_rate})
  equal(controller:poll().code, 'STALE_REPLY'); equal(machine.state, 'ANALYSING')
  machine:transport_started()
  wire.replies[#wire.replies + 1] = response(request, 'COMPLETED', {bank=ready_bank(token), wav_sha256=request.wav_sha256, frames=request.frames, sample_rate=request.sample_rate})
  equal(controller:poll().code, 'STALE_RESULT'); equal(machine.state, 'EMPTY'); check(machine.bank == nil)
end)

test('a result must contain the complete ready-bank schema before forwarding', function()
  local machine, wire, controller = context(); local token = machine:job_token()
  controller:dispatch(asset(token), token); local request = wire.sent[1]
  wire.replies[#wire.replies + 1] = response(request, 'COMPLETED', {bank={project_id=token.project_id}, wav_sha256=request.wav_sha256, frames=request.frames, sample_rate=request.sample_rate})
  equal(controller:poll().code, 'INVALID_BANK'); equal(machine.state, 'FAILED'); check(machine.bank == nil)
end)

test('a result cannot reinterpret the published WAV at a different sample rate', function()
  local machine, wire, controller = context(); local token = machine:job_token()
  controller:dispatch(asset(token), token); local request = wire.sent[1]
  local other_rate = assert(Bank.build({ project_id=token.project_id, generation=token.generation, analysis_revision=token.analysis_revision,
    sample_rate=16000, capture_start_sample=0, capture_end_sample=400000, origin_sample=16000, bpm=100,
    candidates={{lane='BD', sample_index=16000, velocity=100, confidence=1}} }))
  wire.replies[#wire.replies + 1] = response(request, 'COMPLETED', {bank=other_rate, wav_sha256=request.wav_sha256, frames=request.frames, sample_rate=request.sample_rate})
  equal(controller:poll().code, 'INVALID_BANK'); equal(machine.state, 'FAILED')
end)

test('a matching, schema-valid result alone can complete the analysis transition', function()
  local machine, wire, controller = context(); local token = machine:job_token()
  controller:dispatch(asset(token), token); local request = wire.sent[1]
  wire.replies[#wire.replies + 1] = response(request, 'COMPLETED', {bank=ready_bank(token), wav_sha256=request.wav_sha256, frames=request.frames, sample_rate=request.sample_rate})
  equal(controller:poll().code, 'COMPLETED'); equal(machine.state, 'READY'); equal(machine.bank.project_id, token.project_id)
end)

if #errors > 0 then io.stderr:write(table.concat(errors, '\n') .. '\n'); os.exit(1) end
print('rhythm_doctor analysis_controller: ' .. count .. ' tests passed')

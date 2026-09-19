package.path = './lib/?.lua;' .. package.path

-- The transport reaches the socket through LuaJIT's ffi. Its result validator
-- is pure Lua, so stub the C boundary to bring that validator under test on
-- the 5.3 interpreter the component runner uses.
package.preload['ffi'] = function()
  return { cdef=function() end, C=setmetatable({}, {__index=function() return function() return -1 end end}),
    errno=function() return 11 end, string=function() return '' end, new=function() return {} end }
end
package.preload['bit'] = function() return { bor=function(a,b) return a+b end } end
local Transport = require('rhythm_doctor.analysis_transport')
local json = require('helpers.json')
local Bank = require('rhythm_doctor.bank')

-- The transport is the last gate a completed analysis passes before it becomes
-- a bank. It had never been exercised here, and it demanded model artifact
-- digests that the shipped classical-DSP backend does not have: every real
-- capture was rejected as a protocol error.

local SHA = string.rep('a', 64)

local function gates()
  local value = {}
  for _, lane in ipairs(Bank.LANES) do value[lane] = 0.4 end
  return value
end

-- Build a transport that reads one injected result file instead of a socket.
local function transport_reading(stored)
  local self = setmetatable({ fd = -1, queue = {}, result_root = '/results',
    read_file = function() return json.encode(stored) end }, { __index = Transport })
  return self
end

local function envelope()
  return { protocol_version=1, job_id='job-1', project_id='proj-1', generation=1,
    analysis_revision=1, command='ANALYSE', status='COMPLETED',
    result_path='/results/job-1.json', wav_path='/captures/one.wav',
    wav_sha256=string.rep('b', 64), frames=44100 * 20, sample_rate=44100 }
end

local function stored_with(detector)
  local value = envelope()
  value.analysis = { bpm=120.0, tempo_mode='AUTOMATIC', origin_sample=0, detector=detector,
    lane_onset_gates=gates(), candidates={} }
  return value
end

-- The shipped DSP identity: its own source plus the template table it reads.
local dsp = stored_with({ backend_id='nmf-pfnmf-drums-v1', backend_sha256=SHA,
  template_sha256=string.rep('c', 64) })
local out = transport_reading(dsp):_completed(envelope())
assert(out.status == 'COMPLETED',
  'a completed DSP analysis was rejected at the transport: ' .. tostring(out.analysis_error))
assert(out.bank ~= nil, 'no bank was built from a valid DSP analysis')

-- The pretrained identity shape stays supported.
local pretrained = stored_with({ backend_id='pretrained-composite', backend_sha256=SHA,
  drum_artifact_sha256=string.rep('d', 64), bass_artifact_sha256=string.rep('e', 64) })
assert(transport_reading(pretrained):_completed(envelope()).status == 'COMPLETED',
  'the pretrained identity shape stopped being accepted')

-- Half an identity, or two mixed together, is a configuration error and must
-- fail closed rather than pin less than a whole shape.
local partial = stored_with({ backend_id='x', backend_sha256=SHA })
assert(transport_reading(partial):_completed(envelope()).analysis_error == 'ANALYSIS_PROTOCOL_ERROR',
  'a detector pinning neither templates nor artifacts was accepted')

local mixed = stored_with({ backend_id='x', backend_sha256=SHA, template_sha256=string.rep('c', 64),
  drum_artifact_sha256=string.rep('d', 64), bass_artifact_sha256=string.rep('e', 64) })
assert(transport_reading(mixed):_completed(envelope()).analysis_error == 'ANALYSIS_PROTOCOL_ERROR',
  'a detector mixing both identity shapes was accepted')

local malformed = stored_with({ backend_id='x', backend_sha256=SHA, template_sha256='not-a-digest' })
assert(transport_reading(malformed):_completed(envelope()).analysis_error == 'ANALYSIS_PROTOCOL_ERROR',
  'a malformed template digest was accepted')

-- A correction the player confirmed comes back as a manual tempo, and must
-- build a bank at that tempo rather than being rejected or silently reset.
local corrected = stored_with({ backend_id='nmf-pfnmf-drums-v1', backend_sha256=SHA,
  template_sha256=string.rep('c', 64) })
corrected.analysis.bpm = 77.0
corrected.analysis.tempo_mode = 'manual'
corrected.analysis.origin_sample = 12345
local built = transport_reading(corrected):_completed(envelope())
assert(built.status == 'COMPLETED',
  'a confirmed correction was rejected: ' .. tostring(built.analysis_error))
assert(built.bank.bpm == 77.0, 'the bank did not keep the confirmed tempo')
assert(built.bank.tempo_mode == 'manual', 'the bank did not record a manual tempo')

print('test_analysis_transport: 9 tests passed')

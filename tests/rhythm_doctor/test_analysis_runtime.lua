-- Capture publication -> analysis invocation -> validated bank integration.
-- Characterisation outside README; detector quality is intentionally out of scope.
package.path = './lib/?.lua;' .. package.path
local Bank = require('rhythm_doctor.bank')
local Runtime = require('rhythm_doctor.runtime')

local function transport()
  local self = {sent={}, replies={}}
  function self:send(message) self.sent[#self.sent+1]=message; return true end
  function self:poll() if #self.replies == 0 then return nil end return table.remove(self.replies, 1) end
  return self
end
local function reply(request, status, extra)
  local value={protocol_version=request.protocol_version,job_id=request.job_id,project_id=request.project_id,
    generation=request.generation,analysis_revision=request.analysis_revision,command=request.command,status=status}
  for key, item in pairs(extra or {}) do value[key]=item end
  return value
end
local capture, analysis = transport(), transport()
local worker={open=function() return capture end}
local analysis_opens=0
local analysis_worker={open=function() analysis_opens=analysis_opens+1; return analysis end}
local legacy_dispatches=0
local runtime=Runtime.new({project_id='analysis-project',worker=worker,analysis_worker=analysis_worker,now=function() return 0 end,
  transport_stopped=function() return true end,
  on_analysis_ready=function() legacy_dispatches=legacy_dispatches+1 end})
assert(runtime:start_capture('manual').ok)
assert(analysis_opens==1,'mode entry preflights the owned analysis worker')
local preflight=capture.sent[#capture.sent]; capture.replies[#capture.replies+1]=reply(preflight,'READY'); runtime:poll()
local start=capture.sent[#capture.sent]; capture.replies[#capture.replies+1]=reply(start,'STARTED'); runtime:poll()
assert(runtime:finish(true).ok)
local stop=capture.sent[#capture.sent]; capture.replies[#capture.replies+1]=reply(stop,'COMPLETED'); runtime:poll()
local publish=capture.sent[#capture.sent]
capture.replies[#capture.replies+1]=reply(publish,'PUBLISHED',{wav_path='/tmp/integration.wav',wav_sha256=string.rep('b',64),frames=200000,sample_rate=8000})
runtime:poll()
local request=analysis.sent[#analysis.sent]
assert(request.command=='ANALYSE' and request.result_schema_version==Bank.VERSION and request.max_candidates==Bank.MAX_CANDIDATES)
assert(analysis_opens==1,'capture publication reuses the preflighted analysis worker')
assert(legacy_dispatches==0,'injected analysis transport exclusively owns dispatch')
local bank=assert(Bank.build({project_id=request.project_id,generation=request.generation,analysis_revision=request.analysis_revision,
  sample_rate=8000,capture_start_sample=0,capture_end_sample=200000,origin_sample=8000,bpm=100,
  candidates={{lane='BD',sample_index=8000,velocity=100,confidence=1}}}))
analysis.replies[#analysis.replies+1]=reply(request,'COMPLETED',{bank=bank,wav_sha256=request.wav_sha256,frames=request.frames,sample_rate=request.sample_rate})
runtime:poll()
assert(runtime.machine.state=='READY' and runtime.machine.bank==bank,'only a matching full bank reaches READY')
local release=capture.sent[#capture.sent]; assert(release.command=='RELEASE')
capture.replies[#capture.replies+1]=reply(release,'RELEASED'); runtime:poll()
assert(runtime.machine.resources_are_released)
assert(runtime:apply_alignment({bpm=50,start_beat=1,fine_start_ms=0,origin_sample=8000}).ok)
local corrected=analysis.sent[#analysis.sent]
assert(corrected.command=='ANALYSE' and corrected.analysis_revision==1)
assert(corrected.alignment.bpm==50 and corrected.alignment.origin_sample==8000,
  'a correction carries its frozen alignment to the new analysis lease')
print('rhythm_doctor analysis_runtime: 1 test passed')

-- A capture can finish before the analysis worker is ready. The worker builds
-- its backend on first use, which takes tens of seconds on a device, and the
-- publication used to be dropped on the floor: no controller existed yet, so
-- nothing was dispatched and the bank sat in ANALYSING with nothing coming.
do
  local late_capture, late_analysis = transport(), transport()
  local ready = false
  local opens = 0
  local late = Runtime.new({ project_id = 'late-worker', worker = { open = function() return late_capture end },
    analysis_worker = { open = function()
      opens = opens + 1
      if not ready then return nil, 'analysis worker starting' end
      return late_analysis
    end },
    now = function() return 0 end, transport_stopped = function() return true end })

  late:enter()   -- entering the page is what preflights the analysis worker
  assert(late:start_capture('manual').ok)
  local pre = late_capture.sent[#late_capture.sent]
  late_capture.replies[#late_capture.replies + 1] = reply(pre, 'READY'); late:poll()
  local started = late_capture.sent[#late_capture.sent]
  late_capture.replies[#late_capture.replies + 1] = reply(started, 'STARTED'); late:poll()
  assert(late:finish(true).ok)
  local stopped = late_capture.sent[#late_capture.sent]
  late_capture.replies[#late_capture.replies + 1] = reply(stopped, 'COMPLETED'); late:poll()
  local published = late_capture.sent[#late_capture.sent]
  late_capture.replies[#late_capture.replies + 1] = reply(published, 'PUBLISHED',
    { wav_path = '/tmp/late.wav', wav_sha256 = string.rep('c', 64), frames = 200000, sample_rate = 8000 })
  late:poll()
  assert(#late_analysis.sent == 0, 'nothing can be dispatched before the worker exists')
  assert(late.machine.state == 'ANALYSING', 'the capture is waiting on analysis')

  -- The worker comes up. The retained request must be dispatched, exactly once.
  ready = true
  late.analysis_retry_at = 0
  late:poll()
  assert(#late_analysis.sent == 1,
    'the publication held while the worker started must be dispatched when it is ready, got ' .. #late_analysis.sent)
  local held = late_analysis.sent[1]
  assert(held.command == 'ANALYSE' and held.wav_sha256 == string.rep('c', 64), 'and it must be the capture that was published')
  late.analysis_retry_at = 0
  late:poll()
  assert(#late_analysis.sent == 1, 'and dispatched once, not again on every later poll')
end

print('analysis runtime: late worker readiness covered')

-- A backend that fails to build is terminal, not slow. Retrying it forever
-- left the capture in ANALYSING with saving blocked until the player thought
-- to cancel, and nothing on screen said the build had failed.
do
  local cap, failed_worker = transport(), nil
  local runtime = Runtime.new({ project_id = 'build-fails', worker = { open = function() return cap end },
    analysis_worker = { open = function()
      return nil, 'native analysis backend build failed: gcc not found', true
    end },
    now = function() return 0 end, transport_stopped = function() return true end })
  runtime:enter()
  assert(runtime:start_capture('manual').ok)
  local pre = cap.sent[#cap.sent]; cap.replies[#cap.replies + 1] = reply(pre, 'READY'); runtime:poll()
  local started = cap.sent[#cap.sent]; cap.replies[#cap.replies + 1] = reply(started, 'STARTED'); runtime:poll()
  assert(runtime:finish(true).ok)
  local stopped = cap.sent[#cap.sent]; cap.replies[#cap.replies + 1] = reply(stopped, 'COMPLETED'); runtime:poll()
  local published = cap.sent[#cap.sent]
  cap.replies[#cap.replies + 1] = reply(published, 'PUBLISHED',
    { wav_path = '/tmp/nobuild.wav', wav_sha256 = string.rep('d', 64), frames = 200000, sample_rate = 8000 })
  runtime:poll()
  runtime.analysis_retry_at = 0
  runtime:poll()
  assert(runtime.machine.state ~= 'ANALYSING',
    'a backend that cannot be built must fail the capture, not leave it analysing forever')
  assert(runtime.machine.state == 'FAILED', 'and it fails visibly, got ' .. tostring(runtime.machine.state))
end

print('analysis runtime: a terminal build failure is terminal')

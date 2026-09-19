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
local legacy_dispatches=0
local runtime=Runtime.new({project_id='analysis-project',worker=worker,analysis_transport=analysis,now=function() return 0 end,
  transport_stopped=function() return true end,
  on_analysis_ready=function() legacy_dispatches=legacy_dispatches+1 end})
assert(runtime:start_capture('manual').ok)
local preflight=capture.sent[#capture.sent]; capture.replies[#capture.replies+1]=reply(preflight,'READY'); runtime:poll()
local start=capture.sent[#capture.sent]; capture.replies[#capture.replies+1]=reply(start,'STARTED'); runtime:poll()
assert(runtime:finish(true).ok)
local stop=capture.sent[#capture.sent]; capture.replies[#capture.replies+1]=reply(stop,'COMPLETED'); runtime:poll()
local publish=capture.sent[#capture.sent]
capture.replies[#capture.replies+1]=reply(publish,'PUBLISHED',{wav_path='/tmp/integration.wav',wav_sha256=string.rep('b',64),frames=200000,sample_rate=8000})
runtime:poll()
local request=analysis.sent[#analysis.sent]
assert(request.command=='ANALYSE' and request.result_schema_version==Bank.VERSION and request.max_candidates==Bank.MAX_CANDIDATES)
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
print('rhythm_doctor analysis_runtime: 1 test passed')

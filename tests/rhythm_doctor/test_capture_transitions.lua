-- Characterisation outside README: PLAN capture failure and 45-second timeout.
package.path = './lib/?.lua;' .. package.path
local Machine = require('rhythm_doctor.state_machine')
local count = 0
local function equal(a,b) assert(a==b,tostring(a)..' ~= '..tostring(b)) end
local function scenario(mode)
  local released, analysed = {}, {}
  local m=Machine.new{project_id='p',on_release=function(t) released[#released+1]=t end,
    on_analyse=function(t) analysed[#analysed+1]=t end}
  m:start_capture(mode,true)
  return m,m:job_token(),released,analysed
end
for _,mode in ipairs{'auto','manual'} do
  local m,t,r,a=scenario(mode)
  m:request_record_action(true)
  equal(m:capture_failed(t,'INPUT_DISCONNECTED').code,'OK')
  equal(m.state,'FAILED');equal(m.last_message,'INPUT_DISCONNECTED')
  equal(m.modal,nil);equal(#r,1);equal(#a,0)
  equal(m:manual_save().code,'CAPTURE_ACTIVE')
  equal(m:capture_failed(t,'DISK_FULL').code,'STALE_RESULT')
  equal(#r,1)
  m:resources_released(t,true)
  equal(m:manual_save().code,'SAVE_NOW');count=count+1
end
for _,valid in ipairs{true,false} do
  local m,t,r,a=scenario('auto')
  m:request_record_action(true)
  equal(m:capture_timeout(t,valid).code,'OK');equal(m.modal,nil)
  equal(m.state,valid and 'ANALYSING' or 'ALIGNMENT_REQUIRED')
  equal(#r,valid and 0 or 1);equal(#a,valid and 1 or 0)
  equal(m:capture_timeout(t,valid).code,'STALE_RESULT')
  if not valid then
    equal(m.last_message,'TEMPO_UNCERTAIN')
    equal(m:finish_capture(true,true).code,'RESOURCE_RELEASING')
    m:resources_released(t,true)
    equal(m:finish_capture(true,true).code,'OK');equal(#a,1)
    equal(m.resources_are_released,false)
  end
  count=count+1
end
for _,field in ipairs{'project_id','generation','analysis_revision'} do
  local m,t,r,a=scenario('manual')
  t[field]=field=='project_id' and 'other' or t[field]+1
  equal(m:capture_failed(t,'FAILED').code,'STALE_RESULT')
  equal(m:capture_timeout(t,true).code,'STALE_RESULT')
  equal(m.state,'RECORDING');equal(#r,0);equal(#a,0);count=count+1
end
local m,t,r,a=scenario('manual')
m:transport_started()
equal(m:capture_timeout(t,true).code,'STALE_RESULT')
equal(m:capture_failed(t,'FAILED').code,'STALE_RESULT')
equal(m.state,'EMPTY');equal(#r,1);equal(#a,0);count=count+1
local reentrant, started = nil, 0
reentrant=Machine.new{project_id='r',on_state=function(state)
  if state=='ANALYSING' then reentrant:transport_started() end
end,on_analyse=function() started=started+1 end}
reentrant:start_capture('auto',true)
reentrant:capture_timeout(reentrant:job_token(),true)
equal(started,0);equal(reentrant.state,'EMPTY');count=count+1
print(tostring(count)..' capture transition cases passed')

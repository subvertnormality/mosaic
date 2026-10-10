-- PLAN.md Bank lifecycle: resource release is part of save inhibition.
-- Characterisation outside the current README; no hardware/model acceptance.
package.path = './lib/?.lua;' .. package.path
local Machine = require('rhythm_doctor.state_machine')
local errors, count = {}, 0
local function test(name, body)
  count = count + 1
  local ok, err = pcall(body)
  if not ok then errors[#errors+1] = name .. ': ' .. tostring(err) end
end
local function equal(actual, expected) assert(actual == expected, tostring(actual)..' ~= '..tostring(expected)) end

test('terminal saves wait for asynchronous release', function()
  local saved = 0
  local m = Machine.new{project_id='p', on_deferred_save=function() saved=saved+1 end}
  m:start_capture('manual', true)
  local token = m:job_token()
  m:transport_started()
  equal(m.state, 'EMPTY')
  equal(m:autosave().code, 'DEFERRED')
  equal(m:manual_save().code, 'CAPTURE_ACTIVE')
  m:resources_released(token, false)
  equal(saved, 0)
  m:transport_stopped()
  equal(saved, 1)
  equal(m:manual_save().code, 'SAVE_NOW')
end)

test('project replacement preserves in-flight release owner', function()
  local requests = 0
  local m = Machine.new{project_id='p', on_release=function() requests=requests+1 end}
  m:start_capture('auto', true)
  local token = m:job_token()
  m:transport_started()
  m:replace_project('q')
  equal(requests, 1)
  equal(m:resources_released(token, true).code, 'OK')
  equal(m:start_capture('manual', true).code, 'OK')
end)

test('idle cleanup does not invent a resource lease', function()
  local requests = 0
  local m = Machine.new{project_id='p', on_release=function() requests=requests+1 end}
  m:replace_project('q')
  equal(requests, 0)
  equal(m:start_capture('manual', true).code, 'OK')
end)

test('destructive modal requires explicit stopped transport', function()
  local m = Machine.new{project_id='p'}
  m:start_capture('manual', true)
  local modal = m:request_record_action(true)
  equal(m:confirm_modal(modal, true).code, 'STOP_SEQUENCER')
  equal(m.state, 'RECORDING')
end)

test('project change handles synchronous release and returns callback value once', function()
  local m, calls = nil, 0
  m = Machine.new{project_id='p', on_release=function(token)
    equal(m:resources_released(token, true).code, 'OK')
  end}
  m:start_capture('manual', true);m:autosave()
  local outcome = m:prepare_project_change(function()
    equal(m.state, 'EMPTY');equal(m.resources_are_released, true)
    equal(m.pending_save, false);calls=calls+1;return 'loaded'
  end)
  equal(outcome.code, 'OK');equal(outcome.value, 'loaded');equal(calls, 1)
  m:transport_stopped();equal(calls, 1)
end)

test('reentrant project requests from release or state callbacks keep latest owner', function()
  for _,boundary in ipairs({'release','state'}) do
    local m, entered, old_calls, new_calls = nil, false, 0, 0
    local function newer()
      if entered then return end
      entered = true
      equal(m:start_capture('auto', true).code, 'PROJECT_CHANGING')
      m:prepare_project_change(function() new_calls=new_calls+1 end)
    end
    m = Machine.new{project_id='p',
      on_release=function() if boundary=='release' then newer() end end,
      on_state=function(state) if boundary=='state' and state=='EMPTY' then newer() end end}
    m:start_capture('manual', true)
    local token = m:job_token()
    local outcome=m:prepare_project_change(function() old_calls=old_calls+1 end)
    equal(outcome.code, 'STALE_REQUEST')
    m:resources_released(token, true)
    equal(old_calls, 0);equal(new_calls, 1)
  end
end)

test('throwing project continuation cannot replay or revive old autosave', function()
  local calls, saves = 0, 0
  local m = Machine.new{project_id='p',on_deferred_save=function() saves=saves+1 end}
  m:start_capture('manual', true);m:autosave()
  local owner=m:job_token()
  m:prepare_project_change(function() calls=calls+1;error('load failed') end)
  -- An autosave that arrives during release still belongs to the old project.
  equal(m:autosave().code, 'DEFERRED')
  local ok,problem=pcall(function() m:resources_released(owner, true) end)
  equal(ok, false);assert(tostring(problem):find('load failed',1,true))
  equal(m.pending_project_change, nil);equal(m.pending_save, false)
  equal(m:resources_released(owner, true).code, 'STALE_RELEASE')
  m:transport_stopped();equal(calls, 1);equal(saves, 0)
end)

if #errors > 0 then
  io.stderr:write(table.concat(errors, '\n') .. '\n')
  os.exit(1)
end
print('rhythm_doctor lifecycle: '..count..' tests passed')

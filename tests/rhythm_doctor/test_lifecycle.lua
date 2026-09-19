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

if #errors > 0 then
  io.stderr:write(table.concat(errors, '\n') .. '\n')
  os.exit(1)
end
print('rhythm_doctor lifecycle: '..count..' tests passed')

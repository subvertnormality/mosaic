-- PLAN capture architecture: real transport/controller/worker collaboration on
-- the interpreter matron embeds.  Inside matron there is no FFI, whatever the
-- device's standalone luajit offers, so the wait is a sleep not a C call.
package.path = './lib/?.lua;' .. package.path
local function sleep(seconds) os.execute('sleep ' .. tostring(seconds)) end
local Machine = require('rhythm_doctor.state_machine')
local Controller = require('rhythm_doctor.capture_controller')
local Native = require('rhythm_doctor.native_transport')

local mailbox_root = assert(arg[1], 'worker mailbox root is required')
local transport = assert(Native.new(mailbox_root))
local controller, machine, saved, analysed
machine = Machine.new{
  project_id='stack-test',
  on_capture_start=function(mode, token) assert(controller:begin(mode, token, 1)) end,
  on_cancel=function(token) controller:cancel(token) end,
  on_release=function(token) controller:release(token) end,
  on_analyse=function(token) controller:analyse(token) end,
}
controller = Controller.new{
  machine=machine, transport=transport, now=os.clock, transport_stopped=function() return true end,
  on_capture_saved=function(asset) saved=asset end,
  on_analysis_ready=function(asset, token)
    analysed=asset
    machine:receive_analysis{project_id=token.project_id,generation=token.generation,
      analysis_revision=token.analysis_revision,error='TEST_ANALYSIS_STOP'}
  end,
}
assert(machine:start_capture('manual', true).ok)
for _=1,500 do controller:poll();if controller.job.phase=='CAPTURING' then break end;sleep(0.01) end
assert(controller.job.phase=='CAPTURING','worker did not start')
sleep(0.12)
assert(machine:finish_capture(true,true).ok)
for _=1,500 do controller:poll();if machine.resources_are_released then break end;sleep(0.01) end
assert(saved and analysed and saved.wav_sha256==analysed.wav_sha256,'asset callbacks mismatch')
assert(machine.state=='FAILED' and machine.resources_are_released,'terminal release incomplete')
local file=assert(io.open(saved.wav_path,'rb'));local bytes=file:read('*a');file:close()
assert(#bytes>44 and bytes:sub(1,4)=='RIFF' and bytes:sub(9,12)=='WAVE','invalid published WAV')
print(saved.wav_sha256..' '..saved.frames..' '..saved.sample_rate..' '..#bytes)
transport:close()

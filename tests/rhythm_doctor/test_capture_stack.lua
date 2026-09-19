-- PLAN capture architecture: real LuaJIT transport/controller/worker collaboration.
package.path = './lib/?.lua;' .. package.path
local ffi = require('ffi')
ffi.cdef[[int usleep(unsigned int);]]
local Machine = require('rhythm_doctor.state_machine')
local Controller = require('rhythm_doctor.capture_controller')
local Native = require('rhythm_doctor.native_transport')

local socket_path = assert(arg[1], 'worker socket is required')
local transport = assert(Native.new(socket_path))
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
for _=1,500 do controller:poll();if controller.job.phase=='CAPTURING' then break end;ffi.C.usleep(10000) end
assert(controller.job.phase=='CAPTURING','worker did not start')
ffi.C.usleep(120000)
assert(machine:finish_capture(true,true).ok)
for _=1,500 do controller:poll();if machine.resources_are_released then break end;ffi.C.usleep(10000) end
assert(saved and analysed and saved.wav_sha256==analysed.wav_sha256,'asset callbacks mismatch')
assert(machine.state=='FAILED' and machine.resources_are_released,'terminal release incomplete')
local file=assert(io.open(saved.wav_path,'rb'));local bytes=file:read('*a');file:close()
assert(#bytes>44 and bytes:sub(1,4)=='RIFF' and bytes:sub(9,12)=='WAVE','invalid published WAV')
print(saved.wav_sha256..' '..saved.frames..' '..saved.sample_rate..' '..#bytes)
transport:close()

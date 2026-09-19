-- Physical-Norns launch_worker smoke transport. Characterisation outside README.
-- Uses the production LuaJIT AF_UNIX transport against one disposable worker.
local socket_path, lib_root = assert(arg[1]), assert(arg[2])
package.path = lib_root .. "/?.lua;" .. package.path

local ffi = require("ffi")
ffi.cdef[[int usleep(unsigned int useconds);]]
local Native = require("rhythm_doctor.native_transport")
local transport, problem = Native.new(socket_path)
assert(transport, problem and problem.code or "native transport unavailable")

local identity = {
  protocol_version = 1,
  job_id = "launch-worker-smoke",
  project_id = "hardware-smoke",
  generation = 1,
  analysis_revision = 1,
}

local function send(command, extra)
  local message = {}
  for key, value in pairs(identity) do message[key] = value end
  message.command = command
  for key, value in pairs(extra or {}) do message[key] = value end
  local ok, why = transport:send(message)
  assert(ok, why)
end

local function wait_for(status)
  for _ = 1, 300 do
    local message = transport:poll()
    if message then
      assert(message.job_id == identity.job_id and message.project_id == identity.project_id)
      assert(message.generation == identity.generation and message.analysis_revision == identity.analysis_revision)
      assert(message.status == status, (message.status or "nil") .. ":" .. (message.capture_error or ""))
      return message
    end
    ffi.C.usleep(10000)
  end
  error("timed out waiting for " .. status)
end

send("PREFLIGHT", { seconds = 1, mode = "manual" })
wait_for("READY")
send("START", { mode = "manual" })
wait_for("STARTED")
send("CANCEL")
ffi.C.usleep(50000) -- CANCEL deliberately has no immediate RD1 reply.
send("RELEASE")
wait_for("RELEASED")
transport:close() -- peer close is the worker's self-cleanup trigger.

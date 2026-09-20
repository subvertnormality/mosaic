-- Physical-Norns launch_worker smoke transport. Characterisation outside README.
-- Uses the production file-mailbox transport against one disposable worker, on
-- the Lua matron embeds -- not the device's standalone luajit, which has an
-- FFI that matron does not.
local mailbox_root, lib_root = assert(arg[1]), assert(arg[2])
package.path = lib_root .. "/?.lua;" .. package.path

local function sleep(seconds) os.execute("sleep " .. tostring(seconds)) end
local Native = require("rhythm_doctor.native_transport")
local transport, problem = Native.new(mailbox_root)
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
    sleep(0.01)
  end
  error("timed out waiting for " .. status)
end

send("PREFLIGHT", { seconds = 1, mode = "manual" })
wait_for("READY")
send("START", { mode = "manual" })
wait_for("STARTED")
send("CANCEL")
sleep(0.05) -- CANCEL deliberately has no immediate RD1 reply.
send("RELEASE")
wait_for("RELEASED")
transport:close() -- the client stops stamping liveness, which the worker acts on.

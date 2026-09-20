-- Starts the optional local analysis backend away from the norns Lua thread.
local Host = {}; Host.__index = Host
local function shell_quote(value)
  assert(type(value) == "string" and not value:find("%z"), "safe shell value required")
  return "'" .. value:gsub("'", "'\\''") .. "'"
end
local function read_line(path)
  local handle=io.open(path, "r"); if not handle then return nil end
  local value=handle:read("*l"); handle:close(); return value
end
local function code_root()
  local source=debug.getinfo(1, "S").source
  return source:match("^@(.+)/lib/rhythm_doctor/analysis_worker_host%.lua$")
end
local function sha256(value)
  return type(value) == "string" and #value == 64 and value:match("^[%x]+$") ~= nil
end
function Host.new(deps)
  deps=deps or {}; local root=deps.code_root or code_root()
  assert(type(root)=="string" and root~="", "Mosaic code root is required")
  assert(type(deps.runtime_root)=="string" and deps.runtime_root:sub(1,1)=="/", "absolute runtime root is required")
  -- Two identity shapes. A model-free DSP backend pins its source and its
  -- template table; a pretrained chain pins its model artifacts. Exactly one
  -- must be supplied completely: half a set fails closed rather than pinning
  -- less than it claims.
  local configured=deps.backend ~= nil or deps.backend_sha256 ~= nil or deps.drum_artifact_sha256 ~= nil
    or deps.bass_artifact_sha256 ~= nil or deps.template_sha256 ~= nil
  local located=type(deps.backend)=="string" and deps.backend:sub(1,1)=="/" and sha256(deps.backend_sha256)
  local dsp=located and sha256(deps.template_sha256) and deps.drum_artifact_sha256==nil and deps.bass_artifact_sha256==nil
  local pretrained=located and sha256(deps.drum_artifact_sha256) and sha256(deps.bass_artifact_sha256)
    and deps.template_sha256==nil
  local valid=not configured or dsp or pretrained
  return setmetatable({code_root=root, runtime_root=deps.runtime_root, backend=deps.backend,
    backend_sha256=deps.backend_sha256, drum_artifact_sha256=deps.drum_artifact_sha256,
    bass_artifact_sha256=deps.bass_artifact_sha256, template_sha256=deps.template_sha256,
    configuration_error=not valid,
    execute=deps.execute or os.execute, read_line=deps.read_line or read_line,
    transport_factory=assert(deps.transport_factory, "transport factory is required"), launched=false, closed=false}, Host)
end
function Host:open()
  if self.closed then return nil, "analysis worker host closed" end
  if self.configuration_error then return nil, "invalid analysis backend configuration" end
  if not self.launched then
    self.launched=true
    local command="mkdir -p "..shell_quote(self.runtime_root).." && rm -f "..shell_quote(self.runtime_root.."/cancel")..
      " && python3 "..shell_quote(self.code_root.."/tools/rhythm_doctor/launch_analysis_worker.py")..
      " --runtime "..shell_quote(self.runtime_root)
    if not self.backend then
      -- Nothing configured: build and use the native backend Mosaic ships, so
      -- a stock install can analyse a capture without any Python packages.
      command=command.." --native-source "..shell_quote(self.code_root.."/tools/rhythm_doctor/rd_analysis_backend.c")..
        " --templates "..shell_quote(self.code_root.."/tools/rhythm_doctor/data/nmf_drum_templates.bin")
    end
    if self.backend then
      command=command.." --backend "..shell_quote(self.backend).." --backend-sha256 "..shell_quote(self.backend_sha256)
      if self.template_sha256 then
        command=command.." --template-sha256 "..shell_quote(self.template_sha256)
      else
        command=command.." --drum-artifact-sha256 "..shell_quote(self.drum_artifact_sha256)..
          " --bass-artifact-sha256 "..shell_quote(self.bass_artifact_sha256)
      end
    end
    command=command.." >/dev/null 2>&1 &"
    local ok=self.execute(command); if ok~=true and ok~=0 then return nil, "analysis worker launcher failed" end
    return nil, "analysis worker starting"
  end
  local problem=self.read_line(self.runtime_root.."/error"); if problem then return nil,problem end
  local mailbox=self.read_line(self.runtime_root.."/mailbox"); if mailbox then return self.transport_factory(mailbox, self.runtime_root.."/results") end
  return nil,"analysis worker starting"
end
function Host:close()
  self.closed=true
  self.execute("mkdir -p "..shell_quote(self.runtime_root).." && : > "..shell_quote(self.runtime_root.."/cancel"))
  local pid=self.read_line(self.runtime_root.."/pid"); if pid and pid:match("^[0-9]+$") then self.execute("kill "..pid.." 2>/dev/null") end
end
Host.shell_quote=shell_quote
return Host

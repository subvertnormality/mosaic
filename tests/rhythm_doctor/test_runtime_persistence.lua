-- Runtime/project persistence integration for completed Rhythm Doctor banks.
package.path = "./lib/?.lua;./lib/?/init.lua;" .. package.path
local Bank = require("rhythm_doctor.bank")
local Runtime = require("rhythm_doctor.runtime")

local checks = 0
local function check(value, message) checks = checks + 1; assert(value, message or "check failed") end
local function equal(actual, expected, message) check(actual == expected, (message or "mismatch") .. ": " .. tostring(actual) .. " ~= " .. tostring(expected)) end
local function new_runtime(project)
  return Runtime.new({project_id=project, worker={open=function() return {send=function() return true end,poll=function() return nil end} end},
    now=function() return 0 end, transport_stopped=function() return true end})
end

local source_path, save_path = "data/autosave.ptn", "data/fixture.ptn"
local runtime = new_runtime(source_path)
local source_identity = Runtime.project_identity(source_path)
runtime.machine.project_id, runtime.machine.generation, runtime.machine.analysis_revision = source_identity, 3, 1
runtime.machine.state = "READY"
runtime.machine.bank = assert(Bank.build({project_id=source_identity,generation=3,analysis_revision=1,
  sample_rate=100,capture_start_sample=0,capture_end_sample=1000,origin_sample=0,bpm=120,
  candidates={{lane="BASS",sample_index=0,velocity=76,confidence=1}}}))
local data = {song_patterns={}}
check(runtime:serialize_project(data, save_path).ok, "ready bank serializes with project")
check(data.rhythm_doctor and data.rhythm_doctor.version == 1, "versioned bank stored in project data")
equal(data.rhythm_doctor.bank.project_id, Runtime.project_identity(save_path), "save path rebinds project ownership")

local loaded = new_runtime("data/other.ptn")
check(loaded:project_loaded(save_path).ok)
check(loaded:restore_project(data, save_path).ok, "completed bank restores after project replacement")
equal(loaded.machine.state, "READY", "reload reaches ready, never capture")
equal(loaded.machine.bank.lanes.BASS[1].velocity, 76, "restored bank retains derived lane data")
equal(loaded.machine.project_id, Runtime.project_identity(save_path), "restored callbacks use loaded project identity")

local legacy = new_runtime("data/legacy.ptn")
check(legacy:project_loaded("data/legacy.ptn").ok)
check(legacy:restore_project({song_patterns={}}, "data/legacy.ptn").ok, "legacy project has empty Rhythm Doctor state")
equal(legacy.machine.state, "EMPTY", "legacy load cannot resume capture")

runtime.machine.state = "RECORDING"
data.rhythm_doctor = {version=1,bank={unsafe=true}}
check(runtime:serialize_project(data, save_path).ok, "active job does not serialize a partial bank")
check(data.rhythm_doctor == nil, "active job clears any stale project envelope")
print("rhythm_doctor runtime persistence: " .. checks .. " checks")

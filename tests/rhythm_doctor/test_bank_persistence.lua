-- Completed Rhythm Doctor banks survive ordinary project serialization; jobs
-- and source-paint history intentionally do not.  PLAN.md Bank lifecycle.
package.path = "./lib/?.lua;./lib/?/init.lua;" .. package.path
local Bank = require("rhythm_doctor.bank")
local Persistence = require("rhythm_doctor.bank_persistence")

local checks = 0
local function check(value, message) checks = checks + 1; assert(value, message or "check failed") end
local function equal(actual, expected, message) check(actual == expected, (message or "mismatch") .. ": " .. tostring(actual) .. " ~= " .. tostring(expected)) end

local bank = assert(Bank.build({ project_id="project-a", generation=4, analysis_revision=2,
  sample_rate=100, capture_start_sample=0, capture_end_sample=1000, origin_sample=0, bpm=120,
  candidates={{lane="CYM", sample_index=15, velocity=91, confidence=1}} }))
local saved = assert(Persistence.encode(bank))
equal(saved.version, Persistence.VERSION, "versioned envelope")
local restored = assert(Persistence.decode(saved, {project_id="project-a", generation=4, analysis_revision=2}))
check(restored ~= bank and restored.lanes ~= bank.lanes, "project data cannot retain mutable bank aliases")
equal(restored.lanes.CYM[2].velocity, 91, "all active lanes retain their detected velocities")
saved.bank.lanes.CYM[2].velocity = 1
equal(restored.lanes.CYM[2].velocity, 91, "restored data is independent of serialized table")

local value, problem = Persistence.decode({version=999, bank=bank})
check(value == nil and problem.code == "UNKNOWN_BANK_SCHEMA", "unknown schema rejected")
value, problem = Persistence.decode({version=Persistence.VERSION, bank={project_id="project-a"}})
check(value == nil and problem.code == "INVALID_BANK", "malformed bank rejected")
value, problem = Persistence.decode(saved, {project_id="project-b", generation=4, analysis_revision=2})
check(value == nil and problem.code == "INVALID_BANK", "cross-project bank rejected")
value, problem = Persistence.decode(nil)
check(value == nil and problem.code == "EMPTY", "legacy project restores empty")
print("rhythm_doctor bank persistence: " .. checks .. " checks")

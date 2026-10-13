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

-- A project file is text. Lua writes a float with fourteen significant digits,
-- so a bank that comes back from disk is not bit-identical to the one written:
-- a real capture stored samples_per_cell as 15046.530612245 where the double
-- was 15046.530612244898. Demanding equality of derived geometry rejected the
-- bank, and project_lifecycle then rejected the entire project, so a whole
-- session of painting was lost on reload.
local function through_text(value)
  -- Exactly what tabutil.save and tabutil.load do to a number.
  if type(value) == "number" then return tonumber(tostring(value)) end
  if type(value) ~= "table" then return value end
  local out = {}
  for key, item in pairs(value) do out[through_text(key)] = through_text(item) end
  return out
end

-- A tempo whose cell spacing does not terminate in decimal, as most do not.
local awkward = assert(Bank.build({ project_id="project-b", generation=1, analysis_revision=1,
  sample_rate=48000, capture_start_sample=0, capture_end_sample=1354187, origin_sample=0,
  bpm=47.8515625,
  candidates={{lane="BD", sample_index=15046, velocity=100, confidence=0.9}} }))
check(tostring(awkward.samples_per_cell) ~= string.format("%.17g", awkward.samples_per_cell),
  "this tempo must actually lose precision in text, or the test proves nothing")

local written = assert(Persistence.encode(awkward))
local reread = through_text(written)
check(reread.bank.samples_per_cell ~= awkward.samples_per_cell,
  "the round trip must really change the stored double")
local recovered, problem = Persistence.decode(reread)
check(recovered ~= nil, "a bank must survive being written to a project file and read back: "
  .. tostring(problem and problem.code))
equal(recovered.timeline_cells, awkward.timeline_cells, "with the same timeline")
equal(#recovered.candidates, #awkward.candidates, "and the same candidates")

-- Tolerance is for the text round trip, not for a bank that disagrees with itself.
local wrong = through_text(assert(Persistence.encode(awkward)))
wrong.bank.samples_per_cell = wrong.bank.samples_per_cell * 1.01
local rejected, why = Persistence.decode(wrong)
check(rejected == nil and why.code == "INVALID_BANK", "a genuinely wrong spacing is still rejected")

print("rhythm_doctor bank persistence: " .. checks .. " checks")

-- A project saved before phrase alignment must still open. Rejecting the
-- player's existing captures to publish a schema number would destroy work.
do
  local legacy = assert(Bank.build{project_id='p', generation=1, analysis_revision=2,
    sample_rate=48000, capture_start_sample=0, capture_end_sample=480000,
    origin_sample=0, bpm=120, candidates={}})
  legacy.version = 2
  legacy.phrase_start_cell, legacy.phrase_confidence = nil, nil
  local decoded, problem = Persistence.decode({ version = Persistence.VERSION, bank = legacy })
  assert(decoded, "a legacy bank must decode, got " .. tostring(problem and problem.code))
  assert(decoded.version == Bank.VERSION and decoded.phrase_start_cell == 0,
    "a decoded legacy bank is upgraded rather than left at the old schema")
end

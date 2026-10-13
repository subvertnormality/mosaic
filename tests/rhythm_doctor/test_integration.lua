-- Characterisation outside the current README.  This exercises the pure
-- bank -> shared window -> pinned preview -> source-paint journal collaboration
-- specified by docs/rhythm-doctor/PLAN.md sections 208-221 and 333-382.
package.path = "./lib/?.lua;" .. package.path
local Bank = require("rhythm_doctor.bank")
local Paint = require("rhythm_doctor.paint")
local Journal = require("rhythm_doctor.paint_journal")

local checks = 0
local function check(value, message) checks = checks + 1; if not value then error(message, 2) end end
local function eq(a, b, message) check(a == b, (message or "mismatch") .. ": " .. tostring(a) .. " ~= " .. tostring(b)) end

local candidates = {}
for _, lane in ipairs(Bank.LANES) do
  candidates[#candidates + 1] = { lane = lane, sample_index = 100 + (#candidates * 15), velocity = 50 + #candidates, confidence = 1 }
end
-- A middle fill gives overlapping views a distinct source event; no detection
-- implementation supplies it during this test.
candidates[#candidates + 1] = { lane = "BD", sample_index = 100 + 100 * 15, velocity = 101, confidence = 1 }
local bank = assert(Bank.build({ project_id = "p", generation = 4, analysis_revision = 2,
  sample_rate = 100, capture_start_sample = 0, capture_end_sample = 2500,
  origin_sample = 100, bpm = 100, candidates = candidates }))

local first = assert(Bank.window(bank, "BD", 0))
local middle = assert(Bank.window(bank, "BD", 64))
eq(first.cells[1].velocity, 50, "first view preserves its source hit")
eq(middle.cells[37].velocity, 101, "middle view reads the same fixed timeline cell")
check(middle.cells[1] == nil, "sparse windows never synthesize wrapped first-view cells")

local source = { revision = 20, trigs = {}, velocities = {}, lengths = {} }
for i = 1, 64 do source.trigs[i], source.velocities[i], source.lengths[i] = false, 1, 0 end
local target = { project_id = "p", song_slot = 2, pattern_id = 3, revision = 20 }
local function preview_for(view, revision)
  return assert(Paint.preview({ project_id = bank.project_id, generation = bank.generation,
    analysis_revision = bank.analysis_revision, lane = view.lane, window_start = view.start,
    window_revision = revision, target = target, policy = "add", shift = 0, cells = view.cells }))
end
local preview = preview_for(middle, 7)
check(Paint.valid_preview(preview, { project_id = "p", generation = 4, analysis_revision = 2, target = target, window_revision = 7,
  lane = "BD", window_start = 64, shift = 0, policy = "add", thresholds = {} }),
  "preview accepts only its displayed source and target")
local painted = assert(Paint.apply(source, preview))
check(painted.trigs[37] and painted.velocities[37] == 101 and painted.lengths[37] == 1, "paint copies fixed velocity")
check(not source.trigs[37], "preview commit snapshot leaves capture and source untouched")

local journal = Journal.new(1)
assert(Journal.record(journal, target, source, painted, 21, 20))
local undo = assert(Journal.prepare_undo(journal, target, 21))
eq(undo.snapshot.trigs[37], false, "journal restores full source snapshot")
assert(Journal.complete_undo(journal, undo, 22))
local redo = assert(Journal.prepare_redo(journal, target, 22))
eq(redo.snapshot.velocities[37], 101, "redo restores source velocity")
assert(Journal.complete_redo(journal, redo, 23))
eq(Journal.prepare_undo(journal, target, 22).code, "PATTERN_CHANGED", "stale source cannot be overwritten")

print("rhythm_doctor integration: " .. checks .. " assertions passed")

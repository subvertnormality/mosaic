-- PLAN.md "Painting into the current pattern": every source paint is one
-- stopped-only mutation, reprojects every shared channel, and can be undone or
-- redone only while the source revision is still current.  This is a pure
-- integration regression; native grid/screen ownership is covered elsewhere.
package.path = "./lib/?.lua;./lib/?/init.lua;" .. package.path

local Bank = require("rhythm_doctor.bank")
local Transactions = require("rhythm_doctor.paint_transactions")

local checks = 0
local function check(value, message)
  checks = checks + 1
  assert(value, message or "check failed")
end
local function equal(actual, expected, message)
  check(actual == expected, (message or "values differ") .. ": " .. tostring(actual) .. " ~= " .. tostring(expected))
end
local function clone(value)
  if type(value) ~= "table" then return value end
  local out = {}; for key, item in pairs(value) do out[key] = clone(item) end; return out
end

local function ready_bank(project_id, generation, analysis_revision)
  return assert(Bank.build({ project_id = project_id, generation = generation, analysis_revision = analysis_revision,
    sample_rate = 100, capture_start_sample = 0, capture_end_sample = 1500,
    origin_sample = 0, bpm = 100, candidates = {
      { lane = "BD", sample_index = 0, velocity = 98, confidence = .9 },
      { lane = "BD", sample_index = 15, velocity = 72, confidence = .9 },
    },
  }))
end

local function fixture()
  local view = { project_id = "project-a", generation = 4, analysis_revision = 2, state = "READY",
    lane = "BD", window_start = 0, window_revision = 8, policy = "add", shift = 0, thresholds = {} }
  local source = { revision = 10, trigs = {}, velocities = {}, lengths = {} }
  local writes, reprojections = 0, {}
  local engine = Transactions.new({
    context = function() return view end,
    bank = function() return ready_bank(view.project_id, view.generation, view.analysis_revision) end,
    transport_stopped = function() return true end,
    read_source = function(target)
      if target.project_id ~= view.project_id then return nil, { code = "PROJECT_MISMATCH" } end
      return clone(source)
    end,
    write_source = function(target, snapshot, expected_revision)
      if expected_revision ~= source.revision then return nil, { code = "PATTERN_CHANGED" } end
      source = clone(snapshot); source.revision = expected_revision + 1; writes = writes + 1
      return clone(source)
    end,
    reproject = function(target) reprojections[#reprojections + 1] = clone(target); return true end,
  })
  return { engine = engine, view = view, target = { project_id = "project-a", song_slot = 2, pattern_id = 3 },
    get_source = function() return source end, writes = function() return writes end, reprojections = reprojections }
end

-- Acceptance: an Add commit applies all 64 cells through the mutation path,
-- increments the source revision once, and reprojects the shared source.
do
  local c = fixture()
  local preview = assert(c.engine:preview(c.target))
  equal(preview.target.revision, 10, "preview pins current source revision")
  local applied = assert(c.engine:commit(preview, false))
  equal(applied.revision, 11, "commit returns the mutation revision")
  check(c.get_source().trigs[1] and c.get_source().trigs[2], "detected cells painted")
  equal(c.get_source().velocities[1], 98, "velocity survives mutation")
  equal(c.get_source().lengths[1], 1, "new hit gets length one")
  equal(c.writes(), 1, "one source mutation")
  equal(#c.reprojections, 1, "shared source reprojected after paint")

  local undone = assert(c.engine:undo(c.target))
  equal(undone.revision, 12, "undo receives a new source revision")
  check(not c.get_source().trigs[1], "undo restores full before snapshot")
  local redone = assert(c.engine:redo(c.target))
  equal(redone.revision, 13, "redo receives a new source revision")
  equal(c.get_source().velocities[2], 72, "redo restores all paint values")
  equal(c.writes(), 3, "paint undo redo each mutate once")
  equal(#c.reprojections, 3, "paint undo redo each reproject")
end

-- The UI view, bank identity, running transport, and source revision are all
-- rechecked at execution. A stale preview must leave patterns and history alone.
do
  local c = fixture(); local preview = assert(c.engine:preview(c.target))
  c.view.window_revision = c.view.window_revision + 1
  local value, problem = c.engine:commit(preview, false)
  check(value == nil and problem.code == "STALE_PREVIEW", "view revision rejects preview")
  equal(c.writes(), 0, "stale view does not mutate")

  c = fixture(); preview = assert(c.engine:preview(c.target)); c.view.state = "ANALYSING"
  value, problem = c.engine:commit(preview, false)
  check(value == nil and problem.code == "NOT_READY", "only READY can paint")

  c = fixture(); preview = assert(c.engine:preview(c.target)); c.engine.transport_stopped = function() return false end
  value, problem = c.engine:commit(preview, false)
  check(value == nil and problem.code == "STOP_SEQUENCER", "running transport cannot paint")

  c = fixture(); preview = assert(c.engine:preview(c.target)); assert(c.engine:commit(preview, false))
  local source = c.get_source(); source.revision = 99
  value, problem = c.engine:undo(c.target)
  check(value == nil and problem.code == "PATTERN_CHANGED", "ordinary edit blocks undo")
  equal(c.writes(), 1, "stale undo cannot overwrite newer pattern")
end

-- Replace requires its explicit confirmation. Reload/project replacement clears
-- session-only journal entries, while a project mismatch cannot read a source.
do
  local c = fixture(); c.view.policy = "replace"
  local preview = assert(c.engine:preview(c.target))
  local value, problem = c.engine:commit(preview, false)
  check(value == nil and problem.code == "REPLACE_CONFIRMATION_REQUIRED", "replace confirmation required")
  assert(c.engine:commit(preview, true)); c.engine:project_loaded("project-b")
  value, problem = c.engine:undo(c.target)
  check(value == nil and problem.code == "PROJECT_MISMATCH", "old project journal inaccessible")
  equal(c.writes(), 1, "reload clears journal without source mutation")

  c.view.project_id, c.view.generation, c.view.analysis_revision = "project-b", 0, 0
  value, problem = c.engine:undo({ project_id = "project-b", song_slot = 2, pattern_id = 3 })
  check(value == nil and problem.code == "NO_UNDO", "reload clears matching target history too")
end

-- PLAN.md says Toggle/Add painting of an empty lane is a no-op. It must not
-- create an otherwise invisible source revision or a journal entry.
do
  local c = fixture(); c.view.lane = "SD"
  local preview = assert(c.engine:preview(c.target))
  local value, problem = c.engine:commit(preview, false)
  check(value == nil and problem.code == "NO_PAINT_CHANGE", "empty add is explicit no-op")
  equal(c.writes(), 0, "empty add does not mutate source")
  equal(#c.reprojections, 0, "empty add does not reproject")
  value, problem = c.engine:undo(c.target)
  check(value == nil and problem.code == "NO_UNDO", "empty add has no undo entry")
end

-- A failed native mutation does not publish a journal entry or request a
-- reprojection. This keeps a retry from treating an uncommitted preview as an
-- already-applied paint operation.
do
  local c = fixture(); local preview = assert(c.engine:preview(c.target))
  c.engine.write_source = function() return nil, { code = "SOURCE_WRITE_FAILED" } end
  local value, problem = c.engine:commit(preview, false)
  check(value == nil and problem.code == "SOURCE_WRITE_FAILED", "write failure remains visible")
  equal(c.writes(), 0, "failed write reports no source mutation")
  equal(#c.reprojections, 0, "failed write does not reproject")
  value, problem = c.engine:undo(c.target)
  check(value == nil and problem.code == "NO_UNDO", "failed paint did not enter history")
end

print("rhythm_doctor paint transactions: " .. checks .. " checks")

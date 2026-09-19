-- Characterisation outside the current README.  Contract: docs/rhythm-doctor/PLAN.md
-- sections "Four bars, clock and quantisation", "Bank lifecycle, races and
-- persistence", and "Painting into the current pattern".  These pure tests
-- deliberately use no classifier: RD-02 remains the empirical classifier gate.

package.path = "./lib/?.lua;./lib/?/init.lua;" .. package.path

local Bank = require("rhythm_doctor.bank")
local Machine = require("rhythm_doctor.state_machine")
local Paint = require("rhythm_doctor.paint")
local Journal = require("rhythm_doctor.paint_journal")

local total = 0
local function check(condition, message)
  total = total + 1
  if not condition then error(message or "check failed", 2) end
end
local function equal(actual, expected, message)
  check(actual == expected, (message or "values differ") .. ": expected " .. tostring(expected) .. ", got " .. tostring(actual))
end
local function deep_equal(a, b, message)
  if type(a) ~= type(b) then error(message or "different types", 2) end
  if type(a) ~= "table" then return equal(a, b, message) end
  for k, v in pairs(a) do deep_equal(v, b[k], message) end
  for k, v in pairs(b) do check(a[k] ~= nil, message or "missing key") end
end

local function bank_args()
  return {
    project_id = "project-a", generation = 7, analysis_revision = 3,
    sample_rate = 100, capture_start_sample = 0, capture_end_sample = 1100,
    origin_sample = 100, bpm = 150, tempo_mode = "manual",
    candidates = {
      { lane = "BD", sample_index = 100, velocity = 23, confidence = .8 },
      { lane = "BD", sample_index = 105, velocity = 90, confidence = .9 }, -- tie => cell 1
      { lane = "BD", sample_index = 106, velocity = 40, confidence = .2 },
      { lane = "SD", sample_index = 1099, velocity = 71, confidence = .9 },
    },
    sensitivities = { BD = .5, SD = 0, HH = 0, TOM = 0, BASS = 0 },
  }
end

local function ready_bank(project_id, generation, analysis_revision)
  return assert(Bank.build{project_id=project_id, generation=generation,
    analysis_revision=analysis_revision, sample_rate=100, capture_start_sample=0,
    capture_end_sample=800, origin_sample=0, bpm=120})
end

-- Sample positions are authoritative, ties choose the later cell, and filtering
-- retained candidates must not re-quantise them when sensitivity changes.
do
  local bank, err = Bank.build(bank_args())
  check(bank, err)
  equal(bank.timeline_cells, 100, "complete cells exclude the trailing partial cell")
  equal(bank.lanes.BD[1].velocity, 23, "origin is cell zero")
  equal(bank.lanes.BD[2].velocity, 90, "collision keeps maximum velocity")
  equal(bank.lanes.BD[2].collision_count, 1, "collision is reported")
  equal(bank.lanes.SD[100].velocity, 71, "near-final event clamps to last complete cell")
  local changed = Bank.with_sensitivity(bank, "BD", .95)
  check(changed.lanes.BD[2] == nil, "sensitivity hides retained candidate")
  equal(changed.candidates[2].cell, 1, "candidate keeps original quantised identity")
  check(Bank.build({ project_id = "p", sample_rate = 100, capture_end_sample = 5000, origin_sample = 0, bpm = 100 }) == nil,
    "retained capture cannot exceed 45 seconds")
  check(Bank.build({ project_id = "p", sample_rate = 100.5, capture_start_sample = 0, capture_end_sample = 1000, origin_sample = 0, bpm = 100 }) == nil,
    "sample rate must be an integer sample count")
  check(Bank.build({ project_id = "p", sample_rate = 100, capture_start_sample = 0, capture_end_sample = 1000, origin_sample = 0, bpm = 100,
    candidates = { { lane = "BD", sample_index = 1, velocity = 1, confidence = 2 } } }) == nil,
    "worker candidate confidence outside zero to one is rejected")
end

-- All lanes use one variable-length timeline and every 64-cell view has bounded,
-- non-wrapping scroll.  This is a characterisation of PLAN.md lines 208-221, 350-356.
do
  local args = bank_args()
  args.capture_end_sample = 2500
  args.candidates[#args.candidates + 1] = { lane = "HH", sample_index = 1100, velocity = 64, confidence = 1 }
  local bank = assert(Bank.build(args))
  equal(bank.timeline_cells, 240)
  local end_start, _, at_end = Bank.move_window(bank, 10000)
  equal(end_start, 176)
  check(at_end, "window clamps at timeline end")
  local start, at_start = Bank.move_window(bank, -10000)
  equal(start, 0)
  check(at_start, "window clamps at zero")
  local scrolled = assert(Bank.with_window_start(bank, 64))
  equal(scrolled.window_start, 64, "scroll returns a new window header")
  equal(bank.window_start, 0, "scroll does not change the original bank header")
  check(scrolled.candidates == bank.candidates and scrolled.lanes == bank.lanes, "scroll shares immutable timeline storage")
  local view = assert(Bank.window(bank, "HH", 80))
  equal(view.cell_count, 64)
  equal(view.cells[21].velocity, 64, "view maps source cell 100 to display step 21")
end

-- State machine: stopped-only jobs, exact generation/revision/project response
-- matching, stale destructive modal protection, prior READY preservation and
-- deferred autosave semantics. PLAN.md lines 273-331.
do
  local cancelled, deferred = 0, 0
  local m = Machine.new({ project_id = "project-a", on_cancel = function() cancelled = cancelled + 1 end,
    on_deferred_save = function() deferred = deferred + 1 end })
  local denied = m:start_capture("manual", false)
  equal(denied.code, "STOP_SEQUENCER")
  local started = assert(m:start_capture("manual", true))
  equal(m.state, Machine.RECORDING)
  equal(m:autosave().code, "DEFERRED")
  equal(m:autosave().code, "DEFERRED")
  equal(m:manual_save().code, "CAPTURE_ACTIVE")
  local modal = assert(m:request_record_action(true))
  equal(modal.operation, "cancel_capture")
  local old_token = m:job_token()
  m:replace_project("project-b")
  local stale = m:confirm_modal(modal, true)
  equal(stale.code, "STALE_REQUEST")
  equal(cancelled, 1, "project replacement cancels active job once")
  equal(deferred, 0, "old-project deferred save is discarded")
  check(m:resources_released(old_token, true).ok, "old project release can acknowledge after replacement")
  assert(m:start_capture("manual", true))
  local token = m:job_token()
  equal(m:autosave().code, "DEFERRED")
  assert(m:finish_capture(true, true))
  local late = m:receive_analysis({ project_id = "project-b", generation = token.generation - 1,
    analysis_revision = token.analysis_revision, bank = { id = "late" } })
  equal(late.code, "STALE_RESULT")
  check(m:receive_analysis({ project_id = "project-b", generation = token.generation,
    analysis_revision = token.analysis_revision, bank = ready_bank("project-b", token.generation, token.analysis_revision) }).ok)
  equal(m.state, Machine.READY)
  equal(deferred, 0, "release acknowledgement, not analysis completion, permits deferred save")
  check(m:resources_released(token, true).ok)
  equal(deferred, 1, "one deferred autosave is serviced after terminal resource release")
  local correction = assert(m:begin_reanalysis(true))
  equal(m.state, Machine.REANALYSING)
  check(m:receive_analysis({ project_id = "project-b", generation = correction.generation,
    analysis_revision = correction.analysis_revision, error = "model error" }).ok)
  equal(m.state, Machine.READY, "failed correction retains READY snapshot")
  equal(m.bank.project_id, "project-b")
  check(m:resources_released(correction, true).ok, "failed reanalysis releases before later lifecycle work")
end

-- FINISH needs confirmed sufficient audio and a response cannot publish a partial
-- or mismatched bank as READY.  PLAN.md lines 113-114 and 243-244.
do
  local m = Machine.new({ project_id = "p" })
  assert(m:start_capture("manual", true))
  equal(m:finish_capture(true, false).code, "MORE_AUDIO_NEEDED")
  local token = m:job_token()
  assert(m:finish_capture(true, true))
  equal(m:receive_analysis({ project_id = "p", generation = token.generation, analysis_revision = token.analysis_revision,
    bank = { version = Bank.VERSION, project_id = "p", generation = token.generation, analysis_revision = token.analysis_revision, timeline_cells = 64, lanes = { BD = {} } } }).code,
    "INVALID_BANK")
  equal(m.state, Machine.FAILED)
end

-- Cancellation invalidates before its callback can re-enter, while a serialized
-- token remains valid when every frozen field still matches.
do
  local m
  m = Machine.new({ project_id = "p", on_cancel = function(old)
    equal(m:receive_analysis({ project_id = old.project_id, generation = old.generation,
      analysis_revision = old.analysis_revision, bank = { id = "late" } }).code, "STALE_RESULT")
  end })
  assert(m:start_capture("manual", true))
  local running_token = m:job_token(); m:transport_started()
  equal(m.state, Machine.EMPTY)
  check(m:resources_released(running_token, false).ok, "transport Start only acknowledges release; it never saves")
  assert(m:start_capture("manual", true))
  local token = assert(m:request_record_action(true))
  local serialized = { project_id = token.project_id, generation = token.generation,
    analysis_revision = token.analysis_revision, operation = token.operation, state = token.state, nonce = token.nonce }
  check(m:confirm_modal(serialized, false, true).code == "CANCELLED", "modal accepts a value token after UI serialization")
end

-- Preview is read-only and freezes its source/target identity. Shifting rotates
-- only the selected 64-cell view. Paint policy effects are pure source snapshots.
do
  local source = { revision = 11, trigs = {}, velocities = {}, lengths = {} }
  for i = 1, 64 do source.trigs[i], source.velocities[i], source.lengths[i] = false, 10, 0 end
  source.trigs[2], source.lengths[2] = true, 5
  local cells = {}
  for i = 1, 64 do cells[i] = nil end
  cells[1] = { velocity = 80 }; cells[2] = { velocity = 90 }
  local preview = assert(Paint.preview({ project_id = "p", generation = 2, analysis_revision = 4,
    lane = "BD", window_start = 0, window_revision = 1, target = { project_id = "p", song_slot = 1, pattern_id = 9, revision = 11 },
    policy = "toggle", shift = 1, cells = cells }))
  check(Paint.valid_preview(preview, { project_id = "p", generation = 2, analysis_revision = 4,
    target = { project_id = "p", song_slot = 1, pattern_id = 9, revision = 11 }, window_revision = 1,
    lane = "BD", window_start = 0, shift = 1, policy = "toggle", thresholds = {} }))
  check(not Paint.valid_preview(preview, { project_id = "p", generation = 2, analysis_revision = 4,
    target = { project_id = "p", song_slot = 1, pattern_id = 10, revision = 11 }, window_revision = 1,
    lane = "BD", window_start = 0, shift = 1, policy = "toggle", thresholds = {} }))
  check(not Paint.valid_preview(preview, { project_id = "p", generation = 2, analysis_revision = 4,
    target = { project_id = "p", song_slot = 1, pattern_id = 9, revision = 11 }, window_revision = 1,
    lane = "BD", window_start = 0, shift = 0, policy = "toggle", thresholds = {} }), "preview freezes shift")
  local after = assert(Paint.apply(source, preview))
  check(after.trigs[2] == false and after.lengths[2] == 0, "shifted hit toggles existing target step off")
  check(after.trigs[3] and after.velocities[3] == 90 and after.lengths[3] == 1, "shift keeps velocity paired with its trig")
  deep_equal(source.trigs[2], true, "preview does not mutate source")
  local replaced = assert(Paint.apply(source, assert(Paint.preview({ project_id = "p", generation = 2, analysis_revision = 4,
    lane = "BD", window_start = 0, window_revision = 1, target = { project_id = "p", song_slot = 1, pattern_id = 9, revision = 11 },
    policy = "replace", shift = 0, cells = cells }))))
  check(replaced.trigs[1] and replaced.trigs[2] and not replaced.trigs[3])
  equal(replaced.velocities[3], 10, "replace retains velocity for absent cells")
  check(not Paint.apply({ revision = 12 }, preview), "paint refuses a changed pinned source")
  local numeric = { revision = 11, trig_values = {}, velocity_values = {}, length_values = {} }
  for i = 1, 64 do numeric.trig_values[i], numeric.velocity_values[i], numeric.length_values[i] = 0, 1, 0 end
  numeric.trig_values[2] = 1
  local numeric_after = assert(Paint.apply(numeric, preview, { trig_field = "trig_values", velocity_field = "velocity_values", length_field = "length_values", on = 1, off = 0 }))
  equal(numeric_after.trig_values[2], 0, "explicit numeric adapter clears numeric trig")
  equal(numeric_after.trig_values[3], 1, "explicit numeric adapter sets numeric trig")
  equal(numeric_after.velocity_values[3], 90, "explicit adapter writes actual velocity field")
end

-- A bounded per-target journal refuses stale mutations and truncates redo after
-- new paint. PLAN.md lines 370-382.
do
  local j = Journal.new(2)
  local target = { project_id = "p", song_slot = 1, pattern_id = 2 }
  assert(Journal.record(j, target, { value = "before" }, { value = "after" }, 12, 11))
  local undo = assert(Journal.prepare_undo(j, target, 12))
  equal(undo.snapshot.value, "before")
  assert(Journal.complete_undo(j, undo, 13))
  local redo = assert(Journal.prepare_redo(j, target, 13))
  equal(redo.snapshot.value, "after")
  assert(Journal.complete_redo(j, redo, 14))
  local stale = Journal.prepare_undo(j, target, 99)
  equal(stale.code, "PATTERN_CHANGED")
  assert(Journal.record(j, target, { value = "b2" }, { value = "a2" }, 100, 99))
  equal(Journal.prepare_redo(j, target, 100).code, "NO_REDO")
end

-- Multi-level history follows the current source revision, and a prepared token
-- cannot apply after the same target receives an intervening paint.
do
  local j, target = Journal.new(4), { project_id = "p", song_slot = 1, pattern_id = 4 }
  assert(Journal.record(j, target, { v = 0 }, { v = 1 }, 1, 0))
  assert(Journal.record(j, target, { v = 1 }, { v = 2 }, 2, 1))
  local undo_two = assert(Journal.prepare_undo(j, target, 2)); assert(Journal.complete_undo(j, undo_two, 3))
  local undo_one = assert(Journal.prepare_undo(j, target, 3)); equal(undo_one.snapshot.v, 0, "second undo follows the new source revision")
  assert(Journal.complete_undo(j, undo_one, 4))
  local redo_one = assert(Journal.prepare_redo(j, target, 4)); assert(Journal.complete_redo(j, redo_one, 5))
  local prepared = assert(Journal.prepare_redo(j, target, 5))
  assert(Journal.record(j, target, { v = 1 }, { v = 3 }, 6, 5))
  equal(Journal.complete_redo(j, prepared, 7), nil, "intervening paint invalidates a prepared redo token")
end

print("rhythm_doctor core: " .. total .. " assertions passed")

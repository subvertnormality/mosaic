-- Rhythm Doctor's source-pattern paint transaction boundary.  The existing
-- page owns user gestures and the native pattern adapter owns physical source
-- mutation; this module pins their collaboration to a READY bank, stopped
-- transport, project identity and source revision.  See PLAN.md "Painting into
-- the current pattern" (lines 333-382).
local function dependency(name, path)
  if type(include) == "function" then return include(path) end
  return require(name)
end

local Bank = dependency("rhythm_doctor.bank", "mosaic/lib/rhythm_doctor/bank")
local Paint = dependency("rhythm_doctor.paint", "mosaic/lib/rhythm_doctor/paint")
local Journal = dependency("rhythm_doctor.paint_journal", "mosaic/lib/rhythm_doctor/paint_journal")

local Transactions = {}
Transactions.__index = Transactions

local function copy(value)
  if type(value) ~= "table" then return value end
  local out = {}
  for key, item in pairs(value) do out[key] = copy(item) end
  return out
end

local function same_value(left, right)
  if type(left) ~= type(right) then return false end
  if type(left) ~= "table" then return left == right end
  for key, value in pairs(left) do if not same_value(value, right[key]) then return false end end
  for key in pairs(right) do if left[key] == nil then return false end end
  return true
end

local function integer(value)
  return type(value) == "number" and value == value and value ~= math.huge and value ~= -math.huge and math.floor(value) == value
end

local function result(code, extra)
  extra = extra or {}; extra.code, extra.ok = code, code == "OK"; return extra
end

local function valid_target(target)
  return type(target) == "table" and type(target.project_id) == "string" and target.project_id ~= "" and
    target.song_slot ~= nil and target.pattern_id ~= nil
end

local function view_is_ready(view)
  return type(view) == "table" and view.state == "READY" and type(view.project_id) == "string" and view.project_id ~= "" and
    integer(view.generation) and integer(view.analysis_revision) and type(view.lane) == "string" and
    integer(view.window_start) and integer(view.window_revision) and type(view.policy) == "string" and integer(view.shift or 0) and
    type(view.thresholds or {}) == "table"
end

function Transactions.new(deps)
  assert(type(deps) == "table", "dependencies are required")
  for _, name in ipairs({ "context", "bank", "read_source", "write_source", "reproject" }) do
    assert(type(deps[name]) == "function", name .. " callback is required")
  end
  local limit = deps.journal_limit or 32
  local self = setmetatable({ context = deps.context, bank = deps.bank,
    read_source = deps.read_source, write_source = deps.write_source, reproject = deps.reproject, adapter = deps.adapter,
    journal_limit = limit, journal = Journal.new(limit), project_id = nil }, Transactions)
  local view = self.context()
  if view_is_ready(view) then self.project_id = view.project_id end
  return self
end

function Transactions:_view()
  local view = self.context()
  if type(view) ~= "table" or view.state ~= "READY" then return nil, result("NOT_READY") end
  if not view_is_ready(view) then return nil, result("INVALID_CONTEXT") end
  if self.project_id and view.project_id ~= self.project_id then return nil, result("PROJECT_MISMATCH") end
  self.project_id = view.project_id
  return view
end

function Transactions:_target(view, target)
  if not valid_target(target) or target.project_id ~= view.project_id then return nil, result("PROJECT_MISMATCH") end
  if self.project_id and target.project_id ~= self.project_id then return nil, result("PROJECT_MISMATCH") end
  return target
end

function Transactions:_bank(view)
  local bank = self.bank()
  if not Bank.valid_ready(bank, view) then return nil, result("INVALID_BANK") end
  return bank
end

function Transactions:_source(target)
  local source, problem = self.read_source(copy(target))
  if not source then return nil, problem or result("SOURCE_UNAVAILABLE") end
  if type(source) ~= "table" or not integer(source.revision) then return nil, result("INVALID_SOURCE") end
  return source
end

function Transactions:_preview_spec(view, bank, target, source)
  local window, problem = Bank.window(bank, view.lane, view.window_start)
  if not window then return nil, problem or result("INVALID_BANK") end
  local pinned_target = copy(target)
  if pinned_target.revision ~= nil and pinned_target.revision ~= source.revision then return nil, result("PATTERN_CHANGED") end
  pinned_target.revision = source.revision
  return {
    project_id = view.project_id, generation = view.generation, analysis_revision = view.analysis_revision,
    lane = view.lane, window_start = window.start, window_revision = view.window_revision, target = pinned_target,
    policy = view.policy, shift = view.shift or 0, thresholds = copy(view.thresholds or {}), cells = window.cells,
    -- The lane set this bank actually holds. Without it Paint validates the
    -- lane against the device's default three, so painting any lane a remote
    -- analysis produced was refused as an invalid preview.
    lane_names = copy(bank.lane_names),
  }
end

-- Returns a preview whose cells come directly from the retained, selected bank
-- window. Callers cannot inject a different lane mask while retaining a valid
-- identity token.
function Transactions:preview(target)
  local view, view_problem = self:_view(); if not view then return nil, view_problem end
  local valid_target_value, target_problem = self:_target(view, target); if not valid_target_value then return nil, target_problem end
  local bank, bank_problem = self:_bank(view); if not bank then return nil, bank_problem end
  local source, source_problem = self:_source(valid_target_value); if not source then return nil, source_problem end
  local spec, spec_problem = self:_preview_spec(view, bank, valid_target_value, source); if not spec then return nil, spec_problem end
  return Paint.preview(spec)
end

function Transactions:_current(preview)
  local view, view_problem = self:_view(); if not view then return nil, nil, nil, view_problem end
  local target, target_problem = self:_target(view, preview and preview.target); if not target then return nil, nil, nil, target_problem end
  local bank, bank_problem = self:_bank(view); if not bank then return nil, nil, nil, bank_problem end
  local source, source_problem = self:_source(target); if not source then return nil, nil, nil, source_problem end
  local spec, spec_problem = self:_preview_spec(view, bank, target, source); if not spec then return nil, nil, nil, spec_problem end
  return spec, source, target
end

local function write_then_reproject(self, target, snapshot, expected_revision)
  local saved, problem = self.write_source(copy(target), copy(snapshot), expected_revision)
  if not saved then return nil, problem or result("SOURCE_WRITE_FAILED") end
  if type(saved) ~= "table" or not integer(saved.revision) or saved.revision == expected_revision then
    return nil, result("INVALID_SOURCE_MUTATION")
  end
  local reprojected, reproject_problem = self.reproject(copy(target))
  if reprojected ~= true then return nil, reproject_problem or result("REPROJECTION_FAILED") end
  return saved
end

-- Paint writes exactly once after rechecking every preview pin. The journal is
-- updated only once the mutation and all shared-channel reprojections succeed.
function Transactions:commit(preview, replace_confirmed)
  if type(preview) ~= "table" then return nil, result("INVALID_PREVIEW") end
  local spec, source, target, problem = self:_current(preview)
  if not spec then return nil, problem end
  if preview.target.revision ~= source.revision then return nil, result("PATTERN_CHANGED") end
  if not Paint.valid_preview(preview, spec) then return nil, result("STALE_PREVIEW") end
  if preview.requires_replace_confirmation and replace_confirmed ~= true then return nil, result("REPLACE_CONFIRMATION_REQUIRED") end
  local after, paint_problem = Paint.apply(source, preview, self.adapter)
  if not after then return nil, paint_problem or result("INVALID_PAINT") end
  -- Toggle/Add on an empty lane, and any already-identical result, must not
  -- manufacture a source revision or an undo entry.  In particular, an empty
  -- captured lane is explicitly a no-op in the painting contract.
  if same_value(after, source) then return nil, result("NO_PAINT_CHANGE") end
  local saved, write_problem = write_then_reproject(self, target, after, source.revision)
  if not saved then return nil, write_problem end
  local recorded, record_problem = Journal.record(self.journal, target, source, saved, saved.revision, source.revision)
  if not recorded then return nil, record_problem or result("JOURNAL_FAILED") end
  return saved
end

function Transactions:_history(operation, target)
  local view, view_problem = self:_view(); if not view then return nil, view_problem end
  local valid_target_value, target_problem = self:_target(view, target); if not valid_target_value then return nil, target_problem end
  local source, source_problem = self:_source(valid_target_value); if not source then return nil, source_problem end
  local token = operation == "undo" and Journal.prepare_undo(self.journal, valid_target_value, source.revision) or
    Journal.prepare_redo(self.journal, valid_target_value, source.revision)
  if token.code then return nil, token end
  local saved, write_problem = write_then_reproject(self, valid_target_value, token.snapshot, source.revision)
  if not saved then return nil, write_problem end
  local complete = operation == "undo" and Journal.complete_undo or Journal.complete_redo
  local completed, complete_problem = complete(self.journal, token, saved.revision)
  if not completed then return nil, complete_problem or result("STALE_JOURNAL") end
  return saved
end

function Transactions:undo(target) return self:_history("undo", target) end
function Transactions:redo(target) return self:_history("redo", target) end

-- Paint history is deliberately session-only. Project loading must call this
-- after the state machine invalidates the old project so no entry can cross a
-- project boundary, even if song-slot/pattern IDs happen to match.
function Transactions:project_loaded(project_id)
  assert(type(project_id) == "string" and project_id ~= "", "project_id is required")
  self.project_id, self.journal = project_id, Journal.new(self.journal_limit)
  return result("OK")
end

return Transactions

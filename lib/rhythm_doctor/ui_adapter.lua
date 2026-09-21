-- Pure Rhythm Doctor UI controller.
--
-- This module knows the fifth trigger-editor coordinates and the norns K2/K3
-- contract, but deliberately knows nothing about globals, drawing, grid timers,
-- or worker transport.  The trigger page supplies input only while algorithm 5
-- is selected and renders `screen_model()`; the application supplies transport
-- lifecycle notifications.  Destructive-modal validation remains in Runtime's
-- state machine, whose opaque token this module passes back unchanged.
local Adapter = {}
Adapter.__index = Adapter

-- The lane set before any capture exists, and the one the on-device backend
-- produces. A bank carries its own, which is what the grid actually shows.
Adapter.LANES = { "BD", "SD", "CYM" }
-- Columns 1 and 2 of the row are Record and a gap, so this many lanes fit.
Adapter.MAX_LANE_COLUMNS = 14
Adapter.SETUP_FIELDS = { "TEMPO", "MANUAL BPM", "INPUT" }
Adapter.READY_FIELDS = { "WINDOW BAR", "WINDOW STEP", "SENSITIVITY", "PAINT POLICY", "ALIGNMENT" }
Adapter.ALIGNMENT_FIELDS = { "HALF TEMPO", "DOUBLE TEMPO", "EXACT BPM", "START BEAT", "FINE START" }
Adapter.PAINT_POLICIES = { "toggle", "add", "replace" }
Adapter.MIN_BPM, Adapter.MAX_BPM = 40, 240
-- Mirrors Bank.WINDOW_CELLS. The displayed window is one four-bar phrase, so
-- paging by this width keeps every reachable position aligned with the phrase
-- the centre button returns to.
Adapter.WINDOW_CELLS = 64
Adapter.INPUT_SOURCES = { "stereo", "left", "right" }
local capture_states = { LISTENING = true, RECORDING = true }
local function outcome(code, extra)
  extra = extra or {}
  extra.code, extra.ok = code, code == "OK"
  return extra
end

local function lanes_of(self)
  local bank = self.runtime.machine and self.runtime.machine.bank
  local names = type(bank) == "table" and bank.lane_names
  return type(names) == "table" and #names > 0 and names or Adapter.LANES
end

-- The lane the player is working on, guaranteed to be one the bank holds.
-- The adapter starts on the device's first lane, and a remote analysis
-- replaces the whole set -- so a stored lane can stop existing without anyone
-- touching it. Everything that reads a lane reads this.
local function current_lane(self)
  local names = lanes_of(self)
  for _, value in ipairs(names) do if value == self.lane then return self.lane end end
  return names[1]
end

local function lane_valid(self, lane)
  for _, value in ipairs(lanes_of(self)) do if value == lane then return true end end
  return false
end

local function state_of(self)
  return self.runtime.machine and self.runtime.machine.state or "EMPTY"
end

local function stopped(self)
  return not self.transport_running and self.is_transport_stopped() == true
end

local function bounded_bpm(value)
  value = math.floor(tonumber(value) or 120)
  return math.max(Adapter.MIN_BPM, math.min(Adapter.MAX_BPM, value))
end

local function source_label(source)
  if source == "left" then return "L" end
  if source == "right" then return "R" end
  return "STEREO"
end

local function setup_available(self)
  local state = state_of(self)
  return state == "EMPTY" or state == "FAILED"
end

local function setup_values(self)
  return self.setup_draft or {
    capture_mode = self.capture_mode, manual_bpm = self.manual_bpm, input_source = self.input_source,
  }
end

local function begin_setup(self)
  if not self.setup_draft then
    self.setup_draft = {
      capture_mode = self.capture_mode, manual_bpm = self.manual_bpm, input_source = self.input_source,
    }
  end
end

local function bank_of(self)
  return self.runtime.machine and self.runtime.machine.bank or nil
end

local function clamp(value, low, high)
  return math.max(low, math.min(high, value))
end

local function select_index(index, amount, length)
  local direction = amount > 0 and 1 or -1
  return ((index - 1 + direction * math.abs(amount)) % length) + 1
end

local function policy_index(policy)
  for index, value in ipairs(Adapter.PAINT_POLICIES) do if value == policy then return index end end
  return 1
end

local function position_label(cell)
  cell = math.max(0, math.floor(cell or 0))
  return string.format("%d.%d.%d", math.floor(cell / 16) + 1, math.floor(cell % 16 / 4) + 1, cell % 4 + 1)
end

local function touch_window(self)
  self.window_revision = self.window_revision + 1
  self.active_paint_preview = nil
end

-- Which entry of the beat grid holds the detected phrase start. The editor
-- opens there rather than on beat one, so a player who opens it to check the
-- alignment and confirms without editing keeps the detector's answer instead
-- of silently replacing it with the first beat of the capture.
local function phrase_beat_index(bank, beats)
  if type(beats) ~= "table" or #beats == 0 then return 1 end
  local cell, spacing = bank.phrase_start_cell, bank.samples_per_cell
  if type(cell) ~= "number" or type(spacing) ~= "number" or type(bank.origin_sample) ~= "number" then return 1 end
  local target, best, distance = bank.origin_sample + cell * spacing, 1, nil
  for index, beat in ipairs(beats) do
    local gap = math.abs(beat - target)
    if distance == nil or gap < distance then best, distance = index, gap end
  end
  return best
end

local function begin_alignment(self)
  local bank = bank_of(self)
  if type(bank) ~= "table" or type(bank.bpm) ~= "number" then return nil end
  local beats = bank.source and bank.source.beat_positions
  beats = type(beats) == "table" and beats or {}
  self.alignment_draft = {
    bpm = bounded_bpm(bank.bpm), start_beat = phrase_beat_index(bank, beats), fine_start_ms = 0,
    beat_positions = beats,
    capture_start_sample = bank.capture_start_sample, capture_end_sample = bank.capture_end_sample,
    sample_rate = bank.sample_rate, origin_sample = bank.origin_sample,
  }
  self.alignment_field = 1
  return self.alignment_draft
end

local function alignment_payload(draft)
  local value = {}
  for key, item in pairs(draft) do if key ~= "beat_positions" then value[key] = item end end
  local beat = draft.beat_positions[draft.start_beat]
  if type(beat) == "number" then value.origin_sample = beat end
  if type(value.origin_sample) == "number" and type(draft.sample_rate) == "number" then
    value.origin_sample = value.origin_sample + draft.fine_start_ms * draft.sample_rate / 1000
  end
  return value
end

local function modal_copy(token)
  if not token then return nil end
  local operation = token.operation
  local text = {
    clear = { title = "CLEAR CAPTURE BANK?", detail = "ALL LANES", note = "PAINTED PATTERNS KEPT" },
    cancel_capture = { title = "CANCEL CAPTURE?" },
    cancel_correction = { title = "CANCEL CORRECTION?" },
  }
  local rendered = text[operation] or { title = "CONFIRM?" }
  return { operation = operation, title = rendered.title, detail = rendered.detail, note = rendered.note }
end

local function hit_count(bank, lane)
  local hits, cells = 0, bank and bank.lanes and bank.lanes[lane]
  if type(cells) ~= "table" then return 0 end
  for _ in pairs(cells) do hits = hits + 1 end
  return hits
end

-- Runtime owns the authoritative modal token.  Poll/key/redraw boundaries all
-- reconcile it, so a completion, timeout, project replacement, clear, failure,
-- or transport Start cannot leave a locally-rendered confirmation actionable.
local function sync_modal(self)
  local machine, token = self.runtime.machine, self.modal
  if not token or type(machine) ~= "table" then return end
  if machine.modal ~= token or machine.state ~= token.state then self.modal = nil end
end

function Adapter.new(deps)
  assert(type(deps) == "table", "dependencies are required")
  assert(type(deps.runtime) == "table", "runtime is required")
  assert(type(deps.runtime.start_capture) == "function", "runtime.start_capture is required")
  assert(type(deps.runtime.record_action) == "function", "runtime.record_action is required")
  assert(type(deps.runtime.confirm_modal) == "function", "runtime.confirm_modal is required")
  assert(type(deps.runtime.finish) == "function", "runtime.finish is required")
  assert(type(deps.transport_stopped) == "function", "transport_stopped is required")
  local mode = deps.mode or "auto"
  assert(mode == "auto" or mode == "manual", "mode must be auto or manual")
  local input_source = deps.input_source or "stereo"
  assert(input_source == "stereo" or input_source == "left" or input_source == "right", "input_source must be stereo, left, or right")
  return setmetatable({ runtime = deps.runtime, is_transport_stopped = deps.transport_stopped,
    capture_mode = mode, lane = "BD", record_held = false, modal = nil,
    manual_bpm = bounded_bpm(deps.manual_bpm), input_source = input_source, setup_field = 1, setup_draft = nil,
    ready_field = 1, alignment_field = 1, alignment_draft = nil, paint_policy = "toggle", paint_shift = 0, window_revision = 0,
    worker_ready = false, transport_running = false, progress = {}, feedback = nil,
    alignment_error = nil }, Adapter)
end

function Adapter:set_capture_mode(mode)
  if mode ~= "auto" and mode ~= "manual" then return outcome("INVALID_MODE") end
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  if not setup_available(self) then return outcome("SETUP_UNAVAILABLE") end
  self.capture_mode = mode
  self.setup_draft = nil
  return outcome("OK")
end

-- Tempo and input selection are intentionally local UI configuration.  This
-- adapter does not assert that a capture/analysis backend consumes BPM or
-- input routing; the existing runtime continues to receive only auto/manual.
function Adapter:enc(n, d)
  if n ~= 2 and n ~= 3 then return outcome("UNCLAIMED") end
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  if self.alignment_draft then
    if type(d) ~= "number" or d == 0 then return outcome("UNCLAIMED") end
    if n == 2 then
      self.alignment_error = nil
      self.alignment_field = select_index(self.alignment_field, d, #Adapter.ALIGNMENT_FIELDS)
      return outcome("ALIGNMENT_FIELD_SELECTED", { field = Adapter.ALIGNMENT_FIELDS[self.alignment_field] })
    end
    self.alignment_error = nil
    local draft, field = self.alignment_draft, Adapter.ALIGNMENT_FIELDS[self.alignment_field]
    if field == "EXACT BPM" then draft.bpm = bounded_bpm(draft.bpm + d)
    elseif field == "START BEAT" and #draft.beat_positions > 0 then
      draft.start_beat = clamp(draft.start_beat + d, 1, #draft.beat_positions)
    elseif field == "FINE START" then
      local candidate = draft.fine_start_ms + d
      local origin = draft.beat_positions[draft.start_beat] or draft.origin_sample
      if type(origin) == "number" and type(draft.sample_rate) == "number" and draft.sample_rate > 0 and
          type(draft.capture_start_sample) == "number" and type(draft.capture_end_sample) == "number" then
        candidate = clamp(candidate, (draft.capture_start_sample - origin) * 1000 / draft.sample_rate,
          (draft.capture_end_sample - origin) * 1000 / draft.sample_rate)
      end
      draft.fine_start_ms = candidate
    end
    return outcome("ALIGNMENT_EDITED", { field = field })
  end
  if state_of(self) == "READY" then
    if type(d) ~= "number" or d == 0 then return outcome("UNCLAIMED") end
    if n == 2 then
      self.ready_field = select_index(self.ready_field, d, #Adapter.READY_FIELDS)
      return outcome("READY_FIELD_SELECTED", { field = Adapter.READY_FIELDS[self.ready_field] })
    end
    local field, bank = Adapter.READY_FIELDS[self.ready_field], bank_of(self)
    if type(bank) ~= "table" then return outcome("NOT_READY") end
    if field == "WINDOW BAR" or field == "WINDOW STEP" then
      if type(self.runtime.set_window_start) ~= "function" then return outcome("UNSUPPORTED") end
      local step = field == "WINDOW BAR" and 16 or 1
      local value = self.runtime:set_window_start((bank.window_start or 0) + d * step)
      if value and (value.ok or value.code == "WINDOW_MOVED") then touch_window(self) end
      self.feedback = value and value.code
      return value or outcome("WINDOW_UNAVAILABLE")
    elseif field == "SENSITIVITY" then
      if type(self.runtime.set_sensitivity) ~= "function" then return outcome("UNSUPPORTED") end
      local current = bank.sensitivities and bank.sensitivities[current_lane(self)]
      if type(current) ~= "number" then return outcome("INVALID_SENSITIVITY") end
      local value = self.runtime:set_sensitivity(current_lane(self), clamp(current + d * .05, 0, 1))
      if value and (value.ok or value.code == "SENSITIVITY_UPDATED") then touch_window(self) end
      self.feedback = value and value.code
      return value or outcome("SENSITIVITY_UNAVAILABLE")
    elseif field == "PAINT POLICY" then
      self.paint_policy = Adapter.PAINT_POLICIES[select_index(policy_index(self.paint_policy), d, #Adapter.PAINT_POLICIES)]
      touch_window(self)
      return outcome("PAINT_POLICY_UPDATED", { policy = self.paint_policy })
    elseif field == "ALIGNMENT" then
      if not begin_alignment(self) then return outcome("ALIGNMENT_UNAVAILABLE") end
      return outcome("ALIGNMENT_OPENED")
    end
  end
  if not setup_available(self) then return outcome("SETUP_UNAVAILABLE") end
  if type(d) ~= "number" or d == 0 then return outcome("UNCLAIMED") end
  begin_setup(self)
  if n == 2 then
    local direction = d > 0 and 1 or -1
    self.setup_field = ((self.setup_field - 1 + direction * math.abs(d)) % #Adapter.SETUP_FIELDS) + 1
    return outcome("SETUP_FIELD_SELECTED", { field = Adapter.SETUP_FIELDS[self.setup_field] })
  end
  local draft, field = self.setup_draft, Adapter.SETUP_FIELDS[self.setup_field]
  if field == "TEMPO" then
    if math.abs(d) % 2 == 1 then draft.capture_mode = draft.capture_mode == "auto" and "manual" or "auto" end
  elseif field == "MANUAL BPM" then
    draft.manual_bpm = bounded_bpm(draft.manual_bpm + d)
  elseif field == "INPUT" then
    local index = 1
    for candidate, source in ipairs(Adapter.INPUT_SOURCES) do if source == draft.input_source then index = candidate end end
    local direction = d > 0 and 1 or -1
    index = ((index - 1 + direction * math.abs(d)) % #Adapter.INPUT_SOURCES) + 1
    draft.input_source = Adapter.INPUT_SOURCES[index]
  end
  return outcome("SETUP_EDITED", { field = field })
end

function Adapter:confirm_setup()
  if not self.setup_draft then return outcome("UNCLAIMED") end
  self.capture_mode = self.setup_draft.capture_mode
  self.manual_bpm = self.setup_draft.manual_bpm
  self.input_source = self.setup_draft.input_source
  self.setup_draft = nil
  return outcome("SETUP_CONFIRMED")
end

function Adapter:cancel_setup()
  if not self.setup_draft then return outcome("UNCLAIMED") end
  self.setup_draft = nil
  return outcome("SETUP_CANCELLED")
end

function Adapter:confirm_alignment()
  if not self.alignment_draft then return outcome("UNCLAIMED") end
  local draft = self.alignment_draft
  local action = Adapter.ALIGNMENT_FIELDS[self.alignment_field]
  if action == "HALF TEMPO" then draft.bpm = bounded_bpm(draft.bpm / 2)
  elseif action == "DOUBLE TEMPO" then draft.bpm = bounded_bpm(draft.bpm * 2) end
  local payload = alignment_payload(draft)
  local apply = self.runtime.apply_alignment or self.runtime.begin_reanalysis
  if type(apply) ~= "function" then return outcome("UNSUPPORTED") end
  local value = apply(self.runtime, payload)
  self.feedback = value and value.code
  if value and value.ok then self.alignment_draft = nil
  else
    -- The draft is kept so the player can edit or cancel it, which means the
    -- screen would otherwise read exactly as it did before they pressed K3.
    -- Remember the refusal so it can be shown instead.
    self.alignment_error = (value and value.code) or "ALIGNMENT_FAILED"
  end
  return value or outcome("ALIGNMENT_FAILED")
end

function Adapter:cancel_alignment()
  if not self.alignment_draft then return outcome("UNCLAIMED") end
  self.alignment_draft, self.alignment_error = nil, nil
  return outcome("ALIGNMENT_CANCELLED")
end

function Adapter:select_lane(lane)
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  if not lane_valid(self, lane) then return outcome("INVALID_LANE") end
  self.lane = lane
  touch_window(self)
  return outcome("LANE_SELECTED", { lane = lane })
end

-- Paint owns no source data here.  This context is the complete view token that
-- the transaction layer must pin before it previews or writes a source pattern.
-- The lane set the grid should show: the bank's own, or the device's default
-- before anything has been captured. The page must not keep its own copy --
-- a hardcoded list there silently overrides a ten lane analysis.
function Adapter:lanes()
  local names, out = lanes_of(self), {}
  for index, lane in ipairs(names) do
    if index > Adapter.MAX_LANE_COLUMNS then break end
    out[index] = lane
  end
  return out
end

function Adapter:paint_context()
  local bank, machine = bank_of(self), self.runtime.machine or {}
  if state_of(self) ~= "READY" or type(bank) ~= "table" then return nil, outcome("NOT_READY") end
  return {
    state = "READY", project_id = machine.project_id, generation = machine.generation,
    analysis_revision = machine.analysis_revision, lane = current_lane(self),
    window_start = bank.window_start or 0, window_revision = self.window_revision,
    policy = self.paint_policy, shift = self.paint_shift, thresholds = bank.sensitivities or {},
  }
end

-- Window navigation. None of this clamps: Runtime already routes every window
-- move through the bank's own bounds, and a second copy of that rule here
-- could only ever disagree with it.
--
-- What the move does report is where it landed and whether it actually went
-- anywhere. Clamping means a refused move and an absorbed one both come back
-- as success, and a caller that cannot tell them apart ends up telling the
-- player it advanced a phrase while the window sat still at the end of the
-- recording. The label is built here too, beside the one definition of what a
-- cell position is called.
local function move_window(self, target)
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  local bank = bank_of(self)
  if state_of(self) ~= "READY" or type(bank) ~= "table" then return outcome("NOT_READY") end
  if type(self.runtime.set_window_start) ~= "function" then return outcome("UNSUPPORTED") end
  local before = bank.window_start or 0
  local value = self.runtime:set_window_start(target)
  if value and (value.ok or value.code == "WINDOW_MOVED") then
    touch_window(self)
    local landed = bank_of(self)
    landed = type(landed) == "table" and landed.window_start or value.window_start
    landed = type(landed) == "number" and landed or before
    value.window_start, value.window_label, value.moved = landed, position_label(landed), landed ~= before
  end
  self.feedback = value and value.code
  return value or outcome("WINDOW_UNAVAILABLE")
end

local function step_window(self, delta, span)
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  local bank = bank_of(self)
  if state_of(self) ~= "READY" or type(bank) ~= "table" then return outcome("NOT_READY") end
  if type(delta) ~= "number" or delta ~= delta or math.floor(delta) ~= delta then return outcome("INVALID_SHIFT") end
  return move_window(self, (bank.window_start or 0) + delta * span)
end

function Adapter:jump_to_phrase_start()
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  local bank = bank_of(self)
  if state_of(self) ~= "READY" or type(bank) ~= "table" then return outcome("NOT_READY") end
  if type(bank.phrase_start_cell) ~= "number" then return outcome("WINDOW_UNAVAILABLE") end
  -- Runtime clamps through Bank.with_window_start, so a phrase start with no
  -- room for a whole window behind it lands on the last valid position here
  -- without this module needing its own copy of the window rule.
  return move_window(self, bank.phrase_start_cell)
end

-- A single step, which is what one press of the browse buttons is worth. It
-- matches what those buttons do for every other algorithm, where a press
-- shifts the paint pattern by one.
function Adapter:nudge_window(delta)
  return step_window(self, delta, 1)
end

-- A whole four-bar phrase, which is exactly the width of the window, so every
-- position reachable this way stays aligned with the phrase the centre button
-- returns to. Held rather than pressed, because it is the coarse gesture.
function Adapter:page_window(delta)
  return step_window(self, delta, Adapter.WINDOW_CELLS)
end

function Adapter:invalidate_paint_preview()
  touch_window(self)
  return outcome("PREVIEW_INVALIDATED")
end

function Adapter:shift_paint(delta)
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  if state_of(self) ~= "READY" or type(delta) ~= "number" or delta ~= delta or delta == math.huge or delta == -math.huge or
      math.floor(delta) ~= delta then return outcome("INVALID_SHIFT") end
  self.paint_shift = self.paint_shift + delta
  touch_window(self)
  return outcome("PAINT_SHIFTED", { shift = self.paint_shift })
end

function Adapter:reset_paint_shift()
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  if state_of(self) ~= "READY" then return outcome("NOT_READY") end
  self.paint_shift = 0
  touch_window(self)
  return outcome("PAINT_SHIFT_RESET", { shift = 0 })
end

function Adapter:paint_target(target)
  local context, problem = self:paint_context(); if not context then return nil, problem end
  if type(target) ~= "table" then return nil, outcome("INVALID_TARGET") end
  local value = {}
  for key, item in pairs(target) do value[key] = item end
  value.project_id = value.project_id or context.project_id
  return value
end

function Adapter:paint_preview(target)
  if not stopped(self) then return nil, outcome("STOP_SEQUENCER") end
  if type(self.runtime.paint_preview) ~= "function" then return nil, outcome("UNSUPPORTED") end
  local context, problem = self:paint_context(); if not context then return nil, problem end
  local pinned_target, target_problem = self:paint_target(target); if not pinned_target then return nil, target_problem end
  local preview, value = self.runtime:paint_preview(context, pinned_target)
  if preview then self.active_paint_preview = preview end
  return preview, value
end

function Adapter:paint_commit(preview, replace_confirmed)
  if not stopped(self) then return nil, outcome("STOP_SEQUENCER") end
  if type(self.runtime.paint_commit) ~= "function" then return nil, outcome("UNSUPPORTED") end
  local context, problem = self:paint_context(); if not context then return nil, problem end
  local saved, value = self.runtime:paint_commit(context, preview or self.active_paint_preview, replace_confirmed)
  if saved then self.active_paint_preview = nil end
  return saved, value
end

function Adapter:paint_undo(target)
  if not stopped(self) then return nil, outcome("STOP_SEQUENCER") end
  if type(self.runtime.paint_undo) ~= "function" then return nil, outcome("UNSUPPORTED") end
  local context, problem = self:paint_context(); if not context then return nil, problem end
  return self.runtime:paint_undo(context, target)
end

function Adapter:paint_redo(target)
  if not stopped(self) then return nil, outcome("STOP_SEQUENCER") end
  if type(self.runtime.paint_redo) ~= "function" then return nil, outcome("UNSUPPORTED") end
  local context, problem = self:paint_context(); if not context then return nil, problem end
  return self.runtime:paint_redo(context, target)
end

-- Capture diagnostics are observed data from the worker/inference bridge.  The
-- adapter does not infer tempo, confidence, or Finish eligibility itself.
function Adapter:set_capture_progress(value)
  assert(type(value) == "table", "capture progress is required")
  self.progress = {}
  for _, key in ipairs({ "enough_audio", "tempo", "source", "listening_confidence", "acquired_beats", "analysis_progress" }) do
    self.progress[key] = value[key]
  end
end

-- Explicit progress wins when a host supplies it; otherwise the runtime is
-- asked directly. Nothing in the application ever called
-- set_capture_progress, so relying on it alone left Finish permanently
-- disabled and a recording could never reach analysis.
function Adapter:finish_eligible()
  if self.progress.enough_audio ~= nil then return self.progress.enough_audio == true end
  local runtime = self.runtime
  if type(runtime) == "table" and type(runtime.capture_progress) == "function" then
    local value = runtime:capture_progress()
    return type(value) == "table" and value.enough_audio == true
  end
  return false
end

-- The protocol keeps its exact codes; the screen is 128 pixels wide and the
-- player needs to know what to do about it. A code with no entry here is shown
-- with its underscores opened out rather than hidden, so a new one is visible
-- rather than silently swallowed.
Adapter.MESSAGES = {
  BUSY = "ALREADY CAPTURING",
  BAD_STATE = "WRONG STATE",
  INPUT_RESOURCE_BUSY = "INPUT UNAVAILABLE",
  INVALID_DURATION = "BAD LENGTH",
  PUBLISH_FAILED = "SAVE FAILED",
  PUBLISH_TIMEOUT = "SAVE TIMED OUT",
  STALE_JOB = "STALE CAPTURE",
}

function Adapter.readable(code)
  if type(code) ~= "string" or code == "" then return "FAILED" end
  return Adapter.MESSAGES[code] or code:gsub("_", " ")
end

function Adapter:set_status(code, detail)
  self.feedback = code
  if code == "CAPTURE_WORKER_READY" then self.worker_ready = true
  elseif code == "CAPTURE_WORKER_UNAVAILABLE" or code == "CAPTURE_PREFLIGHT_UNAVAILABLE" then self.worker_ready = false end
  self.status_detail = detail
end

function Adapter:enter()
  if type(self.runtime.enter) ~= "function" then return outcome("UNSUPPORTED") end
  local value = self.runtime:enter()
  if value and value.ok then self.worker_ready = true else self.worker_ready = false end
  self.feedback = value and value.code or "WORKER_UNAVAILABLE"
  return value or outcome("WORKER_UNAVAILABLE")
end

function Adapter:record_pressed()
  if self.record_held then return outcome("HELD_RECORD") end
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  if self.setup_draft then return outcome("SETUP_ACTIVE") end
  self.record_held = true
  local state = state_of(self)
  local value
  if state == "EMPTY" or state == "FAILED" then
    value = self.runtime:start_capture(self.capture_mode)
  elseif capture_states[state] and self:finish_eligible() == true then
    -- Record started the take, so Record ends it. Crossing to K3 to stop
    -- something the grid began is a split a player has to memorise.
    value = self.runtime:finish(true)
  else
    -- Too little audio to finish, so the gesture keeps its older meaning and
    -- offers to abandon the take rather than doing nothing at all.
    value = self.runtime:record_action()
    if type(value) == "table" and type(value.operation) == "string" then self.modal = value end
  end
  self.feedback = value and value.code
  return value or outcome("NO_ACTION")
end

function Adapter:record_released()
  if not self.record_held then return outcome("UNCLAIMED") end
  self.record_held = false
  return outcome("RELEASE_CONSUMED")
end

-- Feed raw native grid edges here.  `true` is represented by a result other
-- than UNCLAIMED, so integration can consume only the Record gesture and leave
-- every unrelated legacy key to the existing dispatcher.
function Adapter:grid_key(x, y, z)
  if x == 1 and y == 2 then
    if z == 1 then return self:record_pressed() end
    if z == 0 then return self:record_released() end
    return outcome("UNCLAIMED")
  end
  local names = lanes_of(self)
  local columns = math.min(#names, Adapter.MAX_LANE_COLUMNS)
  if y == 2 and x >= 3 and x <= 2 + columns then
    if z ~= 1 then return outcome("UNCLAIMED") end
    return self:select_lane(names[x - 2])
  end
  return outcome("UNCLAIMED")
end

function Adapter:key(n, z)
  if z ~= 1 or (n ~= 2 and n ~= 3) then return outcome("UNCLAIMED") end
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  sync_modal(self)
  if self.modal then
    if self.record_held then return outcome("RELEASE_PENDING") end
    local token, accepted = self.modal, n == 3
    self.modal = nil
    local value = self.runtime:confirm_modal(token, accepted)
    self.feedback = value and value.code
    return value or outcome("STALE_REQUEST")
  end
  if self.alignment_draft then
    if n == 2 then return self:cancel_alignment() end
    return self:confirm_alignment()
  end
  if self.setup_draft then
    if n == 2 then return self:cancel_setup() end
    return self:confirm_setup()
  end
  if n == 3 and capture_states[state_of(self)] then
    if self:finish_eligible() ~= true then return outcome("MORE_AUDIO_NEEDED") end
    local value = self.runtime:finish(true)
    self.feedback = value and value.code
    return value or outcome("NOT_CAPTURING")
  end
  return outcome("UNCLAIMED")
end

-- These are application transport hooks, not grid actions.  Start has priority
-- over modal input and makes the controller gate subsequent capture gestures
-- until a matching Stop notification arrives.
function Adapter:transport_started()
  self.transport_running, self.record_held, self.modal, self.setup_draft, self.alignment_draft = true, false, nil, nil, nil
  self.alignment_error = nil
  self.active_paint_preview = nil
  if type(self.runtime.transport_started) ~= "function" then return outcome("UNSUPPORTED") end
  return self.runtime:transport_started()
end
function Adapter:transport_stopped()
  self.transport_running = false
  if type(self.runtime.transport_stopped_event) ~= "function" then return outcome("UNSUPPORTED") end
  return self.runtime:transport_stopped_event()
end
function Adapter:disconnect()
  self.record_held, self.active_paint_preview = false, nil
  return outcome("OK")
end
function Adapter:leave()
  return self:disconnect()
end
function Adapter:poll()
  if type(self.runtime.poll) ~= "function" then return outcome("NO_EVENT") end
  local value = self.runtime:poll()
  sync_modal(self)
  return value
end

function Adapter:screen_model()
  sync_modal(self)
  local machine, bank, state = self.runtime.machine or {}, self.runtime.machine and self.runtime.machine.bank, state_of(self)
  local total_steps = type(bank) == "table" and bank.timeline_cells or nil
  local tempo = type(bank) == "table" and bank.bpm or self.progress.tempo
  local tempo_source = type(bank) == "table" and bank.tempo_mode or self.progress.source
  -- A tempo the detector never found is the backend's default, not a reading
  -- of the player's playing, and the grid every trig lands on is built from
  -- it. Saying "auto" there claims a measurement that was never made.
  local tempo_detected = type(bank) ~= "table" or bank.tempo_detected ~= false
  if not tempo_detected and tempo_source == "auto" then tempo_source = "default" end
  local setup = setup_values(self)
  local window_start = type(bank) == "table" and bank.window_start or nil
  local window_end = type(window_start) == "number" and window_start + 63 or nil
  local model = { title = "RHYTHM DOCTOR", state = state, lane = current_lane(self),
    hit_count = hit_count(bank, current_lane(self)), tempo = tempo, tempo_source = tempo_source,
    tempo_detected = tempo_detected,
    listening_confidence = self.progress.listening_confidence, acquired_beats = self.progress.acquired_beats,
    analysis_progress = self.progress.analysis_progress, total_steps = total_steps,
    total_bars = type(total_steps) == "number" and math.floor(total_steps / 16) or nil,
    capture_mode = setup.capture_mode, manual_bpm = setup.manual_bpm, input_source = source_label(setup.input_source),
    setup = { active = self.setup_draft ~= nil, field = Adapter.SETUP_FIELDS[self.setup_field] },
    ready = { active = state == "READY" and self.alignment_draft == nil, field = Adapter.READY_FIELDS[self.ready_field] },
    alignment = self.alignment_draft and { active = true, field = Adapter.ALIGNMENT_FIELDS[self.alignment_field],
      error = self.alignment_error and self.alignment_error:gsub("_", " ") or nil,
      bpm = self.alignment_draft.bpm, start_beat = self.alignment_draft.start_beat,
      fine_start_ms = self.alignment_draft.fine_start_ms, capture_start_sample = self.alignment_draft.capture_start_sample,
      capture_end_sample = self.alignment_draft.capture_end_sample } or { active = false },
    paint_policy = self.paint_policy, sensitivity = type(bank) == "table" and bank.sensitivities and bank.sensitivities[current_lane(self)] or nil,
    window_start = window_start, window_end = window_end,
    window_start_label = window_start ~= nil and position_label(window_start) or nil,
    window_end_label = window_end ~= nil and position_label(window_end) or nil,
    at_window_start = window_start == 0,
    at_window_end = type(total_steps) == "number" and type(window_end) == "number" and window_end == total_steps - 1,
    window_revision = self.window_revision,
    modal = modal_copy(self.modal), finish_enabled = false,
    worker_ready = self.worker_ready }
  if not stopped(self) then model.status = "STOP SEQUENCER"
  elseif self.modal then model.status = model.modal.title
  elseif self.alignment_draft then
    model.status = self.alignment_error and self.alignment_error:gsub("_", " ")
      or ("ALIGNMENT / " .. Adapter.ALIGNMENT_FIELDS[self.alignment_field])
  elseif not self.worker_ready and (state == "EMPTY" or state == "FAILED") then model.status = "NOT READY"
  elseif capture_states[state] then
    model.finish_enabled = self:finish_eligible() == true
    model.status = model.finish_enabled and "ENOUGH / REC OR K3" or "MORE AUDIO NEEDED"
  elseif state == "FAILED" then model.status = Adapter.readable(machine.last_message)
  else model.status = state end
  return model
end

return Adapter

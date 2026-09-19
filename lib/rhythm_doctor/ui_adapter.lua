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

Adapter.LANES = { "BD", "SD", "HH", "TOM", "BASS" }
Adapter.SETUP_FIELDS = { "TEMPO", "MANUAL BPM", "INPUT" }
Adapter.MIN_BPM, Adapter.MAX_BPM = 40, 240
Adapter.INPUT_SOURCES = { "stereo", "left", "right" }
local capture_states = { LISTENING = true, RECORDING = true }
local function outcome(code, extra)
  extra = extra or {}
  extra.code, extra.ok = code, code == "OK"
  return extra
end

local function lane_valid(lane)
  for _, value in ipairs(Adapter.LANES) do if value == lane then return true end end
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
  return state == "EMPTY" or state == "FAILED" or state == "READY"
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

local function modal_copy(token)
  if not token then return nil end
  local operation = token.operation
  local text = {
    clear = { title = "CLEAR CAPTURE BANK?", detail = "ALL 5 LANES", note = "PAINTED PATTERNS KEPT" },
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
    worker_ready = false, transport_running = false, progress = {}, feedback = nil }, Adapter)
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

function Adapter:select_lane(lane)
  if not stopped(self) then return outcome("STOP_SEQUENCER") end
  if not lane_valid(lane) then return outcome("INVALID_LANE") end
  self.lane = lane
  return outcome("LANE_SELECTED", { lane = lane })
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
  else
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
  if y == 2 and x >= 3 and x <= 7 then
    if z ~= 1 then return outcome("UNCLAIMED") end
    return self:select_lane(Adapter.LANES[x - 2])
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
  if self.setup_draft then
    if n == 2 then return self:cancel_setup() end
    return self:confirm_setup()
  end
  if n == 3 and capture_states[state_of(self)] then
    if self.progress.enough_audio ~= true then return outcome("MORE_AUDIO_NEEDED") end
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
  self.transport_running, self.record_held, self.modal, self.setup_draft = true, false, nil, nil
  if type(self.runtime.transport_started) ~= "function" then return outcome("UNSUPPORTED") end
  return self.runtime:transport_started()
end
function Adapter:transport_stopped()
  self.transport_running = false
  if type(self.runtime.transport_stopped_event) ~= "function" then return outcome("UNSUPPORTED") end
  return self.runtime:transport_stopped_event()
end
function Adapter:disconnect()
  self.record_held = false
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
  local setup = setup_values(self)
  local model = { title = "RHYTHM DOCTOR", state = state, lane = self.lane,
    hit_count = hit_count(bank, self.lane), tempo = tempo, tempo_source = tempo_source,
    listening_confidence = self.progress.listening_confidence, acquired_beats = self.progress.acquired_beats,
    analysis_progress = self.progress.analysis_progress, total_steps = total_steps,
    total_bars = type(total_steps) == "number" and math.floor(total_steps / 16) or nil,
    capture_mode = setup.capture_mode, manual_bpm = setup.manual_bpm, input_source = source_label(setup.input_source),
    setup = { active = self.setup_draft ~= nil, field = Adapter.SETUP_FIELDS[self.setup_field] },
    modal = modal_copy(self.modal), finish_enabled = false,
    worker_ready = self.worker_ready }
  if not stopped(self) then model.status = "STOP SEQUENCER"
  elseif self.modal then model.status = model.modal.title
  elseif not self.worker_ready and (state == "EMPTY" or state == "FAILED") then model.status = "NOT READY"
  elseif capture_states[state] then
    model.finish_enabled = self.progress.enough_audio == true
    model.status = model.finish_enabled and "ENOUGH AUDIO / K3 FINISH" or "MORE AUDIO NEEDED"
  elseif state == "FAILED" then model.status = machine.last_message or "FAILED"
  else model.status = state end
  return model
end

return Adapter

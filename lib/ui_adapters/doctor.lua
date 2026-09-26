-- Rhythm Doctor descriptor adapter (docs/ui-reimplementation, UI02).
--
-- Owner: the existing Rhythm Doctor UI controller (lib/rhythm_doctor/ui_adapter.lua)
-- held by the Trig page. `owners` is:
--   owners.trigger_edit_page  the trigger page module (falls back to the global
--                             `trigger_edit_page`); it provides get_rhythm_doctor(),
--                             rhythm_doctor_preview_armed(), rhythm_doctor_paint_destination()
--                             and get_algorithm(). trigger_edit_page_ui.adapter_owners()
--                             does not carry it, so the integrator passes it.
--   owners.server_endpoint    optional function returning the configured analysis server
--                             (mosaic.lua rhythm_doctor_server_endpoint). Without it R14
--                             reads the same two native parameters the same way.
--
-- Routes come only from spec.doctor_routes (route/inputs below). Every edit and
-- invoke forwards to the owner's enc/key/record closures, or to the page's browse
-- functions, exactly as ui.enc/ui.key and the grid reach them today. The transport
-- gate, drafts and modal validation stay in the owner; the modal token is opaque and
-- is only compared by identity before the owner's own K2/K3 runs.

local routes = nil

-- Owner codes that report an accepted gesture. Everything else is the owner's
-- refusal and is returned as a failed outcome carrying the same code.
local ACCEPTED = {
  OK = true, SETUP_FIELD_SELECTED = true, SETUP_EDITED = true, SETUP_CONFIRMED = true, SETUP_CANCELLED = true,
  READY_FIELD_SELECTED = true, WINDOW_MOVED = true, SENSITIVITY_UPDATED = true, PAINT_POLICY_UPDATED = true,
  ALIGNMENT_OPENED = true, ALIGNMENT_FIELD_SELECTED = true, ALIGNMENT_EDITED = true, ALIGNMENT_CANCELLED = true,
  CANCELLED = true, RELEASE_CONSUMED = true, LANE_SELECTED = true,
}

local function none(value)
  if value == nil then return "NONE" end
  return tostring(value)
end

local function index_of(list, value)
  for index, item in ipairs(list) do if item == value then return index end end
  return nil
end

local function in_domain(allowed, value)
  if type(allowed) == "table" then return index_of(allowed, value) ~= nil end
  return allowed == value
end

-- Pure router ------------------------------------------------------------------

-- route(state) -> screen, row_id. state = {doctor_state, modal_operation, draft,
-- preview, playing[, outcome]}. A missing key is a contract error. With an
-- outcome, a doctor_routes.flows override replaces the row screen only on the
-- rows it lists (all of which are overridable).
local function route(state)
  assert(type(state) == "table", "doctor route needs a state")
  for _, key in ipairs({"doctor_state", "modal_operation", "draft", "preview", "playing"}) do
    assert(state[key] ~= nil, "doctor route state is missing " .. key)
  end
  for _, row in ipairs(routes.rows) do
    local match = true
    for key, allowed in pairs(row.when) do
      if not in_domain(allowed, state[key]) then match = false; break end
    end
    if match then
      if state.outcome ~= nil then
        for _, flow in pairs(routes.flows) do
          for _, override in ipairs(flow.overrides) do
            if override.outcome == state.outcome and row.overridable and index_of(override.rows, row.id) then
              return override.screen, row.id
            end
          end
        end
      end
      return row.screen, row.id
    end
  end
  return nil, nil
end

return function(ui_adapters, owners)
  owners = owners or {}
  routes = ui_adapters.spec.doctor_routes

  local function page()
    return owners.trigger_edit_page or _ENV["trigger_edit_page"]
  end

  local function doctor()
    local p = page()
    return p and type(p.get_rhythm_doctor) == "function" and p.get_rhythm_doctor() or nil
  end

  local function playing(A)
    return not (not A.transport_running and A.is_transport_stopped() == true)
  end

  local function draft_of(A)
    if A.alignment_draft then return A.alignment_error ~= nil and "alignment_refused" or "alignment" end
    if A.setup_draft then return "setup" end
    return "none"
  end

  -- The doctor_routes inputs read from the owner. screen_model() runs the owner's
  -- sync_modal first, exactly as a redraw does, so the modal is the live one.
  local function inputs(A, model)
    A = A or doctor()
    if not A then return nil end
    model = model or A:screen_model()
    local p = page()
    return {
      doctor_state = model.state,
      modal_operation = model.modal and model.modal.operation or "none",
      draft = draft_of(A),
      preview = (p and type(p.rhythm_doctor_preview_armed) == "function" and p.rhythm_doctor_preview_armed()) and "armed" or "none",
      playing = playing(A),
    }
  end

  -- Outcomes -------------------------------------------------------------------

  local function wrap(value)
    if type(value) ~= "table" or type(value.code) ~= "string" then
      return ui_adapters.outcome({result = value})
    end
    if ACCEPTED[value.code] then return ui_adapters.outcome({status = value.code, result = value}) end
    return ui_adapters.fail(value.code, {result = value})
  end

  -- E2 onto the field, then E3: the gestures ui.enc sends today. The owner keeps
  -- its field cursor; E2 is skipped when the cursor is already there.
  local function select_field(A, ids, cursor, id)
    local index = index_of(ids, id)
    if index ~= A[cursor] then
      local value = A:enc(2, index - A[cursor])
      if not ACCEPTED[value.code] then return value end
    end
    return nil
  end

  local function encoder_edit(A, ids, cursor, id)
    return function(delta)
      local refused = select_field(A, ids, cursor, id)
      if refused then return wrap(refused) end
      return wrap(A:enc(3, delta))
    end
  end

  local function key_invoke(A, ids, cursor, id, n)
    return function()
      local refused = select_field(A, ids, cursor, id)
      if refused then return wrap(refused) end
      return wrap(A:key(n, 1))
    end
  end

  -- A Record tap: the page's register_pre press then its register_post release.
  local function record(A)
    return {id = "record", label = "Record", kind = "action",
      value = A.worker_ready and "READY" or "NOT READY",
      domain = {grid = {x = 1, y = 2}, worker_ready = A.worker_ready == true},
      invoke = function()
        local value = A:record_pressed()
        A:record_released()
        return wrap(value)
      end}
  end

  local function bank_value(A, model)
    local bank = A.runtime.machine and A.runtime.machine.bank
    if type(bank) ~= "table" then return "NONE" end
    return "HITS " .. tostring(model.hit_count or 0) .. " / " .. tostring(model.state or "EMPTY")
  end

  local function destination()
    local p = page()
    local target = p and type(p.rhythm_doctor_paint_destination) == "function" and p.rhythm_doctor_paint_destination() or nil
    return target
  end

  local function server_endpoint()
    if type(owners.server_endpoint) == "function" then return owners.server_endpoint() end
    -- Same reading as mosaic.lua rhythm_doctor_server_endpoint (not reachable from here).
    if params == nil or type(params.get) ~= "function" then return nil end
    local ok, enabled = pcall(function() return params:get("rhythm_doctor_use_server") end)
    if not ok or enabled ~= 2 then return nil end
    local read, endpoint = pcall(function() return params:get("rhythm_doctor_server") end)
    if not read or type(endpoint) ~= "string" or endpoint:match("^%s*$") then return nil end
    return (endpoint:gsub("^%s+", ""):gsub("%s+$", ""))
  end

  local function browse(name, delta, hold_name)
    return function(modifiers)
      local call = _ENV[(modifiers and modifiers.hold and hold_name) or name]
      if type(call) ~= "function" then return ui_adapters.fail("unsupported") end
      if delta == nil then return ui_adapters.outcome({result = call()}) end
      return ui_adapters.outcome({result = call(delta)})
    end
  end

  -- Descriptor sets -------------------------------------------------------------

  local describe = {}

  describe.R01 = function(A, model)
    local Adapter = getmetatable(A)
    local ids = Adapter.SETUP_FIELD_IDS
    local selected = model.setup.active and ids[index_of(Adapter.SETUP_FIELDS, model.setup.field)] or nil
    local function sel(id) return selected == id end
    return {
      record(A),
      {id = "tempo", label = "Tempo", kind = "value", value = string.upper(tostring(model.capture_mode or "auto")),
        selected = sel("tempo"), domain = {enum = {"auto", "manual"}, consumed_by = "runtime:start_capture"},
        edit = encoder_edit(A, ids, "setup_field", "tempo")},
      {id = "manual_bpm", label = "Manual BPM", kind = "value", value = tostring(model.manual_bpm),
        selected = sel("manual_bpm"),
        domain = {min = Adapter.MIN_BPM, max = Adapter.MAX_BPM, step = 1, unit = "bpm", local_only = true},
        edit = encoder_edit(A, ids, "setup_field", "manual_bpm")},
      {id = "input", label = "Input", kind = "value", value = tostring(model.input_source),
        selected = sel("input"), domain = {enum = Adapter.INPUT_SOURCES, local_only = true},
        edit = encoder_edit(A, ids, "setup_field", "input")},
    }
  end

  describe.R02 = function(A, model)
    local progress = type(A.runtime.capture_progress) == "function" and A.runtime:capture_progress() or {}
    return {
      {id = "elapsed", label = "Elapsed", kind = "readonly",
        value = type(progress.captured_seconds) == "number" and string.format("%.1fs", progress.captured_seconds) or "NONE",
        domain = {unit = "s", required = progress.required_seconds}},
      {id = "audio", label = "Audio", kind = "readonly", value = model.finish_enabled and "ENOUGH" or "MORE AUDIO NEEDED"},
      {id = "finish", label = "Finish", kind = "action", value = model.finish_enabled and "REC OR K3" or "MORE AUDIO NEEDED",
        domain = {eligible = model.finish_enabled == true}, invoke = function() return wrap(A:key(3, 1)) end},
      {id = "capture_still_active", label = "Capture still active", kind = "readonly", value = model.state},
    }
  end

  describe.R04 = function(A, model)
    return {
      {id = "phase", label = "Phase", kind = "readonly", value = model.state},
      {id = "lanes", label = "Lanes", kind = "readonly", value = table.concat(A:lanes(), " ")},
      {id = "bank", label = "Bank", kind = "readonly", value = bank_value(A, model)},
      record(A),
    }
  end

  describe.R05 = function(A, model)
    local Adapter = getmetatable(A)
    local ids = Adapter.READY_FIELD_IDS
    local selected = model.ready.active and ids[index_of(Adapter.READY_FIELDS, model.ready.field)] or nil
    local start = model.window_start
    return {
      {id = "window_bar", label = "Window bar", kind = "value", selected = selected == "window_bar",
        value = type(start) == "number" and tostring(math.floor(start / 16) + 1) or "NONE",
        domain = {step = 16, unit = "cells", window_start = start, label = model.window_start_label},
        edit = encoder_edit(A, ids, "ready_field", "window_bar")},
      {id = "window_step", label = "Window step", kind = "value", selected = selected == "window_step",
        value = type(start) == "number" and tostring(start + 1) or "NONE",
        domain = {step = 1, unit = "cells", window_start = start, label = model.window_start_label},
        edit = encoder_edit(A, ids, "ready_field", "window_step")},
      {id = "sensitivity", label = "Sensitivity", kind = "value", selected = selected == "sensitivity",
        value = none(model.sensitivity), domain = {min = 0, max = 1, step = 0.05, lane = model.lane},
        edit = encoder_edit(A, ids, "ready_field", "sensitivity")},
      {id = "paint_policy", label = "Paint policy", kind = "value", selected = selected == "paint_policy",
        value = string.upper(tostring(model.paint_policy or "toggle")), domain = {enum = Adapter.PAINT_POLICIES},
        edit = encoder_edit(A, ids, "ready_field", "paint_policy")},
      -- E3 on Alignment opens the draft; the owner refuses it while playing.
      {id = "alignment", label = "Alignment", kind = "action", selected = selected == "alignment",
        domain = {opens = "R06", stopped_only = true},
        invoke = function()
          local refused = select_field(A, ids, "ready_field", "alignment")
          if refused then return wrap(refused) end
          return wrap(A:enc(3, 1))
        end},
    }
  end

  local function alignment_descriptors(A, model)
    local Adapter = getmetatable(A)
    local ids = Adapter.ALIGNMENT_FIELD_IDS
    local selected = ids[index_of(Adapter.ALIGNMENT_FIELDS, model.alignment.field)]
    local beats = A.alignment_draft.beat_positions
    return {
      half_tempo = {id = "half_tempo", label = "Half tempo", kind = "action", selected = selected == "half_tempo",
        value = tostring(model.alignment.bpm), domain = {unit = "bpm", draft_bpm = model.alignment.bpm},
        invoke = key_invoke(A, ids, "alignment_field", "half_tempo", 3)},
      double_tempo = {id = "double_tempo", label = "Double tempo", kind = "action", selected = selected == "double_tempo",
        value = tostring(model.alignment.bpm), domain = {unit = "bpm", draft_bpm = model.alignment.bpm},
        invoke = key_invoke(A, ids, "alignment_field", "double_tempo", 3)},
      exact_bpm = {id = "exact_bpm", label = "Exact BPM", kind = "value", selected = selected == "exact_bpm",
        value = tostring(model.alignment.bpm), domain = {min = Adapter.MIN_BPM, max = Adapter.MAX_BPM, step = 1, unit = "bpm"},
        edit = encoder_edit(A, ids, "alignment_field", "exact_bpm")},
      start_beat = {id = "start_beat", label = "Start beat", kind = "value", selected = selected == "start_beat",
        value = tostring(model.alignment.start_beat), domain = {min = 1, max = #beats, step = 1},
        edit = encoder_edit(A, ids, "alignment_field", "start_beat")},
      fine_start = {id = "fine_start", label = "Fine start", kind = "value", selected = selected == "fine_start",
        value = tostring(model.alignment.fine_start_ms or 0) .. "ms", domain = {step = 1, unit = "ms"},
        edit = encoder_edit(A, ids, "alignment_field", "fine_start")},
    }
  end

  describe.R06 = function(A, model)
    if not model.alignment.active then return nil, "no_alignment_draft" end
    local d = alignment_descriptors(A, model)
    return {d.half_tempo, d.double_tempo, d.exact_bpm, d.start_beat, d.fine_start}
  end

  describe.R07 = function(A, model)
    if not model.alignment.active then return nil, "no_alignment_draft" end
    local d = alignment_descriptors(A, model)
    return {
      {id = "refusal", label = "Refused", kind = "readonly", value = none(model.alignment.error)},
      d.start_beat,
      {id = "draft_kept", label = "Draft kept", kind = "readonly"},
      {id = "k2_discards", label = "K2 discards draft", kind = "action", invoke = function() return wrap(A:key(2, 1)) end},
    }
  end

  local function destination_value()
    local target = destination()
    if type(target) ~= "table" or target.pattern_id == nil then return "NONE", {} end
    return tostring(target.pattern_id), {song_slot = target.song_slot, pattern_id = target.pattern_id}
  end

  describe.R08 = function(A, model)
    local value, target = destination_value()
    return {
      {id = "policy", label = "Policy", kind = "readonly", value = string.upper(tostring(model.paint_policy or "toggle"))},
      {id = "window_start", label = "Window start", kind = "readonly", value = none(model.window_start_label)},
      {id = "destination", label = "Destination", kind = "readonly", value = value, domain = target},
      {id = "capture_bank_kept", label = "Capture bank kept", kind = "readonly"},
    }
  end

  describe.R09 = function(A, model)
    local value, target = destination_value()
    local window = model.window_start_label and (model.window_start_label .. "-" .. tostring(model.window_end_label)) or "NONE"
    return {
      {id = "painted", label = "Painted", kind = "readonly", value = value, domain = target},
      {id = "policy", label = "Policy", kind = "readonly", value = string.upper(tostring(model.paint_policy or "toggle"))},
      {id = "window", label = "Window", kind = "readonly", value = window},
      {id = "bank", label = "Bank", kind = "readonly", value = bank_value(A, model)},
    }
  end

  describe.R11 = function(A, model)
    return {
      {id = "transport", label = "Transport", kind = "readonly", value = playing(A) and "RUNNING" or "STOPPED"},
      {id = "record_setup", label = "Record / setup", kind = "readonly", value = none(model.status)},
      {id = "lane", label = "Lane", kind = "readonly", value = none(model.lane)},
      {id = "bank", label = "Bank", kind = "readonly", value = bank_value(A, model)},
    }
  end

  describe.R12 = function(A, model)
    local machine = A.runtime.machine or {}
    local reason = model.state == "FAILED" and A.readable(machine.last_message) or (tostring(model.state):gsub("_", " "))
    return {
      {id = "reason", label = "Reason", kind = "readonly", value = reason, domain = {code = machine.last_message}},
      record(A),
      {id = "setup", label = "Setup", kind = "readonly", value = tostring(model.setup.field), domain = {opens = "R01"}},
      {id = "bank", label = "Bank", kind = "readonly", value = bank_value(A, model)},
    }
  end

  -- One lane descriptor per adapter:lanes() entry, placed by adapter:lane_cells().
  -- Selection stays on the grid (G41), dispatched by the page through lane_at.
  describe.R13 = function(A, model)
    local out = {}
    for index, cell in ipairs(A:lane_cells()) do
      local key = "lane:" .. string.lower(cell.lane)
      out[#out + 1] = {id = key, label = cell.lane, kind = "readonly", repeat_key = key,
        value = "GRID " .. cell.x .. "," .. cell.y, selected = cell.lane == model.lane,
        domain = {lane = cell.lane, index = index, x = cell.x, y = cell.y}}
    end
    out[#out + 1] = {id = "selected", label = "Selected", kind = "readonly", value = none(model.lane)}
    return out
  end

  describe.R14 = function(A, model)
    local endpoint = server_endpoint()
    return {
      {id = "manual_bpm", label = "Manual BPM", kind = "readonly", value = tostring(model.manual_bpm), domain = {local_only = true}},
      {id = "stereo_l_r", label = "Stereo / L / R", kind = "readonly", value = tostring(model.input_source), domain = {local_only = true}},
      {id = "backend", label = "Backend", kind = "readonly", value = endpoint and "SERVER" or "LOCAL"},
      {id = "server", label = "Server", kind = "readonly", value = none(endpoint),
        domain = {params = {"rhythm_doctor_use_server", "rhythm_doctor_server"}}},
    }
  end

  describe.R15 = function(A, model)
    return {
      {id = "back", label = "Back", kind = "action", domain = {grid = {x = 10, y = 8}},
        invoke = browse("rhythm_doctor_nudge_window", -1, "rhythm_doctor_page_window")},
      {id = "phrase_start", label = "Phrase start", kind = "action", domain = {grid = {x = 11, y = 8}},
        invoke = browse("rhythm_doctor_jump_to_phrase_start")},
      {id = "forward", label = "Forward", kind = "action", domain = {grid = {x = 12, y = 8}},
        invoke = browse("rhythm_doctor_nudge_window", 1, "rhythm_doctor_page_window")},
      {id = "window", label = "Window", kind = "readonly", value = none(model.window_start_label)},
    }
  end

  -- Protocol --------------------------------------------------------------------

  local function current_route(A)
    local state = inputs(A)
    return state and route(state) or nil
  end

  local function modal_token(A)
    A:screen_model()
    return A.modal
  end

  -- K2/K3 go to the owner's Adapter:key, which answers the runtime modal first,
  -- then an alignment draft, then a setup draft. A token names the question it
  -- answers: a pending modal needs its own token, and a token with no modal is stale.
  local function answer(n, token)
    local A = doctor()
    if not A then return ui_adapters.fail("no_owner") end
    local pending = modal_token(A)
    if pending ~= token then return ui_adapters.fail("stale_token") end
    return wrap(A:key(n, 1))
  end

  local impl = {
    describe = function(source_route, target)
      local A = doctor()
      if not A then return nil, "no_owner" end
      local build = describe[source_route]
      if not build then return nil, "unsupported_route" end
      return build(A, A:screen_model())
    end,
    generation = function()
      local A = doctor()
      if not A then return "none" end
      local machine = A.runtime.machine or {}
      return table.concat({tostring(machine.project_id), tostring(machine.generation),
        tostring(machine.analysis_revision), tostring(current_route(A))}, "|")
    end,
    target_valid = function(target)
      local A = doctor()
      if not A then return false end
      if type(target) == "table" and target.doctor ~= nil and target.doctor ~= A then return false end
      local p = page()
      return type(p.get_algorithm) ~= "function" or p.get_algorithm() == 5
    end,
    has_draft = function()
      local A = doctor()
      return A ~= nil and (A.setup_draft ~= nil or A.alignment_draft ~= nil)
    end,
    pending_confirmation = function()
      local A = doctor()
      return A ~= nil and modal_token(A) ~= nil
    end,
    apply = function(token) return answer(3, token) end,
    cancel = function(token) return answer(2, token) end,
  }

  local adapter = ui_adapters.new("doctor", impl)
  -- Router helpers (doctor_routes is the sole router for Doctor screens).
  adapter.route = route
  adapter.inputs = function() return inputs() end
  adapter.current_route = function() local A = doctor(); return A and current_route(A) or nil end
  -- The opaque runtime modal token after sync_modal, for the confirmation screens.
  adapter.modal_token = function() local A = doctor(); return A and modal_token(A) or nil end
  return adapter
end

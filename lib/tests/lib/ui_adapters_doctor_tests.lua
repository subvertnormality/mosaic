-- Characterisation of the Rhythm Doctor UI02 adapter (docs/ui-reimplementation
-- spec.json providers.doctor, doctor_routes, field_contracts.doctor). The
-- behaviour it pins is README.md "Rhythm Doctor"; the adapter itself is
-- presentation plumbing outside the manual. Every edit/invoke is compared with
-- the old ui.enc / ui.key / grid path on the real trigger page and the real
-- Rhythm Doctor controller over a recording runtime double.

local ui_adapters = include("mosaic/lib/ui_adapters")
local doctor_factory = include("mosaic/lib/ui_adapters/doctor")
local DoctorUI = include("mosaic/lib/rhythm_doctor/ui_adapter")

local spec = ui_adapters.spec
local ROUTES = spec.doctor_routes
local SAVED = {"fader", "button", "sequencer", "press", "draw", "grid_abstraction", "pattern", "tooltip", "params",
  "trigger_edit_page", "rhythm_doctor_nudge_window", "rhythm_doctor_page_window", "rhythm_doctor_jump_to_phrase_start",
  "screen"}

local function reply(code, extra)
  extra = extra or {}; extra.code, extra.ok = code, code == "OK"; return extra
end

local function ready_bank(names)
  local lanes, sensitivities = {}, {}
  for _, name in ipairs(names or {"BD", "SD", "CYM"}) do lanes[name] = {}; sensitivities[name] = 0.5 end
  local first = (names or {"BD"})[1]
  if first then lanes[first] = {[1] = true, [5] = true} end
  return {lane_names = names, lanes = lanes, sensitivities = sensitivities, window_start = 16, timeline_cells = 256,
    bpm = 120, tempo_mode = "auto", source = {beat_positions = {0, 1000, 2000, 3000}}, phrase_start_cell = 32,
    samples_per_cell = 50, origin_sample = 0, sample_rate = 48000, capture_start_sample = 0, capture_end_sample = 4000}
end

local function fake_runtime(calls)
  local runtime = {machine = {state = "EMPTY", project_id = "p", generation = 1, analysis_revision = 0}}
  local function log(...) calls[#calls + 1] = table.concat({...}, ":") end
  function runtime:enter() log("enter"); return reply("OK") end
  function runtime:start_capture(mode)
    log("start", mode); self.machine.state = mode == "auto" and "LISTENING" or "RECORDING"; return reply("OK")
  end
  function runtime:record_action()
    log("record_action")
    local operations = {READY = "clear", ALIGNMENT_REQUIRED = "clear", LISTENING = "cancel_capture",
      RECORDING = "cancel_capture", ANALYSING = "cancel_capture", REANALYSING = "cancel_correction"}
    local token = {operation = operations[self.machine.state], state = self.machine.state}
    self.machine.modal = token
    return token
  end
  function runtime:confirm_modal(token, accepted)
    log("confirm", token.operation, tostring(accepted))
    self.machine.modal = nil
    if accepted then self.machine.state, self.machine.bank = "EMPTY", nil end
    return reply(accepted and "OK" or "CANCELLED")
  end
  function runtime:finish(enough) log("finish", tostring(enough)); self.machine.state = "ANALYSING"; return reply("OK") end
  function runtime:capture_progress() return {enough_audio = self.enough == true, captured_seconds = 12, required_seconds = 24} end
  function runtime:transport_started() log("transport_started"); return reply("OK") end
  function runtime:transport_stopped_event() return reply("OK") end
  function runtime:set_window_start(start)
    log("window", start)
    local bank = self.machine.bank
    bank.window_start = math.max(0, math.min(bank.timeline_cells - 64, start))
    return reply("WINDOW_MOVED", {window_start = bank.window_start})
  end
  function runtime:set_sensitivity(lane, value)
    log("sensitivity", lane, string.format("%.2f", value))
    self.machine.bank.sensitivities[lane] = value
    return reply("SENSITIVITY_UPDATED")
  end
  function runtime:apply_alignment(payload)
    log("alignment", payload.bpm, tostring(payload.origin_sample))
    if self.refuse_alignment then return reply(self.refuse_alignment) end
    self.machine.state = "REANALYSING"
    return reply("OK")
  end
  function runtime:paint_preview(context) return {shifted_cells = {}, target = {}, window = context.window_start} end
  return runtime
end

-- The real trigger page, UI and Rhythm Doctor controller, with the page's outer
-- dependencies replaced as in trigger_edit_page_hardening_tests.lua.
local function with_env(options, body)
  options = options or {}
  local saved = {}
  for i, name in ipairs(SAVED) do saved[i] = rawget(_G, name) end
  local ok, err = pcall(function()
    fader = include("mosaic/lib/controls/fader")
    button = include("mosaic/lib/controls/button")
    sequencer = include("mosaic/lib/controls/sequencer")
    local env = {normal = {}, pre = {}, post = {}, long = {}, tips = {}, calls = {}, playing = false}
    press = {
      register = function(_, _, handler) env.normal[#env.normal + 1] = handler end,
      register_pre = function(_, _, handler) env.pre[#env.pre + 1] = handler end,
      register_post = function(_, _, handler) env.post[#env.post + 1] = handler end,
      register_long = function(_, _, handler) env.long[#env.long + 1] = handler end,
      register_dual = function() end
    }
    draw = {register_grid = function() end, register_ui = function() end}
    grid_abstraction = {led = function() end}
    pattern = {update_source_working_patterns = function() end}
    tooltip = {show = function(_, text) env.tips[#env.tips + 1] = text end}
    params = {
      string = function() return 64 end,
      get = function(_, id) return (options.params or {})[id] end,
      set = function() end
    }
    program.init()
    env.page = dofile("../../lib/pages/trigger_edit_page/trigger_edit_page.lua")
    env.page.register_press()
    env.runtime = fake_runtime(env.calls)
    env.doctor = DoctorUI.new({runtime = env.runtime, transport_stopped = function() return not env.playing end,
      mode = options.mode})
    env.page.set_rhythm_doctor(env.doctor)
    trigger_edit_page = env.page
    env.ui = dofile("../../lib/pages/trigger_edit_page/trigger_edit_page_ui.lua")
    env.press = function(x, y)
      local claimed = false
      for _, handler in ipairs(env.pre) do claimed = handler(x, y) or claimed end
      if not claimed then for _, handler in ipairs(env.normal) do handler(x, y) end end
      for _, handler in ipairs(env.post) do handler(x, y) end
    end
    env.hold = function(x, y) for _, handler in ipairs(env.long) do handler(x, y) end end
    env.press(16, 2) -- algorithm 5: Rhythm Doctor
    env.calls[#env.calls] = nil -- the enter() that selection makes
    env.adapter = doctor_factory(ui_adapters, {trigger_edit_page = env.page})
    body(env)
  end)
  for i = #SAVED, 1, -1 do rawset(_G, SAVED[i], saved[i]) end
  if not ok then error(err, 0) end
end

-- Owner states named by doctor_routes rows.
local function put(env, state)
  local runtime, doctor = env.runtime, env.doctor
  if state == "ready" or state == "ready_preview" or state == "alignment" or state == "alignment_refused" or
      state == "modal_clear" or state == "ready_playing" then
    runtime.machine.state, runtime.machine.bank = "READY", ready_bank({"BD", "SD", "CYM"})
  end
  if state == "setup" then doctor:enc(2, 1) end
  if state == "capture" or state == "capture_enough" then runtime.machine.state = "LISTENING" end
  if state == "capture_enough" then runtime.enough = true end
  if state == "analysis" then runtime.machine.state = "ANALYSING" end
  if state == "failed" then runtime.machine.state, runtime.machine.last_message = "FAILED", "ANALYSIS_BACKEND_UNAVAILABLE" end
  if state == "ready_preview" then env.press(16, 8) end
  if state == "alignment" or state == "alignment_refused" then
    for _ = 1, 4 do doctor:enc(2, 1) end
    doctor:enc(3, 1)
  end
  if state == "alignment_refused" then runtime.refuse_alignment = "NOT_READY"; doctor:key(3, 1) end
  if state == "modal_clear" or state == "modal_cancel_capture" or state == "modal_cancel_correction" then
    if state == "modal_cancel_capture" then runtime.machine.state = "LISTENING" end
    if state == "modal_cancel_correction" then runtime.machine.state = "REANALYSING" end
    env.press(1, 2)
  end
  if state == "playing_gate" or state == "ready_playing" then env.playing = true end
end

local function target(route, extra)
  local t = {source_route = route, screen = route}
  for k, v in pairs(extra or {}) do t[k] = v end
  return t
end

local function ids_of(outcome)
  local ids = {}
  for _, d in ipairs(outcome.descriptors) do ids[#ids + 1] = d.id end
  return ids
end

local function by_id(outcome)
  local map = {}
  for _, d in ipairs(outcome.descriptors) do map[d.id] = d end
  return map
end

local function spec_ids(screen)
  local ids = {}
  for _, field in ipairs(spec.screens[screen].fields) do ids[#ids + 1] = type(field) == "table" and field.id or field end
  return ids
end

local function snapshot(env)
  local d, m = env.doctor, env.runtime.machine
  local bank = m.bank or {}
  local draft = d.alignment_draft or {}
  local setup = d.setup_draft or {}
  local sens = {}
  for k, v in pairs(bank.sensitivities or {}) do sens[k] = string.format("%.2f", v) end
  return {state = m.state, window = bank.window_start, sensitivities = sens, calls = table.concat(env.calls, ","),
    mode = d.capture_mode, bpm = d.manual_bpm, input = d.input_source, setup_field = d.setup_field,
    setup = {setup.capture_mode, setup.manual_bpm, setup.input_source}, has_setup = d.setup_draft ~= nil,
    ready_field = d.ready_field, alignment_field = d.alignment_field, has_alignment = d.alignment_draft ~= nil,
    alignment = {draft.bpm, draft.start_beat, draft.fine_start_ms}, alignment_error = d.alignment_error,
    policy = d.paint_policy, window_revision = d.window_revision, modal = d.modal and d.modal.operation or "none",
    record_held = d.record_held, lane = d.lane, tips = table.concat(env.tips, "|")}
end

-- Router -----------------------------------------------------------------------

local DOMAIN = ROUTES.inputs

local function expand(when)
  local combos = {{}}
  for _, key in ipairs({"doctor_state", "modal_operation", "draft", "preview", "playing"}) do
    local values = type(when[key]) == "table" and when[key] or {when[key]}
    local next_combos = {}
    for _, combo in ipairs(combos) do
      for _, value in ipairs(values) do
        local c = {}
        for k, v in pairs(combo) do c[k] = v end
        c[key] = value
        next_combos[#next_combos + 1] = c
      end
    end
    combos = next_combos
  end
  return combos
end

function test_ui_adapters_doctor_route_resolves_every_doctor_routes_row()
  local adapter = doctor_factory(ui_adapters, {trigger_edit_page = {}})
  for _, row in ipairs(ROUTES.rows) do
    for _, state in ipairs(expand(row.when)) do
      local screen, row_id = adapter.route(state)
      luaunit.assert_equals(screen, row.screen, row.id)
      luaunit.assert_equals(row_id, row.id)
    end
  end
end

function test_ui_adapters_doctor_route_rows_partition_the_whole_input_domain()
  local adapter = doctor_factory(ui_adapters, {trigger_edit_page = {}})
  local all = expand({doctor_state = DOMAIN.doctor_state.values, modal_operation = DOMAIN.modal_operation.values,
    draft = DOMAIN.draft.values, preview = DOMAIN.preview.values, playing = DOMAIN.playing.values})
  luaunit.assert_equals(#all, 8 * 4 * 4 * 2 * 2)
  for _, state in ipairs(all) do
    local matches = 0
    for _, row in ipairs(ROUTES.rows) do
      local ok = true
      for _, s in ipairs(expand(row.when)) do
        ok = true
        for k, v in pairs(s) do if state[k] ~= v then ok = false end end
        if ok then break end
      end
      if ok then matches = matches + 1 end
    end
    luaunit.assert_equals(matches, 1)
    luaunit.assert_not_nil(adapter.route(state))
  end
end

function test_ui_adapters_doctor_route_applies_flow_overrides_only_on_listed_rows()
  local adapter = doctor_factory(ui_adapters, {trigger_edit_page = {}})
  local ready = {doctor_state = "READY", modal_operation = "none", draft = "none", preview = "none", playing = false}
  ready.outcome = "paint_committed"
  luaunit.assert_equals(adapter.route(ready), "R09")
  ready.outcome = "lane_selected"
  luaunit.assert_equals(adapter.route(ready), "R13")
  ready.outcome = "window_moved"
  luaunit.assert_equals(adapter.route(ready), "R15")
  local gate = {doctor_state = "EMPTY", modal_operation = "none", draft = "none", preview = "none", playing = true,
    outcome = "lane_selected"}
  luaunit.assert_equals(adapter.route(gate), "R11")
  local setup = {doctor_state = "EMPTY", modal_operation = "none", draft = "setup", preview = "none", playing = false,
    outcome = "lane_selected"}
  luaunit.assert_equals(adapter.route(setup), "R01")
  luaunit.assert_error(function() adapter.route({doctor_state = "READY"}) end)
end

function test_ui_adapters_doctor_route_reads_every_row_from_runtime_state()
  local expected = {
    empty = "R01", setup = "R01", capture = "R02", modal_cancel_capture = "R03", analysis = "R04", ready = "R05",
    alignment = "R06", alignment_refused = "R07", ready_preview = "R08", modal_clear = "R10", playing_gate = "R11",
    failed = "R12", modal_cancel_correction = "R16", ready_playing = "R05"
  }
  for state, screen in pairs(expected) do
    with_env({}, function(env)
      put(env, state)
      luaunit.assert_equals(env.adapter.current_route(), screen, state)
      local _, row = env.adapter.route(env.adapter.inputs())
      local known = false
      for _, r in ipairs(ROUTES.rows) do if r.id == row then known = true end end
      luaunit.assert_true(known, state)
    end)
  end
end

function test_ui_adapters_doctor_route_inputs_match_owner_state()
  with_env({}, function(env)
    put(env, "alignment_refused")
    luaunit.assert_equals(env.adapter.inputs(),
      {doctor_state = "READY", modal_operation = "none", draft = "alignment_refused", preview = "none", playing = false})
  end)
  with_env({}, function(env)
    put(env, "ready_preview")
    env.playing = true
    luaunit.assert_equals(env.adapter.inputs(),
      {doctor_state = "READY", modal_operation = "none", draft = "none", preview = "armed", playing = true})
    luaunit.assert_equals(env.adapter.current_route(), "R08")
  end)
  with_env({}, function(env)
    put(env, "modal_clear")
    -- A runtime that dropped the question: sync_modal drops the local token.
    env.runtime.machine.modal = nil
    luaunit.assert_equals(env.adapter.inputs().modal_operation, "none")
    luaunit.assert_equals(env.adapter.current_route(), "R05")
  end)
end

-- Descriptor parity ---------------------------------------------------------------

local ROUTE_OF_STATE = {R01 = "empty", R02 = "capture", R04 = "analysis", R05 = "ready", R06 = "alignment",
  R07 = "alignment_refused", R08 = "ready_preview", R09 = "ready", R11 = "playing_gate", R12 = "failed",
  R13 = "ready", R14 = "empty", R15 = "ready"}

function test_ui_adapters_doctor_every_screen_describes_its_spec_field_ids()
  for route, state in pairs(ROUTE_OF_STATE) do
    with_env({}, function(env)
      put(env, state)
      local outcome = env.adapter:describe(route, route, target(route))
      luaunit.assert_true(outcome.ok, route .. " " .. tostring(outcome.code))
      luaunit.assert_equals(ids_of(outcome), spec_ids(route), route)
    end)
  end
end

function test_ui_adapters_doctor_setup_values_match_the_owner_model()
  with_env({mode = "manual"}, function(env)
    local d = by_id(env.adapter:describe("R01", "R01", target("R01")))
    local model = env.doctor:screen_model()
    luaunit.assert_equals(d.tempo.value, "MANUAL")
    luaunit.assert_equals(d.manual_bpm.value, tostring(model.manual_bpm))
    luaunit.assert_equals(d.input.value, "STEREO")
    luaunit.assert_true(d.manual_bpm.domain.local_only)
    luaunit.assert_true(d.input.domain.local_only)
    luaunit.assert_equals(d.record.value, "READY") -- enter() on selecting algorithm 5
    for _, id in ipairs({"tempo", "manual_bpm", "input"}) do luaunit.assert_false(d[id].selected) end
    env.doctor:enc(2, 1)
    d = by_id(env.adapter:describe("R01", "R01", target("R01")))
    luaunit.assert_true(d.manual_bpm.selected)
    luaunit.assert_false(d.tempo.selected)
  end)
end

function test_ui_adapters_doctor_ready_values_match_the_owner_model()
  with_env({}, function(env)
    put(env, "ready")
    local model = env.doctor:screen_model()
    local d = by_id(env.adapter:describe("R05", "R05", target("R05")))
    luaunit.assert_equals(d.window_bar.value, "2")
    luaunit.assert_equals(d.window_step.value, "17")
    luaunit.assert_equals(d.window_bar.domain.label, model.window_start_label)
    luaunit.assert_equals(d.sensitivity.value, tostring(model.sensitivity))
    luaunit.assert_equals(d.paint_policy.value, "TOGGLE")
    luaunit.assert_true(d.window_bar.selected)
    luaunit.assert_equals(d.alignment.kind, "action")
    local r15 = by_id(env.adapter:describe("R15", "R15", target("R15")))
    luaunit.assert_equals(r15.window.value, model.window_start_label)
    local r09 = by_id(env.adapter:describe("R09", "R09", target("R09")))
    luaunit.assert_equals(r09.window.value, model.window_start_label .. "-" .. model.window_end_label)
    luaunit.assert_equals(r09.bank.value, "HITS 2 / READY")
    luaunit.assert_equals(r09.painted.value, "1")
  end)
end

function test_ui_adapters_doctor_status_screens_keep_none_distinct()
  with_env({}, function(env)
    put(env, "playing_gate")
    local d = by_id(env.adapter:describe("R11", "R11", target("R11")))
    luaunit.assert_equals(d.transport.value, "RUNNING")
    luaunit.assert_equals(d.record_setup.value, "STOP SEQUENCER")
    luaunit.assert_equals(d.lane.value, "BD")
    luaunit.assert_equals(d.bank.value, "NONE")
  end)
  with_env({}, function(env)
    put(env, "failed")
    local d = by_id(env.adapter:describe("R12", "R12", target("R12")))
    luaunit.assert_equals(d.reason.value, "ANALYSIS BACKEND UNAVAILABLE")
    luaunit.assert_equals(d.bank.value, "NONE")
  end)
  with_env({}, function(env)
    put(env, "capture")
    local d = by_id(env.adapter:describe("R02", "R02", target("R02")))
    luaunit.assert_equals(d.audio.value, "MORE AUDIO NEEDED")
    luaunit.assert_equals(d.elapsed.value, "12.0s")
    luaunit.assert_equals(d.capture_still_active.value, "LISTENING")
    env.runtime.enough = true
    d = by_id(env.adapter:describe("R02", "R02", target("R02")))
    luaunit.assert_equals(d.audio.value, "ENOUGH")
    luaunit.assert_equals(d.finish.value, "REC OR K3")
  end)
end

function test_ui_adapters_doctor_alignment_values_match_the_draft()
  with_env({}, function(env)
    put(env, "alignment")
    local model = env.doctor:screen_model()
    local d = by_id(env.adapter:describe("R06", "R06", target("R06")))
    luaunit.assert_equals(d.exact_bpm.value, tostring(model.alignment.bpm))
    luaunit.assert_equals(d.start_beat.value, tostring(model.alignment.start_beat))
    luaunit.assert_equals(d.start_beat.domain.max, 4)
    luaunit.assert_equals(d.fine_start.value, "0ms")
    luaunit.assert_true(d.half_tempo.selected)
  end)
  with_env({}, function(env)
    put(env, "alignment_refused")
    local d = by_id(env.adapter:describe("R07", "R07", target("R07")))
    luaunit.assert_equals(d.refusal.value, "NOT READY")
  end)
  with_env({}, function(env)
    put(env, "ready")
    local outcome = env.adapter:describe("R06", "R06", target("R06"))
    luaunit.assert_false(outcome.ok)
    luaunit.assert_equals(outcome.code, "no_alignment_draft")
  end)
end

function test_ui_adapters_doctor_lanes_follow_the_owner_lane_set()
  -- Before any bank: the on-device default set.
  with_env({}, function(env)
    local outcome = env.adapter:describe("R13", "R13", target("R13"))
    luaunit.assert_equals(ids_of(outcome), {"lane:bd", "lane:sd", "lane:cym", "selected"})
    local d = by_id(outcome)
    luaunit.assert_equals(d["lane:bd"].value, "GRID 3,2")
    luaunit.assert_equals(d["lane:bd"].repeat_key, "lane:bd")
    luaunit.assert_true(d["lane:bd"].selected)
    luaunit.assert_equals(d.selected.value, "BD")
  end)
  -- An empty bank lane list falls back to the same default set.
  with_env({}, function(env)
    env.runtime.machine.state, env.runtime.machine.bank = "READY", ready_bank({})
    env.runtime.machine.bank.lane_names = {}
    luaunit.assert_equals(ids_of(env.adapter:describe("R13", "R13", target("R13"))),
      {"lane:bd", "lane:sd", "lane:cym", "selected"})
  end)
  -- Maximum cardinality: twelve names, ten lanes, two rows of five.
  with_env({}, function(env)
    local names = {"KICK", "SNARE", "HIHAT", "RIDE", "CRASH", "TOMS", "BASS", "PERC", "VOX", "OTHER", "X11", "X12"}
    env.runtime.machine.state, env.runtime.machine.bank = "READY", ready_bank(names)
    env.doctor:select_lane("VOX")
    local outcome = env.adapter:describe("R13", "R13", target("R13"))
    local ids = ids_of(outcome)
    luaunit.assert_equals(#ids, 11)
    luaunit.assert_equals(ids[10], "lane:other")
    local d = by_id(outcome)
    luaunit.assert_equals(d["lane:vox"].value, "GRID 6,3")
    luaunit.assert_true(d["lane:vox"].selected)
    luaunit.assert_false(d["lane:kick"].selected)
    for _, desc in ipairs(outcome.descriptors) do
      if desc.id ~= "selected" then luaunit.assert_str_matches(desc.id, "^lane:[a-z0-9_]+$") end
      local cell = desc.domain
      if cell.x then luaunit.assert_equals(env.doctor:lane_at(cell.x, cell.y), cell.lane) end
    end
  end)
end

function test_ui_adapters_doctor_setup_limits_read_the_native_server_parameters()
  with_env({params = {rhythm_doctor_use_server = 2, rhythm_doctor_server = " 10.0.0.2:8080 "}}, function(env)
    local d = by_id(env.adapter:describe("R14", "R14", target("R14")))
    luaunit.assert_equals(d.backend.value, "SERVER")
    luaunit.assert_equals(d.server.value, "10.0.0.2:8080")
    luaunit.assert_equals(d.stereo_l_r.value, "STEREO")
  end)
  with_env({params = {rhythm_doctor_use_server = 1, rhythm_doctor_server = "10.0.0.2"}}, function(env)
    local d = by_id(env.adapter:describe("R14", "R14", target("R14")))
    luaunit.assert_equals(d.backend.value, "LOCAL")
    luaunit.assert_equals(d.server.value, "NONE")
  end)
end

-- Edit/invoke parity with the old path ----------------------------------------------

-- Old path: E2 to the field, then E3, through trigger_edit_page_ui.enc.
local function old_edit(env, ids, cursor, id, delta)
  local index
  for i, v in ipairs(ids) do if v == id then index = i end end
  if env.doctor[cursor] ~= index then env.ui.enc(2, index - env.doctor[cursor]) end
  env.ui.enc(3, delta)
end

local function compare_edit(state, route, ids_name, cursor, id, delta)
  local old, new
  with_env({}, function(env)
    put(env, state)
    old_edit(env, DoctorUI[ids_name], cursor, id, delta)
    old = snapshot(env)
  end)
  with_env({}, function(env)
    put(env, state)
    local outcome = env.adapter:edit(id, delta, target(route))
    luaunit.assert_true(outcome.ok, id .. " " .. tostring(outcome.code))
    new = snapshot(env)
  end)
  luaunit.assert_equals(new, old, route .. " " .. id)
end

function test_ui_adapters_doctor_setup_edits_match_the_encoder_path()
  for _, id in ipairs({"tempo", "manual_bpm", "input"}) do
    for _, delta in ipairs({1, -1, 3}) do compare_edit("empty", "R01", "SETUP_FIELD_IDS", "setup_field", id, delta) end
  end
end

function test_ui_adapters_doctor_ready_edits_match_the_encoder_path()
  for _, id in ipairs({"window_bar", "window_step", "sensitivity", "paint_policy"}) do
    for _, delta in ipairs({1, -2}) do compare_edit("ready", "R05", "READY_FIELD_IDS", "ready_field", id, delta) end
  end
  -- READY bank fields stay editable while playing (transport_gate.ready_bank_while_playing).
  compare_edit("ready_playing", "R05", "READY_FIELD_IDS", "ready_field", "sensitivity", 1)
end

function test_ui_adapters_doctor_alignment_edits_match_the_encoder_path()
  for _, id in ipairs({"exact_bpm", "start_beat", "fine_start"}) do
    for _, delta in ipairs({1, -1}) do compare_edit("alignment", "R06", "ALIGNMENT_FIELD_IDS", "alignment_field", id, delta) end
  end
  compare_edit("alignment_refused", "R07", "ALIGNMENT_FIELD_IDS", "alignment_field", "start_beat", 1)
end

local function compare_invoke(state, route, id, old_path, modifiers)
  local old, new
  with_env({}, function(env)
    put(env, state)
    old_path(env)
    old = snapshot(env)
  end)
  with_env({}, function(env)
    put(env, state)
    env.adapter:invoke(id, target(route), nil, modifiers)
    new = snapshot(env)
  end)
  luaunit.assert_equals(new, old, route .. " " .. id)
end

function test_ui_adapters_doctor_invokes_match_the_key_and_grid_paths()
  compare_invoke("ready", "R05", "alignment", function(env) old_edit(env, DoctorUI.READY_FIELD_IDS, "ready_field", "alignment", 1) end)
  compare_invoke("ready_playing", "R05", "alignment", function(env) old_edit(env, DoctorUI.READY_FIELD_IDS, "ready_field", "alignment", 1) end)
  compare_invoke("alignment", "R06", "half_tempo", function(env) env.ui.key(3, 1) end)
  compare_invoke("alignment", "R06", "double_tempo", function(env) env.ui.enc(2, 1); env.ui.key(3, 1) end)
  compare_invoke("alignment_refused", "R07", "k2_discards", function(env) env.ui.key(2, 1) end)
  compare_invoke("empty", "R01", "record", function(env) env.press(1, 2) end)
  compare_invoke("failed", "R12", "record", function(env) env.press(1, 2) end)
  compare_invoke("analysis", "R04", "record", function(env) env.press(1, 2) end)
  compare_invoke("ready", "R15", "back", function(env) env.press(10, 8) end)
  compare_invoke("ready", "R15", "forward", function(env) env.press(12, 8) end)
  compare_invoke("ready", "R15", "phrase_start", function(env) env.press(11, 8) end)
  compare_invoke("ready", "R15", "back", function(env) env.hold(10, 8) end, {hold = true})
  compare_invoke("ready", "R15", "forward", function(env) env.hold(12, 8) end, {hold = true})
  compare_invoke("capture", "R02", "finish", function(env) env.ui.key(3, 1) end)
  compare_invoke("capture_enough", "R02", "finish", function(env) env.ui.key(3, 1) end)
end

function test_ui_adapters_doctor_finish_after_enough_audio_reaches_the_owner()
  with_env({}, function(env)
    put(env, "capture")
    luaunit.assert_equals(env.adapter:invoke("finish", target("R02")).code, "MORE_AUDIO_NEEDED")
    env.runtime.enough = true
    local outcome = env.adapter:invoke("finish", target("R02"))
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(env.runtime.machine.state, "ANALYSING")
  end)
end

-- Transport gate stays in the owner ------------------------------------------------

function test_ui_adapters_doctor_owner_gates_setup_record_and_alignment_while_playing()
  with_env({}, function(env)
    put(env, "playing_gate")
    local before = snapshot(env)
    luaunit.assert_equals(env.adapter:edit("tempo", 1, target("R01")).code, "STOP_SEQUENCER")
    luaunit.assert_equals(env.adapter:invoke("record", target("R01")).code, "STOP_SEQUENCER")
    luaunit.assert_equals(snapshot(env), before)
  end)
  with_env({}, function(env)
    put(env, "ready_playing")
    local outcome = env.adapter:invoke("alignment", target("R05"))
    luaunit.assert_equals(outcome.code, "STOP_SEQUENCER")
    luaunit.assert_nil(env.doctor.alignment_draft)
    luaunit.assert_true(env.adapter:edit("paint_policy", 1, target("R05")).ok)
  end)
end

-- Confirmation stays in the owner ---------------------------------------------------

function test_ui_adapters_doctor_apply_and_cancel_forward_the_opaque_modal_token()
  with_env({}, function(env)
    put(env, "modal_clear")
    local token = env.adapter.modal_token()
    luaunit.assert_is(token, env.runtime.machine.modal)
    local before = snapshot(env)
    luaunit.assert_equals(env.adapter:apply(nil, target("R10")).code, "stale_token")
    luaunit.assert_equals(env.adapter:apply({operation = "clear"}, target("R10")).code, "stale_token")
    luaunit.assert_equals(snapshot(env), before)
    local outcome = env.adapter:apply(token, target("R10"))
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(env.calls[#env.calls], "confirm:clear:true")
  end)
  with_env({}, function(env)
    put(env, "modal_cancel_capture")
    local outcome = env.adapter:cancel(env.adapter.modal_token())
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(env.calls[#env.calls], "confirm:cancel_capture:false")
    luaunit.assert_equals(env.runtime.machine.state, "LISTENING")
  end)
  with_env({}, function(env)
    put(env, "setup")
    luaunit.assert_true(env.adapter.impl.has_draft())
    env.adapter:edit("manual_bpm", 5, target("R01"))
    local outcome = env.adapter:apply(nil, target("R01"))
    luaunit.assert_equals(outcome.status, "SETUP_CONFIRMED")
    luaunit.assert_equals(env.doctor.manual_bpm, 125)
  end)
end

-- Route ownership and staleness -----------------------------------------------------

function test_ui_adapters_doctor_describe_of_a_foreign_route_is_an_error()
  with_env({}, function(env)
    for _, route in ipairs({"R03", "R10", "R16", "C01", "M01"}) do
      local outcome = env.adapter:describe(route, route, target(route))
      luaunit.assert_false(outcome.ok)
      luaunit.assert_equals(outcome.code, "foreign_route")
      luaunit.assert_nil(outcome.descriptors)
    end
  end)
end

function test_ui_adapters_doctor_stale_generation_is_refused_without_mutation()
  with_env({}, function(env)
    put(env, "ready")
    local described = env.adapter:describe("R05", "R05", target("R05"))
    local generation = described.owner_generation
    luaunit.assert_true(env.adapter:edit("paint_policy", 1, target("R05"), generation).ok)
    -- The bank is cleared under the captured screen: its generation no longer holds.
    env.press(1, 2)
    env.doctor:key(3, 1)
    local before = snapshot(env)
    local outcome = env.adapter:edit("sensitivity", 1, target("R05"), generation)
    luaunit.assert_equals(outcome.code, "stale_generation")
    luaunit.assert_equals(snapshot(env), before)
  end)
end

function test_ui_adapters_doctor_stale_target_is_refused_without_mutation()
  with_env({}, function(env)
    put(env, "ready")
    local other = DoctorUI.new({runtime = fake_runtime({}), transport_stopped = function() return true end})
    local before = snapshot(env)
    luaunit.assert_equals(env.adapter:edit("paint_policy", 1, target("R05", {doctor = other})).code, "stale_target")
    env.press(15, 2) -- leave algorithm 5
    luaunit.assert_equals(env.adapter:edit("paint_policy", 1, target("R05")).code, "stale_target")
    luaunit.assert_equals(env.doctor.paint_policy, "toggle")
    luaunit.assert_equals(before.policy, "toggle")
  end)
end

function test_ui_adapters_doctor_zero_delta_and_unknown_fields_do_not_reach_the_owner()
  with_env({}, function(env)
    local before = snapshot(env)
    luaunit.assert_equals(env.adapter:edit("tempo", 0, target("R01")).code, "zero_delta")
    luaunit.assert_equals(env.adapter:edit("window_bar", 1, target("R01")).code, "unknown_field")
    luaunit.assert_equals(snapshot(env), before)
  end)
end

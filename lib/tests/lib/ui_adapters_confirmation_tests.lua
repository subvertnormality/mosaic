-- Characterisation of the UI02 confirmation provider (docs/ui-reimplementation
-- spec.json#/confirmation_contracts). Outside the manual's wording except
-- where cited: README.md "Scales" (hold K1 while choosing a scale to save it
-- across the song, K3 confirms) and the Rhythm Doctor K2/K3 modal questions.
-- The adapter is a dispatcher: these tests drive the real save_confirm, the
-- real scale page key handlers and the real Rhythm Doctor ui_adapter, and a
-- fake harmony owner.

local ui_adapters = include("mosaic/lib/ui_adapters")
local confirmation_factory = include("mosaic/lib/ui_adapters/confirmation")
local isolation = include("mosaic/lib/tests/helpers/ui_adapters_isolation")
local DoctorAdapter = include("mosaic/lib/rhythm_doctor/ui_adapter")

-- Scale ------------------------------------------------------------------------

-- A fresh save_confirm and scale page with recording collaborators.
local function scale_env(body)
  local env = {pressed = {}, calls = {}, tips = {}}
  isolation.isolated({
    tooltip = {show = function(_, message) env.tips[#env.tips + 1] = message end},
    m_grid = {get_pressed_keys = function() return env.pressed end},
    sequencer = {new = function() return {draw = function() end} end},
  }, function()
    save_confirm = include("mosaic/lib/ui_components/save_confirm")
    env.save_confirm = save_confirm
    local base_program = program
    program = setmetatable({clear_trig_locks_for_step_for_channel = function(_, s)
      env.calls[#env.calls + 1] = "clear_step_locks " .. s end}, {__index = base_program})
    env.page = include("mosaic/lib/pages/scale_edit_page/scale_edit_page_ui")
    -- The page arms the question exactly as scale_edit_page_ui.update_scale does.
    env.arm = function()
      save_confirm.set_cancel(function() env.calls[#env.calls + 1] = "refresh_quantiser" end)
      save_confirm.set_save(function() env.calls[#env.calls + 1] = "set_all_song_pattern_scales" end)
    end
    env.adapter = confirmation_factory(ui_adapters, {scale_page = function() return env.page.adapter_owners() end})
    body(env)
  end)
end

local function envelope(env)
  return env.adapter.capture("S05", {screen = "S05", source_route = "S05", armed = true, scope = "all_song"})
end

function test_ui_adapters_confirmation_scale_k3_matches_the_old_scale_page_k3()
  local old, new
  scale_env(function(env)
    env.arm()
    env.page.handle_key_three_pressed()
    old = {calls = env.calls, tips = env.tips}
  end)
  scale_env(function(env)
    env.arm()
    local outcome = env.adapter:apply(envelope(env))
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(outcome.code, "confirmed")
    luaunit.assert_equals(outcome.screen, "S05")
    new = {calls = env.calls, tips = env.tips}
    -- exactly once: a second K3 finds save_confirm empty and runs nothing
    env.adapter:apply(envelope(env))
    luaunit.assert_equals(env.calls, {"set_all_song_pattern_scales"})
  end)
  luaunit.assert_equals(new, old)
  luaunit.assert_equals(old.calls, {"set_all_song_pattern_scales"})
end

function test_ui_adapters_confirmation_scale_k2_matches_the_old_scale_page_k2()
  local old, new
  scale_env(function(env)
    env.arm()
    env.page.handle_key_two_pressed()
    old = {calls = env.calls, tips = env.tips}
  end)
  scale_env(function(env)
    env.arm()
    local outcome = env.adapter:cancel(envelope(env))
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(outcome.code, "cancelled")
    new = {calls = env.calls, tips = env.tips}
  end)
  luaunit.assert_equals(new, old)
  luaunit.assert_equals(old.calls, {"refresh_quantiser"})
end

function test_ui_adapters_confirmation_scale_with_held_keys_answers_nothing()
  scale_env(function(env)
    env.arm()
    env.pressed = {{3, 4}}
    local k3 = env.adapter:apply(envelope(env))
    local k2 = env.adapter:cancel(envelope(env))
    luaunit.assert_false(k3.ok)
    luaunit.assert_equals(k3.code, "held")
    luaunit.assert_false(k2.ok)
    luaunit.assert_equals(k2.code, "held")
    -- neither the save nor the held-K2 step-lock clearing ran
    luaunit.assert_equals(env.calls, {})
    env.pressed = {}
    env.adapter:apply(envelope(env))
    luaunit.assert_equals(env.calls, {"set_all_song_pattern_scales"})
  end)
end

function test_ui_adapters_confirmation_scale_describes_s05_only_while_armed()
  scale_env(function(env)
    local armed = {screen = "S05", source_route = "S05", armed = true, scope = "all_song", scale_slot = 3}
    local outcome = env.adapter:describe("S05", "S05", armed)
    luaunit.assert_true(outcome.ok)
    local ids, values = {}, {}
    for _, d in ipairs(outcome.descriptors) do ids[#ids + 1] = d.id; values[d.id] = d.value end
    luaunit.assert_equals(ids, {"change", "target", "scope", "state"})
    luaunit.assert_equals(values.change, "Major / I")
    luaunit.assert_equals(values.target, "Scale slot03")
    luaunit.assert_equals(values.scope, "ALL SONG")
    luaunit.assert_equals(values.state, "NOT APPLIED")
    local idle = env.adapter:describe("S05", "S05", {screen = "S05", source_route = "S05"})
    luaunit.assert_false(idle.ok)
    luaunit.assert_equals(idle.code, "no_pending_confirmation")
    env.arm()
    local unarmed = env.adapter:apply({screen = "S05", target = {screen = "S05"}})
    luaunit.assert_equals(unarmed.code, "no_pending_confirmation")
    luaunit.assert_equals(env.calls, {})
  end)
end

-- Rhythm Doctor ------------------------------------------------------------------

-- The real Doctor ui_adapter over a recording runtime, raised to its
-- cancel_capture question by grid Record while RECORDING.
local function doctor(state)
  local log = {}
  local runtime = {machine = {state = state or "RECORDING"}}
  function runtime:start_capture() return {ok = true, code = "OK"} end
  function runtime:finish() return {ok = true, code = "OK"} end
  function runtime:record_action()
    local operation = ({RECORDING = "cancel_capture", LISTENING = "cancel_capture", ANALYSING = "cancel_capture",
      READY = "clear", REANALYSING = "cancel_correction"})[self.machine.state]
    local token = {operation = operation, state = self.machine.state}
    self.machine.modal = token
    return token
  end
  function runtime:confirm_modal(token, accepted)
    log[#log + 1] = {token = token, accepted = accepted}
    self.machine.modal = nil
    if accepted then self.machine.state = "EMPTY"; return {ok = true, code = "OK"} end
    return {ok = false, code = "CANCELLED"}
  end
  local instance = DoctorAdapter.new({runtime = runtime, transport_stopped = function() return true end})
  instance:record_pressed()
  instance:record_released()
  -- trigger_edit_page's two Doctor entry points, as ui.key reaches them
  local page = {
    handle_rhythm_doctor_key = function(n, z) return instance:key(n, z) end,
    get_rhythm_doctor_model = function() return instance:screen_model() end
  }
  return instance, runtime, log, page
end

function test_ui_adapters_confirmation_doctor_k3_passes_the_unchanged_token_like_the_old_key()
  local instance, runtime, old_log = doctor()
  local old_token = runtime.machine.modal
  instance:key(3, 1)
  local _, runtime2, log, page = doctor()
  local token = runtime2.machine.modal
  local adapter = confirmation_factory(ui_adapters, {doctor_page = function() return page end})
  local target = {screen = "R03", source_route = "R03"}
  local outcome = adapter:apply(adapter.capture("R03", target), target)
  luaunit.assert_true(outcome.ok)
  luaunit.assert_equals(outcome.code, "confirmed")
  luaunit.assert_equals(outcome.owner_code, "OK")
  luaunit.assert_equals(#log, 1)
  luaunit.assert_true(log[1].token == token)
  luaunit.assert_equals(log[1].accepted, old_log[1].accepted)
  luaunit.assert_true(old_log[1].token == old_token)
  luaunit.assert_equals(runtime2.machine.state, runtime.machine.state)
  -- the question is gone: a repeated K3 invokes nothing
  local again = adapter:apply({screen = "R03"}, target)
  luaunit.assert_equals(again.code, "no_pending_confirmation")
  luaunit.assert_equals(#log, 1)
end

function test_ui_adapters_confirmation_doctor_k2_declines_through_the_owner()
  local _, runtime, log, page = doctor()
  local adapter = confirmation_factory(ui_adapters, {doctor_page = function() return page end})
  local outcome = adapter:cancel(adapter.capture("R03", {screen = "R03"}))
  luaunit.assert_true(outcome.ok)
  luaunit.assert_equals(outcome.code, "cancelled")
  luaunit.assert_equals(outcome.owner_code, "CANCELLED")
  luaunit.assert_equals(#log, 1)
  luaunit.assert_false(log[1].accepted)
  luaunit.assert_equals(runtime.machine.state, "RECORDING")
end

function test_ui_adapters_confirmation_doctor_describes_only_the_raised_question()
  local _, _, _, page = doctor("READY")
  local adapter = confirmation_factory(ui_adapters, {doctor_page = function() return page end})
  local r10 = adapter:describe("R10", "R10", {screen = "R10", source_route = "R10"})
  luaunit.assert_true(r10.ok)
  local ids = {}
  for _, d in ipairs(r10.descriptors) do ids[#ids + 1] = d.id end
  luaunit.assert_equals(ids, ui_adapters.spec.screens.R10.fields)
  luaunit.assert_equals(r10.descriptors[1].domain.title, "CLEAR CAPTURE BANK?")
  local r03 = adapter:describe("R03", "R03", {screen = "R03", source_route = "R03"})
  luaunit.assert_false(r03.ok)
  luaunit.assert_equals(r03.code, "no_pending_confirmation")
  local _, _, _, correcting = doctor("REANALYSING")
  local r16 = confirmation_factory(ui_adapters, {doctor_page = function() return correcting end})
    :describe("R16", "R16", {screen = "R16", source_route = "R16"})
  luaunit.assert_true(r16.ok)
  luaunit.assert_equals(#r16.descriptors, 4)
end

function test_ui_adapters_confirmation_doctor_refuses_a_replaced_question_without_answering()
  local _, runtime, log, page = doctor()
  local adapter = confirmation_factory(ui_adapters, {doctor_page = function() return page end})
  local captured = adapter.capture("R03", {screen = "R03"})
  -- the runtime replaced its question (a new state): the captured identity is stale
  runtime.machine.state = "ANALYSING"
  runtime.machine.modal = {operation = "cancel_capture", state = "ANALYSING"}
  local outcome = adapter:apply(captured)
  luaunit.assert_false(outcome.ok)
  luaunit.assert_equals(outcome.code, "stale_generation")
  luaunit.assert_equals(#log, 0)
end

-- Harmony (fake owner; the harmony adapter supplies the real closures) --------------

local function fake_harmony(screen)
  local owner = {screen = screen, generation_value = 1, confirmed = {}, cancelled = {}}
  owner.pending = function(_, contract) return owner.screen == contract.source_route end
  owner.generation = function() return owner.generation_value end
  owner.confirm = function(key, contract) owner.confirmed[#owner.confirmed + 1] = key .. ":" .. contract.action_id end
  owner.cancel = function(key) owner.cancelled[#owner.cancelled + 1] = key end
  return owner
end

function test_ui_adapters_confirmation_harmony_forwards_k3_and_k2_to_the_named_owner_once()
  local owner = fake_harmony("H04_DELETE")
  local adapter = confirmation_factory(ui_adapters, {harmony = owner})
  local outcome = adapter:apply(adapter.capture("H17", {screen = "H17"}))
  luaunit.assert_true(outcome.ok)
  luaunit.assert_equals(owner.confirmed, {"H17:group.confirm_delete"})
  -- the old owner route names the same contract
  owner.screen = "TONE_MAP_RESET"
  adapter:cancel(adapter.capture("TONE_MAP_RESET", {source_route = "TONE_MAP_RESET"}))
  luaunit.assert_equals(owner.cancelled, {"H19"})
end

function test_ui_adapters_confirmation_harmony_refuses_stale_generation_and_missing_owner()
  local owner = fake_harmony("H04_DELETE")
  local adapter = confirmation_factory(ui_adapters, {harmony = owner})
  local captured = adapter.capture("H17", {screen = "H17"})
  owner.generation_value = 2
  local outcome = adapter:apply(captured)
  luaunit.assert_false(outcome.ok)
  luaunit.assert_equals(outcome.code, "stale_generation")
  luaunit.assert_equals(owner.confirmed, {})
  local bare = confirmation_factory(ui_adapters, {})
  luaunit.assert_equals(bare:apply({screen = "H17"}).code, "no_owner")
  luaunit.assert_equals(bare:apply({screen = "C06"}).code, "unknown_confirmation")
end

function test_ui_adapters_confirmation_describe_rejects_foreign_routes()
  local adapter = confirmation_factory(ui_adapters, {harmony = fake_harmony("H04_DELETE")})
  for _, route in ipairs({"H04_DELETE", "C06", "N01"}) do
    local outcome = adapter:describe(route, route, {screen = route, source_route = route})
    luaunit.assert_false(outcome.ok, route)
    luaunit.assert_equals(outcome.code, "foreign_route", route)
    luaunit.assert_nil(outcome.descriptors)
  end
end

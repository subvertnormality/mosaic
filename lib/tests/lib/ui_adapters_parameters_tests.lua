-- Parameters adapter (UI02) over the Channel editor Trig Locks page.
-- Characterises README.md "### Trig Parameters" (E2 selects a param, E3 changes
-- it, holding a step and turning E3 makes a trig lock) and "### Trig Param
-- Locks". Slot ids, descriptor formatting and target checks are presentation
-- plumbing outside the manual (docs/ui-reimplementation spec.json screens
-- C02/C10/C13/F08, field_contracts.parameters).

local h = include("mosaic/lib/tests/helpers/channel_adapter_harness")

local SLOTS = {"slot_1", "slot_2", "slot_3", "slot_4", "slot_5", "slot_6", "slot_7", "slot_8", "slot_9", "slot_10"}

local function describe(env, adapter, route)
  return adapter:describe(route, route, h.target(env, route))
end

local function all_ids()
  local ids = {}
  for _, id in ipairs(SLOTS) do ids[#ids + 1] = id end
  ids[#ids + 1] = "scope"
  ids[#ids + 1] = "wrap"
  return ids
end

function test_ui_adapters_parameters_describes_ten_slots_keyed_by_slot()
  h.isolated(function(env)
    h.setup_rich(env)
    h.start(env)
    env.ui.select_trig_page()
    local outcome = describe(env, h.adapter(env, "parameters"), "C02")
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(h.ids(outcome), all_ids())
    local d = h.by_id(outcome)
    for n = 1, 10 do
      local slot = d["slot_" .. n]
      luaunit.assert_equals(slot.value, tostring(10 * n))
      luaunit.assert_equals(slot.short_label, "L" .. n)
      luaunit.assert_equals(slot.label, "Name " .. n)
      luaunit.assert_equals(slot.repeat_key, "slot_<n>")
      luaunit.assert_equals(slot.domain.slot, n)
      luaunit.assert_equals(slot.domain.state, "set")
    end
    luaunit.assert_equals(d.slot_1.domain.assigned_parameter_id, "tl1")
    luaunit.assert_equals(d.slot_5.domain.assigned_parameter_id, "chord_strum")
    luaunit.assert_true(d.slot_1.selected)
    luaunit.assert_false(d.scope.visible)
  end)
end

function test_ui_adapters_parameters_empty_slots_are_none_and_off_is_x()
  h.isolated(function(env)
    h.setup_rich(env)
    env.channel.trig_lock_params[2] = {}
    env.params.p3 = -1 -- slot 3 at its Off value
    h.start(env)
    env.ui.select_trig_page()
    local d = h.by_id(describe(env, h.adapter(env, "parameters"), "C02"))
    luaunit.assert_equals(d.slot_2.value, "X")
    luaunit.assert_equals(d.slot_2.domain.state, "none")
    luaunit.assert_equals(d.slot_2.domain.assigned_parameter_id, "none")
    luaunit.assert_equals(d.slot_2.short_label, "None")
    luaunit.assert_equals(d.slot_3.value, "X")
    luaunit.assert_equals(d.slot_3.domain.state, "off")
  end)
end

function test_ui_adapters_parameters_views_filter_by_chord_prefix_selection_and_hold()
  h.isolated(function(env)
    h.setup_rich(env)
    h.start(env)
    env.ui.select_trig_page()
    local adapter = h.adapter(env, "parameters")
    luaunit.assert_equals(h.ids(describe(env, adapter, "C10")), {"slot_5", "slot_6"})
    env.ui.enc(2, 8)
    luaunit.assert_equals(h.ids(describe(env, adapter, "C13")), {"slot_9", "scope", "wrap"})
    luaunit.assert_equals(describe(env, adapter, "F08").code, "requires_held")
    env.pressed = {{3, 4}}
    env.ui.refresh_trig_locks()
    local held = describe(env, adapter, "F08")
    luaunit.assert_true(held.ok)
    luaunit.assert_equals(h.values(held), {slot_9 = "90", scope = "STEP03", wrap = "OFF"})
  end)
end

function test_ui_adapters_parameters_reassignment_keeps_the_slot_id()
  h.isolated(function(env)
    h.setup_rich(env)
    h.start(env)
    env.ui.select_trig_page()
    local adapter = h.adapter(env, "parameters")
    local before = describe(env, adapter, "C13")
    env.channel.trig_lock_params[1].id = "cc74"
    local after = describe(env, adapter, "C13")
    luaunit.assert_equals(h.ids(after)[1], "slot_1")
    luaunit.assert_equals(h.by_id(after).slot_1.domain.assigned_parameter_id, "cc74")
    luaunit.assert_true(after.owner_generation > before.owner_generation)
  end)
end

function test_ui_adapters_parameters_describe_of_a_foreign_route_is_an_error()
  h.isolated(function(env)
    h.start(env)
    local outcome = h.adapter(env, "parameters"):describe("C01", "C01", h.target(env, "C01"))
    luaunit.assert_equals(outcome.code, "foreign_route")
    luaunit.assert_nil(outcome.descriptors)
  end)
end

local function parity(setup, old, new)
  local results = {}
  h.isolated(function(env)
    h.setup_rich(env); h.start(env); env.ui.select_trig_page(); if setup then setup(env) end
    env.calls = {}
    old(env)
    results.old = h.observe(env)
  end)
  h.isolated(function(env)
    h.setup_rich(env); h.start(env); env.ui.select_trig_page(); if setup then setup(env) end
    env.calls = {}
    local adapter = h.adapter(env, "parameters")
    local target = h.target(env, "C02")
    local generation = adapter:describe("C02", "C02", target).owner_generation
    new(env, adapter, target, generation)
    results.new = h.observe(env)
  end)
  luaunit.assert_true(#results.old.calls > 0)
  luaunit.assert_equals(results.new, results.old)
end

function test_ui_adapters_parameters_edit_matches_e3_on_the_selected_slot()
  parity(nil,
    function(env) env.ui.enc(3, 2) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("slot_1", 2, target, generation).ok)
    end)
end

function test_ui_adapters_parameters_edit_of_another_slot_matches_e2_then_e3()
  parity(nil,
    function(env) env.ui.enc(2, 2); env.ui.enc(3, -1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("slot_3", -1, target, generation).ok)
    end)
end

function test_ui_adapters_parameters_held_edit_records_the_same_trig_locks()
  parity(function(env) env.pressed = {{3, 4}, {4, 4}}; env.ui.refresh_trig_locks() end,
    function(env) env.ui.enc(2, 1); env.ui.enc(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_equals(target.held, {3, 4})
      luaunit.assert_true(adapter:edit("slot_2", 1, target, generation).ok)
    end)
end

function test_ui_adapters_parameters_slot_edits_are_disabled_while_assignment_is_open()
  h.isolated(function(env)
    h.setup_rich(env)
    h.start(env)
    env.ui.select_trig_page()
    local adapter = h.adapter(env, "parameters")
    env.ui.key(2, 1) -- opens the assignment subpage
    env.calls = {}
    local outcome = adapter:edit("slot_1", 1, h.target(env, "C02"))
    luaunit.assert_equals(outcome.code, "disabled")
    luaunit.assert_equals(env.calls, {})
  end)
end

function test_ui_adapters_parameters_stale_generation_or_target_is_refused_without_mutation()
  h.isolated(function(env)
    h.setup_rich(env)
    h.start(env)
    env.ui.select_trig_page()
    local adapter = h.adapter(env, "parameters")
    local target = h.target(env, "C02")
    local generation = adapter:describe("C02", "C02", target).owner_generation
    env.calls = {}
    env.channel.trig_lock_params[1].id = "cc74" -- reassigned elsewhere
    luaunit.assert_equals(adapter:edit("slot_1", 1, target, generation).code, "stale_generation")
    env.pressed = {{1, 1}} -- a non-step key: the owner would lock step -47
    luaunit.assert_equals(adapter:edit("slot_1", 1, h.target(env, "C02"), nil).code, "stale_target")
    env.pressed = {{3, 4}}
    luaunit.assert_equals(adapter:edit("slot_1", 1, target, nil).code, "stale_target")
    luaunit.assert_equals(env.calls, {})
    luaunit.assert_equals(env.params.p1, 10)
  end)
end

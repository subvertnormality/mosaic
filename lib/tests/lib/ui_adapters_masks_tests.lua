-- Masks adapter (UI02) over the Channel editor Masks page. Characterises
-- README.md "Masks" (### Channel Editor > #### Masks: "Adding Melodic Notes over
-- Harmony and Drums" -- hold a step to lock a mask, no held step sets the
-- channel default) and "### Mask Locks". Descriptor formatting, ids and the
-- held-set target rule are presentation plumbing outside the manual
-- (docs/ui-reimplementation spec.json screens C01/C12/F06, field_contracts.masks).

local h = include("mosaic/lib/tests/helpers/channel_adapter_harness")

local ORDER = {"steps", "trig", "note", "velocity", "length", "chord_1", "chord_2", "chord_3", "chord_4", "scope"}

local function describe(env, adapter, route)
  return adapter:describe(route, route, h.target(env, route))
end

function test_ui_adapters_masks_describes_the_eight_selectors_as_the_page_shows_them()
  h.isolated(function(env)
    h.setup_rich(env)
    h.start(env)
    local outcome = describe(env, h.adapter(env, "masks"), "C01")
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(h.ids(outcome), ORDER)
    -- the same texts channel_edit_page_ui_mutation_killers pins for the drawn page
    luaunit.assert_equals(h.values(outcome), {trig = "Y", note = "C3", velocity = "100", length = "1/4",
      chord_1 = "4th", chord_2 = "6th", chord_3 = "-oct", chord_4 = "--oct", scope = "CHANNEL"})
    local d = h.by_id(outcome)
    luaunit.assert_false(d.steps.visible)
    luaunit.assert_true(d.note.selected) -- init selects the note mask
    luaunit.assert_equals(d.note.domain.state, "set")
    luaunit.assert_equals(d.chord_1.domain.contract_id, "chord_one")
  end)
end

function test_ui_adapters_masks_unset_masks_are_inherit_not_zero()
  h.isolated(function(env)
    h.start(env)
    local d = h.by_id(describe(env, h.adapter(env, "masks"), "C01"))
    for _, id in ipairs({"trig", "note", "velocity", "length", "chord_1", "chord_2", "chord_3", "chord_4"}) do
      luaunit.assert_equals(d[id].value, "X", id)
      luaunit.assert_equals(d[id].domain.state, "inherit", id)
      luaunit.assert_equals(d[id].domain.raw, d[id].domain.inherit, id)
    end
  end)
end

function test_ui_adapters_masks_held_steps_read_the_held_locks_and_scope()
  h.isolated(function(env)
    h.setup_rich(env)
    env.channel.step_note_masks[3] = 64
    env.channel.step_velocity_masks[3] = 30
    h.start(env)
    env.pressed = {{3, 4}}
    env.ui.refresh_masks()
    local adapter = h.adapter(env, "masks")
    local held = describe(env, adapter, "F06")
    luaunit.assert_true(held.ok)
    local v = h.values(held)
    luaunit.assert_equals(v.steps, "03")
    luaunit.assert_equals(v.scope, "STEP03")
    luaunit.assert_equals(v.note, "E3")
    luaunit.assert_equals(v.velocity, "30")
    luaunit.assert_equals(v.trig, "Y") -- no step lock: the channel default
    env.pressed = {{3, 4}, {5, 4}}
    env.ui.refresh_masks()
    v = h.values(describe(env, adapter, "F06"))
    luaunit.assert_equals(v.steps, "03 05")
    luaunit.assert_equals(v.scope, "2 HELD")
    -- the owner shows the last held step's value; it has no MIXED state
    luaunit.assert_equals(v.note, "C3")
  end)
end

function test_ui_adapters_masks_views_filter_the_single_owner_set()
  h.isolated(function(env)
    h.start(env)
    local adapter = h.adapter(env, "masks")
    luaunit.assert_equals(h.ids(describe(env, adapter, "C12")), {"note"})
    luaunit.assert_equals(describe(env, adapter, "F06").code, "requires_held")
    env.ui.enc(2, 1)
    luaunit.assert_equals(h.ids(describe(env, adapter, "C12")), {"velocity"})
  end)
end

function test_ui_adapters_masks_describe_of_a_foreign_route_is_an_error()
  h.isolated(function(env)
    h.start(env)
    local outcome = h.adapter(env, "masks"):describe("C02", "C02", h.target(env, "C02"))
    luaunit.assert_false(outcome.ok)
    luaunit.assert_equals(outcome.code, "foreign_route")
    luaunit.assert_nil(outcome.descriptors)
  end)
end

-- Runs `old` on one fresh page and `new` (given the adapter) on another; both
-- end in the same observable state.
local function parity(setup, old, new)
  local results = {}
  h.isolated(function(env)
    h.setup_rich(env); h.start(env); if setup then setup(env) end
    env.calls = {}
    old(env)
    results.old = h.observe(env)
  end)
  h.isolated(function(env)
    h.setup_rich(env); h.start(env); if setup then setup(env) end
    env.calls = {}
    local adapter = h.adapter(env, "masks")
    local generation = adapter:describe("C01", "C01", h.target(env, "C01")).owner_generation
    new(env, adapter, generation)
    results.new = h.observe(env)
  end)
  luaunit.assert_true(#results.old.calls > 0)
  luaunit.assert_equals(results.new, results.old)
end

function test_ui_adapters_masks_edit_matches_e3_on_the_selected_mask()
  parity(nil,
    function(env) env.ui.enc(3, 2) end,
    function(env, adapter, generation)
      luaunit.assert_true(adapter:edit("note", 2, h.target(env, "C01"), generation).ok)
    end)
end

function test_ui_adapters_masks_edit_of_another_mask_matches_e2_then_e3()
  parity(nil,
    function(env) env.ui.enc(2, 3); env.ui.enc(3, -1) end, -- note -> velocity -> length -> chord 1
    function(env, adapter, generation)
      luaunit.assert_true(adapter:edit("chord_1", -1, h.target(env, "C01"), generation).ok)
    end)
end

function test_ui_adapters_masks_edit_of_the_length_mask_matches_e3()
  parity(function(env) env.ui.enc(2, 2) end,
    function(env) env.ui.enc(3, -3) end,
    function(env, adapter, generation)
      luaunit.assert_true(adapter:edit("length", -3, h.target(env, "C01"), generation).ok)
    end)
end

function test_ui_adapters_masks_held_edit_records_the_same_step_locks()
  local function hold(env)
    env.pressed = {{3, 4}, {7, 5}}
    env.ui.refresh_masks()
  end
  parity(hold,
    function(env) env.ui.enc(2, 1); env.ui.enc(3, 1) end,
    function(env, adapter)
      local target = h.target(env, "F06")
      luaunit.assert_equals(target.held, {3, 23})
      local generation = adapter:describe("F06", "F06", target).owner_generation
      luaunit.assert_true(adapter:edit("velocity", 1, target, generation).ok)
    end)
end

function test_ui_adapters_masks_stale_generation_or_target_is_refused_without_mutation()
  h.isolated(function(env)
    h.setup_rich(env)
    h.start(env)
    local adapter = h.adapter(env, "masks")
    local target = h.target(env, "C01")
    local generation = adapter:describe("C01", "C01", target).owner_generation
    env.calls = {}
    env.pressed = {{3, 4}} -- a hold began after the capture: a new owner state
    luaunit.assert_equals(adapter:edit("note", 1, target, generation).code, "stale_target")
    local held_target = h.target(env, "C01")
    luaunit.assert_equals(adapter:edit("note", 1, held_target, generation).code, "stale_generation")
    env.pressed = {}
    env.program_state.selected_channel = 5
    luaunit.assert_equals(adapter:edit("note", 1, target, nil).code, "stale_target")
    luaunit.assert_equals(env.calls, {})
    luaunit.assert_equals(env.channel.note_mask, 60)
  end)
end

-- Assignment adapter (UI02) over the Trig Locks assignment subpage. Characterises
-- README.md "### Trig Parameters" ("Activating Parameters: To activate a
-- different parameter within the same slot, press K2"). The browse/confirm
-- descriptor shape is presentation plumbing outside the manual
-- (docs/ui-reimplementation spec.json screen C07).

local h = include("mosaic/lib/tests/helpers/channel_adapter_harness")

local function describe(env, adapter)
  return adapter:describe("C07", "C07", h.target(env, "C07", {slot = 1}))
end

local function open(env)
  h.setup_rich(env)
  env.channel.trig_lock_params[1].id = "cc10"
  h.start(env)
  env.ui.select_trig_page()
  env.ui.key(2, 1) -- K2 opens the assignment subpage for slot 1
  return h.adapter(env, "assignment")
end

function test_ui_adapters_assignment_describes_the_filtered_parameter_list()
  h.isolated(function(env)
    local adapter = open(env)
    local outcome = describe(env, adapter)
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(h.ids(outcome), {"none", "cc10", "cc11"})
    luaunit.assert_equals(h.values(outcome), {none = "", cc10 = "CURRENT", cc11 = ""})
    local d = h.by_id(outcome)
    luaunit.assert_true(d.cc10.selected)
    luaunit.assert_equals(d.cc10.kind, "value")
    luaunit.assert_equals(d.none.kind, "readonly")
    luaunit.assert_equals(d.cc11.repeat_key, "<param_id>")
    luaunit.assert_false(adapter.impl.has_draft())
  end)
end

function test_ui_adapters_assignment_route_exists_only_while_the_subpage_is_open()
  h.isolated(function(env)
    local adapter = open(env)
    env.ui.key(2, 1) -- K2 returns to the dials
    luaunit.assert_equals(describe(env, adapter).code, "assignment_closed")
  end)
end

function test_ui_adapters_assignment_describe_of_a_foreign_route_is_an_error()
  h.isolated(function(env)
    local adapter = open(env)
    luaunit.assert_equals(adapter:describe("C02", "C02", h.target(env, "C02")).code, "foreign_route")
  end)
end

function test_ui_adapters_assignment_browse_is_a_draft_until_cancelled()
  h.isolated(function(env)
    local adapter = open(env)
    luaunit.assert_true(adapter:edit("cc10", -2, h.target(env, "C07")).ok)
    luaunit.assert_true(h.by_id(describe(env, adapter)).none.selected)
    luaunit.assert_true(adapter.impl.has_draft())
    env.calls = {}
    luaunit.assert_true(adapter:cancel().ok)
    luaunit.assert_equals(env.channel.trig_lock_params[1].id, "cc10")
    luaunit.assert_equals(env.calls, {})
  end)
end

local function parity(old, new)
  local results = {}
  h.isolated(function(env)
    open(env)
    env.calls = {}
    old(env)
    results.old = h.observe(env)
  end)
  h.isolated(function(env)
    local adapter = open(env)
    env.calls = {}
    local target = h.target(env, "C07", {slot = 1})
    new(env, adapter, target, describe(env, adapter).owner_generation)
    results.new = h.observe(env)
  end)
  luaunit.assert_true(#results.old.calls > 0)
  luaunit.assert_equals(results.new, results.old)
end

function test_ui_adapters_assignment_browse_and_apply_match_e3_k3()
  parity(function(env) env.ui.enc(3, 1); env.ui.key(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("cc10", 1, target, generation).ok)
      luaunit.assert_true(adapter:apply(nil, target).ok)
    end)
end

function test_ui_adapters_assignment_unassign_matches_e3_k3()
  parity(function(env) env.ui.enc(3, -1); env.ui.key(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("cc10", -1, target, generation).ok)
      luaunit.assert_true(adapter:apply(nil, target).ok)
    end)
end

function test_ui_adapters_assignment_stale_generation_or_target_is_refused_without_mutation()
  h.isolated(function(env)
    local adapter = open(env)
    local target = h.target(env, "C07", {slot = 1})
    local generation = describe(env, adapter).owner_generation
    env.calls = {}
    luaunit.assert_equals(adapter:edit("cc11", 1, target, generation).code, "wrong_kind")
    luaunit.assert_equals(adapter:edit("cc10", 1, h.target(env, "C07", {slot = 2}), generation).code, "stale_target")
    env.channel.trig_lock_params[1].id = "cc11" -- assigned elsewhere
    luaunit.assert_equals(adapter:edit("cc10", 1, target, generation).code, "stale_generation")
    luaunit.assert_equals(env.calls, {})
    luaunit.assert_true(h.by_id(describe(env, adapter)).cc10.selected)
  end)
end

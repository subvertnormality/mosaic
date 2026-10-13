-- Clock adapter (UI02) over the Channel editor Clock Mods page. Characterises
-- README.md "#### Clocks, Swing and Shuffle" (per-channel division and
-- multiplication; swing -50..50; shuffle feel and basis; "X" takes the global
-- setting; confirmed changes apply immediately while stopped and at the next
-- song-pattern boundary while playing). Field ids, draft detection and
-- descriptor formatting are presentation plumbing outside the manual
-- (docs/ui-reimplementation spec.json screens C04/F01).

local h = include("mosaic/lib/tests/helpers/channel_adapter_harness")

local ALL = {"rate", "feel_source", "swing_type", "swing", "shuffle_feel", "shuffle_basis", "shuffle_amount",
  "active_rate", "draft_rate", "applies", "scope"}

local function describe(env, adapter, route)
  return adapter:describe(route, route, h.target(env, route))
end

local function open(env)
  h.start(env)
  env.ui.select_clock_mods_page()
  return h.adapter(env, "clock")
end

function test_ui_adapters_clock_describes_the_clock_selectors()
  h.isolated(function(env)
    h.setup_rich(env)
    local adapter = open(env)
    local outcome = describe(env, adapter, "C04")
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(h.ids(outcome), ALL)
    luaunit.assert_equals(h.values(outcome), {rate = "/4", feel_source = "CHANNEL", swing_type = "Swing", swing = "20"})
    luaunit.assert_true(h.by_id(outcome).rate.selected)
    luaunit.assert_equals(describe(env, adapter, "F01").code, "requires_draft")
  end)
end

function test_ui_adapters_clock_unset_channel_shows_global_and_x()
  h.isolated(function(env)
    local adapter = open(env)
    local v = h.values(describe(env, adapter, "C04"))
    luaunit.assert_equals(v.feel_source, "GLOBAL")
    luaunit.assert_equals(v.swing_type, "X")
    luaunit.assert_equals(v.swing, "X") -- global type is Swing, the channel swing is unset
    env.params.global_swing_shuffle_type = 2
    v = h.values(describe(env, adapter, "C04"))
    luaunit.assert_nil(v.swing)
    luaunit.assert_equals({v.shuffle_feel, v.shuffle_basis, v.shuffle_amount}, {"X", "X", "0"})
  end)
end

function test_ui_adapters_clock_staged_rate_is_a_draft_until_cancelled()
  h.isolated(function(env)
    h.setup_rich(env)
    local adapter = open(env)
    luaunit.assert_true(adapter:edit("rate", 1, h.target(env, "C04")).ok)
    local draft = describe(env, adapter, "F01")
    luaunit.assert_true(draft.ok)
    luaunit.assert_equals(h.ids(draft), {"rate", "active_rate", "draft_rate", "applies", "scope"})
    luaunit.assert_equals(h.values(draft), {rate = "/3", active_rate = "/4", draft_rate = "/3",
      applies = "ON CONFIRM", scope = "CHANNEL"})
    luaunit.assert_true(adapter:cancel().ok)
    luaunit.assert_equals(h.values(describe(env, adapter, "C04")).rate, "/4")
    luaunit.assert_equals(env.channel.clock_mods.name, "/4")
  end)
end

function test_ui_adapters_clock_describe_of_a_foreign_route_is_an_error()
  h.isolated(function(env)
    local adapter = open(env)
    luaunit.assert_equals(adapter:describe("C05", "C05", h.target(env, "C05")).code, "foreign_route")
  end)
end

local function parity(setup, old, new)
  local results = {}
  h.isolated(function(env)
    h.setup_rich(env); open(env); if setup then setup(env) end
    env.calls = {}
    old(env)
    results.old = h.observe(env)
  end)
  h.isolated(function(env)
    h.setup_rich(env); local adapter = open(env); if setup then setup(env) end
    env.calls = {}
    local target = h.target(env, "C04")
    local generation = adapter:describe("C04", "C04", target).owner_generation
    new(env, adapter, target, generation)
    results.new = h.observe(env)
  end)
  luaunit.assert_true(#results.old.calls > 0)
  luaunit.assert_equals(results.new, results.old)
end

function test_ui_adapters_clock_rate_edit_and_apply_match_e3_k3()
  parity(nil,
    function(env) env.ui.enc(3, 2); env.ui.key(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("rate", 2, target, generation).ok)
      luaunit.assert_true(adapter:apply(nil, target).ok)
    end)
end

function test_ui_adapters_clock_playing_rate_change_queues_like_e3_k3()
  parity(function(env) env.playing = true end,
    function(env) env.ui.enc(3, -1); env.ui.key(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("rate", -1, target, generation).ok)
      luaunit.assert_true(adapter:apply(nil, target).ok)
    end)
end

function test_ui_adapters_clock_swing_edit_matches_e2_e3_k3()
  parity(nil,
    function(env) env.ui.enc(2, 2); env.ui.enc(3, -3); env.ui.key(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("swing", -3, target, generation).ok)
      luaunit.assert_true(adapter:apply(nil, target).ok)
    end)
end

function test_ui_adapters_clock_type_change_matches_e2_e3_k3()
  parity(nil,
    function(env) env.ui.enc(2, 1); env.ui.enc(3, 1); env.ui.key(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("swing_type", 1, target, generation).ok)
      luaunit.assert_true(adapter:apply(nil, target).ok)
    end)
end

function test_ui_adapters_clock_hidden_fields_and_stale_targets_are_refused_without_mutation()
  h.isolated(function(env)
    h.setup_rich(env)
    local adapter = open(env)
    local target = h.target(env, "C04")
    local generation = adapter:describe("C04", "C04", target).owner_generation
    env.calls = {}
    luaunit.assert_equals(adapter:edit("shuffle_amount", 1, target, generation).code, "disabled")
    env.channel.swing = 5 -- committed elsewhere
    luaunit.assert_equals(adapter:edit("swing", 1, target, generation).code, "stale_generation")
    env.pressed = {{2, 4}}
    luaunit.assert_equals(adapter:edit("swing", 1, target, nil).code, "stale_target")
    luaunit.assert_true(h.by_id(describe(env, adapter, "C04")).rate.selected) -- selection untouched
    luaunit.assert_equals(env.calls, {})
  end)
end

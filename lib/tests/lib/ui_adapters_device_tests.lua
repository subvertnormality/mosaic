-- Device adapter (UI02) over the Channel editor Midi Config page. Characterises
-- README.md "#### Devices" / "#### Device Parameters" (a channel is assigned a
-- device; MIDI devices route to a port and channel). The staged edit, K3
-- confirmation and field ids are presentation plumbing outside the manual
-- (docs/ui-reimplementation spec.json screens C05/C11, provider device).

local h = include("mosaic/lib/tests/helpers/channel_adapter_harness")

local function describe(env, adapter, route)
  return adapter:describe(route, route, h.target(env, route))
end

local function open(env)
  h.start(env)
  env.ui.select_midi_config_page()
  return h.adapter(env, "device")
end

function test_ui_adapters_device_describes_the_routing_selectors()
  h.isolated(function(env)
    local adapter = open(env)
    local outcome = describe(env, adapter, "C05")
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(h.ids(outcome), {"device", "midi_channel", "midi_port", "device_locks", "slot_defaults", "k2_k3"})
    luaunit.assert_equals(h.values(outcome), {device = "MIDI", midi_channel = "CC1", midi_port = "port one"})
    local d = h.by_id(outcome)
    luaunit.assert_true(d.device.selected)
    luaunit.assert_true(d.midi_channel.enabled)
    luaunit.assert_equals(describe(env, adapter, "C11").code, "requires_pending_confirmation")
  end)
end

function test_ui_adapters_device_fixed_and_non_midi_fields()
  h.isolated(function(env)
    local adapter = open(env)
    env.ui.enc(3, 1) -- device map -> "Fixed" (default channel and port)
    local d = h.by_id(describe(env, adapter, "C05"))
    luaunit.assert_equals(d.device.value, "Fixed")
    luaunit.assert_true(d.midi_channel.visible)
    luaunit.assert_false(d.midi_channel.enabled)
    luaunit.assert_false(d.midi_port.enabled)
    env.ui.enc(3, 1) -- -> "Engine" (norns): the owner hides both
    d = h.by_id(describe(env, adapter, "C05"))
    luaunit.assert_false(d.midi_channel.visible)
    luaunit.assert_false(d.midi_port.visible)
    env.ui.enc(3, -2)
    env.midi_connected = false
    luaunit.assert_false(h.by_id(describe(env, adapter, "C05")).midi_port.enabled)
  end)
end

function test_ui_adapters_device_staged_edit_is_a_pending_confirmation()
  h.isolated(function(env)
    local adapter = open(env)
    luaunit.assert_true(adapter:edit("midi_channel", 2, h.target(env, "C05")).ok)
    local outcome = describe(env, adapter, "C11")
    luaunit.assert_true(outcome.ok)
    local v = h.values(outcome)
    luaunit.assert_equals(v.midi_channel, "CC3")
    luaunit.assert_equals(v.device_locks, "RESET")
    luaunit.assert_equals(v.slot_defaults, "REBUILD")
    luaunit.assert_equals(h.by_id(outcome).midi_channel.domain.committed, 1)
    luaunit.assert_true(adapter:cancel().ok)
    luaunit.assert_equals(h.values(describe(env, adapter, "C05")).midi_channel, "CC1")
    luaunit.assert_equals(env.program_state.devices[h.SELECTED].midi_channel, 1)
  end)
end

function test_ui_adapters_device_describe_of_a_foreign_route_is_an_error()
  h.isolated(function(env)
    local adapter = open(env)
    luaunit.assert_equals(adapter:describe("C04", "C04", h.target(env, "C04")).code, "foreign_route")
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
    local target = h.target(env, "C05")
    local generation = adapter:describe("C05", "C05", target).owner_generation
    new(env, adapter, target, generation)
    results.new = h.observe(env)
  end)
  luaunit.assert_true(#results.old.calls > 0)
  luaunit.assert_equals(results.new, results.old)
end

function test_ui_adapters_device_edit_and_apply_match_e2_e3_k3()
  parity(
    function(env) env.ui.enc(2, 1); env.ui.enc(3, 2); env.ui.key(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("midi_channel", 2, target, generation).ok)
      luaunit.assert_true(adapter:apply(nil, target).ok)
    end)
end

function test_ui_adapters_device_map_change_matches_e3_k3()
  parity(
    function(env) env.ui.enc(3, 1); env.ui.key(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("device", 1, target, generation).ok)
      luaunit.assert_true(adapter:apply(nil, target).ok)
    end)
end

function test_ui_adapters_device_stale_generation_or_target_is_refused_without_mutation()
  h.isolated(function(env)
    local adapter = open(env)
    local target = h.target(env, "C05")
    local generation = adapter:describe("C05", "C05", target).owner_generation
    env.program_state.devices[h.SELECTED].midi_channel = 7 -- committed elsewhere
    luaunit.assert_equals(adapter:edit("midi_channel", 1, target, generation).code, "stale_generation")
    env.program_state.selected_channel = 4
    luaunit.assert_equals(adapter:edit("midi_channel", 1, target, nil).code, "stale_target")
    env.program_state.selected_channel = h.SELECTED
    local d = h.by_id(describe(env, adapter, "C05"))
    luaunit.assert_equals(d.midi_channel.value, "CC1")
    luaunit.assert_true(d.device.selected) -- selection untouched
  end)
end

-- History adapter (UI02) over the Channel editor Memory page. Characterises
-- README.md "#### Memory (undo and redo)" (E3 scrolls through past and more
-- recent actions). Descriptor ids and formatting are presentation plumbing
-- outside the manual (docs/ui-reimplementation spec.json screen C03).

local h = include("mosaic/lib/tests/helpers/channel_adapter_harness")

local function describe(env, adapter)
  return adapter:describe("C03", "C03", h.target(env, "C03"))
end

local function open(env, current, total, events)
  env.memory.current, env.memory.total, env.memory.events = current, total, events
  h.start(env)
  env.ui.select_memory_page()
  return h.adapter(env, "history")
end

function test_ui_adapters_history_describes_the_navigator()
  h.isolated(function(env)
    local adapter = open(env, 3, 7, {{type = "note_mask"}})
    local outcome = describe(env, adapter)
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(h.ids(outcome), {"position", "selected_event", "undo_available", "redo_available"})
    luaunit.assert_equals(h.values(outcome), {position = "3 of 7", selected_event = "Event 03",
      undo_available = "3", redo_available = "4"})
    local d = h.by_id(outcome)
    luaunit.assert_true(d.position.selected)
    luaunit.assert_equals(d.selected_event.domain.event_type, "note_mask")
  end)
end

function test_ui_adapters_history_empty_history_and_stored_descriptions()
  h.isolated(function(env)
    local adapter = open(env, 0, 0)
    luaunit.assert_equals(h.values(describe(env, adapter)), {position = "0 of 0", selected_event = "NO HISTORY",
      undo_available = "0", redo_available = "0"})
  end)
  h.isolated(function(env)
    local adapter = open(env, 2, 2, {{type = "trig_lock", description = "Lock p1"}})
    luaunit.assert_equals(h.values(describe(env, adapter)).selected_event, "Lock p1")
  end)
end

function test_ui_adapters_history_describe_of_a_foreign_route_is_an_error()
  h.isolated(function(env)
    local adapter = open(env, 0, 0)
    luaunit.assert_equals(adapter:describe("C01", "C01", h.target(env, "C01")).code, "foreign_route")
  end)
end

local function parity(old, new)
  local results = {}
  h.isolated(function(env)
    open(env, 3, 7)
    env.calls = {}
    old(env)
    results.old = {h.observe(env), env.memory.current}
  end)
  h.isolated(function(env)
    local adapter = open(env, 3, 7)
    env.calls = {}
    local target = h.target(env, "C03")
    new(env, adapter, target, describe(env, adapter).owner_generation)
    results.new = {h.observe(env), env.memory.current}
  end)
  luaunit.assert_true(#results.old[1].calls > 0)
  luaunit.assert_equals(results.new, results.old)
end

function test_ui_adapters_history_position_edit_matches_e3_undo()
  parity(function(env) env.ui.enc(3, -2) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("position", -2, target, generation).ok)
    end)
end

function test_ui_adapters_history_position_edit_matches_e3_redo_and_keeps_generation()
  parity(function(env) env.ui.enc(3, 1); env.ui.enc(3, 1) end,
    function(env, adapter, target, generation)
      luaunit.assert_true(adapter:edit("position", 1, target, generation).ok)
      luaunit.assert_true(adapter:edit("position", 1, target, generation).ok)
    end)
end

function test_ui_adapters_history_stale_generation_or_target_is_refused_without_mutation()
  h.isolated(function(env)
    local adapter = open(env, 3, 7)
    local target = h.target(env, "C03")
    local generation = describe(env, adapter).owner_generation
    env.calls = {}
    luaunit.assert_equals(adapter:edit("undo_available", 1, target, generation).code, "wrong_kind")
    env.memory.total = 8 -- a new event was recorded
    env.ui.refresh_memory()
    luaunit.assert_equals(adapter:edit("position", -1, target, generation).code, "stale_generation")
    env.program_state.selected_channel = 9
    luaunit.assert_equals(adapter:edit("position", -1, target, nil).code, "stale_target")
    luaunit.assert_equals(env.calls, {})
    luaunit.assert_equals(env.memory.current, 3)
  end)
end

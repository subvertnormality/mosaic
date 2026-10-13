local gc_pacer = include("mosaic/lib/gc_pacer")

-- A collector double: records calls, reports a heap size, and completes a
-- cycle after a set number of basic steps. `now` is the CPU clock the pacer
-- reads; each basic step costs `step_cost` seconds of it.
local function fake(options)
  options = options or {}
  local state = {calls = {}, heap_kb = options.heap_kb or 30000, steps = 0,
    cycle_after = options.cycle_after, step_cost = options.step_cost or 0.0001, now = 0,
    after_cycle_kb = options.after_cycle_kb or 20000}
  state.collect = function(what, arg)
    state.calls[#state.calls + 1] = {what, arg}
    if what == "count" then return state.heap_kb end
    if what == "step" then
      state.steps = state.steps + 1
      state.now = state.now + state.step_cost
      if state.cycle_after and state.steps >= state.cycle_after then
        state.heap_kb = state.after_cycle_kb
        return true
      end
      return false
    end
    return 0
  end
  state.clock = function() return state.now end
  state.metros = {}
  state.metro = {
    init = function(action, time, count)
      local m = {action = action, time = time, count = count, id = #state.metros + 1}
      function m:start() self.running = true end
      function m:stop() self.running = false end
      state.metros[#state.metros + 1] = m
      return m
    end,
    free = function(id) state.freed = id end,
  }
  return state
end

local function calls_named(state, what)
  local found = {}
  for _, call in ipairs(state.calls) do
    if call[1] == what then found[#found + 1] = call end
  end
  return found
end

local function new_pacer(state, extra)
  -- Powers of two keep the fake clock exact: a 1/256 s budget.
  local config = {collect = state.collect, clock = state.clock, metro = state.metro, budget_seconds = 1 / 256}
  for k, v in pairs(extra or {}) do config[k] = v end
  return gc_pacer.new(config)
end

-- The automatic collector runs whenever Lua allocates, which in Mosaic is
-- inside clock resumes: on the norns a whole cycle's sweep landed in a few
-- resumes and delayed notes by up to 164 ms. The pacer takes collection out
-- of allocation and runs it from its own timer in bounded slices.
function test_gc_pacer_start_stops_automatic_collection_and_starts_a_timer()
  local state = fake()
  local pacer = gc_pacer.new({collect = state.collect, clock = state.clock, metro = state.metro})
  pacer:start()
  luaunit.assert_equals(#calls_named(state, "stop"), 1)
  luaunit.assert_equals(#state.metros, 1)
  luaunit.assert_true(state.metros[1].running)
  luaunit.assert_almost_equals(state.metros[1].time, 1 / 100, 1e-12)
  luaunit.assert_equals(state.metros[1].count, -1)
end

function test_gc_pacer_slice_uses_basic_steps_until_its_budget_is_spent()
  local state = fake({step_cost = 1 / 1024})
  local pacer = new_pacer(state)
  pacer:start()
  state.metros[1].action()
  -- Basic steps (size 0) only: a sized step would also pay off all debt
  -- accumulated while automatic collection was stopped.
  for _, call in ipairs(calls_named(state, "step")) do luaunit.assert_equals(call[2], 0) end
  -- A 1/256 s budget at 1/1024 s a step: the slice stops once it is spent.
  luaunit.assert_equals(state.steps, 4)
end

function test_gc_pacer_waits_for_garbage_after_a_completed_cycle()
  local state = fake({cycle_after = 2, after_cycle_kb = 20000})
  local pacer = new_pacer(state)
  pacer:start()
  state.metros[1].action()
  luaunit.assert_equals(state.steps, 2)
  -- The cycle left 20 MB: no slices until the heap has grown by half again.
  state.heap_kb = 29000
  state.metros[1].action()
  luaunit.assert_equals(state.steps, 2)
  state.heap_kb = 30500
  state.metros[1].action()
  luaunit.assert_true(state.steps > 2)
end

function test_gc_pacer_spends_a_larger_budget_above_its_ceiling()
  local state = fake({step_cost = 1 / 1024, heap_kb = 70 * 1024})
  local pacer = new_pacer(state, {ceiling_kb = 64 * 1024})
  pacer:start()
  state.metros[1].action()
  -- Four times the 1/256 s budget at 1/1024 s a step.
  luaunit.assert_equals(state.steps, 16)
end

function test_gc_pacer_hands_back_to_the_automatic_collector_when_far_behind()
  local state = fake({heap_kb = 130 * 1024})
  local pacer = new_pacer(state, {ceiling_kb = 64 * 1024})
  pacer:start()
  state.metros[1].action()
  luaunit.assert_equals(#calls_named(state, "restart"), 1)
  -- Once back under the ceiling, pacing resumes with collection stopped.
  state.heap_kb = 40 * 1024
  state.metros[1].action()
  luaunit.assert_equals(#calls_named(state, "stop"), 2)
end

function test_gc_pacer_stop_restores_automatic_collection_for_the_next_script()
  local state = fake()
  local pacer = new_pacer(state)
  pacer:start()
  pacer:stop()
  luaunit.assert_false(state.metros[1].running)
  luaunit.assert_equals(state.freed, state.metros[1].id)
  luaunit.assert_equals(#calls_named(state, "restart"), 1)
  -- Stopping twice is harmless (cleanup can run after a failed init).
  pacer:stop()
  luaunit.assert_equals(#calls_named(state, "restart"), 1)
end

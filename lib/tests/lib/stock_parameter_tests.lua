local stock_parameter = include("mosaic/lib/musical_resolution/stock_parameter")

local function resolve_with(options, resolve_type)
  local calls = {locks = {}, assigned = {}, fallback = 0, default = 0}
  local value = resolve_type(
    options.assignments or {},
    options.type or "fixed_note",
    function(i)
      table.insert(calls.locks, i)
      return options.locks and options.locks[i] or nil
    end,
    function(param_id)
      table.insert(calls.assigned, param_id)
      return options.assigned_values and options.assigned_values[param_id] or nil
    end,
    function()
      calls.fallback = calls.fallback + 1
      return options.fallback_value, function()
        calls.default = calls.default + 1
        return options.fallback_default
      end
    end
  )
  return value, calls
end

-- A step resolves several stock kinds from one assignment scan. Every fixture
-- below also checks that path returns the same value through the same reads.
local function resolve(options)
  local value, calls = resolve_with(options, stock_parameter.resolve)
  local scanned, scanned_calls = resolve_with(options, function(assignments, kind, ...)
    return stock_parameter.resolver(assignments, ...)(kind)
  end)
  luaunit.assert_equals(scanned, value)
  luaunit.assert_equals(scanned_calls, calls)
  return value, calls
end

-- Characterisation, not manual text: the first assigned slot shadows later
-- duplicates and the stock fallback, including when its current value is nil.
function test_stock_parameter_uses_only_the_first_matching_assignment()
  local value, calls = resolve({
    assignments = {
      {id = "fixed_note", param_id = "first", off_value = -1},
      {id = "fixed_note", param_id = "second", off_value = -1}
    },
    assigned_values = {first = 7, second = 9},
    fallback_value = 11,
    fallback_default = 0
  })
  luaunit.assert_equals(value, 7)
  luaunit.assert_equals(calls.locks, {1})
  luaunit.assert_equals(calls.assigned, {"first"})
  luaunit.assert_equals(calls.fallback, 0)

  value, calls = resolve({
    assignments = {{id = "fixed_note", param_id = "first", off_value = -1}},
    fallback_value = 11,
    fallback_default = 0
  })
  luaunit.assert_nil(value)
  luaunit.assert_equals(calls.assigned, {"first"})
  luaunit.assert_equals(calls.fallback, 0)
end

-- Characterisation, not manual text: Off is the assigned definition's own
-- sentinel. Lua zero and minus one remain active values when they are not Off.
function test_stock_parameter_preserves_lock_sentinel_truthiness()
  for _, case in ipairs({
    {off = nil, lock = nil, expected = nil},
    {off = -1, lock = -1, expected = nil},
    {off = 0, lock = 0, expected = nil},
    {off = -1, lock = 0, expected = 0},
    {off = 0, lock = -1, expected = -1}
  }) do
    local value, calls = resolve({
      assignments = {{id = "fixed_note", param_id = "assigned", off_value = case.off}},
      locks = {[1] = case.lock},
      assigned_values = {assigned = 12},
      fallback_value = 15,
      fallback_default = 0
    })
    luaunit.assert_equals(value, case.expected)
    luaunit.assert_equals(calls.locks, {1})
    luaunit.assert_equals(calls.assigned, {})
    luaunit.assert_equals(calls.fallback, 0)
  end
end

function test_stock_parameter_preserves_assigned_current_value_truthiness()
  for _, current in ipairs({0, -1}) do
    local value, calls = resolve({
      assignments = {{id = "fixed_note", param_id = "assigned", off_value = -2}},
      assigned_values = {assigned = current},
      fallback_value = 15,
      fallback_default = 0
    })
    luaunit.assert_equals(value, current)
    luaunit.assert_equals(calls.assigned, {"assigned"})
    luaunit.assert_equals(calls.fallback, 0)
  end
end

-- Characterisation, not manual text: stock fallback is consulted only when no
-- assignment matches and returns a truthy value only when it differs from default.
function test_stock_parameter_preserves_unassigned_fallback_rules()
  for _, case in ipairs({
    {value = nil, default = 0, expected = nil},
    {value = 4, default = 4, expected = nil},
    {value = 0, default = 1, expected = 0},
    {value = -1, default = 0, expected = -1}
  }) do
    local value, calls = resolve({
      assignments = {{id = "random_velocity", param_id = "other", off_value = -1}},
      fallback_value = case.value,
      fallback_default = case.default
    })
    luaunit.assert_equals(value, case.expected)
    luaunit.assert_equals(calls.locks, {})
    luaunit.assert_equals(calls.assigned, {})
    luaunit.assert_equals(calls.fallback, 1)
    luaunit.assert_equals(calls.default, case.value == nil and 0 or 1)
  end
end

-- Characterisation, not manual text: one resolver answers each kind by its own
-- first matching slot among the first ten, ignoring empty and later slots.
function test_stock_parameter_resolver_answers_each_kind_from_one_scan()
  local assignments = {
    {},
    {id = "random_velocity", param_id = "velocity", off_value = -1},
    nil,
    {id = "fixed_note", param_id = "first", off_value = -1},
    {id = "random_velocity", param_id = "shadowed", off_value = -1},
  }
  assignments[11] = {id = "chord_arp", param_id = "beyond", off_value = -1}
  local reads = {}
  local resolve_kind = stock_parameter.resolver(assignments,
    function(i) table.insert(reads, "lock" .. i) end,
    function(param_id) table.insert(reads, param_id); return param_id == "first" and 5 or 6 end,
    function(kind) table.insert(reads, "fallback:" .. kind); return 9, function() return 0 end end)
  luaunit.assert_equals(resolve_kind("fixed_note"), 5)
  luaunit.assert_equals(resolve_kind("random_velocity"), 6)
  luaunit.assert_equals(resolve_kind("chord_arp"), 9)
  luaunit.assert_equals(reads, {"lock4", "first", "lock2", "velocity", "fallback:chord_arp"})
end

-- A remembering resolver answers each kind from its first read until it is
-- reset for another step, including the stock value reported beside an unset
-- kind; after a reset every kind is read again.
function test_stock_parameter_remembering_resolver_reads_each_kind_once_per_step()
  local assignments = {{id = "fixed_note", param_id = "fixed", off_value = -1}}
  local reads = {}
  local assigned = 5
  local resolver = stock_parameter.new_remembering_resolver(
    function(i) table.insert(reads, "lock" .. i) end,
    function(param_id) table.insert(reads, param_id); return assigned end,
    function(kind) table.insert(reads, "fallback:" .. kind); return 0, function() return 0 end end)
  resolver.reset(assignments, {}, 1)
  luaunit.assert_equals(resolver.stock("fixed_note"), 5)
  local value, read = resolver.stock("random_velocity")
  luaunit.assert_nil(value)
  luaunit.assert_equals(read, 0)
  luaunit.assert_equals(resolver.stock("fixed_note"), 5)
  resolver.stock("random_velocity")
  luaunit.assert_equals(reads, {"lock1", "fixed", "fallback:random_velocity"}, "A kind is read once per step")

  assigned = 7
  resolver.reset(assignments, {}, 2)
  luaunit.assert_equals(resolver.stock("fixed_note"), 7, "A reset reads the kind again")
  luaunit.assert_equals(reads, {"lock1", "fixed", "fallback:random_velocity", "lock1", "fixed"})
end

-- The resolver keeps its slot scan between steps, so a reassignment, a cleared
-- slot and a new slot must all be picked up by the next resolver.
function test_stock_parameter_resolver_follows_slot_reassignment()
  local assignments = {{id = "trig_probability", param_id = "p1", off_value = -1}}
  local reads = {}
  local function read_step_lock() return nil end
  local function read_assigned(param_id) reads[#reads + 1] = param_id; return 7 end
  local function read_fallback() return nil, nil end

  local resolve = stock_parameter.resolver(assignments, read_step_lock, read_assigned, read_fallback, {}, 1)
  luaunit.assert_equals(resolve("trig_probability"), 7)
  luaunit.assert_equals(reads, {"p1"})

  -- Same slots again: the cached scan must still answer the same way.
  resolve = stock_parameter.resolver(assignments, read_step_lock, read_assigned, read_fallback, {}, 1)
  luaunit.assert_equals(resolve("trig_probability"), 7)

  -- Reassigned slot.
  assignments[1] = {id = "random_velocity", param_id = "p2", off_value = -1}
  resolve = stock_parameter.resolver(assignments, read_step_lock, read_assigned, read_fallback, {}, 1)
  luaunit.assert_nil(resolve("trig_probability"))
  luaunit.assert_equals(resolve("random_velocity"), 7)
  luaunit.assert_equals(reads[#reads], "p2")

  -- A second slot assigned after the first scan.
  assignments[2] = {id = "trig_probability", param_id = "p3", off_value = -1}
  resolve = stock_parameter.resolver(assignments, read_step_lock, read_assigned, read_fallback, {}, 1)
  luaunit.assert_equals(resolve("trig_probability"), 7)
  luaunit.assert_equals(reads[#reads], "p3")

  -- Clearing a slot removes its kind again.
  assignments[2] = nil
  resolve = stock_parameter.resolver(assignments, read_step_lock, read_assigned, read_fallback, {}, 1)
  luaunit.assert_nil(resolve("trig_probability"))
end

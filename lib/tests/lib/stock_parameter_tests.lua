local stock_parameter = include("mosaic/lib/musical_resolution/stock_parameter")

local function resolve(options)
  local calls = {locks = {}, assigned = {}, fallback = 0, default = 0}
  local value = stock_parameter.resolve(
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

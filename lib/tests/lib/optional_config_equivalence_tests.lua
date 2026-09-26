-- lib/optional_config_transaction.lua compares configurations as their sorted
-- encodings do (keys and scalars by tostring), walked directly so an apply does
-- not serialise whole tables (it stalled the sequencer on the norns).

local transaction = include("mosaic/lib/optional_config_transaction")

function test_optional_config_equivalent_matches_the_encoding_comparison()
  local same = transaction.equivalent
  luaunit.assert_true(same({a = 1, b = {c = "x", d = {1, 2}}}, {b = {d = {1, 2}, c = "x"}, a = 1}))
  luaunit.assert_false(same({a = 1}, {a = 2}))
  luaunit.assert_false(same({a = 1}, {a = 1, b = 2}))
  luaunit.assert_false(same({a = 1, b = 2}, {a = 1}))
  luaunit.assert_false(same({a = {1}}, {a = 1}))
  luaunit.assert_true(same(nil, nil))
  luaunit.assert_false(same({}, nil))
  -- As the encoding does, a number and its string print alike.
  luaunit.assert_true(same({a = 1}, {a = "1"}))
  luaunit.assert_true(same({[1] = true}, {["1"] = true}))
  -- Integer and float print differently in Lua 5.3, as in the encoding.
  luaunit.assert_false(same({a = 1}, {a = 1.0}))
end

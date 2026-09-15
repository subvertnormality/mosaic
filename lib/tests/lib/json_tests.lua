-- Unit tests for lib/helpers/json.lua (vendored rxi/json.lua 0.1.2).
-- README.md does not describe JSON handling, so every assertion here is
-- characterisation: it pins today's behaviour for a later refactor.

local json = include("mosaic/lib/helpers/json")

-- Error message without the "file:line: " prefix Lua adds.
local function json_error(f, ...)
  local ok, err = pcall(f, ...)
  luaunit.assert_false(ok, "expected an error")
  return (tostring(err):gsub("^[^:]*:%d+: ", ""))
end

-- encode ------------------------------------------------------------------------

function test_json_encode_scalars()
  -- characterisation
  luaunit.assert_equals(json.encode(nil), "null")
  luaunit.assert_equals(json.encode(true), "true")
  luaunit.assert_equals(json.encode(false), "false")
  luaunit.assert_equals(json.encode(""), '""')
  luaunit.assert_equals(json.encode("plain"), '"plain"')
end

function test_json_encode_numbers_use_fourteen_significant_digits()
  -- characterisation
  luaunit.assert_equals(json.encode(0), "0")
  luaunit.assert_equals(json.encode(1), "1")
  luaunit.assert_equals(json.encode(-7), "-7")
  luaunit.assert_equals(json.encode(3.0), "3")
  luaunit.assert_equals(json.encode(-0.25), "-0.25")
  luaunit.assert_equals(json.encode(0.1), "0.1")
  luaunit.assert_equals(json.encode(1 / 3), "0.33333333333333")
  luaunit.assert_equals(json.encode(1e20), "1e+20")
  luaunit.assert_equals(json.encode(1e-7), "1e-07")
  luaunit.assert_equals(json.encode(123456789012345), "1.2345678901234e+14")
  luaunit.assert_equals(json.encode(2 ^ 53), "9.007199254741e+15")
  luaunit.assert_equals(json.encode(-0.0), "-0")
end

function test_json_encode_rejects_nan_and_infinities()
  -- characterisation
  luaunit.assert_str_contains(json_error(json.encode, 0 / 0), "unexpected number value '")
  luaunit.assert_equals(json_error(json.encode, math.huge), "unexpected number value 'inf'")
  luaunit.assert_equals(json_error(json.encode, -math.huge), "unexpected number value '-inf'")
  luaunit.assert_equals(json_error(json.encode, {1, math.huge}), "unexpected number value 'inf'")
end

function test_json_encode_escapes_quotes_backslashes_and_control_characters()
  -- characterisation: "/" and DEL (127) and UTF-8 bytes pass through unescaped.
  luaunit.assert_equals(json.encode('a"b\\c'), '"a\\"b\\\\c"')
  luaunit.assert_equals(json.encode("\n\t\r\b\f"), '"\\n\\t\\r\\b\\f"')
  luaunit.assert_equals(json.encode("\1\0\31"), '"\\u0001\\u0000\\u001f"')
  luaunit.assert_equals(json.encode("a/b\127é"), '"a/b\127é"')
end

function test_json_encode_arrays()
  -- characterisation
  luaunit.assert_equals(json.encode({1, 2, 3}), "[1,2,3]")
  luaunit.assert_equals(json.encode({}), "[]")
  luaunit.assert_equals(json.encode({{1}, {}, {"a", true}}), '[[1],[],["a",true]]')
  luaunit.assert_equals(json.encode({{k = 1}}), '[{"k":1}]')
end

function test_json_encode_objects()
  -- characterisation
  luaunit.assert_equals(json.encode({a = 1}), '{"a":1}')
  luaunit.assert_equals(json.encode({name = {list = {1, 2}}}), '{"name":{"list":[1,2]}}')
  luaunit.assert_equals(json.encode({['q"k'] = "v"}), '{"q\\"k":"v"}')
  local two = json.encode({a = 1, b = 2})
  luaunit.assert_true(two == '{"a":1,"b":2}' or two == '{"b":2,"a":1}')
end

function test_json_encode_allows_shared_but_not_circular_references()
  local shared = {1}
  -- characterisation
  luaunit.assert_equals(json.encode({shared, shared}), "[[1],[1]]")
  local object = json.encode({x = shared, y = shared})
  luaunit.assert_true(object == '{"x":[1],"y":[1]}' or object == '{"y":[1],"x":[1]}', object)
  local cycle = {}
  cycle[1] = cycle
  luaunit.assert_equals(json_error(json.encode, cycle), "circular reference")
  local object_cycle = {}
  object_cycle.self = object_cycle
  luaunit.assert_equals(json_error(json.encode, object_cycle), "circular reference")
end

function test_json_encode_rejects_invalid_tables_and_types()
  -- characterisation
  local sparse = {}
  sparse[1] = 1; sparse[3] = 3
  luaunit.assert_equals(json_error(json.encode, sparse), "invalid table: sparse array")
  luaunit.assert_equals(json_error(json.encode, {1, a = 2}), "invalid table: mixed or invalid key types")
  luaunit.assert_equals(json_error(json.encode, {[2] = 1}), "invalid table: mixed or invalid key types")
  luaunit.assert_equals(json_error(json.encode, {[true] = 1}), "invalid table: mixed or invalid key types")
  luaunit.assert_equals(json_error(json.encode, print), "unexpected type 'function'")
  luaunit.assert_equals(json_error(json.encode, {f = print}), "unexpected type 'function'")
end

-- decode ------------------------------------------------------------------------

function test_json_decode_literals()
  -- characterisation
  luaunit.assert_nil(json.decode("null"))
  luaunit.assert_equals(json.decode("true"), true)
  luaunit.assert_equals(json.decode("false"), false)
  luaunit.assert_equals(json.decode("  \n\ttrue \r\n"), true)
end

function test_json_decode_numbers()
  -- characterisation
  luaunit.assert_equals(json.decode("1"), 1)
  luaunit.assert_equals(math.type(json.decode("1")), "integer")
  luaunit.assert_equals(math.type(json.decode("1.0")), "float")
  luaunit.assert_equals(json.decode("-1.5"), -1.5)
  luaunit.assert_equals(json.decode("1e3"), 1000)
  luaunit.assert_equals(json.decode("-1.5E-2"), -0.015)
  -- characterisation: Lua's tonumber is more lenient than JSON.
  luaunit.assert_equals(json.decode("0x10"), 16)
  luaunit.assert_equals(json.decode("01"), 1)
end

function test_json_decode_strings_and_escapes()
  -- characterisation
  luaunit.assert_equals(json.decode('"abc"'), "abc")
  luaunit.assert_equals(json.decode('""'), "")
  luaunit.assert_equals(json.decode('"a\\"b\\\\c\\/d"'), 'a"b\\c/d')
  luaunit.assert_equals(json.decode('"\\n\\t\\r\\b\\f"'), "\n\t\r\b\f")
  luaunit.assert_equals(json.decode('"\\u0041"'), "A")
  luaunit.assert_equals(json.decode('"\\u00e9"'), "\195\169")
  luaunit.assert_equals(json.decode('"\\u20AC"'), "\226\130\172")
  luaunit.assert_equals(json.decode('"\\ud83d\\ude00"'), "\240\159\152\128")
  luaunit.assert_equals(json.decode('"é"'), "é")
  -- characterisation: a lone high surrogate is emitted as its 3-byte form.
  luaunit.assert_equals(json.decode('"\\ud800"'), "\237\160\128")
end

function test_json_decode_arrays_and_objects()
  -- characterisation
  luaunit.assert_equals(json.decode("[]"), {})
  luaunit.assert_equals(json.decode("[ 1 , 2 ,3 ]"), {1, 2, 3})
  luaunit.assert_equals(json.decode('[[1],[],["a",true]]'), {{1}, {}, {"a", true}})
  luaunit.assert_equals(json.decode("{}"), {})
  luaunit.assert_equals(json.decode('{"a":1,"b":[true,false],"c":{"d":"e"}}'),
    {a = 1, b = {true, false}, c = {d = "e"}})
  luaunit.assert_equals(json.decode('{ "a" : 1 }'), {a = 1})
end

function test_json_decode_null_members_leave_holes_and_absent_keys()
  local array = json.decode("[1,null,3]")
  -- characterisation
  luaunit.assert_equals(array[1], 1)
  luaunit.assert_nil(array[2])
  luaunit.assert_equals(array[3], 3)
  luaunit.assert_equals(json.decode('{"a":null,"b":1}'), {b = 1})
  -- duplicate keys: the last one wins.
  luaunit.assert_equals(json.decode('{"a":1,"a":2}'), {a = 2})
end

function test_json_decode_accepts_trailing_commas()
  -- characterisation: not strict JSON.
  luaunit.assert_equals(json.decode("[1,]"), {1})
  luaunit.assert_equals(json.decode('{"a":1,}'), {a = 1})
end

function test_json_decode_errors_report_message_line_and_column()
  -- characterisation
  local cases = {
    {"", "unexpected character '' at line 1 col 1"},
    {"True", "unexpected character 'T' at line 1 col 1"},
    {"tru", "invalid literal 'tru' at line 1 col 1"},
    {"truex", "invalid literal 'truex' at line 1 col 1"},
    {"-", "invalid number '-' at line 1 col 1"},
    {"1.2.3", "invalid number '1.2.3' at line 1 col 1"},
    {'"abc', "expected closing quote for string at line 1 col 1"},
    {'"a\nb"', "control character in string at line 1 col 3"},
    {'"\\x"', "invalid escape char 'x' in string at line 1 col 2"},
    {'"\\u12"', "invalid unicode escape in string at line 1 col 2"},
    {"[1 2]", "expected ']' or ',' at line 1 col 5"},
    {"[", "unexpected character '' at line 1 col 2"},
    {"{", "expected string for key at line 1 col 2"},
    {"{a:1}", "expected string for key at line 1 col 2"},
    {'{"a" 1}', "expected ':' after key at line 1 col 6"},
    {'{"a":}', "unexpected character '}' at line 1 col 6"},
    {'{"a":1 "b":2}', "expected '}' or ',' at line 1 col 9"},
    {'{"a":1,', "expected string for key at line 1 col 8"},
    {"[1] x", "trailing garbage at line 1 col 5"},
    {"[1,\n2,\nx]", "unexpected character 'x' at line 3 col 1"},
  }
  for _, case in ipairs(cases) do
    luaunit.assert_equals(json_error(json.decode, case[1]), case[2], "input " .. string.format("%q", case[1]))
  end
end

function test_json_decode_rejects_non_string_arguments()
  -- characterisation
  luaunit.assert_equals(json_error(json.decode, 5), "expected argument of type string, got number")
  luaunit.assert_equals(json_error(json.decode, nil), "expected argument of type string, got nil")
  luaunit.assert_equals(json_error(json.decode, {}), "expected argument of type string, got table")
end

-- round trips -------------------------------------------------------------------

function test_json_round_trip_nested_structures()
  local original = {
    name = 'Device "One"\n',
    unicode = "é€😀",
    enabled = true,
    disabled = false,
    params = {
      {id = "cutoff", min = 0, max = 127, step = 0.5, options = {"a", "b"}},
      {id = "res", min = -64, max = 63, nested = {deep = {deeper = {1, 2, 3}}}},
    },
    empty_list = {},
  }
  -- characterisation
  luaunit.assert_equals(json.decode(json.encode(original)), original)
end

function test_json_round_trip_text_is_stable_for_arrays()
  local text = '[1,-2.5,"x\\ny",true,false,[],[[1]],{"k":"v"}]'
  -- characterisation
  luaunit.assert_equals(json.encode(json.decode(text)), text)
end

function test_json_round_trip_number_precision_and_type()
  -- characterisation: floats with integral values come back as integers and
  -- values needing more than 14 significant digits lose precision.
  local three = json.decode(json.encode(3.0))
  luaunit.assert_equals(math.type(three), "integer")
  luaunit.assert_equals(json.decode(json.encode(0.1)), 0.1)
  luaunit.assert_not_equals(json.decode(json.encode(1 / 3)), 1 / 3)
  luaunit.assert_equals(json.decode(json.encode(1 / 3)), 0.33333333333333)
  luaunit.assert_equals(json.decode(json.encode(2 ^ 53)), 9.007199254741e+15)
end

function test_json_round_trip_empty_object_becomes_array()
  -- characterisation: an empty table always encodes as [] and decodes to {}.
  luaunit.assert_equals(json.encode(json.decode("{}")), "[]")
end

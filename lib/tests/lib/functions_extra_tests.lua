-- Unit tests for lib/helpers/functions.lua helpers that no other test calls directly.
-- Uses the global `fn` loaded by run_tests.lua. Assertions not backed by README.md
-- are marked "-- characterisation": they pin today's behaviour so a refactor or a
-- performance sweep cannot change it silently.

-- Temporarily replace fields ({tbl, key, value} triples), run body, always restore.
local function with_overrides(overrides, body)
  local saved = {}
  for i, o in ipairs(overrides) do
    saved[i] = o[1][o[2]]
    o[1][o[2]] = o[3]
  end
  local ok, err = pcall(body)
  for i = #overrides, 1, -1 do
    overrides[i][1][overrides[i][2]] = saved[i]
  end
  if not ok then error(err, 0) end
end

-- Error message without the "file:line: " prefix Lua adds.
local function error_of(f, ...)
  local ok, err = pcall(f, ...)
  luaunit.assert_false(ok)
  return (tostring(err):gsub("^[^:]*:%d+: ", ""))
end

-- fn.cleanup ------------------------------------------------------------------

function test_fnx_cleanup_stops_midi_grid_and_both_clocks_in_order()
  local calls = {}
  local midi_stub = {all_off = function(...) table.insert(calls, {"all_off", select("#", ...)}) end}
  local grid_stub = {cleanup = function(...) table.insert(calls, {"g.cleanup", select("#", ...)}) end}
  local function cancel(id) table.insert(calls, {"cancel", id}) end
  with_overrides({
    {_G, "_midi", midi_stub}, {_G, "g", grid_stub}, {clock, "cancel", cancel},
    {_G, "redraw_clock_id", 11}, {_G, "grid_clock_id", 22},
  }, function()
    fn.cleanup()
  end)
  -- characterisation
  luaunit.assert_equals(calls, {{"all_off", 0}, {"g.cleanup", 0}, {"cancel", 11}, {"cancel", 22}})
end

-- dirty flags -----------------------------------------------------------------

function test_fnx_dirty_grid_getter_and_setter_including_false()
  local original = fn.dirty_grid()
  luaunit.assert_equals(fn.dirty_grid(true), true)
  luaunit.assert_equals(fn.dirty_grid(), true)
  luaunit.assert_equals(fn.dirty_grid(nil), true)
  -- false is a value to store, not a request to read. -- characterisation
  luaunit.assert_equals(fn.dirty_grid(false), false)
  luaunit.assert_equals(fn.dirty_grid(), false)
  if original ~= nil then fn.dirty_grid(original) end
end

function test_fnx_dirty_screen_getter_and_setter_independent_of_grid()
  local original_screen, original_grid = fn.dirty_screen(), fn.dirty_grid()
  fn.dirty_grid(false)
  luaunit.assert_equals(fn.dirty_screen(true), true)
  luaunit.assert_equals(fn.dirty_screen(), true)
  luaunit.assert_equals(fn.dirty_grid(), false)
  luaunit.assert_equals(fn.dirty_screen(false), false)
  luaunit.assert_equals(fn.dirty_screen(), false)
  fn.dirty_grid(true)
  luaunit.assert_equals(fn.dirty_screen(), false)
  if original_screen ~= nil then fn.dirty_screen(original_screen) end
  if original_grid ~= nil then fn.dirty_grid(original_grid) end
end

-- id-keyed table helpers ------------------------------------------------------

function test_fnx_remove_table_by_id_removes_every_match_including_adjacent_ones()
  local t = {{id = 1, n = "a"}, {id = 2, n = "b"}, {id = 1, n = "c"}, {id = 1, n = "d"}, {id = 3, n = "e"}}
  luaunit.assert_nil(fn.remove_table_by_id(t, 1))
  luaunit.assert_equals(t, {{id = 2, n = "b"}, {id = 3, n = "e"}})
  fn.remove_table_by_id(t, 99)
  luaunit.assert_equals(t, {{id = 2, n = "b"}, {id = 3, n = "e"}})
  local first_and_last = {{id = 5}, {id = 6}, {id = 5}}
  fn.remove_table_by_id(first_and_last, 5)
  luaunit.assert_equals(first_and_last, {{id = 6}})
  local empty = {}
  fn.remove_table_by_id(empty, 1)
  luaunit.assert_equals(empty, {})
end

function test_fnx_id_appears_in_table_first_last_and_absent()
  local t = {{id = "first"}, {id = "middle"}, {id = "last"}}
  luaunit.assert_true(fn.id_appears_in_table(t, "first"))
  luaunit.assert_true(fn.id_appears_in_table(t, "last"))
  luaunit.assert_false(fn.id_appears_in_table(t, "missing"))
  luaunit.assert_false(fn.id_appears_in_table({}, "first"))
end

function test_fnx_appears_in_table_compares_values_not_ids()
  local t = {"a", 2, "c"}
  luaunit.assert_true(fn.appears_in_table(t, "a"))
  luaunit.assert_true(fn.appears_in_table(t, "c"))
  luaunit.assert_true(fn.appears_in_table(t, 2))
  luaunit.assert_false(fn.appears_in_table(t, "2"))
  luaunit.assert_false(fn.appears_in_table({{id = "a"}}, "a"))
  luaunit.assert_false(fn.appears_in_table({}, "a"))
end

function test_fnx_get_by_id_returns_the_last_match_and_nil_when_absent()
  local early, late = {id = 7, n = "early"}, {id = 7, n = "late"}
  local t = {{id = 1}, early, {id = 2}, late}
  -- characterisation: searches from the end, so the LAST duplicate wins.
  luaunit.assert_is(fn.get_by_id(t, 7), late)
  luaunit.assert_is(fn.get_by_id(t, 1), t[1])
  luaunit.assert_nil(fn.get_by_id(t, 99))
end

function test_fnx_get_index_by_id_returns_the_highest_matching_index()
  local t = {{id = 1}, {id = 7}, {id = 2}, {id = 7}}
  -- characterisation
  luaunit.assert_equals(fn.get_index_by_id(t, 7), 4)
  luaunit.assert_equals(fn.get_index_by_id(t, 1), 1)
  luaunit.assert_nil(fn.get_index_by_id(t, 99))
end

function test_fnx_find_in_table_by_id_returns_the_first_match()
  local early, late = {id = 7, n = "early"}, {id = 7, n = "late"}
  local t = {{id = 1}, early, late}
  -- characterisation: forward search, so the FIRST duplicate wins (opposite of get_by_id).
  luaunit.assert_is(fn.find_in_table_by_id(t, 7), early)
  luaunit.assert_nil(fn.find_in_table_by_id(t, 99))
  luaunit.assert_nil(fn.find_in_table_by_id({}, 7))
end

function test_fnx_find_index_in_table_by_value_reads_the_value_field()
  local t = {{value = "x"}, {value = "y"}, {value = "y"}}
  luaunit.assert_equals(fn.find_index_in_table_by_value(t, "x"), 1)
  luaunit.assert_equals(fn.find_index_in_table_by_value(t, "y"), 2)
  luaunit.assert_nil(fn.find_index_in_table_by_value(t, "z"))
  luaunit.assert_nil(fn.find_index_in_table_by_value({"x"}, "x"))
end

function test_fnx_find_index_by_value_first_match_or_nil()
  local t = {"a", "b", "b", "c"}
  luaunit.assert_equals(fn.find_index_by_value(t, "a"), 1)
  luaunit.assert_equals(fn.find_index_by_value(t, "b"), 2)
  luaunit.assert_equals(fn.find_index_by_value(t, "c"), 4)
  luaunit.assert_nil(fn.find_index_by_value(t, "d"))
end

function test_fnx_find_key_returns_key_for_value_or_nil()
  luaunit.assert_equals(fn.find_key({alpha = 1, beta = 2}, 2), "beta")
  luaunit.assert_equals(fn.find_key({10, 20, 30}, 30), 3)
  luaunit.assert_nil(fn.find_key({alpha = 1}, 2))
  luaunit.assert_nil(fn.find_key({}, 1))
end

-- string helpers --------------------------------------------------------------

function test_fnx_limit_string_boundaries()
  luaunit.assert_equals(fn.limit_string("abcdef", 3), "abc")
  luaunit.assert_equals(fn.limit_string("abcd", 3), "abc")
  luaunit.assert_equals(fn.limit_string("abc", 3), "abc")
  luaunit.assert_equals(fn.limit_string("ab", 3), "ab")
  luaunit.assert_equals(fn.limit_string("", 0), "")
  luaunit.assert_equals(fn.limit_string("a", 0), "")
end

function test_fnx_string_in_table_uses_sequence_part_only()
  luaunit.assert_true(fn.string_in_table({"a", "b"}, "a"))
  luaunit.assert_true(fn.string_in_table({"a", "b"}, "b"))
  luaunit.assert_false(fn.string_in_table({"a", "b"}, "c"))
  -- characterisation: ipairs stops at the first hole and ignores hash keys.
  luaunit.assert_false(fn.string_in_table({"a", nil, "c"}, "c"))
  luaunit.assert_false(fn.string_in_table({k = "a"}, "a"))
end

function test_fnx_title_case_capitalises_each_word_and_returns_count()
  local s, n = fn.title_case("hello wORLD")
  luaunit.assert_equals(s, "Hello World")
  -- characterisation: string.gsub's replacement count is returned as a second value.
  luaunit.assert_equals(n, 2)
  luaunit.assert_equals((fn.title_case("it's snake_case")), "It's Snake_case")
  luaunit.assert_equals({fn.title_case("123abc")}, {"123Abc", 1})
  luaunit.assert_equals({fn.title_case("")}, {"", 0})
end

function test_fnx_snake_case_lowercases_capitals_and_joins_spaces()
  luaunit.assert_equals({fn.snake_case("Hello World")}, {"hello_world", 0})
  luaunit.assert_equals({fn.snake_case("a b c")}, {"a_b_c", 2})
  -- characterisation: camelCase is lowercased without a separator.
  luaunit.assert_equals((fn.snake_case("helloWorld")), "helloworld")
  -- characterisation: a double space keeps one underscore per space.
  luaunit.assert_equals((fn.snake_case("Hello  World")), "hello__world")
  luaunit.assert_equals((fn.snake_case("already_snake")), "already_snake")
end

function test_fnx_format_first_descriptor_truncates_to_four_upper_chars()
  -- characterisation: words longer than 4 lose the first vowel that follows a consonant.
  luaunit.assert_equals(fn.format_first_descriptor("Velocity"), "VLOC")
  luaunit.assert_equals(fn.format_first_descriptor("Filter cutoff"), "FLTE")
  luaunit.assert_equals(fn.format_first_descriptor("Attack"), "ATTC")
  luaunit.assert_equals(fn.format_first_descriptor("Pitch"), "PTCH") -- 5 letters: vowel dropped
  luaunit.assert_equals(fn.format_first_descriptor("Gate"), "GATE") -- 4 letters: kept whole
  luaunit.assert_equals(fn.format_first_descriptor("rhythm"), "RHYT") -- no consonant+vowel pair
  luaunit.assert_equals(fn.format_first_descriptor("Q"), "Q")
  luaunit.assert_equals(fn.format_first_descriptor("  lfo-rate"), "LFO")
end

function test_fnx_format_first_descriptor_errors_without_a_word()
  -- characterisation: no word means truncate_word(nil) raises.
  luaunit.assert_str_contains(error_of(fn.format_first_descriptor, " - "), "attempt to get length of a nil value")
end

function test_fnx_format_last_descriptor_only_for_multi_word_names()
  luaunit.assert_equals(fn.format_last_descriptor("Filter cutoff"), "CTOF")
  luaunit.assert_equals(fn.format_last_descriptor("Mod 1"), "1")
  luaunit.assert_equals(fn.format_last_descriptor("Env amt"), "AMT")
  luaunit.assert_equals(fn.format_last_descriptor("Osc 2 Pitch"), "PTCH")
  -- characterisation
  luaunit.assert_equals(fn.format_last_descriptor("Velocity"), "")
  luaunit.assert_equals(fn.format_last_descriptor(""), "")
end

function test_fnx_string_trim()
  luaunit.assert_equals(fn.string_trim("  a b  "), "a b")
  luaunit.assert_equals(fn.string_trim("\t x\n"), "x")
  luaunit.assert_equals(fn.string_trim("x"), "x")
  luaunit.assert_equals(fn.string_trim("   "), "")
  luaunit.assert_equals(fn.string_trim(""), "")
end

function test_fnx_string_split_keeps_empty_fields_and_accepts_patterns()
  luaunit.assert_equals(fn.string_split("a,b,,c", ","), {"a", "b", "", "c"})
  luaunit.assert_equals(fn.string_split("abc", ","), {"abc"})
  luaunit.assert_equals(fn.string_split("a,", ","), {"a", ""})
  luaunit.assert_equals(fn.string_split(",a", ","), {"", "a"})
  luaunit.assert_equals(fn.string_split("", ","), {""})
  luaunit.assert_equals(fn.string_split("a1b22c", "%d+"), {"a", "b", "c"})
end

function test_fnx_string_split_appends_to_and_returns_the_given_table()
  local out = {"x"}
  local result = fn.string_split("a b", " ", out)
  luaunit.assert_is(result, out)
  luaunit.assert_equals(out, {"x", "a", "b"})
end

function test_fnx_starts_with()
  luaunit.assert_true(fn.starts_with("hello", "he"))
  luaunit.assert_true(fn.starts_with("hello", "hello"))
  luaunit.assert_true(fn.starts_with("hello", ""))
  luaunit.assert_false(fn.starts_with("hello", "lo"))
  luaunit.assert_false(fn.starts_with("he", "hello"))
  luaunit.assert_false(fn.starts_with("Hello", "he"))
end

function test_fnx_get_last_char()
  luaunit.assert_equals(fn.get_last_char("abc"), "c")
  luaunit.assert_equals(fn.get_last_char("a"), "a")
  luaunit.assert_equals(fn.get_last_char(""), "")
end

-- table serialisation ---------------------------------------------------------

function test_fnx_table_to_string_exact_output_for_single_key_shapes()
  luaunit.assert_equals(fn.table_to_string({}), "{}")
  luaunit.assert_equals(fn.table_to_string({5}), "{[1]=5,}")
  luaunit.assert_equals(fn.table_to_string({1, 2}), "{[1]=1,[2]=2,}")
  luaunit.assert_equals(fn.table_to_string({a = "x"}), '{["a"]="x",}')
  luaunit.assert_equals(fn.table_to_string({t = {1}}), '{["t"]={[1]=1,},}')
  luaunit.assert_equals(fn.table_to_string({[3] = 1.5}), "{[3]=1.5,}")
end

function test_fnx_table_to_string_round_trips_through_string_to_table()
  local original = {1, 2, name = "chan", nested = {x = 3, list = {4, 5}}, [10] = -1}
  luaunit.assert_equals(fn.string_to_table(fn.table_to_string(original)), original)
end

function test_fnx_table_to_string_rejects_boolean_values()
  -- characterisation (suspected defect: booleans are passed raw to table.concat,
  -- so any table holding true/false cannot be serialised).
  luaunit.assert_str_contains(error_of(fn.table_to_string, {flag = true}), "invalid value")
end

function test_fnx_table_to_string_does_not_escape_quotes()
  -- characterisation (suspected defect: a string containing a double quote is
  -- written unescaped, so string_to_table cannot load it back).
  local s = fn.table_to_string({a = 'say "hi"'})
  luaunit.assert_equals(s, '{["a"]="say "hi"",}')
  luaunit.assert_false(pcall(fn.string_to_table, s))
end

function test_fnx_string_to_table_evaluates_a_lua_expression()
  luaunit.assert_equals(fn.string_to_table("{1,2}"), {1, 2})
  luaunit.assert_equals(fn.string_to_table("{a=1,b={c=2}}"), {a = 1, b = {c = 2}})
  luaunit.assert_equals(fn.string_to_table("42"), 42)
  -- characterisation: a syntax error surfaces as calling nil.
  luaunit.assert_str_contains(error_of(fn.string_to_table, "{1,"), "attempt to call a nil value")
end

function test_fnx_print_table_prints_flat_nested_and_scalar_values()
  local lines = {}
  with_overrides({{_G, "print", function(s) table.insert(lines, s) end}}, function()
    fn.print_table({a = 1})
    fn.print_table({t = {x = "y"}})
    fn.print_table(5)
    fn.print_table("s", ">>")
  end)
  -- characterisation
  luaunit.assert_equals(lines, {"a : 1", "t :", "  x : y", "5", ">>s"})
end

function test_fnx_print_table_stops_past_max_depth()
  local lines = {}
  with_overrides({{_G, "print", function(s) table.insert(lines, s) end}}, function()
    fn.print_table({t = {x = 1}}, "", 0, 0)
    fn.print_table({t = {x = 1}}, "", 0, 1)
  end)
  -- characterisation
  luaunit.assert_equals(lines, {"t :", "  ...", "t :", "  x : 1"})
end

function test_fnx_print_table_default_depth_is_seven()
  local root = {}
  local node = root
  for _ = 1, 9 do node.c = {}; node = node.c end
  node.leaf = 1
  local lines = {}
  with_overrides({{_G, "print", function(s) table.insert(lines, s) end}}, function()
    fn.print_table(root)
  end)
  -- characterisation: depths 0..7 print their key, depth 8 prints "...".
  local expected = {}
  for d = 0, 7 do table.insert(expected, string.rep("  ", d) .. "c :") end
  table.insert(expected, string.rep("  ", 8) .. "...")
  luaunit.assert_equals(lines, expected)
end

-- merging and copying ---------------------------------------------------------

function test_fnx_merge_tables_is_shallow_in_place_and_aliases_nested_values()
  local shared = {deep = 1}
  local t1 = {a = 1, b = 2, keep = {old = true}}
  local t2 = {b = 3, c = shared, keep = {new = true}}
  local result = fn.merge_tables(t1, t2)
  luaunit.assert_is(result, t1)
  luaunit.assert_equals(t1, {a = 1, b = 3, c = {deep = 1}, keep = {new = true}})
  luaunit.assert_is(t1.c, shared) -- characterisation
  luaunit.assert_equals(t2, {b = 3, c = {deep = 1}, keep = {new = true}})
end

function test_fnx_deep_merge_tables_merges_nested_without_aliasing()
  local t1 = {a = 1, nested = {x = 1, y = 2}}
  local source_nested = {y = 20, z = 30}
  local source_new = {k = {v = 1}}
  local result = fn.deep_merge_tables(t1, {a = 2, nested = source_nested, fresh = source_new})
  luaunit.assert_is(result, t1)
  luaunit.assert_equals(t1, {a = 2, nested = {x = 1, y = 20, z = 30}, fresh = {k = {v = 1}}})
  luaunit.assert_not_is(t1.fresh, source_new)
  luaunit.assert_not_is(t1.fresh.k, source_new.k)
  source_new.k.v = 99
  luaunit.assert_equals(t1.fresh.k.v, 1)
end

function test_fnx_deep_merge_tables_scalar_overwrites_table_and_table_into_scalar_errors()
  local t1 = {a = {x = 1}}
  fn.deep_merge_tables(t1, {a = 5})
  luaunit.assert_equals(t1, {a = 5})
  -- characterisation: merging a table onto an existing scalar indexes the scalar.
  luaunit.assert_str_contains(error_of(fn.deep_merge_tables, {a = 5}, {a = {x = 1}}), "attempt to index a number value")
end

function test_fnx_deep_copy_does_not_alias_and_keeps_metatable()
  local mt = {__index = {kind = "step"}}
  local original = setmetatable({list = {1, 2, {3}}, name = "n"}, mt)
  local copy = fn.deep_copy(original)
  luaunit.assert_equals(copy, original)
  luaunit.assert_not_is(copy, original)
  luaunit.assert_not_is(copy.list, original.list)
  luaunit.assert_not_is(copy.list[3], original.list[3])
  luaunit.assert_is(getmetatable(copy), mt)
  luaunit.assert_equals(copy.kind, "step")
  copy.list[3][1] = 99
  luaunit.assert_equals(original.list[3][1], 3)
  luaunit.assert_equals(fn.deep_copy(5), 5)
  luaunit.assert_equals(fn.deep_copy("s"), "s")
  luaunit.assert_nil(fn.deep_copy(nil))
end

function test_fnx_deep_copy_aliases_below_the_depth_limit()
  local levels = {{}}
  for i = 2, 10 do levels[i] = {}; levels[i - 1].child = levels[i] end
  local copy = fn.deep_copy(levels[1])
  local node = copy
  -- characterisation: default max_depth 7 copies depths 0..7 and aliases depth 8.
  for depth = 0, 7 do
    luaunit.assert_not_is(node, levels[depth + 1])
    node = node.child
  end
  luaunit.assert_is(node, levels[9])

  local shallow = fn.deep_copy(levels[1], 0)
  luaunit.assert_not_is(shallow, levels[1])
  luaunit.assert_is(shallow.child, levels[2])

  local one = fn.deep_copy(levels[1], 1)
  luaunit.assert_not_is(one.child, levels[2])
  luaunit.assert_is(one.child.child, levels[3])
end

-- counting and comparison -----------------------------------------------------

function test_fnx_table_count_counts_all_keys()
  luaunit.assert_equals(fn.table_count({}), 0)
  luaunit.assert_equals(fn.table_count({1, 2, 3}), 3)
  luaunit.assert_equals(fn.table_count({1, a = 2, [10] = 3}), 3)
end

function test_fnx_table_has_one_item()
  luaunit.assert_false(fn.table_has_one_item({}))
  luaunit.assert_true(fn.table_has_one_item({1}))
  luaunit.assert_true(fn.table_has_one_item({a = 1}))
  luaunit.assert_false(fn.table_has_one_item({1, 2}))
  luaunit.assert_false(fn.table_has_one_item({1, a = 2, b = 3}))
end

function test_fnx_tables_are_equal_is_shallow()
  luaunit.assert_true(fn.tables_are_equal({}, {}))
  luaunit.assert_true(fn.tables_are_equal({1, 2, a = "x"}, {1, 2, a = "x"}))
  luaunit.assert_false(fn.tables_are_equal({1, 2}, {1, 2, 3}))
  luaunit.assert_false(fn.tables_are_equal({1, 2, 3}, {1, 2}))
  luaunit.assert_false(fn.tables_are_equal({a = 1, b = 2}, {a = 1, c = 2}))
  luaunit.assert_false(fn.tables_are_equal({a = 1}, {a = 2}))
  local shared = {}
  luaunit.assert_true(fn.tables_are_equal({shared}, {shared}))
  -- characterisation: nested tables compare by reference.
  luaunit.assert_false(fn.tables_are_equal({{}}, {{}}))
end

function test_fnx_table_contains_sequence_values()
  luaunit.assert_true(fn.table_contains({1, 2, 3}, 1))
  luaunit.assert_true(fn.table_contains({1, 2, 3}, 3))
  luaunit.assert_false(fn.table_contains({1, 2, 3}, 4))
  luaunit.assert_false(fn.table_contains({a = 1}, 1))
  luaunit.assert_false(fn.table_contains({}, nil))
end

function test_fnx_remove_table_from_table_removes_only_first_shallow_match()
  local t = {{a = 1}, {b = 2}, {a = 1}}
  luaunit.assert_nil(fn.remove_table_from_table(t, {a = 1}))
  luaunit.assert_equals(t, {{b = 2}, {a = 1}})
  fn.remove_table_from_table(t, {c = 3})
  luaunit.assert_equals(t, {{b = 2}, {a = 1}})
  fn.remove_table_from_table(t, {a = 1})
  luaunit.assert_equals(t, {{b = 2}})
end

function test_fnx_filter_by_type_returns_new_ordered_table()
  local a, b, c = {type = "x", n = 1}, {type = "y", n = 2}, {type = "x", n = 3}
  local input = {a, b, c}
  local result = fn.filter_by_type(input, "x")
  luaunit.assert_equals(#result, 2)
  luaunit.assert_is(result[1], a)
  luaunit.assert_is(result[2], c)
  luaunit.assert_equals(input, {a, b, c})
  luaunit.assert_equals(fn.filter_by_type(input, "z"), {})
end

-- sets ------------------------------------------------------------------------

function test_fnx_set_add_query_remove()
  local set = {}
  luaunit.assert_false(fn.is_in_set(set, "k"))
  fn.add_to_set(set, "k")
  luaunit.assert_equals(set, {k = true})
  luaunit.assert_true(fn.is_in_set(set, "k"))
  luaunit.assert_false(fn.is_in_set(set, "other"))
  fn.remove_from_set(set, "k")
  luaunit.assert_equals(set, {})
  luaunit.assert_false(fn.is_in_set(set, "k"))
  -- characterisation: presence is "not nil", so a stored false counts as a member.
  luaunit.assert_true(fn.is_in_set({k = false}, "k"))
end

-- numeric helpers -------------------------------------------------------------

function test_fnx_scale_maps_linearly_including_inverted_ranges()
  luaunit.assert_equals(fn.scale(5, 0, 10, 0, 100), 50)
  luaunit.assert_equals(fn.scale(0, 0, 10, 20, 40), 20)
  luaunit.assert_equals(fn.scale(10, 0, 10, 20, 40), 40)
  luaunit.assert_equals(fn.scale(2.5, 0, 10, 100, 0), 75)
  luaunit.assert_equals(fn.scale(15, 0, 10, 0, 100), 150) -- characterisation: not clamped
  luaunit.assert_equals(fn.scale(-1, -2, 2, 0, 8), 2)
  -- characterisation: an empty input range yields NaN rather than an error.
  luaunit.assert_nan(fn.scale(1, 1, 1, 0, 10))
end

function test_fnx_value_from_note_and_note_from_value_are_14_minus()
  luaunit.assert_equals(fn.value_from_note(0), 14)
  luaunit.assert_equals(fn.value_from_note(14), 0)
  luaunit.assert_equals(fn.value_from_note(20), -6)
  luaunit.assert_equals(fn.note_from_value(3), 11)
  for n = -7, 21 do
    luaunit.assert_equals(fn.note_from_value(fn.value_from_note(n)), n)
  end
end

function test_fnx_round_half_up_including_negatives()
  luaunit.assert_equals(fn.round(2.5), 3)
  luaunit.assert_equals(fn.round(2.49), 2)
  luaunit.assert_equals(fn.round(2), 2)
  luaunit.assert_equals(fn.round(-2.5), -2) -- characterisation: halves round toward +inf
  luaunit.assert_equals(fn.round(-2.51), -3)
  luaunit.assert_equals(fn.round(-0.5), 0)
end

function test_fnx_round_to_decimal_places()
  luaunit.assert_equals(fn.round_to_decimal_places(2.125, 2), 2.13)
  luaunit.assert_equals(fn.round_to_decimal_places(2.5), 3)
  luaunit.assert_equals(fn.round_to_decimal_places(2.4, 0), 2)
  luaunit.assert_equals(fn.round_to_decimal_places(-1.25, 1), -1.2)
  luaunit.assert_equals(fn.round_to_decimal_places(1234, -2), 1200)
end

function test_fnx_calc_grid_count_maps_rows_four_to_seven_onto_steps()
  luaunit.assert_equals(fn.calc_grid_count(1, 4), 1)
  luaunit.assert_equals(fn.calc_grid_count(16, 4), 16)
  luaunit.assert_equals(fn.calc_grid_count(1, 5), 17)
  luaunit.assert_equals(fn.calc_grid_count(16, 7), 64)
  luaunit.assert_equals(fn.calc_grid_count(1, 1), -47) -- characterisation: no bounds check
  for y = 4, 7 do
    for x = 1, 16 do
      luaunit.assert_equals(fn.calc_grid_count(x, y), (y - 4) * 16 + x)
    end
  end
end

function test_fnx_shift_table_left_and_right_rotate_in_place()
  local t = {1, 2, 3}
  luaunit.assert_is(fn.shift_table_left(t), t)
  luaunit.assert_equals(t, {2, 3, 1})
  luaunit.assert_is(fn.shift_table_right(t), t)
  luaunit.assert_equals(t, {1, 2, 3})
  luaunit.assert_equals(fn.shift_table_right({1, 2, 3}), {3, 1, 2})
  luaunit.assert_equals(fn.shift_table_left({7}), {7})
  luaunit.assert_equals(fn.shift_table_right({7}), {7})
  luaunit.assert_equals(fn.shift_table_left({}), {})
  luaunit.assert_equals(fn.shift_table_right({}), {})
end

function test_fnx_rotate_table_left_returns_new_table_and_consumes_input_head()
  local t = {1, 2, 3}
  local result = fn.rotate_table_left(t)
  luaunit.assert_equals(result, {2, 3, 1})
  luaunit.assert_not_is(result, t)
  -- characterisation: the input loses its first element (its only caller,
  -- quantiser.lua:306, passes a deep copy, so this is harmless there).
  luaunit.assert_equals(t, {2, 3})
  luaunit.assert_equals(fn.rotate_table_left({9}), {9})
  luaunit.assert_equals(fn.rotate_table_left({}), {})
end

function test_fnx_transpose_scale_returns_new_offset_table()
  local scale = {0, 2, 4}
  local result = fn.transpose_scale(scale, 3)
  luaunit.assert_equals(result, {3, 5, 7})
  luaunit.assert_equals(scale, {0, 2, 4})
  luaunit.assert_not_is(result, scale)
  luaunit.assert_equals(fn.transpose_scale({0, 12}, -12), {-12, 0})
  luaunit.assert_equals(fn.transpose_scale({}, 5), {})
end

function test_fnx_signed_inv_mod()
  luaunit.assert_equals(fn.signed_inv_mod(5, 0), 0)
  luaunit.assert_equals(fn.signed_inv_mod(-5, 0), 0)
  luaunit.assert_equals(fn.signed_inv_mod(5, 3), 1)
  luaunit.assert_equals(fn.signed_inv_mod(-5, 3), -2)
  luaunit.assert_equals(fn.signed_inv_mod(1, 3), 2)
  luaunit.assert_equals(fn.signed_inv_mod(-1, 3), -1)
  -- characterisation: exact multiples (including 0) return +/-b, never 0.
  luaunit.assert_equals(fn.signed_inv_mod(6, 3), 3)
  luaunit.assert_equals(fn.signed_inv_mod(0, 3), 3)
  luaunit.assert_equals(fn.signed_inv_mod(-3, 3), -3)
end

function test_fnx_constrain_argument_order_is_min_max_value()
  luaunit.assert_equals(fn.constrain(1, 10, 0), 1)
  luaunit.assert_equals(fn.constrain(1, 10, 1), 1)
  luaunit.assert_equals(fn.constrain(1, 10, 5), 5)
  luaunit.assert_equals(fn.constrain(1, 10, 10), 10)
  luaunit.assert_equals(fn.constrain(1, 10, 11), 10)
  luaunit.assert_equals(fn.constrain(-5, -1, -3.5), -3.5)
end

function test_fnx_average_table_values_rounds_half_up()
  luaunit.assert_nil(fn.average_table_values({}))
  luaunit.assert_equals(fn.average_table_values({4}), 4)
  luaunit.assert_equals(fn.average_table_values({1, 2}), 2)
  luaunit.assert_equals(fn.average_table_values({1, 2, 3, 4}), 3)
  luaunit.assert_equals(fn.average_table_values({1, 1, 2}), 1)
  luaunit.assert_equals(fn.average_table_values({a = 2, b = 4}), 3)
  luaunit.assert_equals(fn.average_table_values({-1, -2}), -1)
end

function test_fnx_clean_number_integers_two_decimals_and_zero()
  luaunit.assert_equals(fn.clean_number(3.0), 3)
  luaunit.assert_equals(math.type(fn.clean_number(3.0)), "integer")
  luaunit.assert_equals(math.type(fn.clean_number(3)), "integer")
  luaunit.assert_equals(fn.clean_number(-7.0), -7)
  luaunit.assert_equals(fn.clean_number(1.234), 1.23)
  luaunit.assert_equals(fn.clean_number(0.005), 0.01)
  luaunit.assert_equals(math.type(fn.clean_number(0.01)), "float")
  luaunit.assert_equals(fn.clean_number(-1.5), -1.5)
  luaunit.assert_equals(fn.clean_number(-0.5), -0.5)
  luaunit.assert_equals(fn.clean_number(0.001), 0)
  luaunit.assert_equals(math.type(fn.clean_number(0.001)), "integer")
  luaunit.assert_equals(math.type(fn.clean_number(-0.001)), "integer")
end

function test_fnx_get_param_type_from_id_all_nine_types()
  local expected = {"number", "option", "control", "file", "taper", "trigger", "group", "text", "binary"}
  for id, name in ipairs(expected) do
    luaunit.assert_equals(fn.get_param_type_from_id(id), name)
  end
  luaunit.assert_nil(fn.get_param_type_from_id(0))
  luaunit.assert_nil(fn.get_param_type_from_id(10))
end

function test_fnx_get_param_id_from_stock_id_all_fourteen_mappings()
  local expected = {
    fixed_note = 2, quantised_fixed_note = 3, bipolar_random_note = 4, random_velocity = 5,
    trig_probability = 6, twos_random_note = 7, chord_strum = 8, chord_arp = 9,
    chord_spread = 10, chord_acceleration = 11, chord_velocity_modifier = 12,
    chord_strum_pattern = 13, mute_root_note = 14, fully_quantise_mask = 15,
  }
  for stock_id, index in pairs(expected) do
    luaunit.assert_equals(fn.get_param_id_from_stock_id(stock_id, 3), "midi_device_params_channel_3_" .. index)
  end
  luaunit.assert_equals(fn.get_param_id_from_stock_id("chord_arp", 16), "midi_device_params_channel_16_9")
  -- characterisation: an unknown stock id raises from string.format.
  luaunit.assert_str_contains(error_of(fn.get_param_id_from_stock_id, "unknown", 1), "bad argument #1 to 'format'")
end

function test_fnx_generate_id_is_a_hex_address_string()
  local id = fn.generate_id()
  luaunit.assert_equals(type(id), "string")
  luaunit.assert_str_matches(id, "0x%x+") -- characterisation (Lua 5.3 on Linux)
end

-- random helpers (README.md:789 and README.md:793) ----------------------------

local function with_random(returns, body)
  local received = {}
  local stub = function(min, max)
    table.insert(received, {min, max})
    return returns(min, max)
  end
  with_overrides({{_G, "random", stub}}, function() body(received) end)
end

function test_fnx_transform_random_value_below_one_is_zero_without_drawing()
  with_random(function() error("random must not be drawn") end, function(received)
    luaunit.assert_equals(fn.transform_random_value(0), 0)
    luaunit.assert_equals(fn.transform_random_value(0.5), 0)
    luaunit.assert_equals(fn.transform_random_value(-3), 0)
    luaunit.assert_equals(received, {})
  end)
end

function test_fnx_transform_random_value_range_per_readme()
  -- README.md:789: 1 -> {0,1}; 2 -> {-1,0,1}; 3 -> {-1..2}; 4 -> {-2..2}.
  local ranges = {[1] = {0, 1}, [2] = {-1, 1}, [3] = {-1, 2}, [4] = {-2, 2}, [5] = {-2, 3}}
  for n = 1, 5 do
    with_random(function(min, max) return max end, function(received)
      luaunit.assert_equals(fn.transform_random_value(n), ranges[n][2])
      luaunit.assert_equals(received, {ranges[n]})
    end)
    with_random(function(min, max) return min end, function()
      luaunit.assert_equals(fn.transform_random_value(n), ranges[n][1])
    end)
  end
end

function test_fnx_transform_twos_random_value_below_one_is_zero_without_drawing()
  with_random(function() error("random must not be drawn") end, function(received)
    luaunit.assert_equals(fn.transform_twos_random_value(0), 0)
    luaunit.assert_equals(fn.transform_twos_random_value(0.9), 0)
    luaunit.assert_equals(received, {})
  end)
end

function test_fnx_transform_twos_random_value_even_offsets_per_readme()
  -- README.md:793: 1 -> {0,2}; 2 -> {-2,0,2}; 3 -> {-2,0,2,4}; 4 -> {-4..4 by 2}.
  local expected = {[1] = {0, 2}, [2] = {-2, 2}, [3] = {-2, 4}, [4] = {-4, 4}}
  for n = 1, 4 do
    local outputs = {}
    for draw = 0, n do
      with_random(function() return draw end, function(received)
        table.insert(outputs, fn.transform_twos_random_value(n))
        luaunit.assert_equals(received, {{0, n}})
      end)
    end
    luaunit.assert_equals(outputs[1], expected[n][1])
    luaunit.assert_equals(outputs[#outputs], expected[n][2])
    for i = 2, #outputs do
      luaunit.assert_equals(outputs[i] - outputs[i - 1], 2)
    end
  end
end

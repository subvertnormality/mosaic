-- Unit tests for the norns-screen components in lib/ui_components/.
-- Drawing is pinned by replacing the `screen` global with a recorder and
-- asserting the exact ordered calls with every argument each call received.
-- fn.dirty_screen, metro, clock, tooltip, program, sequencer and grid_abstraction
-- are replaced with recorders where a component talks to them; every replaced
-- global or field is restored even when the test body fails.
-- Assertions not backed by README.md are marked "-- characterisation".

local NIL = {}

local function swap_fields(target, overrides)
  local saved = {}
  for name, value in pairs(overrides) do
    saved[name] = {rawget(target, name)}
    if value == NIL then value = nil end
    rawset(target, name, value)
  end
  return function()
    for name, box in pairs(saved) do rawset(target, name, box[1]) end
  end
end

-- overrides: list of {table, {field = value, ...}}; NIL installs nil.
local function with_overrides(overrides, body)
  local restores = {}
  for _, pair in ipairs(overrides) do restores[#restores + 1] = swap_fields(pair[1], pair[2]) end
  local ok, err = pcall(body)
  for i = #restores, 1, -1 do restores[i]() end
  if not ok then error(err, 0) end
end

local SCREEN_FUNCTIONS = {"level", "move", "text", "text_trim", "font_size", "font_face", "rect", "fill"}

local function recording_screen(log)
  local stub = {}
  for _, name in ipairs(SCREEN_FUNCTIONS) do
    stub[name] = function(...) log[#log + 1] = {name, ...} end
  end
  return stub
end

local function dirty_recorder(log)
  return function(...) log[#log + 1] = {"dirty", ...} end
end

-- Runs body(log) with screen and fn.dirty_screen recording into one ordered log.
local function recorded(body, extra_globals)
  local log = {}
  local globals = {screen = recording_screen(log)}
  for name, value in pairs(extra_globals or {}) do globals[name] = value end
  with_overrides({{_G, globals}, {fn, {dirty_screen = dirty_recorder(log)}}}, function() body(log) end)
  return log
end

local function draw_log(component)
  return recorded(function() component:draw() end)
end

local value_selector = include("mosaic/lib/ui_components/value_selector")
local list_selector = include("mosaic/lib/ui_components/list_selector")
local vertical_scroll_selector = include("mosaic/lib/ui_components/vertical_scroll_selector")
local control_scroll_selector = include("mosaic/lib/ui_components/control_scroll_selector")
local dial = include("mosaic/lib/ui_components/dial")
local memory_history_navigator = include("mosaic/lib/ui_components/memory_history_navigator")
local page = include("mosaic/lib/ui_components/page")
local pages_component = include("mosaic/lib/ui_components/pages")

-- helpers leave no trace ------------------------------------------------------

function test_uicomp_helpers_restore_screen_and_dirty_screen_even_when_the_body_fails()
  local before_screen = rawget(_G, "screen")
  local before_dirty = fn.dirty_screen
  local before_tooltip = rawget(_G, "tooltip")
  local ok = pcall(recorded, function() error("boom") end, {tooltip = {}})
  luaunit.assert_false(ok)
  luaunit.assert_is(rawget(_G, "screen"), before_screen)
  luaunit.assert_is(fn.dirty_screen, before_dirty)
  luaunit.assert_is(rawget(_G, "tooltip"), before_tooltip)
end

-- value_selector --------------------------------------------------------------

function test_uicomp_value_selector_new_defaults()
  local v = value_selector:new(5, 10, "Length", 1, 64)
  luaunit.assert_equals(v.x, 5)
  luaunit.assert_equals(v.y, 10)
  luaunit.assert_equals(v.name, "Length")
  luaunit.assert_equals(v.min, 1)
  luaunit.assert_equals(v.max, 64)
  luaunit.assert_equals(v:get_value(), 0) -- characterisation: starts below min
  luaunit.assert_false(v:is_selected())
  luaunit.assert_equals(v.view_transform_func(7), 7)
end

function test_uicomp_value_selector_increment_and_decrement_clamp_and_mark_dirty()
  local v = value_selector:new(5, 10, "Length", 1, 3)
  local log = recorded(function()
    v:set_value(2)
    v:increment()
    v:increment()
  end)
  luaunit.assert_equals(v:get_value(), 3)
  luaunit.assert_equals(log, {{"dirty", true}, {"dirty", true}, {"dirty", true}})
  log = recorded(function()
    v:decrement()
    luaunit.assert_equals(v:get_value(), 2)
    v:decrement()
    luaunit.assert_equals(v:get_value(), 1)
    v:decrement()
    luaunit.assert_equals(v:get_value(), 1)
  end)
  luaunit.assert_equals(log, {{"dirty", true}, {"dirty", true}, {"dirty", true}})
  local fresh = value_selector:new(0, 0, "n", 1, 3)
  recorded(function() fresh:increment() end)
  luaunit.assert_equals(fresh:get_value(), 1)
end

function test_uicomp_value_selector_set_value_does_not_clamp()
  local v = value_selector:new(5, 10, "Length", 1, 3)
  local log = recorded(function() v:set_value(99) end)
  luaunit.assert_equals(v:get_value(), 99) -- characterisation
  luaunit.assert_equals(log, {{"dirty", true}})
end

function test_uicomp_value_selector_select_and_deselect()
  local v = value_selector:new(5, 10, "Length", 1, 3)
  local log = recorded(function() v:select() end)
  luaunit.assert_true(v:is_selected())
  luaunit.assert_equals(log, {{"dirty", true}})
  log = recorded(function() v:deselect() end)
  luaunit.assert_false(v:is_selected())
  luaunit.assert_equals(log, {{"dirty", true}})
end

function test_uicomp_value_selector_draw_name_and_value_at_selection_level()
  local v = value_selector:new(5, 10, "Length", 1, 64)
  luaunit.assert_equals(draw_log(v), {
    {"level", 1}, {"move", 5, 10}, {"font_size", 8}, {"text", "Length"},
    {"move", 5, 18}, {"text", 0}
  })
  recorded(function() v:select() v:set_value(12) end)
  luaunit.assert_equals(draw_log(v), {
    {"level", 15}, {"move", 5, 10}, {"font_size", 8}, {"text", "Length"},
    {"move", 5, 18}, {"text", 12}
  })
end

function test_uicomp_value_selector_draw_applies_view_transform_unless_value_is_nil()
  local v = value_selector:new(0, 20, "Swing", 0, 100)
  local received = {}
  v:set_view_transform_func(function(value) received[#received + 1] = value return value .. "%" end)
  recorded(function() v:set_value(40) end)
  luaunit.assert_equals(draw_log(v)[6], {"text", "40%"})
  luaunit.assert_equals(received, {40})
  recorded(function() v:set_value(nil) end)
  luaunit.assert_equals(draw_log(v)[6], {"text", "0"}) -- characterisation
  luaunit.assert_equals(received, {40})
end

function test_uicomp_value_selector_set_name_ignores_its_argument()
  -- characterisation (suspected defect: set_name() takes no parameter and
  -- assigns the global `name`, so the new name is discarded).
  local v = value_selector:new(0, 0, "Old", 0, 1)
  local log
  with_overrides({{_G, {name = NIL}}}, function()
    log = recorded(function() v:set_name("New") end)
  end)
  luaunit.assert_nil(v.name)
  luaunit.assert_equals(log, {{"dirty", true}})
end

-- list_selector ---------------------------------------------------------------

local function sample_list()
  return {{name = "Alpha"}, {name = "Beta"}, {name = "Gamma"}}
end

function test_uicomp_list_selector_new_selects_first_item()
  local list = sample_list()
  local l = list_selector:new(3, 30, "Mode", list)
  luaunit.assert_equals(l.name, "Mode")
  luaunit.assert_is(l.list, list)
  luaunit.assert_equals(l.selected_value, 1)
  luaunit.assert_false(l:is_selected())
  luaunit.assert_is(l:get_selected(), list[1])
end

function test_uicomp_list_selector_increment_and_decrement_clamp_to_list()
  local list = sample_list()
  local l = list_selector:new(3, 30, "Mode", list)
  local log = recorded(function()
    l:increment()
    l:increment()
    l:increment()
  end)
  luaunit.assert_is(l:get_selected(), list[3])
  luaunit.assert_equals(l.selected_value, 3)
  luaunit.assert_equals(log, {{"dirty", true}, {"dirty", true}, {"dirty", true}})
  log = recorded(function()
    l:decrement()
    luaunit.assert_equals(l.selected_value, 2)
    l:decrement()
    l:decrement()
  end)
  luaunit.assert_equals(l.selected_value, 1)
  luaunit.assert_equals(log, {{"dirty", true}, {"dirty", true}, {"dirty", true}})
end

function test_uicomp_list_selector_set_selected_value_set_list_and_selection()
  local l = list_selector:new(3, 30, "Mode", sample_list())
  local replacement = {{name = "Solo"}}
  local log = recorded(function()
    l:set_selected_value(3)
    l:set_list(replacement)
    l:select()
  end)
  luaunit.assert_equals(l.selected_value, 3)
  luaunit.assert_is(l.list, replacement)
  luaunit.assert_true(l:is_selected())
  luaunit.assert_equals(log, {{"dirty", true}, {"dirty", true}, {"dirty", true}})
  log = recorded(function() l:deselect() end)
  luaunit.assert_false(l:is_selected())
  luaunit.assert_equals(log, {{"dirty", true}})
end

function test_uicomp_list_selector_draw_name_and_selected_item_name()
  local l = list_selector:new(3, 30, "Mode", sample_list())
  luaunit.assert_equals(draw_log(l), {
    {"level", 1}, {"move", 3, 30}, {"font_size", 8}, {"text", "Mode"},
    {"move", 3, 38}, {"text", "Alpha"}, {"font_size", 8}
  })
  recorded(function() l:select() l:increment() end)
  luaunit.assert_equals(draw_log(l), {
    {"level", 15}, {"move", 3, 30}, {"font_size", 8}, {"text", "Mode"},
    {"move", 3, 38}, {"text", "Beta"}, {"font_size", 8}
  })
end

function test_uicomp_list_selector_set_name_ignores_its_argument()
  -- characterisation (suspected defect: set_name() assigns the global `name`).
  local l = list_selector:new(3, 30, "Mode", sample_list())
  local log
  with_overrides({{_G, {name = NIL}}}, function()
    log = recorded(function() l:set_name("Other") end)
  end)
  luaunit.assert_nil(l.name)
  luaunit.assert_equals(log, {{"dirty", true}})
end

-- vertical_scroll_selector ----------------------------------------------------

local function scroll_items()
  return {"one", {name = "Two"}, "three", {name = "Four"}}
end

function test_uicomp_vertical_scroll_selector_new_and_accessors()
  local items = scroll_items()
  local s = vertical_scroll_selector:new(10, 20, "Device", items)
  luaunit.assert_equals(s.name, "Device")
  luaunit.assert_is(s:get_items(), items)
  luaunit.assert_equals(s:get_selected_index(), 1)
  luaunit.assert_equals(s:get_selected_item(), "one")
  luaunit.assert_nil(s:get_meta_item())
  luaunit.assert_false(s:is_selected())
  s:set_selected_item(2)
  luaunit.assert_is(s:get_selected_item(), items[2])
  local meta = {"m"}
  s:set_meta_item(meta)
  luaunit.assert_is(s:get_meta_item(), meta)
  local other = {"x"}
  s:set_items(other)
  luaunit.assert_is(s:get_items(), other)
end

function test_uicomp_vertical_scroll_selector_scroll_down_and_up_clamp_but_always_dirty()
  local s = vertical_scroll_selector:new(10, 20, "Device", scroll_items())
  local log = recorded(function()
    s:scroll_up()
    luaunit.assert_equals(s:get_selected_index(), 1)
    s:scroll_down()
    s:scroll_down()
    s:scroll_down()
    luaunit.assert_equals(s:get_selected_index(), 4)
    s:scroll_down()
    luaunit.assert_equals(s:get_selected_index(), 4)
    s:scroll_up()
    luaunit.assert_equals(s:get_selected_index(), 3)
  end)
  luaunit.assert_equals(#log, 6)
  for _, entry in ipairs(log) do luaunit.assert_equals(entry, {"dirty", true}) end
end

function test_uicomp_vertical_scroll_selector_scroll_by_direction_steps_one_at_a_time()
  local s = vertical_scroll_selector:new(10, 20, "Device", scroll_items())
  local log = recorded(function() s:scroll(2) end)
  luaunit.assert_equals(s:get_selected_index(), 3)
  luaunit.assert_equals(log, {{"dirty", true}, {"dirty", true}})
  log = recorded(function() s:scroll(-5) end)
  luaunit.assert_equals(s:get_selected_index(), 1)
  luaunit.assert_equals(#log, 5)
  log = recorded(function() s:scroll(0) end)
  luaunit.assert_equals(s:get_selected_index(), 1)
  luaunit.assert_equals(log, {})
  recorded(function() s:scroll(10) end)
  luaunit.assert_equals(s:get_selected_index(), 4)
  log = recorded(function() s:scroll(-1) end)
  luaunit.assert_equals(s:get_selected_index(), 3)
  luaunit.assert_equals(log, {{"dirty", true}})
  log = recorded(function() s:scroll(1) end)
  luaunit.assert_equals(s:get_selected_index(), 4)
  luaunit.assert_equals(log, {{"dirty", true}})
end

function test_uicomp_vertical_scroll_selector_select_and_deselect()
  local s = vertical_scroll_selector:new(10, 20, "Device", scroll_items())
  local log = recorded(function() s:select() end)
  luaunit.assert_true(s:is_selected())
  luaunit.assert_equals(log, {{"dirty", true}})
  log = recorded(function() s:deselect() end)
  luaunit.assert_false(s:is_selected())
  luaunit.assert_equals(log, {{"dirty", true}})
end

function test_uicomp_vertical_scroll_selector_draw_previous_current_next()
  local s = vertical_scroll_selector:new(10, 20, "Device", scroll_items())
  s:set_selected_item(2)
  recorded(function() s:select() end)
  luaunit.assert_equals(draw_log(s), {
    {"move", 10, 20}, {"level", 1}, {"text", "one", 12},
    {"move", 15, 30}, {"level", 15}, {"text", "Two", 12},
    {"move", 10, 40}, {"level", 1}, {"text", "three", 12}
  })
  s:set_selected_item(3)
  recorded(function() s:deselect() end)
  luaunit.assert_equals(draw_log(s), {
    {"move", 10, 20}, {"level", 1}, {"text", "Two", 12},
    {"move", 15, 30}, {"level", 5}, {"text", "three", 12},
    {"move", 10, 40}, {"level", 1}, {"text", "Four", 12}
  })
end

function test_uicomp_vertical_scroll_selector_draw_at_the_ends_and_without_items()
  local s = vertical_scroll_selector:new(10, 20, "Device", scroll_items())
  luaunit.assert_equals(draw_log(s), {
    {"move", 10, 20},
    {"move", 15, 30}, {"level", 5}, {"text", "one", 12},
    {"move", 10, 40}, {"level", 1}, {"text", "Two", 12}
  })
  s:set_selected_item(4)
  luaunit.assert_equals(draw_log(s), {
    {"move", 10, 20}, {"level", 1}, {"text", "three", 12},
    {"move", 15, 30}, {"level", 5}, {"text", "Four", 12},
    {"move", 10, 40}
  })
  s:set_selected_item(9) -- characterisation: an index past the list draws no text
  luaunit.assert_equals(draw_log(s), {{"move", 10, 20}, {"move", 15, 30}, {"move", 10, 40}})
  s:set_items(nil)
  luaunit.assert_equals(draw_log(s), {})
end

-- control_scroll_selector -----------------------------------------------------

local function fake_controls(log, count)
  local items = {}
  for i = 1, count do
    items[i] = {
      select = function(self) log[#log + 1] = {"select", i, self == items[i]} end,
      deselect = function(self) log[#log + 1] = {"deselect", i, self == items[i]} end,
      draw = function(self) log[#log + 1] = {"draw", i, self == items[i]} end
    }
  end
  return items
end

function test_uicomp_control_scroll_selector_new_and_queries()
  local log = {}
  local items = fake_controls(log, 3)
  local c = control_scroll_selector:new(1, 2, items)
  luaunit.assert_equals(c.x, 1)
  luaunit.assert_equals(c.y, 2)
  luaunit.assert_is(c:get_items(), items)
  luaunit.assert_equals(c:get_selected_index(), 1)
  luaunit.assert_is(c:get_selected_item(), items[1])
  luaunit.assert_equals(log, {})
end

function test_uicomp_control_scroll_selector_select_and_draw_delegate_to_items()
  local log = {}
  local c = control_scroll_selector:new(1, 2, fake_controls(log, 3))
  c:select(2)
  c:draw()
  luaunit.assert_equals(log, {
    {"select", 2, true},
    {"draw", 1, true}, {"draw", 2, true}, {"draw", 3, true}
  })
end

function test_uicomp_control_scroll_selector_scroll_next_deselects_all_then_selects_one()
  local log = recorded(function(log)
    local c = control_scroll_selector:new(1, 2, fake_controls(log, 3))
    c:scroll_next()
    luaunit.assert_equals(c:get_selected_index(), 2)
    c:scroll_next()
    c:scroll_next() -- clamped at the last item
    luaunit.assert_equals(c:get_selected_index(), 3)
  end)
  local round = function(selected)
    return {{"deselect", 1, true}, {"deselect", 2, true}, {"deselect", 3, true}, {"select", selected, true}, {"dirty", true}}
  end
  local expected = {}
  for _, selected in ipairs({2, 3, 3}) do
    for _, entry in ipairs(round(selected)) do expected[#expected + 1] = entry end
  end
  luaunit.assert_equals(log, expected)
end

function test_uicomp_control_scroll_selector_scroll_previous_clamps_at_first()
  local log = recorded(function(log)
    local c = control_scroll_selector:new(1, 2, fake_controls(log, 2))
    c:scroll_previous()
    luaunit.assert_equals(c:get_selected_index(), 1)
    c:scroll_next()
    c:scroll_previous()
    luaunit.assert_equals(c:get_selected_index(), 1)
  end)
  luaunit.assert_equals(log, {
    {"deselect", 1, true}, {"deselect", 2, true}, {"select", 1, true}, {"dirty", true},
    {"deselect", 1, true}, {"deselect", 2, true}, {"select", 2, true}, {"dirty", true},
    {"deselect", 1, true}, {"deselect", 2, true}, {"select", 1, true}, {"dirty", true}
  })
end

function test_uicomp_control_scroll_selector_set_items_marks_dirty()
  local c = control_scroll_selector:new(1, 2, {})
  local replacement = fake_controls({}, 1)
  local log = recorded(function() c:set_items(replacement) end)
  luaunit.assert_is(c:get_items(), replacement)
  luaunit.assert_equals(log, {{"dirty", true}})
end

function test_uicomp_control_scroll_selector_set_selected_item_ignores_its_argument()
  -- characterisation (suspected defect: set_selected_item(item) never uses
  -- `item`; it re-selects the current index and leaves the index unchanged).
  local log = recorded(function(log)
    local c = control_scroll_selector:new(1, 2, fake_controls(log, 3))
    c:set_selected_item(3)
    luaunit.assert_equals(c:get_selected_index(), 1)
  end)
  luaunit.assert_equals(log, {{"select", 1, true}, {"dirty", true}})
end

-- dial ------------------------------------------------------------------------

local function new_dial()
  return dial:new(10, 20, "Param 1", "param_1", "cutoff freq", "low pass")
end

-- The header and footer every dial draw emits around its value section.
local function dial_frame(level, middle)
  local expected = {{"level", level}, {"move", 10, 20}, {"text_trim", "Cutoff Freq", 24}}
  for _, entry in ipairs(middle) do expected[#expected + 1] = entry end
  expected[#expected + 1] = {"move", 10, 34}
  -- characterisation: fn.title_case returns gsub's two results and both reach
  -- screen.text for the bottom label.
  expected[#expected + 1] = {"text", "Low Pass", 2}
  return expected
end

local function bar(rects)
  local expected = {}
  for _, r in ipairs(rects) do
    expected[#expected + 1] = {"rect", r[1], 23, r[2], 4}
    expected[#expected + 1] = {"fill"}
  end
  return expected
end

function test_uicomp_dial_new_defaults()
  local d = new_dial()
  luaunit.assert_equals(d:get_name(), "Param 1")
  luaunit.assert_equals(d:get_value(), -1)
  luaunit.assert_equals(d.top_label, "cutoff freq")
  luaunit.assert_equals(d.bottom_label, "low pass")
  luaunit.assert_false(d:is_selected())
  luaunit.assert_nil(d.min_value)
  luaunit.assert_nil(d.max_value)
  luaunit.assert_equals(d.off_value, -1)
  luaunit.assert_nil(d.ui_labels)
  luaunit.assert_false(d.display_value)
  luaunit.assert_nil(d.display_value_clock)
end

function test_uicomp_dial_get_id_is_always_nil()
  -- characterisation (suspected defect: new() accepts an id but never stores
  -- it, so get_id() returns nil).
  luaunit.assert_nil(new_dial():get_id())
end

function test_uicomp_dial_draw_shows_x_without_range_and_calls_display_modifier()
  local d = new_dial()
  local log = {}
  d:set_display_modifier(function(x, y) log[#log + 1] = {"modifier", x, y} end)
  with_overrides({{_G, {screen = recording_screen(log)}}}, function() d:draw() end)
  local expected = dial_frame(1, {{"move", 10, 27}, {"text", "X"}})
  table.insert(expected, 2, {"modifier", 10, 20})
  luaunit.assert_equals(log, expected)
  recorded(function() d:select() end)
  d:set_display_modifier(function() end)
  luaunit.assert_equals(draw_log(d), dial_frame(15, {{"move", 10, 27}, {"text", "X"}}))
end

function test_uicomp_dial_draw_shows_x_at_off_value_inside_range()
  local d = new_dial()
  d:set_min_value(0)
  d:set_max_value(127)
  d:set_off_value(0)
  recorded(function() d:set_value(0) end)
  luaunit.assert_equals(draw_log(d), dial_frame(1, {{"move", 10, 27}, {"text", "X"}}))
  recorded(function() d:set_value(5) end)
  d:set_min_value(nil) -- a missing min also shows X
  luaunit.assert_equals(draw_log(d), dial_frame(1, {{"move", 10, 27}, {"text", "X"}}))
  d:set_min_value(0)
  d.value = nil -- a nil value shows X without clamping
  luaunit.assert_equals(draw_log(d), dial_frame(1, {{"move", 10, 27}, {"text", "X"}}))
  luaunit.assert_nil(d:get_value())
end

function test_uicomp_dial_draw_shows_x_at_off_value_below_min()
  -- An off_value below min (off -1, min 0) is Off, not the minimum: draw() shows "X" and
  -- leaves the dial's value alone (human decision S20; bugs.json dial-off-display,
  -- M-PARAM-DIAL-OFF-001). This test pinned the old empty bar and stored 0.
  local d = new_dial()
  d:set_min_value(0)
  d:set_max_value(127)
  recorded(function() d:set_value(nil) end)
  luaunit.assert_equals(d:get_value(), -1)
  luaunit.assert_equals(draw_log(d), dial_frame(1, {{"move", 10, 27}, {"text", "X"}}))
  luaunit.assert_equals(d:get_value(), -1)
  -- The 2-second numeric read-out shows "X" at Off too, not the clamped "0".
  d.display_value = true
  luaunit.assert_equals(draw_log(d), dial_frame(1, {{"move", 10, 27}, {"text", "X"}}))
  d.display_value = false
  -- min 0 itself is a value, drawn as an empty bar.
  recorded(function() d:set_value(0) end)
  luaunit.assert_equals(draw_log(d), dial_frame(1, {}))
end

function test_uicomp_dial_draw_clamps_value_above_max()
  local d = new_dial()
  d:set_min_value(0)
  d:set_max_value(10)
  d.value = 15 -- increment() does not clamp; draw() clamps its display copy
  local rects = {}
  for i = 1, 20 do rects[i] = {10 + (i - 1) * (19 / 20), 19 / 20} end
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(rects))) -- characterisation
  -- draw() no longer writes the clamped copy back (bugs.json dial-off-display).
  luaunit.assert_equals(d:get_value(), 15)
end

function test_uicomp_dial_draw_positive_range_bar_segments()
  local d = new_dial()
  d:set_min_value(0)
  d:set_max_value(10)
  recorded(function() d:set_value(5) end)
  local w = 19 / 20
  local rects = {}
  for i = 1, 10 do rects[i] = {10 + (i - 1) * w, w} end
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(rects))) -- characterisation
  recorded(function() d:set_value(0) end)
  luaunit.assert_equals(draw_log(d), dial_frame(1, {})) -- characterisation
end

function test_uicomp_dial_draw_positive_range_partial_segment()
  local d = new_dial()
  d:set_min_value(0)
  d:set_max_value(3)
  recorded(function() d:set_value(1) end)
  local w = 19 / 20
  local fraction = 1 / 3
  local partial = fraction * 20 - 6
  local rects = {}
  for i = 1, 6 do rects[i] = {10 + (i - 1) * w, w} end
  rects[7] = {10 + 6 * w, w * partial}
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(rects))) -- characterisation
end

function test_uicomp_dial_draw_bipolar_range_fills_from_centre()
  local d = new_dial()
  d:set_min_value(-10)
  d:set_max_value(10)
  d:set_off_value(0)
  local w = 19 / 20
  local centre = 10 + 19 / 2
  recorded(function() d:set_value(5) end)
  local right = {}
  for i = 1, 5 do right[i] = {centre + (i - 1) * w, w} end
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(right))) -- characterisation
  recorded(function() d:set_value(-5) end)
  local left = {}
  for i = 1, 5 do left[i] = {centre - i * w, w} end
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(left))) -- characterisation
  recorded(function() d:set_value(-10) end)
  local full_left = {}
  for i = 1, 10 do full_left[i] = {centre - i * w, w} end
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(full_left))) -- characterisation
end

function test_uicomp_dial_draw_bipolar_range_partial_segments()
  local d = new_dial()
  d:set_min_value(-3)
  d:set_max_value(3)
  d:set_off_value(0)
  local w = 19 / 20
  local centre = 10 + 19 / 2
  local fraction = 1 / 3
  local partial = fraction * 10 - 3
  recorded(function() d:set_value(1) end)
  local right = {}
  for i = 1, 3 do right[i] = {centre + (i - 1) * w, w} end
  right[4] = {centre + 3 * w, w * partial}
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(right))) -- characterisation
  recorded(function() d:set_value(-1) end)
  local left = {}
  for i = 1, 3 do left[i] = {centre - i * w, w} end
  local fill = w * partial
  left[4] = {centre - 4 * w + (w - fill), fill}
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(left))) -- characterisation
end

function test_uicomp_dial_draw_ui_labels_take_precedence_over_value_display()
  local d = new_dial()
  d:set_min_value(1)
  d:set_max_value(3)
  d:set_ui_labels({"lo", "mid"})
  recorded(function() d:set_value(2) end)
  d.display_value = true
  luaunit.assert_equals(draw_log(d), dial_frame(1, {{"move", 10, 27}, {"text", "mid", 24}}))
  recorded(function() d:set_value(3) end)
  luaunit.assert_equals(draw_log(d), dial_frame(1, {{"move", 10, 27}, {"text", "", 24}}))
  d:set_min_value(0)
  recorded(function() d:set_value(0) end)
  luaunit.assert_equals(draw_log(d), dial_frame(1, {{"move", 10, 27}, {"text", "lo", 24}}))
end

function test_uicomp_dial_draw_temporary_value_display_uses_clean_number()
  local d = new_dial()
  d:set_min_value(0)
  d:set_max_value(10)
  d.display_value = true
  recorded(function() d:set_value(2.456) end)
  luaunit.assert_equals(draw_log(d), dial_frame(1, {{"move", 10, 27}, {"text", 2.46}}))
  recorded(function() d:set_value(4.0) end)
  local log = draw_log(d)
  luaunit.assert_equals(log[5], {"text", 4})
  luaunit.assert_equals(math.type(log[5][2]), "integer")
end

function test_uicomp_dial_set_value_replaces_out_of_range_with_off_value()
  local d = new_dial()
  local log = recorded(function()
    d:set_value(1000)
    luaunit.assert_equals(d:get_value(), 1000) -- no range: stored verbatim
    d:set_min_value(0)
    d:set_max_value(10)
    d:set_value(nil)
    luaunit.assert_equals(d:get_value(), -1)
    d:set_value(10)
    luaunit.assert_equals(d:get_value(), 10)
    d:set_value(10.1)
    luaunit.assert_equals(d:get_value(), -1)
    d:set_value(0)
    luaunit.assert_equals(d:get_value(), 0)
    d:set_value(-0.5)
    luaunit.assert_equals(d:get_value(), -1)
    d:set_value(10 + 1e-11) -- within epsilon
    luaunit.assert_equals(d:get_value(), 10 + 1e-11)
    d:set_value(-1e-11)
    luaunit.assert_equals(d:get_value(), -1e-11)
    d:set_value(-1e-10) -- exactly min - epsilon is still in range
    luaunit.assert_equals(d:get_value(), -1e-10)
    d:set_value(10 + 1e-10)
    luaunit.assert_equals(d:get_value(), 10 + 1e-10)
    d:set_value(-5e-11)
    luaunit.assert_equals(d:get_value(), -5e-11)
    d:set_value(-5e-10)
    luaunit.assert_equals(d:get_value(), -1)
    d:set_off_value(-5)
    d:set_value(11)
    luaunit.assert_equals(d:get_value(), -5)
  end)
  luaunit.assert_equals(#log, 13)
  for _, entry in ipairs(log) do luaunit.assert_equals(entry, {"dirty", true}) end
end

function test_uicomp_dial_increment_decrement_labels_and_selection_mark_dirty()
  local d = new_dial()
  local log = recorded(function()
    d:increment()
    d:increment()
    d:decrement()
    d:set_top_label("res")
    d:set_bottom_label("q")
    d:select()
  end)
  luaunit.assert_equals(d:get_value(), 0)
  luaunit.assert_equals(d.top_label, "res")
  luaunit.assert_equals(d.bottom_label, "q")
  luaunit.assert_true(d:is_selected())
  luaunit.assert_equals(#log, 6)
  for _, entry in ipairs(log) do luaunit.assert_equals(entry, {"dirty", true}) end
  log = recorded(function() d:deselect() end)
  luaunit.assert_false(d:is_selected())
  luaunit.assert_equals(log, {{"dirty", true}})
end

function test_uicomp_dial_set_name_ignores_its_argument()
  -- characterisation (suspected defect: set_name() assigns the global `name`;
  -- channel_edit_page_ui_refreshers calls m_param:set_name(...)).
  local d = new_dial()
  local log
  with_overrides({{_G, {name = NIL}}}, function()
    log = recorded(function() d:set_name("Resonance") end)
  end)
  luaunit.assert_nil(d:get_name())
  luaunit.assert_equals(log, {{"dirty", true}})
end

function test_uicomp_dial_temp_display_value_restarts_its_clock_and_clears_after_two_seconds()
  local d = new_dial()
  local log, bodies, next_id = {}, {}, 0
  with_overrides({{clock, {
    run = function(body) next_id = next_id + 1 bodies[#bodies + 1] = body log[#log + 1] = {"run"} return "clock-" .. next_id end,
    cancel = function(id) log[#log + 1] = {"cancel", id} end,
    sleep = function(seconds) log[#log + 1] = {"sleep", seconds} end
  }}}, function()
    d:temp_display_value()
    luaunit.assert_true(d.display_value)
    luaunit.assert_equals(d.display_value_clock, "clock-1")
    d:temp_display_value()
    luaunit.assert_equals(d.display_value_clock, "clock-2")
    luaunit.assert_true(d.display_value)
    bodies[2]()
    luaunit.assert_false(d.display_value)
    luaunit.assert_nil(d.display_value_clock)
  end)
  luaunit.assert_equals(log, {{"run"}, {"cancel", "clock-1"}, {"run"}, {"sleep", 2}, {"cancel", "clock-2"}})
end

-- memory_history_navigator ----------------------------------------------------

local function navigator_header(level, current, max)
  return {
    {"level", level}, {"move", 2, 8}, {"font_size", 10}, {"text", current},
    {"move", 2, 20}, {"font_size", 8}, {"text", "of"},
    {"move", 2, 34}, {"font_size", 10}, {"text", max}
  }
end

local function event_entries(middle)
  local entries = {{"font_size", 5}, {"font_face", 60}}
  for _, entry in ipairs(middle) do entries[#entries + 1] = entry end
  entries[#entries + 1] = {"font_face", 1}
  entries[#entries + 1] = {"font_size", 8}
  return entries
end

local function concat_lists(...)
  local out = {}
  for _, list in ipairs({...}) do
    for _, entry in ipairs(list) do out[#out + 1] = entry end
  end
  return out
end

function test_uicomp_memory_history_navigator_new_and_indexes()
  local n = memory_history_navigator:new(2, 3, "History")
  luaunit.assert_equals(n.name, "History")
  luaunit.assert_equals(n:get_current_index(), 0)
  luaunit.assert_equals(n:get_max_index(), 0)
  luaunit.assert_false(n:is_selected())
  local log = recorded(function()
    n:set_current_index(4)
    n:set_max_index(9)
  end)
  luaunit.assert_equals(n:get_current_index(), 4)
  luaunit.assert_equals(n:get_max_index(), 9)
  luaunit.assert_equals(log, {{"dirty", true}, {"dirty", true}})
  recorded(function()
    n:set_current_index(nil)
    n:set_max_index(nil)
  end)
  luaunit.assert_equals(n:get_current_index(), 0)
  luaunit.assert_equals(n:get_max_index(), 0)
end

function test_uicomp_memory_history_navigator_select_and_deselect()
  local n = memory_history_navigator:new(2, 3, "History")
  local log = recorded(function() n:select() end)
  luaunit.assert_true(n:is_selected())
  luaunit.assert_equals(log, {{"dirty", true}})
  log = recorded(function() n:deselect() end)
  luaunit.assert_false(n:is_selected())
  luaunit.assert_equals(log, {{"dirty", true}})
end

function test_uicomp_memory_history_navigator_draw_header_without_events()
  local n = memory_history_navigator:new(2, 3, "History")
  n:set_event_state({})
  recorded(function() n:set_current_index(4) n:set_max_index(9) end)
  luaunit.assert_equals(draw_log(n), navigator_header(1, 4, 9))
  recorded(function() n:select() end)
  luaunit.assert_equals(draw_log(n), navigator_header(15, 4, 9))
end

function test_uicomp_memory_history_navigator_draw_event_glyphs_positions_and_levels()
  local n = memory_history_navigator:new(2, 3, "History")
  n:set_event_state({events = {
    {type = "note_mask", data = {event_data = {note = 30, velocity = 100}}},
    {type = "note_mask", data = {event_data = {note = -1, chord_degrees = {1, 3}}}},
    {type = "trig_lock"},
    {type = "note_mask", data = {event_data = {length = 2}}},
    {type = "note_mask", data = {event_data = {note = 45, velocity = 50}}},
    {type = "note_mask"},
    {type = "other"}
  }})
  -- characterisation: a note-less event takes the y of the nearest later note
  -- (60 when none follows); a trig lock takes the earliest note's y.
  luaunit.assert_equals(draw_log(n), concat_lists(
    navigator_header(1, 0, 0),
    event_entries({{"level", 13}, {"move", 117, 33}, {"text", "\u{286}"}}),
    event_entries({{"level", 15}, {"move", 112, 28}, {"text", "'"}}),
    event_entries({{"level", 15}, {"move", 107, 33}, {"text", "T"}}),
    event_entries({{"level", 15}, {"move", 102, 28}, {"text", "."}}),
    event_entries({{"level", 8}, {"move", 97, 28}, {"text", "\u{286}"}}),
    event_entries({{"level", 15}, {"move", 92, 23}}),
    event_entries({})
  ))
end

function test_uicomp_memory_history_navigator_empty_chord_degrees_fall_back_to_length()
  local n = memory_history_navigator:new(0, 0, "History")
  n:set_event_state({events = {
    {type = "note_mask", data = {event_data = {note = -1, chord_degrees = {}, length = 1, velocity = 0}}},
    {type = "note_mask", data = {event_data = {note = -1, chord_degrees = {}, velocity = 0}}},
    {type = "note_mask", data = {event_data = {note = -1, chord_degrees = {5}, velocity = 0}}}
  }})
  luaunit.assert_equals(draw_log(n), concat_lists(
    {
      {"level", 1}, {"move", 0, 5}, {"font_size", 10}, {"text", 0},
      {"move", 0, 17}, {"font_size", 8}, {"text", "of"},
      {"move", 0, 31}, {"font_size", 10}, {"text", 0}
    },
    event_entries({{"level", 3}, {"move", 115, 20}, {"text", "."}}),
    event_entries({{"level", 3}, {"move", 110, 20}}),
    event_entries({{"level", 3}, {"move", 105, 20}, {"text", "'"}})
  )) -- characterisation
end

function test_uicomp_memory_history_navigator_draws_at_most_fifteen_events()
  local n = memory_history_navigator:new(2, 3, "History")
  local events = {}
  for i = 1, 16 do
    events[i] = {type = "note_mask", data = {event_data = {note = 0, velocity = 0}}}
  end
  n:set_event_state({events = events})
  local expected = navigator_header(1, 0, 0)
  for i = 1, 15 do
    expected = concat_lists(expected, event_entries({{"level", 3}, {"move", 122 - i * 5, 43}, {"text", "\u{286}"}}))
  end
  luaunit.assert_equals(draw_log(n), expected) -- characterisation
end

-- tooltip ---------------------------------------------------------------------

-- Runs body(tooltip, log, callbacks) against a fresh tooltip module with metro,
-- screen and fn.dirty_screen recording into log.
local function with_tooltip(body)
  local tooltip = include("mosaic/lib/ui_components/tooltip")
  local log, callbacks, next_id = {}, {}, 30
  local fake_metro = {
    init = function(callback, time, count)
      next_id = next_id + 1
      local id = next_id
      callbacks[#callbacks + 1] = callback
      log[#log + 1] = {"init", time, count}
      return {
        id = id,
        start = function(self) log[#log + 1] = {"start", self.id} end,
        stop = function(self) log[#log + 1] = {"stop", self.id} end
      }
    end,
    free = function(id) log[#log + 1] = {"free", id} end
  }
  with_overrides({
    {_G, {metro = fake_metro, screen = recording_screen(log)}},
    {fn, {dirty_screen = dirty_recorder(log)}}
  }, function() body(tooltip, log, callbacks) end)
end

-- README.md:306: "tooltips that appear at the bottom of the Norns screen when
-- activated".
function test_uicomp_tooltip_show_sets_text_starts_a_three_second_one_shot_and_draws_at_bottom()
  with_tooltip(function(tooltip, log, callbacks)
    luaunit.assert_false(tooltip.text) -- characterisation
    luaunit.assert_false(tooltip.error_flag) -- characterisation
    luaunit.assert_equals(tooltip.metros, {})
    tooltip:draw()
    luaunit.assert_equals(log, {})
    tooltip:show("Hello")
    luaunit.assert_equals(tooltip.text, "Hello")
    luaunit.assert_equals(log, {{"dirty", true}, {"init", 3, 1}, {"start", 31}}) -- characterisation: timing
    luaunit.assert_equals(#tooltip.metros, 1)
    luaunit.assert_equals(tooltip.metros[1].id, 31)
    for i = #log, 1, -1 do log[i] = nil end
    tooltip:draw()
    luaunit.assert_equals(log, {{"move", 0, 62}, {"font_size", 8}, {"text", "Hello"}})
  end)
end

function test_uicomp_tooltip_new_tip_stops_and_frees_the_previous_metro_by_id()
  with_tooltip(function(tooltip, log)
    tooltip:show("First")
    tooltip:show("Second")
    luaunit.assert_equals(log, {
      {"dirty", true}, {"init", 3, 1}, {"start", 31},
      {"stop", 31}, {"free", 31}, {"dirty", true}, {"init", 3, 1}, {"start", 32}
    })
    luaunit.assert_equals(tooltip.text, "Second")
    luaunit.assert_equals(#tooltip.metros, 1)
    luaunit.assert_equals(tooltip.metros[1].id, 32)
  end)
end

function test_uicomp_tooltip_metro_callback_clears_text_and_error_flag()
  with_tooltip(function(tooltip, log, callbacks)
    tooltip:error("Bad")
    luaunit.assert_true(tooltip.error_flag)
    for i = #log, 1, -1 do log[i] = nil end
    callbacks[1]()
    luaunit.assert_false(tooltip.text)
    luaunit.assert_false(tooltip.error_flag)
    luaunit.assert_equals(log, {{"dirty", true}})
    for i = #log, 1, -1 do log[i] = nil end
    tooltip:draw()
    luaunit.assert_equals(log, {})
  end)
end

function test_uicomp_tooltip_error_blocks_show_until_it_expires()
  with_tooltip(function(tooltip, log, callbacks)
    tooltip:error("Bad")
    luaunit.assert_equals(tooltip.text, "Bad")
    local before = #log
    tooltip:show("ignored") -- characterisation
    luaunit.assert_equals(tooltip.text, "Bad")
    luaunit.assert_equals(#log, before)
    tooltip:error("Worse") -- another error replaces it
    luaunit.assert_equals(tooltip.text, "Worse")
    luaunit.assert_true(tooltip.error_flag)
    callbacks[#callbacks]()
    tooltip:show("after")
    luaunit.assert_equals(tooltip.text, "after")
    luaunit.assert_false(tooltip.error_flag)
  end)
end

-- save_confirm ----------------------------------------------------------------

-- README.md:291: "Some settings require a confirmation before they are set.
-- Press the K3 button to apply any selected changes. If you press K2 or
-- navigate away from the page without applying, the change will be cancelled."
local function with_save_confirm(body)
  local log = {}
  local tooltip_stub = {}
  tooltip_stub.show = function(self, text) log[#log + 1] = {"show", text, self == tooltip_stub} end
  -- The message names are reset to NIL so that a module whose locals leak into
  -- globals cannot inherit a value from an earlier test.
  with_overrides({{_G, {tooltip = tooltip_stub, ok_message = NIL, cancel_message = NIL, confirm_message = NIL,
    save_funcs = NIL, cancel_funcs = NIL}}}, function()
    local save_confirm = include("mosaic/lib/ui_components/save_confirm")
    body(save_confirm, log)
  end)
end

function test_uicomp_save_confirm_set_save_prompts_and_confirm_runs_saves_in_order()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_save(function() log[#log + 1] = {"save", 1} end)
    save_confirm.set_save(function() log[#log + 1] = {"save", 2} end)
    save_confirm.confirm()
    luaunit.assert_equals(log, {
      {"show", "Press K3 to confirm", true},
      {"show", "Press K3 to confirm", true},
      {"save", 1}, {"save", 2},
      {"show", "OK", true}
    })
    save_confirm.confirm() -- the queue was emptied
    luaunit.assert_equals(#log, 5)
  end)
end

function test_uicomp_save_confirm_cancel_runs_cancels_and_discards_saves()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_save(function() log[#log + 1] = {"save"} end)
    save_confirm.set_cancel(function() log[#log + 1] = {"cancel", 1} end)
    save_confirm.set_cancel(function() log[#log + 1] = {"cancel", 2} end)
    save_confirm.cancel()
    save_confirm.confirm()
    save_confirm.cancel()
    luaunit.assert_equals(log, {
      {"show", "Press K3 to confirm", true},
      {"cancel", 1}, {"cancel", 2},
      {"show", "Action cancelled", true}
    })
  end)
end

function test_uicomp_save_confirm_cancel_without_cancel_funcs_still_discards_saves()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_save(function() log[#log + 1] = {"save"} end)
    save_confirm.cancel()
    save_confirm.confirm()
    luaunit.assert_equals(log, {{"show", "Press K3 to confirm", true}})
  end)
end

function test_uicomp_save_confirm_confirm_without_saves_discards_cancels_silently()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_cancel(function() log[#log + 1] = {"cancel"} end)
    save_confirm.confirm()
    save_confirm.cancel()
    luaunit.assert_equals(log, {})
  end)
end

function test_uicomp_save_confirm_custom_messages_are_single_use()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_confirm_message("Press K3 to load")
    save_confirm.set_save(function() end)
    save_confirm.set_save(function() end)
    save_confirm.set_ok_message("Loaded")
    save_confirm.confirm()
    save_confirm.set_save(function() end)
    save_confirm.confirm()
    save_confirm.set_cancel_message("Load cancelled")
    save_confirm.set_cancel(function() end)
    save_confirm.cancel()
    save_confirm.set_cancel(function() end)
    save_confirm.cancel()
    luaunit.assert_equals(log, {
      {"show", "Press K3 to load", true},
      {"show", "Press K3 to confirm", true},
      {"show", "Loaded", true},
      {"show", "Press K3 to confirm", true},
      {"show", "OK", true},
      {"show", "Load cancelled", true},
      {"show", "Action cancelled", true}
    }) -- characterisation
  end)
end

function test_uicomp_save_confirm_messages_reset_even_when_nothing_ran()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_ok_message("Loaded")
    save_confirm.confirm() -- nothing queued: no tooltip, but the message resets
    save_confirm.set_save(function() end)
    save_confirm.confirm()
    save_confirm.set_cancel_message("Load cancelled")
    save_confirm.cancel()
    save_confirm.set_cancel(function() end)
    save_confirm.cancel()
    luaunit.assert_equals(log, {
      {"show", "Press K3 to confirm", true},
      {"show", "OK", true},
      {"show", "Action cancelled", true}
    }) -- characterisation
  end)
end

function test_uicomp_save_confirm_clear_drops_saves_and_resets_confirm_and_ok_messages()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_save(function() log[#log + 1] = {"save"} end)
    save_confirm.set_confirm_message("C")
    save_confirm.set_ok_message("O")
    save_confirm.clear()
    save_confirm.set_save(function() end)
    save_confirm.confirm()
    luaunit.assert_equals(log, {
      {"show", "Press K3 to confirm", true},
      {"show", "Press K3 to confirm", true},
      {"show", "OK", true}
    })
  end)
end

function test_uicomp_save_confirm_clear_drops_cancels_and_resets_cancel_message()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_cancel(function() log[#log + 1] = {"cancel"} end)
    save_confirm.set_cancel_message("X")
    save_confirm.clear()
    save_confirm.set_cancel(function() end)
    save_confirm.cancel()
    luaunit.assert_equals(log, {{"show", "Action cancelled", true}})
  end)
end

function test_uicomp_save_confirm_cancel_empties_the_cancel_queue()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_cancel(function() log[#log + 1] = {"cancel"} end)
    save_confirm.cancel()
    save_confirm.cancel()
    luaunit.assert_equals(log, {{"cancel"}, {"show", "Action cancelled", true}})
  end)
end

function test_uicomp_save_confirm_confirm_empties_the_save_queue()
  with_save_confirm(function(save_confirm, log)
    save_confirm.set_save(function() log[#log + 1] = {"save"} end)
    save_confirm.confirm()
    save_confirm.cancel()
    save_confirm.confirm()
    luaunit.assert_equals(log, {{"show", "Press K3 to confirm", true}, {"save"}, {"show", "OK", true}})
  end)
end

-- page ------------------------------------------------------------------------

function test_uicomp_page_draw_title_then_main_draw_function()
  local log = {}
  local p = page:new("Trig Locks", function() log[#log + 1] = {"main"} end)
  luaunit.assert_equals(p:get_name(), "Trig Locks")
  luaunit.assert_false(p:is_sub_page_enabled())
  with_overrides({{_G, {screen = recording_screen(log)}}}, function() p:draw() end)
  luaunit.assert_equals(log, {
    {"font_size", 8}, {"level", 10}, {"move", 0, 9}, {"text", "Trig Locks"}, {"main"}
  })
end

function test_uicomp_page_sub_name_prefix_and_sub_page_draw()
  local log = {}
  local p = page:new("Params", function() log[#log + 1] = {"main"} end)
  p:set_sub_name_func(function() return "Ch 2 " end)
  p:set_sub_page_draw_func(function() log[#log + 1] = {"sub"} end)
  p:set_name("Mask")
  p:enable_sub_page()
  luaunit.assert_true(p:is_sub_page_enabled())
  with_overrides({{_G, {screen = recording_screen(log)}}}, function() p:draw() end)
  luaunit.assert_equals(log, {
    {"font_size", 8}, {"level", 10}, {"move", 0, 9}, {"text", "Ch 2 Mask"}, {"sub"}
  })
  p:disable_sub_page()
  luaunit.assert_false(p:is_sub_page_enabled())
end

function test_uicomp_page_toggle_sub_page_flips_and_marks_dirty()
  local p = page:new("Params", function() end)
  local log = recorded(function() p:toggle_sub_page() end)
  luaunit.assert_true(p:is_sub_page_enabled())
  luaunit.assert_equals(log, {{"dirty", true}})
  recorded(function() p:toggle_sub_page() end)
  luaunit.assert_false(p:is_sub_page_enabled())
end

function test_uicomp_page_default_sub_page_draw_is_a_no_op()
  local p = page:new("Params", function() error("main should not draw") end)
  p:enable_sub_page()
  luaunit.assert_equals(draw_log(p), {{"font_size", 8}, {"level", 10}, {"move", 0, 9}, {"text", "Params"}})
end

-- pages -----------------------------------------------------------------------

local function fake_pages(log, count)
  local list = {}
  for i = 1, count do list[i] = {draw = function() log[#log + 1] = {"page", i} end} end
  return list
end

local function tabs(selected, count)
  local expected = {}
  for i = 1, count do
    expected[#expected + 1] = {"move", (i - 1) * 10, 1}
    expected[#expected + 1] = {"level", selected == i and 10 or 1}
    expected[#expected + 1] = {"text", "_"}
  end
  return expected
end

function test_uicomp_pages_draw_tabs_and_selected_page()
  local log = {}
  local ps = pages_component:new()
  luaunit.assert_equals(ps:get_selected_page(), 0)
  for _, p in ipairs(fake_pages(log, 3)) do ps:add_page(p) end
  local function draw()
    for i = #log, 1, -1 do log[i] = nil end
    with_overrides({{_G, {screen = recording_screen(log)}}}, function() ps:draw() end)
    return log
  end
  luaunit.assert_equals(draw(), tabs(0, 3)) -- characterisation: page 0 draws no page
  ps:select_page(2)
  luaunit.assert_equals(ps:get_selected_page(), 2)
  local expected = tabs(2, 3)
  expected[#expected + 1] = {"page", 2}
  luaunit.assert_equals(draw(), expected)
  ps:select_page(nil) -- characterisation: nil falls back to the first page
  expected = tabs(nil, 3)
  expected[#expected + 1] = {"page", 1}
  luaunit.assert_equals(draw(), expected)
  ps:select_page(1)
  expected = tabs(1, 3)
  expected[#expected + 1] = {"page", 1}
  luaunit.assert_equals(draw(), expected)
  ps:select_page(4)
  luaunit.assert_equals(draw(), tabs(4, 3))
  ps:select_page(-1)
  luaunit.assert_equals(draw(), tabs(-1, 3))
end

function test_uicomp_pages_draw_with_no_pages_draws_nothing()
  local ps = pages_component:new()
  luaunit.assert_equals(draw_log(ps), {})
  ps:select_page(nil)
  luaunit.assert_equals(draw_log(ps), {})
  local log = {}
  ps:add_page(fake_pages(log, 1)[1])
  with_overrides({{_G, {screen = recording_screen(log)}}}, function() ps:draw() end)
  luaunit.assert_equals(log, {{"move", 0, 1}, {"level", 1}, {"text", "_"}, {"page", 1}})
end

function test_uicomp_pages_next_and_previous_clamp()
  local ps = pages_component:new()
  for _, p in ipairs(fake_pages({}, 3)) do ps:add_page(p) end
  ps:next_page()
  luaunit.assert_equals(ps:get_selected_page(), 1)
  ps:next_page()
  ps:next_page()
  ps:next_page()
  luaunit.assert_equals(ps:get_selected_page(), 3)
  ps:previous_page()
  luaunit.assert_equals(ps:get_selected_page(), 2)
  ps:previous_page()
  ps:previous_page()
  luaunit.assert_equals(ps:get_selected_page(), 1)
  local empty = pages_component:new()
  empty:next_page()
  luaunit.assert_equals(empty:get_selected_page(), 0) -- characterisation
  empty:previous_page()
  luaunit.assert_equals(empty:get_selected_page(), 1) -- characterisation
end

-- grid_viewer -----------------------------------------------------------------

-- README.md:473: "On the Norns screen, you'll find the channel grid visualizer.
-- Use E2 to select the current channel."
-- Loads a fresh grid_viewer against a fake sequencer and runs
-- body(grid_viewer, log, fakes) with program, grid_abstraction and screen faked.
local function with_grid_viewer(body)
  local log = {}
  local fakes = {channel = {number = "channel sentinel"}, state = {}}
  for x = 1, 16 do
    fakes.state[x] = {}
    for y = 1, 8 do fakes.state[x][y] = (x * 3 + y) % 16 end
  end
  local view_sequencer = {
    draw = function(self, channel, draw_func)
      log[#log + 1] = {"sequencer_draw", self == fakes.view_sequencer, channel}
      fakes.draw_func = draw_func
    end
  }
  fakes.view_sequencer = view_sequencer
  local fake_sequencer = {}
  fake_sequencer.new = function(self, y, mode)
    log[#log + 1] = {"sequencer_new", self == fake_sequencer, y, mode}
    return view_sequencer
  end
  local seq = function(x, y, b) log[#log + 1] = {"seq", x, y, b} end
  fakes.seq = seq
  local fake_program = {
    get = function() return {selected_song_pattern = 3} end,
    get_channel = function(song_pattern, channel_number)
      log[#log + 1] = {"get_channel", song_pattern, channel_number}
      return fakes.channel
    end
  }
  with_overrides({
    {_G, {
      sequencer = fake_sequencer,
      program = fake_program,
      grid_abstraction = {seq = seq, get_screen_state = function() return fakes.state end},
      screen = recording_screen(log)
    }},
    {fn, {dirty_screen = dirty_recorder(log)}}
  }, function()
    local grid_viewer = include("mosaic/lib/ui_components/grid_viewer")
    body(grid_viewer, log, fakes)
  end)
end

function test_uicomp_grid_viewer_builds_one_channel_mode_sequencer_on_row_four()
  with_grid_viewer(function(grid_viewer, log)
    luaunit.assert_equals(log, {{"sequencer_new", true, 4, "channel"}})
    local v = grid_viewer:new(7, 9)
    luaunit.assert_equals(v.x, 7)
    luaunit.assert_equals(v.y, 9)
    luaunit.assert_equals(v.selected_channel, 1)
  end)
end

function test_uicomp_grid_viewer_draw_clears_renders_channel_and_paints_screen_state()
  with_grid_viewer(function(grid_viewer, log, fakes)
    local v = grid_viewer:new(7, 9)
    for i = #log, 1, -1 do log[i] = nil end
    v:draw()
    local expected = {}
    for x = 1, 16 do
      for y = 4, 7 do expected[#expected + 1] = {"seq", x, y, 0} end
    end
    expected[#expected + 1] = {"get_channel", 3, 1}
    expected[#expected + 1] = {"sequencer_draw", true, fakes.channel}
    for x = 1, 16 do
      for y = 1, 8 do
        expected[#expected + 1] = {"move", 7 - 3 + x * 7, 9 - 5 + y * 7}
        expected[#expected + 1] = {"level", fakes.state[x][y]}
        expected[#expected + 1] = {"font_size", 35}
        expected[#expected + 1] = {"text", "."}
      end
    end
    expected[#expected + 1] = {"move", 7, 15}
    expected[#expected + 1] = {"level", 10}
    expected[#expected + 1] = {"font_size", 8}
    expected[#expected + 1] = {"text", "Channel 1 grid viewer"}
    luaunit.assert_equals(log, expected)
    luaunit.assert_is(fakes.draw_func, fakes.seq)
  end)
end

function test_uicomp_grid_viewer_channel_navigation_clamps_and_marks_dirty()
  with_grid_viewer(function(grid_viewer, log)
    local v = grid_viewer:new(0, 0)
    for i = #log, 1, -1 do log[i] = nil end
    v:prev_channel()
    luaunit.assert_equals(v.selected_channel, 1)
    v:next_channel()
    luaunit.assert_equals(v.selected_channel, 2)
    luaunit.assert_equals(log, {{"dirty", true}, {"dirty", true}})
    for _ = 1, 13 do v:next_channel() end
    luaunit.assert_equals(v.selected_channel, 15)
    v:next_channel()
    luaunit.assert_equals(v.selected_channel, 16)
    v:next_channel()
    luaunit.assert_equals(v.selected_channel, 16)
    v:next_channel()
    luaunit.assert_equals(v.selected_channel, 16)
    v:prev_channel()
    luaunit.assert_equals(v.selected_channel, 15)
    for i = #log, 1, -1 do log[i] = nil end
    v:draw()
    luaunit.assert_equals(log[65], {"get_channel", 3, 15})
    luaunit.assert_equals(log[#log], {"text", "Channel 15 grid viewer"})
  end)
end

-- dial range edge cases -------------------------------------------------------

local function dial_with_range(min, max, off, value)
  local d = new_dial()
  d:set_min_value(min)
  d:set_max_value(max)
  d:set_off_value(off)
  recorded(function() d:set_value(value) end)
  return d
end

local function segments_from(origin, count, direction)
  local w = 19 / 20
  local rects = {}
  for i = 1, count do
    if direction == "left" then
      rects[i] = {origin - i * w, w}
    else
      rects[i] = {origin + (i - 1) * w, w}
    end
  end
  return rects
end

local CENTRE = 10 + 19 / 2

function test_uicomp_dial_draw_nil_off_value_centres_on_zero()
  local d = dial_with_range(-10, 10, nil, 5)
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(segments_from(CENTRE, 5)))) -- characterisation
end

function test_uicomp_dial_draw_off_value_equal_to_min_is_a_left_anchored_bar()
  local d = dial_with_range(0, 10, 0, 5)
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(segments_from(10, 10)))) -- characterisation
end

function test_uicomp_dial_draw_bipolar_range_around_a_non_zero_off_value()
  local d = dial_with_range(4, 20, 12, 16)
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(segments_from(CENTRE, 5)))) -- characterisation
  recorded(function() d:set_value(8) end)
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(segments_from(CENTRE, 5, "left")))) -- characterisation
end

function test_uicomp_dial_draw_positive_range_with_non_zero_min()
  local d = dial_with_range(10, 20, -1, 15)
  luaunit.assert_equals(draw_log(d), dial_frame(1, bar(segments_from(10, 10)))) -- characterisation
end

function test_uicomp_dial_draw_unit_ranges_fill_completely()
  -- characterisation
  luaunit.assert_equals(draw_log(dial_with_range(-3, 1, 0, 1)), dial_frame(1, bar(segments_from(CENTRE, 10))))
  luaunit.assert_equals(draw_log(dial_with_range(-1, 5, 0, -1)), dial_frame(1, bar(segments_from(CENTRE, 10, "left"))))
  luaunit.assert_equals(draw_log(dial_with_range(0, 1, -1, 1)), dial_frame(1, bar(segments_from(10, 20))))
end

function test_uicomp_dial_draw_empty_range_draws_no_segments()
  local d = dial_with_range(5, 5, -1, 5)
  luaunit.assert_equals(draw_log(d), dial_frame(1, {})) -- characterisation
end

-- independent instances -------------------------------------------------------

function test_uicomp_constructors_return_independent_instances()
  local function pair(make, mutate, read, expected_fresh, module)
    local a, b = make(), make()
    mutate(a)
    luaunit.assert_not_is(a, b)
    luaunit.assert_equals(read(b), expected_fresh)
    luaunit.assert_is(getmetatable(a), module)
  end
  recorded(function()
    pair(function() return value_selector:new(0, 0, "v", 0, 9) end, function(o) o:set_value(4) end,
      function(o) return o:get_value() end, 0, value_selector)
    pair(function() return list_selector:new(0, 0, "l", sample_list()) end, function(o) o:increment() end,
      function(o) return o.selected_value end, 1, list_selector)
    pair(function() return vertical_scroll_selector:new(0, 0, "s", scroll_items()) end, function(o) o:scroll_down() end,
      function(o) return o:get_selected_index() end, 1, vertical_scroll_selector)
    pair(function() return control_scroll_selector:new(0, 0, fake_controls({}, 2)) end, function(o) o:scroll_next() end,
      function(o) return o:get_selected_index() end, 1, control_scroll_selector)
    pair(new_dial, function(o) o:increment() end, function(o) return o:get_value() end, -1, dial)
    pair(function() return memory_history_navigator:new(0, 0, "h") end, function(o) o:set_current_index(3) end,
      function(o) return o:get_current_index() end, 0, memory_history_navigator)
    pair(function() return page:new("p", function() end) end, function(o) o:toggle_sub_page() end,
      function(o) return o:is_sub_page_enabled() end, false, page)
    pair(function() return pages_component:new() end, function(o) o:add_page({}) end,
      function(o) return #o.pages end, 0, pages_component)
  end)
  with_grid_viewer(function(grid_viewer)
    pair(function() return grid_viewer:new(0, 0) end, function(o) o:next_channel() end,
      function(o) return o.selected_channel end, 1, grid_viewer)
  end)
end

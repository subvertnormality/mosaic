-- Unit tests for the grid controls in lib/controls/: fader, vertical_fader,
-- button, fade_button and paint_button. (sequencer.lua lives in
-- sequencer_control_tests.lua.)
-- Drawing is pinned by replacing the `grid_abstraction` global with a recorder
-- and asserting the exact ordered (x, y, brightness) calls.
-- Assertions not backed by README.md are marked "-- characterisation".
--
-- fader.lua, vertical_fader.lua, button.lua and paint_button.lua assign a global
-- named after the module and their :new() reads that global at call time, so the
-- module tables are captured here, the globals restored, and every constructor
-- runs with its global installed only for the duration of the call.

local NIL = {}

local function swap_globals(overrides)
  local saved = {}
  for name, value in pairs(overrides) do
    saved[name] = {rawget(_G, name)}
    if value == NIL then value = nil end
    rawset(_G, name, value)
  end
  return function()
    for name, box in pairs(saved) do rawset(_G, name, box[1]) end
  end
end

local function with_globals(overrides, body)
  local restore = swap_globals(overrides)
  local ok, err = pcall(body)
  restore()
  if not ok then error(err, 0) end
end

local function include_preserving(path, names)
  local overrides = {}
  for _, name in ipairs(names) do overrides[name] = rawget(_G, name) or NIL end
  local restore = swap_globals(overrides)
  local ok, result = pcall(include, path)
  restore()
  if not ok then error(result, 0) end
  return result
end

local fader_module = include_preserving("mosaic/lib/controls/fader", {"fader"})
local vertical_fader_module = include_preserving("mosaic/lib/controls/vertical_fader", {"vertical_fader"})
local button_module = include_preserving("mosaic/lib/controls/button", {"button"})
local fade_button_module = include_preserving("mosaic/lib/controls/fade_button", {})
local paint_button_module = include_preserving("mosaic/lib/controls/paint_button", {"button"})

local function construct(global_name, module, ...)
  local args = table.pack(...)
  local object
  with_globals({[global_name] = module}, function()
    object = module:new(table.unpack(args, 1, args.n))
  end)
  return object
end

local function new_fader(...) return construct("fader", fader_module, ...) end
local function new_vertical_fader(...) return construct("vertical_fader", vertical_fader_module, ...) end
local function new_button(...) return construct("button", button_module, ...) end
local function new_paint_button(...) return construct("button", paint_button_module, ...) end

-- Runs body(log) with grid_abstraction.led recording {x, y, brightness} into log
-- and, optionally, a fake `program` exposing blink state and selected pattern.
local function recording_grid(body, program_state)
  local log = {}
  local overrides = {grid_abstraction = {led = function(x, y, b) log[#log + 1] = {x, y, b} end}}
  if program_state then
    overrides.program = {
      get_blink_state = function() return program_state.blink end,
      get = function() return {selected_pattern = program_state.selected_pattern} end
    }
  end
  with_globals(overrides, function() body(log) end)
  return log
end

local function draw_log(control, program_state)
  return recording_grid(function() control:draw() end, program_state)
end

-- helpers leave no trace ------------------------------------------------------

function test_gridctl_helpers_restore_replaced_globals_even_when_the_body_fails()
  local before_grid = rawget(_G, "grid_abstraction")
  local before_program = rawget(_G, "program")
  local before_fader = rawget(_G, "fader")
  local before_vertical_fader = rawget(_G, "vertical_fader")
  local before_button = rawget(_G, "button")
  local ok = pcall(recording_grid, function() error("boom") end, {blink = true, selected_pattern = 1})
  luaunit.assert_false(ok)
  luaunit.assert_is(rawget(_G, "grid_abstraction"), before_grid)
  luaunit.assert_is(rawget(_G, "program"), before_program)
  new_fader(1, 1, 4, 4)
  new_button(1, 1)
  new_paint_button(1, 1)
  new_vertical_fader(1, 1, 7)
  luaunit.assert_is(rawget(_G, "fader"), before_fader)
  luaunit.assert_is(rawget(_G, "vertical_fader"), before_vertical_fader)
  luaunit.assert_is(rawget(_G, "button"), before_button)
end

-- fader: construction and queries ----------------------------------------------

function test_gridctl_fader_new_starts_at_value_one_enabled_and_undimmed()
  local f = new_fader(3, 2, 6, 10)
  luaunit.assert_equals(f.x, 3)
  luaunit.assert_equals(f.y, 2)
  luaunit.assert_equals(f.length, 6)
  luaunit.assert_equals(f.size, 10)
  luaunit.assert_equals(f:get_value(), 1) -- characterisation
  luaunit.assert_false(f.is_disabled)
  -- characterisation: dimmed is seeded with relative indexes 1..length, while
  -- dim()/draw_simple() use absolute grid x.
  luaunit.assert_equals(f.dimmed, {false, false, false, false, false, false})
  luaunit.assert_is(getmetatable(f), fader_module)
end

function test_gridctl_fader_middle_position_and_middle_value_round_down()
  -- characterisation
  luaunit.assert_equals(new_fader(1, 1, 5, 10):get_middle_button_position(), 3)
  luaunit.assert_equals(new_fader(1, 1, 6, 10):get_middle_button_position(), 3)
  luaunit.assert_equals(new_fader(1, 1, 5, 10):get_middle_value(), 5)
  luaunit.assert_equals(new_fader(1, 1, 5, 9):get_middle_value(), 5)
  luaunit.assert_equals(new_fader(1, 1, 5, 12):get_middle_value(), 6)
end

function test_gridctl_fader_get_value_is_zero_while_disabled_and_restored_when_enabled()
  local f = new_fader(1, 1, 4, 4)
  f:set_value(3)
  luaunit.assert_equals(f:get_value(), 3)
  f:disabled()
  luaunit.assert_true(f.is_disabled)
  luaunit.assert_equals(f:get_value(), 0) -- characterisation
  f:enabled()
  luaunit.assert_false(f.is_disabled)
  luaunit.assert_equals(f:get_value(), 3)
end

function test_gridctl_fader_set_size_clamps_value_only_when_above_new_size()
  local f = new_fader(1, 1, 4, 10)
  f:set_value(8)
  f:set_size(5)
  luaunit.assert_equals(f.size, 5)
  luaunit.assert_equals(f:get_value(), 5) -- characterisation
  f:set_value(3)
  f:set_size(4)
  luaunit.assert_equals(f.size, 4)
  luaunit.assert_equals(f:get_value(), 3)
  f:set_size(3)
  luaunit.assert_equals(f:get_value(), 3)
  f:set_size(12)
  luaunit.assert_equals(f.size, 12)
  luaunit.assert_equals(f:get_value(), 3)
end

function test_gridctl_fader_set_length_and_set_value_store_verbatim()
  local f = new_fader(1, 1, 4, 10)
  f:set_length(7)
  luaunit.assert_equals(f.length, 7)
  f:set_value(42) -- characterisation: set_value does not clamp
  luaunit.assert_equals(f:get_value(), 42)
end

function test_gridctl_fader_is_this_accepts_exactly_its_row_span()
  local f = new_fader(3, 2, 4, 10)
  luaunit.assert_false(f:is_this(2, 2))
  luaunit.assert_true(f:is_this(3, 2))
  luaunit.assert_true(f:is_this(6, 2))
  luaunit.assert_false(f:is_this(7, 2))
  luaunit.assert_false(f:is_this(4, 1))
  luaunit.assert_false(f:is_this(4, 3))
end

-- fader: simple mode (length >= size, or length <= 2) ---------------------------

function test_gridctl_fader_simple_press_sets_value_to_relative_position()
  local f = new_fader(3, 2, 4, 4)
  f:press(3, 2)
  luaunit.assert_equals(f:get_value(), 1)
  f:press(6, 2)
  luaunit.assert_equals(f:get_value(), 4)
  f:press(5, 2)
  luaunit.assert_equals(f:get_value(), 3)
  f:press(7, 2) -- right of the span
  luaunit.assert_equals(f:get_value(), 3)
  f:press(2, 2) -- left of the span
  luaunit.assert_equals(f:get_value(), 3)
  f:press(4, 1) -- wrong row
  luaunit.assert_equals(f:get_value(), 3)
  f:press(4, 3)
  luaunit.assert_equals(f:get_value(), 3)
end

function test_gridctl_fader_simple_press_when_length_exceeds_size()
  local f = new_fader(1, 1, 6, 4)
  f:press(6, 1) -- characterisation: simple mode does not clamp to size
  luaunit.assert_equals(f:get_value(), 6)
end

function test_gridctl_fader_draw_simple_exact_leds_and_pre_func_order()
  local f = new_fader(2, 8, 4, 4)
  f:set_value(3)
  local log = {}
  f:set_pre_func(function(x, y, length) log[#log + 1] = {"pre", x, y, length} end)
  with_globals({grid_abstraction = {led = function(x, y, b) log[#log + 1] = {x, y, b} end}}, function()
    f:draw()
  end)
  -- characterisation: the first LED is written twice (once before the loop).
  luaunit.assert_equals(log, {
    {2, 8, 2}, {2, 8, 2}, {3, 8, 2}, {4, 8, 2}, {5, 8, 2},
    {"pre", 2, 8, 4},
    {4, 8, 15}
  })
end

function test_gridctl_fader_draw_simple_dimmed_cells_draw_zero_and_value_seven()
  local f = new_fader(2, 8, 4, 4)
  f:set_value(3)
  f:dim(3)
  f:dim(4)
  luaunit.assert_equals(draw_log(f), {
    {2, 8, 2}, {2, 8, 2}, {3, 8, 0}, {4, 8, 0}, {5, 8, 2}, {4, 8, 7}
  }) -- characterisation
  f:light(4)
  luaunit.assert_equals(draw_log(f), {
    {2, 8, 2}, {2, 8, 2}, {3, 8, 0}, {4, 8, 2}, {5, 8, 2}, {4, 8, 15}
  })
end

function test_gridctl_fader_draw_simple_omits_value_led_for_zero_or_nil()
  local f = new_fader(1, 1, 3, 3)
  f:set_value(0)
  local background = {{1, 1, 2}, {1, 1, 2}, {2, 1, 2}, {3, 1, 2}}
  luaunit.assert_equals(draw_log(f), background)
  f:set_value(nil)
  luaunit.assert_equals(draw_log(f), background)
  f:set_value(1)
  luaunit.assert_equals(draw_log(f), {{1, 1, 2}, {1, 1, 2}, {2, 1, 2}, {3, 1, 2}, {1, 1, 15}})
end

function test_gridctl_fader_draw_uses_simple_mode_when_length_is_two_or_less()
  local f = new_fader(5, 3, 2, 10) -- length < size but not > 2
  f:set_value(2)
  luaunit.assert_equals(draw_log(f), {{5, 3, 2}, {5, 3, 2}, {6, 3, 2}, {6, 3, 15}})
end

function test_gridctl_fader_disabled_draws_nothing_and_does_not_call_pre_func()
  local f = new_fader(1, 1, 4, 4)
  local called = false
  f:set_pre_func(function() called = true end)
  f:disabled()
  luaunit.assert_equals(draw_log(f), {})
  luaunit.assert_false(called)
  f:enabled()
  luaunit.assert_equals(#draw_log(f), 6)
  luaunit.assert_true(called)
end

-- fader: fine-grain mode (2 < length < size) ------------------------------------

-- README.md:413: "Brightly lit end buttons refine values, with the furthest
-- left-hand button incrementing downwards and the furthest right-hand button
-- incrementing upwards. The dimmer ones in the middle of the faders adjust values
-- broadly."
function test_gridctl_fader_fine_grain_end_buttons_step_by_one_within_bounds()
  local f = new_fader(3, 2, 6, 10)
  f:set_value(4)
  f:press(3, 2)
  luaunit.assert_equals(f:get_value(), 3)
  f:press(8, 2)
  f:press(8, 2)
  luaunit.assert_equals(f:get_value(), 5)
  f:set_value(1)
  f:press(3, 2) -- already at minimum: no change
  luaunit.assert_equals(f:get_value(), 1)
  f:set_value(10)
  f:press(8, 2) -- already at maximum: no change
  luaunit.assert_equals(f:get_value(), 10)
  f:set_value(9)
  f:press(8, 2)
  luaunit.assert_equals(f:get_value(), 10)
  f:set_value(2)
  f:press(3, 2)
  luaunit.assert_equals(f:get_value(), 1)
end

function test_gridctl_fader_fine_grain_inner_buttons_jump_proportionally()
  local f = new_fader(3, 2, 6, 10)
  f:set_value(7)
  f:press(4, 2) -- first inner button
  luaunit.assert_equals(f:get_value(), 1) -- characterisation
  f:press(6, 2)
  luaunit.assert_equals(f:get_value(), 7) -- characterisation: floor(2/3*9)+1
  f:press(7, 2) -- last inner button
  luaunit.assert_equals(f:get_value(), 10) -- characterisation
  f:press(5, 2) -- middle button (position floor((6+1)/2) = 3)
  luaunit.assert_equals(f:get_value(), 5) -- characterisation: middle value
  f:press(9, 2) -- outside
  luaunit.assert_equals(f:get_value(), 5)
  f:press(5, 1) -- wrong row
  luaunit.assert_equals(f:get_value(), 5)
end

function test_gridctl_fader_fine_grain_wider_fader_inner_values()
  local f = new_fader(1, 5, 8, 20)
  f:press(2, 5)
  luaunit.assert_equals(f:get_value(), 1) -- characterisation
  f:press(3, 5)
  luaunit.assert_equals(f:get_value(), 4) -- characterisation: floor(1/5*19)+1
  f:press(4, 5) -- middle button position 4
  luaunit.assert_equals(f:get_value(), 10) -- characterisation
  f:press(5, 5)
  luaunit.assert_equals(f:get_value(), 12) -- characterisation: floor(3/5*19)+1
  f:press(7, 5)
  luaunit.assert_equals(f:get_value(), 20)
end

function test_gridctl_fader_press_on_two_long_fader_uses_fine_grain_but_draws_simple()
  -- characterisation (suspected defect: press() selects fine-grain on
  -- length < size alone, while draw() also requires length > 2, so a 2-long
  -- fader draws as a simple fader but its left key at value 1 jumps to the
  -- middle value instead of selecting 1).
  local f = new_fader(1, 1, 2, 10)
  f:press(1, 1)
  luaunit.assert_equals(f:get_value(), 5)
  f:press(1, 1)
  luaunit.assert_equals(f:get_value(), 4)
  f:press(2, 1)
  luaunit.assert_equals(f:get_value(), 5)
end

function test_gridctl_fader_draw_fine_grain_ends_background_and_lowest_value()
  local f = new_fader(3, 2, 6, 10)
  f:set_value(1)
  luaunit.assert_equals(draw_log(f), {
    {3, 2, 7}, {8, 2, 7},
    {4, 2, 2}, {5, 2, 2}, {6, 2, 2}, {7, 2, 2},
    {4, 2, 5}
  })
end

function test_gridctl_fader_draw_fine_grain_brightness_tracks_remainder()
  local f = new_fader(3, 2, 6, 10)
  local frame = {{3, 2, 7}, {8, 2, 7}, {4, 2, 2}, {5, 2, 2}, {6, 2, 2}, {7, 2, 2}}
  local function with(extra)
    local expected = {}
    for i, v in ipairs(frame) do expected[i] = v end
    for _, v in ipairs(extra) do expected[#expected + 1] = v end
    return expected
  end
  f:set_value(3) -- (3-1)/2.5 -> led 0, remainder 2 -> floor(0.8*10+5)
  luaunit.assert_equals(draw_log(f), with({{4, 2, 13}})) -- characterisation
  f:set_value(4) -- led 1, remainder 0.5 -> 7
  luaunit.assert_equals(draw_log(f), with({{5, 2, 7}})) -- characterisation
  f:set_value(5) -- middle value also lights the middle button
  luaunit.assert_equals(draw_log(f), with({{5, 2, 11}, {5, 2, 15}})) -- characterisation
  f:set_value(9) -- led 3, remainder 0.5
  luaunit.assert_equals(draw_log(f), with({{7, 2, 7}})) -- characterisation
  f:set_value(10) -- maximum lights the last inner LED fully and stops
  luaunit.assert_equals(draw_log(f), with({{7, 2, 15}})) -- characterisation
  f:set_value(11) -- above size: clamped to the last inner LED at full remainder
  luaunit.assert_equals(draw_log(f), with({{7, 2, 15}})) -- characterisation
  f:set_value(nil)
  luaunit.assert_equals(draw_log(f), frame)
end

function test_gridctl_fader_draw_fine_grain_middle_button_on_wider_fader()
  local f = new_fader(1, 5, 8, 14)
  f:set_value(7) -- middle value; (7-1)/(14/6) -> led 2, remainder 4/3
  luaunit.assert_equals(draw_log(f), {
    {1, 5, 7}, {8, 5, 7},
    {2, 5, 2}, {3, 5, 2}, {4, 5, 2}, {5, 5, 2}, {6, 5, 2}, {7, 5, 2},
    {4, 5, 10}, {4, 5, 15}
  }) -- characterisation
  f:set_value(9) -- led 3, remainder 1 -> floor(3/7*10+5)
  local log = draw_log(f)
  luaunit.assert_equals(log[9], {5, 5, 9}) -- characterisation
  luaunit.assert_equals(#log, 9)
end

function test_gridctl_fader_draw_fine_grain_on_three_long_fader()
  local f = new_fader(2, 1, 3, 5)
  f:set_value(2)
  luaunit.assert_equals(draw_log(f), {{2, 1, 7}, {4, 1, 7}, {3, 1, 2}, {3, 1, 7}}) -- characterisation
  f:press(3, 1) -- the single inner key is the middle button
  luaunit.assert_equals(f:get_value(), 3)
  luaunit.assert_equals(draw_log(f), {{2, 1, 7}, {4, 1, 7}, {3, 1, 2}, {3, 1, 9}, {3, 1, 15}}) -- characterisation
end

-- vertical_fader --------------------------------------------------------------

function test_gridctl_vertical_fader_new_defaults_and_accessors()
  local v = new_vertical_fader(3, 1, 21)
  luaunit.assert_equals(v.x, 3)
  luaunit.assert_equals(v.y, 1)
  luaunit.assert_equals(v.size, 21)
  luaunit.assert_equals(v:get_value(), 0)
  luaunit.assert_equals(v:get_vertical_offset(), 0)
  luaunit.assert_equals(v:get_horizontal_offset(), 0)
  luaunit.assert_equals(v.led_brightness, 3)
  v:set_value(9)
  v:set_vertical_offset(7)
  v:set_horizontal_offset(16)
  luaunit.assert_equals(v:get_value(), 9)
  luaunit.assert_equals(v:get_vertical_offset(), 7)
  luaunit.assert_equals(v:get_horizontal_offset(), 16)
  v:set_dark()
  luaunit.assert_equals(v.led_brightness, 1)
  v:set_light()
  luaunit.assert_equals(v.led_brightness, 3)
end

function test_gridctl_vertical_fader_press_sets_row_plus_vertical_offset()
  local v = new_vertical_fader(3, 1, 21)
  v:press(3, 4)
  luaunit.assert_equals(v:get_value(), 4)
  v:press(3, 1)
  luaunit.assert_equals(v:get_value(), 1)
  v:press(3, 7)
  luaunit.assert_equals(v:get_value(), 7)
  v:press(3, 8) -- row 8 is outside the fader
  luaunit.assert_equals(v:get_value(), 7)
  v:press(4, 2) -- other column
  luaunit.assert_equals(v:get_value(), 7)
  v:set_vertical_offset(7)
  v:press(3, 2)
  luaunit.assert_equals(v:get_value(), 9)
  v:set_horizontal_offset(2)
  v:press(3, 2) -- column now drawn at 1
  luaunit.assert_equals(v:get_value(), 9)
  v:press(1, 5)
  luaunit.assert_equals(v:get_value(), 12)
end

function test_gridctl_vertical_fader_press_ignores_rows_above_its_top()
  local v = new_vertical_fader(2, 3, 10)
  v:press(2, 2)
  luaunit.assert_equals(v:get_value(), 0)
  v:press(2, 3)
  luaunit.assert_equals(v:get_value(), 3)
end

function test_gridctl_vertical_fader_is_this_uses_horizontal_offset_and_rows_to_seven()
  local v = new_vertical_fader(20, 3, 10)
  luaunit.assert_false(v:is_this(4, 1))
  v:set_horizontal_offset(16)
  luaunit.assert_true(v:is_this(4, 7))
  luaunit.assert_false(v:is_this(4, 8))
  luaunit.assert_false(v:is_this(5, 2))
  luaunit.assert_true(v:is_this(4, 1)) -- characterisation: rows above y still match
end

function test_gridctl_vertical_fader_draw_rows_reference_line_and_active_led()
  local v = new_vertical_fader(3, 1, 4)
  v:set_dark()
  local state = {blink = false, selected_pattern = 5}
  -- characterisation: rows 1..size lit at led_brightness, reference line row 7.
  luaunit.assert_equals(draw_log(v, state), {
    {3, 1, 1}, {3, 2, 1}, {3, 3, 1}, {3, 4, 1}, {3, 7, 3}
  })
  v:set_value(2)
  luaunit.assert_equals(draw_log(v, state), {
    {3, 1, 1}, {3, 2, 1}, {3, 3, 1}, {3, 4, 1}, {3, 7, 3}, {3, 2, 12}
  })
  v:set_light()
  v:set_value(7)
  luaunit.assert_equals(draw_log(v, state), {
    {3, 1, 3}, {3, 2, 3}, {3, 3, 3}, {3, 4, 3}, {3, 7, 3}, {3, 7, 12}
  })
end

-- README.md:471: "The gentle flicker on the top row indicates the currently
-- chosen pattern."
function test_gridctl_vertical_fader_selected_pattern_column_flickers_on_top_row()
  local v = new_vertical_fader(5, 1, 3)
  v:set_value(1)
  luaunit.assert_equals(draw_log(v, {blink = true, selected_pattern = 5}), {
    {5, 1, 4}, {5, 2, 3}, {5, 3, 3}, {5, 7, 3}, {5, 1, 13}
  })
  luaunit.assert_equals(draw_log(v, {blink = false, selected_pattern = 5}), {
    {5, 1, 2}, {5, 2, 3}, {5, 3, 3}, {5, 7, 3}, {5, 1, 11}
  })
  v:set_value(2) -- active LED off the top row does not flicker
  luaunit.assert_equals(draw_log(v, {blink = true, selected_pattern = 5}), {
    {5, 1, 4}, {5, 2, 3}, {5, 3, 3}, {5, 7, 3}, {5, 2, 12}
  })
  luaunit.assert_equals(draw_log(v, {blink = true, selected_pattern = 6}), {
    {5, 1, 3}, {5, 2, 3}, {5, 3, 3}, {5, 7, 3}, {5, 2, 12}
  })
end

function test_gridctl_vertical_fader_draw_with_top_below_row_one()
  local v = new_vertical_fader(2, 3, 5)
  v:set_value(2)
  luaunit.assert_equals(draw_log(v, {blink = true, selected_pattern = 2}), {
    {2, 3, 3}, {2, 4, 3}, {2, 5, 3}, {2, 7, 3}, {2, 4, 12}
  }) -- characterisation
end

function test_gridctl_vertical_fader_vertical_offsets_move_reference_line()
  local state = {blink = false, selected_pattern = 9}
  local v = new_vertical_fader(1, 1, 21)
  v:set_vertical_offset(3) -- reference at row 4
  luaunit.assert_equals(draw_log(v, state), {
    {1, 1, 3}, {1, 2, 3}, {1, 3, 3}, {1, 4, 3}, {1, 5, 3}, {1, 6, 3}, {1, 7, 3}
  })
  v:set_dark()
  luaunit.assert_equals(draw_log(v, state), {
    {1, 1, 1}, {1, 2, 1}, {1, 3, 1}, {1, 4, 3}, {1, 5, 1}, {1, 6, 1}, {1, 7, 1}
  }) -- characterisation
  v:set_vertical_offset(7) -- no reference row; the zero line on row 7 at 4
  luaunit.assert_equals(draw_log(v, state), {
    {1, 1, 1}, {1, 2, 1}, {1, 3, 1}, {1, 4, 1}, {1, 5, 1}, {1, 6, 1}, {1, 7, 4}
  }) -- characterisation
  v:set_vertical_offset(14) -- multiple of 7 above 7: reference on row 7
  luaunit.assert_equals(draw_log(v, state), {
    {1, 1, 1}, {1, 2, 1}, {1, 3, 1}, {1, 4, 1}, {1, 5, 1}, {1, 6, 1}, {1, 7, 3}
  }) -- characterisation
  v:set_vertical_offset(10) -- not a multiple of 7: no reference row
  luaunit.assert_equals(draw_log(v, state), {
    {1, 1, 1}, {1, 2, 1}, {1, 3, 1}, {1, 4, 1}, {1, 5, 1}, {1, 6, 1}, {1, 7, 1}
  }) -- characterisation
  v:set_vertical_offset(16) -- size - i - 16 + 1 > 0 only for rows 1..5
  luaunit.assert_equals(draw_log(v, state), {
    {1, 1, 1}, {1, 2, 1}, {1, 3, 1}, {1, 4, 1}, {1, 5, 1}
  }) -- characterisation
end

function test_gridctl_vertical_fader_active_led_accounts_for_vertical_offset()
  local state = {blink = false, selected_pattern = 9}
  local v = new_vertical_fader(1, 1, 14)
  v:set_vertical_offset(7)
  v:set_value(10)
  local log = draw_log(v, state)
  luaunit.assert_equals(log[#log], {1, 3, 12})
  luaunit.assert_equals(#log, 8)
  v:set_value(14)
  log = draw_log(v, state)
  luaunit.assert_equals(log[#log], {1, 7, 12})
  v:set_value(15) -- row 8 is never drawn
  luaunit.assert_equals(#draw_log(v, state), 7)
  v:set_value(3) -- characterisation: rows above the page reach grid_abstraction
  log = draw_log(v, state)
  luaunit.assert_equals(log[#log], {1, -4, 12})
end

function test_gridctl_vertical_fader_horizontal_offset_selects_screen_column()
  local state = {blink = false, selected_pattern = 9}
  local v = new_vertical_fader(20, 1, 1)
  luaunit.assert_equals(draw_log(v, state), {}) -- column 20 is off the grid
  v:set_horizontal_offset(16)
  v:set_value(1)
  luaunit.assert_equals(draw_log(v, state), {{4, 1, 3}, {4, 7, 3}, {4, 1, 12}})
  v:set_horizontal_offset(4)
  luaunit.assert_equals(draw_log(v, state), {{16, 1, 3}, {16, 7, 3}, {16, 1, 12}})
  v:set_horizontal_offset(20)
  luaunit.assert_equals(draw_log(v, state), {})
  v:set_horizontal_offset(19)
  luaunit.assert_equals(draw_log(v, state), {{1, 1, 3}, {1, 7, 3}, {1, 1, 12}})
end

function test_gridctl_vertical_fader_offset_page_top_row_active_led_does_not_flicker()
  -- characterisation (suspected defect: the background loop compares the
  -- on-screen column with selected_pattern but the active LED compares the
  -- absolute step x, so on pages 2-4 the selected pattern's active top-row LED
  -- never flickers while on page 1 it does).
  local v = new_vertical_fader(20, 1, 1)
  v:set_horizontal_offset(16)
  v:set_value(1)
  luaunit.assert_equals(draw_log(v, {blink = true, selected_pattern = 4}), {
    {4, 1, 4}, {4, 7, 3}, {4, 1, 12}
  })
  luaunit.assert_equals(draw_log(v, {blink = true, selected_pattern = 20}), {
    {4, 1, 3}, {4, 7, 3}, {4, 1, 13}
  })
end

-- button ----------------------------------------------------------------------

function test_gridctl_button_new_defaults_to_off_on_states()
  local b = new_button(4, 8)
  luaunit.assert_equals(b.x, 4)
  luaunit.assert_equals(b.y, 8)
  luaunit.assert_equals(b.states, {{"off", 2}, {"on", 15}})
  luaunit.assert_equals(b:get_state(), 1)
  luaunit.assert_false(b.blink_active)
  luaunit.assert_equals(b.bright_mod, 6)
  local custom = {{"a", 1}, {"b", 5}, {"c", 9}}
  luaunit.assert_is(new_button(1, 1, custom).states, custom)
end

function test_gridctl_button_press_cycles_states_and_wraps()
  local b = new_button(4, 8)
  b:press(4, 8)
  luaunit.assert_equals(b:get_state(), 2)
  b:press(4, 8)
  luaunit.assert_equals(b:get_state(), 1)
  local c = new_button(2, 3, {{"a", 1}, {"b", 5}, {"c", 9}})
  c:press(2, 3)
  c:press(2, 3)
  luaunit.assert_equals(c:get_state(), 3)
  c:press(2, 3)
  luaunit.assert_equals(c:get_state(), 1)
  c:press(3, 3)
  c:press(2, 4)
  luaunit.assert_equals(c:get_state(), 1)
end

function test_gridctl_button_is_this_and_set_state()
  local b = new_button(4, 8)
  luaunit.assert_true(b:is_this(4, 8))
  luaunit.assert_false(b:is_this(5, 8))
  luaunit.assert_false(b:is_this(4, 7))
  b:set_state(2)
  luaunit.assert_equals(b:get_state(), 2)
end

function test_gridctl_button_draw_uses_state_brightness_and_blink_dims_by_six()
  local b = new_button(4, 8)
  luaunit.assert_equals(draw_log(b, {blink = true}), {{4, 8, 2}})
  b:set_state(2)
  luaunit.assert_equals(draw_log(b, {blink = true}), {{4, 8, 15}})
  b:blink()
  luaunit.assert_true(b.blink_active)
  luaunit.assert_equals(draw_log(b, {blink = true}), {{4, 8, 9}}) -- characterisation
  luaunit.assert_equals(draw_log(b, {blink = false}), {{4, 8, 15}})
  b:no_blink()
  luaunit.assert_false(b.blink_active)
  luaunit.assert_equals(draw_log(b, {blink = true}), {{4, 8, 15}})
end

-- fade_button -----------------------------------------------------------------

function test_gridctl_fade_button_new_starts_at_min()
  local f = fade_button_module:new(16, 8, 2, 9, "up")
  luaunit.assert_equals(f.x, 16)
  luaunit.assert_equals(f.y, 8)
  luaunit.assert_equals(f:get_value(), 2)
  luaunit.assert_equals(f.step_size, 1)
  luaunit.assert_equals(f.button_type, "up")
  luaunit.assert_is(getmetatable(f), fade_button_module)
end

function test_gridctl_fade_button_set_value_clamps_to_range()
  local f = fade_button_module:new(1, 1, 0, 14, "up")
  f:set_value(20)
  luaunit.assert_equals(f:get_value(), 14)
  f:set_value(-3)
  luaunit.assert_equals(f:get_value(), 0)
  f:set_value(7)
  luaunit.assert_equals(f:get_value(), 7)
  f:set_value(14)
  luaunit.assert_equals(f:get_value(), 14)
  f:set_value(0)
  luaunit.assert_equals(f:get_value(), 0)
end

-- README.md:465: "A single press of the end buttons in this trio steps up and
-- down by one step ... A single press of the middle button gets you back to the
-- page with the root note on the bottom row."
function test_gridctl_fade_button_press_steps_and_returns_new_value()
  local down = fade_button_module:new(14, 8, 0, 14, "down")
  luaunit.assert_equals(down:press(14, 8), 1) -- characterisation: "down" increases value
  luaunit.assert_equals(down:get_value(), 1)
  down:set_value(14)
  luaunit.assert_false(down:press(14, 8))
  luaunit.assert_equals(down:get_value(), 14)
  down:set_value(13)
  luaunit.assert_equals(down:press(14, 8), 14)

  local up = fade_button_module:new(16, 8, 0, 14, "up")
  luaunit.assert_false(up:press(16, 8)) -- at min
  luaunit.assert_equals(up:get_value(), 0)
  up:set_value(1)
  luaunit.assert_equals(up:press(16, 8), 0)
  up:set_value(9)
  luaunit.assert_equals(up:press(16, 8), 8)
  luaunit.assert_equals(up:get_value(), 8)
end

function test_gridctl_fade_button_center_press_returns_midpoint()
  local center = fade_button_module:new(15, 8, 0, 14, "center")
  luaunit.assert_equals(center:press(15, 8), 7)
  luaunit.assert_equals(center:get_value(), 7)
  local offset = fade_button_module:new(15, 8, 2, 9, "center")
  offset:set_value(9)
  luaunit.assert_equals(offset:press(15, 8), 5) -- floor(7/2)+2
  luaunit.assert_equals(offset:get_value(), 5)
end

function test_gridctl_fade_button_press_elsewhere_or_unknown_type_returns_false()
  local up = fade_button_module:new(16, 8, 0, 14, "up")
  up:set_value(5)
  luaunit.assert_false(up:press(15, 8))
  luaunit.assert_false(up:press(16, 7))
  luaunit.assert_equals(up:get_value(), 5)
  local other = fade_button_module:new(3, 3, 0, 14, "sideways")
  other:set_value(4)
  luaunit.assert_false(other:press(3, 3))
  luaunit.assert_equals(other:get_value(), 4)
  luaunit.assert_true(other:is_this(3, 3))
  luaunit.assert_false(other:is_this(3, 4))
  luaunit.assert_false(other:is_this(4, 3))
end

function test_gridctl_fade_button_draw_up_fades_from_fifteen_to_floor_of_four()
  local up = fade_button_module:new(16, 8, 0, 7, "up")
  local seen = {}
  for value = 0, 7 do
    up:set_value(value)
    seen[#seen + 1] = draw_log(up)[1]
  end
  luaunit.assert_equals(seen, {
    {16, 8, 15}, {16, 8, 13}, {16, 8, 11}, {16, 8, 9},
    {16, 8, 7}, {16, 8, 5}, {16, 8, 4}, {16, 8, 4}
  }) -- characterisation
  local offset = fade_button_module:new(1, 2, 3, 9, "up")
  offset:set_value(4)
  luaunit.assert_equals(draw_log(offset), {{1, 2, 13}}) -- characterisation
end

function test_gridctl_fade_button_draw_down_fades_in_the_opposite_direction()
  local down = fade_button_module:new(16, 8, 0, 7, "down")
  local seen = {}
  for value = 0, 7 do
    down:set_value(value)
    seen[#seen + 1] = draw_log(down)[1]
  end
  luaunit.assert_equals(seen, {
    {16, 8, 4}, {16, 8, 4}, {16, 8, 5}, {16, 8, 7},
    {16, 8, 9}, {16, 8, 11}, {16, 8, 13}, {16, 8, 15}
  }) -- characterisation
  local offset = fade_button_module:new(1, 2, 3, 9, "down")
  offset:set_value(8)
  luaunit.assert_equals(draw_log(offset), {{1, 2, 13}}) -- characterisation
end

function test_gridctl_fade_button_draw_center_and_unknown_types()
  local center = fade_button_module:new(15, 8, 2, 9, "center")
  luaunit.assert_equals(draw_log(center), {{15, 8, 8}}) -- characterisation
  center:set_value(5)
  luaunit.assert_equals(draw_log(center), {{15, 8, 15}}) -- characterisation
  center:set_value(6)
  luaunit.assert_equals(draw_log(center), {{15, 8, 8}})
  local other = fade_button_module:new(3, 4, 0, 7, "sideways")
  luaunit.assert_equals(draw_log(other), {{3, 4, 3}}) -- characterisation
end

-- paint_button (not included by any production page) --------------------------

function test_gridctl_paint_button_defaults_and_draws_state_brightness()
  local p = new_paint_button(16, 8)
  luaunit.assert_equals(p.states, {{"inactive", 3}, {"save", 15}})
  luaunit.assert_equals(p.state, 1)
  luaunit.assert_equals(draw_log(p), {{16, 8, 3}})
  p:press(16, 8)
  luaunit.assert_equals(p.state, 2)
  luaunit.assert_equals(draw_log(p), {{16, 8, 15}})
  local custom = new_paint_button(1, 2, {{"x", 4}, {"y", 11}})
  luaunit.assert_equals(draw_log(custom), {{1, 2, 4}})
end

function test_gridctl_paint_button_press_elsewhere_keeps_state()
  local p = new_paint_button(16, 8)
  p:press(15, 8)
  p:press(16, 7)
  luaunit.assert_equals(p.state, 1)
end

function test_gridctl_paint_button_second_press_reads_undefined_global_states()
  -- characterisation (suspected defect: press() compares against the undefined
  -- global `states` instead of `self.states`, so pressing in state 2 raises).
  local p = new_paint_button(16, 8)
  p:press(16, 8)
  with_globals({states = NIL}, function()
    local ok, err = pcall(p.press, p, 16, 8)
    luaunit.assert_false(ok)
    luaunit.assert_str_contains(err, "global 'states'")
  end)
  luaunit.assert_equals(p.state, 2)
end

function test_gridctl_paint_button_get_and_set_state_use_value_field()
  -- characterisation (suspected defect: get_state/set_state read and write
  -- self.value, not self.state, so they neither report nor change what is drawn).
  local p = new_paint_button(16, 8)
  luaunit.assert_nil(p:get_state())
  p:press(16, 8)
  luaunit.assert_nil(p:get_state())
  p:set_state(1)
  luaunit.assert_equals(p:get_state(), 1)
  luaunit.assert_equals(p.state, 2)
  luaunit.assert_equals(draw_log(p), {{16, 8, 15}})
end

-- independence and boundary cases ---------------------------------------------

function test_gridctl_constructors_return_independent_instances()
  local a, b = new_vertical_fader(1, 1, 7), new_vertical_fader(2, 1, 7)
  a:set_value(3)
  luaunit.assert_equals(b:get_value(), 0)
  luaunit.assert_not_is(a, b)
  luaunit.assert_is(getmetatable(a), vertical_fader_module)
  local c, d = new_button(1, 1), new_button(2, 2)
  c:press(1, 1)
  luaunit.assert_equals(d:get_state(), 1)
  luaunit.assert_not_is(c, d)
  luaunit.assert_is(getmetatable(c), button_module)
  local e, f = new_paint_button(1, 1), new_paint_button(2, 2)
  e:press(1, 1)
  luaunit.assert_equals(f.state, 1)
  luaunit.assert_not_is(e, f)
  luaunit.assert_is(getmetatable(e), paint_button_module)
end

function test_gridctl_vertical_fader_column_seventeen_is_off_the_grid()
  local state = {blink = false, selected_pattern = 9}
  local v = new_vertical_fader(17, 1, 1)
  luaunit.assert_equals(draw_log(v, state), {})
  v:set_horizontal_offset(1)
  luaunit.assert_equals(draw_log(v, state), {{16, 1, 3}, {16, 7, 3}})
end

function test_gridctl_vertical_fader_offset_eight_has_no_reference_row()
  local v = new_vertical_fader(1, 1, 21)
  v:set_dark()
  v:set_vertical_offset(8) -- above 7 and not a multiple of 7
  luaunit.assert_equals(draw_log(v, {blink = false, selected_pattern = 9}), {
    {1, 1, 1}, {1, 2, 1}, {1, 3, 1}, {1, 4, 1}, {1, 5, 1}, {1, 6, 1}, {1, 7, 1}
  }) -- characterisation
end

function test_gridctl_vertical_fader_reference_row_on_top_row_flickers()
  local v = new_vertical_fader(2, 1, 21)
  v:set_dark()
  v:set_vertical_offset(6) -- reference line at row 1
  local log = draw_log(v, {blink = true, selected_pattern = 2})
  luaunit.assert_equals(log[1], {2, 1, 4}) -- characterisation
  log = draw_log(v, {blink = false, selected_pattern = 2})
  luaunit.assert_equals(log[1], {2, 1, 2}) -- characterisation
  luaunit.assert_equals(log[2], {2, 2, 1})
end

function test_gridctl_vertical_fader_below_row_seven_draws_only_the_active_led()
  -- characterisation: with y past row 7 the row loop never runs and the active
  -- LED keeps the initial zero brightness modifier.
  local v = new_vertical_fader(3, 8, 7)
  v:set_vertical_offset(1)
  v:set_value(1)
  luaunit.assert_equals(draw_log(v, {blink = true, selected_pattern = 9}), {{3, 7, 12}})
end

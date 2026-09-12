-- Integration hardening for the real pattern trigger editor.
-- README.md:406-428 defines algorithm selection, preview, shift, cancel and XOR paint.
-- drum_ops_extra_tests.lua proves the generator arithmetic exhaustively; these tests
-- prove that the page applies complete 64-step outputs to the selected pattern.

local function copy64(values)
  local out = {}
  for i = 1, 64 do out[i] = values[i] end
  return out
end

local function press_all(env, x, y)
  for _, handler in ipairs(env.handlers) do handler(x, y) end
end

local function with_editor(body)
  local names = {
    "fader", "button", "sequencer", "press", "draw", "grid_abstraction",
    "pattern", "tooltip", "params"
  }
  local saved = {}
  for i, name in ipairs(names) do saved[i] = rawget(_G, name) end

  local ok, err = pcall(function()
    fader = include("mosaic/lib/controls/fader")
    button = include("mosaic/lib/controls/button")
    sequencer = include("mosaic/lib/controls/sequencer")
    local env = {handlers = {}, updates = 0, tooltips = {}}
    press = {
      register = function(_, page, handler)
        luaunit.assert_equals(page, "trigger_edit_page")
        env.handlers[#env.handlers + 1] = handler
      end,
      register_dual = function() end,
      register_long = function() end
    }
    draw = {register_grid = function() end}
    grid_abstraction = {led = function() end}
    pattern = {update_working_patterns = function() env.updates = env.updates + 1 end}
    tooltip = {show = function(text) env.tooltips[#env.tooltips + 1] = text end}
    params = {string = function(_, id)
      luaunit.assert_equals(id, "tresillo_amount")
      return 64
    end}

    program.init()
    local page = dofile("../../lib/pages/trigger_edit_page/trigger_edit_page.lua")
    page.register_press()
    luaunit.assert_equals(#env.handlers, 11)
    body(env)
  end)

  for i = #names, 1, -1 do rawset(_G, names[i], saved[i]) end
  if not ok then error(err, 0) end
end

local function set_fader(env, row, edge_x, target)
  for _ = 2, target do press_all(env, edge_x, row) end
end

local function assert_pattern(pattern_value, expected, expected_lengths, label)
  for step = 1, 64 do
    local active = expected[step] == true
    luaunit.assert_equals(pattern_value.trig_values[step], active and 1 or 0,
      label .. " trig step " .. step)
    luaunit.assert_equals(pattern_value.lengths[step], expected_lengths[step],
      label .. " length step " .. step)
  end
end

local function prime_and_paint(env)
  press_all(env, 16, 8)
  press_all(env, 16, 8)
end

local function independent_euclidean(fill, length)
  local pattern_value = {}
  local bucket = 0
  for i = 1, length do
    bucket = bucket + fill
    if bucket >= length then
      bucket = bucket - length
      pattern_value[i] = true
    else
      pattern_value[i] = false
    end
  end
  local first
  for i = 1, length do
    if pattern_value[i] then first = i; break end
  end
  if first and first > 1 then
    local rotated = {}
    for i = 1, length do
      rotated[i] = pattern_value[(i + first - 2) % length + 1]
    end
    pattern_value = rotated
  end
  local out = {}
  for step = 1, 64 do out[step] = pattern_value[(step - 1) % length + 1] end
  return out
end

local function bit_at(bytes, step)
  local wrapped = (step - 1) % (#bytes * 8)
  local byte = bytes[math.floor(wrapped / 8) + 1]
  return bit32.band(byte, bit32.lshift(1, 7 - wrapped % 8)) ~= 0
end

function test_hardening_trigger_editor_boundary_algorithms_apply_all_64_steps()
  local tables = include("mosaic/lib/helpers/drum_ops_tables")
  local cases = {
    {
      name = "drum-bank5-pattern128", algorithm_x = 12, bank_x = 16,
      p1 = 128, p2 = 1,
      oracle = function(step) return bit_at(tables.table_dr_oh[128], step) end
    },
    {
      name = "tresillo-bank5-patterns128", algorithm_x = 13, bank_x = 16,
      p1 = 128, p2 = 128,
      oracle = function(step)
        local wrapped = (step - 1) % 64 + 1
        if wrapped <= 24 then return bit_at(tables.table_dr_oh[128], wrapped) end
        if wrapped <= 48 then return bit_at(tables.table_dr_oh[128], wrapped - 24) end
        return bit_at(tables.table_dr_oh[128], wrapped - 48)
      end
    },
    {
      name = "euclidean-fill32-length32", algorithm_x = 14,
      p1 = 32, p2 = 32, expected = independent_euclidean(32, 32)
    },
    {
      name = "numeric-prime32-mask4-factor16", algorithm_x = 15, bank_x = 15,
      p1 = 32, p2 = 16,
      oracle = function(step)
        local rhythm = tables.table_nr[32]
        local modified = rhythm * 16
        local final_value = bit32.bor(bit32.band(modified, 0xFFFF), bit32.rshift(modified, 16))
        return bit32.band(bit32.rshift(final_value, 16 - ((step - 1) % 16 + 1)), 1) == 1
      end
    }
  }

  for _, case in ipairs(cases) do
    with_editor(function(env)
      program.get().selected_pattern = 16
      local song = program.get_selected_song_pattern()
      song.active = false
      local selected = song.patterns[16]
      local untouched = copy64(song.patterns[1].trig_values)

      press_all(env, case.algorithm_x, 2)
      if case.bank_x then press_all(env, case.bank_x, 3) end
      set_fader(env, 2, 10, case.p1)
      set_fader(env, 3, 10, case.p2)

      local expected = case.expected or {}
      if case.oracle then
        for step = 1, 64 do expected[step] = case.oracle(step) end
      end
      local first_lengths = {}
      for step = 1, 64 do first_lengths[step] = 1 end

      prime_and_paint(env)
      assert_pattern(selected, expected, first_lengths, case.name)
      luaunit.assert_true(song.active)
      luaunit.assert_equals(song.patterns[1].trig_values, untouched,
        case.name .. " selected-pattern isolation")

      prime_and_paint(env)
      local repaint_lengths = {}
      for step = 1, 64 do repaint_lengths[step] = expected[step] and 0 or 1 end
      assert_pattern(selected, {}, repaint_lengths, case.name .. " repaint")
    end)
  end
end

function test_hardening_trigger_editor_paint_is_xor_and_cancel_preserves_all_cells()
  with_editor(function(env)
    local selected = program.get_selected_pattern()
    for step = 1, 64 do
      selected.trig_values[step] = step % 3 == 0 and 1 or 0
      selected.lengths[step] = selected.trig_values[step] == 1 and 7 or 0
    end
    local before_trigs = copy64(selected.trig_values)
    local before_lengths = copy64(selected.lengths)

    press_all(env, 14, 2)
    set_fader(env, 2, 10, 32)
    set_fader(env, 3, 10, 32)
    press_all(env, 16, 8)
    press_all(env, 14, 8)
    luaunit.assert_equals(selected.trig_values, before_trigs)
    luaunit.assert_equals(selected.lengths, before_lengths)

    prime_and_paint(env)
    local generated = independent_euclidean(32, 32)
    for step = 1, 64 do
      local was_on = before_trigs[step] == 1
      local generated_on = generated[step] == true
      luaunit.assert_equals(selected.trig_values[step], was_on ~= generated_on and 1 or 0,
        "xor trig step " .. step)
      local expected_length
      if was_on and generated_on then expected_length = 0
      elseif (not was_on) and generated_on then expected_length = 1
      else expected_length = before_lengths[step] end
      luaunit.assert_equals(selected.lengths[step], expected_length,
        "xor length step " .. step)
    end
  end)
end

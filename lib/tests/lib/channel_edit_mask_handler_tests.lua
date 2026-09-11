-- Unit tests for the eight mask handlers of the REAL
-- lib/pages/channel_edit_page/channel_edit_page_ui.lua:
--   handle_trig_mask_change (968), handle_note_mask_change (1020),
--   handle_velocity_mask_change (1071), handle_length_mask_change (1123),
--   handle_chord_mask_one/two/three/four_change (1197, 1247, 1297, 1340).
--
-- They are near-identical and a refactor is expected to merge them, so every test below pins
-- one handler's exact behaviour and the SPECS table states, per handler, where it differs
-- from the others (each difference cites the production line).
--
-- Every test loads a FRESH copy of the module inside `isolated` (include() is dofile, so the
-- module-local mask_selectors start at value 0 each time) and replaces the collaborators the
-- handlers call with recording stubs: m_grid.get_pressed_keys, program (selected channel,
-- song patterns and the eight set_*_mask setters), recorder.add_note_mask_event_portion,
-- pattern.update_working_pattern and memory.record_event. `isolated` restores every global it
-- replaced and removes any global created meanwhile, even when the test fails. fn (for
-- fn.calc_grid_count and fn.dirty_screen) and lib/clock/divisions stay real.
--
-- README.md:595 (hold a step on the mask page and input a value = a step mask lock) and
-- README.md:597 (without holding a step, the value applies to all steps of the channel) are
-- the manual statements behind the held/unheld split; README.md:203 (a "channel parameters"
-- map controls a specific channel regardless of which channel is selected) and README.md:211
-- (masks are mappable) sit behind the unselected-channel guard, arbitrated as SEM-017
-- fixed-map-ignores-held-steps (docs/testing/decisions.md:441-452). Every other assertion
-- pins current behaviour and is labelled `-- characterisation`.

local UI_MODULE = "mosaic/lib/pages/channel_edit_page/channel_edit_page_ui"
local divisions = include("mosaic/lib/clock/divisions")
local V = divisions.note_division_values

local REPLACED_GLOBALS = {"m_grid", "program", "recorder", "pattern", "memory", "screen_dirty", "include"}

local SELECTED = 2 -- program.get_selected_channel().number
local OTHER = 3 -- a channel that is not the selected one
local RECORDER_SONG_PATTERN = 4 -- program.get().selected_song_pattern (held-step payloads)
local WORKING_SONG_PATTERN = 6 -- program.get_selected_song_pattern() (working-pattern update)

-- Held keys are {x, y}; fn.calc_grid_count(x, y) = (y - 4) * 16 + x (functions.lua:363).
local HELD_ROW_4_AND_7 = {{3, 4}, {16, 7}} -- steps 3 and 64
local HELD_STEPS = {3, 64}

-- Per-handler contract. Everything not stated here is identical across handlers.
--
-- SHARED SUSPECTED DEFECT (all seven generic handlers, both paths): every decrement writes
-- `v == -1 and nil or v` (lines 1000, 1013, 1052, 1065, 1104, 1117, 1229, 1242, 1279, 1292, 1324,
-- 1335, 1372, 1385). In Lua `true and nil or v` evaluates to v, so the expression is always v and
-- -1 is passed on as -1, never as nil. The tests pin -1 and label it
-- `-- characterisation (suspected defect: "and nil or" never yields nil)`; a refactor that
-- "fixes" it to nil changes behaviour and must do so deliberately.
local AND_NIL_OR = -1
local SPECS = {
  trig = {
    fn = "handle_trig_mask_change", field = "trig_mask", setter = "program.set_trig_mask",
    min = -1, max = 1, inc_from = 0, dec_from = 1, -- selector range (line 63)
    -- unheld decrement from an unset mask: nil -> -1 -> clamp -1 (lines 1007, 1012-1013)
    dec_from_unset = -1,
    payload = function(s, v) return {step = s, trig = v} end, -- lines 982-985, 998-1001
    updates_working_pattern = true, -- line 1015
    decrement_sink = "recorder", -- line 993
    writes_step_velocity_on_increment = false
  },
  note = {
    fn = "handle_note_mask_change", field = "note_mask", setter = "program.set_note_mask",
    min = -1, max = 127, inc_from = 60, dec_from = 60, -- line 64
    dec_from_unset = -1, -- lines 1059, 1064-1065
    payload = function(s, v) return {step = s, note = v} end, -- lines 1034-1037, 1050-1053
    updates_working_pattern = true, -- line 1067
    decrement_sink = "recorder", -- line 1045
    writes_step_velocity_on_increment = false
  },
  velocity = {
    fn = "handle_velocity_mask_change", field = "velocity_mask", setter = "program.set_velocity_mask",
    min = -1, max = 127, inc_from = 100, dec_from = 100, -- line 65
    dec_from_unset = -1, -- lines 1111, 1116-1117
    payload = function(s, v) return {step = s, velocity = v} end, -- lines 1086-1089, 1102-1105
    updates_working_pattern = true, -- line 1119
    decrement_sink = "recorder", -- line 1097
    -- DIFFERENCE: the held increment writes channel.step_velocity_masks[s] (line 1080).
    writes_step_velocity_on_increment = true
  },
  chord_one = {
    fn = "handle_chord_mask_one_change", field = "chord_one_mask", setter = "program.set_chord_one_mask",
    min = -14, max = 14, inc_from = 3, dec_from = 3, -- line 68
    -- DIFFERENCE (range): unset -> -1 -> -2, which is above min -14, so it stays -2 (line 1236, 1241-1242)
    dec_from_unset = -2,
    payload = function(s, v) return {step = s, chord_degrees = {v, nil, nil, nil}} end, -- lines 1213, 1229
    -- DIFFERENCE: no pattern.update_working_pattern on the channel path (lines 1235-1244)
    updates_working_pattern = false,
    decrement_sink = "recorder", -- line 1222
    writes_step_velocity_on_increment = false
  },
  chord_two = {
    fn = "handle_chord_mask_two_change", field = "chord_two_mask", setter = "program.set_chord_two_mask",
    min = -14, max = 14, inc_from = 5, dec_from = 5, -- line 69
    dec_from_unset = -2, -- lines 1286, 1291-1292
    payload = function(s, v) return {step = s, chord_degrees = {nil, v, nil, nil}} end, -- lines 1263, 1279
    updates_working_pattern = false, -- lines 1285-1294
    decrement_sink = "recorder", -- line 1272
    writes_step_velocity_on_increment = false
  },
  chord_three = {
    fn = "handle_chord_mask_three_change", field = "chord_three_mask", setter = "program.set_chord_three_mask",
    min = -14, max = 14, inc_from = 7, dec_from = 7, -- line 70
    dec_from_unset = -2, -- lines 1329, 1334-1335
    payload = function(s, v) return {step = s, chord_degrees = {nil, nil, v, nil}} end, -- lines 1313, 1324
    updates_working_pattern = false, -- lines 1328-1337
    -- DIFFERENCE: the held DECREMENT calls memory.record_event(channel, "note_mask", {step, chord_degrees})
    -- directly, with no song_pattern and no recorder portion (lines 1319-1326).
    decrement_sink = "memory",
    writes_step_velocity_on_increment = false
  },
  chord_four = {
    fn = "handle_chord_mask_four_change", field = "chord_four_mask", setter = "program.set_chord_four_mask",
    min = -14, max = 14, inc_from = -9, dec_from = -9, -- line 71
    dec_from_unset = -2, -- lines 1379, 1384-1385
    payload = function(s, v) return {step = s, chord_degrees = {nil, nil, nil, v}} end, -- lines 1356, 1372
    updates_working_pattern = false, -- lines 1378-1387
    decrement_sink = "recorder", -- line 1365
    writes_step_velocity_on_increment = false
  }
}

-- length is structurally different (selector holds an index into divisions.note_division_values,
-- lines 66, 1139, 1180-1191) and gets its own tests below; it shares the guard and the sinks.
local LENGTH = {
  fn = "handle_length_mask_change", field = "length_mask", setter = "program.set_length_mask",
  payload = function(s, v) return {step = s, length = v} end
}

local ALL_HANDLER_FIELDS = {
  {"handle_trig_mask_change", "trig_mask"}, {"handle_note_mask_change", "note_mask"},
  {"handle_velocity_mask_change", "velocity_mask"}, {"handle_length_mask_change", "length_mask"},
  {"handle_chord_mask_one_change", "chord_one_mask"}, {"handle_chord_mask_two_change", "chord_two_mask"},
  {"handle_chord_mask_three_change", "chord_three_mask"}, {"handle_chord_mask_four_change", "chord_four_mask"}
}

------------------------------------------------------------------------------------------------
-- Harness
------------------------------------------------------------------------------------------------

local function recorder_of(env, name, extra)
  return function(...)
    table.insert(env.calls, table.pack(name, ...))
    if extra then extra(...) end
  end
end

local function install_stubs(env)
  env.calls = {}
  env.pressed = {}
  env.velocity_snapshots = {}
  m_grid = {get_pressed_keys = function() return env.pressed end}
  program = {
    get_selected_channel = function() return {number = SELECTED} end,
    get = function() return {selected_song_pattern = RECORDER_SONG_PATTERN} end,
    get_selected_song_pattern = function() return WORKING_SONG_PATTERN end
  }
  for _, setter in ipairs({"set_trig_mask", "set_note_mask", "set_velocity_mask", "set_length_mask",
                           "set_chord_one_mask", "set_chord_two_mask", "set_chord_three_mask",
                           "set_chord_four_mask"}) do
    program[setter] = recorder_of(env, "program." .. setter)
  end
  recorder = {
    add_note_mask_event_portion = recorder_of(env, "recorder.add_note_mask_event_portion", function(_, s)
      -- what channel.step_velocity_masks held for this step at the moment of the recorder call
      if env.channel then
        table.insert(env.velocity_snapshots, {step = s, value = env.channel.step_velocity_masks[s]})
      end
    end)
  }
  pattern = {update_working_pattern = recorder_of(env, "pattern.update_working_pattern")}
  memory = {record_event = recorder_of(env, "memory.record_event")}
end

-- Loading the module (through m_midi and friends) also REASSIGNS existing globals such as
-- m_clock, clock_lattice, midi_devices and handle_midi_event_data, so `isolated` snapshots the
-- whole of _G and afterwards restores every changed value and removes every new key.
local function isolated(body)
  local saved = {}
  for _, name in ipairs(REPLACED_GLOBALS) do
    saved[name] = _G[name]
  end
  local before = {}
  for k, v in pairs(_G) do before[k] = v end
  local env = {}
  local ok, err = pcall(function()
    install_stubs(env)
    -- channel_edit_page_ui_handlers/_refreshers include script-relative "lib/..." paths, which
    -- norns resolves inside the script directory; the test include() only knows "mosaic/...".
    local real_include = saved.include
    include = function(file)
      if file:sub(1, 4) == "lib/" then return real_include("mosaic/" .. file) end
      return real_include(file)
    end
    env.ui = include(UI_MODULE)
    body(env)
  end)
  local keys = {}
  for k in pairs(_G) do table.insert(keys, k) end
  for _, k in ipairs(keys) do
    if before[k] == nil then _G[k] = nil end
  end
  for k, v in pairs(before) do
    if rawget(_G, k) ~= v then _G[k] = v end
  end
  for _, name in ipairs(REPLACED_GLOBALS) do
    _G[name] = saved[name]
  end
  if not ok then error(err, 0) end
end

local function new_channel(number, masks)
  local c = {number = number, step_velocity_masks = {}}
  for k, v in pairs(masks or {}) do c[k] = v end
  return c
end

-- Run a handler once on `channel` with `keys` held; returns the recorded mutating calls.
local function run(env, handler_fn, channel, direction, keys)
  env.calls = {}
  env.velocity_snapshots = {}
  env.pressed = keys or {}
  env.channel = channel
  env.ui[handler_fn](channel, direction)
  local calls = env.calls
  env.calls = {}
  env.pressed = {}
  return calls
end

-- The calls the channel-mask path makes (README.md:597).
local function channel_path_calls(spec, channel, value, updates_working_pattern)
  local calls = {table.pack(spec.setter, channel, value)}
  if updates_working_pattern then
    table.insert(calls, table.pack("pattern.update_working_pattern", channel.number, WORKING_SONG_PATTERN))
  end
  return calls
end

-- The calls the held-step path makes: one per held key, in key order (README.md:595).
local function held_path_calls(spec, channel, steps, value, sink)
  local calls = {}
  for _, s in ipairs(steps) do
    if sink == "memory" then
      local data = spec.payload(s, value)
      table.insert(calls, table.pack("memory.record_event", channel.number, "note_mask",
        {step = data.step, chord_degrees = data.chord_degrees}))
    else
      table.insert(calls, table.pack("recorder.add_note_mask_event_portion", channel.number, s,
        {song_pattern = RECORDER_SONG_PATTERN, data = spec.payload(s, value)}))
    end
  end
  return calls
end

-- Leave a generic handler's module-local selector at `value` by driving its channel path
-- (set_value(mask) then increment), then discard the calls that made.
local function prime(env, spec, value)
  run(env, spec.fn, new_channel(SELECTED, {[spec.field] = value - 1}), 1, {})
end

-- Same for length: the selector holds an index into divisions.note_division_values.
local function prime_length(env, index)
  local mask = nil
  if index - 1 > 0 then mask = V[index - 1] end
  run(env, LENGTH.fn, new_channel(SELECTED, {length_mask = mask}), 1, {})
end

------------------------------------------------------------------------------------------------
-- Generic scenarios (trig, note, velocity, chord one..four), parameterised by SPECS.
------------------------------------------------------------------------------------------------

local function unheld_increment(name)
  local spec = SPECS[name]
  isolated(function(env)
    local c = new_channel(SELECTED, {[spec.field] = spec.inc_from})
    -- README.md:597: no held step sets the channel mask, starting from the channel's own value.
    local calls = run(env, spec.fn, c, 1, {})
    luaunit.assert_equals(calls, channel_path_calls(spec, c, spec.inc_from + 1, spec.updates_working_pattern))
    luaunit.assert_is(calls[1][2], c) -- the setter receives the handled channel itself
    luaunit.assert_equals(c.step_velocity_masks, {}) -- characterisation
  end)
end

local function unheld_decrement(name)
  local spec = SPECS[name]
  isolated(function(env)
    local c = new_channel(SELECTED, {[spec.field] = spec.dec_from})
    -- README.md:597
    luaunit.assert_equals(run(env, spec.fn, c, -1, {}),
      channel_path_calls(spec, c, spec.dec_from - 1, spec.updates_working_pattern))
  end)
end

local function unheld_increment_from_unset(name)
  local spec = SPECS[name]
  isolated(function(env)
    local c = new_channel(SELECTED)
    -- characterisation: an unset mask counts as -1, so one increment sets 0
    luaunit.assert_equals(run(env, spec.fn, c, 1, {}), channel_path_calls(spec, c, 0, spec.updates_working_pattern))
  end)
end

local function unheld_decrement_to_minus_one(name)
  local spec = SPECS[name]
  isolated(function(env)
    local c = new_channel(SELECTED, {[spec.field] = 0})
    local calls = run(env, spec.fn, c, -1, {})
    -- characterisation (suspected defect: "and nil or" never yields nil): -1 is set, not nil
    luaunit.assert_equals(calls, channel_path_calls(spec, c, AND_NIL_OR, spec.updates_working_pattern))
    luaunit.assert_equals(calls[1].n, 3) -- characterisation: the value is passed as an argument
  end)
end

local function unheld_decrement_from_unset(name)
  local spec = SPECS[name]
  isolated(function(env)
    local c = new_channel(SELECTED)
    -- characterisation: unset counts as -1; the result depends on the selector minimum
    -- (for min -1 the clamp holds -1, passed as -1: suspected defect "and nil or" never yields nil)
    luaunit.assert_equals(run(env, spec.fn, c, -1, {}),
      channel_path_calls(spec, c, spec.dec_from_unset, spec.updates_working_pattern))
  end)
end

local function unheld_clamps_at_max(name)
  local spec = SPECS[name]
  isolated(function(env)
    local c = new_channel(SELECTED, {[spec.field] = spec.max})
    luaunit.assert_equals(run(env, spec.fn, c, 1, {}),
      channel_path_calls(spec, c, spec.max, spec.updates_working_pattern)) -- characterisation
  end)
end

local function unheld_clamps_at_min(name)
  local spec = SPECS[name]
  isolated(function(env)
    local c = new_channel(SELECTED, {[spec.field] = spec.min})
    -- characterisation (for min -1 also the suspected defect: "and nil or" never yields nil)
    luaunit.assert_equals(run(env, spec.fn, c, -1, {}),
      channel_path_calls(spec, c, spec.min, spec.updates_working_pattern))
  end)
end

local function direction_zero_decrements(name)
  local spec = SPECS[name]
  isolated(function(env)
    local c = new_channel(SELECTED, {[spec.field] = spec.dec_from})
    -- characterisation: only direction > 0 increments; 0 takes the decrement branch on both paths
    luaunit.assert_equals(run(env, spec.fn, c, 0, {}),
      channel_path_calls(spec, c, spec.dec_from - 1, spec.updates_working_pattern))
    prime(env, spec, spec.dec_from)
    local held = new_channel(SELECTED)
    luaunit.assert_equals(run(env, spec.fn, held, 0, HELD_ROW_4_AND_7),
      held_path_calls(spec, held, HELD_STEPS, spec.dec_from - 1, spec.decrement_sink))
  end)
end

local function held_increment(name)
  local spec = SPECS[name]
  isolated(function(env)
    prime(env, spec, spec.inc_from)
    local c = new_channel(SELECTED, {[spec.field] = 11})
    -- README.md:595: holding steps of the selected channel records a step mask lock per held step.
    -- characterisation: the value continues from the selector's last value (here inc_from),
    -- not from the channel mask (11) or any step value; no setter and no working-pattern update.
    luaunit.assert_equals(run(env, spec.fn, c, 1, HELD_ROW_4_AND_7),
      held_path_calls(spec, c, HELD_STEPS, spec.inc_from + 1, "recorder"))
    if spec.writes_step_velocity_on_increment then
      -- characterisation (suspected defect: gap-scan #16, see M-MEMORY-008)
      luaunit.assert_equals(c.step_velocity_masks, {[3] = spec.inc_from + 1, [64] = spec.inc_from + 1})
    else
      luaunit.assert_equals(c.step_velocity_masks, {}) -- characterisation
    end
  end)
end

local function held_decrement(name)
  local spec = SPECS[name]
  isolated(function(env)
    prime(env, spec, spec.dec_from)
    local c = new_channel(SELECTED, {[spec.field] = 11})
    -- README.md:595
    luaunit.assert_equals(run(env, spec.fn, c, -1, HELD_ROW_4_AND_7),
      held_path_calls(spec, c, HELD_STEPS, spec.dec_from - 1, spec.decrement_sink))
    luaunit.assert_equals(c.step_velocity_masks, {}) -- characterisation: no handler writes on decrement
  end)
end

local function held_decrement_to_minus_one(name)
  local spec = SPECS[name]
  isolated(function(env)
    -- fresh module: the selector starts at 0, so one decrement reaches -1
    local c = new_channel(SELECTED, {[spec.field] = 11})
    local calls = run(env, spec.fn, c, -1, HELD_ROW_4_AND_7)
    -- characterisation (suspected defect: "and nil or" never yields nil): -1 is recorded as -1
    luaunit.assert_equals(calls, held_path_calls(spec, c, HELD_STEPS, AND_NIL_OR, spec.decrement_sink))
  end)
end

local function held_selector_is_independent(name)
  local spec = SPECS[name]
  isolated(function(env)
    -- Drive every OTHER handler's channel path to a large value first.
    for other_name, other in pairs(SPECS) do
      if other_name ~= name then prime(env, other, other.max) end
    end
    prime_length(env, 20)
    local c = new_channel(SELECTED)
    -- characterisation: each handler owns its selector, still at its fresh 0 here
    luaunit.assert_equals(run(env, spec.fn, c, 1, HELD_ROW_4_AND_7),
      held_path_calls(spec, c, HELD_STEPS, 1, "recorder"))
  end)
end

local function held_on_unselected_channel(name)
  local spec = SPECS[name]
  isolated(function(env)
    -- SEM-017 (docs/testing/decisions.md:441-452; README.md:203): a held step on the selected
    -- channel's page does not redirect a map for another channel; it edits that channel's mask.
    local c = new_channel(OTHER, {[spec.field] = spec.inc_from})
    luaunit.assert_equals(run(env, spec.fn, c, 1, {{5, 5}}),
      channel_path_calls(spec, c, spec.inc_from + 1, spec.updates_working_pattern))
    local d = new_channel(OTHER, {[spec.field] = spec.dec_from})
    luaunit.assert_equals(run(env, spec.fn, d, -1, {{5, 5}}),
      channel_path_calls(spec, d, spec.dec_from - 1, spec.updates_working_pattern))
    luaunit.assert_equals(c.step_velocity_masks, {})
  end)
end

local function held_row_boundaries(name)
  local spec = SPECS[name]
  isolated(function(env)
    -- characterisation: only keys whose first held key sits on rows 4..7 (the step rows) take
    -- the held-step path; rows 3 and 8 edit the channel mask.
    for _, row in ipairs({3, 8}) do
      local c = new_channel(SELECTED, {[spec.field] = spec.inc_from})
      luaunit.assert_equals(run(env, spec.fn, c, 1, {{2, row}}),
        channel_path_calls(spec, c, spec.inc_from + 1, spec.updates_working_pattern))
    end
    for _, row in ipairs({4, 7}) do
      prime(env, spec, spec.inc_from)
      local c = new_channel(SELECTED, {[spec.field] = 11})
      luaunit.assert_equals(run(env, spec.fn, c, 1, {{2, row}}),
        held_path_calls(spec, c, {(row - 4) * 16 + 2}, spec.inc_from + 1, "recorder"))
    end
  end)
end

local function only_first_key_row_checked(name)
  local spec = SPECS[name]
  isolated(function(env)
    -- characterisation: only pressed_keys[1] is range-checked; later keys are recorded as-is
    -- (row 2 gives step (2 - 4) * 16 + 2 = -30).
    prime(env, spec, spec.inc_from)
    local c = new_channel(SELECTED)
    luaunit.assert_equals(run(env, spec.fn, c, 1, {{1, 4}, {2, 2}}),
      held_path_calls(spec, c, {1, -30}, spec.inc_from + 1, "recorder"))
    -- ...and a first key outside rows 4..7 sends everything to the channel path.
    local d = new_channel(SELECTED, {[spec.field] = spec.inc_from})
    luaunit.assert_equals(run(env, spec.fn, d, 1, {{1, 2}, {2, 5}}),
      channel_path_calls(spec, d, spec.inc_from + 1, spec.updates_working_pattern))
  end)
end

local function velocity_write_precedes_recorder(name)
  local spec = SPECS[name]
  isolated(function(env)
    prime(env, spec, spec.inc_from)
    local c = new_channel(SELECTED)
    run(env, spec.fn, c, 1, HELD_ROW_4_AND_7)
    if spec.writes_step_velocity_on_increment then
      -- characterisation (suspected defect: gap-scan #16, see M-MEMORY-008): the step's
      -- velocity mask is already written when the recorder portion is added, i.e. before the
      -- release commits the action to memory.
      luaunit.assert_equals(env.velocity_snapshots, {
        {step = 3, value = spec.inc_from + 1}, {step = 64, value = spec.inc_from + 1}
      })
    else
      luaunit.assert_equals(env.velocity_snapshots, {{step = 3}, {step = 64}}) -- characterisation
    end
    -- the decrement never writes it (line 1094-1108 for velocity)
    prime(env, spec, spec.dec_from)
    local d = new_channel(SELECTED)
    run(env, spec.fn, d, -1, HELD_ROW_4_AND_7)
    luaunit.assert_equals(d.step_velocity_masks, {}) -- characterisation
  end)
end

------------------------------------------------------------------------------------------------
-- Length (lines 1123-1195). DIFFERENCES from the generic handlers:
--   * the selector holds an index 0..#divisions.note_divisions (line 66); 0 means unset and the
--     channel path starts from divisions.note_division_index(channel.length_mask) or 0 (line 1180),
--     not from `mask or -1`;
--   * values passed on are divisions.note_division_values[index] (lines 1139, 1156, 1183, 1187),
--     so index 0 yields nil there, with no `== -1 and nil` mapping;
--   * the decrement is guarded by `get_value() ~= 0` (lines 1145, 1185): at 0 the channel path
--     sets nil (lines 1189-1190) while the held path records length = 0 per key (lines 1162-1176).
------------------------------------------------------------------------------------------------

local function length_unheld(env, mask, direction, expected)
  local c = new_channel(SELECTED, {length_mask = mask})
  local calls = run(env, LENGTH.fn, c, direction, {})
  luaunit.assert_equals(calls, channel_path_calls(LENGTH, c, expected, true))
  luaunit.assert_is(calls[1][2], c)
  luaunit.assert_equals(calls[1].n, 3)
  luaunit.assert_equals(c.step_velocity_masks, {})
end

function test_mask_handler_length_unheld_increment_from_unset()
  isolated(function(env)
    length_unheld(env, nil, 1, 1/24) -- characterisation: unset -> index 0 -> index 1 (1/24)
  end)
end

function test_mask_handler_length_unheld_increment()
  isolated(function(env)
    length_unheld(env, 1/4, 1, 1/3) -- README.md:597; characterisation of the next division
  end)
end

function test_mask_handler_length_unheld_clamps_at_max()
  isolated(function(env)
    length_unheld(env, 128, 1, 128) -- characterisation: index 89 is the last division
  end)
end

function test_mask_handler_length_unheld_decrement()
  isolated(function(env)
    length_unheld(env, 1/4, -1, 1/6) -- README.md:597; characterisation of the previous division
  end)
end

function test_mask_handler_length_unheld_decrement_from_first_division_clears()
  isolated(function(env)
    length_unheld(env, 1/24, -1, nil) -- characterisation: index 1 -> 0 -> note_division_values[0] = nil
  end)
end

function test_mask_handler_length_unheld_decrement_from_unset_clears()
  isolated(function(env)
    length_unheld(env, nil, -1, nil) -- characterisation: the `~= 0` guard's else branch (1189-1190)
  end)
end

function test_mask_handler_length_unheld_decrement_from_unset_leaves_selector_at_zero()
  isolated(function(env)
    length_unheld(env, nil, -1, nil) -- characterisation
    -- the selector is 0 afterwards (line 1189), so a held increment records the first division
    local c = new_channel(SELECTED)
    luaunit.assert_equals(run(env, LENGTH.fn, c, 1, HELD_ROW_4_AND_7),
      held_path_calls(LENGTH, c, HELD_STEPS, 1/24, "recorder")) -- characterisation
  end)
end

-- Note: `get_value() ~= 0` on the channel path (line 1185) is observably redundant: the selector
-- minimum is 0 and note_division_values[0] is nil, so decrementing from 0 or 1 passes nil either
-- way. Hand mutation `~= 0` -> `~= 1` there is equivalent and survives by construction.

function test_mask_handler_length_unheld_unknown_value_counts_as_unset()
  isolated(function(env)
    length_unheld(env, 0.3, 1, 1/24) -- characterisation: no division index -> 0
    length_unheld(env, 0.3, -1, nil) -- characterisation
  end)
end

function test_mask_handler_length_direction_zero_decrements()
  isolated(function(env)
    length_unheld(env, 1/4, 0, 1/6) -- characterisation
    prime_length(env, 5)
    local c = new_channel(SELECTED)
    luaunit.assert_equals(run(env, LENGTH.fn, c, 0, HELD_ROW_4_AND_7),
      held_path_calls(LENGTH, c, HELD_STEPS, 1/6, "recorder")) -- characterisation
  end)
end

function test_mask_handler_length_held_increment()
  isolated(function(env)
    prime_length(env, 5) -- selector at 1/4
    local c = new_channel(SELECTED, {length_mask = 2})
    -- README.md:595; characterisation: continues from the selector (1/4 -> 1/3), not from the mask
    luaunit.assert_equals(run(env, LENGTH.fn, c, 1, HELD_ROW_4_AND_7),
      held_path_calls(LENGTH, c, HELD_STEPS, 1/3, "recorder"))
    luaunit.assert_equals(c.step_velocity_masks, {}) -- characterisation
    luaunit.assert_equals(env.velocity_snapshots, {{step = 3}, {step = 64}}) -- characterisation
  end)
end

function test_mask_handler_length_held_increment_clamps_at_max()
  isolated(function(env)
    prime_length(env, 89)
    local c = new_channel(SELECTED)
    luaunit.assert_equals(run(env, LENGTH.fn, c, 1, HELD_ROW_4_AND_7),
      held_path_calls(LENGTH, c, HELD_STEPS, 128, "recorder")) -- characterisation
  end)
end

function test_mask_handler_length_held_decrement()
  isolated(function(env)
    prime_length(env, 5)
    local c = new_channel(SELECTED)
    luaunit.assert_equals(run(env, LENGTH.fn, c, -1, HELD_ROW_4_AND_7),
      held_path_calls(LENGTH, c, HELD_STEPS, 1/6, "recorder")) -- README.md:595
    luaunit.assert_equals(c.step_velocity_masks, {}) -- characterisation
  end)
end

function test_mask_handler_length_held_decrement_from_first_division_records_nil()
  isolated(function(env)
    prime_length(env, 1)
    local c = new_channel(SELECTED)
    -- characterisation: index 1 -> 0 -> note_division_values[0] = nil (key absent from payload)
    luaunit.assert_equals(run(env, LENGTH.fn, c, -1, HELD_ROW_4_AND_7),
      held_path_calls(LENGTH, c, HELD_STEPS, nil, "recorder"))
  end)
end

function test_mask_handler_length_held_decrement_at_zero_records_zero()
  isolated(function(env)
    local c = new_channel(SELECTED, {length_mask = 1/4})
    -- characterisation: a fresh selector is 0, so the `~= 0` else branch records length = 0
    -- (a number, unlike the nil the channel path passes) for every held key.
    luaunit.assert_equals(run(env, LENGTH.fn, c, -1, HELD_ROW_4_AND_7),
      held_path_calls(LENGTH, c, HELD_STEPS, 0, "recorder"))
    -- the selector stays at 0: the next held increment records the first division.
    luaunit.assert_equals(run(env, LENGTH.fn, c, 1, HELD_ROW_4_AND_7),
      held_path_calls(LENGTH, c, HELD_STEPS, 1/24, "recorder"))
  end)
end

function test_mask_handler_length_held_on_unselected_channel()
  isolated(function(env)
    -- SEM-017 (docs/testing/decisions.md:441-452; README.md:203)
    local c = new_channel(OTHER, {length_mask = 1/4})
    luaunit.assert_equals(run(env, LENGTH.fn, c, 1, {{5, 5}}), channel_path_calls(LENGTH, c, 1/3, true))
    local d = new_channel(OTHER, {length_mask = 1/4})
    luaunit.assert_equals(run(env, LENGTH.fn, d, -1, {{5, 5}}), channel_path_calls(LENGTH, d, 1/6, true))
    local e = new_channel(OTHER)
    luaunit.assert_equals(run(env, LENGTH.fn, e, -1, {{5, 5}}), channel_path_calls(LENGTH, e, nil, true))
  end)
end

function test_mask_handler_length_held_row_boundaries()
  isolated(function(env)
    for _, row in ipairs({3, 8}) do
      local c = new_channel(SELECTED, {length_mask = 1/4})
      luaunit.assert_equals(run(env, LENGTH.fn, c, 1, {{2, row}}),
        channel_path_calls(LENGTH, c, 1/3, true)) -- characterisation
    end
    for _, row in ipairs({4, 7}) do
      prime_length(env, 5)
      local c = new_channel(SELECTED, {length_mask = 2})
      luaunit.assert_equals(run(env, LENGTH.fn, c, 1, {{2, row}}),
        held_path_calls(LENGTH, c, {(row - 4) * 16 + 2}, 1/3, "recorder")) -- characterisation
    end
  end)
end

function test_mask_handler_length_only_first_key_row_checked()
  isolated(function(env)
    prime_length(env, 5)
    local c = new_channel(SELECTED)
    luaunit.assert_equals(run(env, LENGTH.fn, c, 1, {{1, 4}, {2, 2}}),
      held_path_calls(LENGTH, c, {1, -30}, 1/3, "recorder")) -- characterisation
    local zero = new_channel(SELECTED)
    isolated(function(inner)
      luaunit.assert_equals(run(inner, LENGTH.fn, zero, -1, {{1, 4}, {2, 2}}),
        held_path_calls(LENGTH, zero, {1, -30}, 0, "recorder")) -- characterisation: 0 branch too
    end)
    local d = new_channel(SELECTED, {length_mask = 1/4})
    luaunit.assert_equals(run(env, LENGTH.fn, d, 1, {{1, 2}, {2, 5}}),
      channel_path_calls(LENGTH, d, 1/3, true)) -- characterisation
  end)
end

function test_mask_handler_length_selector_is_independent()
  isolated(function(env)
    for _, spec in pairs(SPECS) do prime(env, spec, spec.max) end
    local c = new_channel(SELECTED)
    luaunit.assert_equals(run(env, LENGTH.fn, c, 1, HELD_ROW_4_AND_7),
      held_path_calls(LENGTH, c, HELD_STEPS, 1/24, "recorder")) -- characterisation
  end)
end

------------------------------------------------------------------------------------------------
-- Cross-handler: which handlers call which collaborator on the channel path.
------------------------------------------------------------------------------------------------

function test_mask_handler_only_chord_handlers_skip_the_working_pattern_update()
  isolated(function(env)
    local updated = {}
    for _, pair in ipairs(ALL_HANDLER_FIELDS) do
      local calls = run(env, pair[1], new_channel(SELECTED), 1, {})
      local names = {}
      for _, call in ipairs(calls) do table.insert(names, call[1]) end
      updated[pair[1]] = names
    end
    -- characterisation: lines 1015, 1067, 1119, 1193 update; the chord handlers (1235-1244,
    -- 1285-1294, 1328-1337, 1378-1387) only set the mask.
    luaunit.assert_equals(updated, {
      handle_trig_mask_change = {"program.set_trig_mask", "pattern.update_working_pattern"},
      handle_note_mask_change = {"program.set_note_mask", "pattern.update_working_pattern"},
      handle_velocity_mask_change = {"program.set_velocity_mask", "pattern.update_working_pattern"},
      handle_length_mask_change = {"program.set_length_mask", "pattern.update_working_pattern"},
      handle_chord_mask_one_change = {"program.set_chord_one_mask"},
      handle_chord_mask_two_change = {"program.set_chord_two_mask"},
      handle_chord_mask_three_change = {"program.set_chord_three_mask"},
      handle_chord_mask_four_change = {"program.set_chord_four_mask"}
    })
  end)
end

function test_mask_handler_only_chord_three_decrement_bypasses_the_recorder()
  isolated(function(env)
    local sinks = {}
    for _, pair in ipairs(ALL_HANDLER_FIELDS) do
      local calls = run(env, pair[1], new_channel(SELECTED), -1, {{5, 5}})
      luaunit.assert_equals(#calls, 1)
      sinks[pair[1]] = calls[1][1]
    end
    -- characterisation: line 1322 is the only held-step write that is not a recorder portion
    luaunit.assert_equals(sinks, {
      handle_trig_mask_change = "recorder.add_note_mask_event_portion",
      handle_note_mask_change = "recorder.add_note_mask_event_portion",
      handle_velocity_mask_change = "recorder.add_note_mask_event_portion",
      handle_length_mask_change = "recorder.add_note_mask_event_portion",
      handle_chord_mask_one_change = "recorder.add_note_mask_event_portion",
      handle_chord_mask_two_change = "recorder.add_note_mask_event_portion",
      handle_chord_mask_three_change = "memory.record_event",
      handle_chord_mask_four_change = "recorder.add_note_mask_event_portion"
    })
  end)
end

function test_mask_handler_isolation_restores_globals_after_a_failure()
  local before = {}
  for k, v in pairs(_G) do before[k] = v end
  local ok = pcall(isolated, function(env)
    leaked_by_mask_handler_test = true
    m_clock = {}
    error("boom")
  end)
  luaunit.assert_false(ok)
  luaunit.assert_nil(leaked_by_mask_handler_test)
  local after = {}
  for k, v in pairs(_G) do after[k] = v end
  for k, v in pairs(before) do luaunit.assert_is(after[k], v, k) end
  for k in pairs(after) do luaunit.assert_not_nil(before[k], k) end
end

------------------------------------------------------------------------------------------------
-- One explicit test per handler per generic scenario.
------------------------------------------------------------------------------------------------

-- trig
function test_mask_handler_trig_unheld_increment() unheld_increment("trig") end
function test_mask_handler_trig_unheld_decrement() unheld_decrement("trig") end
function test_mask_handler_trig_unheld_increment_from_unset() unheld_increment_from_unset("trig") end
function test_mask_handler_trig_unheld_decrement_to_minus_one() unheld_decrement_to_minus_one("trig") end
function test_mask_handler_trig_unheld_decrement_from_unset() unheld_decrement_from_unset("trig") end
function test_mask_handler_trig_unheld_clamps_at_max() unheld_clamps_at_max("trig") end
function test_mask_handler_trig_unheld_clamps_at_min() unheld_clamps_at_min("trig") end
function test_mask_handler_trig_direction_zero_decrements() direction_zero_decrements("trig") end
function test_mask_handler_trig_held_increment() held_increment("trig") end
function test_mask_handler_trig_held_decrement() held_decrement("trig") end
function test_mask_handler_trig_held_decrement_to_minus_one() held_decrement_to_minus_one("trig") end
function test_mask_handler_trig_held_selector_is_independent() held_selector_is_independent("trig") end
function test_mask_handler_trig_held_on_unselected_channel() held_on_unselected_channel("trig") end
function test_mask_handler_trig_held_row_boundaries() held_row_boundaries("trig") end
function test_mask_handler_trig_only_first_key_row_checked() only_first_key_row_checked("trig") end
function test_mask_handler_trig_velocity_write_precedes_recorder() velocity_write_precedes_recorder("trig") end

-- note
function test_mask_handler_note_unheld_increment() unheld_increment("note") end
function test_mask_handler_note_unheld_decrement() unheld_decrement("note") end
function test_mask_handler_note_unheld_increment_from_unset() unheld_increment_from_unset("note") end
function test_mask_handler_note_unheld_decrement_to_minus_one() unheld_decrement_to_minus_one("note") end
function test_mask_handler_note_unheld_decrement_from_unset() unheld_decrement_from_unset("note") end
function test_mask_handler_note_unheld_clamps_at_max() unheld_clamps_at_max("note") end
function test_mask_handler_note_unheld_clamps_at_min() unheld_clamps_at_min("note") end
function test_mask_handler_note_direction_zero_decrements() direction_zero_decrements("note") end
function test_mask_handler_note_held_increment() held_increment("note") end
function test_mask_handler_note_held_decrement() held_decrement("note") end
function test_mask_handler_note_held_decrement_to_minus_one() held_decrement_to_minus_one("note") end
function test_mask_handler_note_held_selector_is_independent() held_selector_is_independent("note") end
function test_mask_handler_note_held_on_unselected_channel() held_on_unselected_channel("note") end
function test_mask_handler_note_held_row_boundaries() held_row_boundaries("note") end
function test_mask_handler_note_only_first_key_row_checked() only_first_key_row_checked("note") end
function test_mask_handler_note_velocity_write_precedes_recorder() velocity_write_precedes_recorder("note") end

-- velocity
function test_mask_handler_velocity_unheld_increment() unheld_increment("velocity") end
function test_mask_handler_velocity_unheld_decrement() unheld_decrement("velocity") end
function test_mask_handler_velocity_unheld_increment_from_unset() unheld_increment_from_unset("velocity") end
function test_mask_handler_velocity_unheld_decrement_to_minus_one() unheld_decrement_to_minus_one("velocity") end
function test_mask_handler_velocity_unheld_decrement_from_unset() unheld_decrement_from_unset("velocity") end
function test_mask_handler_velocity_unheld_clamps_at_max() unheld_clamps_at_max("velocity") end
function test_mask_handler_velocity_unheld_clamps_at_min() unheld_clamps_at_min("velocity") end
function test_mask_handler_velocity_direction_zero_decrements() direction_zero_decrements("velocity") end
function test_mask_handler_velocity_held_increment() held_increment("velocity") end
function test_mask_handler_velocity_held_decrement() held_decrement("velocity") end
function test_mask_handler_velocity_held_decrement_to_minus_one() held_decrement_to_minus_one("velocity") end
function test_mask_handler_velocity_held_selector_is_independent() held_selector_is_independent("velocity") end
function test_mask_handler_velocity_held_on_unselected_channel() held_on_unselected_channel("velocity") end
function test_mask_handler_velocity_held_row_boundaries() held_row_boundaries("velocity") end
function test_mask_handler_velocity_only_first_key_row_checked() only_first_key_row_checked("velocity") end
function test_mask_handler_velocity_velocity_write_precedes_recorder() velocity_write_precedes_recorder("velocity") end

-- chord_one
function test_mask_handler_chord_one_unheld_increment() unheld_increment("chord_one") end
function test_mask_handler_chord_one_unheld_decrement() unheld_decrement("chord_one") end
function test_mask_handler_chord_one_unheld_increment_from_unset() unheld_increment_from_unset("chord_one") end
function test_mask_handler_chord_one_unheld_decrement_to_minus_one() unheld_decrement_to_minus_one("chord_one") end
function test_mask_handler_chord_one_unheld_decrement_from_unset() unheld_decrement_from_unset("chord_one") end
function test_mask_handler_chord_one_unheld_clamps_at_max() unheld_clamps_at_max("chord_one") end
function test_mask_handler_chord_one_unheld_clamps_at_min() unheld_clamps_at_min("chord_one") end
function test_mask_handler_chord_one_direction_zero_decrements() direction_zero_decrements("chord_one") end
function test_mask_handler_chord_one_held_increment() held_increment("chord_one") end
function test_mask_handler_chord_one_held_decrement() held_decrement("chord_one") end
function test_mask_handler_chord_one_held_decrement_to_minus_one() held_decrement_to_minus_one("chord_one") end
function test_mask_handler_chord_one_held_selector_is_independent() held_selector_is_independent("chord_one") end
function test_mask_handler_chord_one_held_on_unselected_channel() held_on_unselected_channel("chord_one") end
function test_mask_handler_chord_one_held_row_boundaries() held_row_boundaries("chord_one") end
function test_mask_handler_chord_one_only_first_key_row_checked() only_first_key_row_checked("chord_one") end
function test_mask_handler_chord_one_velocity_write_precedes_recorder() velocity_write_precedes_recorder("chord_one") end

-- chord_two
function test_mask_handler_chord_two_unheld_increment() unheld_increment("chord_two") end
function test_mask_handler_chord_two_unheld_decrement() unheld_decrement("chord_two") end
function test_mask_handler_chord_two_unheld_increment_from_unset() unheld_increment_from_unset("chord_two") end
function test_mask_handler_chord_two_unheld_decrement_to_minus_one() unheld_decrement_to_minus_one("chord_two") end
function test_mask_handler_chord_two_unheld_decrement_from_unset() unheld_decrement_from_unset("chord_two") end
function test_mask_handler_chord_two_unheld_clamps_at_max() unheld_clamps_at_max("chord_two") end
function test_mask_handler_chord_two_unheld_clamps_at_min() unheld_clamps_at_min("chord_two") end
function test_mask_handler_chord_two_direction_zero_decrements() direction_zero_decrements("chord_two") end
function test_mask_handler_chord_two_held_increment() held_increment("chord_two") end
function test_mask_handler_chord_two_held_decrement() held_decrement("chord_two") end
function test_mask_handler_chord_two_held_decrement_to_minus_one() held_decrement_to_minus_one("chord_two") end
function test_mask_handler_chord_two_held_selector_is_independent() held_selector_is_independent("chord_two") end
function test_mask_handler_chord_two_held_on_unselected_channel() held_on_unselected_channel("chord_two") end
function test_mask_handler_chord_two_held_row_boundaries() held_row_boundaries("chord_two") end
function test_mask_handler_chord_two_only_first_key_row_checked() only_first_key_row_checked("chord_two") end
function test_mask_handler_chord_two_velocity_write_precedes_recorder() velocity_write_precedes_recorder("chord_two") end

-- chord_three
function test_mask_handler_chord_three_unheld_increment() unheld_increment("chord_three") end
function test_mask_handler_chord_three_unheld_decrement() unheld_decrement("chord_three") end
function test_mask_handler_chord_three_unheld_increment_from_unset() unheld_increment_from_unset("chord_three") end
function test_mask_handler_chord_three_unheld_decrement_to_minus_one() unheld_decrement_to_minus_one("chord_three") end
function test_mask_handler_chord_three_unheld_decrement_from_unset() unheld_decrement_from_unset("chord_three") end
function test_mask_handler_chord_three_unheld_clamps_at_max() unheld_clamps_at_max("chord_three") end
function test_mask_handler_chord_three_unheld_clamps_at_min() unheld_clamps_at_min("chord_three") end
function test_mask_handler_chord_three_direction_zero_decrements() direction_zero_decrements("chord_three") end
function test_mask_handler_chord_three_held_increment() held_increment("chord_three") end
function test_mask_handler_chord_three_held_decrement() held_decrement("chord_three") end
function test_mask_handler_chord_three_held_decrement_to_minus_one() held_decrement_to_minus_one("chord_three") end
function test_mask_handler_chord_three_held_selector_is_independent() held_selector_is_independent("chord_three") end
function test_mask_handler_chord_three_held_on_unselected_channel() held_on_unselected_channel("chord_three") end
function test_mask_handler_chord_three_held_row_boundaries() held_row_boundaries("chord_three") end
function test_mask_handler_chord_three_only_first_key_row_checked() only_first_key_row_checked("chord_three") end
function test_mask_handler_chord_three_velocity_write_precedes_recorder() velocity_write_precedes_recorder("chord_three") end

-- chord_four
function test_mask_handler_chord_four_unheld_increment() unheld_increment("chord_four") end
function test_mask_handler_chord_four_unheld_decrement() unheld_decrement("chord_four") end
function test_mask_handler_chord_four_unheld_increment_from_unset() unheld_increment_from_unset("chord_four") end
function test_mask_handler_chord_four_unheld_decrement_to_minus_one() unheld_decrement_to_minus_one("chord_four") end
function test_mask_handler_chord_four_unheld_decrement_from_unset() unheld_decrement_from_unset("chord_four") end
function test_mask_handler_chord_four_unheld_clamps_at_max() unheld_clamps_at_max("chord_four") end
function test_mask_handler_chord_four_unheld_clamps_at_min() unheld_clamps_at_min("chord_four") end
function test_mask_handler_chord_four_direction_zero_decrements() direction_zero_decrements("chord_four") end
function test_mask_handler_chord_four_held_increment() held_increment("chord_four") end
function test_mask_handler_chord_four_held_decrement() held_decrement("chord_four") end
function test_mask_handler_chord_four_held_decrement_to_minus_one() held_decrement_to_minus_one("chord_four") end
function test_mask_handler_chord_four_held_selector_is_independent() held_selector_is_independent("chord_four") end
function test_mask_handler_chord_four_held_on_unselected_channel() held_on_unselected_channel("chord_four") end
function test_mask_handler_chord_four_held_row_boundaries() held_row_boundaries("chord_four") end
function test_mask_handler_chord_four_only_first_key_row_checked() only_first_key_row_checked("chord_four") end
function test_mask_handler_chord_four_velocity_write_precedes_recorder() velocity_write_precedes_recorder("chord_four") end

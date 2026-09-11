-- Behavioural tests closing observable gaps left by the Lua mutation campaign in
-- lib/m_midi.lua, lib/models/program.lua and lib/controls/sequencer.lua.
--
-- Every test pins what a collaborator receives (MIDI messages, handler arguments,
-- LED calls) or what a public function returns. Each test restores every global
-- it replaces (and removes any global it creates) even when it fails, and resets
-- program/params state it touched, so later test files are unaffected.
-- README references are README.md line numbers; anything else is labelled
-- `-- characterisation`.

local M_MIDI = "mosaic/lib/m_midi"
local sequencer_control = include("mosaic/lib/controls/sequencer")

-- Snapshot the whole of _G (plus util.time and params' store), run body, then
-- restore every changed global and remove every new one.
local function isolated(body)
  local before = {}
  for k, v in pairs(_G) do before[k] = v end
  local saved_time = util.time
  local saved_param_store = param_store
  local copied_params = {}
  for id, p in pairs(param_store or {}) do
    local c = {}
    for k, v in pairs(p) do c[k] = v end
    copied_params[id] = c
  end
  local saved_program = program.get()
  param_store = copied_params
  local ok, err = pcall(body)
  local keys = {}
  for k in pairs(_G) do keys[#keys + 1] = k end
  for _, k in ipairs(keys) do
    if before[k] == nil then _G[k] = nil end
  end
  for k, v in pairs(before) do
    if rawget(_G, k) ~= v then _G[k] = v end
  end
  util.time = saved_time
  param_store = saved_param_store
  if saved_program and saved_program.nrpn_policy_version == 1 and
      not (saved_program.memory and saved_program.memory.serialized) then
    program.set(saved_program)
  else
    program.init()
  end
  if not ok then error(err, 0) end
end

-- ---------------------------------------------------------------------------
-- m_midi: output helpers and device loops
-- ---------------------------------------------------------------------------

local function recording_device(sent, id, fields)
  local d = fields or {}
  local function log(kind, ...) sent[#sent + 1] = {id, kind, ...} end
  d.note_on = function(_, note, velocity, channel) log("note_on", note, velocity, channel) end
  d.note_off = function(_, note, velocity, channel) log("note_off", note, velocity, channel) end
  d.cc = function(_, number, value, channel) log("cc", number, value, channel) end
  d.program_change = function(_, value, channel) log("program_change", value, channel) end
  d.start = function() log("start") end
  d.stop = function() log("stop") end
  return d
end

-- characterisation: Sinfonion commands reach a Norns2sinfonion port even when it
-- is the first MIDI port (README.md:1144 names the norns2sinfonion device).
function test_w3a_sinfonion_command_reaches_a_sinfonion_on_the_first_port()
  isolated(function()
    local m = include(M_MIDI)
    local sent = {}
    midi_devices = {recording_device(sent, 1, {name = "Norns2sinfonion"})}
    m.send_to_sinfonion(7, 42)
    luaunit.assert_equals(sent, {{1, "program_change", 42, 7}})
  end)
end

-- characterisation: resetting note counts forgets the first device's counts too.
function test_w3a_reset_note_counts_clears_the_first_device()
  isolated(function()
    local m = include(M_MIDI)
    local sent = {}
    midi_devices = {recording_device(sent, 1)}
    m:note_on(60, 100, 3, 1)
    luaunit.assert_equals(m.note_counts, {[1] = {[3] = {[60] = 1}}})
    m:reset_note_counts()
    luaunit.assert_equals(m.note_counts, {})
  end)
end

-- characterisation (MIDI 1.0 14-bit CC): MSB is value // 128, LSB value % 128.
function test_w3a_fourteen_bit_cc_msb_is_value_divided_by_128()
  isolated(function()
    local m = include(M_MIDI)
    local sent = {}
    midi_devices = {recording_device(sent, 1)}
    m.cc(1, 33, 128, 2, 1)
    m.cc(1, 33, 255, 2, 1)
    m.cc(1, 33, 16256, 2, 1)
    luaunit.assert_equals(sent, {
      {1, "cc", 1, 1, 2}, {1, "cc", 33, 0, 2},
      {1, "cc", 1, 1, 2}, {1, "cc", 33, 127, 2},
      {1, "cc", 1, 127, 2}, {1, "cc", 33, 0, 2}})
  end)
end

-- characterisation: transport Start and the connected query include port 1.
function test_w3a_start_and_connected_query_include_the_first_port()
  isolated(function()
    local m = include(M_MIDI)
    local sent = {}
    midi = {vports = {{}, {}}}
    midi_devices = {recording_device(sent, 1, {name = "a", device = {}}), recording_device(sent, 2, {name = "b"})}
    m.start()
    luaunit.assert_equals(sent, {{1, "start"}})
    luaunit.assert_equals(m.midi_devices_connected(), true)
  end)
end

-- ---------------------------------------------------------------------------
-- m_midi: MIDI mapping acceleration, per mapped-control family
-- ---------------------------------------------------------------------------

-- Loads a fresh m_midi (its acceleration state starts at time 0), registers the
-- mapping params with recording stubs, and returns a function that fires one
-- action at a given util.time and returns the scaled delta its handler received.
local function mapping_env()
  local m = include(M_MIDI)
  local env = {now = 0, actions = {}, ui = {}}
  local channels = {}
  for n = 1, 16 do channels[n] = {number = n} end
  program = {
    get = function() return {selected_song_pattern = 1} end,
    get_channel = function(_, n) return channels[n] end,
    get_selected_channel = function() return channels[2] end,
    get_selected_page = function() return 1 end,
  }
  params = {
    add_separator = function() end,
    add_group = function() end,
    add_control = function() end,
    set_action = function(_, id, action) env.actions[id] = action end,
    set = function() end,
  }
  controlspec = {new = function() return {} end}
  channel_edit_page_ui = setmetatable({}, {__index = function(_, name)
    return function(...) env.ui[#env.ui + 1] = {name, ...} end
  end})
  util.time = function() return env.now end
  m.set_up_midi_mapping_params()
  return function(id, now, delta_position)
    env.now = now
    env.ui = {}
    env.actions[id](1)
    for _, e in ipairs(env.ui) do
      if e[1]:match("^handle_") then return e[delta_position] end
    end
  end
end

-- One burst: the first action arrives exactly 0.15 s after time 0 (not longer
-- than the window, so it counts as rapid), 24 more arrive 0.125 s apart, then a
-- 0.25 s pause starts a new burst of five.
local function burst_times()
  local times = {0.15}
  local t = 0.15
  for _ = 1, 24 do t = t + 0.125; times[#times + 1] = t end
  t = t + 0.25; times[#times + 1] = t
  for _ = 1, 4 do t = t + 0.125; times[#times + 1] = t end
  return times
end

-- characterisation: the delta is multiplied by 1 until the fourth rapid action,
-- then grows by 0.5 per rapid action up to 10; a gap longer than 0.15 s restarts
-- the count. README.md:199 (relative binary-offset controls), README.md:211 (trig
-- params, masks and channel memory are mappable).
local EXPECTED_BURST = {
  1, 1, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10, 10, 10, 10,
  1, 1, 1, 1, 1.5}

local function assert_burst(id, delta_position)
  isolated(function()
    local fire = mapping_env()
    local got = {}
    for i, t in ipairs(burst_times()) do got[i] = fire(id, t, delta_position) end
    luaunit.assert_equals(got, EXPECTED_BURST, id)
  end)
end

function test_w3a_selected_channel_mask_map_acceleration()
  assert_burst("sel_ch_trig", 3)
end

function test_w3a_channel_mask_map_acceleration()
  assert_burst("ch3_note", 3)
end

function test_w3a_selected_channel_trig_param_map_acceleration()
  assert_burst("sel_ch_trig_param_1", 2)
end

function test_w3a_channel_trig_param_map_acceleration()
  assert_burst("ch_4_trig_param_2", 2)
end

function test_w3a_selected_channel_memory_map_acceleration()
  assert_burst("sel_ch_memory", 3)
end

function test_w3a_channel_memory_map_acceleration()
  assert_burst("ch5_memory", 3)
end

-- ---------------------------------------------------------------------------
-- m_midi: chord length bookkeeping across a stale release
-- ---------------------------------------------------------------------------

-- README.md:239: a chord's length runs from the first key press to the final key
-- release. Human decision 2026-09-11 (bugs.json same-key-two-sources-chord, was S9 and
-- S38): the same key held from two sources is two holders of one chord; the first
-- source's release does not end the chord, a new key on the step joins it, the other
-- source's release records nothing, and the final release records one length for the
-- whole chord (2 s = 16 here).
function test_w3a_same_key_from_two_sources_keeps_one_chord_to_the_final_release()
  isolated(function()
    local sent, recorded = {}, {}
    local now = 100
    local real_include = include
    include = function(path)
      if path == "mosaic/lib/step" then
        return {
          calculate_step_transpose = function() return 0 end,
          calculate_step_scale_number = function() return 1 end,
          manually_calculate_step_scale_number = function() return 1 end,
        }
      end
      if path == "mosaic/lib/quantiser" then
        return {
          process_with_global_params = function() return 0 end,
          get_chord_degree = function(note, root) return note - root end,
        }
      end
      return real_include(path)
    end
    local m = real_include(M_MIDI)
    include = real_include
    local channel = {number = 1, step_scale_number = 1, start_trig = {1, 4}, end_trig = {16, 7},
      clock_mods = {type = "clock_multiplication", value = 1}}
    program = {
      get = function() return {selected_song_pattern = 2, devices = {[1] = {midi_channel = 1, midi_device = 1, device_map = "midi"}}} end,
      get_channel = function() return channel end,
      get_selected_channel = function() return channel end,
      get_current_step_for_channel = function() return 1 end,
    }
    device_map = {get_device = function() return {} end}
    recorder = {
      handle_note_midi_message = function() end,
      add_note_mask_event_portion = function(c, s, payload) recorded[#recorded + 1] = {"portion", c, s, payload} end,
      record_stored_note_mask_events = function(c, s) recorded[#recorded + 1] = {"commit", c, s} end,
    }
    params = {get = function(_, id)
      if id == "record" then return 2 end
      if id == "midi_scale_mapped_to_white_keys" then return 1 end
    end}
    m_grid = {get_pressed_keys = function() return {} end}
    clock = {get_tempo = function() return 120 end}
    m_clock = {calculate_divisor = function() return 4 end}
    util.time = function() return now end
    midi_devices = {recording_device(sent, 1, {name = "out"})}
    local keyboard_a, keyboard_b = {}, {}

    handle_midi_event_data({0x90, 60, 100}, keyboard_a)
    handle_midi_event_data({0x90, 60, 100}, keyboard_b)
    now = 100.5
    handle_midi_event_data({0x80, 60, 0}, keyboard_a)
    luaunit.assert_equals(recorded, {})
    now = 101
    handle_midi_event_data({0x90, 64, 100}, keyboard_a)
    now = 101.25
    handle_midi_event_data({0x80, 60, 0}, keyboard_b)
    luaunit.assert_equals(recorded, {})
    luaunit.assert_equals(sent[#sent], {1, "note_off", 60, 0, 1})
    now = 102
    handle_midi_event_data({0x80, 64, 0}, keyboard_a)
    luaunit.assert_equals(recorded, {
      {"portion", 1, 1, {song_pattern = 2, data = {step = 1, length = 16}}}, {"commit", 1, 1}})
    luaunit.assert_equals(sent[#sent], {1, "note_off", 64, 0, 1})
  end)
end

-- ---------------------------------------------------------------------------
-- program
-- ---------------------------------------------------------------------------

-- README.md:546: "existing projects preserve their historical output". Loading a
-- project without an NRPN policy marks each NRPN control of a present MIDI device
-- map as legacy-half; without a device map module the fallback is device-scoped.
function test_w3a_program_set_migrates_legacy_nrpn_modes_through_the_device_map()
  isolated(function()
    local asked = {}
    device_map = {get_device = function(name)
      asked[#asked + 1] = name
      return {type = "midi", id = "synth", params = {{id = "cutoff", nrpn_msb = 0, nrpn_lsb = 74}, {id = "cc1", cc_msb = 1}}}
    end}
    program.set({devices = {[1] = {device_map = "synth_map"}}})
    luaunit.assert_equals(asked, {"synth_map"})
    luaunit.assert_equals(program.get().nrpn_stored_modes, {[1] = {synth = {cutoff = "legacy-half"}}})
    luaunit.assert_equals(program.get().nrpn_policy_version, 1)

    device_map = nil
    program.set({devices = {[2] = {device_map = "gone_map"}}})
    -- characterisation
    luaunit.assert_equals(program.get().nrpn_stored_modes, {[2] = {gone_map = {["*"] = "legacy-half"}}})
  end)
end

-- characterisation: a parameter definition without a max clamps locks to 127.
function test_w3a_param_trig_lock_without_a_max_is_clamped_to_127()
  isolated(function()
    local channel = {step_trig_lock_banks = {}, trig_lock_params = {[1] = {}}}
    program.add_step_param_trig_lock_to_channel(channel, 3, 1, 128)
    luaunit.assert_equals(channel.step_trig_lock_banks[3][1], 127)
    program.add_step_param_trig_lock_to_channel(channel, 4, 1, 127)
    luaunit.assert_equals(channel.step_trig_lock_banks[4][1], 127)
  end)
end

-- characterisation: a slide on parameter slot 1 alone marks the step as sliding.
function test_w3a_step_has_param_slide_counts_slot_one()
  isolated(function()
    luaunit.assert_true(program.step_has_param_slide({step_trig_lock_slides = {[6] = {[1] = true}}}, 6))
  end)
end

-- characterisation: clearing a step on a channel without param-lock or slide tables
-- (tables are created lazily) clears the other locks without error.
function test_w3a_clear_trig_locks_for_step_tolerates_missing_lock_tables()
  isolated(function()
    program.init()
    program.get().selected_channel = 2
    local channel = program.get_selected_channel()
    channel.step_octave_trig_lock_banks[4] = 1
    channel.step_trig_lock_banks = nil
    channel.step_trig_lock_slides = nil
    program.clear_trig_locks_for_step(4)
    luaunit.assert_nil(channel.step_octave_trig_lock_banks[4])
    luaunit.assert_nil(channel.step_trig_lock_banks)
    luaunit.assert_nil(channel.step_trig_lock_slides)
  end)
end

-- characterisation: scales without a version get version 1 when set everywhere.
function test_w3a_set_all_song_pattern_scales_starts_unversioned_scales_at_one()
  isolated(function()
    program.init()
    program.get_song_pattern(1).scales[2].version = nil
    program.get_song_pattern(3).scales[2].version = nil
    local scale = {number = 7}
    program.set_all_song_pattern_scales(2, scale)
    luaunit.assert_equals(scale.version, 1)
    luaunit.assert_equals(program.get_song_pattern(3).scales[2].version, 1)
  end)
end

-- README.md:685: each channel can have its own shuffle basis; basis 1 is the
-- channel's own value, not the global one.
function test_w3a_channel_shuffle_basis_of_one_is_used()
  isolated(function()
    params:set("global_swing_shuffle_type", 2)
    params:set("global_shuffle_basis", 5)
    luaunit.assert_equals(program.get_effective_shuffle_basis({shuffle_basis = 1}), 1)
  end)
end

-- README.md:917: the channel length is capped at the global length counted from
-- the channel start.
function test_w3a_channel_step_bounds_cap_counts_from_the_start()
  isolated(function()
    program.init()
    program.get_selected_song_pattern().global_pattern_length = 8
    local a, b = program.get_channel_step_bounds({start_trig = {5, 4}, end_trig = {16, 7}})
    luaunit.assert_equals({a, b}, {5, 12})
    program.get_selected_song_pattern().global_pattern_length = 16
    a, b = program.get_channel_step_bounds({start_trig = {1, 4}, end_trig = {16, 7}})
    luaunit.assert_equals({a, b}, {1, 16})
  end)
end

-- A channel covering steps first..last with trigs on every step and the given locks
-- on parameter 1.
local function lock_channel(first, last, locks, trigless_steps)
  local trig_values = {}
  for s = 1, 64 do trig_values[s] = 1 end
  for _, s in ipairs(trigless_steps or {}) do trig_values[s] = 0 end
  local banks = {}
  for s, v in pairs(locks) do banks[s] = {[1] = v} end
  return {
    start_trig = {((first - 1) % 16) + 1, math.floor((first - 1) / 16) + 4},
    end_trig = {((last - 1) % 16) + 1, math.floor((last - 1) / 16) + 4},
    step_trig_lock_banks = banks,
    working_pattern = {trig_values = trig_values},
  }
end

local function with_slide_params(values, next_song_pattern, body)
  isolated(function()
    program.init()
    for id, v in pairs(values) do params:set(id, v) end
    step = {calculate_next_selected_song_pattern = function() return next_song_pattern end}
    body()
  end)
end

-- characterisation: a current step outside the channel range has no next lock.
function test_w3a_next_trig_lock_is_nil_before_the_channel_range()
  with_slide_params({wrap_param_slides = 1, song_mode = 1, trigless_locks = 2}, 1, function()
    luaunit.assert_nil(program.get_next_trig_lock_step(lock_channel(5, 8, {[7] = 50}), 2, 1))
  end)
end

-- README.md:1082: with Param Slides Wrap on, the search wraps back to an earlier
-- lock when the current song pattern repeats. characterisation: with song mode
-- off it always wraps; in song mode it wraps only if the next song pattern is
-- the current one.
function test_w3a_next_trig_lock_wraps_by_song_mode_and_next_pattern()
  local expected = {step = 2, value = 50, distance = 3, should_wrap = true}
  with_slide_params({wrap_param_slides = 2, song_mode = 1, trigless_locks = 2}, 2, function()
    luaunit.assert_equals(program.get_next_trig_lock_step(lock_channel(1, 4, {[2] = 50}), 3, 1), expected)
  end)
  with_slide_params({wrap_param_slides = 2, song_mode = 2, trigless_locks = 2}, 1, function()
    luaunit.assert_equals(program.get_next_trig_lock_step(lock_channel(1, 4, {[2] = 50}), 3, 1), expected)
  end)
  with_slide_params({wrap_param_slides = 2, song_mode = 2, trigless_locks = 2}, 2, function()
    luaunit.assert_nil(program.get_next_trig_lock_step(lock_channel(1, 4, {[2] = 50}), 3, 1))
  end)
end

-- characterisation: the next lock is found at distance 1 inside a range that does
-- not start at step 1, and a wrap from the last step lands on the first step.
function test_w3a_next_trig_lock_distance_within_an_offset_range()
  with_slide_params({wrap_param_slides = 1, song_mode = 1, trigless_locks = 2}, 1, function()
    luaunit.assert_equals(program.get_next_trig_lock_step(lock_channel(5, 8, {[7] = 50}), 6, 1),
      {step = 7, value = 50, distance = 1})
    luaunit.assert_equals(program.get_next_trig_lock_step(lock_channel(1, 4, {[4] = 60}), 3, 1),
      {step = 4, value = 60, distance = 1})
  end)
  with_slide_params({wrap_param_slides = 2, song_mode = 1, trigless_locks = 2}, 1, function()
    luaunit.assert_equals(program.get_next_trig_lock_step(lock_channel(5, 8, {[5] = 70}), 8, 1),
      {step = 5, value = 70, distance = 1, should_wrap = true})
  end)
end

-- README.md:760: an off lock is not a slide destination; README.md:1096: with
-- Trigless Locks off, a lock on a step without a trig is not honoured.
function test_w3a_next_trig_lock_skips_off_locks_and_inactive_trigless_locks()
  with_slide_params({wrap_param_slides = 1, song_mode = 1, trigless_locks = 1}, 1, function()
    luaunit.assert_nil(program.get_next_trig_lock_step(lock_channel(1, 8, {[4] = -1}), 3, 1, -1))
    luaunit.assert_nil(program.get_next_trig_lock_step(lock_channel(1, 8, {[4] = 30}, {4}), 3, 1, -1))
    luaunit.assert_equals(program.get_next_trig_lock_step(lock_channel(1, 8, {[4] = -1, [6] = 30}), 3, 1, -1),
      {step = 6, value = 30, distance = 3})
  end)
end

-- ---------------------------------------------------------------------------
-- sequencer control
-- ---------------------------------------------------------------------------

local function coords(s) return ((s - 1) % 16) + 1, math.floor((s - 1) / 16) + 4 end

local function draw_calls(mode, opts)
  local led = {}
  isolated(function()
    local control = sequencer_control:new(4, mode)
    local function pattern_from(trigs)
      local trig_values, lengths = {}, {}
      for s = 1, 64 do trig_values[s] = 0; lengths[s] = 1 end
      for s, len in pairs(trigs or {}) do trig_values[s] = 1; lengths[s] = len end
      return {trig_values = trig_values, lengths = lengths}
    end
    local sx, sy = coords(opts.start or 1)
    local ex, ey = coords(opts["end"] or 64)
    local channel = {number = 5, start_trig = {sx, sy}, end_trig = {ex, ey},
      working_pattern = pattern_from(opts.channel_trigs)}
    local selected_pattern = pattern_from(opts.pattern_trigs)
    program = {
      get_blink_state = function() return true end,
      get_selected_pattern = function() return selected_pattern end,
      get_selected_song_pattern = function() return {global_pattern_length = 64} end,
      get_current_step_for_channel = function() return 0 end,
    }
    channel_edit_page_ui = {should_show_step_has_trig_lock = function() return false end}
    m_clock = {is_playing = function() return false end}
    control:draw(channel, function(x, y, level) led[#led + 1] = {x, y, level} end)
  end)
  return led
end

local function background(from, to, level)
  local calls = {}
  for s = from, to do
    local x, y = coords(s)
    calls[#calls + 1] = {x, y, level}
  end
  return calls
end

local function concat(a, b)
  local out = {}
  for _, v in ipairs(a) do out[#out + 1] = v end
  for _, v in ipairs(b) do out[#out + 1] = v end
  return out
end

-- README.md:722: the active range is brighter; characterisation: a trig on the
-- channel's end step is lit at full brightness.
function test_w3a_channel_mode_trig_on_the_end_step_is_lit()
  local led = draw_calls("channel", {start = 5, ["end"] = 12, channel_trigs = {[12] = 1}})
  luaunit.assert_equals(led, concat(background(5, 12, 2), {{12, 4, 15}}))
end

-- README.md:397 (bright trigs, glowing length): a two-step note glows on one more step.
function test_w3a_pattern_mode_two_step_length_glows_one_step()
  local led = draw_calls("pattern", {pattern_trigs = {[1] = 2}})
  luaunit.assert_equals(led, concat(background(1, 64, 2), {{1, 4, 15}, {2, 4, 5}}))
end

-- characterisation: a long press resets a trig's length only on the control's
-- own four rows, including its first and last row.
function test_w3a_long_press_acts_only_on_its_own_four_rows()
  isolated(function()
    local pattern = {trig_values = {}, lengths = {}}
    for s = 1, 64 do pattern.trig_values[s] = 1; pattern.lengths[s] = 9 end
    program = {get_selected_pattern = function() return pattern end}
    local at4 = sequencer_control:new(4, "pattern")
    at4:long_press(2, 4)
    at4:long_press(3, 7)
    luaunit.assert_equals(pattern.lengths[2], 1)
    luaunit.assert_equals(pattern.lengths[51], 1)
    -- A control on rows 3-6 ignores row 7; one on rows 5-8 ignores row 4.
    sequencer_control:new(3, "pattern"):long_press(4, 7)
    sequencer_control:new(5, "pattern"):long_press(5, 4)
    luaunit.assert_equals(pattern.lengths[52], 9)
    luaunit.assert_equals(pattern.lengths[5], 9)
  end)
end

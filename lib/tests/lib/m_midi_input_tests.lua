-- Unit tests for the REAL lib/m_midi.lua: keyboard input, chord accumulation,
-- the MIDI-mapping acceleration window, the CC page-return timer and the
-- Stop / Panic / sweep note-count bookkeeping.
--
-- Every test loads a fresh copy of the module (so its file-local chord and
-- release state starts empty) with recording stubs for its collaborators, and
-- restores every global it replaces so other test files keep their mocks.
-- README references are to README.md line numbers:
--   193-195 MIDI keyboard input, 197 map scale to white keys,
--   200-213 MIDI controller mapping, 239 live record.

local SAVED_GLOBALS = {
  "program", "device_map", "recorder", "params", "m_grid", "clock", "m_clock",
  "channel_edit_page_ui", "midi", "midi_devices", "handle_midi_event_data",
  "scheduler", "controlspec", "include"
}

local function fake_device(env, id, fields)
  local d = fields or {}
  local function log(kind, ...)
    env.sent[#env.sent + 1] = {id, kind, ...}
  end
  d.note_on = function(_, note, velocity, channel) log("note_on", note, velocity, channel) end
  d.note_off = function(_, note, velocity, channel) log("note_off", note, velocity, channel) end
  d.program_change = function(_, value, channel) log("program_change", value, channel) end
  d.start = function() log("start") end
  d.stop = function() log("stop") end
  return d
end

local function make_channel(n)
  return {
    number = n,
    step_scale_number = 3,
    start_trig = {1, 4},
    end_trig = {16, 7},
    clock_mods = {type = "clock_multiplication", value = n}
  }
end

-- Build the environment, load the real module and run body(env, m).
local function with_midi(body)
  local saved = {}
  for _, name in ipairs(SAVED_GLOBALS) do saved[name] = _G[name] end
  local saved_time, saved_trim = util.time, util.trim_string_to_width

  local env = {
    now = 100, tempo = 120, divisor = 4, song_pattern = 2, selected = 1,
    program_page = 1, cep_page = 1, pressed = {}, steps = {},
    params = {record = 1, midi_scale_mapped_to_white_keys = 1},
    sent = {}, recorded = {}, quantised = {}, degrees = {}, step_calls = {},
    get_channel_calls = {}, divisor_calls = {}, ui = {}, runs = {}, cancels = {},
    sleeps = {}, param_log = {}, actions = {}, param_sets = {}, debounces = {},
    player_log = {}, degree_override = nil, next_run_id = 100
  }

  env.channels = {}
  for n = 1, 17 do env.channels[n] = make_channel(n) end
  env.devices = {}
  for n = 1, 17 do
    env.devices[n] = {midi_channel = n, midi_device = 1, device_map = "midi"}
  end
  env.devices[3] = {midi_channel = 5, midi_device = 2, device_map = "midi"}
  env.devices[4] = {midi_channel = 9, midi_device = 1, device_map = "nb_voice"}

  env.player = {
    note_on = function(self, note, velocity)
      assert(self == env.player, "player called without self")
      env.player_log[#env.player_log + 1] = {"on", note, velocity}
    end,
    note_off = function(self, note)
      assert(self == env.player, "player called without self")
      env.player_log[#env.player_log + 1] = {"off", note}
    end
  }

  local program_stub = {
    get = function()
      return {selected_song_pattern = env.song_pattern, selected_channel = env.selected, devices = env.devices}
    end,
    get_channel = function(song_pattern, n)
      env.get_channel_calls[#env.get_channel_calls + 1] = {song_pattern, n}
      if env.song_channels then return env.song_channels[song_pattern][n] end
      assert(song_pattern == env.song_pattern, "wrong song pattern")
      return env.channels[n]
    end,
    get_selected_channel = function() return env.channels[env.selected] end,
    get_current_step_for_channel = function(n) return env.steps[n] or 1 end,
    get_selected_page = function() return env.program_page end
  }

  local step_stub = {
    calculate_step_transpose = function(c)
      env.step_calls[#env.step_calls + 1] = {"transpose", c}
      return c * 100
    end,
    calculate_step_scale_number = function(c, s)
      env.step_calls[#env.step_calls + 1] = {"scale", c, s}
      return 5
    end,
    manually_calculate_step_scale_number = function(c, s)
      env.step_calls[#env.step_calls + 1] = {"manual_scale", c, s}
      return 7
    end
  }

  local quantiser_stub = {
    process_with_global_params = function(note_number, octave, transpose, scale)
      env.quantised[#env.quantised + 1] = {note_number, octave, transpose, scale}
      return 36 + note_number + 12 * octave
    end,
    get_chord_degree = function(note, root, scale)
      env.degrees[#env.degrees + 1] = {note, root, scale}
      if env.degree_override then return table.remove(env.degree_override, 1) end
      return note - root
    end
  }

  local ok, err = pcall(function()
    local real_include = saved.include
    include = function(path)
      if path == "mosaic/lib/step" then return step_stub end
      if path == "mosaic/lib/quantiser" then return quantiser_stub end
      return real_include(path)
    end
    local m = real_include("mosaic/lib/m_midi")
    include = real_include

    program = program_stub
    device_map = {
      get_device = function(name)
        if name == "midi" then return {} end
        if name == "nb_voice" then return {player = env.player} end
        error("unexpected device map " .. tostring(name))
      end
    }
    recorder = {
      handle_note_midi_message = function(note, velocity, voice, degree)
        env.recorded[#env.recorded + 1] = {"handle", {note = note, velocity = velocity, voice = voice, degree = degree}}
      end,
      add_note_mask_event_portion = function(c, s, payload)
        env.recorded[#env.recorded + 1] = {"portion", c, s, payload}
      end,
      record_stored_note_mask_events = function(c, s)
        env.recorded[#env.recorded + 1] = {"commit", c, s}
      end
    }
    params = {
      get = function(_, id) return env.params[id] end,
      set = function(_, id, value, silent)
        env.param_sets[#env.param_sets + 1] = {id, value, silent}
        env.ui[#env.ui + 1] = {"params_set", id, value, silent}
      end,
      add_separator = function(_, name) env.param_log[#env.param_log + 1] = {"separator", name} end,
      add_group = function(_, id, name, count) env.param_log[#env.param_log + 1] = {"group", id, name, count} end,
      add_control = function(_, id, name, spec, formatter)
        env.param_log[#env.param_log + 1] = {"control", id, name, spec, formatter}
      end,
      set_action = function(_, id, action)
        assert(env.actions[id] == nil, "duplicate action " .. id)
        env.actions[id] = action
      end
    }
    controlspec = {new = function(...) return {...} end}
    m_grid = {get_pressed_keys = function() return env.pressed end}
    util.time = function() return env.now end
    util.trim_string_to_width = function(s, width) return "trim(" .. s .. "," .. width .. ")" end
    clock = {
      get_tempo = function() return env.tempo end,
      run = function(f)
        env.next_run_id = env.next_run_id + 1
        env.runs[#env.runs + 1] = {id = env.next_run_id, f = f}
        return env.next_run_id
      end,
      cancel = function(id) env.cancels[#env.cancels + 1] = id end,
      sleep = function(s) env.sleeps[#env.sleeps + 1] = s end
    }
    m_clock = {
      calculate_divisor = function(mods)
        env.divisor_calls[#env.divisor_calls + 1] = mods
        return env.divisor
      end
    }
    local ui = {}
    setmetatable(ui, {__index = function(_, name)
      return function(...)
        env.ui[#env.ui + 1] = {name, ...}
        if name == "get_selected_page" then return env.cep_page end
        if name == "select_page" then env.cep_page = ... end
      end
    end})
    channel_edit_page_ui = ui
    scheduler = {
      debounce = function(func)
        local entry = {cos = {}}
        env.debounces[#env.debounces + 1] = entry
        return function(...)
          local args = {...}
          entry.cos[#entry.cos + 1] = coroutine.create(function() func(table.unpack(args)) end)
        end
      end
    }
    env.dev1 = fake_device(env, 1, {name = "keys", device = {}})
    env.dev2 = fake_device(env, 2, {name = "synth", device = {}})
    midi = {vports = {{}, {}}}
    midi_devices = {env.dev1, env.dev2}
    body(env, m)
  end)

  for _, name in ipairs(SAVED_GLOBALS) do _G[name] = saved[name] end
  util.time, util.trim_string_to_width = saved_time, saved_trim
  if not ok then error(err, 0) end
end

local function press(env, key, velocity, source, status)
  handle_midi_event_data({status or 0x90, key, velocity}, source)
end

local function release(env, key, source, status)
  handle_midi_event_data({status or 0x80, key, 64}, source)
end

local function handles(env)
  local out = {}
  for _, r in ipairs(env.recorded) do
    if r[1] == "handle" then out[#out + 1] = r[2] end
  end
  return out
end

local function portions(env)
  local out = {}
  for _, r in ipairs(env.recorded) do
    if r[1] ~= "handle" then out[#out + 1] = r end
  end
  return out
end

local function resume_times(co, n)
  for _ = 1, n do
    local ok, err = coroutine.resume(co)
    if not ok then error(err, 0) end
  end
end

-- ---------------------------------------------------------------------------
-- Keyboard input: routing and releases (README 193-197)
-- ---------------------------------------------------------------------------

-- README 193: "ensure you have your desired channel selected"; README 197: by
-- default "the keyboard plays the keys you press".
function test_midi_input_plays_raw_key_on_selected_channel_device_when_white_key_mapping_off()
  with_midi(function(env, m)
    env.selected = 3
    press(env, 61, 100, env.dev1)
    luaunit.assert_equals(env.sent, {{2, "note_on", 61, 100, 5}})
    luaunit.assert_equals(handles(env), {{note = 61, velocity = 100, voice = 1, degree = 0}})
    -- characterisation: the quantiser still runs with the midi_tables coordinates.
    luaunit.assert_equals(env.quantised, {{1, 0, 300, 5}})
    luaunit.assert_equals(env.step_calls, {{"transpose", 3}, {"scale", 3, 1}})
    luaunit.assert_equals(m.note_counts, {[2] = {[5] = {[61] = 1}}})
  end)
end

-- README 197: "Map scale to white keys" On maps the selected scale to the white
-- keys; the black-key and octave table below is characterisation.
function test_midi_input_white_key_mapping_on_sends_quantised_midi_table_coordinates()
  with_midi(function(env)
    env.params.midi_scale_mapped_to_white_keys = 2
    local keys = {0, 11, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 127}
    for _, key in ipairs(keys) do
      press(env, key, 90, env.dev1)
      release(env, key, env.dev1)
    end
    luaunit.assert_equals(env.quantised, {
      {0, -5, 100, 5}, {6, -5, 100, 5},
      {0, 0, 100, 5}, {1, 0, 100, 5}, {1, 0, 100, 5}, {2, 0, 100, 5},
      {2, 0, 100, 5}, {3, 0, 100, 5}, {4, 0, 100, 5}, {4, 0, 100, 5},
      {5, 0, 100, 5}, {5, 0, 100, 5}, {6, 0, 100, 5}, {6, 0, 100, 5},
      {0, 1, 100, 5}, {4, 5, 100, 5}})
    -- The stub returns 36 + degree + 12 * octave; that value, not the key, is played.
    luaunit.assert_equals(env.sent[1], {1, "note_on", 0, 90, 1})
    luaunit.assert_equals(env.sent[5], {1, "note_on", 36, 90, 1})
    luaunit.assert_equals(env.sent[6], {1, "note_off", 36, 0, 1})
    luaunit.assert_equals(env.sent[#env.sent - 1], {1, "note_on", 100, 90, 1})
    luaunit.assert_equals(env.sent[#env.sent], {1, "note_off", 100, 0, 1})
  end)
end

-- characterisation (MIDI 1.0 convention, norns midi.to_msg): Note On with zero
-- velocity releases, and the caller's packet is not rewritten.
function test_midi_input_note_on_with_zero_velocity_is_a_release_and_leaves_packet_intact()
  with_midi(function(env)
    press(env, 60, 1, env.dev1, 0x91)
    local packet = {0x91, 60, 0}
    handle_midi_event_data(packet, env.dev1)
    luaunit.assert_equals(packet, {0x91, 60, 0})
    luaunit.assert_equals(env.sent, {{1, "note_on", 60, 1, 1}, {1, "note_off", 60, 0, 1}})
    luaunit.assert_equals(handles(env), {{note = 60, velocity = 1, voice = 1, degree = 0}})
    local on_packet = {0x9F, 62, 5}
    handle_midi_event_data(on_packet, env.dev1)
    luaunit.assert_equals(on_packet, {0x9F, 62, 5})
    luaunit.assert_equals(env.sent[3], {1, "note_on", 62, 5, 1})
  end)
end

-- README 193: the selected channel is the target whatever MIDI channel the keyboard uses.
function test_midi_input_any_input_channel_targets_the_selected_channel()
  with_midi(function(env)
    env.selected = 2
    press(env, 60, 70, env.dev1, 0x90)
    press(env, 62, 71, env.dev1, 0x9A)
    press(env, 64, 72, env.dev1, 0x9F)
    luaunit.assert_equals(env.sent, {
      {1, "note_on", 60, 70, 2}, {1, "note_on", 62, 71, 2}, {1, "note_on", 64, 72, 2}})
  end)
end

-- characterisation: a release is owned by the (device, MIDI channel, key) that pressed it.
function test_midi_input_release_is_owned_by_source_device_and_input_channel()
  with_midi(function(env, m)
    local other = {}
    press(env, 60, 100, env.dev1, 0x90)
    release(env, 60, other, 0x80)
    release(env, 60, env.dev1, 0x81)
    handle_midi_event_data({0x91, 60, 0}, env.dev1)
    luaunit.assert_equals(env.sent, {{1, "note_on", 60, 100, 1}})
    release(env, 60, env.dev1, 0x80)
    luaunit.assert_equals(env.sent, {{1, "note_on", 60, 100, 1}, {1, "note_off", 60, 0, 1}})
    release(env, 60, env.dev1, 0x80)
    luaunit.assert_equals(#env.sent, 2)
    luaunit.assert_equals(m.note_counts, {[1] = {[1] = {}}})
  end)
end

-- characterisation: the same key from two sources is two independent notes.
function test_midi_input_same_key_from_two_sources_releases_independently()
  with_midi(function(env, m)
    local keyboard_b = {}
    press(env, 60, 100, env.dev1)
    press(env, 60, 90, keyboard_b)
    luaunit.assert_equals(m.note_counts[1][1][60], 2)
    release(env, 60, keyboard_b)
    luaunit.assert_equals(env.sent[3], {1, "note_off", 60, 0, 1})
    luaunit.assert_equals(m.note_counts[1][1][60], 1)
    release(env, 60, env.dev1)
    luaunit.assert_equals(env.sent[4], {1, "note_off", 60, 0, 1})
    luaunit.assert_nil(m.note_counts[1][1][60])
  end)
end

-- characterisation: an absent source (nil device) is its own owner.
function test_midi_input_nil_source_owns_its_release()
  with_midi(function(env)
    press(env, 60, 100, nil)
    release(env, 60, env.dev1)
    luaunit.assert_equals(#env.sent, 1)
    release(env, 60, nil)
    luaunit.assert_equals(env.sent[2], {1, "note_off", 60, 0, 1})
  end)
end

-- characterisation: a release goes to the channel/device that played the note,
-- even after another channel (or the scale channel 17) is selected.
function test_midi_input_release_follows_the_channel_that_played_the_note()
  with_midi(function(env)
    env.selected = 3
    press(env, 60, 100, env.dev1)
    env.selected = 17
    env.get_channel_calls = {}
    release(env, 60, env.dev1)
    luaunit.assert_equals(env.get_channel_calls[1], {2, 3})
    luaunit.assert_equals(env.sent, {{2, "note_on", 60, 100, 5}, {2, "note_off", 60, 0, 5}})
  end)
end

-- characterisation: channel 17 (the scale channel) takes no keyboard input.
function test_midi_input_scale_channel_selected_ignores_keys()
  with_midi(function(env, m)
    env.selected = 17
    press(env, 60, 100, env.dev1)
    luaunit.assert_equals(env.sent, {})
    luaunit.assert_equals(env.recorded, {})
    luaunit.assert_equals(env.quantised, {})
    luaunit.assert_equals(env.step_calls, {})
    luaunit.assert_equals(m.note_counts, {})
    env.selected = 1
    release(env, 60, env.dev1)
    luaunit.assert_equals(env.sent, {})
  end)
end

-- characterisation: a key outside 0-127 is dropped; an unowned release is silent.
function test_midi_input_out_of_range_key_and_unowned_release_send_nothing()
  with_midi(function(env)
    press(env, 128, 100, env.dev1)
    release(env, 128, env.dev1)
    release(env, 50, env.dev1)
    luaunit.assert_equals(env.sent, {})
    luaunit.assert_equals(env.recorded, {})
    luaunit.assert_equals(env.quantised, {})
  end)
end

-- characterisation: non-note, non-CC messages do nothing.
function test_midi_input_other_message_types_send_nothing()
  with_midi(function(env)
    handle_midi_event_data({0xA0, 60, 10}, env.dev1)
    handle_midi_event_data({0xE0, 0, 64}, env.dev1)
    luaunit.assert_equals(env.sent, {})
    luaunit.assert_equals(env.recorded, {})
    luaunit.assert_equals(env.runs, {})
  end)
end

-- characterisation: an n.b. player voice receives normalised velocity (v-1)/126.
function test_midi_input_player_device_receives_normalised_velocity_and_release()
  with_midi(function(env)
    env.selected = 4
    press(env, 60, 127, env.dev1)
    press(env, 62, 1, env.dev1)
    press(env, 64, 64, env.dev1)
    release(env, 62, env.dev1)
    luaunit.assert_equals(env.player_log, {{"on", 60, 1.0}, {"on", 62, 0.0}, {"on", 64, 0.5}, {"off", 62}})
    luaunit.assert_equals(env.sent, {})
    luaunit.assert_equals(handles(env)[1], {note = 60, velocity = 127, voice = 1, degree = 0})
  end)
end

-- ---------------------------------------------------------------------------
-- Held grid step (README 193)
-- ---------------------------------------------------------------------------

-- README 193: "while holding the desired step, press the corresponding key".
-- The held step (rows 4-7) supplies the step and its scale number.
function test_midi_input_held_step_rows_four_to_seven_select_the_step()
  with_midi(function(env)
    env.params.record = 2
    env.steps[1] = 9
    local cases = {{{1, 4}, 1}, {{5, 6}, 37}, {{16, 7}, 64}}
    for i, case in ipairs(cases) do
      env.pressed = {case[1]}
      env.step_calls = {}
      env.recorded = {}
      env.now = 100
      press(env, 60 + i, 100, env.dev1)
      luaunit.assert_equals(env.step_calls, {{"transpose", 1}, {"manual_scale", 1, case[2]}})
      luaunit.assert_equals(env.quantised[#env.quantised][4], 7)
      luaunit.assert_equals(env.degrees[#env.degrees], {60 + i, 60 + i, 7})
      env.now = 100.5
      release(env, 60 + i, env.dev1)
      -- characterisation: with record armed the release commits a length at the held step.
      luaunit.assert_equals(portions(env), {
        {"portion", 1, case[2], {song_pattern = 2, data = {step = case[2], length = 4}}},
        {"commit", 1, case[2]}})
    end
  end)
end

-- characterisation: a held key outside rows 4-7 keeps the current step and uses
-- the channel's raw step_scale_number without calculating it.
function test_midi_input_held_key_outside_step_rows_uses_current_step_and_raw_scale()
  with_midi(function(env)
    env.params.record = 2
    env.steps[1] = 9
    for i, key in ipairs({{5, 3}, {5, 8}}) do
      env.pressed = {key}
      env.step_calls = {}
      env.recorded = {}
      press(env, 60 + i, 100, env.dev1)
      luaunit.assert_equals(env.step_calls, {{"transpose", 1}})
      luaunit.assert_equals(env.quantised[#env.quantised][4], 3)
      release(env, 60 + i, env.dev1)
      luaunit.assert_equals(portions(env)[1][3], 9)
    end
    env.pressed = {}
    env.step_calls = {}
    press(env, 70, 100, env.dev1)
    luaunit.assert_equals(env.step_calls, {{"transpose", 1}, {"scale", 1, 9}})
    luaunit.assert_equals(env.quantised[#env.quantised][4], 5)
  end)
end

-- README 193: "When setting on a per step basis, the length of these inputs
-- requires manual selection" -- with record off no length is committed.
function test_midi_input_held_step_without_record_commits_no_length()
  with_midi(function(env)
    env.pressed = {{5, 6}}
    press(env, 60, 100, env.dev1)
    env.now = 101
    release(env, 60, env.dev1)
    luaunit.assert_equals(portions(env), {})
    luaunit.assert_equals(handles(env), {{note = 60, velocity = 100, voice = 1, degree = 0}})
    luaunit.assert_equals(env.sent, {{1, "note_on", 60, 100, 1}, {1, "note_off", 60, 0, 1}})
  end)
end

-- ---------------------------------------------------------------------------
-- Chords (README 193 "chords", 239 one shared length)
-- ---------------------------------------------------------------------------

-- The first key is the root; later held keys are voices 2, 3 with degrees
-- measured from the root's played note.
function test_midi_input_chord_voices_count_up_with_degrees_from_the_root()
  with_midi(function(env)
    env.params.midi_scale_mapped_to_white_keys = 2
    press(env, 60, 100, env.dev1)
    press(env, 64, 101, env.dev1)
    press(env, 67, 102, env.dev1)
    luaunit.assert_equals(env.degrees, {{36, 36, 5}, {38, 36, 5}, {40, 36, 5}})
    luaunit.assert_equals(handles(env), {
      {note = 36, velocity = 100, voice = 1, degree = 0},
      {note = 38, velocity = 101, voice = 2, degree = 2},
      {note = 40, velocity = 102, voice = 3, degree = 4}})
  end)
end

-- characterisation: degrees outside -14..14 are sent to the recorder as nil.
function test_midi_input_chord_degree_outside_two_octaves_is_nil()
  with_midi(function(env)
    env.degree_override = {0, 14, -14, 15, -15}
    for key = 60, 64 do press(env, key, 100, env.dev1) end
    local degrees = {}
    for i, h in ipairs(handles(env)) do
      luaunit.assert_equals(h.voice, i)
      degrees[i] = h.degree == nil and "nil" or h.degree
    end
    luaunit.assert_equals(degrees, {0, 14, -14, "nil", "nil"})
  end)
end

-- characterisation: releasing a voice never frees its slot, and the root survives
-- the root key's release while another voice is held.
function test_midi_input_chord_voice_slots_are_never_reused_while_chord_is_held()
  with_midi(function(env)
    press(env, 60, 100, env.dev1)
    press(env, 64, 100, env.dev1)
    release(env, 60, env.dev1)
    press(env, 67, 100, env.dev1)
    release(env, 64, env.dev1)
    press(env, 72, 100, env.dev1)
    luaunit.assert_equals(handles(env), {
      {note = 60, velocity = 100, voice = 1, degree = 0},
      {note = 64, velocity = 100, voice = 2, degree = 4},
      {note = 67, velocity = 100, voice = 3, degree = 7},
      {note = 72, velocity = 100, voice = 4, degree = 12}})
    release(env, 67, env.dev1)
    release(env, 72, env.dev1)
    press(env, 62, 100, env.dev1)
    luaunit.assert_equals(handles(env)[5], {note = 62, velocity = 100, voice = 1, degree = 0})
  end)
end

-- README 239: "A recorded chord has one shared note length, measured from the
-- first key press to the final key release"; recorded once.
function test_midi_input_chord_length_is_recorded_once_at_the_last_release()
  with_midi(function(env)
    env.params.record = 2
    env.selected = 3
    env.steps[3] = 6
    env.now = 10
    press(env, 60, 100, env.dev1)
    env.now = 10.25
    press(env, 64, 100, env.dev1)
    env.now = 10.375
    release(env, 60, env.dev1)
    luaunit.assert_equals(portions(env), {})
    env.selected = 1
    env.now = 10.5
    release(env, 64, env.dev1)
    luaunit.assert_equals(portions(env), {
      {"portion", 3, 6, {song_pattern = 2, data = {step = 6, length = 4}}},
      {"commit", 3, 6}})
    luaunit.assert_equals(env.divisor_calls, {env.channels[3].clock_mods})
  end)
end

-- characterisation: duration * (tempo / 60) * divisor, snapped to the nearest
-- divisions.note_division_values entry; a tie keeps the shorter value.
function test_midi_input_recorded_length_snaps_to_nearest_note_division()
  with_midi(function(env)
    env.params.record = 2
    local cases = {
      {0, 120, 4, 1/24}, {0.1, 120, 4, 5/6}, {0.140625, 120, 4, 1}, {0.15625, 120, 4, 1.25},
      {0.25, 120, 8, 4}, {0.5, 60, 4, 2}, {0.25, 120, 2, 1}, {1000, 120, 4, 128}}
    for i, case in ipairs(cases) do
      env.recorded = {}
      env.tempo, env.divisor = case[2], case[3]
      env.now = 100
      press(env, 40 + i, 100, env.dev1)
      env.now = 100 + case[1]
      release(env, 40 + i, env.dev1)
      luaunit.assert_equals(portions(env)[1][4].data.length, case[4], "case " .. i)
    end
  end)
end

-- README 239: notes begun while armed commit their length on release even after
-- disarming; notes begun while disarmed commit nothing when armed later.
function test_midi_input_recording_is_decided_at_the_press()
  with_midi(function(env)
    env.params.record = 2
    press(env, 60, 100, env.dev1)
    env.params.record = 1
    env.now = 100.5
    release(env, 60, env.dev1)
    luaunit.assert_equals(portions(env), {
      {"portion", 1, 1, {song_pattern = 2, data = {step = 1, length = 4}}}, {"commit", 1, 1}})
    env.recorded = {}
    press(env, 62, 100, env.dev1)
    env.params.record = 2
    release(env, 62, env.dev1)
    luaunit.assert_equals(portions(env), {})
  end)
end

-- characterisation: armed and disarmed presses on one step are separate chords.
function test_midi_input_record_state_splits_chords_on_one_step()
  with_midi(function(env)
    press(env, 60, 100, env.dev1)
    env.params.record = 2
    press(env, 64, 100, env.dev1)
    luaunit.assert_equals(handles(env)[2], {note = 64, velocity = 100, voice = 1, degree = 0})
    env.params.record = 1
    press(env, 67, 100, env.dev1)
    luaunit.assert_equals(handles(env)[3], {note = 67, velocity = 100, voice = 2, degree = 7})
  end)
end

-- README 239: "quantised to align with the current step: the step active when
-- Mosaic processes the note-on" -- a key pressed on a later step starts a new chord.
function test_midi_input_keys_on_different_steps_are_separate_chords_with_own_lengths()
  with_midi(function(env)
    env.params.record = 2
    env.steps[1] = 1
    env.now = 100
    press(env, 60, 100, env.dev1)
    env.steps[1] = 2
    env.now = 100.125
    press(env, 64, 100, env.dev1)
    luaunit.assert_equals(handles(env)[2], {note = 64, velocity = 100, voice = 1, degree = 0})
    env.now = 100.25
    release(env, 64, env.dev1)
    env.now = 100.5
    release(env, 60, env.dev1)
    luaunit.assert_equals(portions(env), {
      {"portion", 1, 2, {song_pattern = 2, data = {step = 2, length = 1}}}, {"commit", 1, 2},
      {"portion", 1, 1, {song_pattern = 2, data = {step = 1, length = 4}}}, {"commit", 1, 1}})
  end)
end

-- README 239: one shared length to the final key release. Human decision 2026-09-11
-- (bugs.json same-key-two-sources-chord, was S9): the same key held from two sources
-- keeps the chord until both sources release it; the final release records the length.
function test_midi_input_same_key_from_two_sources_records_the_length_at_the_final_release()
  with_midi(function(env)
    env.params.record = 2
    local keyboard_b = {}
    press(env, 60, 100, env.dev1)
    press(env, 60, 100, keyboard_b)
    luaunit.assert_equals(handles(env)[2].voice, 2)
    env.now = 100.25
    release(env, 60, env.dev1)
    luaunit.assert_equals(portions(env), {})
    env.now = 100.5
    release(env, 60, keyboard_b)
    luaunit.assert_equals(portions(env), {
      {"portion", 1, 1, {song_pattern = 2, data = {step = 1, length = 4}}}, {"commit", 1, 1}})
    press(env, 64, 100, env.dev1)
    luaunit.assert_equals(handles(env)[3], {note = 64, velocity = 100, voice = 1, degree = 0})
  end)
end

-- Human decision 2026-09-11 (bugs.json repeated-note-on-stuck-note, was S8): a
-- second Note On for a held key from the same source (a merged keyboard) keeps the
-- first onset's release; each Note Off releases one onset, the latest first, and
-- no output onset stays counted.
function test_midi_input_repeated_note_on_keeps_a_release_for_each_output_onset()
  with_midi(function(env, m)
    env.selected = 3
    press(env, 60, 100, env.dev1)
    env.selected = 1
    press(env, 60, 90, env.dev1)
    release(env, 60, env.dev1)
    luaunit.assert_equals(env.sent[#env.sent], {1, "note_off", 60, 0, 1})
    release(env, 60, env.dev1)
    luaunit.assert_equals(env.sent, {
      {2, "note_on", 60, 100, 5}, {1, "note_on", 60, 90, 1},
      {1, "note_off", 60, 0, 1}, {2, "note_off", 60, 0, 5}})
    luaunit.assert_equals(m.note_counts, {[1] = {[1] = {}}, [2] = {[5] = {}}})
    -- Both records are consumed: a further release sends nothing.
    release(env, 60, env.dev1)
    luaunit.assert_equals(#env.sent, 4)
  end)
end

-- Human decision 2026-09-11 (bugs.json keyboard-chord-state-after-lost-release,
-- was S14): Stop resets keyboard chord state, so a key pressed on the same step
-- after a lost Note Off starts a new chord; the stale key's late release does not
-- end or measure that new chord.
function test_midi_input_stop_resets_a_held_chord()
  with_midi(function(env, m)
    env.params.record = 2
    env.now = 100
    press(env, 60, 100, env.dev1)
    m.stop()
    luaunit.assert_equals(env.sent, {
      {1, "note_on", 60, 100, 1}, {1, "note_off", 60, 0, 1}, {1, "stop"}, {2, "stop"}})
    press(env, 64, 100, env.dev1)
    luaunit.assert_equals(handles(env)[2], {note = 64, velocity = 100, voice = 1, degree = 0})
    env.now = 100.25
    release(env, 60, env.dev1)
    -- characterisation: the stale key still owns a release of its output note.
    luaunit.assert_equals(env.sent[#env.sent], {1, "note_off", 60, 0, 1})
    luaunit.assert_equals(portions(env), {})
    press(env, 67, 100, env.dev1)
    luaunit.assert_equals(handles(env)[3], {note = 67, velocity = 100, voice = 2, degree = 3})
    env.now = 100.5
    release(env, 64, env.dev1)
    release(env, 67, env.dev1)
    luaunit.assert_equals(portions(env), {
      {"portion", 1, 1, {song_pattern = 2, data = {step = 1, length = 4}}}, {"commit", 1, 1}})
  end)
end

function test_midi_input_panic_leaves_a_held_chord_open()
  with_midi(function(env, m)
    press(env, 60, 100, env.dev1)
    m.panic()
    luaunit.assert_equals(m.note_counts, {})
    press(env, 67, 100, env.dev1)
    -- characterisation (open question, gap-scan #14)
    luaunit.assert_equals(handles(env)[2], {note = 67, velocity = 100, voice = 2, degree = 7})
    env.steps[1] = 2
    press(env, 69, 100, env.dev1)
    luaunit.assert_equals(handles(env)[3], {note = 69, velocity = 100, voice = 1, degree = 0})
  end)
end

-- ---------------------------------------------------------------------------
-- CC page-return timer (m_midi.lua:216-236)
-- ---------------------------------------------------------------------------

-- characterisation: CC 1-20 on the channel edit page remembers the channel edit
-- sub-page and restores it two seconds after the last such CC.
function test_midi_input_cc_on_channel_edit_page_restores_sub_page_after_timer()
  with_midi(function(env)
    env.program_page = 2
    env.cep_page = 3
    handle_midi_event_data({0xB0, 1, 65}, env.dev1)
    luaunit.assert_equals(#env.runs, 1)
    luaunit.assert_equals(env.cancels, {})
    env.cep_page = 1
    handle_midi_event_data({0xB0, 20, 63}, env.dev1)
    luaunit.assert_equals(env.cancels, {101})
    luaunit.assert_equals(#env.runs, 2)
    env.ui = {}
    env.runs[2].f()
    luaunit.assert_equals(env.sleeps, {2})
    luaunit.assert_equals(env.ui, {{"select_page", 3}})
    luaunit.assert_equals(env.cep_page, 3)
    -- A stale timer that still runs after the restore selects nothing.
    env.ui = {}
    env.runs[1].f()
    luaunit.assert_equals(env.ui, {})
    -- After the restore the next CC captures the page afresh and cancels nothing.
    env.cep_page = 2
    handle_midi_event_data({0xB0, 5, 65}, env.dev1)
    luaunit.assert_equals(env.cancels, {101})
    env.ui = {}
    env.runs[3].f()
    luaunit.assert_equals(env.ui, {{"select_page", 2}})
    luaunit.assert_equals(env.sent, {})
  end)
end

-- characterisation: the timer only starts for CC 1-20, on the channel edit page.
-- Human decision 2026-09-11 (bugs.json cc-page-return-any-channel, was S10): it
-- starts on every MIDI channel 1-16, not only channel 1.
function test_midi_input_cc_timer_needs_cc_one_to_twenty_on_edit_page_on_any_channel()
  with_midi(function(env)
    env.program_page = 2
    handle_midi_event_data({0xB0, 0, 65}, env.dev1)
    handle_midi_event_data({0xB0, 21, 65}, env.dev1)
    handle_midi_event_data({0xBF, 21, 65}, env.dev1)
    env.program_page = 1
    handle_midi_event_data({0xB0, 5, 65}, env.dev1)
    handle_midi_event_data({0xB1, 5, 65}, env.dev1)
    env.program_page = 2
    env.selected = 17
    handle_midi_event_data({0xB0, 5, 65}, env.dev1)
    luaunit.assert_equals(env.runs, {})
    env.selected = 1
    handle_midi_event_data({0xB0, 5, 65}, env.dev1)
    luaunit.assert_equals(#env.runs, 1)
    handle_midi_event_data({0xB1, 5, 65}, env.dev1)
    luaunit.assert_equals(#env.runs, 2)
    handle_midi_event_data({0xBF, 20, 63}, env.dev1)
    luaunit.assert_equals(#env.runs, 3)
    -- Neither a key-pressure message (0xA0) nor a program change (0xC0) starts it.
    handle_midi_event_data({0xA1, 5, 65}, env.dev1)
    handle_midi_event_data({0xC1, 5, 65}, env.dev1)
    luaunit.assert_equals(#env.runs, 3)
  end)
end

-- ---------------------------------------------------------------------------
-- MIDI mapping params and acceleration (README 200-213)
-- ---------------------------------------------------------------------------

local MASK_SUFFIX = {"trig", "note", "vel", "len", "ch1", "ch2", "ch3", "ch4"}
local CHANNEL_MASK_SUFFIX = {"trig", "note", "vel", "len", "chd1", "chd2", "chd3", "chd4"}
local MASK_HANDLER = {
  "handle_trig_mask_change", "handle_note_mask_change", "handle_velocity_mask_change",
  "handle_length_mask_change", "handle_chord_mask_one_change", "handle_chord_mask_two_change",
  "handle_chord_mask_three_change", "handle_chord_mask_four_change"}

-- characterisation: every norns group count equals the params that follow it.
function test_midi_map_param_groups_declare_exactly_the_params_they_contain()
  with_midi(function(env, m)
    m.set_up_midi_mapping_params()
    local groups, current = {}, nil
    luaunit.assert_equals(env.param_log[1], {"separator", "MOSAIC MIDI MAPPING"})
    for i = 2, #env.param_log do
      local e = env.param_log[i]
      if e[1] == "group" then
        current = {id = e[2], name = e[3], declared = e[4], actual = 0}
        groups[#groups + 1] = current
      else
        current.actual = current.actual + 1
      end
    end
    luaunit.assert_equals(groups, {
      {id = "mosaic_mask_midi_maps", name = "MASK MIDI MAPS", declared = 138, actual = 138},
      {id = "mosaic_trig_param_midi_maps", name = "TRIG PARAM MIDI MAPS", declared = 172, actual = 172},
      {id = "mosaic_recorder_midi_maps", name = "MEMORY MIDI MAPS", declared = 19, actual = 19}})
    local controls = 0
    for _, e in ipairs(env.param_log) do
      if e[1] == "control" then
        controls = controls + 1
        -- README 205-209: relative controls from -1 to 1 shown as "MAP".
        luaunit.assert_equals(e[4], {-1, 1, "lin", 1, 0, "", 1, false})
        luaunit.assert_equals(e[5](), "MAP")
        luaunit.assert_not_nil(env.actions[e[2]])
      end
    end
    luaunit.assert_equals(controls, 323)
    luaunit.assert_equals(env.param_log[3], {"separator", "SELECTED CHANNEL MASKS"})
    luaunit.assert_equals(env.param_log[4][2], "sel_ch_trig")
    luaunit.assert_equals(env.param_log[4][3], "Selected Ch. Trig")
    luaunit.assert_equals(env.param_log[11][3], "Selected Ch. Chord 4")
    luaunit.assert_equals(env.param_log[13][3], "Ch.1 Trig Mask")
    luaunit.assert_equals(env.param_log[140][3], "Ch.16 Chd 4 Mask")
  end)
end

-- README 203: selected-channel maps act on the selected channel; channel maps
-- act on their channel "regardless of which channel is selected". Each action
-- re-centres its param silently.
function test_midi_map_every_action_dispatches_to_its_handler_with_exact_arguments()
  with_midi(function(env, m)
    m.set_up_midi_mapping_params()
    env.selected = 5
    env.program_page = 1
    local function run(id, d)
      env.now = env.now + 1
      env.ui = {}
      env.actions[id](d)
      return env.ui
    end
    local selected = env.channels[5]
    for p = 1, 8 do
      luaunit.assert_equals(run("sel_ch_" .. MASK_SUFFIX[p], -1),
        {{MASK_HANDLER[p], selected, -1, env.song_pattern}, {"params_set", "sel_ch_" .. MASK_SUFFIX[p], 0, true}})
    end
    for c = 1, 16 do
      for p = 1, 8 do
        local id = "ch" .. c .. "_" .. CHANNEL_MASK_SUFFIX[p]
        luaunit.assert_equals(run(id, 1), {{MASK_HANDLER[p], env.channels[c], 1, env.song_pattern}, {"params_set", id, 0, true}})
      end
    end
    for p = 1, 10 do
      local id = "sel_ch_trig_param_" .. p
      luaunit.assert_equals(run(id, 1),
        {{"handle_trig_lock_param_change_by_direction", 1, selected, p}, {"params_set", id, 0, true}})
    end
    for c = 1, 16 do
      for p = 1, 10 do
        local id = "ch_" .. c .. "_trig_param_" .. p
        luaunit.assert_equals(run(id, -1),
          {{"handle_trig_lock_param_change_by_direction", -1, env.channels[c], p}, {"params_set", id, 0, true}})
      end
    end
    luaunit.assert_equals(run("sel_ch_memory", 1),
      {{"handle_memory_navigator", 5, 1}, {"params_set", "sel_ch_memory", 0, true}})
    for c = 1, 16 do
      local id = "ch" .. c .. "_memory"
      luaunit.assert_equals(run(id, -1), {{"handle_memory_navigator", c, -1}, {"params_set", id, 0, true}})
    end
  end)
end

-- characterisation: selected-channel maps bring the channel edit page to their
-- sub-page (masks 1 after the change, trig params 2 and memory 3 before it);
-- per-channel maps never switch pages.
function test_midi_map_selected_channel_actions_switch_the_channel_edit_sub_page()
  with_midi(function(env, m)
    m.set_up_midi_mapping_params()
    local function run(id, program_page, cep_page)
      env.now = env.now + 1
      env.program_page, env.cep_page = program_page, cep_page
      env.ui = {}
      env.actions[id](1)
      local names = {}
      for _, e in ipairs(env.ui) do
        if e[1] ~= "get_selected_page" then names[#names + 1] = e[1] end
      end
      return names
    end
    luaunit.assert_equals(run("sel_ch_note", 2, 2), {"handle_note_mask_change", "params_set", "select_mask_page"})
    luaunit.assert_equals(run("sel_ch_note", 2, 1), {"handle_note_mask_change", "params_set"})
    luaunit.assert_equals(run("sel_ch_note", 1, 2), {"handle_note_mask_change", "params_set"})
    luaunit.assert_equals(run("sel_ch_trig_param_3", 2, 1),
      {"select_trig_page", "handle_trig_lock_param_change_by_direction", "params_set"})
    luaunit.assert_equals(run("sel_ch_trig_param_3", 2, 2), {"handle_trig_lock_param_change_by_direction", "params_set"})
    luaunit.assert_equals(run("sel_ch_trig_param_3", 3, 1), {"handle_trig_lock_param_change_by_direction", "params_set"})
    luaunit.assert_equals(run("sel_ch_memory", 2, 1), {"select_memory_page", "handle_memory_navigator", "params_set"})
    luaunit.assert_equals(run("sel_ch_memory", 2, 3), {"handle_memory_navigator", "params_set"})
    luaunit.assert_equals(run("sel_ch_memory", 1, 1), {"handle_memory_navigator", "params_set"})
    luaunit.assert_equals(run("ch2_note", 2, 2), {"handle_note_mask_change", "params_set"})
    luaunit.assert_equals(run("ch_2_trig_param_1", 2, 1), {"handle_trig_lock_param_change_by_direction", "params_set"})
    luaunit.assert_equals(run("ch2_memory", 2, 1), {"handle_memory_navigator", "params_set"})
  end)
end

-- characterisation: a burst of actions no more than 0.15 s apart accelerates
-- after the third rapid step by 0.5 per step, capped at 10; a longer gap resets.
-- The window and the counter are shared by every mapped control.
function test_midi_map_rapid_actions_accelerate_and_reset_after_the_window()
  with_midi(function(env, m)
    m.set_up_midi_mapping_params()
    local ids = {"sel_ch_trig_param_1", "ch3_note", "ch_4_trig_param_2", "ch5_memory", "sel_ch_len"}
    local function scaled(id, now)
      env.now = now
      env.ui = {}
      env.actions[id](1)
      for _, e in ipairs(env.ui) do
        if e[1] == "handle_trig_lock_param_change_by_direction" then return e[2] end
        if e[1] == "handle_memory_navigator" then return e[3] end
        if e[1]:match("^handle_") then return e[3] end
      end
    end
    -- The first action measures from time 0: exactly 0.15 s counts as rapid.
    luaunit.assert_equals(scaled("sel_ch_trig_param_1", 0.15), 1)
    local got = {}
    local t = 0.15
    for i = 1, 24 do
      t = t + 0.125
      got[i] = scaled(ids[(i % #ids) + 1], t)
    end
    luaunit.assert_equals(got, {1, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10, 10, 10, 10})
    luaunit.assert_equals(scaled("ch3_note", t + 0.25), 1)
    luaunit.assert_equals(scaled("ch3_note", t + 0.375), 1)
    luaunit.assert_equals(scaled("ch3_note", t + 0.5), 1)
    luaunit.assert_equals(scaled("ch3_note", t + 0.625), 1)
    luaunit.assert_equals(scaled("ch3_note", t + 0.75), 1.5)
    luaunit.assert_equals(scaled("sel_ch_memory", t + 0.75), 2)
    luaunit.assert_equals(scaled("sel_ch_memory", t + 1), 1)
  end)
end

-- characterisation: a fresh module's first action long after time 0 is not rapid.
function test_midi_map_first_slow_action_is_unscaled_and_starts_a_new_burst()
  with_midi(function(env, m)
    m.set_up_midi_mapping_params()
    env.now = 0.25
    env.ui = {}
    env.actions["ch1_memory"](-1)
    luaunit.assert_equals(env.ui[1], {"handle_memory_navigator", 1, -1})
    for i, expected in ipairs({-1, -1, -1, -1.5}) do
      env.now = 0.25 + i * 0.125
      env.ui = {}
      env.actions["ch1_memory"](-1)
      luaunit.assert_equals(env.ui[1], {"handle_memory_navigator", 1, expected})
    end
  end)
end

-- ---------------------------------------------------------------------------
-- Stop, Panic and the all-off sweep (m_midi.lua:364-462)
-- ---------------------------------------------------------------------------

-- characterisation: Stop releases every counted onset, then sends transport
-- Stop to connected devices, unless called with false; the counts are dropped.
function test_midi_transport_stop_releases_owned_notes_then_sends_stop_unless_suppressed()
  with_midi(function(env, m)
    midi = {vports = {{}, {}, {}}}
    midi_devices[3] = fake_device(env, 3, {name = "absent"})
    m:note_on(60, 100, 1, 1)
    m:note_on(60, 100, 1, 1)
    m:note_on(70, 90, 4, 2)
    env.sent = {}
    m.stop()
    luaunit.assert_equals(env.sent, {{1, "note_off", 60, 0, 1}, {1, "note_off", 60, 0, 1},
      {2, "note_off", 70, 0, 4}, {1, "stop"}, {2, "stop"}})
    luaunit.assert_equals(m.note_counts, {})
    m:note_on(61, 100, 2, 2)
    env.sent = {}
    m.stop(false)
    luaunit.assert_equals(env.sent, {{2, "note_off", 61, 0, 2}})
    luaunit.assert_equals(m.note_counts, {})
    env.sent = {}
    m.stop(true)
    luaunit.assert_equals(env.sent, {{1, "stop"}, {2, "stop"}})
    midi_devices[2] = nil
    env.sent = {}
    m.stop()
    luaunit.assert_equals(env.sent, {{1, "stop"}})
  end)
end

-- characterisation: all_notes_off keeps counts for a device that has gone away.
function test_midi_transport_all_notes_off_keeps_counts_for_a_missing_device()
  with_midi(function(env, m)
    m:note_on(60, 100, 1, 1)
    m:note_on(62, 100, 3, 2)
    midi_devices[2] = nil
    env.sent = {}
    m:all_notes_off()
    luaunit.assert_equals(env.sent, {{1, "note_off", 60, 0, 1}})
    luaunit.assert_equals(m.note_counts, {[2] = {[3] = {[62] = 1}}})
  end)
end

-- characterisation: the sweep releases every note on every channel, note by note,
-- and forgets only the counts it has already passed; notes played behind it keep
-- their ownership for a later Stop.
function test_midi_sweep_forgets_only_notes_it_has_cleared()
  with_midi(function(env, m)
    m:note_on(5, 100, 1, 1)
    m:note_on(100, 100, 3, 1)
    m:note_on(100, 100, 3, 1)
    m:note_on(7, 100, 2, 2)
    env.sent = {}
    m.all_off(1)
    luaunit.assert_equals(#env.debounces, 1)
    local co = env.debounces[1].cos[1]
    luaunit.assert_equals(env.sent, {})
    resume_times(co, 1)
    luaunit.assert_equals(#env.sent, 16)
    for c = 1, 16 do luaunit.assert_equals(env.sent[c], {1, "note_off", 0, 0, c}) end
    resume_times(co, 5)
    luaunit.assert_equals(#env.sent, 96)
    luaunit.assert_equals(env.sent[81], {1, "note_off", 5, 0, 1})
    luaunit.assert_equals(m.note_counts[1], {[1] = {}, [3] = {[100] = 2}})
    m:note_on(2, 100, 1, 1)
    resume_times(co, 122)
    luaunit.assert_equals(coroutine.status(co), "suspended")
    resume_times(co, 1)
    luaunit.assert_equals(coroutine.status(co), "dead")
    luaunit.assert_equals(m.note_counts[1], {[1] = {[2] = 1}, [3] = {}})
    luaunit.assert_equals(m.note_counts[2], {[2] = {[7] = 1}})
    local offs = 0
    for _, e in ipairs(env.sent) do
      if e[1] == 1 and e[2] == "note_off" then offs = offs + 1 end
    end
    luaunit.assert_equals(offs, 2048)
    luaunit.assert_equals(env.sent[#env.sent], {1, "note_off", 127, 0, 16})
  end)
end

-- characterisation: each device gets one debounced sweep, reused by later calls.
function test_midi_sweep_debounce_is_created_once_per_device()
  with_midi(function(env, m)
    m.all_off(1)
    m.all_off(1)
    m.all_off(2)
    luaunit.assert_equals(#env.debounces, 2)
    luaunit.assert_equals(#env.debounces[1].cos, 2)
    luaunit.assert_equals(#env.debounces[2].cos, 1)
    resume_times(env.debounces[2].cos[1], 1)
    luaunit.assert_equals(env.sent[1], {2, "note_off", 0, 0, 1})
  end)
end

-- characterisation: Panic sweeps only connected devices and drops every count at
-- once, before the sweep has run.
function test_midi_transport_panic_sweeps_connected_devices_and_drops_counts()
  with_midi(function(env, m)
    midi_devices[2].device = nil
    m:note_on(60, 100, 1, 1)
    m:note_on(61, 100, 1, 2)
    env.sent = {}
    m.panic()
    luaunit.assert_equals(m.note_counts, {})
    luaunit.assert_equals(#env.debounces, 1)
    luaunit.assert_equals(env.sent, {})
    resume_times(env.debounces[1].cos[1], 1)
    luaunit.assert_equals(env.sent[1], {1, "note_off", 0, 0, 1})
    luaunit.assert_equals(env.sent[16], {1, "note_off", 0, 0, 16})
    luaunit.assert_equals(#env.sent, 16)
  end)
end

function test_midi_transport_start_and_connected_query_follow_the_device_field()
  with_midi(function(env, m)
    midi_devices[1].device = nil
    m.start()
    luaunit.assert_equals(env.sent, {{2, "start"}})
    luaunit.assert_equals(m.midi_devices_connected(), true)
    midi_devices[2].device = nil
    luaunit.assert_equals(m.midi_devices_connected(), false)
  end)
end

-- ---------------------------------------------------------------------------
-- Output helpers and device wiring
-- ---------------------------------------------------------------------------

function test_midi_output_program_change_goes_only_to_a_present_device()
  with_midi(function(env, m)
    m:program_change(12, 3, 2)
    m:program_change(13, 4, 5)
    luaunit.assert_equals(env.sent, {{2, "program_change", 12, 3}})
  end)
end

-- characterisation: Sinfonion commands are program changes (value, command) sent
-- to every port named "Norns2sinfonion" and nowhere else.
function test_midi_output_sinfonion_commands_reach_only_sinfonion_ports()
  with_midi(function(env, m)
    midi_devices[2].name = "Norns2sinfonion"
    midi_devices[3] = fake_device(env, 3, {name = "Norns2sinfonion"})
    m.send_to_sinfonion(7, 42)
    luaunit.assert_equals(env.sent, {{2, "program_change", 42, 7}, {3, "program_change", 42, 7}})
  end)
end

-- characterisation: output choices skip "none" and Sinfonion ports.
function test_midi_output_outs_list_skips_none_and_sinfonion_ports()
  with_midi(function(env, m)
    midi = {vports = {{}, {}, {}, {}}}
    midi_devices[2].name = "none"
    midi_devices[3] = fake_device(env, 3, {name = "Norns2sinfonion"})
    midi_devices[4] = fake_device(env, 4, {name = "bass"})
    luaunit.assert_equals(m.get_midi_outs(), {
      {name = "OUT 1", value = 1, long_name = "trim(keys,80)"},
      {name = "OUT 4", value = 4, long_name = "trim(bass,80)"}})
  end)
end

-- characterisation: init connects every vport and routes its events, with the
-- connected device as the release owner.
function test_midi_input_init_routes_each_port_event_with_its_device_as_source()
  with_midi(function(env, m)
    local connected = {}
    local ports = {fake_device(env, 1, {name = "a", device = {}}), fake_device(env, 2, {name = "b", device = {}})}
    midi = {vports = {{}, {}}, connect = function(i) connected[#connected + 1] = i; return ports[i] end}
    m.init()
    luaunit.assert_equals(connected, {1, 2})
    luaunit.assert_equals(midi_devices[1], ports[1])
    luaunit.assert_equals(midi_devices[2], ports[2])
    ports[1].event({0x90, 60, 100})
    ports[2].event({0x80, 60, 0})
    luaunit.assert_equals(env.sent, {{1, "note_on", 60, 100, 1}})
    ports[1].event({0x80, 60, 0})
    luaunit.assert_equals(env.sent[2], {1, "note_off", 60, 0, 1})
  end)
end

function test_midi_input_final_release_keeps_onset_song_and_clock_mods()
  -- README 239: first press to final release gives one shared recorded length.
  -- Cross-song target ownership is characterisation, not manual text.
  with_midi(function(env)
    env.params.record = 2
    env.steps[1] = 4
    env.song_channels = {[2] = env.channels, [3] = {make_channel(1)}}
    env.now = 10
    press(env, 60, 100, env.dev1)
    env.now = 10.1
    press(env, 64, 100, env.dev1)
    env.song_pattern = 3
    env.now = 10.2
    release(env, 60, env.dev1)
    luaunit.assert_equals(portions(env), {})
    env.now = 10.5
    release(env, 64, env.dev1)
    luaunit.assert_equals(env.get_channel_calls, {{2, 1}, {2, 1}})
    luaunit.assert_equals(env.divisor_calls, {env.channels[1].clock_mods})
    luaunit.assert_equals(portions(env), {
      {"portion", 1, 4, {song_pattern = 2, data = {step = 4, length = 4}}},
      {"commit", 1, 4}})
  end)
end

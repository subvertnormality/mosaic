-- Mutation killers for lib/step.lua (campaign mutation-bc0570c, wave 3).
-- Tests pin observable output of lib/step.lua: MIDI/n.b. events, parameter writes,
-- song-slot selection, scale/transpose selection and Sinfonion values.
-- README references are to README.md at bc0570c. Everything this file replaces in
-- _G is restored after every test, including on failure (with_env).

local step_under_test = include("mosaic/lib/step")
-- step.lua bound the m_clock instance its own include created; the m_clock module
-- publishes itself as the global, so capture it before anything else re-includes it.
local clock_of_step = m_clock
local pattern_of_step = include("mosaic/lib/pattern")

local REPLACED_GLOBALS = {
  "m_clock", "clock_lattice", "step", "pattern", "params", "m_midi", "device_map",
  "channel_edit_page_ui", "norns_param_state_handler", "recorder", "sinfonion",
  "song_edit_page", "channel_edit_page", "random", "midi_note_on_events",
  "midi_note_off_events", "midi_cc_events"
}

local ALIGN_FUNCTIONS = {
  "align_global_and_local_swing_shuffle_type_values",
  "align_global_and_local_swing_values",
  "align_global_and_local_shuffle_feel_values",
  "align_global_and_local_shuffle_basis_values",
  "align_global_and_local_shuffle_amount_values"
}

local REFRESH_FUNCTIONS = {
  "refresh_clock_mods", "refresh_swing", "refresh_swing_shuffle_type", "refresh_shuffle_feel",
  "refresh_shuffle_basis", "refresh_shuffle_amount", "refresh_trig_locks", "refresh_trig_lock_values"
}

local function install(env)
  program.init()
  local store = {}
  env.store, env.events, env.sets, env.dashboard = store, {}, {}, {}
  env.aligned, env.refreshes, env.sinfonion = {}, {}, {}

  local function log(event)
    event.pulse = clock_lattice and clock_lattice.transport
    table.insert(env.events, event)
  end

  params = {}
  function params:get(id) local p = store[id]; if p then return p.val end end
  function params:set(id, value)
    store[id] = store[id] or {}
    store[id].val = value
    table.insert(env.sets, {id = id, value = value})
  end
  function params:lookup_param(id) return store[id] end
  env.set_param = function(id, value, default) store[id] = {val = value, default = default} end

  m_midi = {start = function() end, stop = function() end}
  function m_midi:note_on(note, velocity, channel) log({kind = "on", note = note, velocity = velocity, channel = channel}) end
  function m_midi:note_off(note, velocity, channel) log({kind = "off", note = note, velocity = velocity, channel = channel}) end
  function m_midi.cc(msb, lsb, value, channel) log({kind = "cc", msb = msb, lsb = lsb, value = value, channel = channel}) end
  function m_midi.nrpn(msb, lsb, value, channel, device, mode)
    log({kind = "nrpn", msb = msb, lsb = lsb, value = value, channel = channel, mode = mode})
  end
  function m_midi:program_change() end
  env.log = log

  env.device = {id = "test_midi_device"}
  device_map = {get_device = function() return env.device end}

  channel_edit_page_ui = {}
  for _, name in ipairs(ALIGN_FUNCTIONS) do
    env.aligned[name] = {}
    channel_edit_page_ui[name] = function(c) table.insert(env.aligned[name], c) end
  end
  for _, name in ipairs(REFRESH_FUNCTIONS) do
    channel_edit_page_ui[name] = function() env.refreshes[name] = (env.refreshes[name] or 0) + 1 end
  end
  channel_edit_page_ui.set_note_dashboard_values = function(values) table.insert(env.dashboard, values) end

  norns_param_state_handler = include("mosaic/lib/devices/norns_param_state_handler")
  recorder = {
    trig_lock_is_dirty = function() return nil end,
    clear_trig_lock_dirty = function() end,
    record_trig_event = function() end
  }
  sinfonion = {
    set_root_note = function(v) env.sinfonion.root = v end,
    set_degree_nr = function(v) env.sinfonion.degree = v end,
    set_mode_nr = function(v) env.sinfonion.mode = v end,
    set_transposition = function(v) env.sinfonion.transposition = v end
  }
  song_edit_page = {
    refresh = function() env.refreshes.song_edit_page = (env.refreshes.song_edit_page or 0) + 1 end,
    refresh_faders = function() end
  }
  channel_edit_page = {
    refresh = function() env.refreshes.channel_edit_page = (env.refreshes.channel_edit_page or 0) + 1 end
  }
  step = step_under_test
  pattern = pattern_of_step
  random = math.random
  midi_note_on_events, midi_note_off_events, midi_cc_events = {}, {}, {}

  m_clock = clock_of_step
  clock_of_step.init()
  clock_of_step.cancel_all_spread_actions()
  step_under_test.reset()
  -- Clock-driven cases set up their step first, then start: starting processes step 1.
  env.start = function() clock_of_step:start() end

  env.events, env.sets, env.dashboard = {}, {}, {}
  for _, name in ipairs(ALIGN_FUNCTIONS) do env.aligned[name] = {} end
  env.refreshes = {}
end

local function with_env(body)
  local saved = {}
  for _, name in ipairs(REPLACED_GLOBALS) do saved[name] = rawget(_G, name) end
  local env = {}
  local ok, err = pcall(function()
    install(env)
    body(env)
  end)
  for _, name in ipairs(REPLACED_GLOBALS) do rawset(_G, name, saved[name]) end
  if not ok then error(err, 0) end
end

local function pulse(n)
  for _ = 1, n do clock_of_step.get_clock_lattice():pulse() end
end

local function events_of(env, kind)
  local found = {}
  for _, e in ipairs(env.events) do if e.kind == kind then table.insert(found, e) end end
  return found
end

local function notes_of(events)
  local notes = {}
  for _, e in ipairs(events) do table.insert(notes, e.note) end
  return notes
end

local function sets_of(env, id)
  local found = {}
  for _, s in ipairs(env.sets) do if s.id == id then table.insert(found, s.value) end end
  return found
end

local function channel_one()
  return program.get_channel(1, 1)
end

-- Give channel 1 a working pattern with trigs on the listed steps.
local function working_pattern(trig_steps, values)
  local channel = channel_one()
  local wp = program.initialise_default_pattern()
  wp.merged_notes = {}
  for _, s in ipairs(trig_steps) do wp.trig_values[s] = 1 end
  for field, by_step in pairs(values or {}) do
    for s, v in pairs(by_step) do wp[field][s] = v end
  end
  channel.working_pattern = wp
  return channel
end

local function lock(channel, s, slot, value)
  channel.step_trig_lock_banks[s] = channel.step_trig_lock_banks[s] or {}
  channel.step_trig_lock_banks[s][slot] = value
end

local function stock(c, index) return "midi_device_params_channel_" .. c .. "_" .. index end
local STOCK = {
  fixed_note = 2, quantised_fixed_note = 3, bipolar_random_note = 4, trig_probability = 6,
  chord_strum = 8, chord_arp = 9, chord_acceleration = 11, chord_velocity_modifier = 12,
  chord_strum_pattern = 13
}
-- Stock channel params default to their Off value (lib/devices/param_manager.lua sets
-- p.default = off_value; Off values from lib/devices/device_map.lua stock_params).
local STOCK_OFF = {
  fixed_note = -1, quantised_fixed_note = -1, bipolar_random_note = 0, trig_probability = -1,
  chord_strum = 0, chord_arp = 0, chord_acceleration = 0, chord_velocity_modifier = 0,
  chord_strum_pattern = 0
}
local function set_stock(env, name, value)
  env.set_param(stock(1, STOCK[name]), value, STOCK_OFF[name])
end

local function note_division_index(value)
  local divisions = include("mosaic/lib/clock/divisions")
  for i, d in ipairs(divisions.note_divisions) do if d.value == value then return i end end
  error("no note division " .. tostring(value))
end

local function midi_channel_of(c) return program.get().devices[c].midi_channel end

---------------------------------------------------------------------------
-- MIDI parameter output (step.process_params)
---------------------------------------------------------------------------

-- characterisation: an NRPN parameter is sent with its NRPN LSB mode.
function test_step_killer_nrpn_lock_is_sent_with_its_lsb_mode()
  with_env(function(env)
    local channel = working_pattern({1})
    channel.trig_lock_params[1] = {
      type = "midi", id = "nrpn_param", param_id = "nrpn_param_id", off_value = -1,
      nrpn_msb = 3, nrpn_lsb = 9, nrpn_min_value = 0, nrpn_max_value = 16383,
      cc_msb = 74, cc_min_value = -1, cc_max_value = 127, nrpn_lsb_mode = "legacy-half"
    }
    lock(channel, 1, 1, 1000)

    step_under_test.process_params(channel, 1)

    local sent = events_of(env, "nrpn")
    luaunit.assert_equals(#sent, 1)
    luaunit.assert_equals({sent[1].msb, sent[1].lsb, sent[1].value, sent[1].channel, sent[1].mode},
      {3, 9, 1000, midi_channel_of(1), "legacy-half"})
    luaunit.assert_equals(#events_of(env, "cc"), 0)
  end)
end

-- characterisation: shipped configs contain parameters whose NRPN description is
-- incomplete (lib/config/elektron_syntakt.json filter_filter_type has nrpn_min_value
-- and nrpn_lsb but no nrpn_msb/nrpn_max_value; fx_track_fltr_attack_time has only
-- nrpn_min_value/nrpn_max_value). Such a parameter is sent as its CC.
function test_step_killer_incomplete_nrpn_description_is_sent_as_cc()
  with_env(function(env)
    local channel = working_pattern({1})
    channel.trig_lock_params[1] = {
      type = "midi", id = "filter_filter_type", param_id = "p1", off_value = -1,
      cc_msb = 76, cc_min_value = -1, cc_max_value = 7, nrpn_min_value = -1, nrpn_lsb = 22
    }
    channel.trig_lock_params[2] = {
      type = "midi", id = "fx_track_fltr_attack_time", param_id = "p2", off_value = -1,
      cc_msb = 75, cc_min_value = -1, cc_max_value = 127, nrpn_min_value = -1, nrpn_max_value = 16383
    }
    lock(channel, 1, 1, 5)
    lock(channel, 1, 2, 40)

    step_under_test.process_params(channel, 1)

    luaunit.assert_equals(#events_of(env, "nrpn"), 0)
    local sent = events_of(env, "cc")
    luaunit.assert_equals(#sent, 2)
    luaunit.assert_equals({sent[1].msb, sent[1].value, sent[1].channel}, {76, 5, midi_channel_of(1)})
    luaunit.assert_equals({sent[2].msb, sent[2].value, sent[2].channel}, {75, 40, midi_channel_of(1)})
  end)
end

-- README.md:760 "Handling Off Settings": "An explicit MIDI parameter lock set to "off"
-- sends no value for that parameter on that step." The off value is the
-- parameter's own off_value (lib/config/midisid.json sweep_time uses 0).
function test_step_killer_lock_at_a_parameters_own_off_value_sends_nothing()
  with_env(function(env)
    local channel = working_pattern({1, 2})
    channel.trig_lock_params[1] = {
      type = "midi", id = "sweep_time", param_id = "sweep", off_value = 0,
      cc_msb = 24, cc_min_value = -1, cc_max_value = 127
    }
    lock(channel, 1, 1, 0)
    lock(channel, 2, 1, 9)

    step_under_test.process_params(channel, 1)
    luaunit.assert_equals(#env.events, 0)

    step_under_test.process_params(channel, 2)
    local sent = events_of(env, "cc")
    luaunit.assert_equals(#sent, 1)
    luaunit.assert_equals({sent[1].msb, sent[1].value}, {24, 9})
  end)
end

-- characterisation: a norns parameter without an off_value treats a lock of -1 as
-- Off (lib/step.lua:156 defaults the off value to -1).
function test_step_killer_norns_parameter_without_off_value_treats_minus_one_as_off()
  with_env(function(env)
    local channel = working_pattern({1, 2})
    channel.trig_lock_params[1] = {type = "norns", id = "nb_cutoff", param_id = "nb_cutoff"}
    env.set_param("nb_cutoff", 1)
    lock(channel, 1, 1, -1)
    lock(channel, 2, 1, 3)

    step_under_test.process_params(channel, 1)
    luaunit.assert_equals(env.sets, {})

    step_under_test.process_params(channel, 2)
    luaunit.assert_equals(sets_of(env, "nb_cutoff"), {3})
  end)
end

-- README.md:966-971 "Param Slides": a slide can be locked to a single step ("This
-- locks the parameter slide to the selected step, causing it to transition smoothly
-- to the next lock") without the channel-wide slide (README.md:964).
function test_step_killer_step_slide_alone_starts_a_midi_slide()
  with_env(function(env)
    local channel = working_pattern({1, 2, 3})
    channel.trig_lock_params[1] = {
      type = "midi", id = "cutoff", param_id = "cutoff_id", off_value = -1,
      cc_msb = 20, cc_min_value = -1, cc_max_value = 127
    }
    lock(channel, 1, 1, 10)
    lock(channel, 3, 1, 50)
    program.toggle_step_param_slide(channel, 1, 1)

    env.start()
    pulse(2)
    luaunit.assert_equals(events_of(env, "cc")[1].value, 10)
    luaunit.assert_true(clock_of_step.channel_is_sliding(channel, 1))

    pulse(40)
    local between = 0
    for _, e in ipairs(events_of(env, "cc")) do if e.value > 10 and e.value < 50 then between = between + 1 end end
    luaunit.assert_true(between > 0)
  end)
end

function test_step_killer_step_slide_alone_starts_a_norns_slide()
  with_env(function(env)
    local channel = working_pattern({1, 2, 3})
    channel.trig_lock_params[1] = {type = "norns", id = "nb_cutoff", param_id = "nb_cutoff"}
    env.set_param("nb_cutoff", 0.5)
    lock(channel, 1, 1, 2)
    lock(channel, 3, 1, 8)
    program.toggle_step_param_slide(channel, 1, 1)

    env.start()
    pulse(2)
    luaunit.assert_equals(sets_of(env, "nb_cutoff")[1], 2)
    luaunit.assert_true(clock_of_step.channel_is_sliding(channel, 1))

    pulse(40)
    local between = 0
    for _, v in ipairs(sets_of(env, "nb_cutoff")) do if v > 2 and v < 8 then between = between + 1 end end
    luaunit.assert_true(between > 0)
  end)
end

-- characterisation: with the channel slide on, a lone norns lock (no next lock to
-- slide to) is simply applied.
function test_step_killer_lone_norns_lock_with_channel_slide_is_applied_without_sliding()
  with_env(function(env)
    local channel = working_pattern({1})
    channel.trig_lock_params[1] = {type = "norns", id = "nb_cutoff", param_id = "nb_cutoff"}
    env.set_param("nb_cutoff", 0.5)
    lock(channel, 1, 1, 4)
    program.set_channel_param_slide(channel, 1, true)

    step_under_test.process_params(channel, 1)

    luaunit.assert_equals(sets_of(env, "nb_cutoff"), {4})
    luaunit.assert_false(clock_of_step.channel_is_sliding(channel, 1))
  end)
end

-- README.md:759 "Default Parameter Values": "A pre-set parameter value is transmitted to
-- your selected device on steps without a trig lock, unless the value is off or a
-- parameter slide is active."
function test_step_killer_default_value_is_not_sent_while_a_slide_is_active()
  with_env(function(env)
    local channel = working_pattern({1, 2, 3})
    channel.trig_lock_params[1] = {
      type = "midi", id = "cutoff", param_id = "cutoff_id", off_value = -1,
      cc_msb = 20, cc_min_value = -1, cc_max_value = 127
    }
    env.set_param("cutoff_id", 64)
    lock(channel, 1, 1, 10)
    lock(channel, 3, 1, 50)
    program.set_channel_param_slide(channel, 1, true)

    env.start()
    pulse(2)
    luaunit.assert_equals(events_of(env, "cc")[1].value, 10)
    luaunit.assert_true(clock_of_step.channel_is_sliding(channel, 1))

    pulse(30) -- through step 2, which has no lock, while the slide to step 3 runs
    for _, e in ipairs(events_of(env, "cc")) do
      luaunit.assert_not_equals(e.value, 64, "default value sent at pulse " .. tostring(e.pulse))
    end
  end)
end

-- characterisation: an n.b. Slew lock goes to the player's set_slew, not to a
-- norns parameter; without a lock the channel value is used.
function test_step_killer_nb_slew_is_sent_to_the_player()
  with_env(function(env)
    local slews = {}
    env.device = {id = "nb_device", player = {set_slew = function(_, v) table.insert(slews, v) end}}
    local channel = working_pattern({1, 2})
    channel.trig_lock_params[1] = {type = "norns", id = "nb_slew", param_id = stock(1, 40), off_value = -1}
    env.set_param(stock(1, 40), 7)
    lock(channel, 1, 1, 12)

    step_under_test.process_params(channel, 1)
    step_under_test.process_params(channel, 2)

    luaunit.assert_equals(slews, {12, 7})
    luaunit.assert_equals(env.sets, {})
  end)
end

-- characterisation: a stock trig parameter without a MIDI destination (Chord
-- Acceleration assigned on a MIDI device) produces no output and writes no norns
-- parameter.
function test_step_killer_stock_param_on_midi_device_writes_nothing()
  with_env(function(env)
    local channel = working_pattern({1})
    channel.trig_lock_params[1] = {
      type = "midi", id = "chord_acceleration", param_id = stock(1, 11), param_type = "stock",
      off_value = 0, cc_min_value = -5, cc_max_value = 5
    }
    lock(channel, 1, 1, 2)

    step_under_test.process_params(channel, 1)

    luaunit.assert_equals(env.events, {})
    luaunit.assert_equals(env.sets, {})
  end)
end

-- characterisation: stock trig parameters that step.handle consumes (here Fixed
-- Note) are never written as norns parameters on an n.b. device.
function test_step_killer_consumed_stock_param_on_norns_device_is_not_a_norns_param()
  with_env(function(env)
    env.device = {id = "nb_device", player = {}}
    local channel = working_pattern({1})
    channel.trig_lock_params[1] = {
      type = "norns", id = "fixed_note", param_id = stock(1, 2), param_type = "stock", off_value = -1
    }
    lock(channel, 1, 1, 60)

    step_under_test.process_params(channel, 1)

    luaunit.assert_equals(env.sets, {})
  end)
end

-- bugs.json nb-chord-acceleration-lock (was suspected defect S47): "chord_acceleration"
-- is in should_process_param's skip list, so on an n.b. device its lock is not passed
-- to params:set("chord_acceleration", ...), which norns rejects as "invalid paramset
-- index"; the sequencer consumes it like the other chord parameters.
function test_step_killer_chord_acceleration_lock_on_norns_device_is_not_a_norns_param()
  with_env(function(env)
    env.device = {id = "nb_device", player = {}}
    local channel = working_pattern({1})
    channel.trig_lock_params[1] = {
      type = "norns", id = "chord_acceleration", param_id = stock(1, 11), param_type = "stock", off_value = 0
    }
    lock(channel, 1, 1, 2)

    step_under_test.process_params(channel, 1)

    luaunit.assert_equals(env.sets, {})
  end)
end

-- characterisation: a norns lock is held on following trigless steps (processed
-- with trigless locks on); the next trig without a lock restores the original value.
function test_step_killer_norns_lock_is_restored_at_the_next_trig_not_on_trigless_steps()
  with_env(function(env)
    local channel = working_pattern({1, 3})
    channel.trig_lock_params[1] = {type = "norns", id = "nb_cutoff", param_id = "nb_cutoff"}
    env.set_param("nb_cutoff", 0.1)
    lock(channel, 1, 1, 9)

    step_under_test.process_params(channel, 1)
    luaunit.assert_equals(sets_of(env, "nb_cutoff"), {9})

    env.sets = {}
    step_under_test.process_params(channel, 2)
    luaunit.assert_equals(env.sets, {})

    step_under_test.process_params(channel, 3)
    luaunit.assert_equals(sets_of(env, "nb_cutoff"), {0.1})
  end)
end

-- characterisation: a norns parameter that was never locked is left untouched.
function test_step_killer_unlocked_norns_parameter_is_not_written()
  with_env(function(env)
    local channel = working_pattern({1})
    channel.trig_lock_params[1] = {type = "norns", id = "nb_cutoff", param_id = "nb_cutoff"}
    env.set_param("nb_cutoff", 0.3)

    step_under_test.process_params(channel, 1)

    luaunit.assert_equals(env.sets, {})
    luaunit.assert_equals(params:get("nb_cutoff"), 0.3)
  end)
end

---------------------------------------------------------------------------
-- Song mode (calculate_next_selected_song_pattern, process_song_song_patterns)
---------------------------------------------------------------------------

local function song_slots(active)
  for n = 1, 8 do program.get_song_pattern(n).active = false end
  for _, n in ipairs(active) do program.get_song_pattern(n).active = true end
end

-- README.md:910 "Song Mode Operations": the sequencer "progresses to the next slot after a
-- pattern has played its designated number of repetitions". characterisation: the
-- repeat count is the repetition being played, so the next slot is reported during
-- the final repetition and the current slot before it.
function test_step_killer_next_song_slot_is_reported_during_the_final_repeat_only()
  with_env(function(env)
    env.set_param("song_mode", 2)
    song_slots({1, 2})
    program.get_song_pattern(1).repeats = 3
    program.get().global_step_accumulator = 5

    program.set_repeat_count(2)
    luaunit.assert_equals(step_under_test.calculate_next_selected_song_pattern(), 1)

    program.set_repeat_count(3)
    luaunit.assert_equals(step_under_test.calculate_next_selected_song_pattern(), 2)
  end)
end

-- README.md:910 "Song Mode Operations": "If it encounters an empty slot, it loops back to
-- the first filled slot within that sequence".
function test_step_killer_song_mode_loops_back_to_the_first_filled_slot_of_the_run()
  with_env(function(env)
    env.set_param("song_mode", 2)
    song_slots({3, 4, 5})
    program.get().selected_song_pattern = 5
    program.get_song_pattern(5).repeats = 1
    program.get().global_step_accumulator = 64

    luaunit.assert_equals(step_under_test.calculate_next_selected_song_pattern(), 3)
  end)
end

-- characterisation: the song position is at the end of the slot exactly when the
-- global step count is a positive multiple of length x repeats (length 1 here).
function test_step_killer_end_of_song_slot_needs_a_positive_global_step()
  with_env(function(env)
    local slot = {global_pattern_length = 1, repeats = 1}
    program.get().global_step_accumulator = 0
    luaunit.assert_false(step_under_test.at_end_of_current_song_pattern(slot))
    program.get().global_step_accumulator = 1
    luaunit.assert_true(step_under_test.at_end_of_current_song_pattern(slot))
  end)
end

-- characterisation: a queued slot switch runs at a global-length boundary, not at
-- global step 0.
function test_step_killer_queued_switch_runs_at_the_first_boundary_not_at_zero()
  with_env(function(env)
    env.set_param("song_mode", 1)
    program.get_song_pattern(1).global_pattern_length = 1
    local runs = 0
    step_under_test.queue_switch_to_next_song_pattern_func(function() runs = runs + 1 end)

    program.get().global_step_accumulator = 0
    step_under_test.process_song_song_patterns()
    luaunit.assert_equals(runs, 0)

    program.get().global_step_accumulator = 1
    step_under_test.process_song_song_patterns()
    luaunit.assert_equals(runs, 1)
  end)
end

-- README.md:910: during playback a slot change "will queue your command and execute
-- it after the current sequence completes", so with song mode on a boundary that does
-- not complete the slot keeps the queued slot. characterisation (lib/step.lua:952-953
-- comment): with song mode off a boundary discards it.
function test_step_killer_song_mode_decides_whether_a_boundary_keeps_the_queued_slot()
  with_env(function(env)
    env.set_param("song_mode", 1)
    song_slots({1, 2})
    program.get().global_step_accumulator = 64
    step_under_test.queue_next_song_pattern(5)
    step_under_test.process_song_song_patterns()
    luaunit.assert_equals(step_under_test.calculate_next_selected_song_pattern(), 1)
  end)
  with_env(function(env)
    env.set_param("song_mode", 2)
    song_slots({1, 2})
    program.get_song_pattern(1).repeats = 2
    program.get().global_step_accumulator = 64
    step_under_test.queue_next_song_pattern(5)
    step_under_test.process_song_song_patterns()
    luaunit.assert_equals(program.get().selected_song_pattern, 1)
    luaunit.assert_equals(step_under_test.calculate_next_selected_song_pattern(), 5)
  end)
end

local function one_to_sixteen(times)
  local list = {}
  for _ = 1, times do for c = 1, 16 do table.insert(list, c) end end
  return list
end

local function start_slide_on_channel_one(env)
  local channel = working_pattern({1, 2, 3})
  channel.trig_lock_params[1] = {
    type = "midi", id = "cutoff", param_id = "cutoff_id", off_value = -1,
    cc_msb = 20, cc_min_value = -1, cc_max_value = 127
  }
  lock(channel, 1, 1, 10)
  lock(channel, 3, 1, 50)
  program.set_channel_param_slide(channel, 1, true)
  env.start()
  pulse(2)
  luaunit.assert_true(clock_of_step.channel_is_sliding(channel, 1))
  return channel
end

local function park_all_channels_at(s)
  for c = 1, 17 do program.set_current_step_for_channel(c, s) end
end

local function all_channels_reset()
  for c = 1, 17 do
    -- A reset parks every channel beyond its end, so its next advance starts at its start step.
    if program.get_current_step_for_channel(c) <= 64 then return false end
  end
  return true
end

-- README.md:1074 "Reset at Song Sequence Change" resets all channels on a slot change;
-- README.md:964 slides "do not transition across song patterns"; README.md:687
-- channel swing/shuffle changes "take effect at the next global song-pattern boundary,
-- including a repeat of the same pattern" (channels 1-16 are aligned at each boundary
-- and again after a slot change). characterisation: the new slot's clock mods apply.
function test_step_killer_moving_to_another_song_slot_resets_channels_and_applies_its_settings()
  with_env(function(env)
    env.set_param("song_mode", 2)
    env.set_param("reset_on_song_pattern_transition", 2)
    env.set_param("reset_on_end_of_pattern_repeat", 1)
    song_slots({1, 2})
    local slowed = {name = "/2", value = 2, type = "clock_division"}
    program.get_song_pattern(2).channels[1].clock_mods = slowed
    program.get_song_pattern(2).channels[2].clock_mods = slowed
    local division_before = clock_of_step.get_channel_division(1)
    local channel = start_slide_on_channel_one(env)
    park_all_channels_at(7)
    program.get().global_step_accumulator = 64

    step_under_test.process_song_song_patterns()

    luaunit.assert_equals(program.get().selected_song_pattern, 2)
    luaunit.assert_false(clock_of_step.channel_is_sliding(channel, 1))
    luaunit.assert_true(all_channels_reset())
    luaunit.assert_equals(program.get().global_step_accumulator, 0)
    luaunit.assert_not_equals(clock_of_step.get_channel_division(1), division_before)
    luaunit.assert_equals(clock_of_step.get_channel_division(1), clock_of_step.get_channel_division(2))
    for _, name in ipairs(ALIGN_FUNCTIONS) do
      luaunit.assert_equals(env.aligned[name], one_to_sixteen(2), name)
    end
    luaunit.assert_equals(env.refreshes.song_edit_page, 1)
  end)
end

-- characterisation: repeating the same slot keeps channel phase (reset at song
-- change does not apply), keeps a running slide ("a same-pattern repeat may wrap",
-- lib/step.lua:992) and aligns channel swing once.
function test_step_killer_repeating_the_same_song_slot_keeps_phase_and_slides()
  with_env(function(env)
    env.set_param("song_mode", 2)
    env.set_param("reset_on_song_pattern_transition", 2)
    env.set_param("reset_on_end_of_pattern_repeat", 1)
    song_slots({1})
    local channel = start_slide_on_channel_one(env)
    park_all_channels_at(7)
    program.get().global_step_accumulator = 64

    step_under_test.process_song_song_patterns()

    luaunit.assert_equals(program.get().selected_song_pattern, 1)
    luaunit.assert_true(clock_of_step.channel_is_sliding(channel, 1))
    for c = 1, 17 do luaunit.assert_equals(program.get_current_step_for_channel(c), 7) end
    for _, name in ipairs(ALIGN_FUNCTIONS) do
      luaunit.assert_equals(env.aligned[name], one_to_sixteen(1), name)
    end
    luaunit.assert_equals(env.refreshes.song_edit_page, nil)
  end)
end

-- README.md:1078 "Reset at Pattern Repeat": "When enabled, it resets all channels at the end
-- of a song sequence when repeating the same song editor pattern."
function test_step_killer_reset_at_pattern_repeat_resets_a_repeated_slot()
  with_env(function(env)
    env.set_param("song_mode", 2)
    env.set_param("reset_on_song_pattern_transition", 1)
    env.set_param("reset_on_end_of_pattern_repeat", 2)
    song_slots({1})
    park_all_channels_at(7)
    program.get().global_step_accumulator = 64

    step_under_test.process_song_song_patterns()

    luaunit.assert_true(all_channels_reset())
    luaunit.assert_equals(program.get().global_step_accumulator, 0)
  end)
end

-- characterisation: Stop (step.reset) returns the song position to global step 0.
function test_step_killer_reset_returns_the_song_position_to_zero()
  with_env(function(env)
    program.get().global_step_accumulator = 37
    step_under_test.reset()
    luaunit.assert_equals(program.get().global_step_accumulator, 0)
  end)
end

---------------------------------------------------------------------------
-- Scales and transpose
---------------------------------------------------------------------------

local function scale_lock(channel_number, s, value)
  program.get().selected_channel = channel_number
  program.add_step_scale_trig_lock(s, value)
  program.get().selected_channel = 1
end

-- README.md:1007 and README.md:856: global scale-track locks "persist until another
-- global lock replaces them or the global scale track wraps". Scale 1 is a valid lock
-- value (lock values are clamped to 1..16, lib/models/program.lua add_step_scale_trig_lock).
function test_step_killer_global_scale_lock_of_scale_one_applies_and_persists()
  with_env(function(env)
    program.get().default_scale = 2
    scale_lock(17, 3, 1)
    program.set_current_step_for_channel(17, 3)
    luaunit.assert_equals(step_under_test.calculate_step_scale_number(1, 5), 1)

    program.set_current_step_for_channel(17, 4)
    luaunit.assert_equals(step_under_test.calculate_step_scale_number(1, 6), 1)
  end)
end

function test_step_killer_global_scale_lock_ends_when_the_scale_track_wraps()
  with_env(function(env)
    program.get().default_scale = 2
    scale_lock(17, 3, 5)
    program.set_current_step_for_channel(17, 3)
    luaunit.assert_equals(step_under_test.calculate_step_scale_number(17, 3), 5)

    program.set_current_step_for_channel(17, 1)
    luaunit.assert_equals(step_under_test.calculate_step_scale_number(17, 1), 2)
    luaunit.assert_equals(step_under_test.calculate_step_scale_number(1, 9), 2)
  end)
end

-- README.md:1007: "Scale locks set on steps in the Channel Editor take precedence
-- over global scale locks"; characterisation: the default scale applies without locks.
function test_step_killer_manual_scale_lookup_precedence_includes_scale_one()
  with_env(function(env)
    program.get().default_scale = 3
    luaunit.assert_equals(step_under_test.manually_calculate_step_scale_number(2, 4), 3)

    scale_lock(17, 1, 1)
    luaunit.assert_equals(step_under_test.manually_calculate_step_scale_number(2, 4), 1)

    scale_lock(17, 1, 4)
    scale_lock(2, 2, 1)
    luaunit.assert_equals(step_under_test.manually_calculate_step_scale_number(2, 4), 1)
  end)
end

-- characterisation: for a channel 16 times slower than the scale track, channel
-- step n reads the scale track up to step 16 * n.
function test_step_killer_manual_scale_lookup_for_a_channel_sixteen_times_slower()
  with_env(function(env)
    program.get().default_scale = 1
    clock_of_step.set_channel_division(17, clock_of_step.calculate_divisor({name = "x16", value = 16, type = "clock_multiplication"}))
    clock_of_step.set_channel_division(2, clock_of_step.calculate_divisor({name = "/1", value = 1, type = "clock_division"}))
    scale_lock(17, 1, 2)
    scale_lock(17, 32, 3)

    luaunit.assert_equals(step_under_test.manually_calculate_step_scale_number(2, 2), 3)
  end)
end

-- characterisation: for a channel more than 16 times slower than the scale track
-- (/17 against /1), every channel step reads only the scale track's first step.
function test_step_killer_manual_scale_lookup_for_a_channel_seventeen_times_slower()
  with_env(function(env)
    program.get().default_scale = 1
    clock_of_step.set_channel_division(17, clock_of_step.calculate_divisor({name = "/1", value = 1, type = "clock_division"}))
    clock_of_step.set_channel_division(2, clock_of_step.calculate_divisor({name = "/17", value = 17, type = "clock_division"}))
    scale_lock(17, 1, 2)
    scale_lock(17, 32, 3)

    luaunit.assert_equals(step_under_test.manually_calculate_step_scale_number(2, 2), 2)
  end)
end

-- README.md:1110 "Scales lock until ptn end" (quantiser_trig_lock_hold, mosaic.lua:414): "When off, the next
-- active trig that passes its probability check clears the previous lock"; when on,
-- the lock persists.
function test_step_killer_scale_lock_hold_decides_whether_the_next_trig_clears_it()
  for _, case in ipairs({{hold = 1, expected = 1}, {hold = 2, expected = 3}}) do
    with_env(function(env)
      env.set_param("quantiser_trig_lock_hold", case.hold)
      working_pattern({1, 2})
      scale_lock(1, 1, 3)
      step_under_test.handle(1, 1)
      luaunit.assert_equals(program.get_channel_step_scale_number(1), 3)

      step_under_test.handle(1, 2)
      luaunit.assert_equals(program.get_channel_step_scale_number(1), case.expected, "hold " .. case.hold)
    end)
  end
end

-- characterisation: after Stop the selected channel's scale is its step-1 scale.
function test_step_killer_reset_sets_the_selected_channel_to_its_first_step_scale()
  with_env(function(env)
    scale_lock(1, 1, 4)
    program.set_channel_step_scale_number(1, 9)
    step_under_test.reset()
    luaunit.assert_equals(program.get_channel_step_scale_number(1), 4)
  end)
end

-- characterisation: a scale-track transpose lock persists on later steps until the
-- channel wraps (current_step % channel end step == 1).
function test_step_killer_transpose_lock_persists_to_later_steps_of_the_channel()
  with_env(function(env)
    program.get_channel(1, 17).step_transpose_trig_lock_banks = {[50] = 5}
    program.set_current_step_for_channel(1, 50)
    luaunit.assert_equals(step_under_test.calculate_step_transpose(1), 5)
    program.set_current_step_for_channel(1, 56)
    luaunit.assert_equals(step_under_test.calculate_step_transpose(1), 5)
  end)
end

---------------------------------------------------------------------------
-- Notes a step emits (step.handle)
---------------------------------------------------------------------------

local function note_ons(env) return events_of(env, "on") end

-- README.md:777 "Trig Probability"; characterisation: a channel probability of Off (-1)
-- assigned to a trig parameter slot plays every trig.
function test_step_killer_trig_probability_off_plays_the_trig()
  with_env(function(env)
    local channel = working_pattern({1})
    channel.trig_lock_params[1] = {
      type = "midi", id = "trig_probability", param_id = stock(1, 6), param_type = "stock",
      off_value = -1, cc_min_value = -1, cc_max_value = 100
    }
    env.set_param(stock(1, 6), -1, -1)

    step_under_test.handle(1, 1)

    luaunit.assert_equals(notes_of(note_ons(env)), {60})
  end)
end

-- README.md:777 "Trig Probability": "At 50, the trig will play half the time": over every
-- equally likely draw, exactly p out of 100 play.
function test_step_killer_trig_probability_plays_p_of_100_equally_likely_draws()
  with_env(function(env)
    working_pattern({1}, {lengths = {[1] = 0}})
    for probability = 0, 100 do
      env.events = {}
      set_stock(env, "trig_probability", probability)
      local k = 0
      random = function(a, b)
        luaunit.assert_equals({a, b}, {0, 99})
        local v = a + (k % (b - a + 1))
        k = k + 1
        return v
      end

      for _ = 1, 100 do step_under_test.handle(1, 1) end

      luaunit.assert_equals(k, probability == 100 and 0 or 100, "draw count at " .. probability)
      luaunit.assert_equals(#note_ons(env), probability, "note-ons at " .. probability)
    end
  end)
end

-- README.md:572 "Masks": mask notes "align with the selected musical scale" by default
-- and this "can be disabled" ("Snap note masks to scale", quantiser_act_on_note_masks,
-- mosaic.lua:412); with it off the mask note is played as set. characterisation: the
-- equidistant C#4 (61) snaps down to C4 (60) in C major.
function test_step_killer_snap_note_masks_setting_decides_whether_a_mask_is_snapped()
  with_env(function(env)
    env.set_param("quantiser_fully_act_on_note_masks", 1)
    env.set_param("quantiser_act_on_note_masks", 1)
    working_pattern({1}, {note_mask_values = {[1] = 61}})
    step_under_test.handle(1, 1)
    luaunit.assert_equals(notes_of(note_ons(env)), {61})
  end)
  with_env(function(env)
    env.set_param("quantiser_fully_act_on_note_masks", 1)
    env.set_param("quantiser_act_on_note_masks", 2)
    working_pattern({1}, {note_mask_values = {[1] = 61}})
    step_under_test.handle(1, 1)
    local played = notes_of(note_ons(env))
    luaunit.assert_equals(#played, 1)
    luaunit.assert_not_equals(played[1], 61)
    luaunit.assert_equals(played[1], 60)
  end)
end

-- characterisation: a snapped note mask is raised by the channel octave (12 per octave).
function test_step_killer_snapped_note_mask_includes_the_channel_octave()
  with_env(function(env)
    env.set_param("quantiser_fully_act_on_note_masks", 1)
    env.set_param("quantiser_act_on_note_masks", 2)
    local channel = working_pattern({1}, {note_mask_values = {[1] = 64}})
    channel.octave = 1
    step_under_test.handle(1, 1)
    luaunit.assert_equals(notes_of(note_ons(env)), {76})
  end)
end

-- characterisation: a negative merged velocity (possible with the Lower velocity
-- merge mode, README.md:659) is sent as velocity 0.
function test_step_killer_negative_velocity_is_sent_as_zero()
  with_env(function(env)
    working_pattern({1}, {velocity_values = {[1] = -10}})
    step_under_test.handle(1, 1)
    local on = note_ons(env)
    luaunit.assert_equals(#on, 1)
    luaunit.assert_equals(on[1].velocity, 0)
  end)
end

-- README.md:785 "Quantised Fixed Note": "when both are Off, ordinary pitch processing
-- resumes". README.md:781 "Fixed Note": "The value represents a MIDI note number."
function test_step_killer_fixed_notes_at_off_keep_the_pattern_pitch_and_127_is_a_note()
  with_env(function(env)
    working_pattern({1}, {note_values = {[1] = 2}})
    set_stock(env, "quantised_fixed_note", -1)
    set_stock(env, "fixed_note", -1)
    step_under_test.handle(1, 1)
    luaunit.assert_equals(notes_of(note_ons(env)), {64})
  end)
  with_env(function(env)
    working_pattern({1}, {note_values = {[1] = 2}})
    set_stock(env, "fixed_note", 127)
    step_under_test.handle(1, 1)
    luaunit.assert_equals(notes_of(note_ons(env)), {127})
  end)
end

-- README.md:738: a muted channel is silenced.
function test_step_killer_muted_channel_emits_no_note()
  with_env(function(env)
    local channel = working_pattern({1})
    channel.mute = true
    step_under_test.handle(1, 1)
    luaunit.assert_equals(note_ons(env), {})
  end)
end

-- README.md:679 "Note Dashboard": it shows the last played notes of the currently selected
-- channel only.
function test_step_killer_note_dashboard_follows_only_the_selected_channel()
  local function play(selected, with_chord)
    local dashboard
    with_env(function(env)
      local channel = working_pattern({1})
      if with_chord then channel.chord_one_mask = 2 end
      program.get().selected_channel = selected
      step_under_test.handle(1, 1)
      dashboard = env.dashboard
    end)
    return dashboard
  end
  luaunit.assert_equals(play(2, false), {})
  luaunit.assert_equals(play(2, true), {})
  local own = play(1, false)
  luaunit.assert_equals(#own, 1)
  luaunit.assert_equals({own[1].note, own[1].velocity, own[1].length}, {60, 100, 1})
  local chord = play(1, true)
  luaunit.assert_equals(#chord, 2)
  luaunit.assert_equals(chord[2].chords[1], 64)
end

-- Human decision S51 (bugs.json dashboard-chord-slots): the dashboard shows chord voices as
-- MIDI sends them, clamped to 0..127 (lib/m_midi.lua note_on). A root at MIDI 12 with the
-- chord mask -9 (--6th) computes MIDI -3.
function test_step_killer_note_dashboard_chord_voices_are_clamped_as_sent()
  local function chord_voice(mask)
    local dashboard, ons
    with_env(function(env)
      local channel = working_pattern({1}, {note_mask_values = {[1] = 12}})
      channel.chord_one_mask = mask
      program.get().selected_channel = 1
      step_under_test.handle(1, 1)
      dashboard = env.dashboard
      ons = notes_of(events_of(env, "on"))
    end)
    local chords = {}
    for _, values in ipairs(dashboard) do
      if values.chords then table.insert(chords, values.chords[1]) end
    end
    return chords, ons
  end
  local chords, ons = chord_voice(-9)
  luaunit.assert_equals(ons, {12, -3}) -- characterisation: this fake note_on does not clamp
  luaunit.assert_equals(chords, {0})
  chords, ons = chord_voice(-7)
  luaunit.assert_equals(ons, {12, 0})
  luaunit.assert_equals(chords, {0})
end

-- Clock-driven cases: the first lattice pulse processes step 1.

-- characterisation: when the same pitch repeats on consecutive steps, the earlier
-- note's Note Off is sent before the next Note On (lib/m_lattice.lua "Finish due
-- note releases before a new step can retrigger the same MIDI pitch").
function test_step_killer_repeated_pitch_releases_before_it_retriggers()
  with_env(function(env)
    working_pattern({1, 2})
    env.start()
    pulse(24 + 2)
    local order = {}
    for _, e in ipairs(env.events) do table.insert(order, e.kind .. e.note) end
    luaunit.assert_equals({order[1], order[2], order[3]}, {"on60", "off60", "on60"})
  end)
end

local function arp_step(env, arp_value, extra)
  local channel = working_pattern({1}, extra)
  set_stock(env, "chord_arp", note_division_index(arp_value))
  return channel
end

-- README.md:801 "Chord Arpeggio": "Chord arpeggios can also be used as ratchets if no
-- chord masks are set"; README.md:807 "Chord Shape": "an unmuted root instead forms a
-- one-slot ratchet".
function test_step_killer_arp_without_chord_masks_ratchets_the_root()
  with_env(function(env)
    arp_step(env, 1/4)
    env.start()
    pulse(24)
    local on = note_ons(env)
    luaunit.assert_equals(notes_of(on), {60, 60, 60, 60})
  end)
end

-- characterisation: each arp note lasts one arp division (off-phase onsets included).
function test_step_killer_arp_notes_last_one_arp_division()
  with_env(function(env)
    arp_step(env, 1/3, {lengths = {[1] = 2}})
    env.start()
    pulse(48)
    local on, off = note_ons(env), events_of(env, "off")
    luaunit.assert_true(#on >= 4)
    for i = 1, 4 do
      luaunit.assert_equals(off[i].pulse - on[i].pulse, 8, "arp note " .. i)
    end
  end)
end

-- README.md:832 "Chord Velocity Modifier" adjusts successive notes; characterisation:
-- velocities are clamped to MIDI 0..127.
function test_step_killer_arp_velocity_modifier_is_clamped_to_midi_range()
  local function arp_velocities(velocity, modifier)
    local velocities = {}
    with_env(function(env)
      local channel = arp_step(env, 1/4, {velocity_values = {[1] = velocity}})
      channel.chord_one_mask = 1
      channel.chord_two_mask = 2
      set_stock(env, "chord_velocity_modifier", modifier)
      env.start()
      pulse(24)
      for _, e in ipairs(note_ons(env)) do table.insert(velocities, e.velocity) end
    end)
    return velocities
  end
  luaunit.assert_equals(arp_velocities(50, -40), {50, 10, 0})
  luaunit.assert_equals(arp_velocities(120, 40), {120, 127, 127})
end

-- README.md:679 "Note Dashboard" for arpeggios: only the selected channel is shown.
function test_step_killer_arp_updates_the_dashboard_only_for_the_selected_channel()
  local function arp_dashboard(selected)
    local count
    with_env(function(env)
      local channel = arp_step(env, 1/4)
      channel.chord_one_mask = 2
      program.get().selected_channel = selected
      env.start()
      pulse(24)
      count = #env.dashboard
    end)
    return count
  end
  luaunit.assert_equals(arp_dashboard(2), 0)
  luaunit.assert_true(arp_dashboard(1) >= 2)
end

-- Human decision S51 (bugs.json dashboard-chord-slots): arpeggiated chord voices are shown as
-- sent too, clamped to 0..127. Root MIDI 12, chord mask -9 computes MIDI -3.
function test_step_killer_arp_dashboard_chord_voices_are_clamped_as_sent()
  local chords, ons
  with_env(function(env)
    local channel = arp_step(env, 1/4, {note_mask_values = {[1] = 12}})
    channel.chord_one_mask = -9
    program.get().selected_channel = 1
    env.start()
    pulse(24)
    ons = notes_of(note_ons(env))
    chords = env.dashboard[#env.dashboard].chords
  end)
  luaunit.assert_equals({ons[1], ons[2]}, {12, -3}) -- characterisation: the fake does not clamp
  luaunit.assert_equals(chords[1], 0)
end

-- characterisation: with strum shape 2 the root plays last, carrying the random
-- note offset and four velocity-modifier increments.
function test_step_killer_reverse_strum_root_plays_last_with_offset_and_velocity()
  with_env(function(env)
    local channel = working_pattern({1}, {velocity_values = {[1] = 60}})
    channel.chord_one_mask = 2
    set_stock(env, "chord_strum", note_division_index(1/4))
    set_stock(env, "chord_strum_pattern", 2)
    set_stock(env, "chord_velocity_modifier", 5)
    set_stock(env, "bipolar_random_note", 2)
    random = function(a, b) return b end
    env.start()
    pulse(30)
    local on = note_ons(env)
    luaunit.assert_equals(#on, 2)
    luaunit.assert_equals({on[2].note, on[2].velocity}, {62, 80})
  end)
end

---------------------------------------------------------------------------
-- Sinfonion (step.sinfonian_sync)
---------------------------------------------------------------------------

local function program_scale(slot, quantiser_number, chord, root_note)
  local quantiser = include("mosaic/lib/quantiser")
  program.get_selected_song_pattern().scales[slot] = {
    number = quantiser_number, scale = quantiser.get_scale(quantiser_number).scale,
    pentatonic_scale = quantiser.get_scale(quantiser_number).pentatonic_scale,
    root_note = root_note, chord = chord, chord_degree_rotation = 0, version = 1
  }
end

-- characterisation: with the default scale set to chromatic (0) and no scale-track
-- lock, the Sinfonion follows program scale 1. Minor (Sinfonion mode 4) on its
-- fifth degree (7) is sent as mode 3 degree 4 with the root raised by 3
-- (lib/step.lua:1064-1069 "hack" for the Sinfonion's flattened fifth).
function test_step_killer_sinfonion_falls_back_to_scale_one_and_maps_minor_fifth()
  with_env(function(env)
    program.get().default_scale = 0
    program_scale(1, 3, 5, 2)   -- Minor, chord 5, root D
    program_scale(2, 6, 1, 0)   -- Dorian, differs from slot 1
    step_under_test.sinfonian_sync(1)
    luaunit.assert_equals({env.sinfonion.root, env.sinfonion.degree, env.sinfonion.mode}, {5, 4, 3})
  end)
end

-- characterisation: a persisting scale-track lock of scale 1 reaches the Sinfonion;
-- the root adds the scale's Sinfonion root offset (Dorian +10), and the fifth-degree
-- mapping applies only to mode 4.
function test_step_killer_sinfonion_uses_a_persisting_scale_one_lock_and_root_offset()
  with_env(function(env)
    program.get().default_scale = 2
    program_scale(1, 6, 4, 2)   -- Dorian, chord 4 (Sinfonion degree 7), root D
    program_scale(2, 1, 1, 0)   -- Major
    scale_lock(17, 3, 1)
    program.set_current_step_for_channel(17, 3)
    step_under_test.calculate_step_scale_number(17, 3)
    program.set_current_step_for_channel(17, 4)
    step_under_test.sinfonian_sync(4)
    luaunit.assert_equals({env.sinfonion.root, env.sinfonion.degree, env.sinfonion.mode}, {12, 7, 3})
  end)
end

-- characterisation (suspected defect: lib/step.lua:1045 passes the module table
-- `step` instead of the argument `s` to program.get_step_scale_trig_lock, so
-- sinfonian_sync never reads the scale-track lock on its step and uses the persisted
-- or default scale instead. In playback this is masked: m_clock.lua:415 calls
-- process_global_step_scale_trig_lock for the same step first, which persists the lock.)
function test_step_killer_sinfonion_sync_alone_ignores_the_scale_lock_on_its_step()
  with_env(function(env)
    program.get().default_scale = 2
    program_scale(1, 6, 4, 2)   -- Dorian, chord 4, root D
    program_scale(2, 1, 1, 0)   -- Major, chord 1, root C
    scale_lock(17, 3, 1)
    program.set_current_step_for_channel(17, 3)

    step_under_test.sinfonian_sync(3)
    luaunit.assert_equals({env.sinfonion.root, env.sinfonion.degree, env.sinfonion.mode}, {0, 0, 3})

    step_under_test.process_global_step_scale_trig_lock(3)
    step_under_test.sinfonian_sync(3)
    luaunit.assert_equals({env.sinfonion.root, env.sinfonion.degree, env.sinfonion.mode}, {12, 7, 3})
  end)
end

-- README.md:789-793 and 1118: the all/merged/random pentatonic switches are
-- independent. Exhaust all eight settings in contexts that make merged and
-- nonzero-random conditions observable through emitted MIDI.
function test_step_hardening_all_pentatonic_switch_combinations()
  for all_bit = 0, 1 do
    for merged_bit = 0, 1 do
      for random_bit = 0, 1 do
        with_env(function(env)
          local channel = working_pattern({1}, {
            note_values = {[1] = 3},
            lengths = {[1] = 0}
          })
          channel.working_pattern.merged_notes[1] = true
          env.set_param("all_scales_lock_to_pentatonic", all_bit == 1 and 2 or 1)
          env.set_param("merged_lock_to_pentatonic", merged_bit == 1 and 2 or 1)
          env.set_param("random_lock_to_pentatonic", random_bit == 1 and 2 or 1)

          step_under_test.handle(1, 1)

          local expected = (all_bit == 1 or merged_bit == 1) and 64 or 65
          luaunit.assert_equals(notes_of(note_ons(env)), {expected},
            string.format("merged context %d/%d/%d", all_bit, merged_bit, random_bit))
        end)

        with_env(function(env)
          working_pattern({1}, {
            note_values = {[1] = 2},
            lengths = {[1] = 0}
          })
          set_stock(env, "bipolar_random_note", 1)
          env.set_param("all_scales_lock_to_pentatonic", all_bit == 1 and 2 or 1)
          env.set_param("merged_lock_to_pentatonic", merged_bit == 1 and 2 or 1)
          env.set_param("random_lock_to_pentatonic", random_bit == 1 and 2 or 1)
          random = function(low, high)
            luaunit.assert_equals({low, high}, {0, 1})
            return 1
          end

          step_under_test.handle(1, 1)

          local expected = (all_bit == 1 or random_bit == 1) and 64 or 65
          luaunit.assert_equals(notes_of(note_ons(env)), {expected},
            string.format("random context %d/%d/%d", all_bit, merged_bit, random_bit))
        end)
      end
    end
  end
end

-- README.md:801-813 and 939-971: chord/arp voices are independent scheduled
-- notes. Two consecutive five-voice chords with two-step lengths create ten
-- simultaneous voice owners; Stop must release every owner, including repeated
-- pitches, exactly once.
function test_step_hardening_maximum_chord_overlap_releases_every_repeated_pitch_owner()
  with_env(function(env)
    local channel = working_pattern({1, 2}, {
      lengths = {[1] = 2, [2] = 2}
    })
    channel.chord_one_mask = 1
    channel.chord_two_mask = 2
    channel.chord_three_mask = 3
    channel.chord_four_mask = 4

    env.start()
    pulse(26)
    local ons = notes_of(note_ons(env))
    luaunit.assert_equals(ons, {60, 62, 64, 65, 67, 60, 62, 64, 65, 67})

    nb = {stop_all = function() end}
    clock_of_step:stop()
    local offs = notes_of(events_of(env, "off"))
    table.sort(offs)
    luaunit.assert_equals(offs, {60, 60, 62, 62, 64, 64, 65, 65, 67, 67})
    luaunit.assert_equals(#events_of(env, "off"), #note_ons(env))
  end)
end

-- README.md:777: probability zero means the trig never plays. Rejection happens
-- before root/chord scheduling, so delayed voices must not leak later.
function test_step_hardening_probability_zero_rejects_root_and_all_four_delayed_voices()
  with_env(function(env)
    local channel = working_pattern({1}, {lengths = {[1] = 4}})
    channel.chord_one_mask = 1
    channel.chord_two_mask = 2
    channel.chord_three_mask = 3
    channel.chord_four_mask = 4
    set_stock(env, "trig_probability", 0)
    set_stock(env, "chord_strum", note_division_index(1 / 4))
    random = function(low, high)
      luaunit.assert_equals({low, high}, {0, 99})
      return 0
    end

    env.start()
    pulse(120)
    nb = {stop_all = function() end}
    clock_of_step:stop()

    luaunit.assert_equals(note_ons(env), {})
    luaunit.assert_equals(events_of(env, "off"), {})
  end)
end

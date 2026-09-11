-- Unit tests for the REAL lib/devices/device_map.lua and lib/devices/param_manager.lua.
--
-- The rest of the unit suite replaces device_map with helpers/mocks/device_map_mock.lua,
-- so every test here loads fresh copies of the real modules inside `isolated`, which
-- saves each global it replaces and restores it afterwards (even when the test fails),
-- leaving the mocks other test files installed at load time untouched.
--
-- Assertions that restate README.md cite its line number; every other assertion pins
-- current behaviour and is labelled `-- characterisation`.

local JSON_MODULE = "mosaic/lib/helpers/json"
-- include() resolves "mosaic/..." against '../../../' (run_tests.lua); the stock configs
-- therefore live at STOCK_DATA .. "config".
local STOCK_DATA = "../../../mosaic/lib/"

local REPLACED_GLOBALS = {
  "device_map", "params", "norns", "note_players", "controlspec", "_menu",
  "channel_edit_page_ui", "autosave_reset", "m_midi", "m_clock", "recorder",
  "program", "print"
}

local STOCK_IDS = {
  "none", "fixed_note", "quantised_fixed_note", "bipolar_random_note", "random_velocity",
  "trig_probability", "twos_random_note", "chord_strum", "chord_arp", "chord_spread",
  "chord_acceleration", "chord_velocity_modifier", "chord_strum_pattern", "mute_root_note",
  "fully_quantise_mask"
}

local function slot_id(channel, i)
  return "midi_device_params_channel_" .. channel .. "_" .. i
end

local function new_param_object(id, name, spec)
  local p = {id = id, name = name, controlspec = spec, value = nil, sets = {}}
  function p:set(v, silent)
    table.insert(self.sets, {value = v, silent = silent})
    self.value = v
  end
  function p:get()
    return self.value
  end
  return p
end

local function new_fake_params()
  local P = {
    lookup = {}, store = {}, visible = {}, actions = {}, ranges = {},
    group_calls = {}, control_calls = {}, set_calls = {}, show_calls = {}, range_calls = {},
    count = 0
  }
  function P:add_group(id, name, n)
    table.insert(self.group_calls, {id = id, name = name, n = n})
    self.count = self.count + 1
    self.lookup[id] = self.count
    self.store[id] = {id = id, name = name}
  end
  function P:add_control(id, name, spec)
    table.insert(self.control_calls, {id = id, name = name, spec = spec})
    self.count = self.count + 1
    self.lookup[id] = self.count
    self.store[id] = new_param_object(id, name, spec)
  end
  function P:hide(id) self.visible[id] = false end
  function P:show(id)
    self.visible[id] = true
    table.insert(self.show_calls, id)
  end
  function P:set_action(id, f) self.actions[id] = f end
  function P:lookup_param(id) return self.store[id] end
  function P:set(id, v) table.insert(self.set_calls, {id = id, value = v}) end
  function P:get_range(id)
    table.insert(self.range_calls, id)
    return self.ranges[id]
  end
  return P
end

local function install_stubs(env)
  env.midi = {}
  env.refreshes = 0
  env.autosaves = 0
  env.menu_rebuilds = 0
  env.cancels = {}
  env.dirty_clears = {}
  env.prints = {}
  env.get_channel_calls = {}
  env.files = {}
  env.dirs = {}
  env.channels = {}
  env.prog = {devices = {}, selected_song_pattern = 1}
  for i = 1, 16 do
    env.prog.devices[i] = {device_map = "none", midi_channel = 1, midi_device = 1}
  end

  env.params = new_fake_params()
  params = env.params
  norns = {state = {data = STOCK_DATA}}
  note_players = nil
  print = function(...) table.insert(env.prints, {...}) end
  controlspec = {
    new = function(minval, maxval, warp, step, default, units, quantum)
      return {
        minval = minval, maxval = maxval, warp = warp, step = step, default = default,
        units = units, quantum = quantum,
        args = {minval = minval, maxval = maxval, warp = warp, step = step, default = default,
                units = units, quantum = quantum}
      }
    end
  }
  _menu = {rebuild_params = function() env.menu_rebuilds = env.menu_rebuilds + 1 end}
  channel_edit_page_ui = {refresh_trig_lock_values = function() env.refreshes = env.refreshes + 1 end}
  autosave_reset = function() env.autosaves = env.autosaves + 1 end
  m_midi = {
    cc = function(...)
      local a = table.pack(...)
      table.insert(env.midi, {kind = "cc", msb = a[1], lsb = a[2], value = a[3], channel = a[4],
                              device = a[5], n = a.n})
    end,
    nrpn = function(...)
      local a = table.pack(...)
      table.insert(env.midi, {kind = "nrpn", msb = a[1], lsb = a[2], value = a[3], channel = a[4],
                              device = a[5], mode = a[6], n = a.n})
    end
  }
  m_clock = {
    cancel_spread_actions_for_channel_trig_lock = function(channel, index)
      table.insert(env.cancels, {channel, index})
    end
  }
  recorder = {
    clear_trig_lock_dirty = function(channel, index)
      table.insert(env.dirty_clears, {channel, index})
    end
  }
  program = {
    get = function() return env.prog end,
    get_channel = function(song_pattern, c)
      table.insert(env.get_channel_calls, {song_pattern, c})
      return env.channels[c]
    end
  }
end

local function isolated(body)
  local saved = {}
  for _, name in ipairs(REPLACED_GLOBALS) do
    saved[name] = _G[name]
  end
  local saved_json = package.loaded[JSON_MODULE]
  local env = {}
  local ok, err = pcall(function()
    install_stubs(env)
    body(env)
  end)
  for i = #(env.files or {}), 1, -1 do os.remove(env.files[i]) end
  for i = #(env.dirs or {}), 1, -1 do os.remove(env.dirs[i]) end
  for _, name in ipairs(REPLACED_GLOBALS) do
    _G[name] = saved[name]
  end
  package.loaded[JSON_MODULE] = saved_json
  if not ok then error(err, 0) end
end

local function load_device_map(env, data_dir, players, skip_init)
  norns = {state = {data = data_dir or STOCK_DATA}}
  note_players = players
  package.loaded[JSON_MODULE] = include("mosaic/lib/helpers/json")
  local dm = include("mosaic/lib/devices/device_map")
  if not skip_init then dm.init() end
  device_map = dm
  return dm
end

local function load_param_manager(env)
  local pm = include("mosaic/lib/devices/param_manager")
  pm.init()
  for _, p in pairs(env.params.store) do
    if p.sets then p.sets = {} end
  end
  return pm
end

-- A data directory holding config/<name> for each entry of files (name -> content).
local function make_data_dir(env, files, symlinks)
  local root = os.tmpname()
  os.remove(root)
  assert(os.execute("mkdir -p '" .. root .. "/config'"))
  table.insert(env.dirs, root)
  table.insert(env.dirs, root .. "/config")
  for name, content in pairs(files) do
    local path = root .. "/config/" .. name
    local f = assert(io.open(path, "w"))
    f:write(content)
    f:close()
    table.insert(env.files, path)
  end
  for name, target in pairs(symlinks or {}) do
    local path = root .. "/config/" .. name
    assert(os.execute("ln -s '" .. target .. "' '" .. path .. "'"))
    table.insert(env.files, path)
  end
  return root .. "/", root .. "/config"
end

local function device_json(id, name, extra)
  return '[{"id":"' .. id .. '","name":"' .. name .. '","type":"midi","params":[]' .. (extra or "") .. '}]'
end

local function ids_of(list)
  local out = {}
  for i, v in ipairs(list) do out[i] = v.id end
  return out
end

local function names_of(list)
  local out = {}
  for i, v in ipairs(list) do out[i] = v.name end
  return out
end

local function find_by_id(list, id)
  for _, v in ipairs(list) do
    if v.id == id then return v end
  end
  return nil
end

local function nb_player(description)
  local player = {}
  player.describe = function() return description end
  return player
end

local function count_keys(t)
  local n = 0
  for _ in pairs(t) do n = n + 1 end
  return n
end

-- Oracle derived independently from lib/config/*.json (param position k => merged index 15+k).
local AUTO_MAPPED = {
  digitakt = {
    {"source_parameters_source_tune", 25, {cc_msb = 16, nrpn_msb = 1, nrpn_lsb = 0, nrpn_min_value = 0, nrpn_max_value = 127}},
    {"source_parameters_source_play_mode", 26, {cc_msb = 17, nrpn_msb = 1, nrpn_lsb = 1, nrpn_min_value = 0, nrpn_max_value = 127}},
    {"source_parameters_source_bit_reduction", 27, {cc_msb = 18, nrpn_msb = 1, nrpn_lsb = 2, nrpn_min_value = 0, nrpn_max_value = 127}},
    {"source_parameters_source_loop_position", 31, {cc_msb = 22, nrpn_msb = 1, nrpn_lsb = 6, nrpn_min_value = 0, nrpn_max_value = 127}},
    {"filter_parameters_filter_frequency", 33, {cc_msb = 74, nrpn_msb = 1, nrpn_lsb = 20, nrpn_min_value = 0, nrpn_max_value = 127}},
    {"filter_parameters_resonance", 34, {cc_msb = 75, nrpn_msb = 1, nrpn_lsb = 21, nrpn_min_value = 0, nrpn_max_value = 127}},
    {"lfo_parameters_lfo_depth", 56, {cc_msb = 109, cc_lsb = 118, nrpn_msb = 1, nrpn_lsb = 39, nrpn_min_value = 0, nrpn_max_value = 127}},
    {"amp_parameters_amp_overdrive", 44, {cc_msb = 81, nrpn_msb = 1, nrpn_lsb = 27, nrpn_min_value = 0, nrpn_max_value = 127}},
    {"amp_parameters_amp_pan", 47, {cc_msb = 10, nrpn_msb = 1, nrpn_lsb = 30, nrpn_min_value = 0, nrpn_max_value = 127}},
  },
  digitakt2 = {
    {"source_parameters_source_tune", 25, {cc_msb = 16, nrpn_msb = 1, nrpn_lsb = 0, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"source_parameters_source_play_mode", 27, {cc_msb = 17, cc_max_value = 3}},
    {"fx_parameters_sample_rate_reduction", 53, {cc_msb = 55}},
    {"src_sample_select", 26, {cc_msb = 19}},
    {"source_parameters_data_E", 28, {cc_msb = 20, nrpn_msb = 1, nrpn_lsb = 4, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"filter_parameters_filter_frequency", 32, {cc_msb = 74}},
    {"filter_parameters_filter_env_depth", 39, {cc_msb = 77}},
    {"lfo1_parameters_lfo_depth", 64, {cc_msb = 109, cc_lsb = 59, nrpn_msb = 1, nrpn_lsb = 49, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"lfo1_parameters_lfo_speed", 57, {cc_msb = 102, cc_lsb = 58, nrpn_msb = 1, nrpn_lsb = 42, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"amp_parameters_amp_pan", 49, {cc_msb = 90}},
  },
  digitone = {
    {"fm_parameters_syn_1_ratio_a", 25, {cc_msb = 92, cc_max_value = 35}},
    {"fm_parameters_syn_1_ratio_b", 26, {cc_msb = 16, cc_lsb = 48, cc_max_value = 360}},
    {"fm_parameters_syn_1_ratio_c", 24, {cc_msb = 91, cc_max_value = 18}},
    {"fm_parameters_syn_1_mix", 30, {cc_msb = 20, cc_lsb = 52, nrpn_msb = 1, nrpn_lsb = 79, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"fm_parameters_syn_2_a_level", 34, {cc_msb = 78, nrpn_msb = 1, nrpn_lsb = 83, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"fm_parameters_syn_2_b_level", 38, {cc_msb = 82, nrpn_msb = 1, nrpn_lsb = 87, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"filter_parameters_filter_frequency", 46, {cc_msb = 23, cc_lsb = 55, nrpn_msb = 1, nrpn_lsb = 20, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"filter_parameters_resonance", 47, {cc_msb = 24, cc_lsb = 56, nrpn_msb = 1, nrpn_lsb = 21, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"lfo_parameters_lfo_1_depth", 74, {cc_msb = 29, cc_lsb = 61, nrpn_msb = 1, nrpn_lsb = 55, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"lfo_parameters_lfo_2_depth", 82, {cc_msb = 31, cc_lsb = 63, nrpn_msb = 1, nrpn_lsb = 64, nrpn_min_value = -1, nrpn_max_value = 16383}},
  },
  syntakt = {
    {"syn_data_entry_knob_b", 26, {cc_msb = 19}},
    {"syn_data_entry_knob_c", 27, {cc_msb = 20}},
    {"syn_data_entry_knob_d", 28, {cc_msb = 18}},
    {"syn_data_entry_knob_e", 29, {cc_msb = 21}},
    {"syn_data_entry_knob_f", 30, {cc_msb = 22}},
    {"syn_data_entry_knob_g", 31, {cc_msb = 23}},
    {"syn_data_entry_knob_h", 32, {cc_msb = 24}},
    {"filter_filter_frequency", 33, {cc_msb = 74, nrpn_msb = 1, nrpn_lsb = 20, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"lfo_1_depth", 58, {cc_msb = 109, cc_lsb = 61, cc_max_value = 16383, nrpn_msb = 1, nrpn_lsb = 39, nrpn_min_value = -1, nrpn_max_value = 16383}},
    {"lfo_2_depth", 66, {cc_msb = 119, cc_lsb = 63, cc_max_value = 16383, nrpn_msb = 1, nrpn_lsb = 47, nrpn_min_value = -1, nrpn_max_value = 16383}},
  },
  ["nord-drum-2"] = {
    {"tone_wave", 37, {cc_msb = 46}},
    {"tone_spectra", 34, {cc_msb = 30}},
    {"tone_pitch", 35, {cc_msb = 31, cc_lsb = 63, cc_max_value = 16384}},
    {"tone_bend_amount", 45, {cc_msb = 54}},
    {"tone_timbre_decay", 38, {cc_msb = 47}},
    {"noise_attack_rate", 22, {cc_msb = 18}},
    {"noise_decay", 25, {cc_msb = 21}},
    {"noise_decay_lo", 26, {cc_msb = 22}},
    {"dist_amount", 27, {cc_msb = 23}},
    {"eq_freq", 29, {cc_msb = 25}},
  },
}

local MIDI_FIELDS = {"cc_msb", "cc_lsb", "cc_min_value", "cc_max_value", "off_value",
                     "nrpn_msb", "nrpn_lsb", "nrpn_min_value", "nrpn_max_value"}

local function expected_midi_fields(spec)
  local out = {}
  for _, k in ipairs(MIDI_FIELDS) do out[k] = spec[k] end
  out.cc_min_value = spec.cc_min_value or -1
  out.cc_max_value = spec.cc_max_value or 127
  out.off_value = spec.off_value or -1
  return out
end

local function actual_midi_fields(param)
  local out = {}
  for _, k in ipairs(MIDI_FIELDS) do out[k] = param[k] end
  return out
end

local function is_nrpn(spec)
  return spec.nrpn_msb ~= nil
end

-------------------------------------------------------------------------------
-- device_map: loading, lookup
-------------------------------------------------------------------------------

function test_real_device_map_lookups_are_empty_before_init()
  isolated(function(env)
    local dm = load_device_map(env, nil, nil, true)
    luaunit.assert_nil(dm.get_devices()) -- characterisation
    luaunit.assert_nil(dm.get_device("digitakt")) -- characterisation
    luaunit.assert_equals(dm.params_cache, {}) -- characterisation
    luaunit.assert_false(pcall(dm.get_device_by_name, "Digitakt")) -- characterisation
  end)
end

function test_real_device_map_stock_configs_load_sorted_with_none_first()
  isolated(function(env)
    local dm = load_device_map(env)
    -- characterisation: None first, then case-insensitive alphabetical order
    luaunit.assert_equals(names_of(dm.get_devices()), {
      "None", "CC Device", "Digitakt", "Digitakt 2", "Digitone", "DRM BD", "DRM Clap",
      "DRM Drum 1", "DRM Drum 2", "DRM HH 1", "DRM HH 2", "DRM Multi", "DRM Snare",
      "DT M Sample", "DT Poly CV", "EX Braids", "EX M Mixer", "EX M Sample", "EX Plaits",
      "MidiSid", "Nord Drum 2", "OP-1", "Syntakt"
    })
  end)
end

function test_real_device_map_get_device_returns_the_first_class_stock_devices_by_id()
  isolated(function(env)
    local dm = load_device_map(env)
    -- README.md:170 names Digitone, Digitakt 2, Syntakt and Nord Drum 2 as first class.
    local expected = {
      digitakt = {"Digitakt", 56, "source_parameters_source_tune", 9},
      digitakt2 = {"Digitakt 2", 87, "source_parameters_source_tune", 10},
      digitone = {"Digitone", 98, "fm_parameters_syn_1_ratio_a", 10},
      syntakt = {"Syntakt", 96, "syn_data_entry_knob_b", 10},
      ["nord-drum-2"] = {"Nord Drum 2", 34, "tone_wave", 10},
    }
    for id, e in pairs(expected) do
      local device = dm.get_device(id)
      luaunit.assert_equals(device.id, id)
      luaunit.assert_equals(device.name, e[1]) -- characterisation
      luaunit.assert_equals(device.type, "midi") -- characterisation
      luaunit.assert_equals(#device.params, e[2]) -- characterisation
      luaunit.assert_equals(device.map_params_automatically[1], e[3]) -- characterisation
      luaunit.assert_equals(#device.map_params_automatically, e[4]) -- characterisation
      luaunit.assert_is(device, find_by_id(dm.get_devices(), id)) -- characterisation: same table
    end
    luaunit.assert_equals(dm.get_device("digitakt2").nrpn_lsb_mode, "legacy-half") -- characterisation
    luaunit.assert_nil(dm.get_device("digitakt").nrpn_lsb_mode) -- characterisation
    luaunit.assert_nil(dm.get_device("no-such-device")) -- characterisation
    luaunit.assert_nil(dm.get_device(nil)) -- characterisation
  end)
end

function test_real_device_map_get_device_by_name_is_exact_and_case_sensitive()
  isolated(function(env)
    local dm = load_device_map(env)
    luaunit.assert_equals(dm.get_device_by_name("Nord Drum 2").id, "nord-drum-2") -- characterisation
    luaunit.assert_equals(dm.get_device_by_name("Syntakt").id, "syntakt") -- characterisation
    luaunit.assert_equals(dm.get_device_by_name("CC Device").id, "cc_device") -- characterisation
    luaunit.assert_equals(dm.get_device_by_name("None").id, "none") -- characterisation
    luaunit.assert_nil(dm.get_device_by_name("nord drum 2")) -- characterisation
    luaunit.assert_nil(dm.get_device_by_name("Nord Drum")) -- characterisation
    -- Digitakt and Digitakt 2 are different devices (README.md:170 names Digitakt 2; user-confirmed
    -- 2026-09-11); each stock config carries its own name (defect digitakt-2-config-name, fixed).
    luaunit.assert_equals(dm.get_device_by_name("Digitakt").id, "digitakt")
    luaunit.assert_equals(dm.get_device_by_name("Digitakt 2").id, "digitakt2")
  end)
end

function test_real_device_map_duplicate_names_resolve_to_the_first_sorted_entry()
  isolated(function(env)
    local data = make_data_dir(env, {
      ["a.json"] = device_json("first", "Same"),
      ["b.json"] = device_json("second", "Same"),
    })
    local dm = load_device_map(env, data)
    local sorted = {}
    for _, d in ipairs(dm.get_devices()) do
      if d.name == "Same" then table.insert(sorted, d.id) end
    end
    luaunit.assert_equals(#sorted, 2) -- characterisation
    luaunit.assert_equals(dm.get_device_by_name("Same").id, sorted[1]) -- characterisation
    luaunit.assert_equals(dm.get_device("first").name, "Same") -- characterisation
    luaunit.assert_equals(dm.get_device("second").name, "Same") -- characterisation
  end)
end

function test_real_device_map_cc_device_has_127_plain_cc_params()
  isolated(function(env)
    local dm = load_device_map(env)
    -- README.md:526: without a config you can still use the CC device.
    local cc = dm.get_device("cc_device")
    luaunit.assert_equals(cc.type, "midi") -- characterisation
    luaunit.assert_equals(cc.name, "CC Device") -- characterisation
    luaunit.assert_false(cc.map_params_automatically) -- characterisation
    luaunit.assert_nil(cc.default_midi_channel) -- characterisation
    luaunit.assert_equals(#cc.params, 127) -- characterisation
    luaunit.assert_equals(cc.params[64], {
      id = "cc_64", param_id = "cc_64", name = "CC 64", cc_msb = 64, off_value = -1,
      cc_min_value = -1, cc_max_value = 127, short_descriptor_1 = "CC64", short_descriptor_2 = ""
    }) -- characterisation
    luaunit.assert_equals(cc.params[1].id, "cc_1") -- characterisation
    luaunit.assert_equals(cc.params[1].cc_msb, 1) -- characterisation
    luaunit.assert_equals(cc.params[127].id, "cc_127") -- characterisation
    luaunit.assert_equals(cc.params[127].cc_msb, 127) -- characterisation
  end)
end

function test_real_device_map_none_device_has_no_params()
  isolated(function(env)
    local dm = load_device_map(env)
    local none = dm.get_device("none")
    luaunit.assert_equals(none.type, "none") -- characterisation
    luaunit.assert_equals(none.name, "None") -- characterisation
    luaunit.assert_false(none.map_params_automatically) -- characterisation
    luaunit.assert_equals(none.params, {}) -- characterisation
    luaunit.assert_is(dm.get_devices()[1], none) -- characterisation
  end)
end

function test_real_device_map_stock_params_ids_ranges_and_labels()
  isolated(function(env)
    local dm = load_device_map(env)
    local stock = dm.get_stock_params()
    luaunit.assert_equals(ids_of(stock), STOCK_IDS) -- characterisation
    local ranges = {
      -- {id, off, min, max}
      {"fixed_note", -1, -1, 127}, -- README.md:781 value is a MIDI note number
      {"quantised_fixed_note", -1, -1, 127}, -- README.md:785 absolute MIDI pitch 0-127
      {"bipolar_random_note", 0, 0, 200},
      {"random_velocity", 0, 0, 254},
      {"trig_probability", -1, -1, 100}, -- README.md:777 100 always plays
      {"twos_random_note", 0, 0, 200},
      {"chord_strum", 0, 0, 89},
      {"chord_arp", 0, 0, 89},
      {"chord_spread", 0, 0, 89},
      {"chord_acceleration", 0, -5, 5}, -- README.md:811 Off (0)
      {"chord_velocity_modifier", 0, -40, 40},
      {"chord_strum_pattern", 0, 0, 4},
      {"mute_root_note", 0, 0, 1},
      {"fully_quantise_mask", 0, 0, 2},
    }
    for i, r in ipairs(ranges) do
      local p = stock[i + 1]
      luaunit.assert_equals(p.id, r[1])
      luaunit.assert_equals({p.off_value, p.cc_min_value, p.cc_max_value}, {r[2], r[3], r[4]}) -- characterisation where uncited
      luaunit.assert_equals(p.param_type, "stock") -- characterisation
    end
    luaunit.assert_equals(stock[1], {
      id = "none", param_id = "none", name = "None", short_descriptor_1 = "None", short_descriptor_2 = ""
    }) -- characterisation
    luaunit.assert_equals(#stock[2].ui_labels, 129) -- characterisation: one label per value -1..127
    luaunit.assert_equals({stock[2].ui_labels[1], stock[2].ui_labels[2], stock[2].ui_labels[129]},
      {"X", "C0", "G10"}) -- characterisation
    local divisions = include("mosaic/lib/clock/divisions").note_division_labels
    luaunit.assert_equals(#divisions, 90) -- characterisation: 89 = #labels - 1 above
    luaunit.assert_equals(stock[8].ui_labels, divisions) -- characterisation
    luaunit.assert_equals(stock[13].ui_labels, {"X", "->", "<-", "-><-", "<-->"}) -- characterisation
    luaunit.assert_equals(stock[14].ui_labels, {"OFF", "ON"}) -- characterisation
    luaunit.assert_equals(stock[15].ui_labels, {"X", "OFF", "ON"}) -- characterisation
    luaunit.assert_equals(stock[2].short_descriptor_1 .. stock[2].short_descriptor_2, "FIXDNOTE") -- characterisation
    luaunit.assert_is(dm.get_stock_params(), stock) -- characterisation: the live table, not a copy
  end)
end

-------------------------------------------------------------------------------
-- device_map: get_params and its cache
-------------------------------------------------------------------------------

function test_real_device_map_get_params_prefixes_stock_params_and_indexes_every_entry()
  isolated(function(env)
    local dm = load_device_map(env)
    local merged = dm.get_params("nord-drum-2")
    luaunit.assert_equals(#merged, 49) -- characterisation: 15 stock + 34 device params
    for i = 1, 15 do
      luaunit.assert_equals(merged[i].id, STOCK_IDS[i]) -- characterisation
    end
    for i, p in ipairs(merged) do
      luaunit.assert_equals(p.index, i) -- characterisation
    end
    luaunit.assert_equals(merged[16].id, "level") -- characterisation
    luaunit.assert_equals(merged[16].cc_msb, 7) -- characterisation
    luaunit.assert_nil(merged[16].param_type) -- characterisation
    luaunit.assert_equals(merged[49].id, "mix_balance") -- characterisation
    luaunit.assert_equals(merged[49].cc_msb, 58) -- characterisation
    luaunit.assert_equals(merged[2].param_type, "stock") -- characterisation
  end)
end

function test_real_device_map_get_params_counts_per_device()
  isolated(function(env)
    local dm = load_device_map(env)
    local counts = {
      digitakt = 71, digitakt2 = 102, digitone = 113, syntakt = 111, ["nord-drum-2"] = 49,
      cc_device = 142, none = 15, ["no-such-device"] = 15, ["ex-braids"] = 67,
    }
    for id, n in pairs(counts) do
      luaunit.assert_equals(#dm.get_params(id), n, id) -- characterisation
    end
    luaunit.assert_equals(ids_of(dm.get_params("no-such-device")), STOCK_IDS) -- characterisation
    local cc = dm.get_params("cc_device")
    luaunit.assert_equals({cc[79].id, cc[79].cc_msb, cc[79].index}, {"cc_64", 64, 79}) -- characterisation
  end)
end

function test_real_device_map_get_params_maps_auto_params_to_exact_cc_and_nrpn_numbers()
  isolated(function(env)
    local dm = load_device_map(env)
    for device_id, entries in pairs(AUTO_MAPPED) do
      local merged = dm.get_params(device_id)
      for _, e in ipairs(entries) do
        local p = find_by_id(merged, e[1])
        luaunit.assert_not_nil(p, device_id .. ":" .. e[1])
        luaunit.assert_equals(p.index, e[2], device_id .. ":" .. e[1]) -- characterisation
        luaunit.assert_equals(actual_midi_fields(p), expected_midi_fields(e[3]), device_id .. ":" .. e[1]) -- characterisation
      end
    end
  end)
end

function test_real_device_map_get_params_returns_the_shared_cached_table()
  isolated(function(env)
    local dm = load_device_map(env)
    local first = dm.get_params("digitone")
    luaunit.assert_is(dm.get_params("digitone"), first) -- characterisation
    luaunit.assert_is(dm.params_cache["digitone"], first) -- characterisation
    -- characterisation (hazard: no defensive copy, so a caller's mutation reaches every later caller)
    first[16].name = "corrupted"
    luaunit.assert_equals(dm.get_params("digitone")[16].name, "corrupted")
    -- characterisation: merged entries are shallow copies, so the device's own params are untouched
    local device = dm.get_device("digitone")
    luaunit.assert_not_is(first[16], device.params[1])
    luaunit.assert_equals(device.params[1].name, "Mute")
    luaunit.assert_nil(device.params[1].index)
    -- characterisation: nested tables are shared with the device params
    local ratio_a = find_by_id(first, "fm_parameters_syn_1_ratio_a")
    luaunit.assert_is(ratio_a.ui_labels, device.params[10].ui_labels)
    -- characterisation: stock entries are copies, but share nested labels with get_stock_params
    luaunit.assert_not_is(first[2], dm.get_stock_params()[2])
    luaunit.assert_is(first[2].ui_labels, dm.get_stock_params()[2].ui_labels)
  end)
end

function test_real_device_map_invalidate_params_cache_rebuilds_only_that_device()
  isolated(function(env)
    local dm = load_device_map(env)
    local digitone = dm.get_params("digitone")
    local syntakt = dm.get_params("syntakt")
    dm.invalidate_params_cache("digitone")
    luaunit.assert_nil(dm.params_cache["digitone"]) -- characterisation
    local rebuilt = dm.get_params("digitone")
    luaunit.assert_not_is(rebuilt, digitone) -- characterisation
    luaunit.assert_equals(rebuilt, digitone) -- characterisation: same content
    luaunit.assert_is(dm.get_params("syntakt"), syntakt) -- characterisation
  end)
end

function test_real_device_map_invalidate_all_params_cache_rebuilds_every_device()
  isolated(function(env)
    local dm = load_device_map(env)
    local digitone = dm.get_params("digitone")
    local syntakt = dm.get_params("syntakt")
    dm.invalidate_all_params_cache()
    luaunit.assert_equals(dm.params_cache, {}) -- characterisation
    luaunit.assert_not_is(dm.get_params("digitone"), digitone) -- characterisation
    luaunit.assert_not_is(dm.get_params("syntakt"), syntakt) -- characterisation
  end)
end

function test_real_device_map_reinit_keeps_stale_params_cache()
  isolated(function(env)
    local data, config = make_data_dir(env, {["a.json"] = device_json("fixture", "Fixture")})
    local dm = load_device_map(env, data)
    local before = dm.get_params("fixture")
    luaunit.assert_equals(#before, 15) -- characterisation
    local path = config .. "/a.json"
    local f = assert(io.open(path, "w"))
    f:write('[{"id":"fixture","name":"Fixture","type":"midi","params":[{"id":"p1","name":"P1","cc_msb":3}]}]')
    f:close()
    dm.init()
    luaunit.assert_equals(#dm.get_device("fixture").params, 1) -- characterisation
    -- characterisation (hazard: init() does not invalidate params_cache)
    luaunit.assert_is(dm.get_params("fixture"), before)
    dm.invalidate_params_cache("fixture")
    luaunit.assert_equals(#dm.get_params("fixture"), 16) -- characterisation
  end)
end

function test_real_device_map_get_params_nil_id_raises()
  isolated(function(env)
    local dm = load_device_map(env)
    luaunit.assert_false(pcall(dm.get_params, nil)) -- characterisation
  end)
end

function test_real_device_map_merge_adds_none_when_stock_list_does_not_start_with_it()
  isolated(function(env)
    local dm = load_device_map(env)
    table.remove(dm.get_stock_params(), 1)
    local merged = dm.get_params("nord-drum-2")
    luaunit.assert_equals(#merged, 49) -- characterisation
    luaunit.assert_equals(merged[1], {
      id = "none", param_id = "none", name = "None", short_descriptor_1 = "None", short_descriptor_2 = ""
    }) -- characterisation: the inserted none param carries no index
    luaunit.assert_equals({merged[2].id, merged[2].index}, {"fixed_note", 2}) -- characterisation
    luaunit.assert_equals({merged[16].id, merged[16].index}, {"level", 16}) -- characterisation
  end)
end

function test_real_device_map_merge_drops_repeated_ids_and_shifts_later_indices()
  isolated(function(env)
    local dm = load_device_map(env)
    local braids = dm.get_device("ex-braids")
    luaunit.assert_equals(braids.params[1].id, "none") -- characterisation (config data)
    local merged = dm.get_params("ex-braids")
    local nones = 0
    for _, p in ipairs(merged) do
      if p.id == "none" then nones = nones + 1 end
    end
    luaunit.assert_equals(nones, 1) -- characterisation
    luaunit.assert_equals(#merged, 67) -- characterisation: 15 + 53 - 1
    -- characterisation (suspected defect: see the param_manager Braids test; the slot is 17)
    luaunit.assert_equals({merged[16].id, merged[16].index}, {"model_1", 16})
  end)
end

-------------------------------------------------------------------------------
-- device_map: config directory handling (fixtures)
-------------------------------------------------------------------------------

function test_real_device_map_config_loading_skips_unusable_files()
  isolated(function(env)
    local data = make_data_dir(env, {
      ["good.json"] = device_json("good", "Good"),
      ["empty.json"] = "",
      ["broken.json"] = "[{",
      ["no_id.json"] = '[{"name":"No Id","params":[]}]',
      ["number_name.json"] = '[{"id":"numbered","name":5,"params":[]}]',
      ["object.json"] = '{"id":"object","name":"Object","params":[]}',
      ["scalar.json"] = '[1]',
      ["pair.json"] = '[{"id":"pair1","name":"Pair One","params":[]},{"id":"pair2","name":"Pair Two","params":[]}]',
      ["ignored.txt"] = device_json("txt", "Txt"),
      ["ignored.json.bak"] = device_json("bak", "Bak"),
    })
    local dm = load_device_map(env, data)
    -- characterisation: only a first array element with string id and name is kept
    luaunit.assert_equals(ids_of(dm.get_devices()), {"none", "cc_device", "good", "pair1"})
    luaunit.assert_nil(dm.get_device("pair2")) -- characterisation
    luaunit.assert_nil(dm.get_device("numbered")) -- characterisation
  end)
end

function test_real_device_map_value_is_load_order_before_sorting()
  isolated(function(env)
    local data = make_data_dir(env, {
      ["a.json"] = device_json("zed", "Zed", ',"value":99'),
      ["b.json"] = device_json("alpha", "Alpha"),
    })
    local dm = load_device_map(env, data)
    luaunit.assert_equals(ids_of(dm.get_devices()), {"none", "alpha", "cc_device", "zed"}) -- characterisation
    -- characterisation: value is the pre-sort position (files, then CC, then None), overwriting JSON
    local values = {}
    for _, d in ipairs(dm.get_devices()) do values[d.id] = d.value end
    luaunit.assert_equals(values, {zed = 1, alpha = 2, cc_device = 3, none = 4})
  end)
end

function test_real_device_map_sort_ignores_case()
  isolated(function(env)
    local data = make_data_dir(env, {
      ["a.json"] = device_json("b", "beta"),
      ["b.json"] = device_json("c", "CHARLIE"),
      ["c.json"] = device_json("a", "Alpha"),
    })
    local dm = load_device_map(env, data)
    luaunit.assert_equals(names_of(dm.get_devices()), {"None", "Alpha", "beta", "CC Device", "CHARLIE"}) -- characterisation
  end)
end

function test_real_device_map_missing_config_directory_leaves_builtin_devices()
  isolated(function(env)
    local root = os.tmpname()
    os.remove(root)
    local dm = load_device_map(env, root .. "/")
    luaunit.assert_equals(ids_of(dm.get_devices()), {"none", "cc_device"}) -- characterisation
  end)
end

function test_real_device_map_unopenable_config_file_is_skipped()
  isolated(function(env)
    local data = make_data_dir(env, {["a.json"] = device_json("fine", "Fine")},
      {["dangling.json"] = "/nonexistent/mosaic-device-map-test-target"})
    local dm = load_device_map(env, data, nil, true)
    -- bugs.json unreadable-device-config-skipped (was suspected defect S7): an unreadable file
    -- is skipped like an invalid or empty one, and the rest still load
    dm.init()
    luaunit.assert_equals(ids_of(dm.get_devices()), {"none", "cc_device", "fine"})
  end)
end

-------------------------------------------------------------------------------
-- device_map: n.b. note players
-------------------------------------------------------------------------------

function test_real_device_map_only_tested_nb_players_become_devices()
  isolated(function(env)
    local kit = nb_player({supports_slew = false})
    local dm = load_device_map(env, nil, {
      ["jf kit"] = kit,
      ["untested voice"] = nb_player({supports_slew = false}),
      ["midi 1"] = nb_player({supports_slew = false}),
    })
    local device = dm.get_device("jf kit")
    luaunit.assert_equals(device.type, "norns") -- characterisation
    luaunit.assert_equals(device.name, "Jf Kit") -- characterisation
    luaunit.assert_true(device.unique) -- characterisation
    luaunit.assert_equals(device.map_params_automatically, {}) -- characterisation
    luaunit.assert_is(device.player, kit) -- characterisation
    luaunit.assert_equals(device.params, {}) -- characterisation
    luaunit.assert_false(device.supports_slew) -- characterisation
    luaunit.assert_nil(dm.get_device("untested voice")) -- characterisation
    luaunit.assert_nil(dm.get_device("midi 1")) -- characterisation
    luaunit.assert_equals(#dm.get_devices(), 24) -- characterisation: 21 configs + CC + None + jf kit
    luaunit.assert_equals(dm.get_device_by_name("Jf Kit").id, "jf kit") -- characterisation
  end)
end

function test_real_device_map_nb_player_params_come_from_the_norns_param_table()
  isolated(function(env)
    env.params.lookup = {cutoff_1 = 101, reso_1 = 102, mode_1 = 103}
    env.params.store[101] = {name = "filter cutoff", controlspec = {quantum = 0.5, step = 0.25, default = 3, warp = "exp"}}
    env.params.store[102] = {name = "resonance", controlspec = {quantum = 0.5}}
    env.params.store[103] = {name = "mode", min = 1, max = 4}
    env.params.ranges = {[101] = {-2, 2}, [102] = {0, 1}, [103] = {0, 10}}
    local dm = load_device_map(env, nil, {
      ["emplait 1"] = nb_player({params = {"cutoff_1", "reso_1", "mode_1"}, supports_slew = false}),
    })
    local device = dm.get_device("emplait 1")
    luaunit.assert_equals(device.map_params_automatically, {
      "plaits_model_1", "plaits_harmonics_1", "plaits_timbre_1", "plaits_morph_1", "plaits_fm_mod_1",
      "plaits_timb_mod_1", "plaits_morph_mod_1", "plaits_aux_1", "plaits_send_a_1", "plaits_send_b_1"
    }) -- characterisation
    luaunit.assert_equals(device.params, {
      -- characterisation (suspected defect, device_map.lua:387-388: controlspec.quantum is
      -- overwritten by controlspec.step or 0, and "step" is always 0)
      {id = "cutoff_1", param_id = 101, name = "Filter Cutoff", unique = true, short_descriptor_1 = "FLTE",
       short_descriptor_2 = "CTOF", cc_min_value = -2, cc_max_value = 2, quantum = 0.25, step = 0, default = 3},
      {id = "reso_1", param_id = 102, name = "Resonance", unique = true, short_descriptor_1 = "RSON",
       short_descriptor_2 = "", cc_min_value = 0, cc_max_value = 1, quantum = 0, step = 0, default = 0},
      -- characterisation: p.min/p.max override get_range; no controlspec keeps quantum 0.01
      {id = "mode_1", param_id = 103, name = "Mode", unique = true, short_descriptor_1 = "MODE",
       short_descriptor_2 = "", cc_min_value = 1, cc_max_value = 4, quantum = 0.01, step = 0, default = 0},
    })
    luaunit.assert_equals(env.params.show_calls, {101, 102, 103}) -- characterisation
    luaunit.assert_equals(env.params.range_calls, {101, 101, 102, 102, 103, 103}) -- characterisation
    local merged = dm.get_params("emplait 1")
    luaunit.assert_equals({merged[16].id, merged[16].index, merged[18].id}, {"cutoff_1", 16, "mode_1"}) -- characterisation
  end)
end

function test_real_device_map_nb_player_without_described_params_uses_nb_param_map()
  isolated(function(env)
    env.params.lookup = setmetatable({}, {__index = function(_, name) return "pid:" .. name end})
    env.params.store = setmetatable({}, {__index = function() return {name = "some value"} end})
    env.params.get_range = function() return {0, 1} end
    local dm = load_device_map(env, nil, {["emplait 2"] = nb_player({supports_slew = false})})
    local device = dm.get_device("emplait 2")
    luaunit.assert_equals(ids_of(device.params), {
      "plaits_model_2", "plaits_harmonics_2", "plaits_timbre_2", "plaits_morph_2", "plaits_fm_mod_2",
      "plaits_timb_mod_2", "plaits_morph_mod_2", "plaits_a_2", "plaits_d_2", "plaits_s_2", "plaits_r_2",
      "plaits_lpg_color_2", "plaits_amp_2", "plaits_aux_2", "plaits_gain_2", "plaits_pan_2",
      "plaits_send_a_2", "plaits_send_b_2"
    }) -- characterisation
    luaunit.assert_equals(device.params[1].param_id, "pid:plaits_model_2") -- characterisation
  end)
end

function test_real_device_map_nb_slew_param_is_appended_when_supported()
  isolated(function(env)
    local dm = load_device_map(env, nil, {["jf n 1"] = nb_player({supports_slew = true})})
    local device = dm.get_device("jf n 1")
    luaunit.assert_true(device.supports_slew) -- characterisation
    luaunit.assert_equals(device.params, {{
      id = "nb_slew", name = "Slew", short_descriptor_1 = "SLEW", short_descriptor_2 = "",
      off_value = -1, cc_min_value = -1, cc_max_value = 60, quantum = 1, default = -1
    }}) -- characterisation
    local merged = dm.get_params("jf n 1")
    luaunit.assert_equals({#merged, merged[16].id, merged[16].index}, {16, "nb_slew", 16}) -- characterisation
  end)
end

-------------------------------------------------------------------------------
-- device_map: per-channel availability and validation
-------------------------------------------------------------------------------

function test_real_device_map_available_devices_exclude_unique_devices_used_elsewhere()
  isolated(function(env)
    local dm = load_device_map(env, nil, {["jf kit"] = nb_player({supports_slew = false})})
    env.prog.devices[1].device_map = "jf kit"
    env.prog.devices[2].device_map = "digitakt"
    env.prog.devices[3].device_map = "digitakt"
    local total = #dm.get_devices()
    local for_two = dm.get_available_devices_for_channel(2)
    luaunit.assert_equals(#for_two, total - 1) -- characterisation
    luaunit.assert_nil(find_by_id(for_two, "jf kit")) -- characterisation: unique and used by channel 1
    luaunit.assert_not_nil(find_by_id(for_two, "digitakt")) -- characterisation: not unique
    luaunit.assert_not_nil(find_by_id(for_two, "none")) -- characterisation
    luaunit.assert_is(find_by_id(for_two, "digitakt"), dm.get_device("digitakt")) -- characterisation
    local for_one = dm.get_available_devices_for_channel(1)
    luaunit.assert_equals(#for_one, total) -- characterisation: a channel's own device stays available
    luaunit.assert_equals(ids_of(for_one), ids_of(dm.get_devices())) -- characterisation: order kept
  end)
end

function test_real_device_map_available_params_filter_other_slots_and_return_copies()
  isolated(function(env)
    local dm = load_device_map(env)
    env.prog.selected_song_pattern = 4
    env.prog.devices[2].device_map = "nord-drum-2"
    local slots = {{id = "level"}, {id = "pan"}}
    for i = 3, 10 do slots[i] = {id = "none"} end
    env.channels[2] = {number = 2, trig_lock_params = slots}
    local available = dm.get_available_params_for_channel(2, 2)
    luaunit.assert_equals(env.get_channel_calls, {{4, 2}}) -- characterisation
    luaunit.assert_equals(#available, 48) -- characterisation
    luaunit.assert_nil(find_by_id(available, "level")) -- characterisation: used by slot 1
    luaunit.assert_not_nil(find_by_id(available, "pan")) -- characterisation: the selected slot's own
    luaunit.assert_equals(available[1].id, "none") -- characterisation: none is never filtered
    local cached = dm.get_params("nord-drum-2")
    local pan = find_by_id(available, "pan")
    luaunit.assert_not_is(pan, find_by_id(cached, "pan")) -- characterisation: deep copy
    pan.name = "changed"
    pan.ui_labels[2] = "changed"
    luaunit.assert_equals(find_by_id(cached, "pan").name, "Pan") -- characterisation
    luaunit.assert_equals(find_by_id(cached, "pan").ui_labels[2], "20:00") -- characterisation

    local other = dm.get_available_params_for_channel(2, 1)
    luaunit.assert_not_nil(find_by_id(other, "level")) -- characterisation
    luaunit.assert_nil(find_by_id(other, "pan")) -- characterisation
  end)
end

function test_real_device_map_validate_devices_resets_unknown_maps_to_none()
  isolated(function(env)
    local dm = load_device_map(env)
    env.prog.devices[5] = {device_map = "missing-device", midi_channel = 9, midi_device = 3}
    local kept = {device_map = "digitone", midi_channel = 7, midi_device = 2}
    env.prog.devices[6] = kept
    local none_route = env.prog.devices[7]
    dm.validate_devices()
    luaunit.assert_equals(env.prog.devices[5], {midi_channel = 1, midi_device = 1, device_map = "none"}) -- characterisation
    luaunit.assert_is(env.prog.devices[6], kept) -- characterisation
    luaunit.assert_equals(kept, {device_map = "digitone", midi_channel = 7, midi_device = 2}) -- characterisation
    luaunit.assert_is(env.prog.devices[7], none_route) -- characterisation
  end)
end

-------------------------------------------------------------------------------
-- param_manager.init
-------------------------------------------------------------------------------

function test_real_param_manager_init_creates_hidden_groups_of_180_placeholder_controls()
  isolated(function(env)
    load_device_map(env)
    include("mosaic/lib/devices/param_manager").init()
    local P = env.params
    luaunit.assert_equals(#P.group_calls, 16) -- characterisation
    luaunit.assert_equals(P.group_calls[3], {id = "midi_device_params_group_channel_3", name = "MOSAIC CH 3", n = 180}) -- characterisation
    luaunit.assert_false(P.visible["midi_device_params_group_channel_3"]) -- characterisation
    luaunit.assert_equals(#P.control_calls, 16 * 180) -- characterisation
    local p = P.store[slot_id(16, 180)]
    luaunit.assert_equals(p.name, "undefined") -- characterisation
    luaunit.assert_equals(p.controlspec.args, {minval = 0, maxval = 0, warp = "lin", step = 0, default = -1, units = "", quantum = 0}) -- characterisation
    luaunit.assert_equals(p.controlspec.default, -1) -- characterisation
    luaunit.assert_equals(p.sets, {{value = -1}}) -- characterisation
    luaunit.assert_true(P.visible[slot_id(16, 180)]) -- characterisation
    luaunit.assert_equals(p.formatter(p), "X") -- characterisation
    p.value = 7
    luaunit.assert_equals(p.formatter(p), 7) -- characterisation
    luaunit.assert_equals(P.control_calls[1].id, slot_id(1, 1)) -- characterisation
    luaunit.assert_equals(P.control_calls[181].id, slot_id(2, 1)) -- characterisation
  end)
end

function test_real_param_manager_init_skips_ids_that_already_exist()
  isolated(function(env)
    load_device_map(env)
    env.params:add_group("midi_device_params_group_channel_1", "EXISTING", 1)
    env.params:add_control(slot_id(1, 5), "existing", {default = 9})
    local pm = include("mosaic/lib/devices/param_manager")
    pm.init()
    luaunit.assert_equals(#env.params.group_calls, 16) -- characterisation: 1 pre-existing + 15
    luaunit.assert_equals(#env.params.control_calls, 16 * 180) -- characterisation: 1 pre-existing + 2879
    luaunit.assert_equals(env.params.store[slot_id(1, 5)].name, "existing") -- characterisation
    luaunit.assert_nil(env.params.visible["midi_device_params_group_channel_1"]) -- characterisation: not re-hidden
    pm.init()
    luaunit.assert_equals(#env.params.group_calls, 16) -- characterisation: idempotent
    luaunit.assert_equals(#env.params.control_calls, 16 * 180) -- characterisation
  end)
end

-------------------------------------------------------------------------------
-- param_manager.add_device_params
-------------------------------------------------------------------------------

function test_real_param_manager_add_device_params_configures_stock_slots()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = load_param_manager(env)
    local P = env.params
    pm.add_device_params(3, dm.get_device("digitakt"), 5, 2, true)
    luaunit.assert_equals(P.store["midi_device_params_group_channel_3"].name, "MOSAIC CH 3: DIGITAKT") -- characterisation
    luaunit.assert_true(P.visible["midi_device_params_group_channel_3"]) -- characterisation
    luaunit.assert_false(P.visible[slot_id(3, 1)]) -- characterisation: the none stock param
    luaunit.assert_equals(P.store[slot_id(3, 1)].name, "undefined") -- characterisation: left unconfigured
    luaunit.assert_equals(P.store[slot_id(3, 1)].sets, {}) -- characterisation
    local stock = dm.get_stock_params()
    for i = 2, 15 do
      local p = P.store[slot_id(3, i)]
      local s = stock[i]
      luaunit.assert_equals(p.name, s.name) -- characterisation
      luaunit.assert_equals({p.default, p.min, p.max}, {s.off_value, s.cc_min_value, s.cc_max_value}) -- characterisation
      luaunit.assert_equals(p.controlspec.args, {
        minval = s.cc_min_value, maxval = s.cc_max_value, warp = "lin", step = 1, default = s.off_value,
        units = "", quantum = 1 / (s.cc_max_value - s.cc_min_value)
      }) -- characterisation
      luaunit.assert_equals(p.sets, {{value = s.off_value, silent = true}}) -- characterisation
      luaunit.assert_true(P.visible[slot_id(3, i)]) -- characterisation
    end
    local fixed = P.store[slot_id(3, 2)]
    fixed.value = -1
    luaunit.assert_equals(fixed.formatter(fixed), "X") -- characterisation
    fixed.value = 60
    luaunit.assert_equals(fixed.formatter(fixed), "C5") -- characterisation: label index value - off + 1
    local accel = P.store[slot_id(3, 11)]
    accel.value = 0
    luaunit.assert_equals(accel.formatter(accel), "X") -- README.md:811 Off (0)
    accel.value = -3
    luaunit.assert_equals(accel.formatter(accel), -3) -- characterisation
    local mask = P.store[slot_id(3, 15)]
    mask.value = 2
    luaunit.assert_equals(mask.formatter(mask), "ON") -- characterisation
    mask.value = 1
    luaunit.assert_equals(mask.formatter(mask), "OFF") -- characterisation
    -- a stock slot's action refreshes the UI and autosaves, and never sends MIDI
    P.actions[slot_id(3, 6)](50)
    luaunit.assert_equals({env.refreshes, env.autosaves, #env.midi}, {1, 1, 0}) -- characterisation
    luaunit.assert_equals(env.menu_rebuilds, 1) -- characterisation
  end)
end

function test_real_param_manager_add_device_params_without_init_does_not_set_values()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = load_param_manager(env)
    pm.add_device_params(1, dm.get_device("digitone"), 1, 1, false)
    for i = 1, 180 do
      luaunit.assert_equals(env.params.store[slot_id(1, i)].sets, {}, "slot " .. i) -- characterisation
    end
    luaunit.assert_equals(env.params.store[slot_id(1, 30)].name, "FM Syn1 Mix") -- characterisation
  end)
end

function test_real_param_manager_add_device_params_wires_first_class_device_slots_to_midi()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = load_param_manager(env)
    for device_id, entries in pairs(AUTO_MAPPED) do
      env.midi = {}
      local device = dm.get_device(device_id)
      pm.add_device_params(4, device, 11, 3, true)
      for _, e in ipairs(entries) do
        local id = slot_id(4, e[2])
        local spec = e[3]
        luaunit.assert_true(env.params.visible[id], id) -- characterisation
        env.midi = {}
        local autosaves, refreshes = env.autosaves, env.refreshes
        env.params.actions[id](64)
        local expected
        if is_nrpn(spec) then
          local mode = device_id == "digitakt2" and "legacy-half" or "standard"
          expected = {kind = "nrpn", msb = spec.nrpn_msb, lsb = spec.nrpn_lsb, value = 64, channel = 11, device = 3, mode = mode, n = 6}
        else
          expected = {kind = "cc", msb = spec.cc_msb, lsb = spec.cc_lsb, value = 64, channel = 11, device = 3, n = 5}
        end
        -- README.md:546 any non-Off value is sent to the device
        luaunit.assert_equals(env.midi, {expected}, device_id .. ":" .. e[1])
        luaunit.assert_equals({env.autosaves - autosaves, env.refreshes - refreshes}, {1, 1}) -- characterisation
        env.midi = {}
        env.params.actions[id](-1)
        luaunit.assert_equals(env.midi, {}, device_id .. ":" .. e[1]) -- README.md:546 Off leaves the device unchanged
        luaunit.assert_equals({env.autosaves - autosaves, env.refreshes - refreshes}, {2, 1}) -- characterisation
      end
    end
  end)
end

function test_real_param_manager_device_slot_controlspecs_follow_cc_or_nrpn_range()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = load_param_manager(env)
    pm.add_device_params(2, dm.get_device("digitone"), 1, 1, true)
    -- NRPN range with Off inside it: -1..16383
    local mix = env.params.store[slot_id(2, 30)]
    luaunit.assert_equals(mix.controlspec.args, {minval = -1, maxval = 16383, warp = "lin", step = 1, default = -1, units = "", quantum = 127 / 16384}) -- characterisation
    luaunit.assert_equals({mix.min, mix.max, mix.default, mix.name}, {-1, 16383, -1, "FM Syn1 Mix"}) -- characterisation
    luaunit.assert_equals(mix.sets, {{value = -1, silent = true}}) -- characterisation
    -- CC-only range
    local ratio = env.params.store[slot_id(2, 25)]
    luaunit.assert_equals(ratio.controlspec.args, {minval = -1, maxval = 35, warp = "lin", step = 1, default = -1, units = "", quantum = 1 / 36}) -- characterisation
    luaunit.assert_equals({ratio.min, ratio.max}, {-1, 35}) -- characterisation

    -- NRPN range with Off outside it: 0..127 plus a separate Off position
    pm.add_device_params(2, dm.get_device("digitakt"), 1, 1, true)
    local solo = env.params.store[slot_id(2, 16)]
    luaunit.assert_equals(solo.name, "Solo") -- characterisation
    luaunit.assert_equals(solo.controlspec.args, {minval = -1, maxval = 127, warp = "lin", step = 1, default = -1, units = "", quantum = 127 / 128}) -- characterisation
    luaunit.assert_equals({solo.min, solo.max}, {-1, 127}) -- characterisation
    luaunit.assert_equals(type(solo.controlspec.warp), "table") -- characterisation
  end)
end

function test_real_param_manager_syntakt_pedals_are_cc_parameters()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = load_param_manager(env)
    pm.add_device_params(1, dm.get_device("syntakt"), 6, 2, true)
    -- The Syntakt configuration maps Sustain and Sostenuto to CC 64 and CC 66 (MIDI 1.0 pedal
    -- controllers); README.md:546 "all CC parameters are accessible for editing". They carried
    -- nrpn_* = -1 placeholders that collapsed the range to -1 (defect syntakt-pedal-params, fixed).
    for _, e in ipairs({{110, "Sustain", 64}, {111, "Sostenuto", 66}}) do
      local p = env.params.store[slot_id(1, e[1])]
      luaunit.assert_equals(p.name, e[2])
      luaunit.assert_equals(p.controlspec.args, {minval = -1, maxval = 127, warp = "lin", step = 1, default = -1, units = "", quantum = 1 / 128}) -- characterisation: one CC step per detent
      luaunit.assert_equals({p.min, p.max}, {-1, 127})
      env.midi = {}
      env.params.actions[slot_id(1, e[1])](100)
      luaunit.assert_equals(env.midi, {{kind = "cc", msb = e[3], value = 100, channel = 6, device = 2, n = 5}})
    end
  end)
end

function test_real_param_manager_digitakt2_nrpn_mode_honours_the_channel_override()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = load_param_manager(env)
    env.prog.nrpn_stored_modes = {[5] = {digitakt2 = {source_parameters_source_tune = "standard"}}}
    pm.add_device_params(5, dm.get_device("digitakt2"), 9, 1, true)
    env.params.actions[slot_id(5, 25)](200)
    env.params.actions[slot_id(5, 28)](300)
    -- characterisation: the stored override is keyed by the Mosaic channel (5), not the MIDI channel (9)
    luaunit.assert_equals(env.midi, {
      {kind = "nrpn", msb = 1, lsb = 0, value = 200, channel = 9, device = 1, mode = "standard", n = 6},
      {kind = "nrpn", msb = 1, lsb = 4, value = 300, channel = 9, device = 1, mode = "legacy-half", n = 6},
    })
  end)
end

function test_real_param_manager_device_param_branches_on_a_fixture_device()
  isolated(function(env)
    load_device_map(env)
    local pm = load_param_manager(env)
    local device = {type = "midi", name = "Fixture", id = "fixture", params = {
      {id = "none"},                                                                  -- slot 16
      {id = "stocky", param_type = "stock", cc_msb = 1, cc_max_value = 127},          -- slot 17
      {id = "own_channel", cc_msb = 5, cc_max_value = 100, cc_min_value = 0, channel = 9, off_value = 0,
       ui_labels = {"off", "one", "two"}},                                            -- slot 18
      {id = "nrpn_no_min", nrpn_msb = 2, nrpn_lsb = 3, nrpn_max_value = 200, cc_min_value = 0, cc_max_value = 50}, -- slot 19
      {id = "neither"},                                                               -- slot 20
      {id = "cc_no_max", cc_msb = 4},                                                 -- slot 21
      {id = "nrpn_no_lsb", nrpn_msb = 6, nrpn_max_value = 90, cc_msb = 12, cc_max_value = 127}, -- slot 22
    }}
    pm.add_device_params(6, device, 2, 8, true)
    local P = env.params
    luaunit.assert_false(P.visible[slot_id(6, 16)]) -- characterisation
    luaunit.assert_false(P.visible[slot_id(6, 17)]) -- characterisation: param_type stock is hidden
    P.actions[slot_id(6, 17)](10)
    luaunit.assert_equals({#env.midi, env.autosaves, env.refreshes}, {0, 0, 0}) -- characterisation: no-op action

    local own = P.store[slot_id(6, 18)]
    luaunit.assert_true(P.visible[slot_id(6, 18)]) -- characterisation
    luaunit.assert_equals(own.controlspec.args, {minval = 0, maxval = 100, warp = "lin", step = 1, default = 0, units = "", quantum = 1 / 100}) -- characterisation
    luaunit.assert_equals(own.sets, {{value = 0, silent = true}}) -- characterisation
    own.value = 0
    luaunit.assert_equals(own.formatter(own), "X") -- characterisation
    own.value = 1
    luaunit.assert_equals(own.formatter(own), "one") -- characterisation
    own.value = 5
    luaunit.assert_equals(own.formatter(own), 5) -- characterisation: no label falls back to the value
    P.actions[slot_id(6, 18)](42)
    luaunit.assert_equals(env.midi, {{kind = "cc", msb = 5, value = 42, channel = 9, device = 8, n = 5}}) -- characterisation: param channel wins
    env.midi = {}
    P.actions[slot_id(6, 18)](0)
    luaunit.assert_equals(env.midi, {}) -- README.md:546 the configured Off value sends nothing

    -- characterisation: the range test needs all four nrpn fields, the send test only three
    local nrpn = P.store[slot_id(6, 19)]
    luaunit.assert_equals(nrpn.controlspec.args, {minval = -1, maxval = 50, warp = "lin", step = 1, default = -1, units = "", quantum = 1 / 51}) -- characterisation
    P.actions[slot_id(6, 19)](30)
    luaunit.assert_equals(env.midi, {{kind = "nrpn", msb = 2, lsb = 3, value = 30, channel = 2, device = 8, mode = "standard", n = 6}}) -- characterisation

    env.midi = {}
    local refreshes, autosaves = env.refreshes, env.autosaves
    P.actions[slot_id(6, 20)](30)
    P.actions[slot_id(6, 21)](30)
    luaunit.assert_equals(env.midi, {}) -- characterisation: no cc_max_value means no CC
    luaunit.assert_equals({env.refreshes - refreshes, env.autosaves - autosaves}, {2, 2}) -- characterisation
    local neither = P.store[slot_id(6, 20)]
    luaunit.assert_equals({neither.min, neither.max}, {-1, 127}) -- characterisation: defaults

    -- characterisation: sending NRPN needs msb, lsb and max; without an lsb the CC is sent
    P.actions[slot_id(6, 22)](30)
    luaunit.assert_equals(env.midi, {{kind = "cc", msb = 12, value = 30, channel = 2, device = 8, n = 5}})
    env.midi = {}

    luaunit.assert_true(P.visible[slot_id(6, 21)]) -- characterisation
    luaunit.assert_true(P.visible[slot_id(6, 22)]) -- characterisation
    luaunit.assert_false(P.visible[slot_id(6, 23)]) -- characterisation
    luaunit.assert_false(P.visible[slot_id(6, 180)]) -- characterisation
    P.actions[slot_id(6, 23)](1)
    luaunit.assert_equals({#env.midi, env.autosaves - autosaves}, {0, 3}) -- characterisation: no-op
  end)
end

function test_real_param_manager_add_device_params_hides_slots_after_the_last_device_param()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = load_param_manager(env)
    pm.add_device_params(1, dm.get_device("nord-drum-2"), 1, 1, true)
    luaunit.assert_true(env.params.visible[slot_id(1, 49)]) -- characterisation
    for i = 50, 180 do
      luaunit.assert_false(env.params.visible[slot_id(1, i)], "slot " .. i) -- characterisation
    end
    luaunit.assert_equals(env.params.store[slot_id(1, 17)].name, "Pan") -- characterisation
    local pan = env.params.store[slot_id(1, 17)]
    pan.value = 0
    luaunit.assert_equals(pan.formatter(pan), "20:00") -- characterisation
    -- a later device with fewer params re-hides and disarms the stale slots
    pm.add_device_params(1, dm.get_device("cc_device"), 1, 1, true)
    luaunit.assert_true(env.params.visible[slot_id(1, 142)]) -- characterisation
    luaunit.assert_false(env.params.visible[slot_id(1, 143)]) -- characterisation
    env.midi = {}
    env.params.actions[slot_id(1, 79)](100)
    luaunit.assert_equals(env.midi, {{kind = "cc", msb = 64, value = 100, channel = 1, device = 1, n = 5}}) -- characterisation
  end)
end

function test_real_param_manager_add_device_params_for_none_or_nil_resets_the_channel()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = load_param_manager(env)
    local P = env.params
    for _, device in ipairs({dm.get_device("none"), false}) do
      pm.add_device_params(7, dm.get_device("digitakt"), 1, 1, true)
      for i = 1, 180 do P.store[slot_id(7, i)].sets = {} end
      local rebuilds = env.menu_rebuilds
      pm.add_device_params(7, device or nil, 1, 1, true)
      luaunit.assert_false(P.visible["midi_device_params_group_channel_7"]) -- characterisation
      for i = 1, 180 do
        local p = P.store[slot_id(7, i)]
        luaunit.assert_equals(p.name, "undefined") -- characterisation
        luaunit.assert_false(P.visible[slot_id(7, i)]) -- characterisation
        luaunit.assert_equals(p.sets, {{value = p.controlspec.default, silent = true}}) -- characterisation
      end
      luaunit.assert_equals(P.store[slot_id(7, 2)].sets, {{value = -1, silent = true}}) -- characterisation
      luaunit.assert_equals(P.store[slot_id(7, 4)].sets, {{value = 0, silent = true}}) -- characterisation
      local before = {#env.midi, env.autosaves, env.refreshes}
      P.actions[slot_id(7, 16)](5)
      luaunit.assert_equals({#env.midi, env.autosaves, env.refreshes}, before) -- characterisation: no-op
      luaunit.assert_equals(env.menu_rebuilds - rebuilds, 1) -- characterisation
    end
  end)
end

function test_real_param_manager_norns_slew_slot_is_configured_then_hidden()
  isolated(function(env)
    local dm = load_device_map(env, nil, {["jf n 1"] = nb_player({supports_slew = true})})
    local pm = load_param_manager(env)
    local device = dm.get_device("jf n 1")
    pm.add_device_params(2, device, 1, 1, true)
    local slew = env.params.store[slot_id(2, 40)]
    luaunit.assert_equals(env.params.store["midi_device_params_group_channel_2"].name, "MOSAIC CH 2: JF N 1") -- characterisation
    luaunit.assert_equals(slew.name, "Slew") -- characterisation
    luaunit.assert_equals({slew.default, slew.min, slew.max}, {-1, 0, 60}) -- characterisation
    luaunit.assert_equals(slew.controlspec.args, {minval = 0, maxval = 60, warp = "lin", step = 1, default = 0, units = "", quantum = 1 / 60}) -- characterisation
    luaunit.assert_equals(slew.sets, {{value = 0, silent = true}}) -- characterisation
    -- characterisation (suspected defect, param_manager.lua:122-167: the device-param loop resets
    -- oob_accumulator to 17 for the single nb_slew param, so slot 40 is hidden and its action
    -- replaced by a no-op straight after being configured as "Slew")
    luaunit.assert_false(env.params.visible[slot_id(2, 40)])
    local before = {env.autosaves, env.refreshes}
    env.params.actions[slot_id(2, 40)](10)
    luaunit.assert_equals({env.autosaves, env.refreshes}, before)
    -- characterisation: n.b. device params are never shown in the MIDI slots
    luaunit.assert_false(env.params.visible[slot_id(2, 16)])
    -- characterisation (suspected defect: the nb_slew trig param addresses slot 16, not slot 40)
    local channel = {number = 2, trig_lock_params = {}}
    pm.update_param(1, channel, find_by_id(dm.get_params("jf n 1"), "nb_slew"), device)
    luaunit.assert_equals(channel.trig_lock_params[1].param_id, slot_id(2, 16))
  end)
end

function test_real_param_manager_norns_device_without_params_leaves_slots_16_to_39_as_they_were()
  isolated(function(env)
    local dm = load_device_map(env, nil, {["jf kit"] = nb_player({supports_slew = false})})
    local pm = load_param_manager(env)
    pm.add_device_params(2, dm.get_device("digitakt"), 1, 1, true)
    for i = 1, 180 do env.params.store[slot_id(2, i)].sets = {} end
    pm.add_device_params(2, dm.get_device("jf kit"), 1, 1, true)
    luaunit.assert_equals(env.params.store["midi_device_params_group_channel_2"].name, "MOSAIC CH 2: JF KIT") -- characterisation
    luaunit.assert_true(env.params.visible[slot_id(2, 15)]) -- characterisation: stock slots shown
    luaunit.assert_false(env.params.visible[slot_id(2, 40)]) -- characterisation
    luaunit.assert_false(env.params.visible[slot_id(2, 180)]) -- characterisation
    luaunit.assert_equals(env.params.store[slot_id(2, 40)].sets, {}) -- characterisation: no slew set
    -- characterisation (suspected defect, param_manager.lua:95-167: with no device params and no
    -- slew, oob_accumulator stays 40, so slots 16-39 keep the previous Digitakt configuration,
    -- stay visible and still send MIDI from their actions)
    luaunit.assert_true(env.params.visible[slot_id(2, 16)])
    luaunit.assert_equals(env.params.store[slot_id(2, 16)].name, "Solo")
    env.midi = {}
    env.params.actions[slot_id(2, 16)](5)
    luaunit.assert_equals(env.midi, {{kind = "nrpn", msb = 1, lsb = 102, value = 5, channel = 1, device = 1, mode = "standard", n = 6}})
  end)
end

function test_real_param_manager_braids_slot_and_merged_index_disagree()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = load_param_manager(env)
    local braids = dm.get_device("ex-braids")
    pm.add_device_params(1, braids, 3, 4, true)
    luaunit.assert_false(env.params.visible[slot_id(1, 16)]) -- characterisation: the "none" config param
    luaunit.assert_equals(env.params.store[slot_id(1, 17)].name, "Model 1") -- characterisation
    env.params.actions[slot_id(1, 17)](5)
    luaunit.assert_equals(env.midi, {{kind = "cc", msb = 7, value = 5, channel = 3, device = 4, n = 5}}) -- characterisation
    -- characterisation (suspected defect: merge_params drops the duplicate "none" id, so
    -- Model 1's merged index is 16 and its trig lock addresses the hidden slot 16, not slot 17)
    local channel = {number = 1, trig_lock_params = {}}
    pm.update_param(1, channel, find_by_id(dm.get_params("ex-braids"), "model_1"), braids)
    luaunit.assert_equals(channel.trig_lock_params[1].param_id, slot_id(1, 16))
  end)
end

-------------------------------------------------------------------------------
-- param_manager.update_param
-------------------------------------------------------------------------------

local function update_param_env(env)
  local dm = load_device_map(env)
  local pm = include("mosaic/lib/devices/param_manager")
  return dm, pm
end

function test_real_param_manager_update_param_assigns_a_midi_device_param_by_index()
  isolated(function(env)
    local dm, pm = update_param_env(env)
    local digitone = dm.get_device("digitone")
    local param = find_by_id(dm.get_params("digitone"), "fm_parameters_syn_1_ratio_a")
    local channel = {number = 3, trig_lock_params = {}}
    pm.update_param(2, channel, param, {type = "midi", device_name = "Digitone", id = "digitone"})
    local slot = channel.trig_lock_params[2]
    luaunit.assert_equals(slot.param_id, slot_id(3, 25)) -- characterisation
    luaunit.assert_equals({slot.id, slot.type, slot.device_name, slot.cc_msb, slot.index},
      {"fm_parameters_syn_1_ratio_a", "midi", "Digitone", 92, 25}) -- characterisation
    luaunit.assert_nil(slot.nrpn_lsb_mode) -- characterisation: CC-only param
    luaunit.assert_not_is(slot, param) -- characterisation: deep copy
    luaunit.assert_not_is(slot.ui_labels, param.ui_labels) -- characterisation
    slot.ui_labels[2] = "changed"
    luaunit.assert_equals(param.ui_labels[2], digitone.params[10].ui_labels[2]) -- characterisation
    luaunit.assert_not_equals(param.ui_labels[2], "changed") -- characterisation
    luaunit.assert_equals(env.cancels, {{3, 2}}) -- characterisation: channel number, slot
    luaunit.assert_equals(env.dirty_clears, {{3, 2}}) -- characterisation
  end)
end

function test_real_param_manager_update_param_maps_stock_params_to_their_fixed_slots()
  isolated(function(env)
    local dm, pm = update_param_env(env)
    local merged = dm.get_params("digitone")
    local channel = {number = 4, trig_lock_params = {}}
    for i = 2, 15 do
      pm.update_param(1, channel, merged[i], {type = "midi", device_name = "Digitone"})
      luaunit.assert_equals(channel.trig_lock_params[1].param_id, slot_id(4, i), merged[i].id) -- characterisation
    end
    -- characterisation: stock params keep their stock slot even on a norns device
    pm.update_param(1, channel, merged[6], {type = "norns", device_name = "Jf Kit"})
    luaunit.assert_equals(channel.trig_lock_params[1].param_id, slot_id(4, 6))
    -- characterisation: an explicit stock param_id wins over the id
    local renamed = {id = "alias", param_type = "stock", param_id = "chord_arp"}
    pm.update_param(1, channel, renamed, {type = "midi"})
    luaunit.assert_equals({channel.trig_lock_params[1].id, channel.trig_lock_params[1].param_id}, {"alias", slot_id(4, 9)})
  end)
end

function test_real_param_manager_update_param_uses_a_norns_param_id_only_when_present()
  isolated(function(env)
    local dm, pm = update_param_env(env)
    local channel = {number = 5, trig_lock_params = {}}
    pm.update_param(1, channel, {id = "cutoff_1", param_id = 101, index = 16}, {type = "norns", device_name = "Emplait 1"})
    luaunit.assert_equals(channel.trig_lock_params[1].param_id, 101) -- characterisation
    luaunit.assert_equals(channel.trig_lock_params[1].type, "norns") -- characterisation
    pm.update_param(2, channel, {id = "no_pid", index = 17}, {type = "norns"})
    luaunit.assert_equals(channel.trig_lock_params[2].param_id, slot_id(5, 17)) -- characterisation
    -- characterisation: a midi param ignores any param_id it carries
    pm.update_param(3, channel, {id = "cc_9", param_id = "cc_9", index = 24}, {type = "midi"})
    luaunit.assert_equals(channel.trig_lock_params[3].param_id, slot_id(5, 24))
  end)
end

function test_real_param_manager_update_param_none_clears_the_slot()
  isolated(function(env)
    local dm, pm = update_param_env(env)
    local channel = {number = 6, trig_lock_params = {{id = "level", param_id = slot_id(6, 16), type = "midi"}}}
    pm.update_param(1, channel, {id = "none", param_id = "none"}, {type = "midi"})
    luaunit.assert_equals(channel.trig_lock_params[1], {}) -- characterisation
    luaunit.assert_equals(env.cancels, {{6, 1}}) -- characterisation: assignment changed
    luaunit.assert_equals(env.dirty_clears, {{6, 1}}) -- characterisation
    env.cancels, env.dirty_clears = {}, {}
    pm.update_param(1, channel, {id = "none"}, {type = "midi"})
    luaunit.assert_equals(channel.trig_lock_params[1], {}) -- characterisation
    luaunit.assert_equals({env.cancels, env.dirty_clears}, {{}, {}}) -- characterisation: unchanged
    -- a missing previous slot is treated as empty
    pm.update_param(9, channel, {id = "none"}, {type = "midi"})
    luaunit.assert_equals({env.cancels, env.dirty_clears}, {{}, {}}) -- characterisation
  end)
end

function test_real_param_manager_update_param_retires_recording_only_when_the_assignment_changes()
  isolated(function(env)
    local dm, pm = update_param_env(env)
    local base_param = {id = "p", index = 20, nrpn_msb = 1, nrpn_lsb = 2}
    local base_meta = {type = "midi", device_name = "Dev", id = "dev"}
    local function assign(param, meta)
      local channel = {number = 2, trig_lock_params = {}}
      pm.update_param(1, channel, base_param, base_meta)
      env.cancels, env.dirty_clears = {}, {}
      pm.update_param(1, channel, param, meta)
      return #env.cancels, #env.dirty_clears
    end
    -- README.md:241 confirming the same assignment preserves pending recording
    luaunit.assert_equals({assign(base_param, base_meta)}, {0, 0})
    -- README.md:241 changing a parameter assignment clears its pending recording
    luaunit.assert_equals({assign({id = "q", index = 20, nrpn_msb = 1, nrpn_lsb = 2}, base_meta)}, {1, 1}) -- id
    luaunit.assert_equals({assign({id = "p", index = 21, nrpn_msb = 1, nrpn_lsb = 2}, base_meta)}, {1, 1}) -- param_id
    luaunit.assert_equals({assign(base_param, {type = "norns", device_name = "Dev", id = "dev"})}, {1, 1}) -- type
    luaunit.assert_equals({assign(base_param, {type = "midi", device_name = "Other", id = "dev"})}, {1, 1}) -- device name
    luaunit.assert_equals({assign(base_param, {type = "midi", device_name = "Dev", id = "dev", nrpn_lsb_mode = "legacy-half"})}, {1, 1}) -- NRPN mode
  end)
end

function test_real_param_manager_update_param_records_the_stored_nrpn_mode()
  isolated(function(env)
    local dm, pm = update_param_env(env)
    local mix = find_by_id(dm.get_params("digitone"), "fm_parameters_syn_1_mix")
    local digitone = dm.get_device("digitone")
    local channel = {number = 3, trig_lock_params = {}}
    pm.update_param(1, channel, mix, digitone)
    luaunit.assert_equals(channel.trig_lock_params[1].nrpn_lsb_mode, "standard") -- characterisation
    luaunit.assert_equals(channel.trig_lock_params[1].device_name, nil) -- characterisation: devices carry no device_name
    env.prog.nrpn_stored_modes = {[3] = {digitone = {fm_parameters_syn_1_mix = "legacy-half"}}}
    pm.update_param(2, channel, mix, digitone)
    luaunit.assert_equals(channel.trig_lock_params[2].nrpn_lsb_mode, "legacy-half") -- characterisation: keyed by channel number and device id
    local other = {number = 4, trig_lock_params = {}}
    pm.update_param(2, other, mix, digitone)
    luaunit.assert_equals(other.trig_lock_params[2].nrpn_lsb_mode, "standard") -- characterisation
    local d2 = dm.get_device("digitakt2")
    pm.update_param(3, channel, find_by_id(dm.get_params("digitakt2"), "source_parameters_source_tune"), d2)
    luaunit.assert_equals(channel.trig_lock_params[3].nrpn_lsb_mode, "legacy-half") -- characterisation: device default
    -- characterisation: a mode is recorded only when both NRPN numbers are present
    pm.update_param(4, channel, {id = "msb_only", index = 30, nrpn_msb = 1}, d2)
    luaunit.assert_nil(channel.trig_lock_params[4].nrpn_lsb_mode)
    pm.update_param(5, channel, {id = "lsb_only", index = 31, nrpn_lsb = 1}, d2)
    luaunit.assert_nil(channel.trig_lock_params[5].nrpn_lsb_mode)
  end)
end

-------------------------------------------------------------------------------
-- param_manager.update_default_params
-------------------------------------------------------------------------------

function test_real_param_manager_update_default_params_assigns_the_auto_mapped_params()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = include("mosaic/lib/devices/param_manager")
    for device_id, entries in pairs(AUTO_MAPPED) do
      local device = dm.get_device(device_id)
      local channel = {number = 8, trig_lock_params = {}}
      env.dirty_clears = {}
      local refreshes = env.refreshes
      pm.update_default_params(channel, device)
      for i, e in ipairs(entries) do
        local slot = channel.trig_lock_params[i]
        luaunit.assert_equals({slot.id, slot.param_id, slot.type, slot.device_name, slot.index},
          {e[1], slot_id(8, e[2]), "midi", "", e[2]}, device_id .. ":" .. i) -- characterisation
        luaunit.assert_equals(actual_midi_fields(slot), expected_midi_fields(e[3]), device_id .. ":" .. i) -- characterisation
        local mode = nil
        if is_nrpn(e[3]) then mode = device_id == "digitakt2" and "legacy-half" or "standard" end
        luaunit.assert_equals(slot.nrpn_lsb_mode, mode, device_id .. ":" .. i) -- characterisation
      end
      for i = #entries + 1, 10 do
        luaunit.assert_equals(channel.trig_lock_params[i], {}, device_id .. ":" .. i) -- characterisation
      end
      local expected_clears = {}
      for i = 1, 10 do expected_clears[i] = {8, i} end
      luaunit.assert_equals(env.dirty_clears, expected_clears) -- characterisation
      luaunit.assert_equals(env.refreshes - refreshes, 1) -- characterisation
    end
    luaunit.assert_equals(env.params.set_calls, {}) -- characterisation: no fixed_note on these devices
  end)
end

function test_real_param_manager_update_default_params_copies_do_not_alias_the_cache()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = include("mosaic/lib/devices/param_manager")
    local channel = {number = 1, trig_lock_params = {}}
    pm.update_default_params(channel, dm.get_device("nord-drum-2"))
    local cached = find_by_id(dm.get_params("nord-drum-2"), "tone_wave")
    luaunit.assert_not_is(channel.trig_lock_params[1], cached) -- characterisation
    channel.trig_lock_params[1].ui_labels[2] = "changed"
    luaunit.assert_not_equals(cached.ui_labels[2], "changed") -- characterisation
    luaunit.assert_nil(cached.param_id) -- characterisation: the cache is not stamped per channel
    luaunit.assert_nil(cached.device_name) -- characterisation
  end)
end

function test_real_param_manager_update_default_params_edge_cases()
  isolated(function(env)
    load_device_map(env)
    local pm = include("mosaic/lib/devices/param_manager")
    local keep = {id = "kept"}
    local channel = {number = 2, trig_lock_params = {[3] = keep}}
    -- 1: a known stock id, 2: an unknown id, 3: a non-string id, 4-10: nothing mapped
    local meta = {id = "no-such-device", type = "norns", device_name = "Custom", fixed_note = 64,
                  map_params_automatically = {"trig_probability", "missing", 7}}
    pm.update_default_params(channel, meta)
    local slot = channel.trig_lock_params[1]
    luaunit.assert_equals({slot.id, slot.type, slot.device_name, slot.index}, {"trig_probability", "norns", "Custom", 6}) -- characterisation
    luaunit.assert_nil(slot.param_id) -- characterisation: non-midi keeps the copied (absent) param_id
    luaunit.assert_equals(channel.trig_lock_params[2], {}) -- characterisation
    luaunit.assert_is(channel.trig_lock_params[3], keep) -- characterisation: non-string id leaves the slot alone
    for i = 4, 10 do luaunit.assert_equals(channel.trig_lock_params[i], {}) end -- characterisation
    local clears = {}
    for _, c in ipairs(env.dirty_clears) do table.insert(clears, c[2]) end
    luaunit.assert_equals(clears, {1, 2, 4, 5, 6, 7, 8, 9, 10}) -- characterisation: slot 3 not cleared
    luaunit.assert_equals(env.params.set_calls, {{id = slot_id(2, 2), value = 64}}) -- characterisation
  end)
end

function test_real_param_manager_update_default_params_without_a_map_empties_every_slot()
  isolated(function(env)
    local dm = load_device_map(env)
    local pm = include("mosaic/lib/devices/param_manager")
    local channel = {number = 3}
    pm.update_default_params(channel, dm.get_device("cc_device"))
    luaunit.assert_equals(#channel.trig_lock_params, 10) -- characterisation: created when absent
    for i = 1, 10 do luaunit.assert_equals(channel.trig_lock_params[i], {}) end -- characterisation
    luaunit.assert_equals(count_keys(dm.params_cache), 1) -- characterisation
    luaunit.assert_not_nil(dm.params_cache["cc_device"]) -- characterisation: get_params received the device id
  end)
end

function test_real_param_manager_update_default_params_records_nrpn_mode_only_with_both_numbers()
  isolated(function(env)
    local data = make_data_dir(env, {["a.json"] = '[{"id":"fx","name":"Fx","type":"midi",' ..
      '"map_params_automatically":["both","msb_only","lsb_only"],"params":[' ..
      '{"id":"both","name":"Both","nrpn_msb":1,"nrpn_lsb":2},' ..
      '{"id":"msb_only","name":"Msb","nrpn_msb":1},' ..
      '{"id":"lsb_only","name":"Lsb","nrpn_lsb":2}]}]'})
    local dm = load_device_map(env, data)
    local pm = include("mosaic/lib/devices/param_manager")
    local channel = {number = 1, trig_lock_params = {}}
    pm.update_default_params(channel, dm.get_device("fx"))
    local slots = channel.trig_lock_params
    luaunit.assert_equals({slots[1].param_id, slots[1].nrpn_lsb_mode}, {slot_id(1, 16), "standard"}) -- characterisation
    luaunit.assert_equals({slots[2].id, slots[2].nrpn_lsb_mode}, {"msb_only", nil}) -- characterisation
    luaunit.assert_equals({slots[3].id, slots[3].nrpn_lsb_mode}, {"lsb_only", nil}) -- characterisation
  end)
end

function test_real_param_manager_update_default_params_defaults_meta_fields()
  isolated(function(env)
    load_device_map(env)
    local pm = include("mosaic/lib/devices/param_manager")
    local channel = {trig_lock_params = {}}
    pm.update_default_params(channel, {id = "none", map_params_automatically = {"fixed_note"}, fixed_note = 12})
    local slot = channel.trig_lock_params[1]
    luaunit.assert_equals({slot.id, slot.type, slot.device_name}, {"fixed_note", "", ""}) -- characterisation
    luaunit.assert_equals(env.params.set_calls, {{id = "midi_device_params_channel_0_2", value = 12}}) -- characterisation: nil channel number formats as 0
  end)
end

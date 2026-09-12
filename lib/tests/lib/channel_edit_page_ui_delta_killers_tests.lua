-- Wave-4 mutation killers for lib/pages/channel_edit_page/channel_edit_page_ui.lua and
-- channel_edit_page_ui_handlers.lua: the lines the wave-3 units newly execute (the X labels of
-- the value selectors, the clock-mods page's global-mode fallback and selector navigation, the
-- Device Config page's MIDI-device list, the i2c pull-ups on device confirmation, the reset of
-- the ten trig-lock slots, the memory window, the key guards for held grid steps, the
-- slide-lock marker, screen redraw requests and the Note Dashboard's partial updates).
--
-- One test per (function, pattern) group. README.md is cited where the manual states the
-- behaviour; everything else pins current behaviour and is labelled `-- characterisation`.
--
-- Harness (copied from channel_edit_page_ui_mutation_killers_tests.lua): every test loads a
-- FRESH copy of the module inside `isolated` (include() is dofile, so its module-local
-- selectors start from their constructor state), the collaborators the page calls are
-- recording stubs, include() hands back stubs for m_midi and param_manager, and `isolated`
-- snapshots the whole of _G and afterwards restores every changed value and removes every new
-- key, even when the test fails. fn stays real; its module-local redraw flag
-- (fn.dirty_screen) is put back to its previous boolean value afterwards.

local UI_MODULE = "mosaic/lib/pages/channel_edit_page/channel_edit_page_ui"
local divisions = include("mosaic/lib/clock/divisions")

local SELECTED = 2 -- the selected channel's number

------------------------------------------------------------------------------------------------
-- Harness
------------------------------------------------------------------------------------------------

-- A recording screen: env.frame gets "x,y text" per text call, env.bright the texts drawn at
-- level 15 (the selected selector), env.lines "x1,y1-x2,y2" per screen.line.
local function new_screen(env)
  env.frame, env.bright, env.lines = {}, {}, {}
  local x, y, level = 0 / 0, 0 / 0, 0
  local function put(text)
    table.insert(env.frame, string.format("%.10g,%.10g %s", x, y, tostring(text)))
    if level == 15 then table.insert(env.bright, tostring(text)) end
  end
  return setmetatable({
    move = function(nx, ny) x, y = nx, ny end,
    line = function(nx, ny)
      table.insert(env.lines, string.format("%.10g,%.10g-%.10g,%.10g", x, y, nx, ny))
      x, y = nx, ny
    end,
    level = function(l) level = l end,
    text = put, text_trim = put, text_right = put, text_center = put
  }, {__index = function() return function() end end})
end

local function recorder_of(env, name, result)
  return function(...)
    table.insert(env.calls, table.pack(name, ...))
    return result
  end
end

local function new_channel(number)
  local c = {
    number = number,
    trig_lock_params = {},
    clock_mods = {name = "/1", value = 1, type = "clock_division"},
    step_note_masks = {}, step_velocity_masks = {}, step_length_masks = {},
    step_trig_masks = {}, step_chord_masks = {}
  }
  for i = 1, 10 do c.trig_lock_params[i] = {} end
  return c
end

local function install_stubs(env)
  env.calls = {}
  env.pressed = {}
  env.memory_events = {}
  env.params = {
    global_swing_shuffle_type = 1, global_swing = 0, global_shuffle_feel = 0,
    global_shuffle_basis = 0, global_shuffle_amount = 0, record = 1
  }
  env.channel = new_channel(SELECTED)
  env.devices = {
    {id = "midi", name = "MIDI", type = "midi"},
    {id = "fixed", name = "Fixed", type = "midi", default_midi_channel = 10, default_midi_device = 1},
    {id = "norns_engine", name = "Engine", type = "norns"}
  }
  env.device_params = {}
  env.program_state = {
    selected_channel = SELECTED,
    selected_song_pattern = 1,
    devices = {[SELECTED] = {midi_channel = 1, midi_device = 1, device_map = "midi"}}
  }
  env.playing = false
  env.step_slide = function() return false end

  screen = new_screen(env)
  m_grid = {get_pressed_keys = function() return env.pressed end}
  params = {
    get = function(_, id) return env.params[id] end,
    lookup = {}
  }
  memory = {
    get_total_event_count = function() return #env.memory_events end,
    get_event_count = function() return #env.memory_events end,
    get_recent_events = function(c, count)
      table.insert(env.calls, table.pack("memory.get_recent_events", c, count))
      local out = {}
      for i = 1, math.min(count, #env.memory_events) do out[i] = env.memory_events[i] end
      return out
    end
  }
  program = {
    get = function() return env.program_state end,
    get_selected_channel = function() return env.channel end,
    get_channel = function(_, c) return c == SELECTED and env.channel or new_channel(c) end,
    get_song_pattern = function() return 1 end,
    get_selected_song_pattern = function() return 1 end,
    get_channel_param_slide = function() return false end,
    get_step_param_slide = function(_, s, i) return env.step_slide(s, i) end,
    get_step_param_trig_lock = function() return nil end,
    get_current_step_for_channel = function() return 1 end,
    get_effective_swing_shuffle_type = recorder_of(env, "program.get_effective_swing_shuffle_type", 11),
    get_effective_swing = recorder_of(env, "program.get_effective_swing", 12),
    get_effective_shuffle_feel = recorder_of(env, "program.get_effective_shuffle_feel", 13),
    get_effective_shuffle_basis = recorder_of(env, "program.get_effective_shuffle_basis", 14),
    get_effective_shuffle_amount = recorder_of(env, "program.get_effective_shuffle_amount", 15),
    increment_trig_lock_calculator_id = recorder_of(env, "program.increment_trig_lock_calculator_id"),
    clear_device_trig_locks_for_channel = function() end,
    clear_masks_for_step_for_channel = recorder_of(env, "program.clear_masks_for_step_for_channel"),
    clear_trig_locks_for_step_for_channel = recorder_of(env, "program.clear_trig_locks_for_step_for_channel"),
    toggle_step_param_slide = recorder_of(env, "program.toggle_step_param_slide"),
    toggle_channel_param_slide = recorder_of(env, "program.toggle_channel_param_slide")
  }
  m_clock = {
    get_clock_divisions = function() return divisions.clock_divisions end,
    calculate_divisor = function(mods) return {divisor_of = mods} end,
    is_playing = function() return env.playing end,
    set_swing_shuffle_type = recorder_of(env, "m_clock.set_swing_shuffle_type"),
    set_channel_swing = recorder_of(env, "m_clock.set_channel_swing"),
    set_channel_shuffle_feel = recorder_of(env, "m_clock.set_channel_shuffle_feel"),
    set_channel_shuffle_basis = recorder_of(env, "m_clock.set_channel_shuffle_basis"),
    set_channel_shuffle_amount = recorder_of(env, "m_clock.set_channel_shuffle_amount"),
    set_channel_division = recorder_of(env, "m_clock.set_channel_division"),
    channel_is_sliding = function() return false end
  }
  device_map = {
    get_devices = function() return env.devices end,
    get_device = function(id) return fn.get_by_id(env.devices, id) end,
    get_params = function() return env.device_params end,
    get_available_devices_for_channel = function() return env.devices end,
    get_available_params_for_channel = function() return env.device_params end
  }
  draw = {register_ui = function(_, name, func) env.draws = env.draws or {}; env.draws[name] = func end}
  tooltip = {
    show = function(_, message) table.insert(env.calls, table.pack("tooltip.show", message)) end,
    error = function(_, message) table.insert(env.calls, table.pack("tooltip.error", message)) end
  }
  recorder = {clear_trig_lock_dirty = recorder_of(env, "recorder.clear_trig_lock_dirty")}
  pattern = {update_working_pattern = function() end}
  step = {queue_for_pattern_change = recorder_of(env, "step.queue_for_pattern_change")}
  crow = {ii = {
    pullup = recorder_of(env, "crow.ii.pullup"),
    jf = {mode = recorder_of(env, "crow.ii.jf.mode")}
  }}
  norns_param_state_handler = {get_original_param_state = function() return {} end}
  is_key1_down = false
end

local STUB_MODULES = {
  ["mosaic/lib/m_midi"] = function(env)
    return {
      get_midi_outs = function() return {{name = "port one", value = 1}, {name = "port two", value = 2}} end,
      midi_devices_connected = function() return env.midi_connected ~= false end
    }
  end,
  ["mosaic/lib/devices/param_manager"] = function(env)
    return {
      add_device_params = recorder_of(env, "param_manager.add_device_params"),
      update_default_params = function() end
    }
  end
}

local function isolated(body)
  local before = {}
  for k, v in pairs(_G) do before[k] = v end
  local dirty_before = fn.dirty_screen()
  local env = {}
  local ok, err = pcall(function()
    install_stubs(env)
    local real_include = before.include
    include = function(file)
      if STUB_MODULES[file] then return STUB_MODULES[file](env) end
      -- the handlers/refreshers include script-relative "lib/..." paths
      if file:sub(1, 4) == "lib/" then return real_include("mosaic/" .. file) end
      return real_include(file)
    end
    save_confirm = include("mosaic/lib/ui_components/save_confirm")
    env.ui = include(UI_MODULE)
    channel_edit_page_ui = env.ui -- the handlers and refreshers call back through this global
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
  if type(dirty_before) == "boolean" then fn.dirty_screen(dirty_before) end
  if not ok then error(err, 0) end
end

-- register the draw, then init, in lib/ui.lua's order (ui.init)
local function start(env)
  env.ui.register_ui_draws()
  env.ui.init()
end

-- Draw the channel editor once; returns the sorted "x,y text" entries it drew.
local function frame(env)
  env.frame, env.bright, env.lines = {}, {}, {}
  env.draws.channel_edit_page()
  local f = env.frame
  table.sort(f)
  return f
end

-- The entries of one frame that are not the page tabs or the page title.
local function body_of(env)
  local out = {}
  for _, e in ipairs(frame(env)) do
    if not e:match("^%d+,1 _$") and not e:match("^0,9 ") then table.insert(out, e) end
  end
  return out
end

local function calls_named(env, name, from)
  local out = {}
  for i = from or 1, #env.calls do
    local c = env.calls[i]
    if c[1] == name then
      local args = {}
      for k = 2, c.n do args[k - 1] = c[k] end
      table.insert(out, args)
    end
  end
  return out
end

local function turn(env, n, d) env.ui.enc(n, d) end

local function press(env, n) env.ui.key(n, 1) end

-- The label of the selector drawn at level 15 (the selected one), or nil.
local function selected_label(env)
  frame(env)
  return env.bright[1]
end

------------------------------------------------------------------------------------------------
-- configure_note_value_selector (156) and configure_note_page_velocity_length_value_selector
-- (162): -1 means "no value" and is shown as X.
------------------------------------------------------------------------------------------------

function test_w4c_unset_masks_and_dashboard_notes_show_x()
  isolated(function(env)
    start(env) -- a channel with no masks at all
    env.ui.select_mask_page()
    -- characterisation: every unset mask shows "X" (note -1, velocity -1, length 0, chord 0)
    luaunit.assert_equals(body_of(env), {
      "0,18 Trig", "0,26 X", "0,40 Chd1", "0,48 X", "25,18 Note", "25,26 X", "25,40 Chd2", "25,48 X",
      "50,18 Vel", "50,26 X", "50,40 Chd3", "50,48 X", "75,18 Len", "75,26 X", "75,40 Chd4", "75,48 X"
    })
    -- Selecting a channel on the grid resets the dashboard with -1 everywhere
    -- (channel_edit_page.lua:203-208). README.md:679: the dashboard shows the last played notes.
    env.ui.select_note_dashboard_page()
    env.ui.set_note_dashboard_values({note = -1, velocity = -1, length = -1, chords = {-1, -1, -1, -1}})
    -- No note has velocity or length -1, so every cell shows the Note cell's absence marker "X"
    -- (the marker is characterisation; bugs.json dashboard-absent-velocity-length, M-DASHBOARD-SELECT-001).
    luaunit.assert_equals(body_of(env), {
      "0,18 Note", "0,26 X", "0,40 Chd1", "0,48 X", "25,18 Vel", "25,26 X", "25,40 Chd2", "25,48 X",
      "50,18 Len", "50,26 X", "50,40 Chd3", "50,48 X", "75,40 Chd4", "75,48 X"
    })
  end)
end

------------------------------------------------------------------------------------------------
-- Clock-mods page (draw 247; ui_handlers 51, 74): an X swing type takes the global type.
------------------------------------------------------------------------------------------------

-- {channel swing_shuffle_type (nil = X), global_swing_shuffle_type, controls shown after the
-- type selector}
local MODE_CASES = {
  {nil, 1, "swing"}, {nil, 2, "shuffle"},
  {1, 1, "swing"}, {1, 2, "swing"},
  {2, 1, "shuffle"}, {2, 2, "shuffle"}
}

local SWING_CONTROLS = {"0,40 Swing", "0,48 X"}
local SHUFFLE_CONTROLS = {"0,40 Feel", "0,48 X", "40,40 Basis", "40,48 X", "70,40 Amount", "70,48 0"}

function test_w4c_clock_mods_page_draws_the_controls_of_the_effective_mode()
  for _, case in ipairs(MODE_CASES) do
    isolated(function(env)
      env.channel.swing_shuffle_type = case[1]
      env.params.global_swing_shuffle_type = case[2]
      start(env)
      env.ui.select_clock_mods_page()
      local label = tostring(case[1]) .. "/" .. case[2]
      -- README.md:687: an unset ("X") channel takes the global mode; an explicit mode overrides it.
      local expected = {"0,18 Clock Mod", "0,26 /1", "70,18 Swing Type",
        "70,26 " .. ({[0] = "X", "Swing", "Shuffle"})[case[1] or 0]}
      for _, e in ipairs(case[3] == "swing" and SWING_CONTROLS or SHUFFLE_CONTROLS) do
        table.insert(expected, e)
      end
      table.sort(expected)
      luaunit.assert_equals(body_of(env), expected, label)
    end)
  end
end

function test_w4c_encoder_two_walks_the_visible_clock_mods_selectors_and_stops_at_the_last()
  for _, case in ipairs(MODE_CASES) do
    isolated(function(env)
      env.channel.swing_shuffle_type = case[1]
      env.params.global_swing_shuffle_type = case[2]
      start(env)
      env.ui.select_clock_mods_page()
      local label = tostring(case[1]) .. "/" .. case[2]
      -- README.md:291: E2 chooses the setting; README.md:687: an X channel follows the global
      -- mode, so its controls are the global mode's. characterisation: E2 right stops at the last.
      local expected = case[3] == "swing"
        and {"Clock Mod", "Swing Type", "Swing", "Swing", "Swing"}
        or {"Clock Mod", "Swing Type", "Feel", "Basis", "Amount", "Amount", "Amount"}
      local walked = {selected_label(env)}
      for _ = 2, #expected do
        turn(env, 2, 1)
        table.insert(walked, selected_label(env))
      end
      luaunit.assert_equals(walked, expected, label)
    end)
  end
end

------------------------------------------------------------------------------------------------
-- Device Config page draw (264): the MIDI device list shows only for a device without a fixed
-- MIDI device, and only while a MIDI output is connected.
------------------------------------------------------------------------------------------------

function test_w4c_device_config_shows_the_midi_device_list_only_when_choosable()
  local cases = {
    -- {device, connected, expected body}
    {{id = "free", name = "Free", type = "midi"}, true,
      {"10,35 Free", "70,35 CC1", "65,45 CC2", "95,35 port one", "90,45 port two"}},
    {{id = "free", name = "Free", type = "midi"}, false,
      {"10,35 Free", "70,35 CC1", "65,45 CC2"}},
    -- a device config with a default MIDI device but no default channel
    {{id = "pinned", name = "Pinned", type = "midi", default_midi_device = 1}, true,
      {"10,35 Pinned", "70,35 CC1", "65,45 CC2"}}
  }
  for i, case in ipairs(cases) do
    isolated(function(env)
      env.devices = {case[1]}
      env.midi_connected = case[2]
      env.program_state.devices[SELECTED] = {midi_channel = 1, midi_device = 1, device_map = case[1].id}
      start(env)
      env.ui.select_midi_config_page()
      local expected = case[3]
      table.sort(expected)
      -- characterisation: the device list (x = 90) is drawn only when the device has no default
      -- MIDI device AND a MIDI output is connected; the channel list (x = 65) when it has no
      -- default channel.
      luaunit.assert_equals(body_of(env), expected, "case " .. i)
    end)
  end
end

------------------------------------------------------------------------------------------------
-- update_channel_config (554, 572-588, 600): what confirming a device does.
------------------------------------------------------------------------------------------------

-- Device Config: scroll the device list from `from` to the next entry and press K3.
local function confirm_next_device(env, from, target)
  env.devices = {from, target}
  env.program_state.devices[SELECTED] = {midi_channel = 1, midi_device = 1, device_map = from.id}
  start(env)
  env.ui.select_midi_config_page()
  turn(env, 3, 1)
  local mark = #env.calls + 1
  press(env, 3)
  luaunit.assert_equals(env.program_state.devices[SELECTED].device_map, target.id)
  return mark
end

local MIDI_DEVICE = {id = "midi", name = "MIDI", type = "midi"}

local JF_IDS = {"jf kit", "jf n 1", "jf n 2", "jf poly", "jf unison", "jf n 5", "jf mpe", "jf n 4",
  "jf n 3", "jf n 6"}

function test_w4c_confirming_an_i2c_device_enables_the_crow_pullups()
  -- README.md:189: Just Friends and Ansible are driven over i2c (n.b.). characterisation: a Just
  -- Friends voice enables crow's i2c pull-ups and puts JF in mode 1; Ansible 1/2 only the pull-ups.
  local cases = {}
  for _, id in ipairs(JF_IDS) do table.insert(cases, {id, {{true}}, {{1}}}) end
  table.insert(cases, {"ansible 1", {{true}}, {}})
  table.insert(cases, {"ansible 2", {{true}}, {}})
  -- characterisation: other devices touch neither.
  table.insert(cases, {"crow 1/2", {}, {}})
  table.insert(cases, {"emplait 1", {}, {}})
  -- characterisation (suspected defect: "ansible 3" and "ansible 4" are tested n.b. players
  -- (device_map.lua:300, 304) but lines 587-588 enable the pull-ups only for Ansible 1 and 2).
  table.insert(cases, {"ansible 3", {}, {}})
  for _, case in ipairs(cases) do
    isolated(function(env)
      local mark = confirm_next_device(env, MIDI_DEVICE, {id = case[1], name = case[1], type = "norns"})
      luaunit.assert_equals(calls_named(env, "crow.ii.pullup", mark), case[2], case[1])
      luaunit.assert_equals(calls_named(env, "crow.ii.jf.mode", mark), case[3], case[1])
    end)
  end
  isolated(function(env)
    local mark = confirm_next_device(env, {id = "jf kit", name = "JF", type = "norns"}, MIDI_DEVICE)
    luaunit.assert_equals(calls_named(env, "crow.ii.pullup", mark), {}, "midi")
    luaunit.assert_equals(calls_named(env, "crow.ii.jf.mode", mark), {}, "midi")
  end)
end

function test_w4c_confirming_a_device_resets_all_ten_trig_lock_slots()
  isolated(function(env)
    local mark = confirm_next_device(env, MIDI_DEVICE, {id = "other", name = "Other", type = "midi"})
    local dirty, calculators = {}, {}
    for slot = 1, 10 do
      table.insert(dirty, {SELECTED, slot})
      table.insert(calculators, {env.channel, slot})
    end
    -- README.md:241: applying a MIDI device change resets the pending parameter recording, of
    -- every slot and of no other.
    luaunit.assert_equals(calls_named(env, "recorder.clear_trig_lock_dirty", mark), dirty)
    -- characterisation: each of the ten dials gets a fresh lock calculator
    luaunit.assert_equals(calls_named(env, "program.increment_trig_lock_calculator_id", mark), calculators)
  end)
end

------------------------------------------------------------------------------------------------
-- handle_midi_config_page_increment / _decrement (1512, 1537): a confirmed device resets the
-- trig-lock parameter picker to its first entry.
------------------------------------------------------------------------------------------------

function test_w4c_confirming_a_device_resets_the_open_param_picker_to_its_first_entry()
  for _, direction in ipairs({1, -1}) do
    isolated(function(env)
      env.devices = {MIDI_DEVICE, {id = "other", name = "Other", type = "midi"}}
      env.program_state.devices[SELECTED] = {midi_channel = 1, midi_device = 1, device_map = "other"}
      env.device_params = {{id = "alpha", name = "Alpha"}, {id = "beta", name = "Beta"}, {id = "gamma", name = "Gamma"}}
      env.channel.trig_lock_params[1].id = "gamma" -- dial 1 holds Gamma
      start(env)
      turn(env, 1, 1) -- Masks -> Trig Locks
      press(env, 2) -- README.md:757: K2 opens the parameter picker
      -- characterisation: the picker opens on the dial's current parameter
      luaunit.assert_equals(body_of(env), {"30,25 Beta", "35,35 Gamma"}, "E3 " .. direction)
      turn(env, 1, 3) -- Trig Locks -> Device Config (the picker page stays open)
      turn(env, 3, direction)
      press(env, 3)
      turn(env, 1, -3) -- back to Trig Locks
      -- characterisation: after a device is applied the picker's current entry is the first
      luaunit.assert_equals(body_of(env), {"30,45 Beta", "35,35 Alpha"}, "E3 " .. direction)
    end)
  end
end

------------------------------------------------------------------------------------------------
-- refresh_memory (894): the Memory page draws a 25-event window.
------------------------------------------------------------------------------------------------

function test_w4c_memory_page_reads_a_window_of_25_recent_events()
  isolated(function(env)
    for i = 1, 30 do env.memory_events[i] = {type = "trig_lock"} end
    -- the 26th most recent action is the first note: outside the window
    env.memory_events[26] = {type = "note_mask", data = {event_data = {note = 90}}}
    start(env)
    env.ui.select_memory_page()
    luaunit.assert_equals(calls_named(env, "memory.get_recent_events")[1], {SELECTED, 25})
    -- README.md:700: each action is an icon, the most recent on the right. characterisation: 15
    -- icons, 5 px apart; with no note inside the window a trig-lock icon sits at the default
    -- height (60 -> y 38), not at the height of a note outside it.
    local icons = {}
    for _, e in ipairs(frame(env)) do
      if e:match(" T$") then table.insert(icons, e) end
    end
    local expected = {}
    for i = 1, 15 do table.insert(expected, string.format("%d,38 T", 120 - i * 5)) end
    table.sort(expected)
    luaunit.assert_equals(icons, expected)
  end)
end

------------------------------------------------------------------------------------------------
-- key (835), handle_key_two_pressed (1561), handle_key_three_pressed (1637): which key events
-- act, and how held grid steps change them.
------------------------------------------------------------------------------------------------

-- Clock-mods page with an unconfirmed swing-type edit (X -> Swing).
local function pending_swing_type_edit(env)
  start(env)
  env.ui.select_clock_mods_page()
  turn(env, 2, 1)
  turn(env, 3, 1)
end

function test_w4c_only_a_k3_press_with_no_step_held_confirms()
  isolated(function(env)
    pending_swing_type_edit(env)
    -- characterisation: releasing K3 and pressing / releasing K1 confirm nothing
    env.ui.key(3, 0)
    env.ui.key(1, 1)
    env.ui.key(1, 0)
    luaunit.assert_equals(calls_named(env, "m_clock.set_swing_shuffle_type"), {})
    -- characterisation: K3 with one grid step held does not confirm either
    env.pressed = {{3, 5}}
    press(env, 3)
    luaunit.assert_equals(calls_named(env, "m_clock.set_swing_shuffle_type"), {})
    -- README.md:291: K3 applies the change (here with nothing held on the grid)
    env.pressed = {}
    press(env, 3)
    luaunit.assert_equals(calls_named(env, "m_clock.set_swing_shuffle_type"), {{SELECTED, 1}})
  end)
end

function test_w4c_k2_with_one_held_step_clears_that_steps_locks()
  isolated(function(env)
    start(env)
    env.pressed = {{3, 5}} -- step (5 - 4) * 16 + 3 = 19
    press(env, 2)
    -- README.md:607: on the Masks page, hold a step and press K2 to clear its step masks
    luaunit.assert_equals(calls_named(env, "program.clear_masks_for_step_for_channel"), {{env.channel, 19}})
    luaunit.assert_equals(calls_named(env, "tooltip.show"), {{"Masks for step 19 cleared"}}) -- characterisation
    turn(env, 1, 1) -- Masks -> Trig Locks
    local mark = #env.calls + 1
    press(env, 2)
    -- README.md:946-947: on the trig lock page, hold the step and press K2
    luaunit.assert_equals(calls_named(env, "program.clear_trig_locks_for_step_for_channel", mark), {{env.channel, 19}})
    luaunit.assert_equals(calls_named(env, "program.clear_masks_for_step_for_channel", mark), {})
  end)
end

------------------------------------------------------------------------------------------------
-- Dial display modifier (302): the slide-lock marker of a held step.
------------------------------------------------------------------------------------------------

function test_w4c_trig_lock_dial_marks_a_slide_locked_held_step()
  isolated(function(env)
    env.step_slide = function(s, i) return s == 3 and i == 2 end
    start(env)
    env.ui.select_trig_page()
    frame(env)
    luaunit.assert_equals(env.lines, {}) -- characterisation: nothing held, no marker
    env.pressed = {{3, 4}} -- step 3
    frame(env)
    -- README.md:966-969: hold a step and press K3 on a parameter to lock a slide to that step.
    -- characterisation: the dial (dial 2, at 25,18) gets a top and a right edge.
    luaunit.assert_equals(env.lines, {"25,12-48,12", "48,12-48,31"})
  end)
end

------------------------------------------------------------------------------------------------
-- Redraw requests (1441, 1654).
------------------------------------------------------------------------------------------------

function test_w4c_swing_type_edit_and_mask_page_selection_request_a_redraw()
  isolated(function(env)
    start(env)
    env.ui.select_clock_mods_page()
    turn(env, 2, 1) -- clock mod -> swing type
    fn.dirty_screen(false)
    turn(env, 3, 1)
    luaunit.assert_true(fn.dirty_screen()) -- characterisation: the edit is redrawn
    -- m_midi.lua:521 selects the mask page directly on MIDI input
    fn.dirty_screen(false)
    env.ui.select_mask_page()
    luaunit.assert_true(fn.dirty_screen()) -- characterisation
  end)
end

function test_w4c_encoder_one_page_changes_leave_a_redraw_requested()
  isolated(function(env)
    start(env)
    env.ui.select_trig_page()
    -- characterisation: E1 in either direction changes page and leaves the screen marked for redraw
    for _, d in ipairs({1, -1}) do
      fn.dirty_screen(false)
      turn(env, 1, d)
      luaunit.assert_true(fn.dirty_screen())
    end
  end)
end

------------------------------------------------------------------------------------------------
-- set_note_dashboard_values (1710-1726): partial updates as lib/step.lua sends them.
------------------------------------------------------------------------------------------------

local function dashboard(env)
  local out = {}
  for _, e in ipairs(body_of(env)) do
    local pos, text = e:match("^(%S+) (.*)$")
    if pos:match(",26$") or pos:match(",48$") then out[pos] = text end
  end
  return out
end

function test_w4c_dashboard_partial_updates_keep_the_other_values()
  isolated(function(env)
    start(env)
    env.ui.select_note_dashboard_page()
    env.ui.set_note_dashboard_values({note = 60, velocity = 100, length = 0.25, chords = {62, 64, 65, 67}})
    -- lib/step.lua:696-701 sends one strummed chord voice at a time: a sparse chords table only
    env.ui.set_note_dashboard_values({chords = {[2] = 69}})
    -- README.md:679: the dashboard shows the last played notes, so the others stay.
    luaunit.assert_equals(dashboard(env), {
      ["0,26"] = "C3", ["25,26"] = "100", ["50,26"] = "0.25",
      ["0,48"] = "D3", ["25,48"] = "A3", ["50,48"] = "F3", ["75,48"] = "G3"
    })
    -- lib/step.lua:660 sends the root without a chords table
    env.ui.set_note_dashboard_values({note = 62, velocity = 90, length = 0.5})
    luaunit.assert_equals(dashboard(env), {
      ["0,26"] = "D3", ["25,26"] = "90", ["50,26"] = "0.5",
      ["0,48"] = "D3", ["25,48"] = "A3", ["50,48"] = "F3", ["75,48"] = "G3"
    })
  end)
end

function test_w4c_dashboard_rounds_length_and_shows_chord_note_zero()
  isolated(function(env)
    start(env)
    env.ui.select_note_dashboard_page()
    env.ui.set_note_dashboard_values({chords = {62, 64, 65, 67}})
    local shown = {}
    for _, length in ipairs({1, 0.333, 2.5}) do
      env.ui.set_note_dashboard_values({note = 60, velocity = 100, length = length})
      table.insert(shown, dashboard(env)["50,26"])
    end
    luaunit.assert_equals(shown, {"1.0", "0.33", "2.5"}) -- characterisation: two decimals
    env.ui.set_note_dashboard_values({chords = {1, 0}})
    -- README.md:679: a chord voice sent as MIDI note 0 is a played note and is shown as C-2;
    -- this test pinned the old "0 means no chord" (human decision S51; bugs.json
    -- dashboard-chord-slots, M-DASHBOARD-CHORD-001).
    luaunit.assert_equals(dashboard(env)["0,48"], "C#-2")
    luaunit.assert_equals(dashboard(env)["25,48"], "C-2")
  end)
end

function test_w4c_fresh_dashboard_chord_slots_show_x()
  isolated(function(env)
    start(env)
    env.ui.select_note_dashboard_page()
    -- Human decision S51 (bugs.json dashboard-chord-slots): chord slots that never played
    -- show X (characterisation of the marker), not C-2 (MIDI 0).
    local d = dashboard(env)
    luaunit.assert_equals({d["0,48"], d["25,48"], d["50,48"], d["75,48"]}, {"X", "X", "X", "X"})
    -- A partial update leaves unplayed slots at X.
    env.ui.set_note_dashboard_values({chords = {[2] = 69}})
    d = dashboard(env)
    luaunit.assert_equals({d["0,48"], d["25,48"], d["50,48"], d["75,48"]}, {"X", "A3", "X", "X"})
  end)
end

-- Characterisation of R09 display coalescing; musical commits remain per release.
-- Real channel_edit_page.lua + real scheduler; only page collaborators are minimal.

local function r09_restore_globals(saved, names)
  for _, name in ipairs(names) do rawset(_G, name, saved[name]) end
end

function test_hardening_channel_step_releases_commit_individually_and_coalesce_only_refresh()
  local names = {
    "scheduler", "include", "fader", "button", "sequencer", "press",
    "channel_edit_page_ui", "program", "recorder", "pattern"
  }
  local saved = {}
  for _, name in ipairs(names) do saved[name] = rawget(_G, name) end

  local ok, err = pcall(function()
    local refreshes, commits, rebuilds = {}, {}, 0
    local selected = {number = 1}
    scheduler = dofile("../../lib/scheduler.lua")
    include = function(path)
      luaunit.assert_equals(path, "mosaic/lib/quantiser")
      return {}
    end

    local function control()
      return {is_this = function(_, _, y) return y >= 4 and y <= 7 end}
    end
    fader = {new = control}
    button = {new = control}
    sequencer = {new = control}
    _G.press = {
      post = {},
      register = function() end,
      register_long = function() end,
      register_pre = function() end,
      register_dual = function() end,
      register_post = function(_, page, handler)
        luaunit.assert_equals(page, "channel_edit_page")
        _G.press.post[#_G.press.post + 1] = handler
      end,
    }
    program = {
      get_selected_channel = function() return selected end,
      get = function() return {selected_song_pattern = 1, selected_channel = selected.number} end,
    }
    recorder = {
      record_stored_note_mask_events = function(channel, step)
        commits[#commits + 1] = {"mask", channel, step}
      end,
      record_stored_trig_lock_events = function(channel, step)
        commits[#commits + 1] = {"trig-lock", channel, step}
      end,
    }
    pattern = {
      update_working_patterns = function()
        rebuilds = rebuilds + 1
      end,
    }
    channel_edit_page_ui = {
      refresh_memory = function() refreshes[#refreshes + 1] = {"memory", selected.number} end,
      refresh_trig_locks = function() refreshes[#refreshes + 1] = {"trig-locks", selected.number} end,
      refresh_masks = function() refreshes[#refreshes + 1] = {"masks", selected.number} end,
    }

    local page = dofile("../../lib/pages/channel_edit_page/channel_edit_page.lua")
    page.refresh_faders = function()
      refreshes[#refreshes + 1] = {"faders", selected.number}
    end
    page.register_press()
    luaunit.assert_equals(#_G.press.post, 1)

    -- Each ordinary release records history and asks for musical rebuild before
    -- the UI scheduler is allowed to run.
    for step = 1, 3 do _G.press.post[1](step, 4) end
    luaunit.assert_equals(commits, {
      {"mask", 1, 1}, {"trig-lock", 1, 1},
      {"mask", 1, 2}, {"trig-lock", 1, 2},
      {"mask", 1, 3}, {"trig-lock", 1, 3},
    })
    luaunit.assert_equals(rebuilds, 3)
    luaunit.assert_equals(refreshes, {})

    -- Refresh is display-only and deliberately reads the selection when it runs.
    selected.number = 16
    scheduler.update()
    luaunit.assert_equals(refreshes, {
      {"memory", 16}, {"trig-locks", 16}, {"masks", 16}, {"faders", 16},
    })
    luaunit.assert_equals(scheduler.active_count, 0)
  end)

  r09_restore_globals(saved, names)
  luaunit.assert_true(ok, err)
end

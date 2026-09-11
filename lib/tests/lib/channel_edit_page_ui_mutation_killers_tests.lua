-- Mutation killers for lib/pages/channel_edit_page/channel_edit_page_ui.lua beyond its mask
-- handlers (those are pinned by channel_edit_mask_handler_tests.lua).
--
-- The surviving mutants sat in the module's load-time construction (lines 27-112): the screen
-- position of every widget on the six channel-editor pages, the option values of the swing and
-- shuffle list selectors, the swing / shuffle-amount ranges, the MIDI channel list values, the
-- ten trig-lock dials, the page-name-to-index map and which note-dashboard selectors show note
-- names (lines 195-200). None of those is visible except through the pages' drawing and through
-- the values the page hands to m_clock and program, so these tests drive the page the way
-- lib/ui.lua does (register_ui_draws, init, enc, key) and pin:
--   * the text each page draws and where (a recording `screen`), per page;
--   * the values handed to m_clock and program when an edit is confirmed with K3.
--
-- README.md:683 (per-channel clock division and multiplication on the channel editor page),
-- README.md:685 (swing -50..50; shuffle with a feel and a basis) and README.md:687 ("X" takes
-- the global setting; while stopped, confirmed changes apply immediately) are the manual
-- statements behind the clock-mods page. Screen coordinates, labels and option orders are not
-- stated in README.md and are pinned as `-- characterisation`.
--
-- Every test loads a FRESH copy of the module inside `isolated`: include() is dofile, so the
-- module-local selectors start from their constructor state each time. The collaborators the
-- page calls (program, params, memory, m_clock, device_map, screen, ...) are recording stubs,
-- and include() hands back stubs for m_midi and param_manager (the module's own includes);
-- save_confirm, the page/selector components, the handlers and the refreshers stay real.
-- `isolated` snapshots the whole of _G and afterwards restores every changed value and removes
-- every new key, even when the test fails.

local UI_MODULE = "mosaic/lib/pages/channel_edit_page/channel_edit_page_ui"
local divisions = include("mosaic/lib/clock/divisions")

local SELECTED = 2 -- the selected channel's number

------------------------------------------------------------------------------------------------
-- Harness
------------------------------------------------------------------------------------------------

local function new_screen(env)
  env.frame = {}
  local x, y = 0 / 0, 0 / 0
  local function put(text)
    -- %.10g: a coordinate is a number; 0 and 0.0 draw the same pixel, so they print the same
    table.insert(env.frame, string.format("%.10g,%.10g %s", x, y, tostring(text)))
  end
  return setmetatable({
    move = function(nx, ny) x, y = nx, ny end,
    text = function(t) put(t) end,
    text_trim = function(t) put(t) end,
    text_right = function(t) put(t) end,
    text_center = function(t) put(t) end
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
  env.program_state = {
    selected_channel = SELECTED,
    selected_song_pattern = 1,
    devices = {[SELECTED] = {midi_channel = 1, midi_device = 1, device_map = "midi"}}
  }
  env.playing = false

  screen = new_screen(env)
  m_grid = {get_pressed_keys = function() return env.pressed end}
  params = {
    get = function(_, id) return env.params[id] end,
    lookup = {}
  }
  memory = {
    get_total_event_count = function() return 0 end,
    get_event_count = function() return 0 end,
    get_recent_events = function() return {} end
  }
  program = {
    get = function() return env.program_state end,
    get_selected_channel = function() return env.channel end,
    get_channel = function(_, c) return c == SELECTED and env.channel or new_channel(c) end,
    get_selected_song_pattern = function() return 1 end,
    get_channel_param_slide = function() return false end,
    get_step_param_slide = function() return false end,
    get_current_step_for_channel = function() return 1 end,
    get_effective_swing_shuffle_type = recorder_of(env, "program.get_effective_swing_shuffle_type", 11),
    get_effective_swing = recorder_of(env, "program.get_effective_swing", 12),
    get_effective_shuffle_feel = recorder_of(env, "program.get_effective_shuffle_feel", 13),
    get_effective_shuffle_basis = recorder_of(env, "program.get_effective_shuffle_basis", 14),
    get_effective_shuffle_amount = recorder_of(env, "program.get_effective_shuffle_amount", 15),
    increment_trig_lock_calculator_id = function() end,
    clear_device_trig_locks_for_channel = function() end
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
    get_params = function() return {} end,
    get_available_devices_for_channel = function() return env.devices end,
    get_available_params_for_channel = function() return {} end
  }
  draw = {register_ui = function(_, name, func) env.draws = env.draws or {}; env.draws[name] = func end}
  tooltip = {show = function() end, error = function() end}
  recorder = {clear_trig_lock_dirty = function() end}
  pattern = {update_working_pattern = function() end}
  step = {queue_for_pattern_change = recorder_of(env, "step.queue_for_pattern_change")}
  crow = {ii = {pullup = function() end, jf = {mode = function() end}}}
  norns_param_state_handler = {get_original_param_state = function() return {} end}
  is_key1_down = false
end

local STUB_MODULES = {
  ["mosaic/lib/m_midi"] = function(env)
    return {
      get_midi_outs = function() return {{name = "port one", value = 1}, {name = "port two", value = 2}} end,
      midi_devices_connected = function() return true end
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
  if not ok then error(err, 0) end
end

-- register the draw, then init, in lib/ui.lua's order (ui.init)
local function start(env)
  env.ui.register_ui_draws()
  env.ui.init()
end

-- Draw the channel editor once; returns the sorted "x,y text" entries it drew.
local function frame(env)
  env.frame = {}
  env.draws.channel_edit_page()
  local f = env.frame
  table.sort(f)
  return f
end

local function calls_named(env, prefix)
  local out = {}
  for _, c in ipairs(env.calls) do
    if c[1]:sub(1, #prefix) == prefix then table.insert(out, c) end
  end
  return out
end


-- The row of page tabs pages:draw puts at y = 1: one per page, six pages.
local TABS = {"0,1 _", "10,1 _", "20,1 _", "30,1 _", "40,1 _", "50,1 _"}

local function with_tabs(entries)
  local all = {}
  for _, e in ipairs(TABS) do table.insert(all, e) end
  for _, e in ipairs(entries) do table.insert(all, e) end
  table.sort(all)
  return all
end

-- m_clock setter calls recorded since `from`, as {channel, value} pairs.
local function m_clock_values(env, name, from)
  local out = {}
  for i = from or 1, #env.calls do
    local c = env.calls[i]
    if c[1] == "m_clock." .. name then table.insert(out, {c[2], c[3]}) end
  end
  return out
end

-- Turn encoder n by d, one detent at a time as norns delivers them.
local function turn(env, n, d)
  env.ui.enc(n, d)
end

-- K3 press: confirms the pending save (handle_key_three_pressed -> save_confirm.confirm).
local function confirm(env)
  local from = #env.calls + 1
  env.ui.key(3, 1)
  return from
end

-- A channel with a value in every field the six pages show.
local function setup_rich(env)
  local c = env.channel
  c.trig_mask, c.note_mask, c.velocity_mask, c.length_mask = 1, 60, 100, 1/4
  c.chord_one_mask, c.chord_two_mask, c.chord_three_mask, c.chord_four_mask = 3, 5, -7, -14
  for i = 1, 10 do
    c.trig_lock_params[i] = {id = "tl" .. i, param_id = "p" .. i, name = "n" .. i,
      short_descriptor_1 = "L" .. i, short_descriptor_2 = "", off_value = -1}
    env.params["p" .. i] = -1
  end
  c.trig_lock_params[1].id = "beta"
  memory.get_total_event_count = function() return 7 end
  memory.get_event_count = function() return 3 end
  c.clock_mods = {name = "/4", value = 4, type = "clock_division"}
  c.swing_shuffle_type, c.swing = 1, 20
  env.devices = {
    {id = "fixed", name = "Fixed", type = "midi", default_midi_channel = 10, default_midi_device = 1},
    {id = "midi", name = "MIDI", type = "midi"},
    {id = "norns_engine", name = "Engine", type = "norns"}
  }
  env.program_state.devices[SELECTED] = {midi_channel = 5, midi_device = 2, device_map = "midi"}
  device_map.get_available_params_for_channel = function()
    return {{id = "alpha", name = "Alpha"}, {id = "beta", name = "Beta"}, {id = "gamma", name = "Gamma"}}
  end
end

------------------------------------------------------------------------------------------------
-- Page layouts (lines 27-31, 62-108, 195-200, 112). All characterisation: README.md states no
-- screen coordinates. Each entry is "x,y text" for one screen.text after a screen.move.
------------------------------------------------------------------------------------------------

function test_w3c_mask_page_layout()
  isolated(function(env)
    setup_rich(env)
    start(env)
    env.ui.select_mask_page()
    -- characterisation: two rows of four value selectors (label at y, value at y + 8)
    luaunit.assert_equals(frame(env), with_tabs({
      "0,9 Ch. 2 Note Masks",
      "0,18 Trig", "0,26 Y", "25,18 Note", "25,26 C3", "50,18 Vel", "50,26 100", "75,18 Len", "75,26 1/4",
      "0,40 Chd1", "0,48 4th", "25,40 Chd2", "25,48 6th", "50,40 Chd3", "50,48 -oct", "75,40 Chd4", "75,48 --oct"
    }))
  end)
end

function test_w3c_trig_lock_page_layout()
  isolated(function(env)
    setup_rich(env)
    start(env)
    env.ui.select_trig_page()
    -- characterisation: ten dials, five per row at x = 0, 25, 50, 75, 100 and rows y = 18, 40;
    -- each draws its label at y, its value ("X" = off) at y + 7 and its bottom label at y + 14.
    local expected = {"0,9 Ch. 2 Trig Locks"}
    for i = 1, 10 do
      local x, y = (i - 1) % 5 * 25, i <= 5 and 18 or 40
      table.insert(expected, string.format("%d,%d L%d", x, y, i))
      table.insert(expected, string.format("%d,%d X", x, y + 7))
      table.insert(expected, string.format("%d,%d ", x, y + 14))
    end
    luaunit.assert_equals(frame(env), with_tabs(expected))
  end)
end

function test_w3c_trig_lock_dials_show_x_at_off_outside_range_and_midi_default_off()
  isolated(function(env)
    setup_rich(env)
    local c = env.channel
    -- Dial 1: off -1 below its 0..127 range (54 stock Digitakt params); at Off.
    c.trig_lock_params[1] = {id = "beta", param_id = "p1", name = "n1", short_descriptor_1 = "L1",
      short_descriptor_2 = "", type = "midi", off_value = -1, cc_min_value = 0, cc_max_value = 127}
    -- Dial 2: a MIDI device-config param without off_value (README 546: "default -1"); at -1.
    c.trig_lock_params[2] = {id = "tl2", param_id = "p2", name = "n2", short_descriptor_1 = "L2",
      short_descriptor_2 = "", type = "midi", cc_min_value = -1, cc_max_value = 127}
    -- Dial 3: the same MIDI param at 0, a value.
    c.trig_lock_params[3] = {id = "tl3", param_id = "p3", name = "n3", short_descriptor_1 = "L3",
      short_descriptor_2 = "", type = "midi", cc_min_value = -1, cc_max_value = 127}
    env.params.p3 = 0
    -- Dial 4: an n.b. (norns) param without off_value keeps -1 as a value (no X).
    c.trig_lock_params[4] = {id = "tl4", param_id = "p4", name = "n4", short_descriptor_1 = "L4",
      short_descriptor_2 = "", type = "norns", cc_min_value = -1, cc_max_value = 1}
    start(env)
    env.ui.select_trig_page()
    local shown = {}
    for _, e in ipairs(frame(env)) do
      local x, text = e:match("^(%d+),25 (.*)$")
      if x then shown[tonumber(x)] = text end
    end
    -- Human decision S20/S62 (bugs.json dial-off-display, M-PARAM-DIAL-OFF-001): X at Off.
    luaunit.assert_equals(shown[0], "X")
    luaunit.assert_equals(shown[25], "X")
    luaunit.assert_nil(shown[50]) -- a bar, no text
    luaunit.assert_nil(shown[75]) -- characterisation: n.b. params are outside README 546
  end)
end

function test_w3c_trig_lock_param_list_layout()
  isolated(function(env)
    setup_rich(env)
    start(env)
    env.ui.select_trig_page()
    env.ui.key(2, 1) -- K2 on the trig lock page opens the parameter picker for the selected dial
    -- characterisation: the picker lists the channel's params around the dial's current one
    -- (dial 1 holds "beta"): previous at (30, 25), current indented at (35, 35), next at (30, 45).
    luaunit.assert_equals(frame(env), with_tabs({
      "0,9 Ch. 2 Trig Locks", "30,25 Alpha", "35,35 Beta", "30,45 Gamma"
    }))
  end)
end

function test_w3c_memory_page_layout()
  isolated(function(env)
    setup_rich(env)
    start(env)
    env.ui.select_memory_page()
    -- characterisation: the history navigator shows "<current> of <total>" down the left edge
    luaunit.assert_equals(frame(env), with_tabs({"0,9 Ch. 2 Memory", "0,23 3", "0,35 of", "0,49 7"}))
  end)
end

function test_w3c_clock_mods_page_layout_with_swing()
  isolated(function(env)
    setup_rich(env)
    start(env)
    env.ui.select_clock_mods_page()
    -- README.md:683 (per-channel clock division on this page), README.md:685 (swing mode);
    -- characterisation of the positions.
    luaunit.assert_equals(frame(env), with_tabs({
      "0,9 Ch. 2 Clocks", "0,18 Clock Mod", "0,26 /4", "70,18 Swing Type", "70,26 Swing",
      "0,40 Swing", "0,48 20"
    }))
  end)
end

function test_w3c_clock_mods_page_layout_with_shuffle()
  isolated(function(env)
    setup_rich(env)
    local c = env.channel
    c.swing_shuffle_type, c.shuffle_feel, c.shuffle_basis, c.shuffle_amount = 2, 3, 2, 40
    start(env)
    env.ui.select_clock_mods_page()
    -- README.md:685 (shuffle has a feel and a basis); characterisation of positions and labels.
    luaunit.assert_equals(frame(env), with_tabs({
      "0,9 Ch. 2 Clocks", "0,18 Clock Mod", "0,26 /4", "70,18 Swing Type", "70,26 Shuffle",
      "0,40 Feel", "0,48 Heavy", "40,40 Basis", "40,48 7", "70,40 Amount", "70,48 40"
    }))
  end)
end

function test_w3c_device_config_page_layout()
  isolated(function(env)
    setup_rich(env)
    start(env)
    env.ui.select_midi_config_page()
    -- characterisation: three scrolling lists, each showing previous / current (indented by 5,
    -- 10 lower) / next: device at x = 5, MIDI channel at x = 65, MIDI device at x = 90.
    luaunit.assert_equals(frame(env), with_tabs({
      "0,9 Ch. 2 Device Config",
      "5,25 Fixed", "10,35 MIDI", "5,45 Engine",
      "65,25 CC4", "70,35 CC5", "65,45 CC6",
      "90,25 port one", "95,35 port two"
    }))
  end)
end

function test_w3c_note_dashboard_layout_shows_note_names()
  isolated(function(env)
    setup_rich(env)
    start(env)
    env.ui.select_note_dashboard_page()
    env.ui.set_note_dashboard_values({note = 60, velocity = 100, length = 0.25, chords = {62, 64, 65, 67}})
    -- characterisation: the note and all four chord notes are shown by name (lines 195-200),
    -- velocity and length as numbers; the chord row has no fifth column.
    luaunit.assert_equals(frame(env), with_tabs({
      "0,9 Ch. 2 Note Dashboard",
      "0,18 Note", "0,26 C3", "25,18 Vel", "25,26 100", "50,18 Len", "50,26 0.25",
      "0,40 Chd1", "0,48 D3", "25,40 Chd2", "25,48 E3", "50,40 Chd3", "50,48 F3", "75,40 Chd4", "75,48 G3"
    }))
  end)
end

function test_w3c_page_selectors_select_their_page()
  isolated(function(env)
    start(env)
    -- characterisation: the page order behind encoder 1 and each select_* entry point
    local expected = {
      {"select_mask_page", 1, "Note Masks"}, {"select_trig_page", 2, "Trig Locks"},
      {"select_memory_page", 3, "Memory"}, {"select_clock_mods_page", 4, "Clocks"},
      {"select_midi_config_page", 5, "Device Config"}, {"select_note_dashboard_page", 6, "Note Dashboard"}
    }
    for _, e in ipairs(expected) do
      env.ui[e[1]]()
      luaunit.assert_equals(env.ui.get_selected_page(), e[2], e[1])
      local titles = {}
      for _, entry in ipairs(frame(env)) do
        if entry:sub(1, 4) == "0,9 " then table.insert(titles, entry:sub(5)) end
      end
      luaunit.assert_equals(titles, {"Ch. 2 " .. e[3]}, e[1])
    end
  end)
end

------------------------------------------------------------------------------------------------
-- Clock-mods page values (lines 27-31): what K3 hands to m_clock and stores on the channel.
------------------------------------------------------------------------------------------------

-- Open the clock-mods page and move encoder 2 `steps` selectors to the right of the clock-mod
-- list (init selects the clock-mod list).
local function focus_clock_mods_selector(env, steps)
  env.ui.select_clock_mods_page()
  for _ = 1, steps do turn(env, 2, 1) end
end

-- The label the clock-mods page shows at (x, y + 8) for the selector drawn at (x, y).
local function value_label_at(env, xy)
  for _, entry in ipairs(frame(env)) do
    local pos, text = entry:match("^(%S+) (.*)$")
    if pos == xy then return text end
  end
end

function test_w3c_swing_type_options_hand_their_index_to_m_clock()
  isolated(function(env)
    start(env)
    focus_clock_mods_selector(env, 1) -- clock mod -> swing type
    -- "X" (an edit that stays on X, then K3): README.md:687, X restores the global mode, so
    -- m_clock receives the effective (global) type.
    turn(env, 3, -1)
    local from = confirm(env)
    luaunit.assert_equals(env.channel.swing_shuffle_type, 0)
    luaunit.assert_equals(m_clock_values(env, "set_swing_shuffle_type", from), {{SELECTED, 11}})
    luaunit.assert_equals(value_label_at(env, "70,26"), "X")
    -- README.md:685 (two modes); characterisation of their order and indexes: Swing 1, Shuffle 2.
    for index, label in ipairs({"Swing", "Shuffle"}) do
      turn(env, 3, 1)
      from = confirm(env)
      luaunit.assert_equals(env.channel.swing_shuffle_type, index, label)
      luaunit.assert_equals(m_clock_values(env, "set_swing_shuffle_type", from), {{SELECTED, index}}, label)
      luaunit.assert_equals(value_label_at(env, "70,26"), label)
    end
    turn(env, 3, 1) -- characterisation: Shuffle is the last option
    from = confirm(env)
    luaunit.assert_equals(m_clock_values(env, "set_swing_shuffle_type", from), {{SELECTED, 2}})
  end)
end

local function assert_list_options(env, steps, setter, field, labels, effective)
  env.channel.swing_shuffle_type = 2
  start(env)
  focus_clock_mods_selector(env, steps)
  turn(env, 3, -1) -- stays on X
  local from = confirm(env)
  -- README.md:687: X takes the global setting, so m_clock gets the effective value
  luaunit.assert_equals(env.channel[field], 0)
  luaunit.assert_equals(m_clock_values(env, setter, from), {{SELECTED, effective}})
  for index = 1, #labels - 1 do
    turn(env, 3, 1)
    from = confirm(env)
    -- characterisation: option k (after X) is stored and sent as k
    luaunit.assert_equals(env.channel[field], index, labels[index + 1])
    luaunit.assert_equals(m_clock_values(env, setter, from), {{SELECTED, index}}, labels[index + 1])
  end
  turn(env, 3, 1) -- characterisation: no option after the last
  from = confirm(env)
  luaunit.assert_equals(m_clock_values(env, setter, from), {{SELECTED, #labels - 1}})
end

function test_w3c_shuffle_feel_options_hand_their_index_to_m_clock()
  isolated(function(env)
    assert_list_options(env, 2, "set_channel_shuffle_feel", "shuffle_feel",
      {"X", "Drunk", "Smooth", "Heavy", "Clave"}, 13)
    luaunit.assert_equals(value_label_at(env, "0,48"), "Clave") -- characterisation
  end)
end

function test_w3c_shuffle_basis_options_hand_their_index_to_m_clock()
  isolated(function(env)
    assert_list_options(env, 3, "set_channel_shuffle_basis", "shuffle_basis",
      {"X", "9", "7", "5", "6", "8??", "9??"}, 14)
    luaunit.assert_equals(value_label_at(env, "40,48"), "9??") -- characterisation
  end)
end

function test_w3c_swing_range_is_x_then_minus_50_to_50()
  isolated(function(env)
    env.channel.swing_shuffle_type = 1
    start(env)
    focus_clock_mods_selector(env, 2) -- clock mod -> swing type -> swing
    -- README.md:687: an unset channel swing shows "X" and takes the global swing;
    -- characterisation: X is stored as -51, one below the README.md:685 range
    luaunit.assert_equals(value_label_at(env, "0,48"), "X")
    turn(env, 3, -1)
    local from = confirm(env)
    luaunit.assert_equals(env.channel.swing, -51) -- nothing below X
    luaunit.assert_equals(m_clock_values(env, "set_channel_swing", from), {{SELECTED, 12}})
    turn(env, 3, 1)
    from = confirm(env)
    luaunit.assert_equals(env.channel.swing, -50) -- README.md:685: the range starts at -50
    luaunit.assert_equals(m_clock_values(env, "set_channel_swing", from), {{SELECTED, -50}})
    turn(env, 3, 120)
    from = confirm(env)
    luaunit.assert_equals(env.channel.swing, 50) -- README.md:685: ...and ends at 50
    luaunit.assert_equals(m_clock_values(env, "set_channel_swing", from)[1], {SELECTED, 50})
    luaunit.assert_equals(value_label_at(env, "0,48"), "50")
  end)
end

function test_w3c_shuffle_amount_range_is_0_to_100()
  isolated(function(env)
    env.channel.swing_shuffle_type = 2
    start(env)
    focus_clock_mods_selector(env, 4) -- clock mod -> type -> feel -> basis -> amount
    turn(env, 3, -1)
    local from = confirm(env)
    -- characterisation: 0 is the lowest amount and, like X, means "take the global amount"
    luaunit.assert_equals(env.channel.shuffle_amount, 0)
    luaunit.assert_equals(m_clock_values(env, "set_channel_shuffle_amount", from), {{SELECTED, 15}})
    turn(env, 3, 130)
    from = confirm(env)
    luaunit.assert_equals(env.channel.shuffle_amount, 100) -- characterisation: 100 is the highest
    luaunit.assert_equals(m_clock_values(env, "set_channel_shuffle_amount", from)[1], {SELECTED, 100})
    luaunit.assert_equals(value_label_at(env, "70,48"), "100")
  end)
end

------------------------------------------------------------------------------------------------
-- Device config page: the MIDI channel list (lines 90-95).
------------------------------------------------------------------------------------------------

function test_w3c_midi_channel_list_confirms_channels_1_to_16()
  isolated(function(env)
    start(env)
    env.ui.select_midi_config_page()
    turn(env, 2, 1) -- device list -> MIDI channel list (the "midi" device has no fixed channel)
    turn(env, 3, -1) -- stays on the first entry
    confirm(env)
    local function check(k)
      -- characterisation: the list entry labelled CC<k> configures MIDI channel k
      luaunit.assert_equals(env.program_state.devices[SELECTED].midi_channel, k, "CC" .. k)
      local added = calls_named(env, "param_manager.add_device_params")
      local last = added[#added]
      luaunit.assert_equals({last[2], last[3].id, last[4], last[5], last[6]}, {SELECTED, "midi", k, 1, true})
      luaunit.assert_equals(value_label_at(env, "70,35"), "CC" .. k)
    end
    check(1)
    for k = 2, 16 do
      turn(env, 3, 1)
      confirm(env)
      check(k)
    end
    turn(env, 3, 1) -- characterisation: 16 is the last MIDI channel
    confirm(env)
    check(16)
  end)
end

function test_w3c_isolation_restores_globals_after_a_failure()
  local before = {}
  for k, v in pairs(_G) do before[k] = v end
  local ok = pcall(isolated, function(env)
    leaked_by_w3c_test = true
    m_clock = {}
    error("boom")
  end)
  luaunit.assert_false(ok)
  luaunit.assert_nil(leaked_by_w3c_test)
  for k, v in pairs(before) do luaunit.assert_is(_G[k], v, k) end
  for k in pairs(_G) do luaunit.assert_not_nil(before[k], k) end
end

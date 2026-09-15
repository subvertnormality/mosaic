-- Behaviour pins for gaps a Lua mutation campaign found in modules whose own test
-- files did not reach them: param_manager, device_map, json, functions, dial,
-- norns_param_state_handler, project_validation and chord_timing.
--
-- Every replaced global is snapshotted and restored even when a test body fails.
-- Modules with private state are loaded as fresh copies with include(), so the
-- instances other test files use are untouched.
-- Assertions that restate README.md cite its line; every other assertion pins
-- current behaviour and is labelled "-- characterisation".

local W3B_JSON_MODULE = "mosaic/lib/helpers/json"

-- Runs body with the named globals snapshotted; restores them even on failure.
local function w3b_isolated(names, body)
  local saved = {}
  for _, name in ipairs(names) do saved[name] = {rawget(_G, name)} end
  local ok, err = pcall(body)
  for _, name in ipairs(names) do rawset(_G, name, saved[name][1]) end
  if not ok then error(err, 0) end
end

-------------------------------------------------------------------------------
-- param_manager
-------------------------------------------------------------------------------

local function w3b_slot(channel, i)
  return "midi_device_params_channel_" .. channel .. "_" .. i
end

-- A paramset that, like norns' ParamSet, raises for an id it does not hold.
local function w3b_strict_params()
  local P = {lookup = {}, store = {}, hidden = {}}
  local function new_param(id, name, spec)
    local p = {id = id, name = name, controlspec = spec, sets = {}}
    function p:set(v, silent)
      self.sets[#self.sets + 1] = {value = v, silent = silent}
      self.value = v
    end
    function p:get() return self.value end
    return p
  end
  function P:add_group(id, name)
    self.lookup[id] = true
    self.store[id] = {id = id, name = name}
  end
  function P:add_control(id, name, spec)
    self.lookup[id] = true
    self.store[id] = new_param(id, name, spec)
  end
  function P:lookup_param(id)
    if not self.lookup[id] then error("invalid paramset index: " .. tostring(id)) end
    return self.store[id]
  end
  function P:set_action(id, f) self:lookup_param(id).action = f end
  function P:hide(id) self:lookup_param(id); self.hidden[id] = true end
  function P:show(id) self:lookup_param(id); self.hidden[id] = false end
  return P
end

local W3B_PM_GLOBALS = {
  "params", "controlspec", "device_map", "_menu", "channel_edit_page_ui",
  "autosave_reset", "m_midi", "program"
}

-- A fresh param_manager over a strict paramset, with a stock list holding only "none".
local function w3b_with_param_manager(body)
  w3b_isolated(W3B_PM_GLOBALS, function()
    local env = {midi = {}, refreshes = 0, autosaves = 0}
    env.params = w3b_strict_params()
    params = env.params
    controlspec = {
      new = function(minval, maxval, warp, step, default, units, quantum)
        return {minval = minval, maxval = maxval, warp = warp, step = step,
                default = default, units = units, quantum = quantum}
      end
    }
    device_map = {get_stock_params = function() return {{id = "none"}} end}
    _menu = {rebuild_params = function() end}
    channel_edit_page_ui = {refresh_trig_lock_values = function() env.refreshes = env.refreshes + 1 end}
    autosave_reset = function() env.autosaves = env.autosaves + 1 end
    m_midi = {
      cc = function(...) env.midi[#env.midi + 1] = {"cc", table.pack(...)} end,
      nrpn = function(...) env.midi[#env.midi + 1] = {"nrpn", table.pack(...)} end
    }
    program = {get = function() return {} end}
    local pm = include("mosaic/lib/devices/param_manager")
    pm.init()
    for _, p in pairs(env.params.store) do p.sets = {} end
    body(pm, env)
  end)
end

-- A CC device parameter with a range but no configured off_value.
local W3B_NO_OFF_DEVICE = {
  type = "midi", name = "fixture", id = "fixture",
  params = {{id = "level", name = "Level", cc_msb = 7, cc_min_value = 0, cc_max_value = 100}}
}

function test_w3b_param_manager_device_param_without_off_value_uses_minus_one_as_off()
  w3b_with_param_manager(function(pm, env)
    pm.add_device_params(3, W3B_NO_OFF_DEVICE, 9, 2, true)
    -- the stock "none" takes slot 1, so the first device param is slot 2
    local p = env.params.store[w3b_slot(3, 2)]
    luaunit.assert_equals(p.name, "Level") -- characterisation
    -- README.md:546 the Off value defaults to -1, and init loads it silently
    luaunit.assert_equals(p.sets, {{value = -1, silent = true}})
    p.value = -1
    luaunit.assert_equals(p.formatter(p), "X") -- characterisation: Off is shown as X
    p.value = 5
    luaunit.assert_equals(p.formatter(p), 5) -- characterisation
    local action = env.params.store[w3b_slot(3, 2)].action
    action(-1)
    luaunit.assert_equals(env.midi, {}) -- README.md:546 the default Off value (-1) sends nothing
    luaunit.assert_equals({env.autosaves, env.refreshes}, {1, 0}) -- characterisation
    action(64)
    luaunit.assert_equals(#env.midi, 1) -- README.md:546 any other value is sent
    luaunit.assert_equals(env.midi[1][1], "cc")
    luaunit.assert_equals(env.midi[1][2], {7, nil, 64, 9, 2, n = 5}) -- characterisation: msb, lsb, value, channel, device
    luaunit.assert_equals({env.autosaves, env.refreshes}, {2, 1}) -- characterisation
  end)
end

function test_w3b_param_manager_add_device_params_touches_only_the_180_existing_slots()
  w3b_with_param_manager(function(pm, env)
    -- the strict paramset raises for an id it does not hold, as norns' ParamSet does
    pm.add_device_params(5, W3B_NO_OFF_DEVICE, 1, 1, true)
    local P = env.params
    luaunit.assert_true(P.hidden[w3b_slot(5, 1)]) -- characterisation: the stock "none" slot
    luaunit.assert_false(P.hidden[w3b_slot(5, 2)]) -- characterisation
    for i = 3, 180 do
      luaunit.assert_true(P.hidden[w3b_slot(5, i)], "slot " .. i) -- characterisation: unused slots hidden
    end
    local before = {#env.midi, env.autosaves, env.refreshes}
    P.store[w3b_slot(5, 180)].action(10)
    luaunit.assert_equals({#env.midi, env.autosaves, env.refreshes}, before) -- characterisation: disarmed
  end)
end

-------------------------------------------------------------------------------
-- device_map
-------------------------------------------------------------------------------

-- A fresh device_map reading config/<name> files from a temporary data directory.
local function w3b_with_device_map(files, players, body)
  w3b_isolated({"norns", "note_players", "params", "program", "print"}, function()
    local saved_json = package.loaded[W3B_JSON_MODULE]
    local root = os.tmpname()
    os.remove(root)
    local ok, err = pcall(function()
      assert(os.execute("mkdir -p '" .. root .. "/config'"))
      for name, content in pairs(files) do
        local f = assert(io.open(root .. "/config/" .. name, "w"))
        f:write(content)
        f:close()
      end
      norns = {state = {data = root .. "/"}}
      note_players = players
      print = function() end
      params = {lookup = {}, show = function() end}
      package.loaded[W3B_JSON_MODULE] = include(W3B_JSON_MODULE)
      body(include("mosaic/lib/devices/device_map"))
    end)
    os.execute("rm -rf '" .. root .. "'")
    package.loaded[W3B_JSON_MODULE] = saved_json
    if not ok then error(err, 0) end
  end)
end

function test_w3b_device_map_merged_params_keep_the_first_of_duplicate_device_ids()
  local config = '[{"id":"dup","name":"Dup","type":"midi","params":[' ..
    '{"id":"a","name":"First"},{"id":"a","name":"Second"},{"id":"b","name":"Bee"}]}]'
  w3b_with_device_map({["dup.json"] = config}, nil, function(dm)
    dm.init()
    local merged = dm.get_params("dup")
    local stock_count = #dm.get_stock_params()
    luaunit.assert_equals(#merged, stock_count + 2) -- characterisation: the repeated id is dropped
    luaunit.assert_equals(merged[stock_count + 1].name, "First") -- characterisation
    luaunit.assert_equals(merged[stock_count + 1].index, stock_count + 1) -- characterisation
    luaunit.assert_equals(merged[stock_count + 2].id, "b") -- characterisation
    luaunit.assert_equals(merged[stock_count + 2].index, stock_count + 2) -- characterisation
  end)
end

function test_w3b_device_map_ignores_a_norns_player_whose_params_are_not_a_table()
  local player = {describe = function() return {params = "cutoff", supports_slew = false} end}
  w3b_with_device_map({}, {["jf n 1"] = player}, function(dm)
    dm.init()
    local device = dm.get_device("jf n 1")
    luaunit.assert_equals(device.type, "norns") -- characterisation
    luaunit.assert_equals(device.params, {}) -- characterisation: no device params, no error
  end)
end

function test_w3b_device_map_validate_devices_resets_an_unknown_map_on_channel_1()
  w3b_with_device_map({}, nil, function(dm)
    dm.init()
    local prog = {devices = {}}
    for i = 1, 16 do prog.devices[i] = {device_map = "none", midi_channel = 3, midi_device = 2} end
    prog.devices[1] = {device_map = "gone", midi_channel = 5, midi_device = 4}
    program = {get = function() return prog end}
    dm.validate_devices()
    luaunit.assert_equals(prog.devices[1], {midi_channel = 1, midi_device = 1, device_map = "none"}) -- characterisation
    luaunit.assert_equals(prog.devices[2], {device_map = "none", midi_channel = 3, midi_device = 2}) -- characterisation
  end)
end

-------------------------------------------------------------------------------
-- json
-------------------------------------------------------------------------------

local w3b_json = include(W3B_JSON_MODULE)

function test_w3b_json_decode_unicode_escapes_at_each_utf8_length_boundary()
  local cases = {
    {"\\u007f", "\127"},                     -- U+007F, last 1-byte
    {"\\u0080", "\194\128"},                 -- U+0080, first 2-byte
    {"\\u0400", "\208\128"},                 -- U+0400
    {"\\u07ff", "\223\191"},                 -- U+07FF, last 2-byte
    {"\\u0800", "\224\160\128"},             -- U+0800, first 3-byte
    {"\\u1000", "\225\128\128"},             -- U+1000
    {"\\uffff", "\239\191\191"},             -- U+FFFF, last 3-byte
    {"\\ud800\\udc00", "\240\144\128\128"},  -- U+10000, first 4-byte
    {"\\ud8c0\\udc00", "\241\128\128\128"},  -- U+40000
    {"\\udbc0\\udc00", "\244\128\128\128"},  -- U+100000
    {"\\udbff\\udfff", "\244\143\191\191"},  -- U+10FFFF, last codepoint
  }
  for _, c in ipairs(cases) do
    luaunit.assert_equals(w3b_json.decode('"' .. c[1] .. '"'), c[2], c[1]) -- characterisation: standard UTF-8
  end
end

function test_w3b_json_decode_empty_object_followed_by_more_members()
  luaunit.assert_equals(w3b_json.decode('[{},1]'), {{}, 1}) -- characterisation
  luaunit.assert_equals(w3b_json.decode('{"a":{},"b":2}'), {a = {}, b = 2}) -- characterisation
end

-------------------------------------------------------------------------------
-- functions
-------------------------------------------------------------------------------

function test_w3b_functions_id_appears_in_table_checks_the_first_element()
  local t = {{id = "a"}, {id = "b"}}
  luaunit.assert_true(fn.id_appears_in_table(t, "a")) -- characterisation
  luaunit.assert_true(fn.id_appears_in_table(t, "b")) -- characterisation
  luaunit.assert_false(fn.id_appears_in_table(t, "c")) -- characterisation
end

-------------------------------------------------------------------------------
-- dial
-------------------------------------------------------------------------------

local w3b_dial = include("mosaic/lib/ui_components/dial")

-- The rect calls a dial draw makes, with screen replaced by a recorder.
local function w3b_dial_rects(d)
  local rects = {}
  w3b_isolated({"screen"}, function()
    local noop = function() end
    screen = {level = noop, move = noop, text = noop, text_trim = noop, fill = noop,
              rect = function(...) rects[#rects + 1] = {...} end}
    d:draw()
  end)
  return rects
end

function test_w3b_dial_without_off_value_draws_an_empty_bar_at_the_top_of_a_negative_range()
  -- channel_edit_page_ui_refreshers.lua passes a param's off_value, which is nil for params
  -- that declare none; draw() then treats 0 as the centre of the bar.
  local d = w3b_dial:new(10, 20, "Param 1", "param_1", "top", "bottom")
  d:set_min_value(-5)
  d:set_max_value(0)
  d:set_off_value(nil)
  d.value = 0
  luaunit.assert_equals(w3b_dial_rects(d), {}) -- characterisation: no fill at the centre
  d.value = -5
  local w = 19 / 20
  local centre = 10 + 19 / 2
  local expected = {}
  for i = 1, 10 do expected[i] = {centre - i * w, 23, w, 4} end
  luaunit.assert_equals(w3b_dial_rects(d), expected) -- characterisation: min fills the left half
end

-------------------------------------------------------------------------------
-- norns_param_state_handler
-------------------------------------------------------------------------------

function test_w3b_norns_param_state_flush_restores_every_channel_and_slot_then_clears()
  w3b_isolated({"params"}, function()
    local sets = {}
    params = {set = function(_, id, value) sets[#sets + 1] = {id, value} end}
    local handler = include("mosaic/lib/devices/norns_param_state_handler")
    handler.set_original_param_state(1, 1, 10, "first")
    handler.set_original_param_state(2, 5, 30, "middle")
    handler.set_original_param_state(16, 10, 20, "last")
    handler.flush_norns_original_param_trig_lock_store()
    luaunit.assert_equals(sets, {{"first", 10}, {"middle", 30}, {"last", 20}}) -- characterisation
    luaunit.assert_equals(handler.get_original_param_state(1, 1), {}) -- characterisation
    sets = {}
    handler.flush_norns_original_param_trig_lock_store()
    luaunit.assert_equals(sets, {}) -- characterisation: flushed state is not restored twice
  end)
end

function test_w3b_norns_param_state_get_for_a_channel_without_state_is_nil()
  local handler = include("mosaic/lib/devices/norns_param_state_handler")
  luaunit.assert_nil(handler.get_original_param_state(17, 1)) -- characterisation
  luaunit.assert_nil(handler.get_original_param_state(0, 1)) -- characterisation
  luaunit.assert_equals(handler.get_original_param_state(3, 4), {}) -- characterisation
end

-------------------------------------------------------------------------------
-- project_validation
-------------------------------------------------------------------------------

function test_w3b_project_validation_accepts_an_envelope_without_a_name()
  local validation = include("mosaic/lib/project_validation")
  local channels = {}
  for i = 1, 17 do channels[i] = {start_trig = {1, 4}, end_trig = {16, 7}} end
  local data = {song_patterns = {[1] = {global_pattern_length = 64, channels = channels}}}
  luaunit.assert_true(validation.check({nil, data})) -- characterisation: the name is optional
  luaunit.assert_true(validation.check({"named", data})) -- characterisation
  local valid, reason = validation.check({7, data})
  luaunit.assert_nil(valid) -- characterisation
  luaunit.assert_equals(reason, "Invalid project envelope") -- characterisation
end

-------------------------------------------------------------------------------
-- chord_timing
-------------------------------------------------------------------------------

function test_w3b_chord_timing_division_zero_ignores_spread()
  local timing = include("mosaic/lib/clock/chord_timing")
  -- README.md:828 spacing modifiers act only when Strum or Arpeggio is enabled;
  -- characterisation: a zero division is the disabled strum
  luaunit.assert_equals(timing.delay(0, 1, 0, 2), 0)
  luaunit.assert_equals(timing.delay(0, 0.5, 1, 3), 0)
  luaunit.assert_equals(timing.delay(1, 1, 0, 2), 4) -- README.md:813 two gaps of d + s
end

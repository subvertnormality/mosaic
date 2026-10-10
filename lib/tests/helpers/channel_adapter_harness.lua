-- Shared harness for the Channel-page adapter tests (UI02: masks, parameters,
-- device, clock, history, assignment). Modelled on
-- lib/tests/lib/channel_edit_page_ui_mutation_killers_tests.lua: every scenario
-- loads a FRESH channel_edit_page_ui inside `isolated`, with recording stubs for
-- the collaborators (program, params, memory, m_clock, device_map, recorder,
-- pattern, ...). save_confirm, the page/selector components, the handlers,
-- refreshers and owners stay real. `isolated` restores _G afterwards.
--
-- Parity tests run one scenario twice on fresh state: once through the old
-- ui.enc / ui.key path and once through the adapter, then compare `observe`.

local harness = {}

local UI_MODULE = "mosaic/lib/pages/channel_edit_page/channel_edit_page_ui"
local divisions = include("mosaic/lib/clock/divisions")

harness.SELECTED = 2

local function recorder_of(env, name, result)
  return function(...)
    local args = table.pack(...)
    local entry = {name}
    for i = 1, args.n do
      local v = args[i]
      if type(v) == "table" and v.number then v = "channel" .. v.number end
      if type(v) == "function" then v = "<function>" end
      entry[#entry + 1] = v
    end
    table.insert(env.calls, entry)
    return result
  end
end
harness.recorder_of = recorder_of

local function new_channel(number)
  local c = {
    number = number,
    trig_lock_params = {},
    clock_mods = {name = "/1", value = 1, type = "clock_division"},
    step_note_masks = {}, step_velocity_masks = {}, step_length_masks = {},
    step_trig_masks = {}, step_chord_masks = {}, step_trig_locks = {}
  }
  for i = 1, 10 do c.trig_lock_params[i] = {} end
  return c
end

local function new_params(env)
  local store = {}
  local p = {lookup = {}}
  function p.get(_, id)
    if type(id) == "number" then return store[id].value end
    return env.params[id]
  end
  function p.lookup_param(_, id) return env.param_objects[id] end
  function p.t() return 1 end
  function p.add(_, args)
    store[#store + 1] = {id = args.id, value = 0}
    p.lookup[args.id] = #store
  end
  function p.hide() end
  function p.set_action() end
  function p.set(_, index, value) store[index].value = value end
  function p.delta(_, index, d) store[index].value = store[index].value + d end
  return p
end

local function param_object(env, id)
  return {
    delta = function(_, d)
      env.params[id] = env.params[id] + d
      table.insert(env.calls, {"param.delta", id, d})
    end,
    get = function() return env.params[id] end,
    get_raw = function() return env.params[id] end,
    set_raw = function(_, v) env.params[id] = v end
  }
end

local function install_stubs(env)
  env.calls = {}
  env.pressed = {}
  env.params = {
    global_swing_shuffle_type = 1, global_swing = 0, global_shuffle_feel = 0,
    global_shuffle_basis = 0, global_shuffle_amount = 0, record = 1, wrap_param_slides = 1
  }
  env.param_objects = {}
  env.channel = new_channel(harness.SELECTED)
  env.devices = {
    {id = "midi", name = "MIDI", type = "midi"},
    {id = "fixed", name = "Fixed", type = "midi", default_midi_channel = 10, default_midi_device = 1},
    {id = "norns_engine", name = "Engine", type = "norns"}
  }
  env.program_state = {
    selected_channel = harness.SELECTED,
    selected_song_pattern = 1,
    devices = {[harness.SELECTED] = {midi_channel = 1, midi_device = 1, device_map = "midi"}}
  }
  env.playing = false
  env.memory = {current = 0, total = 0}
  env.available_params = {{id = "none", name = "None"}, {id = "cc10", name = "CC10"}, {id = "cc11", name = "CC11"}}

  screen = setmetatable({}, {__index = function() return function() end end})
  m_grid = {get_pressed_keys = function() return env.pressed end}
  params = new_params(env)
  clock = {run = function() return 1 end, cancel = function() end, sleep = function() end}
  memory = {
    get_total_event_count = function() return env.memory.total end,
    get_event_count = function() return env.memory.current end,
    get_recent_events = function() return env.memory.events or {} end,
    undo = function(c)
      table.insert(env.calls, {"memory.undo", c})
      env.memory.current = math.max(0, env.memory.current - 1)
    end,
    redo = function(c)
      table.insert(env.calls, {"memory.redo", c})
      env.memory.current = math.min(env.memory.total, env.memory.current + 1)
    end
  }
  local function setter(field)
    return function(channel, value)
      table.insert(env.calls, {"program.set_" .. field, channel.number, value})
      channel[field] = value
    end
  end
  program = {
    get = function() return env.program_state end,
    get_selected_channel = function() return env.channel end,
    get_channel = function(_, c) return c == harness.SELECTED and env.channel or new_channel(c) end,
    get_selected_song_pattern = function() return 1 end,
    get_song_pattern = function(n) return {song_pattern = n} end,
    get_channel_param_slide = function(_, i) return env.channel_slides and env.channel_slides[i] or false end,
    get_step_param_slide = function() return false end,
    get_current_step_for_channel = function() return 1 end,
    get_step_param_trig_lock = function(_, s, i) return env.step_locks and env.step_locks[s .. ":" .. i] end,
    get_trig_lock_calculator_id = function() return 0 end,
    get_effective_swing_shuffle_type = recorder_of(env, "program.get_effective_swing_shuffle_type", 11),
    get_effective_swing = recorder_of(env, "program.get_effective_swing", 12),
    get_effective_shuffle_feel = recorder_of(env, "program.get_effective_shuffle_feel", 13),
    get_effective_shuffle_basis = recorder_of(env, "program.get_effective_shuffle_basis", 14),
    get_effective_shuffle_amount = recorder_of(env, "program.get_effective_shuffle_amount", 15),
    increment_trig_lock_calculator_id = recorder_of(env, "program.increment_trig_lock_calculator_id"),
    clear_device_trig_locks_for_channel = recorder_of(env, "program.clear_device_trig_locks_for_channel"),
    set_trig_mask = setter("trig_mask"),
    set_note_mask = setter("note_mask"),
    set_velocity_mask = setter("velocity_mask"),
    set_length_mask = setter("length_mask"),
    set_chord_one_mask = setter("chord_one_mask"),
    set_chord_two_mask = setter("chord_two_mask"),
    set_chord_three_mask = setter("chord_three_mask"),
    set_chord_four_mask = setter("chord_four_mask")
  }
  m_clock = {
    get_clock_divisions = function() return divisions.clock_divisions end,
    calculate_divisor = function(mods) return mods.name end,
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
    get_available_params_for_channel = function() return env.available_params end
  }
  draw = {register_ui = function(_, name, func) env.draws = env.draws or {}; env.draws[name] = func end}
  tooltip = {show = function() end, error = recorder_of(env, "tooltip.error")}
  recorder = {
    clear_trig_lock_dirty = function() end,
    set_trig_lock_dirty = recorder_of(env, "recorder.set_trig_lock_dirty"),
    add_note_mask_event_portion = function(c, s, event)
      table.insert(env.calls, {"recorder.add_note_mask_event_portion", c, s, event})
    end,
    add_trig_lock_event_portion = function(c, s, event)
      table.insert(env.calls, {"recorder.add_trig_lock_event_portion", c, s, event})
    end
  }
  pattern = {update_working_pattern = recorder_of(env, "pattern.update_working_pattern")}
  step = {queue_for_pattern_change = recorder_of(env, "step.queue_for_pattern_change")}
  crow = {ii = {pullup = function() end, jf = {mode = function() end}}}
  norns_param_state_handler = {
    get_original_param_state = function() return {} end,
    clear_original_param_state = recorder_of(env, "norns_param_state_handler.clear_original_param_state")
  }
  is_key1_down = false
  m_midi = {
    get_midi_outs = function() return {{name = "port one", value = 1}, {name = "port two", value = 2}} end,
    midi_devices_connected = function() return env.midi_connected ~= false end
  }
end

local STUB_MODULES = {
  ["mosaic/lib/m_midi"] = function() return m_midi end,
  ["mosaic/lib/devices/param_manager"] = function(env)
    return {
      add_device_params = recorder_of(env, "param_manager.add_device_params"),
      update_default_params = recorder_of(env, "param_manager.update_default_params"),
      update_param = function(i, channel, item)
        table.insert(env.calls, {"param_manager.update_param", i, channel.number, item and item.id})
        channel.trig_lock_params[i] = {id = item and item.id}
      end
    }
  end
}

function harness.isolated(body)
  local before = {}
  for k, v in pairs(_G) do before[k] = v end
  local env = {}
  local ok, err = pcall(function()
    install_stubs(env)
    local real_include = before.include
    include = function(file)
      if STUB_MODULES[file] then return STUB_MODULES[file](env) end
      if file:sub(1, 4) == "lib/" then return real_include("mosaic/" .. file) end
      return real_include(file)
    end
    save_confirm = include("mosaic/lib/ui_components/save_confirm")
    env.ui = include(UI_MODULE)
    channel_edit_page_ui = env.ui
    env.ui_adapters = include("mosaic/lib/ui_adapters")
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

-- lib/ui.lua order: register the draw, then init.
function harness.start(env)
  env.ui.register_ui_draws()
  env.ui.init()
end

function harness.adapter(env, provider)
  return include("mosaic/lib/ui_adapters/" .. provider)(env.ui_adapters, env.ui.adapter_owners())
end

-- A captured target for `route` from the current owner state.
function harness.target(env, route, extra)
  local held = {}
  for _, key in ipairs(env.pressed) do
    if key[2] > 3 and key[2] < 8 then held[#held + 1] = fn.calc_grid_count(key[1], key[2]) end
  end
  local target = {source_route = route, screen = route, channel = env.program_state.selected_channel,
    song_slot = env.program_state.selected_song_pattern, held = held}
  for k, v in pairs(extra or {}) do target[k] = v end
  return target
end

function harness.ids(outcome)
  local ids = {}
  for _, d in ipairs(outcome.descriptors or {}) do ids[#ids + 1] = d.id end
  return ids
end

function harness.by_id(outcome)
  local map = {}
  for _, d in ipairs(outcome.descriptors or {}) do map[d.id] = d end
  return map
end

-- Visible descriptor id -> formatted value.
function harness.values(outcome)
  local map = {}
  for _, d in ipairs(outcome.descriptors or {}) do
    if d.visible then map[d.id] = d.value end
  end
  return map
end

-- The observable result of a scenario: recorded collaborator calls, the
-- channel's mask/clock fields, trig lock params, device routing and params.
function harness.observe(env)
  local c = env.channel
  local fields = {}
  for _, key in ipairs({"trig_mask", "note_mask", "velocity_mask", "length_mask", "chord_one_mask",
    "chord_two_mask", "chord_three_mask", "chord_four_mask", "swing_shuffle_type", "swing", "shuffle_feel",
    "shuffle_basis", "shuffle_amount"}) do
    fields[key] = c[key]
  end
  fields.clock_mods = c.clock_mods and c.clock_mods.name
  local assigned = {}
  for i = 1, 10 do assigned[i] = tostring(c.trig_lock_params[i].id) end
  return {calls = env.calls, fields = fields, assigned = assigned,
    devices = env.program_state.devices[harness.SELECTED], params = env.params}
end

-- A channel with a value in every field the pages show.
function harness.setup_rich(env)
  local c = env.channel
  c.trig_mask, c.note_mask, c.velocity_mask, c.length_mask = 1, 60, 100, 1 / 4
  c.chord_one_mask, c.chord_two_mask, c.chord_three_mask, c.chord_four_mask = 3, 5, -7, -14
  for i = 1, 10 do
    c.trig_lock_params[i] = {id = "tl" .. i, param_id = "p" .. i, name = "Name " .. i, type = "norns",
      short_descriptor_1 = "L" .. i, short_descriptor_2 = "", off_value = -1, cc_min_value = 0, cc_max_value = 127}
    env.params["p" .. i] = 10 * i
    env.param_objects["p" .. i] = param_object(env, "p" .. i)
  end
  c.trig_lock_params[5].id = "chord_strum"
  c.trig_lock_params[6].id = "chord_spread"
  c.clock_mods = {name = "/4", value = 4, type = "clock_division"}
  c.swing_shuffle_type, c.swing = 1, 20
end

return harness

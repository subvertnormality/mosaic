-- Boots the whole live norns UI for lib/tests/lib/ui_live_tests.lua: the real
-- program model, lib/ui.lua (every page UI, tooltip, save_confirm and
-- ui_live), each page's init and ui_live.install(). Only the hardware and the
-- sequencing collaborators the pages call outward (screen, metro, clock,
-- m_clock, device_map, m_midi, pattern, step, param_manager) are
-- recording stubs. `isolated` snapshots _G and restores it afterwards, even
-- when the body fails; include() is dofile, so every scenario starts fresh.

local ui_live_env = {}

local divisions = include("mosaic/lib/clock/divisions")

local function record(env, name, result)
  return function(...)
    env.calls[#env.calls + 1] = {name, ...}
    return result
  end
end

-- A small ParamSet stand-in: unknown ids read 0 (norns returns the default).
local function stub_params(env)
  local values = {
    clock_tempo = 120, global_swing_shuffle_type = 1, global_swing = 0, global_shuffle_feel = 1,
    global_shuffle_basis = 1, global_shuffle_amount = 0, record = 1, wrap_param_slides = 1,
    song_mode = 2, tresillo_amount = 3, all_scales_lock_to_pentatonic = 1
  }
  env.param_values = values
  env.param_objects = {}
  local store = {}
  local p = {lookup = {}, params = {}}
  function p:get(id)
    if type(id) == "number" then return store[id] and store[id].value or 0 end
    local v = values[id]
    if v == nil then return 0 end
    return v
  end
  function p:set(id, value)
    if type(id) == "number" then store[id].value = value; return end
    if env.param_objects[id] then p.lookup[id] = p.lookup[id] or id end
    values[id] = value
    env.calls[#env.calls + 1] = {"params.set", id, value}
  end
  function p:string(id) return tostring(values[id]) end
  -- Parameter objects a scenario registers in env.param_objects (id -> table).
  function p:lookup_param(id) return env.param_objects[id] end
  function p:t() return 1 end
  function p:add(args)
    store[#store + 1] = {id = args and args.id, value = 0}
    if args and args.id then p.lookup[args.id] = #store end
  end
  function p:hide() end
  function p:show() end
  function p:set_action() end
  function p:delta(id, d)
    if type(id) == "number" then store[id].value = store[id].value + d else values[id] = (values[id] or 0) + d end
  end
  return p
end

-- The shape device_descriptors.load_devices gives: None first.
local DEVICES = {
  {id = "none", name = "None", type = "none"},
  {id = "midi", name = "MIDI", type = "midi"},
  {id = "fixed", name = "Fixed", type = "midi", default_midi_channel = 10, default_midi_device = 1},
}

local function install_stubs(env, before)
  env.calls = {}
  env.pressed = {}
  env.playing = false
  env.algorithm = 1

  screen = setmetatable({}, {__index = function() return function() end end})
  metro = {init = function() return {start = function() end, stop = function() end, id = 1} end, free = function() end}
  clock = {run = function() return 1 end, cancel = function() end, sleep = function() end, get_beats = function() return 0 end}
  draw = {register_ui = function() end, register_grid = function() end}
  m_grid = {get_pressed_keys = function() return env.pressed end}
  params = stub_params(env)
  crow = {ii = {pullup = function() end, jf = {mode = function() end}}}
  is_key1_down = false

  m_clock = {
    get_clock_divisions = function() return divisions.clock_divisions end,
    calculate_divisor = function(mods) return mods and mods.value or 1 end,
    is_playing = function() return env.playing end,
    set_swing_shuffle_type = record(env, "m_clock.set_swing_shuffle_type"),
    set_channel_swing = record(env, "m_clock.set_channel_swing"),
    set_channel_shuffle_feel = record(env, "m_clock.set_channel_shuffle_feel"),
    set_channel_shuffle_basis = record(env, "m_clock.set_channel_shuffle_basis"),
    set_channel_shuffle_amount = record(env, "m_clock.set_channel_shuffle_amount"),
    set_channel_division = record(env, "m_clock.set_channel_division"),
    channel_is_sliding = function() return false end,
  }
  device_map = {
    get_devices = function() return DEVICES end,
    get_device = function(id) return fn.get_by_id(DEVICES, id) end,
    get_params = function() return {} end,
    get_available_devices_for_channel = function() return DEVICES end,
    get_available_params_for_channel = function()
      return {{id = "none", name = "None"}, {id = "cc10", name = "CC10"}, {id = "cc11", name = "CC11"}}
    end,
  }
  m_midi = {
    get_midi_outs = function() return {{name = "port one", value = 1}, {name = "port two", value = 2}} end,
    midi_devices_connected = function() return true end,
  }
  pattern = setmetatable({}, {__index = function(_, key) return record(env, "pattern." .. key) end})
  step = setmetatable({queue_for_pattern_change = function(f) env.queued = env.queued or {}; env.queued[#env.queued + 1] = f end,
    -- No queued jump: the next slot is the current one (A03 reads it).
    calculate_next_selected_song_pattern = function() return program.get().selected_song_pattern end},
    {__index = function(_, key) return record(env, "step." .. key) end})
  norns_param_state_handler = {
    get_original_param_state = function() return {} end,
    clear_original_param_state = record(env, "norns_param_state_handler.clear_original_param_state"),
  }
  trigger_edit_page = {get_algorithm = function() return env.algorithm end}

  local real_include = before.include
  -- The real recorder: held-step edits stage their step locks here.
  recorder = real_include("mosaic/lib/recorder")
  local STUBS = {
    ["mosaic/lib/m_midi"] = function() return m_midi end,
    ["mosaic/lib/devices/param_manager"] = function()
      return {
        add_device_params = record(env, "param_manager.add_device_params"),
        update_default_params = record(env, "param_manager.update_default_params"),
        update_param = function(i, channel, item)
          env.calls[#env.calls + 1] = {"param_manager.update_param", i, channel.number, item and item.id}
          channel.trig_lock_params[i] = {id = item and item.id}
        end,
      }
    end,
  }
  include = function(file)
    if STUBS[file] then return STUBS[file]() end
    if file:sub(1, 4) == "lib/" then return real_include("mosaic/" .. file) end
    return real_include(file)
  end
end

-- Runs body(env) with a booted live UI. env.ui is lib/ui.lua; the page UIs,
-- tooltip, save_confirm and ui_live are the globals lib/ui.lua installs.
function ui_live_env.isolated(body, options)
  options = options or {}
  local before = {}
  for k, v in pairs(_G) do before[k] = v end
  local dirty_screen, dirty_grid = fn.dirty_screen, fn.dirty_grid
  local env = {}
  local ok, err = pcall(function()
    fn.dirty_screen = function() end
    fn.dirty_grid = function() end
    program.init()
    -- Another suite's m_clock.init may have left its lock edit listener on the
    -- shared program module; with none, a lock edit behaves as it always has.
    program.set_lock_edit_listener(nil)
    install_stubs(env, before)
    program.set_selected_page(options.page or pages.pages.channel_edit_page)
    env.ui = include("mosaic/lib/ui")
    ui = env.ui
    env.ui.init()
    body(env)
  end)
  fn.dirty_screen, fn.dirty_grid = dirty_screen, dirty_grid
  local keys = {}
  for k in pairs(_G) do keys[#keys + 1] = k end
  for _, k in ipairs(keys) do
    if before[k] == nil then _G[k] = nil end
  end
  for k, v in pairs(before) do
    if rawget(_G, k) ~= v then _G[k] = v end
  end
  if not ok then error(err, 0) end
end

-- Holds grid steps (1..64) the way m_grid reports pressed keys: {x, y} with
-- rows 4..7 as the step rows.
function ui_live_env.press_steps(env, steps)
  local keys = {}
  for _, s in ipairs(steps) do
    keys[#keys + 1] = {(s - 1) % 16 + 1, 4 + (s - 1) // 16}
  end
  env.pressed = keys
end

function ui_live_env.screen() return ui_live.state().screen end

function ui_live_env.channel_page()
  return channel_edit_page_ui.adapter_owners().channel_pages:get_selected_page()
end

return ui_live_env

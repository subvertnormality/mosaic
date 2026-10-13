-- Test harness for the Scale, Song and Trig page adapters (UI02): loads a
-- fresh copy of the real page UI module over recording stubs, so the old
-- ui.enc/ui.key path and the adapter path can each run on fresh state and be
-- compared. Every global the harness installs is restored afterwards.

local page_env = {}

local PAGES = {
  scale = {module = "mosaic/lib/pages/scale_edit_page/scale_edit_page_ui", global = "scale_edit_page_ui"},
  song = {module = "mosaic/lib/pages/song_edit_page/song_edit_page_ui", global = "song_edit_page_ui"},
  trig = {module = "mosaic/lib/pages/trigger_edit_page/trigger_edit_page_ui", global = "trigger_edit_page_ui"}
}

local OPTIONS = {
  all_scales_lock_to_pentatonic = {"Off", "On"},
  song_mode = {"Off", "On"},
  tresillo_amount = {8, 16, 24, 32, 40, 48, 56, 64}
}

local function stub_params(env)
  local values = {
    clock_tempo = 120, song_mode = 2, global_swing_shuffle_type = 1, global_swing = 0,
    global_shuffle_feel = 1, global_shuffle_basis = 1, global_shuffle_amount = 0,
    tresillo_amount = 3, all_scales_lock_to_pentatonic = 1
  }
  env.param_values = values
  env.param_sets = {}
  local p = {}
  function p:get(id) return values[id] end
  function p:set(id, value)
    values[id] = value
    env.param_sets[#env.param_sets + 1] = {id, value}
  end
  function p:string(id)
    local options = OPTIONS[id]
    if options then return tostring(options[values[id]]) end
    return tostring(values[id])
  end
  return p
end

function page_env.isolated(body)
  local before = {}
  for k, v in pairs(_G) do before[k] = v end
  local env = {pressed = {}, tooltips = {}, divisions_set = {}, queued = {}, algorithm = 1}
  local ok, err = pcall(function()
    program.init()
    local divisions = include("mosaic/lib/clock/divisions").clock_divisions
    local real_divisor = before.m_clock and before.m_clock.calculate_divisor
    draw = {register_ui = function() end, register_grid = function() end}
    tooltip = {show = function(_, message) env.tooltips[#env.tooltips + 1] = message end}
    m_grid = {get_pressed_keys = function() return env.pressed end}
    m_clock = {
      get_clock_divisions = function() return divisions end,
      calculate_divisor = function(mods) return real_divisor and real_divisor(mods) or mods.value end,
      set_channel_division = function(channel, division)
        env.divisions_set[#env.divisions_set + 1] = {channel, division}
      end,
      is_playing = function() return false end
    }
    step = {queue_for_pattern_change = function(f) env.queued[#env.queued + 1] = f end}
    params = stub_params(env)
    save_confirm = include("mosaic/lib/ui_components/save_confirm")
    is_key1_down = false
    trigger_edit_page = {get_algorithm = function() return env.algorithm end}
    body(env)
  end)
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

-- Loads a fresh page UI, installs it as the global lib/ui.lua would, and runs
-- its init. Returns the module.
function page_env.load(name)
  local page = PAGES[name]
  local ui = include(page.module)
  _G[page.global] = ui
  if ui.register_ui_draws then ui.register_ui_draws() end
  ui.init()
  -- The page's own init (scale_edit_page.init etc.) refreshes the UI from the
  -- model before the first draw.
  if ui.refresh then ui.refresh(ui) end
  return ui
end

function page_env.ids(descriptors)
  local ids = {}
  for index, d in ipairs(descriptors) do ids[index] = d.id end
  return ids
end

function page_env.by_id(descriptors)
  local map = {}
  for _, d in ipairs(descriptors) do map[d.id] = d end
  return map
end

function page_env.copy(value)
  if type(value) ~= "table" then return value end
  local out = {}
  for k, v in pairs(value) do out[k] = page_env.copy(v) end
  return out
end

return page_env

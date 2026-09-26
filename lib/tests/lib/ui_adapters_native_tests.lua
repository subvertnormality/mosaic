-- Characterises README.md "Norns Menu Navigation" (and "Lock lead time",
-- "Mods and Software Devices", "MIDI Controller Mapping", "Device
-- Parameters") as the UI02 native adapter sees them: every Mosaic parameter
-- keeps its id, metadata and action, the runtime device / n.b. / MIDI-map
-- inventories are read from the live ParamSet, and edits go through the same
-- param calls as the norns PARAMETERS menu (core/menu/params.lua).

local ui_adapters = include("mosaic/lib/ui_adapters")
local make_native = include("mosaic/lib/ui_adapters/native")
local application_parameters = include("mosaic/lib/application_parameters")
local param_slots = include("mosaic/lib/devices/param_slots")

local NATIVE_GLOBALS = {"params", "norns", "_menu", "controlspec", "m_midi", "m_clock", "step",
  "song_edit_page_ui", "channel_edit_page_ui", "trigger_edit_page_ui"}

local function core(name)
  local saved_path = package.path
  package.path = "./test_artefacts/norns_test_artefact/lua/?.lua;" .. package.path
  local module = require(name)
  package.path = saved_path
  return module
end

-- A real norns ParamSet with Mosaic's parameters registered in their order.
local function with_params(body)
  local saved = {}
  for index, name in ipairs(NATIVE_GLOBALS) do saved[index] = rawget(_G, name) end
  local ok, err = pcall(function()
    program.init()
    local ParamSet = core("core/paramset")
    controlspec = core("core/controlspec")
    norns = {pmap = {data = {}}, state = {data = "/home/we/dust/data/mosaic/"}}
    _menu = {binarystates = {triggered = {}, on = {}}}
    local env = {calls = {}, dialogs = {}}
    local function record(name) return function(...) env.calls[#env.calls + 1] = {name, ...} end end
    m_midi = {set_lead_time = record("m_midi.set_lead_time")}
    m_clock = {set_lock_contract = record("m_clock.set_lock_contract")}
    step = {forget_sent_lock_values = record("step.forget_sent_lock_values")}
    song_edit_page_ui = setmetatable({}, {__index = function(_, key) return record("song_edit_page_ui." .. key) end})
    channel_edit_page_ui = setmetatable({}, {__index = function(_, key) return record("channel_edit_page_ui." .. key) end})
    trigger_edit_page_ui = setmetatable({}, {__index = function(_, key) return record("trigger_edit_page_ui." .. key) end})
    params = ParamSet.new("ui_adapters_native_test", "test")
    application_parameters.register({save = record("project.save"), load = record("project.load"), new = record("project.new")})
    env.textentry = {enter = function(callback, default, title)
      env.dialogs[#env.dialogs + 1] = {kind = "textentry", callback = callback, default = default, title = title}
    end}
    env.adapter = make_native(ui_adapters, {textentry = env.textentry})
    body(env)
  end)
  for index, name in ipairs(NATIVE_GLOBALS) do rawset(_G, name, saved[index]) end
  if not ok then error(err, 0) end
end

local function describe(adapter, route, fields)
  local target = adapter.capture(route, fields)
  local outcome = adapter:describe(target.screen, route, target, adapter:generation(target))
  luaunit.assert_true(outcome.ok, tostring(outcome.code))
  return outcome.descriptors, target
end

local function by_id(descriptors)
  local map = {}
  for _, d in ipairs(descriptors) do map[d.id] = d end
  return map
end

local function spec_ids(screen)
  local ids = {}
  for _, field in ipairs(ui_adapters.spec.screens[screen].fields) do ids[#ids + 1] = field.id end
  return ids
end

local SCREENS = {X01 = "X01", X02 = "X02", X03 = "X03", X04 = "X04", X05 = "X05", X06 = "X06", X07 = "X07",
  X08 = "X08", X09 = "midi_lock_lead_time"}

function test_ui_adapters_native_every_screen_describes_its_spec_fields_in_order()
  with_params(function(env)
    for screen, route in pairs(SCREENS) do
      luaunit.assert_equals(ui_adapters.spec.screens[screen].existing_route, route)
      local descriptors = describe(env.adapter, route)
      local ids = {}
      for index = 1, #spec_ids(screen) do ids[index] = descriptors[index].id end
      luaunit.assert_equals(ids, spec_ids(screen), screen)
    end
  end)
end

function test_ui_adapters_native_parameters_come_from_the_live_param_objects()
  with_params(function(env)
    local x04 = by_id(describe(env.adapter, "X04"))
    luaunit.assert_equals(x04.stop_safety.domain.param_id, "stop_safety")
    luaunit.assert_equals(x04.stop_safety.label, "Shift press to stop")
    luaunit.assert_equals(x04.stop_safety.value, "Off")
    luaunit.assert_equals(x04.stop_safety.domain.enum, {"Off", "On"})
    luaunit.assert_equals(x04.reset_on_song.domain.param_id, "reset_on_song_pattern_transition")
    luaunit.assert_equals(x04.reset_on_song.value, "On")
    luaunit.assert_equals(x04.repeat_reset.domain.param_id, "reset_on_end_of_pattern_repeat")
    luaunit.assert_equals(x04.slides_wrap.domain.param_id, "wrap_param_slides")
    -- the rest of the MOSAIC group, including the Rhythm Doctor server params
    for _, id in ipairs({"record", "song_mode", "elektron_program_changes", "elektron_program_change_channel",
      "trigless_locks", "repeat_unchanged_locks", "tresillo_amount", "rhythm_doctor_server", "rhythm_doctor_use_server"}) do
      luaunit.assert_not_nil(x04["param:" .. id], id)
      luaunit.assert_equals(x04["param:" .. id].repeat_key, "param:" .. id)
    end
    luaunit.assert_equals(x04["param:rhythm_doctor_server"].kind, "action")
    luaunit.assert_equals(x04["param:rhythm_doctor_use_server"].value, "Off")
    luaunit.assert_equals(x04["param:tresillo_amount"].value, "24")
    luaunit.assert_false(x04["param:global_swing"].visible)
    luaunit.assert_nil(x04["param:midi_lock_lead_time"])
    local x09 = describe(env.adapter, "midi_lock_lead_time")[1]
    luaunit.assert_equals(x09.value, "25")
    luaunit.assert_equals(x09.domain.min, 0)
    luaunit.assert_equals(x09.domain.max, 50)
    local x01 = by_id(describe(env.adapter, "X01"))
    luaunit.assert_equals(x01.save_project.kind, "action")
    luaunit.assert_equals(x01.save_project.label, "< Save project")
    luaunit.assert_equals(x01.autosave.kind, "unavailable")
    luaunit.assert_equals(x01.autosave.value, "NONE")
  end)
end

-- Sweep: every parameter the MOSAIC group registers is reachable from exactly
-- one native screen, so no id is dropped by the migration.
function test_ui_adapters_native_every_mosaic_parameter_is_described_once()
  with_params(function(env)
    local seen = {}
    for _, route in pairs(SCREENS) do
      for _, d in ipairs(describe(env.adapter, route)) do
        local id = d.domain.param_id
        if id and d.kind ~= "unavailable" and d.id ~= "action" then
          luaunit.assert_nil(seen[id], id .. " described twice")
          seen[id] = route
        end
      end
    end
    local group = params.lookup["mosaic"]
    for index = group + 1, group + params.params[group].n do
      local p = params.params[index]
      if p.t ~= params.tSEPARATOR then luaunit.assert_not_nil(seen[p.id], p.id .. " is on no native screen") end
    end
  end)
end

function test_ui_adapters_native_edits_match_the_params_menu()
  local function run(via_adapter)
    local result
    with_params(function(env)
      if via_adapter then
        local _, target = describe(env.adapter, "X04")
        luaunit.assert_true(env.adapter:edit("stop_safety", 1, target, env.adapter:generation(target)).ok)
        local _, lead = describe(env.adapter, "midi_lock_lead_time")
        luaunit.assert_true(env.adapter:edit("midi_lock_lead_time", -5, lead, env.adapter:generation(lead)).ok)
        local _, project = describe(env.adapter, "X01")
        luaunit.assert_true(env.adapter:invoke("save_project", project, env.adapter:generation(project)).ok)
      else
        -- core/menu/params.lua: E3 delta_value -> prm:delta(d); K3 on a trigger -> params:set(i)
        params:lookup_param("stop_safety"):delta(1)
        params:lookup_param("midi_lock_lead_time"):delta(-5)
        params:set("save_p")
      end
      result = {stop = params:get("stop_safety"), lead = params:get("midi_lock_lead_time"), calls = env.calls}
    end)
    return result
  end
  local old, new = run(false), run(true)
  luaunit.assert_equals(new, old)
  luaunit.assert_equals(new.stop, 2)
  luaunit.assert_equals(new.lead, 20)
  luaunit.assert_equals(new.calls[1], {"m_midi.set_lead_time", 20})
  luaunit.assert_equals(new.calls[3], {"project.save"})
end

function test_ui_adapters_native_text_params_open_the_native_text_entry()
  with_params(function(env)
    local _, target = describe(env.adapter, "X04")
    luaunit.assert_true(env.adapter:invoke("param:rhythm_doctor_server", target, env.adapter:generation()).ok)
    luaunit.assert_equals(#env.dialogs, 1)
    luaunit.assert_equals(env.dialogs[1].default, "")
    luaunit.assert_equals(env.dialogs[1].title, "PARAM: Analysis server")
    env.dialogs[1].callback("cancel")
    luaunit.assert_equals(params:get("rhythm_doctor_server"), "")
    env.dialogs[1].callback("10.0.0.2:8765")
    luaunit.assert_equals(params:get("rhythm_doctor_server"), "10.0.0.2:8765")
  end)
end

local function add_device_group(channel, count, hidden_slot)
  params:add_group(param_slots.group_id(channel), "MOSAIC CH " .. channel .. ": GENERIC MIDI", count)
  for slot = 1, count do
    params:add_control(param_slots.control_id(channel, slot), "slot " .. slot, controlspec.new(-1, 127, "lin", 1, -1, "", 1 / 128))
  end
  if hidden_slot then params:hide(param_slots.control_id(channel, hidden_slot)) end
end

function test_ui_adapters_native_device_inventory_is_read_live_for_the_target_channel()
  with_params(function(env)
    -- empty inventory: no device group for the channel
    local empty = describe(env.adapter, "X07", {channel = 5})
    luaunit.assert_equals(#empty, 4)
    luaunit.assert_equals(by_id(empty).device.kind, "unavailable")
    luaunit.assert_equals(by_id(empty).channel.value, "05")

    add_device_group(2, 3, 3)
    local slot_one = param_slots.control_id(2, 1)
    local descriptors, target = describe(env.adapter, "X07", {channel = 2, param_id = slot_one})
    local d = by_id(descriptors)
    luaunit.assert_equals(#descriptors, 7)
    luaunit.assert_equals(d.device.value, "MOSAIC CH 2: GENERIC MIDI")
    luaunit.assert_equals(d.parameter.value, "slot 1")
    luaunit.assert_equals(d.value.domain.param_id, slot_one)
    luaunit.assert_true(d["param:" .. slot_one].visible)
    luaunit.assert_false(d["param:" .. param_slots.control_id(2, 3)].visible)
    luaunit.assert_true(env.adapter:edit("value", 3, target, env.adapter:generation(target)).ok)
    luaunit.assert_equals(params:get(slot_one), 2)
  end)
end

function test_ui_adapters_native_device_inventory_keeps_every_slot_at_maximum_cardinality()
  with_params(function(env)
    add_device_group(16, param_slots.SLOT_COUNT)
    local descriptors = describe(env.adapter, "X07", {channel = 16})
    luaunit.assert_equals(#descriptors, 4 + param_slots.SLOT_COUNT)
    luaunit.assert_equals(descriptors[#descriptors].id, "param:" .. param_slots.control_id(16, param_slots.SLOT_COUNT))
  end)
end

function test_ui_adapters_native_nb_and_midi_map_inventories_are_read_live()
  with_params(function(env)
    params:add_option("voice_id", "NB PARAMS", {"none", "midi: port 1"}, 1)
    params:add_text("voice_id_hidden_string", "_hidden string", "")
    params:hide("voice_id_hidden_string")
    params:add_group("midi_voice_1_1", "midi 1: port", 1)
    params:add_number("midi_chan_1_1", "channel", 1, 16, 1)
    params:add_binary("nb_sentinel_param", "nb_sentinel_param")
    params:hide("nb_sentinel_param")
    local x08 = by_id(describe(env.adapter, "X08"))
    luaunit.assert_equals(x08.audio_n_b.domain.param_id, "voice_id")
    luaunit.assert_equals(x08.audio_n_b.value, "none")
    luaunit.assert_false(x08["param:voice_id_hidden_string"].visible)
    luaunit.assert_equals(x08["param:midi_chan_1_1"].value, "1")
    luaunit.assert_nil(x08["param:nb_sentinel_param"])
    luaunit.assert_equals(x08.mods.kind, "unavailable")

    params:add_group("mosaic_mask_midi_maps", "MASK MIDI MAPS", 1)
    params:add_number("sel_ch_trig", "Selected Ch. Trig", -1, 1, 0)
    norns.pmap.data.sel_ch_trig = {dev = 2, ch = 1, cc = 21, in_lo = 0, in_hi = 127, out_lo = -1, out_hi = 1, accum = true}
    local x06 = by_id(describe(env.adapter, "X06", {param_id = "sel_ch_trig"}))
    luaunit.assert_equals(x06.input.value, "2")
    luaunit.assert_equals(x06.target.value, "Selected Ch. Trig")
    luaunit.assert_equals(x06.controller.value, "CC 21")
    luaunit.assert_equals(x06.mode.value, "yes")
    luaunit.assert_not_nil(x06["param:sel_ch_trig"])
    luaunit.assert_not_nil(x06["param:midi_honour_rotation"])
    local unmapped = by_id(describe(env.adapter, "X06"))
    luaunit.assert_equals(unmapped.controller.kind, "unavailable")
  end)
end

function test_ui_adapters_native_rejects_foreign_routes_and_stale_targets()
  with_params(function(env)
    local adapter = env.adapter
    for _, route in ipairs({"X09", "S01", "A02"}) do
      local outcome = adapter:describe(route, route, {source_route = route})
      luaunit.assert_false(outcome.ok)
      luaunit.assert_equals(outcome.code, "foreign_route")
    end
    local missing = adapter.capture("X07", {param_id = "no_such_param"})
    luaunit.assert_equals(adapter:describe("X07", "X07", missing).code, "stale_target")
    local _, target = describe(adapter, "X04")
    local generation = adapter:generation(target)
    params:add_number("late_param", "late", 0, 1, 0)
    luaunit.assert_equals(adapter:edit("stop_safety", 1, target, generation).code, "stale_generation")
    luaunit.assert_equals(params:get("stop_safety"), 1)
  end)
end

-- Native provider adapter (UI02): screens X01..X08 and X09 (existing_route
-- midi_lock_lead_time).
--
-- owners (all optional; each defaults to the norns global at call time, so a
-- runtime-generated inventory is always read live):
--   params      the live ParamSet (lib/application_parameters.lua, n.b. and
--               param_manager register into it)
--   pmap        norns.pmap (MIDI mapping data)
--   textentry, fileselect   the native dialogs (require "textentry"/"fileselect")
--   dust        _path.dust, the root the params menu gives fileselect
--   data_dir    norns.state.data, the directory mosaic.lua gives fileselect
--               for Load project and textentry's save for Save project
--
-- Every parameter descriptor is built from the live param object: its id,
-- name, type, options/range/controlspec units, visibility (params:visible)
-- and formatted string (param:string()). Nothing is rebuilt from examples.
-- Edits go exactly where the norns PARAMETERS menu sends them
-- (core/menu/params.lua): E3 is delta_value -- param:delta(d), or d/20 with
-- modifiers.fine, a toggle binary is param:set(d) -- and K3 is params:set(id)
-- for a trigger, params:delta(id, 1) for a binary (release: params:delta(id,
-- 0)), textentry.enter for text and fileselect.enter for file, whose
-- callbacks params:set the result unless "cancel". Actions therefore run
-- unchanged, including device, n.b., MIDI-map and Rhythm Doctor server params.
--
-- Spec field ids name live params through PARAM_FIELDS (the param id is the
-- stable identity; the spec id is an alias). Each screen then lists its live
-- inventory as repeated descriptors id = repeat_key = "param:<param id>":
--   X04  every other member of the "mosaic" group (by the group's declared
--        count), so Record, Song mode, Elektron, Trigless, Tresillo, hidden
--        global swing and the Rhythm Doctor server params stay reachable
--   X05  the other pentatonic locks
--   X06  the MIDI control options and the three mapping groups
--   X07  every member of the target channel's device group (all 180 slots)
--   X08  the n.b. voice selector and every n.b. player param after it
-- Fields with no live owner value (autosave state, dialog contents) are
-- "unavailable" with value NONE, the spec's missing value.

local T = {SEPARATOR = 0, NUMBER = 1, OPTION = 2, CONTROL = 3, FILE = 4, TAPER = 5,
  TRIGGER = 6, GROUP = 7, TEXT = 8, BINARY = 9}

local MIDI_MAP_GROUPS = {"mosaic_mask_midi_maps", "mosaic_trig_param_midi_maps", "mosaic_recorder_midi_maps"}

local param_slots = include("mosaic/lib/devices/param_slots")

local function device_group_id(channel)
  return param_slots.group_id(channel)
end

-- Spec field id -> live param id, per screen, in spec field order.
local PARAM_FIELDS = {
  X01 = {{"save_project", "save_p"}, {"load_project", "load_p"}, {"new_project", "new"}},
  X02 = {{"action", "load_p"}},
  X04 = {{"stop_safety", "stop_safety"}, {"reset_on_song", "reset_on_song_pattern_transition"},
    {"repeat_reset", "reset_on_end_of_pattern_repeat"}, {"slides_wrap", "wrap_param_slides"}},
  X05 = {{"snap_masks", "quantiser_act_on_note_masks"}, {"full_quantise", "quantiser_fully_act_on_note_masks"},
    {"scale_lock_hold", "quantiser_trig_lock_hold"}, {"all_pentatonic", "all_scales_lock_to_pentatonic"}},
  X08 = {{"clock", "clock_source"}, {"tempo", "clock_tempo"}, {"audio_n_b", "voice_id"}},
  midi_lock_lead_time = {{"midi_lock_lead_time", "midi_lock_lead_time"}}
}

-- Named inventory params a screen claims from the mosaic group.
local CLAIMED = {
  X05 = {"random_lock_to_pentatonic", "merged_lock_to_pentatonic"},
  X06 = {"midi_scale_mapped_to_white_keys", "midi_honour_rotation", "midi_honour_degree", "midi_honour_transpose"}
}

local ROUTE_ORDER = {"X01", "X02", "X03", "X04", "X05", "X06", "X07", "X08", "midi_lock_lead_time"}

return function(ui_adapters, owners)
  owners = owners or {}

  local function ps() return owners.params or params end
  local function pmap() return owners.pmap or (norns and norns.pmap) end
  local function data_dir() return owners.data_dir or (norns and norns.state and norns.state.data) end
  local function dust() return owners.dust or (_path and _path.dust) end
  local function dialog(name)
    if owners[name] then return owners[name] end
    local ok, module = pcall(require, name)
    return ok and module or nil
  end

  local function index_of(id)
    local set = ps()
    return set.lookup and set.lookup[id] or nil
  end

  local function param_at(index)
    return ps().params[index]
  end

  local function exists(id)
    local index = index_of(id)
    return index ~= nil and param_at(index) ~= nil
  end

  local function structural(p) return p.t == T.SEPARATOR or p.t == T.GROUP end

  -- Members of a norns group: the n params registered after it.
  local function group_members(group_id)
    local index = index_of(group_id)
    if not index then return {} end
    local group = param_at(index)
    if not group or group.t ~= T.GROUP then return {} end
    local ids = {}
    for i = index + 1, index + (group.n or 0) do
      local p = param_at(i)
      if p and not structural(p) then ids[#ids + 1] = p.id end
    end
    return ids
  end

  -- Params registered strictly between two ids (n.b. player params).
  local function between(first_id, last_id)
    local first, last = index_of(first_id), index_of(last_id)
    if not first then return {} end
    last = last or (ps().count or #ps().params) + 1
    local ids = {}
    for i = first + 1, last - 1 do
      local p = param_at(i)
      if p and not structural(p) then ids[#ids + 1] = p.id end
    end
    return ids
  end

  local function unavailable(id, label, domain)
    return {id = id, label = label, kind = "unavailable", value = "NONE", domain = domain or {}}
  end

  local function readonly(id, label, value, domain)
    return {id = id, label = label, kind = "readonly", value = value, domain = domain or {}}
  end

  local function safe_string(p)
    local ok, text = pcall(p.string, p)
    if ok and text ~= nil then return tostring(text) end
    return ""
  end

  -- One descriptor over a live param, dispatching the way the params menu does.
  local function param_descriptor(param_id, field_id, label)
    local set = ps()
    local index = index_of(param_id)
    local p = index and param_at(index)
    if not p or structural(p) then
      return unavailable(field_id or ("param:" .. param_id), label or param_id, {param_id = param_id, missing = true})
    end
    local domain = {param_id = param_id, param_type = p.t, native = true, allow_pmap = p.allow_pmap}
    if p.options then
      domain.enum = {}
      for k, v in ipairs(p.options) do domain.enum[k] = tostring(v) end
    end
    if p.get_range then
      local ok, range = pcall(p.get_range, p)
      if ok and type(range) == "table" then domain.min, domain.max = range[1], range[2] end
    end
    if p.controlspec then
      domain.unit = p.controlspec.units
      domain.step = p.controlspec.step
      domain.min = domain.min or p.controlspec.minval
      domain.max = domain.max or p.controlspec.maxval
    end
    if p.t == T.BINARY then domain.behavior = p.behavior end
    local d = {
      id = field_id or ("param:" .. param_id),
      repeat_key = field_id == nil and ("param:" .. param_id) or nil,
      label = label or p.name or param_id,
      short_label = p.name or param_id,
      value = safe_string(p),
      visible = set.visible == nil or set:visible(index),
      domain = domain
    }
    if p.t == T.TRIGGER then
      d.kind = "action"
      d.invoke = function() return set:set(param_id) end
    elseif p.t == T.BINARY and p.behavior ~= "toggle" then
      d.kind = "action"
      d.invoke = function() return set:delta(param_id, 1) end
      d.release = function() return set:delta(param_id, 0) end
    elseif p.t == T.BINARY then
      d.kind = "value"
      d.edit = function(delta) return p:set(delta) end
      d.invoke = function() return set:delta(param_id, 1) end
    elseif p.t == T.TEXT then
      d.kind = "action"
      d.invoke = function()
        local textentry = dialog("textentry")
        if not textentry then return ui_adapters.fail("native_dialog_unavailable", {field = d.id}) end
        return textentry.enter(function(txt)
          if txt ~= "cancel" then set:set(param_id, txt) end
        end, set:get(param_id), "PARAM: " .. (p.name or param_id))
      end
    elseif p.t == T.FILE then
      d.kind = "action"
      d.invoke = function()
        local fileselect = dialog("fileselect")
        if not fileselect then return ui_adapters.fail("native_dialog_unavailable", {field = d.id}) end
        fileselect.enter(dust(), function(file)
          if file ~= "cancel" then set:set(param_id, file) end
        end)
        if p.dir ~= nil then fileselect.pushd(p.dir) end
      end
    else
      d.kind = "value"
      d.edit = function(delta, modifiers)
        local dx = (modifiers and modifiers.fine) and (delta / 20) or delta
        p:delta(dx)
        return p:get()
      end
    end
    return d
  end

  local function aliases(route)
    local out = {}
    for _, pair in ipairs(PARAM_FIELDS[route] or {}) do
      local d = param_descriptor(pair[2], pair[1])
      d.domain.alias_of = pair[2]
      out[#out + 1] = d
    end
    return out
  end

  local function append_inventory(descriptors, ids, skip)
    for _, id in ipairs(ids) do
      if not (skip and skip[id]) then descriptors[#descriptors + 1] = param_descriptor(id) end
    end
    return descriptors
  end

  -- Param ids other screens name, so X04 lists only what nobody else does.
  local function claimed_elsewhere()
    local claimed = {}
    for route, pairs_ in pairs(PARAM_FIELDS) do
      if route ~= "X04" then for _, pair in ipairs(pairs_) do claimed[pair[2]] = true end end
    end
    for route, ids in pairs(CLAIMED) do
      if route ~= "X04" then for _, id in ipairs(ids) do claimed[id] = true end end
    end
    for _, pair in ipairs(PARAM_FIELDS.X04) do claimed[pair[2]] = true end
    return claimed
  end

  local function mapped_param(target)
    local id = type(target) == "table" and target.param_id or nil
    if id and exists(id) then return id, param_at(index_of(id)) end
    return nil
  end

  local builders = {}

  builders.X01 = function()
    local d = aliases("X01")
    d[#d + 1] = unavailable("autosave", "Autosave",
      {reason = "project_lifecycle keeps autosave_inhibited closure-local; no owner getter"})
    return d
  end

  builders.X02 = function()
    local dir = data_dir()
    local action = aliases("X02")[1]
    return {
      dir and readonly("directory", "Directory", dir, {source = "mosaic.lua fileselect.enter(norns.state.data)"})
        or unavailable("directory", "Directory"),
      unavailable("project", "Project", {owner = "native fileselect"}),
      action,
      unavailable("current_song", "Current song", {owner = "native fileselect"})
    }
  end

  builders.X03 = function()
    return {
      unavailable("name", "Name", {owner = "native textentry"}),
      readonly("files", "Files", ".ptn + .pset", {source = "project_lifecycle save_project"}),
      readonly("scope", "Scope", "Whole project", {source = "program.prepare_for_save"}),
      unavailable("state", "State", {owner = "project_lifecycle"})
    }
  end

  builders.X04 = function()
    local skip = claimed_elsewhere()
    return append_inventory(aliases("X04"), group_members("mosaic"), skip)
  end

  builders.X05 = function()
    return append_inventory(aliases("X05"), CLAIMED.X05)
  end

  builders.X06 = function(target)
    local id, p = mapped_param(target)
    local map = id and pmap() and pmap().data and pmap().data[id] or nil
    local d = {}
    if map then
      d[1] = readonly("input", "Input", tostring(map.dev), {dev = map.dev, ch = map.ch})
      d[2] = readonly("target", "Target", p.name or id, {param_id = id})
      d[3] = readonly("controller", "Controller", "CC " .. tostring(map.cc), {cc = map.cc, ch = map.ch,
        in_lo = map.in_lo, in_hi = map.in_hi, out_lo = map.out_lo, out_hi = map.out_hi})
      d[4] = readonly("mode", "Mode", map.accum and "yes" or "no", {accum = map.accum, echo = map.echo,
        parser = "accum: value > 64 is +1, otherwise -1 (norns core/menu/params.lua)"})
    else
      d[1] = unavailable("input", "Input")
      d[2] = id and readonly("target", "Target", p.name or id, {param_id = id}) or unavailable("target", "Target")
      d[3] = unavailable("controller", "Controller")
      d[4] = unavailable("mode", "Mode")
    end
    append_inventory(d, CLAIMED.X06)
    for _, group_id in ipairs(MIDI_MAP_GROUPS) do append_inventory(d, group_members(group_id)) end
    return d
  end

  builders.X07 = function(target)
    local channel = type(target) == "table" and target.channel or program.get().selected_channel
    if type(channel) ~= "number" then
      return {unavailable("channel", "Channel"), unavailable("device", "Device"),
        unavailable("parameter", "Parameter"), unavailable("value", "Value")}
    end
    local group_id = device_group_id(channel)
    local group_index = index_of(group_id)
    local group = group_index and param_at(group_index)
    local d = {
      readonly("channel", "Channel", string.format("%02d", channel), {channel = channel}),
      group and readonly("device", "Device", group.name, {group_id = group_id, visible = ps():visible(group_index)})
        or unavailable("device", "Device", {group_id = group_id})
    }
    local id, p = mapped_param(target)
    if id then
      d[3] = readonly("parameter", "Parameter", p.name or id, {param_id = id})
      d[4] = param_descriptor(id, "value", "Value")
    else
      d[3] = unavailable("parameter", "Parameter")
      d[4] = unavailable("value", "Value")
    end
    return append_inventory(d, group_members(group_id))
  end

  builders.X08 = function()
    local d = aliases("X08")
    table.insert(d, 3, unavailable("mods", "Mods", {owner = "norns SYSTEM > MODS"}))
    return append_inventory(d, between("voice_id", "nb_sentinel_param"))
  end

  builders.midi_lock_lead_time = function()
    return aliases("midi_lock_lead_time")
  end

  local function target_valid(target)
    if target == nil then return true end
    if type(target) ~= "table" then return false end
    if target.param_id ~= nil and not exists(target.param_id) then return false end
    if target.channel ~= nil and (type(target.channel) ~= "number" or target.channel < 1 or target.channel > 16) then
      return false
    end
    return true
  end

  local adapter = ui_adapters.new("native", {
    describe = function(route, target)
      local builder = builders[route]
      if not builder then return nil, "unknown_native_route" end
      return builder(target)
    end,
    -- The live inventory size: n.b./device registration changes it.
    generation = function() return ps().count or 0 end,
    target_valid = target_valid
  })

  adapter.routes = ROUTE_ORDER

  function adapter.capture(route, fields)
    local target = {source_route = route, screen = route == "midi_lock_lead_time" and "X09" or route}
    for key, value in pairs(fields or {}) do target[key] = value end
    return target
  end

  return adapter
end

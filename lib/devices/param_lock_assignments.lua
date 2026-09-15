local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")
local param_slots = include("mosaic/lib/devices/param_slots")

local assignments = {}

function assignments.update_param(index, channel, param, meta_device)
  local previous = channel.trig_lock_params[index] or {}
  if param.id == "none" then
    channel.trig_lock_params[index] = {}
  else
    channel.trig_lock_params[index] = fn.deep_copy(param)
    local assigned = channel.trig_lock_params[index]
    assigned.device_name = meta_device.device_name
    assigned.type = meta_device.type
    assigned.id = param.id
    assigned.param_id = param.id

    if param.param_type == "stock" then
      assigned.param_id = fn.get_param_id_from_stock_id(param.param_id or param.id, channel.number)
    elseif meta_device.type == "norns" and param.param_id then
      assigned.param_id = param.param_id
    else
      assigned.param_id = param_slots.assignment_id(channel.number, param.index)
    end
  end

  local assigned = channel.trig_lock_params[index]
  if assigned.nrpn_msb ~= nil and assigned.nrpn_lsb ~= nil then
    assigned.nrpn_lsb_mode = nrpn_codec.stored_mode(program.get(), channel.number, param, meta_device)
  end
  if previous.id ~= assigned.id or previous.param_id ~= assigned.param_id or
      previous.type ~= assigned.type or previous.device_name ~= assigned.device_name or
      previous.nrpn_lsb_mode ~= assigned.nrpn_lsb_mode then
    m_clock.cancel_spread_actions_for_channel_trig_lock(channel.number, index)
    recorder.clear_trig_lock_dirty(channel.number, index)
  end
end

local function safe_set_param(channel, index, param, meta_device)
  recorder.clear_trig_lock_dirty(channel.number, index)
  if not channel.trig_lock_params then
    channel.trig_lock_params = {}
  end

  if not param or not next(param) then
    channel.trig_lock_params[index] = {}
    return
  end

  local param_copy = fn.deep_copy(param)
  param_copy.device_name = meta_device and meta_device.device_name or ""
  param_copy.type = meta_device and meta_device.type or ""
  param_copy.id = param.id or ""

  if param_copy.type == "midi" and param_copy.index then
    param_copy.param_id = param_slots.assignment_id(channel.number, param_copy.index)
  end

  if param_copy.nrpn_msb ~= nil and param_copy.nrpn_lsb ~= nil then
    param_copy.nrpn_lsb_mode = nrpn_codec.stored_mode(program.get(), channel.number, param, meta_device)
  end
  channel.trig_lock_params[index] = param_copy
end

function assignments.update_default_params(channel, meta_device)
  local device_params = device_map.get_params(meta_device.id)

  for i = 1, param_slots.LOCK_SLOT_COUNT do
    if meta_device.map_params_automatically and type(meta_device.map_params_automatically) == "table" and meta_device.map_params_automatically[i] then
      local id = meta_device.map_params_automatically[i]
      if type(id) == "string" then
        local param = fn.find_in_table_by_id(device_params or {}, id)
        safe_set_param(channel, i, param, meta_device)
      end
    else
      safe_set_param(channel, i, nil, meta_device)
    end
  end

  if meta_device.fixed_note then
    params:set(param_slots.assignment_id(channel.number or 0, param_slots.FIXED_NOTE_SLOT), meta_device.fixed_note)
  end

  channel_edit_page_ui.refresh_trig_lock_values()
end

return assignments

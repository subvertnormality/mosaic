

local param_manager = {}

local first_run = true


local function construct_value_formatter(off_value, ui_labels)
  local off_val = off_value
  return function(param)
    local value = param:get()
    if not off_value then
      return ui_labels and ui_labels[value + 1] or value
    end
    if value == off_val then
      return "X"
    else
      return ui_labels and ui_labels[value + 1] or value
    end
  end
end

function param_manager.init()
  for i = 1, 16 do
    if params.lookup["midi_device_params_group_channel_" .. i] == nil then
      params:add_group("midi_device_params_group_channel_" .. i, "MOSAIC CH " .. i, 180)
      params:hide("midi_device_params_group_channel_" .. i)
    end

    for j = 1, 180 do
      if params.lookup["midi_device_params_channel_" .. i .. "_" .. j] == nil then
        -- params:add_number("midi_device_params_channel_" .. i .. "_" .. j, "undefined", -1, 10000, -1)
        params:add_control("midi_device_params_channel_" .. i .. "_" .. j, "undefined", controlspec.new(0, 0, 'lin', 0, -1, '', 0))
        params:set_action(
          "midi_device_params_channel_" .. i .. "_" .. j,
          function(x)
          end
        )
        params:show("midi_device_params_channel_" .. i .. "_" .. j)
        local p = params:lookup_param("midi_device_params_channel_" .. i .. "_" .. j)
        p.controlspec.default = -1
        p:set(-1)
        p.formatter = construct_value_formatter(-1)

      end
    end
  end
end


function param_manager.add_device_params(channel_id, device, c, midi_device, init)
  if device and (device.type == "midi" or device.type == "norns") then
    -- Set group parameter name and show it
    params:lookup_param("midi_device_params_group_channel_" .. channel_id).name =
      "MOSAIC CH " .. channel_id .. ": " .. string.upper(device.name)
    params:show("midi_device_params_group_channel_" .. channel_id)

    local stock_params = device_map.get_stock_params()
    local accumulator = 1

    -- Process stock parameters
    for i, val in pairs(stock_params) do
      if val and val.id ~= "none" then

        local p = params:lookup_param("midi_device_params_channel_" .. channel_id .. "_" .. i)

        p.default = val.off_value or -1
        p.controlspec.minval = val.cc_min_value or -1
        p.controlspec.maxval = val.cc_max_value or 127
        p.min = val.cc_min_value or -1
        p.max = val.cc_max_value or 127
        p.controlspec.step = 1
        p.controlspec.quantum = 1/((val.cc_max_value - val.cc_min_value) or 127)
        p.controlspec.default = val.off_value or -1

        p.name = val.name

        if init == true then
          p:set(val.off_value or -1)
        end
        p.formatter = construct_value_formatter(val.off_value or -1, val.ui_labels)
        params:set_action(
          "midi_device_params_channel_" .. channel_id .. "_" .. i,
          function(x)
            channel_edit_page_ui.refresh_trig_lock_values()
            autosave_reset()
          end
        )
        params:show("midi_device_params_channel_" .. channel_id .. "_" .. i)
      end
      accumulator = accumulator + 1
      if val.id == "none" then
        params:hide("midi_device_params_channel_" .. channel_id .. "_" .. i)
      end
    end

    local oob_accumulator = 40 -- ensure we have room to add more stock params without breaking changes

    if device.type == "norns" and device.supports_slew then
      local p = params:lookup_param("midi_device_params_channel_" .. channel_id .. "_" .. oob_accumulator)

      p.default = -1
      p.controlspec.minval = 0
      p.controlspec.maxval = 60
      p.min = 0
      p.max = 60
      p.controlspec.step = 1
      p.controlspec.quantum = 1/60
      p.controlspec.default = 0
      p.name = "Slew"
      if init == true then
        p:set(0)
      end
      p.formatter = construct_value_formatter(-1)
      params:set_action(
        "midi_device_params_channel_" .. channel_id .. "_" .. oob_accumulator,
        function(x)
          channel_edit_page_ui.refresh_trig_lock_values()
          autosave_reset()
        end
      )
      params:show("midi_device_params_channel_" .. channel_id .. "_" .. oob_accumulator)
      oob_accumulator = oob_accumulator + 1
    end


    -- Process device-specific parameters
    for k, val in pairs(device.params) do
      local i = k + accumulator - 1
      if device.type == "midi" and val and val.id ~= "none" and val.param_type ~= "stock" then
        local p = params:lookup_param("midi_device_params_channel_" .. channel_id .. "_" .. i)

        if val.nrpn_min_value and val.nrpn_max_value and val.nrpn_lsb and val.nrpn_msb then
          p.controlspec.minval = val.nrpn_min_value or -1
          p.controlspec.maxval = val.nrpn_max_value or 16383
          p.min = val.nrpn_min_value or -1
          p.max = val.nrpn_max_value or 16383
          p.controlspec.step = 1
          p.controlspec.quantum = 1/(((val.nrpn_max_value - val.nrpn_min_value) or 16383) / 127)
          p.controlspec.default = val.off_value or -1
        else
          p.controlspec.minval = val.cc_min_value or -1
          p.controlspec.maxval = val.cc_max_value or 127
          p.min = val.cc_min_value or -1
          p.max = val.cc_max_value or 127
          p.controlspec.step = 1
          p.controlspec.quantum = 1/(val.cc_max_value - val.cc_min_value) or 127
          p.controlspec.default = val.off_value or -1
        end
        p.name = val.name
        if init == true then
          p:set(val.off_value or 0)
        end
        p.formatter = construct_value_formatter(val.off_value, val.ui_labels)
        params:set_action(
          "midi_device_params_channel_" .. channel_id .. "_" .. i,
          function(x)
            if x ~= val.off_value then
              if val.nrpn_max_value and val.nrpn_lsb and val.nrpn_msb then
                m_midi.nrpn(val.nrpn_msb, val.nrpn_lsb, x, c, midi_device)
              elseif val.cc_msb and val.cc_max_value then
                m_midi.cc(val.cc_msb, val.cc_lsb or nil, x, c, midi_device)
              end
              channel_edit_page_ui.refresh_trig_lock_values()
            end
            autosave_reset()
          end
        )
        params:show("midi_device_params_channel_" .. channel_id .. "_" .. i)
      else
        params:set_action("midi_device_params_channel_" .. channel_id .. "_" .. i, function(x) end)
        params:hide("midi_device_params_channel_" .. channel_id .. "_" .. i)
      end
      oob_accumulator = i + 1
    end


    -- Hide remaining parameters
    for j = oob_accumulator, 180 do
      params:set_action("midi_device_params_channel_" .. channel_id .. "_" .. j, function(x) end)
      params:hide("midi_device_params_channel_" .. channel_id .. "_" .. j)
    end
  else
    -- Hide group parameter and reset individual parameters
    params:hide("midi_device_params_group_channel_" .. channel_id)
    for i = 1, 180 do
      local p = params:lookup_param("midi_device_params_channel_" .. channel_id .. "_" .. i)
      p:set(-1)
      p.name = "undefined"
      params:set_action("midi_device_params_channel_" .. channel_id .. "_" .. i, function(x) end)
      params:hide("midi_device_params_channel_" .. channel_id .. "_" .. i)
    end
  end
  _menu.rebuild_params()
end


function param_manager.update_param(index, channel, param, meta_device)
  if param.id == "none" then
    channel.trig_lock_params[index] = {}
  else
    channel.trig_lock_params[index] = {}
    channel.trig_lock_params[index] = fn.deep_copy(param)
    channel.trig_lock_params[index].device_name = meta_device.device_name
    channel.trig_lock_params[index].type = meta_device.type
    channel.trig_lock_params[index].id = param.id
    channel.trig_lock_params[index].param_id = param.id
      
    if param.param_type == "stock" then
      channel.trig_lock_params[index].param_id = fn.get_param_id_from_stock_id(param.param_id, channel.number)
    elseif meta_device.type == "norns" and param.param_id then
      channel.trig_lock_params[index].param_id = param.param_id
    else
      channel.trig_lock_params[index].param_id = string.format("midi_device_params_channel_%d_%d", channel.number, param.index)
    end

  end
end

local function safe_set_param(channel, index, param, meta_device)
  if not channel.trig_lock_params then 
    channel.trig_lock_params = {} 
  end
  
  -- If param is nil or empty, just set empty table
  if not param or not next(param) then
    channel.trig_lock_params[index] = {}
    return
  end
  
  -- Create a deep clone of the param
  local param_copy = fn.deep_copy(param)
  
  -- Set the channel-specific fields
  param_copy.device_name = meta_device and meta_device.device_name or ""
  param_copy.type = meta_device and meta_device.type or ""
  param_copy.id = param.id or ""
  
  -- Always ensure param_id is channel-specific
  if param_copy.type == "midi" and param_copy.index then
    param_copy.param_id = string.format("midi_device_params_channel_%d_%d", channel.number, param_copy.index)
  end
  
  -- Assign the cloned and modified param
  channel.trig_lock_params[index] = param_copy
end

function param_manager.update_default_params(channel, meta_device)
  -- Use the merged parameters with index keys
  local device_params = device_map.get_params(meta_device.id)

  for i = 1, 10 do
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
    params:set(string.format("midi_device_params_channel_%d_2", channel.number or 0), meta_device.fixed_note)
  end

  channel_edit_page_ui.refresh_trig_lock_values()
end



return param_manager

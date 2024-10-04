local fn = include("mosaic/lib/functions")

local param_manager = {}

local first_run = true


local function construct_off_value_formatter(off_value)
  local off_val = off_value
  return function(param)
    local value = param:get()
    if not off_value then
      return value
    end
    if value == off_val then
      return "X"
    else
      return value
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
        params:add_number("midi_device_params_channel_" .. i .. "_" .. j, "undefined", -1, 10000, -1)

        params:set_action(
          "midi_device_params_channel_" .. i .. "_" .. j,
          function(x)
          end
        )
        params:show("midi_device_params_channel_" .. i .. "_" .. j)
      end
    end
  end
end


function param_manager.add_device_params(channel_id, device, channel, midi_device, init)
  if device and (device.type == "midi" or device.type == "norns") then
    -- Set group parameter name and show it
    params:lookup_param("midi_device_params_group_channel_" .. channel_id).name =
      "MOSAIC CH " .. channel_id .. ": " .. string.upper(device.name)
    params:show("midi_device_params_group_channel_" .. channel_id)

    local stock_params = device_map.get_stock_params()
    local accumulator = 1

    -- Process stock parameters
    for i, val in pairs(stock_params) do
      if val then
        local p = params:lookup_param("midi_device_params_channel_" .. channel_id .. "_" .. i)

        if val.nrpn_min_value and val.nrpn_max_value and val.nrpn_lsb and val.nrpn_msb then
          p.min = val.nrpn_min_value or -1
          p.max = val.nrpn_max_value or 16383
        else
          p.min = val.cc_min_value or -1
          p.max = val.cc_max_value or 127
        end

        p.name = val.name
        if init == true then
          p.value = val.off_value or -1
        end
        p.formatter = construct_off_value_formatter(val.off_value)
        params:set_action(
          "midi_device_params_channel_" .. channel_id .. "_" .. i,
          function(x)
            channel_edit_page_ui_controller.refresh_trig_lock_values()
            autosave_reset()
          end
        )
        params:show("midi_device_params_channel_" .. channel_id .. "_" .. i)
        accumulator = accumulator + 1
        if val.id == "none" then
          params:hide("midi_device_params_channel_" .. channel_id .. "_" .. i)
        end
      end
    end

    local oob_accumulator = 40 -- ensure we have room to add more stock params without breaking changes

    if device.type == "norns" and device.supports_slew then
      local p = params:lookup_param("midi_device_params_channel_" .. channel_id .. "_" .. oob_accumulator)
      p.min = -1
      p.max = 60
      p.name = "Slew"
      if init == true then
        p.value = -1
      end
      p.formatter = construct_off_value_formatter(-1)
      params:set_action(
        "midi_device_params_channel_" .. channel_id .. "_" .. oob_accumulator,
        function(x)
          channel_edit_page_ui_controller.refresh_trig_lock_values()
          autosave_reset()
        end
      )
      params:show("midi_device_params_channel_" .. channel_id .. "_" .. oob_accumulator)
      oob_accumulator = oob_accumulator + 1
    end

    if device.type == "midi" then
      -- Process device-specific parameters
      for k, val in pairs(device.params) do
        local i = k + accumulator - 1
        if val and val.id ~= "none" and val.param_type ~= "stock" then
          local p = params:lookup_param("midi_device_params_channel_" .. channel_id .. "_" .. i)

          if val.nrpn_min_value and val.nrpn_max_value and val.nrpn_lsb and val.nrpn_msb then
            p.min = val.nrpn_min_value or -1
            p.max = val.nrpn_max_value or 16383
          else
            p.min = val.cc_min_value or -1
            p.max = val.cc_max_value or 127
          end
          p.name = val.name
          if init == true then
            p.value = val.off_value or -1
          end
          p.formatter = construct_off_value_formatter(val.off_value)
          params:set_action(
            "midi_device_params_channel_" .. channel_id .. "_" .. i,
            function(x)
              if x ~= -1 then
                if val.nrpn_max_value and val.nrpn_lsb and val.nrpn_msb then
                  midi_controller.nrpn(val.nrpn_msb, val.nrpn_lsb, x, channel, midi_device)
                else
                  midi_controller.cc(val.cc_msb, val.cc_lsb, x, channel, midi_device)
                end
                channel_edit_page_ui_controller.refresh_trig_lock_values()
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
      p.value = -1
      p.name = "undefined"
      params:set_action("midi_device_params_channel_" .. channel_id .. "_" .. i, function(x) end)
      params:hide("midi_device_params_channel_" .. channel_id .. "_" .. i)
    end
  end
end


function param_manager.update_param(index, channel, param, meta_device)
  if param.id == "none" then
    channel.trig_lock_params[index] = {}
  else
    channel.trig_lock_params[index] = param
    -- param_select_vertical_scroll_selector:get_meta_item().device_name
    channel.trig_lock_params[index].device_name = meta_device.device_name
    channel.trig_lock_params[index].type = meta_device.type
    channel.trig_lock_params[index].id = param.id
    channel.trig_lock_params[index].param_id = param.id
      
    if meta_device.type == "norns" then
      channel.trig_lock_params[index].param_id = param.param_id
    else
      channel.trig_lock_params[index].param_id = "midi_device_params_channel_" .. channel.number .. "_" .. param.index
    end

  end
end


function param_manager.update_default_params(channel, meta_device)
  for i = 1, 10 do
    channel.trig_lock_params[i] = {}
    if type(meta_device.map_params_automatically) == "table" then
      local id = meta_device.map_params_automatically[i]
      print("is table, id: ", id)
      if id and type(id) == "string" then
        print("is string ", id)
        local param = fn.find_in_table_by_id(meta_device.params, id)
        if param then
          print("found param ", param)
          channel.trig_lock_params[i] = param
          channel.trig_lock_params[i].device_name = meta_device.device_name
          channel.trig_lock_params[i].type = meta_device.type
          channel.trig_lock_params[i].id = param.id
          if (channel.trig_lock_params[i].type == "midi" and param.index) then
            channel.trig_lock_params[i].param_id =
              "midi_device_params_channel_" .. channel.number .. "_" .. param.index
          elseif (channel.trig_lock_params[i].type == "norns" and param.index) then
              channel.trig_lock_params[i].param_id = param.param_id
          end
        end
      end
    elseif meta_device.map_params_automatically == true then
      
      if meta_device.params[i + 1] then
        channel.trig_lock_params[i] = meta_device.params[i + 1]
        channel.trig_lock_params[i].device_name = meta_device.device_name
        channel.trig_lock_params[i].type = meta_device.type
        channel.trig_lock_params[i].id = meta_device.params[i + 1].id
        if
          (channel.trig_lock_params[i].type == "midi" and meta_device.params[i + 1].index)
         then
          channel.trig_lock_params[i].param_id =
            "midi_device_params_channel_" .. channel.number .. "_" .. meta_device.params[i + 1].index
        elseif (channel.trig_lock_params[i].type == "norns" and meta_device.params[i + 1].index) then
            channel.trig_lock_params[i].param_id = meta_device.params[i + 1].param_id
        end
      end
    end
  end

  if meta_device.fixed_note then
    params:set("midi_device_params_channel_" .. channel.number .. "_2", meta_device.fixed_note)  -- TODO: fix this magic number
  end

  channel_edit_page_ui_controller.refresh_trig_lock_values()
end

return param_manager

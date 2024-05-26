local fn = include("mosaic/lib/functions")

local param_manager = {}

local first_run = true

function param_manager.init()
  for i = 1, 16 do
    if params.lookup["midi_device_params_group_channel_" .. i] == nil then
      params:add_group("midi_device_params_group_channel_" .. i, "MOSAIC CH " .. i, 127)
      params:hide("midi_device_params_group_channel_" .. i)
    end

    for j = 1, 127 do
      if params.lookup["midi_device_params_channel_" .. i .. "_" .. j] == nil then
        params:add_number("midi_device_params_channel_" .. i .. "_" .. j, "undefined", -1, 10000, -1)
        params:set_action(
          "midi_device_params_channel_" .. i .. "_" .. j,
          function(x)
          end
        )
        params:hide("midi_device_params_channel_" .. i .. "_" .. j)
      end
    end
  end
end

function param_manager.add_device_params(channel_id, device, channel, midi_device, init)
  if device and device.type == "midi" then
    params:lookup_param("midi_device_params_group_channel_" .. channel_id).name =
      "MOSAIC CH " .. channel_id .. ": " .. string.upper(device.name)
    params:show("midi_device_params_group_channel_" .. channel_id)

    for i = 1, 127 do
      if device.params[i] ~= nil and device.params[i].id ~= "none" then
        local p = params:lookup_param("midi_device_params_channel_" .. channel_id .. "_" .. i)
        p.max = device.params[i].cc_max_value
        p.name = device.params[i].name
        if init == true then
          p.value = -1
        end
        params:set_action(
          "midi_device_params_channel_" .. channel_id .. "_" .. i,
          function(x)
            if x ~= -1 then
              midi_controller.cc(device.params[i].cc_msb, device.params[i].cc_lsb, x, channel, midi_device)
              channel_edit_page_ui_controller.refresh_trig_lock_values()
            end
            autosave_reset()
          end
        )
        params:show("midi_device_params_channel_" .. channel_id .. "_" .. i)
      else
        params:set_action(
          "midi_device_params_channel_" .. channel_id .. "_" .. i,
          function(x)
          end
        )
        params:hide("midi_device_params_channel_" .. channel_id .. "_" .. i)
      end
    end
  else
    params:hide("midi_device_params_group_channel_" .. channel_id)
    for i = 1, 127 do
      local p = params:lookup_param("midi_device_params_channel_" .. channel_id .. "_" .. i)
      p.value = -1
      p.name = "undefined"
      params:set_action(
        "midi_device_params_channel_" .. channel_id .. "_" .. i,
        function(x)
        end
      )
      params:hide("midi_device_params_channel_" .. channel_id .. "_" .. i)
    end
  end
end



function param_manager.update_param(index, channel, param, meta_device)
  if id == "none" then
    channel.trig_lock_params[index] = {}
  else

    channel.trig_lock_params[index] = param
    -- param_select_vertical_scroll_selector:get_meta_item().device_name
    channel.trig_lock_params[index].device_name = meta_device.device_name
    channel.trig_lock_params[index].type = meta_device.type
    channel.trig_lock_params[index].id = param.id
      
    if (meta_device.type == "midi" and meta_device.param_type ~= "stock") then
      channel.trig_lock_params[index].param_id =
        "midi_device_params_channel_" .. channel.number .. "_" .. param.index
    else
      channel.trig_lock_params[index].param_id = nil
    end
  end
end


function param_manager.update_default_params(channel, meta_device)
  -- local midi_device_m = device_map_vertical_scroll_selector:get_selected_item()

  for i = 1, 10 do
    if meta_device.params[i + 1] and meta_device.map_params_automatically then
      channel.trig_lock_params[i] = meta_device.params[i + 1]
      channel.trig_lock_params[i].device_name = meta_device.device_name
      channel.trig_lock_params[i].type = meta_device.type
      channel.trig_lock_params[i].id = meta_device.params[i + 1].id
      if
        (channel.trig_lock_params[i].type == "midi" and meta_device.params[i + 1].param_type ~= "stock" and
          meta_device.params[i + 1].index
        )
       then
        channel.trig_lock_params[i].param_id =
          "midi_device_params_channel_" .. channel.number .. "_" .. meta_device.params[i + 1].index
      else
        channel.trig_lock_params[i].param_id = nil
      end
      if meta_device.params[i + 1].default then
        channel.trig_lock_banks[i] = meta_device.params[i + 1].default
      end
    else
      channel.trig_lock_params[i] = {}
    end
  end

  channel_edit_page_ui_controller.refresh_trig_lock_values()
end

return param_manager

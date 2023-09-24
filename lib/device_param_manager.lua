local midi_controller = include("mosaic/lib/midi_controller")
local fn = include("mosaic/lib/functions")

local device_param_manager = {}

local first_run = true


-- TODO: Init needs to take into account the set devices and establish them as needed
function device_param_manager.init()

  if params.lookup["midi_device_params_separator"] == nil then
    params:add_separator("midi_device_params_separator", "Mosaic Midi Device Params")
  end

  for i = 1, 16 do
    if params.lookup["midi_device_params_group_channel_"..i] == nil then
      params:add_group ("midi_device_params_group_channel_"..i, "Channel "..i, 127)
      params:hide("midi_device_params_group_channel_"..i)
    end

    for j = 1, 127 do
      if params.lookup["midi_device_params_channel_"..i.."_"..j] == nil then
        params:add_number("midi_device_params_channel_"..i.."_"..j, "undefined", -1, -1, -1)
        params:set_action("midi_device_params_channel_"..i.."_"..j, function(x) end)
        params:hide("midi_device_params_channel_"..i.."_"..j)
      end
    end

  end

end


function device_param_manager.add_device_params(channel_id, device, channel, midi_device, init)

  if device.type == "midi" then

    params:lookup_param("midi_device_params_group_channel_"..channel_id).name = "Channel "..channel_id..": ".. device.name
    params:show("midi_device_params_group_channel_"..channel_id)

    for i = 1, 127 do
      if device.params[i] ~= nil and device.params[i].id ~= "none" then
        local p = params:lookup_param("midi_device_params_channel_"..channel_id.."_"..i)
        p.max = device.params[i].cc_max_value
        p.name = device.params[i].name
        if init == true then
          p.value = -1
        end
        params:set_action("midi_device_params_channel_"..channel_id.."_"..i, function(x) 
          if x ~= -1 then
            midi_controller.cc(device.params[i].cc_msb, device.params[i].cc_lsb, x, channel, midi_device)
          end
        end)
        params:show("midi_device_params_channel_"..channel_id.."_"..i)
      else
        params:set_action("midi_device_params_channel_"..channel_id.."_"..i, function(x) end)
        params:hide("midi_device_params_channel_"..channel_id.."_"..i)
      end
    end
  else
    params:hide("midi_device_params_group_channel_"..channel_id)
    for i = 1, 127 do
      params:set_action("midi_device_params_channel_"..channel_id.."_"..i, function(x) end)
      params:hide("midi_device_params_channel_"..channel_id.."_"..i)
    end
  end

end

return device_param_manager
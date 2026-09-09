local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")
-- Recall stored device controls independently of per-step lock assignments.
local recall = {}
function recall.send()
  for channel=1,16 do
    local route = program.get().devices[channel]
    local device = device_map.get_device(route.device_map)
    if device and device.type == "midi" then
      local stock_count = #device_map.get_stock_params()
      for index,parameter in ipairs(device.params) do
        if parameter.id ~= "none" and parameter.param_type ~= "stock" then
          local value = params:get("midi_device_params_channel_"..channel.."_"..(stock_count+index))
          local off = parameter.off_value == nil and -1 or parameter.off_value
          if value ~= off then
            local midi_channel = parameter.channel or route.midi_channel
            if parameter.nrpn_max_value and parameter.nrpn_msb and parameter.nrpn_lsb then
              m_midi.nrpn(parameter.nrpn_msb,parameter.nrpn_lsb,value,midi_channel,route.midi_device,
                nrpn_codec.stored_mode(program.get(), channel, parameter, device))
            elseif parameter.cc_msb and parameter.cc_max_value then
              m_midi.cc(parameter.cc_msb,parameter.cc_lsb,value,midi_channel,route.midi_device)
            end
          end
        end
      end
    end
  end
end
return recall

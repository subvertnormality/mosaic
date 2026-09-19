local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")


local param_manager = {}
local param_slots = include("mosaic/lib/devices/param_slots")
local param_lock_assignments = include("mosaic/lib/devices/param_lock_assignments")
local midi_value_domain = include("mosaic/lib/devices/midi_value_domain")



local function construct_value_formatter(off_value, ui_labels)
  local off_val = off_value
  return function(param)
    local value = param:get()
    if not off_value then
      return ui_labels and ui_labels[value-off_value+1] or value
    end
    if value == off_val then
      return "X"
    else
      return ui_labels and ui_labels[value-off_value+1] or value
    end
  end
end

function param_manager.init()
  for i = 1, param_slots.CHANNEL_COUNT do
    if params.lookup[param_slots.group_id(i)] == nil then
      params:add_group(param_slots.group_id(i), "MOSAIC CH " .. i, param_slots.SLOT_COUNT)
      params:hide(param_slots.group_id(i))
    end

    for j = 1, param_slots.SLOT_COUNT do
      if params.lookup[param_slots.control_id(i, j)] == nil then
        params:add_control(param_slots.control_id(i, j), "undefined", controlspec.new(0, 0, 'lin', 0, -1, '', 0))
        params:set_action(
          param_slots.control_id(i, j),
          function(x)
          end
        )
        params:show(param_slots.control_id(i, j))
        local p = params:lookup_param(param_slots.control_id(i, j))
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
    params:lookup_param(param_slots.group_id(channel_id)).name =
      "MOSAIC CH " .. channel_id .. ": " .. string.upper(device.name)
    params:show(param_slots.group_id(channel_id))

    local stock_params = device_map.get_stock_params()
    local accumulator = 1

    -- Process stock parameters
    for i, val in pairs(stock_params) do
      if val and val.id ~= "none" then

        local p = params:lookup_param(param_slots.control_id(channel_id, i))

        p.default = val.off_value or -1
        p.min = val.cc_min_value or -1
        p.max = val.cc_max_value or 127
        p.controlspec = controlspec.new(p.min,p.max,"lin",1,p.default,"",1/math.max(1,p.max-p.min))

        p.name = val.name

        if init == true then
          p:set(val.off_value or -1, true)
        end
        p.formatter = construct_value_formatter(val.off_value or -1, val.ui_labels)
        params:set_action(
          param_slots.control_id(channel_id, i),
          function(x)
            channel_edit_page_ui.refresh_trig_lock_values()
            autosave_reset()
          end
        )
        params:show(param_slots.control_id(channel_id, i))
      end
      accumulator = accumulator + 1
      if val.id == "none" then
        params:hide(param_slots.control_id(channel_id, i))
      end
    end

    local oob_accumulator = param_slots.SLEW_SLOT -- ensure we have room to add more stock params without breaking changes

    if device.type == "norns" and device.supports_slew then
      local p = params:lookup_param(param_slots.control_id(channel_id, oob_accumulator))

      p.default = -1
      p.min = 0
      p.max = 60
      p.controlspec = controlspec.new(0,60,"lin",1,0,"",1/60)
      p.name = "Slew"
      if init == true then
        p:set(0, true)
      end
      p.formatter = construct_value_formatter(-1)
      params:set_action(
        param_slots.control_id(channel_id, oob_accumulator),
        function(x)
          channel_edit_page_ui.refresh_trig_lock_values()
          autosave_reset()
        end
      )
      params:show(param_slots.control_id(channel_id, oob_accumulator))
      oob_accumulator = oob_accumulator + 1
    end


    -- Process device-specific parameters
    for k, val in pairs(device.params) do
      local i = k + accumulator - 1
      if device.type == "midi" and val and val.id ~= "none" and val.param_type ~= "stock" then
        local p = params:lookup_param(param_slots.control_id(channel_id, i))

        local nrpn = val.nrpn_min_value and val.nrpn_max_value and val.nrpn_lsb and val.nrpn_msb
        local minimum = nrpn and val.nrpn_min_value or val.cc_min_value or -1
        local maximum = nrpn and val.nrpn_max_value or val.cc_max_value or 127
        p.default = val.off_value or -1
        p.controlspec = midi_value_domain.new(minimum,maximum,p.default,nrpn and 127 or 1)
        p.min = p.controlspec.minval
        p.max = p.controlspec.maxval
        p.name = val.name
        if init == true then
          p:set(val.off_value or -1, true)
        end
        p.formatter = construct_value_formatter(val.off_value == nil and -1 or val.off_value, val.ui_labels)
        params:set_action(
          param_slots.control_id(channel_id, i),
          function(x)
            if x ~= (val.off_value == nil and -1 or val.off_value) then
              if val.nrpn_max_value and val.nrpn_lsb and val.nrpn_msb then
                m_midi.nrpn(val.nrpn_msb, val.nrpn_lsb, x, val.channel or c, midi_device,
                  nrpn_codec.stored_mode(program.get(), channel_id, val, device))
              elseif val.cc_msb and val.cc_max_value then
                m_midi.cc(val.cc_msb, val.cc_lsb or nil, x, val.channel or c, midi_device)
              end
              channel_edit_page_ui.refresh_trig_lock_values()
            end
            autosave_reset()
          end
        )
        params:show(param_slots.control_id(channel_id, i))
      else
        params:set_action(param_slots.control_id(channel_id, i), function(x) end)
        params:hide(param_slots.control_id(channel_id, i))
      end
      oob_accumulator = i + 1
    end

    -- A device without its own params keeps none of the previous device's slots
    if next(device.params) == nil then
      oob_accumulator = accumulator
    end

    -- Hide remaining parameters
    for j = oob_accumulator, param_slots.SLOT_COUNT do
      params:set_action(param_slots.control_id(channel_id, j), function(x) end)
      params:hide(param_slots.control_id(channel_id, j))
    end
  else
    -- Hide group parameter and reset individual parameters
    params:hide(param_slots.group_id(channel_id))
    for i = 1, param_slots.SLOT_COUNT do
      local p = params:lookup_param(param_slots.control_id(channel_id, i))
      p:set(p.controlspec.default, true)
      p.name = "undefined"
      params:set_action(param_slots.control_id(channel_id, i), function(x) end)
      params:hide(param_slots.control_id(channel_id, i))
    end
  end
  _menu.rebuild_params()
end
function param_manager.update_param(index, channel, param, meta_device)
  return param_lock_assignments.update_param(index, channel, param, meta_device)
end

function param_manager.update_default_params(channel, meta_device)
  return param_lock_assignments.update_default_params(channel, meta_device)
end



return param_manager

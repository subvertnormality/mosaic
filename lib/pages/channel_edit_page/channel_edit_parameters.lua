local channel_edit_parameters = {}

function channel_edit_parameters.new(controls, public_ui, refreshers, dependencies)
  local controller = {}
  local function get_value_using_handler_param(channel, dial_index, p, param_id, p_value, delta)
    local param_args = {}
    
    for key, arg in pairs(p) do
      param_args[key] = arg
    end
  
    local handler_param_id = channel.number .. "_lock_calculator_" .. dial_index .. "_" .. program.get_trig_lock_calculator_id(channel, dial_index)
  
    param_args.id = handler_param_id
    param_args.type = fn.get_param_type_from_id(params:t(param_id))
    param_args.controlspec = p.controlspec
  
    local handler_param_id_index = params.lookup[handler_param_id]
  
    if not handler_param_id_index then
      params:add(param_args)
      handler_param_id_index = params.lookup[handler_param_id]
      params:hide(handler_param_id_index)
      params:set_action(handler_param_id_index, function() end)
      params:set(handler_param_id_index, p_value, true)
    end
  
    params:delta(handler_param_id_index, delta)
    
    return params:get(handler_param_id_index)
  end
  function controller.update_channel_config()
    local channel = program.get_selected_channel()
    local midi_device = controls.midi_device_vertical_scroll_selector:get_selected_item()
    local midi_channel = controls.midi_channel_vertical_scroll_selector:get_selected_item()
    local device_m = controls.device_map_vertical_scroll_selector:get_selected_item()
  
    if not midi_device then
      if device_m.type == "midi" then
        tooltip:error("No midi devices connected")
        return
      end
    end
  
    -- Configuration confirmation rebuilds the parameter bank and its actions.
    for slot = 1, 10 do
      recorder.clear_trig_lock_dirty(channel.number, slot)
    end
    program.get().devices[channel.number].midi_device = midi_device and midi_device.value or nil
    program.get().devices[channel.number].midi_channel = midi_channel and midi_channel.value or nil
    program.get().devices[channel.number].device_map = device_m and device_m.id or nil
  
    local device = device_map.get_device(program.get().devices[channel.number].device_map)
    if device.default_midi_channel then
      program.get().devices[channel.number].midi_channel = device.default_midi_channel
    end
  
    if device.default_midi_device then
      program.get().devices[channel.number].midi_device = device.default_midi_device
    end
  
    public_ui.refresh_device_selector()
  
    if device_m.id == "jf kit" or
      device_m.id == "jf n 1" or
      device_m.id == "jf n 2" or
      device_m.id == "jf poly" or
      device_m.id == "jf unison" or
      device_m.id == "jf n 5" or
      device_m.id == "jf mpe" or
      device_m.id == "jf n 4" or
      device_m.id == "jf n 3" or
      device_m.id == "jf n 6"
    then
      crow.ii.pullup(true) 
      crow.ii.jf.mode(1)
    end
  
    if device_m.id == "ansible 1" or
      device_m.id == "ansible 2"
    then
      crow.ii.pullup(true) 
    end
  
    dependencies.param_manager.add_device_params(
      channel.number,
      device_m,
      program.get().devices[channel.number].midi_channel,
      program.get().devices[channel.number].midi_device,
      true
    )
    for i = 1, 10 do
      program.increment_trig_lock_calculator_id(channel, i)
    end
  
    public_ui.refresh_trig_locks()
    
  end
  
  -- Trig lock functions
  function controller.handle_trig_lock_param_change_by_direction(direction, channel, dial_index)
  
    local pressed_keys = m_grid.get_pressed_keys()
    local trig_lock_param = channel.trig_lock_params[dial_index]
  
    if not trig_lock_param then
      return
    end
  
    local param_id = trig_lock_param.param_id
  
    local p, p_index
    if param_id then
      p = params:lookup_param(param_id)
      p_index = params.lookup[param_id]
    else
      return
    end
  
    if not p then
      return
    end
  
    local p_value = params:get(param_id)
  
    local total_range = 0
    local old_quantum = trig_lock_param.quantum or 1
  
    if p.controlspec then 
  
      if p.controlspec.quantum then
        old_quantum = p.controlspec.quantum
      end
  
      total_range = ((p.controlspec.maxval - p.controlspec.minval) / p.controlspec.quantum)
  
      if trig_lock_param.nrpn_min_value and trig_lock_param.nrpn_max_value and trig_lock_param.nrpn_lsb and trig_lock_param.nrpn_msb then
        p.controlspec.quantum = dependencies.midi_value_domain.unit_quantum(trig_lock_param.nrpn_min_value, trig_lock_param.nrpn_max_value, trig_lock_param.off_value)
        total_range = p.controlspec.maxval - p.controlspec.minval
      elseif trig_lock_param.cc_min_value and trig_lock_param.cc_max_value and trig_lock_param.cc_msb then
        p.controlspec.quantum = dependencies.midi_value_domain.unit_quantum(trig_lock_param.cc_min_value, trig_lock_param.cc_max_value, trig_lock_param.off_value)
        total_range = p.controlspec.maxval - p.controlspec.minval
      elseif trig_lock_param.cc_min_value and trig_lock_param.cc_max_value and trig_lock_param.type == "midi" then
        p.controlspec.quantum = dependencies.midi_value_domain.unit_quantum(trig_lock_param.cc_min_value, trig_lock_param.cc_max_value, trig_lock_param.off_value)
        total_range = p.controlspec.maxval - p.controlspec.minval
      end
    elseif p.count then
      total_range = p.count
    elseif p.maxval and p.minval then
      total_range = p.maxval - p.minval
    else
      total_range = 127
    end
  
    local d = direction
  
    if trig_lock_param.type ~= "norns" then
      if total_range > 126 and is_key1_down == false then
        if math.abs(direction) > 0 then
          d = direction * math.floor(total_range / 127) or 1
        end
  
        if math.abs(direction) > 2 then
          d = direction * math.floor(total_range / 64) or 1
        end
  
        if math.abs(direction) > 5 then
          d = direction * math.floor(total_range / 32) or 1
        end
  
        if math.abs(direction) > 8 then
          d = direction * math.floor(total_range / 16) or 1
        end
  
        if math.abs(direction) > 10 then
          d = direction * math.floor(total_range / 8) or 1
        end
  
        if math.abs(direction) > 13 then
          d = direction * math.floor(total_range / 4) or 1
        end
  
        if math.abs(direction) > 15 then
          d = direction * math.floor(total_range / 2) or 1
        end
      end
    end
  
    if #pressed_keys > 0 and trig_lock_param and trig_lock_param.id then
      local song_pattern = program.get().selected_song_pattern
      for _, keys in ipairs(pressed_keys) do
  
        local s = fn.calc_grid_count(keys[1], keys[2])
        
        local value = get_value_using_handler_param(
          channel,
          dial_index, 
          p,
          param_id,
          p_value,
          d
        )
  
        controls.m_params[dial_index]:set_value(value)
  
        recorder.add_trig_lock_event_portion(channel.number, s, {
          song_pattern = song_pattern,
          data = {
            parameter = dial_index,
            step = s,
            value = value
          }
        })
      end
    elseif p_value and trig_lock_param and trig_lock_param.id then
  
  
      local quant = old_quantum
      if p.controlspec and p.controlspec.quantum then
        quant = p.controlspec.quantum
      end
    
      if (norns_param_state_handler.get_original_param_state(channel.number, dial_index).value) then
        local original_val = norns_param_state_handler.get_original_param_state(channel.number, dial_index).value      
        
        local new_val = get_value_using_handler_param(
          channel,
          dial_index, 
          p,
          param_id,
          original_val,
          d
        )
        
        norns_param_state_handler.set_original_param_state(channel.number, dial_index, new_val)
        
        controls.m_params[dial_index]:set_value(new_val)
      else
  
        if m_clock.channel_is_sliding(channel, dial_index) then
          p:set_raw(p:get_raw() + (d * quant), true)
        else
          p:delta(d)
        end
        if params:get("record") == 2 then
          recorder.set_trig_lock_dirty(channel.number, dial_index, p:get())
        end
      end
  
      public_ui.refresh_trig_lock_value(dial_index)
    end
  
    controls.m_params[dial_index]:temp_display_value()
    if p.controlspec and p.controlspec.quantum then
      p.controlspec.quantum = old_quantum
    end
  end
  
  -- Encoder and key handling

  function controller.set_device_map_selector(selector)
    controls.device_map_vertical_scroll_selector = selector
  end

  function controller.refresh_device_selector()
    refreshers.refresh_device_selector(controls.device_map_vertical_scroll_selector, controls.param_select_vertical_scroll_selector)
  end

  function controller.refresh_trig_lock_value(index)
    refreshers.refresh_trig_lock_value(index, controls.m_params)
  end

  function controller.refresh_trig_lock_values()
    for index = 1, 10 do public_ui.refresh_trig_lock_value(index) end
  end

  function controller.refresh_trig_locks()
    refreshers.refresh_trig_locks(controls.m_params)
  end

  function controller.refresh_param_list()
    controls.param_select_vertical_scroll_selector:set_items(device_map.get_available_params_for_channel(program.get().selected_channel, controls.dials:get_selected_index()))
  end

  return controller
end

return channel_edit_parameters

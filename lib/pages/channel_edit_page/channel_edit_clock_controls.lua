local channel_edit_clock_controls = {}

function channel_edit_clock_controls.new(controls, public_ui, refreshers)
  local controller = {}

  function controller.get_swing_shuffle_type_selector_value()
    return controls.swing_shuffle_type_selector:get_selected().value - 1
  end

  function controller.get_shuffle_feel_selector_value()
    return controls.shuffle_feel_selector:get_selected().value - 1
  end

  function controller.get_shuffle_basis_selector_value()
    return controls.shuffle_basis_selector:get_selected().value - 1
  end

  function controller.set_swing_shuffle_type_selector_value(value)
    controls.swing_shuffle_type_selector:set_selected_value(value + 1)
  end

  function controller.set_shuffle_feel_selector_value(value)
    controls.shuffle_feel_selector:set_selected_value(value + 1)
  end

  function controller.set_shuffle_basis_selector_value(value)
    controls.shuffle_basis_selector:set_selected_value(value + 1)
  end

  function controller.draw()
    controls.swing_shuffle_type_selector:draw()

    local value = public_ui.get_swing_shuffle_type_selector_value()
    if value == 0 then
      value = params:get("global_swing_shuffle_type")
    end

    if value == 1 then
      controls.swing_selector:draw()
    elseif value == 2 then
      controls.shuffle_feel_selector:draw()
      controls.shuffle_basis_selector:draw()
      controls.shuffle_amount_selector:draw()
    end

    controls.clock_mod_list_selector:draw()
  end

  function controller.initialize_clock_mod_list()
    controls.clock_mod_list_selector:set_list(m_clock.get_clock_divisions())
  end

  function controller.initialize_values()
    controls.clock_mod_list_selector:set_selected_value(13)
    controls.clock_mod_list_selector:select()
    controls.swing_selector:set_value(0)

    public_ui.set_swing_shuffle_type_selector_value(params:get("global_swing_shuffle_type"))
    controls.swing_selector:set_value(params:get("global_swing"))
    public_ui.set_shuffle_feel_selector_value(params:get("global_shuffle_feel"))
    public_ui.set_shuffle_basis_selector_value(params:get("global_shuffle_basis"))
    controls.shuffle_amount_selector:set_value(params:get("global_shuffle_amount"))
  end

  function controller.update_swing_shuffle_type()
    local channel = program.get_selected_channel()
    local value = public_ui.get_swing_shuffle_type_selector_value()
    channel.swing_shuffle_type = value

    if value == 0 or nil then
      value = program.get_effective_swing_shuffle_type(channel)
    end

    if m_clock.is_playing() then
      step.queue_for_pattern_change(function()
        local c = channel.number
        local val = value
        m_clock.set_swing_shuffle_type(c, val)
      end)
    else
      m_clock.set_swing_shuffle_type(channel.number, value)
    end
  end

  function controller.align_global_and_local_swing_shuffle_type_values(c)
    local channel = program.get_channel(program.get().selected_song_pattern, c)
    m_clock.set_swing_shuffle_type(channel.number, program.get_effective_swing_shuffle_type(channel))
  end

  function controller.update_swing()
    local channel = program.get_selected_channel()
    local value = controls.swing_selector:get_value()
    channel.swing = value
    if value == -51 or nil then
      value = program.get_effective_swing(channel)
    end

    if m_clock.is_playing() then
      step.queue_for_pattern_change(function()
        local c = channel.number
        local val = value
        m_clock.set_channel_swing(c, val)
      end)
    else
      m_clock.set_channel_swing(channel.number, value)
    end
  end

  function controller.align_global_and_local_swing_values(c)
    local channel = program.get_channel(program.get().selected_song_pattern, c)
    m_clock.set_channel_swing(channel.number, program.get_effective_swing(channel))
  end

  function controller.update_shuffle_feel()
    local channel = program.get_selected_channel()
    local shuffle_feel = public_ui.get_shuffle_feel_selector_value()
    channel.shuffle_feel = shuffle_feel
    if shuffle_feel == 0 or nil then
      shuffle_feel = program.get_effective_shuffle_feel(channel)
    end

    if m_clock.is_playing() then
      step.queue_for_pattern_change(function()
        local c = channel.number
        local sf = shuffle_feel
        m_clock.set_channel_shuffle_feel(c, sf)
      end)
    else
      m_clock.set_channel_shuffle_feel(channel.number, shuffle_feel)
    end
  end

  function controller.align_global_and_local_shuffle_feel_values(c)
    local channel = program.get_channel(program.get().selected_song_pattern, c)
    m_clock.set_channel_shuffle_feel(channel.number, program.get_effective_shuffle_feel(channel))
  end

  function controller.update_shuffle_basis()
    local channel = program.get_selected_channel()
    local shuffle_basis = public_ui.get_shuffle_basis_selector_value()
    channel.shuffle_basis = shuffle_basis

    if shuffle_basis == 0 or nil then
      shuffle_basis = program.get_effective_shuffle_basis(channel)
    end

    if m_clock.is_playing() then
      step.queue_for_pattern_change(function()
        local c = channel.number
        local sb = shuffle_basis
        m_clock.set_channel_shuffle_basis(c, sb)
      end)
    else
      m_clock.set_channel_shuffle_basis(channel.number, shuffle_basis)
    end
  end

  function controller.align_global_and_local_shuffle_basis_values(c)
    local channel = program.get_channel(program.get().selected_song_pattern, c)
    m_clock.set_channel_shuffle_basis(channel.number, program.get_effective_shuffle_basis(channel))
  end

  function controller.update_shuffle_amount()
    local channel = program.get_selected_channel()
    local shuffle_amount = controls.shuffle_amount_selector:get_value()
    channel.shuffle_amount = shuffle_amount

    if shuffle_amount == 0 or nil then
      shuffle_amount = program.get_effective_shuffle_amount(channel)
    end

    if m_clock.is_playing() then
      step.queue_for_pattern_change(function()
        local c = channel.number
        local sa = shuffle_amount
        m_clock.set_channel_shuffle_amount(c, sa)
      end)
    else
      m_clock.set_channel_shuffle_amount(channel.number, shuffle_amount)
    end
  end

  function controller.align_global_and_local_shuffle_amount_values(c)
    local channel = program.get_channel(program.get().selected_song_pattern, c)
    m_clock.set_channel_shuffle_amount(channel.number, program.get_effective_shuffle_amount(channel))
  end

  function controller.update_clock_mods()
    local channel = program.get_selected_channel()
    local clock_mods = controls.clock_mod_list_selector:get_selected()
    channel.clock_mods = clock_mods

    if m_clock.is_playing() then
      step.queue_for_pattern_change(function()
        local c = channel.number
        local div = m_clock.calculate_divisor(clock_mods)
        m_clock.set_channel_division(c, div)
      end)
    else
      m_clock.set_channel_division(channel.number, m_clock.calculate_divisor(clock_mods))
    end
  end

  function controller.refresh_clock_mods()
    refreshers.refresh_clock_mods(controls.clock_mod_list_selector, controls.swing_selector)
  end

  function controller.refresh_swing()
    refreshers.refresh_swing(controls.swing_selector)
  end

  function controller.refresh_swing_shuffle_type()
    refreshers.refresh_swing_shuffle_type(controls.swing_shuffle_type_selector)
  end

  function controller.refresh_shuffle_feel()
    refreshers.refresh_shuffle_feel(controls.shuffle_feel_selector)
  end

  function controller.refresh_shuffle_basis()
    refreshers.refresh_shuffle_basis(controls.shuffle_basis_selector)
  end

  function controller.refresh_shuffle_amount()
    refreshers.refresh_shuffle_amount(controls.shuffle_amount_selector)
  end

  function controller.handle_increment()
    if controls.swing_shuffle_type_selector:is_selected() then
      controls.swing_shuffle_type_selector:increment()
      save_confirm.set_save(public_ui.update_swing_shuffle_type)
      save_confirm.set_save(public_ui.update_shuffle_feel)
      save_confirm.set_save(public_ui.update_shuffle_basis)
      save_confirm.set_save(public_ui.update_shuffle_amount)
      save_confirm.set_save(public_ui.update_swing)
      save_confirm.set_cancel(public_ui.refresh_swing_shuffle_type)
      save_confirm.set_cancel(public_ui.refresh_swing)
      save_confirm.set_cancel(public_ui.refresh_shuffle_feel)
      save_confirm.set_cancel(public_ui.refresh_shuffle_basis)
      save_confirm.set_cancel(public_ui.refresh_shuffle_amount)

      fn.dirty_screen(true)
    elseif controls.swing_selector:is_selected() then
      controls.swing_selector:increment()
      save_confirm.set_save(public_ui.update_swing)
      save_confirm.set_cancel(public_ui.refresh_swing)
    elseif controls.shuffle_feel_selector:is_selected() then
      controls.shuffle_feel_selector:increment()
      save_confirm.set_save(public_ui.update_shuffle_feel)
      save_confirm.set_cancel(public_ui.refresh_shuffle_feel)
    elseif controls.shuffle_basis_selector:is_selected() then
      controls.shuffle_basis_selector:increment()
      save_confirm.set_save(public_ui.update_shuffle_basis)
      save_confirm.set_cancel(public_ui.refresh_shuffle_basis)
    elseif controls.shuffle_amount_selector:is_selected() then
      controls.shuffle_amount_selector:increment()
      save_confirm.set_save(public_ui.update_shuffle_amount)
      save_confirm.set_cancel(public_ui.refresh_shuffle_amount)
    elseif controls.clock_mod_list_selector:is_selected() then
      controls.clock_mod_list_selector:decrement()
      save_confirm.set_save(public_ui.update_clock_mods)
      save_confirm.set_cancel(public_ui.refresh_clock_mods)
    end
  end

  function controller.handle_decrement()
    if controls.swing_shuffle_type_selector:is_selected() then
      controls.swing_shuffle_type_selector:decrement()
      save_confirm.set_save(public_ui.update_swing_shuffle_type)
      save_confirm.set_cancel(public_ui.refresh_swing_shuffle_type)
    elseif controls.swing_selector:is_selected() then
      controls.swing_selector:decrement()
      save_confirm.set_save(public_ui.update_swing)
      save_confirm.set_cancel(public_ui.refresh_swing)
    elseif controls.shuffle_feel_selector:is_selected() then
      controls.shuffle_feel_selector:decrement()
      save_confirm.set_save(public_ui.update_shuffle_feel)
      save_confirm.set_cancel(public_ui.refresh_shuffle_feel)
    elseif controls.shuffle_basis_selector:is_selected() then
      controls.shuffle_basis_selector:decrement()
      save_confirm.set_save(public_ui.update_shuffle_basis)
      save_confirm.set_cancel(public_ui.refresh_shuffle_basis)
    elseif controls.shuffle_amount_selector:is_selected() then
      controls.shuffle_amount_selector:decrement()
      save_confirm.set_save(public_ui.update_shuffle_amount)
      save_confirm.set_cancel(public_ui.refresh_shuffle_amount)
    elseif controls.clock_mod_list_selector:is_selected() then
      controls.clock_mod_list_selector:increment()
      save_confirm.set_save(public_ui.update_clock_mods)
      save_confirm.set_cancel(public_ui.refresh_clock_mods)
    end
  end

  function controller.navigate(direction, get_swing_shuffle_type_selector_value)
    local selectors = {
      controls.clock_mod_list_selector,
      controls.swing_shuffle_type_selector
    }
    local value = get_swing_shuffle_type_selector_value()
    if value == 0 then
      value = params:get("global_swing_shuffle_type")
    end

    if value == 1 then
      table.insert(selectors, controls.swing_selector)
    elseif value == 2 then
      table.insert(selectors, controls.shuffle_feel_selector)
      table.insert(selectors, controls.shuffle_basis_selector)
      table.insert(selectors, controls.shuffle_amount_selector)
    end

    local current_index = nil
    for index, selector in ipairs(selectors) do
      if selector:is_selected() then
        current_index = index
        break
      end
    end

    if current_index then
      local next_index = current_index + direction
      if selectors[next_index] then
        selectors[current_index]:deselect()
        selectors[next_index]:select()
      end
    elseif direction > 0 then
      selectors[1]:select()
    else
      selectors[#selectors]:select()
    end
  end

  return controller
end

return channel_edit_clock_controls

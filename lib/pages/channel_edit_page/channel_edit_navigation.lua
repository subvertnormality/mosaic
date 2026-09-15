local channel_edit_navigation = {}

function channel_edit_navigation.new(controls, public_ui, handlers)
  local controller = {}
  local pages = {
    channel_pages = controls.channel_pages,
    channel_page_to_index = controls.channel_page_to_index
  }
  local selectors = {
    mask_selectors = controls.mask_selectors,
    midi_device_vertical_scroll_selector = controls.midi_device_vertical_scroll_selector,
    midi_channel_vertical_scroll_selector = controls.midi_channel_vertical_scroll_selector,
    device_map_vertical_scroll_selector = controls.device_map_vertical_scroll_selector
  }

  function controller.set_device_map_selector(selector)
    selectors.device_map_vertical_scroll_selector = selector
  end

  function controller.set_trig_lock_page(page)
    controls.trig_lock_page = page
  end

  function controller.enc(n, d)
    if n == 3 then
      for _ = 1, math.abs(d) do
        if controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Masks"] then
          public_ui.handle_mask_page_change(d)
        elseif controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Memory"] then
          public_ui.handle_memory_page_change(d)
        end

        if d > 0 then
          if controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Clock Mods"] then
            public_ui.handle_clock_mods_page_increment()
          elseif controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Midi Config"] then
            public_ui.handle_midi_config_page_increment()
          elseif controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Trig Locks"] then
            handlers.handle_trig_locks_page_change(d, controls.parameter_controller)
          end
        else
          if controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Clock Mods"] then
            public_ui.handle_clock_mods_page_decrement()
          elseif controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Midi Config"] then
            public_ui.handle_midi_config_page_decrement()
          elseif controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Trig Locks"] then
            handlers.handle_trig_locks_page_change(d, controls.parameter_controller)
          end
        end
      end
    elseif n == 2 then
      for _ = 1, math.abs(d) do
        if d > 0 then
          handlers.handle_encoder_two_positive(
            pages,
            selectors,
            controls.parameter_controller,
            controls.clock_controls_controller
          )
        else
          handlers.handle_encoder_two_negative(
            pages,
            selectors,
            controls.parameter_controller,
            controls.clock_controls_controller
          )
        end
      end
    elseif n == 1 then
      for _ = 1, math.abs(d) do
        if d > 0 then
          public_ui.handle_encoder_one_positive()
        else
          public_ui.handle_encoder_one_negative()
        end
      end
    end
  end

  function controller.key(n, z)
    if n == 2 and z == 1 then
      public_ui.handle_key_two_pressed()
    elseif n == 3 and z == 1 then
      public_ui.handle_key_three_pressed()
    end
  end

  function controller.handle_encoder_one_positive()
    public_ui.select_channel_page_by_index((controls.channel_pages:get_selected_page() or 1) + 1)
    fn.dirty_screen(true)
    save_confirm.cancel()
  end

  function controller.handle_encoder_one_negative()
    public_ui.select_channel_page_by_index((controls.channel_pages:get_selected_page() or 1) - 1)
    fn.dirty_screen(true)
    save_confirm.cancel()
  end

  function controller.handle_key_two_pressed()
    local pressed_keys = m_grid.get_pressed_keys()
    if #pressed_keys > 0 then
      local selected = program.get()
      local song_pattern = selected.selected_song_pattern or 1
      if not selected.selected_song_pattern then selected.selected_song_pattern = song_pattern end
      local channel = program.get_channel(song_pattern, selected.selected_channel)
      for _, keys in ipairs(pressed_keys) do
        local s = fn.calc_grid_count(keys[1], keys[2])
        if controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Masks"] then
          program.clear_masks_for_step_for_channel(channel, s)
          tooltip:show("Masks for step " .. s .. " cleared")
          public_ui.refresh_masks()
          pattern.update_working_pattern(channel.number, program.get_song_pattern(song_pattern))
        end
        if controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Trig Locks"] then
          program.clear_trig_locks_for_step_for_channel(channel, s)
          tooltip:show("Trig locks for step " .. s .. " cleared")
          public_ui.refresh_trig_locks()
        end
      end
    else
      if controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Trig Locks"] then
        if is_key1_down then
          program.clear_trig_locks_for_channel(program.get_selected_channel())
          tooltip:show("Trig locks for ch " .. program.get_selected_channel().number .. " cleared")
          public_ui.refresh_trig_locks()
        else
          controls.parameter_controller.toggle_assignment_subpage()
        end
      elseif controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Masks"] then
        if is_key1_down then
          program.clear_masks_for_channel(program.get_selected_channel())
          tooltip:show("Masks for ch " .. program.get_selected_channel().number .. " cleared")
          public_ui.refresh_masks()
          pattern.update_working_pattern(program.get_selected_channel().number, program.get_selected_song_pattern())
        end
      elseif controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Memory"] then
        if is_key1_down then
          memory.undo_all(program.get_selected_channel().number)
          memory.clear(program.get_selected_channel().number)
          tooltip:show("Memory undone and forgotten")
        else
          memory.undo_all(program.get_selected_channel().number)
          tooltip:show("Ch. " .. program.get_selected_channel().number .. " memory undone")
        end
        public_ui.refresh_memory()
        pattern.update_working_pattern(program.get_selected_channel().number, program.get_selected_song_pattern())
      end
      save_confirm.cancel()
    end
  end

  function controller.handle_key_three_pressed()
    local pressed_keys = m_grid.get_pressed_keys()
    if controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Memory"] then
      if is_key1_down then
        memory.redo_all(program.get_selected_channel().number)
        memory.clear(program.get_selected_channel().number)
        tooltip:show("Memory applied and forgotten")
      else
        memory.redo_all(program.get_selected_channel().number)
        tooltip:show("Ch. " .. program.get_selected_channel().number .. " memory applied")
      end
      public_ui.refresh_memory()
      pattern.update_working_pattern(program.get_selected_channel().number, program.get_selected_song_pattern())
    elseif controls.channel_pages:get_selected_page() == controls.channel_page_to_index["Trig Locks"] and
      not controls.trig_lock_page:is_sub_page_enabled() then
      local pressed_keys = m_grid.get_pressed_keys()
      if #pressed_keys > 0 then
        for _, keys in ipairs(pressed_keys) do
          local step = fn.calc_grid_count(keys[1], keys[2])
          program.toggle_step_param_slide(program.get_selected_channel(), step, controls.dials:get_selected_index())
        end
      elseif not is_key1_down then
        program.toggle_channel_param_slide(program.get_selected_channel(), controls.dials:get_selected_index())
      end
      fn.dirty_screen(true)
    elseif #pressed_keys < 1 then
      save_confirm.confirm()
    end
  end

  function controller.select_page(page)
    controls.channel_pages:select_page(page)
    fn.dirty_screen(true)
  end

  function controller.get_selected_page()
    return controls.channel_pages:get_selected_page()
  end

  function controller.select_mask_page()
    public_ui.refresh_masks()
    controls.channel_pages:select_page(controls.channel_page_to_index["Masks"])
    fn.dirty_screen(true)
  end

  function controller.select_trig_page()
    public_ui.refresh_trig_locks()
    controls.channel_pages:select_page(controls.channel_page_to_index["Trig Locks"])
  end

  function controller.select_memory_page()
    public_ui.refresh_memory()
    controls.channel_pages:select_page(controls.channel_page_to_index["Memory"])
  end

  function controller.select_clock_mods_page()
    public_ui.refresh_clock_mods()
    public_ui.refresh_swing()
    public_ui.refresh_swing_shuffle_type()
    public_ui.refresh_shuffle_feel()
    public_ui.refresh_shuffle_basis()
    public_ui.refresh_shuffle_amount()
    controls.channel_pages:select_page(controls.channel_page_to_index["Clock Mods"])
  end

  function controller.select_midi_config_page()
    public_ui.refresh_channel_config()
    controls.channel_pages:select_page(controls.channel_page_to_index["Midi Config"])
  end

  function controller.select_note_dashboard_page()
    controls.channel_pages:select_page(controls.channel_page_to_index["Note Dashboard"])
  end

  function controller.select_scales_quantizer_page()
    public_ui.refresh_quantiser()
    public_ui.refresh_romans()
    scales_pages:select_page(scales_page_to_index["Quantizer"])
  end

  function controller.select_channel_page_by_index(index)
    if index == 1 then
      public_ui.select_mask_page()
    elseif index == 2 then
      public_ui.select_trig_page()
    elseif index == 3 then
      public_ui.select_memory_page()
    elseif index == 4 then
      public_ui.select_clock_mods_page()
    elseif index == 5 then
      public_ui.select_midi_config_page()
    elseif index == 6 then
      public_ui.select_note_dashboard_page()
    end
  end

  function controller.refresh()
    public_ui.select_channel_page_by_index(controls.channel_pages:get_selected_page() or 1)
  end

  return controller
end

return channel_edit_navigation

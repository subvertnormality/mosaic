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
  local feature_editors = controls.feature_editors or {}
  local last_legacy_page = controls.channel_page_to_index["Masks"]

  local function remember_legacy_page(page)
    -- Held-step gestures belong to the two editable legacy workspaces. Page
    -- traversal through Memory/Clock/Device/Dashboard must not replace that
    -- return target merely because E1 passed over it on the way to a feature.
    if page==controls.channel_page_to_index["Masks"]or
      page==controls.channel_page_to_index["Trig Locks"]then
      last_legacy_page = page
    end
  end

  local function cancel_feature_drafts_for_legacy_workspace()
    for _, feature in pairs(feature_editors) do
      if feature.cancel_for_grid then feature:cancel_for_grid() end
    end
  end

  function controller.set_device_map_selector(selector)
    selectors.device_map_vertical_scroll_selector = selector
  end

  function controller.set_trig_lock_page(page)
    controls.trig_lock_page = page
  end

  function controller.enc(n, d)
    local selected_page = controls.channel_pages:get_selected_page()
    local feature = selected_page == controls.channel_page_to_index["Merge Shape"] and feature_editors.merge or
      selected_page == controls.channel_page_to_index["Harmony"] and feature_editors.harmony
    if feature and (n == 2 or n == 3) then feature:enc(n, d); return end
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
    local selected_page = controls.channel_pages:get_selected_page()
    local feature = selected_page == controls.channel_page_to_index["Merge Shape"] and feature_editors.merge or
      selected_page == controls.channel_page_to_index["Harmony"] and feature_editors.harmony
    -- A grid step held before K2/K3 owns the gesture.  Restore its last legacy
    -- workspace before dispatch so feature Apply/Cancel cannot steal the key.
    if feature and z==1 and(n==2 or n==3)and #m_grid.get_pressed_keys()>0 then
      controller.leave_feature_editor_for_grid()
      feature=nil
    end
    if feature and z == 1 and (n == 2 or n == 3) then feature:key(n); return end
    if n == 2 and z == 1 then
      public_ui.handle_key_two_pressed()
    elseif n == 3 and z == 1 then
      public_ui.handle_key_three_pressed()
    end
  end

  function controller.handle_encoder_one_positive()
    local selected_page = controls.channel_pages:get_selected_page()
    local feature = selected_page == controls.channel_page_to_index["Merge Shape"] and feature_editors.merge or
      selected_page == controls.channel_page_to_index["Harmony"] and feature_editors.harmony
    if feature and feature:encoder_one() then fn.dirty_screen(true); return end
    public_ui.select_channel_page_by_index((controls.channel_pages:get_selected_page() or 1) + 1)
    fn.dirty_screen(true)
    save_confirm.cancel()
  end

  function controller.handle_encoder_one_negative()
    local selected_page = controls.channel_pages:get_selected_page()
    local feature = selected_page == controls.channel_page_to_index["Merge Shape"] and feature_editors.merge or
      selected_page == controls.channel_page_to_index["Harmony"] and feature_editors.harmony
    if feature and feature:encoder_one() then fn.dirty_screen(true); return end
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
    remember_legacy_page(page)
    controls.channel_pages:select_page(page)
    fn.dirty_screen(true)
  end

  function controller.get_selected_page()
    return controls.channel_pages:get_selected_page()
  end

  function controller.select_mask_page()
    cancel_feature_drafts_for_legacy_workspace()
    public_ui.refresh_masks()
    controls.channel_pages:select_page(controls.channel_page_to_index["Masks"])
    remember_legacy_page(controls.channel_page_to_index["Masks"])
    fn.dirty_screen(true)
  end

  function controller.select_trig_page()
    cancel_feature_drafts_for_legacy_workspace()
    public_ui.refresh_trig_locks()
    controls.channel_pages:select_page(controls.channel_page_to_index["Trig Locks"])
    remember_legacy_page(controls.channel_page_to_index["Trig Locks"])
  end

  function controller.select_memory_page()
    cancel_feature_drafts_for_legacy_workspace()
    public_ui.refresh_memory()
    controls.channel_pages:select_page(controls.channel_page_to_index["Memory"])
    remember_legacy_page(controls.channel_page_to_index["Memory"])
  end

  function controller.select_clock_mods_page()
    cancel_feature_drafts_for_legacy_workspace()
    public_ui.refresh_clock_mods()
    public_ui.refresh_swing()
    public_ui.refresh_swing_shuffle_type()
    public_ui.refresh_shuffle_feel()
    public_ui.refresh_shuffle_basis()
    public_ui.refresh_shuffle_amount()
    controls.channel_pages:select_page(controls.channel_page_to_index["Clock Mods"])
    remember_legacy_page(controls.channel_page_to_index["Clock Mods"])
  end

  function controller.select_midi_config_page()
    cancel_feature_drafts_for_legacy_workspace()
    public_ui.refresh_channel_config()
    controls.channel_pages:select_page(controls.channel_page_to_index["Midi Config"])
    remember_legacy_page(controls.channel_page_to_index["Midi Config"])
  end

  function controller.select_note_dashboard_page()
    cancel_feature_drafts_for_legacy_workspace()
    controls.channel_pages:select_page(controls.channel_page_to_index["Note Dashboard"])
    remember_legacy_page(controls.channel_page_to_index["Note Dashboard"])
  end

  function controller.select_merge_shape_page()
    if feature_editors.merge then feature_editors.merge:enter() end
    controls.channel_pages:select_page(controls.channel_page_to_index["Merge Shape"])
  end

  function controller.select_harmony_page()
    if feature_editors.harmony then feature_editors.harmony:enter() end
    controls.channel_pages:select_page(controls.channel_page_to_index["Harmony"])
  end

  function controller.leave_feature_editor_for_grid()
    local page=controls.channel_pages:get_selected_page()
    if page~=controls.channel_page_to_index["Merge Shape"]and page~=controls.channel_page_to_index["Harmony"]then return false end
    cancel_feature_drafts_for_legacy_workspace()
    public_ui.select_channel_page_by_index(last_legacy_page)
    return true
  end

  function controller.show_merge_gesture(label)
    if controls.channel_pages:get_selected_page()~=controls.channel_page_to_index["Merge Shape"]then return false end
    if feature_editors.merge then feature_editors.merge:show_merge_gesture(label);fn.dirty_screen(true);return true end
    return false
  end

  function controller.hide_merge_gesture()
    if feature_editors.merge then feature_editors.merge:hide_merge_gesture();fn.dirty_screen(true)end
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
    elseif index == 7 then
      public_ui.select_merge_shape_page()
    elseif index == 8 then
      public_ui.select_harmony_page()
    end
  end

  function controller.refresh()
    public_ui.select_channel_page_by_index(controls.channel_pages:get_selected_page() or 1)
  end

  return controller
end

return channel_edit_navigation

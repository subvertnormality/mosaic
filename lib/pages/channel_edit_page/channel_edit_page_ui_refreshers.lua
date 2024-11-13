-- channel_edit_page_ui_refreshers.lua
local channel_edit_page_ui_refreshers = {}
local quantiser = include("lib/quantiser")
local divisions = include("lib/divisions")

local throttle_time = 0.01

channel_edit_page_ui_refreshers.refresh_masks = scheduler.debounce(function(note_selectors)
  local pressed_keys = mosaic_grid.get_pressed_keys()
  local channel = program.get_selected_channel()

  -- Cache frequently accessed selectors
  local note_selector = note_selectors.note
  local velocity_selector = note_selectors.velocity
  local length_selector = note_selectors.length
  local trig_selector = note_selectors.trig
  local chord_selectors = note_selectors.chords

  -- Cache channel properties
  local note_mask = channel.note_mask or -1
  local velocity_mask = channel.velocity_mask or -1
  local length_mask_index = divisions.note_division_indexes[channel.length_mask] or 0
  local trig_mask = channel.trig_mask or -1
  local chord_masks = {
    channel.chord_one_mask or 0,
    channel.chord_two_mask or 0,
    channel.chord_three_mask or 0,
    channel.chord_four_mask or 0
  }

  if #pressed_keys > 0 and pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
    -- Cache step masks for efficiency
    local step_note_masks = channel.step_note_masks
    local step_velocity_masks = channel.step_velocity_masks
    local step_length_masks = channel.step_length_masks
    local step_trig_masks = channel.step_trig_masks
    local step_chord_masks = channel.step_chord_masks

    for _, keys in ipairs(pressed_keys) do
      local s = fn.calc_grid_count(keys[1], keys[2])

      -- Set note selector values using cached masks
      note_selector:set_value(step_note_masks[s] or note_mask)
      velocity_selector:set_value(step_velocity_masks[s] or velocity_mask)
      length_selector:set_value(divisions.note_division_indexes[step_length_masks[s]] or length_mask_index)
      trig_selector:set_value(step_trig_masks[s] or trig_mask)

      -- Get step chord masks or default chord masks
      local step_chords = step_chord_masks[s] or chord_masks

      for i, chord_selector in ipairs(chord_selectors) do
        chord_selector:set_value(step_chords[i] or chord_masks[i])
      end
    end
  else
    -- Set selectors to channel-level masks
    note_selector:set_value(note_mask)
    velocity_selector:set_value(velocity_mask)
    length_selector:set_value(length_mask_index)
    trig_selector:set_value(trig_mask)

    for i, chord_selector in ipairs(chord_selectors) do
      chord_selector:set_value(chord_masks[i])
    end
  end
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_clock_mods = scheduler.debounce(function(clock_mod_list_selector, clock_swing_value_selector)
  local channel = program.get_selected_channel()
  local clock_mods = channel.clock_mods
  local divisions = fn.filter_by_type(clock_controller.get_clock_divisions(), clock_mods.type)
  local i = fn.find_index_in_table_by_value(divisions, clock_mods.value)
  if clock_mods.type == "clock_division" then
    i = i + 12
  end
  clock_mod_list_selector:set_selected_value(i)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_swing = scheduler.debounce(function(clock_swing_value_selector)
  local channel = program.get_selected_channel()
  local value = channel.swing 
  if value == nil then
    value = -51
  end
  clock_swing_value_selector:set_value(value)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_swing_shuffle_type = scheduler.debounce(function(swing_shuffle_type_selector)
  local channel = program.get_selected_channel()
  local value = channel.swing_shuffle_type or 1
  swing_shuffle_type_selector:set_selected_value(value)
end, throttle_time)


channel_edit_page_ui_refreshers.refresh_shuffle_feel = scheduler.debounce(function(shuffle_feel_selector)
  local channel = program.get_selected_channel()
  local value = channel.shuffle_feel or 1
  shuffle_feel_selector:set_selected_value(value)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_shuffle_basis = scheduler.debounce(function(shuffle_basis_selector)
  local channel = program.get_selected_channel()
  local value = channel.shuffle_basis or 1
  shuffle_basis_selector:set_selected_value(value)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_shuffle_amount = scheduler.debounce(function(shuffle_amount_selector)
  local channel = program.get_selected_channel()
  local value = channel.shuffle_amount or 0
  shuffle_amount_selector:set_value(value)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_device_selector = scheduler.debounce(function(device_map_vertical_scroll_selector, param_select_vertical_scroll_selector)
  local channel = program.get_selected_channel()
  local device = device_map.get_device(program.get().devices[channel.number].device_map)
  local device_params = device_map.get_params(program.get().devices[channel.number].device_map)
  param_select_vertical_scroll_selector:set_items(device_params)
  param_select_vertical_scroll_selector:set_meta_item(device)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_trig_lock_value = scheduler.debounce(function(i, m_params)
  local channel = program.get_selected_channel()
  local param_id = channel.trig_lock_params[i].param_id

  if not param_id then
    m_params[i]:set_value(-1)
    return
  end

  local val = fn.clean_number(params:get(param_id))

  if (norns_param_state_handler.get_original_param_state(channel.number, i).value) then
    val = norns_param_state_handler.get_original_param_state(channel.number, i).value
  end

  m_params[i]:set_value(val)

end, throttle_time)


channel_edit_page_ui_refreshers.refresh_trig_locks = scheduler.debounce(function(m_params)
  local channel = program.get_selected_channel()
  local pressed_keys = mosaic_grid.get_pressed_keys()
  local current_step = program.get_current_step_for_channel(channel.number)

  -- Process all updates in a single batch
  local updates = {}
  
  for i = 1, 10 do
    -- Gather all the updates first
    local m_param = m_params[i]
    local trig_lock_param = channel.trig_lock_params[i]
    if trig_lock_param and trig_lock_param.param_id then
      local param_id = trig_lock_param.param_id
      local param_value = params:get(param_id) or trig_lock_param.off_value
      local default_param = norns_param_state_handler.get_original_param_state(channel.number, i).value
      
      -- Store the update info
      updates[i] = {
        param = m_param,
        value = default_param or param_value,
        trig_lock_param = trig_lock_param
      }
      
      -- Handle pressed keys
      if #pressed_keys > 0 then
        local pressed_key = pressed_keys[1]
        if pressed_key[2] > 3 and pressed_key[2] < 8 then
          local grid_count = fn.calc_grid_count(pressed_key[1], pressed_key[2])
          local step_trig_lock = program.get_step_param_trig_lock(channel, grid_count, i)
          updates[i].value = step_trig_lock or params:get(param_id)
        end
      end
    else
      updates[i] = {
        param = m_param,
        value = -1,
        trig_lock_param = {
          name = "",
          short_descriptor_1 = "None",
          short_descriptor_2 = "",
          off_value = -1,
          value = -1
        }
      }
    end
  end
  
  -- Apply all updates in a single pass
  for i, update in pairs(updates) do
    local m_param = update.param
    local u_trig_lock_param = update.trig_lock_param
    
    m_param:set_name(u_trig_lock_param.name)
    m_param:set_top_label(u_trig_lock_param.short_descriptor_1)
    m_param:set_bottom_label(u_trig_lock_param.short_descriptor_2)
    m_param:set_off_value(u_trig_lock_param.off_value)
    m_param:set_min_value(u_trig_lock_param.nrpn_min_value or u_trig_lock_param.cc_min_value)
    m_param:set_max_value(u_trig_lock_param.nrpn_max_value or u_trig_lock_param.cc_max_value)
    m_param:set_ui_labels(u_trig_lock_param.ui_labels)
    m_param:set_value(update.value)
  end

  -- Request a single UI refresh after all updates are complete
  fn.dirty_screen(true)
end, throttle_time)

return channel_edit_page_ui_refreshers

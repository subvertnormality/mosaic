-- channel_edit_page_ui_refreshers.lua
local channel_edit_page_ui_refreshers = {}
local quantiser = include("lib/quantiser")
local divisions = include("lib/divisions")

local throttle_time = 0.01

channel_edit_page_ui_refreshers.refresh_masks = ui_scheduler.debounce(function(note_selectors)
  local pressed_keys = grid_controller.get_pressed_keys()
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
      local step = fn.calc_grid_count(keys[1], keys[2])

      -- Set note selector values using cached masks
      note_selector:set_value(step_note_masks[step] or note_mask)
      velocity_selector:set_value(step_velocity_masks[step] or velocity_mask)
      length_selector:set_value(divisions.note_division_indexes[step_length_masks[step]] or length_mask_index)
      trig_selector:set_value(step_trig_masks[step] or trig_mask)

      -- Get step chord masks or default chord masks
      local step_chords = step_chord_masks[step] or chord_masks

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

channel_edit_page_ui_refreshers.refresh_clock_mods = ui_scheduler.debounce(function(clock_mod_list_selector, clock_swing_value_selector)
  local channel = program.get_selected_channel()
  local clock_mods = channel.clock_mods
  local divisions = fn.filter_by_type(clock_controller.get_clock_divisions(), clock_mods.type)
  local i = fn.find_index_in_table_by_value(divisions, clock_mods.value)
  if clock_mods.type == "clock_division" then
    i = i + 12
  end
  clock_mod_list_selector:set_selected_value(i)
  if channel.number == 17 then
    clock_mod_list_selector:select()
    clock_swing_value_selector:deselect()
  end
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_swing = ui_scheduler.debounce(function(clock_swing_value_selector)
  local channel = program.get_selected_channel()
  local value = channel.swing 
  if value == nil then
    value = -51
  end
  clock_swing_value_selector:set_value(value)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_swing_shuffle_type = ui_scheduler.debounce(function(swing_shuffle_type_selector)
  local channel = program.get_selected_channel()
  local value = channel.swing_shuffle_type or 1
  swing_shuffle_type_selector:set_selected_value(value)
end, throttle_time)


channel_edit_page_ui_refreshers.refresh_shuffle_feel = ui_scheduler.debounce(function(shuffle_feel_selector)
  local channel = program.get_selected_channel()
  local value = channel.shuffle_feel or 1
  shuffle_feel_selector:set_selected_value(value)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_shuffle_basis = ui_scheduler.debounce(function(shuffle_basis_selector)
  local channel = program.get_selected_channel()
  local value = channel.shuffle_basis or 1
  shuffle_basis_selector:set_selected_value(value)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_shuffle_amount = ui_scheduler.debounce(function(shuffle_amount_selector)
  local channel = program.get_selected_channel()
  local value = channel.shuffle_amount or 0
  shuffle_amount_selector:set_value(value)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_device_selector = ui_scheduler.debounce(function(device_map_vertical_scroll_selector, param_select_vertical_scroll_selector)
  local channel = program.get_selected_channel()
  if channel.number == 17 then return end
  local device = device_map.get_device(program.get().devices[channel.number].device_map)
  local device_params = device_map.get_params(program.get().devices[channel.number].device_map)
  param_select_vertical_scroll_selector:set_items(device_params)
  param_select_vertical_scroll_selector:set_meta_item(device)
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_romans= ui_scheduler.debounce(function(quantizer_vertical_scroll_selector, romans_vertical_scroll_selector)
  local scale = quantizer_vertical_scroll_selector:get_selected_item()
  if scale then
    local number = scale.number
    program.get_selected_sequencer_pattern().active = true
    romans_vertical_scroll_selector:set_items(quantiser.get_scales()[number].romans)
    fn.dirty_screen(true)
  end
end, throttle_time)

channel_edit_page_ui_refreshers.refresh_quantiser= ui_scheduler.debounce(function(quantizer_vertical_scroll_selector, notes_vertical_scroll_selector, romans_vertical_scroll_selector, rotation_vertical_scroll_selector, m_params)
  local channel = program.get_selected_channel()
  local scale = program.get_scale(program.get().selected_scale)
  program.get_selected_sequencer_pattern().active = true
  quantizer_vertical_scroll_selector:set_selected_item(scale.number)
  notes_vertical_scroll_selector:set_selected_item(scale.root_note + 1)
  romans_vertical_scroll_selector:set_selected_item(scale.chord)
  rotation_vertical_scroll_selector:set_selected_item((scale.chord_degree_rotation or 0) + 1)
  channel_edit_page_ui_refreshers.refresh_romans(quantizer_vertical_scroll_selector, romans_vertical_scroll_selector, quantiser, fn)
end, throttle_time)


channel_edit_page_ui_refreshers.refresh_trig_lock_value= ui_scheduler.debounce(function(i, m_params)
  local channel = program.get_selected_channel()
  local param_id = channel.trig_lock_params[i].param_id

  if not param_id then
    m_params[i]:set_value(-1)
    return
  end

  local val = params:get(param_id)

  m_params[i]:set_value(fn.clean_number(val))

end, throttle_time)


function channel_edit_page_ui_refreshers.refresh_trig_lock(i, m_params, channel, pressed_keys, current_step)
  -- Cache m_params[i] to avoid multiple table lookups
  local m_param = m_params[i]

  -- Pass 'channel' to avoid calling 'program.get_selected_channel()' again
  channel_edit_page_ui_refreshers.refresh_trig_lock_value(i, m_params)

  -- Cache 'trig_lock_param' to avoid multiple table accesses
  local trig_lock_param = channel.trig_lock_params[i]

  if trig_lock_param and trig_lock_param.param_id then
    local param_id = trig_lock_param.param_id

    m_param:set_name(trig_lock_param.name)
    m_param:set_top_label(trig_lock_param.short_descriptor_1)
    m_param:set_bottom_label(trig_lock_param.short_descriptor_2)
    m_param:set_off_value(trig_lock_param.off_value)
    m_param:set_min_value(trig_lock_param.nrpn_min_value or trig_lock_param.cc_min_value)
    m_param:set_max_value(trig_lock_param.nrpn_max_value or trig_lock_param.cc_max_value)
    m_param:set_ui_labels(trig_lock_param.ui_labels)

    -- Cache the parameter value
    local param_value = params:get(param_id) or trig_lock_param.off_value
    m_param:set_value(param_value)

    -- Get the step trigger lock
    local step_trig_lock = program.get_step_param_trig_lock(channel, current_step, i)

    if #pressed_keys > 0 then
      local pressed_key = pressed_keys[1]
      if pressed_key[2] > 3 and pressed_key[2] < 8 then
        local grid_count = fn.calc_grid_count(pressed_key[1], pressed_key[2])
        step_trig_lock = program.get_step_param_trig_lock(channel, grid_count, i)
        local default_param = params:get(param_id)
        m_param:set_value(step_trig_lock or default_param)
      end
    end
  else
    m_param:set_name("")
    m_param:set_top_label("None")
    m_param:set_bottom_label("")
  end
end


channel_edit_page_ui_refreshers.refresh_trig_locks = ui_scheduler.debounce(function(m_params)
  
  local channel = program.get_selected_channel()
  local pressed_keys = grid_controller.get_pressed_keys()
  local current_step = program.get_current_step_for_channel(channel.number)

  for i = 1, 10 do
    channel_edit_page_ui_refreshers.refresh_trig_lock(i, m_params, channel, pressed_keys, current_step)
    continue.yield()
  end
end, throttle_time)

return channel_edit_page_ui_refreshers

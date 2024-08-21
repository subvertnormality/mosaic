-- channel_edit_page_ui_refreshers.lua
local channel_edit_page_ui_refreshers = {}
local quantiser = include("lib/quantiser")
local fn = include("lib/functions")
local divisions = include("lib/divisions")

function channel_edit_page_ui_refreshers.refresh_masks(note_selectors)
  local pressed_keys = grid_controller.get_pressed_keys()
  local channel = program.get_selected_channel()
  local values = {
    note = -1, velocity = -1, length = -1, trig = -1,
    chords = {0, 0, 0, 0}
  }

  if #pressed_keys > 0 then
    if pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
      for _, keys in ipairs(pressed_keys) do
        local step = fn.calc_grid_count(keys[1], keys[2])
        note_selectors.note:set_value(channel.step_note_masks[step] or channel.note_mask or -1)
        note_selectors.velocity:set_value(channel.step_velocity_masks[step] or channel.velocity_mask or -1)
        note_selectors.length:set_value(divisions.note_division_indexes[channel.step_length_masks[step]] or divisions.note_division_indexes[channel.length_mask] or 0)
        note_selectors.trig:set_value(channel.step_trig_masks[step] or channel.trig_mask or -1) 
        for i, chord_selector in ipairs(note_selectors.chords) do
          if i == 1 then
            chord_selector:set_value(channel.step_chord_masks[step] and channel.step_chord_masks[step][1] or channel.chord_one_mask or 0)
          elseif i == 2 then
              chord_selector:set_value(channel.step_chord_masks[step] and channel.step_chord_masks[step][2] or channel.chord_two_mask or 0)
          elseif i == 3 then
              chord_selector:set_value(channel.step_chord_masks[step] and channel.step_chord_masks[step][3] or channel.chord_three_mask or 0)
          elseif i == 4 then
              chord_selector:set_value(channel.step_chord_masks[step] and channel.step_chord_masks[step][4] or channel.chord_four_mask or 0)
          end
        end
      end
    end
  else
    note_selectors.note:set_value(channel.note_mask or -1)
    note_selectors.velocity:set_value(channel.velocity_mask or -1)
    note_selectors.length:set_value(divisions.note_division_indexes[channel.length_mask] or 0)
    note_selectors.trig:set_value(channel.trig_mask or -1)
    for i, chord_selector in ipairs(note_selectors.chords) do
      if i == 1 then
          chord_selector:set_value(channel.chord_one_mask or 0)
      elseif i == 2 then
          chord_selector:set_value(channel.chord_two_mask or 0)
      elseif i == 3 then
          chord_selector:set_value(channel.chord_three_mask or 0)
      elseif i == 4 then
          chord_selector:set_value(channel.chord_four_mask or 0)
      end
    end
  end
end

function channel_edit_page_ui_refreshers.refresh_clock_mods(clock_mod_list_selector, clock_swing_value_selector)
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
end

function channel_edit_page_ui_refreshers.refresh_swing(clock_swing_value_selector)
  local channel = program.get_selected_channel()
  clock_swing_value_selector:set_value(channel.swing)
end

function channel_edit_page_ui_refreshers.refresh_device_selector(device_map_vertical_scroll_selector, param_select_vertical_scroll_selector)
  local channel = program.get_selected_channel()
  if channel.number == 17 then return end
  local device = device_map.get_device(program.get().devices[channel.number].device_map)
  local device_params = device_map.get_params(program.get().devices[channel.number].device_map)
  param_select_vertical_scroll_selector:set_items(device_params)
  param_select_vertical_scroll_selector:set_meta_item(device)
end

function channel_edit_page_ui_refreshers.refresh_romans(quantizer_vertical_scroll_selector, romans_vertical_scroll_selector)
  local scale = quantizer_vertical_scroll_selector:get_selected_item()
  if scale then
    local number = scale.number
    program.get_selected_sequencer_pattern().active = true
    romans_vertical_scroll_selector:set_items(quantiser.get_scales()[number].romans)
    fn.dirty_screen(true)
  end
end

function channel_edit_page_ui_refreshers.refresh_quantiser(quantizer_vertical_scroll_selector, notes_vertical_scroll_selector, romans_vertical_scroll_selector, rotation_vertical_scroll_selector, m_params)
  local channel = program.get_selected_channel()
  local scale = program.get_scale(program.get().selected_scale)
  program.get_selected_sequencer_pattern().active = true
  quantizer_vertical_scroll_selector:set_selected_item(scale.number)
  notes_vertical_scroll_selector:set_selected_item(scale.root_note + 1)
  romans_vertical_scroll_selector:set_selected_item(scale.chord)
  rotation_vertical_scroll_selector:set_selected_item((scale.chord_degree_rotation or 0) + 1)
  channel_edit_page_ui_refreshers.refresh_romans(quantizer_vertical_scroll_selector, romans_vertical_scroll_selector, quantiser, fn)
end

function channel_edit_page_ui_refreshers.refresh_trig_lock_value(i, m_params)
  local channel = program.get_selected_channel()
  local param_id = channel.trig_lock_params[i].param_id

  if channel.trig_lock_banks[i] then
    m_params[i]:set_value(channel.trig_lock_banks[i])
  end
end

function channel_edit_page_ui_refreshers.refresh_trig_lock(i, m_params)
  local channel = program.get_selected_channel()
  local pressed_keys = grid_controller.get_pressed_keys()

  channel_edit_page_ui_refreshers.refresh_trig_lock_value(i, m_params)

  if channel.trig_lock_params[i].id then
    m_params[i]:set_name(channel.trig_lock_params[i].name)
    m_params[i]:set_top_label(channel.trig_lock_params[i].short_descriptor_1)
    m_params[i]:set_bottom_label(channel.trig_lock_params[i].short_descriptor_2)
    m_params[i]:set_off_value(channel.trig_lock_params[i].off_value)
    m_params[i]:set_min_value(channel.trig_lock_params[i].cc_min_value)
    m_params[i]:set_max_value(channel.trig_lock_params[i].cc_max_value)
    m_params[i]:set_ui_labels(channel.trig_lock_params[i].ui_labels)
    m_params[i]:set_value(channel.trig_lock_banks[i] or channel.trig_lock_params[i].off_value)

    local step_trig_lock = program.get_step_param_trig_lock(channel, program.get_current_step_for_channel(channel.number), i)
    if #pressed_keys > 0 then
      if pressed_keys[1][2] > 3 and pressed_keys[1][2] < 8 then
        step_trig_lock = program.get_step_param_trig_lock(channel, fn.calc_grid_count(pressed_keys[1][1], pressed_keys[1][2]), i)
        local default_param = channel.trig_lock_banks[i]
        if channel.trig_lock_params[i].type == "midi" and channel.trig_lock_params[i].param_id then
          default_param = params:lookup_param(channel.trig_lock_params[i].param_id).value
        end
        m_params[i]:set_value(step_trig_lock or default_param)
      end
    end
  else
    m_params[i]:set_name("")
    m_params[i]:set_top_label("None")
    m_params[i]:set_bottom_label("")
  end
end

function channel_edit_page_ui_refreshers.refresh_trig_locks(m_params)
  for i = 1, 10 do
    channel_edit_page_ui_refreshers.refresh_trig_lock(i, m_params)
  end
end

return channel_edit_page_ui_refreshers

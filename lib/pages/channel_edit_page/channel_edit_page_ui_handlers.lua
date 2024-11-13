-- channel_edit_page_ui_handlers.lua
local channel_edit_page_ui_handlers = {}
local param_manager = include("mosaic/lib/devices/param_manager")
local channel_edit_page_ui_refreshers = include("lib/pages/channel_edit_page/channel_edit_page_ui_refreshers")

function channel_edit_page_ui_handlers.handle_encoder_two_positive(pages, selectors, dials, trig_lock_page)
  local channel_pages = pages.channel_pages
  local channel_page_to_index = pages.channel_page_to_index
  local scales_pages = pages.scales_pages
  local scales_page_to_index = pages.scales_page_to_index

  local mask_selectors = selectors.mask_selectors
  local clock_mod_list_selector = selectors.clock_mod_list_selector
  local midi_device_vertical_scroll_selector = selectors.midi_device_vertical_scroll_selector
  local midi_channel_vertical_scroll_selector = selectors.midi_channel_vertical_scroll_selector
  local device_map_vertical_scroll_selector = selectors.device_map_vertical_scroll_selector
  local swing_shuffle_type_selector = selectors.swing_shuffle_type_selector
  local swing_selector = selectors.swing_selector
  local shuffle_feel_selector = selectors.shuffle_feel_selector
  local shuffle_basis_selector = selectors.shuffle_basis_selector
  local shuffle_amount_selector = selectors.shuffle_amount_selector
  
  if channel_pages:get_selected_page() == channel_page_to_index["Masks"] then
    if mask_selectors.trig:is_selected() then
      mask_selectors.trig:deselect()
      mask_selectors.note:select()
    elseif mask_selectors.note:is_selected() then
      mask_selectors.note:deselect()
      mask_selectors.velocity:select()
    elseif mask_selectors.velocity:is_selected() then
      mask_selectors.velocity:deselect()
      mask_selectors.length:select()
    elseif mask_selectors.length:is_selected() then
      mask_selectors.length:deselect()
      mask_selectors.chords[1]:select()
    elseif mask_selectors.chords[1]:is_selected() then
      mask_selectors.chords[1]:deselect()
      mask_selectors.chords[2]:select()
    elseif mask_selectors.chords[2]:is_selected() then
      mask_selectors.chords[2]:deselect()
      mask_selectors.chords[3]:select()
    elseif mask_selectors.chords[3]:is_selected() then
      mask_selectors.chords[3]:deselect()
      mask_selectors.chords[4]:select()
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] then
    -- Adjusted navigation for Clock Mods page
    local function get_visible_clock_mod_selectors()
      local selectors = {clock_mod_list_selector, swing_shuffle_type_selector}
      local value = swing_shuffle_type_selector:get_selected().value
      if value == 1 then 
        value = params:get("global_swing_shuffle_type") + 1
      end
      if value == 2 then
        table.insert(selectors, swing_selector)
      elseif value == 3 then
        table.insert(selectors, shuffle_feel_selector)
        table.insert(selectors, shuffle_basis_selector)
        table.insert(selectors, shuffle_amount_selector)
      end
      return selectors
    end

    local selectors = get_visible_clock_mod_selectors()
    local current_index = nil
    for idx, selector in ipairs(selectors) do
      if selector:is_selected() then
        current_index = idx
        break
      end
    end

    if current_index then
      if current_index < #selectors then
        selectors[current_index]:deselect()
        selectors[current_index + 1]:select()
      end
    else
      -- No selector is currently selected, select the first one
      selectors[1]:select()
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] then
    local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
    if midi_channel_vertical_scroll_selector:is_selected() then
      if not device.default_midi_device and m_midi.midi_devices_connected() then
        midi_channel_vertical_scroll_selector:deselect()
        midi_device_vertical_scroll_selector:select()
      end
    elseif device_map_vertical_scroll_selector:is_selected() then
      if not device.default_midi_channel then
        device_map_vertical_scroll_selector:deselect()
        midi_channel_vertical_scroll_selector:select()
      else
        if not device.default_midi_device and m_midi.midi_devices_connected() then
          device_map_vertical_scroll_selector:deselect()
          midi_device_vertical_scroll_selector:select()
        end
      end
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
    if not trig_lock_page:is_sub_page_enabled() then
      dials:scroll_next()
    end
  end
end

function channel_edit_page_ui_handlers.handle_encoder_two_negative(pages, selectors, dials, trig_lock_page)
  local channel_pages = pages.channel_pages
  local channel_page_to_index = pages.channel_page_to_index
  local scales_pages = pages.scales_pages
  local scales_page_to_index = pages.scales_page_to_index

  local mask_selectors = selectors.mask_selectors
  local clock_mod_list_selector = selectors.clock_mod_list_selector
  local midi_device_vertical_scroll_selector = selectors.midi_device_vertical_scroll_selector
  local midi_channel_vertical_scroll_selector = selectors.midi_channel_vertical_scroll_selector
  local device_map_vertical_scroll_selector = selectors.device_map_vertical_scroll_selector
  local swing_shuffle_type_selector = selectors.swing_shuffle_type_selector
  local swing_selector = selectors.swing_selector
  local shuffle_feel_selector = selectors.shuffle_feel_selector
  local shuffle_basis_selector = selectors.shuffle_basis_selector
  local shuffle_amount_selector = selectors.shuffle_amount_selector

  if channel_pages:get_selected_page() == channel_page_to_index["Masks"] then
    if mask_selectors.note:is_selected() then
      mask_selectors.note:deselect()
      mask_selectors.trig:select()
    elseif mask_selectors.velocity:is_selected() then
      mask_selectors.velocity:deselect()
      mask_selectors.note:select()
    elseif mask_selectors.length:is_selected() then
      mask_selectors.length:deselect()
      mask_selectors.velocity:select()
    elseif mask_selectors.chords[1]:is_selected() then
      mask_selectors.chords[1]:deselect()
      mask_selectors.length:select()
    elseif mask_selectors.chords[2]:is_selected() then
      mask_selectors.chords[2]:deselect()
      mask_selectors.chords[1]:select()
    elseif mask_selectors.chords[3]:is_selected() then
      mask_selectors.chords[3]:deselect()
      mask_selectors.chords[2]:select()
    elseif mask_selectors.chords[4]:is_selected() then
      mask_selectors.chords[4]:deselect()
      mask_selectors.chords[3]:select()
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] then
    -- Adjusted navigation for Clock Mods page
    local function get_visible_clock_mod_selectors()
      local selectors = {clock_mod_list_selector, swing_shuffle_type_selector}
      local value = swing_shuffle_type_selector:get_selected().value
      if value == 1 then 
        value = params:get("global_swing_shuffle_type") + 1
      end
      if value == 2 then
        table.insert(selectors, swing_selector)
      elseif value == 3 then
        table.insert(selectors, shuffle_feel_selector)
        table.insert(selectors, shuffle_basis_selector)
        table.insert(selectors, shuffle_amount_selector)
      end
      return selectors
    end

    local selectors = get_visible_clock_mod_selectors()
    local current_index = nil
    for idx, selector in ipairs(selectors) do
      if selector:is_selected() then
        current_index = idx
        break
      end
    end

    if current_index then
      if current_index > 1 then
        selectors[current_index]:deselect()
        selectors[current_index - 1]:select()
      end
    else
      -- No selector is currently selected, select the last one
      selectors[#selectors]:select()
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] then
    local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
    if midi_device_vertical_scroll_selector:is_selected() then
      if device.default_midi_channel == nil and m_midi.midi_devices_connected() then
        midi_device_vertical_scroll_selector:deselect()
        midi_channel_vertical_scroll_selector:select()
      elseif device.default_midi_device == nil and m_midi.midi_devices_connected() then
        midi_device_vertical_scroll_selector:deselect()
        device_map_vertical_scroll_selector:select()
      end
    elseif midi_channel_vertical_scroll_selector:is_selected() then
      midi_channel_vertical_scroll_selector:deselect()
      device_map_vertical_scroll_selector:select()
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] then
    if not trig_lock_page:is_sub_page_enabled() then
      dials:scroll_previous()
    end
  end
end


function channel_edit_page_ui_handlers.handle_trig_locks_page_change(direction, trig_lock_page, param_select_vertical_scroll_selector, dials)
  local channel = program.get_selected_channel()
  local dial_index = dials:get_selected_index()

  if trig_lock_page:is_sub_page_enabled() then
    param_select_vertical_scroll_selector:scroll(direction)
    save_confirm.set_save(function()
      norns_param_state_handler.clear_original_param_state(channel.number, dial_index)
      param_manager.update_param(
        dial_index,
        channel,
        param_select_vertical_scroll_selector:get_selected_item(),
        param_select_vertical_scroll_selector:get_meta_item()
      )
      channel_edit_page_ui.refresh_trig_locks()
      program.increment_trig_lock_calculator_id(channel, dial_index)
    end)
    save_confirm.set_cancel(function() end)
  else
    channel_edit_page_ui.handle_trig_lock_param_change_by_direction(direction, channel, dial_index)
  end
end

return channel_edit_page_ui_handlers

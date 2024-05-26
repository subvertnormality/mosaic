-- channel_edit_page_ui_handlers.lua
local channel_edit_page_ui_handlers = {}
local fn = include("lib/functions")
local param_manager = include("mosaic/lib/param_manager")

function channel_edit_page_ui_handlers.handle_encoder_two_positive(channel_pages, channel_page_to_index, scales_pages, scales_page_to_index, note_selectors, quantizer_vertical_scroll_selector, romans_vertical_scroll_selector, notes_vertical_scroll_selector, rotation_vertical_scroll_selector, clock_mod_list_selector, clock_swing_value_selector, midi_device_vertical_scroll_selector, midi_channel_vertical_scroll_selector, device_map_vertical_scroll_selector, dials, trig_lock_page)
  if channel_pages:get_selected_page() == channel_page_to_index["Notes"] and program.get().selected_channel ~= 17 then
    if note_selectors.trig:is_selected() then
      note_selectors.trig:deselect()
      note_selectors.note:select()
    elseif note_selectors.note:is_selected() then
      note_selectors.note:deselect()
      note_selectors.velocity:select()
    elseif note_selectors.velocity:is_selected() then
      note_selectors.velocity:deselect()
      note_selectors.length:select()
    elseif note_selectors.length:is_selected() then
      note_selectors.length:deselect()
      note_selectors.chords[1]:select()
    elseif note_selectors.chords[1]:is_selected() then
      note_selectors.chords[1]:deselect()
      note_selectors.chords[2]:select()
    elseif note_selectors.chords[2]:is_selected() then
      note_selectors.chords[2]:deselect()
      note_selectors.chords[3]:select()
    elseif note_selectors.chords[3]:is_selected() then
      note_selectors.chords[3]:deselect()
      note_selectors.chords[4]:select()
    end
  elseif scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] and program.get().selected_channel == 17 then
    if quantizer_vertical_scroll_selector:is_selected() then
      quantizer_vertical_scroll_selector:deselect()
      romans_vertical_scroll_selector:select()
    elseif romans_vertical_scroll_selector:is_selected() then
      romans_vertical_scroll_selector:deselect()
      rotation_vertical_scroll_selector:select()
    elseif notes_vertical_scroll_selector:is_selected() then
      notes_vertical_scroll_selector:deselect()
      quantizer_vertical_scroll_selector:select()
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] and program.get().selected_channel ~= 17 then
    if clock_mod_list_selector:is_selected() then
      clock_mod_list_selector:deselect()
      clock_swing_value_selector:select()
    end
  elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] and program.get().selected_channel == 17 then
    clock_mod_list_selector:select()
  elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] and program.get().selected_channel ~= 17 then
    local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
    if midi_channel_vertical_scroll_selector:is_selected() then
      if not device.default_midi_device and midi_controller.midi_devices_connected() then
        midi_channel_vertical_scroll_selector:deselect()
        midi_device_vertical_scroll_selector:select()
      end
    elseif device_map_vertical_scroll_selector:is_selected() then
      if not device.default_midi_channel then
        device_map_vertical_scroll_selector:deselect()
        midi_channel_vertical_scroll_selector:select()
      else
        if not device.default_midi_device and midi_controller.midi_devices_connected() then
          device_map_vertical_scroll_selector:deselect()
          midi_device_vertical_scroll_selector:select()
        end
      end
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] and program.get().selected_channel ~= 17 then
    if not trig_lock_page:is_sub_page_enabled() then
      dials:scroll_next()
    end
  end
end

function channel_edit_page_ui_handlers.handle_encoder_two_negative(channel_pages, channel_page_to_index, scales_pages, scales_page_to_index, note_selectors, quantizer_vertical_scroll_selector, romans_vertical_scroll_selector, notes_vertical_scroll_selector, rotation_vertical_scroll_selector, clock_mod_list_selector, clock_swing_value_selector, midi_device_vertical_scroll_selector, midi_channel_vertical_scroll_selector, device_map_vertical_scroll_selector, dials, trig_lock_page)
  if channel_pages:get_selected_page() == channel_page_to_index["Notes"] and program.get().selected_channel ~= 17 then
    if note_selectors.note:is_selected() then
      note_selectors.note:deselect()
      note_selectors.trig:select()
    elseif note_selectors.velocity:is_selected() then
      note_selectors.velocity:deselect()
      note_selectors.note:select()
    elseif note_selectors.length:is_selected() then
      note_selectors.length:deselect()
      note_selectors.velocity:select()
    elseif note_selectors.chords[1]:is_selected() then
      note_selectors.chords[1]:deselect()
      note_selectors.length:select()
    elseif note_selectors.chords[2]:is_selected() then
      note_selectors.chords[2]:deselect()
      note_selectors.chords[1]:select()
    elseif note_selectors.chords[3]:is_selected() then
      note_selectors.chords[3]:deselect()
      note_selectors.chords[2]:select()
    elseif note_selectors.chords[4]:is_selected() then
      note_selectors.chords[4]:deselect()
      note_selectors.chords[3]:select()
    end
  elseif scales_pages:get_selected_page() == scales_page_to_index["Quantizer"] and program.get().selected_channel == 17 then
    if quantizer_vertical_scroll_selector:is_selected() then
      quantizer_vertical_scroll_selector:deselect()
      notes_vertical_scroll_selector:select()
    elseif romans_vertical_scroll_selector:is_selected() then
      romans_vertical_scroll_selector:deselect()
      quantizer_vertical_scroll_selector:select()
    elseif rotation_vertical_scroll_selector:is_selected() then
      rotation_vertical_scroll_selector:deselect()
      romans_vertical_scroll_selector:select()
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Clock Mods"] and program.get().selected_channel ~= 17 then
    if clock_swing_value_selector:is_selected() then
      clock_swing_value_selector:deselect()
      clock_mod_list_selector:select()
    end
  elseif scales_pages:get_selected_page() == scales_page_to_index["Clock Mods"] and program.get().selected_channel == 17 then
    clock_mod_list_selector:select()
  elseif channel_pages:get_selected_page() == channel_page_to_index["Midi Config"] and program.get().selected_channel ~= 17 then
    local device = fn.get_by_id(device_map.get_devices(), device_map_vertical_scroll_selector:get_selected_item().id)
    if midi_device_vertical_scroll_selector:is_selected() then
      if device.default_midi_channel == nil and midi_controller.midi_devices_connected() then
        midi_device_vertical_scroll_selector:deselect()
        midi_channel_vertical_scroll_selector:select()
      elseif device.default_midi_device == nil and midi_controller.midi_devices_connected() then
        midi_device_vertical_scroll_selector:deselect()
        device_map_vertical_scroll_selector:select()
      end
    elseif midi_channel_vertical_scroll_selector:is_selected() then
      midi_channel_vertical_scroll_selector:deselect()
      device_map_vertical_scroll_selector:select()
    end
  elseif channel_pages:get_selected_page() == channel_page_to_index["Trig Locks"] and program.get().selected_channel ~= 17 then
    if not trig_lock_page:is_sub_page_enabled() then
      dials:scroll_previous()
    end
  end
end


function channel_edit_page_ui_handlers.handle_trig_locks_page_change(direction, trig_lock_page, param_select_vertical_scroll_selector, dials)
  if trig_lock_page:is_sub_page_enabled() then
    param_select_vertical_scroll_selector:scroll(direction)
    save_confirm.set_save(function()
      param_manager.update_param(
        dials:get_selected_index(),
        program.get_selected_channel(),
        param_select_vertical_scroll_selector:get_selected_item(),
        param_select_vertical_scroll_selector:get_meta_item()
      )
      channel_edit_page_ui_controller.refresh_trig_locks()
    end)
    save_confirm.set_cancel(function() end)
  else
    channel_edit_page_ui_controller.handle_trig_lock_param_change_by_direction(direction, program.get_selected_channel(), dials:get_selected_index())
  end
end

return channel_edit_page_ui_handlers

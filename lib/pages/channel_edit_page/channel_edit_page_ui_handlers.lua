-- channel_edit_page_ui_handlers.lua
local channel_edit_page_ui_handlers = {}
local param_manager = include("mosaic/lib/devices/param_manager")
local channel_edit_page_ui_refreshers = include("lib/pages/channel_edit_page/channel_edit_page_ui_refreshers")

function channel_edit_page_ui_handlers.handle_encoder_two_positive(pages, selectors, dials, trig_lock_page, parameter_controller, clock_controls_controller)
  local channel_pages = pages.channel_pages
  local channel_page_to_index = pages.channel_page_to_index
  local scales_pages = pages.scales_pages
  local scales_page_to_index = pages.scales_page_to_index

  local mask_selectors = selectors.mask_selectors
  local midi_device_vertical_scroll_selector = selectors.midi_device_vertical_scroll_selector
  local midi_channel_vertical_scroll_selector = selectors.midi_channel_vertical_scroll_selector
  local device_map_vertical_scroll_selector = selectors.device_map_vertical_scroll_selector
  
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
    clock_controls_controller.navigate(1, function()
      return channel_edit_page_ui.get_swing_shuffle_type_selector_value()
    end)
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
    parameter_controller.navigate_dial(1)
  end
end

function channel_edit_page_ui_handlers.handle_encoder_two_negative(pages, selectors, dials, trig_lock_page, parameter_controller, clock_controls_controller)
  local channel_pages = pages.channel_pages
  local channel_page_to_index = pages.channel_page_to_index
  local scales_pages = pages.scales_pages
  local scales_page_to_index = pages.scales_page_to_index

  local mask_selectors = selectors.mask_selectors
  local midi_device_vertical_scroll_selector = selectors.midi_device_vertical_scroll_selector
  local midi_channel_vertical_scroll_selector = selectors.midi_channel_vertical_scroll_selector
  local device_map_vertical_scroll_selector = selectors.device_map_vertical_scroll_selector

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
    clock_controls_controller.navigate(-1, function()
      return channel_edit_page_ui.get_swing_shuffle_type_selector_value()
    end)
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
    parameter_controller.navigate_dial(-1)
  end
end


-- Reuse adapters across encoder events while retaining the original lookup lifetimes.
local function assign_parameter(dial_index, channel, selected_item, meta_item)
  param_manager.update_param(dial_index, channel, selected_item, meta_item)
end
local assignment_callbacks = {
  refresh_trig_locks = function()
    channel_edit_page_ui.refresh_trig_locks()
  end,
  handle_trig_lock_param_change = function(direction, channel, dial_index)
    channel_edit_page_ui.handle_trig_lock_param_change_by_direction(direction, channel, dial_index)
  end
}

function channel_edit_page_ui_handlers.handle_trig_locks_page_change(direction, parameter_controller)
  parameter_controller.handle_assignment_page_change(direction, assign_parameter, assignment_callbacks)
end

return channel_edit_page_ui_handlers

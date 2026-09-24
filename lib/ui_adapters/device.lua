-- Device provider adapter (UI02): screens C05 and C11 (descriptor_filter views).
--
-- owners = channel_edit_page_ui.adapter_owners(); uses owners.parameters (the
-- channel_edit_parameters controller). Its adapter_controls() hold the device
-- map, MIDI channel and MIDI port selectors (the device map selector is only
-- installed at init). Field ids are declared in channel_edit_parameters.device_fields.
--
-- The selectors are the owner's draft; program.get().devices[channel] is the
-- committed routing. E3 on the Midi Config page scrolls the selected selector
-- and stages update_channel_config through save_confirm; K3 confirms, K2/E1
-- cancel. An edit here selects the field's selector (as E2 would) and then
-- calls handle_midi_config_page_increment/decrement once per detent.
--
-- The owner draws the MIDI channel/port only for MIDI devices without a fixed
-- value (and the port only while a port is connected). Here they stay visible
-- for MIDI devices and are disabled when fixed or unavailable (screen C05);
-- for non-MIDI devices they are hidden, as the owner hides them.
--
-- pending_confirmation / has_draft: an enabled selector differs from the
-- committed routing. C11 extras describe the owner's confirm closure, which
-- always clears the channel's device trig locks and rebuilds default slots.

local channel_edit_parameters = include("mosaic/lib/pages/channel_edit_page/channel_edit_parameters")
local channel_target = include("mosaic/lib/ui_adapters/channel_target")

local function item_name(item)
  if item == nil then return "NONE" end
  if type(item) == "table" then return tostring(item.name) end
  return tostring(item)
end

return function(ui_adapters, owners)
  local controller = owners.parameters

  local function controls() return controller.adapter_controls() end

  local function midi_connected()
    -- mosaic.lua installs m_midi as a global; the page UI holds its own include.
    local midi = _ENV["m_midi"] or include("mosaic/lib/m_midi")
    return midi.midi_devices_connected()
  end

  -- The device the selected map item names (the owner's draw() lookup).
  local function selected_device()
    local item = controls().device_map_vertical_scroll_selector:get_selected_item()
    return item and fn.get_by_id(device_map.get_devices(), item.id) or nil
  end

  local function committed()
    return program.get().devices[program.get_selected_channel().number] or {}
  end

  -- Per field: visible, enabled, draft value, committed value.
  local function field_state(field, device)
    local selector = controls()[field.control]
    local item = selector:get_selected_item()
    local devices = committed()
    if field.id == "device" then
      return true, true, item and item.id, devices.device_map
    end
    local is_midi = device ~= nil and device.type == "midi"
    if field.id == "midi_channel" then
      return is_midi, is_midi and device.default_midi_channel == nil, item and item.value, devices.midi_channel
    end
    return is_midi, is_midi and device.default_midi_device == nil and midi_connected(), item and item.value, devices.midi_device
  end

  local function pending()
    if controls().device_map_vertical_scroll_selector == nil then return false end
    local device = selected_device()
    for _, field in ipairs(channel_edit_parameters.device_fields) do
      local _, enabled, draft, active = field_state(field, device)
      if enabled and draft ~= active then return true end
    end
    return false
  end

  local function describe()
    if controls().device_map_vertical_scroll_selector == nil then return nil, "not_initialised" end
    local device = selected_device()
    local descriptors = {}
    for _, field in ipairs(channel_edit_parameters.device_fields) do
      local selector = controls()[field.control]
      local visible, enabled, draft, active = field_state(field, device)
      descriptors[#descriptors + 1] = {
        id = field.id,
        label = field.label,
        kind = "value",
        value = item_name(selector:get_selected_item()),
        visible = visible,
        enabled = enabled,
        selected = selector:is_selected(),
        domain = {draft = draft, committed = active, items = selector:get_items(),
          fixed = field.id ~= "device" and visible and not enabled},
        edit = function(delta)
          local all = controls()
          for _, other in ipairs(channel_edit_parameters.device_fields) do
            if other ~= field then all[other.control]:deselect() end
          end
          if not selector:is_selected() then selector:select() end
          return channel_target.per_detent(delta, function(d)
            if d > 0 then return controller.handle_midi_config_page_increment() end
            return controller.handle_midi_config_page_decrement()
          end)
        end
      }
    end
    local staged = pending()
    descriptors[#descriptors + 1] = {id = "device_locks", label = "Device locks", kind = "readonly",
      value = "RESET", visible = staged}
    descriptors[#descriptors + 1] = {id = "slot_defaults", label = "Slot defaults", kind = "readonly",
      value = "REBUILD", visible = staged}
    descriptors[#descriptors + 1] = {id = "k2_k3", label = "K2 / K3", kind = "readonly",
      value = "CANCEL/APPLY", visible = staged}
    return descriptors
  end

  local function identity()
    local devices = committed()
    return channel_target.identity() .. "|" .. tostring(devices.device_map) .. ":" ..
      tostring(devices.midi_channel) .. ":" .. tostring(devices.midi_device)
  end

  return ui_adapters.new("device", {
    describe = describe,
    generation = channel_target.generation(identity),
    target_valid = function(target) return channel_target.valid(target) end,
    has_draft = pending,
    pending_confirmation = pending,
    -- K3 (handle_key_three_pressed with no held step) confirms the staged save.
    apply = function() return save_confirm.confirm() end,
    -- K2 / E1 cancel: the owner's cancel closure refreshes the selectors.
    cancel = function() return save_confirm.cancel() end
  })
end

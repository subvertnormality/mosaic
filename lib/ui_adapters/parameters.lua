-- Parameters provider adapter (UI02): screens C02, C10, C13, F08 (descriptor_filter views).
--
-- owners = channel_edit_page_ui.adapter_owners(); uses owners.parameters (the
-- channel_edit_parameters controller) and owners.m_params (the ten trig-lock
-- dials). The selected slot and the trig lock page come from
-- owners.parameters.adapter_controls().
--
-- One descriptor per slot, id slot_<n> (field_contracts.parameters.identity);
-- channel.trig_lock_params[n].id is metadata in domain.assigned_parameter_id
-- ("none" when unassigned), so selection is retained by slot and the C10 view
-- filters on the chord_ prefix of that metadata. The value is the dial's own
-- display (refresh_trig_locks fills the dial with the default, or the first
-- held step's lock while steps are held): "X" for Off or an unassigned slot,
-- the ui_label, else the clean number. domain.state keeps none / off / set
-- apart.
--
-- Edits call controller.handle_trig_lock_param_change_by_direction(d, channel,
-- n) once per detent with the full delta: the call channel_edit_navigation
-- reaches through handle_trig_locks_page_change when the assignment subpage is
-- closed. While the subpage is open E3 browses assignments instead, so slot
-- edits are disabled (the assignment adapter owns that state).
--
-- F08 extras `scope` and `wrap` describe the held edit scope and the slide wrap
-- setting; they are marked selected (they belong to the selected-slot views)
-- and are visible only while steps are held.

local channel_edit_parameters = include("mosaic/lib/pages/channel_edit_page/channel_edit_parameters")
local channel_target = include("mosaic/lib/ui_adapters/channel_target")

-- The text dial:draw shows for a dial (lib/ui_components/dial.lua), with the
-- numeric form it shows while display_value is on in place of the bar.
local function dial_text(dial)
  local value = dial.value
  if dial.min_value and value then
    value = math.max(dial.min_value, math.min(value, dial.max_value))
  end
  if dial.value == dial.off_value or value == dial.off_value or not value or not dial.min_value or not dial.max_value then
    return "X", "off"
  elseif dial.ui_labels and dial.min_value then
    return dial.ui_labels[value - (dial.min_value - 1)] or "", "set"
  end
  return tostring(fn.clean_number(value)), "set"
end

return function(ui_adapters, owners)
  local controller = owners.parameters
  local m_params = owners.m_params

  local function sub_page_open()
    local page = controller.adapter_controls().trig_lock_page
    return page ~= nil and page:is_sub_page_enabled() == true
  end

  local function describe()
    local controls = controller.adapter_controls()
    local channel = program.get_selected_channel()
    local selected_index = controls.dials:get_selected_index()
    local held = channel_target.held_steps()
    local editable = not sub_page_open()
    local descriptors = {}
    for n = 1, channel_edit_parameters.SLOT_COUNT do
      local dial = m_params[n]
      local lock_param = channel.trig_lock_params[n] or {}
      local text, state = dial_text(dial)
      if not lock_param.param_id then state = "none" end
      local held_slide, held_lock = false, false
      for _, s in ipairs(held) do
        if program.get_step_param_slide(channel, s, n) then held_slide = true end
        local bank = channel.step_trig_lock_banks and channel.step_trig_lock_banks[s]
        if bank and bank[n] ~= nil then held_lock = true end
        -- A lock made while the step is held is staged until release; it is
        -- already this step's lock, so it shows L at once.
        local staged = recorder and recorder.trig_lock_events and recorder.trig_lock_events[channel.number]
        staged = staged and staged[s]
        if staged and staged.data and staged.data.parameter == n then held_lock = true end
      end
      local channel_slide = program.get_channel_param_slide(channel, n) and true or false
      -- Cell marker: S a slide (held step, or channel-wide with nothing held), L a
      -- lock on a held step (spec C02: "L indicates a lock in held scope, S a slide").
      local marker = nil
      if held_slide or (#held == 0 and channel_slide) then marker = "S" elseif held_lock then marker = "L" end
      descriptors[#descriptors + 1] = {
        id = channel_edit_parameters.slot_field_id(n),
        label = (lock_param.name and lock_param.name ~= "") and lock_param.name or tostring(dial.top_label),
        short_label = tostring(dial.top_label),
        kind = "value",
        value = text,
        repeat_key = "slot_<n>",
        selected = selected_index == n,
        enabled = editable,
        domain = {
          slot = n,
          assigned_parameter_id = lock_param.id or "none",
          assigned_parameter_label = lock_param.name,
          param_id = lock_param.param_id,
          min = dial.min_value, max = dial.max_value, off = dial.off_value,
          enum = dial.ui_labels, raw = dial.value, state = state,
          bottom_label = dial.bottom_label,
          channel_slide = channel_slide,
          held_slide = held_slide, held_lock = held_lock
        },
        marker = marker,
        edit = function(delta)
          return channel_target.per_detent(delta, function(d)
            return controller.handle_trig_lock_param_change_by_direction(d, program.get_selected_channel(), n)
          end)
        end
      }
    end
    local wrap = params and params.get and params:get("wrap_param_slides")
    descriptors[#descriptors + 1] = {id = "scope", label = "Scope", kind = "readonly",
      value = channel_target.scope(held), selected = true, visible = #held > 0, domain = {held = held}}
    descriptors[#descriptors + 1] = {id = "wrap", label = "Wrap", kind = "readonly",
      value = wrap == 2 and "ON" or "OFF", selected = true, visible = #held > 0, domain = {raw = wrap}}
    return descriptors
  end

  -- Assignment changes (slot identity metadata) and song/channel/held changes
  -- are new owner states; value edits and slot selection are not.
  local function identity()
    local channel = program.get_selected_channel()
    local ids = {}
    for n = 1, channel_edit_parameters.SLOT_COUNT do
      ids[n] = tostring((channel.trig_lock_params[n] or {}).id)
    end
    return channel_target.identity() .. "|" .. table.concat(ids, ",")
  end

  return ui_adapters.new("parameters", {
    describe = describe,
    generation = channel_target.generation(identity),
    target_valid = function(target) return channel_target.valid(target, true) end
  })
end

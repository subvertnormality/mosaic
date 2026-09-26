-- Clock provider adapter (UI02): screens C04 and F01 (descriptor_filter views).
--
-- owners = channel_edit_page_ui.adapter_owners(); uses owners.clock_controls
-- (the channel_edit_clock_controls controller) and the six selectors it drives:
-- owners.clock_mod_list_selector, swing_shuffle_type_selector, swing_selector,
-- shuffle_feel_selector, shuffle_basis_selector, shuffle_amount_selector.
-- Field ids are declared in channel_edit_clock_controls.fields.
--
-- The selectors are the owner's draft; the selected channel's clock_mods,
-- swing_shuffle_type, swing, shuffle_* are the committed values (the defaults
-- the refreshers use when a channel value is unset). E3 stages a change with
-- save_confirm (handle_increment / handle_decrement on the selected selector);
-- K3 confirms, and a playing transport queues it for the pattern boundary
-- (update_* in the owner). An edit here selects the field's selector, as E2
-- would, then calls the owner once per detent.
--
-- Swing is visible for effective type Swing, the shuffle fields for Shuffle,
-- exactly as draw() and navigate() decide (type X resolves to the global
-- type). Values are the selector texts: "X" for unset type / feel / basis /
-- swing, the division name for rate.
--
-- F01 extras (active_rate, draft_rate, applies, scope) are selected and
-- visible only while a draft exists.

local channel_edit_clock_controls = include("mosaic/lib/pages/channel_edit_page/channel_edit_clock_controls")
local channel_target = include("mosaic/lib/ui_adapters/channel_target")

return function(ui_adapters, owners)
  local controller = owners.clock_controls

  local function effective_type()
    local value = controller.get_swing_shuffle_type_selector_value()
    if value == 0 then value = params:get("global_swing_shuffle_type") end
    return value
  end

  local function text(field, selector)
    if field.control == "swing_selector" or field.control == "shuffle_amount_selector" then
      return selector.view_transform_func(selector:get_value())
    end
    local item = selector:get_selected()
    return item and item.name or "NONE"
  end

  -- {draft, committed} per field, compared the way the refreshers restore them.
  local function values(field)
    local channel = program.get_selected_channel()
    local c = field.control
    if c == "clock_mod_list_selector" then
      local item = owners.clock_mod_list_selector:get_selected() or {}
      local mods = channel.clock_mods or {}
      return tostring(item.type) .. ":" .. tostring(item.value), tostring(mods.type) .. ":" .. tostring(mods.value)
    elseif c == "swing_shuffle_type_selector" then
      return controller.get_swing_shuffle_type_selector_value(), channel.swing_shuffle_type or 0
    elseif c == "swing_selector" then
      return owners.swing_selector:get_value(), channel.swing or -51
    elseif c == "shuffle_feel_selector" then
      return controller.get_shuffle_feel_selector_value(), channel.shuffle_feel or 0
    elseif c == "shuffle_basis_selector" then
      return controller.get_shuffle_basis_selector_value(), channel.shuffle_basis or 0
    end
    return owners.shuffle_amount_selector:get_value(), channel.shuffle_amount or 0
  end

  local function has_draft()
    for _, field in ipairs(channel_edit_clock_controls.fields) do
      local draft, active = values(field)
      if draft ~= active then return true end
    end
    return false
  end

  local function describe()
    local type_now = effective_type()
    local descriptors = {}
    for _, field in ipairs(channel_edit_clock_controls.fields) do
      local selector = owners[field.control]
      local draft, active = values(field)
      descriptors[#descriptors + 1] = {
        id = field.id,
        label = field.label,
        short_label = selector.name,
        kind = "value",
        value = text(field, selector),
        visible = field.swing_type == nil or field.swing_type == type_now,
        selected = selector:is_selected(),
        domain = {min = selector.min, max = selector.max, step = 1, enum = selector.list,
          draft = draft, committed = active, off = field.control == "swing_selector" and -51 or nil},
        edit = function(delta)
          for _, other in ipairs(channel_edit_clock_controls.fields) do
            if other ~= field then owners[other.control]:deselect() end
          end
          if not selector:is_selected() then selector:select() end
          return channel_target.per_detent(delta, function(d)
            if d > 0 then return controller.handle_increment() end
            return controller.handle_decrement()
          end)
        end
      }
      if field.id == "rate" then
        descriptors[#descriptors + 1] = {id = "feel_source", label = "Feel source", kind = "readonly",
          value = controller.get_swing_shuffle_type_selector_value() == 0 and "GLOBAL" or "CHANNEL",
          domain = {effective_type = type_now}}
      end
    end
    local drafted = has_draft()
    local mods = program.get_selected_channel().clock_mods or {}
    local draft_item = owners.clock_mod_list_selector:get_selected() or {}
    local extras = {
      {id = "active_rate", label = "Active rate", value = mods.name or "NONE"},
      {id = "draft_rate", label = "Draft rate", value = draft_item.name or "NONE"},
      {id = "applies", label = "Applies", value = m_clock.is_playing() and "PATTERN END" or "ON CONFIRM"},
      {id = "scope", label = "Scope", value = "CHANNEL"}
    }
    for _, extra in ipairs(extras) do
      extra.kind, extra.selected, extra.visible = "readonly", drafted, drafted
      descriptors[#descriptors + 1] = extra
    end
    return descriptors
  end

  local function identity()
    local channel = program.get_selected_channel()
    local mods = channel.clock_mods or {}
    return channel_target.identity() .. "|" .. table.concat({tostring(mods.type), tostring(mods.value),
      tostring(channel.swing_shuffle_type), tostring(channel.swing), tostring(channel.shuffle_feel),
      tostring(channel.shuffle_basis), tostring(channel.shuffle_amount)}, ":")
  end

  return ui_adapters.new("clock", {
    describe = describe,
    generation = channel_target.generation(identity),
    target_valid = function(target) return channel_target.valid(target) end,
    has_draft = has_draft,
    pending_confirmation = has_draft,
    apply = function() return save_confirm.confirm() end,
    cancel = function() return save_confirm.cancel() end
  })
end

-- Assignment provider adapter (UI02): screen C07 (trig lock assignment subpage).
--
-- owners = channel_edit_page_ui.adapter_owners(); uses owners.parameters (the
-- channel_edit_parameters controller) and, through adapter_controls(), its
-- trig_lock_page, dials and param_select_vertical_scroll_selector. The browse
-- closure is channel_edit_page_ui_handlers.handle_trig_locks_page_change
-- (owners.ui_handlers when given, else that module).
--
-- The route exists only while K2 has opened the subpage; otherwise describe is
-- an error outcome. One descriptor per parameter in the owner's filtered list
-- (device_map.get_available_params_for_channel), keyed by the parameter id
-- ("none" unassigns). The list cursor is the one E3 moves: the item under it is
-- the only editable descriptor and its edit is the owner browse (scroll and
-- stage the assignment with save_confirm), once per detent with the full delta.
-- Other items are readonly. Values: CURRENT for the slot's assigned id, else
-- AVAILABLE. K3 (apply) confirms the staged assignment; K2 cancel discards it.

local channel_target = include("mosaic/lib/ui_adapters/channel_target")

return function(ui_adapters, owners)
  local controller = owners.parameters
  local ui_handlers = owners.ui_handlers or
    include("mosaic/lib/pages/channel_edit_page/channel_edit_page_ui_handlers")

  local function controls() return controller.adapter_controls() end

  local function open()
    local page = controls().trig_lock_page
    return page ~= nil and page:is_sub_page_enabled() == true
  end

  local function current_id()
    local channel = program.get_selected_channel()
    return (channel.trig_lock_params[controls().dials:get_selected_index()] or {}).id
  end

  local function has_draft()
    if not open() then return false end
    local item = controls().param_select_vertical_scroll_selector:get_selected_item()
    return item ~= nil and item.id ~= current_id()
  end

  local function describe()
    if not open() then return nil, "assignment_closed" end
    local selector = controls().param_select_vertical_scroll_selector
    local cursor = selector:get_selected_index()
    local assigned = current_id()
    local descriptors = {}
    for index, item in ipairs(selector:get_items() or {}) do
      local under_cursor = index == cursor
      descriptors[#descriptors + 1] = {
        id = tostring(item.id),
        label = tostring(item.name or item.id),
        kind = under_cursor and "value" or "readonly",
        value = item.id == assigned and "CURRENT" or "AVAILABLE",
        repeat_key = "<param_id>",
        selected = under_cursor,
        domain = {index = index, parameter_id = item.id, slot = controls().dials:get_selected_index(),
          short_descriptor_1 = item.short_descriptor_1, short_descriptor_2 = item.short_descriptor_2},
        edit = under_cursor and function(delta)
          return channel_target.per_detent(delta, function(d)
            return ui_handlers.handle_trig_locks_page_change(d, controller)
          end)
        end or nil
      }
    end
    return descriptors
  end

  local function identity()
    return channel_target.identity() .. "|" .. tostring(open()) .. ":" ..
      tostring(controls().dials:get_selected_index()) .. ":" .. tostring(current_id())
  end

  return ui_adapters.new("assignment", {
    describe = describe,
    generation = channel_target.generation(identity),
    target_valid = function(target)
      if not channel_target.valid(target) then return false end
      return target.slot == nil or target.slot == controls().dials:get_selected_index()
    end,
    has_draft = has_draft,
    pending_confirmation = has_draft,
    apply = function() return save_confirm.confirm() end,
    cancel = function() return save_confirm.cancel() end
  })
end

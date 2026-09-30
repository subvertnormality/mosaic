-- History provider adapter (UI02): screen C03 (Memory page).
--
-- owners = channel_edit_page_ui.adapter_owners(); uses owners.history (the
-- channel_edit_history controller) and its navigator, whose current/max index
-- and event_state the Memory page draws. Field ids are declared in
-- channel_edit_history.fields.
--
-- position is the navigator's "<current> of <max>", edited by the owner's
-- handle_page_change once per detent (memory.redo / memory.undo), as
-- channel_edit_navigation.enc(3, d) does. selected_event shows a stored
-- description when the event has one, else "Event NN", and NO HISTORY when
-- empty. undo_available / redo_available are the counts either side of the
-- current position. Undo all / redo all (K2/K3) stay with the navigation owner.

local channel_edit_history = include("mosaic/lib/pages/channel_edit_page/channel_edit_history")
local channel_target = include("mosaic/lib/ui_adapters/channel_target")

return function(ui_adapters, owners)
  local history = owners.history

  local function describe()
    local navigator = history.navigator
    local current, max = navigator:get_current_index(), navigator:get_max_index()
    local events = navigator.event_state and navigator.event_state.events or {}
    local event = events[1]
    local event_text = "NO HISTORY"
    if current > 0 then
      event_text = event and event.description or string.format("Event %02d", current)
    end
    local values = {
      position = current .. " of " .. max,
      selected_event = event_text,
      undo_available = current,
      redo_available = math.max(0, max - current)
    }
    local descriptors = {}
    for _, field in ipairs(channel_edit_history.fields) do
      local d = {id = field.id, label = field.label, kind = "readonly", value = values[field.id]}
      if field.id == "position" then
        d.kind = "value"
        d.selected = navigator:is_selected()
        d.domain = {min = 0, max = max, step = 1, current = current}
        d.edit = function(delta)
          return channel_target.per_detent(delta, function(d_) return history.handle_page_change(d_) end)
        end
      elseif field.id == "selected_event" then
        d.domain = {event_type = event and event.type or nil}
      end
      descriptors[#descriptors + 1] = d
    end
    return descriptors
  end

  -- Moving through history is the value edit, not a new owner state; a new
  -- channel or a changed history length (a recorded event, a forget) is.
  local function identity()
    return tostring(program.get().selected_channel) .. ":" .. tostring(history.navigator:get_max_index())
  end

  return ui_adapters.new("history", {
    describe = describe,
    generation = channel_target.generation(identity),
    target_valid = function(target)
      return type(target) == "table" and (target.channel == nil or target.channel == program.get().selected_channel)
    end
  })
end

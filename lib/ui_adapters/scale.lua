-- Scale provider adapter (UI02): screen S01 (existing_route S01).
--
-- owners = scale_edit_page_ui.adapter_owners(): the five vertical scroll
-- selectors of the Quantizer page. The page module itself (its E3 handlers,
-- update_scale and K2/K3 handlers) is reached through owners.ui, else the
-- global scale_edit_page_ui that lib/ui.lua installs.
--
-- The selectors are the owner's draft; program.get_scale(selected_scale) is
-- the stored scale slot. E3 on the Quantizer page runs
-- handle_quantizer_page_increment/decrement once per detent on the selected
-- selector, and each call ends in update_scale, which stages the save with
-- save_confirm. An edit here selects the field's selector, as E2 would, then
-- calls the same handler once per detent.
--
-- K1-at-edit scope is kept exactly: update_scale reads the global
-- is_key1_down on EACH edit and stages program.set_all_song_pattern_scales
-- (K1 held) or program.set_scale (current song slot). The adapter never sets
-- or caches it; an edit outcome reports the scope that edit staged (read from
-- the same global, immediately after the owner ran) so the page can show it.
-- K3 (apply) runs save_confirm.confirm through handle_key_three_pressed; K2
-- (cancel) runs save_confirm.cancel through handle_key_two_pressed. With grid
-- keys held the owner's K3 does nothing and its K2 clears step scale locks,
-- so apply/cancel refuse a held target instead of calling them.
--
-- Pentatonic has no Scale-page control: it is the native option
-- all_scales_lock_to_pentatonic (edited on X05), described read-only here.

local quantiser = include("mosaic/lib/quantiser")
local channel_target = include("mosaic/lib/ui_adapters/channel_target")

local FIELDS = {
  {id = "root", label = "Root", selector = "notes_vertical_scroll_selector"},
  {id = "scale", label = "Scale", selector = "quantizer_vertical_scroll_selector"},
  {id = "degree", label = "Degree", selector = "romans_vertical_scroll_selector"},
  {id = "transpose", label = "Transpose", selector = "transpose_vertical_scroll_selector"},
  {id = "rotation", label = "Rotation", selector = "rotation_vertical_scroll_selector"}
}

local PENTATONIC_PARAM = "all_scales_lock_to_pentatonic"

local function item_text(item)
  if type(item) == "table" then return item.name end
  return item
end

local function enum_of(items)
  local enum = {}
  for index, item in ipairs(items or {}) do enum[index] = item_text(item) end
  return enum
end

-- The stored slot formatted the way refresh_quantiser loads it into the
-- selectors, so draft and stored compare index for index.
local function stored_indices(scale)
  if not scale then return {} end
  return {
    root = scale.root_note + 1,
    scale = scale.number,
    degree = scale.chord,
    transpose = (scale.transpose or 0) + 13,
    rotation = (scale.chord_degree_rotation or 0) + 1
  }
end

local function stored_text(id, scale, index)
  if index == nil then return nil end
  if id == "root" then return quantiser.get_notes()[index] end
  if id == "scale" then return quantiser.get_scale_name_from_index(index) end
  if id == "degree" then
    local family = scale.number and quantiser.get_scales()[scale.number]
    return family and family.romans[index] or nil
  end
  if id == "transpose" then
    local t = index - 13
    return t > 0 and ("+" .. t) or tostring(t)
  end
  return "r" .. (index - 1)
end

return function(ui_adapters, owners)
  local function ui() return owners.ui or scale_edit_page_ui end

  local function stored_scale()
    local ok, scale = pcall(program.get_scale, program.get().selected_scale)
    if ok then return scale end
    return nil
  end

  local function has_draft()
    local stored = stored_indices(stored_scale())
    for _, field in ipairs(FIELDS) do
      if stored[field.id] ~= owners[field.selector]:get_selected_index() then return true end
    end
    return false
  end

  local function focus(field)
    for _, other in ipairs(FIELDS) do
      if other ~= field then owners[other.selector]:deselect() end
    end
    owners[field.selector]:select()
  end

  local function current_scope()
    return is_key1_down and "all_songs" or "current_song"
  end

  local function describe()
    local scale = stored_scale()
    local stored = stored_indices(scale)
    local descriptors = {}
    for _, field in ipairs(FIELDS) do
      local selector = owners[field.selector]
      local items = selector:get_items()
      descriptors[#descriptors + 1] = {
        id = field.id,
        label = field.label,
        short_label = selector.name,
        kind = "value",
        value = item_text(selector:get_selected_item()) or "NONE",
        selected = selector:is_selected(),
        domain = {
          min = 1, max = #(items or {}), step = 1, enum = enum_of(items),
          draft_index = selector:get_selected_index(),
          stored_index = stored[field.id],
          stored = stored_text(field.id, scale or {}, stored[field.id]),
          scale_slot = program.get().selected_scale,
          scope = current_scope()
        },
        edit = function(delta)
          focus(field)
          local page = ui()
          channel_target.per_detent(delta, function(d)
            if d > 0 then return page.handle_quantizer_page_increment() end
            return page.handle_quantizer_page_decrement()
          end)
          -- update_scale just read is_key1_down to pick the staged setter.
          return {scope = current_scope()}
        end
      }
    end
    local enum = {"Off", "On"}
    local ok, text = pcall(params.string, params, PENTATONIC_PARAM)
    if not ok or text == nil then
      local value = params:get(PENTATONIC_PARAM)
      text = value and enum[value] or nil
    end
    descriptors[#descriptors + 1] = {
      id = "pentatonic",
      label = "Pentatonic",
      kind = "readonly",
      value = text or "NONE",
      domain = {enum = enum, native_param = PENTATONIC_PARAM}
    }
    return descriptors
  end

  local function identity()
    local state = program.get()
    return tostring(state.selected_song_pattern) .. ":" .. tostring(state.selected_scale)
  end

  local function target_valid(target)
    if target == nil then return true end
    if type(target) ~= "table" then return false end
    local state = program.get()
    if target.song_slot ~= nil and target.song_slot ~= state.selected_song_pattern then return false end
    if target.scale_slot ~= nil and target.scale_slot ~= state.selected_scale then return false end
    return true
  end

  local adapter
  adapter = ui_adapters.new("scale", {
    describe = describe,
    generation = channel_target.generation(identity),
    target_valid = target_valid,
    has_draft = has_draft,
    pending_confirmation = has_draft,
    apply = function(_, target)
      if not target_valid(target) then return ui_adapters.fail("stale_target", adapter:identity(target)) end
      if channel_target.pressed_count() > 0 then return ui_adapters.fail("held_keys", adapter:identity(target)) end
      return ui().handle_key_three_pressed()
    end,
    cancel = function()
      if channel_target.pressed_count() > 0 then return ui_adapters.fail("held_keys", adapter:identity()) end
      return ui().handle_key_two_pressed()
    end
  })

  -- The owner identity an S01 dispatch captures: song slot and scale slot.
  function adapter.capture(route)
    local state = program.get()
    return {source_route = route or "S01", screen = route or "S01",
      song_slot = state.selected_song_pattern, scale_slot = state.selected_scale}
  end

  return adapter
end

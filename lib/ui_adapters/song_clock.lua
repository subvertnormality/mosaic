-- Song clock provider adapter (UI02): screen A02 (existing_route A02).
--
-- owners = song_edit_page_ui.adapter_owners(): owners.pages, page_to_index and
-- the "Global settings" selectors tempo_selector, swing_shuffle_type,
-- swing_selector, shuffle_feel_selector, shuffle_basis_selector and
-- shuffle_amount_selector. The page module is owners.ui, else the global
-- song_edit_page_ui.
--
-- The selectors are the owner's draft; the committed values are the native
-- params clock_tempo, global_swing_shuffle_type, global_swing,
-- global_shuffle_feel, global_shuffle_basis and global_shuffle_amount, which
-- update_* write on K3 (save_confirm.confirm). Visibility follows the page's
-- get_visible_selectors: Swing while the type selector reads Swing, the three
-- shuffle fields otherwise (the draft type, before K3, exactly as draw()).
-- An edit selects the Global settings page (as E1 does), selects the field's
-- selector alone (as E2 does) and calls song_edit_page_ui.enc(3, delta), whose
-- inline branch stages the matching update_*/refresh_* pair.

local channel_target = include("mosaic/lib/ui_adapters/channel_target")

local FIELDS = {
  {id = "tempo", label = "Tempo", selector = "tempo_selector", param = "clock_tempo", unit = "BPM"},
  {id = "swing_type", label = "Swing type", selector = "swing_shuffle_type", param = "global_swing_shuffle_type"},
  {id = "swing", label = "Swing", selector = "swing_selector", param = "global_swing", type_value = 1},
  {id = "shuffle_feel", label = "Feel", selector = "shuffle_feel_selector", param = "global_shuffle_feel", type_value = 2},
  {id = "shuffle_basis", label = "Basis", selector = "shuffle_basis_selector", param = "global_shuffle_basis", type_value = 2},
  {id = "shuffle_amount", label = "Amount", selector = "shuffle_amount_selector", param = "global_shuffle_amount", type_value = 2}
}

return function(ui_adapters, owners)
  local function ui() return owners.ui or song_edit_page_ui end
  local page_index = owners.page_to_index["Global settings"]

  local function is_list(selector) return selector.list ~= nil end

  local function draft(selector)
    if is_list(selector) then return (selector:get_selected() or {}).value end
    return selector:get_value()
  end

  local function has_draft()
    for _, field in ipairs(FIELDS) do
      if draft(owners[field.selector]) ~= params:get(field.param) then return true end
    end
    return false
  end

  local function describe()
    local type_now = (owners.swing_shuffle_type:get_selected() or {}).value
    local descriptors = {}
    for _, field in ipairs(FIELDS) do
      local selector = owners[field.selector]
      local d = {
        id = field.id,
        label = field.label,
        short_label = selector.name,
        kind = "value",
        visible = field.type_value == nil or field.type_value == type_now,
        selected = selector:is_selected(),
        domain = {step = 1, unit = field.unit, native_param = field.param, draft = draft(selector),
          committed = params:get(field.param), scope = "global"}
      }
      if is_list(selector) then
        local enum = {}
        for index, item in ipairs(selector.list) do enum[index] = item.name end
        d.value = (selector:get_selected() or {}).name or "NONE"
        d.domain.min, d.domain.max, d.domain.enum = 1, #enum, enum
      else
        local value = selector:get_value()
        d.value = value and selector.view_transform_func(value) or "0"
        d.domain.min, d.domain.max = selector.min, selector.max
      end
      d.edit = function(delta)
        owners.pages:select_page(page_index)
        for _, other in ipairs(FIELDS) do
          if other ~= field then owners[other.selector]:deselect() end
        end
        selector:select()
        return ui().enc(3, delta)
      end
      descriptors[#descriptors + 1] = d
    end
    return descriptors
  end

  local adapter
  adapter = ui_adapters.new("song_clock", {
    describe = describe,
    has_draft = has_draft,
    pending_confirmation = has_draft,
    apply = function(_, target)
      if channel_target.pressed_count() > 0 then return ui_adapters.fail("held_keys", adapter:identity(target)) end
      return ui().handle_key_three_pressed()
    end,
    cancel = function()
      if channel_target.pressed_count() > 0 then return ui_adapters.fail("held_keys", adapter:identity()) end
      return ui().handle_key_two_pressed()
    end
  })

  -- Global settings: nothing to capture beyond the route.
  function adapter.capture(route)
    return {source_route = route or "A02", screen = route or "A02"}
  end

  return adapter
end

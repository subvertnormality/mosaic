-- Song provider adapter (UI02): screen A01 (existing_route A01).
--
-- owners = song_edit_page_ui.adapter_owners(): owners.pages, page_to_index,
-- pattern_repeat_selector and song_mode_selector (the "Song progression"
-- page). The page module (enc, update_*/refresh_*, K2/K3 handlers) is
-- owners.ui, else the global song_edit_page_ui.
--
-- The selectors are the owner's draft. Repeats commits to the selected song
-- slot (update_pattern_repeat), Song mode to the native param song_mode
-- (update_song_mode); both are staged with save_confirm by the E3 branch of
-- song_edit_page_ui.enc, whose closures are inline. An edit therefore selects
-- the Song progression page (as E1 does, with no other effect on this page),
-- selects the field's selector (as E2 does) and calls song_edit_page_ui.enc(3,
-- delta) unchanged. K3/K2 are handle_key_three_pressed / handle_key_two_pressed.

local channel_target = include("mosaic/lib/ui_adapters/channel_target")

local FIELDS = {
  {id = "repeats", label = "Repeats", selector = "pattern_repeat_selector"},
  {id = "song_mode", label = "Song mode", selector = "song_mode_selector"}
}

return function(ui_adapters, owners)
  local function ui() return owners.ui or song_edit_page_ui end
  local page_index = owners.page_to_index["Song progression"]

  local function committed(id)
    if id == "repeats" then return program.get_selected_song_pattern().repeats end
    return params:get("song_mode")
  end

  local function draft(id)
    if id == "repeats" then return owners.pattern_repeat_selector:get_value() end
    local item = owners.song_mode_selector:get_selected()
    return item and item.value
  end

  local function has_draft()
    for _, field in ipairs(FIELDS) do
      if draft(field.id) ~= committed(field.id) then return true end
    end
    return false
  end

  local function describe()
    local repeats = owners.pattern_repeat_selector
    local mode = owners.song_mode_selector
    local mode_enum = {}
    for index, item in ipairs(mode.list) do mode_enum[index] = item.name end
    local descriptors = {
      {id = "repeats", label = "Repeats", short_label = repeats.name, kind = "value",
        value = repeats.view_transform_func(repeats:get_value() or 0),
        selected = repeats:is_selected(),
        domain = {min = repeats.min, max = repeats.max, step = 1, draft = draft("repeats"),
          committed = committed("repeats"), scope = "song_slot"}},
      {id = "song_mode", label = "Song mode", short_label = mode.name, kind = "value",
        value = (mode:get_selected() or {}).name or "NONE",
        selected = mode:is_selected(),
        domain = {min = 1, max = #mode_enum, step = 1, enum = mode_enum, draft = draft("song_mode"),
          committed = committed("song_mode"), native_param = "song_mode", scope = "global"}}
    }
    for index, d in ipairs(descriptors) do
      local field = FIELDS[index]
      d.edit = function(delta)
        owners.pages:select_page(page_index)
        for _, other in ipairs(FIELDS) do
          if other ~= field then owners[other.selector]:deselect() end
        end
        owners[field.selector]:select()
        return ui().enc(3, delta)
      end
    end
    return descriptors
  end

  local function identity()
    return tostring(program.get().selected_song_pattern)
  end

  local function target_valid(target)
    if target == nil then return true end
    if type(target) ~= "table" then return false end
    return target.song_slot == nil or target.song_slot == program.get().selected_song_pattern
  end

  local adapter
  adapter = ui_adapters.new("song", {
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

  -- Repeats belongs to the edited song slot.
  function adapter.capture(route)
    return {source_route = route or "A01", screen = route or "A01", song_slot = program.get().selected_song_pattern}
  end

  return adapter
end

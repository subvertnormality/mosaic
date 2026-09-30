-- Scale clock provider adapter (UI02): screen S02 (existing_route S02).
--
-- owners = scale_edit_page_ui.adapter_owners(): owners.clock_mod_list_selector
-- is the owner's draft rate. The page module (E3 handlers, K2/K3 handlers) is
-- owners.ui, else the global scale_edit_page_ui.
--
-- E3 on the Clock Mods page runs handle_scales_clock_mods_page_increment /
-- _decrement once per detent while the list selector is selected (E2 on that
-- page selects it); note the owner's increment moves the list DOWN. Each call
-- stages update_clock_mods with save_confirm and refresh_clock_mods as cancel.
--
-- CODE.SCALE.CLOCK.TARGET (spec.json discrepancies): this adapter binds the
-- EXISTING write unchanged. K3 runs save_confirm.confirm ->
-- scale_edit_page_ui.update_clock_mods, which writes clock_mods and the
-- channel division to program.get_selected_channel(); the Scale page forces
-- selected_channel = 17 (m_grid.sync_current_channel_state), while
-- refresh_clock_mods and the values described here read
-- program.get_channel(selected_song_pattern, 17). The captured target is the
-- selected channel the write will use; a target whose channel no longer
-- matches is refused so a staged rate never lands on a different channel.
-- Retargeting the write to channel 17 is out of scope for UI02.
--
-- Selected range, global cap and playable range are read-only: the existing
-- grid range gesture (scale_edit_page sequencer dual press) and the Song page
-- length fader change them. Playable range is program.get_channel_step_bounds.

local channel_target = include("mosaic/lib/ui_adapters/channel_target")

local SCALES_CHANNEL = 17

local function range_text(first, last)
  return string.format("%02d..%02d", first, last)
end

return function(ui_adapters, owners)
  local function ui() return owners.ui or scale_edit_page_ui end
  local selector = owners.clock_mod_list_selector

  local function scales_channel()
    return program.get_channel(program.get().selected_song_pattern, SCALES_CHANNEL)
  end

  local function stored_index()
    local clock_mods = scales_channel().clock_mods
    if not clock_mods then return nil end
    for index, item in ipairs(selector.list or {}) do
      if item.type == clock_mods.type and item.value == clock_mods.value then return index end
    end
    return nil
  end

  local function has_draft()
    return stored_index() ~= selector.selected_value
  end

  local function describe()
    local channel = scales_channel()
    local draft = selector:get_selected()
    local enum = {}
    for index, item in ipairs(selector.list or {}) do enum[index] = item.name end
    local stored = stored_index()
    local first = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
    local last = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])
    local cap = program.get_selected_song_pattern().global_pattern_length
    local play_first, play_last = program.get_channel_step_bounds(channel)
    return {
      {
        id = "rate", label = "Rate", short_label = selector.name, kind = "value",
        value = draft and draft.name or "NONE",
        selected = selector:is_selected(),
        domain = {min = 1, max = #enum, step = 1, enum = enum, draft_index = selector.selected_value,
          stored_index = stored, stored = stored and enum[stored] or nil,
          write_target = "selected_channel", read_channel = SCALES_CHANNEL},
        edit = function(delta)
          selector:select()
          local page = ui()
          return channel_target.per_detent(delta, function(d)
            if d > 0 then return page.handle_scales_clock_mods_page_increment() end
            return page.handle_scales_clock_mods_page_decrement()
          end)
        end
      },
      {id = "selected_range", label = "Selected range", kind = "readonly", value = range_text(first, last),
        domain = {first = first, last = last}},
      {id = "global_cap", label = "Global cap", kind = "readonly", value = tostring(cap),
        domain = {unit = "steps", steps = cap}},
      {id = "playable_range", label = "Playable range", kind = "readonly", value = range_text(play_first, play_last),
        domain = {first = play_first, last = play_last}}
    }
  end

  local function identity()
    local state = program.get()
    return tostring(state.selected_song_pattern) .. ":" .. tostring(state.selected_channel)
  end

  local function target_valid(target)
    if target == nil then return true end
    if type(target) ~= "table" then return false end
    local state = program.get()
    if target.channel ~= nil and target.channel ~= state.selected_channel then return false end
    if target.song_slot ~= nil and target.song_slot ~= state.selected_song_pattern then return false end
    return true
  end

  local adapter
  adapter = ui_adapters.new("scale_clock", {
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

  -- The target update_clock_mods writes: the selected channel (see above).
  function adapter.capture(route)
    local state = program.get()
    return {source_route = route or "S02", screen = route or "S02",
      channel = state.selected_channel, song_slot = state.selected_song_pattern}
  end

  return adapter
end

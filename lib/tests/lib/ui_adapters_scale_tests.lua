-- Characterises README.md "Scale Editor" (and "Transposition") as the UI02
-- scale and scale_clock adapters see it: the Quantizer and Clock Mods pages'
-- E3 staging, K1-at-edit scope, K3 save and K2 cancel, driven through the old
-- scale_edit_page_ui.enc/key path and through the adapters on fresh state.

local ui_adapters = include("mosaic/lib/ui_adapters")
local page_env = include("mosaic/lib/tests/helpers/ui_adapter_page_env")
local make_scale = include("mosaic/lib/ui_adapters/scale")
local make_scale_clock = include("mosaic/lib/ui_adapters/scale_clock")

local function scale_adapter(ui)
  local owners = ui.adapter_owners()
  owners.ui = ui
  return make_scale(ui_adapters, owners)
end

local function clock_adapter(ui)
  local owners = ui.adapter_owners()
  owners.ui = ui
  return make_scale_clock(ui_adapters, owners)
end

local function all_scales(slot)
  local out = {}
  for index, song_pattern in pairs(program.get().song_patterns) do
    out[index] = page_env.copy(song_pattern.scales[slot])
  end
  return out
end

local function describe(adapter, route)
  local target = adapter.capture(route)
  local outcome = adapter:describe(route, route, target, adapter:generation(target))
  luaunit.assert_true(outcome.ok, tostring(outcome.code))
  return outcome.descriptors, target
end

function test_ui_adapters_scale_describes_every_s01_field_from_the_selectors()
  page_env.isolated(function()
    local ui = page_env.load("scale")
    local adapter = scale_adapter(ui)
    local descriptors = describe(adapter, "S01")
    luaunit.assert_equals(page_env.ids(descriptors), {"root", "scale", "degree", "transpose", "rotation", "pentatonic"})
    local owners = ui.adapter_owners()
    local d = page_env.by_id(descriptors)
    luaunit.assert_equals(d.root.value, owners.notes_vertical_scroll_selector:get_selected_item())
    luaunit.assert_equals(d.scale.value, owners.quantizer_vertical_scroll_selector:get_selected_item().name)
    luaunit.assert_equals(d.degree.value, owners.romans_vertical_scroll_selector:get_selected_item())
    luaunit.assert_equals(d.transpose.value, "0")
    luaunit.assert_equals(d.rotation.value, "r0")
    luaunit.assert_equals(d.pentatonic.value, "Off")
    luaunit.assert_equals(d.pentatonic.kind, "readonly")
    -- init selects the Quantizer selector, as the page does today
    luaunit.assert_true(d.scale.selected)
    luaunit.assert_false(d.root.selected)
    luaunit.assert_equals(#d.transpose.domain.enum, 25)
    luaunit.assert_equals(#d.rotation.domain.enum, 7)
    luaunit.assert_false(adapter.impl.has_draft())
    params:set("all_scales_lock_to_pentatonic", 2)
    luaunit.assert_equals(page_env.by_id(describe(adapter, "S01")).pentatonic.value, "On")
  end)
end

function test_ui_adapters_scale_changing_family_refreshes_degree_labels()
  page_env.isolated(function()
    local ui = page_env.load("scale")
    local adapter = scale_adapter(ui)
    local target = adapter.capture("S01")
    local quantiser = include("mosaic/lib/quantiser")
    local before = page_env.by_id(describe(adapter, "S01"))
    luaunit.assert_equals(before.degree.domain.enum, quantiser.get_scales()[1].romans)
    luaunit.assert_true(adapter:edit("scale", 2, target, adapter:generation(target)).ok)
    local after = page_env.by_id(describe(adapter, "S01"))
    luaunit.assert_equals(after.scale.value, quantiser.get_scales()[3].name)
    luaunit.assert_equals(after.degree.domain.enum, quantiser.get_scales()[3].romans)
    luaunit.assert_true(after.scale.selected)
    luaunit.assert_true(adapter.impl.has_draft())
  end)
end

-- Old path: E2 from Scale to Root, E3 +2, K3. New path: adapter edit + apply.
local function old_root_edit(k1_at_edit, k1_at_confirm)
  local result
  page_env.isolated(function()
    program.get_song_pattern(2); program.get_song_pattern(3)
    local ui = page_env.load("scale")
    ui.enc(2, -1)
    is_key1_down = k1_at_edit
    ui.enc(3, 2)
    is_key1_down = k1_at_confirm
    ui.key(3, 1)
    result = {scales = all_scales(1), root = ui.adapter_owners().notes_vertical_scroll_selector:get_selected_index()}
  end)
  return result
end

local function new_root_edit(k1_at_edit, k1_at_confirm)
  local result
  page_env.isolated(function()
    program.get_song_pattern(2); program.get_song_pattern(3)
    local ui = page_env.load("scale")
    local adapter = scale_adapter(ui)
    local target = adapter.capture("S01")
    is_key1_down = k1_at_edit
    local outcome = adapter:edit("root", 2, target, adapter:generation(target))
    luaunit.assert_true(outcome.ok)
    luaunit.assert_equals(outcome.result.scope, k1_at_edit and "all_songs" or "current_song")
    is_key1_down = k1_at_confirm
    luaunit.assert_true(adapter:apply(nil, target).ok)
    result = {scales = all_scales(1), root = ui.adapter_owners().notes_vertical_scroll_selector:get_selected_index()}
  end)
  return result
end

function test_ui_adapters_scale_edit_and_apply_match_the_old_encoder_path()
  program.init()
  for _, case in ipairs({{false, false}, {true, false}, {false, true}}) do
    local old, new = old_root_edit(case[1], case[2]), new_root_edit(case[1], case[2])
    luaunit.assert_equals(new, old)
    luaunit.assert_equals(new.root, 3)
  end
end

function test_ui_adapters_scale_k1_at_edit_saves_across_songs_and_k1_at_confirm_does_not()
  program.init()
  local across = new_root_edit(true, false)
  local current = new_root_edit(false, true)
  local changed_across, changed_current = 0, 0
  for _, scale in pairs(across.scales) do if scale.root_note == 2 then changed_across = changed_across + 1 end end
  for _, scale in pairs(current.scales) do if scale.root_note == 2 then changed_current = changed_current + 1 end end
  luaunit.assert_equals(changed_across, 3)
  luaunit.assert_equals(changed_current, 1)
end

function test_ui_adapters_scale_cancel_restores_the_stored_slot()
  page_env.isolated(function()
    local ui = page_env.load("scale")
    local adapter = scale_adapter(ui)
    local target = adapter.capture("S01")
    local stored = all_scales(1)
    adapter:edit("transpose", 3, target, adapter:generation(target))
    luaunit.assert_equals(page_env.by_id(describe(adapter, "S01")).transpose.value, "+3")
    luaunit.assert_true(adapter:cancel(nil).ok)
    luaunit.assert_equals(page_env.by_id(describe(adapter, "S01")).transpose.value, "0")
    luaunit.assert_equals(all_scales(1), stored)
    luaunit.assert_false(adapter.impl.has_draft())
  end)
end

function test_ui_adapters_scale_held_keys_refuse_apply_and_cancel_without_calling_the_owner()
  page_env.isolated(function(env)
    local ui = page_env.load("scale")
    local adapter = scale_adapter(ui)
    local target = adapter.capture("S01")
    local stored = all_scales(1)
    adapter:edit("root", 1, target, adapter:generation(target))
    env.pressed = {{1, 4}}
    luaunit.assert_equals(adapter:apply(nil, target).code, "held_keys")
    luaunit.assert_equals(adapter:cancel(nil).code, "held_keys")
    luaunit.assert_equals(all_scales(1), stored)
    env.pressed = {}
    luaunit.assert_true(adapter.impl.has_draft())
  end)
end

function test_ui_adapters_scale_rejects_foreign_routes_and_stale_targets()
  page_env.isolated(function()
    local ui = page_env.load("scale")
    local adapter = scale_adapter(ui)
    local foreign = adapter:describe("A01", "A01", {source_route = "A01"})
    luaunit.assert_false(foreign.ok)
    luaunit.assert_equals(foreign.code, "foreign_route")
    luaunit.assert_equals(adapter:describe("S02", "S02", {source_route = "S02"}).code, "foreign_route")

    local target = adapter.capture("S01")
    local generation = adapter:generation(target)
    local selector = ui.adapter_owners().notes_vertical_scroll_selector
    program.get().selected_scale = 2
    local stale = adapter:edit("root", 1, target, generation)
    luaunit.assert_equals(stale.code, "stale_target")
    luaunit.assert_equals(selector:get_selected_index(), 1)
    luaunit.assert_equals(adapter:apply(nil, target).code, "stale_target")

    local fresh = adapter.capture("S01")
    luaunit.assert_equals(adapter:edit("root", 1, fresh, generation).code, "stale_generation")
    luaunit.assert_equals(selector:get_selected_index(), 1)
    luaunit.assert_true(adapter:edit("root", 1, fresh, adapter:generation(fresh)).ok)
    luaunit.assert_equals(selector:get_selected_index(), 2)
  end)
end

-- Scale clock (S02) ---------------------------------------------------------

function test_ui_adapters_scale_clock_describes_rate_and_readonly_ranges()
  page_env.isolated(function()
    local ui = page_env.load("scale")
    local adapter = clock_adapter(ui)
    program.get().selected_channel = 17
    local channel = program.get_channel(1, 17)
    channel.start_trig = {2, 4}
    channel.end_trig = {16, 4}
    program.get_selected_song_pattern().global_pattern_length = 8
    local d = page_env.by_id(describe(adapter, "S02"))
    luaunit.assert_equals(page_env.ids(describe(adapter, "S02")), {"rate", "selected_range", "global_cap", "playable_range"})
    luaunit.assert_equals(d.rate.value, "/1")
    luaunit.assert_equals(d.rate.kind, "value")
    luaunit.assert_equals(d.selected_range.value, "02..16")
    luaunit.assert_equals(d.global_cap.value, "8")
    luaunit.assert_equals(d.playable_range.value, "02..09")
    for _, id in ipairs({"selected_range", "global_cap", "playable_range"}) do
      luaunit.assert_equals(d[id].kind, "readonly")
    end
    luaunit.assert_false(adapter.impl.has_draft())
  end)
end

local function old_rate_edit()
  local result
  page_env.isolated(function(env)
    local ui = page_env.load("scale")
    program.get().selected_channel = 17
    ui.enc(1, 1)
    ui.enc(2, 1)
    ui.enc(3, -2)
    ui.key(3, 1)
    result = {mods = page_env.copy(program.get_channel(1, 17).clock_mods), set = env.divisions_set}
  end)
  return result
end

local function new_rate_edit()
  local result
  page_env.isolated(function(env)
    local ui = page_env.load("scale")
    program.get().selected_channel = 17
    local adapter = clock_adapter(ui)
    local target = adapter.capture("S02")
    luaunit.assert_true(adapter:edit("rate", -2, target, adapter:generation(target)).ok)
    luaunit.assert_true(adapter.impl.has_draft())
    luaunit.assert_true(adapter:apply(nil, target).ok)
    luaunit.assert_false(adapter.impl.has_draft())
    result = {mods = page_env.copy(program.get_channel(1, 17).clock_mods), set = env.divisions_set}
  end)
  return result
end

function test_ui_adapters_scale_clock_edit_and_apply_match_the_old_encoder_path()
  local old, new = old_rate_edit(), new_rate_edit()
  luaunit.assert_equals(new, old)
  -- E3 negative moves the owner's list up, toward faster rates: /1 -> /2
  luaunit.assert_equals(new.mods.name, "/2")
  luaunit.assert_equals(new.set[1][1], 17)
end

function test_ui_adapters_scale_clock_refuses_a_target_whose_selected_channel_moved()
  page_env.isolated(function(env)
    local ui = page_env.load("scale")
    program.get().selected_channel = 17
    local adapter = clock_adapter(ui)
    local target = adapter.capture("S02")
    local generation = adapter:generation(target)
    local selector = ui.adapter_owners().clock_mod_list_selector
    local before = selector.selected_value
    program.get().selected_channel = 3
    luaunit.assert_equals(adapter:edit("rate", 1, target, generation).code, "stale_target")
    luaunit.assert_equals(selector.selected_value, before)
    luaunit.assert_equals(adapter:apply(nil, target).code, "stale_target")
    luaunit.assert_equals(#env.divisions_set, 0)
    luaunit.assert_equals(adapter:describe("S01", "S01", {source_route = "S01"}).code, "foreign_route")
    local fresh = adapter.capture("S02")
    luaunit.assert_equals(adapter:edit("rate", 1, fresh, generation).code, "stale_generation")
    luaunit.assert_equals(selector.selected_value, before)
  end)
end

-- Characterises README.md "Song Editor" ("Song Mode Operations", "Navigating
-- the Norns Display") and "Clocks, Swing and Shuffle" (global feel) as the
-- UI02 song and song_clock adapters see them: the Song progression and Global
-- settings pages' E3 staging, K3 save and K2 cancel, driven through the old
-- song_edit_page_ui.enc/key path and through the adapters on fresh state.

local ui_adapters = include("mosaic/lib/ui_adapters")
local page_env = include("mosaic/lib/tests/helpers/ui_adapter_page_env")
local make_song = include("mosaic/lib/ui_adapters/song")
local make_song_clock = include("mosaic/lib/ui_adapters/song_clock")

local function adapter_for(make, ui)
  local owners = ui.adapter_owners()
  owners.ui = ui
  return make(ui_adapters, owners)
end

local function describe(adapter, route)
  local target = adapter.capture(route)
  local outcome = adapter:describe(route, route, target, adapter:generation(target))
  luaunit.assert_true(outcome.ok, tostring(outcome.code))
  return outcome.descriptors
end

local function model_state(env)
  return {params = page_env.copy(env.param_values), repeats = program.get_selected_song_pattern().repeats}
end

function test_ui_adapters_song_describes_repeats_and_song_mode()
  page_env.isolated(function()
    local ui = page_env.load("song")
    local adapter = adapter_for(make_song, ui)
    program.get_selected_song_pattern().repeats = 4
    ui.refresh()
    local descriptors = describe(adapter, "A01")
    luaunit.assert_equals(page_env.ids(descriptors), {"repeats", "song_mode"})
    local d = page_env.by_id(descriptors)
    luaunit.assert_equals(d.repeats.value, "4")
    luaunit.assert_equals(d.repeats.domain.min, 1)
    luaunit.assert_equals(d.repeats.domain.max, 16)
    luaunit.assert_equals(d.song_mode.value, "On")
    luaunit.assert_equals(d.song_mode.domain.enum, {"Off", "On"})
    luaunit.assert_true(d.repeats.selected)
    luaunit.assert_false(d.song_mode.selected)
    luaunit.assert_false(adapter.impl.has_draft())
  end)
end

local function old_song_edit()
  local result
  page_env.isolated(function(env)
    local ui = page_env.load("song")
    ui.enc(3, 3)
    ui.enc(2, 1)
    ui.enc(3, -1)
    ui.key(3, 1)
    result = model_state(env)
  end)
  return result
end

local function new_song_edit()
  local result
  page_env.isolated(function(env)
    local ui = page_env.load("song")
    local adapter = adapter_for(make_song, ui)
    local target = adapter.capture("A01")
    -- the owner page is elsewhere: the edit must still land on Song progression
    ui.enc(1, 1)
    luaunit.assert_true(adapter:edit("repeats", 3, target, adapter:generation(target)).ok)
    luaunit.assert_true(adapter:edit("song_mode", -1, target, adapter:generation(target)).ok)
    luaunit.assert_true(adapter.impl.has_draft())
    luaunit.assert_true(adapter:apply(nil, target).ok)
    luaunit.assert_false(adapter.impl.has_draft())
    result = model_state(env)
  end)
  return result
end

function test_ui_adapters_song_edit_and_apply_match_the_old_encoder_path()
  local old, new = old_song_edit(), new_song_edit()
  luaunit.assert_equals(new, old)
  luaunit.assert_equals(new.repeats, 4)
  luaunit.assert_equals(new.params.song_mode, 1)
end

function test_ui_adapters_song_cancel_discards_the_staged_repeats()
  page_env.isolated(function(env)
    local ui = page_env.load("song")
    local adapter = adapter_for(make_song, ui)
    local target = adapter.capture("A01")
    local before = model_state(env)
    adapter:edit("repeats", 5, target, adapter:generation(target))
    luaunit.assert_equals(page_env.by_id(describe(adapter, "A01")).repeats.value, "6")
    luaunit.assert_true(adapter:cancel(nil).ok)
    luaunit.assert_equals(page_env.by_id(describe(adapter, "A01")).repeats.value, "1")
    luaunit.assert_equals(model_state(env), before)
  end)
end

function test_ui_adapters_song_rejects_foreign_routes_and_stale_song_slots()
  page_env.isolated(function(env)
    local ui = page_env.load("song")
    local adapter = adapter_for(make_song, ui)
    luaunit.assert_equals(adapter:describe("A02", "A02", {source_route = "A02"}).code, "foreign_route")
    luaunit.assert_equals(adapter:describe("S01", "S01", {source_route = "S01"}).code, "foreign_route")
    local target = adapter.capture("A01")
    local generation = adapter:generation(target)
    local selector = ui.adapter_owners().pattern_repeat_selector
    program.set_selected_song_pattern(2)
    luaunit.assert_equals(adapter:edit("repeats", 1, target, generation).code, "stale_target")
    luaunit.assert_equals(selector:get_value(), 1)
    luaunit.assert_equals(adapter:apply(nil, target).code, "stale_target")
    local fresh = adapter.capture("A01")
    luaunit.assert_equals(adapter:edit("repeats", 1, fresh, generation).code, "stale_generation")
    luaunit.assert_equals(selector:get_value(), 1)
    luaunit.assert_equals(#env.param_sets, 0)
  end)
end

-- Song clock (A02) ----------------------------------------------------------

function test_ui_adapters_song_clock_describes_swing_and_shuffle_modes()
  page_env.isolated(function()
    local ui = page_env.load("song")
    local adapter = adapter_for(make_song_clock, ui)
    local descriptors = describe(adapter, "A02")
    luaunit.assert_equals(page_env.ids(descriptors),
      {"tempo", "swing_type", "swing", "shuffle_feel", "shuffle_basis", "shuffle_amount"})
    local d = page_env.by_id(descriptors)
    luaunit.assert_equals(d.tempo.value, "120")
    luaunit.assert_equals(d.tempo.domain.min, 30)
    luaunit.assert_equals(d.tempo.domain.max, 300)
    luaunit.assert_equals(d.swing_type.value, "Swing")
    luaunit.assert_equals(d.swing.value, "0")
    luaunit.assert_true(d.swing.visible)
    for _, id in ipairs({"shuffle_feel", "shuffle_basis", "shuffle_amount"}) do luaunit.assert_false(d[id].visible) end
    luaunit.assert_true(d.tempo.selected)

    -- the draft type switches the visible set immediately, as draw() does
    local target = adapter.capture("A02")
    adapter:edit("swing_type", 1, target, adapter:generation(target))
    d = page_env.by_id(describe(adapter, "A02"))
    luaunit.assert_equals(d.swing_type.value, "Shuffle")
    luaunit.assert_false(d.swing.visible)
    luaunit.assert_equals(d.shuffle_feel.value, "Drunk")
    luaunit.assert_equals(d.shuffle_basis.value, "9")
    luaunit.assert_equals(d.shuffle_amount.value, "0")
    for _, id in ipairs({"shuffle_feel", "shuffle_basis", "shuffle_amount"}) do luaunit.assert_true(d[id].visible) end
    luaunit.assert_true(adapter.impl.has_draft())
  end)
end

local function old_clock_edit()
  local result
  page_env.isolated(function(env)
    local ui = page_env.load("song")
    ui.enc(1, 1)
    ui.enc(3, 5)
    ui.enc(2, 1)
    ui.enc(2, 1)
    ui.enc(3, -7)
    ui.key(3, 1)
    result = model_state(env)
  end)
  return result
end

local function new_clock_edit()
  local result
  page_env.isolated(function(env)
    local ui = page_env.load("song")
    local adapter = adapter_for(make_song_clock, ui)
    local target = adapter.capture("A02")
    luaunit.assert_true(adapter:edit("tempo", 5, target, adapter:generation(target)).ok)
    luaunit.assert_true(adapter:edit("swing", -7, target, adapter:generation(target)).ok)
    luaunit.assert_true(adapter:apply(nil, target).ok)
    result = model_state(env)
  end)
  return result
end

function test_ui_adapters_song_clock_edit_and_apply_match_the_old_encoder_path()
  local old, new = old_clock_edit(), new_clock_edit()
  luaunit.assert_equals(new, old)
  luaunit.assert_equals(new.params.clock_tempo, 125)
  luaunit.assert_equals(new.params.global_swing, -7)
end

function test_ui_adapters_song_clock_rejects_foreign_routes_stale_generation_and_hidden_fields()
  page_env.isolated(function(env)
    local ui = page_env.load("song")
    local adapter = adapter_for(make_song_clock, ui)
    luaunit.assert_equals(adapter:describe("A01", "A01", {source_route = "A01"}).code, "foreign_route")
    local target = adapter.capture("A02")
    local tempo = ui.adapter_owners().tempo_selector
    luaunit.assert_equals(adapter:edit("tempo", 1, target, 1).code, "stale_generation")
    luaunit.assert_equals(tempo:get_value(), 120)
    -- a hidden shuffle field is refused without touching the owner
    luaunit.assert_equals(adapter:edit("shuffle_amount", 1, target, 0).code, "disabled")
    luaunit.assert_equals(ui.adapter_owners().shuffle_amount_selector:get_value(), 0)
    luaunit.assert_equals(#env.param_sets, 0)
  end)
end

-- Characterises README.md "Adding Trigs" (the Tresillo algorithm's amount on
-- the Trig editor options page) as the UI02 trig_options adapter sees it: E3
-- sets the native tresillo_amount option immediately, driven through the old
-- trigger_edit_page_ui.enc path and through the adapter on fresh state. The
-- Rhythm Doctor (algorithm 5) owns the encoders and is out of scope here.

local ui_adapters = include("mosaic/lib/ui_adapters")
local page_env = include("mosaic/lib/tests/helpers/ui_adapter_page_env")
local make_trig_options = include("mosaic/lib/ui_adapters/trig_options")

local function adapter_for(ui)
  local owners = ui.adapter_owners()
  owners.ui = ui
  return make_trig_options(ui_adapters, owners)
end

local function describe(adapter)
  local target = adapter.capture("P02")
  local outcome = adapter:describe("P02", "P02", target, adapter:generation(target))
  luaunit.assert_true(outcome.ok, tostring(outcome.code))
  return outcome.descriptors
end

function test_ui_adapters_trig_options_describes_the_amount_at_both_ends()
  page_env.isolated(function()
    local ui = page_env.load("trig")
    local adapter = adapter_for(ui)
    local descriptors = describe(adapter)
    -- Owner decision 2026-09-25: the setting only; the explanation rows are gone.
    luaunit.assert_equals(page_env.ids(descriptors), {"tresillo_amount"})
    local d = page_env.by_id(descriptors)
    luaunit.assert_equals(d.tresillo_amount.value, "x24")
    luaunit.assert_equals(d.tresillo_amount.domain.values, {8, 16, 24, 32, 40, 48, 56, 64})
    luaunit.assert_equals(d.tresillo_amount.domain.enum, {"x8", "x16", "x24", "x32", "x40", "x48", "x56", "x64"})
    luaunit.assert_true(d.tresillo_amount.enabled)
    local target = adapter.capture("P02")
    adapter:edit("tresillo_amount", -20, target, 0)
    luaunit.assert_equals(page_env.by_id(describe(adapter)).tresillo_amount.value, "x8")
    adapter:edit("tresillo_amount", 20, target, 0)
    luaunit.assert_equals(page_env.by_id(describe(adapter)).tresillo_amount.value, "x64")
  end)
end

local function old_path()
  local result
  page_env.isolated(function(env)
    local ui = page_env.load("trig")
    ui.enc(1, 1)
    ui.enc(3, 2)
    ui.enc(3, -1)
    result = {params = page_env.copy(env.param_values), sets = page_env.copy(env.param_sets)}
  end)
  return result
end

local function new_path()
  local result
  page_env.isolated(function(env)
    local ui = page_env.load("trig")
    local adapter = adapter_for(ui)
    local target = adapter.capture("P02")
    luaunit.assert_true(adapter:edit("tresillo_amount", 2, target, 0).ok)
    luaunit.assert_true(adapter:edit("tresillo_amount", -1, target, 0).ok)
    result = {params = page_env.copy(env.param_values), sets = page_env.copy(env.param_sets)}
  end)
  return result
end

function test_ui_adapters_trig_options_edit_matches_the_old_encoder_path()
  local old, new = old_path(), new_path()
  luaunit.assert_equals(new, old)
  luaunit.assert_equals(new.params.tresillo_amount, 4)
  luaunit.assert_equals(#new.sets, 3)
end

function test_ui_adapters_trig_options_refuses_while_the_rhythm_doctor_owns_input()
  page_env.isolated(function(env)
    local ui = page_env.load("trig")
    local adapter = adapter_for(ui)
    env.algorithm = 5
    local d = page_env.by_id(describe(adapter))
    luaunit.assert_false(d.tresillo_amount.enabled)
    luaunit.assert_equals(d.tresillo_amount.domain.reason, "rhythm_doctor_owns_input")
    luaunit.assert_equals(adapter:edit("tresillo_amount", 1, adapter.capture("P02"), 0).code, "disabled")
    luaunit.assert_equals(#env.param_sets, 0)
  end)
end

function test_ui_adapters_trig_options_rejects_foreign_routes_and_stale_generation()
  page_env.isolated(function(env)
    local ui = page_env.load("trig")
    local adapter = adapter_for(ui)
    local foreign = adapter:describe("P01", "P01", {source_route = "P01"})
    luaunit.assert_false(foreign.ok)
    luaunit.assert_equals(foreign.code, "foreign_route")
    luaunit.assert_equals(adapter:describe("R01", "R01", {source_route = "R01"}).code, "foreign_route")
    luaunit.assert_equals(adapter:edit("tresillo_amount", 1, adapter.capture("P02"), 7).code, "stale_generation")
    luaunit.assert_equals(#env.param_sets, 0)
    luaunit.assert_equals(ui.adapter_owners().tresillo_mult:get_selected().value, 24)
  end)
end

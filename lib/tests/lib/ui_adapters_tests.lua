-- Characterisation of the UI02 adapter protocol (docs/ui-reimplementation
-- spec.json#/provider_protocol). Outside the manual: presentation plumbing only.

local ui_adapters = include("mosaic/lib/ui_adapters")

local function fake(owner)
  owner = owner or {generation = 1, value = 3, invoked = 0}
  return ui_adapters.new("history", {
    generation = function() return owner.generation end,
    describe = function(route)
      return {
        {id = "position", label = "Position", kind = "value", value = owner.value,
          edit = function(delta) owner.value = owner.value + delta; return owner.value end},
        {id = "undo_all", label = "Undo all", kind = "action", invoke = function() owner.invoked = owner.invoked + 1 end},
        {id = "hidden", label = "Hidden", kind = "value", visible = false, edit = function() error("hidden edited") end}
      }
    end
  }), owner
end

function test_ui_adapters_owned_routes_follow_the_spec_route_map()
  luaunit.assert_true(ui_adapters.owns_route("merge", "M01"))
  luaunit.assert_false(ui_adapters.owns_route("merge", "H01"))
  luaunit.assert_true(ui_adapters.owns_route("harmony", "H04_DELETE"))
  luaunit.assert_true(ui_adapters.owns_route("parameters", "C13"))
  luaunit.assert_false(ui_adapters.owns_route("parameters", "C01"))
  luaunit.assert_true(ui_adapters.owns_route("history", "C03"))
  luaunit.assert_equals(ui_adapters.translate_route("merge", "M04"), "M06")
end

function test_ui_adapters_snapshot_routes_exist_only_for_visual_variants()
  luaunit.assert_true(ui_adapters.owns_route("merge", "snapshot:M04"))
  luaunit.assert_true(ui_adapters.owns_route("harmony", "snapshot:M10"))
  luaunit.assert_false(ui_adapters.owns_route("merge", "snapshot:M02"))
  luaunit.assert_false(ui_adapters.owns_route("merge", "snapshot:H14"))
end

function test_ui_adapters_every_screen_existing_route_has_an_owner()
  for id, screen in pairs(ui_adapters.spec.screens) do
    if screen.existing_route and not screen.existing_route:match("^snapshot:") then
      luaunit.assert_true(ui_adapters.owns_route(screen.provider, screen.existing_route),
        id .. " route " .. screen.existing_route .. " is not owned by " .. screen.provider)
    end
  end
end

function test_ui_adapters_describe_rejects_a_foreign_route_with_an_error_outcome()
  local adapter = fake()
  local outcome = adapter:describe("M02", "M01", {source_route = "M01"})
  luaunit.assert_false(outcome.ok)
  luaunit.assert_equals(outcome.code, "foreign_route")
  luaunit.assert_nil(outcome.descriptors)
end

function test_ui_adapters_describe_normalises_descriptors_and_keeps_closures()
  local adapter = fake()
  local outcome = adapter:describe("C03", "C03", {source_route = "C03"})
  luaunit.assert_true(outcome.ok)
  luaunit.assert_equals(outcome.descriptors[1].value, "3")
  luaunit.assert_equals(outcome.descriptors[1].short_label, "Position")
  luaunit.assert_true(outcome.descriptors[1].enabled)
  luaunit.assert_equals(type(outcome.descriptors[1].edit), "function")
  luaunit.assert_equals(outcome.owner_generation, 1)
end

function test_ui_adapters_edit_runs_the_owner_closure_once_and_ignores_zero_delta()
  local adapter, owner = fake()
  local target = {source_route = "C03"}
  luaunit.assert_equals(adapter:edit("position", 0, target, 1).code, "zero_delta")
  luaunit.assert_equals(owner.value, 3)
  local outcome = adapter:edit("position", 2, target, 1)
  luaunit.assert_true(outcome.ok)
  luaunit.assert_equals(outcome.result, 5)
  luaunit.assert_equals(owner.value, 5)
end

function test_ui_adapters_edit_rejects_stale_generation_hidden_and_wrong_kind()
  local adapter, owner = fake()
  local target = {source_route = "C03"}
  luaunit.assert_equals(adapter:edit("position", 1, target, 0).code, "stale_generation")
  luaunit.assert_equals(adapter:edit("hidden", 1, target, 1).code, "disabled")
  luaunit.assert_equals(adapter:edit("undo_all", 1, target, 1).code, "wrong_kind")
  luaunit.assert_equals(adapter:edit("missing", 1, target, 1).code, "unknown_field")
  luaunit.assert_equals(owner.value, 3)
end

function test_ui_adapters_invoke_runs_action_once()
  local adapter, owner = fake()
  local outcome = adapter:invoke("undo_all", {source_route = "C03"}, 1)
  luaunit.assert_true(outcome.ok)
  luaunit.assert_equals(owner.invoked, 1)
end

function test_ui_adapters_duplicate_ids_are_refused()
  local adapter = ui_adapters.new("history", {describe = function()
    return {{id = "a", label = "A", kind = "readonly"}, {id = "a", label = "B", kind = "readonly"}}
  end})
  luaunit.assert_error_msg_contains("duplicate descriptor id a", function()
    adapter:describe("C03", "C03", {source_route = "C03"})
  end)
end

function test_ui_adapters_descriptor_filter_views_select_and_require()
  local drafted = false
  local adapter = ui_adapters.new("parameters", {
    has_draft = function() return drafted end,
    describe = function(route)
      luaunit.assert_nil(route)
      return {
        {id = "slot_1", label = "Chord 1", kind = "value", domain = {assigned_parameter_id = "chord_1_note"}},
        {id = "slot_2", label = "CC74", kind = "value", selected = true, domain = {assigned_parameter_id = "cc74"}}
      }
    end
  })
  local all = adapter:describe("C02", "C02", {source_route = "C02"})
  luaunit.assert_equals(#all.descriptors, 2)
  local chords = adapter:describe("C10", "C10", {source_route = "C10"})
  luaunit.assert_equals(#chords.descriptors, 1)
  luaunit.assert_equals(chords.descriptors[1].id, "slot_1")
  local selected = adapter:describe("C13", "C13", {source_route = "C13"})
  luaunit.assert_equals(selected.descriptors[1].id, "slot_2")
  luaunit.assert_equals(adapter:describe("F08", "F08", {source_route = "F08"}).code, "requires_held")
  local held = adapter:describe("F08", "F08", {source_route = "F08", held = {3}})
  luaunit.assert_true(held.ok)
end

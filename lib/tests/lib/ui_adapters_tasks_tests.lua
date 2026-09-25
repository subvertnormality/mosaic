-- Characterisation of the UI02 tasks provider (docs/ui-reimplementation
-- spec.json#/tasks). Outside the manual: the task navigators are new
-- presentation code with no README section; spec.tasks is the only authority.

local ui_adapters = include("mosaic/lib/ui_adapters")
local tasks_factory = include("mosaic/lib/ui_adapters/tasks")

local function ids(outcome)
  local out = {}
  for _, d in ipairs(outcome.descriptors) do out[#out + 1] = d.id end
  return out
end

local function row_ids(rows)
  local out = {}
  for _, row in ipairs(rows) do out[#out + 1] = row.id end
  return out
end

local function describe(adapter, route, target)
  target = target or {}
  target.source_route, target.screen = route, route
  return adapter:describe(route, route, target)
end

function test_ui_adapters_tasks_navigator_fields_equal_the_spec_rows_in_order()
  local adapter = tasks_factory(ui_adapters)
  for _, route in ipairs({"N01", "N02", "N05"}) do
    local outcome = describe(adapter, route)
    luaunit.assert_true(outcome.ok, route)
    luaunit.assert_equals(ids(outcome), row_ids(ui_adapters.spec.tasks.rows[route]), route)
    luaunit.assert_equals(ids(outcome), ui_adapters.spec.screens[route].fields, route)
    for index, d in ipairs(outcome.descriptors) do
      local row = ui_adapters.spec.tasks.rows[route][index]
      luaunit.assert_equals(d.label, row.label)
      luaunit.assert_equals(d.kind, "action")
      luaunit.assert_equals(d.domain.destination, row.screen or row.native)
    end
  end
end

function test_ui_adapters_tasks_n03_resolves_the_pattern_row_by_context_and_hides_trig_only_rows()
  local adapter = tasks_factory(ui_adapters)
  local note = describe(adapter, "N03", {context = "Note", state = {algorithm = 5}})
  luaunit.assert_equals(ids(note), {"pattern", "channel_view"})
  luaunit.assert_equals(note.descriptors[1].value, "P03")
  local velocity = describe(adapter, "N03", {context = "Velocity"})
  luaunit.assert_equals(velocity.descriptors[1].domain.destination, "P04")
  local trig = describe(adapter, "N03", {context = "Trig", state = {algorithm = 1}})
  luaunit.assert_equals(ids(trig), {"pattern", "options", "algorithm", "channel_view"})
  luaunit.assert_equals(trig.descriptors[1].value, "P01")
end

function test_ui_adapters_tasks_rhythm_doctor_row_follows_the_trig_algorithm_owner_state()
  local algorithm = 1
  local adapter = tasks_factory(ui_adapters, {state = function() return {algorithm = algorithm} end})
  luaunit.assert_equals(ids(describe(adapter, "N03", {context = "Trig"})), {"pattern", "options", "algorithm", "channel_view"})
  algorithm = 5
  local outcome = describe(adapter, "N03", {context = "Trig"})
  luaunit.assert_equals(ids(outcome), ui_adapters.spec.screens.N03.fields)
  luaunit.assert_equals(outcome.descriptors[5].domain.destination, "R01")
  -- no state source at all: the conditional row stays hidden
  luaunit.assert_equals(ids(describe(tasks_factory(ui_adapters), "N03", {context = "Trig"})), {"pattern", "options", "algorithm", "channel_view"})
end

function test_ui_adapters_tasks_invoke_names_the_destination_without_navigating()
  local adapter = tasks_factory(ui_adapters)
  local target = {source_route = "N01", screen = "N01"}
  local outcome = adapter:invoke("harmony", target)
  luaunit.assert_true(outcome.ok)
  luaunit.assert_equals(outcome.code, "open_screen")
  luaunit.assert_equals(outcome.destination, "H01")
  luaunit.assert_equals(outcome.field, "harmony")
  local trig = adapter:invoke("pattern", {source_route = "N03", screen = "N03", context = "Trig"})
  luaunit.assert_equals(trig.destination, "P01")
end

function test_ui_adapters_tasks_m01_lists_its_fields_from_the_channel_rows()
  local adapter = tasks_factory(ui_adapters)
  local outcome = describe(adapter, "M01")
  luaunit.assert_true(outcome.ok)
  luaunit.assert_equals(ids(outcome), ui_adapters.spec.screens.M01.fields)
  luaunit.assert_equals(outcome.descriptors[1].domain.destination, "C06")
end

function test_ui_adapters_tasks_every_tasks_screen_field_is_covered_at_maximum_cardinality()
  local adapter = tasks_factory(ui_adapters, {state = function() return {algorithm = 5} end})
  for id, screen in pairs(ui_adapters.spec.screens) do
    if screen.provider == "tasks" then
      local seen = {}
      for _, context in ipairs(screen.context) do
        local outcome = describe(adapter, screen.existing_route, {context = context})
        luaunit.assert_true(outcome.ok, id)
        for _, d in ipairs(outcome.descriptors) do seen[d.id] = true end
      end
      for _, field in ipairs(screen.fields) do luaunit.assert_true(seen[field], id .. " misses " .. field) end
    end
  end
end

function test_ui_adapters_tasks_rejects_foreign_routes_missing_context_and_hidden_rows()
  local adapter = tasks_factory(ui_adapters)
  local foreign = describe(adapter, "C06")
  luaunit.assert_false(foreign.ok)
  luaunit.assert_equals(foreign.code, "foreign_route")
  luaunit.assert_nil(foreign.descriptors)
  local missing = describe(adapter, "N03")
  luaunit.assert_false(missing.ok)
  luaunit.assert_equals(missing.code, "missing_context")
  local hidden = adapter:invoke("options", {source_route = "N03", screen = "N03", context = "Note"})
  luaunit.assert_false(hidden.ok)
  luaunit.assert_equals(hidden.code, "unknown_field")
end

function test_ui_adapters_tasks_refuses_a_stale_generation()
  local adapter = tasks_factory(ui_adapters)
  local outcome = adapter:invoke("masks", {source_route = "N01", screen = "N01"}, 7)
  luaunit.assert_false(outcome.ok)
  luaunit.assert_equals(outcome.code, "stale_generation")
end

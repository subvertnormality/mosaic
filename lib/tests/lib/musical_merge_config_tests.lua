-- README.md Musical Merge persistence: the requested configuration is saved,
-- missing fields are Off, and invalid/unknown optional schemas fail closed.

local loaded, config = pcall(include, "mosaic/lib/musical_merge/config")

function test_musical_merge_config_module_exists()
  luaunit.assert_true(loaded)
end

function test_musical_merge_config_default_is_complete_and_foundation_is_opt_in()
  local value = config.new()
  luaunit.assert_equals(value.schema_version, 1)
  luaunit.assert_equals(value.mode, "off")
  luaunit.assert_equals(value.amount, 100)
  luaunit.assert_equals(value.accent, 70)
  luaunit.assert_equals(value.gap, 0)
  luaunit.assert_equals(value.cycles, 1)
  luaunit.assert_equals(value.percentages, {100})
  luaunit.assert_equals(value.variation, "fixed")
  luaunit.assert_equals(value.target.kind, "legacy")
end

function test_musical_merge_config_exact_named_curves_for_every_cycle_count()
  luaunit.assert_equals(config.curve("flat", 8), {100, 100, 100, 100, 100, 100, 100, 100})
  luaunit.assert_equals(config.curve("build", 2), {50, 100})
  luaunit.assert_equals(config.curve("build", 4), {25, 50, 75, 100})
  luaunit.assert_equals(config.curve("build", 8), {13, 25, 38, 50, 63, 75, 88, 100})
  luaunit.assert_equals(config.curve("answer", 4), {100, 25, 100, 25})
  luaunit.assert_equals(config.curve("fill", 4), {25, 25, 25, 100})
  for _, name in ipairs({"flat", "build", "answer", "fill"}) do
    luaunit.assert_equals(config.curve(name, 1), {100})
  end
end

function test_musical_merge_config_rejects_every_invalid_domain_without_mutation()
  local cases = {
    {"schema_version", 2, "merge schema version"}, {"mode", "magic", "merge mode"},
    {"anchor", 17, "merge anchor"}, {"amount", 101, "merge amount"},
    {"accent", -1, "merge accent"}, {"gap", 9, "merge gap"},
    {"seed", 65536, "merge seed"}, {"ranking_version", 2, "merge ranking version"},
    {"cycles", 3, "merge cycles"}, {"variation", "random", "merge variation"}
  }
  for _, case in ipairs(cases) do
    local value = config.new()
    value[case[1]] = case[2]
    luaunit.assert_equals(({config.validate(value)})[2], case[3], case[1])
  end
end

function test_musical_merge_config_validates_curve_and_target_identity()
  local value = config.new()
  value.mode = "foundation"
  value.anchor = 1
  value.cycles = 4
  value.percentages = {25, 50, 75}
  luaunit.assert_equals(({config.validate(value)})[2], "merge percentages")
  value.percentages = {25, 50, 75, 100}
  value.target = {kind = "degrees", degrees = {}}
  luaunit.assert_equals(({config.validate(value)})[2], "merge target degrees")
  value.target = {kind = "chord", group_id = 17}
  luaunit.assert_equals(({config.validate(value)})[2], "merge target group")
  value.target = {kind = "degrees", degrees = {1, 3, 5}}
  luaunit.assert_true(config.validate(value))
end


-- README.md Musical Merge persistence: the requested configuration is saved,
-- missing fields are Off, and invalid/unknown optional schemas fail closed.

local loaded, config = pcall(include, "mosaic/lib/musical_merge/config")

function test_musical_merge_config_module_exists()
  luaunit.assert_true(loaded)
end

function test_musical_merge_config_default_is_complete_and_foundation_is_opt_in()
  local value = config.new()
  luaunit.assert_equals(value.schema_version, 2)
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
    {"schema_version", 3, "merge schema version"}, {"mode", "magic", "merge mode"},
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

-- Schema v2 and v1 migration. Contract: docs/musical-merge-extensions-plan.md §0
-- (Schema and migration). README "Musical Merge and Voice Leading" requires
-- missing optional configuration to load as Off and unknown schema versions to
-- reject; the v2 field set itself is a characterisation of the approved plan.

local function v2_defaults()
  return {
    schema_version = 2, mode = "off", anchor = nil, amount = 100, accent = 70, gap = 0, seed = 0,
    ranking_version = 1, cycles = 1, shape = "flat", percentages = {100}, variation = "fixed",
    keep_anchor_pitch = false, target = {kind = "legacy"},
    interlock = {leader = nil, window = 0}, space = {leader = nil, release = 0},
    fragments = {size = 8, keep_anchor = false}, structure = {markers = "off", group_id = nil}
  }
end

local function v1_foundation()
  return {
    schema_version = 1, mode = "foundation", anchor = 3, amount = 37, accent = 55, gap = 2, seed = 4242,
    ranking_version = 1, cycles = 4, shape = "custom", percentages = {10, 40, 70, 99},
    variation = "per_phrase", keep_anchor_pitch = true, target = {kind = "degrees", degrees = {1, 3, 5}}
  }
end

function test_musical_merge_config_v2_default_has_every_new_field_at_its_default()
  luaunit.assert_equals(config.new(), v2_defaults())
  luaunit.assert_true(config.validate(config.new()))
end

function test_musical_merge_config_v2_new_field_domains()
  local cases = {
    {function(v) v.mode = "fragments" end, true},
    {function(v) v.interlock.leader = 16;v.interlock.window = 4 end, true},
    {function(v) v.interlock.leader = 0 end, "merge interlock"},
    {function(v) v.interlock.leader = 17 end, "merge interlock"},
    {function(v) v.interlock.window = 5 end, "merge interlock"},
    {function(v) v.interlock.window = 1.5 end, "merge interlock"},
    -- §0: space is reserved and inert; only {leader = nil, release = 0}.
    {function(v) v.space.leader = 1;v.space.release = 4 end, "merge space"},
    {function(v) v.space.leader = 2 end, "merge space"},
    {function(v) v.space.release = 1 end, "merge space"},
    {function(v) v.space.release = 0.5 end, "merge space"},
    {function(v) v.space.release = nil end, "merge space"},
    {function(v) v.space = nil end, "merge space"},
    {function(v) v.space.leader = 17 end, "merge space"},
    {function(v) v.space.release = -1 end, "merge space"},
    {function(v) v.fragments.size = 16;v.fragments.keep_anchor = true;v.anchor = 2 end, true},
    {function(v) v.fragments.size = 4 end, true},
    {function(v) v.fragments.size = 6 end, "merge fragments"},
    {function(v) v.fragments.keep_anchor = 1 end, "merge fragments"},
    {function(v) v.mode = "fragments";v.fragments.keep_anchor = true end, "merge anchor"},
    {function(v) v.structure.markers = "every_4";v.structure.group_id = 3 end, true},
    {function(v) v.structure.markers = "anchors" end, "merge structure"},
    {function(v) v.structure.markers = "every_2";v.structure.group_id = 3 end, "merge structure"},
    {function(v) v.structure.markers = "every_8";v.structure.group_id = 17 end, "merge structure"},
    {function(v) v.interlock = nil end, "merge interlock"},
    {function(v) v.fragments = "on" end, "merge fragments"}
  }
  for index, case in ipairs(cases) do
    local value = config.new();case[1](value)
    local ok, reason = config.validate(value)
    if case[2] == true then luaunit.assert_true(ok, index) else luaunit.assert_equals(reason, case[2], index) end
  end
end

function test_musical_merge_config_v2_leader_cannot_name_its_own_channel()
  local value = config.new();value.interlock.leader = 5
  luaunit.assert_true(config.validate(value, 4))
  luaunit.assert_equals(({config.validate(value, 5)})[2], "merge interlock")
  value = config.new();value.space.leader = 9
  luaunit.assert_equals(({config.validate(value, 9)})[2], "merge space")
  luaunit.assert_equals(({config.validate(value, 4)})[2], "merge space")
end

function test_musical_merge_config_v2_schema_is_closed_at_every_level()
  local cases = {
    {function(v) v.extra = true end, "merge field"},
    {function(v) v.target.extra = 1 end, "merge target"},
    {function(v) v.target = {kind = "scale", degrees = {1}} end, "merge target"},
    {function(v) v.target = {kind = "degrees", degrees = {1, 3, extra = 2}} end, "merge target degrees"},
    {function(v) v.percentages.extra = 1 end, "merge percentages"},
    {function(v) v.interlock.extra = 1 end, "merge interlock"},
    {function(v) v.space.extra = 1 end, "merge space"},
    {function(v) v.fragments.extra = 1 end, "merge fragments"},
    {function(v) v.structure.extra = 1 end, "merge structure"}
  }
  for index, case in ipairs(cases) do
    local value = config.new();case[1](value)
    luaunit.assert_equals(({config.validate(value)})[2], case[2], index)
  end
end

function test_musical_merge_config_v1_validator_rejects_v2_and_v2_rejects_v1()
  luaunit.assert_true(config.validate_v1(v1_foundation()))
  luaunit.assert_equals(({config.validate(v1_foundation())})[2], "merge schema version")
  luaunit.assert_equals(({config.validate_v1(config.new())})[2], "merge schema version")
  local fragments_v1 = v1_foundation();fragments_v1.mode = "fragments"
  luaunit.assert_equals(({config.canonicalize(fragments_v1)})[2], "merge mode")
end

function test_musical_merge_config_v1_migrates_recognized_fields_and_discards_everything_else()
  local saved = v1_foundation()
  saved.unknown = "kept nowhere"
  saved.target.extra = {nested = true}
  saved.interlock = {leader = 2, window = 3}
  saved.space = "collides"
  saved.fragments = {size = 4, keep_anchor = true}
  saved.structure = {markers = "anchors", group_id = 1}
  local original = config.canonicalize(v1_foundation())
  local migrated = config.canonicalize(saved)
  local expected = v2_defaults()
  expected.mode, expected.anchor, expected.amount, expected.accent = "foundation", 3, 37, 55
  expected.gap, expected.seed, expected.cycles, expected.shape = 2, 4242, 4, "custom"
  expected.percentages, expected.variation, expected.keep_anchor_pitch = {10, 40, 70, 99}, "per_phrase", true
  expected.target = {kind = "degrees", degrees = {1, 3, 5}}
  luaunit.assert_equals(migrated, expected)
  luaunit.assert_equals(original, expected)
  luaunit.assert_true(config.validate(migrated))
  -- The v1 source is not mutated and nothing aliases it.
  luaunit.assert_equals(saved.unknown, "kept nowhere")
  luaunit.assert_false(migrated.target == saved.target)
  luaunit.assert_false(migrated.percentages == saved.percentages)
end

function test_musical_merge_config_v1_target_fields_copy_by_kind_only()
  for _, case in ipairs({
    {{kind = "legacy", group_id = 4, degrees = {1}}, {kind = "legacy"}},
    {{kind = "scale", group_id = 4}, {kind = "scale"}},
    {{kind = "chord", group_id = 4, degrees = {1}}, {kind = "chord", group_id = 4}},
    {{kind = "degrees", degrees = {2, 4}, group_id = 4}, {kind = "degrees", degrees = {2, 4}}}
  }) do
    local saved = v1_foundation();saved.target = case[1]
    luaunit.assert_equals(config.canonicalize(saved).target, case[2])
  end
end

function test_musical_merge_config_v1_off_migrates_to_v2_off()
  local saved = {schema_version = 1, mode = "off", amount = 100, accent = 70, gap = 0, seed = 0,
    ranking_version = 1, cycles = 1, shape = "flat", percentages = {100}, variation = "fixed",
    keep_anchor_pitch = false, target = {kind = "legacy"}}
  luaunit.assert_equals(config.canonicalize(saved), v2_defaults())
end

function test_musical_merge_config_canonicalization_is_idempotent_and_rejects_before_copying()
  local once = config.canonicalize(v1_foundation())
  luaunit.assert_equals(config.canonicalize(once), once)
  luaunit.assert_equals(config.canonicalize(config.canonicalize(once)), once)
  local inactive = config.new();inactive.structure.group_id = 5
  luaunit.assert_nil(config.canonicalize(inactive).structure.group_id)
  local bad = v1_foundation();bad.amount = 101
  luaunit.assert_equals({config.canonicalize(bad)}, {nil, "merge amount"})
  luaunit.assert_equals({config.canonicalize({schema_version = 3})}, {nil, "merge schema version"})
  luaunit.assert_equals({config.canonicalize("off")}, {nil, "merge schema version"})
  local unknown = config.new();unknown.extra = 1
  luaunit.assert_equals({config.canonicalize(unknown)}, {nil, "merge field"})
end

-- §0 / §6: the reserved `space` field is inert. Canonicalization of v2 keeps
-- only the inert value (a fresh table) and rejects anything else; a v1 key
-- named `space` is discarded whatever it holds.
function test_musical_merge_config_space_field_is_reserved_and_inert()
  local value = config.new()
  local canonical = config.canonicalize(value)
  luaunit.assert_equals(canonical.space, {leader = nil, release = 0})
  luaunit.assert_false(canonical.space == value.space)
  for _, space in ipairs({{leader = 3, release = 0}, {leader = nil, release = 2}, {leader = 3, release = 4}}) do
    local bad = config.new();bad.space = space
    luaunit.assert_equals({config.canonicalize(bad, 1)}, {nil, "merge space"})
  end
  local v1 = v1_foundation();v1.space = {leader = 2, release = 4}
  luaunit.assert_equals(config.canonicalize(v1).space, {leader = nil, release = 0})
end

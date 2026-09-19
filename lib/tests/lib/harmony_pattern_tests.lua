-- README.md Voice leading: Pattern mappings preserve recurring effective-value
-- identity, keep Raw events untouched and fail closed on conflicting aliases.

local runtime = include("mosaic/lib/harmony/pattern")
local config = include("mosaic/lib/harmony/config")

local function channel()
  local value = config.new_channel("pattern")
  value.roles.v1 = {min=48,max=60,centre=54,preferred_leap=12,strict_leap=false,enabled=true}
  value.roles.v2 = {min=52,max=72,centre=60,preferred_leap=12,strict_leap=false,enabled=true}
  return value
end

function test_harmony_pattern_binding_is_source_configuration_not_contents_or_ui()
  local a = {selected_patterns={[4]=true,[2]=true}, note_merge_mode="average",
    velocity_merge_mode="up", length_merge_mode="down"}
  local b = {selected_patterns={[2]=true,[4]=true}, note_merge_mode="average",
    velocity_merge_mode="up", length_merge_mode="down"}
  luaunit.assert_equals(runtime.binding_key(a), runtime.binding_key(b))
  b.note_merge_mode = "pattern_number_7"
  luaunit.assert_not_equals(runtime.binding_key(a), runtime.binding_key(b))
end

function test_harmony_pattern_repeated_identity_reuses_one_pitch_and_raw_is_legacy()
  local c = channel()
  local binding = "binding"
  c.pattern_maps[binding] = {schema_version=1, revision=1,
    assignments={["0"]="bass", ["2"]="inner1"}}
  local result = runtime.prepare({}, 1, "scale-a", binding,
    {[0]=60, [2]=64, [7]=79}, c)
  luaunit.assert_equals(result.status, "ok")
  luaunit.assert_equals(runtime.pitch_for(result, 2, 64), runtime.pitch_for(result, 2, 64))
  luaunit.assert_equals(runtime.pitch_for(result, 7, 79), 79)
end

function test_harmony_pattern_alias_conflict_fails_closed_without_touching_raw()
  local c = channel()
  c.pattern_maps.b = {schema_version=1, revision=2,
    assignments={["0"]="bass", ["7"]="bass"}}
  local result = runtime.prepare({}, 1, "scale-b", "b", {[0]=60,[7]=67,[9]=81}, c)
  luaunit.assert_equals(result.status, "alias_conflict")
  luaunit.assert_nil(runtime.pitch_for(result, 0, 60))
  luaunit.assert_equals(runtime.pitch_for(result, 9, 81), 81)
end

function test_harmony_pattern_binding_includes_foundation_pitch_identity()
  local c = {selected_patterns={[1]=true}, note_merge_mode="average",
    velocity_merge_mode="average", length_merge_mode="average",
    musical_merge={keep_anchor_pitch=true,target={kind="degrees",degrees={1,3,5}}}}
  local first = runtime.binding_key(c)
  c.musical_merge.target.degrees = {1,4,5}
  luaunit.assert_not_equals(runtime.binding_key(c), first)
end

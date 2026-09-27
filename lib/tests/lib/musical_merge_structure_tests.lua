-- Structural chord tones (MM-10) pure policy. Contract:
-- docs/musical-merge-extensions-plan.md §4 (markers, chord source, shared pitch
-- resolution, between-marker rule, persisted Pattern identity, reference repair).
-- README "Merge Shape" still lists passing-note freedom as a later design until
-- the MM-11 UI/docs card, so every assertion here is a characterisation of that
-- approved contract, outside the current manual.

local loaded, structure = pcall(include, "mosaic/lib/musical_merge/structure")
local pitch_target = include("mosaic/lib/musical_merge/pitch_target")
local merge_config = include("mosaic/lib/musical_merge/config")

local function sorted_keys(set)
  local result = {}
  for key, value in pairs(set) do if value then result[#result + 1] = key end end
  table.sort(result)
  return result
end

local function span(first, last)
  local result = {}
  for step = first, last do result[#result + 1] = step end
  return result
end

local function foundation(markers, group_id)
  local value = merge_config.new()
  value.mode, value.anchor = "foundation", 1
  value.structure = {markers = markers, group_id = group_id}
  return value
end

function test_structure_module_loads()
  luaunit.assert_true(loaded, tostring(structure))
end

-- §4 Markers: every_4 / every_8 count p1, p5, p9 … / p1, p9 … of the playable
-- positions from the loop's own first position, whether or not an onset lands.
function test_structure_every_n_markers_count_from_nonzero_loop_start()
  luaunit.assert_equals(sorted_keys(structure.markers("every_4", span(3, 18), {})), {3, 7, 11, 15})
  luaunit.assert_equals(sorted_keys(structure.markers("every_8", span(3, 18), {})), {3, 11})
  luaunit.assert_equals(sorted_keys(structure.markers("every_4", span(1, 64), {})),
    {1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61})
  luaunit.assert_equals(sorted_keys(structure.markers("every_8", span(1, 64), {})),
    {1, 9, 17, 25, 33, 41, 49, 57})
end

function test_structure_short_loops_mark_only_their_first_position()
  luaunit.assert_equals(sorted_keys(structure.markers("every_4", span(10, 12), {})), {10})
  luaunit.assert_equals(sorted_keys(structure.markers("every_8", span(10, 16), {})), {10})
  luaunit.assert_equals(sorted_keys(structure.markers("every_4", {33}, {})), {33})
  luaunit.assert_equals(sorted_keys(structure.markers("every_8", span(5, 13), {})), {5, 13})
end

-- §4 anchors: every Foundation anchor onset position inside the playable range.
function test_structure_anchor_markers_are_foundation_anchor_positions()
  local roles = {[2] = "anchor", [3] = "addition", [9] = "anchor", [40] = "anchor"}
  luaunit.assert_equals(sorted_keys(structure.markers("anchors", span(1, 16), roles)), {2, 9})
  luaunit.assert_equals(sorted_keys(structure.markers("off", span(1, 16), roles)), {})
end

function test_structure_active_only_for_foundation_with_markers()
  luaunit.assert_nil(structure.active(nil))
  luaunit.assert_nil(structure.active(merge_config.new()))
  luaunit.assert_nil(structure.active(foundation("off", nil)))
  local fragments = foundation("every_4", 2); fragments.mode = "fragments"
  luaunit.assert_nil(structure.active(fragments))
  local off = foundation("every_4", 2); off.mode = "off"
  luaunit.assert_nil(structure.active(off))
  luaunit.assert_equals(structure.active(foundation("every_4", 2)), {markers = "every_4", group_id = 2})
  -- A v1 configuration has no structure at all.
  luaunit.assert_nil(structure.active({schema_version = 1, mode = "foundation", anchor = 1}))
end

-- §4 Shared pitch resolution: nearest chord pitch class, lower on ties.
function test_structure_snap_to_chord_is_nearest_pitch_class_lower_on_ties()
  luaunit.assert_equals(pitch_target.snap_to_chord(62, {0, 4, 7}), 60)   -- D: C and E tie, lower
  luaunit.assert_equals(pitch_target.snap_to_chord(63, {0, 4, 7}), 64)
  luaunit.assert_equals(pitch_target.snap_to_chord(66, {0, 4, 7}), 67)
  luaunit.assert_equals(pitch_target.snap_to_chord(69, {0, 4, 7}), 67)   -- A: G (2) vs C (3)
  luaunit.assert_equals(pitch_target.snap_to_chord(70, {0, 4, 7}), 72)
  luaunit.assert_equals(pitch_target.snap_to_chord(65, {2, 8}), 62)       -- F: D and G# tie, lower
  luaunit.assert_equals(pitch_target.snap_to_chord(64, {4}), 64)
  luaunit.assert_equals(pitch_target.snap_to_chord(0, {11}), 11)
  luaunit.assert_equals(pitch_target.snap_to_chord(127, {0}), 120)
  luaunit.assert_nil(pitch_target.snap_to_chord(nil, {0}))
end

-- §4 precedence: explicit bypass > marker (chord or CHORD MISSING) > between-marker rule.
function test_structure_policy_precedence()
  local target = {kind = "scale"}
  for _, bypass in ipairs({"note_mask", "random", "quantised_fixed", "fixed"}) do
    for _, role in ipairs({"anchor", "addition"}) do
      local policy = structure.policy({marker = true, role = role, bypass = bypass, target = target,
        target_available = true, marker_material = {0, 4, 7}})
      luaunit.assert_equals({policy.kind, policy.bypass, policy.suppress_merged_pentatonic},
        {"bypass", bypass, false})
    end
  end
  local marker = structure.policy({marker = true, role = "addition", target = target,
    target_available = true, marker_material = {0, 4, 7}})
  luaunit.assert_equals({marker.kind, marker.suppress_merged_pentatonic}, {"marker", true})
  local anchor_marker = structure.policy({marker = true, role = "anchor", marker_material = {0}})
  luaunit.assert_equals({anchor_marker.kind, anchor_marker.suppress_merged_pentatonic}, {"marker", true})
  -- A marker position without a Foundation role (a masked-in trig) is still a marker onset.
  luaunit.assert_equals(structure.policy({marker = true, marker_material = {0}}).kind, "marker")
  for _, material in ipairs({{}, false}) do
    local missing = structure.policy({marker = true, role = "addition", target = target,
      target_available = true, marker_material = material or nil})
    luaunit.assert_equals({missing.kind, missing.suppress_merged_pentatonic}, {"chord_missing", false})
  end
end

function test_structure_policy_between_markers_keeps_existing_rules()
  local addition = structure.policy({marker = false, role = "addition", target = {kind = "scale"},
    target_available = true, marker_material = {0}})
  luaunit.assert_equals({addition.kind, addition.suppress_merged_pentatonic}, {"addition", true})
  local unavailable = structure.policy({role = "addition", target = {kind = "degrees", degrees = {9}},
    target_available = false})
  luaunit.assert_equals({unavailable.kind, unavailable.suppress_merged_pentatonic}, {"addition", false})
  local legacy_target = structure.policy({role = "addition", target = {kind = "legacy"}, target_available = false})
  luaunit.assert_equals({legacy_target.kind, legacy_target.suppress_merged_pentatonic}, {"addition", false})
  local bypassed = structure.policy({role = "addition", bypass = "fixed", target = {kind = "scale"},
    target_available = true})
  luaunit.assert_equals({bypassed.kind, bypassed.bypass, bypassed.suppress_merged_pentatonic},
    {"addition", "fixed", false})
  for _, role in ipairs({"anchor", false}) do
    local policy = structure.policy({role = role or nil, target = {kind = "scale"}, target_available = true})
    luaunit.assert_equals({policy.kind, policy.suppress_merged_pentatonic}, {"legacy", false})
  end
end

function test_structure_resolve_applies_policy_after_conversion()
  local context = {target = {kind = "scale"}, scale_pitch_classes = {0, 2, 4, 5, 7, 9, 11}}
  local marker = structure.policy({marker = true, role = "addition", marker_material = {0, 4, 7}})
  luaunit.assert_equals({structure.resolve(marker, 62, context)}, {60, "marker"})
  local missing = structure.policy({marker = true, role = "addition"})
  luaunit.assert_equals({structure.resolve(missing, 61, context)}, {61, "chord_missing"})
  local bypass = structure.policy({marker = true, role = "anchor", bypass = "note_mask", marker_material = {0}})
  luaunit.assert_equals({structure.resolve(bypass, 61, context)}, {61, "note_mask"})
  -- Between markers the Addition Target is exactly pitch_target.resolve.
  local addition = structure.policy({role = "addition", target = context.target, target_available = true})
  luaunit.assert_equals({structure.resolve(addition, 61, context)},
    {pitch_target.resolve(61, {eligible = true, config = context.target,
      scale_pitch_classes = context.scale_pitch_classes})})
  local bypassed = structure.policy({role = "addition", bypass = "random", target = context.target,
    target_available = true})
  luaunit.assert_equals({structure.resolve(bypassed, 61, context)}, {61, "random"})
  luaunit.assert_equals({structure.resolve(structure.policy({role = "anchor"}), 61, context)}, {61, nil})
end

function test_structure_reasons_for_later_ui()
  luaunit.assert_equals(structure.reason("marker", 3), "MARKER · CHORD G03")
  luaunit.assert_equals(structure.reason("marker", 12), "MARKER · CHORD G12")
  luaunit.assert_equals(structure.reason("chord_missing", 3), "CHORD MISSING")
  luaunit.assert_equals(structure.reason("marker_priority"), "MARKER PRIORITY")
  luaunit.assert_nil(structure.reason("targeted", 3))
  luaunit.assert_nil(structure.reason(nil))
end

-- §4 Persisted Pattern identity: suffix only for active markers on Foundation.
function test_structure_identity_suffix_only_for_active_foundation_markers()
  luaunit.assert_nil(structure.identity(nil))
  luaunit.assert_nil(structure.identity(merge_config.new()))
  luaunit.assert_nil(structure.identity(foundation("off", nil)))
  local off_mode = foundation("anchors", 4); off_mode.mode = "off"
  luaunit.assert_nil(structure.identity(off_mode))
  luaunit.assert_equals(structure.identity(foundation("anchors", 4)), "structure-v1,anchors,4")
  luaunit.assert_equals(structure.identity(foundation("every_8", 16)), "structure-v1,every_8,16")
end

-- §4 Reference lifecycle: a missing or disabled group turns markers Off, group nil.
function test_structure_repair_turns_markers_off_for_missing_or_disabled_group()
  local groups = {[1] = {enabled = true}, [2] = {enabled = false}}
  local healthy = foundation("every_4", 1)
  luaunit.assert_false(structure.repair(healthy, groups))
  luaunit.assert_equals(healthy.structure, {markers = "every_4", group_id = 1})
  for _, id in ipairs({2, 3}) do
    local broken = foundation("anchors", id)
    luaunit.assert_true(structure.repair(broken, groups))
    luaunit.assert_equals(broken.structure, {markers = "off"})
    luaunit.assert_true(merge_config.validate(broken))
  end
  -- Inactive merge modes are repaired too: the stored reference is what is saved.
  local off_mode = foundation("every_8", 3); off_mode.mode = "off"
  luaunit.assert_true(structure.repair(off_mode, groups))
  luaunit.assert_false(structure.repair(nil, groups))
  luaunit.assert_false(structure.repair({schema_version = 1, mode = "foundation"}, groups))
  luaunit.assert_false(structure.repair(foundation("off", nil), {}))
end

function test_structure_group_available_requires_existing_enabled_group()
  luaunit.assert_true(structure.group_available({groups = {[2] = {enabled = true}}}, 2))
  luaunit.assert_false(structure.group_available({groups = {[2] = {enabled = false}}}, 2))
  luaunit.assert_false(structure.group_available({groups = {}}, 2))
  luaunit.assert_false(structure.group_available(nil, 2))
end

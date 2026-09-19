-- README.md Musical Merge: structural pitch targets affect admitted additions
-- only, after legacy pitch precedence, with lower-note nearest ties.

local target = include("mosaic/lib/musical_merge/pitch_target")

function test_merge_pitch_target_bypasses_anchors_masks_random_and_fixed()
  for _, reason in ipairs({"anchor","note_mask","random","quantised_fixed","fixed"}) do
    local pitch, status = target.resolve(61, {eligible=true, bypass=reason,
      config={kind="scale"}, scale_pitch_classes={0,2}})
    luaunit.assert_equals({pitch,status}, {61,reason})
  end
end

function test_merge_pitch_target_scale_and_degrees_snap_lower_on_tie()
  luaunit.assert_equals({target.resolve(61, {eligible=true, config={kind="scale"},
    scale_pitch_classes={0,2}})}, {60,"targeted"})
  luaunit.assert_equals({target.resolve(66, {eligible=true,
    config={kind="degrees",degrees={1,3}}, scale_pitch_classes={0,2,4,5,7}})},
    {64,"targeted"})
end

function test_merge_pitch_target_empty_or_missing_explicit_source_is_visible_legacy()
  luaunit.assert_equals({target.resolve(60, {eligible=true,
    config={kind="degrees",degrees={9}}, scale_pitch_classes={0,2,4}})},
    {60,"target_empty"})
  luaunit.assert_equals({target.resolve(60, {eligible=true,
    config={kind="chord",group_id=2}})}, {60,"source_missing"})
end

function test_merge_pitch_target_uses_surviving_degrees_after_runtime_source_change()
  luaunit.assert_equals({target.resolve(60,{eligible=true,
    config={kind="degrees",degrees={1,9}},scale_pitch_classes={0,2,4}})},
    {60,"targeted"})
end

function test_merge_pitch_target_explicit_chord_consumes_material_not_voiced_pitches()
  local pitch, status = target.resolve(65, {eligible=true,
    config={kind="chord",group_id=2}, chord_material={0,4,7},
    voiced_pitches={72,76,79}})
  luaunit.assert_equals({pitch,status}, {64,"targeted"})
end

function test_merge_pitch_target_legacy_and_ineligible_are_exact()
  luaunit.assert_equals({target.resolve(63, {eligible=true,config={kind="legacy"}})}, {63,"legacy"})
  luaunit.assert_equals({target.resolve(63, {eligible=false,config={kind="scale"},scale_pitch_classes={0}})},
    {63,"ineligible"})
end

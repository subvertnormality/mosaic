-- README.md Voice leading: templates resolve through Mosaic's actual scale
-- transforms; they are pitch collections, not inferred major/minor chord names.

local loaded, context = pcall(include, "mosaic/lib/harmony/context")
local harmony_config = include("mosaic/lib/harmony/config")

local function setup()
  program.init()
  program.set_selected_song_pattern(1)
  return program.get_song_pattern(1)
end

function test_harmony_context_module_exists()
  luaunit.assert_true(loaded)
end

function test_harmony_context_resolves_template_offsets_through_actual_scale()
  setup()
  local group = harmony_config.four_part_smooth(1, {2, 3, 4, 5})
  local frame = context.group_material(group, 1, 0)
  luaunit.assert_equals(frame.pitch_classes, {0, 4, 7})
  luaunit.assert_equals(frame.material, {
    {id = "tone1", pc = 0, required = true},
    {id = "tone2", pc = 4, required = true},
    {id = "tone3", pc = 7, required = true}
  })
end

function test_harmony_context_preserves_modal_synthetic_collection_without_labels()
  local song = setup()
  song.scales[1].scale = {0, 2, 6, 9, 12, 14, 18, 21, 24}
  song.scales[1].root_note = 0
  song.scales[1].chord = 1
  song.scales[1].chord_degree_rotation = 0
  song.scales[1].version = 2
  local group = harmony_config.new_group(2)
  group.template = {offsets = {0, 1, 2, 3}, required = {true, false, false, false}}
  local frame = context.group_material(group, 1, 0)
  luaunit.assert_equals(frame.pitch_classes, {0, 2, 6, 9})
  luaunit.assert_nil(frame.chord_name)
end

function test_harmony_context_selected_degrees_use_ordered_effective_inventory()
  local song = setup()
  song.scales[1].scale = {0, 2, 6, 9, 12, 14, 18, 21, 24}
  song.scales[1].version = 3
  luaunit.assert_equals(context.scale_pitch_classes(1, 0), {0, 2, 6, 9})
  luaunit.assert_equals(context.selected_degree_pitch_classes(1, 0, {2, 4}), {2, 9})
  luaunit.assert_equals(context.selected_degree_pitch_classes(1, 0, {5}), {})
end

function test_harmony_context_nearest_target_uses_lower_pitch_on_exact_tie()
  luaunit.assert_equals(context.nearest_pitch(61, {0, 2}), 60)
  luaunit.assert_equals(context.nearest_pitch(0, {11}), 11)
  luaunit.assert_equals(context.nearest_pitch(127, {0}), 120)
  luaunit.assert_nil(context.nearest_pitch(60, {}))
end

function test_harmony_context_revision_changes_with_source_or_template_not_ui_selection()
  local song = setup()
  local group = harmony_config.new_group(2)
  local first = context.group_material(group, 1, 0).revision
  program.get().selected_scale = 9
  luaunit.assert_equals(context.group_material(group, 1, 0).revision, first)
  song.scales[1].version = song.scales[1].version + 1
  luaunit.assert_not_equals(context.group_material(group, 1, 0).revision, first)
  local prior = context.group_material(group, 1, 0).revision
  group.template.offsets = {0, 2}
  group.template.required = {true, false}
  luaunit.assert_not_equals(context.group_material(group, 1, 0).revision, prior)
end


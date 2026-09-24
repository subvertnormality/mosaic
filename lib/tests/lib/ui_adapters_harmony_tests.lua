-- README.md "Musical Merge and Voice Leading" > "Harmony": characterises the
-- UI02 harmony adapter (docs/ui-reimplementation IMPLEMENTATION.md "Adapter
-- extraction (UI02)") against the existing channel_feature_editor owner.

local ui_adapters = include("mosaic/lib/ui_adapters")
local harmony_adapter_factory = include("mosaic/lib/ui_adapters/harmony")
local feature_editor = include("mosaic/lib/pages/channel_edit_page/channel_feature_editor")
local merge_state = include("mosaic/lib/musical_merge/state")
local merge_config = include("mosaic/lib/musical_merge/config")
local harmony_state = include("mosaic/lib/harmony/config_state")
local harmony_config = include("mosaic/lib/harmony/config")
local harmony_inspection = include("mosaic/lib/harmony/inspection")

local function setup()
  program.init(); globals.reset(); params.reset()
  m_clock.init()
  merge_state.reset(); harmony_state.reset(); harmony_inspection.reset()
  program.set_selected_song_pattern(1)
  return program.get_song_pattern(1), program.get_channel(1, 1)
end

local function build()
  local editor = feature_editor.new("harmony"); editor:enter()
  return harmony_adapter_factory(ui_adapters, {feature_editors = {harmony = editor}}), editor
end

local function fresh()
  local song, channel = setup()
  local adapter, editor = build()
  return adapter, editor, song, channel
end

local function target(editor) return {source_route = editor.screen, channel_number = editor.channel_number} end

local function describe(adapter, editor)
  local route = editor.screen
  return adapter:describe(ui_adapters.translate_route("harmony", route), route, target(editor), editor.generation)
end

local function ids(outcome)
  local result = {}
  for _, d in ipairs(outcome.descriptors) do result[#result + 1] = d.id end
  return result
end

local function assert_parity(adapter, editor)
  local outcome = describe(adapter, editor)
  luaunit.assert_true(outcome.ok, tostring(outcome.code))
  local fields = editor:get_fields()
  luaunit.assert_equals(#outcome.descriptors, #fields)
  for index, field in ipairs(fields) do
    local d = outcome.descriptors[index]
    luaunit.assert_equals(d.label, field.label)
    luaunit.assert_equals(d.value, field.action and ">" or feature_editor.field_value(field))
    luaunit.assert_equals(d.kind == "action", field.action == true)
    luaunit.assert_equals(d.kind == "readonly", field.readonly == true)
  end
  return ids(outcome), outcome
end

local function select_label(editor, label)
  for index, field in ipairs(editor:get_fields()) do
    if field.label == label then editor.selected = index; return field end
  end
  error("missing field " .. label .. " on " .. editor.screen)
end
local function open_label(editor, label) select_label(editor, label); editor:key(3) end

local function invoke(adapter, editor, id)
  local outcome = adapter:invoke(id, target(editor), editor.generation)
  luaunit.assert_true(outcome.ok, id .. ": " .. tostring(outcome.code))
  return outcome
end
local function edit(adapter, editor, id, delta)
  local outcome = adapter:edit(id, delta, target(editor), editor.generation)
  luaunit.assert_true(outcome.ok, id .. ": " .. tostring(outcome.code))
  return outcome
end

local function ensemble_song(song, members)
  local group = harmony_config.four_part_smooth(1, members or {1, 2, 3, 4}); group.enabled = true
  song.voicing = {schema_version = 1, groups = {[1] = group}}
  song.channels[1].voicing = harmony_config.new_channel("ensemble"); song.channels[1].voicing.group_id = 1
  return group
end

function test_ui_adapters_harmony_root_descriptors_follow_each_mode()
  local adapter, editor = fresh()
  local root = {"mode", "group", "preset", "register", "bass", "groups", "rules", "entry", "result"}
  luaunit.assert_equals(assert_parity(adapter, editor), root)
  local _, off = assert_parity(adapter, editor)
  luaunit.assert_equals(off.descriptors[2].value, "NOT USED")
  luaunit.assert_equals(off.descriptors[2].kind, "readonly")
  editor.draft.mode = "revoice"
  luaunit.assert_equals(assert_parity(adapter, editor), root)
  editor.draft.mode = "pattern"
  luaunit.assert_equals(assert_parity(adapter, editor),
    {"mode", "group", "preset", "tone_map", "register", "bass", "groups", "rules", "entry", "result"})
  editor.draft.mode = "ensemble"
  local _, ensemble = assert_parity(adapter, editor)
  luaunit.assert_equals(ensemble.descriptors[2].kind, "value")
  luaunit.assert_equals(ensemble.descriptors[2].domain.min, 0)
  luaunit.assert_equals(ensemble.descriptors[2].domain.max, 16)
  luaunit.assert_equals(ensemble.descriptors[2].value, "0")
end

function test_ui_adapters_harmony_child_routes_cover_owner_fields()
  local adapter, editor = fresh()
  local expected = {
    register = {"role", "low", "high", "centre", "preferred_leap", "strict_leap"},
    bass = {"mode", "direction", "strict_direction", "pedal", "non_chord_pedal", "bass_register"},
    groups = {"group", "create_group"},
    rules = {"crossing", "pc_doubling", "exact_unison", "common_tones", "upper_spacing", "bass_separation", "coverage"},
    entry = {"start", "song_transition", "same_slot_repeat", "failure_fallback", "absolute_pitch"},
    result = {"step", "status", "planned_ch1", "emitted_ch1"}
  }
  for id, fields in pairs(expected) do
    invoke(adapter, editor, id)
    luaunit.assert_equals(assert_parity(adapter, editor), fields, id)
    editor:encoder_one()
  end
  -- Pattern bass is smooth octave only; inversion adds the bass tone selector.
  editor.draft.mode = "pattern"; invoke(adapter, editor, "bass")
  luaunit.assert_equals(assert_parity(adapter, editor), {"mode", "direction", "strict_direction", "bass_register"})
  editor:encoder_one(); editor.draft.mode = "revoice"; editor.draft.bass.mode = "inversion"; invoke(adapter, editor, "bass")
  luaunit.assert_equals(assert_parity(adapter, editor),
    {"mode", "bass_tone", "direction", "strict_direction", "pedal", "non_chord_pedal", "bass_register"})
  -- Tone map with an empty note inventory keeps only Reset.
  editor:encoder_one(); editor.draft.mode = "pattern"; editor.channel.working_pattern.note_values = {}
  invoke(adapter, editor, "tone_map")
  luaunit.assert_equals(assert_parity(adapter, editor), {"reset_map"})
end

function test_ui_adapters_harmony_group_routes_at_maximum_cardinality()
  local adapter, editor = fresh()
  invoke(adapter, editor, "groups")
  -- Empty inventory: no group, and the group child routes show one row.
  luaunit.assert_equals(assert_parity(adapter, editor), {"group", "create_group"})
  editor.context_group = true
  editor.screen = "H07"; luaunit.assert_equals(assert_parity(adapter, editor), {"group"})
  editor.screen = "H10"; luaunit.assert_equals(assert_parity(adapter, editor), {"source"})
  editor.screen = "H04"
  invoke(adapter, editor, "create_group")
  luaunit.assert_equals(assert_parity(adapter, editor),
    {"group", "create_group", "four_part_smooth", "members", "source", "policies", "entry", "result", "delete_group"})
  invoke(adapter, editor, "members")
  edit(adapter, editor, "voice_count", 1); edit(adapter, editor, "voice_count", 1); edit(adapter, editor, "voice_count", 1)
  edit(adapter, editor, "voice_count", 1); edit(adapter, editor, "voice_count", 1)
  local members, outcome = assert_parity(adapter, editor)
  luaunit.assert_equals(members, {"voice_count", "bass", "inner1", "inner2", "inner3", "top", "group_enabled"})
  luaunit.assert_equals(outcome.descriptors[2].repeat_key, "<role>")
  luaunit.assert_equals(outcome.descriptors[2].value, "1")
  luaunit.assert_equals(outcome.descriptors[3].value, "0") -- owner shows an empty member as 0
  editor.stack = {{screen = "H04", selected = 1}}; editor.screen = "H04"
  invoke(adapter, editor, "source")
  edit(adapter, editor, "source_kind", 1)
  for _ = 1, 5 do edit(adapter, editor, "template_count", 1) end
  luaunit.assert_equals(assert_parity(adapter, editor), {"source_kind", "scale_slot", "template_count", "root_offset",
    "tone_2", "tone_3", "tone_4", "tone_5", "required_1", "required_2", "required_3", "required_4", "required_5"})
  editor.screen = "H04"; invoke(adapter, editor, "policies")
  local _, policies = assert_parity(adapter, editor)
  luaunit.assert_equals(policies.descriptors[2].kind, "value")
  luaunit.assert_equals(policies.descriptors[7].kind, "action")
  editor.screen = "H04"; invoke(adapter, editor, "entry")
  luaunit.assert_equals(assert_parity(adapter, editor), {"start", "song_transition", "same_slot_repeat", "failure_fallback"})
  editor.screen = "H04"; invoke(adapter, editor, "delete_group")
  luaunit.assert_equals(assert_parity(adapter, editor), {"group", "affected", "confirm_delete"})
end

function test_ui_adapters_harmony_result_and_failure_details()
  local adapter, editor, song = fresh()
  harmony_inspection.plan(song, 1, {step = 1, status = "no_solution", reason = "range", fallback = "silence"})
  invoke(adapter, editor, "result")
  local fields, outcome = assert_parity(adapter, editor)
  luaunit.assert_equals(fields, {"step", "status", "planned_ch1", "emitted_ch1", "failure_details"})
  luaunit.assert_equals(outcome.descriptors[1].kind, "inspection")
  luaunit.assert_equals(outcome.descriptors[2].value, "NO VOICING RANGE")
  invoke(adapter, editor, "failure_details")
  luaunit.assert_equals(assert_parity(adapter, editor), {"reason", "fallback", "settings"})
  -- Group result: planned/emitted per member role.
  local song2 = setup(); ensemble_song(song2)
  local group_adapter, group_editor = build()
  group_editor.context_group = true; group_editor.selected_group = 1
  group_editor.screen = "H05"
  luaunit.assert_equals(assert_parity(group_adapter, group_editor), {"step", "status", "planned_bass", "emitted_bass",
    "planned_inner1", "emitted_inner1", "planned_inner2", "emitted_inner2", "planned_top", "emitted_top"})
end

function test_ui_adapters_harmony_edit_and_apply_match_the_old_path()
  local function drive(use_adapter)
    local song, channel = setup()
    local adapter, editor = build()
    if use_adapter then
      edit(adapter, editor, "mode", 1)
      invoke(adapter, editor, "register")
      edit(adapter, editor, "low", 3); edit(adapter, editor, "strict_leap", 1)
      editor:encoder_one()
    else
      editor:enc(3, 1)
      open_label(editor, "Register")
      select_label(editor, "Low"); editor:enc(3, 3)
      select_label(editor, "Strict leap"); editor:enc(3, 1)
      editor:encoder_one()
    end
    -- E1 on a dirty draft cancels: nothing reaches the model.
    luaunit.assert_nil(channel.voicing)
    if use_adapter then
      edit(adapter, editor, "mode", 1)
      invoke(adapter, editor, "register"); edit(adapter, editor, "high", -2)
      luaunit.assert_true(adapter:apply(adapter.owner_token(), target(editor), editor.generation).ok)
    else
      editor:enc(3, 1); open_label(editor, "Register"); select_label(editor, "High"); editor:enc(3, -2)
      select_label(editor, "Role"); luaunit.assert_true(editor:key(3))
    end
    return channel.voicing, editor.status, song.voicing
  end
  local old_voicing, old_status, old_song = drive(false)
  local new_voicing, new_status, new_song = drive(true)
  luaunit.assert_equals(new_voicing, old_voicing)
  luaunit.assert_equals(new_status, old_status)
  luaunit.assert_equals(new_song, old_song)
  luaunit.assert_equals(new_voicing.mode, "revoice")
end

function test_ui_adapters_harmony_group_delete_confirmation_stays_in_the_owner()
  local function drive(use_adapter)
    local song = setup(); ensemble_song(song, {1, 2})
    song.channels[2].musical_merge = merge_config.new(); song.channels[2].musical_merge.target = {kind = "chord", group_id = 1}
    local adapter, editor = build()
    if use_adapter then
      invoke(adapter, editor, "groups")
      luaunit.assert_false(adapter.impl.pending_confirmation())
      invoke(adapter, editor, "delete_group")
      luaunit.assert_true(adapter.impl.pending_confirmation())
      luaunit.assert_equals(ui_adapters.translate_route("harmony", editor.screen), "H17")
      -- K2 cancels the question and restores the parent without mutation.
      luaunit.assert_true(adapter:cancel(adapter.owner_token()).ok)
      luaunit.assert_equals(editor.screen, "H04")
      luaunit.assert_not_nil(song.voicing.groups[1])
      invoke(adapter, editor, "delete_group")
      local outcome = invoke(adapter, editor, "confirm_delete")
      luaunit.assert_equals(outcome.result.route, "H04")
    else
      open_label(editor, "Groups"); open_label(editor, "Delete group"); open_label(editor, "Confirm delete")
    end
    return song, editor
  end
  local old_song, old_editor = drive(false)
  local new_song, new_editor = drive(true)
  luaunit.assert_nil(new_song.voicing.groups[1])
  luaunit.assert_equals(new_song.voicing, old_song.voicing)
  luaunit.assert_equals(new_song.channels[1].voicing, old_song.channels[1].voicing)
  luaunit.assert_equals(new_song.channels[2].musical_merge, old_song.channels[2].musical_merge)
  luaunit.assert_equals(new_editor.status, old_editor.status)
end

function test_ui_adapters_harmony_tone_map_reset_confirmation()
  local adapter, editor, song, channel = fresh()
  channel.selected_patterns[1] = true
  song.patterns[1].note_values[1] = 0; channel.working_pattern.note_values[1] = 0
  song.patterns[1].note_values[2] = -7; channel.working_pattern.note_values[2] = -7
  editor.draft.mode = "pattern"
  invoke(adapter, editor, "tone_map")
  local fields, outcome = assert_parity(adapter, editor)
  luaunit.assert_equals(fields, {"value_-7", "value_0", "reset_map"})
  luaunit.assert_equals(outcome.descriptors[1].repeat_key, "value_<raw>")
  luaunit.assert_equals(outcome.descriptors[1].value, "RAW")
  edit(adapter, editor, "value_0", 1)
  luaunit.assert_equals(describe(adapter, editor).descriptors[2].value, "BASS")
  invoke(adapter, editor, "reset_map")
  luaunit.assert_true(adapter.impl.pending_confirmation())
  luaunit.assert_equals(assert_parity(adapter, editor), {"reset_map", "confirm_reset"})
  invoke(adapter, editor, "confirm_reset")
  luaunit.assert_equals(editor.screen, "TONE_MAP")
  luaunit.assert_equals(describe(adapter, editor).descriptors[2].value, "RAW")
  luaunit.assert_true(editor.dirty)
  luaunit.assert_nil(channel.voicing)
end

function test_ui_adapters_harmony_foreign_routes_and_stale_targets_are_refused()
  local adapter, editor = fresh()
  local foreign = adapter:describe("M02", "M01", {source_route = "M01"}, editor.generation)
  luaunit.assert_false(foreign.ok); luaunit.assert_equals(foreign.code, "foreign_route"); luaunit.assert_nil(foreign.descriptors)
  luaunit.assert_equals(adapter:describe("H11", "H11", {source_route = "H11"}).code, "foreign_route")
  luaunit.assert_equals(adapter:describe("H02", "H02", {source_route = "H02"}, editor.generation).code, "stale_target")
  local captured, generation = target(editor), editor.generation
  edit(adapter, editor, "mode", 1)
  adapter:cancel(adapter.owner_token())
  luaunit.assert_equals(editor.draft.mode, "off")
  luaunit.assert_equals(adapter:edit("mode", 1, captured, generation).code, "stale_generation")
  luaunit.assert_equals(adapter:invoke("register", captured, generation).code, "stale_generation")
  luaunit.assert_equals(editor.draft.mode, "off"); luaunit.assert_equals(editor.screen, "H01")
  luaunit.assert_equals(adapter:apply({generation = generation}).code, "stale_generation")
  luaunit.assert_equals(adapter:edit("mode", 1, {source_route = "H01", channel_number = 5}, editor.generation).code, "stale_target")
  luaunit.assert_equals(editor.draft.mode, "off")
  luaunit.assert_false(editor.dirty)
end

function test_ui_adapters_harmony_apply_reports_global_pattern_boundary()
  local adapter, editor, song, channel = fresh()
  m_clock:start()
  edit(adapter, editor, "mode", 1); edit(adapter, editor, "mode", 1)
  local outcome = adapter:apply(adapter.owner_token(), target(editor), editor.generation)
  luaunit.assert_true(outcome.ok)
  luaunit.assert_equals(outcome.code, "queued")
  luaunit.assert_equals(outcome.status, "NEXT PATTERN")
  luaunit.assert_equals(outcome.commit_boundary, "global_pattern_boundary")
  luaunit.assert_equals(channel.voicing.mode, "pattern")
  local h14 = adapter:describe("H14", "snapshot:H14", {source_route = "snapshot:H14"})
  luaunit.assert_equals(ids(h14), {"active_mode", "queued", "changed", "sources_unchanged"})
  luaunit.assert_equals(h14.descriptors[1].value, "OFF")
  luaunit.assert_equals(h14.descriptors[2].value, "PATTERN")
  luaunit.assert_equals(h14.descriptors[3].value, "ON")
  harmony_state.on_pattern_boundary(song)
  local later = adapter:describe("H14", "snapshot:H14", {source_route = "snapshot:H14"})
  luaunit.assert_equals(later.descriptors[1].value, "PATTERN")
  luaunit.assert_equals(later.descriptors[2].value, "NONE")
end

function test_ui_adapters_harmony_snapshot_variants_read_one_immutable_event()
  local adapter, editor, song = fresh()
  local event = {step = 1, status = "ok", output = 60}
  harmony_inspection.plan(song, 1, event)
  harmony_inspection.scheduled(song, 1, 60, "root", event)
  harmony_inspection.emitted(song, 1, 61, "root", event)
  invoke(adapter, editor, "result")
  local snapshot = adapter:snapshot(target(editor), 11).snapshot
  luaunit.assert_error_msg_contains("immutable", function() snapshot.trace.planned.output = 1 end)
  -- Later playback does not change the captured snapshot.
  harmony_inspection.plan(song, 1, {step = 1, status = "no_solution", reason = "range"})
  local calls, original = 0, editor.get_fields
  editor.get_fields = function(...) calls = calls + 1; return original(...) end
  local h18 = adapter:describe("H18", "snapshot:H18", {source_route = "snapshot:H18", snapshot = snapshot})
  local h15 = adapter:describe("H15", "snapshot:H15", {source_route = "snapshot:H15", snapshot = snapshot})
  editor.get_fields = original
  luaunit.assert_equals(calls, 0)
  luaunit.assert_equals(ids(h18), {"step", "planned", "scheduled", "emitted", "status", "source_chain"})
  luaunit.assert_equals(h18.descriptors[2].value, "60")
  luaunit.assert_equals(h18.descriptors[4].value, "61")
  luaunit.assert_equals(h18.descriptors[5].value, "OK")
  luaunit.assert_equals(h18.descriptors[6].value, "ROOT")
  luaunit.assert_equals(ids(h15), {"step", "status", "planned", "scheduled", "emitted"})
  for _, id in ipairs({"M10", "H12", "H13", "H16"}) do
    local variant = adapter:describe(id, "snapshot:" .. id, {source_route = "snapshot:" .. id})
    luaunit.assert_true(variant.ok, id)
    luaunit.assert_equals(ids(variant), ui_adapters.spec.screens[id].fields, id)
  end
  -- M10 fields come from H01 only; captured on H05 they are unavailable.
  luaunit.assert_equals(adapter:describe("M10", "snapshot:M10", {source_route = "snapshot:M10"}).descriptors[1].kind, "unavailable")
  editor:encoder_one()
  local m10 = adapter:describe("M10", "snapshot:M10", {source_route = "snapshot:M10"})
  luaunit.assert_equals(m10.descriptors[1].value, "OFF")
  luaunit.assert_equals(m10.descriptors[2].kind, "unavailable") -- tone_map exists only in Pattern mode
  -- A merge snapshot is not a harmony snapshot.
  luaunit.assert_equals(adapter:describe("H18", "snapshot:H18",
    {source_route = "snapshot:H18", snapshot = ui_adapters.spec}).code, "foreign_snapshot")
end

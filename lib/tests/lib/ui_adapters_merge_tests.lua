-- README.md "Musical Merge and Voice Leading" > "Merge Shape": characterises the
-- UI02 merge adapter (docs/ui-reimplementation IMPLEMENTATION.md "Adapter
-- extraction (UI02)") against the existing channel_feature_editor owner.

local ui_adapters = include("mosaic/lib/ui_adapters")
local merge_adapter_factory = include("mosaic/lib/ui_adapters/merge")
local feature_editor = include("mosaic/lib/pages/channel_edit_page/channel_feature_editor")
local merge_state = include("mosaic/lib/musical_merge/state")
local harmony_state = include("mosaic/lib/harmony/config_state")
local harmony_config = include("mosaic/lib/harmony/config")

local function setup(patterns)
  program.init(); globals.reset(); params.reset()
  m_clock.init()
  merge_state.reset(); harmony_state.reset()
  program.set_selected_song_pattern(1)
  local song, channel = program.get_song_pattern(1), program.get_channel(1, 1)
  for _, number in ipairs(patterns or {}) do channel.selected_patterns[number] = true end
  return song, channel
end

local function fresh(patterns)
  local song, channel = setup(patterns)
  local editor = feature_editor.new("merge"); editor:enter()
  local adapter = merge_adapter_factory(ui_adapters, {feature_editors = {merge = editor}})
  return adapter, editor, song, channel
end

local function target(editor) return {source_route = editor.screen, channel_number = editor.channel_number} end

local function describe(adapter, editor)
  local route = editor.screen
  return adapter:describe(ui_adapters.translate_route("merge", route), route, target(editor), editor.generation)
end

local function ids(outcome)
  local result = {}
  for _, d in ipairs(outcome.descriptors) do result[#result + 1] = d.id end
  return result
end

-- Descriptor labels/values/kinds equal what the owner's draw path shows.
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
  return outcome
end

local function select_label(editor, label)
  for index, field in ipairs(editor:get_fields()) do
    if field.label == label then editor.selected = index; return field end
  end
  error("missing field " .. label .. " on " .. editor.screen)
end

local function open_label(editor, label) select_label(editor, label); editor:key(3) end

local function open_id(adapter, editor, id)
  local outcome = adapter:invoke(id, target(editor), editor.generation)
  luaunit.assert_true(outcome.ok, tostring(outcome.code))
  return outcome
end

function test_ui_adapters_merge_descriptor_ids_cover_every_owner_route()
  local adapter, editor = fresh({1, 2})
  luaunit.assert_equals(ids(assert_parity(adapter, editor)), {"mode", "rhythm", "phrase", "pitch", "result"})
  open_id(adapter, editor, "rhythm")
  luaunit.assert_equals(ids(assert_parity(adapter, editor)), {"anchor", "add_amount", "amount_detail", "add_accent", "anchor_gap", "seed"})
  open_id(adapter, editor, "amount_detail")
  luaunit.assert_equals(ids(assert_parity(adapter, editor)), {"add_amount", "eligible", "admitted"})
  editor:encoder_one(); open_id(adapter, editor, "phrase")
  luaunit.assert_equals(ids(assert_parity(adapter, editor)), {"cycles", "shape", "cycle_1", "variation"})
  editor:encoder_one(); open_id(adapter, editor, "pitch")
  luaunit.assert_equals(ids(assert_parity(adapter, editor)), {"keep_anchor", "add_target", "target_setup", "harmony"})
  open_id(adapter, editor, "target_setup")
  luaunit.assert_equals(ids(assert_parity(adapter, editor)), {"target", "scope"})
  editor:encoder_one(); open_id(adapter, editor, "result")
  local result = assert_parity(adapter, editor)
  luaunit.assert_equals(ids(result), {"step", "role", "decision", "reason"})
  luaunit.assert_equals(result.descriptors[1].kind, "inspection")
  open_id(adapter, editor, "reason")
  luaunit.assert_equals(ids(assert_parity(adapter, editor)), {"step", "role", "sources", "decision", "velocity", "pitch_target"})
  editor:show_merge_gesture("TRIG SKIP")
  luaunit.assert_equals(ids(assert_parity(adapter, editor)), {"merge_gesture", "active_shape"})
end

function test_ui_adapters_merge_conditional_modes_and_cardinality()
  -- Empty inventory: no assigned pattern leaves the anchor enum empty and NONE.
  local adapter, editor = fresh({})
  open_id(adapter, editor, "rhythm")
  local anchor = assert_parity(adapter, editor).descriptors[1]
  luaunit.assert_equals(anchor.value, "NONE")
  luaunit.assert_equals(anchor.domain.enum, {})
  -- Maximum phrase cardinality: 8 cycles, each repeated with cycle_<n>.
  editor:encoder_one(); editor.draft.cycles = 8; editor.draft.percentages = {1, 2, 3, 4, 5, 6, 7, 8}
  open_id(adapter, editor, "phrase")
  local phrase = assert_parity(adapter, editor)
  luaunit.assert_equals(#phrase.descriptors, 11)
  luaunit.assert_equals(phrase.descriptors[10].id, "cycle_8")
  luaunit.assert_equals(phrase.descriptors[10].repeat_key, "cycle_<n>")
  -- Degree target: one degree_<n> per scale degree, ON/OFF kept distinct.
  editor:encoder_one(); editor.draft.target = {kind = "degrees", degrees = {1, 3}}
  open_id(adapter, editor, "pitch"); open_id(adapter, editor, "target_setup")
  local degrees = assert_parity(adapter, editor)
  luaunit.assert_true(#degrees.descriptors >= 3)
  for index, d in ipairs(degrees.descriptors) do
    luaunit.assert_equals(d.id, "degree_" .. index)
    luaunit.assert_equals(d.repeat_key, "degree_<n>")
    luaunit.assert_not_nil(d.id:match(ui_adapters.spec.field_contracts.merge.repeat_key.pattern))
  end
  luaunit.assert_equals(degrees.descriptors[1].value, "ON")
  -- Owner characterisation: field_value reads `get() or value`, so an OFF
  -- boolean draws as NONE today; the adapter keeps that exact text.
  luaunit.assert_equals(degrees.descriptors[2].value, "NONE")
  -- Chord target: one group_id enum descriptor.
  editor:encoder_one(); editor.draft.target = {kind = "chord"}
  open_id(adapter, editor, "pitch"); open_id(adapter, editor, "target_setup")
  luaunit.assert_equals(ids(assert_parity(adapter, editor)), {"group_id"})
end

function test_ui_adapters_merge_edit_matches_the_old_encoder_path()
  local function drive(use_adapter)
    local adapter, editor, _, channel = fresh({1, 3})
    if use_adapter then
      luaunit.assert_true(adapter:edit("mode", 1, target(editor), editor.generation).ok)
      open_id(adapter, editor, "rhythm")
      luaunit.assert_true(adapter:edit("anchor", 1, target(editor), editor.generation).ok)
      luaunit.assert_true(adapter:edit("add_amount", -5, target(editor), editor.generation).ok)
      luaunit.assert_true(adapter:edit("seed", 3, target(editor), editor.generation).ok)
      luaunit.assert_true(adapter:apply(adapter.owner_token(), target(editor), editor.generation).ok)
    else
      editor:enc(3, 1)
      open_label(editor, "Rhythm")
      select_label(editor, "Anchor"); editor:enc(3, 1)
      select_label(editor, "Add amount"); editor:enc(3, -5)
      select_label(editor, "Seed"); editor:enc(3, 3)
      luaunit.assert_true(editor:key(3))
    end
    return channel.musical_merge, editor.status
  end
  local old_config, old_status = drive(false)
  local new_config, new_status = drive(true)
  luaunit.assert_equals(new_config, old_config)
  luaunit.assert_equals(new_status, old_status)
  luaunit.assert_equals(new_config.mode, "foundation")
end

function test_ui_adapters_merge_route_action_runs_owner_open_and_translates()
  local adapter, editor = fresh({1})
  local outcome = open_id(adapter, editor, "phrase")
  luaunit.assert_equals(editor.screen, "M04")
  luaunit.assert_equals(outcome.result.screen, "M06")
  luaunit.assert_equals(#editor.stack, 1)
  luaunit.assert_equals(editor.stack[1].screen, "M01")
  -- The new id is never written into the owner's screen variable.
  local phrase = describe(adapter, editor)
  luaunit.assert_equals(phrase.screen, "M06")
end

function test_ui_adapters_merge_voice_leading_is_a_cross_owner_link()
  local song = setup({1})
  local merge = feature_editor.new("merge"); merge:enter()
  local harmony = feature_editor.new("harmony"); harmony:enter()
  harmony.screen, harmony.stack = "H02", {{screen = "H01", selected = 1}}
  local selected
  local saved = channel_edit_page_ui
  channel_edit_page_ui = {select_harmony_page = function() harmony:enter(); selected = true; return true end}
  local adapter = merge_adapter_factory(ui_adapters, {feature_editors = {merge = merge, harmony = harmony}})
  local ok, err = pcall(function()
    adapter:edit("mode", 1, target(merge), merge.generation)
    open_id(adapter, merge, "pitch")
    local link = describe(adapter, merge).descriptors[4]
    luaunit.assert_equals(link.id, "harmony")
    luaunit.assert_equals(link.domain.edge, "cross_owner_link")
    luaunit.assert_equals(link.domain.destination, "H01")
    local stale = target(merge); local generation = merge.generation
    local outcome = open_id(adapter, merge, "harmony")
    luaunit.assert_true(outcome.result.cancel_unapplied)
    luaunit.assert_false(outcome.result.return_frame)
    luaunit.assert_true(selected)
    luaunit.assert_false(merge.dirty)
    luaunit.assert_equals(merge.draft.mode, "off")
    luaunit.assert_equals(merge.screen, "M05")
    luaunit.assert_equals(harmony.screen, "H01")
    luaunit.assert_equals(harmony.stack, {})
    luaunit.assert_equals(adapter:edit("add_target", 1, stale, generation).code, "stale_generation")
  end)
  channel_edit_page_ui = saved
  luaunit.assert_nil(song.channels[1].musical_merge)
  if not ok then error(err, 0) end
end

function test_ui_adapters_merge_foreign_and_non_live_routes_are_error_outcomes()
  local adapter, editor = fresh({1})
  local foreign = adapter:describe("H01", "H01", {source_route = "H01"}, editor.generation)
  luaunit.assert_false(foreign.ok)
  luaunit.assert_equals(foreign.code, "foreign_route")
  luaunit.assert_nil(foreign.descriptors)
  luaunit.assert_equals(adapter:describe("M02", "HARMONY_LINK", {source_route = "HARMONY_LINK"}).code, "foreign_route")
  -- M02 is owned but not the live owner route: refused, never described.
  local not_live = adapter:describe("M03", "M02", {source_route = "M02"}, editor.generation)
  luaunit.assert_false(not_live.ok)
  luaunit.assert_equals(not_live.code, "stale_target")
  luaunit.assert_equals(adapter:describe("M03", "M02", {source_route = "M01"}, editor.generation).code, "route_not_live")
  luaunit.assert_equals(editor.screen, "M01")
end

function test_ui_adapters_merge_stale_generation_and_target_are_refused_without_mutation()
  local adapter, editor = fresh({1})
  local captured, generation = target(editor), editor.generation
  adapter:edit("mode", 1, captured, generation)
  luaunit.assert_true(editor.dirty)
  editor:key(2) -- owner K2 cancel reloads: generation moves on
  luaunit.assert_equals(editor.draft.mode, "off")
  luaunit.assert_equals(adapter:edit("mode", 1, captured, generation).code, "stale_generation")
  luaunit.assert_equals(editor.draft.mode, "off")
  luaunit.assert_false(editor.dirty)
  local other = target(editor); other.channel_number = 2
  luaunit.assert_equals(adapter:edit("mode", 1, other, editor.generation).code, "stale_target")
  luaunit.assert_equals(adapter:apply({generation = generation}).code, "stale_generation")
  luaunit.assert_equals(adapter:cancel({generation = generation}).code, "stale_generation")
  luaunit.assert_equals(editor.draft.mode, "off")
end

function test_ui_adapters_merge_apply_and_cancel_wrap_owner_commit()
  local adapter, editor, _, channel = fresh({1})
  editor.draft.anchor = 1
  adapter:edit("mode", 1, target(editor), editor.generation)
  local cancelled = adapter:cancel(adapter.owner_token())
  luaunit.assert_true(cancelled.ok)
  luaunit.assert_true(cancelled.result.cancelled)
  luaunit.assert_equals(editor.status, "DRAFT CANCELLED")
  luaunit.assert_nil(channel.musical_merge)
  -- Invalid draft: exact owner error, stays on the draft.
  adapter:edit("mode", 1, target(editor), editor.generation)
  local invalid = adapter:apply(adapter.owner_token(), target(editor))
  luaunit.assert_false(invalid.ok)
  luaunit.assert_equals(invalid.code, "invalid")
  luaunit.assert_equals(invalid.status, "INVALID merge anchor")
  luaunit.assert_true(editor.dirty)
  -- snapshot:M08 reports the invalid anchor from an immutable snapshot.
  local m08 = adapter:describe("M08", "snapshot:M08", {source_route = "snapshot:M08"})
  luaunit.assert_true(m08.ok)
  luaunit.assert_equals(m08.descriptors[1].id, "p01_is_not_assigned")
  luaunit.assert_equals(m08.descriptors[1].kind, "readonly")
  editor.draft.anchor = 2
  luaunit.assert_equals(adapter:apply(adapter.owner_token()).status, "INVALID anchor not assigned")
  luaunit.assert_equals(adapter:describe("M08", "snapshot:M08", {source_route = "snapshot:M08"}).descriptors[1].value, "2")
  editor.draft.anchor = 1
  m_clock:start()
  local applied = adapter:apply(adapter.owner_token(), target(editor), editor.generation)
  luaunit.assert_true(applied.ok)
  luaunit.assert_equals(applied.code, "queued")
  luaunit.assert_equals(applied.status, "NEXT CYCLE")
  luaunit.assert_equals(applied.commit_boundary, "channel_cycle")
  luaunit.assert_equals(channel.musical_merge.mode, "foundation")
  local unchanged = adapter:apply(adapter.owner_token())
  luaunit.assert_equals(unchanged.code, "unchanged")
end

function test_ui_adapters_merge_snapshot_variants_are_immutable_and_skip_get_fields()
  local adapter, editor, song, channel = fresh({1})
  editor.draft.mode, editor.draft.anchor, editor.draft.amount, editor.dirty = "foundation", 1, 75, true
  m_clock:start()
  luaunit.assert_true(adapter:apply(adapter.owner_token()).ok)
  local snapshot = adapter:snapshot({source_route = "snapshot:M04"}, 7).snapshot
  luaunit.assert_error_msg_contains("immutable", function() snapshot.status = "x" end)
  luaunit.assert_error_msg_contains("immutable", function() snapshot.draft.mode = "off" end)
  local calls = 0
  local original = editor.get_fields
  editor.get_fields = function(...) calls = calls + 1; return original(...) end
  local m04 = adapter:describe("M04", "snapshot:M04", {source_route = "snapshot:M04", snapshot = snapshot})
  editor.get_fields = original
  luaunit.assert_equals(calls, 0)
  luaunit.assert_true(m04.ok)
  luaunit.assert_equals(ids(m04), {"active_amount", "queued_amount", "changed", "result_is_active"})
  luaunit.assert_equals(m04.descriptors[1].value, "100")
  luaunit.assert_equals(m04.descriptors[3].value, "ON")
  luaunit.assert_equals(m04.descriptors[2].value, "75")
  luaunit.assert_equals(m04.descriptors[4].value, "OFF")
  luaunit.assert_equals(m04.descriptors[1].domain.event_id, 7)
  merge_state.on_cycle_boundary(song, 1, channel.musical_merge)
  local later = adapter:describe("M04", "snapshot:M04", {source_route = "snapshot:M04"})
  luaunit.assert_equals(later.descriptors[1].value, "75")
  luaunit.assert_equals(later.descriptors[2].value, "NONE")
  luaunit.assert_equals(later.descriptors[4].value, "ON")
  for _, id in ipairs({"M09", "M11"}) do
    local variant = adapter:describe(id, "snapshot:" .. id, {source_route = "snapshot:" .. id})
    luaunit.assert_true(variant.ok, id)
    local expected = {}
    for _, field in ipairs(ui_adapters.spec.screens[id].fields) do expected[#expected + 1] = field end
    luaunit.assert_equals(ids(variant), expected)
  end
  luaunit.assert_equals(adapter:describe("M02", "snapshot:M02", {source_route = "snapshot:M02"}).code, "foreign_route")
end

function test_ui_adapters_merge_chord_group_source_lists_enabled_groups()
  local adapter, editor, song = fresh({1})
  local group = harmony_config.new_group(1); group.enabled = true
  song.voicing = {schema_version = 1, groups = {[2] = group}}
  editor.draft.target = {kind = "chord"}
  open_id(adapter, editor, "pitch"); open_id(adapter, editor, "target_setup")
  local d = assert_parity(adapter, editor).descriptors[1]
  luaunit.assert_equals(d.domain.enum, {2})
  luaunit.assert_true(adapter:edit("group_id", 1, target(editor), editor.generation).ok)
  luaunit.assert_equals(editor.draft.target.group_id, 2)
end

-- Structural chord tones (MM-10) reference lifecycle: deleting or disabling the
-- marker chord group repairs every Structure reference in the same song-slot
-- transaction, activates with the group at the shared pattern boundary while
-- playing, replaces queued requests, invalidates stale drafts, is one history
-- event, settles on Stop and saves only the valid requested snapshot.
-- Contract: docs/musical-merge-extensions-plan.md §4 "Chord source" and
-- "Reference lifecycle". README "Merge Shape" still lists passing-note freedom
-- as a later design until the MM-11 UI/docs card, so every assertion is a
-- characterisation of that approved contract, outside the current manual.

local feature_editor = include("mosaic/lib/pages/channel_edit_page/channel_feature_editor")
local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state = include("mosaic/lib/musical_merge/state")
local harmony_config = include("mosaic/lib/harmony/config")
local harmony_config_state = include("mosaic/lib/harmony/config_state")
local transaction = include("mosaic/lib/optional_config_transaction")
local validation = include("mosaic/lib/project_validation")
local structure = include("mosaic/lib/musical_merge/structure")
local pattern_model = include("mosaic/lib/pattern")

local function group(members)
  local value = harmony_config.four_part_smooth(1, members or {9, 10, 11, 12})
  value.enabled = true
  return value
end

local function structured(markers, group_id)
  local value = merge_config.new()
  value.mode, value.anchor = "foundation", 1
  value.structure = {markers = markers, group_id = group_id}
  return value
end

-- Channel 2 (4-step loop) and channel 3 (12-step loop) both mark with group 1;
-- the global pattern is 16 steps, so their cycles are unequal and neither
-- divides the pattern boundary evenly for channel 3.
local function setup()
  program.init(); globals.reset(); params.reset(); memory.init()
  m_clock.init()
  merge_state.reset(); harmony_config_state.reset()
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  song.global_pattern_length = 16
  for _, position in ipairs({1, 5, 9, 13}) do song.patterns[1].trig_values[position] = 1 end
  song.voicing = {schema_version = 1, groups = {[1] = group(), [2] = group({13, 14, 15, 16})}}
  song.voicing.groups[2].enabled = false
  for number, loop_end in pairs({[2] = 4, [3] = 12}) do
    local channel = song.channels[number]
    channel.selected_patterns = {[1] = true}
    channel.end_trig = {loop_end, 4}
  end
  song.channels[2].musical_merge = structured("every_4", 1)
  song.channels[3].musical_merge = structured("every_8", 1)
  return song
end

local function select_label(value, label)
  for index, field in ipairs(value:get_fields()) do
    if field.label == label then value.selected = index; return field end
  end
  error("missing field " .. label .. " on " .. value:get_screen())
end

local function open_label(value, label) select_label(value, label); value:key(3) end

local function delete_group(id)
  local value = feature_editor.new("harmony"); value:enter(); open_label(value, "Groups")
  value.selected_group = id; open_label(value, "Delete group"); open_label(value, "Confirm delete")
  return value
end

local function disable_group(id)
  local value = feature_editor.new("harmony"); value:enter(); open_label(value, "Groups")
  value.selected_group = id; open_label(value, "Members")
  select_label(value, "Group enabled"); value:enc(3, 1); value:key(3)
  return value
end

local function active_structure(song, number)
  return merge_state.effective(song, number, song.channels[number].musical_merge or merge_config.new()).config.structure
end

local function active_groups(song)
  return harmony_config_state.effective_song(song, song.voicing or {schema_version = 1, groups = {}}).groups
end

-- The pairing invariant: an active Structure reference names an active enabled group.
local function assert_paired(song, label)
  for number = 2, 3 do
    local value = active_structure(song, number)
    if value and value.markers ~= "off" then
      luaunit.assert_true(structure.group_available({groups = active_groups(song)}, value.group_id),
        (label or "") .. " channel " .. number)
    end
  end
end

local function select_channel(number) program.get().selected_channel = number end

local function pulses(count)
  for _ = 1, count do m_clock.get_clock_lattice():pulse() end
end

local function stop_transport()
  local saved_nb, saved_handler, saved_stop = rawget(_G, "nb"), rawget(_G, "norns_param_state_handler"), m_midi.stop
  rawset(_G, "nb", {stop_all = function() end})
  rawset(_G, "norns_param_state_handler", include("mosaic/lib/devices/norns_param_state_handler"))
  m_midi.stop = function() end
  local ok, err = pcall(function() m_clock:stop() end)
  rawset(_G, "nb", saved_nb); rawset(_G, "norns_param_state_handler", saved_handler); m_midi.stop = saved_stop
  if not ok then error(err, 0) end
end

-- Apply/load validation: markers on need an existing enabled group.
function test_structure_transaction_validation_requires_existing_enabled_group()
  local song = setup()
  local snapshot = transaction.snapshot(song)
  luaunit.assert_true(transaction.validate(song, snapshot))
  for _, id in ipairs({2, 3}) do
    snapshot.channels[2].musical_merge = structured("anchors", id)
    luaunit.assert_equals({transaction.validate(song, snapshot)}, {nil, "channel 2 structure group unavailable"})
  end
  -- Inactive merge modes are validated too: the stored reference is what is saved.
  snapshot.channels[2].musical_merge = structured("anchors", 3); snapshot.channels[2].musical_merge.mode = "off"
  luaunit.assert_equals({transaction.validate(song, snapshot)}, {nil, "channel 2 structure group unavailable"})
  snapshot.channels[2].musical_merge = structured("off", nil)
  luaunit.assert_true(transaction.validate(song, snapshot))
end

function test_structure_project_validation_requires_existing_enabled_group()
  local song = setup()
  local saved = fn.deep_copy(program.prepare_for_save())
  luaunit.assert_true(validation.check({"ok", saved}))
  saved.song_patterns[1].channels[3].musical_merge = structured("every_4", 2)
  luaunit.assert_equals({validation.check({"disabled", saved})}, {nil, "Slot 1 ch 3 merge structure group unavailable"})
  saved.song_patterns[1].channels[3].musical_merge = structured("every_4", 7)
  luaunit.assert_equals({validation.check({"missing", saved})}, {nil, "Slot 1 ch 3 merge structure group unavailable"})
  luaunit.assert_not_nil(song)
end

function test_structure_merge_editor_rejects_unavailable_group_and_stores_canonical_off()
  local song = setup()
  select_channel(2)
  local value = feature_editor.new("merge"); value:enter()
  value.draft.structure = {markers = "every_8", group_id = 2}; value.dirty = true
  luaunit.assert_false(value:key(3))
  luaunit.assert_equals(value.status, "INVALID structure group unavailable")
  luaunit.assert_equals(song.channels[2].musical_merge.structure, {markers = "every_4", group_id = 1})
  value.draft.structure = {markers = "off", group_id = nil}; value.dirty = true
  luaunit.assert_true(value:key(3))
  luaunit.assert_equals(song.channels[2].musical_merge.structure, {markers = "off"})
end

-- Stopped delete: group and every reference change together; one history event.
function test_structure_stopped_group_delete_repairs_references_as_one_history_event()
  local song = setup()
  local counts = {memory.get_event_count(2), memory.get_event_count(3)}
  local value = delete_group(1)
  luaunit.assert_equals(value.status, "APPLIED")
  luaunit.assert_nil(song.voicing.groups[1])
  for number = 2, 3 do
    luaunit.assert_equals(song.channels[number].musical_merge.structure, {markers = "off"})
    luaunit.assert_equals(active_structure(song, number), {markers = "off"})
  end
  luaunit.assert_equals({memory.get_event_count(2), memory.get_event_count(3)}, {counts[1] + 1, counts[2] + 1})
  memory.undo(3)
  luaunit.assert_not_nil(song.voicing.groups[1])
  luaunit.assert_equals(song.channels[2].musical_merge.structure, {markers = "every_4", group_id = 1})
  luaunit.assert_equals(song.channels[3].musical_merge.structure, {markers = "every_8", group_id = 1})
  assert_paired(song, "after undo")
  memory.redo(2)
  luaunit.assert_nil(song.voicing.groups[1])
  luaunit.assert_equals(song.channels[3].musical_merge.structure, {markers = "off"})
  assert_paired(song, "after redo")
end

function test_structure_stopped_group_disable_repairs_references()
  local song = setup()
  local value = disable_group(1)
  luaunit.assert_equals(value.status, "APPLIED")
  luaunit.assert_false(song.voicing.groups[1].enabled)
  for number = 2, 3 do luaunit.assert_equals(song.channels[number].musical_merge.structure, {markers = "off"}) end
  memory.undo(2)
  luaunit.assert_true(song.voicing.groups[1].enabled)
  luaunit.assert_equals(song.channels[2].musical_merge.structure, {markers = "every_4", group_id = 1})
end

-- Unrelated references are untouched: deleting group 2 changes no structure.
function test_structure_group_delete_leaves_other_group_references()
  local song = setup()
  song.voicing.groups[2].enabled = true
  song.channels[3].musical_merge = structured("anchors", 2)
  delete_group(1)
  luaunit.assert_equals(song.channels[2].musical_merge.structure, {markers = "off"})
  luaunit.assert_equals(song.channels[3].musical_merge.structure, {markers = "anchors", group_id = 2})
end

-- Playing: a stale dirty merge draft is invalidated; the delete, an older
-- queued Structure request and the repair activate together at the pattern
-- boundary (never at an earlier, unequal channel wrap), paired at every pulse.
function test_structure_playing_group_delete_activates_atomically_across_unequal_cycles()
  local song = setup()
  m_clock:start()
  -- Channel 3 has a queued (NEXT CYCLE) Structure request naming group 1.
  select_channel(3)
  local queued = feature_editor.new("merge"); queued:enter()
  queued.draft.structure = {markers = "anchors", group_id = 1}; queued.dirty = true
  luaunit.assert_true(queued:key(3)); luaunit.assert_equals(queued.status, "NEXT CYCLE")
  -- Channel 2 has an unapplied draft.
  select_channel(2)
  local stale = feature_editor.new("merge"); stale:enter()
  stale.draft.amount = 40; stale.dirty = true

  local value = delete_group(1)
  luaunit.assert_equals(value.status, "NEXT PATTERN")
  luaunit.assert_false(stale:key(3))
  luaunit.assert_equals(stale.status, "INVALID STALE DRAFT")
  luaunit.assert_equals(song.channels[2].musical_merge.amount, 100)
  -- The requested snapshot is already repaired; the active one is the old pair.
  luaunit.assert_equals(song.channels[3].musical_merge.structure, {markers = "off"})
  luaunit.assert_not_nil(active_groups(song)[1])
  luaunit.assert_equals(active_structure(song, 2), {markers = "every_4", group_id = 1})

  local wraps, boundary_seen = {[2] = 0, [3] = 0}, false
  local previous = {[2] = program.get_current_step_for_channel(2), [3] = program.get_current_step_for_channel(3)}
  for _ = 1, 16 * 24 + 48 do
    pulses(1)
    for number = 2, 3 do
      local current = program.get_current_step_for_channel(number)
      if current < previous[number] then wraps[number] = wraps[number] + 1 end
      previous[number] = current
    end
    assert_paired(song, "pulse")
    if active_groups(song)[1] == nil then
      boundary_seen = true
      luaunit.assert_equals(active_structure(song, 2), {markers = "off"})
      luaunit.assert_equals(active_structure(song, 3), {markers = "off"})
    else
      luaunit.assert_false(boundary_seen)
      luaunit.assert_equals(active_structure(song, 2), {markers = "every_4", group_id = 1})
      -- The old queue never restores the reference at channel 3's earlier wrap.
      luaunit.assert_equals(active_structure(song, 3), {markers = "every_8", group_id = 1})
    end
  end
  luaunit.assert_true(boundary_seen)
  luaunit.assert_true(wraps[2] >= 3)
  luaunit.assert_true(wraps[3] >= 1)
  stop_transport()
end

-- Playing disable: same pairing through the boundary, then Stop settles.
function test_structure_playing_group_disable_waits_for_pattern_boundary()
  local song = setup()
  m_clock:start()
  disable_group(1)
  luaunit.assert_true(active_groups(song)[1].enabled)
  merge_state.on_cycle_boundary(song, 2, song.channels[2].musical_merge)
  merge_state.on_cycle_boundary(song, 3, song.channels[3].musical_merge)
  luaunit.assert_equals(active_structure(song, 2), {markers = "every_4", group_id = 1})
  assert_paired(song, "after channel wraps")
  harmony_config_state.on_pattern_boundary(song); merge_state.on_pattern_boundary(song)
  luaunit.assert_false(active_groups(song)[1].enabled)
  luaunit.assert_equals(active_structure(song, 2), {markers = "off"})
  stop_transport()
end

-- Stop settles the whole requested snapshot together.
function test_structure_stop_settles_pending_repair_together()
  local song = setup()
  m_clock:start()
  delete_group(1)
  luaunit.assert_not_nil(active_groups(song)[1])
  stop_transport()
  luaunit.assert_nil(active_groups(song)[1])
  for number = 2, 3 do luaunit.assert_equals(active_structure(song, number), {markers = "off"}) end
  assert_paired(song, "after stop")
end

-- A later per-channel request replaces the pending global one, so neither the
-- boundary nor Stop lands the older repair over it.
function test_structure_later_channel_request_replaces_pending_global_repair()
  local song = setup()
  m_clock:start()
  delete_group(1)
  select_channel(2)
  local value = feature_editor.new("merge"); value:enter()
  luaunit.assert_equals(value.draft.structure, {markers = "off"})
  value.draft.amount = 40; value.dirty = true
  luaunit.assert_true(value:key(3))
  harmony_config_state.on_pattern_boundary(song); merge_state.on_pattern_boundary(song)
  luaunit.assert_equals(merge_state.effective(song, 2, song.channels[2].musical_merge).config.amount, 40)
  stop_transport()
  luaunit.assert_equals(merge_state.effective(song, 2, song.channels[2].musical_merge).config,
    song.channels[2].musical_merge)
end

-- Review D1: a normal merge edit made while a cross-feature repair (or its
-- undo restoration) is pending stays with the shared pattern boundary. It
-- replaces the pending global request, leaves no channel queue, reports NEXT
-- PATTERN, and neither channel's earlier (unequal) wraps activate the
-- repaired or restored references before the group change. Audible: channel
-- 2 plays raw 1 (62) at its every_4 marker, snapped to C (60) while the group
-- and markers are active and paired.
local function channel_pitches(before)
  local result = {}
  for index = before + 1, #midi_note_on_events do
    local event = midi_note_on_events[index]
    result[event[3]] = result[event[3]] or {}
    table.insert(result[event[3]], event[1])
  end
  return result
end

local function amount_edit(number, amount)
  select_channel(number)
  local value = feature_editor.new("merge"); value:enter()
  value.draft.amount = amount; value.dirty = true
  luaunit.assert_true(value:key(3))
  return value
end

local function run_to_pattern_boundary(song, expect_before, expect_after, label)
  local wraps, boundary_seen = {[2] = 0, [3] = 0}, false
  local previous = {[2] = program.get_current_step_for_channel(2), [3] = program.get_current_step_for_channel(3)}
  local heard = {before = {}, after = {}}
  for _ = 1, 16 * 24 + 48 do
    local count = #midi_note_on_events
    pulses(1)
    for number = 2, 3 do
      local current = program.get_current_step_for_channel(number)
      if current < previous[number] then wraps[number] = wraps[number] + 1 end
      previous[number] = current
    end
    assert_paired(song, label .. " pulse")
    local switched = expect_after.groups(active_groups(song))
    if switched then boundary_seen = true else luaunit.assert_false(boundary_seen, label) end
    local expected = switched and expect_after or expect_before
    for number = 2, 3 do
      local config = merge_state.effective(song, number, song.channels[number].musical_merge).config
      luaunit.assert_equals(config.structure, expected.structure[number], label .. " channel " .. number)
      luaunit.assert_equals(config.amount, expected.amount[number], label .. " amount " .. number)
    end
    for _, pitch in ipairs(channel_pitches(count)[2] or {}) do
      table.insert(switched and heard.after or heard.before, pitch)
    end
  end
  luaunit.assert_true(boundary_seen, label)
  luaunit.assert_true(wraps[2] >= 3, label)
  luaunit.assert_true(wraps[3] >= 1, label)
  return heard
end

local function marker_raws(song)
  for _, position in ipairs({1, 5, 9, 13}) do song.patterns[1].note_values[position] = 1 end
  for number = 2, 3 do program.get().devices[number].midi_channel = number end
  for number = 2, 3 do pattern_model.update_working_pattern(number, song) end
end

local function repair_then_amount_edit(repair, label)
  local song = setup(); marker_raws(song)
  m_clock:start()
  local value = repair(1)
  luaunit.assert_equals(value.status, "NEXT PATTERN", label)
  local edit = amount_edit(2, 40)
  luaunit.assert_equals(edit.status, "NEXT PATTERN", label)
  local record = merge_state.peek(song, 2)
  luaunit.assert_nil(record.queued, label .. " no channel queue")
  luaunit.assert_equals(record.global_queued.amount, 40, label)
  luaunit.assert_equals(record.global_queued.structure, {markers = "off"}, label)
  local on = {markers = "every_4", group_id = 1}
  local heard = run_to_pattern_boundary(song, {
    structure = {[2] = on, [3] = {markers = "every_8", group_id = 1}}, amount = {[2] = 100, [3] = 100}
  }, {
    groups = function(groups) return not structure.group_available({groups = groups}, 1) end,
    structure = {[2] = {markers = "off"}, [3] = {markers = "off"}}, amount = {[2] = 40, [3] = 100}
  }, label)
  luaunit.assert_true(#heard.before >= 3, label)
  for _, pitch in ipairs(heard.before) do luaunit.assert_equals(pitch, 60, label .. " snapped before") end
  stop_transport()
  luaunit.assert_equals(merge_state.effective(song, 2, song.channels[2].musical_merge).config,
    song.channels[2].musical_merge)
  assert_paired(song, label .. " after stop")
end

function test_structure_amount_edit_during_pending_delete_waits_for_pattern_boundary()
  repair_then_amount_edit(delete_group, "delete")
end

function test_structure_amount_edit_during_pending_disable_waits_for_pattern_boundary()
  repair_then_amount_edit(disable_group, "disable")
end

-- The same for an undo restoration: the restored references must not reach
-- channel 2's wrap before the restored group reaches the pattern boundary.
function test_structure_amount_edit_during_pending_undo_restoration_waits_for_pattern_boundary()
  local song = setup(); marker_raws(song)
  delete_group(1)
  m_clock:start()
  memory.undo(2)
  luaunit.assert_nil(active_groups(song)[1])
  local edit = amount_edit(2, 40)
  luaunit.assert_equals(edit.status, "NEXT PATTERN")
  luaunit.assert_nil(merge_state.peek(song, 2).queued)
  local heard = run_to_pattern_boundary(song, {
    structure = {[2] = {markers = "off"}, [3] = {markers = "off"}}, amount = {[2] = 100, [3] = 100}
  }, {
    groups = function(groups) return structure.group_available({groups = groups}, 1) end,
    structure = {[2] = {markers = "every_4", group_id = 1}, [3] = {markers = "every_8", group_id = 1}},
    amount = {[2] = 40, [3] = 100}
  }, "undo")
  luaunit.assert_true(#heard.before >= 3)
  for _, pitch in ipairs(heard.before) do luaunit.assert_equals(pitch, 62, "unsnapped before") end
  for _, pitch in ipairs(heard.after) do luaunit.assert_equals(pitch, 60, "snapped after") end
  stop_transport()
end

-- An edit that restores the active configuration withdraws the pending
-- global request without leaving a channel queue: undoing both the Amount
-- edit and the deletion before the boundary changes nothing at any wrap.
function test_structure_undo_of_edit_and_delete_withdraws_pending_global_request()
  local song = setup()
  m_clock:start()
  delete_group(1)
  amount_edit(2, 40)
  memory.undo(2)
  local record = merge_state.peek(song, 2)
  luaunit.assert_nil(record.queued)
  luaunit.assert_equals(record.global_queued.amount, 100)
  luaunit.assert_equals(record.global_queued.structure, {markers = "off"})
  memory.undo(2)
  luaunit.assert_nil(record.queued)
  luaunit.assert_nil(record.global_queued)
  merge_state.on_cycle_boundary(song, 2, song.channels[2].musical_merge)
  luaunit.assert_equals(active_structure(song, 2), {markers = "every_4", group_id = 1})
  assert_paired(song, "withdrawn")
  stop_transport()
end

-- Undo while playing restores group and references through the same boundary.
function test_structure_playing_undo_redo_restores_through_pattern_boundary()
  local song = setup()
  delete_group(1)
  m_clock:start()
  memory.undo(2)
  luaunit.assert_not_nil(song.voicing.groups[1])
  luaunit.assert_equals(song.channels[2].musical_merge.structure, {markers = "every_4", group_id = 1})
  luaunit.assert_nil(active_groups(song)[1])
  luaunit.assert_equals(active_structure(song, 2), {markers = "off"})
  merge_state.on_cycle_boundary(song, 2, song.channels[2].musical_merge)
  luaunit.assert_equals(active_structure(song, 2), {markers = "off"})
  harmony_config_state.on_pattern_boundary(song); merge_state.on_pattern_boundary(song)
  luaunit.assert_not_nil(active_groups(song)[1])
  luaunit.assert_equals(active_structure(song, 2), {markers = "every_4", group_id = 1})
  luaunit.assert_equals(active_structure(song, 3), {markers = "every_8", group_id = 1})
  memory.redo(3)
  luaunit.assert_not_nil(active_groups(song)[1])
  harmony_config_state.on_pattern_boundary(song); merge_state.on_pattern_boundary(song)
  luaunit.assert_nil(active_groups(song)[1])
  assert_paired(song, "after redo boundary")
  stop_transport()
end

-- Save while a repair is pending stores the valid requested snapshot.
function test_structure_save_during_pending_repair_stores_requested_snapshot()
  local song = setup()
  m_clock:start()
  delete_group(1)
  luaunit.assert_not_nil(active_groups(song)[1])
  local saved = fn.deep_copy(program.prepare_for_save())
  luaunit.assert_true(validation.check({"pending", saved}))
  luaunit.assert_true(validation.migrate({"pending", saved}))
  local slot = saved.song_patterns[1]
  luaunit.assert_nil(slot.voicing.groups[1])
  for number = 2, 3 do luaunit.assert_equals(slot.channels[number].musical_merge.structure, {markers = "off"}) end
  stop_transport()
  merge_state.reset(); harmony_config_state.reset()
  program.set(saved); program.set_selected_song_pattern(1)
  local reloaded = program.get_song_pattern(1)
  luaunit.assert_equals(reloaded.channels[2].musical_merge.structure, {markers = "off"})
  luaunit.assert_equals(active_structure(reloaded, 2), {markers = "off"})
end

-- Invalid or stale history restoration is rejected before any mutation.
function test_structure_invalid_restoration_rejects_without_mutation()
  local song = setup()
  local before = transaction.snapshot(song)
  local after = transaction.copy(before)
  after.voicing.groups[1] = nil
  -- A snapshot that deletes the group but keeps the references is invalid.
  luaunit.assert_equals({memory.record_optional_config(1, {2, 3}, before, after, "pattern")},
    {nil, "channel 2 structure group unavailable"})
  luaunit.assert_not_nil(song.voicing.groups[1])
  luaunit.assert_equals(song.channels[2].musical_merge.structure, {markers = "every_4", group_id = 1})
end

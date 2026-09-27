-- Structural chord tones (MM-10) through the working-pattern build, step.handle,
-- the Harmony Pattern material loop, Revoice/Ensemble and the persisted Pattern
-- identity. Contract: docs/musical-merge-extensions-plan.md §4. README "Merge
-- Shape" still lists passing-note freedom as a later design until the MM-11
-- UI/docs card, so every assertion is a characterisation of that approved
-- contract, outside the current manual. Default scale: C major, raw n is the
-- n-th degree from middle C (0=60, 1=62, 3=65, 5=69, 6=71).

local step = include("mosaic/lib/step")
local pattern_model = include("mosaic/lib/pattern")
local harmony_config = include("mosaic/lib/harmony/config")
local harmony_config_state = include("mosaic/lib/harmony/config_state")
local harmony_runtime_state = include("mosaic/lib/harmony/state")
local harmony_inspection = include("mosaic/lib/harmony/inspection")
local harmony_grid_projection = include("mosaic/lib/harmony/grid_projection")
local pattern_harmony = include("mosaic/lib/harmony/pattern")
local merge_config = include("mosaic/lib/musical_merge/config")
local merge_state = include("mosaic/lib/musical_merge/state")
local quantiser = include("mosaic/lib/quantiser")
local validation = include("mosaic/lib/project_validation")
local transaction = include("mosaic/lib/optional_config_transaction")

include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
local m_clock = include("mosaic/lib/clock/m_clock")

local function reset_runtime()
  merge_state.reset()
  harmony_config_state.reset()
  harmony_runtime_state.reset()
  harmony_inspection.reset()
end

local function exact_role(pitch)
  return {min=pitch,max=pitch,centre=pitch,preferred_leap=127,strict_leap=false,enabled=true}
end

-- An enabled Ensemble group whose template is C-E-G (pitch classes 0, 4, 7).
local function chord_group(offsets)
  local group = harmony_config.four_part_smooth(1, {9, 10, 11, 12})
  group.enabled = true
  if offsets then
    group.template = {offsets = offsets, required = {}}
    for index = 1, #offsets do group.template.required[index] = true end
  end
  return group
end

-- Channel 1 Foundation: pattern 1 is the anchor, pattern 2 the additions, both
-- carrying the same raw value at every position so the merged value is known.
local function structure_song(options)
  program.init(); globals.reset(); params.reset(); memory.init(); m_clock.init(); reset_runtime()
  if not options.stopped then m_clock:start() end
  program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  song.channels[1].end_trig = {16, 4}   -- a 16-step loop unless a test says otherwise
  for number, trigs in pairs({[1] = options.anchors or {}, [2] = options.additions or {}}) do
    local value = program.initialise_default_pattern()
    for position, raw in pairs(options.raws or {}) do value.note_values[position] = raw end
    for position, raw in pairs(number == 1 and options.anchor_raws or {}) do value.note_values[position] = raw end
    for _, position in ipairs(trigs) do value.trig_values[position] = 1 end
    song.patterns[number] = value
  end
  song.voicing = {schema_version = 1, groups = {[1] = chord_group(options.offsets)}}
  local channel = song.channels[1]
  fn.add_to_set(channel.selected_patterns, 1)
  fn.add_to_set(channel.selected_patterns, 2)
  local merge = merge_config.new()
  merge.mode, merge.anchor = "foundation", 1
  merge.keep_anchor_pitch = options.keep_anchor_pitch == true
  merge.target = options.target or {kind = "legacy"}
  if options.markers and options.markers ~= "off" then
    merge.structure = {markers = options.markers, group_id = options.group_id or 1}
  end
  channel.musical_merge = merge
  if options.voicing then channel.voicing = options.voicing end
  pattern_model.update_working_pattern(1, song)
  return song, channel
end

local function play(steps)
  local before = #midi_note_on_events
  for _, position in ipairs(steps) do step.handle(1, position) end
  local pitches = {}
  for index = before + 1, #midi_note_on_events do pitches[#pitches + 1] = midi_note_on_events[index][1] end
  return pitches
end

local function sorted_markers(channel)
  local result = {}
  local foundation = channel.working_pattern.foundation
  for position in pairs(foundation and foundation.markers or {}) do result[#result + 1] = position end
  table.sort(result)
  return result
end

local every_4_fixture = {anchors = {1, 9}, additions = {2, 5, 6, 13},
  raws = {[1] = 1, [2] = 1, [5] = 3, [6] = 3, [9] = 5, [13] = 6}}

local function with(base, overrides)
  local result = {}
  for key, value in pairs(base) do result[key] = value end
  for key, value in pairs(overrides) do result[key] = value end
  return result
end

-- §4 Markers + Shared pitch resolution: marker onsets snap after scale
-- conversion to the nearest chord pitch class (lower on ties); others unchanged.
function test_structure_every_4_markers_snap_only_marker_onsets()
  local song, channel = structure_song(with(every_4_fixture, {markers = "every_4"}))
  luaunit.assert_equals(sorted_markers(channel), {1, 5, 9, 13})
  luaunit.assert_equals(play({1, 2, 5, 6, 9, 13}), {60, 62, 64, 65, 67, 72})
  luaunit.assert_equals(song.patterns[1].note_values[1], 1)
end

-- §0 Off stays exact: markers Off plays the legacy Foundation pitches.
function test_structure_markers_off_output_is_legacy()
  local _, channel = structure_song(with(every_4_fixture, {markers = "off"}))
  luaunit.assert_nil(channel.working_pattern.foundation.markers)
  luaunit.assert_equals(play({1, 2, 5, 6, 9, 13}), {62, 62, 65, 65, 69, 71})
end

-- Markers are Foundation-only: merge Off with inactive stored settings is legacy.
function test_structure_inactive_outside_foundation()
  local song, channel = structure_song(with(every_4_fixture, {markers = "every_4"}))
  channel.musical_merge.mode = "off"; merge_state.reset(); pattern_model.update_working_pattern(1, song)
  luaunit.assert_nil(channel.working_pattern.foundation)
  local pitches = play({1, 9})
  luaunit.assert_equals(pitches, {62, 69})
end

function test_structure_markers_count_from_nonzero_start_short_loop_and_global_cap()
  local song, channel = structure_song(with(every_4_fixture, {markers = "every_4"}))
  channel.start_trig, channel.end_trig = {3, 4}, {2, 5}
  pattern_model.update_working_pattern(1, song)
  luaunit.assert_equals(sorted_markers(channel), {3, 7, 11, 15})
  channel.musical_merge.structure.markers = "every_8"; merge_state.reset(); pattern_model.update_working_pattern(1, song)
  luaunit.assert_equals(sorted_markers(channel), {3, 11})
  song.global_pattern_length = 8; merge_state.reset(); pattern_model.update_working_pattern(1, song)
  luaunit.assert_equals(sorted_markers(channel), {3})
  channel.musical_merge.structure.markers = "every_4"; merge_state.reset(); pattern_model.update_working_pattern(1, song)
  luaunit.assert_equals(sorted_markers(channel), {3, 7})
  song.global_pattern_length = 64
  channel.start_trig, channel.end_trig = {10, 4}, {12, 4}; pattern_model.update_working_pattern(1, song)
  luaunit.assert_equals(sorted_markers(channel), {10})
end

-- §4 anchors: every Foundation anchor onset, including Keep anchor pitch as the
-- existing anchor-pitch choice before conversion and snapping.
function test_structure_anchor_markers_snap_anchor_onsets_with_keep_anchor_pitch()
  local fixture = {anchors = {1, 5}, additions = {3, 5}, raws = {[1] = 1, [3] = 1, [5] = 1},
    anchor_raws = {[5] = 5}, markers = "anchors"}
  local _, channel = structure_song(fixture)
  luaunit.assert_equals(sorted_markers(channel), {1, 5})
  luaunit.assert_equals(channel.working_pattern.note_values[5], 3)   -- average of 5 and 1
  luaunit.assert_equals(play({1, 3, 5}), {60, 62, 64})                -- 65 snaps to E
  structure_song(with(fixture, {keep_anchor_pitch = true}))
  luaunit.assert_equals(play({1, 3, 5}), {60, 62, 67})                -- kept 69 snaps to G
end

-- §4 Between markers: additions keep the Addition Target, anchors legacy pitch.
function test_structure_between_markers_additions_keep_addition_target_and_anchors_legacy()
  local fixture = {anchors = {1, 3}, additions = {2, 6, 9},
    raws = {[1] = 1, [2] = 1, [3] = 1, [6] = 3, [9] = 3}, target = {kind = "degrees", degrees = {1}}}
  structure_song(with(fixture, {markers = "off"}))
  local off = play({1, 2, 3, 6, 9})
  luaunit.assert_equals(off, {62, 60, 62, 60, 60})
  structure_song(with(fixture, {markers = "every_8"}))
  local on = play({1, 2, 3, 6, 9})
  luaunit.assert_equals(on, {60, 60, 62, 60, 64})
  -- Only the marker positions (1 and 9) differ.
  luaunit.assert_equals({off[2], off[3], off[4]}, {on[2], on[3], on[4]})
end

-- §4: an eligible marker suppresses merged-pentatonic; between markers it stays.
function test_structure_marker_suppresses_merged_pentatonic_only_at_markers()
  -- Both patterns trig at 5 (marker) and 6: merged values, anchor role.
  local fixture = {anchors = {5, 6}, additions = {5, 6}, raws = {[5] = 3, [6] = 3},
    markers = "every_4", offsets = {2, 3}}   -- chord E-F (pitch classes 4, 5)
  local song = structure_song(fixture)
  params:set("merged_lock_to_pentatonic", 2)
  luaunit.assert_true(song.channels[1].working_pattern.merged_notes[5] == true)
  -- Pentatonic would give 64 at the marker; suppressed it converts to 65 (F).
  luaunit.assert_equals(play({5, 6}), {65, 64})
  params:set("all_scales_lock_to_pentatonic", 2)
  -- The global all-scales policy keeps its upstream conversion: 64 is a chord tone.
  luaunit.assert_equals(play({5}), {64})
end

-- §4: explicit note-mask, random, fixed and quantised-fixed keep the complete
-- legacy path at a marker, with their existing reason.
function test_structure_explicit_pitch_bypasses_win_at_markers()
  local cases = {
    {name = "note_mask", setup = function(channel) channel.step_note_masks[5] = 61 end},
    {name = "fixed", setup = function(channel)
      channel.trig_lock_params[3] = {id = "fixed_note", param_id = "test_fixed"}
      program.add_step_param_trig_lock(5, 3, 63) end},
    {name = "quantised_fixed", setup = function(channel)
      channel.trig_lock_params[3] = {id = "quantised_fixed_note", param_id = "test_fixed"}
      program.add_step_param_trig_lock(5, 3, 63) end},
    {name = "random", setup = function(channel)
      channel.trig_lock_params[1] = {id = "bipolar_random_note", param_id = "test_random"}
      program.add_step_param_trig_lock(5, 1, 4) end},
  }
  local original_random = random
  local ok, err = pcall(function()
    for _, case in ipairs(cases) do
      local results = {}
      for _, markers in ipairs({"off", "every_4"}) do
        local song, channel = structure_song(with(every_4_fixture,
          {markers = markers, target = {kind = "degrees", degrees = {1}}}))
        case.setup(channel); pattern_model.update_working_pattern(1, song)
        random = function() return 1 end
        results[markers] = play({5})[1]
        local planned = harmony_inspection.snapshot(song, 1, 5).planned
        luaunit.assert_equals({planned.structural_status, planned.bypass}, {case.name, case.name}, case.name)
        luaunit.assert_nil(planned.structural_reason, case.name)
      end
      luaunit.assert_equals(results.every_4, results.off, case.name)
      luaunit.assert_not_nil(results.off, case.name)
    end
  end)
  random = original_random
  if not ok then error(err, 0) end
end

-- Inspection and the grid read the same final root decision as MIDI.
function test_structure_marker_inspection_grid_and_midi_agree()
  local song = structure_song(with(every_4_fixture, {markers = "every_4"}))
  local pitches = play({1, 2})
  local marker = harmony_inspection.snapshot(song, 1, 1)
  luaunit.assert_equals({marker.planned.structural_status, marker.planned.structural_reason, marker.planned.bypass},
    {"marker", "MARKER · CHORD G01", nil})
  luaunit.assert_equals({marker.planned.output, marker.emitted.pitch}, {pitches[1], pitches[1]})
  local grid_value, kind = harmony_grid_projection.value(song, 1, 1, 1, 1)
  luaunit.assert_equals(kind, "ordinary")
  luaunit.assert_equals(quantiser.process(grid_value, 0, 0, 1, false), pitches[1])
  local between = harmony_inspection.snapshot(song, 1, 2).planned
  luaunit.assert_equals({between.structural_status, between.structural_reason}, {"legacy", nil})
  luaunit.assert_equals(between.output, pitches[2])
end

-- Review D2 (§4 Shared pitch resolution, Downstream Harmony "Grid inspection
-- and MIDI must consume the same final root decision"): with Harmony Off a
-- reverse strum (patterns 2 and 4) sounds the root last from a delayed
-- callback. That callback must play the marker's snapped root, root-only or
-- with a local chord, while explicit bypasses and Structure Off keep the
-- legacy recomputation. Channel 1 plays raw 1 (62) at marker step 1; C-E-G
-- snaps it to 60. The local chord voice (offset 2, raw 3 = 65) is governed by
-- existing playback and not snapped.
local function note_division_index(value)
  local divisions = include("mosaic/lib/clock/divisions")
  for index, division in ipairs(divisions.note_divisions) do if division.value == value then return index end end
  error("no note division " .. tostring(value))
end

local function strum_step_one(channel, pattern_number, chord_offset, arp)
  channel.trig_lock_params[6] = {id = "chord_strum_pattern", param_id = "test_strum_pattern"}
  program.add_step_param_trig_lock(1, 6, pattern_number)
  channel.trig_lock_params[7] = {id = "chord_strum", param_id = "test_strum"}
  program.add_step_param_trig_lock(1, 7, note_division_index(1/4))
  if arp then
    channel.trig_lock_params[8] = {id = "chord_arp", param_id = "test_arp"}
    program.add_step_param_trig_lock(1, 8, note_division_index(1/4))
  end
  channel.chord_one_mask = chord_offset
end

-- Every note-on of channel 1 from step 1 and its delayed callbacks (a 1/4
-- strum delays the last voice by less than 96 pulses). The fixture has a trig
-- only at step 1 of a 16-step loop, so no later onset of the loop sounds.
local STRUM_PULSES = 96
local function strummed(song)
  local before = #midi_note_on_events
  step.handle(1, 1)
  for _ = 1, STRUM_PULSES do m_clock.get_clock_lattice():pulse() end
  local pitches = {}
  for index = before + 1, #midi_note_on_events do pitches[#pitches + 1] = midi_note_on_events[index][1] end
  return pitches, harmony_inspection.snapshot(song, 1, 1).planned
end

function test_structure_reverse_strum_delayed_root_keeps_snapped_marker_root()
  local fixture = {anchors = {1}, additions = {}, raws = {[1] = 1}}
  for _, pattern_number in ipairs({2, 4}) do
    for _, chord_offset in ipairs({0, 2}) do
      local label = "pattern " .. pattern_number .. " chord " .. chord_offset
      local song, channel = structure_song(with(fixture, {markers = "every_4"}))
      strum_step_one(channel, pattern_number, chord_offset)
      local pitches, planned = strummed(song)
      -- The root sounds last, after any chord voice.
      luaunit.assert_equals(#pitches, chord_offset == 0 and 1 or 2, label)
      luaunit.assert_equals(pitches[#pitches], 60, label)
      if chord_offset ~= 0 then luaunit.assert_equals(pitches[1], 65, label) end
      luaunit.assert_equals({planned.structural_status, planned.output}, {"marker", 60}, label)
      local grid_value = harmony_grid_projection.value(song, 1, 1, 1, 1)
      luaunit.assert_equals(quantiser.process(grid_value, 0, 0, 1, false), pitches[#pitches], label)
      -- Structure Off keeps the legacy delayed root.
      song, channel = structure_song(with(fixture, {markers = "off"}))
      strum_step_one(channel, pattern_number, chord_offset)
      pitches = strummed(song)
      luaunit.assert_equals(pitches[#pitches], 62, label .. " off")
    end
  end
end

-- An explicit pitch bypass at the marker keeps the complete legacy path in
-- the delayed callback too: the same root as Structure Off.
function test_structure_reverse_strum_delayed_root_bypass_matches_legacy()
  local fixture = {anchors = {1}, additions = {}, raws = {[1] = 1}}
  local results = {}
  for _, markers in ipairs({"off", "every_4"}) do
    local _, channel = structure_song(with(fixture, {markers = markers}))
    strum_step_one(channel, 2, 0)
    channel.step_note_masks[1] = 61
    local song = program.get_song_pattern(1); pattern_model.update_working_pattern(1, song)
    local pitches, planned = strummed(song)
    results[markers] = pitches
    if markers == "off" then luaunit.assert_nil(planned.structural_status)
    else luaunit.assert_equals(planned.structural_status, "note_mask") end
  end
  luaunit.assert_equals(results.every_4, results.off)
  luaunit.assert_equals(#results.off, 1)
end

-- The same final-root rule for an arpeggiated marker step with Harmony Off:
-- the root voice the arp sounds is the snapped marker root.
function test_structure_arp_root_voice_keeps_snapped_marker_root()
  local fixture = {anchors = {1}, additions = {}, raws = {[1] = 1}}
  local song, channel = structure_song(with(fixture, {markers = "every_4"}))
  strum_step_one(channel, 1, 0, true)
  local pitches, planned = strummed(song)
  luaunit.assert_equals(planned.output, 60)
  luaunit.assert_true(#pitches >= 1)
  luaunit.assert_equals(pitches[1], 60)
  song, channel = structure_song(with(fixture, {markers = "off"}))
  strum_step_one(channel, 1, 0, true)
  pitches = strummed(song)
  luaunit.assert_equals(pitches[1], 62)
end

-- §4 Chord source: a missing or disabled group bypasses snapping (and the
-- Addition Target) with CHORD MISSING; the next source revision recovers.
function test_structure_missing_group_is_visible_legacy_and_recovers()
  local song = structure_song(with(every_4_fixture,
    {markers = "every_4", target = {kind = "degrees", degrees = {1}}}))
  song.voicing.groups[1].enabled = false; harmony_config_state.reset_song(song)
  luaunit.assert_equals(play({5, 6}), {65, 60})
  local planned = harmony_inspection.snapshot(song, 1, 5).planned
  luaunit.assert_equals({planned.structural_status, planned.structural_reason, planned.bypass},
    {"chord_missing", "CHORD MISSING", "chord_missing"})
  song.voicing.groups[1] = nil; harmony_config_state.reset_song(song)
  luaunit.assert_equals(play({5}), {65})
  song.voicing.groups[1] = chord_group(); harmony_config_state.reset_song(song)
  luaunit.assert_equals(play({5, 6}), {64, 60})
  luaunit.assert_equals(harmony_inspection.snapshot(song, 1, 5).planned.structural_reason, "MARKER · CHORD G01")
end

-- §4 Downstream Harmony, Pattern: the loop uses the same per-position policy,
-- so a raw value resolved differently at a marker and between markers is a
-- source conflict that fails closed when mapped; unmapped values keep their
-- per-event pitch; removing the repeat recovers with the snapped pitch class.
local function pattern_voicing()
  local voicing = harmony_config.new_channel("pattern")
  voicing.roles.v1 = {min = 48, max = 59, centre = 53, preferred_leap = 127, strict_leap = false, enabled = true}
  return voicing
end

function test_structure_pattern_repeated_value_across_marker_boundary_fails_closed_when_mapped()
  local fixture = {anchors = {1}, additions = {2}, raws = {[1] = 1, [2] = 1}, markers = "every_4",
    voicing = pattern_voicing()}
  local song, channel = structure_song(fixture)
  local binding = pattern_harmony.binding_key(channel)
  luaunit.assert_equals(binding, "pattern-binding-v1|1,2|average|false,legacy|structure-v1,every_4,1")
  channel.voicing.pattern_maps[binding] = {schema_version = 1, revision = 1, assignments = {["1"] = "bass"}}
  luaunit.assert_equals(play({1, 2}), {})
  for _, position in ipairs({1, 2}) do
    local planned = harmony_inspection.snapshot(song, 1, position).planned
    luaunit.assert_equals(planned.status, "source_conflict")
    luaunit.assert_nil(planned.output)
  end
  -- Recovery: the non-marker position now carries another value.
  song.patterns[1].note_values[2], song.patterns[2].note_values[2] = 2, 2
  pattern_model.update_working_pattern(1, song)
  local pitches = play({1})
  luaunit.assert_equals(#pitches, 1)
  luaunit.assert_equals(pitches[1] % 12, 0)          -- the snapped chord pitch class C
  luaunit.assert_true(pitches[1] >= 48 and pitches[1] <= 59)
  local planned = harmony_inspection.snapshot(song, 1, 1).planned
  luaunit.assert_equals({planned.status, planned.output}, {"ok", pitches[1]})
end

function test_structure_pattern_unmapped_repeated_value_keeps_per_event_pitch()
  local fixture = {anchors = {1}, additions = {2}, raws = {[1] = 1, [2] = 1, [3] = 4},
    markers = "every_4", voicing = pattern_voicing()}
  fixture.additions = {2, 3}
  local _, channel = structure_song(fixture)
  channel.voicing.pattern_maps[pattern_harmony.binding_key(channel)] =
    {schema_version = 1, revision = 1, assignments = {["4"] = "bass"}}
  local pitches = play({1, 2, 3})
  luaunit.assert_equals({pitches[1], pitches[2]}, {60, 62})
  luaunit.assert_equals(pitches[3] % 12, 7)
end

-- §4 Downstream Harmony, Revoice: snapped marker roots bypass with MARKER
-- PRIORITY; between markers and explicit pitch bypasses keep existing behaviour.
function test_structure_revoice_marker_priority_keeps_snapped_root()
  local song = structure_song(with(every_4_fixture,
    {markers = "every_4", voicing = harmony_config.new_channel("revoice")}))
  local pitches = play({1, 2})
  luaunit.assert_equals(pitches[1], 60)
  local marker = harmony_inspection.snapshot(song, 1, 1).planned
  luaunit.assert_equals({marker.status, marker.reason, marker.bypass, marker.output},
    {"marker_priority", "MARKER PRIORITY", "marker_priority", 60})
  local between = harmony_inspection.snapshot(song, 1, 2).planned
  luaunit.assert_equals(between.status, "ok")
  luaunit.assert_nil(between.bypass)
  luaunit.assert_equals(pitches[2] % 12, 2)
  -- A note mask at a marker is an explicit pitch instruction: no snap, no marker priority.
  song.channels[1].step_note_masks[5] = 59; pattern_model.update_working_pattern(1, song)
  local masked = play({5})
  local planned = harmony_inspection.snapshot(song, 1, 5).planned
  luaunit.assert_not_equals(planned.status, "marker_priority")
  luaunit.assert_equals(planned.structural_status, "note_mask")
  luaunit.assert_equals(masked, {59})
end

-- §4 Downstream Harmony, Ensemble: same rule; local octave bypass wins first.
function test_structure_ensemble_marker_priority_after_explicit_bypasses()
  local song = structure_song(with(every_4_fixture, {markers = "every_4"}))
  local group = song.voicing.groups[1]
  group.members = {{role = "bass", channel = 1}}; group.roles = {bass = exact_role(48)}
  group.template.required = {true, false, false}
  song.channels[1].voicing = harmony_config.new_channel("ensemble"); song.channels[1].voicing.group_id = 1
  harmony_config_state.reset_song(song)
  luaunit.assert_equals(play({1, 2}), {60, 48})
  luaunit.assert_equals(harmony_inspection.snapshot(song, 1, 1).planned.status, "marker_priority")
  luaunit.assert_equals(harmony_inspection.snapshot(song, 1, 2).planned.status, "ok")
  program.add_step_octave_trig_lock(1, 1)
  local octave = play({1})
  luaunit.assert_equals(octave, {72})    -- 74 snapped to C, legacy through the octave bypass
  luaunit.assert_equals(harmony_inspection.snapshot(song, 1, 1).planned.status, "local_octave")
end

-- §4 Persisted Pattern identity: a saved v1 Foundation + Pattern map keeps its
-- exact key and mapped playback through v2 migration and save/reload; Structure
-- on selects a fresh map; Structure Off recovers the original.
local function save_and_reload()
  local saved = fn.deep_copy(program.prepare_for_save())
  luaunit.assert_true(validation.check({"structure", saved}))
  luaunit.assert_true(validation.migrate({"structure", saved}))
  reset_runtime(); program.set(saved); program.set_selected_song_pattern(1)
  local song = program.get_song_pattern(1)
  pattern_model.update_working_pattern(1, song)
  return song, song.channels[1]
end

-- History and transactions read the global transport; this test owns it (stopped).
local function with_global_clock(body)
  local saved = rawget(_G, "m_clock")
  rawset(_G, "m_clock", m_clock)
  local ok, err = pcall(body)
  rawset(_G, "m_clock", saved)
  if not ok then error(err, 0) end
end

function test_structure_pattern_map_survives_v1_migration_and_structure_toggle()
  with_global_clock(function()
  local song, channel = structure_song({anchors = {1}, additions = {2}, raws = {[1] = 1, [2] = 4},
    voicing = pattern_voicing(), stopped = true})
  channel.musical_merge = {schema_version = 1, mode = "foundation", anchor = 1, amount = 100, accent = 70,
    gap = 0, seed = 0, ranking_version = 1, cycles = 1, shape = "flat", percentages = {100},
    variation = "fixed", keep_anchor_pitch = false, target = {kind = "legacy"}}
  local legacy_key = "pattern-binding-v1|1,2|average|false,legacy"
  luaunit.assert_equals(pattern_harmony.binding_key(channel), legacy_key)
  channel.voicing.pattern_maps[legacy_key] = {schema_version = 1, revision = 3, assignments = {["1"] = "bass"}}
  merge_state.reset(); pattern_model.update_working_pattern(1, song)
  local mapped = play({1})
  luaunit.assert_equals(mapped[1] % 12, 2)

  song, channel = save_and_reload()
  luaunit.assert_equals(channel.musical_merge.schema_version, 2)
  luaunit.assert_equals(pattern_harmony.binding_key(channel), legacy_key)
  luaunit.assert_equals(channel.voicing.pattern_maps[legacy_key].assignments, {["1"] = "bass"})
  luaunit.assert_equals(play({1}), mapped)

  local function apply_structure(markers, group_id)
    local before = transaction.snapshot(song); local after = transaction.copy(before)
    after.channels[1].musical_merge.structure = {markers = markers, group_id = group_id}
    luaunit.assert_true(memory.record_optional_config(1, {1}, before, after, "channel"))
    pattern_model.update_working_pattern(1, song)
  end
  apply_structure("every_4", 1)
  luaunit.assert_equals(pattern_harmony.binding_key(channel), legacy_key .. "|structure-v1,every_4,1")
  luaunit.assert_nil(channel.voicing.pattern_maps[pattern_harmony.binding_key(channel)])
  luaunit.assert_equals(play({1}), {60})       -- a fresh (empty) map: the snapped per-event pitch
  apply_structure("off", nil)
  luaunit.assert_equals(pattern_harmony.binding_key(channel), legacy_key)
  luaunit.assert_equals(play({1}), mapped)
  song, channel = save_and_reload()
  luaunit.assert_equals(channel.voicing.pattern_maps[legacy_key],
    {schema_version = 1, revision = 3, assignments = {["1"] = "bass"}})
  luaunit.assert_equals(play({1}), mapped)
  end)
end

function test_structure_binding_key_off_mode_ignores_inactive_structure()
  local base = {selected_patterns = {[2] = true}, note_merge_mode = "up"}
  local merge = merge_config.new()
  merge.structure = {markers = "every_8", group_id = 3}
  base.musical_merge = merge
  luaunit.assert_equals(pattern_harmony.binding_key(base), "pattern-binding-v1|2|up|off")
  merge.mode, merge.anchor = "fragments", 2
  luaunit.assert_equals(pattern_harmony.binding_key(base), "pattern-binding-v1|2|up|false,legacy")
  merge.mode = "foundation"
  luaunit.assert_equals(pattern_harmony.binding_key(base), "pattern-binding-v1|2|up|false,legacy|structure-v1,every_8,3")
  -- The effective (active) configuration decides, not the requested one.
  luaunit.assert_equals(pattern_harmony.binding_key(base, merge_config.new()), "pattern-binding-v1|2|up|off")
end

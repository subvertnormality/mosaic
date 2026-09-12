-- End-to-end guards for merged pattern notes travelling through the selected
-- scale to MIDI.  The merge primitive and ordinary scale paths have broad
-- coverage elsewhere; these cases deliberately cover their junction.

local scale_merge_quantiser = include("mosaic/lib/quantiser")
local scale_merge_pattern = include("mosaic/lib/pattern")
local scale_merge_step = include("mosaic/lib/step")
local scale_merge_clock = include("mosaic/lib/clock/m_clock")

include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")

local function setup_scale_merge()
  program.init()
  globals.reset()
  params.reset()
  scale_merge_clock.init()
  scale_merge_clock:start()
end

local function install_scale(slot, scale_type, root, transpose)
  local source = scale_merge_quantiser.get_scales()[scale_type]
  program.set_scale(slot, {
    number = scale_type,
    scale = source.scale,
    pentatonic_scale = source.pentatonic_scale,
    romans = source.romans,
    root_note = root,
    chord = 1,
    chord_degree_rotation = 0,
    transpose = transpose or 0
  })
end

local function set_source(song, source, step_number, degree, mask)
  local pattern = program.initialise_default_pattern()
  pattern.trig_values[step_number] = 1
  pattern.note_values[step_number] = degree
  pattern.note_mask_values[step_number] = mask or -1
  pattern.lengths[step_number] = 1
  pattern.velocity_values[step_number] = 100
  song.patterns[source] = pattern
end

-- README.md:1120-1122: merged notes use the five-note selection, retain
-- seven-note degrees, select the lower pitch on a tie, and apply root then the
-- effective octave/transpose.  Two equal source degrees are still a merge:
-- that catches duplicate pitch-class contributors rather than only arithmetic
-- differences between sources.
function test_scale_merge_lydian_tie_with_duplicate_sources_root_and_transpose_reaches_midi()
  setup_scale_merge()
  local song = program.get_song_pattern(1)
  local channel = song.channels[1]
  install_scale(2, 8, 2, 2) -- Lydian D, then scale transpose +2
  program.get().default_scale = 2
  program.set_transpose(1) -- effective transpose is +3
  params:set("all_scales_lock_to_pentatonic", 1)
  params:set("merged_lock_to_pentatonic", 2)
  channel.trig_merge_mode = "all"
  channel.note_merge_mode = "average"
  set_source(song, 1, 1, 0)
  set_source(song, 2, 1, 0)
  channel.selected_patterns = {[1] = true, [2] = true}

  scale_merge_pattern.update_working_pattern(1, song)
  luaunit.assert_true(channel.working_pattern.merged_notes[1])
  scale_merge_step.handle(1, 1)

  -- Lydian's selection omits its tonic; it is tied between the preceding B
  -- and following D, so it chooses the pitch below.  The scale root (D) and
  -- combined +3 transpose then produce E/64.
  luaunit.assert_equals(midi_note_on_events, {{64, 100, 1, 1}})
end

-- README.md:1120-1122 gives a distinct selected-degree set for all ten named
-- scales.  This table uses real duplicate sources and the MIDI path, so a
-- future scale-table or merge-policy refactor cannot silently test only Major.
function test_scale_merge_named_scale_selections_reach_documented_midi_pitches()
  local cases = {
    {1, 3, 64}, -- Major: F ties E/G and selects E
    {2, 3, 64}, -- Harmonic Major: F ties E/G and selects E
    {3, 1, 63}, -- Minor: D snaps up to E-flat
    {4, 1, 63}, -- Harmonic Minor: D snaps up to E-flat
    {5, 1, 63}, -- Melodic Minor: D snaps up to E-flat
    {6, 2, 62}, -- Dorian: E-flat snaps down to D
    {7, 1, 60}, -- Phrygian: D-flat snaps down to C
    {8, 0, 59}, -- Lydian: documented C-to-B-below tie
    {9, 3, 65}, -- Mixolydian: F is selected (degree 4)
    {10, 0, 61} -- Locrian: C snaps up to D-flat
  }
  for _, case in ipairs(cases) do
    setup_scale_merge()
    local song = program.get_song_pattern(1)
    local channel = song.channels[1]
    install_scale(2, case[1], 0, 0)
    program.get().default_scale = 2
    params:set("all_scales_lock_to_pentatonic", 1)
    params:set("merged_lock_to_pentatonic", 2)
    channel.trig_merge_mode = "all"
    channel.note_merge_mode = "average"
    set_source(song, 1, 1, case[2])
    set_source(song, 2, 1, case[2])
    channel.selected_patterns = {[1] = true, [2] = true}
    scale_merge_pattern.update_working_pattern(1, song)
    luaunit.assert_true(channel.working_pattern.merged_notes[1], "scale " .. case[1])
    scale_merge_step.handle(1, 1)
    luaunit.assert_equals(midi_note_on_events, {{case[3], 100, 1, 1}}, "scale " .. case[1])
  end
end

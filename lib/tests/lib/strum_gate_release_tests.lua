-- README#chord-spread: spacing modifiers "do not change the selected note
-- length", so a strummed chord note sounds for the selected length from its own
-- onset, however fractional that onset is. Controlled lattice time, one pulse at
-- a time; the expected pulses are literal.
step = step or include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")
local divisions = include("mosaic/lib/clock/divisions")

include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
local m_clock = include("mosaic/lib/clock/m_clock")

local function division_index(value)
  for index, entry in ipairs(divisions.note_divisions) do
    if entry.value == value then return index end
  end
  error("no note division " .. value)
end

-- Plays one step of channel 1 with the given chord masks and trig params, and
-- returns note-on and note-off events as {pulse, note}.
local function strum_gates(args)
  program.init()
  globals.reset()
  params.reset()
  m_clock.init()
  m_clock:start()
  local song_pattern = 1
  program.set_selected_song_pattern(song_pattern)
  local test_pattern = program.initialise_default_pattern()
  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = args.length
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100
  local channel = program.get_channel(song_pattern, 1)
  channel.chord_one_mask = 2
  channel.chord_two_mask = 4
  program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  fn.add_to_set(channel.selected_patterns, 1)
  pattern.update_working_patterns()
  program.get().default_scale = 1
  local scale = program.get_scale(1)
  scale.root_note = 0
  scale.number = 1
  local slot = 0
  for id, value in pairs(args.params) do
    slot = slot + 1
    channel.trig_lock_params[slot] = {id = id, param_id = id .. "_1", off_value = 0}
    params:set(id .. "_1", value)
  end
  midi_note_on_events, midi_note_off_events = {}, {}
  step.handle(1, 1)
  local ons, offs = {}, {}
  for pulse = 0, args.pulses do
    if pulse > 0 then m_clock.get_clock_lattice():pulse() end
    while #midi_note_on_events > 0 do
      ons[#ons + 1] = {pulse, table.remove(midi_note_on_events, 1)[1]}
    end
    while #midi_note_off_events > 0 do
      offs[#offs + 1] = {pulse, table.remove(midi_note_off_events, 1)[1]}
    end
  end
  return ons, offs
end

-- One channel step is 24 pulses at the default lattice.
local STRUM_HALF_SPREAD_QUARTER = {chord_strum = division_index(1/2), chord_spread = division_index(1/4)}

local function with_pattern(strum_pattern)
  return {chord_strum = division_index(1/2), chord_spread = division_index(1/4), chord_strum_pattern = strum_pattern}
end

local function run(params)
  return strum_gates({length = 2, pulses = 200, params = params})
end

-- README#chord-spread: Length 2 steps, Strum 1/2 with Spread 1/4 puts the chord
-- notes at 0, 0.75 and 1.5 steps (pulses 0, 18, 36); each ends a full 2 steps
-- after its own onset: 2.0, 2.75 and 3.5 steps (pulses 48, 66, 84).
function test_strum_at_fractional_onsets_releases_a_full_length_after_each_onset()
  local ons, offs = run(STRUM_HALF_SPREAD_QUARTER)
  luaunit.assert_equals(ons, {{0, 60}, {18, 64}, {36, 67}})
  luaunit.assert_equals(offs, {{48, 60}, {66, 64}, {84, 67}})
end

-- Same rule when the root is the delayed voice (README#chord-strum pattern
-- orders) and the onsets are the odd ones, 0.75, 2.25 and 3.0 steps.
function test_strum_pattern_orders_release_a_full_length_after_each_fractional_onset()
  local ons, offs = run(with_pattern(2))
  luaunit.assert_equals(ons, {{36, 67}, {54, 64}, {72, 60}})
  luaunit.assert_equals(offs, {{84, 67}, {102, 64}, {120, 60}})
  ons, offs = run(with_pattern(4))
  luaunit.assert_equals(ons, {{18, 64}, {54, 67}, {72, 60}})
  luaunit.assert_equals(offs, {{66, 64}, {102, 67}, {120, 60}})
end

-- Whole-step onsets, a block chord and arpeggios keep the releases they had:
-- the arpeggio rule (each note lasts one division, README#chord-arpeggio) is
-- characterised here so the strum fix cannot move it.
function test_whole_step_strum_block_chord_and_arp_gates_are_unchanged()
  local ons, offs = run({chord_strum = division_index(1), chord_spread = division_index(1)})
  luaunit.assert_equals(ons, {{0, 60}, {48, 64}, {96, 67}})
  luaunit.assert_equals(offs, {{48, 60}, {96, 64}, {144, 67}})
  ons, offs = run({})
  luaunit.assert_equals(ons, {{0, 60}, {0, 64}, {0, 67}})
  luaunit.assert_equals(offs, {{48, 60}, {48, 64}, {48, 67}})
  ons, offs = run({chord_arp = division_index(1/2)})
  luaunit.assert_equals(ons, {{0, 60}, {12, 64}, {24, 67}})
  luaunit.assert_equals(offs, {{12, 60}, {24, 64}, {36, 67}})
  ons, offs = run({chord_arp = division_index(1/4), chord_strum = division_index(1/2),
    chord_spread = division_index(1/4)})
  luaunit.assert_equals(ons, {{0, 60}, {12, 64}, {24, 67}})
  luaunit.assert_equals(offs, {{6, 60}, {18, 64}, {30, 67}})
end

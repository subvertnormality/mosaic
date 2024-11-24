step = include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")

local m_clock = include("mosaic/lib/clock/m_clock")
local quantiser = include("mosaic/lib/quantiser")

-- Mocks
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/m_midi_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/channel_sequence_page_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_mock")

local function setup()
  program.init()
  globals.reset()
  params.reset()
end

local function clock_setup()
  m_clock.init()
  m_clock:start()
end

local function progress_clock_by_beats(b)
  for i = 1, (24 * b) do
    m_clock.get_clock_lattice():pulse()
  end
end

local function progress_clock_by_pulses(p)
  for i = 1, p do
    m_clock.get_clock_lattice():pulse()
  end
end

function test_channel_17_doesnt_fire_notes()

    local test_pattern
  
    setup()
    local song_pattern = 3
    program.set_selected_song_pattern(3)
    test_pattern = program.initialise_default_pattern()
    test_pattern2 = program.initialise_default_pattern()
  
    local steps = 6
  
    test_pattern.note_values[steps] = 0
    test_pattern.lengths[steps] = 1
    test_pattern.trig_values[steps] = 1
    test_pattern.velocity_values[steps] = 20
  
    program.get_song_pattern(song_pattern).patterns[1] = test_pattern
  
    fn.add_to_set(program.get_song_pattern(song_pattern).channels[17].selected_patterns, 1)
  
    pattern.update_working_patterns()
  
    -- Reset and set up the clock and MIDI event tracking
    clock_setup()
  
    -- Progress the clock according to the current steps being tested
    progress_clock_by_beats(steps)
  
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    -- Check there are no note on events
    luaunit.assertNil(note_on_event)
  
  end
  
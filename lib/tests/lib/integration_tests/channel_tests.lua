step_handler = include("mosaic/lib/step_handler")
pattern_controller = include("mosaic/lib/pattern_controller")

local clock_controller = include("mosaic/lib/clock_controller")
local quantiser = include("mosaic/lib/quantiser")

-- Mocks
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/midi_controller_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_ui_controller_mock")
include("mosaic/lib/tests/helpers/mocks/device_map_mock")
include("mosaic/lib/tests/helpers/mocks/norns_mock")
include("mosaic/lib/tests/helpers/mocks/channel_sequence_page_controller_mock")
include("mosaic/lib/tests/helpers/mocks/channel_edit_page_controller_mock")

local function setup()
  program.init()
  globals.reset()
  params.reset()
end

local function clock_setup()
  clock_controller.init()
  clock_controller:start()
end

local function progress_clock_by_beats(b)
  for i = 1, (24 * b) do
    clock_controller.get_clock_lattice():pulse()
  end
end

local function progress_clock_by_pulses(p)
  for i = 1, p do
    clock_controller.get_clock_lattice():pulse()
  end
end

function test_channel_17_doesnt_fire_notes()

    local test_pattern
  
    setup()
    local sequencer_pattern = 3
    program.set_selected_sequencer_pattern(3)
    test_pattern = program.initialise_default_pattern()
    test_pattern2 = program.initialise_default_pattern()
  
    local steps = 6
  
    test_pattern.note_values[steps] = 0
    test_pattern.lengths[steps] = 1
    test_pattern.trig_values[steps] = 1
    test_pattern.velocity_values[steps] = 20
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[17].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    -- Reset and set up the clock and MIDI event tracking
    clock_setup()
  
    -- Progress the clock according to the current steps being tested
    progress_clock_by_beats(steps)
  
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    -- Check there are no note on events
    luaunit.assertNil(note_on_event)
  
  end
  
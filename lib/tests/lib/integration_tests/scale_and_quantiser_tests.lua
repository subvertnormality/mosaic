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



function test_global_default_scale_setting_quantises_notes_properly()
    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    local test_pattern = program.initialise_default_pattern()
  
    local scale = quantiser.get_scales()[3]
  
    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        chord = 1,
        root_note = 1
      }
    )
  
    program.get().default_scale = 2
    program.get_channel(1).default_scale = 0
  
    test_pattern.note_values[2] = 2
    test_pattern.lengths[2] = 1
    test_pattern.trig_values[2] = 1
    test_pattern.velocity_values[2] = 100
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    clock_setup()
  
    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 64)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  
  end
  
  
  function test_channel_default_scale_setting_quantises_notes_properly()
    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    local test_pattern = program.initialise_default_pattern()
    local channel = 2
    local scale = quantiser.get_scales()[3]
  
    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        chord = 1,
        root_note = 1
      }
    )
  
    program.get().default_scale = 2
  
    program.get_channel(channel).default_scale = 1
  
    test_pattern.note_values[2] = 2
    test_pattern.lengths[2] = 1
    test_pattern.trig_values[2] = 1
    test_pattern.velocity_values[2] = 100
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    clock_setup()
  
    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 64)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  
  end
  
  
  function test_step_scale_trig_lock_quantises_notes_properly()
    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    local test_pattern = program.initialise_default_pattern()
    local channel = 2
    local step = 2
    local scale = quantiser.get_scales()[3]
  
    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        chord = 2,
        root_note = 1
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        chord = 4,
        root_note = 1
      }
    )
  
    program.get().default_scale = 1
    program.get_channel(channel).default_scale = 2
    program.get_channel(channel).step_scale_trig_lock_banks[step] = 3
  
    test_pattern.note_values[step] = 2
    test_pattern.lengths[step] = 1
    test_pattern.trig_values[step] = 1
    test_pattern.velocity_values[step] = 100
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    clock_setup()
  
    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 69)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  
  end
  
  function test_global_step_scale_quantises_notes_properly()
    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
  
    program.get().selected_channel = 17
  
    local test_pattern = program.initialise_default_pattern()
    local channel = 2
    local step = 4
    local scale = quantiser.get_scales()[3]
  
    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        chord = 2,
        root_note = 1
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        chord = 4,
        root_note = 1
      }
    )
  
    program.get().default_scale = 1
    program.get_channel(channel).default_scale = 2
    program.add_step_scale_trig_lock(step, 3)
  
    test_pattern.note_values[step] = 2
    test_pattern.lengths[step] = 1
    test_pattern.trig_values[step] = 1
    test_pattern.velocity_values[step] = 100
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    clock_setup()
  
    progress_clock_by_beats(4)
  
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 69)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  
  end


  function test_complex_step_scale_trig_lock_quantises_notes_properly_when_length_1_to_4()

    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    program.get().selected_channel = 17
    local test_pattern = program.initialise_default_pattern()
    local scale = quantiser.get_scales()[1]
  
    program.set_scale(
      1,
      {
        number = 1,
        scale = scale.scale,
        chord = 1,
        root_note = 0
      }
    )

    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        chord = 3,
        root_note = 0
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        chord = 5,
        root_note = 0
      }
    )
  
    program.get().default_scale = 1

    program.add_step_scale_trig_lock(1, 1)
    program.add_step_scale_trig_lock(17, 3)
    program.add_step_scale_trig_lock(33, 2)
    program.add_step_scale_trig_lock(49, 3)
    
    program.get_channel(1).step_scale_trig_lock_banks[3] = 2
  
    test_pattern.note_values[1] = 0
    test_pattern.lengths[1] = 1
    test_pattern.trig_values[1] = 1
    test_pattern.velocity_values[1] = 100
  
    test_pattern.note_values[3] = 0
    test_pattern.lengths[3] = 1
    test_pattern.trig_values[3] = 1
    test_pattern.velocity_values[3] = 100

    program.get_channel(1).start_trig[1] = 1
    program.get_channel(1).start_trig[2] = 4
  
    program.get_channel(1).end_trig[1] = 4
    program.get_channel(1).end_trig[2] = 4

    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()
  
    local correct_note_values = {
      60, 0, 64, 0, 60, 0, 64, 0, 
      60, 0, 64, 0, 60, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0, 
      64, 0, 64, 0, 64, 0, 64, 0, 
      64, 0, 64, 0, 64, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0 
    }

    clock_setup() -- Step 1

    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], correct_note_values[1])
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
    
    for i = 3, 200 do

      if i % 2 ~= 0 then
        progress_clock_by_beats(2)

        local note_on_event = table.remove(midi_note_on_events, 1)
    
        luaunit.assert_equals(note_on_event[1], correct_note_values[i % 64])
        luaunit.assert_equals(note_on_event[2], 100)
        luaunit.assert_equals(note_on_event[3], 1)
      end


    end

  end



  function test_complex_step_scale_trig_lock_quantises_notes_properly_when_length_17_to_20()

    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    program.get().selected_channel = 17
    local test_pattern = program.initialise_default_pattern()
    local scale = quantiser.get_scales()[1]
  
    program.set_scale(
      1,
      {
        number = 1,
        scale = scale.scale,
        chord = 1,
        root_note = 0
      }
    )

    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        chord = 3,
        root_note = 0
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        chord = 5,
        root_note = 0
      }
    )
  
    program.get().default_scale = 1

    program.add_step_scale_trig_lock(1, 1)
    program.add_step_scale_trig_lock(17, 3)
    program.add_step_scale_trig_lock(33, 2)
    program.add_step_scale_trig_lock(49, 3)
    
    program.get_channel(1).step_scale_trig_lock_banks[19] = 2
  
    test_pattern.note_values[17] = 0
    test_pattern.lengths[17] = 1
    test_pattern.trig_values[17] = 1
    test_pattern.velocity_values[17] = 100
  
    test_pattern.note_values[19] = 0
    test_pattern.lengths[19] = 1
    test_pattern.trig_values[19] = 1
    test_pattern.velocity_values[19] = 100

    program.get_channel(1).start_trig[1] = 1
    program.get_channel(1).start_trig[2] = 5
  
    program.get_channel(1).end_trig[1] = 4
    program.get_channel(1).end_trig[2] = 5

    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()

    local correct_note_values = {
      60, 0, 64, 0, 60, 0, 64, 0, 
      60, 0, 64, 0, 60, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0, 
      64, 0, 64, 0, 64, 0, 64, 0, 
      64, 0, 64, 0, 64, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0 
    }

    clock_setup() -- Step 1

    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], correct_note_values[1])
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
    
    for i = 3, 200 do

      if i % 2 ~= 0 then
        progress_clock_by_beats(2)

        local note_on_event = table.remove(midi_note_on_events, 1)
    
        luaunit.assert_equals(note_on_event[1], correct_note_values[i % 64])
        luaunit.assert_equals(note_on_event[2], 100)
        luaunit.assert_equals(note_on_event[3], 1)
      end


    end
  

  end


  

  function test_complex_step_scale_trig_lock_quantises_notes_properly_when_length_1_to_4_different_step()

    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    program.get().selected_channel = 17
    local test_pattern = program.initialise_default_pattern()
    local scale = quantiser.get_scales()[1]
  
    program.set_scale(
      1,
      {
        number = 1,
        scale = scale.scale,
        chord = 1,
        root_note = 0
      }
    )

    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        chord = 3,
        root_note = 0
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        chord = 5,
        root_note = 0
      }
    )
  
    program.get().default_scale = 1

    program.add_step_scale_trig_lock(1, 1)
    program.add_step_scale_trig_lock(17, 3)
    program.add_step_scale_trig_lock(33, 2)
    program.add_step_scale_trig_lock(49, 3)
    
    program.get_channel(1).step_scale_trig_lock_banks[18] = 2
  
    test_pattern.note_values[17] = 0
    test_pattern.lengths[17] = 1
    test_pattern.trig_values[17] = 1
    test_pattern.velocity_values[17] = 100
  
    test_pattern.note_values[19] = 0
    test_pattern.lengths[19] = 1
    test_pattern.trig_values[19] = 1
    test_pattern.velocity_values[19] = 100

    program.get_channel(1).start_trig[1] = 1
    program.get_channel(1).start_trig[2] = 5
  
    program.get_channel(1).end_trig[1] = 4
    program.get_channel(1).end_trig[2] = 5

    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
    pattern_controller.update_working_patterns()

    local correct_note_values = {
      60, 0, 64, 0, 60, 0, 64, 0, 
      60, 0, 64, 0, 60, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0, 
      64, 0, 64, 0, 64, 0, 64, 0, 
      64, 0, 64, 0, 64, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0, 
      67, 0, 64, 0, 67, 0, 64, 0 
    }

    clock_setup() -- Step 1

    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], correct_note_values[1])
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
    
    for i = 3, 200 do

      if i % 2 ~= 0 then
        progress_clock_by_beats(2)

        local note_on_event = table.remove(midi_note_on_events, 1)

        luaunit.assert_equals(note_on_event[1], correct_note_values[i % 64])
        luaunit.assert_equals(note_on_event[2], 100)
        luaunit.assert_equals(note_on_event[3], 1)
      end


    end
  

  end

step = include("mosaic/lib/step")
pattern = include("mosaic/lib/pattern")

local clock_controller = include("mosaic/lib/clock/clock_controller")
local quantiser = include("mosaic/lib/quantiser")

-- Mocks
include("mosaic/lib/tests/helpers/mocks/sinfonion_mock")
include("mosaic/lib/tests/helpers/mocks/params_mock")
include("mosaic/lib/tests/helpers/mocks/mosaic_midi_mock")
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
        pentatonic_scale = scale.pentatonic_scale,
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
  
    pattern.update_working_patterns()
  
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
        pentatonic_scale = scale.pentatonic_scale,
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
  
    pattern.update_working_patterns()
  
    clock_setup()
  
    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 64)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  
  end
  
  
  function test_channel_default_scale_setting_quantises_notes_properly_when_global_pentatonic_is_set_c_major()
    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    local test_pattern = program.initialise_default_pattern()
    local channel = 2
    local scale = quantiser.get_scales()[1]

    params:set("all_scales_lock_to_pentatonic", 2)
  
    program.set_scale(
      2,
      {
        number = 1,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
        chord = 1,
        root_note = 0
      }
    )
  
    program.get().default_scale = 2
  
  
    test_pattern.note_values[1] = 0
    test_pattern.lengths[1] = 1
    test_pattern.trig_values[1] = 1
    test_pattern.velocity_values[1] = 100

    test_pattern.note_values[2] = 1
    test_pattern.lengths[2] = 1
    test_pattern.trig_values[2] = 1
    test_pattern.velocity_values[2] = 100

    test_pattern.note_values[3] = 2
    test_pattern.lengths[3] = 1
    test_pattern.trig_values[3] = 1
    test_pattern.velocity_values[3] = 100

    test_pattern.note_values[4] = 3
    test_pattern.lengths[4] = 1
    test_pattern.trig_values[4] = 1
    test_pattern.velocity_values[4] = 100

    test_pattern.note_values[5] = 4
    test_pattern.lengths[5] = 1
    test_pattern.trig_values[5] = 1
    test_pattern.velocity_values[5] = 100

    test_pattern.note_values[6] = 5
    test_pattern.lengths[6] = 1
    test_pattern.trig_values[6] = 1
    test_pattern.velocity_values[6] = 100

    test_pattern.note_values[7] = 6
    test_pattern.lengths[7] = 1
    test_pattern.trig_values[7] = 1
    test_pattern.velocity_values[7] = 100

    test_pattern.note_values[8] = 7
    test_pattern.lengths[8] = 1
    test_pattern.trig_values[8] = 1
    test_pattern.velocity_values[8] = 100
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)
  
    pattern.update_working_patterns()
  
    clock_setup()
  
    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 60)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 62)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 64)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 64) -- snap to pentatonic scale
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 67)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 69)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 72)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 72) -- snap to pentatonic scale
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  end


  function test_channel_default_scale_setting_quantises_notes_properly_when_global_pentatonic_is_set_d_major()
    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    local test_pattern = program.initialise_default_pattern()
    local channel = 2
    local scale = quantiser.get_scales()[1]

    params:set("all_scales_lock_to_pentatonic", 2)

  
    program.set_scale(
      2,
      {
        number = 1,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
        chord = 1,
        root_note = 2
      }
    )
  
    program.get().default_scale = 2
  
  
    test_pattern.note_values[1] = 0
    test_pattern.lengths[1] = 1
    test_pattern.trig_values[1] = 1
    test_pattern.velocity_values[1] = 100

    test_pattern.note_values[2] = 1
    test_pattern.lengths[2] = 1
    test_pattern.trig_values[2] = 1
    test_pattern.velocity_values[2] = 100

    test_pattern.note_values[3] = 2
    test_pattern.lengths[3] = 1
    test_pattern.trig_values[3] = 1
    test_pattern.velocity_values[3] = 100

    test_pattern.note_values[4] = 3
    test_pattern.lengths[4] = 1
    test_pattern.trig_values[4] = 1
    test_pattern.velocity_values[4] = 100

    test_pattern.note_values[5] = 4
    test_pattern.lengths[5] = 1
    test_pattern.trig_values[5] = 1
    test_pattern.velocity_values[5] = 100

    test_pattern.note_values[6] = 5
    test_pattern.lengths[6] = 1
    test_pattern.trig_values[6] = 1
    test_pattern.velocity_values[6] = 100

    test_pattern.note_values[7] = 6
    test_pattern.lengths[7] = 1
    test_pattern.trig_values[7] = 1
    test_pattern.velocity_values[7] = 100

    test_pattern.note_values[8] = 7
    test_pattern.lengths[8] = 1
    test_pattern.trig_values[8] = 1
    test_pattern.velocity_values[8] = 100

    test_pattern.note_values[9] = 8
    test_pattern.lengths[9] = 1
    test_pattern.trig_values[9] = 1
    test_pattern.velocity_values[9] = 100
  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)
  
    pattern.update_working_patterns()
  
    clock_setup()
  
    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 62)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 64)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 66)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 66) -- snap to pentatonic scale
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 69)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 71)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 74) -- snap to pentatonic scale
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 74) 
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)


    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 76)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)
  end


  function test_channel_default_scale_setting_quantises_notes_properly_when_pentatonic_merged_notes()
    setup()
    local sequencer_pattern = 1
    program.set_selected_sequencer_pattern(1)
    local test_pattern = program.initialise_default_pattern()
    local test_pattern_2 = program.initialise_default_pattern()
    local channel = 11
    local scale = quantiser.get_scales()[1]

    params:set("all_scales_lock_to_pentatonic", 1)
    params:set("merged_lock_to_pentatonic", 2)

    program.get_channel(channel).trig_merge_mode = "all"
    program.get_channel(channel).note_merge_mode = "down"
  
    program.set_scale(
      2,
      {
        number = 1,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
        chord = 1,
        root_note = 2
      }
    )
  
    program.get().default_scale = 2
  
  
    test_pattern.note_values[1] = 0
    test_pattern.lengths[1] = 1
    test_pattern.trig_values[1] = 1
    test_pattern.velocity_values[1] = 100

    test_pattern.note_values[2] = 1
    test_pattern.lengths[2] = 1
    test_pattern.trig_values[2] = 1
    test_pattern.velocity_values[2] = 100

    test_pattern.note_values[3] = 2
    test_pattern.lengths[3] = 1
    test_pattern.trig_values[3] = 1
    test_pattern.velocity_values[3] = 100

    test_pattern.note_values[4] = 3
    test_pattern.lengths[4] = 1
    test_pattern.trig_values[4] = 1
    test_pattern.velocity_values[4] = 100


    test_pattern_2.note_values[1] = 2
    test_pattern_2.lengths[1] = 1
    test_pattern_2.trig_values[1] = 1
    test_pattern_2.velocity_values[1] = 100

    test_pattern_2.note_values[2] = 3
    test_pattern_2.lengths[2] = 1
    test_pattern_2.trig_values[2] = 1
    test_pattern_2.velocity_values[2] = 100

    test_pattern_2.note_values[3] = 4
    test_pattern_2.lengths[3] = 1
    test_pattern_2.trig_values[3] = 1
    test_pattern_2.velocity_values[3] = 100

    test_pattern_2.note_values[4] = 5
    test_pattern_2.lengths[4] = 1
    test_pattern_2.trig_values[4] = 1
    test_pattern_2.velocity_values[4] = 100

  
    program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
    program.get_sequencer_pattern(sequencer_pattern).patterns[2] = test_pattern_2
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)
    fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 2)


    pattern.update_working_patterns()
  
    clock_setup()
  
    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 62)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 62)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 64)
    luaunit.assert_equals(note_on_event[2], 100)
    luaunit.assert_equals(note_on_event[3], 1)

    progress_clock_by_beats(1)
    
    local note_on_event = table.remove(midi_note_on_events, 1)
  
    luaunit.assert_equals(note_on_event[1], 66)
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
        pentatonic_scale = scale.pentatonic_scale,
        chord = 2,
        root_note = 1
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
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
  
    pattern.update_working_patterns()
  
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
        pentatonic_scale = scale.pentatonic_scale,
        chord = 2,
        root_note = 1
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
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
  
    pattern.update_working_patterns()
  
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
        pentatonic_scale = scale.pentatonic_scale,
        chord = 1,
        root_note = 0
      }
    )

    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
        chord = 3,
        root_note = 0
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
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
  
    pattern.update_working_patterns()
  
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
        pentatonic_scale = scale.pentatonic_scale,
        chord = 1,
        root_note = 0
      }
    )

    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
        chord = 3,
        root_note = 0
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
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
  
    pattern.update_working_patterns()

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
        pentatonic_scale = scale.pentatonic_scale,
        chord = 1,
        root_note = 0
      }
    )

    program.set_scale(
      2,
      {
        number = 2,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
        chord = 3,
        root_note = 0
      }
    )
  
    program.set_scale(
      3,
      {
        number = 3,
        scale = scale.scale,
        pentatonic_scale = scale.pentatonic_scale,
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
  
    pattern.update_working_patterns()

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
      pentatonic_scale = scale.pentatonic_scale,
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

  pattern.update_working_patterns()

  clock_setup()

  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end


function test_chord_degree_rotation_drops_the_octave_of_last_notes_in_scale_in_accordence_to_rotation_parameter_of_one()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 2,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0, 
      chord_degree_rotation = 0
    }
  )

  program.set_chord_degree_rotation_for_scale(2, 1)

  program.get().default_scale = 2

  test_pattern.note_values[1] = 6
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)


  pattern.update_working_patterns()

  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 59)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

end

function test_chord_degree_rotation_with_negative_octave_mod()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 2,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0, 
      chord_degree_rotation = 0
    }
  )

  program.set_chord_degree_rotation_for_scale(2, 1)
  program.get_sequencer_pattern(sequencer_pattern).channels[channel].octave = -1

  program.get().default_scale = 2

  test_pattern.note_values[1] = 6
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)


  pattern.update_working_patterns()

  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 47)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)  
  

end



function test_chord_degree_rotation_drops_the_octave_of_last_notes_in_scale_in_accordence_to_rotation_parameter_of_six()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 2,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0, 
      chord_degree_rotation = 0
    }
  )

  program.get().default_scale = 2

  test_pattern.note_values[1] = 6
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  test_pattern.note_values[2] = 5
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  test_pattern.note_values[3] = 4
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 100

  test_pattern.note_values[4] = 3
  test_pattern.lengths[4] = 1
  test_pattern.trig_values[4] = 1
  test_pattern.velocity_values[4] = 100

  test_pattern.note_values[5] = 2
  test_pattern.lengths[5] = 1
  test_pattern.trig_values[5] = 1
  test_pattern.velocity_values[5] = 100

  test_pattern.note_values[6] = 1
  test_pattern.lengths[6] = 1
  test_pattern.trig_values[6] = 1
  test_pattern.velocity_values[6] = 100

  test_pattern.note_values[7] = 0
  test_pattern.lengths[7] = 1
  test_pattern.trig_values[7] = 1
  test_pattern.velocity_values[7] = 100

  test_pattern.note_values[8] = 7
  test_pattern.lengths[8] = 1
  test_pattern.trig_values[8] = 1
  test_pattern.velocity_values[8] = 100

  test_pattern.note_values[9] = 8
  test_pattern.lengths[9] = 1
  test_pattern.trig_values[9] = 1
  test_pattern.velocity_values[9] = 100


  program.set_chord_degree_rotation_for_scale(2, 6)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)


  pattern.update_working_patterns()

  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 59)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 57)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 55)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 53)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 52)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 50)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 72)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end




function test_chord_degree_rotation_drops_the_octave_of_last_notes_in_scale_in_accordence_to_rotation_parameter_of_two()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 2,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0, 
      chord_degree_rotation = 0
    }
  )

  program.get().default_scale = 2

  test_pattern.note_values[1] = 6
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  test_pattern.note_values[2] = 5
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  test_pattern.note_values[3] = 4
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 100

  test_pattern.note_values[4] = 3
  test_pattern.lengths[4] = 1
  test_pattern.trig_values[4] = 1
  test_pattern.velocity_values[4] = 100

  test_pattern.note_values[5] = 2
  test_pattern.lengths[5] = 1
  test_pattern.trig_values[5] = 1
  test_pattern.velocity_values[5] = 100

  test_pattern.note_values[6] = 1
  test_pattern.lengths[6] = 1
  test_pattern.trig_values[6] = 1
  test_pattern.velocity_values[6] = 100

  test_pattern.note_values[7] = 0
  test_pattern.lengths[7] = 1
  test_pattern.trig_values[7] = 1
  test_pattern.velocity_values[7] = 100

  test_pattern.note_values[8] = 7
  test_pattern.lengths[8] = 1
  test_pattern.trig_values[8] = 1
  test_pattern.velocity_values[8] = 100

  test_pattern.note_values[9] = 8
  test_pattern.lengths[9] = 1
  test_pattern.trig_values[9] = 1
  test_pattern.velocity_values[9] = 100


  program.set_chord_degree_rotation_for_scale(2, 2)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)


  pattern.update_working_patterns()

  clock_setup()
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 59)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 57)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 67)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 65)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 60)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 72)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)

  progress_clock_by_beats(1)

  local note_on_event = table.remove(midi_note_on_events, 1)

  luaunit.assert_equals(note_on_event[1], 74)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end


function test_global_transpose_applies_to_notes()

  setup()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1] -- Major scale

  -- Set up a basic scale
  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.get().default_scale = 2
  program.set_transpose(2) -- Transpose up 2 semitones

  -- Set up a simple note
  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  -- C (60) + 2 semitones = D (62)
  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end


function test_step_transpose_overrides_global_transpose()

  setup()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.get().default_scale = 2
  program.set_transpose(2) -- Global transpose +2
  
  -- Add a step transpose that should override the global transpose
  local current_step = 1
  program.add_step_transpose_trig_lock(current_step, 4) -- Step transpose +4

  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  -- C (60) + 4 semitones = E (64)
  luaunit.assert_equals(note_on_event[1], 64)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end

function test_negative_transpose_values()

  setup()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.get().default_scale = 2
  program.set_transpose(-3) -- Transpose down 3 semitones

  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  -- C (60) - 3 semitones = A (57)
  luaunit.assert_equals(note_on_event[1], 57)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end

function test_transpose_resets_at_pattern_start()

  setup()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.get().default_scale = 2
  program.set_transpose(0) -- No global transpose
  
  -- Set step transpose
  program.add_step_transpose_trig_lock(2, 2)

  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  test_pattern.note_values[2] = 0  -- C
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  
  -- First pattern
  progress_clock_by_beats(1)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60) -- C + 2

  progress_clock_by_beats(1)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62) -- C + 2

  -- Play to reset
  progress_clock_by_beats(62)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 60) -- Should be back to C

  progress_clock_by_beats(1)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 62) -- C + 2
end


function test_transpose_with_octave_modification()

  setup()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.get().default_scale = 2
  program.set_transpose(2) -- Transpose up 2 semitones
  program.get_channel(channel).octave = 1 -- Up one octave

  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  -- C (60) + 2 semitones + 12 semitones = D5 (74)
  luaunit.assert_equals(note_on_event[1], 74)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end



function test_scale_transpose_applies_to_notes()

  setup()

  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1] -- Major scale

  -- Set up a basic scale
  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.get().default_scale = 2
  program.set_scale_transpose(2, 2) -- Transpose up 2 semitones on scale 2

  -- Set up a simple note
  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  -- C (60) + 2 semitones = D (62)
  luaunit.assert_equals(note_on_event[1], 62)
  luaunit.assert_equals(note_on_event[2], 100)
  luaunit.assert_equals(note_on_event[3], 1)
end


function test_transpose_hierarchy_step_transpose_adds_to_scale_transpose()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  -- Set up scale with its own transpose
  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0,
      transpose = 3 -- Scale transpose +3
    }
  )

  program.get().default_scale = 2
  program.set_transpose(2) -- Global transpose +2
  
  -- Add step transpose that should take precedence over global
  program.add_step_transpose_trig_lock(1, 4) -- Step transpose +4

  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  -- Should use step transpose (4) added to scale transpose (3) not global transpose (2)
  luaunit.assert_equals(note_on_event[1], 67) -- C (60) + 7 = E (67)
end

function test_transpose_hierarchy_scale_transpose_adds_to_global()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0,
      transpose = 3 -- Scale transpose +3
    }
  )

  program.get().default_scale = 2
  program.set_transpose(2) -- Global transpose +2 (should be ignored)

  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  -- Should add scale transpose (3) to global transpose (2)
  luaunit.assert_equals(note_on_event[1], 65)
end

function test_transpose_hierarchy_should_fall_back_to_global_on_new_scale_step()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.get().default_scale = 2
  program.set_transpose(1) -- Global transpose +1
  
  -- Set up two notes, first with step transpose
  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  test_pattern.note_values[2] = 0  -- C
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  test_pattern.note_values[3] = 0  -- C
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 100

  program.add_step_transpose_trig_lock(1, 4) -- Step transpose +4 for first step
  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(3, 1) -- New scale for second step

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  
  -- First step - should use step transpose
  progress_clock_by_beats(1)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64) -- C (60) + 4 = E (64)
  
  -- Second step - should use step transpose
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64)

  -- Third step - should use global
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 61) -- Should use global
end

function test_transpose_hierarchy_uses_scale_transpose()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  -- Set up scale with transpose
  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0,
      transpose = 3
    }
  )

  program.get().default_scale = 2
  program.set_transpose(1) -- Global transpose +1

  -- Set pattern length to 3 steps
  local channel_17 = program.get_channel(17)
  channel_17.end_trig[1] = 3
  channel_17.end_trig[2] = 4

  local channel_2 = program.get_channel(2)
  channel_2.end_trig[1] = 3
  channel_2.end_trig[2] = 4
  
  -- First note without step transpose
  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  -- Second note with step transpose
  test_pattern.note_values[2] = 0  -- C
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100
  program.get().selected_channel = 17
  program.add_step_transpose_trig_lock(2, 4) -- Step transpose +4

  -- Third note without step transpose
  test_pattern.note_values[3] = 0  -- C
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  
  -- First pattern
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64) -- No step transpose, uses scale transpose + global (3)

  progress_clock_by_beats(1)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 67) -- Step transpose (4) added to scale transpose (3)
  
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 67) -- Step transpose (4) added to scale transpose (3)
  
  progress_clock_by_beats(1)
  -- Next pattern - persistent transpose should be reset
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64) -- No step transpose, uses scale transpose + global
  
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 67) -- Step transpose (4) added to scale transpose (3)
  
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 67) -- Step transpose (4) added to scale transpose (3)
end

function test_transpose_hierarchy_fallback_to_global()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  -- Set up scale without transpose
  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.get().default_scale = 2
  program.set_transpose(2) -- Global transpose +2

  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  progress_clock_by_beats(1)
  
  local note_on_event = table.remove(midi_note_on_events, 1)

  -- Should fall back to global transpose since no other transpose is set
  luaunit.assert_equals(note_on_event[1], 62) -- C (60) + 2 = D (62)
end

function test_multiple_scale_transpose_changes()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.get().selected_channel = channel

  -- Set up two scales with different transposes
  program.set_scale_transpose(2, 3)
  program.set_scale_transpose(3, 5)

  program.get().default_scale = 2
  program.set_transpose(1) -- Global transpose +1

  -- Set up two notes with different scales
  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  test_pattern.note_values[2] = 0  -- C
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  program.get().selected_channel = 17
  program.add_step_scale_trig_lock(2, 3)

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  
  -- First note - uses scale 2's transpose + global
  progress_clock_by_beats(1)
  local note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 64) -- C (60) + 3 + 1
  
  -- Second note - uses scale 3's transpose
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  luaunit.assert_equals(note_on_event[1], 66) -- C (60) + 5 + 1
end


function test_transpose_persistence_across_steps_until_next_scale_trig_lock()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(1)
  local test_pattern = program.initialise_default_pattern()
  local channel = 2
  local scale = quantiser.get_scales()[1]

  program.set_scale(
    2,
    {
      number = 1,
      scale = scale.scale,
      pentatonic_scale = scale.pentatonic_scale,
      chord = 1,
      root_note = 0
    }
  )

  program.get().default_scale = 2
  
  -- Set step transpose for first step
  program.add_step_transpose_trig_lock(1, 2)

  -- Set step transpose for fourth step
  program.add_step_transpose_trig_lock(4, 0)


  -- Set up multiple notes
  test_pattern.note_values[1] = 0  -- C
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  test_pattern.note_values[2] = 0  -- C
  test_pattern.lengths[2] = 1
  test_pattern.trig_values[2] = 1
  test_pattern.velocity_values[2] = 100

  test_pattern.note_values[3] = 0  -- C
  test_pattern.lengths[3] = 1
  test_pattern.trig_values[3] = 1
  test_pattern.velocity_values[3] = 100

  test_pattern.note_values[4] = 0  -- D
  test_pattern.lengths[4] = 1
  test_pattern.trig_values[4] = 1
  test_pattern.velocity_values[4] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)

  pattern.update_working_patterns()
  clock_setup()
  
  -- First step
  progress_clock_by_beats(1)
  local note_on_event = table.remove(midi_note_on_events, 1)
  -- C (60) + 2 semitones = D (62)
  luaunit.assert_equals(note_on_event[1], 62)
  
  -- Second step should maintain the transpose from step 1
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  -- D (62) + 2 semitones = E (64)
  luaunit.assert_equals(note_on_event[1], 62)

  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  -- D (62) + 2 semitones = E (64)
  luaunit.assert_equals(note_on_event[1], 62)

  -- should not have the step transpose
  progress_clock_by_beats(1)
  note_on_event = table.remove(midi_note_on_events, 1)
  -- D (62) + 2 semitones = E (64)
  luaunit.assert_equals(note_on_event[1], 60)
end
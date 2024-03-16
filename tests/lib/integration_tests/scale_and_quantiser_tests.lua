-- step_handler = include("mosaic/lib/step_handler")
-- pattern_controller = include("mosaic/lib/pattern_controller")

-- local clock_controller = include("mosaic/lib/clock_controller")
-- local quantiser = include("mosaic/lib/quantiser")

-- -- Mocks
-- include("mosaic/tests/helpers/mocks/sinfonion_mock")
-- include("mosaic/tests/helpers/mocks/params_mock")
-- include("mosaic/tests/helpers/mocks/midi_controller_mock")
-- include("mosaic/tests/helpers/mocks/channel_edit_page_ui_controller_mock")
-- include("mosaic/tests/helpers/mocks/device_map_mock")
-- include("mosaic/tests/helpers/mocks/norns_mock")
-- include("mosaic/tests/helpers/mocks/channel_sequence_page_controller_mock")
-- include("mosaic/tests/helpers/mocks/channel_edit_page_controller_mock")

-- local function setup()
--   program.init()
--   globals.reset()
--   params.reset()
-- end

-- local function clock_setup()
--   clock_controller.init()
--   clock_controller:start()
-- end

-- local function progress_clock_by_beats(b)
--   for i = 1, (24 * b) do
--     clock_controller.get_clock_lattice():pulse()
--   end
-- end

-- local function progress_clock_by_pulses(p)
--   for i = 1, p do
--     clock_controller.get_clock_lattice():pulse()
--   end
-- end



-- function test_global_default_scale_setting_quantises_notes_properly()
--     setup()
--     local sequencer_pattern = 1
--     program.set_selected_sequencer_pattern(1)
--     local test_pattern = program.initialise_default_pattern()
  
--     local scale = quantiser.get_scales()[3]
  
--     program.set_scale(
--       2,
--       {
--         number = 2,
--         scale = scale.scale,
--         chord = 1,
--         root_note = 1
--       }
--     )
  
--     program.get().default_scale = 2
--     program.get_channel(1).default_scale = 0
  
--     test_pattern.note_values[2] = 2
--     test_pattern.lengths[2] = 1
--     test_pattern.trig_values[2] = 1
--     test_pattern.velocity_values[2] = 100
  
--     program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
--     fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  
--     pattern_controller.update_working_patterns()
  
--     clock_setup()
  
--     progress_clock_by_beats(1)
    
--     local note_on_event = table.remove(midi_note_on_events, 1)
  
--     luaunit.assert_equals(note_on_event[1], 64)
--     luaunit.assert_equals(note_on_event[2], 100)
--     luaunit.assert_equals(note_on_event[3], 1)
  
--   end
  
  
--   function test_channel_default_scale_setting_quantises_notes_properly()
--     setup()
--     local sequencer_pattern = 1
--     program.set_selected_sequencer_pattern(1)
--     local test_pattern = program.initialise_default_pattern()
--     local channel = 2
--     local scale = quantiser.get_scales()[3]
  
--     program.set_scale(
--       2,
--       {
--         number = 2,
--         scale = scale.scale,
--         chord = 1,
--         root_note = 1
--       }
--     )
  
--     program.get().default_scale = 2
  
--     program.get_channel(channel).default_scale = 1
  
--     test_pattern.note_values[2] = 2
--     test_pattern.lengths[2] = 1
--     test_pattern.trig_values[2] = 1
--     test_pattern.velocity_values[2] = 100
  
--     program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
--     fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)
  
--     pattern_controller.update_working_patterns()
  
--     clock_setup()
  
--     progress_clock_by_beats(1)
    
--     local note_on_event = table.remove(midi_note_on_events, 1)
  
--     luaunit.assert_equals(note_on_event[1], 64)
--     luaunit.assert_equals(note_on_event[2], 100)
--     luaunit.assert_equals(note_on_event[3], 1)
  
--   end
  
  
--   function test_step_scale_trig_lock_quantises_notes_properly()
--     setup()
--     local sequencer_pattern = 1
--     program.set_selected_sequencer_pattern(1)
--     local test_pattern = program.initialise_default_pattern()
--     local channel = 2
--     local step = 2
--     local scale = quantiser.get_scales()[3]
  
--     program.set_scale(
--       2,
--       {
--         number = 2,
--         scale = scale.scale,
--         chord = 2,
--         root_note = 1
--       }
--     )
  
--     program.set_scale(
--       3,
--       {
--         number = 3,
--         scale = scale.scale,
--         chord = 4,
--         root_note = 1
--       }
--     )
  
--     program.get().default_scale = 1
--     program.get_channel(channel).default_scale = 2
--     program.get_channel(channel).step_scale_trig_lock_banks[step] = 3
  
--     test_pattern.note_values[step] = 2
--     test_pattern.lengths[step] = 1
--     test_pattern.trig_values[step] = 1
--     test_pattern.velocity_values[step] = 100
  
--     program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
--     fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)
  
--     pattern_controller.update_working_patterns()
  
--     clock_setup()
  
--     progress_clock_by_beats(1)
    
--     local note_on_event = table.remove(midi_note_on_events, 1)
  
--     luaunit.assert_equals(note_on_event[1], 69)
--     luaunit.assert_equals(note_on_event[2], 100)
--     luaunit.assert_equals(note_on_event[3], 1)
  
--   end
  
--   function test_global_step_scale_quantises_notes_properly()
--     setup()
--     local sequencer_pattern = 1
--     program.set_selected_sequencer_pattern(1)
  
--     program.get().selected_channel = 17
  
--     local test_pattern = program.initialise_default_pattern()
--     local channel = 2
--     local step = 4
--     local scale = quantiser.get_scales()[3]
  
--     program.set_scale(
--       2,
--       {
--         number = 2,
--         scale = scale.scale,
--         chord = 2,
--         root_note = 1
--       }
--     )
  
--     program.set_scale(
--       3,
--       {
--         number = 3,
--         scale = scale.scale,
--         chord = 4,
--         root_note = 1
--       }
--     )
  
--     program.get().default_scale = 1
--     program.get_channel(channel).default_scale = 2
--     program.add_step_scale_trig_lock(step, 3)
  
--     test_pattern.note_values[step] = 2
--     test_pattern.lengths[step] = 1
--     test_pattern.trig_values[step] = 1
--     test_pattern.velocity_values[step] = 100
  
--     program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
--     fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[channel].selected_patterns, 1)
  
--     pattern_controller.update_working_patterns()
  
--     clock_setup()
  
--     progress_clock_by_beats(4)
  
--     local note_on_event = table.remove(midi_note_on_events, 1)
  
--     luaunit.assert_equals(note_on_event[1], 69)
--     luaunit.assert_equals(note_on_event[2], 100)
--     luaunit.assert_equals(note_on_event[3], 1)
  
--   end
  
  
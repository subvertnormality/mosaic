-- local step_handler = include("mosaic/lib/step_handler")
-- pattern_controller = include("mosaic/lib/pattern_controller")

-- include("mosaic/tests/helpers/mocks/device_map_mock")
-- include("mosaic/tests/helpers/mocks/channel_edit_page_ui_controller_mock")
-- include("mosaic/tests/helpers/mocks/midi_controller_mock")
-- include("mosaic/tests/helpers/mocks/params_mock")

-- local function setup()
--   program.init()
--   globals.reset()
-- end

-- function test_steps_process_note_on_events()
--   setup()
--   local sequencer_pattern = 1
--   program.set_selected_sequencer_pattern(sequencer_pattern)

--   local test_pattern = program.initialise_default_pattern()

--   test_pattern.note_values[1] = 0
--   test_pattern.lengths[1] = 1
--   test_pattern.trig_values[1] = 1
--   test_pattern.velocity_values[1] = 100

--   program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
--   fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
--   pattern_controller.update_working_patterns()

--   step_handler.handle(1, 1)

--   local note_on_event = table.remove(midi_note_on_events, 1)

--   luaunit.assert_equals(note_on_event[1], 60)
--   luaunit.assert_equals(note_on_event[2], 100)
--   luaunit.assert_equals(note_on_event[3], 1)
-- end

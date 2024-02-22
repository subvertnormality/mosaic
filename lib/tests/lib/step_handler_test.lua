local step_handler = include("mosaic/lib/step_handler")
pattern_controller = include("mosaic/lib/pattern_controller")

device_map = {}
device_map.get_device = function () 
  return {}
end

channel_edit_page_ui_controller = {}
channel_edit_page_ui_controller.refresh_trig_locks = function () end

local midi_note_on_events = {}

midi_controller = {}

function midi_controller:note_on(note, velocity, channel, device)
  table.insert(midi_note_on_events, {note, velocity, channel, device})
end

params = {}
params.set = function () end
params.get = function () end
params.lookup_param = function () end

local function setup()
  program.init()
  midi_note_on_events = {}
end

function test_steps_process_notes()
  setup()
  local sequencer_pattern = 1
  program.set_selected_sequencer_pattern(sequencer_pattern)

  local test_pattern = program.initialise_default_pattern()

  test_pattern.note_values[1] = 0
  test_pattern.lengths[1] = 1
  test_pattern.trig_values[1] = 1
  test_pattern.velocity_values[1] = 100

  program.get_sequencer_pattern(sequencer_pattern).patterns[1] = test_pattern
  fn.add_to_set(program.get_sequencer_pattern(sequencer_pattern).channels[1].selected_patterns, 1)
  pattern_controller.update_working_patterns()

  step_handler.handle(1, 1)

  local note_on_event = table.remove(midi_note_on_events)

  luaunit.assertEquals(note_on_event[1], 60)
  luaunit.assertEquals(note_on_event[2], 100)
  luaunit.assertEquals(note_on_event[3], 1)
end
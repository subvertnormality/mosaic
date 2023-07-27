local musicutil = require("musicutil")

local program = {}
local program_store = {}

local pages = {
  channel_edit_page = 1,
  channel_sequencer_page = 2,
  pattern_trigger_edit_page = 3,
  pattern_note_edit_page = 4,
  pattern_velocity_edit_page = 5
}

local function add_step_trig_lock(sequencer_pattern, channel, step, parameter, trig_lock)
  local step_trig_lock_banks = program.get().sequencer_patterns[sequencer_pattern].channels[channel].step_trig_lock_banks
  if step_trig_lock_banks[step] == nil then
    step_trig_lock_banks[step] = {}
  end
  step_trig_lock_banks[step][parameter] = trig_lock
end

local function get_step_trig_lock(sequencer_pattern, channel, step, parameter)
  local step_trig_lock_banks = program.get().sequencer_patterns[sequencer_pattern].channels[channel].step_trig_lock_banks
  if step_trig_lock_banks[step] == nil then
    return nil
  end
  return step_trig_lock_banks[step][parameter]
end

local function initialise_default_channels()
  
  local channels = {}
  
  for i=1,16 do
    channels[i] = {
      trig_lock_banks = {0, 0, 0, 0, 0, 0, 0, 0},
      trig_lock_params = {{}, {}, {}, {}, {}, {}, {}, {}},
      step_trig_lock_banks = {},
      working_pattern = {
        trig_values = program.initialise_64_table(0),
        lengths = program.initialise_64_table(1),
        note_values = program.initialise_64_table(0),
        velocity_values = program.initialise_64_table(100)
      },
      start_trig = {1, 4},
      end_trig = {16, 7},
      midi_channel = i,
      midi_device = 1,
      selected_patterns = {},
      default_scale = 1,
      root_note = 0,
      chord = 1,
      step_scales = program.initialise_64_table(0),
      merge_mode = "skip",
      octave = 0,
      clock_division = 4,
      current_step = 1,
      midi_device_map = 1
    }
  end
  
  return channels
end


local function initialise_default_patterns()
  
  local patterns = {}

  for i=1,16 do
    patterns[i] = program.initialise_default_pattern()
  end
  
  return patterns
end


local function initialise_default_sequencer_patterns()
  
  local sequencer_patterns = {}
  
  for i=1,96 do 
    
    sequencer_patterns[i] = {
      active = false,
      global_pattern_length = 64,
      scale = 0,
      patterns = initialise_default_patterns(),
      channels = initialise_default_channels()
    }
    
  end

  return sequencer_patterns
end


function program.initialise_default_pattern()
  
  return {
    trig_values = program.initialise_64_table(0),
    lengths = program.initialise_64_table(1),
    note_values = program.initialise_64_table(0),
    velocity_values = program.initialise_64_table(100)
  }

end

function program.initialise_64_table(d)
  local table_64 = {}
  for i=1,64 do
    table_64[i] = d
  end
  return table_64
end

function program.init()
  local root_note = 0
  program_store = {
    selected_page = pages.channel_edit_page,
    selected_sequencer_pattern = 1,
    selected_pattern = 1,
    selected_channel = 1,
    scale_type = "sinfonion",
    root_note = root_note,
    chord = 1,
    default_scale = 1,
    chord = 1,
    current_step = 1,
    scales = {
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1}, 
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1},
      {number = 1, scale = musicutil.generate_scale_of_length(0, "major", 7), root_note = root_note, chord = 1}
    },
    sequencer_patterns = initialise_default_sequencer_patterns()
  }

end

function program.get()
  return program_store
end

function program.get_selected_channel()
  return program_store.sequencer_patterns[program_store.selected_sequencer_pattern].channels[program_store.selected_channel]
end

function program.get_selected_pattern()
  return program_store.get().sequencer_patterns[program.get().selected_sequencer_pattern].patterns[program.get().selected_pattern]
end

function program.get_channel(x)
  return program_store.sequencer_patterns[program_store.selected_sequencer_pattern].channels[x]
end

function program.set(p)
  program_store = p
end

function program.get_pages()
  return pages
end

return program
_grid = include("sinfcommand/lib/_grid")
fn = include("sinfcommand/lib/functions")

function initialise_64_table()
  local table_64 = {}
  for i=1,64 do
    table_64[i] = -1
  end
  return table_64
end


function initialise_default_trig_locks()
  local trig_locks = {}
  for i=1,64 do
    trig_locks[i] = -1
  end
  return trig_locks
end

function initialise_default_trig_lock_banks()
  local trig_lock_banks = {}
  for i=1,8 do
    trig_lock_banks[i] = initialise_default_trig_locks()
  end
  return trig_lock_banks
end


function initialise_default_channels()
  
  local channels = {}
  
  for i=1,16 do
    channels[i] = {
      trig_lock_banks = initialise_default_trig_lock_banks(),
      start_trig = 0,
      end_trig = 0,
      midi_channel_location = 1,
      default_note = 60,
      merge_mode = "add",
      trig_lock_locations = {
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 },
        {midi_channel = -1, midi_cc = -1 }
      }
    }
  end
  
  return channels
end

function initialise_default_patterns()
  
  local patterns = {}
  
  for i=1,16 do
    patterns[i] = {
      trig_values = initialise_64_table(),
      lengths = initialise_64_table(),
      note_values = initialise_64_table(),
      velocity_values = initialise_64_table(),
      probability_values = initialise_64_table()
    }
  end
  
  return patterns
end


function initialise_default_sequencer_patterns()
  
  local sequencer_patterns = {}
  
  for i=1,64 do 
    sequencer_patterns[i] = {
      global_pattern_length = 64,
      scale = 0,
      patterns = initialise_default_patterns(),
      channels = initialise_default_channels()
    }
  end
  
  return sequencer_patterns
end

program = {
  selected_page = "pattern_trigger_edit_page",
  selected_sequencer_pattern = 1,
  selected_pattern = 1,
  current_step = 1,
  scale_type = "sinfonion",
  scales = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
  sequencer_patterns = initialise_default_sequencer_patterns()
}


function init()
  _grid.init()
  grid_clock_id = clock.run(_grid.grid_redraw_clock)
  fn.dirty_grid(true)
end
local grid_controller = include("sinfcommand/lib/grid_controller")
local fn = include("sinfcommand/lib/functions")

function initialise_64_table(d)
  local table_64 = {}
  for i=1,64 do
    table_64[i] = d
  end
  return table_64
end



function initialise_default_trig_lock_banks()
  local trig_lock_banks = {}
  for i=1,8 do
    trig_lock_banks[i] = initialise_64_table(-1)
  end
  return trig_lock_banks
end


function initialise_default_channels()
  
  local channels = {}
  
  for i=1,16 do
    channels[i] = {
      trig_lock_banks = initialise_default_trig_lock_banks(),
      start_trig = {1, 4},
      end_trig = {16, 7},
      midi_channel_location = 1,
      selected_patterns = {},
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
      trig_values = initialise_64_table(0),
      lengths = initialise_64_table(-1),
      note_values = initialise_64_table(-1),
      velocity_values = initialise_64_table(-1)
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

pages = {
  channel_edit_page = 1,
  channel_sequencer_page = 2,
  pattern_trigger_edit_page = 3,
  pattern_note_edit_page = 4,
  pattern_velocity_edit_page = 5
}

program = {
  selected_page = pages.channel_edit_page,
  selected_sequencer_pattern = 1,
  selected_pattern = 1,
  selected_channel = 1,
  current_step = 1,
  scale_type = "sinfonion",
  scales = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
  sequencer_patterns = initialise_default_sequencer_patterns()
}

function save_state(pset_number)
  os.execute("mkdir -p "..norns.state.data.."/"..pset_number.."/")
  local file = io.open(norns.state.data.."/"..pset_number.."/script_settings.data", "w+")
  io.output(file)
  io.write(fn.table_to_string(program))
  io.close(file)
end


function load_state(pset_number)
  all_loaded = false
  local file = io.open(norns.state.data.."/"..pset_number.."/script_settings.data", "r")
  if file then
    io.input(file)
    program = fn.string_to_table(io.read())
    io.close(file)
    fn.dirty_grid(true)
    fn.dirty_screen(true)
  end
  
  
end

function init()

  params.action_write = function(filename, name, pset_number)
    if pset_number == nil then
      clock.run(function()
        clock.sleep(0.25)
        local file = io.open(norns.state.data.."pset-last.txt", "r")
        if file then
          io.input(file)
          pset_number = string.format("%02d",io.read())
          save_state(pset_number)
          io.close(file)
        end
      end)
    else
      save_state(pset_number)
    end
  end
  params.action_read = function(filename, silent, pset_number)
    if pset_number == nil then
      clock.run(function()
        clock.sleep(0.25)
        local file = io.open(norns.state.data.."pset-last.txt", "r")
        if file then
          io.input(file)
          pset_number = string.format("%02d",io.read())
          load_state(pset_number)
          io.close(file)
        end
      end)
    else
      load_state(pset_number)
    end
  end
  params.action_delete = function(filename, name, pset_number)
    if pset_number == nil then
      clock.run(function()
        clock.sleep(0.25)
        local file = io.open(norns.state.data.."pset-last.txt", "r")
        if file then
          io.input(file)
          pset_number = string.format("%02d",io.read())
          norns.system_cmd("rm -r "..norns.state.data.."/"..pset_number.."/")
          io.close(file)
        end
      end)
    else
      norns.system_cmd("rm -r "..norns.state.data.."/"..pset_number.."/")
    end
  end

  grid_controller.init()
  grid_clock_id = clock.run(grid_controller.grid_redraw_clock)
  fn.dirty_grid(true)
end
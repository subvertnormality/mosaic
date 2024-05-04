local musicutil = require("musicutil")
local fn = include("mosaic/lib/functions")

local program = {}
local program_store = {}

local pages = {
  channel_edit_page = 1,
  channel_sequencer_page = 2,
  pattern_trigger_edit_page = 3,
  pattern_note_edit_page = 4,
  pattern_velocity_edit_page = 5
}

local function initialise_default_channels()
  local channels = {}

  for i = 1, 17 do
    channels[i] = {
      number = i,
      trig_lock_banks = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
      trig_lock_params = {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}},
      step_trig_lock_banks = {},
      step_octave_trig_lock_banks = {},
      step_scale_trig_lock_banks = {},
      step_trig_masks = {},
      step_note_masks = {},
      step_velocity_masks = {},
      step_length_masks = {},
      step_micro_time_masks = {},
      step_chord_masks = {},
      working_pattern = {
        trig_values = program.initialise_64_table(0),
        lengths = program.initialise_64_table(1),
        note_values = program.initialise_64_table(0),
        velocity_values = program.initialise_64_table(100),
        note_mask_values = {},
      },
      start_trig = {1, 4},
      end_trig = {16, 7},
      selected_patterns = {},
      default_scale = 1,
      step_scale_number = 1,
      root_note = 0,
      chord = 1,
      trig_merge_mode = "skip",
      note_merge_mode = "average",
      velocity_merge_mode = "average",
      length_merge_mode = "average",
      octave = 0,
      clock_mods = {name = "/1", value = 1, type = "clock_division"},
      current_step = 1,
      mute = false,
      swing = 50
    }
  end

  return channels
end

local function initialise_default_patterns()
  local patterns = {}

  for i = 1, 16 do
    patterns[i] = program.initialise_default_pattern()
  end

  return patterns
end

local function initialise_default_sequencer_pattern()
  local sequencer_pattern = {}
  local root_note = 0

  sequencer_pattern = {
    active = false,
    global_pattern_length = 64,
    scale = 0,
    repeats = 1,
    patterns = initialise_default_patterns(),
    channels = initialise_default_channels(),
    scales = {
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0},
      {number = 1, scale = musicutil.generate_scale(0, "major", 20), root_note = root_note, chord = 1, chord_degree_rotation = 0}
    }
  }

  return sequencer_pattern
end

function program.initialise_64_table(d)
  local table_64 = {}
  for i = 1, 64 do
    table_64[i] = d
  end
  return table_64
end

function program.initialise_default_pattern()
  return {
    trig_values = program.initialise_64_table(0),
    lengths = program.initialise_64_table(1),
    note_values = program.initialise_64_table(0),
    note_mask_values = program.initialise_64_table(-1),
    velocity_values = program.initialise_64_table(100)
  }
end

function program.init()
  local root_note = 0
  program_store = {
    selected_page = pages.channel_edit_page,
    selected_sequencer_pattern = 1,
    selected_pattern = 1,
    selected_channel = 1,
    selected_scale = 1,
    root_note = root_note,
    chord = 1,
    default_scale = 1,
    current_step = 1,
    current_channel_step = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1},
    sequencer_patterns = {},
    global_step_accumulator = 0,
    devices = {
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"},
      {midi_channel = 1, midi_device = 1, device_map = "none"}
    }
  }
end

function program.is_sequencer_pattern_active(p)
  if (program_store.sequencer_patterns[p] and program_store.sequencer_patterns[p].active) then
    return true
  end

  return false
end

function program.get_selected_sequencer_pattern()
  return program.get_sequencer_pattern(program_store.selected_sequencer_pattern)
end

function program.set_selected_sequencer_pattern(p)
  program_store.selected_sequencer_pattern = p
end

function program.get_sequencer_pattern(p)
  if not program_store.sequencer_patterns[p] then
    program_store.sequencer_patterns[p] = initialise_default_sequencer_pattern()
  end

  return program_store.sequencer_patterns[p]
end

function program.set_sequencer_pattern(p, pattern)
  local sequencer_pattern = fn.deep_copy(program.get_sequencer_pattern(p))

  program_store.sequencer_patterns[pattern] = sequencer_pattern
end

function program.get_current_step_for_channel(c)
  return program_store.current_channel_step[c]
end

function program.set_current_step_for_channel(c, s)
  program_store.current_channel_step[c] = s
end

function program.set_global_step_scale_number(step_scale_number)
  for _, sequencer_pattern in pairs(program_store.sequencer_patterns) do
    sequencer_pattern.channels[17].step_scale_number = step_scale_number
  end
end

function program.set_channel_step_scale_number(c, step_scale_number)
  for _, sequencer_pattern in pairs(program_store.sequencer_patterns) do
    sequencer_pattern.channels[c].step_scale_number = step_scale_number
  end
end

function program.get()
  return program_store
end

function program.get_selected_channel()
  return program.get_sequencer_pattern(program.get().selected_sequencer_pattern).channels[program.get().selected_channel]
end

function program.get_selected_pattern()
  return program.get_sequencer_pattern(program.get().selected_sequencer_pattern).patterns[program.get().selected_pattern]
end

function program.get_channel(x)
  return program.get_sequencer_pattern(program.get().selected_sequencer_pattern).channels[x]
end

function program.set(p)
  program_store = p
end

function program.get_pages()
  return pages
end

function program.add_step_param_trig_lock(step, parameter, trig_lock)
  local step_trig_lock_banks = program.get_selected_channel().step_trig_lock_banks
  local trig_lock_params = program.get_selected_channel().trig_lock_params
  if step_trig_lock_banks[step] == nil then
    step_trig_lock_banks[step] = {}
  end
  if (trig_lock < (trig_lock_params[parameter].cc_min_value or 0)) then
    trig_lock = (trig_lock_params[parameter].cc_min_value or 0)
  end
  if (trig_lock > (trig_lock_params[parameter].cc_max_value or 127)) then
    trig_lock = (trig_lock_params[parameter].cc_max_value or 127)
  end
  step_trig_lock_banks[step][parameter] = trig_lock
end

function program.get_step_param_trig_lock(channel, step, parameter)
  local step_trig_lock_banks = channel.step_trig_lock_banks
  if step_trig_lock_banks[step] == nil then
    return nil
  end
  return step_trig_lock_banks[step][parameter]
end

function program.step_has_param_trig_lock(channel, step)
  local step_trig_lock_banks = channel.step_trig_lock_banks

  if step_trig_lock_banks[step] == nil then
    return false
  end

  return true
end

function program.step_has_trig_lock(channel, step)
  if
    program.step_has_param_trig_lock(channel, step) or program.step_octave_has_trig_lock(channel, step) or
      program.step_scale_has_trig_lock(channel, step) or
      program.step_transpose_has_trig_lock(step) or 
      program.step_has_trig_mask(step) or
      program.step_has_note_mask(step) or
      program.step_has_velocity_mask(step) or
      program.step_has_length_mask(step) or
      program.step_has_micro_time_mask(step) or
      program.step_has_chord_1_mask(step) or
      program.step_has_chord_2_mask(step) or
      program.step_has_chord_3_mask(step) or
      program.step_has_chord_4_mask(step)
   then
    return true
  end

  return false
end

function program.add_step_octave_trig_lock(step, trig_lock)
  local selected_channel = program.get_selected_channel()
  if selected_channel.step_octave_trig_lock_banks == nil then
    selected_channel.step_octave_trig_lock_banks = {}
  end
  local step_octave_trig_lock_banks = selected_channel.step_octave_trig_lock_banks

  if trig_lock ~= nil then
    if (trig_lock < -2) then
      trig_lock = -2
    end
    if (trig_lock > 2) then
      trig_lock = 2
    end
  end

  step_octave_trig_lock_banks[step] = trig_lock
end

function program.get_step_octave_trig_lock(channel, step)
  local step_octave_trig_lock_banks = channel.step_octave_trig_lock_banks
  if not step_octave_trig_lock_banks or step_octave_trig_lock_banks[step] == nil then
    return nil
  end
  return step_octave_trig_lock_banks[step]
end

function program.step_octave_has_trig_lock(channel, step)
  local step_octave_trig_lock_banks = channel.step_octave_trig_lock_banks

  if step_octave_trig_lock_banks and step_octave_trig_lock_banks[step] and step_octave_trig_lock_banks[step] ~= 0 then
    return true
  end

  return false
end

function program.add_step_transpose_trig_lock(step, trig_lock)
  local channel = program.get_channel(17)
  if channel.step_transpose_trig_lock_banks == nil then
    channel.step_transpose_trig_lock_banks = {}
  end
  local step_transpose_trig_lock_banks = channel.step_transpose_trig_lock_banks

  if trig_lock ~= nil then
    if (trig_lock < -7) then
      trig_lock = -7
    end
    if (trig_lock > 7) then
      trig_lock = 7
    end
  end

  step_transpose_trig_lock_banks[step] = trig_lock
end

function program.set_transpose(transpose)
  program.get_selected_sequencer_pattern().transpose = transpose
end

function program.get_transpose()
  if program.get_selected_sequencer_pattern().transpose == nil then
    return 0
  else
    return program.get_selected_sequencer_pattern().transpose
  end
end

function program.get_step_transpose_trig_lock(step)
  local channel = program.get_channel(17)
  local step_transpose_trig_lock_banks = channel.step_transpose_trig_lock_banks
  if step_transpose_trig_lock_banks == nil or step_transpose_trig_lock_banks[step] == nil then
    return nil
  end
  return step_transpose_trig_lock_banks[step]
end

function program.step_transpose_has_trig_lock(step)
  local channel = program.get_channel(17)
  local step_transpose_trig_lock_banks = channel.step_transpose_trig_lock_banks

  if step_transpose_trig_lock_banks ~= nil and step_transpose_trig_lock_banks[step] and step_transpose_trig_lock_banks[step] ~= 0 then
    return true
  end

  return false
end

function program.step_has_trig_mask(step)
  local step_trig_masks = program.get_selected_channel().step_trig_masks

  if step_trig_masks and step_trig_masks[step] then
    return true
  end

  return false
end

function program.step_has_note_mask(step)
  local step_note_masks = program.get_selected_channel().step_note_masks

  if step_note_masks and step_note_masks[step] then
    return true
  end

  return false
end

function program.step_has_velocity_mask(step)
  local step_velocity_masks = program.get_selected_channel().step_velocity_masks

  if step_velocity_masks and step_velocity_masks[step] then
    return true
  end

  return false
end

function program.step_has_length_mask(step)
  local step_length_masks = program.get_selected_channel().step_length_masks

  if step_length_masks and step_length_masks[step] then
    return true
  end

  return false
end

function program.step_has_micro_time_mask(step)
  local step_micro_time_masks = program.get_selected_channel().step_micro_time_masks

  if step_micro_time_masks and step_micro_time_masks[step] then
    return true
  end

  return false
end

function program.step_has_chord_1_mask(step)
  local step_chord_masks = program.get_selected_channel().step_chord_masks

  if step_chord_masks and step_chord_masks[step] and step_chord_masks[step][1] then
    return true
  end

  return false
end

function program.step_has_chord_2_mask(step)
  local step_chord_masks = program.get_selected_channel().step_chord_masks

  if step_chord_masks and step_chord_masks[step] and step_chord_masks[step][2] then
    return true
  end

  return false
end

function program.step_has_chord_3_mask(step)
  local step_chord_masks = program.get_selected_channel().step_chord_masks

  if step_chord_masks and step_chord_masks[step] and step_chord_masks[step][3] then
    return true
  end

  return false
end

function program.step_has_chord_4_mask(step)
  local step_chord_masks = program.get_selected_channel().step_chord_masks

  if step_chord_masks and step_chord_masks[step] and step_chord_masks[step][4] then
    return true
  end

  return false
end



function program.add_step_scale_trig_lock(step, trig_lock)
  local selected_channel = program.get_selected_channel()
  if selected_channel.step_scale_trig_lock_banks == nil then
    selected_channel.step_scale_trig_lock_banks = {}
  end
  local step_scale_trig_lock_banks = selected_channel.step_scale_trig_lock_banks

  if trig_lock ~= nil then
    if (trig_lock < 1) then
      trig_lock = 1
    end
    if (trig_lock > 16) then
      trig_lock = 16
    end
  end

  step_scale_trig_lock_banks[step] = trig_lock
end

function program.get_step_scale_trig_lock(channel, step)
  local step_scale_trig_lock_banks = channel.step_scale_trig_lock_banks
  if not step_scale_trig_lock_banks or step_scale_trig_lock_banks[step] == nil then
    return nil
  end
  return step_scale_trig_lock_banks[step]
end

function program.step_scale_has_trig_lock(channel, step)
  local step_scale_trig_lock_banks = channel.step_scale_trig_lock_banks

  if step_scale_trig_lock_banks and step_scale_trig_lock_banks[step] then
    return true
  end

  return false
end

function program.clear_trig_locks_for_step(step)
  local channel = program.get_selected_channel()
  local step_trig_lock_banks = channel.step_trig_lock_banks
  program.add_step_scale_trig_lock(step, nil)
  if channel.number ~= 17 then
    if (step_trig_lock_banks and step_trig_lock_banks[step]) then
      step_trig_lock_banks[step] = nil
    end

    program.add_step_octave_trig_lock(step, nil)
  elseif channel.number == 17 then
    program.add_step_transpose_trig_lock(step, nil)
  end
end

function program.clear_masks_for_step(step)
  program.clear_step_trig_mask(program.get().selected_channel, step)
  program.clear_step_note_mask(program.get().selected_channel, step)
  program.clear_step_velocity_mask(program.get().selected_channel, step)
  program.clear_step_length_mask(program.get().selected_channel, step)
  program.clear_step_micro_time_mask(program.get().selected_channel, step)
  program.clear_step_chord_1_mask(program.get().selected_channel, step)
  program.clear_step_chord_2_mask(program.get().selected_channel, step)
  program.clear_step_chord_3_mask(program.get().selected_channel, step)
  program.clear_step_chord_4_mask(program.get().selected_channel, step)
end

function program.get_scale(s)
  if s == 0 then
    return {
      name = "Chromatic",
      number = 0,
      scale = musicutil.generate_scale(0, "chromatic", 12),
      romans = {},
      root_note = 0,
      chord = 1,
      chord_degree_rotation = 0
    }
  end

  -- Backwards compatability
  if not program.get_selected_sequencer_pattern().scales then
    if program_store.scales then
      program.get_selected_sequencer_pattern().scales = fn.deep_copy(program_store.scales)
    end
  end

  return program.get_selected_sequencer_pattern().scales[s]
end

function program.set_scale(s, scale)
  program.get_selected_sequencer_pattern().scales[s] = scale
end

function program.set_all_sequencer_pattern_scales(s, scale)
  for _, sequencer_pattern in pairs(program_store.sequencer_patterns) do
    sequencer_pattern.scales[s] = scale
  end
end

function program.set_chord_degree_rotation_for_scale(s, rotation)
  if rotation then
    program.get_selected_sequencer_pattern().scales[s].chord_degree_rotation = util.clamp(rotation, 0, 6)
  end
end

function program.get_step_trig_masks(channel) 
  if program.get_channel(channel) == nil then return end

  if program.get_channel(channel).step_trig_masks == nil then
    program.get_channel(channel).step_trig_masks = {}
  end
  return program.get_channel(channel).step_trig_masks
end

function program.set_step_trig_mask(channel, step, mask)
  if program.get_channel(channel).step_trig_masks == nil then
    program.get_channel(channel).step_trig_masks = {}
  end
  program.get_channel(channel).step_trig_masks[step] = mask
end

function program.get_step_note_masks(channel) 
  if program.get_channel(channel) == nil then return end

  if program.get_channel(channel).step_note_masks == nil then
    program.get_channel(channel).step_note_masks = {}
  end
  return program.get_channel(channel).step_note_masks
end

function program.get_step_velocity_masks(channel) 
  if program.get_channel(channel) == nil then return end

  if program.get_channel(channel).step_velocity_masks == nil then
    program.get_channel(channel).step_velocity_masks = {}
  end
  return program.get_channel(channel).step_velocity_masks
end

function program.get_step_length_masks(channel) 
  if program.get_channel(channel) == nil then return end

  if program.get_channel(channel).step_length_masks == nil then
    program.get_channel(channel).step_length_masks = {}
  end
  return program.get_channel(channel).step_length_masks
end


function program.toggle_step_trig_mask(channel, step)
  if program.get_channel(channel).step_trig_masks == nil then
    program.get_channel(channel).step_trig_masks = {}
  end

  if program.get_channel(channel).working_pattern.trig_values[step] == 0 then
    program.get_channel(channel).step_trig_masks[step] = 1
  elseif program.get_channel(channel).working_pattern.trig_values[step] == 1 then
    program.get_channel(channel).step_trig_masks[step] = 0
  end

end

function program.clear_step_trig_mask(channel, step)
  program.get_channel(channel).step_trig_masks[step] = nil
end

function program.clear_step_note_mask(channel, step)
  program.get_channel(channel).step_note_masks[step] = nil
end

function program.clear_step_velocity_mask(channel, step)
  program.get_channel(channel).step_velocity_masks[step] = nil
end

function program.clear_step_length_mask(channel, step)
  program.get_channel(channel).step_length_masks[step] = nil
end

function program.clear_step_micro_time_mask(channel, step)
  program.get_channel(channel).step_micro_time_masks[step] = nil
end

function program.clear_step_chord_1_mask(channel, step)
  if program.get_channel(channel).step_chord_masks == nil then
    program.get_channel(channel).step_chord_masks = {}
  end
  if program.get_channel(channel).step_chord_masks[step] ~= nil then
    program.get_channel(channel).step_chord_masks[step][1] = nil
  end
end

function program.clear_step_chord_2_mask(channel, step)
  if program.get_channel(channel).step_chord_masks == nil then
    program.get_channel(channel).step_chord_masks = {}
  end
  if program.get_channel(channel).step_chord_masks[step] ~= nil then
    program.get_channel(channel).step_chord_masks[step][2] = nil
  end
end

function program.clear_step_chord_3_mask(channel, step)
  if program.get_channel(channel).step_chord_masks == nil then
    program.get_channel(channel).step_chord_masks = {}
  end
  if program.get_channel(channel).step_chord_masks[step] ~= nil then
    program.get_channel(channel).step_chord_masks[step][3] = nil
  end

end

function program.clear_step_chord_4_mask(channel, step)
  if program.get_channel(channel).step_chord_masks == nil then
    program.get_channel(channel).step_chord_masks = {}
  end
  if program.get_channel(channel).step_chord_masks[step] ~= nil then
    program.get_channel(channel).step_chord_masks[step][4] = nil
  end
end



return program

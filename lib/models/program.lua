local musicutil = require("musicutil")

local quantiser = include("mosaic/lib/quantiser")

local program = {}
local program_store = {}


local function initialise_default_channels()
  local channels = {}

  for i = 1, 17 do
    channels[i] = {
      number = i,
      trig_lock_params = {{}, {}, {}, {}, {}, {}, {}, {}, {}, {}},
      trig_lock_calculator_ids = {},
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
      swing_shuffle_type = nil, -- 1 for Swing, 2 for Shuffle, nil to use global
      swing = nil,              -- -50 to 50, nil to use global
      shuffle_feel = nil,       -- 1 to 4, nil to use global
      shuffle_basis = nil,      -- 1 to 6, nil to use global
      shuffle_amount = nil
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

  local c_major = quantiser.get_scale(1)

  local function create_scale()
    return {
      number = 1,
      scale = c_major.scale,
      pentatonic_scale = c_major.pentatonic_scale,
      root_note = root_note,
      chord = 1,
      chord_degree_rotation = 0
    }
  end

  sequencer_pattern = {
    active = false,
    global_pattern_length = 64,
    scale = 0,
    repeats = 1,
    patterns = initialise_default_patterns(),
    channels = initialise_default_channels(),
    scales = {}
  }

  for i = 1, 16 do
    table.insert(sequencer_pattern.scales, create_scale())
  end

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
    selected_page = pages.pages.channel_edit_page,
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
    devices = {},
    blink_state = false
  }

  for i = 1, 16 do
    table.insert(program_store.devices, {midi_channel = 1, midi_device = 1, device_map = "none"})
  end
end

function program.is_sequencer_pattern_active(p)
  return program_store.sequencer_patterns[p] and program_store.sequencer_patterns[p].active or false
end

function program.get_selected_sequencer_pattern()
  return program.get_sequencer_pattern(program_store.selected_sequencer_pattern)
end

function program.set_selected_sequencer_pattern(p)
  program_store.selected_sequencer_pattern = p
end

function program.set_selected_page(p)
  program_store.selected_page = p
end

function program.get_selected_page()
  return program_store.selected_page
end

function program.get_sequencer_pattern(p)
  if not program_store.sequencer_patterns[p] then
    program_store.sequencer_patterns[p] = initialise_default_sequencer_pattern()
  end
  return program_store.sequencer_patterns[p]
end

function program.set_sequencer_pattern(p, pattern)
  program_store.sequencer_patterns[pattern] = fn.deep_copy(program.get_sequencer_pattern(p))
end

function program.get_current_step_for_channel(c)
  return program_store.current_channel_step[c]
end

function program.set_current_step_for_channel(c, s)
  program_store.current_channel_step[c] = s
end

function program.set_global_step_scale_number(step_scale_number)
  -- TODO check why this was being applied across all sequencer patterns
  -- for _, sequencer_pattern in pairs(program_store.sequencer_patterns) do
    program.get_selected_sequencer_pattern().channels[17].step_scale_number = step_scale_number
  -- end
end

function program.set_channel_step_scale_number(c, step_scale_number)
  -- TODO check why this was being applied across all sequencer patterns
  -- for _, sequencer_pattern in pairs(program_store.sequencer_patterns) do
    program.get_selected_sequencer_pattern().channels[c].step_scale_number = step_scale_number
  -- end
end

function program.get_channel_step_scale_number(c)
  return program.get_selected_sequencer_pattern().channels[c].step_scale_number
end

function program.get()
  return program_store
end

function program.get_selected_channel()
  return program.get_selected_sequencer_pattern().channels[program.get().selected_channel]
end

function program.get_selected_pattern()
  return program.get_selected_sequencer_pattern().patterns[program.get().selected_pattern]
end

function program.get_channel(song_pattern, x)
  return program.get_sequencer_pattern(song_pattern).channels[x]
end

function program.set(p)
  program_store = p
end

function program.add_step_param_trig_lock(step, parameter, trig_lock)
  local channel = program.get_selected_channel()
  local step_trig_lock_banks = channel.step_trig_lock_banks
  local trig_lock_params = channel.trig_lock_params

  if not step_trig_lock_banks[step] then
    step_trig_lock_banks[step] = {}
  end

  trig_lock = math.max(trig_lock, trig_lock_params[parameter].nrpn_min_value or trig_lock_params[parameter].cc_min_value or 0)
  trig_lock = math.min(trig_lock, trig_lock_params[parameter].nrpn_max_value or trig_lock_params[parameter].cc_max_value or 127)

  step_trig_lock_banks[step][parameter] = trig_lock
end


function program.get_step_param_trig_lock(channel, step, parameter)
  local step_trig_lock_banks = channel.step_trig_lock_banks
  return step_trig_lock_banks[step] and step_trig_lock_banks[step][parameter] or nil
end

function program.step_has_param_trig_lock(channel, step)
  local step_trig_lock_banks = channel.step_trig_lock_banks
  return step_trig_lock_banks[step] ~= nil
end

function program.step_has_trig_lock(channel, step)

  return program.step_has_param_trig_lock(channel, step) or 
         program.step_octave_has_trig_lock(channel, step) or 
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
end

function program.add_step_octave_trig_lock(step, trig_lock)
  local channel = program.get_selected_channel()
  local step_octave_trig_lock_banks = channel.step_octave_trig_lock_banks

  trig_lock = trig_lock and math.max(math.min(trig_lock, 2), -2) or nil

  step_octave_trig_lock_banks[step] = trig_lock
end

function program.get_step_octave_trig_lock(channel, step)
  local step_octave_trig_lock_banks = channel.step_octave_trig_lock_banks
  return step_octave_trig_lock_banks and step_octave_trig_lock_banks[step] or nil
end

function program.step_octave_has_trig_lock(channel, step)
  local step_octave_trig_lock_banks = channel.step_octave_trig_lock_banks
  return step_octave_trig_lock_banks and step_octave_trig_lock_banks[step] and step_octave_trig_lock_banks[step] ~= 0
end

function program.add_step_transpose_trig_lock(step, trig_lock)
  local channel = program.get_channel(program.get().selected_sequencer_pattern, 17)

  if trig_lock ~= nil then
    trig_lock = math.max(math.min(trig_lock, 7), -7) or nil
  end

  if not channel.step_transpose_trig_lock_banks then 
    channel.step_transpose_trig_lock_banks = {}
  end

  channel.step_transpose_trig_lock_banks[step] = trig_lock
end

function program.set_transpose(transpose)
  program.get_selected_sequencer_pattern().transpose = transpose or 0
end

function program.set_scale_transpose(scale, transpose)
  
  local s = program.get_scale(scale)
  s.transpose = transpose
end

function program.get_transpose()
  return program.get_selected_sequencer_pattern().transpose or 0
end

function program.get_step_transpose_trig_lock(step)
  local channel = program.get_channel(program.get().selected_sequencer_pattern, 17)
  local step_transpose_trig_lock_banks = channel.step_transpose_trig_lock_banks
  return step_transpose_trig_lock_banks and step_transpose_trig_lock_banks[step]
end

function program.step_transpose_has_trig_lock(step)
  if program.get_selected_channel().number ~= 17 then return false end
  local channel = program.get_channel(program.get().selected_sequencer_pattern, 17)
  local step_transpose_trig_lock_banks = channel.step_transpose_trig_lock_banks
  return step_transpose_trig_lock_banks and step_transpose_trig_lock_banks[step]
end

function program.step_has_trig_mask(step)
  local step_trig_masks = program.get_selected_channel().step_trig_masks
  return step_trig_masks and step_trig_masks[step]
end

function program.step_has_note_mask(step)
  local step_note_masks = program.get_selected_channel().step_note_masks
  return step_note_masks and step_note_masks[step]
end

function program.step_has_velocity_mask(step)
  local step_velocity_masks = program.get_selected_channel().step_velocity_masks
  return step_velocity_masks and step_velocity_masks[step]
end

function program.step_has_length_mask(step)
  local step_length_masks = program.get_selected_channel().step_length_masks
  return step_length_masks and step_length_masks[step]
end

function program.step_has_micro_time_mask(step)
  local step_micro_time_masks = program.get_selected_channel().step_micro_time_masks
  return step_micro_time_masks and step_micro_time_masks[step]
end

function program.step_has_chord_1_mask(step)
  local step_chord_masks = program.get_selected_channel().step_chord_masks
  return step_chord_masks and step_chord_masks[step] and step_chord_masks[step][1]
end

function program.step_has_chord_2_mask(step)
  local step_chord_masks = program.get_selected_channel().step_chord_masks
  return step_chord_masks and step_chord_masks[step] and step_chord_masks[step][2]
end

function program.step_has_chord_3_mask(step)
  local step_chord_masks = program.get_selected_channel().step_chord_masks
  return step_chord_masks and step_chord_masks[step] and step_chord_masks[step][3]
end

function program.step_has_chord_4_mask(step)
  local step_chord_masks = program.get_selected_channel().step_chord_masks
  return step_chord_masks and step_chord_masks[step] and step_chord_masks[step][4]
end

function program.add_step_scale_trig_lock(step, trig_lock)
  local channel = program.get_selected_channel()
  local step_scale_trig_lock_banks = channel.step_scale_trig_lock_banks

  trig_lock = trig_lock and math.max(math.min(trig_lock, 16), 1) or nil

  step_scale_trig_lock_banks[step] = trig_lock
end

function program.get_step_scale_trig_lock(channel, step)
  local step_scale_trig_lock_banks = channel.step_scale_trig_lock_banks
  return step_scale_trig_lock_banks and step_scale_trig_lock_banks[step] or nil
end

function program.step_scale_has_trig_lock(channel, step)
  local step_scale_trig_lock_banks = channel.step_scale_trig_lock_banks
  return step_scale_trig_lock_banks and step_scale_trig_lock_banks[step]
end

function program.step_has_trig(channel, step)
  return channel.working_pattern.trig_values[step] == 1
end


function program.increment_trig_lock_calculator_id(channel, parameter)
  if not channel.trig_lock_calculator_ids then
    channel.trig_lock_calculator_ids = {}
  end
  channel.trig_lock_calculator_ids[parameter] = (channel.trig_lock_calculator_ids[parameter] or 0) + 1
end

function program.get_trig_lock_calculator_id(channel, parameter)
  if not channel.trig_lock_calculator_ids then
    channel.trig_lock_calculator_ids = {}
    channel.trig_lock_calculator_ids[parameter] = 0
  end
  return channel.trig_lock_calculator_ids[parameter]
end

function program.clear_trig_locks_for_step(step)
  local channel = program.get_selected_channel()
  program.add_step_scale_trig_lock(step, nil)

  if channel.number ~= 17 then
    if channel.step_trig_lock_banks and channel.step_trig_lock_banks[step] then
      channel.step_trig_lock_banks[step] = nil
    end
    program.add_step_octave_trig_lock(step, nil)
  else
    program.add_step_transpose_trig_lock(step, nil)
  end
end

function program.clear_trig_locks_for_channel(channel)
  channel.step_trig_lock_banks = {}
  channel.step_octave_trig_lock_banks = {}
  channel.step_scale_trig_lock_banks = {}
  channel.step_transpose_trig_lock_banks = {}
end

function program.clear_device_trig_locks_for_channel(channel)
  channel.step_trig_lock_banks = {}
end

function program.clear_masks_for_step(step)
  local channel = program.get().selected_channel
  program.clear_step_trig_mask(channel, step)
  program.clear_step_note_mask(channel, step)
  program.clear_step_velocity_mask(channel, step)
  program.clear_step_length_mask(channel, step)
  program.clear_step_micro_time_mask(channel, step)
  program.clear_step_chord_1_mask(channel, step)
  program.clear_step_chord_2_mask(channel, step)
  program.clear_step_chord_3_mask(channel, step)
  program.clear_step_chord_4_mask(channel, step)
end


function program.clear_masks_for_channel(channel)
  channel.step_trig_masks = {}
  channel.step_note_masks = {}
  channel.step_velocity_masks = {}
  channel.step_length_masks = {}
  channel.step_micro_time_masks = {}
  channel.step_chord_masks = {}
end

function program.get_scale(s)
  if s == 0 then
    return {
      name = "Chromatic",
      number = 0,
      scale = musicutil.generate_scale(0, "chromatic", 12),
      pentatonic_scale = musicutil.generate_scale(0, "chromatic", 12),
      romans = {},
      root_note = 0,
      chord = 1,
      chord_degree_rotation = 0
    }
  end

  -- Backwards compatibility
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

local function ensure_step_masks(channel)
  if not program.get_channel(program.get().selected_sequencer_pattern, channel).step_trig_masks then
    program.get_channel(program.get().selected_sequencer_pattern, channel).step_trig_masks = {}
  end
end


function program.get_step_trig_masks(channel)
  ensure_step_masks(channel)
  return program.get_channel(program.get().selected_sequencer_pattern, channel).step_trig_masks
end

function program.set_step_trig_mask(channel, step, mask)
  ensure_step_masks(channel)
  program.get_channel(program.get().selected_sequencer_pattern, channel).step_trig_masks[step] = mask
end

function program.set_trig_mask(channel, mask) 
  channel.trig_mask = mask
end

function program.get_step_note_masks(channel)
  ensure_step_masks(channel)
  return program.get_channel(program.get().selected_sequencer_pattern, channel).step_note_masks
end

function program.set_step_note_mask(channel, step, mask)
  channel.step_note_masks[step] = mask
end

function program.set_note_mask(channel, mask) 
  channel.note_mask = mask
end

function program.get_step_velocity_masks(channel)
  ensure_step_masks(channel)
  return program.get_channel(program.get().selected_sequencer_pattern, channel).step_velocity_masks
end

function program.set_velocity_mask(channel, mask) 
  channel.velocity_mask = mask
end

function program.get_step_length_masks(channel)
  ensure_step_masks(channel)
  return program.get_channel(program.get().selected_sequencer_pattern, channel).step_length_masks
end

function program.set_length_mask(channel, mask) 
  channel.length_mask = mask
end

function program.get_length_mask(channel) 
  return channel.length_mask
end

function program.set_step_length_mask(channel, step, mask)
  channel.step_length_masks[step] = mask
end

function program.set_chord_one_mask(channel, mask) 
  channel.chord_one_mask = mask
end

function program.set_chord_two_mask(channel, mask) 
  channel.chord_two_mask = mask
end

function program.set_chord_three_mask(channel, mask) 
  channel.chord_three_mask = mask
end

function program.set_chord_four_mask(channel, mask) 
  channel.chord_four_mask = mask
end

function program.get_effective_swing_shuffle_type(channel)
  if channel.swing_shuffle_type ~= nil then
    return channel.swing_shuffle_type
  else
    return params:get("global_swing_shuffle_type")
  end
end

function program.get_effective_swing(channel)
  if channel.swing ~= nil then
    return channel.swing
  else
    return params:get("global_swing")
  end
end

function program.get_effective_shuffle_feel(channel)
  if channel.shuffle_feel ~= nil then
    return channel.shuffle_feel
  else
    return params:get("global_shuffle_feel")
  end
end

function program.get_effective_shuffle_basis(channel)
  if channel.shuffle_basis ~= nil then
    return channel.shuffle_basis
  else
    return params:get("global_shuffle_basis")
  end
end

function program.get_effective_shuffle_amount(channel)
  if channel.shuffle_amount ~= nil then
    return channel.shuffle_amount
  else
    return params:get("global_shuffle_amount")
  end
end

function program.toggle_step_trig_mask(channel, step)
  ensure_step_masks(channel)

  local trig_values = program.get_channel(program.get().selected_sequencer_pattern, channel).working_pattern.trig_values
  if trig_values[step] == 0 then
    program.get_channel(program.get().selected_sequencer_pattern, channel).step_trig_masks[step] = 1
  elseif trig_values[step] == 1 then
    program.get_channel(program.get().selected_sequencer_pattern, channel).step_trig_masks[step] = 0
  end
end

function program.clear_step_trig_mask(channel, step)
  program.get_channel(program.get().selected_sequencer_pattern, channel).step_trig_masks[step] = nil
end

function program.clear_step_note_mask(channel, step)
  program.get_channel(program.get().selected_sequencer_pattern, channel).step_note_masks[step] = nil
end

function program.clear_step_velocity_mask(channel, step)
  program.get_channel(program.get().selected_sequencer_pattern, channel).step_velocity_masks[step] = nil
end

function program.clear_step_length_mask(channel, step)
  program.get_channel(program.get().selected_sequencer_pattern, channel).step_length_masks[step] = nil
end

function program.clear_step_micro_time_mask(channel, step)
  program.get_channel(program.get().selected_sequencer_pattern, channel).step_micro_time_masks[step] = nil
end

function program.clear_step_chord_1_mask(channel, step)
  local step_chord_masks = program.get_channel(program.get().selected_sequencer_pattern, channel).step_chord_masks
  if step_chord_masks and step_chord_masks[step] then
    step_chord_masks[step][1] = nil
  end
end

function program.clear_step_chord_2_mask(channel, step)
  local step_chord_masks = program.get_channel(program.get().selected_sequencer_pattern, channel).step_chord_masks
  if step_chord_masks and step_chord_masks[step] then
    step_chord_masks[step][2] = nil
  end
end

function program.clear_step_chord_3_mask(channel, step)
  local step_chord_masks = program.get_channel(program.get().selected_sequencer_pattern, channel).step_chord_masks
  if step_chord_masks and step_chord_masks[step] then
    step_chord_masks[step][3] = nil
  end
end

function program.clear_step_chord_4_mask(channel, step)
  local step_chord_masks = program.get_channel(program.get().selected_sequencer_pattern, channel).step_chord_masks
  if step_chord_masks and step_chord_masks[step] then
    step_chord_masks[step][4] = nil
  end
end

function program.set_step_chord_mask(channel, i, step, mask)
  local step_chord_masks = program.get_channel(program.get().selected_sequencer_pattern, channel).step_chord_masks
  if not step_chord_masks[step] then
    step_chord_masks[step] = {}
  end
  step_chord_masks[step][i] = mask
end

function program.get_blink_state()
  return program.get().blink_state
end

function program.toggle_blink_state()
  program.get().blink_state = not program.get().blink_state
end

function program.update_working_pattern_for_step(channel, step, trig, note_mask, velocity, length)
  if not channel.working_pattern then
    channel.working_pattern = program.initialise_default_pattern()
  end
  
  if note_mask then
    channel.working_pattern.note_mask_values[step] = note_mask
  end
  
  if velocity then
    channel.working_pattern.velocity_values[step] = velocity
  end
  
  if length then
    channel.working_pattern.lengths[step] = length
  end
  
  if trig then
    channel.working_pattern.trig_values[step] = trig
  end

end

function program.update_working_pattern_trig(channel, step, value)
  if not channel.working_pattern then
    channel.working_pattern = program.initialise_default_pattern()
  end
  channel.working_pattern.trig_values[step] = value
end

function program.clear_working_pattern_for_step(channel, step)
  if not channel.working_pattern then return end
  
  channel.working_pattern.trig_values[step] = 0
  channel.working_pattern.note_values[step] = 0
  channel.working_pattern.velocity_values[step] = 100 -- Default velocity
  channel.working_pattern.lengths[step] = 1 -- Default length
end

return program

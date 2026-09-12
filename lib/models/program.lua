local musicutil = require("musicutil")

local quantiser = include("mosaic/lib/quantiser")

local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")
local model_defaults = include("mosaic/lib/models/model_defaults").new(quantiser, nrpn_codec)
local program = {}
local program_store = {}

function program.initialise_64_table(value)
  return model_defaults.table_64(value)
end

function program.initialise_default_pattern()
  return model_defaults.pattern()
end

function program.init()
  program_store = model_defaults.program(pages.pages.channel_edit_page)
  if memory and memory.bind_project then memory.bind_project(program_store.memory) end
end

function program.is_song_pattern_active(p)
  return program_store.song_patterns[p] and program_store.song_patterns[p].active or false
end

function program.get_selected_song_pattern()
  local data = program.get()
  if not data.selected_song_pattern then
    data.selected_song_pattern = 1
  end
  return program.get_song_pattern(data.selected_song_pattern)
end

function program.set_selected_song_pattern(p)
  program_store.selected_song_pattern = p
end

function program.set_selected_page(p)
  program_store.selected_page = p
end

function program.get_selected_page()
  return program_store.selected_page
end

function program.get_song_pattern(p)
  local data = program_store
  if not data.song_patterns[p] then
    data.song_patterns[p] = model_defaults.song_pattern()
  end
  return data.song_patterns[p]
end

function program.set_song_pattern(p, pattern)
  program_store.song_patterns[pattern] = fn.deep_copy(program.get_song_pattern(p))
end

function program.get_current_step_for_channel(c)
  return program_store.current_channel_step[c]
end

function program.set_current_step_for_channel(c, s)
  program_store.current_channel_step[c] = s
end

function program.set_global_step_scale_number(step_scale_number)
  -- TODO check why this was being applied across all song patterns
  -- for _, song_pattern in pairs(program_store.song_patterns) do
    program.get_selected_song_pattern().channels[17].step_scale_number = step_scale_number
  -- end
end

function program.set_channel_step_scale_number(c, step_scale_number)
  -- TODO check why this was being applied across all song patterns
  -- for _, song_pattern in pairs(program_store.song_patterns) do
    program.get_selected_song_pattern().channels[c].step_scale_number = step_scale_number
  -- end
end

function program.get_channel_step_scale_number(c)
  return program.get_selected_song_pattern() and program.get_selected_song_pattern().channels[c] and program.get_selected_song_pattern().channels[c].step_scale_number or nil
end

function program.get()
  -- Ensure program_store is initialized
  if not program_store then
    program_store = {}
  end
  -- Ensure song_patterns exists
  if not program_store.song_patterns then
    program_store.song_patterns = {}
  end
  -- Ensure memory exists
  if not program_store.memory then
    program_store.memory = {
      channels = {},
      current_indices = {},
      original_states = {},
      pattern_states = {}
    }
  end
  return program_store
end

function program.get_selected_channel()
  return program.get_selected_song_pattern().channels[program.get().selected_channel]
end

function program.get_selected_pattern()
  return program.get_selected_song_pattern().patterns[program.get().selected_pattern]
end

function program.get_channel(song_pattern, x)
  return program.get_song_pattern(song_pattern).channels[x]
end

function program.set(p)
  program_store = model_defaults.migrate(p, device_map and device_map.get_device) or {}
  
  -- Ensure memory structure exists after loading
  if not program_store.memory then
    program_store.memory = {
      channels = {},
      current_indices = {},
      original_states = {},
      pattern_states = {}
    }
  end
  
  -- Bind history ownership to the replacement project before restoring it.
  if memory and memory.bind_project then memory.bind_project(program_store.memory) end

  -- Deserialize the memory state if it exists
  if program_store.memory.serialized then
    memory.deserialize_state(program_store.memory.serialized)
    program_store.memory = program.get().memory -- Update with deserialized state
  end
end

function program.add_step_param_trig_lock_to_channel(channel, step, parameter, trig_lock)

  if not parameter then
    return
  end

  local step_trig_lock_banks = channel.step_trig_lock_banks
  local trig_lock_params = channel.trig_lock_params

  if not step_trig_lock_banks[step] then
    step_trig_lock_banks[step] = {}
  end

  local definition = trig_lock_params[parameter]
  local off = definition.off_value == nil and -1 or definition.off_value
  if trig_lock ~= off then
    trig_lock = math.max(trig_lock, definition.nrpn_min_value or definition.cc_min_value or 0)
    trig_lock = math.min(trig_lock, definition.nrpn_max_value or definition.cc_max_value or 127)
  end

  step_trig_lock_banks[step][parameter] = trig_lock

end

function program.add_step_param_trig_lock(step, parameter, trig_lock)
  program.add_step_param_trig_lock_to_channel(program.get_selected_channel(), step, parameter, trig_lock)
end


function program.get_step_param_trig_lock(channel, step, parameter)
  local step_trig_lock_banks = channel.step_trig_lock_banks
  return step_trig_lock_banks[step] and step_trig_lock_banks[step][parameter] or nil
end

function program.step_has_param_trig_lock(channel, step)
  local step_trig_lock_banks = channel.step_trig_lock_banks
  return step_trig_lock_banks[step] ~= nil and step_trig_lock_banks[step] ~= {}
end

function program.step_has_param_slide(channel, step)
  local step_trig_lock_slides = channel.step_trig_lock_slides
  if not step_trig_lock_slides or not step_trig_lock_slides[step] then return false end
  
  for i = 1, 10 do
    if step_trig_lock_slides[step][i] then
      return true
    end
  end

  return false
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
         program.step_has_chord_4_mask(step) or
         program.step_has_param_slide(channel, step)
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
  local channel = program.get_channel(program.get().selected_song_pattern, 17)

  if trig_lock ~= nil then
    trig_lock = math.max(math.min(trig_lock, 12), -12) or nil
  end

  if not channel.step_transpose_trig_lock_banks then 
    channel.step_transpose_trig_lock_banks = {}
  end

  channel.step_transpose_trig_lock_banks[step] = trig_lock
end

function program.set_transpose(transpose)
  program.get_selected_song_pattern().transpose = transpose or 0
end

function program.set_scale_transpose(scale, transpose)
  
  local s = program.get_scale(scale)
  s.transpose = transpose
end

function program.get_transpose()
  return program.get_selected_song_pattern().transpose or 0
end

function program.get_step_transpose_trig_lock(step)
  local channel = program.get_channel(program.get().selected_song_pattern, 17)
  local step_transpose_trig_lock_banks = channel.step_transpose_trig_lock_banks
  return step_transpose_trig_lock_banks and step_transpose_trig_lock_banks[step]
end

function program.set_channel_param_slide(channel, trig_param, value)
  channel.trig_lock_slides[trig_param] = value
end

function program.toggle_channel_param_slide(channel, trig_param)
  if not channel.trig_lock_slides then
    channel.trig_lock_slides = {}
  end
  if not channel.trig_lock_slides[trig_param] then
    channel.trig_lock_slides[trig_param] = true
    return
  end
  channel.trig_lock_slides[trig_param] = not channel.trig_lock_slides[trig_param]
end

function program.get_channel_param_slide(channel, trig_param)
  if not channel.trig_lock_slides then
    channel.trig_lock_slides = {}
  end
  return channel.trig_lock_slides[trig_param]
end

function program.toggle_step_param_slide(channel, step, trig_param)
  if not channel.step_trig_lock_slides then
    channel.step_trig_lock_slides = {}
  end

  if not channel.step_trig_lock_slides[step] then
    channel.step_trig_lock_slides[step] = {}
  end

  if not channel.step_trig_lock_slides[step][trig_param] then
    channel.step_trig_lock_slides[step][trig_param] = true
    return
  end

  channel.step_trig_lock_slides[step][trig_param] = not channel.step_trig_lock_slides[step][trig_param]
end

function program.clear_step_param_slide(channel, step, trig_param)
  channel.step_trig_lock_slides[step][trig_param] = nil

  if next(channel.step_trig_lock_slides[step]) == nil then
    channel.step_trig_lock_slides[step] = nil
  end 
end

function program.get_step_param_slide(channel, step, trig_param)
  if not channel.step_trig_lock_slides then
    channel.step_trig_lock_slides = {}
  end
  return channel.step_trig_lock_slides[step] and channel.step_trig_lock_slides[step][trig_param]
end 

function program.step_transpose_has_trig_lock(step)
  if program.get_selected_channel().number ~= 17 then return false end
  local channel = program.get_channel(program.get().selected_song_pattern, 17)
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
    if channel.step_trig_lock_slides and channel.step_trig_lock_slides[step] then
      channel.step_trig_lock_slides[step] = nil
    end
  else
    program.add_step_transpose_trig_lock(step, nil)
  end
end

function program.clear_trig_lock_for_step_for_channel(channel, step, parameter)
  if channel.number ~= 17 then
    if channel.step_trig_lock_banks and channel.step_trig_lock_banks[step] and channel.step_trig_lock_banks[step][parameter] then
      channel.step_trig_lock_banks[step][parameter] = nil

      -- If step table is empty, remove it
      if next(channel.step_trig_lock_banks[step]) == nil then
        channel.step_trig_lock_banks[step] = nil
      end
      -- Clear the cleared lock's slide, even while other locks remain on the step
      -- (bugs.json undo-lock-clears-step-slide)
      if channel.step_trig_lock_slides and channel.step_trig_lock_slides[step] then
        channel.step_trig_lock_slides[step][parameter] = nil

        -- If step slide table is empty, remove it
        if next(channel.step_trig_lock_slides[step]) == nil then
          channel.step_trig_lock_slides[step] = nil
        end
      end
    end
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
      scale = musicutil.generate_scale(0, "chromatic", 20),
      pentatonic_scale = musicutil.generate_scale(0, "chromatic", 20),
      romans = {},
      root_note = 0,
      chord = 1,
      chord_degree_rotation = 0
    }
  end

  -- Backwards compatibility
  if not program.get_selected_song_pattern().scales then
    if program_store.scales then
      program.get_selected_song_pattern().scales = fn.deep_copy(program_store.scales)
    end
  end

  return program.get_selected_song_pattern().scales[s]
end

function program.set_scale(s, scale)
  scale.version = (program.get_selected_song_pattern().scales[s].version or 0) + 1
  program.get_selected_song_pattern().scales[s] = scale
end

function program.set_all_song_pattern_scales(s, scale)
  for _, song_pattern in pairs(program_store.song_patterns) do
    scale.version = (song_pattern.scales[s].version or 0) + 1
    song_pattern.scales[s] = scale
  end
end

function program.set_chord_degree_rotation_for_scale(s, rotation)
  if rotation then
    program.get_selected_song_pattern().scales[s].chord_degree_rotation = util.clamp(rotation, 0, 6)
  end
end

local function ensure_step_masks(channel)
  if not program.get_channel(program.get().selected_song_pattern, channel).step_trig_masks then
    program.get_channel(program.get().selected_song_pattern, channel).step_trig_masks = {}
  end
end


function program.get_step_trig_masks(channel)
  ensure_step_masks(channel)
  return program.get_channel(program.get().selected_song_pattern, channel).step_trig_masks
end

function program.set_step_trig_mask(channel, step, mask)
  ensure_step_masks(channel)
  program.get_channel(program.get().selected_song_pattern, channel).step_trig_masks[step] = mask
end

function program.set_trig_mask(channel, mask) 
  channel.trig_mask = mask
end

function program.get_step_note_masks(channel)
  ensure_step_masks(channel)
  return program.get_channel(program.get().selected_song_pattern, channel).step_note_masks
end

function program.set_step_note_mask(channel, step, mask)
  channel.step_note_masks[step] = mask
end

function program.set_note_mask(channel, mask) 
  channel.note_mask = mask
end

function program.get_step_velocity_masks(channel)
  ensure_step_masks(channel)
  return program.get_channel(program.get().selected_song_pattern, channel).step_velocity_masks
end

function program.set_velocity_mask(channel, mask) 
  channel.velocity_mask = mask
end

function program.get_step_length_masks(channel)
  ensure_step_masks(channel)
  return program.get_channel(program.get().selected_song_pattern, channel).step_length_masks
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
  if channel.swing_shuffle_type ~= nil and channel.swing_shuffle_type > 0 then
    return channel.swing_shuffle_type
  else
    return params:get("global_swing_shuffle_type")
  end
end

function program.get_effective_swing(channel)
  if channel.swing ~= nil and channel.swing > -51 then
    return channel.swing
  elseif params:get("global_swing_shuffle_type") == 1 then
    return params:get("global_swing")
  else
    return 0
  end
end

function program.get_effective_shuffle_feel(channel)
  if channel.shuffle_feel ~= nil and channel.shuffle_feel > 0 then
    return channel.shuffle_feel
  elseif params:get("global_swing_shuffle_type") == 2 then
    return params:get("global_shuffle_feel")
  else
    return 0
  end
end

function program.get_effective_shuffle_basis(channel)
  if channel.shuffle_basis ~= nil and channel.shuffle_basis > 0 then
    return channel.shuffle_basis
  elseif params:get("global_swing_shuffle_type") == 2 then
    return params:get("global_shuffle_basis")
  else
    return 0
  end
end

function program.get_effective_shuffle_amount(channel)
  if channel.shuffle_amount ~= nil and channel.shuffle_amount > 0 then
    return channel.shuffle_amount
  elseif params:get("global_swing_shuffle_type") == 2 then
    return params:get("global_shuffle_amount")
  else
    return 0
  end
end

function program.toggle_step_trig_mask(channel, step)
  ensure_step_masks(channel)

  local trig_values = program.get_channel(program.get().selected_song_pattern, channel).working_pattern.trig_values
  if trig_values[step] == 0 then
    program.get_channel(program.get().selected_song_pattern, channel).step_trig_masks[step] = 1
  elseif trig_values[step] == 1 then
    program.get_channel(program.get().selected_song_pattern, channel).step_trig_masks[step] = 0
  end
end

function program.clear_step_trig_mask(channel, step)
  program.get_channel(program.get().selected_song_pattern, channel).step_trig_masks[step] = nil
end

function program.clear_step_note_mask(channel, step)
  program.get_channel(program.get().selected_song_pattern, channel).step_note_masks[step] = nil
end

function program.clear_step_velocity_mask(channel, step)
  program.get_channel(program.get().selected_song_pattern, channel).step_velocity_masks[step] = nil
end

function program.clear_step_length_mask(channel, step)
  program.get_channel(program.get().selected_song_pattern, channel).step_length_masks[step] = nil
end

function program.clear_step_micro_time_mask(channel, step)
  program.get_channel(program.get().selected_song_pattern, channel).step_micro_time_masks[step] = nil
end

function program.clear_step_chord_1_mask(channel, step)
  local step_chord_masks = program.get_channel(program.get().selected_song_pattern, channel).step_chord_masks
  if step_chord_masks and step_chord_masks[step] then
    step_chord_masks[step][1] = nil
  end
end

function program.clear_step_chord_2_mask(channel, step)
  local step_chord_masks = program.get_channel(program.get().selected_song_pattern, channel).step_chord_masks
  if step_chord_masks and step_chord_masks[step] then
    step_chord_masks[step][2] = nil
  end
end

function program.clear_step_chord_3_mask(channel, step)
  local step_chord_masks = program.get_channel(program.get().selected_song_pattern, channel).step_chord_masks
  if step_chord_masks and step_chord_masks[step] then
    step_chord_masks[step][3] = nil
  end
end

function program.clear_step_chord_4_mask(channel, step)
  local step_chord_masks = program.get_channel(program.get().selected_song_pattern, channel).step_chord_masks
  if step_chord_masks and step_chord_masks[step] then
    step_chord_masks[step][4] = nil
  end
end

function program.set_step_chord_mask(channel, i, step, mask)
  local step_chord_masks = program.get_channel(program.get().selected_song_pattern, channel).step_chord_masks
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

-- Playback and slide destinations share the effective channel traversal.
function program.get_channel_step_bounds(channel)
  local first = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
  local last = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])
  last = math.min(last, first + program.get_selected_song_pattern().global_pattern_length - 1)
  return first, last
end

function program.get_next_trig_lock_step(channel, current_step, parameter, off_value)
  local banks = channel.step_trig_lock_banks
  if not banks then return nil end
  local first, last = program.get_channel_step_bounds(channel)
  if current_step < first or current_step > last then return nil end
  local wrap = params:get("wrap_param_slides") == 2 and
    (params:get("song_mode") ~= 2 or step.calculate_next_selected_song_pattern() == program.get().selected_song_pattern)
  local limit = wrap and (last - first + 1) or (last - current_step)
  for distance = 1, limit do
    local candidate = first + ((current_step - first + distance) % (last - first + 1))
    local value = banks[candidate] and banks[candidate][parameter]
    if value ~= nil and value ~= off_value and
        (program.step_has_trig(channel, candidate) or params:get("trigless_locks") == 2) then
      return {step=candidate, value=value, distance=distance,
        should_wrap=(current_step + distance > last) or nil}
    end
  end
  return nil
end

function program.get_memory()
  if not program_store.memory then
    program_store.memory = {}
  end
  return program_store.memory
end

-- Add a function to prepare the program state for saving
function program.prepare_for_save()
  -- Serialize the memory state before saving
  local current_memory = program.get().memory
  current_memory.serialized = memory.serialize_state()
  return program_store
end


function program.get_repeat_count()
  if not program_store.repeat_count then
    program_store.repeat_count = 1
  end
  return program_store.repeat_count
end

function program.set_repeat_count(count)
  program_store.repeat_count = count
end

return program

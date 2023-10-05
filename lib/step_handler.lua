local midi_controller = include("mosaic/lib/midi_controller")
local quantiser = include("mosaic/lib/quantiser")

local fn = include("mosaic/lib/functions")

local step_handler = {}
local length_tracker = {}
local persistent_channel_step_scale_numbers = {nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil}
local persistent_global_step_scale_number = nil
local persistent_step_transpose = nil

local step_scale_number = 0
local global_step_accumulator = 0

local switch_to_next_song_pattern_func = function() end
local switch_to_next_song_pattern_blink_cancel_func = function() end

function step_handler.process_stock_params(c, step, type)
  local channel = program.get_channel(c)

  for i=1,10 do

    if channel.trig_lock_params[i] and channel.trig_lock_params[i].id == type then
      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)
      if step_trig_lock then
        return step_trig_lock
      else
        return channel.trig_lock_banks[i]
      end
    end
  end

  return false
end


function step_handler.process_params(c, step)

  local channel = program.get_channel(c)
  local device = device_map.get_device(program.get().devices[channel.number].device_map)

  for i=1,10 do

    if channel.trig_lock_params[i] and (
      channel.trig_lock_params[i].id == "trig_probability" or 
      channel.trig_lock_params[i].id == "quantised_fixed_note" or
      channel.trig_lock_params[i].id == "bipolar_random_note" or
      channel.trig_lock_params[i].id == "twos_random_note" or
      channel.trig_lock_params[i].id == "random_velocity" or
      channel.trig_lock_params[i].id == "fixed_note") then
        return
    end

    if channel.trig_lock_params[i] and channel.trig_lock_params[i].type == "midi" and channel.trig_lock_params[i].cc_msb then
      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)
      local midi_channel = program.get().devices[channel.number].midi_channel

      local param_id = channel.trig_lock_params[i].param_id
      local p_value = nil
      local p = nil
      if param_id ~= nil then
        p = params:lookup_param(channel.trig_lock_params[i].param_id)
        
        if p.name ~= "undefined" then
          p_value = p.value
        end
      end

      
      if channel.trig_lock_params[i].channel then
        midi_channel = channel.trig_lock_params[i].channel
      end
      if step_trig_lock then
        midi_controller.cc(channel.trig_lock_params[i].cc_msb, channel.trig_lock_params[i].cc_lsb, step_trig_lock, midi_channel, program.get().devices[channel.number].midi_device)
      elseif p_value then
        midi_controller.cc(channel.trig_lock_params[i].cc_msb, channel.trig_lock_params[i].cc_lsb, p_value, midi_channel, program.get().devices[channel.number].midi_device)
      else
        midi_controller.cc(channel.trig_lock_params[i].cc_msb, channel.trig_lock_params[i].cc_lsb, channel.trig_lock_banks[i], midi_channel, program.get().devices[channel.number].midi_device)
      end
    elseif channel.trig_lock_params[i] and channel.trig_lock_params[i].type == "norns" and channel.trig_lock_params[i].id == "nb_slew" then
      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)

      if step_trig_lock then
        device.player:set_slew(step_trig_lock / (channel.trig_lock_params[i].quantum_modifier or 1))
      else
        device.player:set_slew(channel.trig_lock_banks[i] / (channel.trig_lock_params[i].quantum_modifier or 1))
      end
    elseif channel.trig_lock_params[i] and channel.trig_lock_params[i].type == "norns" and channel.trig_lock_params[i].id then
      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)

      if step_trig_lock then
        params:set(channel.trig_lock_params[i].id, step_trig_lock / (channel.trig_lock_params[i].quantum_modifier or 1))
      else
        params:set(channel.trig_lock_params[i].id, channel.trig_lock_banks[i] / (channel.trig_lock_params[i].quantum_modifier or 1))
      end
    end
  end
end


function step_handler.calculate_next_selected_sequencer_pattern()

  local selected_sequencer_pattern_number = program.get().selected_sequencer_pattern

  if selected_sequencer_pattern_number + 1 < 91 and program.get().sequencer_patterns[selected_sequencer_pattern_number + 1] and program.get().sequencer_patterns[selected_sequencer_pattern_number + 1].active then
    return selected_sequencer_pattern_number + 1
  end

  local last_active_previous_sequencer_pattern = selected_sequencer_pattern_number
  if last_active_previous_sequencer_pattern - 1 > 0  then

    while program.get().sequencer_patterns[last_active_previous_sequencer_pattern - 1] and program.get().sequencer_patterns[last_active_previous_sequencer_pattern - 1].active == true do
      last_active_previous_sequencer_pattern = last_active_previous_sequencer_pattern - 1
    end
  end

  return last_active_previous_sequencer_pattern

end

function step_handler.calculate_step_scale_number(c, current_step)

  local channel = program.get_channel(c)
  local channel_step_scale_number = program.get_step_scale_trig_lock(channel, current_step)

  if c == 17 then
    channel_step_scale_number = nil
    persistent_channel_step_scale_numbers[17] = nil
  end

  local global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(17), program.get_current_step_for_channel(17))
  local channel_default_scale = channel.default_scale
  local global_default_scale = program.get().default_scale

  if current_step == 1 then
    persistent_channel_step_scale_numbers[c] = nil
  end
  
  if program.get_current_step_for_channel(17) == 1 then
    persistent_global_step_scale_number = nil
    
  end

  -- Scale Precedence : channel_step_scale > global_step_scale > channel_default_scale > global_default_scale

  if channel_step_scale_number and channel_step_scale_number > 0 and program.get_scale(channel_step_scale_number).scale then
    if (params:get("quantiser_trig_lock_hold") == 1) then
      persistent_channel_step_scale_numbers[c] = channel_step_scale_number
    end
    return channel_step_scale_number
  elseif (persistent_channel_step_scale_numbers[c] and program.get_scale(persistent_channel_step_scale_numbers[c]).scale) then
    return persistent_channel_step_scale_numbers[c]
  elseif global_step_scale_number and global_step_scale_number > 0 then
    persistent_global_step_scale_number = global_step_scale_number
    return global_step_scale_number
  elseif persistent_global_step_scale_number and persistent_global_step_scale_number > 0 then
    return persistent_global_step_scale_number
  elseif channel_default_scale and channel_default_scale > 0 and program.get_scale(channel_default_scale).scale then
    return channel_default_scale
  elseif global_default_scale and global_default_scale > 0 and program.get_scale(global_default_scale).scale then
    return global_default_scale
  else
    return 0
  end

end

function step_handler.calculate_step_transpose(current_step)

  local step_transpose = program.get_step_transpose_trig_lock(current_step)
  local global_tranpose = program.get_transpose()
  local transpose = 0

  if program.get().current_step == 1 then
    persistent_step_transpose = nil
  end

  if step_transpose == nil and persistent_step_transpose ~= nil then
    transpose = persistent_step_transpose
  elseif step_transpose ~= nil then
    transpose = step_transpose
    persistent_step_transpose = step_transpose
  else
    transpose = global_tranpose
  end

  return transpose
end

function step_handler.handle(c, current_step) 

  local channel = program.get_channel(c)
  local trig_value = channel.working_pattern.trig_values[current_step]

  local note_value = channel.working_pattern.note_values[current_step]
  local velocity_value = channel.working_pattern.velocity_values[current_step]
  local length_value = channel.working_pattern.lengths[current_step]
  local midi_channel = program.get().devices[channel.number].midi_channel
  local midi_device = program.get().devices[channel.number].midi_device
  local octave_mod = channel.octave

  if program.get_step_octave_trig_lock(channel, current_step) then
    octave_mod = program.get_step_octave_trig_lock(channel, current_step)
  end

  channel.step_scale_number = step_handler.calculate_step_scale_number(c, current_step)
  
  local trig_prob = step_handler.process_stock_params(c, current_step, "trig_probability")
  if not trig_prob then trig_prob = 100 end

  local random_val = math.random(0, 99)
  local transpose = step_handler.calculate_step_transpose(current_step)

  if trig_value == 1 and random_val < trig_prob then

    channel_edit_page_ui_controller.refresh_trig_locks()
    local random_shift = fn.transform_random_value(step_handler.process_stock_params(c, current_step, "bipolar_random_note") or 0) 
    random_shift = random_shift + fn.transform_twos_random_value(step_handler.process_stock_params(c, current_step, "twos_random_note") or 0)

    local note = quantiser.process(note_value + random_shift, octave_mod, transpose, channel.step_scale_number, c)

    local velocity_random_shift = fn.transform_random_value(step_handler.process_stock_params(c, current_step, "random_velocity") or 0) 
    velocity_value = velocity_value + velocity_random_shift
    if velocity_value < 0 then velocity_value = 0 end
    if velocity_value > 127 then velocity_value = 127 end

    local quantised_fixed_note = step_handler.process_stock_params(c, current_step, "quantised_fixed_note")

    if quantised_fixed_note and quantised_fixed_note > -1 then
      note = quantiser.process(quantised_fixed_note, octave_mod, 0, channel.step_scale_number, c)
    end

    local fixed_note = step_handler.process_stock_params(c, current_step, "fixed_note")

    if fixed_note and fixed_note > -1 then
      note = fixed_note
    end

    local device = device_map.get_device(program.get().devices[channel.number].device_map)

    if not channel.mute then
      if not device.player then
        midi_controller:note_on(note, velocity_value, midi_channel, midi_device)
        table.insert(length_tracker, {note = note, velocity = velocity_value, midi_channel = midi_channel, midi_device = midi_device, steps_remaining = length_value, player = midi_controller})
      else
        device.player:note_on(note, velocity_value/127)
        table.insert(length_tracker, {note = note, velocity = velocity_value, midi_channel = midi_channel, midi_device = midi_device, steps_remaining = length_value, player = device.player})
      
      end
    end
  end

end

function step_handler.process_global_step_scale_trig_lock(current_step)

  program.get_channel(17).step_scale_number = step_handler.calculate_step_scale_number(17, current_step)
  
end


function step_handler.process_song_sequencer_patterns(step)
  local selected_sequencer_pattern_number = program.get().selected_sequencer_pattern
  local selected_sequencer_pattern = program.get().sequencer_patterns[selected_sequencer_pattern_number]

  if (global_step_accumulator % (selected_sequencer_pattern.global_pattern_length * selected_sequencer_pattern.repeats) == 0) then 
    if params:get("song_mode") == 1 then
      program.set_selected_sequencer_pattern(step_handler.calculate_next_selected_sequencer_pattern())
      global_step_accumulator = 0
      if params:get("reset_on_end_of_pattern") == 1 then
        step_handler.reset_sequencer_pattern()
      end
    end
  end

  if global_step_accumulator % selected_sequencer_pattern.global_pattern_length == 0 then
    switch_to_next_song_pattern_func()
    switch_to_next_song_pattern_blink_cancel_func()
    switch_to_next_song_pattern_func = function () end
    channel_sequencer_page_controller.refresh()
    channel_edit_page_controller.refresh()
  end

  global_step_accumulator = global_step_accumulator + 1

end


function step_handler.sinfonian_sync(step)

  local global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(17), step)
  local global_default_scale = program.get().default_scale

  local sinfonion_scale_number = 1

  if global_step_scale_number and global_step_scale_number > 0 then
    sinfonion_scale_number = global_step_scale_number
  elseif persistent_global_step_scale_number and persistent_global_step_scale_number > 0 then
    sinfonion_scale_number = persistent_global_step_scale_number
  elseif global_default_scale and global_default_scale > 0 and program.get_scale(global_default_scale).scale then
    sinfonion_scale_number = global_default_scale
  end

  local scale_container = program.get_scale(sinfonion_scale_number)
  local transpose = step_handler.calculate_step_transpose(step)
  local degree = quantiser.get_scales()[scale_container.number].sinf_degrees[scale_container.chord]
  local root = scale_container.root_note + quantiser.get_scales()[scale_container.number].sinf_root_mod
  local sinf_mode = quantiser.get_scales()[scale_container.number].sinf_mode


  -- This is a hack to get around the "feature" of the sinfonion where the fifth degree of the minor key has a flattened note
  if sinf_mode == 4 and degree == 7 then
    root = root + 3
    degree = 4
    sinf_mode = 3
  end

  if scale_container and scale_container.root_note then 
    sinfonion.set_root_note(root)
    sinfonion.set_degree_nr(degree)
    sinfonion.set_mode_nr(sinf_mode)
    sinfonion.set_transposition(transpose)

    -- Could do something with these later
    -- sinfonion.set_clock(0)
    -- sinfonion.set_beat(0)
    -- sinfonion.set_step(0)
    -- sinfonion.set_reset(0)
    -- sinfonion.set_chaotic_detune(0)
    -- sinfonion.set_harmonic_shift(0)
  end

end

function step_handler.process_lengths() 
  for i=#length_tracker, 1, -1 do
    local l = length_tracker[i]
    l.steps_remaining = l.steps_remaining - 1
    if l.steps_remaining < 1 then
      l.player:note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
      table.remove(length_tracker, i)
    end
  end
end

function step_handler.flush_lengths() 
  for i=#length_tracker, 1, -1 do
    local l = length_tracker[i]
    l.player:note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
    table.remove(length_tracker, i)
  end
end

function step_handler.queue_switch_to_next_song_pattern_func(func)
  switch_to_next_song_pattern_func = func
end

function step_handler.queue_switch_to_next_song_pattern_blink_cancel_func(func)
  switch_to_next_song_pattern_blink_cancel_func = func
end

function step_handler.execute_blink_cancel_func()
  switch_to_next_song_pattern_blink_cancel_func()
  switch_to_next_song_pattern_blink_cancel_func = function () end
end

function step_handler.reset()
  global_step_accumulator = 0
  persistent_global_step_scale_number = nil
  persistent_channel_step_scale_numbers = {nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil}
  persistent_step_transpose = nil
  step_handler.execute_blink_cancel_func()
  step_handler.flush_lengths() 
end

function step_handler.reset_sequencer_pattern() 
  for i = 1, 17 do
    program.set_current_step_for_channel(i, 1)
  end
end

return step_handler
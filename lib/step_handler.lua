local midi_controller = include("mosaic/lib/midi_controller")
local quantiser = include("mosaic/lib/quantiser")

local step_handler = {}
local length_tracker = {}
local persistent_channel_step_scale_numbers = {nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil}
local persistent_global_step_scale_number = nil

local step_scale_number = 0
local global_step_accumulator = 0

local switch_to_next_song_pattern_func = function() end
local switch_to_next_song_pattern_blink_cancel_func = function() end


local do_once = true


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

  for i=1,10 do

    if channel.trig_lock_params[i] and channel.trig_lock_params[i].type == "midi" and channel.trig_lock_params[i].cc_msb then
      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)
      local midi_channel = channel.midi_channel
      if channel.trig_lock_params[i].channel then
        midi_channel = channel.trig_lock_params[i].channel
      end
      if step_trig_lock then
        midi_controller.cc(channel.trig_lock_params[i].cc_msb, step_trig_lock, midi_channel, channel.midi_device)
      else
        midi_controller.cc(channel.trig_lock_params[i].cc_msb, channel.trig_lock_banks[i], midi_channel, channel.midi_device)
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

function step_handler.handle(c, current_step) 

  local channel = program.get_channel(c)
  local trig_value = channel.working_pattern.trig_values[current_step]

  local note_value = channel.working_pattern.note_values[current_step]
  local velocity_value = channel.working_pattern.velocity_values[current_step]
  local length_value = channel.working_pattern.lengths[current_step]
  local midi_channel = channel.midi_channel
  local midi_device = channel.midi_device
  local octave_mod = channel.octave
  

  if current_step == 1 then
    persistent_channel_step_scale_numbers[c] = nil
  end

  if program.get().current_step == 1 then
    persistent_global_step_scale_number = nil
  end

  if program.get_step_octave_trig_lock(channel, current_step) then
    octave_mod = program.get_step_octave_trig_lock(channel, current_step)
  end
  
  local channel_step_scale_number = program.get_step_scale_trig_lock(channel, current_step)

  local global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(17), program.get().current_step)

  local channel_default_scale = channel.default_scale

  local global_default_scale = program.get().default_scale

  -- Precedence : channel_step_scale > global_step_scale > channel_default_scale > global_default_scale

  if channel_step_scale_number and channel_step_scale_number > 0 and program.get_scale(channel_step_scale_number).scale then
    if (params:get("quantiser_trig_lock_hold") == 1) then
      persistent_channel_step_scale_numbers[c] = channel_step_scale_number
    end
    channel.step_scale_number = channel_step_scale_number
  elseif (persistent_channel_step_scale_numbers[c] and program.get_scale(persistent_channel_step_scale_numbers[c]).scale) then
    channel.step_scale_number = persistent_channel_step_scale_numbers[c]
  elseif global_step_scale_number and global_step_scale_number > 0 then
    persistent_global_step_scale_number = global_step_scale_number
    channel.step_scale_number = global_step_scale_number
  elseif persistent_global_step_scale_number and persistent_global_step_scale_number > 0 then
    channel.step_scale_number = persistent_global_step_scale_number
  elseif channel_default_scale and channel_default_scale > 0 and program.get_scale(channel_default_scale).scale then
    channel.step_scale_number = channel_default_scale
  elseif global_default_scale and global_default_scale > 0 and program.get_scale(global_default_scale).scale then
    channel.step_scale_number = global_default_scale
  else
    channel.step_scale_number = 0
  end

  local trig_prob = step_handler.process_stock_params(c, current_step, "trig_probability")

  if not trig_prob then trig_prob = 100 end

  local random_val = math.random(0, 99)

  if trig_value == 1 and random_val < trig_prob then
    local note = quantiser.process(note_value, octave_mod, channel.step_scale_number, c)

    channel_edit_page_ui_controller.refresh_trig_locks()

    local fixed_note = step_handler.process_stock_params(c, current_step, "fixed_note")

    if fixed_note and fixed_note > -1 then
      note = fixed_note
    end

    if not channel.mute then
      midi_controller.note_on(note, velocity_value, midi_channel, midi_device)
    end
    table.insert(length_tracker, {note = note, velocity = velocity_value, midi_channel = midi_channel, midi_device = midi_device, steps_remaining = length_value})
  end

end

function step_handler.process_global_step_scale_trig_lock(current_step)

  program.get_channel(17).step_scale_number = persistent_global_step_scale_number or program.get_step_scale_trig_lock(program.get_channel(17), current_step)
end


function step_handler.process_song_sequencer_patterns(step)
  local selected_sequencer_pattern_number = program.get().selected_sequencer_pattern
  local selected_sequencer_pattern = program.get().sequencer_patterns[selected_sequencer_pattern_number]

  if global_step_accumulator % (selected_sequencer_pattern.global_pattern_length * selected_sequencer_pattern.repeats) == 0 then 
    if params:get("song_mode") == 1 then
      program.set_selected_sequencer_pattern(step_handler.calculate_next_selected_sequencer_pattern())
      global_step_accumulator = 0
      step_handler.reset_sequencer_pattern(selected_sequencer_pattern)
    end
  end

  if global_step_accumulator % selected_sequencer_pattern.global_pattern_length == 0 then
    switch_to_next_song_pattern_func()
    switch_to_next_song_pattern_blink_cancel_func()
    switch_to_next_song_pattern_func = function () end
  end

  global_step_accumulator = global_step_accumulator + 1

  if global_step_accumulator % (selected_sequencer_pattern.global_pattern_length * selected_sequencer_pattern.repeats) == 0 then 
    if params:get("song_mode") == 1 then
      channel_sequencer_page_controller.refresh()
      channel_edit_page_controller.refresh()
    end
  end

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
  
  sinfonion.set_root_note(scale_container.root_note + quantiser.get_scales()[scale_container.number].sinf_root_mod)
  sinfonion.set_degree_nr(quantiser.get_scales()[scale_container.number].sinf_degrees[scale_container.chord])
  sinfonion.set_mode_nr(quantiser.get_scales()[scale_container.number].sinf_mode)
  sinfonion.set_transposition(0)

  -- Could do something with these later
  -- sinfonion.set_clock(0)
  -- sinfonion.set_beat(0)
  -- sinfonion.set_step(0)
  -- sinfonion.set_reset(0)
  -- sinfonion.set_chaotic_detune(0)
  -- sinfonion.set_harmonic_shift(0)

end

function step_handler.process_lengths() 
  for i=#length_tracker, 1, -1 do
    local l = length_tracker[i]
    l.steps_remaining = l.steps_remaining - 1
    if l.steps_remaining < 1 then
      midi_controller.note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
      table.remove(length_tracker, i)
    end
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
  step_handler.execute_blink_cancel_func()
end

function step_handler.reset_sequencer_pattern(pattern) 
  for i = 1, 16 do
    pattern.channels[i].current_step = 1
  end
end

return step_handler
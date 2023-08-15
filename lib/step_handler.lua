local midi_controller = include("patterning/lib/midi_controller")
local quantiser = include("patterning/lib/quantiser")

local step_handler = {}
local length_tracker = {}
local persistent_channel_step_scale_numbers = {nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil, nil}
local persistent_global_step_scale_number = nil

local step_scale_number = 0
local gobal_step_accumalator = 0

local switch_to_next_song_pattern_func = function() end
local switch_to_next_song_pattern_blink_cancel_func = function() end


local do_once = true

function step_handler.process_params(c, step)
  local channel = program.get_channel(c)

  for i=1,8 do
    step_trig_lock = program.get_step_param_trig_lock(channel, step, i)
    if channel.trig_lock_params[i] and channel.trig_lock_params[i].cc_msb then
      if step_trig_lock then
        midi_controller.cc(channel.trig_lock_params[i].cc_msb, step_trig_lock, channel.midi_channel, channel.midi_device)
      else
        midi_controller.cc(channel.trig_lock_params[i].cc_msb, channel.trig_lock_banks[i], channel.midi_channel, channel.midi_device)
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
    persistent_global_step_scale_number = nil
  end

  if program.get_step_octave_trig_lock(channel, current_step) then
    octave_mod = program.get_step_octave_trig_lock(channel, current_step)
  end
  
  local channel_step_scale_number = program.get_step_scale_trig_lock(channel, current_step)

  local global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(17), current_step)

  local channel_default_scale = channel.default_scale
  local step_scale_number = program.get().default_scale


  if channel_step_scale_number and program.get().scales[channel_step_scale_number].scale then
    if (params:get("quantiser_trig_lock_hold") == 1) then
      persistent_channel_step_scale_numbers[c] = channel_step_scale_number
    end
    step_scale_number = channel_step_scale_number
  elseif (persistent_channel_step_scale_numbers[c] and program.get().scales[persistent_channel_step_scale_numbers[c]].scale) then
    step_scale_number = persistent_channel_step_scale_numbers[c]
  elseif global_step_scale_number then
    persistent_global_step_scale_number = global_step_scale_number
    step_scale_number = global_step_scale_number
  elseif persistent_global_step_scale_number then
    step_scale_number = persistent_global_step_scale_number
  elseif
    channel_default_scale and program.get().scales[channel_default_scale].scale then
    step_scale_number = channel_default_scale
  end

  if trig_value == 1 then
    channel_edit_page_ui_controller.refresh_trig_locks()
    local note = quantiser.process(note_value, octave_mod, step_scale_number, channel)

    fixed_note_trig_lock = program.get_step_fixed_note_trig_lock(channel, current_step)

    if fixed_note_trig_lock and fixed_note_trig_lock > -1 then
      note = fixed_note_trig_lock
    elseif channel.fixed_note and channel.fixed_note > -1 then
      note = channel.fixed_note
    end

    if not channel.mute then
      midi_controller.note_on(note, velocity_value, midi_channel, midi_device)
    end
    table.insert(length_tracker, {note = note, velocity = velocity_value, midi_channel = midi_channel, midi_device = midi_device, steps_remaining = length_value})
  end

end



function step_handler.process_song_sequencer_patterns(step)
  local selected_sequencer_pattern_number = program.get().selected_sequencer_pattern
  local selected_sequencer_pattern = program.get().sequencer_patterns[selected_sequencer_pattern_number]

  if gobal_step_accumalator % (selected_sequencer_pattern.global_pattern_length * selected_sequencer_pattern.repeats) == 0 then 
    if params:get("song_mode") == 1 then

      program.set_selected_sequencer_pattern(step_handler.calculate_next_selected_sequencer_pattern())
      channel_sequencer_page_controller.refresh()
      channel_edit_page_controller.refresh()
      channel_edit_page_ui_controller.refresh()
      gobal_step_accumalator = 0
      step_handler.reset_sequencer_pattern(selected_sequencer_pattern)
    end
  end

  if gobal_step_accumalator % selected_sequencer_pattern.global_pattern_length == 0 then
    switch_to_next_song_pattern_func()
    switch_to_next_song_pattern_blink_cancel_func()
    switch_to_next_song_pattern_func = function () end
  end

  gobal_step_accumalator = gobal_step_accumalator + 1

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
  gobal_step_accumalator = 0
  step_handler.execute_blink_cancel_func()
end

function step_handler.reset_sequencer_pattern(pattern) 
  for i = 1, 16 do
    pattern.channels[i].current_step = 1
  end
end

return step_handler
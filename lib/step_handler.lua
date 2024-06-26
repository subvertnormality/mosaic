local quantiser = include("mosaic/lib/quantiser")
local clock_controller = include("mosaic/lib/clock_controller")
local fn = include("mosaic/lib/functions")

local step_handler = {}
local length_tracker = {}
local persistent_channel_step_scale_numbers = {
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil,
  nil
}
local persistent_global_step_scale_number = nil
local persistent_step_transpose = nil

local step_scale_number = 0

local switch_to_next_song_pattern_func = function()
end
local switch_to_next_song_pattern_blink_cancel_func = function()
end
local next_song_pattern_queue = nil

function step_handler.process_stock_params(c, step, type)
  local channel = program.get_channel(c)
  local trig_lock_params = channel.trig_lock_params
  local trig_lock_banks = channel.trig_lock_banks

  for i = 1, 10 do
    local param = trig_lock_params[i]
    if param and param.id == type then
      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)
      if step_trig_lock == param.off_value then
        return nil
      end
      if step_trig_lock then
        return step_trig_lock
      else
        if trig_lock_banks[i] == param.off_value then
          return nil
        end
        return trig_lock_banks[i]
      end
    end
  end

  return nil
end


function step_handler.process_params(c, step)
  local channel = program.get_channel(c)
  local device = device_map.get_device(program.get().devices[channel.number].device_map)
  local trig_lock_params = channel.trig_lock_params
  local trig_lock_banks = channel.trig_lock_banks
  local devices = program.get().devices

  for i = 1, 10 do
    local param = trig_lock_params[i]
    if param and
       (param.id ~= "trig_probability" and
        param.id ~= "quantised_fixed_note" and
        param.id ~= "bipolar_random_note" and
        param.id ~= "twos_random_note" and
        param.id ~= "random_velocity" and
        param.id ~= "fixed_note")
     then
      if param.type == "midi" and param.cc_msb then
        local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)
        local midi_channel = devices[channel.number].midi_channel

        local param_id = param.param_id
        local p_value = nil
        if param_id then
          local p = params:lookup_param(param_id)
          if p.name ~= "undefined" then
            p_value = p.value
          end
        end

        if param.channel then
          midi_channel = param.channel
        end
        if step_trig_lock then
          if step_trig_lock == param.off_value then
            break
          end
          midi_controller.cc(param.cc_msb, param.cc_lsb, step_trig_lock, midi_channel, devices[channel.number].midi_device)
        elseif p_value then
          if p_value == param.off_value then
            break
          end
          midi_controller.cc(param.cc_msb, param.cc_lsb, p_value, midi_channel, devices[channel.number].midi_device)
        else
          if trig_lock_banks[i] == param.off_value then
            break
          end
          midi_controller.cc(param.cc_msb, param.cc_lsb, trig_lock_banks[i], midi_channel, devices[channel.number].midi_device)
        end
      elseif param.type == "norns" and param.id == "nb_slew" then
        local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)

        if step_trig_lock then
          if step_trig_lock == param.off_value then
            break
          end
          device.player:set_slew(step_trig_lock / (param.quantum_modifier or 1))
        else
          device.player:set_slew(trig_lock_banks[i] / (param.quantum_modifier or 1))
        end
      elseif param.type == "norns" and param.id then
        local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)

        if step_trig_lock then

          if step_trig_lock == param.off_value then
            break
          end

          params:set(param.id, step_trig_lock / (param.quantum_modifier or 1))
        else
          params:set(param.id, trig_lock_banks[i] / (param.quantum_modifier or 1))
        end
      end
    end
  end
end


function step_handler.calculate_next_selected_sequencer_pattern()
  local program_data = program.get()  -- Store the result of program.get() in a local variable
  local selected_sequencer_pattern_number = program_data.selected_sequencer_pattern
  local sequencer_patterns = program_data.sequencer_patterns

  if next_song_pattern_queue then
    local next = next_song_pattern_queue
    next_song_pattern_queue = nil
    return next
  end

  local next_pattern_number = selected_sequencer_pattern_number + 1
  if next_pattern_number < 91 and sequencer_patterns[next_pattern_number] and sequencer_patterns[next_pattern_number].active then
    return next_pattern_number
  end

  local last_active_previous_sequencer_pattern = selected_sequencer_pattern_number
  while last_active_previous_sequencer_pattern > 1 and sequencer_patterns[last_active_previous_sequencer_pattern - 1] and sequencer_patterns[last_active_previous_sequencer_pattern - 1].active do
    last_active_previous_sequencer_pattern = last_active_previous_sequencer_pattern - 1
  end

  return last_active_previous_sequencer_pattern
end


function step_handler.calculate_step_scale_number(c, step)
  local program_data = program.get()
  local channel = program.get_channel(c)
  local channel_step_scale_number = program.get_step_scale_trig_lock(channel, step)
  local persistent_numbers = persistent_channel_step_scale_numbers

  if c == 17 then
    channel_step_scale_number = nil
    persistent_numbers[17] = nil
  end

  local current_step_17 = program.get_current_step_for_channel(17)
  local global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(17), current_step_17)
  local global_default_scale = program_data.default_scale

  local start_trig_c = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
  if step == start_trig_c then
    persistent_numbers[c] = nil
  end

  local start_trig_17 = fn.calc_grid_count(program.get_channel(17).start_trig[1], program.get_channel(17).start_trig[2])
  if current_step_17 == start_trig_17 then
    persistent_global_step_scale_number = nil
  end

  -- Scale Precedence : channel_step_scale > global_step_scale > global_default_scale
  if channel_step_scale_number and channel_step_scale_number > 0 and program.get_scale(channel_step_scale_number).scale then
    persistent_numbers[c] = channel_step_scale_number
    return channel_step_scale_number
  end

  local persistent_channel_scale = persistent_numbers[c]
  if persistent_channel_scale and program.get_scale(persistent_channel_scale).scale then
    return persistent_channel_scale
  end

  if global_step_scale_number and global_step_scale_number > 0 then
    persistent_global_step_scale_number = global_step_scale_number
    return global_step_scale_number
  end

  if persistent_global_step_scale_number and persistent_global_step_scale_number > 0 then
    return persistent_global_step_scale_number
  end

  if global_default_scale and global_default_scale > 0 and program.get_scale(global_default_scale).scale then
    return global_default_scale
  end

  return 0
end

function step_handler.manually_calculate_step_scale_number(c, step)
  local program_data = program.get()
  local channel = program.get_channel(c)
  local current_step_17 = program.get_current_step_for_channel(17)
  local global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(17), current_step_17)
  local global_default_scale = program_data.default_scale
  local clock_division_17 = clock_controller.get_channel_division(17)

  -- Calculate channel_step_scale_number
  local channel_step_scale_number = nil
  if c ~= 17 then
    for i = 1, step do
      channel_step_scale_number = program.get_step_scale_trig_lock(channel, i) or channel_step_scale_number
    end
  end

  -- Calculate global_step_scale_number for global scale steps
  local global_scale_step = math.floor(step / (clock_division_17 * 4 * 4))
  for i = 1, global_scale_step do
    global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(17), i) or global_step_scale_number
  end

  -- Scale Precedence: channel_step_scale > global_step_scale > global_default_scale
  if channel_step_scale_number and channel_step_scale_number > 0 and program.get_scale(channel_step_scale_number).scale then
    return channel_step_scale_number
  elseif global_step_scale_number and global_step_scale_number > 0 then
    return global_step_scale_number
  elseif global_default_scale and global_default_scale > 0 and program.get_scale(global_default_scale).scale then
    return global_default_scale
  else
    return 0
  end
end


function step_handler.calculate_step_transpose(current_step, c)
  local program_data = program.get()
  local step_transpose = program.get_step_transpose_trig_lock(current_step)
  local global_transpose = program.get_transpose()
  local transpose = 0
  local channel = program.get_channel(c)
  local start_trig_1, start_trig_2 = channel.start_trig[1], channel.start_trig[2]
  local current_channel_step = fn.calc_grid_count(start_trig_1, start_trig_2)
  
  if program_data.current_step == current_channel_step then
    persistent_step_transpose = nil
  end

  if step_transpose then
    if step_transpose ~= 0 then
      transpose = step_transpose
      persistent_step_transpose = step_transpose
    elseif persistent_step_transpose then
      transpose = persistent_step_transpose
    else
      transpose = global_transpose
    end
  else
    if persistent_step_transpose then
      transpose = persistent_step_transpose
    else
      transpose = global_transpose
    end
  end

  return transpose
end

local function handle_note(device, current_step, note_container, unprocessed_note_container, note_on_func)
  local c = note_container.channel
  local channel = program.get_channel(c)
  local step_chord_masks = channel.step_chord_masks[current_step]

  if not device.polyphonic then
    step_handler.flush_lengths_for_channel(c)
  end

  local chord_notes = {
    step_chord_masks and step_chord_masks[1],
    step_chord_masks and step_chord_masks[2],
    step_chord_masks and step_chord_masks[3],
    step_chord_masks and step_chord_masks[4]
  }

  local division_index = step_handler.process_stock_params(c, current_step, "chord_strum")
  local chord_velocity_mod = step_handler.process_stock_params(c, current_step, "chord_velocity_modifier")
  local chord_strum_pattern = step_handler.process_stock_params(c, current_step, "chord_strum_pattern")

  local selected_channel = program.get().selected_channel
  if not chord_strum_pattern or chord_strum_pattern == 1 or chord_strum_pattern == 3 then
    if c == selected_channel then
      channel_edit_page_ui_controller.set_current_note(note_container)
    end
    note_on_func(note_container.note, note_container.velocity, note_container.midi_channel, note_container.midi_device)
    table.insert(length_tracker, note_container)
  end

  for i, chord_note in ipairs(chord_notes) do
    if chord_note then
      if not device.polyphonic then
        step_handler.flush_lengths_for_channel(c)
      end

      local chord_number, delay_multiplier = i, i

      if chord_strum_pattern == 2 then
        chord_number = #chord_notes + 1 - i
        delay_multiplier = delay_multiplier - 1
      elseif chord_strum_pattern == 3 then
        if i % 2 == 1 then
          chord_number = (i // 2) + 1
        else
          chord_number = #chord_notes - (i // 2) + 1
        end
      elseif chord_strum_pattern == 4 then
        if i % 2 == 1 then
          chord_number = #chord_notes - (i // 2)
        else
          chord_number = (i // 2)
        end
        delay_multiplier = delay_multiplier - 1
      end

      clock_controller.delay_action(
        c,
        division_index,
        delay_multiplier,
        function()
          local note_value = unprocessed_note_container.note_value + chord_notes[chord_number]
          local processed_chord_note = quantiser.process(
            note_value,
            unprocessed_note_container.octave_mod,
            unprocessed_note_container.transpose,
            channel.step_scale_number
          )

          if unprocessed_note_container.note_mask_value and unprocessed_note_container.note_mask_value > -1 then
            processed_chord_note = quantiser.process_chord_note_for_mask(
              unprocessed_note_container.note_mask_value,
              chord_notes[chord_number],
              unprocessed_note_container.octave_mod,
              unprocessed_note_container.transpose,
              channel.step_scale_number
            )
          end

          local velocity = fn.constrain(0, 127, note_container.velocity + ((chord_velocity_mod or 0) * delay_multiplier))

          if processed_chord_note then
            note_on_func(processed_chord_note, velocity, note_container.midi_channel, note_container.midi_device)
            table.insert(length_tracker, {
              channel = c,
              steps_remaining = note_container.steps_remaining,
              player = note_container.player,
              note = processed_chord_note,
              velocity = velocity,
              midi_channel = note_container.midi_channel,
              midi_device = note_container.midi_device
            })
          end
        end
      )
    end
  end

  if chord_strum_pattern == 2 or chord_strum_pattern == 4 then
    clock_controller.delay_action(
      c,
      division_index,
      #chord_notes,
      function()
        local processed_note = quantiser.process(
          unprocessed_note_container.note_value,
          unprocessed_note_container.octave_mod,
          unprocessed_note_container.transpose,
          channel.step_scale_number
        )
        if unprocessed_note_container.note_mask_value and unprocessed_note_container.note_mask_value > -1 then
          processed_note = quantiser.process_chord_note_for_mask(
            unprocessed_note_container.note_mask_value,
            0,
            unprocessed_note_container.octave_mod,
            unprocessed_note_container.transpose,
            channel.step_scale_number
          )
        end
        if processed_note then
          local velocity = note_container.velocity + ((chord_velocity_mod or 0) * #chord_notes)
          note_on_func(processed_note, velocity, note_container.midi_channel, note_container.midi_device)
          table.insert(length_tracker, {
            channel = c,
            steps_remaining = note_container.steps_remaining,
            player = note_container.player,
            note = processed_note,
            velocity = note_container.velocity,
            midi_channel = note_container.midi_channel,
            midi_device = note_container.midi_device
          })
        end
      end
    )
  end
end

function step_handler.handle(c, current_step)
  local program_data = program.get()
  local channel = program.get_channel(c)
  local working_pattern = channel.working_pattern
  local devices = program_data.devices[channel.number]

  local trig_value = working_pattern.trig_values[current_step]
  local note_value = working_pattern.note_values[current_step]
  local note_mask_value = working_pattern.note_mask_values[current_step]
  local velocity_value = working_pattern.velocity_values[current_step]
  local length_value = working_pattern.lengths[current_step]
  local midi_channel = devices.midi_channel
  local midi_device = devices.midi_device
  local octave_mod = channel.octave

  local step_octave_trig_lock = program.get_step_octave_trig_lock(channel, current_step)
  if step_octave_trig_lock then
    octave_mod = step_octave_trig_lock
  end

  if c == 17 and current_step == fn.calc_grid_count(program.get_channel(17).start_trig[1], program.get_channel(17).start_trig[2]) then
    persistent_global_step_scale_number = nil
  end

  local trig_prob = step_handler.process_stock_params(c, current_step, "trig_probability") or 100
  local random_val = random(0, 99)

  if trig_value == 1 and random_val < trig_prob then
    if params:get("quantiser_trig_lock_hold") == 1 then
      persistent_channel_step_scale_numbers[c] = nil
    end
  end

  program.set_channel_step_scale_number(c, step_handler.calculate_step_scale_number(c, current_step))

  local transpose = step_handler.calculate_step_transpose(current_step, c)

  if trig_value == 1 and random_val < trig_prob then
    channel_edit_page_ui_controller.refresh_trig_locks()

    local random_shift = fn.transform_random_value(step_handler.process_stock_params(c, current_step, "bipolar_random_note") or 0) +
                         fn.transform_twos_random_value(step_handler.process_stock_params(c, current_step, "twos_random_note") or 0)

    local note
    if note_mask_value and note_mask_value > -1 then
      if params:get("quantiser_act_on_note_masks") == 2 then
        note = quantiser.snap_to_scale(note_mask_value + octave_mod * 12 + random_shift, channel.step_scale_number, transpose)
      else
        note = note_mask_value + octave_mod * 12 + random_shift + transpose
      end
    else
      note_value = note_value + random_shift
      local do_pentatonic = params:get("all_scales_lock_to_pentatonic") == 2 or 
                            (params:get("merged_lock_to_pentatonic") == 2 and working_pattern.merged_notes[current_step]) or
                            (params:get("random_lock_to_pentatonic") == 2 and random_shift > 0)
      note = quantiser.process(note_value, octave_mod, transpose, channel.step_scale_number, do_pentatonic)
    end

    local velocity_random_shift = fn.transform_random_value(step_handler.process_stock_params(c, current_step, "random_velocity") or 0)
    velocity_value = fn.constrain(0, 127, velocity_value + velocity_random_shift)

    local quantised_fixed_note = step_handler.process_stock_params(c, current_step, "quantised_fixed_note")
    if quantised_fixed_note and quantised_fixed_note > -1 and quantised_fixed_note <= 127 then
      note = quantiser.snap_to_scale(quantised_fixed_note, channel.step_scale_number)
    end

    local fixed_note = step_handler.process_stock_params(c, current_step, "fixed_note")
    if fixed_note and fixed_note > -1 and fixed_note <= 127 then
      note = fixed_note
    end

    local device = device_map.get_device(devices.device_map)
    if device.id == "none" then
      return
    end

    if not channel.mute then
      local note_container = {
        note = note,
        velocity = velocity_value,
        length = length_value,
        midi_channel = midi_channel,
        midi_device = midi_device,
        steps_remaining = length_value,
        player = device.player or midi_controller,
        channel = c
      }

      handle_note(
        device,
        current_step,
        note_container,
        {note_value = note_value, note_mask_value = note_mask_value, octave_mod = octave_mod, transpose = transpose},
        function(chord_note, velocity, midi_channel, midi_device)

          if device.player then
            device.player:note_on(chord_note, velocity)
          elseif midi_controller then
            midi_controller:note_on(chord_note, velocity, midi_channel, midi_device)
          end
        end
      )
    end
  end
end


function step_handler.process_global_step_scale_trig_lock(current_step)
  program.set_global_step_scale_number(step_handler.calculate_step_scale_number(17, current_step))
end


function step_handler.process_elektron_program_change(next_sequencer_pattern)
  for i = 1, 16 do
    local channel = program.get_channel(i)
    local device = device_map.get_device(program.get().devices[i].device_map)
    
    if device.id == "digitone" or 
      device.id == "digitakt" or 
      device.id == "digitakt_2" or 
      device.id == "syntakt" or 
      device.id == "analog_rytm" or 
      device.id == "analog_four" or 
      device.id == "oktatrack" or
      device.id == "analog_heat_1" or    
      device.id == "analog_heat_2" or
      device.id == "model_samples" or
      device.id == "analog_cycles" 
    then

      local midi_device = program.get().devices[1].midi_device
      local midi_channel = program.get().devices[1].midi_channel

      midi_controller:program_change(next_sequencer_pattern - 1, params:get("elektron_program_change_channel"), midi_device)

    end
  end
  
end

function step_handler.queue_next_song_pattern(s)
  next_song_pattern_queue = s
end

function step_handler.process_song_sequencer_patterns()
  local selected_sequencer_pattern_number = program.get().selected_sequencer_pattern
  local selected_sequencer_pattern = program.get().sequencer_patterns[selected_sequencer_pattern_number]
  if
    (program.get().global_step_accumulator ~= 0 and program.get().global_step_accumulator % (selected_sequencer_pattern.global_pattern_length * selected_sequencer_pattern.repeats) ==
      0)
   then
    if params:get("song_mode") == 2 then

      local next_sequencer_pattern = step_handler.calculate_next_selected_sequencer_pattern()

      program.set_selected_sequencer_pattern(next_sequencer_pattern)
      if selected_sequencer_pattern_number ~= next_sequencer_pattern and params:get("reset_on_end_of_sequencer_pattern") == 2 then
        step_handler.reset_pattern()
      else
        if params:get("reset_on_end_of_pattern") == 2 then
          step_handler.reset_pattern()
        end
      end
      pattern_controller.update_working_patterns()
    end
  end

  if program.get().global_step_accumulator % selected_sequencer_pattern.global_pattern_length == 0 then
    switch_to_next_song_pattern_func()
    switch_to_next_song_pattern_blink_cancel_func()
    switch_to_next_song_pattern_func = function()
    end
    channel_sequencer_page_controller.refresh()
    channel_edit_page_controller.refresh()
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
  local transpose = step_handler.calculate_step_transpose(step, 17)
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
function step_handler.process_lengths_for_channel(c)
  local i = #length_tracker
  while i > 0 do
    local l = length_tracker[i]
    if l.channel == c then
      l.steps_remaining = l.steps_remaining - 1
      if l.steps_remaining < 1 then
        l.player:note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
        table.remove(length_tracker, i)
      end
    end
    i = i - 1
  end
end

function step_handler.flush_lengths()
  for i = #length_tracker, 1, -1 do
    local l = length_tracker[i]
    l.player:note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
    table.remove(length_tracker, i)
  end
end

function step_handler.flush_lengths_for_channel(c)
  local i = #length_tracker
  while i > 0 do
    local l = length_tracker[i]
    if l.channel == c then
      l.player:note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
      table.remove(length_tracker, i)
    end
    i = i - 1
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
  switch_to_next_song_pattern_blink_cancel_func = function()
  end
end

function step_handler.reset()
  local channel = program.get_current
  program.get().global_step_accumulator = 0
  persistent_global_step_scale_number = nil
  persistent_channel_step_scale_numbers = {
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil,
    nil
  }
  persistent_step_transpose = nil
  step_handler.execute_blink_cancel_func()
  step_handler.flush_lengths()
  channel_edit_page_ui_controller.set_current_note({note = -1, velocity = -1, length = -1})
  local c = program.get_selected_channel().number
  program.set_channel_step_scale_number(
    c, step_handler.calculate_step_scale_number(c, 1)
  )
end

function step_handler.reset_pattern()
  for i = 1, 17 do
    program.set_current_step_for_channel(i, 99)
    program.get().global_step_accumulator = 0
  end

end

return step_handler

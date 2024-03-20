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

function step_handler.process_stock_params(c, step, type)
  local channel = program.get_channel(c)

  for i = 1, 10 do
    if channel.trig_lock_params[i] and channel.trig_lock_params[i].id == type then
      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)
      if step_trig_lock == channel.trig_lock_params[i].off_value then
        return nil
      end
      if step_trig_lock then
        return step_trig_lock
      else
        if channel.trig_lock_banks[i] == channel.trig_lock_params[i].off_value then
          return nil
        end
        return channel.trig_lock_banks[i]
      end
    end
  end

  return results
end

function step_handler.process_params(c, step)
  local channel = program.get_channel(c)
  local device = device_map.get_device(program.get().devices[channel.number].device_map)

  for i = 1, 10 do
    if
      channel.trig_lock_params[i] and
        (channel.trig_lock_params[i].id ~= "trig_probability" and
          channel.trig_lock_params[i].id ~= "quantised_fixed_note" and
          channel.trig_lock_params[i].id ~= "bipolar_random_note" and
          channel.trig_lock_params[i].id ~= "twos_random_note" and
          channel.trig_lock_params[i].id ~= "random_velocity" and
          channel.trig_lock_params[i].id ~= "fixed_note" and
          not string.match(channel.trig_lock_params[i].id or "", "^chord"))
     then
      if
        channel.trig_lock_params[i] and channel.trig_lock_params[i].type == "midi" and
          channel.trig_lock_params[i].cc_msb
       then
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
          if step_trig_lock == channel.trig_lock_params[i].off_value then
            break
          end
          midi_controller.cc(
            channel.trig_lock_params[i].cc_msb,
            channel.trig_lock_params[i].cc_lsb,
            step_trig_lock,
            midi_channel,
            program.get().devices[channel.number].midi_device
          )
        elseif p_value then
          if p_value == channel.trig_lock_params[i].off_value then
            break
          end
          midi_controller.cc(
            channel.trig_lock_params[i].cc_msb,
            channel.trig_lock_params[i].cc_lsb,
            p_value,
            midi_channel,
            program.get().devices[channel.number].midi_device
          )
        else
          if channel.trig_lock_banks[i] == channel.trig_lock_params[i].off_value then
            break
          end
          midi_controller.cc(
            channel.trig_lock_params[i].cc_msb,
            channel.trig_lock_params[i].cc_lsb,
            channel.trig_lock_banks[i],
            midi_channel,
            program.get().devices[channel.number].midi_device
          )
        end
      elseif
        channel.trig_lock_params[i] and channel.trig_lock_params[i].type == "norns" and
          channel.trig_lock_params[i].id == "nb_slew"
       then
        local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)

        if step_trig_lock == channel.trig_lock_params[i].off_value then
          break
        end

        if step_trig_lock then
          device.player:set_slew(step_trig_lock / (channel.trig_lock_params[i].quantum_modifier or 1))
        else
          device.player:set_slew(channel.trig_lock_banks[i] / (channel.trig_lock_params[i].quantum_modifier or 1))
        end
      elseif
        channel.trig_lock_params[i] and channel.trig_lock_params[i].type == "norns" and channel.trig_lock_params[i].id
       then
        local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)

        if step_trig_lock == channel.trig_lock_params[i].off_value then
          break
        end

        if step_trig_lock then
          params:set(
            channel.trig_lock_params[i].id,
            step_trig_lock / (channel.trig_lock_params[i].quantum_modifier or 1)
          )
        else
          params:set(
            channel.trig_lock_params[i].id,
            channel.trig_lock_banks[i] / (channel.trig_lock_params[i].quantum_modifier or 1)
          )
        end
      end
    end
  end
end

function step_handler.calculate_next_selected_sequencer_pattern()
  local selected_sequencer_pattern_number = program.get().selected_sequencer_pattern

  if
    selected_sequencer_pattern_number + 1 < 91 and
      program.get().sequencer_patterns[selected_sequencer_pattern_number + 1] and
      program.get().sequencer_patterns[selected_sequencer_pattern_number + 1].active
   then
    return selected_sequencer_pattern_number + 1
  end

  local last_active_previous_sequencer_pattern = selected_sequencer_pattern_number
  if last_active_previous_sequencer_pattern - 1 > 0 then
    while program.get().sequencer_patterns[last_active_previous_sequencer_pattern - 1] and
      program.get().sequencer_patterns[last_active_previous_sequencer_pattern - 1].active == true do
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

  local global_step_scale_number =
    program.get_step_scale_trig_lock(program.get_channel(17), program.get_current_step_for_channel(17))

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
    persistent_channel_step_scale_numbers[c] = channel_step_scale_number
    return channel_step_scale_number
  elseif
    (persistent_channel_step_scale_numbers[c] and program.get_scale(persistent_channel_step_scale_numbers[c]).scale)
   then
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

local function handle_note(device, current_step, note_container, unprocessed_note_container, note_on_func)
  local c = note_container.channel
  local channel = program.get_channel(c)

  if device.polyphonic == false then
    step_handler.flush_lengths_for_channel(c)
  end

  local chord_notes = {chord_note_1, chord_note_2, chord_note_3, chord_note_4}

  table.insert(chord_notes, step_handler.process_stock_params(c, current_step, "chord1"))
  table.insert(chord_notes, step_handler.process_stock_params(c, current_step, "chord2"))
  table.insert(chord_notes, step_handler.process_stock_params(c, current_step, "chord3"))
  table.insert(chord_notes, step_handler.process_stock_params(c, current_step, "chord4"))

  local division_index = step_handler.process_stock_params(c, current_step, "chord_strum")
  local chord_velocity_mod = step_handler.process_stock_params(c, current_step, "chord_velocity_modifier")

  local chord_strum_pattern = step_handler.process_stock_params(c, current_step, "chord_strum_pattern")

  local chord_start = 1
  local chord_end = #chord_notes

  if chord_strum_pattern == nil or chord_strum_pattern == 1 or chord_strum_pattern == 3 then
    note_on_func(note_container.note, note_container.velocity, note_container.midi_channel, note_container.midi_device)
    table.insert(length_tracker, note_container)
  end

  for i = 1, #chord_notes do
    if (chord_notes[i]) then
      if device.polyphonic == false then
        step_handler.flush_lengths_for_channel(c)
      end

      local chord_number = i
      local delay_multiplier = i

      if chord_strum_pattern == 2 then
        chord_number = (#chord_notes + 1) - i
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
          local processed_chord_note =
            quantiser.process(
            unprocessed_note_container.note_value + chord_notes[chord_number],
            unprocessed_note_container.octave_mod,
            unprocessed_note_container.transpose,
            channel.step_scale_number
          )

          local v = fn.constrain(0, 127, note_container.velocity + ((chord_velocity_mod or 0) * delay_multiplier))

          note_on_func(processed_chord_note, v, note_container.midi_channel, note_container.midi_device)

          table.insert(
            length_tracker,
            {
              channel = c,
              steps_remaining = note_container.steps_remaining,
              player = note_container.player,
              note = processed_chord_note,
              velocity = v,
              midi_channel = note_container.midi_channel,
              midi_device = note_container.midi_device
            }
          )
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
        local processed_note =
          quantiser.process(
          unprocessed_note_container.note_value,
          unprocessed_note_container.octave_mod,
          unprocessed_note_container.transpose,
          channel.step_scale_number
        )
        note_on_func(processed_note, note_container.velocity + ((chord_velocity_mod or 0) * #chord_notes), note_container.midi_channel, note_container.midi_device)
        table.insert(
          length_tracker,
          {
            channel = c,
            steps_remaining = note_container.steps_remaining,
            player = note_container.player,
            note = processed_note,
            velocity = note_container.velocity,
            midi_channel = note_container.midi_channel,
            midi_device = note_container.midi_device
          }
        )
      end
    )
  end
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

  local trig_prob = step_handler.process_stock_params(c, current_step, "trig_probability")
  if not trig_prob then
    trig_prob = 100
  end

  local random_val = random(0, 99)

  if trig_value == 1 and random_val < trig_prob then
    if (params:get("quantiser_trig_lock_hold") ~= 1) then
      persistent_channel_step_scale_numbers[c] = nil
    end
  end

  program.set_channel_step_scale_number(c, step_handler.calculate_step_scale_number(c, current_step))

  local transpose = step_handler.calculate_step_transpose(current_step)

  if trig_value == 1 and random_val < trig_prob then
    channel_edit_page_ui_controller.refresh_trig_locks()

    local random_shift =
      fn.transform_random_value(step_handler.process_stock_params(c, current_step, "bipolar_random_note") or 0)
    random_shift =
      random_shift +
      fn.transform_twos_random_value(step_handler.process_stock_params(c, current_step, "twos_random_note") or 0)

    note_value = note_value + random_shift

    local note = quantiser.process(note_value, octave_mod, transpose, channel.step_scale_number)

    local velocity_random_shift =
      fn.transform_random_value(step_handler.process_stock_params(c, current_step, "random_velocity") or 0)
    velocity_value = velocity_value + velocity_random_shift
    if velocity_value < 0 then
      velocity_value = 0
    end
    if velocity_value > 127 then
      velocity_value = 127
    end

    local quantised_fixed_note = step_handler.process_stock_params(c, current_step, "quantised_fixed_note")

    if quantised_fixed_note and quantised_fixed_note > -1 then
      note = quantiser.process(quantised_fixed_note, octave_mod, 0, channel.step_scale_number, c)
    end

    local fixed_note = step_handler.process_stock_params(c, current_step, "fixed_note")

    if fixed_note and fixed_note > -1 then
      note = fixed_note
    end

    local device = device_map.get_device(program.get().devices[channel.number].device_map)

    if device.id == "none" then
      return
    end

    if not channel.mute then
      if not device.player then

        local note_container = {
          note = note,
          velocity = velocity_value,
          midi_channel = midi_channel,
          midi_device = midi_device,
          steps_remaining = length_value,
          player = midi_controller,
          channel = c
        }
        handle_note(
          device,
          current_step,
          note_container,
          {note_value = note_value, octave_mod = octave_mod, transpose = transpose},
          function(chord_note, velocity, midi_channel, midi_device)
            midi_controller:note_on(chord_note, velocity, midi_channel, midi_device)
          end
        )
      else
        local note_container = {
          note = note,
          velocity = velocity_value,
          midi_channel = midi_channel,
          midi_device = midi_device,
          steps_remaining = length_value,
          player = device.player,
          channel = c
        }

        handle_note(
          device,
          current_step,
          note_container,
          {note_value = note_value, octave_mod = octave_mod, transpose = transpose},
          function(chord_note, velocity, midi_channel, midi_device)
            device.player:note_on(chord_note, velocity / 127)
          end
        )
      end
    end
  end
end

function step_handler.process_global_step_scale_trig_lock(current_step)
  program.set_global_step_scale_number(step_handler.calculate_step_scale_number(17, current_step))
end

function step_handler.process_song_sequencer_patterns()
  local selected_sequencer_pattern_number = program.get().selected_sequencer_pattern
  local selected_sequencer_pattern = program.get().sequencer_patterns[selected_sequencer_pattern_number]
  if
    (program.get().global_step_accumulator ~= 0 and program.get().global_step_accumulator % (selected_sequencer_pattern.global_pattern_length * selected_sequencer_pattern.repeats) ==
      0)
   then
    if params:get("song_mode") == 1 then

      local next_sequencer_pattern = step_handler.calculate_next_selected_sequencer_pattern()
      program.set_selected_sequencer_pattern(next_sequencer_pattern)
      if selected_sequencer_pattern_number ~= next_sequencer_pattern and params:get("reset_on_end_of_sequencer_pattern") == 1 then
        step_handler.reset_pattern()
      else
        if params:get("reset_on_end_of_pattern") == 1 then
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

function step_handler.process_lengths_for_channel(c)
  for i = #length_tracker, 1, -1 do
    local l = length_tracker[i]
    if l.channel == c then
      l.steps_remaining = l.steps_remaining - 1
      if l.steps_remaining < 1 then
        l.player:note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
        table.remove(length_tracker, i)
      end
    end
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
  for i = #length_tracker, 1, -1 do
    local l = length_tracker[i]
    if l.channel == c then
      l.player:note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
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
  switch_to_next_song_pattern_blink_cancel_func = function()
  end
end

function step_handler.reset()
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
end

function step_handler.reset_pattern()
  for i = 1, 17 do
    program.set_current_step_for_channel(i, 99)
    program.get().global_step_accumulator = 0
  end

end

return step_handler

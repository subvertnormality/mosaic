local param_slots = include("mosaic/lib/devices/param_slots")
local nrpn_codec = include("mosaic/lib/devices/nrpn_codec")
local chord_timing = include("mosaic/lib/clock/chord_timing")
local chord_order = include("mosaic/lib/musical_resolution/chord_order")
local stock_parameter = include("mosaic/lib/musical_resolution/stock_parameter")
local pitch_resolution = include("mosaic/lib/musical_resolution/pitch_resolution")
local arp_descriptor = include("mosaic/lib/musical_resolution/arp_descriptor")
local strum_descriptor = include("mosaic/lib/musical_resolution/strum_descriptor")
local quantiser = include("mosaic/lib/quantiser")
local m_clock = include("mosaic/lib/clock/m_clock")
local play_note, play_arp_note = include("mosaic/lib/clock/voice_lifetime").new(m_clock)

local divisions = include("mosaic/lib/clock/divisions")

local step = {}
local persistent_channel_step_scale_numbers = {
    nil, nil, nil, nil, nil, nil, nil, nil,
    nil, nil, nil, nil, nil, nil, nil, nil
}
local persistent_global_step_scale_number = nil
local persistent_step_transpose = nil

local arp_note = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0}

local step_scale_number = 0



local note_divisions = divisions.note_divisions

random = math.random

-- performance optimisation
local program = program
local ipairs = ipairs
local table = table
local song_transition = include("mosaic/lib/song_transition").new(program, m_clock, step)

local quantiser_process = quantiser.process
local quantiser_process_chord_note_for_mask = quantiser.process_chord_note_for_mask
local fn_constrain = fn.constrain

local resolve_pitch = pitch_resolution.new(
  quantiser.translate_note_mask_to_relative_scale_position,
  quantiser.process,
  quantiser.snap_to_scale,
  function()
    return params:get("quantiser_fully_act_on_note_masks") == 2
  end,
  function()
    return params:get("quantiser_act_on_note_masks") == 2
  end
)
local build_arp_sequence = arp_descriptor.new(chord_order.index)
local play_strum_root_now, resolve_strum_chord, resolve_strum_root_later =
  strum_descriptor.new(chord_order.index, chord_timing.delay)

function step.process_stock_params(c, step, type)
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  return stock_parameter.resolve(
    channel.trig_lock_params,
    type,
    function(i)
      return program.get_step_param_trig_lock(channel, step, i)
    end,
    function(param_id)
      return params:get(param_id)
    end,
    function()
      local stock_param_id = fn.get_param_id_from_stock_id(type, c)
      if stock_param_id then
        local param_id = string.format(stock_param_id, c)
        local param_value = params:get(param_id)
        local p = params:lookup_param(param_id)
        return param_value, function()
          return p.default
        end
      end
      return nil, nil
    end
  )
end

local function should_process_param(param)
  local skip_params = {
      "trig_probability",
      "quantised_fixed_note", 
      "bipolar_random_note",
      "twos_random_note",
      "random_velocity",
      "chord_strum",
      "chord_arp",
      "chord_velocity_modifier",
      "chord_spread",
      "chord_acceleration",
      "chord_strum_pattern",
      "fixed_note",
      "mute_root_note",
      "fully_quantise_mask"
  }
  
  if not param then return false end
  
  for _, skip_param in ipairs(skip_params) do
      if param.id == skip_param then 
          return false
      end
  end
  
  return true
end

local function process_midi_param(param, step_trig_lock, midi_channel, midi_device, mode)

  if param.nrpn_min_value and param.nrpn_max_value and param.nrpn_lsb and param.nrpn_msb then
      m_midi.nrpn(
          param.nrpn_msb,
          param.nrpn_lsb, 
          step_trig_lock or value,
          midi_channel,
          midi_device,
          mode
      )
  elseif param.cc_min_value and param.cc_max_value and param.cc_msb then
      m_midi.cc(
          param.cc_msb,
          param.cc_lsb,
          step_trig_lock or value, 
          midi_channel,
          midi_device
      )
  end
end


-- Emit the value that this eligible step will record, not a stale playback
-- lock. Repeating it also restores sound after selection or mute pauses.
function step.process_recording_params(channel)
  local data = program.get()
  if channel.mute or params:get("record") ~= 2 or data.selected_channel ~= channel.number then return end
  for i, param in ipairs(channel.trig_lock_params) do
    local dirty = recorder.trig_lock_is_dirty(channel.number, i)
    if dirty ~= nil and dirty ~= false and param.type == "midi" and param.param_id and
        (param.cc_msb ~= nil or (param.nrpn_msb ~= nil and param.nrpn_lsb ~= nil)) then
      local off = param.off_value == nil and -1 or param.off_value
      -- Off sends nothing and does not cancel a running slide (user contract).
      if dirty ~= off then
        m_clock.cancel_spread_actions_for_channel_trig_lock(channel.number, i)
        local p = params:lookup_param(param.param_id)
        assert(p and type(p.action) == "function", "Missing MIDI parameter recording action")
        p.action(dirty)
      end
    end
  end
end

function step.process_params(channel, step)
  local program_data = program.get()

  local device = device_map.get_device(program_data.devices[channel.number].device_map)
  local trig_lock_params = channel.trig_lock_params

  local value
  local devices = program_data.devices

  if channel.mute then
    return
  end 

  for i, param in ipairs(trig_lock_params) do
    local off = param.off_value == nil and -1 or param.off_value

    if should_process_param(param) then
      if not param.param_id then
        goto continue
      end

      if params:get("record") == 2 and program_data.selected_channel == channel.number and
        recorder.trig_lock_is_dirty(channel.number, i) then
        goto continue
      end

      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)

      value = params:get(trig_lock_params[i].param_id)

      local next_lock
      
      if step_trig_lock then
        next_lock = program.get_next_trig_lock_step(channel, step, i, off)
      end

      if param.type == "midi" and (param.cc_msb or param.nrpn_msb) then

        local midi_channel = param.channel or devices[channel.number].midi_channel
        local nrpn_mode
        if param.nrpn_msb ~= nil then
          nrpn_mode = param.nrpn_lsb_mode or nrpn_codec.stored_mode(program_data, channel.number, param, device)
        end

        local param_id = param.param_id
        local p_value = nil
        local p = nil
        if param_id then
          p = params:lookup_param(param_id)
          p_value = params:get(param_id)
        end

        if param.channel then
          midi_channel = param.channel
        end
        if step_trig_lock then
          if step_trig_lock == off then
            goto continue
          end

          if not m_clock.handoff_spread_lock(channel.number, i, step, step_trig_lock) then
            process_midi_param(param, step_trig_lock, midi_channel, devices[channel.number].midi_device, nrpn_mode)
          end

          if next_lock and (program.get_channel_param_slide(channel, i) or program.get_step_param_slide(channel, step, i)) then
            m_clock.execute_action_across_steps_by_pulses({
              channel_number = channel.number,
              trig_lock = i,
              start_step = step,
              end_step = next_lock.step,
              distance = next_lock.distance,
              start_value = step_trig_lock,
              end_value = next_lock.value,
              should_wrap = next_lock.should_wrap,
              quant = 1,
              func = function(value, last_value)
                if last_value ~= value then
                  process_midi_param(param, value, midi_channel, devices[channel.number].midi_device, nrpn_mode)
                end
              end
            })
          end

        elseif p_value and param.type == "midi" and (param.cc_msb or param.nrpn_msb) and not m_clock.channel_is_sliding(channel, i) then
          if p_value == off then
            goto continue
          end

          process_midi_param(param, p_value, midi_channel, devices[channel.number].midi_device, nrpn_mode)
        elseif not m_clock.channel_is_sliding(channel, i) then
          if value == off then
            goto continue
          end

          process_midi_param(param, value, midi_channel, devices[channel.number].midi_device, nrpn_mode)
        end
      elseif param.type == "norns" and param.id == "nb_slew" then

        if step_trig_lock then
          if step_trig_lock == off then
            goto continue
          end
          device.player:set_slew(step_trig_lock)
        elseif value then
          device.player:set_slew(value)
        end
      elseif param.type == "norns" and param.id then
        if step_trig_lock then

          if step_trig_lock == off then
            goto continue
          end

          if not norns_param_state_handler.get_original_param_state(channel.number, i).value then
            norns_param_state_handler.set_original_param_state(channel.number, i, value, param.id)
          end

          if not m_clock.handoff_spread_lock(channel.number, i, step, step_trig_lock) then
            params:set(param.id, step_trig_lock)
          end
          if next_lock and (program.get_channel_param_slide(channel, i) or program.get_step_param_slide(channel, step, i)) then
            m_clock.execute_action_across_steps_by_pulses({
              channel_number = channel.number,
              trig_lock = i,
              start_step = step,
              end_step = next_lock.step,
              distance = next_lock.distance,
              start_value = step_trig_lock,
              end_value = next_lock.value,
              should_wrap = next_lock.should_wrap,
              func = function(value, last_value)
                if last_value ~= value then 
                  params:set(param.id, value)
                end
              end
            })
          end
        elseif program.step_has_trig(channel, step) and not m_clock.channel_is_sliding(channel, i) then
          if norns_param_state_handler.get_original_param_state(channel.number, i) and norns_param_state_handler.get_original_param_state(channel.number, i).value then 
            params:set(param.id, norns_param_state_handler.get_original_param_state(channel.number, i).value)
            norns_param_state_handler.clear_original_param_state(channel.number, i)
          end
        end
      end
    end

    ::continue::
  end
end


step.calculate_next_selected_song_pattern = song_transition.calculate_next_selected_song_pattern

function step.calculate_step_scale_number(c, s)
  local program_data = program.get()
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local channel_step_scale_number = program.get_step_scale_trig_lock(channel, s)
  local persistent_numbers = persistent_channel_step_scale_numbers

  if c == 17 then
    channel_step_scale_number = nil
    persistent_numbers[17] = nil
  end

  local current_step_17 = program.get_current_step_for_channel(17)
  local global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(program.get().selected_song_pattern, 17), current_step_17)
  local global_default_scale = program_data.default_scale

  local start_trig_c = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
  if s == start_trig_c then
    persistent_numbers[c] = nil
  end

  local start_trig_17 = fn.calc_grid_count(program.get_channel(program.get().selected_song_pattern, 17).start_trig[1], program.get_channel(program.get().selected_song_pattern, 17).start_trig[2])
  if c == 17 and current_step_17 == start_trig_17 then
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

function step.manually_calculate_step_scale_number(c, step)
  local program_data = program.get()
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local clock_division_17 = m_clock.get_channel_division(17)
  local channel_division = m_clock.get_channel_division(c)
  
  -- Calculate the relative speed between the two sequencers
  local speed_ratio = channel_division / clock_division_17
  
  -- Calculate what step channel 17 would be on
  local global_scale_step

  if step == 1 then
    global_scale_step = 1
  elseif speed_ratio > 16 then
    global_scale_step = 1 
  else
    global_scale_step = math.ceil(step * speed_ratio)
  end
  
  local global_default_scale = program_data.default_scale      
  
  local global_step_scale_number = nil   
  for i = 1, global_scale_step do     
    global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(program.get().selected_song_pattern, 17), i) or global_step_scale_number   
  end    
  
  local channel_step_scale_number = nil   
  if c ~= 17 then     
    for i = 1, step do       
      channel_step_scale_number = program.get_step_scale_trig_lock(channel, i) or channel_step_scale_number     
    end   
  end    
  
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


function step.calculate_step_transpose(c)
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local current_scale_number = program.get_channel_step_scale_number(c)
  if not current_scale_number then
    current_scale_number = program.get_channel_step_scale_number(17)
  end
  local scale = program.get_scale(current_scale_number)
  local current_step = program.get_current_step_for_channel(c)
  local step_transpose = program.get_step_transpose_trig_lock(current_step)
  local global_transpose = program.get_transpose()
  local scale_transpose = scale.transpose or 0

  local transpose = 0
  local end_trig_1, end_trig_2 = channel.end_trig[1], channel.end_trig[2]
  local scale_channel_end_step = fn.calc_grid_count(end_trig_1, end_trig_2)
  
  if current_step and current_step % scale_channel_end_step == 1 then
    persistent_step_transpose = nil
  end

  if program.get_step_scale_trig_lock(channel, current_step) then
    persistent_step_transpose = nil
  end

  -- First determine base transpose from step/persistent/global
  if step_transpose then
    transpose = step_transpose
    persistent_step_transpose = step_transpose
  elseif persistent_step_transpose then
    transpose = persistent_step_transpose
  else
    transpose = global_transpose or 0
  end

  -- Add scale transpose to whatever base transpose was selected
  transpose = transpose + (scale_transpose or 0)

  return transpose
end



local function handle_arp(note_container, unprocessed_note_container, chord_notes, arp_division, chord_strum_pattern, chord_velocity_mod, chord_spread, chord_acceleration, mute_root, note_on_func, process_func)
  local c = note_container.channel
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local release_ids = {}
  local note_dashboard_values = {chords = {}}
  local sequenced_chord_notes = build_arp_sequence(
    chord_notes,
    chord_strum_pattern,
    mute_root,
    unprocessed_note_container.note_value,
    unprocessed_note_container.octave_mod,
    unprocessed_note_container.transpose,
    unprocessed_note_container.random_shift
  )
  if not sequenced_chord_notes then
    m_clock.cancel_arp_onsets(c)
    if c == program.get().selected_channel then
      channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
    end
    return
  end
  local total_notes = #sequenced_chord_notes
  local initial = sequenced_chord_notes[1]
  if initial then
    local note = process_func(initial.note_value, initial.octave_mod, initial.transpose, channel.step_scale_number)
    local release_id = play_arp_note(note, note_container, note_container.velocity, arp_division, note_on_func)
    if release_id then table.insert(release_ids, release_id) end
    note_dashboard_values.note = note
    note_dashboard_values.velocity = note_container.velocity
    note_dashboard_values.length = arp_division
  end
  arp_note[c] = total_notes == 1 and 1 or 2
  local number_of_executions = 1
  if c == program.get().selected_channel then
    channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
  end
  m_clock.new_arp_sprocket(c, arp_division, chord_spread, chord_acceleration, note_container.length, function(div, onset_offset)
    local velocity = fn.constrain(0, 127, note_container.velocity + ((chord_velocity_mod or 0) * number_of_executions))
    local note_to_play = sequenced_chord_notes[arp_note[c]]
    -- Every slot consumes time and acceleration, including trailing rests.
    if note_to_play then
      local note = process_func(note_to_play.note_value, note_to_play.octave_mod, note_to_play.transpose, channel.step_scale_number)
      local release_id = play_arp_note(note, note_container, velocity, arp_division, note_on_func, onset_offset)
      if release_id then table.insert(release_ids, release_id) end
      table.insert(note_dashboard_values.chords, note and fn_constrain(0, 127, note)) -- as sent (dashboard-chord-slots)
    end
    arp_note[c] = arp_note[c] % total_notes + 1
    number_of_executions = number_of_executions + 1
    if c == program.get().selected_channel then
      channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
    end
  end, release_ids)
end

local function handle_note(device, current_step, note_container, unprocessed_note_container, note_on_func)
  local c = note_container.channel
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  
  -- Check if root note should be muted
  local mute_root = step.process_stock_params(c, current_step, "mute_root_note") == 1

  -- Cache frequently accessed values
  local step_chord_masks = channel.step_chord_masks[current_step]
  local chord_one = step_chord_masks and step_chord_masks[1] or channel.chord_one_mask
  local chord_two = step_chord_masks and step_chord_masks[2] or channel.chord_two_mask
  local chord_three = step_chord_masks and step_chord_masks[3] or channel.chord_three_mask
  local chord_four = step_chord_masks and step_chord_masks[4] or channel.chord_four_mask
  local chord_notes = {chord_one, chord_two, chord_three, chord_four}
  
  -- Cache params early
  local chord_division = note_divisions[step.process_stock_params(c, current_step, "chord_strum")] 
                        and note_divisions[step.process_stock_params(c, current_step, "chord_strum")].value
  local chord_velocity_mod = step.process_stock_params(c, current_step, "chord_velocity_modifier")
  local chord_strum_pattern = step.process_stock_params(c, current_step, "chord_strum_pattern")
  local chord_spread = step.process_stock_params(c, current_step, "chord_spread") or 0
  local chord_acceleration = step.process_stock_params(c, current_step, "chord_acceleration") or 0
  local arp_division = note_divisions[step.process_stock_params(c, current_step, "chord_arp")] 
                      and note_divisions[step.process_stock_params(c, current_step, "chord_arp")].value
  
  -- Cache note processing values
  local note_value = unprocessed_note_container.note_value
  local octave_mod = unprocessed_note_container.octave_mod
  local transpose = unprocessed_note_container.transpose
  local random_shift = unprocessed_note_container.random_shift
  local step_scale_number = channel.step_scale_number
  local velocity = note_container.velocity
  local length = note_container.length

  local process_func
  if unprocessed_note_container.is_mask then
    process_func = function (note_number, octave_mod, transpose, scale_number) 
      return quantiser.process_with_mask_params(note_number, octave_mod, transpose, scale_number, unprocessed_note_container.fully_quantise_mask) 
    end
  else
    process_func = quantiser.process
  end

  if chord_spread ~= 0 then
    chord_spread = divisions.note_division_values[chord_spread]
  end

  if arp_division then
    handle_arp(note_container, unprocessed_note_container, chord_notes, arp_division, 
              chord_strum_pattern, chord_velocity_mod, chord_spread, chord_acceleration, mute_root, note_on_func, process_func)
    return
  end

  local note_dashboard_values = {}
  
  local selected_channel = program.get().selected_channel
  if play_strum_root_now(chord_strum_pattern, mute_root) then
    play_note(note_container.note, note_container, note_container.velocity, note_container.length, note_on_func)
    note_dashboard_values.note = note_container.note
    note_dashboard_values.velocity = note_container.velocity
    note_dashboard_values.length = note_container.length
    if c == program.get().selected_channel then
      channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
    end
  end


  local chord_note_dashboard_values = {}
  chord_note_dashboard_values.chords = {}

  for i = 1, 4 do
    local chord_number, delay, delay_multiplier = resolve_strum_chord(
      i,
      chord_notes,
      chord_strum_pattern,
      chord_division,
      chord_spread,
      chord_acceleration
    )
    if chord_number then
      m_clock.delay_action(
        c,
        delay,
        false,
        function()
          local note_value = unprocessed_note_container.note_value + chord_notes[chord_number] + random_shift

          local processed_chord_note = process_func(
            note_value,
            unprocessed_note_container.octave_mod,
            unprocessed_note_container.transpose,
            channel.step_scale_number
          )

          local velocity = fn.constrain(0, 127, note_container.velocity + ((chord_velocity_mod or 0) * delay_multiplier))

          if processed_chord_note then
            play_note(processed_chord_note, note_container, velocity, note_container.length, note_on_func)

            if not note_dashboard_values.chords then
              note_dashboard_values.chords = {}
            end
            -- Show the voice as sent: MIDI clamps it to 0..127 (bugs.json dashboard-chord-slots).
            chord_note_dashboard_values.chords[chord_number] = fn_constrain(0, 127, processed_chord_note)

            if c == program.get().selected_channel then
              channel_edit_page_ui.set_note_dashboard_values(chord_note_dashboard_values)
            end
          end
        end
      )

    end

  end

  local delayed_root_delay = resolve_strum_root_later(
    chord_strum_pattern,
    mute_root,
    chord_division,
    chord_spread,
    chord_acceleration
  )
  if delayed_root_delay ~= nil then
    m_clock.delay_action(
      c,
      delayed_root_delay,
      false,
      function()

        local processed_note = process_func(
          unprocessed_note_container.note_value + random_shift,
          unprocessed_note_container.octave_mod,
          unprocessed_note_container.transpose,
          channel.step_scale_number
        )

        if processed_note then
          local velocity = fn.constrain(0, 127, note_container.velocity + ((chord_velocity_mod or 0) * 4))
          play_note(processed_note, note_container, velocity, note_container.length, note_on_func)

          if c == program.get().selected_channel then
            channel_edit_page_ui.set_note_dashboard_values({
              note = processed_note,
              velocity = velocity,
              length = note_container.length
            })
          end
        end
      end
    )
  end

end

function step.handle(c, current_step)
  local program_data = program.get()
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local working_pattern = channel.working_pattern
  local devices = program_data.devices[channel.number]

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

  if c == 17 and current_step == fn.calc_grid_count(program.get_channel(program.get().selected_song_pattern, 17).start_trig[1], program.get_channel(program.get().selected_song_pattern, 17).start_trig[2]) then
    persistent_global_step_scale_number = nil
  end

  local trig_prob = (step.process_stock_params(c, current_step, "trig_probability") == -1) and 100 or (step.process_stock_params(c, current_step, "trig_probability") or 100)

  local random_outcome = true
  if trig_prob < 100 then
    random_outcome = random(0, 99) < trig_prob
  end

  if random_outcome then
    if params:get("quantiser_trig_lock_hold") == 1 then
      persistent_channel_step_scale_numbers[c] = nil
    end
  end

  program.set_channel_step_scale_number(c, step.calculate_step_scale_number(c, current_step))

  local transpose = step.calculate_step_transpose(c)

  if random_outcome then

    local random_shift = fn.transform_random_value(step.process_stock_params(c, current_step, "bipolar_random_note") or 0) +
                         fn.transform_twos_random_value(step.process_stock_params(c, current_step, "twos_random_note") or 0)
                  
    local do_pentatonic = params:get("all_scales_lock_to_pentatonic") == 2 or 
                         (params:get("merged_lock_to_pentatonic") == 2 and working_pattern.merged_notes[current_step]) or
                         (params:get("random_lock_to_pentatonic") == 2 and random_shift ~= 0)            

    local fully_quantise_mask = step.process_stock_params(c, current_step, "fully_quantise_mask")
    local note, relative_note_mask_value, octave_mod_offset, is_mask
    note, relative_note_mask_value, octave_mod_offset, is_mask, fully_quantise_mask = resolve_pitch(
      note_value,
      note_mask_value,
      octave_mod,
      transpose,
      channel.step_scale_number,
      random_shift,
      do_pentatonic,
      fully_quantise_mask
    )

    local velocity_random_shift = fn.transform_random_value(step.process_stock_params(c, current_step, "random_velocity") or 0)
    velocity_value = fn.constrain(0, 127, velocity_value + velocity_random_shift)

    local quantised_fixed_note = step.process_stock_params(c, current_step, "quantised_fixed_note")

    if not quantised_fixed_note then
      quantised_fixed_note = params:get(param_slots.control_id(channel.number, param_slots.QUANTISED_FIXED_NOTE_SLOT))
    end

    if quantised_fixed_note and quantised_fixed_note > -1 and quantised_fixed_note <= 127 then
      note = quantiser.snap_to_scale(quantised_fixed_note, channel.step_scale_number, nil, true)
    end

    local fixed_note = step.process_stock_params(c, current_step, "fixed_note")

    if not fixed_note then
      fixed_note = params:get(param_slots.control_id(channel.number, param_slots.FIXED_NOTE_SLOT))
    end

    if fixed_note and fixed_note > -1 and fixed_note <= 127 then
      note = fixed_note
    end


    local device = device_map.get_device(devices.device_map)
    if device.id == "none" then
      return
    end

    if not channel.mute and note then
      local note_container = {
        note = note,
        velocity = velocity_value,
        length = length_value,
        midi_channel = midi_channel,
        midi_device = midi_device,
        steps_remaining = length_value,
        player = device.player or m_midi,
        channel = c
      }

      handle_note(
        device,
        current_step,
        note_container,
        {note_value = relative_note_mask_value or note_value, octave_mod = octave_mod + octave_mod_offset, transpose = transpose, random_shift = random_shift, is_mask = is_mask, fully_quantise_mask = fully_quantise_mask, do_pentatonic = do_pentatonic },
        function(chord_note, velocity, midi_channel, midi_device)
          if device.player then
            device.player:note_on(chord_note, (127 > 1) and ((velocity - 1) / 126) or 0)
          elseif m_midi then
            m_midi:note_on(chord_note, velocity, midi_channel, midi_device)
          end
        end
      )
    end
  end

end

function step.process_global_step_scale_trig_lock(current_step)
  program.set_global_step_scale_number(step.calculate_step_scale_number(17, current_step))
end

step.process_elektron_program_change = song_transition.process_elektron_program_change

step.queue_next_song_pattern = song_transition.queue_next_song_pattern

step.queue_for_pattern_change = song_transition.queue_for_pattern_change

step.at_end_of_current_song_pattern = song_transition.at_end_of_current_song_pattern

step.process_song_song_patterns = song_transition.process_song_song_patterns

function step.sinfonian_sync(s)
  local global_step_scale_number = program.get_step_scale_trig_lock(program.get_channel(program.get().selected_song_pattern, 17), step)
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
  local transpose = step.calculate_step_transpose(17)
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


step.queue_switch_to_next_song_pattern_func = song_transition.queue_switch_to_next_song_pattern_func

step.queue_switch_to_next_song_pattern_blink_cancel_func = song_transition.queue_switch_to_next_song_pattern_blink_cancel_func

step.execute_blink_cancel_func = song_transition.execute_blink_cancel_func

function step.reset()
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
  arp_note = {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0}
  persistent_step_transpose = nil
  -- Stop discards song commands queued for a boundary that was never reached
  -- (arbitrated 2026-09-11, discard-on-stop); the next Play follows song mode.
  song_transition.clear_pending()
  if song_edit_page and song_edit_page.refresh_faders then song_edit_page.refresh_faders() end -- show the length that will play
  step.execute_blink_cancel_func()
  local c = program.get_selected_channel().number
  program.set_channel_step_scale_number(
    c, step.calculate_step_scale_number(c, 1)
  )
  norns_param_state_handler.flush_norns_original_param_trig_lock_store()
end

function step.reset_pattern()
  for i = 1, 17 do
    program.set_current_step_for_channel(i, 99)
    program.get().global_step_accumulator = 0
  end

end

return step


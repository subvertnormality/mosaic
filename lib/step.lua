local quantiser = include("mosaic/lib/quantiser")
local m_clock = include("mosaic/lib/clock/m_clock")

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

local switch_to_next_song_pattern_func = function() end
local switch_to_next_song_pattern_blink_cancel_func = function() end
local next_song_pattern_queue = nil
local pattern_change_queue = {}

local note_divisions = divisions.note_divisions

random = math.random

-- performance optimisation
local program = program
local ipairs = ipairs
local table = table

local quantiser_process = quantiser.process
local quantiser_process_chord_note_for_mask = quantiser.process_chord_note_for_mask
local fn_constrain = fn.constrain

function step.process_stock_params(c, step, type)
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local trig_lock_params = channel.trig_lock_params

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
            return params:get(trig_lock_params[i].param_id) or nil
          end
      end
  end

  local stock_param_id = fn.get_param_id_from_stock_id(type, c)
  if stock_param_id then
    local param_id = string.format(stock_param_id, c)
    local param_value = params:get(param_id)
    local p = params:lookup_param(param_id)
    if param_value and param_value ~= p.default then
      return param_value
    end
  end

  return nil
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

local function process_midi_param(param, step_trig_lock, midi_channel, midi_device)

  if param.nrpn_min_value and param.nrpn_max_value and param.nrpn_lsb and param.nrpn_msb then
      m_midi.nrpn(
          param.nrpn_msb,
          param.nrpn_lsb, 
          step_trig_lock or value,
          midi_channel,
          midi_device
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


function step.process_params(c, step)
  local program_data = program.get()
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  local device = device_map.get_device(program_data.devices[channel.number].device_map)
  local trig_lock_params = channel.trig_lock_params

  local value
  local devices = program_data.devices

  if channel.mute then
    return
  end 

  for i, param in ipairs(trig_lock_params) do

    if should_process_param(param) then
      if not param.param_id then
        goto continue
      end

      if params:get("record") == 2 and recorder.trig_lock_is_dirty(c, i) then
        goto continue
      end

      local step_trig_lock = program.get_step_param_trig_lock(channel, step, i)

      value = params:get(trig_lock_params[i].param_id)

      local next_lock
      
      if step_trig_lock then
        next_lock = program.get_next_trig_lock_step(channel, step, i)
      end

      if param.type == "midi" and (param.cc_msb or param.nrpn_msb) then
        local midi_channel = devices[channel.number].midi_channel

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
          if step_trig_lock == param.off_value then
            goto continue
          end

          process_midi_param(param, step_trig_lock, midi_channel, devices[channel.number].midi_device)

          if next_lock and (program.get_channel_param_slide(channel, i) or program.get_step_param_slide(channel, step, i)) then
            m_clock.cancel_spread_actions_for_channel_trig_lock(channel.number, i)
            m_clock.execute_action_across_steps_by_pulses({
              channel_number = channel.number,
              trig_lock = i,
              start_step = step,
              end_step = next_lock.step,
              start_value = step_trig_lock,
              end_value = next_lock.value,
              should_wrap = next_lock.should_wrap,
              quant = 1,
              func = function(value, last_value)
                if last_value ~= value then
                  process_midi_param(param, value, midi_channel, devices[channel.number].midi_device)
                end
              end
            })
          end

        elseif p_value and param.type == "midi" and (param.cc_msb or param.nrpn_msb) and not m_clock.channel_is_sliding(channel, i) then
          if p_value == param.off_value then
            goto continue
          end

          process_midi_param(param, p_value, midi_channel, devices[channel.number].midi_device)
        elseif not m_clock.channel_is_sliding(channel, i) then
          if value == param.off_value then
            goto continue
          end

          process_midi_param(param, value, midi_channel, devices[channel.number].midi_device)
        end
      elseif param.type == "norns" and param.id == "nb_slew" then

        if step_trig_lock then
          if step_trig_lock == param.off_value then
            goto continue
          end
          device.player:set_slew(step_trig_lock)
        elseif value then
          device.player:set_slew(value)
        end
      elseif param.type == "norns" and param.id then
        if step_trig_lock then

          if step_trig_lock == param.off_value then
            goto continue
          end

          if not norns_param_state_handler.get_original_param_state(c, i).value then
            norns_param_state_handler.set_original_param_state(c, i, value, param.id)
          end

          params:set(param.id, step_trig_lock)
          if next_lock and (program.get_channel_param_slide(channel, i) or program.get_step_param_slide(channel, step, i)) then
            m_clock.execute_action_across_steps_by_pulses({
              channel_number = channel.number,
              trig_lock = i,
              start_step = step,
              end_step = next_lock.step,
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
          if norns_param_state_handler.get_original_param_state(c, i) and norns_param_state_handler.get_original_param_state(c, i).value then 
            params:set(param.id, norns_param_state_handler.get_original_param_state(c, i).value)
            norns_param_state_handler.clear_original_param_state(c, i)
          end
        end
      end
    end

    ::continue::
  end
end


function step.calculate_next_selected_song_pattern()
  local program_data = program.get()  -- Store the result of program.get() in a local variable
  local selected_song_pattern_number = program_data.selected_song_pattern
  local song_patterns = program_data.song_patterns

  if next_song_pattern_queue then
    local next = next_song_pattern_queue
    next_song_pattern_queue = nil
    return next
  end

  local next_pattern_number = selected_song_pattern_number + 1

  if next_pattern_number < 97 and song_patterns[next_pattern_number] and song_patterns[next_pattern_number].active then
    return next_pattern_number
  end

  local last_active_previous_song_pattern = selected_song_pattern_number
  while last_active_previous_song_pattern > 1 and song_patterns[last_active_previous_song_pattern - 1] and song_patterns[last_active_previous_song_pattern - 1].active do
    last_active_previous_song_pattern = last_active_previous_song_pattern - 1
  end

  return last_active_previous_song_pattern
end


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



local function play_note_internal(note, note_container, velocity, division, note_on_func, action_flag)
  local c = note_container.channel
  local channel = program.get_channel(program.get().selected_song_pattern, c)
  
  note_on_func(note, velocity, note_container.midi_channel, note_container.midi_device)

  m_clock.delay_action(c, division, action_flag, function()
    note_container.player:note_off(note, velocity, note_container.midi_channel, note_container.midi_device)
  end)

end

-- Redefine play_note to use the helper function
local function play_note(note, note_container, velocity, division, note_on_func)
  play_note_internal(note, note_container, velocity, division, note_on_func, "must_execute")
end

-- Redefine play_arp_note to use the helper function
local function play_arp_note(note, note_container, velocity, division, note_on_func)
  play_note_internal(note, note_container, velocity, division, note_on_func, "execute_at_note_end")
end

local function get_chord_number(i, total_notes, chord_strum_pattern)
  if chord_strum_pattern == 2 then
      return total_notes + 1 - i
  end
  
  if chord_strum_pattern == 3 then
      local half_i = i // 2
      return i % 2 == 1 and (half_i + 1) or (total_notes - half_i + 1)
  end
  
  if chord_strum_pattern == 4 then
      local half_i = i // 2
      return i % 2 == 1 and (total_notes - half_i) or half_i
  end
  
  return i -- Default case (pattern 1 or nil)
end

local function handle_arp(note_container, unprocessed_note_container, chord_notes, arp_division, chord_strum_pattern, chord_velocity_mod, chord_spread, chord_acceleration, mute_root, note_on_func, process_func)
  local c = note_container.channel
  local channel = program.get_channel(program.get().selected_song_pattern, c)

  local note_dashboard_values = {}
  note_dashboard_values.chords = {}

  local sequenced_chord_notes = {}

  local acceleration_accumulator = 0
  
  for i, cn in ipairs(chord_notes) do
    local chord_note = chord_notes[get_chord_number(i, #chord_notes, chord_strum_pattern)]

    if not chord_note or chord_note == 0 then
      sequenced_chord_notes[i] = false
    else
      sequenced_chord_notes[i] = {
        note_value = unprocessed_note_container.note_value + chord_note + unprocessed_note_container.random_shift,
        octave_mod = unprocessed_note_container.octave_mod,
        transpose = unprocessed_note_container.transpose
      }
    end
  end

  -- Add root note based on strum pattern if not muted
  if not mute_root then
    if not chord_strum_pattern or chord_strum_pattern == 1 or chord_strum_pattern == 3 then

      table.insert(sequenced_chord_notes, 1, {
        note_value = unprocessed_note_container.note_value + unprocessed_note_container.random_shift,
        octave_mod = unprocessed_note_container.octave_mod,
        transpose = unprocessed_note_container.transpose
      })

    elseif chord_strum_pattern == 2 or chord_strum_pattern == 4 then
      table.insert(sequenced_chord_notes, {
        note_value = unprocessed_note_container.note_value + unprocessed_note_container.random_shift,
        octave_mod = unprocessed_note_container.octave_mod,
        transpose = unprocessed_note_container.transpose
      })
    end
  end

  -- Only play initial note if not muted
  if not mute_root then
    if sequenced_chord_notes[1] and sequenced_chord_notes[1].note_value then

      local note = process_func(
        sequenced_chord_notes[1].note_value + (sequenced_chord_notes[1].chord_note or 0),
        sequenced_chord_notes[1].octave_mod,
        sequenced_chord_notes[1].transpose,
        channel.step_scale_number
      )

      play_arp_note(note, note_container, note_container.velocity, arp_division, note_on_func)
      note_dashboard_values.note = note
      note_dashboard_values.velocity = note_container.velocity
      note_dashboard_values.length = arp_division
    end
  end

  -- Start arp from first chord note when root is muted
  arp_note[c] = mute_root and 1 or 2

  local number_of_executions = 1
  local total_notes = #sequenced_chord_notes  -- Cache the length of the processed_chord_notes table

  if c == program.get().selected_channel then
    channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
  end

  m_clock.new_arp_sprocket(c, arp_division, chord_spread, chord_acceleration, note_container.length, function(div)
    
    local velocity = fn.constrain(0, 127, note_container.velocity + ((chord_velocity_mod or 0) * number_of_executions))
    local length = div

    local note_to_play = sequenced_chord_notes[arp_note[c]]
    
    -- Function to check for a playable note later in the table
    local function check_for_later_note(start)
        local next_note = start + 1

        while next_note <= total_notes do
            local potential_note = sequenced_chord_notes[next_note] and sequenced_chord_notes[next_note].note_value
            if potential_note and potential_note ~= 0 then
                return true  -- Found a valid note
            end
            next_note = next_note + 1
        end
        
        return false  -- No valid notes found
    end

    -- Function to find the next playable note
    local function find_next_note()
        while true do
            if not note_to_play then
                -- Currently at a rest
                if check_for_later_note(arp_note[c]) then
                    return nil  -- There is a valid note later, rest now
                else
                    arp_note[c] = 1  -- Loop back to the start
                    note_to_play = sequenced_chord_notes[arp_note[c]]
                end
            else
                return note_to_play  -- Found a note to play
            end
        end
    end

    note_to_play = find_next_note()

    if note_to_play then

      local note = process_func(
        note_to_play.note_value + (note_to_play.chord_note or 0),
        note_to_play.octave_mod,
        note_to_play.transpose,
        channel.step_scale_number
      )
      play_arp_note(note, note_container, velocity, arp_division, note_on_func)
      table.insert(note_dashboard_values.chords, note)
    end

    arp_note[c] = arp_note[c] + 1

    if arp_note[c] > total_notes then
        arp_note[c] = 1
    end
    
    number_of_executions = number_of_executions + 1

    if c == program.get().selected_channel then
      channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
    end
  end)

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
  local chord_acceleration = step.process_stock_params(c, current_step, "chord_acceleration") or 1
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
  if not chord_strum_pattern or chord_strum_pattern == 1 or chord_strum_pattern == 3 then
    if not mute_root then -- Only play root note if not muted
      play_note(note_container.note, note_container, note_container.velocity, note_container.length, note_on_func)
      note_dashboard_values.note = note_container.note
      note_dashboard_values.velocity = note_container.velocity
      note_dashboard_values.length = note_container.length
      if c == program.get().selected_channel then
        channel_edit_page_ui.set_note_dashboard_values(note_dashboard_values)
      end
    end
  end

  local delay_multiplier = 0
  local acceleration_accumulator = 0

  local chord_note_dashboard_values = {}
  chord_note_dashboard_values.chords = {}

  for i, chord_note in ipairs(chord_notes) do
    if chord_note and chord_note ~= 0 then

      local chord_number, delay_multiplier = i, i

      local half_i = i // 2

      if chord_strum_pattern == 2 then
        chord_number = #chord_notes + 1 - i
        delay_multiplier = delay_multiplier - 1
      elseif chord_strum_pattern == 3 then
        if i % 2 == 1 then
          chord_number = half_i + 1
        else
          chord_number = #chord_notes - half_i + 1
        end
      elseif chord_strum_pattern == 4 then
        if i % 2 == 1 then
          chord_number = #chord_notes - half_i
        else
          chord_number = half_i
        end
        delay_multiplier = delay_multiplier - 1
      end

      

      m_clock.delay_action(
        c,
        (((chord_division or 0) * delay_multiplier) + ((chord_spread * delay_multiplier) + (acceleration_accumulator)) * chord_acceleration),
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
            chord_note_dashboard_values.chords[chord_number] = processed_chord_note

            if c == program.get().selected_channel then
              channel_edit_page_ui.set_note_dashboard_values(chord_note_dashboard_values)
            end
          end
        end
      )

      acceleration_accumulator = acceleration_accumulator + (chord_spread * delay_multiplier)

    end

  end

  if chord_strum_pattern == 2 or chord_strum_pattern == 4 then

    m_clock.delay_action(
      c,
      (((chord_division or 0) * #chord_notes) + (((chord_spread * delay_multiplier) + (acceleration_accumulator)) * chord_acceleration)),
      false,
      function()

        local processed_note = process_func(
          unprocessed_note_container.note_value + random_shift,
          unprocessed_note_container.octave_mod,
          unprocessed_note_container.transpose,
          channel.step_scale_number
        )

        if processed_note then
          local velocity = note_container.velocity + ((chord_velocity_mod or 0) * #chord_notes)
          play_note(processed_note, note_container, velocity, note_container.length, note_on_func)

          if not note_dashboard_values.chords then
            note_dashboard_values.chords = {}
          end
          table.insert(note_dashboard_values.chords, processed_note)

          if c == program.get().selected_channel then
            channel_edit_page_ui.set_note_dashboard_values(chord_note_dashboard_values)
          end
        end
      end
    )

    acceleration_accumulator = acceleration_accumulator + (chord_spread * delay_multiplier)


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
                         (params:get("random_lock_to_pentatonic") == 2 and random_shift > 0)            

    local note
    local relative_note_mask_value
    local octave_mod_offset = 0

    local is_mask = false
    local fully_quantise_mask = step.process_stock_params(c, current_step, "fully_quantise_mask")

    if note_mask_value and note_mask_value > -1 then
      is_mask = true
      fully_quantise_mask = (params:get("quantiser_fully_act_on_note_masks") == 2 and (fully_quantise_mask == -1 or fully_quantise_mask == nil)) or fully_quantise_mask == 2
      relative_note_mask_value, octave_mod_offset = quantiser.translate_note_mask_to_relative_scale_position(note_mask_value, channel.step_scale_number)

      if fully_quantise_mask then
        local final_octave = octave_mod + octave_mod_offset
        note = quantiser.process(relative_note_mask_value + random_shift, final_octave, transpose, channel.step_scale_number, do_pentatonic)
      elseif params:get("quantiser_act_on_note_masks") == 2 then
        note = quantiser.snap_to_scale(note_mask_value + octave_mod * 12 + random_shift, channel.step_scale_number, transpose)
      else
        note = note_mask_value + random_shift + octave_mod * 12
      end
    else
      local shifted_note_val = note_value + random_shift
      note = quantiser.process(shifted_note_val, octave_mod, transpose, channel.step_scale_number, do_pentatonic)
    end

    local velocity_random_shift = fn.transform_random_value(step.process_stock_params(c, current_step, "random_velocity") or 0)
    velocity_value = fn.constrain(0, 127, velocity_value + velocity_random_shift)

    local quantised_fixed_note = step.process_stock_params(c, current_step, "quantised_fixed_note")

    if not quantised_fixed_note then
      quantised_fixed_note = params:get("midi_device_params_channel_" .. channel.number .. "_3") -- TODO: fix this magic number
    end

    if quantised_fixed_note and quantised_fixed_note > -1 and quantised_fixed_note <= 127 then
      note = quantiser.snap_to_scale(quantised_fixed_note, channel.step_scale_number)
    end

    local fixed_note = step.process_stock_params(c, current_step, "fixed_note")

    if not fixed_note then
      fixed_note = params:get("midi_device_params_channel_" .. channel.number .. "_2") -- TODO: fix this magic number
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

function step.process_elektron_program_change(next_song_pattern)
  for i = 1, 16 do
    local channel = program.get_channel(program.get().selected_song_pattern, i)
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

      m_midi:program_change(next_song_pattern - 1, params:get("elektron_program_change_channel"), midi_device)

    end
  end
  
end

function step.queue_next_song_pattern(s)
  next_song_pattern_queue = s
end

function step.queue_for_pattern_change(func)
  table.insert(pattern_change_queue, func)
end

function step.process_song_song_patterns()
  local selected_song_pattern_number = program.get().selected_song_pattern
  local selected_song_pattern = program.get().song_patterns[selected_song_pattern_number]
  if
    (program.get().global_step_accumulator ~= 0 and program.get().global_step_accumulator % (selected_song_pattern.global_pattern_length * selected_song_pattern.repeats) ==
      0)
   then
    m_clock.realign_sprockets()
    
    if params:get("song_mode") == 2 then

      local next_song_pattern = step.calculate_next_selected_song_pattern()

      program.set_selected_song_pattern(next_song_pattern)
      if selected_song_pattern_number ~= next_song_pattern and params:get("reset_on_song_pattern_transition") == 2 then
        step.reset_pattern()
      else
        if params:get("reset_on_end_of_pattern_repeat") == 2 then
          step.reset_pattern()
        end
      end
      pattern.update_working_patterns()

      if selected_song_pattern_number ~= next_song_pattern then
        for channel_number = 1, 17 do
          local channel = program.get_channel(program.get().selected_song_pattern, channel_number)
          m_clock.set_channel_division(channel_number, m_clock.calculate_divisor(channel.clock_mods))
          if channel_number ~= 17 then
            channel_edit_page_ui.align_global_and_local_shuffle_feel_values(channel_number)
            channel_edit_page_ui.align_global_and_local_swing_values(channel_number)
            channel_edit_page_ui.align_global_and_local_swing_shuffle_type_values(channel_number)
            channel_edit_page_ui.align_global_and_local_shuffle_basis_values(channel_number)
            channel_edit_page_ui.align_global_and_local_shuffle_amount_values(channel_number)
          end
      
        end
      
        channel_edit_page_ui.refresh_clock_mods()
        channel_edit_page_ui.refresh_swing()
        channel_edit_page_ui.refresh_swing_shuffle_type()
        channel_edit_page_ui.refresh_shuffle_feel()
        channel_edit_page_ui.refresh_shuffle_basis()
        channel_edit_page_ui.refresh_shuffle_amount()
        song_edit_page.refresh()
        channel_edit_page.refresh()
      end
    end
  end

  if program.get().global_step_accumulator % selected_song_pattern.global_pattern_length == 0 then
    switch_to_next_song_pattern_func()
    switch_to_next_song_pattern_blink_cancel_func()
    switch_to_next_song_pattern_func = function()
    end
    for i, func in ipairs(pattern_change_queue) do
      func()
    end
    for channel_number = 1, 16 do
      channel_edit_page_ui.align_global_and_local_swing_shuffle_type_values(channel_number)
      channel_edit_page_ui.align_global_and_local_swing_values(channel_number)
      channel_edit_page_ui.align_global_and_local_shuffle_feel_values(channel_number)
      channel_edit_page_ui.align_global_and_local_shuffle_basis_values(channel_number)
      channel_edit_page_ui.align_global_and_local_shuffle_amount_values(channel_number)
    end
    pattern_change_queue = {}
  end

end

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


function step.queue_switch_to_next_song_pattern_func(func)
  switch_to_next_song_pattern_func = func
end

function step.queue_switch_to_next_song_pattern_blink_cancel_func(func)
  switch_to_next_song_pattern_blink_cancel_func = func
end

function step.execute_blink_cancel_func()
  switch_to_next_song_pattern_blink_cancel_func()
  switch_to_next_song_pattern_blink_cancel_func = function()
  end
end

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


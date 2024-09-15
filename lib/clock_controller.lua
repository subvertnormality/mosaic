local fn = include("mosaic/lib/functions")
local lattice = include("mosaic/lib/mosaic_lattice")

clock_controller = {}
clock_lattice = {}

local playing = false
local first_run = true
local master_clock
local sinfonion_clock
local trigless_lock_active = {}

local delayed_sprockets = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}
local delayed_sprockets_must_execute = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}
local arp_delay_sprockets = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}
local arp_sprockets = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}

local clock_divisions = include("mosaic/lib/divisions").clock_divisions

function clock_controller.calculate_divisor(clock_mod)
  if clock_mod.type == "clock_multiplication" then
    return 4 * clock_mod.value
  elseif clock_mod.type == "clock_division" then
    return 4 / clock_mod.value
  else
    return 4
  end
end

local function destroy_delay_sprockets()
  for i, sprocket_table in ipairs(delayed_sprockets) do
    for j, item in ipairs(sprocket_table) do
      if item then
        item:destroy()
      end
    end
  end
end

local function get_shuffle_values(channel)
  local shuffle_values = {}

  local swing_value = params:get("global_swing")
  if channel.swing ~= -51 then
    swing_value = channel.swing
  end
  if channel.number == 17 then
    swing_value = 0
  end
  shuffle_values.swing = swing_value

  local swing_or_shuffle_value = params:get("global_swing_shuffle_type")
  if channel.swing_shuffle_type and channel.swing_shuffle_type > 1 then
    swing_or_shuffle_value = channel.swing_shuffle_type - 1
  end
  if channel.number == 17 then
    swing_or_shuffle_value = 1
  end

  shuffle_values.swing_or_shuffle = swing_or_shuffle_value

  local shuffle_basis_value = params:get("global_shuffle_basis")
  if channel.shuffle_basis and channel.shuffle_basis > 1 then
    shuffle_basis_value = channel.shuffle_basis - 1
  end
  if channel.number == 17 then
    shuffle_basis_value = 0
  end

  shuffle_values.shuffle_basis = shuffle_basis_value

  local shuffle_feel_value = params:get("global_shuffle_feel")
  if channel.shuffle_feel and channel.shuffle_feel > 1 then
    shuffle_feel_value = channel.shuffle_feel - 1
  end
  if channel.number == 17 then
    shuffle_feel_value = 0
  end

  shuffle_values.shuffle_feel = shuffle_feel_value

  return shuffle_values
  
end

function clock_controller.init()
  local program_data = program.get()
  clock_lattice = lattice:new()

  if testing then
    clock_lattice.auto = false
  end

  destroy_delay_sprockets()
  delayed_sprockets = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}

  local midi_clock_init = nil

  midi_clock_init = clock_lattice:new_sprocket {
    action = function(t)
      midi_controller.start()
      midi_clock_init:destroy()
    end,
    division = 0,
    swing = 0,
    order = 4,
    delay = 0,
    swing_or_shuffle = 1,
    shuffle_basis = 0,
    shuffle_feel = 0,
    enabled = true
  }

  master_clock =
    clock_lattice:new_sprocket {
      action = function(t)


        local selected_sequencer_pattern = program_data.sequencer_patterns[program_data.selected_sequencer_pattern]
        if params:get("elektron_program_changes") == 2 and program_data.current_step == selected_sequencer_pattern.global_pattern_length - 1 then
          step_handler.process_elektron_program_change(step_handler.calculate_next_selected_sequencer_pattern())
        end
        if first_run ~= true then
          step_handler.process_song_sequencer_patterns(program_data.current_step)
          local selected_sequencer_pattern = program_data.sequencer_patterns[program_data.selected_sequencer_pattern]
          if program_data.global_step_accumulator % selected_sequencer_pattern.global_pattern_length == 0 then
            for i = 1, 17 do
              local channel = program.get_channel(i)
              if (fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2]) - fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2]) + 1) > selected_sequencer_pattern.global_pattern_length then
                program.set_current_step_for_channel(i, 99)
              end
            end
          end
        end

        program_data.current_step = program_data.current_step + 1
        program_data.global_step_accumulator = program_data.global_step_accumulator + 1

        if program_data.current_step > program.get_selected_sequencer_pattern().global_pattern_length then
          program_data.current_step = 1
          first_run = false
        end
      end,
      division = 1 / 16,
      swing = 0,
      swing_or_shuffle = 1,
      shuffle_basis = 0,
      shuffle_feel = 0,
      order = 1,
      enabled = true
    }

  for channel_number = 17, 1, -1 do
    local channel = program.get_channel(channel_number)
    local div = clock_controller.calculate_divisor(channel.clock_mods)


    local sprocket_action = function(t)
      local current_step = program.get_current_step_for_channel(channel_number)

      local start_trig = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
      local end_trig = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])

      if current_step < start_trig then
        program.set_current_step_for_channel(channel_number, start_trig)
        current_step = start_trig
      end

      if not clock_controller["channel_" .. channel_number .. "_clock"].first_run then
        program.set_current_step_for_channel(channel_number, current_step + 1)
        current_step = current_step + 1
      end

      if program.get_current_step_for_channel(channel_number) > end_trig then
        program.set_current_step_for_channel(channel_number, start_trig)
        current_step = start_trig
      end

      if channel_number == 17 then
        step_handler.process_global_step_scale_trig_lock(current_step)
        step_handler.sinfonian_sync(current_step)
      else
        step_handler.handle(channel_number, current_step)
      end

      clock_controller["channel_" .. channel_number .. "_clock"].first_run = false
      clock_controller["channel_" .. channel_number .. "_clock"].next_step = current_step

      if program_data.selected_channel == channel_number and program_data.selected_page == program.get_pages().channel_edit_page then
        fn.dirty_grid(true)
      end
    end

    local end_of_clock_action = function(t)
      if channel_number ~= 17 then
        local step = program.get_current_step_for_channel(channel_number) + 1
        if step < 1 then return end

        local start_trig = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
        local end_trig = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])

        if step > end_trig then
          step = start_trig
        end

        local next_trig_value = channel.working_pattern.trig_values[step]
        if next_trig_value == 1 then
          trigless_lock_active[channel_number] = false
          step_handler.process_params(channel_number, step)
        elseif params:get("trigless_locks") == 2 and not trigless_lock_active[channel_number] and program.step_has_param_trig_lock(channel, step) then
          trigless_lock_active[channel_number] = true
          step_handler.process_params(channel_number, step)
        end

      end
    end

    local shuffle_values = get_shuffle_values(channel)

    clock_controller["channel_" .. channel_number .. "_clock"] = clock_lattice:new_sprocket {
      action = sprocket_action,
      division = 1 / (div * 4),
      swing = shuffle_values.swing,
      swing_or_shuffle = shuffle_values.swing_or_shuffle,
      shuffle_basis = shuffle_values.shuffle_basis,
      shuffle_feel = shuffle_values.shuffle_feel,
      enabled = true
    }

    clock_controller["channel_" .. channel_number .. "_clock"].end_of_clock_processor = clock_lattice:new_sprocket {
      action = end_of_clock_action,
      division = 1 / (div * 4),
      swing = shuffle_values.swing,
      swing_or_shuffle = shuffle_values.swing_or_shuffle,
      shuffle_basis = shuffle_values.shuffle_basis,
      shuffle_feel = shuffle_values.shuffle_feel,
      delay = 0.95,
      enabled = true
    }

    clock_controller["channel_" .. channel_number .. "_clock"].first_run = true
  end
end

function clock_controller.set_swing_shuffle_type(channel_number, swing_or_shuffle)
  local clock = clock_controller["channel_" .. channel_number .. "_clock"]
  clock:set_swing_or_shuffle(swing_or_shuffle - 1)
  clock.end_of_clock_processor:set_swing_or_shuffle(swing_or_shuffle - 1)
end

function clock_controller.set_channel_swing(channel_number, swing)
  local clock = clock_controller["channel_" .. channel_number .. "_clock"]
  clock:set_swing(swing)
  clock.end_of_clock_processor:set_swing(swing)
end

function clock_controller.set_channel_shuffle_feel(channel_number, shuffle_feel)
  local clock = clock_controller["channel_" .. channel_number .. "_clock"]
  clock:set_shuffle_feel(shuffle_feel - 1)
  clock.end_of_clock_processor:set_shuffle_feel(shuffle_feel - 1)
end

function clock_controller.set_channel_shuffle_basis(channel_number, shuffle_basis)
  local clock = clock_controller["channel_" .. channel_number .. "_clock"]
  clock:set_shuffle_basis(shuffle_basis - 1)
  clock.end_of_clock_processor:set_shuffle_basis(shuffle_basis - 1)
end

function clock_controller.set_channel_division(channel_number, division)
  local clock = clock_controller["channel_" .. channel_number .. "_clock"]
  local div_value = 1 / (division * 4)
  clock:set_division(div_value)
  clock.end_of_clock_processor:set_division(div_value)
end

function clock_controller.get_channel_division(channel_number)
  local clock = clock_controller["channel_" .. channel_number .. "_clock"]
  return clock and clock.division or 0.4
end



local function meta_delay_action(c, division, delay, type, func)

  local channel = program.get_channel(c)
  local delayed

  local sprocket_action = function(t)
    func()
    delayed:destroy()
  end

  local shuffle_values = get_shuffle_values(channel)

  delayed = clock_lattice:new_sprocket {
    action = sprocket_action,
    division = division,
    enabled = true,
    delay = delay,
    swing = shuffle_values.swing,
    swing_or_shuffle = shuffle_values.swing_or_shuffle,
    shuffle_basis = shuffle_values.shuffle_basis,
    shuffle_feel = shuffle_values.shuffle_feel,
    delay_offset = -2
  }


  if type == "must_execute" then
    table.insert(delayed_sprockets_must_execute[c], delayed)
  elseif type == "destroy_at_note_end" then
    table.insert(arp_delay_sprockets[c], delayed)
  else
    table.insert(delayed_sprockets[c], delayed)
  end
end

function clock_controller.delay_action(c, note_division, multiplier, acceleration, delay, type, func)
  if note_division == 0 or note_division == nil then
    func()
    return
  end
  local channel = program.get_channel(c)
  local delayed

  local division = clock_controller["channel_" .. c .. "_clock"].division
  local ppqn = clock_lattice.ppqn  -- Pulses per quarter note
  
  local note_division_mod = ((note_division * multiplier) + acceleration) * division
  -- local division = ((note_division * multiplier) + acceleration) * clock_controller["channel_" .. c .. "_clock"].division

  local count = division
  local sprocket_action = function(t)
    count = count + division
    if count > note_division_mod then
      if (delay == 0) then
        func()
      else
        if note_division_mod < division then
          meta_delay_action(c, note_division_mod, delay, type, func)
        else
          meta_delay_action(c, division + (note_division_mod - (count - division)), delay, type, func)
        end
      end
      delayed:destroy()
    end
  end

  local shuffle_values = get_shuffle_values(channel)

  delayed = clock_lattice:new_sprocket {
    action = sprocket_action,
    division = division,
    enabled = true,
    delay = 0,
    swing = shuffle_values.swing,
    swing_or_shuffle = shuffle_values.swing_or_shuffle,
    shuffle_basis = shuffle_values.shuffle_basis,
    shuffle_feel = shuffle_values.shuffle_feel,
  }

end

function clock_controller.new_arp_sprocket(c, division, chord_spread, chord_acceleration, length, func)
  if division == 0 or division == nil then
    return
  end

  local channel = program.get_channel(c)

  if (arp_sprockets[c]) then
    for i, sprocket in ipairs(arp_sprockets[c]) do
      sprocket:destroy()
    end
  end

  local arp
  local runs = 1
  local total_runs = length / division
  local acceleration_accumulator = 0

  local sprocket_action = function(div)
    func(div)
    if length == 0 then
      arp:destroy()
    end
  end
  local shuffle_values = get_shuffle_values(channel)
  arp = clock_lattice:new_sprocket {
    action = function()
      
      runs = runs + 1
      local div = (division + ((chord_spread * chord_acceleration * (runs - 1))) + (acceleration_accumulator * chord_acceleration))

      sprocket_action(div)

      if div <= 0 then

        arp:destroy()
        clock_controller.kill_arp_delay_sprockets(c)
      end

      arp:set_division(div * clock_controller["channel_" .. c .. "_clock"].division)

    end,
    division = (division + (chord_spread * chord_acceleration)) * clock_controller["channel_" .. c .. "_clock"].division,
    enabled = true,
    swing = shuffle_values.swing,
    swing_or_shuffle = shuffle_values.swing_or_shuffle,
    shuffle_basis = shuffle_values.shuffle_basis,
    shuffle_feel = shuffle_values.shuffle_feel,
    delay = division + chord_spread
  }

  acceleration_accumulator = acceleration_accumulator + chord_spread

  clock_controller.delay_action(c, length, 1, 0, 0.95, "must_execute", function()
    arp:destroy()
    clock_controller.kill_arp_delay_sprockets(c)
  end)

  table.insert(arp_sprockets[c], arp)
end


local function execute_delayed_sprockets()
  for i, sprocket_table in ipairs(delayed_sprockets_must_execute) do
    for j, item in ipairs(sprocket_table) do
      if item then
        item:action()
      end
    end
  end
end

function clock_controller.kill_arp_delay_sprockets(c)
  for i, item in ipairs(arp_delay_sprockets[c]) do
    if item then
      item:destroy()
    end
  end
end

function clock_controller:start()
  first_run = true
  if params:get("elektron_program_changes") == 2 then
    step_handler.process_elektron_program_change(program.get().selected_sequencer_pattern)
  end

  clock_controller.set_playing()

  for i = 1, 16 do
    step_handler.process_params(i, 1)
  end

  clock_lattice:start()
       
end

function clock_controller:stop()
  if clock_lattice and clock_lattice.stop then
    clock_lattice:stop()
  end

  execute_delayed_sprockets()

  playing = false
  first_run = true
  nb:stop_all()
  midi_controller:stop()
  clock_controller.reset()
end

function clock_controller.is_playing()
  return playing
end

function clock_controller.set_playing()
  playing = true
end

function clock_controller.reset()
  local program_data = program.get()
  for _, pattern in ipairs(program_data.sequencer_patterns) do
    for i = 1, 17 do
      program.set_current_step_for_channel(i, 1)
    end
  end

  program_data.current_step = 1
  step_handler.reset()

  if clock_lattice and clock_lattice.destroy then
    clock_lattice:destroy()
  end

  clock_controller.init()
end

function clock_controller.panic()
  midi_controller.panic()
end

function clock_controller.get_clock_divisions()
  return clock_divisions
end

function clock_controller.get_clock_lattice()
  return clock_lattice
end

return clock_controller

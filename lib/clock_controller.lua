local fn = include("mosaic/lib/functions")
local lattice = require("lattice")

clock_controller = {}
clock_lattice = {}

local playing = false
local first_run = true
local master_clock
local sinfonion_clock
local trigless_lock_active = {}

local delayed_sprockets = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}
local delayed_sprockets_must_execute = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}
local arp_sprockets = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}

local clock_divisions = {
  {name = "x16", value = 16, type = "clock_multiplication"},
  {name = "x12", value = 12, type = "clock_multiplication"},
  {name = "x8", value = 8, type = "clock_multiplication"},
  {name = "x6", value = 6, type = "clock_multiplication"},
  {name = "x5.3", value = 5.3, type = "clock_multiplication"},
  {name = "x5", value = 5, type = "clock_multiplication"},
  {name = "x4", value = 4, type = "clock_multiplication"},
  {name = "x3", value = 3, type = "clock_multiplication"},
  {name = "x2.6", value = 2.6, type = "clock_multiplication"},
  {name = "x2", value = 2, type = "clock_multiplication"},
  {name = "x1.5", value = 1.5, type = "clock_multiplication"},
  {name = "x1.3", value = 1.3, type = "clock_multiplication"},
  {name = "/1", value = 1, type = "clock_division"},
  {name = "/1.5", value = 1.5, type = "clock_division"},
  {name = "/2", value = 2, type = "clock_division"},
  {name = "/2.6", value = 2.6, type = "clock_division"},
  {name = "/3", value = 3, type = "clock_division"},
  {name = "/4", value = 4, type = "clock_division"},
  {name = "/5", value = 5, type = "clock_division"},
  {name = "/5.3", value = 5.3, type = "clock_division"},
  {name = "/6", value = 6, type = "clock_division"},
  {name = "/7", value = 7, type = "clock_division"},
  {name = "/8", value = 8, type = "clock_division"},
  {name = "/9", value = 9, type = "clock_division"},
  {name = "/10", value = 10, type = "clock_division"},
  {name = "/11", value = 11, type = "clock_division"},
  {name = "/12", value = 12, type = "clock_division"},
  {name = "/13", value = 13, type = "clock_division"},
  {name = "/14", value = 14, type = "clock_division"},
  {name = "/15", value = 15, type = "clock_division"},
  {name = "/16", value = 16, type = "clock_division"},
  {name = "/17", value = 17, type = "clock_division"},
  {name = "/19", value = 19, type = "clock_division"},
  {name = "/21", value = 21, type = "clock_division"},
  {name = "/23", value = 23, type = "clock_division"},
  {name = "/24", value = 24, type = "clock_division"},
  {name = "/25", value = 25, type = "clock_division"},
  {name = "/27", value = 27, type = "clock_division"},
  {name = "/29", value = 29, type = "clock_division"},
  {name = "/32", value = 32, type = "clock_division"},
  {name = "/40", value = 40, type = "clock_division"},
  {name = "/48", value = 48, type = "clock_division"},
  {name = "/56", value = 56, type = "clock_division"},
  {name = "/64", value = 64, type = "clock_division"},
  {name = "/96", value = 96, type = "clock_division"},
  {name = "/101", value = 101, type = "clock_division"},
  {name = "/128", value = 128, type = "clock_division"},
  {name = "/192", value = 192, type = "clock_division"},
  {name = "/256", value = 256, type = "clock_division"},
  {name = "/384", value = 384, type = "clock_division"},
  {name = "/512", value = 512, type = "clock_division"}
}

local note_divisions = {
  {name = "1/32", value = 1/32, type = "clock_division"},
  {name = "1/28", value = 1/28, type = "clock_division"},
  {name = "1/24", value = 1/24, type = "clock_division"},
  {name = "1/20", value = 1/20, type = "clock_division"},
  {name = "1/16", value = 1/16, type = "clock_division"},
  {name = "1/15", value = 1/15, type = "clock_division"},
  {name = "1/14", value = 1/14, type = "clock_division"},
  {name = "1/13", value = 1/13, type = "clock_division"},
  {name = "1/12", value = 1/12, type = "clock_division"},
  {name = "1/11", value = 1/11, type = "clock_division"},
  {name = "1/10", value = 1/10, type = "clock_division"},
  {name = "1/9", value = 1/9, type = "clock_division"},
  {name = "1/8", value = 1/8, type = "clock_division"},
  {name = "1/7", value = 1/7, type = "clock_division"},
  {name = "1/6", value = 1/6, type = "clock_division"},
  {name = "1/5", value = 1/5, type = "clock_division"},
  {name = "1/4", value = 1/4, type = "clock_division"},
  {name = "1/3", value = 1/3, type = "clock_division"},
  {name = "1/2", value = 1/2, type = "clock_division"},
  {name = "1", value = 1, type = "clock_multiplication"},
  {name = "1.5", value = 1.5, type = "clock_multiplication"},
  {name = "2", value = 2, type = "clock_multiplication"},
  {name = "3", value = 3, type = "clock_multiplication"},
  {name = "4", value = 4, type = "clock_multiplication"},
  {name = "5", value = 5, type = "clock_multiplication"},
  {name = "6", value = 6, type = "clock_multiplication"},
  {name = "7", value = 7, type = "clock_multiplication"},
  {name = "8", value = 8, type = "clock_multiplication"},
  {name = "9", value = 9, type = "clock_multiplication"},
  {name = "10", value = 10, type = "clock_multiplication"},
  {name = "11", value = 11, type = "clock_multiplication"},
  {name = "12", value = 12, type = "clock_multiplication"},
  {name = "13", value = 13, type = "clock_multiplication"},
  {name = "14", value = 14, type = "clock_multiplication"},
  {name = "15", value = 15, type = "clock_multiplication"},
  {name = "16", value = 16, type = "clock_multiplication"},
  {name = "24", value = 24, type = "clock_multiplication"},
  {name = "32", value = 32, type = "clock_multiplication"},
  {name = "64", value = 64, type = "clock_multiplication"}
}

function clock_controller.calculate_divisor(clock_mod)
  if clock_mod.type == "clock_multiplication" then
    return 4 * clock_mod.value
  elseif clock_mod.type == "clock_division" then
    return 4 / clock_mod.value
  else
    return 4
  end
end

function clock_controller.calculate_note_divisor(clock_mod)
  if clock_mod.type == "clock_division" then
    return 1 / clock_mod.value
  elseif clock_mod.type == "clock_multiplication" then
    return 1 * clock_mod.value
  else
    return 1
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

function clock_controller.init()
  local program_data = program.get()
  clock_lattice = lattice:new()

  if testing then
    clock_lattice.auto = false
  end

  destroy_delay_sprockets()
  delayed_sprockets = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}

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
      swing = 50,
      enabled = true
    }

  for channel_number = 17, 1, -1 do
    local channel = program.get_channel(channel_number)
    local div = clock_controller.calculate_divisor(channel.clock_mods)
    local swing = channel_number == 17 and 50 or channel.swing

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

        if channel_number ~= 17 then
          step_handler.process_lengths_for_channel(channel_number)
        end
      end
    end

    clock_controller["channel_" .. channel_number .. "_clock"] = clock_lattice:new_sprocket {
      action = sprocket_action,
      division = 1 / (div * 4),
      swing = swing,
      enabled = true
    }

    clock_controller["channel_" .. channel_number .. "_clock"].end_of_clock_processor = clock_lattice:new_sprocket {
      action = end_of_clock_action,
      division = 1 / (div * 4),
      swing = 50,
      delay = 0.95,
      enabled = true
    }

    clock_controller["channel_" .. channel_number .. "_clock"].first_run = true
  end
end

function clock_controller.set_channel_swing(channel_number, swing)
  local clock = clock_controller["channel_" .. channel_number .. "_clock"]
  clock:set_swing(swing)
  clock.end_of_clock_processor:set_swing(swing)
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

function clock_controller.delay_action(c, division_index, multiplier, must_execute, func)
  if division_index == 0 or division_index == nil then
    func()
    return
  end
  local delayed
  local sprocket_action = function(t)
    func()
    delayed:destroy()
  end

  local division = note_divisions[division_index].value * clock_controller["channel_" .. c .. "_clock"].division * multiplier
  delayed = clock_lattice:new_sprocket {
    action = sprocket_action,
    division = division,
    enabled = true,
    delay = 0.90
  }

  if must_execute then
    table.insert(delayed_sprockets_must_execute[c], delayed)
  else
    table.insert(delayed_sprockets[c], delayed)
  end
end

function clock_controller.new_arp_sprocket(c, division_index, length, func)
  if division_index == 0 or division_index == nil then
    return
  end

  if (arp_sprockets[c]) then
    for i, sprocket in ipairs(arp_sprockets[c]) do
      sprocket:destroy()
    end
  end

  local arp
  local runs = 0
  local total_runs = length / note_divisions[division_index].value
  local sprocket_action = function(t)
      func()
    if length == 0 then
      arp:destroy()
    end
  end

  arp = clock_lattice:new_sprocket {
    action = function()
      sprocket_action()
      runs = runs + 1
      if runs >= total_runs then
        arp:destroy()
      end
    end,
    division = note_divisions[division_index].value * clock_controller["channel_" .. c .. "_clock"].division,
    enabled = true
  }

  table.insert(arp_sprockets[c], arp)
end


function execute_delayed_sprockets()
  for i, sprocket_table in ipairs(delayed_sprockets_must_execute) do
    for j, item in ipairs(sprocket_table) do
      if item then
        item:action()
      end
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
  
  clock.run(function()
    clock.sync(1/32)
    midi_controller.start()   
  end)
       

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

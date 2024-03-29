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

function clock_controller.calculate_divisor(clock_mod)
  local divisor = 4

  if clock_mod.type == "clock_multiplication" then
    divisor = 4 * clock_mod.value
  elseif clock_mod.type == "clock_division" then
    divisor = 4 / clock_mod.value
  end

  return divisor
end

local function destroy_delay_sprockets()
  for i, sprocket_table in ipairs(delayed_sprockets) do
    if (sprocket_table) then
      for j, item in ipairs(sprocket_table) do
          if item then
            item:destroy()
          end
      end
    end
  end
end

function clock_controller.init()
  clock_lattice = lattice:new()

  if testing then
    clock_lattice.auto = false
  end

  destroy_delay_sprockets()
  delayed_sprockets = {{},{},{},{},{},{},{},{},{},{},{},{},{},{},{},{}}

  master_clock =
    clock_lattice:new_sprocket {
      action = function(t)
        if first_run ~= true then
          step_handler.process_song_sequencer_patterns(program.get().current_step)
          local selected_sequencer_pattern_number = program.get().selected_sequencer_pattern
          local selected_sequencer_pattern = program.get().sequencer_patterns[selected_sequencer_pattern_number]
          if program.get().global_step_accumulator % selected_sequencer_pattern.global_pattern_length == 0 then
            for i = 1, 17 do
                if (((fn.calc_grid_count(program.get_channel(i).end_trig[1], program.get_channel(i).end_trig[2]) 
                  - fn.calc_grid_count(program.get_channel(i).start_trig[1], program.get_channel(i).start_trig[2]) + 1)
                  > selected_sequencer_pattern.global_pattern_length)) then
                    program.set_current_step_for_channel(i, 99)
                end
              end
            end
          end

        program.get().current_step = program.get().current_step + 1
        program.get().global_step_accumulator = program.get().global_step_accumulator + 1

        if program.get().current_step > program.get_selected_sequencer_pattern().global_pattern_length then
          program.get().current_step = 1
          first_run = false
        end
      end,
      division = 1 / 16,
      swing = 50,
      enabled = true
    }

  for channel_number = 17, 1, -1 do
    local div = 1
    div = clock_controller.calculate_divisor(program.get_channel(channel_number).clock_mods)

    local swing = program.get_channel(channel_number).swing

    if channel_number == 17 then
      swing = 50
    end

    clock_controller["channel_" .. channel_number .. "_clock"] =
      clock_lattice:new_sprocket {
      action = function(t)
        
        if channel_number ~= 17 then
          step_handler.process_lengths_for_channel(channel_number)
        end

        local start_trig =
          fn.calc_grid_count(
          program.get_channel(channel_number).start_trig[1],
          program.get_channel(channel_number).start_trig[2]
        )
        local end_trig =
          fn.calc_grid_count(
          program.get_channel(channel_number).end_trig[1],
          program.get_channel(channel_number).end_trig[2]
        )
        local current_step = program.get_current_step_for_channel(channel_number)

        if current_step < start_trig then
          program.set_current_step_for_channel(channel_number, start_trig)
          current_step = start_trig
        end

        if clock_controller["channel_" .. channel_number .. "_clock"].first_run ~= true then
          program.set_current_step_for_channel(channel_number, current_step + 1)
          current_step = current_step + 1
        end

        if program.get_current_step_for_channel(channel_number) > end_trig then
          program.set_current_step_for_channel(channel_number, start_trig)
          current_step = start_trig
        end

        if channel_number ~= 17 then
          local next_trig_value = program.get_channel(channel_number).working_pattern.trig_values[current_step]
          if next_trig_value == 1 then
            trigless_lock_active[channel_number] = false
            step_handler.process_params(channel_number, current_step)
          elseif
            params:get("trigless_locks") == 1 and trigless_lock_active[i] ~= true and
              program.step_has_param_trig_lock(program.get_channel(channel_number), current_step)
           then
            trigless_lock_active[channel_number] = true
            step_handler.process_params(channel_number, current_step)
          end
        end

        if channel_number == 17 then
          step_handler.process_global_step_scale_trig_lock(current_step)
          step_handler.sinfonian_sync(current_step)

        end

        if channel_number ~= 17 then
          step_handler.handle(channel_number, current_step)
        end

        clock_controller["channel_" .. channel_number .. "_clock"].first_run = false
        clock_controller["channel_" .. channel_number .. "_clock"].next_step = current_step

        if program.get().selected_channel == channel_number and program.get().selected_page == program.get_pages().channel_edit_page then
          fn.dirty_grid(true)
        end
      end,
      division = 1 / (div * 4),
      swing = swing,
      enabled = true
    }

    clock_controller["channel_" .. channel_number .. "_clock"].first_run = true
  end

end

function clock_controller.set_channel_swing(channel_number, swing)
  clock_controller["channel_" .. channel_number .. "_clock"]:set_swing(swing)
end

function clock_controller.set_channel_division(channel_number, division)
  clock_controller["channel_" .. channel_number .. "_clock"]:set_division(1 / (division * 4))
end

function clock_controller.delay_action(c, division_index, multiplier, func)
  
  if division_index == 0 or division_index == nil then
    func()
    return
  end
  local first_run = true
  local delayed
  local sprocket_action = function(t)
    if first_run ~= true then
      func()
      delayed:destroy()
    else
      first_run = false
    end
  end

  delayed = clock_lattice:new_sprocket {
    action = sprocket_action,
    division = (clock_controller.calculate_divisor(clock_divisions[division_index]) * clock_controller["channel_" .. c .. "_clock"].division) * multiplier,
    enabled = true
  }

  table.insert(delayed_sprockets[c], delayed)
end

function clock_controller:start()
  first_run = true
  clock_controller.set_playing()

  midi_controller.start()

  for i = 1, 16 do
    step_handler.process_params(i, 1)
  end

  clock_lattice:start()
end

function clock_controller:stop()
  if clock_lattice and clock_lattice.stop then
    clock_lattice:stop()
  end

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
  for x, pattern in ipairs(program.get().sequencer_patterns) do
    for i = 1, 17 do
      program.set_current_step_for_channel(i, 1)
    end
  end

  program.get().current_step = 1
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

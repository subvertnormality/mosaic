local fn = include 'lib/functions'

local midi_controller = include 'lib/midi_controller'
local step_handler = include 'lib/step_handler'
local ListSelector = include 'lib/ui_components/ListSelector'

local clock_controller = {}

local playing = false
local master_clock
local midi_transport

local time_store = 0

local master_clock
local midi_transport
local trigless_lock_active = {}

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

function map_log(x)
  local min_x = 0
  local max_x = 50
  local min_y = 16
  local max_y = 2

  if x == min_x then return min_y end
  if x == max_x then return max_y end

  -- normalize x to 0-1 range, and slightly shift it to avoid log(0)
  local norm_x = (x - min_x) / (max_x - min_x) + 0.01

  -- convert to log scale, normalize to 0-1 range
  local log_x = (math.log(norm_x) - math.log(0.01)) / (math.log(1) - math.log(0.01))

  -- scale to y range
  local y = log_x * (max_y - min_y) + min_y

  return fn.round_to_decimal_places(y, 2)
end



local function channel_go(channel_number, divisor, on_step)
  local div = divisor
  local swing_on = 0
  while true do

    local clock_mod = program.get_channel(channel_number).clock_mods

    if clock_mod.type == "clock_multiplication" then
      div = 4 * clock_mod.value
    elseif clock_mod.type == "clock_division" then
      div = 4 / clock_mod.value
    end



    local beat = 1/div
    local processed_swing = program.get_channel(channel_number).swing

    if processed_swing < 0 then
      processed_swing = 0
    end

    if processed_swing == 0 then
      clock.sync(beat)
    else
      
      local s = map_log(processed_swing)
      clock.sync(beat, (beat/s) * swing_on)
    end
    on_step()
    swing_on = swing_on ~ 1
  end
end

local function go(divisor, on_step)
  local div = divisor
  while true do
    clock.sync(1/div)
    on_step()
  end
end

local function start_midi_transport(divisor)
  clock.sync(1/divisor)
  midi_controller:start()
end


local function delay_param_set(channel, func)

  local divisor = 4

  if channel then
    local clock_mod = channel.clock_mods

    if clock_mod.type == "clock_multiplication" then
      divisor = 4 * clock_mod.value
    elseif clock_mod.type == "clock_division" then
      divisor = 4 / clock_mod.value
    end
  end

  local d = divisor + 1
  local pause = (1/d)
  clock.sync(pause)
  pause = 1/(d*6)
  clock.sync(pause)
  func()
end

local function master_func() 

  step_handler.process_lengths()
  step_handler.process_song_sequencer_patterns(program.get().current_step)

  program.get().current_step = program.get().current_step + 1

  if program.get().current_step > program.get_selected_sequencer_pattern().global_pattern_length then
    program.get().current_step = 1
  end
  fn.dirty_grid(true)
end


function clock_controller:start() 

  for i = 1, 16 do
    step_handler.process_params(i, 1)
  end

  midi_transport = clock.run(start_midi_transport, 4)
  midi_clock = clock.run(go, 24, function () midi_controller.clock_send() end)
  master_clock = clock.run(go, 4, master_func)
  for i = 1, 16 do
    local channel = program.get_channel(i)
    clock_controller["channel_"..i.."_clock"] = clock.run(channel_go, i, 4, function () 

      local start_trig = fn.calc_grid_count(program.get_channel(i).start_trig[1], program.get_channel(i).start_trig[2])
      local end_trig = fn.calc_grid_count(program.get_channel(i).end_trig[1], program.get_channel(i).end_trig[2])
      local current_step = program.get_channel(i).current_step

      if program.get_channel(i).current_step < start_trig then
        program.get_channel(i).current_step = start_trig
        current_step = start_trig - 1
      end

      local next_step = program.get_channel(i).current_step + 1

      if next_step > end_trig then
        next_step = start_trig
      end

      local next_trig_value = program.get_channel(i).working_pattern.trig_values[next_step]

      step_handler.handle(i, current_step)


      if next_trig_value == 1 then
        time_store = clock.get_beats()
        trigless_lock_active[i] = false
        clock.run(delay_param_set, program.get_channel(i), function ()
          step_handler.process_params(i, next_step)
        end)
        
      elseif params:get("trigless_locks") == 1 and trigless_lock_active[i] ~= true and program.step_has_param_trig_lock(program.get_channel(i), next_step) then
        time_store = clock.get_beats()
        trigless_lock_active[i] = true
        clock.run(delay_param_set, program.get_channel(i), function ()
          step_handler.process_params(i, next_step)
        end)
      end
    
      program.get_channel(i).current_step = current_step + 1
    
      if program.get_channel(i).current_step > end_trig then
        program.get_channel(i).current_step = start_trig
      end
      fn.dirty_grid(true)
      fn.dirty_screen(true)
    end)
  end

  
  playing = true
end

function clock_controller:stop()

  if (playing) then
    if (master_clock) then
      clock.cancel(master_clock)
    end
    if (midi_transport) then
      clock.cancel(midi_transport)
    end
    if (midi_clock) then
      clock.cancel(midi_clock)
    end
    midi_controller:stop()
    for i = 1, 16 do
      if clock_controller["channel_"..i.."_clock"] then
        clock.cancel(clock_controller["channel_"..i.."_clock"])
      end
    end
    playing = false
    clock_controller.reset() 
  end
end

function clock_controller.is_playing()
  return playing
end


function clock_controller.reset() 
  for x, pattern in ipairs(program.get().sequencer_patterns) do

    for i = 1, 16 do
      pattern.channels[i].current_step = 1
    end

  end
  program.get().current_step = 1
  step_handler.reset()
end

function clock_controller.get_clock_divisions()
  return clock_divisions
end

return clock_controller
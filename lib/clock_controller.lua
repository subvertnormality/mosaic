local beatclock = require 'beatclock'
local fn = include 'lib/functions'

local midi_controller = include 'lib/midi_controller'
local step_handler = include 'lib/step_handler'

local clock_controller = {}

local playing = false

for i = 1, 16 do
  clock_controller["channel_"..i.."_clock"] = beatclock.new()
end

local master_clock = beatclock.new()
local midi_clock = beatclock.new()


function clock_controller:init()
  for i = 1, 16 do
    local clock_division = program.sequencer_patterns[program.selected_sequencer_pattern].channels[i].clock_division

    master_clock:bpm_change(program.bpm)
    midi_clock:bpm_change(program.bpm * 6)

    clock_controller["channel_"..i.."_clock"]:bpm_change(fn.round(program.bpm / clock_division))
    clock_controller["channel_"..i.."_clock"].on_step = function () 

      local channel = program.sequencer_patterns[program.selected_sequencer_pattern].channels[i]
      local start_trig = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
      local end_trig = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])
      local current_step = channel.current_step

      if channel.current_step < start_trig then
        channel.current_step = start_trig
        current_step = start_trig
      end

      step_handler:handle(i, current_step)
    
      channel.current_step = current_step + 1

      if channel.current_step > end_trig then
        channel.current_step = start_trig
      end


      fn.dirty_grid(true)

    end
    master_clock.on_step = function () 

      step_handler:process_lengths()

      program.current_step = program.current_step + 1

      if program.current_step > program.sequencer_patterns[program.selected_sequencer_pattern].global_pattern_length then
        program.current_step = 1
      end

    end

    midi_clock.on_step = function() 
      midi_controller:clock_send()
    end

  end
end

function clock_controller:update_divisions()
  for i = 1, 16 do
    local clock_division = program.sequencer_patterns[program.selected_sequencer_pattern].channels[i].clock_division
    clock_controller["channel_"..i.."_clock"]:bpm_change(fn.round(program.bpm / clock_division))
  end
end

function clock_controller:start() 
  master_clock:start()
  midi_clock:start()
  midi_controller:start()
  playing = true
  for i = 1, 16 do
    clock_controller["channel_"..i.."_clock"]:start()
  end
end

function clock_controller:stop()
  master_clock:stop()
  midi_clock:stop()
  midi_controller:stop()
  playing = false
  for i = 1, 16 do
    clock_controller["channel_"..i.."_clock"]:stop()
  end
end

function clock_controller:is_playing()
  return playing
end

function clock_controller:reset() 
  master_clock:reset()
  midi_clock:reset()
  for i = 1, 16 do
    clock_controller["channel_"..i.."_clock"]:reset()
    program.sequencer_patterns[program.selected_sequencer_pattern].channels[i].current_step = 1
  end
  program.current_step = 1
end

return clock_controller
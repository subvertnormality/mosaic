local beatclock = require 'beatclock'
local fn = include 'lib/functions'

local clock_controller = {}

for i = 1, 16 do
  clock_controller["channel_"..i.."_clock"] = beatclock.new()
end

local master_clock = beatclock.new()



function clock_controller:init()
  for i = 1, 16 do
    local clock_division = program.sequencer_patterns[program.selected_sequencer_pattern].channels[i].clock_division
    clock_controller["channel_"..i.."_clock"]:bpm_change(fn.round(program.bpm / clock_division))
    clock_controller["channel_"..i.."_clock"].on_step = function () 

      local channel = program.sequencer_patterns[program.selected_sequencer_pattern].channels[i]
      local start_trig = fn.calc_grid_count(channel.start_trig[1], channel.start_trig[2])
      local end_trig = fn.calc_grid_count(channel.end_trig[1], channel.end_trig[2])

      if channel.current_step < start_trig then
        channel.current_step = start_trig
      end

      channel.current_step = channel.current_step + 1

      if channel.current_step > end_trig then
        channel.current_step = start_trig
      end

      if program.selected_channel == i then
        fn.dirty_grid(true)
      end
    end
    master_clock.on_step = function () 
      program.current_step = program.current_step + 1

      if program.current_step > program.sequencer_patterns[program.selected_sequencer_pattern].global_pattern_length then
        program.current_step = 1
      end

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
  for i = 1, 16 do
    clock_controller["channel_"..i.."_clock"]:start()
  end
end


return clock_controller
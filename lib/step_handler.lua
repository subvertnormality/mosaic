local midi_controller = include("lib/midi_controller")

local step_handler = {}
local length_tracker = {}

function step_handler:handle(c) 

  local channel = program.sequencer_patterns[program.selected_sequencer_pattern].channels[c]
  local current_step = channel.current_step

  local trig_value = channel.working_pattern.trig_values[current_step]
  local note_value = channel.working_pattern.note_values[current_step]
  local velocity_value = channel.working_pattern.velocity_values[current_step]
  local length_value = channel.working_pattern.lengths[current_step]
  local midi_channel = channel.midi_channel
  local midi_device = channel.midi_device

  if trig_value == 1 then
    midi_controller:note_on(note_value + program.root_note, velocity_value, midi_channel, midi_device)
    table.insert(length_tracker, {note = note_value + program.root_note, velocity = velocity_value, midi_channel = midi_channel, midi_device = midi_device, steps_remaining = length_value})
  end

end


function step_handler:process_lengths() 
  for i=#length_tracker, 1, -1 do
    local l = length_tracker[i]
    l.steps_remaining = l.steps_remaining - 1
    if l.steps_remaining < 1 then
      midi_controller:note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
      table.remove(length_tracker, i)
    end
  end
end

return step_handler
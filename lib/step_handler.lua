local midi_controller = include("lib/midi_controller")
local quantiser = include("lib/quantiser")

local step_handler = {}
local length_tracker = {}

local step_scale_number = 0

local do_once = true

function step_handler.process_params(c, step)
  local channel = program.get_channel(c)

  for i=1,8 do
    step_trig_lock = program.get_step_trig_lock(step, i)
    if channel.trig_lock_params[i] and channel.trig_lock_params[i].cc_msb then
      if step_trig_lock then
        midi_controller.cc(channel.trig_lock_params[i].cc_msb, step_trig_lock, channel.midi_channel, channel.midi_device)
      else
        midi_controller.cc(channel.trig_lock_params[i].cc_msb, channel.trig_lock_banks[i], channel.midi_channel, channel.midi_device)
      end
    end
  end
end

function step_handler.handle(c, current_step) 

  local channel = program.get_channel(c)
  local channel_step_scale_number = channel.step_scales[current_step]

  local trig_value = channel.working_pattern.trig_values[current_step]

  local note_value = channel.working_pattern.note_values[current_step]
  local velocity_value = channel.working_pattern.velocity_values[current_step]
  local length_value = channel.working_pattern.lengths[current_step]
  local midi_channel = channel.midi_channel
  local midi_device = channel.midi_device
  local octave_mod = channel.octave
  
  if (channel_step_scale_number > 0) then
    step_scale_number = channel_step_scale_number
  elseif
    (channel.default_scale > 0) then
    step_scale_number = channel.default_scale
  else
    step_scale_number = program.get().default_scale
  end

  if trig_value == 1 then
    channel_edit_page_ui_controller.refresh_trig_locks()
    local note = quantiser.process(note_value, octave_mod, step_scale_number, channel)
    midi_controller.note_on(note, velocity_value, midi_channel, midi_device)
    table.insert(length_tracker, {note = note, velocity = velocity_value, midi_channel = midi_channel, midi_device = midi_device, steps_remaining = length_value})
  end

end


function step_handler.process_lengths() 
  for i=#length_tracker, 1, -1 do
    local l = length_tracker[i]
    l.steps_remaining = l.steps_remaining - 1
    if l.steps_remaining < 1 then
      midi_controller.note_off(l.note, l.velocity, l.midi_channel, l.midi_device)
      table.remove(length_tracker, i)
    end
  end
end

return step_handler
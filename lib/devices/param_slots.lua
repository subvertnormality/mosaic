local param_slots = {
  CHANNEL_COUNT = 16,
  SLOT_COUNT = 180,
  LOCK_SLOT_COUNT = 10,
  FIXED_NOTE_SLOT = 2,
  QUANTISED_FIXED_NOTE_SLOT = 3,
  SLEW_SLOT = 40,
}

function param_slots.group_id(channel)
  return "midi_device_params_group_channel_" .. channel
end

function param_slots.control_id(channel, slot)
  return "midi_device_params_channel_" .. channel .. "_" .. slot
end

function param_slots.assignment_id(channel, slot)
  return string.format("midi_device_params_channel_%d_%d", channel, slot)
end

return param_slots

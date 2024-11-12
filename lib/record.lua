local record = {}
local record_store = {}

local function initialise_default_channel()
  return {
    step_trig_masks = {},
    step_note_masks = {},
    step_velocity_masks = {},
    step_length_masks = {},
    step_chord_masks = {},
  }
end

local function initialise_default_sequencer_pattern()
  return {
    channels = {}
  }
end

function record.init()
  record_store = {
    sequencer_patterns = {}
  }
  -- Initialize the first sequencer pattern
  record.get_sequencer_pattern(1)
end

function record.get()
  return record_store
end

function record.get_sequencer_pattern(p)
  if not record_store.sequencer_patterns[p] then
    record_store.sequencer_patterns[p] = initialise_default_sequencer_pattern()
  end
  return record_store.sequencer_patterns[p]
end

function record.get_channel(song_pattern, x)
  local pattern = record.get_sequencer_pattern(song_pattern)
  if not pattern.channels[x] then
    pattern.channels[x] = initialise_default_channel()
    pattern.channels[x].number = x
  end
  return pattern.channels[x]
end

function record.get_step_trig_mask(song_pattern, channel, step)
  return record.get_channel(song_pattern, channel).step_trig_masks[step]
end

function record.set_step_trig_mask(song_pattern, channel, step, mask)
  record.get_channel(song_pattern, channel).step_trig_masks[step] = mask
end

function record.get_step_note_mask(song_pattern, channel, step)
  return record.get_channel(song_pattern, channel).step_note_masks[step]
end

function record.set_step_note_mask(song_pattern, channel, step, mask)
  record.get_channel(song_pattern, channel).step_note_masks[step] = mask
end

function record.get_step_velocity_mask(song_pattern, channel, step)
  return record.get_channel(song_pattern, channel).step_velocity_masks[step]
end

function record.set_step_velocity_mask(song_pattern, channel, step, mask)
  record.get_channel(song_pattern, channel).step_velocity_masks[step] = mask
end

function record.get_step_length_mask(song_pattern, channel, step)
  return record.get_channel(song_pattern, channel).step_length_masks[step]
end

function record.set_step_length_mask(song_pattern, channel, step, mask)
  record.get_channel(song_pattern, channel).step_length_masks[step] = mask
end

function record.get_step_chord_mask(song_pattern, channel, step)
  return record.get_channel(song_pattern, channel).step_chord_masks[step]
end

function record.set_step_chord_mask(song_pattern, channel, step, mask)
  record.get_channel(song_pattern, channel).step_chord_masks[step] = mask
end

return record
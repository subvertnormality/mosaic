-- README#trig-parameters: trig params are unique to a song pattern. A channel's
-- sequencer (stock) params, such as Chord Strum or Trig Probability, are single
-- controls in the norns paramset, so each song pattern keeps its own values on
-- its channels and they are swapped into the paramset when the selected pattern
-- changes. Everything that plays or draws reads the paramset, so playback, the
-- Trig params page, previews and lock lookahead all see the selected pattern's
-- values. Device params are a patch, shared by every song pattern (README
-- "Device configuration"), and are not swapped.
local song_slot_params = {}

local CHANNEL_COUNT = 16

-- A song pattern is created when first used, so one that does not exist yet
-- has nothing to capture or restore.
local function channel_of(program_data, song_pattern_number, channel_number)
  local song_pattern = program_data.song_patterns and program_data.song_patterns[song_pattern_number]
  return song_pattern and song_pattern.channels and song_pattern.channels[channel_number]
end

-- Remember the paramset's current stock values on a song pattern's channels.
function song_slot_params.capture(program_data, song_pattern_number)
  for channel_number = 1, CHANNEL_COUNT do
    local channel = channel_of(program_data, song_pattern_number, channel_number)
    if channel then
      local values
      fn.each_stock_param_id(channel_number, function(stock_id, param_id)
        local value = params:get(param_id)
        if value ~= nil then
          values = values or {}
          values[stock_id] = value
        end
      end)
      channel.stock_param_values = values
    end
  end
end

-- Put a song pattern's remembered stock values into the paramset. A pattern
-- that has remembered nothing yet leaves the paramset as it is. Returns whether
-- any value changed.
function song_slot_params.restore(program_data, song_pattern_number)
  local changed = false
  for channel_number = 1, CHANNEL_COUNT do
    local channel = channel_of(program_data, song_pattern_number, channel_number)
    local values = channel and channel.stock_param_values
    if values then
      fn.each_stock_param_id(channel_number, function(stock_id, param_id)
        local value = values[stock_id]
        if value ~= nil and params:get(param_id) ~= value then
          params:set(param_id, value, true)
          changed = true
        end
      end)
    end
  end
  return changed
end

-- The selected song pattern changes from one to another.
function song_slot_params.switch(program_data, from, to)
  if from == nil or to == nil or from == to then return end
  song_slot_params.capture(program_data, from)
  song_slot_params.restore(program_data, to)
end

return song_slot_params

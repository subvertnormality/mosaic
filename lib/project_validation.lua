-- Validate range-bearing saved data without changing the current project.
local validation = {}

local function integer(value, low, high)
  return type(value) == "number" and value >= low and value <= high and value % 1 == 0
end

local function endpoint(value)
  return type(value) == "table" and integer(value[1], 1, 16) and integer(value[2], 4, 7)
end

function validation.check(saved)
  if type(saved) ~= "table" or type(saved[2]) ~= "table" or
    (saved[1] ~= nil and type(saved[1]) ~= "string") then
    return nil, "Invalid project envelope"
  end
  local data = saved[2]
  -- Existing migration recognizes this alias. Validation itself is read-only.
  local songs = data.song_patterns or data.sequencer_patterns
  if type(songs) ~= "table" then return nil, "Invalid song slots" end
  for slot, song in pairs(songs) do
    if not integer(slot, 1, 96) or type(song) ~= "table" then
      return nil, "Invalid song slot"
    end
    local prefix = "Slot " .. slot
    if not integer(song.global_pattern_length, 1, 64) then
      return nil, prefix .. " global length"
    end
    if type(song.channels) ~= "table" then return nil, prefix .. " channels" end
    for number = 1, 17 do
      local channel = song.channels[number]
      local label = prefix .. " ch " .. number
      if type(channel) ~= "table" then return nil, label .. " missing" end
      if not endpoint(channel.start_trig) then return nil, label .. " start" end
      if not endpoint(channel.end_trig) then return nil, label .. " end" end
      local first = (channel.start_trig[2] - 4) * 16 + channel.start_trig[1]
      local last = (channel.end_trig[2] - 4) * 16 + channel.end_trig[1]
      -- Equal endpoints are valid stored data; only their grid gesture is absent.
      if first > last then return nil, label .. " reversed" end
    end
  end
  return true
end

return validation

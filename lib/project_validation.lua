-- Validate range-bearing saved data without changing the current project.
local validation = {}
local function dependency(name, path)
  if type(include) == "function" then return include(path) end
  return require(name)
end
local harmony_config = include("mosaic/lib/harmony/config")
local merge_config = include("mosaic/lib/musical_merge/config")
local rhythm_doctor_persistence = dependency("rhythm_doctor.bank_persistence", "mosaic/lib/rhythm_doctor/bank_persistence")

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
    local harmony_ok, harmony_reason = harmony_config.validate_song(song)
    if not harmony_ok then return nil, prefix .. " " .. harmony_reason end
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
      if channel.musical_merge ~= nil then
        local merge_ok, merge_reason = merge_config.validate(channel.musical_merge)
        if not merge_ok then return nil, prefix .. " " .. merge_reason end
        local target = channel.musical_merge.target
        if target and target.kind == "chord" then
          local groups = song.voicing and song.voicing.groups
          if not groups or not groups[target.group_id] then
            return nil, label .. " merge target group missing"
          end
        end
      end
    end
  end
  local rhythm_ok, rhythm_reason = rhythm_doctor_persistence.validate(data.rhythm_doctor)
  if not rhythm_ok then return nil, rhythm_reason == "UNKNOWN_BANK_SCHEMA" and "Unknown Rhythm Doctor bank" or "Invalid Rhythm Doctor bank" end
  return true
end

return validation

-- Captured-target helpers shared by the Channel-page adapters (UI02): masks,
-- parameters, device, clock, history and assignment.
--
-- A Channel target is {channel =, song_slot =, held = {step, ...}, ...}. Every
-- key is optional; a present key must still match the owner state. The owners
-- read the held set from m_grid.get_pressed_keys() at call time, so an adapter
-- refuses a target whose held set is not exactly the one the owner would edit.

local channel_target = {}

-- Ordered held step numbers, read the way the mask handlers (held_step_keys)
-- and refreshers read them: pressed keys on grid rows 4..7.
function channel_target.held_steps()
  local steps = {}
  if not (m_grid and m_grid.get_pressed_keys) then return steps end
  for _, key in ipairs(m_grid.get_pressed_keys()) do
    if key[2] > 3 and key[2] < 8 then steps[#steps + 1] = fn.calc_grid_count(key[1], key[2]) end
  end
  return steps
end

function channel_target.pressed_count()
  if not (m_grid and m_grid.get_pressed_keys) then return 0 end
  return #m_grid.get_pressed_keys()
end

function channel_target.same_steps(a, b)
  if #a ~= #b then return false end
  for index = 1, #a do
    if a[index] ~= b[index] then return false end
  end
  return true
end

-- The target still names the owner's selected channel, song slot and held set.
-- `only_step_keys` also refuses a hold that includes non-step keys (the trig
-- lock handler edits every pressed key, not only rows 4..7).
function channel_target.valid(target, only_step_keys)
  if type(target) ~= "table" then return false end
  local state = program.get()
  if target.channel ~= nil and target.channel ~= state.selected_channel then return false end
  if target.song_slot ~= nil and target.song_slot ~= state.selected_song_pattern then return false end
  local held = channel_target.held_steps()
  if not channel_target.same_steps(target.held or {}, held) then return false end
  if only_step_keys and channel_target.pressed_count() ~= #held then return false end
  return true
end

-- Nonnegative integer generation that advances whenever identity() changes.
function channel_target.generation(identity)
  local generation, last = 0, nil
  return function()
    local key = identity()
    if last ~= nil and key ~= last then generation = generation + 1 end
    last = key
    return generation
  end
end

function channel_target.identity()
  local state = program.get()
  return tostring(state.selected_song_pattern) .. ":" .. tostring(state.selected_channel) .. ":" ..
    table.concat(channel_target.held_steps(), ",")
end

-- CHANNEL, STEP05, or "<n> HELD" (screen C01 state explanation).
function channel_target.scope(held)
  if #held == 0 then return "CHANNEL" end
  if #held == 1 then return string.format("STEP%02d", held[1]) end
  return #held .. " HELD"
end

function channel_target.format_steps(held)
  local parts = {}
  for _, s in ipairs(held) do parts[#parts + 1] = string.format("%02d", s) end
  return table.concat(parts, " ")
end

-- Run an owner closure once per encoder detent, passing the whole delta each
-- time, exactly as channel_edit_navigation.enc does for E3.
function channel_target.per_detent(delta, call)
  local result
  for _ = 1, math.abs(delta) do result = call(delta) end
  return result
end

return channel_target
